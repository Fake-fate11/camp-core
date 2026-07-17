from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import json
import os
import socket
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_v24_evidence_claim.py"
)
SPEC = importlib.util.spec_from_file_location("v24_evidence_claim_review", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


CURRENT_HEAD = "c" * 40
AUTHORITY_HEAD = CURRENT_HEAD
SOURCE_REVIEW_HEAD = module.SOURCE_REVIEWER_CAMP_HEAD
EXECUTION_HEAD = module.EXECUTION_SOURCE_HEAD
PREFLIGHT_HEAD = module.PREFLIGHT_CAMP_HEAD
PILOT_REVIEW_HEAD = module.PILOT_REVIEW_CAMP_HEAD
PILOT_EXECUTION_HEAD = module.PILOT_EXECUTION_SOURCE_HEAD
CONFIG_SHA = module.CONFIG_SHA256
EVALUATOR_SHA = module.EVALUATOR_SHA256
SOURCE_REVIEW_CHECK_NAMES = frozenset(
    {
        "all_source_complete_seals_verified",
        "execution_launch_chain_bound",
        "preflight_authorization_reviews_passed",
        "split_and_training_roots_verified",
        "split_census_schedule_exact_join_verified",
        "source_census_arc_length_denominators_verified",
        "frozen_train_coverage_and_learning_curve_risk_disclosed",
        "runtime_selector_matches_training",
        "fixed_request_and_assets_hash_bound",
        "main_schedule_24x5_120",
        "arm_order_hash_rank_balance_60_60",
        "outcome_blind_preregistered_arm_order_control_verified",
        "independent_reset_same_initial_state_and_exogenous_seed_verified",
        "one_family_three_corridors",
        "holdout_state_exact_open_once",
        "live_camp_and_fixed_dp_clean",
        "producer_code_provenance_unchanged",
        "all_pair_arm_tick_receipts_recomputed",
        "t0_cross_arm_identity_only",
        "post_divergence_cross_arm_tensors_not_compared",
        "safety_secondary_latency_recomputed",
        "producer_descriptive_statistics_consistent",
        "raw_byte_evidence_limit_disclosed",
        "latency_descriptive_only",
        "latency_comparative_conclusion_forbidden",
        "map_family_ci_and_unseen_claim_forbidden",
        "disk_floor",
    }
)
SOURCE_ROOT_NAMES = frozenset(
    {
        "execution",
        "launch",
        "preflight",
        "preflight_review",
        "pilot_review",
        "authorization",
        "authorization_review",
        "split",
        "split_review",
        "route_census",
        "route_census_review",
        "training",
        "training_review",
        "runtime_selector",
    }
)
SAFETY_COMPONENT_NAMES = frozenset(
    {
        "collision_any",
        "near_miss_noncollision_rate",
        "offroad_rate",
        "wrong_way_rate",
        "red_light_violation_any",
        "speed_limit_violation_rate",
    }
)
SPEED_SENSITIVITY_NAMES = frozenset(
    {
        "0.0",
        "0.05",
        "0.1",
        "0.2",
        "continuous_maximum_excess_mps_delta",
        "continuous_mean_excess_mps_delta",
        "continuous_excess_duration_s_delta",
        "continuous_magnitude_duration_m_delta",
    }
)
SECONDARY_DIRECTIONS = {
    "dt_s": "descriptive_only",
    "route_progress_m": "higher_is_better",
    "route_length_m": "descriptive_only",
    "route_completion_rate": "higher_is_better",
    "distance_traveled_m": "descriptive_only",
    "stopped_fraction": "descriptive_only",
    "mean_speed_mps": "descriptive_only",
    "max_speed_mps": "descriptive_only",
    "mean_abs_acceleration_mps2": "descriptive_only",
    "max_acceleration_mps2": "descriptive_only",
    "mean_abs_jerk_mps3": "lower_is_better",
    "max_jerk_mps3": "lower_is_better",
    "mean_abs_yaw_rate_radps": "descriptive_only",
    "max_abs_yaw_rate_radps": "descriptive_only",
    "mean_abs_lateral_acceleration_mps2": "lower_is_better",
    "max_abs_lateral_acceleration_mps2": "lower_is_better",
}
LATENCY_STAGE_NAMES = {
    "dp": frozenset({"default", "tracker", "total"}),
    "camp": frozenset(
        {"default", "k8_candidate", "atom", "selector", "tracker", "total"}
    ),
}
EXPECTED_MEAN_DELTA = -0.014322916666666666
EXPECTED_CI95_LOW = -0.06380208333333333
EXPECTED_CI95_HIGH = 0.01953125
REVIEWER_SCRIPT_BYTES = b"synthetic evidence-claim reviewer implementation\n"
REVIEWER_TEST_BYTES = b"synthetic evidence-claim reviewer tests\n"
REVIEWER_SCRIPT_SHA = hashlib.sha256(REVIEWER_SCRIPT_BYTES).hexdigest()
REVIEWER_TEST_SHA = hashlib.sha256(REVIEWER_TEST_BYTES).hexdigest()


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(root).as_posix()}"
        for path in files
    ]
    manifest = ("\n".join(lines) + "\n").encode("utf-8")
    (root / "SHA256SUMS").write_bytes(manifest)
    root_sha256 = hashlib.sha256(manifest).hexdigest()
    (root / "ROOT_SHA256SUMS").write_bytes(
        f"{root_sha256}  SHA256SUMS\n".encode("ascii")
    )
    return root_sha256


def _summary(
    pair_count: int,
    *,
    mean: float = 0.0,
    median: float = 0.0,
    low: float = 0.0,
    high: float = 0.0,
    better: int = 0,
    tie: int | None = None,
    worse: int = 0,
    direction: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "pair_count": pair_count,
        "mean": mean,
        "median": median,
        "ci95_low": low,
        "ci95_high": high,
        "better_tie_worse": {
            "better": better,
            "tie": pair_count - better - worse if tie is None else tie,
            "worse": worse,
        },
    }
    if direction is not None:
        result["direction"] = direction
        result["descriptive_unclassified_count"] = 0
    return result


def _latency_distribution() -> dict[str, object]:
    return {
        "count": 7680,
        "mean": 1.0,
        "median": 1.0,
        "p95": 1.0,
        "p99": 1.0,
        "max": 1.0,
    }


def _metrics() -> dict[str, object]:
    guards = {
        name: name != "independent_review_passed"
        for name in module.EVIDENCE_GUARD_NAMES
    }
    source_gates = {
        "retention_rate": True,
        "paired_complete_rate": True,
        "source_invalid_rate": True,
        "execution_invalid_rate": True,
        "safety_cost_mean_delta_below_zero": True,
        "clustered_ci95_upper_below_zero": False,
        "better_exceeds_worse": True,
        "no_additional_collision_pairs": True,
        "no_additional_offroad_pairs": True,
        "no_additional_red_light_pairs": True,
        "no_additional_wrong_way_pairs": True,
        "evidence_guards": False,
    }
    overall = _summary(
        120,
        mean=EXPECTED_MEAN_DELTA,
        low=EXPECTED_CI95_LOW,
        high=EXPECTED_CI95_HIGH,
        better=4,
        tie=113,
        worse=3,
    )
    return {
        "schema": "camp_dp_v24_holdout_main_independent_statistics_v1",
        "bootstrap_contract": {
            "primary_hierarchy": [
                "corridor_group_sha256",
                "route_identity_sha256",
                "seed",
            ],
            "map_family_cluster_level_authorized": False,
            "resamples": 5000,
            "seed": 24047,
        },
        "coverage": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": 120,
            "source_invalid_pair_count": 0,
            "execution_invalid_pair_count": 0,
            "retention_rate": 1.0,
            "paired_complete_rate": 1.0,
            "source_invalid_rate": 0.0,
            "execution_invalid_rate": 0.0,
        },
        "failure_accounting": {
            "dp_status": {"ok": 120},
            "camp_status": {"ok": 120},
            "failure_class": {"None": 120},
            "failed_pairs_dropped": False,
            "replacement_or_resampling_used": False,
        },
        "safety_cost_delta": overall,
        "strata": {
            "overall": copy.deepcopy(overall),
            "all_k_high_risk": _summary(8, better=2, tie=4, worse=2),
        },
        "components": {
            name: _summary(120) for name in SAFETY_COMPONENT_NAMES
        },
        "speed_sensitivity": {
            name: _summary(120) for name in SPEED_SENSITIVITY_NAMES
        },
        "secondary": {
            name: _summary(
                120,
                direction=None if direction == "lower_is_better" else direction,
            )
            for name, direction in SECONDARY_DIRECTIONS.items()
        },
        "additional_event_pairs": {
            name: 0 for name in module.MAJOR_EVENT_FIELDS
        },
        "candidate_selection": {
            "camp_tick_count": 7680,
            "candidate0_selection_count": 1401,
            "non_candidate0_selection_count": 6279,
            "all_k_high_risk_pair_count": 8,
            "all_k_high_risk_tick_count": 36,
            "camp_selected_index_histogram": {
                "0": 1401,
                "1": 913,
                "2": 894,
                "3": 900,
                "4": 909,
                "5": 824,
                "6": 923,
                "7": 916,
            },
        },
        "latency": {
            arm: {stage: _latency_distribution() for stage in stages}
            for arm, stages in LATENCY_STAGE_NAMES.items()
        },
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
        "evidence_guards": guards,
        "claim_gate_result": {
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "claim_scope": "frozen_held_out_map_family_and_three_corridor_groups_only",
            "map_family_level_ci": False,
            "unseen_map_generalization": False,
            "native_ranked_k8_superiority": False,
            "latency_comparative_conclusion": False,
            "gates": source_gates,
            "failed_gates": [
                "clustered_ci95_upper_below_zero",
                "evidence_guards",
            ],
        },
    }


