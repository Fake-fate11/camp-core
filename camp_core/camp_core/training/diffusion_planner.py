#!/usr/bin/env python3
"""Train the V26 scene-conditioned CAMP finite-K objective with observation.

Each outer work step advances the current convex master to either solver-native
completion or JAXopt's native work boundary, evaluates all K candidates, and
adds only missing original finite-master cuts.  The academic approximate rule
tracks the best full-K feasible objective: after 100 native blocks without a
0.1% cumulative improvement, one exact full-K check of that incumbent either
adds unseen cuts and warm-continues or saves a zero-unseen approximate Benders
checkpoint without claiming solver-native optimality.
"""

from __future__ import annotations

import argparse
import gzip
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Iterator, Mapping, Sequence

import numpy as np


from camp_core.integrations.diffusion_planner_v26_scene_camp_math import (  # noqa: E402
    V26_CVAR_ALPHA,
    empirical_cvar,
    fixed_v26_scene_camp_atom_scales,
    normalize_v26_sparse_pool,
    project_rows_to_simplex,
    scales_by_global_name,
)
from camp_core.integrations.diffusion_planner_v26_sparse_schema import (  # noqa: E402
    V26_GLOBAL_ATOM_NAMES,
)
from camp_core.integrations.diffusion_planner_v26_scene_camp_jaxopt import (  # noqa: E402
    ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS,
    ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT,
    solve_scene_conditioned_camp_jaxopt_benders,
)


@dataclass
class PatternData:
    status_pattern: tuple[str, ...]
    active_global_indices: tuple[int, ...]
    anchor_ids: tuple[str, ...]
    embeddings: np.ndarray
    candidate_atoms: np.ndarray
    expert_atoms: np.ndarray
    candidate_cuts: list[set[int]]
    candidate_offsets: np.ndarray | None = None
    candidate_face_scales: np.ndarray | None = None
    scene_group_indices: np.ndarray | None = None
    record_weights: np.ndarray | None = None
    objective_kind_override: str | None = None


