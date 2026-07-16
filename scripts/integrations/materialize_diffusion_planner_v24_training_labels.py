#!/usr/bin/env python3
"""Materialize v24 train-only causal labels from the sealed native corpus."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (  # noqa: E402
    _validate_snapshot,
)
from scripts.integrations.preflight_diffusion_planner_v24_convex_training import (  # noqa: E402
    EXPECTED_ATOM_CONTRACT_SHA256,
    EXPECTED_ROUTES,
    EXPECTED_ROUTE_SEEDS,
    EXPECTED_SEEDS,
    EXPECTED_SEVERITY,
    EXPECTED_SNAPSHOTS,
    FIXED_DP_HEAD,
    MINIMUM_FREE_BYTES,
    SOURCE_NAMES,
    _canonical_json_bytes,
    _file_sha256,
    _is_sha256,
    _lock_is_free,
    _read_jsonl,
    _require_clean_repo,
    validate_plan_config,
    verify_complete_seal,
)


PREFLIGHT_SOURCE_HEAD = "bfc0a52307bf7d9184a5f4596b951058c02ba67c"
PREFLIGHT_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_training_static_preflight_bfc0a523_20260716T195856CST"
)
PREFLIGHT_ROOT_SHA256 = (
    "43f26263ff24cad5966cb3a740af6d3307490ab1bd3e07d03284589bee0d28f5"
)
CONFIG_RELATIVE = Path(
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json"
)
LABEL_LOCK = Path("/root/autodl-tmp/.camp_dp_v24_training_label_materialization.lock")
LABEL_SCHEMA = "camp_dp_v24_train_causal_label_columns_v1"
MANIFEST_SCHEMA = "camp_dp_v24_train_causal_label_manifest_v1"
PROVENANCE_FIELDS = frozenset(
    {
        "snapshot_sha256",
        "route_identity_sha256",
        "seed",
        "phase",
        "source_relative_path",
        "tick_index",
    }
)
OUTPUT_FILES = (
    "snapshot_sha256.txt",
    "snapshot_provenance.jsonl",
    "candidate_cost.f64le",
    "oracle_index.u8",
    "source_valid_mask.u8",
    "physical_feasible_mask.u8",
    "all_k_high_risk.u8",
)
PRODUCER_PROVENANCE_FILES = (
    "scripts/integrations/materialize_diffusion_planner_v24_training_labels.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/freeze_diffusion_planner_v24_atom_availability.py",
)
PREFLIGHT_STABLE_PROVENANCE_FILES = PRODUCER_PROVENANCE_FILES[1:]


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_clean_execution_receipt(root: Path) -> None:
    if (
        (Path(root) / "run.exit").read_text(encoding="ascii") != "0\n"
        or (Path(root) / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("source artifact execution receipt is not clean")


def _git_blob_bytes(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def tracked_source_provenance(
    *, repo: Path, current_head: str
) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for relative in PRODUCER_PROVENANCE_FILES:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        live = (Path(repo) / relative).read_bytes()
        current = _git_blob_bytes(Path(repo), current_head, relative)
        blob = subprocess.run(
            ["git", "rev-parse", f"{current_head}:{relative}"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if (
            live != current
            or len(blob) != 40
            or set(blob) - frozenset("0123456789abcdef")
        ):
            raise ValueError(f"label source is not tracked by current HEAD: {relative}")
        stable = relative in PREFLIGHT_STABLE_PROVENANCE_FILES
        if stable and live != _git_blob_bytes(
            Path(repo), PREFLIGHT_SOURCE_HEAD, relative
        ):
            raise ValueError(f"label validator changed after static preflight: {relative}")
        receipts[relative] = {
            "git_blob": blob,
            "sha256": hashlib.sha256(live).hexdigest(),
            "matches_current_head": True,
            "matches_preflight_head": stable,
        }
    return receipts


def _validate_preflight(
    *,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (
        Path(preflight_root) != PREFLIGHT_ARTIFACT
        or expected_preflight_root_sha256 != PREFLIGHT_ROOT_SHA256
    ):
        raise ValueError("v24 label source preflight path or root drift")
    verify_complete_seal(preflight_root, expected_preflight_root_sha256)
    _require_clean_execution_receipt(preflight_root)
    plan = _read_json(Path(preflight_root) / "training_plan_preflight.json")
    routes = _read_jsonl(Path(preflight_root) / "learning_curve_routes.jsonl")
    route_bytes = (Path(preflight_root) / "learning_curve_routes.jsonl").read_bytes()
    decision = plan.get("decision")
    corpus = plan.get("corpus_receipt")
    levels = plan.get("learning_curve_levels")
    if (
        plan.get("schema") != "camp_dp_v24_convex_training_static_preflight_v1"
        or plan.get("status") != "passed"
        or plan.get("camp_head") != PREFLIGHT_SOURCE_HEAD
        or plan.get("fixed_dp_head") != FIXED_DP_HEAD
        or plan.get("route_plan_row_count") != EXPECTED_ROUTES
        or plan.get("route_plan_sha256") != hashlib.sha256(route_bytes).hexdigest()
        or len(routes) != EXPECTED_ROUTES
        or not isinstance(corpus, Mapping)
        or corpus.get("route_count") != EXPECTED_ROUTES
        or corpus.get("retained_route_seed_count") != EXPECTED_ROUTE_SEEDS
        or corpus.get("complete_route_seed_count") != 1054
        or corpus.get("failed_route_seed_count") != 821
        or corpus.get("snapshot_count") != EXPECTED_SNAPSHOTS
        or corpus.get("candidate_count") != EXPECTED_SNAPSHOTS * 8
        or not isinstance(levels, list)
        or [level.get("route_count") for level in levels] != [94, 188, 281, 375]
        or [level.get("percent") for level in levels] != [25, 50, 75, 100]
        or levels[-1].get("snapshot_count") != EXPECTED_SNAPSHOTS
        or levels[-1].get("primary_model") is not True
        or plan.get("labels_materialized") is not False
        or plan.get("training_executed") is not False
        or plan.get("outcome_fields_consumed") != []
        or plan.get("calibration_accessed") is not False
        or plan.get("holdout_opened") is not False
        or plan.get("claim_authorized") is not False
        or not isinstance(decision, Mapping)
        or decision.get("label_materialization_tdd_execution_authorized") is not True
        or decision.get("label_independent_review_authorized") is not True
        or decision.get("training_execution_authorized") is not False
        or decision.get("outcome_access_authorized") is not False
        or decision.get("calibration_access_authorized") is not False
        or decision.get("holdout_access_authorized") is not False
        or decision.get("claim_authorized") is not False
        or plan.get("next_work_target")
        != "v24_train_only_causal_label_materialization_tdd_execution_review_only"
    ):
        raise ValueError("v24 static preflight does not authorize label materialization")
    seen_routes: set[str] = set()
    prior_rank = 0
    for route in routes:
        route_sha = route.get("route_identity_sha256")
        rank = route.get("route_order_rank")
        seeds = route.get("seeds")
        if (
            not isinstance(route, Mapping)
            or not _is_sha256(route_sha)
            or route_sha in seen_routes
            or type(rank) is not int
            or rank != prior_rank + 1
            or seeds != list(EXPECTED_SEEDS)
            or route.get("retained_route_seed_count") != len(EXPECTED_SEEDS)
            or route.get("complete_route_seed_count")
            + route.get("failed_route_seed_count")
            != len(EXPECTED_SEEDS)
            or not _is_sha256(route.get("route_order_key_sha256"))
            or not _is_sha256(route.get("logical_map_sha256"))
            or not _is_sha256(route.get("corridor_group_sha256"))
        ):
            raise ValueError("learning-curve route provenance is invalid")
        seen_routes.add(route_sha)
        prior_rank = rank
    return plan, routes


def compute_label_batch(
    atoms: np.ndarray,
    source_valid: np.ndarray,
    physical_feasible: np.ndarray,
    *,
    frozen_scales: np.ndarray,
    severity_weights: np.ndarray,
    physical_risk_penalty: float,
    normalized_atom_clip: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute causal labels from explicitly supplied frozen preprocessing."""

    matrix = np.asarray(atoms, dtype=np.float64)
    valid_raw = np.asarray(source_valid)
    physical_raw = np.asarray(physical_feasible)
    scales = np.asarray(frozen_scales, dtype=np.float64).reshape(-1)
    severity = np.asarray(severity_weights, dtype=np.float64).reshape(-1)
    if valid_raw.dtype.kind != "b" or physical_raw.dtype.kind != "b":
        raise ValueError("label masks must contain strict booleans")
    valid = valid_raw.astype(bool, copy=False)
    physical = physical_raw.astype(bool, copy=False)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or valid.shape != matrix.shape[:2]
        or physical.shape != matrix.shape[:2]
        or scales.shape != (14,)
        or severity.shape != (14,)
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or not np.isfinite(severity).all()
        or np.any(severity < 0.0)
        or not valid.any(axis=1).all()
        or not np.isfinite(physical_risk_penalty)
        or physical_risk_penalty < 0.0
        or not np.isfinite(normalized_atom_clip)
        or normalized_atom_clip <= 0.0
    ):
        raise ValueError("v24 causal label inputs or contract are invalid")
    normalized = np.clip(
        matrix / scales.reshape(1, 1, 14),
        0.0,
        float(normalized_atom_clip),
    )
    costs = float(physical_risk_penalty) * (~physical).astype(np.float64)
    for atom_index in range(14):
        costs = costs + normalized[:, :, atom_index] * severity[atom_index]
    if not np.isfinite(costs).all() or np.any(costs < 0.0):
        raise ValueError("v24 causal label costs are invalid")
    oracle = np.argmin(np.where(valid, costs, np.inf), axis=1).astype(np.uint8)
    all_k_high_risk = (valid.all(axis=1) & ~physical.any(axis=1)).astype(np.uint8)
    return costs, oracle, all_k_high_risk