def _schedule() -> dict[str, object]:
    return {
        "pair_count": 120,
        "unique_pair_count": 120,
        "route_count": 24,
        "seed_count_per_route": 5,
        "seeds": [24201, 24202, 24203, 24204, 24205],
        "map_family_count": 1,
        "corridor_group_count": 3,
        "arm_order_counts": {"dp_camp": 60, "camp_dp": 60},
        "arm_order_domain_separator": "camp-v24-paired-arm-order-v1",
        "deterministic_hash_rank_verified": True,
        "outcome_blind_preregistered_order_control_verified": True,
        "independent_reset_per_arm_verified": True,
        "latency_comparative_conclusion_authorized": False,
    }


def _source_provenance() -> dict[str, object]:
    return {
        "live_camp_head": SOURCE_REVIEW_HEAD,
        "execution_source_head": EXECUTION_HEAD,
        "execution_source_is_ancestor": True,
        "prior_gate_heads_are_execution_source_ancestors": {
            "preflight_camp_head": True,
            "pilot_review_camp_head": True,
            "pilot_execution_source_head": True,
        },
        "live_camp_tracked_clean": True,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": True,
        "producer_blob_sha256": {},
        "config_blob_sha256": CONFIG_SHA,
        "expected_config_sha256": CONFIG_SHA,
        "evaluator_blob_sha256": EVALUATOR_SHA,
        "expected_evaluator_sha256": EVALUATOR_SHA,
    }


def _source_roots() -> dict[str, object]:
    roots = {
        name: {
            "label": name,
            "root": f"/sealed/{name}",
            "root_sha256": _sha(name),
            "file_count": 1,
            "manifest_paths": [f"{name}.json"],
        }
        for name in SOURCE_ROOT_NAMES
    }
    roots["training"]["root_sha256"] = module.EXPECTED_TRAINING_ROOT_SHA256
    roots["training_review"]["root_sha256"] = (
        module.EXPECTED_TRAINING_REVIEW_ROOT_SHA256
    )
    roots["runtime_selector"].update(
        {
            "root_sha256": module.EXPECTED_RUNTIME_SELECTOR_ROOT_SHA256,
            "file_count": len(module.EXPECTED_RUNTIME_SELECTOR_MANIFEST_PATHS),
            "manifest_paths": list(
                module.EXPECTED_RUNTIME_SELECTOR_MANIFEST_PATHS
            ),
        }
    )
    return roots


def _route_source_bindings() -> dict[str, object]:
    logical_map_sha256 = _sha("held-out-logical-map")
    source_map_path = "/sealed/maps/held-out-map.osm"
    source_map_sha256 = _sha("held-out-source-map")
    bindings: dict[str, object] = {}
    for index in range(24):
        source_geometry_sha256 = _sha(f"route-geometry-{index}")
        identity = _canonical_sha(
            {
                "logical_map_sha256": logical_map_sha256,
                "source_geometry_sha256": source_geometry_sha256,
            }
        )
        bindings[identity] = {
            "record_key": f"held-out-route-{index:02d}",
            "identity_sha256": identity,
            "logical_map_sha256": logical_map_sha256,
            "map_family_id": "held-out-map-family",
            "source_map_path": source_map_path,
            "source_map_sha256": source_map_sha256,
            "source_geometry_sha256": source_geometry_sha256,
            "route_serialization_sha256": _sha(f"route-serialization-{index}"),
            "source_arc_length_m": 100.0 + index,
            "source_route_length_m": 100.0 + index,
            "corridor_group_sha256": _sha(f"corridor-{index % 3}"),
            "seeds": [24201, 24202, 24203, 24204, 24205],
        }
    return bindings


def _request_assets(bindings: dict[str, object]) -> dict[str, object]:
    first = next(iter(bindings.values()))
    assert isinstance(first, dict)
    map_path = str(first["source_map_path"])
    map_sha256 = str(first["source_map_sha256"])
    return {
        "fixed_dp_assets": copy.deepcopy(module.EXPECTED_FIXED_DP_ASSETS),
        "route_asset_count": 24,
        "route_asset_sha256": {
            identity: _sha(f"route-asset-{identity}") for identity in bindings
        },
        "map_asset_count": 1,
        "map_asset_sha256": {map_path: map_sha256},
        "same_fixed_dp_request_all_pairs": True,
    }


def _runtime_selector() -> dict[str, object]:
    return {
        "weights_sha256": module.EXPECTED_RUNTIME_WEIGHTS_SHA256,
        "atom_scales_sha256": module.EXPECTED_RUNTIME_ATOM_SCALES_SHA256,
        "weights": list(module.EXPECTED_RUNTIME_WEIGHTS),
        "atom_scales": list(module.EXPECTED_RUNTIME_ATOM_SCALES),
    }