class ProgressReporter:
    """Persist only observed stage and solver progress for the current run."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.started = time.monotonic()

    def update(self, phase: str, **metrics: Any) -> dict[str, Any]:
        document = {
            "phase": str(phase),
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "worker_pid": os.getpid(),
            "output_root": str(self.path.parent),
            "elapsed_seconds": time.monotonic() - self.started,
            **metrics,
        }
        temporary = self.path.with_suffix(self.path.suffix + ".partial")
        temporary.write_text(
            json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
        print(json.dumps({"progress": document}, sort_keys=True), flush=True)
        return document


def _solver_observation(problem: Any, wall_elapsed_seconds: float) -> dict[str, Any]:
    """Return only solver statistics actually exposed by CVXPY."""

    stats = problem.solver_stats
    return {
        "solver_name": str(stats.solver_name),
        "solver_status": str(problem.status),
        "solver_iterations": None if stats.num_iters is None else int(stats.num_iters),
        "solver_solve_time_seconds": (
            None if stats.solve_time is None else float(stats.solve_time)
        ),
        "solver_setup_time_seconds": (
            None if stats.setup_time is None else float(stats.setup_time)
        ),
        "solver_objective": float(problem.value),
        "wall_solve_elapsed_seconds": float(wall_elapsed_seconds),
        "primal_dual_residual_gap_source": (
            "forwarded_verbatim_in_CVXPY_CLARABEL_verbose_worker_log; "
            "CVXPY_SolverStats_does_not_expose_these_fields"
        ),
    }


def _jsonl(path: Path) -> Iterator[Mapping[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, Mapping):
                    raise ValueError("complete-pool JSONL rows must be objects")
                yield value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_theta_checkpoint(
    path: Path,
    *,
    patterns: list[PatternData],
    theta_values: Mapping[tuple[str, ...], np.ndarray],
    metadata: Mapping[str, Any],
) -> None:
    arrays: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    for index, pattern in enumerate(patterns):
        key = tuple(pattern.status_pattern)
        theta_key = f"theta_{index:03d}"
        arrays[theta_key] = np.asarray(theta_values[key], dtype=np.float64)
        arrays[f"active_global_indices_{index:03d}"] = np.asarray(
            pattern.active_global_indices, dtype=np.int64
        )
        arrays[f"status_pattern_{index:03d}"] = np.asarray(
            pattern.status_pattern, dtype="U32"
        )
        rows.append(
            {
                "pattern_index": index,
                "theta_key": theta_key,
                "status_pattern": list(pattern.status_pattern),
                "active_global_atom_indices": list(pattern.active_global_indices),
                "scene_count": int(pattern.embeddings.shape[0]),
            }
        )
    temporary = path.with_name(path.stem + ".partial.npz")
    np.savez(temporary, **arrays)
    os.replace(temporary, path)
    _write_json(
        path.with_suffix(".json"),
        {
            **dict(metadata),
            "checkpoint": str(path),
            "patterns": rows,
        },
    )


def _load_reusable_bt_state(
    path: Path, patterns: list[PatternData]
) -> tuple[dict[tuple[str, ...], dict[str, Any]], dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("patterns")
    if not isinstance(rows, list):
        raise ValueError("reusable BT state must contain pattern rows")
    by_pattern: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("reusable BT pattern rows must be mappings")
        key = tuple(str(value) for value in row.get("status_pattern", ()))
        weights = np.asarray(row.get("weights"), dtype=np.float64)
        if key in by_pattern or not key or not np.all(np.isfinite(weights)):
            raise ValueError("reusable BT pattern identity or weights are invalid")
        by_pattern[key] = {**row, "weights": weights}
    expected = {tuple(pattern.status_pattern) for pattern in patterns}
    if set(by_pattern) != expected:
        raise ValueError("reusable BT patterns do not match the loaded population")
    for pattern in patterns:
        weights = by_pattern[tuple(pattern.status_pattern)]["weights"]
        if (
            weights.shape != (pattern.candidate_atoms.shape[2],)
            or np.any(weights < 0.0)
            or not np.isclose(np.sum(weights), 1.0, rtol=0.0, atol=1e-10)
        ):
            raise ValueError("reusable BT weights do not match one active simplex")
    return by_pattern, document


def _load_theta_resume_seed(
    path: Path, patterns: list[PatternData]
) -> dict[tuple[str, ...], np.ndarray]:
    metadata_path = path.with_suffix(".json")
    document = json.loads(metadata_path.read_text(encoding="utf-8"))
    rows = document.get("patterns")
    if not isinstance(rows, list) or len(rows) != len(patterns):
        raise ValueError("resume checkpoint pattern metadata differs from population")
    result: dict[tuple[str, ...], np.ndarray] = {}
    with np.load(path, allow_pickle=False) as arrays:
        for pattern, row in zip(patterns, rows):
            if not isinstance(row, Mapping):
                raise ValueError("resume checkpoint pattern rows must be mappings")
            key = tuple(str(value) for value in row.get("status_pattern", ()))
            if key != tuple(pattern.status_pattern):
                raise ValueError("resume checkpoint status-pattern order changed")
            if tuple(int(value) for value in row["active_global_atom_indices"]) != tuple(
                pattern.active_global_indices
            ):
                raise ValueError("resume checkpoint active atoms changed")
            theta = np.asarray(arrays[str(row["theta_key"])], dtype=np.float64)
            expected_shape = (
                pattern.candidate_atoms.shape[2],
                pattern.embeddings.shape[1] + 1,
            )
            if theta.shape != expected_shape or not bool(np.all(np.isfinite(theta))):
                raise ValueError("resume checkpoint Theta is invalid")
            result[key] = theta.copy()
    return result


def _native_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _load_embeddings(paths: Sequence[Path]) -> tuple[dict[str, np.ndarray], int]:
    result: dict[str, np.ndarray] = {}
    embedding_dimension: int | None = None
    for path in paths:
        with np.load(path, allow_pickle=False) as bundle:
            anchor_ids = np.asarray(bundle["anchor_ids"]).reshape(-1)
            embeddings = np.asarray(bundle["pooled_encoder"], dtype=np.float64)
        if embeddings.ndim != 2 or embeddings.shape[0] != anchor_ids.size:
            raise ValueError(
                "embedding bundle must contain anchor_ids [N] and pooled_encoder [N,D]"
            )
        if embeddings.shape[1] < 1 or not np.all(np.isfinite(embeddings)):
            raise ValueError("pooled encoder embeddings must be finite and nonempty")
        if embedding_dimension is None:
            embedding_dimension = int(embeddings.shape[1])
        elif embedding_dimension != int(embeddings.shape[1]):
            raise ValueError("embedding shard dimensions must match")
        for raw_id, embedding in zip(anchor_ids, embeddings):
            anchor_id = _native_text(raw_id)
            if anchor_id in result:
                raise ValueError(f"duplicate embedding anchor_id: {anchor_id}")
            result[anchor_id] = embedding.copy()
    if embedding_dimension is None:
        raise ValueError("at least one embedding bundle is required")
    return result, embedding_dimension


def _load_pattern_data(
    pool_paths: Sequence[Path],
    *,
    bank_names: Sequence[str],
    normalize_pool: Callable[..., Mapping[str, Any]],
    atom_scales: Mapping[str, float],
    embeddings_by_anchor: Mapping[str, np.ndarray],
    expected_scenes: int,
    progress: ProgressReporter | None = None,
    structured_ranking: bool = False,
    pool_delta_ranking: bool = False,
    pool_delta_slack_rescaling: bool = False,
    grouped_scene_cvar: bool = False,
) -> tuple[list[PatternData], dict[str, Any]]:
    if pool_delta_slack_rescaling and not pool_delta_ranking:
        raise ValueError("Pool-Delta slack rescaling requires Pool-Delta ranking")
    grouped: dict[
        tuple[str, ...],
        dict[str, Any],
    ] = {}
    used_anchor_ids: set[str] = set()
    used_sample_ids: set[str] = set()
    group_index_by_anchor: dict[str, int] = {}
    rounds_by_anchor: dict[str, set[str]] = {}
    record_count_by_anchor: dict[str, int] = {}
    expected_records = int(expected_scenes) * (2 if grouped_scene_cvar else 1)
    loading_started = time.monotonic()
    artifacts = (artifact for path in pool_paths for artifact in _jsonl(path))
    for processed, artifact in enumerate(artifacts, start=1):
        normalization_artifact = artifact
        if structured_ranking and pool_delta_ranking:
            teacher = artifact.get("pool_delta_teacher")
            teacher_row = int(teacher.get("teacher_row", -1)) if isinstance(teacher, Mapping) else -1
            candidate_raw = np.asarray(artifact.get("candidate_atoms_raw"), dtype=np.float64)
            observed_names = tuple(str(name) for name in artifact.get("observed_atom_names", ()))
            if (
                candidate_raw.ndim != 2
                or candidate_raw.shape[1] != len(observed_names)
                or not 0 <= teacher_row < candidate_raw.shape[0]
            ):
                raise ValueError("Pool-Delta candidate-only normalization view is invalid")
            normalization_artifact = dict(artifact)
            normalization_artifact["human_atoms_raw"] = candidate_raw[teacher_row].tolist()
            normalization_artifact["human_observed_atom_names"] = list(observed_names)
            normalization_artifact["human_margin_delta"] = 1.0
        normalized = normalize_pool(normalization_artifact, atom_scales=atom_scales)
        identity = normalized["identity"]
        anchor_id = str(identity.get("anchor_id", ""))
        sample_id = str(artifact.get("training_sample_id", anchor_id))
        if not anchor_id or not sample_id or sample_id in used_sample_ids:
            raise ValueError("training pools must have unique nonempty sample identities")
        try:
            embedding = embeddings_by_anchor[anchor_id]
        except KeyError as exc:
            raise ValueError(f"missing pooled encoder embedding: {anchor_id}") from exc
        used_anchor_ids.add(anchor_id)
        used_sample_ids.add(sample_id)
        group_index = group_index_by_anchor.setdefault(
            anchor_id, len(group_index_by_anchor)
        )
        behavior_round = str(
            artifact.get("materialization", {}).get("behavior_round", "")
        )
        rounds_by_anchor.setdefault(anchor_id, set()).add(behavior_round)
        record_count_by_anchor[anchor_id] = record_count_by_anchor.get(anchor_id, 0) + 1
        status_by_name = normalized["atom_status_by_name"]
        status_pattern = tuple(status_by_name[name] for name in bank_names)
        active_indices = tuple(normalized["active_global_atom_indices"])
        holder = grouped.setdefault(
            status_pattern,
            {
                "active_indices": active_indices,
                "anchor_ids": [],
                "embeddings": [],
                "candidate_atoms": [],
                "expert_atoms": [],
                "candidate_offsets": [],
                "candidate_face_scales": [],
                "scene_group_indices": [],
                "record_weights": [],
            },
        )
        if holder["active_indices"] != active_indices:
            raise RuntimeError("one endpoint-status pattern produced different active atoms")
        holder["anchor_ids"].append(sample_id)
        holder["embeddings"].append(embedding)
        holder["candidate_atoms"].append(normalized["candidate_atoms"])
        if pool_delta_ranking:
            teacher = artifact.get("pool_delta_teacher")
            if not isinstance(teacher, Mapping):
                raise ValueError("Pool-Delta training row lacks its fixed teacher")
            teacher_row = int(teacher.get("teacher_row", -1))
            offsets = np.asarray(
                teacher.get("candidate_regret_delta"), dtype=np.float64
            )
            candidates = np.asarray(normalized["candidate_atoms"], dtype=np.float64)
            if (
                not 0 <= teacher_row < candidates.shape[0]
                or offsets.shape != (candidates.shape[0],)
                or not np.all(np.isfinite(offsets))
                or np.any(offsets < 0.0)
                or offsets[teacher_row] != 0.0
            ):
                raise ValueError("Pool-Delta teacher row or candidate regret is invalid")
            holder["expert_atoms"].append(candidates[teacher_row])
            holder["candidate_offsets"].append(offsets)
            holder["candidate_face_scales"].append(
                offsets if pool_delta_slack_rescaling else np.ones_like(offsets)
            )
        else:
            holder["expert_atoms"].append(normalized["expert_atoms"])
            holder["candidate_offsets"].append(
                np.ones(normalized["candidate_atoms"].shape[0], dtype=np.float64)
                if structured_ranking
                else np.zeros(normalized["candidate_atoms"].shape[0], dtype=np.float64)
            )
            holder["candidate_face_scales"].append(
                np.ones(normalized["candidate_atoms"].shape[0], dtype=np.float64)
            )
        holder["scene_group_indices"].append(group_index)
        holder["record_weights"].append(0.5 if grouped_scene_cvar else 1.0)
        if progress is not None and (
            processed == 1 or processed % 1_000 == 0 or processed == expected_records
        ):
            loading_elapsed = time.monotonic() - loading_started
            loading_rate = processed / loading_elapsed
            progress.update(
                "loading_complete_pools",
                processed=processed,
                denominator=expected_records,
                research_scene_denominator=int(expected_scenes),
                complete=processed == expected_records,
                throughput_anchors_per_second=loading_rate,
                eta_seconds=(
                    max(expected_records - processed, 0) / loading_rate
                ),
                pattern_count_observed_so_far=len(grouped),
            )

    if len(used_sample_ids) != expected_records:
        raise ValueError(
            f"full training record count must be {expected_records}, got {len(used_sample_ids)}"
        )
    if len(used_anchor_ids) != int(expected_scenes):
        raise ValueError(
            f"research scene count must be {expected_scenes}, got {len(used_anchor_ids)}"
        )
    if grouped_scene_cvar:
        invalid_rounds = {
            anchor_id: sorted(rounds)
            for anchor_id, rounds in rounds_by_anchor.items()
            if rounds != {"round0", "round1"}
            or record_count_by_anchor[anchor_id] != 2
        }
        if invalid_rounds:
            raise ValueError(
                "grouped scene CVaR requires one round0 and one round1 record per anchor"
            )
    if not structured_ranking and set(embeddings_by_anchor) != used_anchor_ids:
        raise ValueError("embedding and complete-pool anchor populations must match exactly")
    if structured_ranking and not used_anchor_ids.issubset(set(embeddings_by_anchor)):
        raise ValueError("structured training references an anchor without a frozen embedding")

    patterns: list[PatternData] = []
    for status_pattern, holder in sorted(grouped.items()):
        candidates = np.stack(holder["candidate_atoms"]).astype(np.float64, copy=False)
        experts = np.stack(holder["expert_atoms"]).astype(np.float64, copy=False)
        patterns.append(
            PatternData(
                status_pattern=status_pattern,
                active_global_indices=tuple(holder["active_indices"]),
                anchor_ids=tuple(holder["anchor_ids"]),
                embeddings=np.stack(holder["embeddings"]).astype(np.float64, copy=False),
                candidate_atoms=candidates,
                expert_atoms=experts,
                candidate_offsets=np.stack(holder["candidate_offsets"]).astype(
                    np.float64, copy=False
                ),
                candidate_face_scales=(
                    np.stack(holder["candidate_face_scales"]).astype(
                        np.float64, copy=False
                    )
                    if pool_delta_slack_rescaling
                    else None
                ),
                candidate_cuts=[set() for _ in range(candidates.shape[0])],
                scene_group_indices=np.asarray(
                    holder["scene_group_indices"], dtype=np.int64
                ),
                record_weights=np.asarray(holder["record_weights"], dtype=np.float64),
            )
        )
    if progress is not None:
        progress.update(
            "patterns_ready",
            processed=len(used_sample_ids),
            denominator=expected_records,
            research_scene_denominator=int(expected_scenes),
            complete=True,
            pattern_count=len(patterns),
            pattern_scene_counts=[
                int(pattern.embeddings.shape[0]) for pattern in patterns
            ],
            eta="unknown_until_solver_rounds_complete",
        )
    return patterns, {
        "scene_count": len(used_anchor_ids),
        "record_count": len(used_sample_ids),
        "unique_anchor_count": len(used_anchor_ids),
        "records_per_scene": 2 if grouped_scene_cvar else 1,
        "risk_population": "50k_unique_scene_grouped_round_average" if grouped_scene_cvar else "unique_scenes",
        "pattern_count": len(patterns),
        "pattern_scene_counts": [int(pattern.embeddings.shape[0]) for pattern in patterns],
        "embedding_dimension": int(patterns[0].embeddings.shape[1]),
    }


def _apply_demonstration_preference_targets(
    patterns: list[PatternData], target_path: Path, *, expected_scenes: int
) -> dict[str, Any]:
    with np.load(target_path.resolve(strict=True), allow_pickle=False) as bundle:
        raw_anchor_ids = np.asarray(bundle["anchor_ids"]).astype(str)
        target_mask = np.asarray(bundle["target_set_mask"], dtype=bool)
        beta_hat = np.asarray(bundle["beta_hat"], dtype=np.float64)
    if target_mask.ndim != 2 or target_mask.shape[0] != expected_scenes or target_mask.shape[1] < 1:
        raise ValueError("preference target mask must have shape [N,K], K>=1")
    if beta_hat.shape != (16,) or not np.all(np.isfinite(beta_hat)):
        raise ValueError("preference calibration beta must be finite shape [16]")
    target_by_anchor = {
        anchor: target.copy()
        for anchor, target in zip(raw_anchor_ids, target_mask, strict=True)
    }
    if len(target_by_anchor) != expected_scenes or np.any(target_mask.sum(axis=1) < 1):
        raise ValueError("preference targets must cover every scene with a nonempty set")
    applied = 0
    target_sizes: list[int] = []
    for pattern in patterns:
        rows = []
        for sample_id in pattern.anchor_ids:
            anchor_id = (
                sample_id.split(":", 1)[1]
                if sample_id.startswith(("round0:", "round1:"))
                else sample_id
            )
            try:
                rows.append(target_by_anchor[anchor_id])
            except KeyError as exc:
                raise ValueError(f"preference target lacks anchor: {anchor_id}") from exc
        membership = np.stack(rows)
        if membership.shape != pattern.candidate_atoms.shape[:2]:
            raise ValueError("preference target/candidate identity changed")
        target_sizes.extend(membership.sum(axis=1).astype(int).tolist())
        weights = membership.astype(np.float64)
        pattern.expert_atoms = np.einsum(
            "nk,nkq->nq", weights, pattern.candidate_atoms
        ) / weights.sum(axis=1, keepdims=True)
        negative = (~membership).astype(np.float64)
        pattern.candidate_offsets = negative
        pattern.candidate_face_scales = negative
        pattern.candidate_cuts = [set() for _ in range(membership.shape[0])]
        pattern.objective_kind_override = (
            "demonstration_calibrated_target_set_structured_hinge"
        )
        applied += membership.shape[0]
    if applied != expected_scenes:
        raise ValueError(f"preference targets applied to {applied}, expected {expected_scenes}")
    return {
        "source": str(target_path.resolve()),
        "scene_count": applied,
        "target_size_distribution": dict(Counter(target_sizes)),
        "beta_hat": beta_hat.tolist(),
        "loss": "max(0,max_k_not_in_P[1+(mean_p_in_P(x_ip)-x_ik)^T w_i])",
    }


def _solve_pattern_bt(pattern: PatternData, *, cp: Any, solver: str) -> dict[str, Any]:
    pair_delta = (pattern.expert_atoms[:, None, :] - pattern.candidate_atoms).reshape(
        -1, pattern.candidate_atoms.shape[2]
    )
    atom_count = pair_delta.shape[1]
    if atom_count == 1:
        weights = np.ones(1, dtype=np.float64)
        objective = float(np.mean(np.logaddexp(0.0, pair_delta[:, 0])))
        status = "analytic_single_atom"
        solver_observation = None
    else:
        variable = cp.Variable(atom_count)
        problem = cp.Problem(
            cp.Minimize(cp.sum(cp.logistic(pair_delta @ variable)) / pair_delta.shape[0]),
            [variable >= 0.0, cp.sum(variable) == 1.0],
        )
        solve_started = time.monotonic()
        problem.solve(solver=solver, verbose=True)
        solver_observation = _solver_observation(
            problem, time.monotonic() - solve_started
        )
        if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
            raise RuntimeError(f"Bradley-Terry solve ended with {problem.status}")
        weights = project_rows_to_simplex(np.asarray(variable.value, dtype=np.float64))
        objective = float(np.mean(np.logaddexp(0.0, pair_delta @ weights)))
        status = str(problem.status)
    return {
        "status": status,
        "active_global_atom_indices": list(pattern.active_global_indices),
        "scene_count": int(pattern.embeddings.shape[0]),
        "pair_count": int(pair_delta.shape[0]),
        "objective": objective,
        "solver_observation": solver_observation,
        "weights": weights,
    }


def _solve_restricted_master(
    patterns: list[PatternData],
    *,
    cp: Any,
    alpha: float,
    lambda_theta: float,
    solver: str,
    warm_state: Mapping[str, Any] | None,
) -> tuple[dict[tuple[str, ...], np.ndarray], dict[str, Any], dict[str, Any]]:
    eta = cp.Variable()
    theta_variables: dict[tuple[str, ...], Any] = {}
    weight_expressions: dict[tuple[str, ...], Any] = {}
    q_variables: dict[tuple[str, ...], Any] = {}
    slack_variables: dict[tuple[str, ...], Any] = {}
    constraints: list[Any] = []
    slack_sum: Any = 0.0
    theta_regularization: Any = 0.0
    total_scenes = sum(pattern.embeddings.shape[0] for pattern in patterns)

    for pattern_index, pattern in enumerate(patterns):
        scene_count, embedding_dimension = pattern.embeddings.shape
        atom_count = pattern.candidate_atoms.shape[2]
        phi_augmented = np.concatenate(
            [pattern.embeddings, np.ones((scene_count, 1), dtype=np.float64)], axis=1
        )
        theta = cp.Variable((atom_count, embedding_dimension + 1), name=f"theta_{pattern_index}")
        weights = cp.Variable((atom_count, scene_count), name=f"weights_{pattern_index}")
        restricted_cost = cp.Variable(scene_count, name=f"q_{pattern_index}")
        slack = cp.Variable(scene_count, nonneg=True, name=f"s_{pattern_index}")
        constraints.extend(
            [
                weights == theta @ phi_augmented.T,
                weights >= 0.0,
                cp.sum(weights, axis=0) == 1.0,
            ]
        )
        for candidate_index in range(pattern.candidate_atoms.shape[1]):
            scene_indices = np.asarray(
                [
                    scene_index
                    for scene_index, cuts in enumerate(pattern.candidate_cuts)
                    if candidate_index in cuts
                ],
                dtype=np.int64,
            )
            if scene_indices.size:
                candidate_columns = pattern.candidate_atoms[
                    scene_indices, candidate_index, :
                ].T
                constraints.append(
                    restricted_cost[scene_indices]
                    >= cp.sum(
                        cp.multiply(weights[:, scene_indices], candidate_columns), axis=0
                    )
                )
        constraints.append(slack >= restricted_cost - eta)
        slack_sum = slack_sum + cp.sum(slack)
        theta_regularization = theta_regularization + cp.sum_squares(theta)
        theta_variables[pattern.status_pattern] = theta
        weight_expressions[pattern.status_pattern] = weights
        q_variables[pattern.status_pattern] = restricted_cost
        slack_variables[pattern.status_pattern] = slack

        if warm_state is not None:
            key = pattern.status_pattern
            theta.value = np.asarray(warm_state["theta"][key], dtype=np.float64)
            weights.value = np.asarray(warm_state["weights"][key], dtype=np.float64).T
            restricted_cost.value = np.asarray(warm_state["q"][key], dtype=np.float64)
            slack.value = np.asarray(warm_state["slack"][key], dtype=np.float64)

    if warm_state is not None:
        eta.value = float(warm_state["eta"])

    objective = cp.Minimize(
        eta
        + slack_sum / ((1.0 - float(alpha)) * total_scenes)
        + float(lambda_theta) * theta_regularization
    )
    problem = cp.Problem(objective, constraints)
    solve_started = time.monotonic()
    if str(solver).upper() == "SCS":
        problem.solve(
            solver=solver,
            verbose=True,
            warm_start=True,
            use_indirect=True,
        )
    else:
        problem.solve(solver=solver, verbose=True, warm_start=True)
    solver_observation = _solver_observation(
        problem, time.monotonic() - solve_started
    )
    if problem.status != cp.OPTIMAL:
        raise RuntimeError(f"scene-conditioned CAMP master ended with {problem.status}")

    theta_values: dict[tuple[str, ...], np.ndarray] = {}
    next_state: dict[str, Any] = {
        "theta": {},
        "weights": {},
        "q": {},
        "slack": {},
        "eta": float(eta.value),
    }
    for pattern in patterns:
        key = pattern.status_pattern
        theta_values[key] = np.asarray(theta_variables[key].value, dtype=np.float64)
        next_state["theta"][key] = theta_values[key]
        next_state["weights"][key] = np.asarray(
            weight_expressions[key].value, dtype=np.float64
        ).T
        next_state["q"][key] = np.asarray(q_variables[key].value, dtype=np.float64)
        next_state["slack"][key] = np.asarray(
            slack_variables[key].value, dtype=np.float64
        )
    return theta_values, next_state, {
        "status": str(problem.status),
        "restricted_objective": float(problem.value),
        "eta": float(eta.value),
        "solver_observation": solver_observation,
    }


def _project_theta_to_primal_feasible(
    pattern: PatternData, theta: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, float | bool]]:
    theta_bar = np.asarray(theta, dtype=np.float64).copy()
    atom_count = int(theta_bar.shape[0])
    target_sum = np.zeros(theta_bar.shape[1], dtype=np.float64)
    target_sum[-1] = 1.0
    theta_bar += (target_sum - np.sum(theta_bar, axis=0))[None, :] / atom_count
    z = np.concatenate(
        [
            np.asarray(pattern.embeddings, dtype=np.float64),
            np.ones((pattern.embeddings.shape[0], 1), dtype=np.float64),
        ],
        axis=1,
    )
    weights = z @ theta_bar.T
    minimum = float(np.min(weights))
    rho = 0.0
    if minimum < 0.0:
        uniform = np.zeros_like(theta_bar)
        uniform[:, -1] = 1.0 / atom_count
        rho = float(np.nextafter(-minimum / (1.0 / atom_count - minimum), 1.0))
        theta_bar = (1.0 - rho) * theta_bar + rho * uniform
        weights = z @ theta_bar.T
        for _ in range(4):
            minimum = float(np.min(weights))
            if minimum >= 0.0:
                break
            delta = float(
                np.nextafter(-minimum / (1.0 / atom_count - minimum), 1.0)
            )
            theta_bar = (1.0 - delta) * theta_bar + delta * uniform
            rho = 1.0 - (1.0 - rho) * (1.0 - delta)
            weights = z @ theta_bar.T
    fallback = False
    if np.any(weights < 0.0) or not np.all(np.isfinite(weights)):
        fallback = True
        theta_bar = np.zeros_like(theta_bar)
        theta_bar[:, -1] = 1.0 / atom_count
        weights = z @ theta_bar.T
        rho = 1.0
    return theta_bar, weights, {
        "simplex_error": float(np.max(np.abs(np.sum(weights, axis=1) - 1.0))),
        "minimum_weight": float(np.min(weights)),
        "uniform_mix_rho": rho,
        "uniform_fallback": fallback,
    }


def _initial_master_warm_state(
    patterns: list[PatternData],
    *,
    bt_rows: Mapping[tuple[str, ...], Mapping[str, Any]],
    alpha: float,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "theta": {},
        "weights": {},
        "q": {},
        "slack": {},
    }
    q_parts: list[np.ndarray] = []
    for pattern in patterns:
        key = pattern.status_pattern
        bt = np.asarray(bt_rows[key]["weights"], dtype=np.float64)
        theta = np.zeros(
            (bt.size, pattern.embeddings.shape[1] + 1), dtype=np.float64
        )
        theta[:, -1] = bt
        weights = np.broadcast_to(bt, (pattern.embeddings.shape[0], bt.size)).copy()
        scores = np.einsum("nkr,nr->nk", pattern.candidate_atoms, weights)
        q = np.asarray(
            [
                max(scores[index, candidate] for candidate in cuts)
                for index, cuts in enumerate(pattern.candidate_cuts)
            ],
            dtype=np.float64,
        )
        state["theta"][key] = theta
        state["weights"][key] = weights
        state["q"][key] = q
        q_parts.append(q)
    all_q = np.concatenate(q_parts)
    eta = float(np.sort(all_q)[max(int(np.ceil(float(alpha) * all_q.size)) - 1, 0)])
    state["eta"] = eta
    for pattern in patterns:
        key = pattern.status_pattern
        state["slack"][key] = np.maximum(state["q"][key] - eta, 0.0)
    return state


def _train_to_full_candidate_convergence(
    patterns: list[PatternData],
    *,
    bt_rows: Mapping[tuple[str, ...], Mapping[str, Any]],
    cp: Any,
    alpha: float,
    lambda_theta: float,
    solver: str,
    device_name: str,
    progress: ProgressReporter | None = None,
    checkpoint: Any | None = None,
) -> tuple[dict[tuple[str, ...], np.ndarray], list[dict[str, Any]]]:
    for pattern in patterns:
        bt_weights = np.asarray(bt_rows[pattern.status_pattern]["weights"], dtype=np.float64)
        scores = np.einsum("nkr,r->nk", pattern.candidate_atoms, bt_weights)
        worst = np.argmax(scores, axis=1)
        for cuts, candidate_index in zip(pattern.candidate_cuts, worst):
            cuts.add(int(candidate_index))

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("GPU Benders separation requires torch") from exc
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    gpu_atoms = {
        pattern.status_pattern: torch.as_tensor(
            pattern.candidate_atoms, dtype=torch.float64, device=device
        )
        for pattern in patterns
    }
    warm_state = _initial_master_warm_state(
        patterns, bt_rows=bt_rows, alpha=float(alpha)
    )
    history: list[dict[str, Any]] = []
    best_theta: dict[tuple[str, ...], np.ndarray] | None = None
    best_full_objective = float("inf")
    training_started = time.monotonic()
    while True:
        round_index = len(history) + 1
        round_started = time.monotonic()
        active_cuts_before_solve = sum(
            len(cuts) for pattern in patterns for cuts in pattern.candidate_cuts
        )
        if progress is not None:
            progress.update(
                "cutting_plane_solver_running",
                round=round_index,
                active_candidate_cuts=active_cuts_before_solve,
                completed_rounds=len(history),
                master_solver=str(solver),
                master_termination="solver_native_default_numerical_status",
                eta="unknown_until_first_complete_round",
            )
        theta_values, warm_state, solve = _solve_restricted_master(
            patterns,
            cp=cp,
            alpha=alpha,
            lambda_theta=lambda_theta,
            solver=solver,
            warm_state=warm_state,
        )
        new_cuts = 0
        exact_cost_parts: list[np.ndarray] = []
        feasible_theta: dict[tuple[str, ...], np.ndarray] = {}
        max_simplex_error = 0.0
        minimum_weight = float("inf")
        separation_started = time.monotonic()
        for pattern in patterns:
            key = pattern.status_pattern
            theta_bar, weights, feasible = _project_theta_to_primal_feasible(
                pattern, theta_values[key]
            )
            feasible_theta[key] = theta_bar
            max_simplex_error = max(
                max_simplex_error, float(feasible["simplex_error"])
            )
            minimum_weight = min(minimum_weight, float(feasible["minimum_weight"]))
            weights_gpu = torch.as_tensor(weights, dtype=torch.float64, device=device)
            scores_gpu = torch.einsum("nkr,nr->nk", gpu_atoms[key], weights_gpu)
            worst_gpu = torch.argmax(scores_gpu, dim=1)
            exact_cost_parts.append(
                torch.max(scores_gpu, dim=1).values.detach().cpu().numpy()
            )
            worst = worst_gpu.detach().cpu().numpy()
            for scene_index, candidate_index_raw in enumerate(worst):
                candidate_index = int(candidate_index_raw)
                if candidate_index not in pattern.candidate_cuts[scene_index]:
                    pattern.candidate_cuts[scene_index].add(candidate_index)
                    new_cuts += 1
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        separation_elapsed = time.monotonic() - separation_started
        exact_cvar = empirical_cvar(np.concatenate(exact_cost_parts), alpha=alpha)
        exact_regularization = float(lambda_theta) * sum(
            float(np.sum(theta * theta)) for theta in feasible_theta.values()
        )
        exact_objective = exact_cvar + exact_regularization
        if exact_objective < best_full_objective:
            best_full_objective = exact_objective
            best_theta = {
                key: value.copy() for key, value in feasible_theta.items()
            }
        assert best_theta is not None
        active_cuts = sum(
            len(cuts) for pattern in patterns for cuts in pattern.candidate_cuts
        )
        round_elapsed = time.monotonic() - round_started
        missing_max = max(
            max(
                pattern.candidate_atoms.shape[1] - len(cuts)
                for cuts in pattern.candidate_cuts
            )
            for pattern in patterns
        )
        prior_durations = [float(row["round_elapsed_seconds"]) for row in history]
        typical_round = float(np.median(prior_durations + [round_elapsed]))
        remaining_passes_upper = 0 if new_cuts == 0 else missing_max + 1
        history_row = {
            "outer_step": round_index,
            "solver_status": solve["status"],
            "restricted_objective": solve["restricted_objective"],
            "exact_full_candidate_cvar": exact_cvar,
            "theta_regularization": exact_regularization,
            "exact_objective": exact_objective,
            "best_primal_feasible_full_objective": best_full_objective,
            "new_candidate_cuts": new_cuts,
            "total_candidate_cuts": active_cuts,
            "simplex_error": max_simplex_error,
            "minimum_weight": minimum_weight,
            "separation_device": str(device),
            "separation_elapsed_seconds": separation_elapsed,
            "separation_scenes_per_second": sum(
                pattern.embeddings.shape[0] for pattern in patterns
            )
            / max(separation_elapsed, np.finfo(np.float64).eps),
            "round_elapsed_seconds": round_elapsed,
            "total_elapsed_seconds": time.monotonic() - training_started,
            "eta_status": (
                "complete_zero_new_cut_pass"
                if new_cuts == 0
                else "finite_K_bound_with_observed_round_duration"
            ),
            "eta_seconds_range": (
                [0.0, 0.0]
                if new_cuts == 0
                else [typical_round, typical_round * remaining_passes_upper]
            ),
            "next_heartbeat_seconds": None if new_cuts == 0 else typical_round,
            "remaining_passes_upper_from_finite_K": remaining_passes_upper,
            "solver_observation": solve["solver_observation"],
        }
        history.append(history_row)
        if checkpoint is not None:
            checkpoint(
                {
                    "round": round_index,
                    "best_full_objective": best_full_objective,
                    "active_candidate_cuts": active_cuts,
                    "new_candidate_cuts": new_cuts,
                    "final_zero_new_cut_pass": bool(new_cuts == 0),
                    "simplex_error": max_simplex_error,
                    "minimum_weight": minimum_weight,
                },
                best_theta,
            )
        if progress is not None:
            progress.update(
                "cutting_plane_round_complete",
                round=round_index,
                completed_rounds=round_index,
                active_candidate_cuts=history_row["total_candidate_cuts"],
                new_candidate_cuts=new_cuts,
                restricted_objective=solve["restricted_objective"],
                exact_full_candidate_cvar=exact_cvar,
                theta_regularization=exact_regularization,
                exact_objective=history_row["exact_objective"],
                best_primal_feasible_full_objective=best_full_objective,
                simplex_error=max_simplex_error,
                minimum_weight=minimum_weight,
                separation_device=str(device),
                separation_scenes_per_second=history_row[
                    "separation_scenes_per_second"
                ],
                solver=solve["solver_observation"],
                final_zero_new_cut_pass=bool(new_cuts == 0),
                eta_status=history_row["eta_status"],
                eta_seconds_range=history_row["eta_seconds_range"],
                next_heartbeat_seconds=history_row["next_heartbeat_seconds"],
                remaining_passes_upper_from_finite_K=remaining_passes_upper,
            )
        if new_cuts == 0:
            return best_theta, history


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not hasattr(args, "structured_transition_ranking"):
        args.structured_transition_ranking = False
    if not hasattr(args, "sequential_camp"):
        args.sequential_camp = False
    if not hasattr(args, "grouped_scene_cvar"):
        args.grouped_scene_cvar = False
    if not hasattr(args, "pool_delta_ranking"):
        args.pool_delta_ranking = False
    if not hasattr(args, "pool_delta_slack_rescaling"):
        args.pool_delta_slack_rescaling = False
    if not hasattr(args, "preference_target_npz"):
        args.preference_target_npz = None
    if args.pool_delta_slack_rescaling:
        args.pool_delta_ranking = True
    if args.pool_delta_ranking:
        args.structured_transition_ranking = True
    if args.grouped_scene_cvar and not args.structured_transition_ranking:
        raise ValueError("grouped scene CVaR is defined only for structured transition ranking")
    if args.structured_transition_ranking and args.sequential_camp:
        raise ValueError("structured transition ranking and the 21-atom ablation are distinct paths")
    pool_paths = [path.resolve(strict=True) for path in args.complete_pool_jsonl]
    embedding_paths = [path.resolve(strict=True) for path in args.embedding_npz]
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    progress = ProgressReporter(output_dir / "progress.json")
    progress.update(
        "initializing",
        processed=0,
        denominator=int(args.expected_scenes),
        complete=False,
        bt_solver=str(args.solver),
        master_solver="active_cut_warm_native_work_blocks_with_exact_full_K_separation",
        eta="unknown",
    )

    scale_document = (
        fixed_v26_scene_camp_atom_scales()
        if args.atom_scales_json is None
        else json.loads(args.atom_scales_json.resolve(strict=True).read_text(encoding="utf-8"))
    )
    if args.structured_transition_ranking:
        from camp_core.integrations.diffusion_planner_v26_structured_transition_camp import (
            V26_STRUCTURED_ATOM_NAMES,
            normalize_structured_sparse_pool,
        )

        bank_names = V26_STRUCTURED_ATOM_NAMES
        normalize_pool = normalize_structured_sparse_pool
        atom_scales = {
            str(row["atom_name"]): float(row["scale"])
            for row in scale_document["atom_rows"]
        }
    elif args.sequential_camp:
        from camp_core.integrations.diffusion_planner_v26_sequential_camp import (
            V26_SEQUENTIAL_ATOM_NAMES,
            normalize_sequential_sparse_pool,
            scales_by_sequential_name,
        )

        bank_names = V26_SEQUENTIAL_ATOM_NAMES
        normalize_pool = normalize_sequential_sparse_pool
        atom_scales = scales_by_sequential_name(scale_document)
    else:
        bank_names = V26_GLOBAL_ATOM_NAMES
        normalize_pool = normalize_v26_sparse_pool
        atom_scales = scales_by_global_name(scale_document)
    embeddings_by_anchor, embedding_dimension = _load_embeddings(embedding_paths)
    patterns, population = _load_pattern_data(
        pool_paths,
        bank_names=bank_names,
        normalize_pool=normalize_pool,
        atom_scales=atom_scales,
        embeddings_by_anchor=embeddings_by_anchor,
        expected_scenes=args.expected_scenes,
        progress=progress,
        structured_ranking=bool(args.structured_transition_ranking),
        grouped_scene_cvar=bool(args.grouped_scene_cvar),
        pool_delta_ranking=bool(args.pool_delta_ranking),
        pool_delta_slack_rescaling=bool(args.pool_delta_slack_rescaling),
    )
    preference_target_document = None
    if args.preference_target_npz is not None:
        preference_target_document = _apply_demonstration_preference_targets(
            patterns,
            args.preference_target_npz,
            expected_scenes=int(args.expected_scenes),
        )
        _write_json(output_dir / "preference_target_definition.json", preference_target_document)
        progress.update(
            "demonstration_preference_targets_ready",
            processed=int(args.expected_scenes),
            denominator=int(args.expected_scenes),
            target_size_distribution=preference_target_document[
                "target_size_distribution"
            ],
            source=preference_target_document["source"],
            eta="unknown_until_first_complete_Benders_round",
        )
    if population["embedding_dimension"] != embedding_dimension:
        raise RuntimeError("packed embedding dimension changed")

    if args.structured_transition_ranking:
        bt_by_pattern = {
            pattern.status_pattern: {
                "weights": np.full(
                    pattern.candidate_atoms.shape[2],
                    1.0 / float(pattern.candidate_atoms.shape[2]),
                    dtype=np.float64,
                ),
                "initialization_role": "deterministic_uniform_cut_discovery_only",
            }
            for pattern in patterns
        }
        bt_document = {
            "objective": (
                "demonstration_calibrated_target_set_structured_hinge"
                if args.preference_target_npz is not None
                else
                "fixed_pool_delta_candidate_regret_supplies_face_offsets_and_slopes_with_unit_margin_one"
                if args.pool_delta_slack_rescaling
                else "fixed_pool_delta_candidate_regret_supplies_pairwise_face_offsets"
                if args.pool_delta_ranking
                else "none_human_demonstration_unit_margin_supplies_pairwise_faces"
            ),
            "patterns": [
                {
                    "status_pattern": list(pattern.status_pattern),
                    "weights": bt_by_pattern[pattern.status_pattern]["weights"].tolist(),
                    "initialization_role": "deterministic_uniform_cut_discovery_only",
                }
                for pattern in patterns
            ],
        }
        progress.update(
            (
                "pool_delta_fixed_teacher_state_ready"
                if args.pool_delta_ranking
                else "human_demonstration_state_ready"
            ),
            processed=int(args.expected_scenes),
            denominator=int(args.expected_scenes),
            pattern_count=len(patterns),
            eta="unknown_until_first_complete_Benders_round",
        )
    elif args.reuse_bt_json is not None:
        reusable_bt_path = args.reuse_bt_json.resolve(strict=True)
        bt_by_pattern, bt_document = _load_reusable_bt_state(
            reusable_bt_path, patterns
        )
        progress.update(
            "bt_state_reused",
            processed=int(args.expected_scenes),
            denominator=int(args.expected_scenes),
            pattern_count=len(patterns),
            bt_patterns_completed=len(patterns),
            source=str(reusable_bt_path),
            eta="unknown_until_first_complete_Benders_round",
        )
    else:
        try:
            import cvxpy as cp
        except ImportError as exc:
            raise RuntimeError("Bradley-Terry initialization requires cvxpy") from exc
        bt_by_pattern = {}
        for pattern_index, pattern in enumerate(patterns):
            progress.update(
                "bt_pattern_solver_running",
                processed=int(args.expected_scenes),
                denominator=int(args.expected_scenes),
                pattern_index=pattern_index,
                pattern_count=len(patterns),
                bt_patterns_completed=pattern_index,
                active_global_atom_indices=list(pattern.active_global_indices),
                pattern_scene_count=int(pattern.embeddings.shape[0]),
                eta="unknown_until_completed_pattern_solves_exist",
            )
            bt_result = _solve_pattern_bt(pattern, cp=cp, solver=args.solver)
            bt_by_pattern[pattern.status_pattern] = bt_result
            progress.update(
                "bt_pattern_solver_complete",
                processed=int(args.expected_scenes),
                denominator=int(args.expected_scenes),
                pattern_index=pattern_index,
                pattern_count=len(patterns),
                bt_patterns_completed=pattern_index + 1,
                pattern_objective=bt_result["objective"],
                pattern_pair_count=bt_result["pair_count"],
                solver=bt_result["solver_observation"],
                eta=("complete" if pattern_index + 1 == len(patterns) else "unknown"),
            )
        bt_document = {
            "objective": "pattern_local_expert_preferred_bradley_terry_no_added_regularizer",
            "patterns": [
                {
                    **{
                        key: value
                        for key, value in bt_by_pattern[pattern.status_pattern].items()
                        if key != "weights"
                    },
                    "status_pattern": list(pattern.status_pattern),
                    "weights": np.asarray(
                        bt_by_pattern[pattern.status_pattern]["weights"], dtype=np.float64
                    ).tolist(),
                }
                for pattern in patterns
            ],
        }
    _write_json(output_dir / "bt_initialization.json", bt_document)
    progress.update(
        "bt_state_saved",
        processed=int(args.expected_scenes),
        denominator=int(args.expected_scenes),
        pattern_count=len(patterns),
        bt_patterns_completed=len(patterns),
        reusable_bt_state=str(output_dir / "bt_initialization.json"),
        eta="unknown_until_first_complete_Benders_round",
    )

    resume_theta_rows: list[dict[tuple[str, ...], np.ndarray]] = []
    resume_theta_paths: list[str] = []
    for raw_path in args.resume_theta_checkpoint:
        resume_path = raw_path.resolve(strict=True)
        resume_theta_rows.append(_load_theta_resume_seed(resume_path, patterns))
        resume_theta_paths.append(str(resume_path))
    if resume_theta_rows:
        progress.update(
            "primal_checkpoint_resume_seeds_loaded",
            processed=int(args.expected_scenes),
            denominator=int(args.expected_scenes),
            complete=False,
            resume_theta_checkpoints=resume_theta_paths,
            resume_semantics=(
                "original_BT_cut_union_full_K_worst_legal_cuts_from_each_"
                "available_primal_checkpoint;_dual_params_native_state_and_"
                "historical_active_cut_identities_were_not_persisted"
            ),
            eta="unknown_until_first_complete_round",
        )

    best_checkpoint = output_dir / "best_primal_feasible_checkpoint.npz"
    current_checkpoint = output_dir / "current_approximate_checkpoint.npz"
    trajectory_path = output_dir / "trajectory.jsonl"
    latest_checkpoint_metadata: dict[str, Any] = {}

    def save_checkpoint(
        metadata: Mapping[str, Any],
        theta: Mapping[tuple[str, ...], np.ndarray],
    ) -> None:
        latest_checkpoint_metadata.clear()
        latest_checkpoint_metadata.update(dict(metadata))
        _write_theta_checkpoint(
            best_checkpoint,
            patterns=patterns,
            theta_values=theta,
            metadata={
                **dict(metadata),
                "objective": (
                    "full_K_equal_scene_CVaR_of_equal_round_average_pool_delta_candidate_regret_loss_plus_lambda_Theta_Frobenius_squared"
                    if args.pool_delta_ranking and args.grouped_scene_cvar
                    else "full_K_equal_scene_CVaR_pool_delta_candidate_regret_loss_plus_lambda_Theta_Frobenius_squared"
                    if args.pool_delta_ranking
                    else "full_K_equal_scene_CVaR_of_equal_round_average_unit_margin_human_demonstration_loss_plus_lambda_Theta_Frobenius_squared"
                    if args.structured_transition_ranking and args.grouped_scene_cvar
                    else "full_K_equal_scene_CVaR_unit_margin_human_demonstration_loss_plus_lambda_Theta_Frobenius_squared"
                    if args.structured_transition_ranking
                    else "full_K_equal_scene_CVaR_plus_lambda_Theta_Frobenius_squared"
                ),
                "primal_feasibility": (
                    "minimum_norm_affine_closure_then_minimum_closed_form_"
                    "uniform_mix_only_if_scene_weights_are_negative"
                ),
            },
        )

    progress.update(
        "benders_native_convex_master_starting",
        processed=int(args.expected_scenes),
        denominator=int(args.expected_scenes),
        complete=False,
        pattern_count=len(patterns),
        bt_patterns_completed=len(patterns),
        active_candidate_cuts=(
            None if resume_theta_rows else int(population["record_count"])
        ),
        active_candidate_cuts_lower_bound=int(population["record_count"]),
        resume_theta_checkpoints=resume_theta_paths,
        termination="academic_approximate_Benders_patience_100_on_best_feasible_full_objective_with_0.001_anchor_improvement_reset_then_one_exact_GPU_full_K_best_checkpoint_check;_unseen_cuts_warm_continue_and_reset_patience;_native_completion_is_optional",
        approximate_relative_improvement_reset=ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT,
        approximate_patience_blocks=ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS,
        approximate_eligible_block="every_native_block_best_primal_feasible_full_objective",
        approximate_nonconditions="no_fallback_free_or_recovery_window;_raw_scaled_error_weights_top1_rho_are_diagnostic_only;_no_solver_native_completion_requirement",
        requested_checkpoint_claim="approximate_Benders_not_solver_native_optimum",
        master_solver=str(args.master_solver),
        master_native_termination=(
            "JAXopt_default_numerical_status_only_for_final_master_completion;_"
            "native_maxiter_is_a_resumable_early_separation_work_boundary"
        ),
        master_linear_system=(
            "JAXopt_nonaccelerated_projected_gradient_default_backtracking_"
            "scene_density_empirical_L2_coordinate_scaling_GPU_float64_matrix_free"
        ),
        eta="unknown_until_first_complete_round",
    )
    if str(args.master_solver).upper() != "JAXOPT-PROJECTED-GRADIENT":
        raise ValueError(
            "the active finite-K master solver must be JAXOPT-PROJECTED-GRADIENT"
        )

    def report_benders(row: Mapping[str, Any]) -> None:
        progress.update(
            str(row["phase"]),
            **{key: value for key, value in row.items() if key != "phase"},
        )

    augmented_embeddings = {
        pattern.status_pattern: np.concatenate(
            [
                pattern.embeddings,
                np.ones((pattern.embeddings.shape[0], 1), dtype=np.float64),
            ],
            axis=1,
        )
        for pattern in patterns
    }
    previous_theta: np.ndarray | None = None
    previous_weights: np.ndarray | None = None
    previous_top1: np.ndarray | None = None

    def observe_separation(
        solver_row: Mapping[str, Any],
        current_theta: Mapping[tuple[str, ...], np.ndarray],
    ) -> None:
        nonlocal previous_theta, previous_weights, previous_top1
        theta_parts: list[np.ndarray] = []
        weight_parts: list[np.ndarray] = []
        top1_parts: list[np.ndarray] = []
        anchor_ids: list[str] = []
        for pattern in patterns:
            key = pattern.status_pattern
            theta = np.asarray(current_theta[key], dtype=np.float64)
            weights = augmented_embeddings[key] @ theta.T
            scores = np.einsum("nkr,nr->nk", pattern.candidate_atoms, weights)
            theta_parts.append(theta.reshape(-1))
            weight_parts.append(weights.reshape(-1))
            top1_parts.append(np.argmin(scores, axis=1).astype(np.int64, copy=False))
            anchor_ids.extend(pattern.anchor_ids)
        theta_vector = np.concatenate(theta_parts)
        weight_vector = np.concatenate(weight_parts)
        top1 = np.concatenate(top1_parts)
        if previous_theta is None:
            theta_change_max = theta_change_rms = None
            weight_change_max = weight_change_rms = weight_change_scene_l1 = None
            top1_changed = None
        else:
            theta_delta = theta_vector - previous_theta
            weight_delta = weight_vector - previous_weights
            theta_change_max = float(np.max(np.abs(theta_delta)))
            theta_change_rms = float(np.sqrt(np.mean(theta_delta * theta_delta)))
            weight_change_max = float(np.max(np.abs(weight_delta)))
            weight_change_rms = float(np.sqrt(np.mean(weight_delta * weight_delta)))
            weight_change_scene_l1 = float(
                np.sum(np.abs(weight_delta)) / float(population["record_count"])
            )
            top1_changed = int(np.sum(top1 != previous_top1))

        block = int(solver_row["outer_step"])
        checkpoint_metadata = {
            "status": "approximate_benders_checkpoint",
            "claim": "not_solver_native_optimum",
            "block": block,
            "master_iteration": int(solver_row["native_iteration_total"]),
            "exact_full_K_zero_new_cut": bool(solver_row["zero_new_cut_pass"]),
            "best_checkpoint_zero_unseen_legal_cuts": solver_row[
                "best_checkpoint_zero_unseen_legal_cuts"
            ],
            "best_checkpoint_new_candidate_cuts": solver_row[
                "best_checkpoint_new_candidate_cuts"
            ],
            "approximate_stop_eligible": bool(
                solver_row["approximate_stop_eligible"]
            ),
            "approximate_anchor_best_full_objective": solver_row[
                "approximate_anchor_best_full_objective"
            ],
            "approximate_patience": int(solver_row["approximate_patience"]),
            "approximate_final_check_armed": bool(
                solver_row["approximate_final_check_armed"]
            ),
            "approximate_terminal_completion": bool(
                solver_row["approximate_terminal_completion"]
            ),
            "completion_claim": str(solver_row["completion_claim"]),
            "current_full_K_objective": float(solver_row["exact_objective"]),
            "active_candidate_cuts": int(solver_row["total_candidate_cuts"]),
            "new_candidate_cuts": int(solver_row["new_candidate_cuts"]),
            "uniform_fallback_pattern_indices": list(
                solver_row["uniform_fallback_pattern_indices"]
            ),
            "uniform_fallback_affected_scenes": int(
                solver_row["uniform_fallback_affected_scenes"]
            ),
            "uniform_mixed_pattern_indices": list(
                solver_row["uniform_mixed_pattern_indices"]
            ),
            "maximum_uniform_mix_rho": float(
                solver_row["maximum_uniform_mix_rho"]
            ),
            "maximum_affine_projection_norm": float(
                solver_row["maximum_affine_projection_norm"]
            ),
        }
        _write_theta_checkpoint(
            current_checkpoint,
            patterns=patterns,
            theta_values=current_theta,
            metadata=checkpoint_metadata,
        )
        top1_temporary = output_dir / "current_top1_reranking.partial.npz"
        np.savez(
            top1_temporary,
            anchor_ids=np.asarray(anchor_ids, dtype=np.str_),
            candidate_indices=top1,
        )
        os.replace(top1_temporary, output_dir / "current_top1_reranking.npz")

        master_seconds = float(solver_row["master_elapsed_seconds"])
        native_iterations = int(solver_row["native_iterations"])
        row = {
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "worker_pid": os.getpid(),
            "output_root": str(output_dir),
            "block": block,
            "native_iteration_total": int(solver_row["native_iteration_total"]),
            "scaled_native_error": float(solver_row["native_error"]),
            "raw_equivalent_error": float(
                solver_row["native_error_raw_coordinate_equivalent"]
            ),
            "native_master_objective": float(solver_row["native_objective"]),
            "exact_full_K_objective": float(solver_row["exact_objective"]),
            "exact_full_K_cvar": float(solver_row["exact_full_candidate_cvar"]),
            "theta_regularization": float(solver_row["theta_regularization"]),
            "new_candidate_cuts": int(solver_row["new_candidate_cuts"]),
            "total_candidate_cuts": int(solver_row["total_candidate_cuts"]),
            "zero_new_cut_pass": bool(solver_row["zero_new_cut_pass"]),
            "best_checkpoint_zero_unseen_legal_cuts": solver_row[
                "best_checkpoint_zero_unseen_legal_cuts"
            ],
            "best_checkpoint_new_candidate_cuts": solver_row[
                "best_checkpoint_new_candidate_cuts"
            ],
            "strict_primal_feasible": bool(solver_row["strict_primal_feasible"]),
            "recovery_transition": bool(solver_row["recovery_transition"]),
            "approximate_stop_eligible": bool(
                solver_row["approximate_stop_eligible"]
            ),
            "approximate_anchor_best_full_objective": solver_row[
                "approximate_anchor_best_full_objective"
            ],
            "approximate_anchor_relative_cumulative_improvement": solver_row[
                "approximate_anchor_relative_cumulative_improvement"
            ],
            "approximate_patience": int(solver_row["approximate_patience"]),
            "approximate_final_check_armed": bool(
                solver_row["approximate_final_check_armed"]
            ),
            "approximate_terminal_completion": bool(
                solver_row["approximate_terminal_completion"]
            ),
            "solver_native_terminal_completion": bool(
                solver_row["solver_native_terminal_completion"]
            ),
            "completion_claim": str(solver_row["completion_claim"]),
            "master_native_complete": bool(solver_row["master_native_complete"]),
            "uniform_fallback_pattern_indices": list(
                solver_row["uniform_fallback_pattern_indices"]
            ),
            "uniform_fallback_affected_scenes": int(
                solver_row["uniform_fallback_affected_scenes"]
            ),
            "uniform_mixed_pattern_indices": list(
                solver_row["uniform_mixed_pattern_indices"]
            ),
            "maximum_uniform_mix_rho": float(
                solver_row["maximum_uniform_mix_rho"]
            ),
            "maximum_affine_projection_norm": float(
                solver_row["maximum_affine_projection_norm"]
            ),
            "theta_change_max_abs": theta_change_max,
            "theta_change_rms": theta_change_rms,
            "theta_norm_fro": float(np.linalg.norm(theta_vector)),
            "weights_change_max_abs": weight_change_max,
            "weights_change_rms": weight_change_rms,
            "weights_change_mean_scene_l1": weight_change_scene_l1,
            "weights_norm_fro": float(np.linalg.norm(weight_vector)),
            "top1_changed_records": top1_changed,
            "top1_candidate_indices": top1.tolist(),
            "native_work_elapsed_seconds": master_seconds,
            "native_iterations_per_second": native_iterations
            / max(master_seconds, np.finfo(np.float64).eps),
            "exact_separation_elapsed_seconds": float(
                solver_row["separation_elapsed_seconds"]
            ),
            "total_elapsed_seconds": float(solver_row["total_elapsed_seconds"]),
            "approximate_checkpoint": str(current_checkpoint),
            "final_eta_status": "unknown_pending_academic_patience_and_best_checkpoint_exact_separation",
            "final_eta_seconds_range": None,
        }
        with trajectory_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        previous_theta = theta_vector.copy()
        previous_weights = weight_vector.copy()
        previous_top1 = top1.copy()
        progress.update(
            (
                "structured_ranking_benders_block_observed"
                if args.structured_transition_ranking
                else "approximate_benders_block_observed"
            ),
            complete=False,
            processed=int(args.expected_scenes),
            denominator=int(args.expected_scenes),
            **{key: value for key, value in row.items() if key not in {
                "observed_at_utc", "worker_pid", "output_root", "top1_candidate_indices"
            }},
        )

    theta_values, history = solve_scene_conditioned_camp_jaxopt_benders(
        patterns,
        bt_rows=bt_by_pattern,
        alpha=args.alpha,
        lambda_theta=args.lambda_theta,
        progress=report_benders,
        checkpoint=save_checkpoint,
        separation_observer=observe_separation,
        resume_theta_rows=resume_theta_rows,
        structured_ranking=bool(args.structured_transition_ranking),
        grouped_scene_cvar=bool(args.grouped_scene_cvar),
        allow_academic_approximate_completion=True,
    )
    if not bool(history[-1]["terminal_completion"]):
        raise RuntimeError(
            "JAXopt Benders returned without an approximate or solver-native terminal"
        )

    progress.update(
        "writing_terminal_artifacts",
        processed=int(args.expected_scenes),
        denominator=int(args.expected_scenes),
        complete=False,
        completed_benders_rounds=len(history),
        final_native_master_complete=bool(history[-1]["master_native_complete"]),
        final_zero_new_cut_pass=bool(
            history[-1]["best_checkpoint_zero_unseen_legal_cuts"]
            if history[-1]["approximate_terminal_completion"]
            else history[-1]["zero_new_cut_pass"]
        ),
        approximate_terminal_completion=bool(
            history[-1]["approximate_terminal_completion"]
        ),
        completion_claim=str(history[-1]["completion_claim"]),
        terminal_completion=bool(history[-1]["terminal_completion"]),
        best_primal_feasible_checkpoint=str(best_checkpoint),
        eta="unknown",
    )
    _write_json(output_dir / "atom_scales.json", scale_document)
    _write_json(output_dir / "optimization_history.json", {"steps": history})

    parameter_arrays: dict[str, np.ndarray] = {}
    pattern_rows: list[dict[str, Any]] = []
    for index, pattern in enumerate(patterns):
        theta_key = f"theta_{index:03d}"
        parameter_arrays[theta_key] = theta_values[pattern.status_pattern]
        parameter_arrays[f"active_global_indices_{index:03d}"] = np.asarray(
            pattern.active_global_indices, dtype=np.int64
        )
        parameter_arrays[f"status_pattern_{index:03d}"] = np.asarray(
            pattern.status_pattern, dtype="U32"
        )
        pattern_rows.append(
            {
                "pattern_index": index,
                "theta_key": theta_key,
                "status_pattern": list(pattern.status_pattern),
                "active_global_atom_indices": list(pattern.active_global_indices),
                "scene_count": int(pattern.embeddings.shape[0]),
            }
        )
    np.savez(output_dir / "scene_conditioned_parameters.npz", **parameter_arrays)

    result = {
        "status": (
            "completed_approximate_Benders_checkpoint"
            if history[-1]["approximate_terminal_completion"]
            else "completed_solver_native_zero_new_cut_separation"
        ),
        "population": population,
        "global_atom_names": list(bank_names),
        "embedding": {
            "source": "fixed_diffusion_planner_encoder_token_mean",
            "dimension": embedding_dimension,
            "bundle": [str(path) for path in embedding_paths],
        },
        "objective": {
            "scene_cost": (
                "max_zero_and_pool_delta_times_one_plus_teacher_minus_candidate_score"
                if args.pool_delta_slack_rescaling
                else "max_zero_and_pool_delta_plus_teacher_minus_candidate_score"
                if args.pool_delta_ranking
                else "max_zero_and_one_plus_human_minus_candidate_score"
                if args.structured_transition_ranking
                else "max_over_all_configured_K_candidates"
            ),
            "risk": "equal_scene_empirical_cvar",
            "scene_loss_aggregation": (
                "one_half_round0_plus_one_half_round1_before_scene_CVaR"
                if args.grouped_scene_cvar
                else "one_record_per_scene"
            ),
            "risk_scene_count": int(args.expected_scenes),
            "alpha": float(args.alpha),
            "lambda_theta": float(args.lambda_theta),
            "missing_semantics": "separate_full_status_patterns_no_zero_fill",
            "candidate_filter": "none",
        },
        "convergence": {
            "definition": (
                "academic_approximate_Benders_patience_100_on_best_feasible_full_objective_with_0.001_anchor_improvement_reset_then_one_exact_GPU_full_K_best_checkpoint_check;_unseen_legal_cuts_warm_continue_and_reset_patience;_native_completion_is_optional_stronger_terminal"
            ),
            "master": "JAXopt_nonaccelerated_ProjectedGradient_exact_smooth_dual_scene_density_empirical_L2_coordinate_scaling_exact_capped_simplex_projection_GPU_float64_matrix_free_cross_round_warm_start",
            "master_solver": str(args.master_solver),
            "master_native_termination": "solver_default_numerical_status_on_current_final_active_master_no_user_epsilon_KKT_certificate_gap_epoch_or_wall_clock_gate",
            "early_separation_schedule": "JAXopt_native_maxiter_work_boundary_exact_full_K_argmax_scan_then_same_warm_master_resume",
            "early_separation_iterate_role": "valid_original_finite_master_cut_discovery_only_never_final_acceptance",
            "fixed_epoch_or_outer_step_limit": None,
            "approximate_relative_improvement_reset": (
                ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT
            ),
            "approximate_patience_blocks": (
                ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS
            ),
            "approximate_eligible_block": (
                "every_native_block_best_feasible_full_objective;_fallback_and_recovery_are_diagnostics_only"
            ),
            "approximate_diagnostics_only": [
                "raw_error",
                "scaled_error",
                "weights_movement",
                "top1_identity_movement",
                "maximum_minimum_mix_rho",
            ],
            "rounds": len(history),
            "cuts_added_per_round": [
                int(row["new_candidate_cuts"]) for row in history
            ],
            "final_zero_new_cut_pass": bool(
                history[-1]["best_checkpoint_zero_unseen_legal_cuts"]
                if history[-1]["approximate_terminal_completion"]
                else history[-1]["zero_new_cut_pass"]
            ),
            "best_checkpoint_zero_unseen_legal_cuts": history[-1][
                "best_checkpoint_zero_unseen_legal_cuts"
            ],
            "approximate_terminal_completion": bool(
                history[-1]["approximate_terminal_completion"]
            ),
            "completion_claim": str(history[-1]["completion_claim"]),
            "final_native_master_complete": bool(
                history[-1]["master_native_complete"]
            ),
            "terminal_completion": bool(history[-1]["terminal_completion"]),
            "final_simplex_error": float(
                history[-1]["simplex_error"]
            ),
            "final_minimum_weight": float(
                history[-1]["minimum_weight"]
            ),
        },
        "best_primal_feasible_checkpoint": {
            "path": str(best_checkpoint),
            **latest_checkpoint_metadata,
        },
        "patterns": pattern_rows,
        "artifacts": [
            "atom_scales.json",
            "bt_initialization.json",
            "optimization_history.json",
            "scene_conditioned_parameters.npz",
        ],
    }
    _write_json(output_dir / "result.json", result)
    progress.update(
        "complete",
        processed=int(args.expected_scenes),
        denominator=int(args.expected_scenes),
        complete=True,
        pattern_count=len(patterns),
        completed_benders_rounds=len(history),
        cuts_added_per_round=[int(row["new_candidate_cuts"]) for row in history],
        final_native_master_complete=bool(history[-1]["master_native_complete"]),
        final_zero_new_cut_pass=bool(
            history[-1]["best_checkpoint_zero_unseen_legal_cuts"]
            if history[-1]["approximate_terminal_completion"]
            else history[-1]["zero_new_cut_pass"]
        ),
        approximate_terminal_completion=bool(
            history[-1]["approximate_terminal_completion"]
        ),
        completion_claim=str(history[-1]["completion_claim"]),
        terminal_completion=bool(history[-1]["terminal_completion"]),
        final_simplex_error=float(history[-1]["simplex_error"]),
        final_minimum_weight=float(history[-1]["minimum_weight"]),
        best_primal_feasible_checkpoint=str(best_checkpoint),
        result=str(output_dir / "result.json"),
        eta="complete",
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--complete-pool-jsonl", type=Path, action="append", required=True
    )
    parser.add_argument("--embedding-npz", type=Path, action="append", required=True)
    parser.add_argument("--atom-scales-json", type=Path)
    parser.add_argument(
        "--preference-target-npz",
        type=Path,
        help="fixed train-only demonstration-calibrated point preference sets",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-scenes", type=int, default=50_000)
    parser.add_argument("--alpha", type=float, default=V26_CVAR_ALPHA)
    parser.add_argument("--lambda-theta", type=float, default=1.0)
    parser.add_argument("--solver", type=str, default="CLARABEL")
    parser.add_argument(
        "--master-solver", type=str, default="JAXOPT-PROJECTED-GRADIENT"
    )
    parser.add_argument("--reuse-bt-json", type=Path)
    parser.add_argument(
        "--resume-theta-checkpoint", type=Path, action="append", default=[]
    )
    parser.add_argument("--benders-device", type=str, default="auto")
    parser.add_argument(
        "--sequential-camp",
        action="store_true",
        help="load the fixed 21-atom continuity/trackability bank and extended context embedding",
    )
    parser.add_argument(
        "--structured-transition-ranking",
        action="store_true",
        help="use the 16-atom argmin-aligned structured loss with exact full-K separation",
    )
    parser.add_argument(
        "--pool-delta-ranking",
        action="store_true",
        help="use fixed pool-relative teacher rows and candidate-regret offsets",
    )
    parser.add_argument(
        "--pool-delta-slack-rescaling",
        action="store_true",
        help="use fixed unit-margin-one Pool-Delta slack rescaling: Delta*(1+s_t-s_k)",
    )
    parser.add_argument(
        "--grouped-scene-cvar",
        action="store_true",
        help="average round0/round1 record losses within each anchor before the 50k-scene CVaR",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = run(args)
    except BaseException as exc:
        progress_path = args.output_dir.resolve() / "progress.json"
        if progress_path.exists():
            failure = json.loads(progress_path.read_text(encoding="utf-8"))
            failure.update(
                {
                    "phase": "failed",
                    "complete": False,
                    "failure_type": type(exc).__name__,
                    "failure_message": str(exc),
                    "failure_observed_unix": time.time(),
                }
            )
            temporary = progress_path.with_suffix(progress_path.suffix + ".partial")
            temporary.write_text(
                json.dumps(failure, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, progress_path)
        raise
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