def _little_endian_f64_bytes(values: np.ndarray) -> bytes:
    matrix = np.asarray(values, dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError("nonfinite values cannot be serialized")
    return matrix.astype(np.dtype("<f8"), copy=False).tobytes(order="C")


def _u8_bytes(values: np.ndarray) -> bytes:
    array = np.asarray(values)
    if array.size and (np.any(array < 0) or np.any(array > 255)):
        raise ValueError("uint8 column value is out of range")
    return array.astype(np.uint8, copy=False).tobytes(order="C")


def _validate_config_and_authority(
    *, repo: Path, config_path: Path, current_head: str
) -> tuple[dict[str, Any], dict[str, Path], dict[str, str]]:
    expected_config = (Path(repo) / CONFIG_RELATIVE).resolve()
    if Path(config_path).resolve() != expected_config:
        raise ValueError("label materializer must use the tracked v24 config")
    config_bytes = Path(config_path).read_bytes()
    if config_bytes != _git_blob_bytes(
        Path(repo), current_head, CONFIG_RELATIVE.as_posix()
    ):
        raise ValueError("live v24 config differs from current CAMP HEAD")
    if config_bytes != _git_blob_bytes(
        Path(repo), PREFLIGHT_SOURCE_HEAD, CONFIG_RELATIVE.as_posix()
    ):
        raise ValueError("v24 config changed after static preflight")
    config = json.loads(config_bytes)
    validated = validate_plan_config(config)
    authority = validated["source_authority"]
    roots = {name: Path(authority[name]["artifact"]) for name in SOURCE_NAMES}
    digests = {
        name: authority[name]["artifact_root_sha256"] for name in SOURCE_NAMES
    }
    for name in SOURCE_NAMES:
        verify_complete_seal(roots[name], digests[name])
        _require_clean_execution_receipt(roots[name])
    return validated, roots, digests


def materialize_labels(
    *,
    repo: Path,
    dp_repo: Path,
    config_path: Path,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    expected_camp_head: str,
    output_dir: Path,
    expected_snapshot_count: int = EXPECTED_SNAPSHOTS,
    free_bytes: int | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    available = (
        int(free_bytes)
        if free_bytes is not None
        else int(shutil.disk_usage(output.parent).free)
    )
    if available <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")
    _require_clean_repo(Path(repo), expected_camp_head)
    _require_clean_repo(Path(dp_repo), FIXED_DP_HEAD)
    if not _lock_is_free():
        raise RuntimeError("v24 native corpus lock is held")
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current_head != expected_camp_head:
        raise ValueError("live CAMP HEAD differs from label execution authority")
    source_provenance = tracked_source_provenance(
        repo=Path(repo), current_head=current_head
    )
    plan, route_rows = _validate_preflight(
        preflight_root=preflight_root,
        expected_preflight_root_sha256=expected_preflight_root_sha256,
    )
    validated, roots, digests = _validate_config_and_authority(
        repo=repo,
        config_path=config_path,
        current_head=current_head,
    )
    merged = _read_json(roots["merged_train_corpus"] / "merged_summary.json")
    freeze = _read_json(roots["atom_freeze"] / "atom_freeze.json")
    if (
        merged.get("snapshot_count") != expected_snapshot_count
        or merged.get("retained_route_seed_runs") != EXPECTED_ROUTE_SEEDS
        or merged.get("route_count") != EXPECTED_ROUTES
        or merged.get("seeds") != list(EXPECTED_SEEDS)
        or freeze.get("source_merged_root_sha256")
        != digests["merged_train_corpus"]
        or freeze.get("atom_contract_projection_sha256")
        != EXPECTED_ATOM_CONTRACT_SHA256
        or freeze.get("active_atom_mask") != [True] * 14
        or freeze.get("excluded_atom_names") != []
    ):
        raise ValueError("merged corpus or atom freeze label authority drift")
    frozen_scales = np.asarray(freeze.get("atom_scales"), dtype=np.float64)
    plan_scales = np.asarray(plan["atom_freeze"]["atom_scales"], dtype=np.float64)
    if (
        frozen_scales.shape != (14,)
        or not np.array_equal(frozen_scales, plan_scales)
        or plan["atom_freeze"].get("active_atom_mask") != [True] * 14
        or plan["atom_freeze"].get("scale_or_mask_recomputed") is not False
    ):
        raise ValueError("frozen v24 scales or mask differ from static preflight")
    label_contract = validated["label_contract"]
    if label_contract != plan.get("label_contract"):
        raise ValueError("label contract differs from static preflight")
    severity = np.asarray(label_contract["atom_severity_weights"], dtype=np.float64)
    if not np.array_equal(severity, np.asarray(EXPECTED_SEVERITY)):
        raise ValueError("causal severity policy drift")
    label_contract_sha256 = hashlib.sha256(
        _canonical_json_bytes(label_contract)
    ).hexdigest()
    atom_scales_sha256 = hashlib.sha256(
        _canonical_json_bytes(frozen_scales.tolist())
    ).hexdigest()

    source_specs = merged.get("source_artifacts")
    if not isinstance(source_specs, Mapping):
        raise ValueError("merged source artifacts are missing")
    source_roots: dict[str, Path] = {}
    source_inventories: dict[str, dict[str, str]] = {}
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        spec = source_specs.get(name)
        if not isinstance(spec, Mapping):
            raise ValueError(f"merged source {name} is missing")
        raw_path = spec.get("path")
        root_sha = spec.get("root_sha256")
        pure = PurePosixPath(raw_path) if isinstance(raw_path, str) else None
        if (
            pure is None
            or not pure.is_absolute()
            or pure.parts[:3] != ("/", "root", "autodl-tmp")
            or ".." in pure.parts
            or not _is_sha256(root_sha)
        ):
            raise ValueError("merged source path or root is invalid")
        source_roots[name] = Path(raw_path)
        source_inventories[name] = verify_complete_seal(Path(raw_path), root_sha)
        _require_clean_execution_receipt(Path(raw_path))

    index_path = roots["merged_train_corpus"] / "snapshot_index.jsonl"
    index_bytes = index_path.read_bytes()
    if hashlib.sha256(index_bytes).hexdigest() != merged.get("snapshot_index_sha256"):
        raise ValueError("merged snapshot index SHA256 mismatch")
    index_rows = [json.loads(line) for line in index_bytes.splitlines() if line.strip()]
    if len(index_rows) != expected_snapshot_count:
        raise ValueError("merged snapshot index count mismatch")
    route_set = {str(row["route_identity_sha256"]) for row in route_rows}

    costs = np.empty((expected_snapshot_count, 8), dtype=np.float64)
    oracles = np.empty(expected_snapshot_count, dtype=np.uint8)
    valid_masks = np.empty((expected_snapshot_count, 8), dtype=bool)
    physical_masks = np.empty((expected_snapshot_count, 8), dtype=bool)
    all_k = np.empty(expected_snapshot_count, dtype=np.uint8)
    snapshot_digests: list[str] = []
    provenance_lines: list[bytes] = []
    seen: set[str] = set()
    seen_tick: set[tuple[str, int, int]] = set()
    prior_order: tuple[str, str] | None = None
    started = time.perf_counter()
    for index, row in enumerate(index_rows):
        if not isinstance(row, Mapping) or set(row) != {
            "phase",
            "relative_path",
            "sha256",
        }:
            raise ValueError("snapshot index row schema mismatch")
        phase = row["phase"]
        digest = row["sha256"]
        relative = PurePosixPath(str(row["relative_path"]))
        order = (str(digest), str(phase))
        if (
            phase not in {"pilot", "remaining"}
            or not _is_sha256(digest)
            or relative.as_posix() != f"snapshots/{digest}.json"
            or relative.is_absolute()
            or ".." in relative.parts
            or digest in seen
            or (prior_order is not None and order <= prior_order)
            or source_inventories[str(phase)].get(relative.as_posix()) != digest
        ):
            raise ValueError("snapshot index identity, order, or source seal mismatch")
        source_path = source_roots[str(phase)] / Path(*relative.parts)
        content = source_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("snapshot content address mismatch")
        payload = json.loads(content)
        atom, valid, physical = _validate_snapshot(
            payload, phase=str(phase), expected_sha256=str(digest)
        )
        sidecar = payload["sidecar"]
        route = sidecar["route_identity_sha256"]
        seed = sidecar["seed"]
        tick = sidecar["tick_index"]
        tick_key = (route, seed, tick)
        if route not in route_set or tick_key in seen_tick:
            raise ValueError("snapshot route prefix membership or tick identity failed")
        batch_cost, batch_oracle, batch_all_k = compute_label_batch(
            atom.reshape(1, 8, 14),
            valid.reshape(1, 8),
            physical.reshape(1, 8),
            frozen_scales=frozen_scales,
            severity_weights=severity,
            physical_risk_penalty=float(label_contract["physical_risk_penalty"]),
            normalized_atom_clip=float(label_contract["normalized_atom_clip"]),
        )
        costs[index] = batch_cost[0]
        oracles[index] = batch_oracle[0]
        valid_masks[index] = valid
        physical_masks[index] = physical
        all_k[index] = batch_all_k[0]
        snapshot_digests.append(digest)
        provenance = {
            "snapshot_sha256": digest,
            "route_identity_sha256": route,
            "seed": seed,
            "phase": phase,
            "source_relative_path": relative.as_posix(),
            "tick_index": tick,
        }
        if set(provenance) != PROVENANCE_FIELDS:
            raise AssertionError("internal provenance schema drift")
        provenance_lines.append(_canonical_json_bytes(provenance))
        seen.add(digest)
        seen_tick.add(tick_key)
        prior_order = order
    wall_clock_s = time.perf_counter() - started

    output.mkdir()
    output_payloads = {
        "snapshot_sha256.txt": ("\n".join(snapshot_digests) + "\n").encode("ascii"),
        "snapshot_provenance.jsonl": b"".join(provenance_lines),
        "candidate_cost.f64le": _little_endian_f64_bytes(costs),
        "oracle_index.u8": _u8_bytes(oracles),
        "source_valid_mask.u8": _u8_bytes(valid_masks),
        "physical_feasible_mask.u8": _u8_bytes(physical_masks),
        "all_k_high_risk.u8": _u8_bytes(all_k),
    }
    for name, content in output_payloads.items():
        (output / name).write_bytes(content)
    oracle_histogram = np.bincount(oracles, minlength=8).astype(int).tolist()
    file_receipts = {
        name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        for name, content in output_payloads.items()
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "passed",
        "label_schema": LABEL_SCHEMA,
        "split": "train",
        "camp_head": expected_camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_preflight_artifact": str(preflight_root),
        "source_preflight_root_sha256": expected_preflight_root_sha256,
        "source_merged_root_sha256": digests["merged_train_corpus"],
        "source_merged_review_root_sha256": digests[
            "merged_train_corpus_review"
        ],
        "source_atom_freeze_root_sha256": digests["atom_freeze"],
        "source_atom_freeze_review_root_sha256": digests["atom_freeze_review"],
        "source_provenance": source_provenance,
        "route_plan_sha256": plan["route_plan_sha256"],
        "label_contract": label_contract,
        "label_contract_sha256": label_contract_sha256,
        "floating_point_contract": {
            "input_dtype": "float64",
            "normalized_dtype": "float64",
            "cost_dtype": "little_endian_float64",
            "accumulation": "physical_penalty_then_atoms_0_through_13_left_to_right",
            "fused_multiply_add": False,
            "review_match": "exact_binary_float64",
        },
        "atom_scales": frozen_scales.tolist(),
        "atom_scales_sha256": atom_scales_sha256,
        "active_atom_mask": [True] * 14,
        "scale_or_mask_recomputed": False,
        "columns": {
            "candidate_cost": {"file": "candidate_cost.f64le", "dtype": "<f8", "shape": [expected_snapshot_count, 8]},
            "oracle_index": {"file": "oracle_index.u8", "dtype": "u1", "shape": [expected_snapshot_count]},
            "source_valid_mask": {"file": "source_valid_mask.u8", "dtype": "u1_bool", "shape": [expected_snapshot_count, 8]},
            "physical_feasible_mask": {"file": "physical_feasible_mask.u8", "dtype": "u1_bool", "shape": [expected_snapshot_count, 8]},
            "all_k_high_risk": {"file": "all_k_high_risk.u8", "dtype": "u1_bool", "shape": [expected_snapshot_count]},
        },
        "file_receipts": file_receipts,
        "snapshot_count": expected_snapshot_count,
        "candidate_count": expected_snapshot_count * 8,
        "route_count": EXPECTED_ROUTES,
        "retained_route_seed_count": EXPECTED_ROUTE_SEEDS,
        "complete_route_seed_count": plan["corpus_receipt"][
            "complete_route_seed_count"
        ],
        "failed_route_seed_count": plan["corpus_receipt"][
            "failed_route_seed_count"
        ],
        "failure_reason_counts": plan["corpus_receipt"]["failure_reason_counts"],
        "learning_curve_levels": plan["learning_curve_levels"],
        "train_seeds": list(EXPECTED_SEEDS),
        "source_valid_candidate_count": int(valid_masks.sum()),
        "source_invalid_candidate_count": int(valid_masks.size - valid_masks.sum()),
        "physical_feasible_candidate_count": int(physical_masks.sum()),
        "all_k_high_risk_snapshot_count": int(all_k.sum()),
        "oracle_histogram": oracle_histogram,
        "oracle_candidate0_count": oracle_histogram[0],
        "oracle_non_candidate0_count": expected_snapshot_count - oracle_histogram[0],
        "candidate_cost_minimum": float(np.min(costs)),
        "candidate_cost_maximum": float(np.max(costs)),
        "candidate_cost_mean": float(np.mean(costs)),
        "offline_label_materialization_wall_clock_s": wall_clock_s,
        "source_verified_file_counts": {
            name: len(files) for name, files in source_inventories.items()
        },
        "snapshot_payloads_copied": False,
        "snapshot_payloads_modified": False,
        "candidate_tensors_modified": False,
        "identity_fields_stored_only_in_separate_provenance": True,
        "identity_fields_used_as_label_or_feature": False,
        "actual_closed_loop_outcomes_read": False,
        "future_outcome_fields_read": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "independent_review_authorized": True,
        "training_execution_authorized": False,
        "free_disk_gib": available / (1024**3),
        "minimum_free_disk_gib": 10,
        "next_work_target": (
            "v24_train_only_causal_label_materialization_independent_review_only"
        ),
    }
    (output / "label_manifest.json").write_bytes(_canonical_json_bytes(manifest))
    return manifest


def seal_artifact(root: Path) -> str:
    source = Path(root)
    if source.is_symlink():
        raise ValueError("artifact root symlink is forbidden")
    manifest = source / "SHA256SUMS"
    root_receipt = source / "ROOT_SHA256SUMS"
    files: list[Path] = []
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("artifact symlink is forbidden")
        if not path.is_file() or path in {manifest, root_receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested reserved manifest name is forbidden")
        files.append(path)
    files.sort()
    manifest.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(manifest)
    root_receipt.write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if os.name != "posix":
        raise RuntimeError("v24 label execution requires the isolated AutoDL host")
    import fcntl

    LABEL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    command = " ".join(sys.argv)
    with LABEL_LOCK.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("v24 label materialization lock is held") from exc
        manifest = materialize_labels(
            repo=args.repo,
            dp_repo=args.dp_repo,
            config_path=args.config,
            preflight_root=args.preflight_root,
            expected_preflight_root_sha256=args.expected_preflight_root_sha256,
            expected_camp_head=args.camp_head,
            output_dir=args.output_dir,
        )
        (args.output_dir / "HEADS").write_text(
            f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(command + "\n", encoding="utf-8")
        (args.output_dir / "label_manifest.md").write_text(
            "# V24 Train-Only Causal Label Materialization\n\n"
            f"- status: `{manifest['status']}`\n"
            f"- snapshots / candidates: `{manifest['snapshot_count']} / "
            f"{manifest['candidate_count']}`\n"
            f"- oracle candidate-0 / non-0: `{manifest['oracle_candidate0_count']} / "
            f"{manifest['oracle_non_candidate0_count']}`\n"
            "- training / calibration / holdout: `not executed`\n"
            f"- next: `{manifest['next_work_target']}`\n",
            encoding="utf-8",
        )
        stdout = json.dumps(
            {
                "status": manifest["status"],
                "snapshot_count": manifest["snapshot_count"],
                "oracle_histogram": manifest["oracle_histogram"],
                "training_executed": False,
                "next_work_target": manifest["next_work_target"],
            },
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
        (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root_sha256 = seal_artifact(args.output_dir)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