def _source_review_artifact(root: Path) -> tuple[str, dict[str, object]]:
    root.mkdir()
    metrics = _metrics()
    schedule = _schedule()
    provenance = _source_provenance()
    route_source_bindings = _route_source_bindings()
    review = {
        "schema": module.SOURCE_REVIEW_SCHEMA,
        "status": "passed",
        "check_count": 27,
        "failed_count": 0,
        "failed_checks": [],
        "checks": {name: True for name in SOURCE_REVIEW_CHECK_NAMES},
        "source_roots": _source_roots(),
        "schedule": schedule,
        "execution": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": 120,
            "source_invalid_pair_count": 0,
            "execution_failure_pair_count": 0,
            "dp_tick_count": 7680,
            "camp_tick_count": 7680,
            "all_k_high_risk_tick_count": 36,
        },
        "launch": {
            "output_path_file": "OUTPUT_PATH",
            "state_path_file": "STATE_PATH",
            "heads_file": "HEADS.txt",
            "command_file": "COMMAND.txt",
            "stderr_bytes": 0,
        },
        "metrics": copy.deepcopy(metrics),
        "claim_guard_handoff": {
            "independent_review_passed": False,
            "status": "pending_separate_claim_decision_rehash_of_sealed_reviewer_root",
            "reviewer_self_authorization_forbidden": True,
        },
        "evidence_limitations": {
            "raw_candidate_tensor_bytes_present": False,
            "raw_atom_matrix_bytes_present": False,
            "affine_score_receipt_consistency_verified": True,
            "affine_scores_recomputed_from_raw_atoms": False,
            "candidate_hashes_recomputed_from_raw_tensor_bytes": False,
            "candidate_and_atom_hash_scope": "complete_sealed_receipt_consistency_only",
            "raw_byte_proof_claimed": False,
        },
        "holdout_state": {
            "schema": "camp_dp_v24_holdout_once_state_v1",
            "holdout_opened": True,
            "holdout_open_count": 1,
            "rerun_authorized": False,
            "camp_head": EXECUTION_HEAD,
            "authorization_root_sha256": _sha("authorization"),
            "preflight_root_sha256": _sha("preflight"),
            "output_dir": "/sealed/execution",
        },
        "provenance": provenance,
        "runtime_selector": _runtime_selector(),
        "request_assets": _request_assets(route_source_bindings),
        "route_source_bindings": route_source_bindings,
        "frozen_metric_contract": {
            "train_route_seed_source_coverage_disclosure": {
                "retained": 1875,
                "complete": 1054,
                "failed": 821,
                "failure_rate": 821 / 1875,
            },
            "learning_curve_stability": {
                "levels_percent": [25, 50, 75, 100],
                "weights_l1_to_full": [
                    0.3998769535788546,
                    0.18971764213000833,
                    0.20611942009995507,
                    0.0,
                ],
                "effective_support_gt_1e_6": [3, 3, 3, 3],
                "candidate0_selection_rate": [
                    0.20219094175157548,
                    0.2786534178516361,
                    0.25863020176544765,
                    0.270222432001888,
                ],
                "selected_index_histogram_l1_to_full": [
                    0.13606298050062507,
                    0.019765760782601463,
                    0.023184460472880697,
                    0.0,
                ],
                "selected_index_argmax": [0, 0, 0, 0],
                "full_effective_support_indices": [7, 8, 13],
                "full_effective_support_names": [
                    "lane_deviation",
                    "clearance",
                    "dp_prior_jerk_excess_cost",
                ],
                "full_effective_support_weights": [
                    0.4178605234516141,
                    0.5784894895043772,
                    0.0036499870440052018,
                ],
                "distribution_concentration_is_automatic_failure": False,
                "risk_disclosure_required": True,
                "calibration_or_holdout_repair_authorized": False,
            },
            "distribution_concentration_risk_disclosed": True,
            "calibration_or_holdout_repair_authorized": False,
        },
        "camp_head": SOURCE_REVIEW_HEAD,
        "execution_source_head": EXECUTION_HEAD,
        "preflight_camp_head": PREFLIGHT_HEAD,
        "preflight_config_sha256": CONFIG_SHA,
        "pilot_review_camp_head": PILOT_REVIEW_HEAD,
        "pilot_execution_source_head": PILOT_EXECUTION_HEAD,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "source_execution_reexecuted": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
        "holdout_open_count": 1,
        "latency_comparison_authorized": False,
        "map_family_level_ci_authorized": False,
        "unseen_map_generalization_authorized": False,
        "native_ranked_k8_claim_authorized": False,
        "final_claim_authorized": False,
        "next_work_target": (
            "v24_evidence_package_and_preregistered_claim_decision"
        ),
        "free_bytes_after_review": module.MINIMUM_FREE_BYTES + 1,
    }
    _write_json(root / "review_result.json", review)
    _write_json(root / "recomputed_metrics.json", metrics)
    _write_json(root / "schedule_receipt.json", schedule)
    _write_json(root / "provenance.json", provenance)
    (root / "summary.md").write_text("# synthetic source review\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD={SOURCE_REVIEW_HEAD}\n"
        f"EXECUTION_SOURCE_HEAD={EXECUTION_HEAD}\n"
        f"PREFLIGHT_CAMP_HEAD={PREFLIGHT_HEAD}\n"
        f"PILOT_REVIEW_CAMP_HEAD={PILOT_REVIEW_HEAD}\n"
        f"PILOT_EXECUTION_SOURCE_HEAD={PILOT_EXECUTION_HEAD}\n"
        f"FIXED_DP_HEAD={module.FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (root / "COMMAND.txt").write_text("synthetic-source-review\n", encoding="utf-8")
    _write_json(root / "stdout.txt", review)
    (root / "stderr.txt").write_bytes(b"")
    (root / "run.exit").write_bytes(b"0\n")
    return _seal(root), review


def _static_preflight_artifact(root: Path) -> tuple[str, dict[str, object]]:
    root.mkdir()
    result = {
        "schema": module.STATIC_PREFLIGHT_SCHEMA,
        "status": "passed",
        "implementation_source_head": CURRENT_HEAD,
        "package_camp_head": module.PACKAGE_CAMP_HEAD,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "reviewer_script_sha256": REVIEWER_SCRIPT_SHA,
        "reviewer_test_sha256": REVIEWER_TEST_SHA,
        "preflight_scope": "static_preflight_process_only",
        "consumed_artifact_roots": [],
        "real_artifacts_unopened": True,
        "operations": {
            name: False for name in module.STATIC_PREFLIGHT_OPERATION_NAMES
        },
        "checks": {name: True for name in module.STATIC_PREFLIGHT_CHECK_NAMES},
        "failed_checks": [],
    }
    _write_json(root / "static_preflight.json", result)
    _write_json(root / "stdout.txt", result)
    (root / "HEADS.txt").write_text(
        f"IMPLEMENTATION_SOURCE_HEAD={CURRENT_HEAD}\n"
        f"PACKAGE_CAMP_HEAD={module.PACKAGE_CAMP_HEAD}\n"
        f"FIXED_DP_HEAD={module.FIXED_DP_HEAD}\n"
        f"REVIEWER_SCRIPT_SHA256={REVIEWER_SCRIPT_SHA}\n"
        f"REVIEWER_TEST_SHA256={REVIEWER_TEST_SHA}\n",
        encoding="ascii",
    )
    (root / "COMMAND.txt").write_text(
        "synthetic-static-preflight\n", encoding="utf-8"
    )
    (root / "summary.md").write_text(
        "# synthetic static preflight\n", encoding="utf-8"
    )
    for stem in ("py_compile", "pytest", "git_diff_check"):
        (root / f"{stem}.stdout.txt").write_text("passed\n", encoding="utf-8")
        (root / f"{stem}.stderr.txt").write_bytes(b"")
        (root / f"{stem}.exit").write_bytes(b"0\n")
    (root / "stderr.txt").write_bytes(b"")
    (root / "run.exit").write_bytes(b"0\n")
    return _seal(root), result


def _claim(source_root_sha256: str) -> dict[str, object]:
    derived_guards = {
        name: True for name in _metrics()["evidence_guards"]  # type: ignore[index]
    }
    gates = {
        "retention_rate": True,
        "paired_complete_rate": True,
        "source_invalid_rate": True,
        "execution_invalid_rate": True,
        "safety_cost_mean_delta_below_zero": True,
        "clustered_ci95_upper_below_zero": False,
        "better_exceeds_worse": True,
        "no_additional_collision_pairs": True,
        "no_additional_offroad_pairs": True,
        "no_additional_red_light_pairs": True,
        "no_additional_wrong_way_pairs": True,
        "evidence_guards": True,
    }
    return {
        "schema": module.CLAIM_SCHEMA,
        "status": "passed_honest_no_claim",
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "claim_scope": "frozen_held_out_map_family_and_three_corridor_groups_only",
        "map_family_level_ci": False,
        "unseen_map_generalization": False,
        "native_ranked_k8_superiority": False,
        "latency_comparative_conclusion": False,
        "allowed_claim_text": module.ALLOWED_CLAIM_TEXT,
        "forbidden_claims": list(module.FORBIDDEN_CLAIMS),
        "derived_evidence_guards": derived_guards,
        "gates": gates,
        "failed_gates": ["clustered_ci95_upper_below_zero"],
        "source_reviewer_root_sha256": source_root_sha256,
        "guard_closure": {
            "source_reviewer_root_sha256": source_root_sha256,
            "source_self_guard": False,
            "derived_independent_review_passed": True,
            "authority": "external_complete_seal_rehash_of_reviewer_root",
            "source_reviewer_json_modified": False,
            "only_guard_changed": "independent_review_passed",
        },
        "directional_safety_cost_summary": {
            "mean_delta": EXPECTED_MEAN_DELTA,
            "ci95": [EXPECTED_CI95_LOW, EXPECTED_CI95_HIGH],
            "better_tie_worse": {"better": 4, "tie": 113, "worse": 3},
            "additional_major_event_pairs": {
                name: 0 for name in module.MAJOR_EVENT_FIELDS
            },
        },
    }


def _evidence_artifact(
    root: Path,
    source_root: Path,
    source_root_sha256: str,
    metrics: dict[str, object],
    marker: Path,
    marker_sha256: str,
) -> tuple[str, dict[str, object], dict[str, object]]:
    root.mkdir()
    claim = _claim(source_root_sha256)
    guard_closure = copy.deepcopy(claim["guard_closure"])
    source_review = json.loads(
        (source_root / "review_result.json").read_text(encoding="utf-8")
    )
    builder_authority_fields = {
        "current_v24_status": module.BUILDER_AUTHORIZED_CURRENT_STATUS,
        "current_v24_artifact_source_head": (
            module.BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD
        ),
        "current_v24_final_synced_head": "pending_current_docs_commit_not_source_drift",
        "current_v24_artifact": module.BUILDER_STATIC_PREFLIGHT_PATH,
        "current_v24_artifact_root_sha256": (
            module.BUILDER_STATIC_PREFLIGHT_ROOT_SHA256
        ),
        "current_v24_reviewer_artifact": module.BUILDER_SOURCE_REVIEW_PATH,
        "current_v24_reviewer_artifact_root_sha256": source_root_sha256,
        "current_v24_reviewer_source_head": SOURCE_REVIEW_HEAD,
        "current_v24_holdout_state": marker.as_posix(),
        "current_v24_holdout_state_sha256": marker_sha256,
        "current_v24_holdout_open_count": "1",
        "current_v24_holdout_rerun_authorized": "false",
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "source_a_status": "source_ineligible_missing_authorized_build_prerequisites",
        "source_a_terminal": "true",
        "source_b_status": module.BUILDER_AUTHORIZED_SOURCE_B_STATUS,
        "source_b_terminal": "false",
        "authorized_source_count": "2",
        "source_terminal_count": "1",
        "global_stop_authorized": "false",
        "global_stop_reason": "none",
        "next_work_target": module.BUILDER_AUTHORIZED_NEXT_WORK_TARGET,
    }
    evidence = {
        "schema": module.EVIDENCE_SCHEMA,
        "status": "passed",
        "reviewer_root": {
            "path": source_root.as_posix(),
            "root_sha256": source_root_sha256,
            "file_count": 10,
            "manifest_digests": {
                line.split("  ", 1)[1]: line.split("  ", 1)[0]
                for line in (source_root / "SHA256SUMS")
                .read_text(encoding="utf-8")
                .splitlines()
            },
            "review_result_sha256": hashlib.sha256(
                (source_root / "review_result.json").read_bytes()
            ).hexdigest(),
            "recomputed_metrics_sha256": hashlib.sha256(
                (source_root / "recomputed_metrics.json").read_bytes()
            ).hexdigest(),
            "source_bytes_unchanged": True,
            "complete_seal_rehashed_before_and_after": True,
        },
        "guard_closure": guard_closure,
        "live_authority": {
            "fields": builder_authority_fields,
            "audit_sha256": _sha("builder-audit"),
            "current_status_sha256": _sha("builder-current-status"),
            "verified_before_and_after": True,
            "static_preflight": {
                "source_head": module.BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD,
                "path": module.BUILDER_STATIC_PREFLIGHT_PATH,
                "root_sha256": module.BUILDER_STATIC_PREFLIGHT_ROOT_SHA256,
                "file_count": 16,
                "manifest_digests": {
                    name: _sha(f"builder-static-{name}")
                    for name in module.STATIC_PREFLIGHT_PAYLOAD_PATHS
                },
            },
        },
        "repository_provenance": {
            "package_camp_head": module.PACKAGE_CAMP_HEAD,
            "camp_origin_main": module.PACKAGE_CAMP_HEAD,
            "camp_remote_main": module.PACKAGE_CAMP_HEAD,
            "camp_branch": "main",
            "camp_origin_url": module.CANONICAL_ORIGIN_URL,
            "review_camp_head_is_ancestor": True,
            "execution_source_is_review_ancestor": True,
            "camp_tracked_clean": True,
            "fixed_dp_head": module.FIXED_DP_HEAD,
            "fixed_dp_tracked_clean": True,
            "static_preflight_source_head": (
                module.BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD
            ),
            "static_preflight_source_is_package_ancestor": True,
        },
        "reviewer_camp_head": SOURCE_REVIEW_HEAD,
        "execution_source_head": EXECUTION_HEAD,
        "config_sha256": CONFIG_SHA,
        "evaluator_sha256": EVALUATOR_SHA,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "live_holdout_once": {
            "path": marker.as_posix(),
            "sha256": marker_sha256,
            "open_count": 1,
            "rerun_authorized": False,
            "marker_bytes_unchanged_before_and_after": True,
            "global_lock_exclusively_held_by_this_gate": True,
            "active_evaluator_or_reviewer_process_count": 0,
        },
        "transitive_source_roots_rehashed_by_this_gate": False,
        "transitive_source_roots_role": "inventory_from_complete_sealed_independent_reviewer",
        "source_root_inventory": copy.deepcopy(source_review["source_roots"]),
        "evidence_limitations": copy.deepcopy(
            source_review["evidence_limitations"]
        ),
        "reviewed_metrics": copy.deepcopy(metrics),
        "frozen_training_risk_disclosure": copy.deepcopy(
            source_review["frozen_metric_contract"]
        ),
        "evaluation_summary": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": 120,
            "source_invalid_pair_count": 0,
            "execution_failure_pair_count": 0,
            "dp_tick_count": 7680,
            "camp_tick_count": 7680,
            "candidate0_selection_count": 1401,
            "non_candidate0_selection_count": 6279,
            "all_k_high_risk_pair_count": 8,
            "all_k_high_risk_tick_count": 36,
            "map_family_count": 1,
            "corridor_group_count": 3,
        },
        "claim_decision": {
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "failed_gates": ["clustered_ci95_upper_below_zero"],
        },
        "reviewer_or_execution_rerun": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "online_activation_authorized": False,
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
        "free_bytes_before_package": module.MINIMUM_FREE_BYTES + 1,
        "final_post_publication_checks_required": True,
        "free_bytes_after_gate_recorded_in_return_and_launch_receipt": True,
        "next_work_target": module.EXPECTED_BUILDER_NEXT_WORK_TARGET,
    }
    _write_json(root / "claim_decision.json", claim)
    _write_json(root / "evidence_package.json", evidence)
    (root / "summary.md").write_text("# synthetic evidence package\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"PACKAGE_CAMP_HEAD={module.PACKAGE_CAMP_HEAD}\n"
        f"REVIEWER_CAMP_HEAD={SOURCE_REVIEW_HEAD}\n"
        f"EXECUTION_SOURCE_HEAD={EXECUTION_HEAD}\n"
        f"FIXED_DP_HEAD={module.FIXED_DP_HEAD}\n"
        f"REVIEWER_ROOT_SHA256={source_root_sha256}\n"
        f"CONFIG_SHA256={CONFIG_SHA}\n"
        f"EVALUATOR_SHA256={EVALUATOR_SHA}\n",
        encoding="ascii",
    )
    (root / "COMMAND.txt").write_text("synthetic-builder\n", encoding="utf-8")
    _write_json(
        root / "stdout.txt",
        {
            "status": "passed",
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "failed_gates": ["clustered_ci95_upper_below_zero"],
            "next_work_target": module.EXPECTED_BUILDER_NEXT_WORK_TARGET,
        },
    )
    (root / "stderr.txt").write_bytes(b"")
    (root / "run.exit").write_bytes(b"0\n")
    return _seal(root), claim, evidence


