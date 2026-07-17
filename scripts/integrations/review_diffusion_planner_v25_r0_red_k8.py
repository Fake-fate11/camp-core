#!/usr/bin/env python3
"""Independently review the bounded V25 R0 3x64 red K8 preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    canonical_json_sha256,
    validate_causal_signal_atom_input,
    validate_no_signal_chain,
    validate_runtime_no_signal_receipt,
    validate_runtime_signal_receipt,
    validate_signal_chain,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _load_json,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_r01_21red_1nosignal_sequential_k8_review_v5"
SOURCE_SCHEMA_VERSION = "camp_dp_v25_r01_21red_1nosignal_sequential_k8_preflight_v5"


def _strict_json_bool_array(
    value: Any, shape: tuple[int, ...], *, label: str
) -> np.ndarray:
    """Parse a JSON boolean tensor without accepting numeric/string coercion."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list")

    def flatten(node: Any, depth: int) -> list[bool]:
        if depth == len(shape):
            if type(node) is not bool:
                raise ValueError(f"{label} elements must be native booleans")
            return [node]
        if not isinstance(node, list) or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        result: list[bool] = []
        for child in node:
            result.extend(flatten(child, depth + 1))
        return result

    return np.asarray(flatten(value, 0), dtype=np.bool_).reshape(shape)


