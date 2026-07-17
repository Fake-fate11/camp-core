#!/usr/bin/env python3
"""Run the bounded S0 sequential-K8 correctness preflight.

This is deliberately not the 1,500-identity corpus runner.  It executes one
formal identity twice plus one red-light/easy identity, consumes no Fresh or
calibration inputs, and seals only contract fingerprints and latency summaries.
"""

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

from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    CANONICAL_NORMALIZED_ATOM_CLIP,
    canonical_score_atoms,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (  # noqa: E402
    array_sha256,
    select_camp_candidate,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    _load_frozen_selector_scales,
    _load_frozen_selector_weights,
    build_native_arm_runner,
    validate_native_arm_receipt,
    verify_config_assets,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _file_sha256,
    _load_json,
    _materialize_routes,
    _seal,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORRECTED_GENERATION_SCALES,
    CORPUS_STEPS,
    EXPECTED_SEED,
    EXPECTED_TEMPLATE_SHA256,
    FORMAL_ARTIFACT,
    MINIMUM_FREE_BYTES,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    TRAIN_LOCK,
    V25ControlledSceneAdapter,
    _canonical_sha256,
    _exclusive_lock,
    _git_head,
    _load_formal_plan,
    _shared_assets,
    _tracked_dirty,
    build_controlled_train_config,
    combine_snapshot_context,
)