def _launch_artifact(
    root: Path,
    evidence_root: Path,
    evidence_root_sha256: str,
    source_root_sha256: str,
    marker_sha256: str,
) -> tuple[str, dict[str, object]]:
    root.mkdir()
    receipt = {
        "schema": module.LAUNCH_SCHEMA,
        "status": "failed_closed",
        "builder_exit": 0,
        "builder_stderr_empty": True,
        "output_dir": evidence_root.as_posix(),
        "output_exists": True,
        "output_file_count": 8,
        "output_root_sha256": evidence_root_sha256,
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "failed_gates": ["clustered_ci95_upper_below_zero"],
        "final_post_publication_checks_passed": True,
        "validation_error": module.EXPECTED_WRAPPER_VALIDATION_ERROR,
        "marker_unchanged": True,
        "holdout_open_count": 1,
        "holdout_rerun_authorized": False,
        "reviewer_or_execution_rerun": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
        "related_process_count_after": 0,
        "global_lock_free_after": False,
        "config_sha256": CONFIG_SHA,
        "evaluator_sha256": EVALUATOR_SHA,
        "execution_source_head": EXECUTION_HEAD,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "holdout_state_sha256": module.HOLDOUT_STATE_SHA256,
        "next_work_target": module.EXPECTED_LAUNCH_NEXT_WORK_TARGET,
        "package_camp_head": module.PACKAGE_CAMP_HEAD,
        "reviewer_camp_head": SOURCE_REVIEW_HEAD,
        "reviewer_root_sha256": source_root_sha256,
        "duration_s": 1.0,
        "free_bytes_after": module.MINIMUM_FREE_BYTES + 1,
    }
    _write_json(root / "launch_receipt.json", receipt)
    (root / "summary.md").write_text("# synthetic launch wrapper\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"PACKAGE_CAMP_HEAD={module.PACKAGE_CAMP_HEAD}\n"
        f"REVIEWER_CAMP_HEAD={SOURCE_REVIEW_HEAD}\n"
        f"EXECUTION_SOURCE_HEAD={EXECUTION_HEAD}\n"
        f"FIXED_DP_HEAD={module.FIXED_DP_HEAD}\n"
        f"REVIEWER_ROOT_SHA256={source_root_sha256}\n"
        f"CONFIG_SHA256={CONFIG_SHA}\n"
        f"EVALUATOR_SHA256={EVALUATOR_SHA}\n"
        f"HOLDOUT_STATE_SHA256={module.HOLDOUT_STATE_SHA256}\n",
        encoding="ascii",
    )
    (root / "COMMAND.txt").write_text("synthetic-launch\n", encoding="utf-8")
    _write_json(
        root / "stdout.txt",
        {
            "status": "passed",
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "output_dir": evidence_root.as_posix(),
            "root_sha256": evidence_root_sha256,
            "free_bytes_after_gate": module.MINIMUM_FREE_BYTES + 1,
            "final_post_publication_checks_passed": True,
            "next_work_target": module.EXPECTED_BUILDER_NEXT_WORK_TARGET,
        },
    )
    (root / "stderr.txt").write_bytes(b"")
    (root / "run.exit").write_bytes(b"0\n")
    return _seal(root), receipt


def _authority_fields(
    evidence_root: Path,
    evidence_sha: str,
    launch_root: Path,
    launch_sha: str,
    source_root: Path,
    source_sha: str,
    static_preflight_root: Path,
    static_preflight_sha: str,
    marker: Path,
    marker_sha: str,
) -> dict[str, str]:
    return {
        "current_v24_status": module.AUTHORIZED_CURRENT_STATUS,
        "current_v24_artifact_source_head": module.PACKAGE_CAMP_HEAD,
        "current_v24_artifact": evidence_root.as_posix(),
        "current_v24_artifact_root_sha256": evidence_sha,
        "current_v24_launch_artifact": launch_root.as_posix(),
        "current_v24_launch_artifact_root_sha256": launch_sha,
        "current_v24_launch_status": module.AUTHORIZED_LAUNCH_STATUS,
        "current_v24_reviewer_artifact": source_root.as_posix(),
        "current_v24_reviewer_artifact_root_sha256": source_sha,
        "current_v24_reviewer_source_head": SOURCE_REVIEW_HEAD,
        "current_v24_independent_review_source_head": CURRENT_HEAD,
        "current_v24_independent_review_script_sha256": REVIEWER_SCRIPT_SHA,
        "current_v24_independent_review_test_sha256": REVIEWER_TEST_SHA,
        "current_v24_independent_review_static_artifact": (
            static_preflight_root.as_posix()
        ),
        "current_v24_independent_review_static_artifact_root_sha256": (
            static_preflight_sha
        ),
        "current_v24_holdout_state": marker.as_posix(),
        "current_v24_holdout_state_sha256": marker_sha,
        "current_v24_holdout_open_count": "1",
        "current_v24_holdout_rerun_authorized": "false",
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "source_a_status": module.AUTHORIZED_SOURCE_A_STATUS,
        "source_a_terminal": "true",
        "source_b_status": module.AUTHORIZED_SOURCE_B_STATUS,
        "source_b_terminal": "false",
        "authorized_source_count": "2",
        "source_terminal_count": "1",
        "global_stop_authorized": "false",
        "global_stop_reason": "none",
        "next_work_target": module.AUTHORIZED_NEXT_WORK_TARGET,
    }


def _write_authority(camp: Path, fields: dict[str, str]) -> tuple[bytes, bytes]:
    receipt = "\n".join(f"{key}={value}" for key, value in fields.items())
    audit = ("# synthetic audit\n\n" + receipt + "\n").encode("utf-8")
    status = (
        "## Current V24 Status\n\n"
        + receipt
        + "\n\n## Current V23 Status\n\nlegacy\n"
    ).encode("utf-8")
    audit_path = camp / module.AUDIT_RELATIVE_PATH
    status_path = camp / module.CURRENT_STATUS_RELATIVE_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_bytes(audit)
    status_path.write_bytes(status)
    return audit, status