def _strict_json_numeric_array(
    value: Any,
    shape: tuple[int, ...],
    *,
    label: str,
    dtype: np.dtype[Any] = np.dtype(np.float64),
) -> np.ndarray:
    """Parse a finite numeric JSON tensor without bool/string/ragged coercion."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list")

    def flatten(node: Any, depth: int) -> list[float]:
        if depth == len(shape):
            if type(node) not in (int, float) or not np.isfinite(float(node)):
                raise ValueError(f"{label} elements must be finite native numbers")
            return [float(node)]
        if not isinstance(node, list) or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        result: list[float] = []
        for child in node:
            result.extend(flatten(child, depth + 1))
        return result

    return np.asarray(flatten(value, 0), dtype=dtype).reshape(shape)


def _independent_red_stopping_oracle(
    candidates: np.ndarray,
    causal_signal_atom_input: Mapping[str, Any],
    dt_s: float,
) -> np.ndarray:
    """Local scalar oracle for the frozen red stopping-envelope formula."""
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.shape != (8, 80, 4) or not np.isfinite(trajectories).all():
        raise ValueError("red stopping oracle requires finite [8,80,4]")
    if not causal_signal_atom_input["applicable"]:
        return np.zeros(8, dtype=np.float64)
    stop = _strict_json_numeric_array(
        causal_signal_atom_input.get("stop_line_geometry_ego_m"),
        (2, 2),
        label="stop_line_geometry_ego_m",
    )
    tangent = _strict_json_numeric_array(
        causal_signal_atom_input.get("route_tangent_ego"),
        (2,),
        label="route_tangent_ego",
    )
    tangent = tangent / np.linalg.norm(tangent)
    red_xy = stop.mean(axis=0)[None, :]
    red_direction = tangent[None, :]
    costs = np.zeros(8, dtype=np.float64)
    for candidate_index, trajectory in enumerate(trajectories):
        xy = trajectory[:, :2]
        speeds = np.linalg.norm(np.diff(xy, axis=0), axis=1) / float(dt_s)
        headings = np.arctan2(trajectory[:, 3], trajectory[:, 2])[1:]
        heading_vectors = np.column_stack((np.cos(headings), np.sin(headings)))
        relative = red_xy[None, :, :] - xy[1:, None, :]
        distances = np.linalg.norm(relative, axis=2)
        aligned = heading_vectors @ red_direction.T > 0.5
        ahead = np.einsum("trd,td->tr", relative, heading_vectors) > 0.0
        eligible = aligned & ahead & (distances <= 40.0)
        nearest = np.min(np.where(eligible, distances, np.inf), axis=1)
        active = np.isfinite(nearest)
        if not active.any():
            continue
        safe_speed = np.sqrt(4.0 * np.maximum(nearest[active] - 3.0, 0.0))
        excess = np.maximum(speeds[active] - safe_speed, 0.0)
        proximity = np.maximum(1.0 - nearest[active] / 40.0, 0.0)
        costs[candidate_index] = float(dt_s) * float(
            np.sum(proximity * excess**2)
        )
    if not np.isfinite(costs).all() or np.any(costs < 0.0):
        raise ValueError("red stopping oracle violated finite/nonnegative contract")
    return costs


def _independently_validate_tick_atoms(
    row: Mapping[str, Any],
    *,
    chain: Mapping[str, Any],
    signal_receipt: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = _strict_json_numeric_array(
        row.get("raw_atom_matrix"), (8, 14), label="raw_atom_matrix"
    )
    source_valid = _strict_json_bool_array(
        row.get("source_valid_mask"), (8,), label="source_valid_mask"
    )
    physical = _strict_json_bool_array(
        row.get("physical_feasible_mask"),
        (8,),
        label="physical_feasible_mask",
    )
    atom_source_valid = _strict_json_bool_array(
        row.get("atom_source_valid_mask"),
        (8, 14),
        label="atom_source_valid_mask",
    )
    atom_applicable = _strict_json_bool_array(
        row.get("atom_applicable_mask"),
        (8, 14),
        label="atom_applicable_mask",
    )
    candidates = validate_fixed_k8_candidate_tensor(
        _strict_json_numeric_array(
            row.get("candidate_tensor"),
            (8, 80, 4),
            label="candidate_tensor",
            dtype=np.dtype(np.float32),
        )
    )
    if (
        raw.shape != (8, 14)
        or not np.isfinite(raw).all()
        or np.any(raw < 0.0)
        or not source_valid.any()
        or np.any(physical & ~source_valid)
        or np.any(atom_applicable & ~atom_source_valid)
        or not np.array_equal(source_valid, atom_source_valid.all(axis=1))
    ):
        raise ValueError("R0 fingerprint/mask/raw atom contract drifted")
    causal_signal = row.get("causal_signal_atom_input")
    validated_signal = validate_causal_signal_atom_input(
        causal_signal, chain, signal_receipt
    )
    signal_applicable = validated_signal["current_phase"] == "red"
    signal_columns = np.asarray([10, 12])
    if (
        row.get("current_phase") != validated_signal["current_phase"]
        or not np.array_equal(
            atom_applicable[:, signal_columns],
            np.full((8, 2), signal_applicable, dtype=np.bool_),
        )
        or (
            not signal_applicable
            and not np.array_equal(raw[:, signal_columns], np.zeros((8, 2)))
        )
        or type(row.get("all_k_high_risk")) is not bool
        or row.get("all_k_high_risk") is not bool(
            source_valid.all() and not physical.any()
        )
    ):
        raise ValueError("R0 signal applicability or all-K evidence drifted")
    dt_s = row.get("dt_s")
    if isinstance(dt_s, bool) or not isinstance(dt_s, (int, float)) or float(dt_s) != 0.1:
        raise ValueError("R0 atom timestep drifted")
    expected_red_stopping = _independent_red_stopping_oracle(
        candidates, validated_signal, float(dt_s)
    )
    if not np.allclose(
        raw[:, 12], expected_red_stopping, rtol=0.0, atol=1e-12
    ):
        raise ValueError("R0 red-stopping atom does not match certified causal input")
    return (
        raw,
        source_valid,
        physical,
        atom_source_valid,
        atom_applicable,
        candidates,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-artifact", type=Path, required=True)
    parser.add_argument("--preflight-root-sha256", required=True)
    parser.add_argument("--r0-source-artifact", type=Path, required=True)
    parser.add_argument("--r0-source-root-sha256", required=True)
    parser.add_argument("--r0-review-artifact", type=Path, required=True)
    parser.add_argument("--r0-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    preflight_seal = verify_complete_seal(
        args.preflight_artifact,
        args.preflight_root_sha256,
        label="V25 R0 red K8 preflight",
    )
    source_seal = verify_complete_seal(
        args.r0_source_artifact,
        args.r0_source_root_sha256,
        label="V25 R0 source",
    )
    source_review_seal = verify_complete_seal(
        args.r0_review_artifact,
        args.r0_review_root_sha256,
        label="V25 R0 source review",
    )
    for artifact in (
        args.preflight_artifact,
        args.r0_source_artifact,
        args.r0_review_artifact,
    ):
        if (artifact / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError("R0 input run.exit is not zero")
    report = _load_json(args.preflight_artifact / "report.json")
    probe_payload = _load_json(args.preflight_artifact / "probe_results.json")
    selector = _load_json(args.preflight_artifact / "selector_contract.json")
    chains = _load_json(args.r0_source_artifact / "red_signal_chains.json").get(
        "chains"
    )
    no_signal_chains = _load_json(
        args.r0_source_artifact / "no_signal_chains.json"
    ).get("chains")
    source_review = _load_json(args.r0_review_artifact / "report.json")
    results = probe_payload.get("results")
    if (
        report.get("schema_version") != SOURCE_SCHEMA_VERSION
        or report.get("status")
        != "passed_bounded_21red_1nosignal_x64_full_r_closed"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("r0_source_root_sha256") != source_seal["root_sha256"]
        or report.get("r0_review_root_sha256")
        != source_review_seal["root_sha256"]
        or source_review.get("reviewed_root_sha256") != source_seal["root_sha256"]
        or report.get("selector_contract_sha256")
        != canonical_json_sha256(selector)
        or report.get("full_r_authorized") is not False
        or report.get("fresh_b2_opened") is not False
        or not isinstance(results, list)
        or len(results) != 22
        or not isinstance(chains, list)
        or len(chains) != 21
        or not isinstance(no_signal_chains, list)
        or len(no_signal_chains) != 1
    ):
        raise ValueError("R0 red K8 preflight authority drifted")
    scales = _strict_json_numeric_array(
        selector.get("scales"), (14,), label="selector scales"
    )
    weights = _strict_json_numeric_array(
        selector.get("weights"), (14,), label="selector weights"
    )
    if (
        scales.shape != (14,)
        or weights.shape != (14,)
        or not np.isfinite(scales).all()
        or not np.isfinite(weights).all()
        or np.any(scales <= 0.0)
        or np.any(weights < 0.0)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12)
        or selector.get("eligibility") != "source_valid"
    ):
        raise ValueError("R0 selector contract is invalid")
    chain_by_id = {str(chain["scenario_id"]): validate_signal_chain(chain) for chain in chains}
    chain_by_id.update(
        {
            str(chain["scenario_id"]): validate_no_signal_chain(chain)
            for chain in no_signal_chains
        }
    )
    reviewed = []
    for result in results:
        scenario_id = str(result.get("scenario_id"))
        chain = chain_by_id.get(scenario_id)
        rows = result.get("tick_fingerprints")
        if (
            chain is None
            or result.get("source_chain_sha256") != chain["source_chain_sha256"]
            or result.get("semantic_clone_sha256") != chain["semantic_clone_sha256"]
            or not isinstance(rows, list)
            or len(rows) != CORPUS_STEPS
            or result.get("tick_fingerprint_root_sha256")
            != canonical_json_sha256(rows)
        ):
            raise ValueError("R0 result/source-chain or 64-tick denominator drifted")
        selected = []
        all_k_high_risk = 0
        for tick_index, row in enumerate(rows):
            payload = {
                key: value for key, value in row.items() if key != "fingerprint_sha256"
            }
            signal_receipt = row.get("runtime_signal_receipt")
            if result.get("family") == "red_light_phase_timing":
                validate_runtime_signal_receipt(signal_receipt, chain)
            else:
                validate_runtime_no_signal_receipt(signal_receipt, chain)
            (
                raw,
                source_valid,
                physical,
                atom_source_valid,
                atom_applicable,
                candidates,
            ) = _independently_validate_tick_atoms(
                row, chain=chain, signal_receipt=signal_receipt
            )
            default = _strict_json_numeric_array(
                row.get("default_output"),
                (80, 4),
                label="default_output",
                dtype=np.dtype(np.float32),
            )
            if (
                row.get("tick_index") != tick_index
                or row.get("fingerprint_sha256") != canonical_json_sha256(payload)
                or default.shape != candidates[0].shape
            ):
                raise ValueError("R0 fingerprint/mask/raw atom contract drifted")
            candidate_rows = [
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
                for value in candidates
            ]
            candidate_tensor_sha = hashlib.sha256(
                np.ascontiguousarray(candidates).tobytes()
            ).hexdigest()
            default_sha = hashlib.sha256(
                np.ascontiguousarray(default).tobytes()
            ).hexdigest()
            normalized = np.clip(raw / scales.reshape(1, 14), 0.0, 10.0)
            scores = normalized @ weights
            expected = int(np.argmin(np.where(source_valid, scores, np.inf)))
            causal_signal = row.get("causal_signal_atom_input")
            context = row.get("complete_context")
            if (
                row.get("selected_index") != expected
                or not np.array_equal(
                    _strict_json_numeric_array(
                        row.get("production_scores"),
                        (8,),
                        label="production_scores",
                    ),
                    scores,
                )
                or row.get("candidate0_sha256") != row.get("default_output_sha256")
                or row.get("candidate0_sha256")
                != row.get("candidate_row_sha256", [None])[0]
                or row.get("candidate_row_sha256") != candidate_rows
                or row.get("candidate_tensor_sha256") != candidate_tensor_sha
                or row.get("default_output_sha256") != default_sha
                or not np.array_equal(default, candidates[0])
                or row.get("selected_trajectory_sha256")
                != candidate_rows[expected]
                or row.get("runtime_signal_receipt_sha256")
                != canonical_json_sha256(signal_receipt)
                or row.get("source_chain_sha256") != chain["source_chain_sha256"]
                or row.get("semantic_clone_sha256") != chain["semantic_clone_sha256"]
                or row.get("causal_signal_atom_input_sha256")
                != canonical_json_sha256(causal_signal)
                or row.get("context_sha256") != canonical_json_sha256(context)
            ):
                raise ValueError("R0 independent score/index/signal binding mismatch")
            selected.append(expected)
            all_k_high_risk += int(bool(row.get("all_k_high_risk")))
        if result.get("selected_sequence_sha256") != canonical_json_sha256(selected):
            raise ValueError("R0 selected sequence hash mismatch")
        reviewed.append(
            {
                "scenario_id": scenario_id,
                "tier": result["tier"],
                "tick_count": len(rows),
                "all_k_high_risk_tick_count": all_k_high_risk,
                "selected_sequence_sha256": result["selected_sequence_sha256"],
                "fingerprint_root_sha256": result["tick_fingerprint_root_sha256"],
            }
        )
    if (
        sum(result.get("family") == "red_light_phase_timing" for result in results)
        != 21
        or sum(result.get("family") != "red_light_phase_timing" for result in results)
        != 1
    ):
        raise ValueError("R0.1 review denominator is not 21 red plus one non-signal")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_21red_1nosignal_x64_review_full_r_closed",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(args.preflight_artifact),
        "reviewed_root_sha256": preflight_seal["root_sha256"],
        "r0_source_root_sha256": source_seal["root_sha256"],
        "r0_source_review_root_sha256": source_review_seal["root_sha256"],
        "probe_count": len(reviewed),
        "probe_tick_count": sum(row["tick_count"] for row in reviewed),
        "probes": reviewed,
        "independent_scalar_clip_affine_argmin": True,
        "runtime_signal_receipts_independently_bound": True,
        "actual_k8_default_context_hashes_independently_recomputed": True,
        "candidate0_operational_default_alias": True,
        "full_r_authorized": False,
        "full_r_started": False,
        "monitor_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 R0 red K8 review")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "full_r_started": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed R0 red K8 review")
        raise


if __name__ == "__main__":
    main()