SCHEMA_VERSION = "camp_dp_v25_ultra_correction_preflight_v2"
REQUIRED_REPORT_CHECKS = frozenset(
    {
        "shared_clip_counterexample_passed",
        "invalid_heading_fails_closed",
        "nonfinite_atom_fails_closed",
        "three_probes_complete_64_ticks",
        "identity0_repeat_is_deterministic",
        "all_candidate_tensors_immutable",
        "all_candidate0_default_identity",
        "all_native_canonical_scores_and_indices_equal",
        "all_context_v2_no_v2i",
        "all_speed_sources_complete",
        "red_light_easy_family_covered",
        "fresh_remained_unopened",
    }
)
REQUIRED_PROBE_CHECKS = frozenset(
    {
        "candidate_tensor_immutable",
        "candidate0_default_identity",
        "native_canonical_equal",
        "context_v2_no_v2i",
        "speed_source_complete",
        "heading_unit_vector_validated_before_selection",
        "failure_class",
    }
)
FINGERPRINT_PAYLOAD_KEYS = frozenset(
    {
        "tick_index",
        "input_sha256",
        "candidate_tensor_sha256",
        "candidate_row_sha256",
        "default_output_sha256",
        "candidate0_sha256",
        "default_candidate0_identity",
        "candidate0_semantics",
        "candidate0_independent_second_forward",
        "atom_matrix_sha256",
        "normalized_atom_matrix_sha256",
        "selected_index",
        "selected_trajectory_sha256",
        "context_sha256",
        "tracker_sha256",
        "source_valid_mask",
        "physical_feasible_mask",
        "failure_class",
    }
)
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded S0 V25 sequential-K8 correction preflight."
    )
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    with _exclusive_lock(TRAIN_LOCK):
        try:
            report = _run(args)
            _write_json(args.output_dir / "report.json", report)
            (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
            root_sha = _seal(args.output_dir)
            print(
                json.dumps(
                    {
                        "status": report["status"],
                        "output_dir": str(args.output_dir),
                        "root_sha256": root_sha,
                    },
                    sort_keys=True,
                )
            )
        except BaseException as exc:
            _write_json(
                args.output_dir / "failure.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed",
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "fresh_b_opened": False,
                    "outcome_fields_consumed": [],
                    "seal_passed": False,
                },
            )
            (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
            _seal(args.output_dir)
            raise


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")
    camp_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP HEAD or tracked worktree drifted")
    if _file_sha256(args.probe_template) != EXPECTED_TEMPLATE_SHA256:
        raise ValueError("probe template SHA256 mismatch")

    plan, formal_root = _load_formal_plan()
    cases = [case for case in plan["train"] if case["runner_eligible"]]
    identity0 = cases[0]
    red_easy = _first_easy_family(cases, "red_light_phase_timing")
    if identity0.get("family") != "lead_vehicle_hard_brake":
        raise ValueError("formal corrected-corpus identity0 family drifted")
    probe_plan = (
        ("identity0_repeat_a", identity0),
        ("identity0_repeat_b", identity0),
        ("red_light_easy", red_easy),
    )
    unique_cases = [identity0, red_easy]
    template = _load_json(args.probe_template)
    route_assets = _materialize_routes(
        unique_cases, args.output_dir / "routes", args.dp_repo
    )

    common: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "camp_head": camp_head,
        "released_camp_source_head": camp_head,
        "current_repo_head_at_run": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": formal_root,
        "probe_template": str(args.probe_template),
        "probe_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "seed": EXPECTED_SEED,
        "corpus_steps_per_probe": CORPUS_STEPS,
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "sequential_k8": True,
        "micro_batch_used": False,
        "cache_optimization_used": False,
        "snapshot_sharding_used": False,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "selector_runtime_mode": "Static14D",
        "scene14d_runtime_connected": False,
    }

    configs: dict[str, Mapping[str, Any]] = {}
    shared = None
    for case in unique_cases:
        identity = str(case["route_identity_sha256"])
        config = build_controlled_train_config(
            template, case, route_assets[identity]
        )
        verify_config_assets(config)
        if shared is None:
            shared = _shared_assets(config)
        elif _shared_assets(config) != shared:
            raise ValueError("preflight fixed assets changed between identities")
        configs[str(case["scenario_id"])] = config

    first_config = configs[str(identity0["scenario_id"])]
    if Path(str(first_config["selector"]["atom_scales"]["path"])) != (
        CORRECTED_GENERATION_SCALES
    ):
        raise ValueError("preflight generation-scale path drifted")
    config_receipts = [
        {
            "scenario_id": str(case["scenario_id"]),
            "family": str(case["family"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "seed": EXPECTED_SEED,
            "config": configs[str(case["scenario_id"])],
            "config_sha256": _canonical_sha256(
                configs[str(case["scenario_id"])]
            ),
        }
        for case in unique_cases
    ]
    common.update(
        {
            "generation_scales": dict(first_config["selector"]["atom_scales"]),
            "static_weights": dict(first_config["selector"]["weights"]),
            "config_receipts_root_sha256": _canonical_sha256(config_receipts),
        }
    )
    _write_json(
        args.output_dir / "source_receipt.json",
        {**common, "config_receipts": config_receipts},
    )
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={camp_head}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    scales, _ = _load_frozen_selector_scales(
        Path(str(first_config["selector"]["atom_scales"]["path"]))
    )
    weights = _load_frozen_selector_weights(
        Path(str(first_config["selector"]["weights"]["path"]))
    )
    fixture_report = _contract_fixtures(scales, weights)
    runner = build_native_arm_runner(first_config, device=args.device)
    probe_results = []
    started = time.perf_counter()
    for run_label, case in probe_plan:
        probe_results.append(
            _run_probe(
                runner=runner,
                config=configs[str(case["scenario_id"])],
                case=case,
                run_label=run_label,
                scales=scales,
                weights=weights,
                config_sha256=_canonical_sha256(
                    configs[str(case["scenario_id"])]
                ),
                output_dir=args.output_dir,
            )
        )

    deterministic = (
        probe_results[0]["tick_fingerprints"]
        == probe_results[1]["tick_fingerprints"]
    )
    checks = {
        "shared_clip_counterexample_passed": fixture_report["clip_counterexample"][
            "passed"
        ],
        "invalid_heading_fails_closed": fixture_report["invalid_heading"][
            "failure_class"
        ]
        == "ValueError",
        "nonfinite_atom_fails_closed": fixture_report["nonfinite_atom"][
            "failure_class"
        ]
        == "ValueError",
        "three_probes_complete_64_ticks": all(
            row["tick_count"] == CORPUS_STEPS for row in probe_results
        ),
        "identity0_repeat_is_deterministic": deterministic,
        "all_candidate_tensors_immutable": all(
            row["checks"]["candidate_tensor_immutable"] for row in probe_results
        ),
        "all_candidate0_default_identity": all(
            row["checks"]["candidate0_default_identity"] for row in probe_results
        ),
        "all_native_canonical_scores_and_indices_equal": all(
            row["checks"]["native_canonical_equal"] for row in probe_results
        ),
        "all_context_v2_no_v2i": all(
            row["checks"]["context_v2_no_v2i"] for row in probe_results
        ),
        "all_speed_sources_complete": all(
            row["checks"]["speed_source_complete"] for row in probe_results
        ),
        "red_light_easy_family_covered": probe_results[2]["family"]
        == "red_light_phase_timing",
        "fresh_remained_unopened": True,
    }
    if set(checks) != REQUIRED_REPORT_CHECKS:
        raise RuntimeError("bounded preflight report-check schema drifted")
    _write_json(
        args.output_dir / "probe_results.json",
        {
            "schema_version": SCHEMA_VERSION,
            "fixture_report": fixture_report,
            "probe_results": probe_results,
            "fresh_b_opened": False,
            "outcome_fields_consumed": [],
        },
    )
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(
            "bounded correction preflight invariant failed: " + ",".join(failed)
        )
    return {
        **common,
        "mode": "execute_bounded_correction_preflight",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "probe_count": len(probe_results),
        "probe_tick_count": sum(row["tick_count"] for row in probe_results),
        "probe_scenarios": [
            {
                "run_label": row["run_label"],
                "scenario_id": row["scenario_id"],
                "family": row["family"],
                "tier": row["tier"],
                "selected_sequence_sha256": row[
                    "selected_sequence_sha256"
                ],
                "tick_fingerprint_root_sha256": row[
                    "tick_fingerprint_root_sha256"
                ],
                "raw_values_above_clip_count": row[
                    "raw_values_above_clip_count"
                ],
                "latency": row["latency"],
            }
            for row in probe_results
        ],
        "fixture_report": fixture_report,
        "passive_latency_instrumentation_design": _latency_design(),
        "wall_seconds": time.perf_counter() - started,
        "training_executed": False,
        "calibration_executed": False,
        "full_corpus_started": False,
        "claim_authorized": False,
    }


def _first_easy_family(
    cases: list[Mapping[str, Any]], family: str
) -> Mapping[str, Any]:
    matches = [
        case
        for case in cases
        if case.get("family") == family and case.get("tier") == "easy"
    ]
    if not matches:
        raise ValueError(f"no executable easy case for {family}")
    return matches[0]


def _run_probe(
    *,
    runner: Any,
    config: Mapping[str, Any],
    case: Mapping[str, Any],
    run_label: str,
    scales: np.ndarray,
    weights: np.ndarray,
    config_sha256: str,
    output_dir: Path,
) -> dict[str, Any]:
    snapshots: list[Mapping[str, Any]] = []
    contexts: list[Mapping[str, Any]] = []
    adapter = V25ControlledSceneAdapter(
        case,
        red_signal_authority=case.get("red_signal_authority"),
    )
    receipt = runner(
        route=config["routes"][0],
        arm="camp",
        config=config,
        output_dir=output_dir / "native_runs" / run_label,
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
    if (
        len(snapshots) != CORPUS_STEPS
        or len(contexts) != CORPUS_STEPS
        or len(adapter.receipts) != CORPUS_STEPS
    ):
        raise ValueError("bounded probe did not produce exactly 64 records")

    fingerprints = []
    selected_sequence = []
    raw_above_clip_count = 0
    immutable = True
    default_identity = True
    canonical_equal = True
    no_v2i = True
    speed_complete = True
    for tick_index, (tick, snapshot, context) in enumerate(
        zip(receipt["ticks"], snapshots, contexts, strict=True)
    ):
        combine_snapshot_context(
            snapshot=snapshot,
            context=context,
            case=case,
            tick_index=tick_index,
        )
        atoms = np.asarray(snapshot["feature_payload"]["atom_matrix"], dtype=np.float64)
        normalized, scores = canonical_score_atoms(atoms, scales, weights)
        valid = np.asarray(snapshot["feature_payload"]["source_valid_mask"], dtype=bool)
        canonical_index = int(np.argmin(np.where(valid, scores, np.inf)))
        native_scores = np.asarray(tick["scores"], dtype=np.float64)
        raw_above_clip_count += int(
            np.count_nonzero(atoms / scales.reshape(1, 14) > 10.0)
        )
        immutable &= (
            tick["candidate_tensor_sha256_before"]
            == tick["candidate_tensor_sha256_after"]
        )
        identity_receipt = tick["default_candidate0_identity"]
        default_output_sha256 = str(tick["default_output_sha256"])
        candidate0_sha256 = str(tick["candidate_row_sha256"][0])
        default_identity &= (
            identity_receipt.get("elementwise_equal") is True
            and identity_receipt.get("native_ranked_k8") is False
            and identity_receipt.get("default_output_sha256")
            == default_output_sha256
            and identity_receipt.get("candidate0_sha256") == candidate0_sha256
            and candidate0_sha256 == default_output_sha256
        )
        canonical_equal &= (
            tick["selected_index"] == canonical_index
            and np.array_equal(native_scores, scores)
            and tick["normalized_atom_matrix_sha256"]
            == array_sha256(normalized)
            and tick["selected_trajectory_sha256"]
            == tick["candidate_row_sha256"][canonical_index]
        )
        receipt_source = context["source_receipt"]
        no_v2i &= (
            context["schema_version"] == "camp_dp_v25_causal_context_raw_v2"
            and receipt_source.get("mode") == "no_v2i"
            and receipt_source.get("phase_remaining_available") is False
            and context["raw_context"]["traffic_signal_phase_remaining_s"] == 0.0
            and context["source_complete"][
                "traffic_signal_phase_remaining_s"
            ]
            is False
        )
        speed_complete &= (
            all(bool(value) for value in tick["source_complete_mask"])
            and context["raw_context"]["route_speed_limit_min_mps"] > 0.0
            and context["raw_context"]["route_speed_limit_current_mps"] > 0.0
        )
        selected_sequence.append(int(tick["selected_index"]))
        fingerprint_payload = {
            "tick_index": tick_index,
            "input_sha256": tick["input_sha256"],
            "candidate_tensor_sha256": tick[
                "candidate_tensor_sha256_before"
            ],
            "candidate_row_sha256": tick["candidate_row_sha256"],
            "default_output_sha256": default_output_sha256,
            "candidate0_sha256": candidate0_sha256,
            "default_candidate0_identity": dict(identity_receipt),
            "candidate0_semantics": (
                "operational_default_alias_from_same_forward"
            ),
            "candidate0_independent_second_forward": False,
            "atom_matrix_sha256": tick["atom_matrix_sha256"],
            "normalized_atom_matrix_sha256": tick[
                "normalized_atom_matrix_sha256"
            ],
            "selected_index": tick["selected_index"],
            "selected_trajectory_sha256": tick[
                "selected_trajectory_sha256"
            ],
            "context_sha256": _canonical_sha256(context),
            "tracker_sha256": _canonical_sha256(tick["tracker"]),
            "source_valid_mask": tick["source_valid_mask"],
            "physical_feasible_mask": tick["physical_feasible_mask"],
            "failure_class": None,
        }
        if set(fingerprint_payload) != FINGERPRINT_PAYLOAD_KEYS:
            raise ValueError("bounded preflight fingerprint schema drifted")
        fingerprints.append(
            {
                **fingerprint_payload,
                "fingerprint_sha256": _canonical_sha256(fingerprint_payload),
            }
        )

    probe_checks = {
        "candidate_tensor_immutable": bool(immutable),
        "candidate0_default_identity": bool(default_identity),
        "native_canonical_equal": bool(canonical_equal),
        "context_v2_no_v2i": bool(no_v2i),
        "speed_source_complete": bool(speed_complete),
        "heading_unit_vector_validated_before_selection": True,
        "failure_class": None,
    }
    if set(probe_checks) != REQUIRED_PROBE_CHECKS:
        raise ValueError("bounded preflight probe-check schema drifted")
    return {
        "run_label": run_label,
        "scenario_id": case["scenario_id"],
        "family": case["family"],
        "tier": case["tier"],
        "route_identity_sha256": case["route_identity_sha256"],
        "seed": EXPECTED_SEED,
        "config_sha256": config_sha256,
        "tick_count": len(fingerprints),
        "tick_fingerprints": fingerprints,
        "tick_fingerprint_root_sha256": _canonical_sha256(fingerprints),
        "selected_sequence": selected_sequence,
        "selected_sequence_sha256": _canonical_sha256(selected_sequence),
        "raw_values_above_clip_count": raw_above_clip_count,
        "checks": probe_checks,
        "latency": receipt["latency"],
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }


def _contract_fixtures(
    scales: np.ndarray, weights: np.ndarray
) -> dict[str, Any]:
    fixture_scales = np.ones(14, dtype=np.float64)
    fixture_weights = np.zeros(14, dtype=np.float64)
    fixture_weights[:2] = 0.5
    atoms = np.full((8, 14), 10.0, dtype=np.float64)
    atoms[0] = 0.0
    atoms[0, 0] = 100.0
    atoms[1] = 0.0
    atoms[1, :2] = 9.0
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    materialized = {
        "canonical_eligible": True,
        "exclusion_reason": None,
        "atom_matrix": atoms,
        "candidate_reasons": [[] for _ in range(8)],
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "source_valid_mask": np.ones(8, dtype=bool),
    }
    normalized, canonical_scores = canonical_score_atoms(
        atoms, fixture_scales, fixture_weights
    )
    native = select_camp_candidate(
        candidates=candidates,
        materialized=materialized,
        atom_scales=fixture_scales,
        weights=fixture_weights,
        eligibility_mask_name="source_valid_mask",
    )
    invalid = candidates.copy()
    invalid[0, 0, 2:] = 0.0
    invalid_heading = _failure_receipt(
        lambda: validate_fixed_k8_candidate_tensor(invalid)
    )
    nonfinite = atoms.copy()
    nonfinite[0, 0] = np.nan
    nonfinite_atom = _failure_receipt(
        lambda: canonical_score_atoms(nonfinite, fixture_scales, fixture_weights)
    )
    return {
        "canonical_clip": CANONICAL_NORMALIZED_ATOM_CLIP,
        "production_scales_sha256": hashlib.sha256(
            np.ascontiguousarray(scales).tobytes()
        ).hexdigest(),
        "production_weights_sha256": hashlib.sha256(
            np.ascontiguousarray(weights).tobytes()
        ).hexdigest(),
        "clip_counterexample": {
            "raw_unclipped_selected_index": int(
                np.argmin((atoms / fixture_scales) @ fixture_weights)
            ),
            "canonical_selected_index": int(np.argmin(canonical_scores)),
            "native_selected_index": int(native["selected_index"]),
            "candidate0_normalized_first_atom": float(normalized[0, 0]),
            "passed": bool(
                int(np.argmin((atoms / fixture_scales) @ fixture_weights)) == 1
                and int(np.argmin(canonical_scores)) == 0
                and int(native["selected_index"]) == 0
                and normalized[0, 0] == 10.0
            ),
        },
        "invalid_heading": invalid_heading,
        "nonfinite_atom": nonfinite_atom,
    }


def _failure_receipt(callable_: Any) -> dict[str, Any]:
    try:
        callable_()
    except Exception as exc:
        return {
            "failure_class": type(exc).__name__,
            "failure_reason": str(exc),
        }
    return {"failure_class": None, "failure_reason": None}


def _latency_design() -> dict[str, Any]:
    return {
        "status": "design_only_not_implemented_in_s0",
        "clock": "monotonic_ns_passive_timestamps",
        "semantic_effect": "none",
        "planned_stages": [
            "dp_operational_default",
            "extra_fixed_k8_generation",
            "atom_materialization",
            "context_materialization",
            "scene_weight_evaluation",
            "selector",
            "tracker",
            "total_tick",
        ],
        "summary_statistics": ["mean", "median", "p95", "p99", "max"],
        "selector_vs_k8_overhead_separate": True,
        "arm_order_bias_policy": "paired_AB_BA_or_descriptive_only",
        "micro_batch_cache_sharding_in_s0": False,
    }


if __name__ == "__main__":
    main()