@pytest.fixture
def environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    camp = (tmp_path / "camp").resolve()
    dp = (tmp_path / "dp").resolve()
    camp.mkdir()
    dp.mkdir()
    script_path = camp / module.REVIEWER_SCRIPT_RELATIVE_PATH
    test_path = camp / module.REVIEWER_TEST_RELATIVE_PATH
    script_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_bytes(REVIEWER_SCRIPT_BYTES)
    test_path.write_bytes(REVIEWER_TEST_BYTES)
    marker = (tmp_path / "holdout_once_state.json").resolve()
    marker_state = {
        "schema": "camp_dp_v24_holdout_once_state_v1",
        "holdout_opened": True,
        "holdout_open_count": 1,
        "rerun_authorized": False,
        "camp_head": EXECUTION_HEAD,
        "authorization_root_sha256": _sha("authorization"),
        "preflight_root_sha256": _sha("preflight"),
        "output_dir": "/sealed/execution",
    }
    _write_json(marker, marker_state)
    marker_sha = hashlib.sha256(marker.read_bytes()).hexdigest()
    monkeypatch.setattr(module, "HOLDOUT_STATE_SHA256", marker_sha)
    lock = (tmp_path / "paired.global.lock").resolve()
    lock.write_bytes(b"")
    source_root = (tmp_path / "source-review").resolve()
    source_sha, source_review = _source_review_artifact(source_root)
    monkeypatch.setattr(module, "BUILDER_SOURCE_REVIEW_PATH", source_root.as_posix())
    static_preflight_root = (tmp_path / "static-preflight").resolve()
    static_preflight_sha, static_preflight = _static_preflight_artifact(
        static_preflight_root
    )
    evidence_root = (tmp_path / "evidence").resolve()
    evidence_sha, claim, evidence = _evidence_artifact(
        evidence_root,
        source_root,
        source_sha,
        copy.deepcopy(source_review["metrics"]),  # type: ignore[arg-type]
        marker,
        marker_sha,
    )
    launch_root = (tmp_path / "launch").resolve()
    launch_sha, launch = _launch_artifact(
        launch_root, evidence_root, evidence_sha, source_sha, marker_sha
    )
    monkeypatch.setattr(module, "CANONICAL_SOURCE_REVIEW_ROOT", source_root)
    monkeypatch.setattr(module, "CANONICAL_EVIDENCE_ROOT", evidence_root)
    monkeypatch.setattr(module, "CANONICAL_LAUNCH_ROOT", launch_root)
    monkeypatch.setattr(module, "EXPECTED_SOURCE_REVIEW_ROOT_SHA256", source_sha)
    monkeypatch.setattr(module, "EXPECTED_EVIDENCE_ROOT_SHA256", evidence_sha)
    monkeypatch.setattr(module, "EXPECTED_LAUNCH_ROOT_SHA256", launch_sha)
    fields = _authority_fields(
        evidence_root,
        evidence_sha,
        launch_root,
        launch_sha,
        source_root,
        source_sha,
        static_preflight_root,
        static_preflight_sha,
        marker,
        marker_sha,
    )
    audit_bytes, status_bytes = _write_authority(camp, fields)
    git_blobs = {
        f"{AUTHORITY_HEAD}:{module.AUDIT_RELATIVE_PATH.as_posix()}": audit_bytes,
        f"{AUTHORITY_HEAD}:{module.CURRENT_STATUS_RELATIVE_PATH.as_posix()}": status_bytes,
        f"{CURRENT_HEAD}:{module.REVIEWER_SCRIPT_RELATIVE_PATH.as_posix()}": (
            REVIEWER_SCRIPT_BYTES
        ),
        f"{CURRENT_HEAD}:{module.REVIEWER_TEST_RELATIVE_PATH.as_posix()}": (
            REVIEWER_TEST_BYTES
        ),
    }

    def fake_git_text(repo: Path, *args: str) -> str:
        repo = Path(repo).resolve()
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("rev-parse", "HEAD"):
            return CURRENT_HEAD if repo == camp else module.FIXED_DP_HEAD
        if args == ("rev-parse", "origin/main"):
            return CURRENT_HEAD
        if args == ("symbolic-ref", "--short", "HEAD"):
            return "main"
        if args == ("remote", "get-url", "origin"):
            return module.CANONICAL_ORIGIN_URL
        if args == ("ls-remote", "origin", "refs/heads/main"):
            return f"{CURRENT_HEAD}\trefs/heads/main"
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if len(args) == 3 and args[:2] == ("cat-file", "-t"):
            return "commit"
        raise AssertionError((repo, args))

    monkeypatch.setattr(module, "CANONICAL_CAMP_REPO", camp)
    monkeypatch.setattr(module, "CANONICAL_DP_REPO", dp)
    monkeypatch.setattr(module, "CANONICAL_OUTPUT_PARENT", tmp_path.resolve())
    monkeypatch.setattr(module, "CANONICAL_HOLDOUT_STATE_PATH", marker)
    monkeypatch.setattr(module, "GLOBAL_LOCK_PATH", lock)
    monkeypatch.setattr(module, "_git_text", fake_git_text)
    monkeypatch.setattr(module, "_git_bytes", lambda _repo, obj: git_blobs[obj])
    monkeypatch.setattr(module, "_git_is_ancestor", lambda *_args: True)
    monkeypatch.setattr(module, "_active_v24_processes", lambda: [])
    monkeypatch.setattr(module, "_fsync_tree", lambda _path: None)
    monkeypatch.setattr(module, "_fsync_directory", lambda _path: None)

    @contextlib.contextmanager
    def fake_lock(_path: Path):
        yield

    def fake_rename(source: Path, destination: Path) -> None:
        if Path(destination).exists():
            raise FileExistsError(destination)
        os.rename(source, destination)

    monkeypatch.setattr(module, "_exclusive_global_lock", fake_lock)
    monkeypatch.setattr(module, "_rename_noreplace", fake_rename)

    return {
        "camp": camp,
        "dp": dp,
        "marker": marker,
        "source_root": source_root,
        "source_sha": source_sha,
        "static_preflight_root": static_preflight_root,
        "static_preflight_sha": static_preflight_sha,
        "static_preflight": static_preflight,
        "evidence_root": evidence_root,
        "evidence_sha": evidence_sha,
        "launch_root": launch_root,
        "launch_sha": launch_sha,
        "claim": claim,
        "evidence": evidence,
        "launch": launch,
        "fields": fields,
        "output": (
            tmp_path
            / (
                f"{module.OUTPUT_NAME_PREFIX}{CURRENT_HEAD}_"
                f"{evidence_sha}"
            )
        ).resolve(),
    }


def _kwargs(environment: dict[str, object]) -> dict[str, object]:
    # Synthetic fixtures deliberately reseal mutated inputs so semantic negative
    # tests reach the intended verifier layer. Production calls cannot rewrite
    # these frozen module constants.
    module.EXPECTED_SOURCE_REVIEW_ROOT_SHA256 = str(environment["source_sha"])
    module.EXPECTED_EVIDENCE_ROOT_SHA256 = str(environment["evidence_sha"])
    module.EXPECTED_LAUNCH_ROOT_SHA256 = str(environment["launch_sha"])
    environment["output"] = module._expected_output_path(
        CURRENT_HEAD, str(environment["evidence_sha"])
    )
    return {
        "evidence_root": environment["evidence_root"],
        "expected_evidence_root_sha256": environment["evidence_sha"],
        "launch_root": environment["launch_root"],
        "expected_launch_root_sha256": environment["launch_sha"],
        "source_review_root": environment["source_root"],
        "expected_source_review_root_sha256": environment["source_sha"],
        "static_preflight_root": environment["static_preflight_root"],
        "expected_static_preflight_root_sha256": environment[
            "static_preflight_sha"
        ],
        "camp_repo": environment["camp"],
        "package_camp_head": module.PACKAGE_CAMP_HEAD,
        "authority_source_head": AUTHORITY_HEAD,
        "implementation_source_head": CURRENT_HEAD,
        "expected_reviewer_script_sha256": REVIEWER_SCRIPT_SHA,
        "expected_reviewer_test_sha256": REVIEWER_TEST_SHA,
        "expected_current_camp_head": CURRENT_HEAD,
        "dp_repo": environment["dp"],
        "expected_dp_head": module.FIXED_DP_HEAD,
        "holdout_state_path": environment["marker"],
        "output_dir": environment["output"],
        "enable_independent_review": True,
        "minimum_free_bytes": module.MINIMUM_FREE_BYTES,
        "command": ["synthetic-review"],
    }


def test_frozen_runtime_selector_receipt_matches_production_contract() -> None:
    assert module.EXPECTED_RUNTIME_SELECTOR_ROOT_SHA256 == (
        "ef5539ba04ca5264f1c38951e15f7daac9d32a1dae9c4a80cf0d21109eed2cc5"
    )
    assert module.EXPECTED_RUNTIME_SELECTOR_MANIFEST_PATHS == [
        "adapter_receipt.json",
        "atom_scales.json",
        "weights.npy",
    ]


def test_review_accepts_only_exact_wrapper_false_negative_and_seals_atomically(
    environment: dict[str, object],
) -> None:
    roots = [
        Path(environment[name])
        for name in (
            "source_root",
            "evidence_root",
            "launch_root",
            "static_preflight_root",
        )
    ]
    before = {
        root: {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*")
            if path.is_file()
        }
        for root in roots
    }

    result = module.review_evidence_claim(**_kwargs(environment))

    output = Path(environment["output"])
    assert result["status"] == "passed"
    assert result["classification"] == "launch_wrapper_validation_false_negative"
    assert result["builder_succeeded"] is True
    assert result["sealed_output_authoritative"] is True
    assert result["decision"] == "honest_no_claim"
    assert result["failed_gates"] == ["clustered_ci95_upper_below_zero"]
    assert module.verify_complete_seal(output, result["root_sha256"], label="review")
    assert not output.with_name(output.name + ".tmp").exists()
    review = json.loads((output / "review_result.json").read_text(encoding="utf-8"))
    assert review["checks"]
    assert all(review["checks"].values())
    assert review["check_count"] == len(review["checks"]) == result["check_count"]
    assert review["failed_checks"] == []
    assert review["claim_guard_path_verified"] == (
        "derived_evidence_guards.independent_review_passed"
    )
    assert review["launch_wrapper"]["status_does_not_override_sealed_output"] is True
    assert review["launch_wrapper"]["global_lock_free_after_inconclusive"] is True
    assert review["source_metrics_deep_equal"] is True
    assert review["operations"] == {
        "evaluator_executed": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
    }
    after = {
        root: {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*")
            if path.is_file()
        }
        for root in roots
    }
    assert after == before


