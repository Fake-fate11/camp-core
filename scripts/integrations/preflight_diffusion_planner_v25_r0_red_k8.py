#!/usr/bin/env python3
"""Run the bounded V25 R0 3x64 sequential-K8 no-V2I red preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
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
    canonical_score_atoms,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    V25ControlledSceneAdapter,
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
    _load_frozen_selector_scales,
    _load_frozen_selector_weights,
    build_native_arm_runner,
    validate_native_arm_receipt,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _load_json,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    MINIMUM_FREE_BYTES,
    TRAIN_LOCK,
    _exclusive_lock,
    _git_head,
    _tracked_dirty,
    combine_snapshot_context,
)


SCHEMA_VERSION = "camp_dp_v25_r01_21red_1nosignal_sequential_k8_preflight_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r0-source-artifact", type=Path, required=True)
    parser.add_argument("--r0-source-root-sha256", required=True)
    parser.add_argument("--r0-review-artifact", type=Path, required=True)
    parser.add_argument("--r0-review-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _run_case(
    *,
    runner: Any,
    config: Mapping[str, Any],
    case: Mapping[str, Any],
    scales: np.ndarray,
    weights: np.ndarray,
    output_dir: Path,
) -> dict[str, Any]:
    is_red = case.get("family") == "red_light_phase_timing"
    chain = (
        validate_signal_chain(case["red_signal_authority"])
        if is_red
        else validate_no_signal_chain(case["no_signal_authority"])
    )
    adapter = V25ControlledSceneAdapter(
        case,
        red_signal_authority=chain if is_red else None,
        no_signal_authority=chain if not is_red else None,
    )
    snapshots: list[Mapping[str, Any]] = []
    contexts: list[Mapping[str, Any]] = []
    receipt = runner(
        route=config["routes"][0],
        arm="camp",
        config=config,
        output_dir=output_dir,
        max_steps=CORPUS_STEPS,
        decision_sink=snapshots.append,
        scene_adapter=adapter,
        v25_context_sink=contexts.append,
    )
    validate_native_arm_receipt(
        receipt,
        "camp",
        expected_ticks=CORPUS_STEPS,
        require_summary=False,
        expected_selection_policy="v22_source_valid",
        expected_safety_schema="safety_cost_native_v22",
    )
    if not (
        len(receipt.get("ticks", []))
        == len(snapshots)
        == len(contexts)
        == len(adapter.receipts)
        == CORPUS_STEPS
    ):
        raise ValueError("R0 bounded red probe is not exactly 64 ticks")
    fingerprints = []
    for tick_index, (tick, snapshot, context, controlled) in enumerate(
        zip(
            receipt["ticks"], snapshots, contexts, adapter.receipts, strict=True
        )
    ):
        combined = combine_snapshot_context(
            snapshot=snapshot,
            context=context,
            case=case,
            tick_index=tick_index,
            controlled_scene_receipt=controlled,
        )
        signal_receipt = controlled.get("signal", {}).get("source_receipt")
        if is_red:
            validate_runtime_signal_receipt(signal_receipt, chain)
        else:
            validate_runtime_no_signal_receipt(signal_receipt, chain)
        atoms = np.asarray(snapshot["feature_payload"]["atom_matrix"], dtype=np.float64)
        source_valid = np.asarray(
            snapshot["feature_payload"]["source_valid_mask"], dtype=bool
        )
        physical = np.asarray(
            snapshot["sidecar"]["physical_feasible_mask"], dtype=bool
        )
        atom_source_valid = np.asarray(
            snapshot["feature_payload"]["atom_source_valid_mask"], dtype=np.bool_
        )
        atom_applicable = np.asarray(
            snapshot["feature_payload"]["atom_applicable_mask"], dtype=np.bool_
        )
        causal_signal = snapshot["sidecar"]["causal_signal_atom_input"]
        validate_causal_signal_atom_input(causal_signal)
        if (
            atoms.shape != (8, 14)
            or source_valid.shape != (8,)
            or physical.shape != (8,)
            or np.any(physical & ~source_valid)
            or not source_valid.any()
            or atom_source_valid.shape != (8, 14)
            or atom_applicable.shape != (8, 14)
            or np.any(atom_applicable & ~atom_source_valid)
        ):
            raise ValueError("R0 bounded red masks/atoms violate source-valid contract")
        normalized, scores = canonical_score_atoms(atoms, scales, weights)
        expected_index = int(np.argmin(np.where(source_valid, scores, np.inf)))
        if (
            tick.get("eligibility_mask_name") != "source_valid_mask"
            or tick.get("selected_index") != expected_index
            or not np.array_equal(np.asarray(tick.get("scores")), scores)
            or tick.get("candidate_tensor_sha256_before")
            != tick.get("candidate_tensor_sha256_after")
            or context.get("source_receipt", {}).get("mode") != "no_v2i"
            or context.get("source_receipt", {}).get("phase_remaining_available")
            is not False
            or context.get("raw_context", {}).get(
                "traffic_signal_phase_remaining_s"
            )
            != 0.0
            or context.get("source_complete", {}).get(
                "traffic_signal_phase_remaining_s"
            )
            is not False
        ):
            raise ValueError("R0 bounded red selection/context contract drifted")
        payload = {
            "tick_index": tick_index,
            "candidate_tensor_sha256": tick["candidate_tensor_sha256_before"],
            "candidate_tensor": snapshot["feature_payload"]["candidate_tensor"],
            "candidate_row_sha256": list(tick["candidate_row_sha256"]),
            "candidate0_sha256": tick["candidate_row_sha256"][0],
            "default_output_sha256": tick["default_output_sha256"],
            "default_output": snapshot["feature_payload"]["default_output"],
            "atom_matrix_sha256": tick["atom_matrix_sha256"],
            "raw_atom_matrix": atoms.tolist(),
            "production_scores": list(tick["scores"]),
            "normalized_atom_matrix_sha256": tick[
                "normalized_atom_matrix_sha256"
            ],
            "independent_normalized_sha256": hashlib.sha256(
                np.ascontiguousarray(normalized).tobytes()
            ).hexdigest(),
            "selected_index": expected_index,
            "selected_trajectory_sha256": tick["selected_trajectory_sha256"],
            "source_valid_mask": source_valid.tolist(),
            "physical_feasible_mask": physical.tolist(),
            "atom_source_valid_mask": atom_source_valid.tolist(),
            "atom_applicable_mask": atom_applicable.tolist(),
            "all_k_high_risk": bool(source_valid.all() and not physical.any()),
            "source_chain_sha256": chain["source_chain_sha256"],
            "semantic_clone_sha256": chain["semantic_clone_sha256"],
            "runtime_signal_receipt": dict(signal_receipt),
            "runtime_signal_receipt_sha256": canonical_json_sha256(signal_receipt),
            "causal_signal_atom_input": causal_signal,
            "causal_signal_atom_input_sha256": canonical_json_sha256(causal_signal),
            "current_phase": signal_receipt["current_phase"],
            "context_sha256": canonical_json_sha256(context),
            "complete_context": context,
            "combined_snapshot_sha256": canonical_json_sha256(combined),
        }
        fingerprints.append(
            {**payload, "fingerprint_sha256": canonical_json_sha256(payload)}
        )
    return {
        "scenario_id": case["scenario_id"],
        "tier": case["tier"],
        "family": case["family"],
        "tick_count": len(fingerprints),
        "source_chain_sha256": chain["source_chain_sha256"],
        "semantic_clone_sha256": chain["semantic_clone_sha256"],
        "tick_fingerprints": fingerprints,
        "tick_fingerprint_root_sha256": canonical_json_sha256(fingerprints),
        "selected_sequence_sha256": canonical_json_sha256(
            [row["selected_index"] for row in fingerprints]
        ),
        "latency": receipt["latency"],
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below 10 GiB")
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP drifted or is dirty")
    source_seal = verify_complete_seal(
        args.r0_source_artifact,
        args.r0_source_root_sha256,
        label="V25 R0 source",
    )
    review_seal = verify_complete_seal(
        args.r0_review_artifact,
        args.r0_review_root_sha256,
        label="V25 R0 source review",
    )
    source_report = _load_json(args.r0_source_artifact / "report.json")
    review_report = _load_json(args.r0_review_artifact / "report.json")
    bounded = _load_json(args.r0_source_artifact / "bounded_red_cases.json")
    config_payload = _load_json(args.r0_source_artifact / "config_receipts.json")
    cases = bounded.get("cases")
    receipts = config_payload.get("receipts")
    if (
        source_report.get("status") != "passed_source_only_full_r_closed"
        or review_report.get("status")
        != "passed_independent_source_review_full_r_closed"
        or review_report.get("reviewed_root_sha256") != source_seal["root_sha256"]
        or source_report.get("full_r_authorized") is not False
        or review_report.get("full_r_authorized") is not False
        or not isinstance(cases, list)
        or not isinstance(receipts, list)
        or len(cases) != 22
        or len(receipts) != 22
        or [case.get("scenario_id") for case in cases]
        != [receipt.get("scenario_id") for receipt in receipts]
    ):
        raise ValueError("R0 bounded execution authority is invalid")
    if (
        sum(case.get("family") == "red_light_phase_timing" for case in cases) != 21
        or sum(case.get("signal", {}).get("phase") == "none" for case in cases) != 1
    ):
        raise ValueError("R0.1 bounded denominator is not 21 red plus one non-signal")
    configs = {str(row["scenario_id"]): row["config"] for row in receipts}
    first = configs[str(cases[0]["scenario_id"])]
    scales, _ = _load_frozen_selector_scales(
        Path(str(first["selector"]["atom_scales"]["path"]))
    )
    weights = _load_frozen_selector_weights(
        Path(str(first["selector"]["weights"]["path"]))
    )
    runner = build_native_arm_runner(first, device=args.device)
    results = []
    started = time.perf_counter()
    for case in cases:
        results.append(
            _run_case(
                runner=runner,
                config=configs[str(case["scenario_id"])],
                case=case,
                scales=scales,
                weights=weights,
                output_dir=args.output_dir
                / "native_runs"
                / str(case["scenario_id"]),
            )
        )
    _write_json(args.output_dir / "probe_results.json", {"results": results})
    selector_contract = {
        "scales": np.asarray(scales, dtype=np.float64).tolist(),
        "weights": np.asarray(weights, dtype=np.float64).tolist(),
        "score_contract": "score_k=clip(a_k/s,0,10)^T w",
        "eligibility": "source_valid",
        "tie_break": "lowest_eligible_candidate_index",
    }
    _write_json(args.output_dir / "selector_contract.json", selector_contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_bounded_21red_1nosignal_x64_full_r_closed",
        "camp_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "r0_source_artifact": str(args.r0_source_artifact),
        "r0_source_root_sha256": source_seal["root_sha256"],
        "r0_review_artifact": str(args.r0_review_artifact),
        "r0_review_root_sha256": review_seal["root_sha256"],
        "probe_count": len(results),
        "probe_tick_count": sum(result["tick_count"] for result in results),
        "tiers": [result["tier"] for result in results],
        "red_identity_count": sum(
            result["family"] == "red_light_phase_timing" for result in results
        ),
        "non_signal_identity_count": sum(
            result["family"] != "red_light_phase_timing" for result in results
        ),
        "probe_fingerprint_roots": [
            result["tick_fingerprint_root_sha256"] for result in results
        ],
        "selector_contract_sha256": canonical_json_sha256(selector_contract),
        "sequential_k8": True,
        "no_v2i": True,
        "source_valid_progress_and_selection": True,
        "full_r_authorized": False,
        "full_r_started": False,
        "monitor_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene14d_runtime_connected": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "wall_seconds": time.perf_counter() - started,
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    with _exclusive_lock(TRAIN_LOCK):
        try:
            report = run(args)
            _write_json(args.output_dir / "report.json", report)
            (args.output_dir / "HEADS").write_text(
                f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
                encoding="ascii",
            )
            (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
            (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
            root = seal_artifact(args.output_dir, label="V25 R0 red K8 preflight")
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
            seal_artifact(args.output_dir, label="V25 failed R0 red K8 preflight")
            raise


if __name__ == "__main__":
    main()