def test_explicit_enable_is_required(environment: dict[str, object]) -> None:
    kwargs = _kwargs(environment)
    kwargs["enable_independent_review"] = False
    with pytest.raises(ValueError, match="explicit --enable-independent-review"):
        module.review_evidence_claim(**kwargs)
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("target", "mutation"),
    (
        ("claim", lambda value: value["derived_evidence_guards"].update(independent_review_passed=False)),
        ("claim", lambda value: value["gates"].update(evidence_guards=False)),
        ("claim", lambda value: value["guard_closure"].update(source_self_guard=True)),
        ("claim", lambda value: value.update(failed_gates=[])),
        ("claim", lambda value: value["gates"].update(retention_rate=False)),
        ("evidence", lambda value: value.update(reviewed_metrics={"drift": True})),
        ("source", lambda value: value.update(metrics={"drift": True})),
    ),
)
def test_claim_paths_and_source_metrics_fail_closed(
    environment: dict[str, object], target: str, mutation
) -> None:
    if target == "claim":
        path = Path(environment["evidence_root"]) / "claim_decision.json"
    elif target == "evidence":
        path = Path(environment["evidence_root"]) / "evidence_package.json"
    else:
        path = Path(environment["source_root"]) / "review_result.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutation(value)
    _write_json(path, value)
    if target in {"claim", "evidence"}:
        environment["evidence_sha"] = _seal(Path(environment["evidence_root"]))
    else:
        environment["source_sha"] = _seal(Path(environment["source_root"]))
    with pytest.raises(ValueError):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("schema", "wrong"),
        ("status", "passed"),
        ("builder_exit", 1),
        ("builder_stderr_empty", False),
        ("output_exists", False),
        ("output_file_count", 7),
        ("decision", "limited_claim_gates_passed"),
        ("validation_error", "KeyError: independent_review_passed"),
        ("marker_unchanged", False),
        ("holdout_open_count", 2),
        ("holdout_rerun_authorized", True),
        ("runner_built", True),
        ("model_loaded", True),
        ("simulator_executed", True),
        ("holdout_reopened", True),
        ("related_process_count_after", 1),
        ("global_lock_free_after", True),
    ),
)
def test_launch_receipt_accepts_no_variant(
    environment: dict[str, object], field: str, replacement: object
) -> None:
    path = Path(environment["launch_root"]) / "launch_receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt[field] = replacement
    _write_json(path, receipt)
    environment["launch_sha"] = _seal(Path(environment["launch_root"]))
    with pytest.raises(ValueError, match="launch"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def test_launch_receipt_rejects_unknown_sealed_audit_metadata(
    environment: dict[str, object]
) -> None:
    path = Path(environment["launch_root"]) / "launch_receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["additional_audit_metadata"] = {"receipt_version": 1}
    _write_json(path, receipt)
    environment["launch_sha"] = _seal(Path(environment["launch_root"]))
    with pytest.raises(ValueError, match="key set"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize("target", ("source", "metrics", "launch", "static"))
def test_unknown_extra_schema_fields_fail_closed(
    environment: dict[str, object], target: str
) -> None:
    if target == "source":
        root = Path(environment["source_root"])
        review = json.loads((root / "review_result.json").read_text(encoding="utf-8"))
        review["unknown_extra"] = True
        _write_json(root / "review_result.json", review)
        _write_json(root / "stdout.txt", review)
        environment["source_sha"] = _seal(root)
    elif target == "metrics":
        root = Path(environment["source_root"])
        review = json.loads((root / "review_result.json").read_text(encoding="utf-8"))
        metrics = copy.deepcopy(review["metrics"])
        metrics["unknown_extra"] = True
        review["metrics"] = metrics
        _write_json(root / "review_result.json", review)
        _write_json(root / "recomputed_metrics.json", metrics)
        _write_json(root / "stdout.txt", review)
        environment["source_sha"] = _seal(root)
    elif target == "launch":
        root = Path(environment["launch_root"])
        receipt = json.loads(
            (root / "launch_receipt.json").read_text(encoding="utf-8")
        )
        receipt["unknown_extra"] = True
        _write_json(root / "launch_receipt.json", receipt)
        environment["launch_sha"] = _seal(root)
    else:
        root = Path(environment["static_preflight_root"])
        result = json.loads(
            (root / "static_preflight.json").read_text(encoding="utf-8")
        )
        result["unknown_extra"] = True
        _write_json(root / "static_preflight.json", result)
        _write_json(root / "stdout.txt", result)
        environment["static_preflight_sha"] = _seal(root)
    with pytest.raises(ValueError, match="key set|schema"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("target", "message"),
    (
        ("candidate_histogram", "candidate|histogram"),
        ("source_root_extra", "source root|root receipt|key set"),
        ("holdout_head", "holdout"),
        ("launch_extra", "launch|key set"),
        ("runtime_selector_shape", "runtime selector|14"),
        ("request_route_count", "request[- ]asset|route[- ]asset"),
        ("route_binding_seed", "route.*binding|seed"),
        ("route_binding_identity", "route.*binding|identity"),
    ),
)
def test_source_nested_exact_contracts_fail_closed(
    environment: dict[str, object], target: str, message: str
) -> None:
    root = Path(environment["source_root"])
    review = json.loads((root / "review_result.json").read_text(encoding="utf-8"))
    if target == "candidate_histogram":
        histogram = review["metrics"]["candidate_selection"][
            "camp_selected_index_histogram"
        ]
        histogram["1"] += 1
        histogram["2"] -= 1
        _write_json(root / "recomputed_metrics.json", review["metrics"])
    elif target == "source_root_extra":
        review["source_roots"]["execution"]["unknown_extra"] = True
    elif target == "holdout_head":
        review["holdout_state"]["camp_head"] = "f" * 40
    elif target == "launch_extra":
        review["launch"]["unknown_extra"] = True
    elif target == "runtime_selector_shape":
        review["runtime_selector"]["atom_scales"].pop()
    elif target == "request_route_count":
        review["request_assets"]["route_asset_count"] = 23
    else:
        identity = next(iter(review["route_source_bindings"]))
        if target == "route_binding_seed":
            review["route_source_bindings"][identity]["seeds"] = [24201]
        else:
            review["route_source_bindings"][identity]["identity_sha256"] = "f" * 64
    _write_json(root / "review_result.json", review)
    _write_json(root / "stdout.txt", review)
    source_sha = _seal(root)
    seal = module.verify_complete_seal(
        root,
        source_sha,
        label="source reviewer",
        exact_manifest_paths=module.SOURCE_REVIEW_PAYLOAD_PATHS,
    )
    with pytest.raises(ValueError, match=message):
        module._verify_source_review(seal, source_sha)


@pytest.mark.parametrize(
    ("target", "filename", "replacement", "message"),
    (
        ("source", "schedule_receipt.json", {"pair_count": 119}, "embedded.*schedule"),
        ("source", "stdout.txt", {"status": "passed"}, "stdout"),
        ("launch", "stdout.txt", {"status": "passed"}, "stdout"),
    ),
)
def test_embedded_and_standalone_cross_bindings_fail_closed(
    environment: dict[str, object],
    target: str,
    filename: str,
    replacement: dict[str, object],
    message: str,
) -> None:
    root_key = "source_root" if target == "source" else "launch_root"
    sha_key = "source_sha" if target == "source" else "launch_sha"
    root = Path(environment[root_key])
    if filename == "schedule_receipt.json":
        value = json.loads((root / filename).read_text(encoding="utf-8"))
        value.update(replacement)
        replacement = value
    _write_json(root / filename, replacement)
    environment[sha_key] = _seal(root)
    with pytest.raises(ValueError, match=message):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("root_key", "sha_key", "heads_key", "replacement"),
    (
        ("static_preflight_root", "static_preflight_sha", "REVIEWER_SCRIPT_SHA256", "f" * 64),
        ("launch_root", "launch_sha", "REVIEWER_ROOT_SHA256", "f" * 64),
        ("source_root", "source_sha", "EXECUTION_SOURCE_HEAD", "f" * 40),
    ),
)
def test_heads_cross_binding_drift_is_rejected(
    environment: dict[str, object],
    root_key: str,
    sha_key: str,
    heads_key: str,
    replacement: str,
) -> None:
    root = Path(environment[root_key])
    path = root / "HEADS.txt"
    lines = path.read_text(encoding="ascii").splitlines()
    path.write_text(
        "\n".join(
            f"{heads_key}={replacement}" if line.startswith(f"{heads_key}=") else line
            for line in lines
        )
        + "\n",
        encoding="ascii",
    )
    environment[sha_key] = _seal(root)
    with pytest.raises(ValueError, match="HEADS|binding|provenance"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def test_authority_source_head_must_equal_current_head(
    environment: dict[str, object]
) -> None:
    kwargs = _kwargs(environment)
    kwargs["authority_source_head"] = "a" * 40
    with pytest.raises(ValueError, match="authority source head must equal"):
        module.review_evidence_claim(**kwargs)
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("relative_path", "replacement"),
    (
        (module.REVIEWER_SCRIPT_RELATIVE_PATH, b"drifted reviewer script\n"),
        (module.REVIEWER_TEST_RELATIVE_PATH, b"drifted reviewer tests\n"),
    ),
)
def test_live_reviewer_code_must_equal_frozen_source_blob(
    environment: dict[str, object], relative_path: Path, replacement: bytes
) -> None:
    path = Path(environment["camp"]) / relative_path
    path.write_bytes(replacement)
    with pytest.raises(ValueError, match="source blobs differ from live code"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    "root_name",
    ("evidence_root", "launch_root", "source_root", "static_preflight_root"),
)
def test_all_source_complete_seals_are_rehashed(
    environment: dict[str, object], root_name: str
) -> None:
    root = Path(environment[root_name])
    target = next(
        path for path in root.iterdir() if path.is_file() and path.name != "SHA256SUMS"
    )
    target.write_bytes(target.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="SHA256"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    ("root_name", "sha_name"),
    (
        ("evidence_root", "evidence_sha"),
        ("launch_root", "launch_sha"),
        ("source_root", "source_sha"),
        ("static_preflight_root", "static_preflight_sha"),
    ),
)
def test_all_source_manifests_reject_sealed_extra_files(
    environment: dict[str, object], root_name: str, sha_name: str
) -> None:
    root = Path(environment[root_name])
    (root / "extra.txt").write_text("sealed but unauthorized\n", encoding="utf-8")
    environment[sha_name] = _seal(root)
    with pytest.raises(ValueError, match="manifest path set"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def test_symlink_in_any_sealed_source_is_rejected_when_supported(
    environment: dict[str, object]
) -> None:
    root = Path(environment["launch_root"])
    link = root / "link.txt"
    try:
        os.symlink(root / "summary.md", link)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        module.review_evidence_claim(**_kwargs(environment))


def test_claim_is_independently_recomputed_from_source_metrics() -> None:
    metrics = _metrics()
    derived = module._independently_recompute_claim(metrics)
    assert derived["failed_gates"] == ["clustered_ci95_upper_below_zero"]
    assert derived["gates"]["evidence_guards"] is True

    metrics["safety_cost_delta"]["mean"] = 0.01  # type: ignore[index]
    changed = module._independently_recompute_claim(metrics)
    assert changed["failed_gates"] == [
        "safety_cost_mean_delta_below_zero",
        "clustered_ci95_upper_below_zero",
    ]


def test_raw_byte_and_transitive_evidence_limitations_cannot_be_upgraded(
    environment: dict[str, object]
) -> None:
    path = Path(environment["evidence_root"]) / "evidence_package.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["evidence_limitations"]["raw_byte_proof_claimed"] = True
    evidence["transitive_source_roots_rehashed_by_this_gate"] = True
    _write_json(path, evidence)
    environment["evidence_sha"] = _seal(Path(environment["evidence_root"]))
    with pytest.raises(ValueError, match="limitations"):
        module.review_evidence_claim(**_kwargs(environment))


def test_claim_scope_and_forbidden_claims_cannot_be_upgraded(
    environment: dict[str, object]
) -> None:
    path = Path(environment["evidence_root"]) / "claim_decision.json"
    claim = json.loads(path.read_text(encoding="utf-8"))
    claim["unseen_map_generalization"] = True
    claim["forbidden_claims"].remove("broad_unseen_map_generalization")
    _write_json(path, claim)
    environment["evidence_sha"] = _seal(Path(environment["evidence_root"]))
    environment["output"] = module._expected_output_path(
        CURRENT_HEAD, str(environment["evidence_sha"])
    )
    with pytest.raises(ValueError, match="claim scope|forbidden-claim"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def _write_proc_stat(proc: Path, pid: int, parent: int) -> Path:
    root = proc / str(pid)
    root.mkdir(parents=True)
    (root / "stat").write_text(
        f"{pid} (synthetic process) S {parent}\n", encoding="utf-8"
    )
    return root


def test_process_scan_excludes_ancestors_detects_unrelated_and_fails_unreadable(
    tmp_path: Path,
) -> None:
    proc = tmp_path / "proc"
    proc.mkdir()
    current = _write_proc_stat(proc, 100, 1)
    parent = _write_proc_stat(proc, 1, 0)
    unrelated = _write_proc_stat(proc, 200, 1)
    (current / "cmdline").mkdir()
    (parent / "cmdline").mkdir()
    (unrelated / "cmdline").write_bytes(
        b"python\0evaluate_diffusion_planner_v24_pairs.py\0"
    )
    assert module._active_v24_processes(proc_root=proc, current_pid=100) == [200]

    (unrelated / "cmdline").unlink()
    (unrelated / "cmdline").mkdir()
    with pytest.raises(RuntimeError, match="non-ancestor process cmdline"):
        module._active_v24_processes(proc_root=proc, current_pid=100)


def test_marker_process_disk_repo_and_dp_gates_fail_closed(
    environment: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _kwargs(environment)
    marker = Path(environment["marker"])
    marker.write_bytes(marker.read_bytes() + b" ")
    with pytest.raises(ValueError, match="marker"):
        module.review_evidence_claim(**kwargs)

    marker.write_bytes(marker.read_bytes()[:-1])
    monkeypatch.setattr(module, "_active_v24_processes", lambda: [123])
    with pytest.raises(ValueError, match="process"):
        module.review_evidence_claim(**kwargs)

    monkeypatch.setattr(module, "_active_v24_processes", lambda: [])
    kwargs["minimum_free_bytes"] = 2**80
    with pytest.raises(ValueError, match="10 GiB|disk"):
        module.review_evidence_claim(**kwargs)

    kwargs["minimum_free_bytes"] = module.MINIMUM_FREE_BYTES
    kwargs["expected_current_camp_head"] = "e" * 40
    kwargs["output_dir"] = module._expected_output_path(
        str(kwargs["expected_current_camp_head"]),
        str(environment["evidence_sha"]),
    )
    with pytest.raises(ValueError, match="CAMP"):
        module.review_evidence_claim(**kwargs)

    kwargs["expected_current_camp_head"] = CURRENT_HEAD
    kwargs["output_dir"] = module._expected_output_path(
        CURRENT_HEAD, str(environment["evidence_sha"])
    )
    kwargs["expected_dp_head"] = "e" * 40
    with pytest.raises(ValueError, match="DP"):
        module.review_evidence_claim(**kwargs)
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    "field",
    (
        "current_v24_status",
        "current_v24_launch_status",
        "source_a_status",
        "source_b_status",
        "next_work_target",
    ),
)
def test_live_authority_is_bound_to_exact_static_pass_tuple(
    environment: dict[str, object], field: str
) -> None:
    fields = dict(environment["fields"])
    fields[field] = "wrong"
    _write_authority(Path(environment["camp"]), fields)
    with pytest.raises(ValueError, match="authority"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def test_no_clobber_and_atomic_cleanup(
    environment: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    output = Path(environment["output"])
    output.mkdir()
    with pytest.raises(FileExistsError):
        module.review_evidence_claim(**_kwargs(environment))
    assert output.is_dir()
    output.rmdir()

    original = module._write_json

    def fail_review(path: Path, value: object) -> None:
        if Path(path).name == "review_result.json":
            raise RuntimeError("write-sentinel")
        original(path, value)

    monkeypatch.setattr(module, "_write_json", fail_review)
    with pytest.raises(RuntimeError, match="write-sentinel"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not output.exists()
    assert not output.with_name(output.name + ".tmp").exists()


def test_package_and_dp_heads_are_not_configurable_drift(
    environment: dict[str, object]
) -> None:
    kwargs = _kwargs(environment)
    kwargs["package_camp_head"] = "f" * 40
    with pytest.raises(ValueError, match="package CAMP"):
        module.review_evidence_claim(**kwargs)
    kwargs = _kwargs(environment)
    kwargs["expected_dp_head"] = "f" * 40
    with pytest.raises(ValueError, match="DP"):
        module.review_evidence_claim(**kwargs)


def test_output_path_is_deterministic_not_prefix_only(
    environment: dict[str, object]
) -> None:
    kwargs = _kwargs(environment)
    kwargs["output_dir"] = Path(environment["output"]).with_name(
        f"{module.OUTPUT_NAME_PREFIX}arbitrary"
    )
    with pytest.raises(ValueError, match="deterministic|output artifact path"):
        module.review_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()


@pytest.mark.parametrize(
    ("field", "replacement_kind"),
    (
        ("source_review_root", "path"),
        ("evidence_root", "path"),
        ("launch_root", "path"),
        ("expected_source_review_root_sha256", "sha"),
        ("expected_evidence_root_sha256", "sha"),
        ("expected_launch_root_sha256", "sha"),
    ),
)
def test_production_source_evidence_and_launch_roots_are_frozen(
    environment: dict[str, object], field: str, replacement_kind: str, tmp_path: Path
) -> None:
    kwargs = _kwargs(environment)
    kwargs[field] = (
        (tmp_path / f"drift-{field}").resolve()
        if replacement_kind == "path"
        else "f" * 64
    )
    with pytest.raises(ValueError, match="frozen production root"):
        module.review_evidence_claim(**kwargs)
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    "root_name",
    ("evidence_root", "launch_root", "source_root", "static_preflight_root"),
)
def test_artifact_root_symlinks_are_rejected_before_resolve(
    environment: dict[str, object], root_name: str
) -> None:
    root = Path(environment[root_name])
    real = root.with_name(root.name + "-real")
    root.rename(real)
    try:
        os.symlink(real, root, target_is_directory=True)
    except OSError:
        real.rename(root)
        pytest.skip("directory symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


@pytest.mark.parametrize(
    "label",
    ("source reviewer", "evidence", "launch", "static preflight"),
)
def test_all_sealed_roots_reject_ancestor_component_symlinks(
    tmp_path: Path, label: str
) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    root = real_parent / label.replace(" ", "-")
    root.mkdir()
    (root / "summary.txt").write_text("sealed\n", encoding="utf-8")
    root_sha256 = _seal(root)
    alias_parent = tmp_path / "alias-parent"
    try:
        os.symlink(real_parent, alias_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")

    with pytest.raises(ValueError, match="symlink component"):
        module.verify_complete_seal(
            alias_parent / root.name,
            root_sha256,
            label=label,
        )


@pytest.mark.parametrize(
    ("constant_name", "leaf_kind"),
    (
        ("CANONICAL_SOURCE_REVIEW_ROOT", "directory"),
        ("CANONICAL_EVIDENCE_ROOT", "directory"),
        ("CANONICAL_LAUNCH_ROOT", "directory"),
        ("CANONICAL_CAMP_REPO", "directory"),
        ("CANONICAL_DP_REPO", "directory"),
        ("CANONICAL_HOLDOUT_STATE_PATH", "file"),
        ("GLOBAL_LOCK_PATH", "file"),
        ("CANONICAL_OUTPUT_PARENT", "directory"),
    ),
)
def test_frozen_production_paths_reject_ancestor_component_symlinks(
    environment: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    constant_name: str,
    leaf_kind: str,
) -> None:
    real_parent = tmp_path / f"real-{constant_name.lower()}"
    real_parent.mkdir()
    leaf = real_parent / "leaf"
    if leaf_kind == "directory":
        leaf.mkdir()
    else:
        leaf.write_bytes(b"")
    alias_parent = tmp_path / f"alias-{constant_name.lower()}"
    try:
        os.symlink(real_parent, alias_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")
    monkeypatch.setattr(module, constant_name, alias_parent / leaf.name)

    with pytest.raises(ValueError, match="symlink component"):
        module._verify_frozen_production_path_components()


def test_public_entry_checks_frozen_components_before_global_lock(
    environment: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def fail_component_check() -> None:
        events.append("components")
        raise ValueError("component guard stopped review")

    @contextlib.contextmanager
    def forbidden_lock(_path: Path):
        events.append("lock")
        yield

    monkeypatch.setattr(
        module, "_verify_frozen_production_path_components", fail_component_check
    )
    monkeypatch.setattr(module, "_exclusive_global_lock", forbidden_lock)

    with pytest.raises(ValueError, match="component guard"):
        module.review_evidence_claim(**_kwargs(environment))
    assert events == ["components"]


@pytest.mark.parametrize(
    "root_name",
    ("evidence_root", "launch_root", "source_root", "static_preflight_root"),
)
def test_exact_artifact_trees_reject_extra_directories(
    environment: dict[str, object], root_name: str
) -> None:
    root = Path(environment[root_name])
    (root / "extra-directory").mkdir()
    with pytest.raises(ValueError, match="non-regular|inexact"):
        module.review_evidence_claim(**_kwargs(environment))


def test_complete_seal_rejects_external_hardlink_alias(
    environment: dict[str, object], tmp_path: Path
) -> None:
    root = Path(environment["source_root"])
    try:
        os.link(root / "summary.md", tmp_path / "external-summary-hardlink.md")
    except OSError:
        pytest.skip("hard links are unavailable")
    with pytest.raises(ValueError, match="unaliased regular file"):
        module.review_evidence_claim(**_kwargs(environment))


@pytest.mark.skipif(os.name == "nt", reason="POSIX special files required")
@pytest.mark.parametrize("kind", ("fifo", "socket"))
def test_complete_seal_rejects_posix_fifo_and_socket(
    environment: dict[str, object], kind: str
) -> None:
    root = Path(environment["launch_root"])
    special = root / f"extra-{kind}"
    handle: socket.socket | None = None
    if kind == "fifo":
        os.mkfifo(special)
    else:
        handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        handle.bind(str(special))
    try:
        with pytest.raises(ValueError, match="non-regular"):
            module.review_evidence_claim(**_kwargs(environment))
    finally:
        if handle is not None:
            handle.close()


def test_public_disk_floor_is_exactly_ten_gib(
    environment: dict[str, object]
) -> None:
    kwargs = _kwargs(environment)
    for invalid in (0, module.MINIMUM_FREE_BYTES - 1, module.MINIMUM_FREE_BYTES + 1, True):
        kwargs["minimum_free_bytes"] = invalid
        with pytest.raises(ValueError, match="equal the frozen 10 GiB"):
            module.review_evidence_claim(**kwargs)
    assert not Path(environment["output"]).exists()


def test_disk_floor_boundary_is_strict(
    environment: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    free = module.MINIMUM_FREE_BYTES

    def fake_usage(_path: Path):
        return type("DiskUsage", (), {"free": free})()

    monkeypatch.setattr(module.shutil, "disk_usage", fake_usage)
    with pytest.raises(ValueError, match="10 GiB disk floor"):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()
    free = module.MINIMUM_FREE_BYTES + 1
    result = module.review_evidence_claim(**_kwargs(environment))
    assert result["free_bytes_after_gate"] == module.MINIMUM_FREE_BYTES + 1


@pytest.mark.parametrize(
    "target",
    (
        "runtime_weight",
        "training_risk_weight",
        "config",
        "route_asset_identity_join",
        "map_asset_path_join",
        "fixed_asset_key_set",
    ),
)
def test_selector_training_config_and_asset_joins_are_exact(
    environment: dict[str, object], target: str
) -> None:
    root = Path(environment["source_root"])
    review = json.loads((root / "review_result.json").read_text(encoding="utf-8"))
    if target == "runtime_weight":
        review["runtime_selector"]["weights"][0] = 0.0
    elif target == "training_risk_weight":
        review["frozen_metric_contract"]["learning_curve_stability"][
            "full_effective_support_weights"
        ][0] += 0.01
    elif target == "config":
        review["preflight_config_sha256"] = "f" * 64
    elif target == "route_asset_identity_join":
        assets = review["request_assets"]["route_asset_sha256"]
        assets["f" * 64] = assets.pop(next(iter(assets)))
    elif target == "map_asset_path_join":
        maps = review["request_assets"]["map_asset_sha256"]
        maps["/sealed/maps/different-map.osm"] = maps.pop(next(iter(maps)))
    else:
        review["request_assets"]["fixed_dp_assets"]["unknown"] = "f" * 64
    _write_json(root / "review_result.json", review)
    _write_json(root / "stdout.txt", review)
    source_sha = _seal(root)
    seal = module.verify_complete_seal(
        root,
        source_sha,
        label="source reviewer",
        exact_manifest_paths=module.SOURCE_REVIEW_PAYLOAD_PATHS,
    )
    with pytest.raises(ValueError):
        module._verify_source_review(seal, source_sha)


def test_route_pickle_asset_is_joined_by_identity_not_serialization_digest(
    environment: dict[str, object]
) -> None:
    root = Path(environment["source_root"])
    source_sha = str(environment["source_sha"])
    seal = module.verify_complete_seal(
        root,
        source_sha,
        label="source reviewer",
        exact_manifest_paths=module.SOURCE_REVIEW_PAYLOAD_PATHS,
    )
    verified = module._verify_source_review(seal, source_sha)
    review = verified["review"]
    for identity, binding in review["route_source_bindings"].items():
        assert identity in review["request_assets"]["route_asset_sha256"]
        assert (
            binding["route_serialization_sha256"]
            != review["request_assets"]["route_asset_sha256"][identity]
        )


@pytest.mark.parametrize(
    "target",
    (
        "claim_extra",
        "evidence_extra",
        "stdout_extra",
        "live_authority",
        "source_inventory",
        "training_risk",
        "evaluation_summary",
    ),
)
def test_evidence_claim_stdout_and_deep_bindings_are_exact(
    environment: dict[str, object], target: str
) -> None:
    root = Path(environment["evidence_root"])
    if target == "claim_extra":
        path = root / "claim_decision.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unknown"] = True
    elif target == "stdout_extra":
        path = root / "stdout.txt"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unknown"] = True
    else:
        path = root / "evidence_package.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        if target == "evidence_extra":
            value["unknown"] = True
        elif target == "live_authority":
            value["live_authority"]["fields"]["source_terminal_count"] = "2"
        elif target == "source_inventory":
            value["source_root_inventory"]["training"]["root_sha256"] = "f" * 64
        elif target == "training_risk":
            value["frozen_training_risk_disclosure"][
                "train_route_seed_source_coverage_disclosure"
            ]["failed"] = 820
        else:
            value["evaluation_summary"]["camp_tick_count"] = 7679
    _write_json(path, value)
    environment["evidence_sha"] = _seal(root)
    with pytest.raises(ValueError):
        module.review_evidence_claim(**_kwargs(environment))
    assert not Path(environment["output"]).exists()


def test_post_publish_cleanup_never_deletes_replacement_inode(
    environment: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    output = Path(environment["output"])
    displaced = output.with_name(output.name + ".owned-displaced")

    def swap_after_publish(source: Path, destination: Path) -> None:
        os.rename(source, destination)
        os.rename(destination, displaced)
        destination.mkdir()
        (destination / "sentinel.txt").write_text("do not delete\n", encoding="utf-8")

    monkeypatch.setattr(module, "_rename_noreplace", swap_after_publish)
    with pytest.raises(ValueError, match="inode"):
        module.review_evidence_claim(**_kwargs(environment))
    assert (output / "sentinel.txt").read_text(encoding="utf-8") == "do not delete\n"
    assert displaced.is_dir()
