from __future__ import annotations

import argparse
import contextlib
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PACKAGE_CAMP_HEAD = "f5907606a2e1e9c68b9211fb8aa4b588f2c0c90a"
SOURCE_REVIEWER_CAMP_HEAD = "aff69dfcae3d3dcde79b9c46912493767f9208f2"
EXECUTION_SOURCE_HEAD = "8caa2699b3657154f464e14c2f274190d3036c4a"
PREFLIGHT_CAMP_HEAD = "ca54fa2c921440a7ae44961ee410bdab67d5fe19"
PILOT_REVIEW_CAMP_HEAD = "e7d78689eb853a3d3a97651a689683294d2396a0"
PILOT_EXECUTION_SOURCE_HEAD = "3ac4b0096c0ed25181c5f90dcc3957e852fd13fb"
CONFIG_SHA256 = "9dc0ab9415239211f16e65495362d83c2a11ffe04a96f4ddd2881b12fc193c0f"
EVALUATOR_SHA256 = "c2285006bb820f9e2db6d6f54987f9b8b44447e95fe682c2649002f3342e5fc1"
HOLDOUT_STATE_SHA256 = "f40ae944de12078e5d8f169f7c3b6b451cd0c48a1d0819a165e2cdc1260c1633"
EXPECTED_SOURCE_REVIEW_ROOT_SHA256 = (
    "43e165aad29a614835430d90f53d0c906079ba01826f1f49d73dbe5de4f3e5bf"
)
EXPECTED_EVIDENCE_ROOT_SHA256 = (
    "044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808"
)
EXPECTED_LAUNCH_ROOT_SHA256 = (
    "8a7ee77bea252de0ac84a6531408a8f82b071ba144eee42c924531042e90c3af"
)
BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD = "ca30eb470943b0128c4ab79122cfae3a9988bfc0"
BUILDER_STATIC_PREFLIGHT_ROOT_SHA256 = (
    "6955d6bb52817a1e5d3eda0bc3d54aaa9a0754f059baca597cb01381fac6f481"
)
BUILDER_STATIC_PREFLIGHT_PATH = (
    "/root/autodl-tmp/camp_dp_v24_evidence_claim_static_preflight_"
    "ca30eb47_20260717T063226CST_process_scan_remediation"
)
BUILDER_SOURCE_REVIEW_PATH = (
    "/root/autodl-tmp/camp_dp_v24_paired_holdout_main_once_execution_"
    "independent_review_aff69dfc_20260717T052311CST"
)
CANONICAL_SOURCE_REVIEW_ROOT = Path(BUILDER_SOURCE_REVIEW_PATH)
CANONICAL_EVIDENCE_ROOT = Path(
    "/root/autodl-tmp/camp_dp_v24_evidence_package_and_claim_decision_"
    "f5907606a2e1e9c68b9211fb8aa4b588f2c0c90a_"
    "43e165aad29a614835430d90f53d0c906079ba01826f1f49d73dbe5de4f3e5bf"
)
CANONICAL_LAUNCH_ROOT = Path(f"{CANONICAL_EVIDENCE_ROOT.as_posix()}_launch")
CANONICAL_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
CANONICAL_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
CANONICAL_OUTPUT_PARENT = Path("/root/autodl-tmp")
CANONICAL_HOLDOUT_STATE_PATH = Path(
    "/root/autodl-tmp/camp_dp_v24_paired_holdout_once_state.json"
)
GLOBAL_LOCK_PATH = Path(
    "/root/autodl-tmp/camp_dp_v24_paired_evaluation.global.lock"
)
CANONICAL_ORIGIN_URL = "https://github.com/Fake-fate11/camp-core.git"
AUDIT_RELATIVE_PATH = Path("docs/diffusion_planner_v24_iteration_audit.md")
CURRENT_STATUS_RELATIVE_PATH = Path("docs/diffusion_planner_current_status.md")
OUTPUT_NAME_PREFIX = "camp_dp_v24_evidence_package_claim_decision_independent_review_"
REVIEWER_SCRIPT_RELATIVE_PATH = Path(
    "scripts/integrations/review_diffusion_planner_v24_evidence_claim.py"
)
REVIEWER_TEST_RELATIVE_PATH = Path(
    "camp_core/tests/test_diffusion_planner_v24_evidence_claim_review.py"
)

AUTHORIZED_CURRENT_STATUS = (
    "v24_evidence_package_and_preregistered_claim_decision_independent_review_"
    "tdd_static_preflight_passed"
)
AUTHORIZED_LAUNCH_STATUS = (
    "sealed_wrapper_validation_false_negative_builder_exit_0"
)
AUTHORIZED_NEXT_WORK_TARGET = (
    "v24_evidence_package_and_preregistered_claim_decision_independent_review_"
    "execution_only"
)
AUTHORIZED_SOURCE_A_STATUS = (
    "source_ineligible_missing_authorized_build_prerequisites"
)
AUTHORIZED_SOURCE_B_STATUS = (
    "paired_holdout_main_once_execution_complete_open_count_1_rerun_forbidden_"
    "independent_result_review_passed_evidence_claim_execution_complete_honest_"
    "no_claim_launch_wrapper_false_negative_independent_review_tdd_static_"
    "preflight_passed"
)
EXPECTED_WRAPPER_VALIDATION_ERROR = (
    "ValueError: external reviewer self-guard not closed"
)
EXPECTED_LAUNCH_NEXT_WORK_TARGET = "v24_evidence_claim_retry_failure_review_only"
EXPECTED_BUILDER_NEXT_WORK_TARGET = "v24_honest_no_claim_record_only_closeout"
BUILDER_AUTHORIZED_CURRENT_STATUS = (
    "v24_evidence_package_and_preregistered_claim_decision_process_scan_"
    "remediation_static_preflight_passed"
)
BUILDER_AUTHORIZED_NEXT_WORK_TARGET = (
    "v24_evidence_package_and_preregistered_claim_decision_retry_execution_only"
)
BUILDER_AUTHORIZED_SOURCE_B_STATUS = (
    "paired_holdout_main_once_execution_complete_open_count_1_rerun_forbidden_"
    "independent_result_review_passed_evidence_claim_process_scan_remediation_"
    "static_preflight_passed_honest_no_claim_retry_pending"
)
ALLOWED_CLAIM_TEXT = (
    "Within the frozen single held-out map family, three corridor groups, and "
    "120 paired runs, CAMP's SafetyCost mean was directionally lower than the "
    "DP operational candidate-0 default, but the preregistered clustered CI95 "
    "crossed zero, so the preregistered safety-improvement claim is not supported."
)
FORBIDDEN_CLAIMS = (
    "statistically_supported_safety_improvement",
    "broad_unseen_map_generalization",
    "map_family_level_ci",
    "native_ranked_top1_superiority",
    "comparative_latency_conclusion",
    "real_world_safety",
    "promotion",
    "deployment",
    "online_activation",
    "independent_raw_candidate_tensor_rehash",
    "independent_raw_atom_matrix_recomputation",
)

SOURCE_REVIEW_SCHEMA = (
    "camp_dp_v24_paired_holdout_main_once_execution_independent_review_v1"
)
EVIDENCE_SCHEMA = "camp_dp_v24_evidence_package_v1"
CLAIM_SCHEMA = "camp_dp_v24_preregistered_claim_decision_v1"
LAUNCH_SCHEMA = "camp_dp_v24_evidence_package_claim_decision_launch_v1"
REVIEW_SCHEMA = "camp_dp_v24_evidence_package_claim_decision_independent_review_v1"
STATIC_PREFLIGHT_SCHEMA = (
    "camp_dp_v24_evidence_claim_independent_review_static_preflight_v1"
)

MINIMUM_FREE_BYTES = 10 * 1024**3
HEX = frozenset("0123456789abcdef")
EVIDENCE_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "claim_decision.json",
        "evidence_package.json",
        "run.exit",
        "stderr.txt",
        "stdout.txt",
        "summary.md",
    }
)
LAUNCH_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "launch_receipt.json",
        "run.exit",
        "stderr.txt",
        "stdout.txt",
        "summary.md",
    }
)
SOURCE_REVIEW_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "provenance.json",
        "recomputed_metrics.json",
        "review_result.json",
        "run.exit",
        "schedule_receipt.json",
        "stderr.txt",
        "stdout.txt",
        "summary.md",
    }
)
STATIC_PREFLIGHT_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "static_preflight.json",
        "summary.md",
        "py_compile.stdout.txt",
        "py_compile.stderr.txt",
        "py_compile.exit",
        "pytest.stdout.txt",
        "pytest.stderr.txt",
        "pytest.exit",
        "git_diff_check.stdout.txt",
        "git_diff_check.stderr.txt",
        "git_diff_check.exit",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
    }
)
REVIEW_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "provenance.json",
        "review_result.json",
        "run.exit",
        "stderr.txt",
        "stdout.txt",
        "summary.md",
    }
)
EVIDENCE_GUARD_NAMES = (
    "artifact_sha_verified",
    "per_arm_candidate_immutability_verified",
    "per_arm_candidate0_default_identity_verified",
    "t0_cross_arm_input_and_candidate_identity_verified",
    "independent_review_passed",
    "split_zero_overlap_verified",
    "holdout_once_verified",
    "arm_order_balance_verified",
    "feature_identity_denylist_verified",
)
CLAIM_GATE_NAMES = (
    "retention_rate",
    "paired_complete_rate",
    "source_invalid_rate",
    "execution_invalid_rate",
    "safety_cost_mean_delta_below_zero",
    "clustered_ci95_upper_below_zero",
    "better_exceeds_worse",
    "no_additional_collision_pairs",
    "no_additional_offroad_pairs",
    "no_additional_red_light_pairs",
    "no_additional_wrong_way_pairs",
    "evidence_guards",
)
EXPECTED_FAILED_GATES = ["clustered_ci95_upper_below_zero"]
MAJOR_EVENT_FIELDS = (
    "collision_any",
    "offroad_rate",
    "red_light_violation_any",
    "wrong_way_rate",
)
FORBIDDEN_LIVE_PROCESS_TOKENS = (
    "build_diffusion_planner_v24_evidence_claim.py",
    "review_diffusion_planner_v24_evidence_claim.py",
    "evaluate_diffusion_planner_v24_pairs.py",
    "review_diffusion_planner_v24_holdout_main_result.py",
    "execute_diffusion_planner_v24_native_corpus.py",
    "scenario_simulator_v2",
)
AUTHORITY_REQUIRED_FIELDS = frozenset(
    {
        "current_v24_status",
        "current_v24_artifact_source_head",
        "current_v24_artifact",
        "current_v24_artifact_root_sha256",
        "current_v24_launch_artifact",
        "current_v24_launch_artifact_root_sha256",
        "current_v24_launch_status",
        "current_v24_reviewer_artifact",
        "current_v24_reviewer_artifact_root_sha256",
        "current_v24_reviewer_source_head",
        "current_v24_independent_review_source_head",
        "current_v24_independent_review_script_sha256",
        "current_v24_independent_review_test_sha256",
        "current_v24_independent_review_static_artifact",
        "current_v24_independent_review_static_artifact_root_sha256",
        "current_v24_holdout_state",
        "current_v24_holdout_state_sha256",
        "current_v24_holdout_open_count",
        "current_v24_holdout_rerun_authorized",
        "fixed_dp_head",
        "source_a_status",
        "source_a_terminal",
        "source_b_status",
        "source_b_terminal",
        "authorized_source_count",
        "source_terminal_count",
        "global_stop_authorized",
        "global_stop_reason",
        "next_work_target",
    }
)
FORBIDDEN_OPERATION_FIELDS = (
    "reviewer_or_execution_rerun",
    "runner_built",
    "model_loaded",
    "simulator_executed",
    "holdout_reopened",
)
SOURCE_REVIEW_FORBIDDEN_OPERATION_FIELDS = (
    "source_execution_reexecuted",
    "runner_built",
    "model_loaded",
    "simulator_executed",
    "holdout_reopened",
)
REVIEW_CHECK_NAMES = (
    "static_preflight_complete_seal_exact",
    "reviewer_code_and_test_blobs_pinned",
    "evidence_complete_seal_exact",
    "launch_complete_seal_exact",
    "source_reviewer_complete_seal_exact",
    "source_metrics_deep_equal",
    "independent_claim_recomputed",
    "derived_guard_path_verified",
    "aggregate_guard_gate_path_verified",
    "exact_wrapper_false_negative_verified",
    "live_authority_verified",
    "camp_repository_verified",
    "fixed_dp_verified",
    "holdout_marker_verified",
    "global_lock_exclusive",
    "no_active_processes",
    "disk_floor_preserved",
    "evidence_limitations_preserved",
    "prohibited_operations_absent",
    "atomic_no_clobber_publication_contract_prepared",
)
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 27
EXPECTED_SOURCE_REVIEW_CHECK_NAMES = frozenset(
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
EXPECTED_MEAN_DELTA = -0.014322916666666666
EXPECTED_CI95_LOW = -0.06380208333333333
EXPECTED_CI95_HIGH = 0.01953125
EXPECTED_BETTER_TIE_WORSE = {"better": 4, "tie": 113, "worse": 3}
STATIC_PREFLIGHT_CHECK_NAMES = frozenset(
    {
        "py_compile_passed",
        "focused_pytest_passed",
        "git_diff_check_passed",
        "reviewer_script_sha256_verified",
        "reviewer_test_sha256_verified",
        "real_artifacts_unopened",
        "no_production_operations",
    }
)
STATIC_PREFLIGHT_OPERATION_NAMES = frozenset(
    {
        "evidence_artifact_opened",
        "launch_artifact_opened",
        "source_reviewer_artifact_opened",
        "independent_review_executed",
        "evidence_builder_executed",
        "evaluator_executed",
        "runner_built",
        "model_loaded",
        "simulator_executed",
        "holdout_reopened",
    }
)
SOURCE_REVIEW_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "status",
        "check_count",
        "failed_count",
        "failed_checks",
        "checks",
        "source_roots",
        "schedule",
        "execution",
        "holdout_state",
        "launch",
        "provenance",
        "runtime_selector",
        "request_assets",
        "route_source_bindings",
        "frozen_metric_contract",
        "evidence_limitations",
        "claim_guard_handoff",
        "metrics",
        "camp_head",
        "execution_source_head",
        "preflight_camp_head",
        "preflight_config_sha256",
        "pilot_review_camp_head",
        "pilot_execution_source_head",
        "fixed_dp_head",
        "source_execution_reexecuted",
        "runner_built",
        "model_loaded",
        "simulator_executed",
        "holdout_reopened",
        "holdout_open_count",
        "latency_comparison_authorized",
        "map_family_level_ci_authorized",
        "unseen_map_generalization_authorized",
        "native_ranked_k8_claim_authorized",
        "final_claim_authorized",
        "free_bytes_after_review",
        "next_work_target",
    }
)
SOURCE_METRIC_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "bootstrap_contract",
        "coverage",
        "failure_accounting",
        "safety_cost_delta",
        "strata",
        "components",
        "speed_sensitivity",
        "secondary",
        "additional_event_pairs",
        "candidate_selection",
        "latency",
        "latency_comparison_authorized",
        "latency_reporting_role",
        "evidence_guards",
        "claim_gate_result",
    }
)
SOURCE_SCHEDULE_TOP_LEVEL_KEYS = frozenset(
    {
        "pair_count",
        "unique_pair_count",
        "route_count",
        "seed_count_per_route",
        "seeds",
        "map_family_count",
        "corridor_group_count",
        "arm_order_counts",
        "arm_order_domain_separator",
        "deterministic_hash_rank_verified",
        "outcome_blind_preregistered_order_control_verified",
        "independent_reset_per_arm_verified",
        "latency_comparative_conclusion_authorized",
    }
)
SOURCE_PROVENANCE_TOP_LEVEL_KEYS = frozenset(
    {
        "live_camp_head",
        "execution_source_head",
        "execution_source_is_ancestor",
        "prior_gate_heads_are_execution_source_ancestors",
        "live_camp_tracked_clean",
        "fixed_dp_head",
        "fixed_dp_tracked_clean",
        "producer_blob_sha256",
        "config_blob_sha256",
        "expected_config_sha256",
        "evaluator_blob_sha256",
        "expected_evaluator_sha256",
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
SOURCE_ROOT_RECEIPT_KEYS = frozenset(
    {"label", "root", "root_sha256", "file_count", "manifest_paths"}
)
SOURCE_HOLDOUT_STATE_KEYS = frozenset(
    {
        "schema",
        "holdout_opened",
        "holdout_open_count",
        "rerun_authorized",
        "camp_head",
        "authorization_root_sha256",
        "preflight_root_sha256",
        "output_dir",
    }
)
SOURCE_LAUNCH_KEYS = frozenset(
    {
        "output_path_file",
        "state_path_file",
        "heads_file",
        "command_file",
        "stderr_bytes",
    }
)
SOURCE_RUNTIME_SELECTOR_KEYS = frozenset(
    {"weights_sha256", "atom_scales_sha256", "weights", "atom_scales"}
)
SOURCE_REQUEST_ASSET_KEYS = frozenset(
    {
        "fixed_dp_assets",
        "route_asset_count",
        "route_asset_sha256",
        "map_asset_count",
        "map_asset_sha256",
        "same_fixed_dp_request_all_pairs",
    }
)
SOURCE_ROUTE_BINDING_KEYS = frozenset(
    {
        "record_key",
        "identity_sha256",
        "logical_map_sha256",
        "map_family_id",
        "source_map_path",
        "source_map_sha256",
        "source_geometry_sha256",
        "route_serialization_sha256",
        "source_arc_length_m",
        "source_route_length_m",
        "corridor_group_sha256",
        "seeds",
    }
)
EXPECTED_SELECTED_INDEX_HISTOGRAM = {
    "0": 1401,
    "1": 913,
    "2": 894,
    "3": 900,
    "4": 909,
    "5": 824,
    "6": 923,
    "7": 916,
}
EXPECTED_TRAIN_SOURCE_COVERAGE = {
    "retained": 1875,
    "complete": 1054,
    "failed": 821,
    "failure_rate": 821 / 1875,
}
EXPECTED_LEARNING_CURVE_STABILITY = {
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
}
EXPECTED_RUNTIME_WEIGHTS = [
    4.652417726891036e-16,
    7.50590055534417e-16,
    7.450659655635859e-16,
    0.0,
    0.0,
    0.0,
    0.0,
    0.4178605234516141,
    0.5784894895043772,
    3.64204122511374e-16,
    6.233691611751105e-16,
    0.0,
    6.923211902627337e-16,
    0.0036499870440052018,
]
EXPECTED_RUNTIME_ATOM_SCALES = [
    2481.7550516727697,
    12392.161075623555,
    14971.368820214635,
    2.6449764764205814,
    112.10250469410671,
    143.20765397475728,
    178.29595558846955,
    226.1003046244964,
    4.4473526890636705,
    5.273085428042301,
    1e-06,
    1.4948622881714675,
    1e-06,
    1.804866652285605,
]
EXPECTED_RUNTIME_WEIGHTS_SHA256 = (
    "7ba2cfb2925ccbba8eca6effb2699cc8634b7990e01dff68f449c7fea9a8af9d"
)
EXPECTED_RUNTIME_ATOM_SCALES_SHA256 = (
    "7b720cbe244d24cc6ce5283fc4f269278d94ebc11bd3b5dd973920177f14440d"
)
EXPECTED_RUNTIME_SELECTOR_ROOT_SHA256 = (
    "94ea5ccaefa40eafdc99c8a4fae51f5e48f504f4fee69cd27ca3e18458d89f9a"
)
EXPECTED_TRAINING_ROOT_SHA256 = (
    "91ddd978d383d66488215e2fc8135dee37f4e3d40efb7f801389b40d6fb2c175"
)
EXPECTED_TRAINING_REVIEW_ROOT_SHA256 = (
    "0b2539ef6c8fa195dfefac6f330775cdc8cb6c0ec7a7ca3aec96d19d0e0b5e6c"
)
EXPECTED_FIXED_DP_ASSETS = {
    "fixed_dp_checkpoint": "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75",
    "fixed_dp_args_json": "42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa",
    "fixed_dp_source:scenario_generation/replay.py": "92158e32f8e2626a20aeee1783501d1afad228f06d5948f3426716d93320c5eb",
    "fixed_dp_source:scenario_generation/simulate.py": "de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e",
    "fixed_dp_source:scenario_generation/tensor_converter.py": "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7",
    "fixed_dp_source:scenario_generation/mpc_tracker.py": "bf2fdc6398898a42eda4ab3d12045c5204eb5ce8a993dbf96feee975de04395a",
    "fixed_dp_source:scenario_generation/traffic_light.py": "5a1659fe753102c514528c0bd93c261124bdf8de11bbc00ba5b941c151956af4",
}
CLAIM_DECISION_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "status",
        "decision",
        "final_claim_authorized",
        "derived_evidence_guards",
        "gates",
        "failed_gates",
        "claim_scope",
        "map_family_level_ci",
        "unseen_map_generalization",
        "native_ranked_k8_superiority",
        "latency_comparative_conclusion",
        "allowed_claim_text",
        "forbidden_claims",
        "source_reviewer_root_sha256",
        "guard_closure",
        "directional_safety_cost_summary",
    }
)
EVIDENCE_PACKAGE_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "status",
        "reviewer_root",
        "guard_closure",
        "live_authority",
        "live_holdout_once",
        "source_root_inventory",
        "transitive_source_roots_rehashed_by_this_gate",
        "transitive_source_roots_role",
        "repository_provenance",
        "reviewer_camp_head",
        "execution_source_head",
        "fixed_dp_head",
        "config_sha256",
        "evaluator_sha256",
        "evidence_limitations",
        "reviewed_metrics",
        "frozen_training_risk_disclosure",
        "evaluation_summary",
        "claim_decision",
        "latency_comparison_authorized",
        "latency_reporting_role",
        "reviewer_or_execution_rerun",
        "runner_built",
        "model_loaded",
        "simulator_executed",
        "holdout_reopened",
        "promotion_authorized",
        "deployment_authorized",
        "online_activation_authorized",
        "free_bytes_before_package",
        "final_post_publication_checks_required",
        "free_bytes_after_gate_recorded_in_return_and_launch_receipt",
        "next_work_target",
    }
)
EVIDENCE_STDOUT_KEYS = frozenset(
    {"status", "decision", "final_claim_authorized", "failed_gates", "next_work_target"}
)
EVIDENCE_REVIEWER_ROOT_KEYS = frozenset(
    {
        "path",
        "root_sha256",
        "file_count",
        "manifest_digests",
        "review_result_sha256",
        "recomputed_metrics_sha256",
        "complete_seal_rehashed_before_and_after",
        "source_bytes_unchanged",
    }
)
EVIDENCE_LIVE_AUTHORITY_KEYS = frozenset(
    {"fields", "audit_sha256", "current_status_sha256", "verified_before_and_after", "static_preflight"}
)
EVIDENCE_STATIC_PREFLIGHT_KEYS = frozenset(
    {"source_head", "path", "root_sha256", "file_count", "manifest_digests"}
)
BUILDER_AUTHORITY_FIELD_KEYS = frozenset(
    {
        "current_v24_status",
        "current_v24_artifact_source_head",
        "current_v24_final_synced_head",
        "current_v24_artifact",
        "current_v24_artifact_root_sha256",
        "current_v24_reviewer_artifact",
        "current_v24_reviewer_artifact_root_sha256",
        "current_v24_reviewer_source_head",
        "current_v24_holdout_state",
        "current_v24_holdout_state_sha256",
        "current_v24_holdout_open_count",
        "current_v24_holdout_rerun_authorized",
        "fixed_dp_head",
        "source_a_status",
        "source_a_terminal",
        "source_b_status",
        "source_b_terminal",
        "authorized_source_count",
        "source_terminal_count",
        "global_stop_authorized",
        "global_stop_reason",
        "next_work_target",
    }
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _require_sha256(value: Any, name: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return str(value)


def _require_git_oid(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or not set(value) <= HEX:
        raise ValueError(f"{name} must be a lowercase Git OID")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _require_finite_json(value: Any, name: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require_finite_json(item, f"{name}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_json(item, f"{name}[{index}]")


def _loads_json_bytes(value: bytes, name: str) -> Any:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8") from exc
    parsed = json.loads(
        text,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
    _require_finite_json(parsed, name)
    return parsed


def _write_json(path: Path, value: Any) -> None:
    Path(path).write_text(
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


def _canonical_json(value: Any, name: str) -> bytes:
    _require_finite_json(value, name)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _exact_int(value: Any, name: str, expected: int | None = None) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an exact integer")
    if expected is not None and value != expected:
        raise ValueError(f"{name} mismatch")
    return value


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _require_absolute_no_symlink_components(path: Path, *, label: str) -> Path:
    """Reject any symlink in an existing absolute path before path resolution."""

    raw = Path(path)
    if not raw.is_absolute() or not raw.anchor:
        raise ValueError(f"{label} path must be absolute")
    parts = raw.parts
    current = Path(raw.anchor)
    components = (current,)
    for part in parts[1:]:
        if part in {".", ".."}:
            raise ValueError(f"{label} path contains an unsafe component")
        current = current / part
        components += (current,)
    for index, component in enumerate(components):
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ValueError(
                f"{label} path component is missing or unreadable: {component}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} path contains a symlink component: {component}")
        if index < len(components) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(
                f"{label} non-leaf path component is not a directory: {component}"
            )
    return raw


def _verify_frozen_production_path_components() -> None:
    for path, label in (
        (CANONICAL_SOURCE_REVIEW_ROOT, "frozen source reviewer root"),
        (CANONICAL_EVIDENCE_ROOT, "frozen evidence root"),
        (CANONICAL_LAUNCH_ROOT, "frozen launch root"),
        (CANONICAL_CAMP_REPO, "canonical CAMP repo"),
        (CANONICAL_DP_REPO, "canonical DP repo"),
        (CANONICAL_HOLDOUT_STATE_PATH, "canonical holdout marker"),
        (GLOBAL_LOCK_PATH, "global lock"),
        (CANONICAL_OUTPUT_PARENT, "canonical output parent"),
    ):
        _require_absolute_no_symlink_components(path, label=label)


def verify_complete_seal(
    root: Path,
    expected_root_sha256: str,
    *,
    label: str,
    exact_manifest_paths: frozenset[str] | None = None,
) -> dict[str, Any]:
    raw_root = _require_absolute_no_symlink_components(
        Path(root), label=f"{label} artifact root"
    )
    root = raw_root.resolve()
    expected_root_sha256 = _require_sha256(
        expected_root_sha256, f"{label} expected root"
    )
    if not root.is_dir():
        raise ValueError(f"{label} artifact directory is missing")
    sums = root / "SHA256SUMS"
    root_sums = root / "ROOT_SHA256SUMS"
    if sums.is_symlink() or root_sums.is_symlink():
        raise ValueError(f"{label} seal must not contain symlinks")
    if not sums.is_file() or not root_sums.is_file():
        raise ValueError(f"{label} complete seal is missing")
    for seal_path in (sums, root_sums):
        metadata = os.lstat(seal_path)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError(f"{label} seal files must be unaliased regular files")
    manifest_bytes = sums.read_bytes()
    actual_root_sha256 = _sha256_bytes(manifest_bytes)
    if actual_root_sha256 != expected_root_sha256:
        raise ValueError(f"{label} root SHA256 mismatch")
    if root_sums.read_bytes() != (
        f"{actual_root_sha256}  SHA256SUMS\n".encode("ascii")
    ):
        raise ValueError(f"{label} ROOT_SHA256SUMS mismatch")
    try:
        manifest_text = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} SHA256SUMS is not valid UTF-8") from exc
    declared: dict[str, str] = {}
    for line_number, line in enumerate(manifest_text.splitlines(), start=1):
        if line.count("  ") != 1 or line != line.strip():
            raise ValueError(f"{label} malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        _require_sha256(digest, f"{label} manifest digest line {line_number}")
        pure = PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or pure.as_posix() != relative
            or relative in declared
            or relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ):
            raise ValueError(f"{label} unsafe or duplicate manifest path: {relative}")
        path = root.joinpath(*pure.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"{label} manifest file is missing or symlinked: {relative}")
        metadata = os.lstat(path)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError(
                f"{label} manifest file is not an unaliased regular file: {relative}"
            )
        if _sha256_file(path) != digest:
            raise ValueError(f"{label} manifest file SHA256 mismatch: {relative}")
        declared[relative] = digest
    actual_entries: set[str] = set()
    with os.scandir(root) as entries:
        for entry in entries:
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValueError(
                    f"{label} artifact tree cannot be inspected: {entry.name}"
                ) from exc
            if entry.is_symlink():
                raise ValueError(
                    f"{label} artifact contains a symlink: {entry.name}"
                )
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    f"{label} artifact contains a non-regular node: {entry.name}"
                )
            actual_entries.add(entry.name)
    expected_entries = set(declared) | {"SHA256SUMS", "ROOT_SHA256SUMS"}
    if actual_entries != expected_entries:
        raise ValueError(f"{label} seal has an inexact artifact tree")
    if exact_manifest_paths is not None and set(declared) != set(
        exact_manifest_paths
    ):
        raise ValueError(f"{label} manifest path set mismatch")
    return {
        "root": root,
        "root_sha256": actual_root_sha256,
        "file_count": len(declared),
        "manifest_digests": dict(sorted(declared.items())),
    }


def _read_verified_bytes(seal: Mapping[str, Any], relative: str, label: str) -> bytes:
    digests = _mapping(seal, "manifest_digests")
    expected = digests.get(relative)
    if not _is_sha256(expected):
        raise ValueError(f"{label} sealed file is not declared: {relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        raise ValueError(f"{label} unsafe sealed file path: {relative}")
    root = Path(str(seal.get("root")))
    path = root.joinpath(*pure.parts)
    _require_absolute_no_symlink_components(root, label=f"{label} sealed root")
    _require_absolute_no_symlink_components(path, label=f"{label} sealed file")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} sealed file is missing or symlinked: {relative}")
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ValueError(f"{label} sealed file is not an unaliased regular file: {relative}")
    value = path.read_bytes()
    if _sha256_bytes(value) != expected:
        raise ValueError(f"{label} sealed file changed before read: {relative}")
    return value


def _sealed_json(seal: Mapping[str, Any], relative: str, label: str) -> Mapping[str, Any]:
    value = _loads_json_bytes(_read_verified_bytes(seal, relative, label), f"{label} {relative}")
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} {relative} must contain a mapping")
    return value


def _seal_artifact(root: Path) -> str:
    root = Path(root)
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in files
    ]
    manifest = ("\n".join(lines) + "\n").encode("utf-8")
    (root / "SHA256SUMS").write_bytes(manifest)
    root_sha256 = _sha256_bytes(manifest)
    (root / "ROOT_SHA256SUMS").write_bytes(
        f"{root_sha256}  SHA256SUMS\n".encode("ascii")
    )
    return root_sha256


def _parse_heads(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("evidence HEADS.txt is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, item = line.partition("=")
        if not separator or not key or not item or key in result:
            raise ValueError("evidence HEADS.txt is malformed")
        result[key] = item
    expected = {
        "PACKAGE_CAMP_HEAD",
        "REVIEWER_CAMP_HEAD",
        "EXECUTION_SOURCE_HEAD",
        "FIXED_DP_HEAD",
        "REVIEWER_ROOT_SHA256",
        "CONFIG_SHA256",
        "EVALUATOR_SHA256",
    }
    if set(result) != expected:
        raise ValueError("evidence HEADS.txt key set mismatch")
    for key in ("PACKAGE_CAMP_HEAD", "REVIEWER_CAMP_HEAD", "EXECUTION_SOURCE_HEAD", "FIXED_DP_HEAD"):
        _require_git_oid(result[key], f"evidence HEADS {key}")
    for key in ("REVIEWER_ROOT_SHA256", "CONFIG_SHA256", "EVALUATOR_SHA256"):
        _require_sha256(result[key], f"evidence HEADS {key}")
    return result


def _parse_source_review_heads(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("source reviewer HEADS.txt is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, item = line.partition("=")
        if not separator or not key or not item or key in result:
            raise ValueError("source reviewer HEADS.txt is malformed")
        result[key] = item
    expected = {
        "CAMP_HEAD",
        "EXECUTION_SOURCE_HEAD",
        "PREFLIGHT_CAMP_HEAD",
        "PILOT_REVIEW_CAMP_HEAD",
        "PILOT_EXECUTION_SOURCE_HEAD",
        "FIXED_DP_HEAD",
    }
    if set(result) != expected:
        raise ValueError("source reviewer HEADS.txt key set mismatch")
    for key in expected:
        _require_git_oid(result[key], f"source reviewer HEADS {key}")
    return result


def _parse_launch_heads(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("launch HEADS.txt is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, item = line.partition("=")
        if not separator or not key or not item or key in result:
            raise ValueError("launch HEADS.txt is malformed")
        result[key] = item
    expected = {
        "PACKAGE_CAMP_HEAD",
        "REVIEWER_CAMP_HEAD",
        "EXECUTION_SOURCE_HEAD",
        "FIXED_DP_HEAD",
        "REVIEWER_ROOT_SHA256",
        "CONFIG_SHA256",
        "EVALUATOR_SHA256",
        "HOLDOUT_STATE_SHA256",
    }
    if set(result) != expected:
        raise ValueError("launch HEADS.txt key set mismatch")
    for key in (
        "PACKAGE_CAMP_HEAD",
        "REVIEWER_CAMP_HEAD",
        "EXECUTION_SOURCE_HEAD",
        "FIXED_DP_HEAD",
    ):
        _require_git_oid(result[key], f"launch HEADS {key}")
    for key in (
        "REVIEWER_ROOT_SHA256",
        "CONFIG_SHA256",
        "EVALUATOR_SHA256",
        "HOLDOUT_STATE_SHA256",
    ):
        _require_sha256(result[key], f"launch HEADS {key}")
    return result


def _parse_static_preflight_heads(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("static preflight HEADS.txt is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, item = line.partition("=")
        if not separator or not key or not item or key in result:
            raise ValueError("static preflight HEADS.txt is malformed")
        result[key] = item
    expected = {
        "IMPLEMENTATION_SOURCE_HEAD",
        "PACKAGE_CAMP_HEAD",
        "FIXED_DP_HEAD",
        "REVIEWER_SCRIPT_SHA256",
        "REVIEWER_TEST_SHA256",
    }
    if set(result) != expected:
        raise ValueError("static preflight HEADS.txt key set mismatch")
    for key in ("IMPLEMENTATION_SOURCE_HEAD", "PACKAGE_CAMP_HEAD", "FIXED_DP_HEAD"):
        _require_git_oid(result[key], f"static preflight HEADS {key}")
    for key in ("REVIEWER_SCRIPT_SHA256", "REVIEWER_TEST_SHA256"):
        _require_sha256(result[key], f"static preflight HEADS {key}")
    return result


def _validate_fixed_source_metrics(metrics: Mapping[str, Any]) -> None:
    if set(metrics) != SOURCE_METRIC_TOP_LEVEL_KEYS:
        raise ValueError("source reviewer metrics top-level key set mismatch")
    if metrics.get("schema") != "camp_dp_v24_holdout_main_independent_statistics_v1":
        raise ValueError("source reviewer metrics schema mismatch")
    if _mapping(metrics, "bootstrap_contract") != {
        "primary_hierarchy": [
            "corridor_group_sha256",
            "route_identity_sha256",
            "seed",
        ],
        "map_family_cluster_level_authorized": False,
        "resamples": 5000,
        "seed": 24047,
    }:
        raise ValueError("source reviewer bootstrap contract mismatch")
    coverage = _mapping(metrics, "coverage")
    for name, expected in {
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": 120,
        "source_invalid_pair_count": 0,
        "execution_invalid_pair_count": 0,
    }.items():
        _exact_int(coverage.get(name), f"coverage {name}", expected)
    for name, expected in {
        "retention_rate": 1.0,
        "paired_complete_rate": 1.0,
        "source_invalid_rate": 0.0,
        "execution_invalid_rate": 0.0,
    }.items():
        if _finite_number(coverage.get(name), f"coverage {name}") != expected:
            raise ValueError(f"coverage {name} mismatch")
    safety = _mapping(metrics, "safety_cost_delta")
    if (
        _finite_number(safety.get("mean"), "SafetyCost mean")
        != EXPECTED_MEAN_DELTA
        or _finite_number(safety.get("median"), "SafetyCost median") != 0.0
        or _finite_number(safety.get("ci95_low"), "SafetyCost CI95 low")
        != EXPECTED_CI95_LOW
        or _finite_number(safety.get("ci95_high"), "SafetyCost CI95 high")
        != EXPECTED_CI95_HIGH
        or dict(_mapping(safety, "better_tie_worse"))
        != EXPECTED_BETTER_TIE_WORSE
    ):
        raise ValueError("source reviewer fixed SafetyCost result mismatch")
    events = _mapping(metrics, "additional_event_pairs")
    if set(events) != set(MAJOR_EVENT_FIELDS) or any(
        type(events[name]) is not int or events[name] != 0
        for name in MAJOR_EVENT_FIELDS
    ):
        raise ValueError("source reviewer major-event result mismatch")
    if (
        metrics.get("latency_comparison_authorized") is not False
        or metrics.get("latency_reporting_role")
        != "descriptive_instrumented_only"
    ):
        raise ValueError("source reviewer latency scope mismatch")
    selection = _mapping(metrics, "candidate_selection")
    if set(selection) != {
        "camp_tick_count",
        "camp_selected_index_histogram",
        "candidate0_selection_count",
        "non_candidate0_selection_count",
        "all_k_high_risk_pair_count",
        "all_k_high_risk_tick_count",
    }:
        raise ValueError("source reviewer candidate-selection key set mismatch")
    for name, expected in {
        "camp_tick_count": 7680,
        "candidate0_selection_count": 1401,
        "non_candidate0_selection_count": 6279,
        "all_k_high_risk_pair_count": 8,
        "all_k_high_risk_tick_count": 36,
    }.items():
        _exact_int(selection.get(name), f"candidate selection {name}", expected)
    if (
        _mapping(selection, "camp_selected_index_histogram")
        != EXPECTED_SELECTED_INDEX_HISTOGRAM
    ):
        raise ValueError("source reviewer selected-index histogram mismatch")
    failure = _mapping(metrics, "failure_accounting")
    if (
        failure.get("dp_status") != {"ok": 120}
        or failure.get("camp_status") != {"ok": 120}
        or failure.get("failure_class") != {"None": 120}
        or failure.get("failed_pairs_dropped") is not False
        or failure.get("replacement_or_resampling_used") is not False
    ):
        raise ValueError("source reviewer failure accounting mismatch")


def _independently_recompute_claim(metrics: Mapping[str, Any]) -> dict[str, Any]:
    source_guards = _mapping(metrics, "evidence_guards")
    if set(source_guards) != set(EVIDENCE_GUARD_NAMES):
        raise ValueError("source reviewer evidence guard set mismatch")
    if source_guards.get("independent_review_passed") is not False:
        raise ValueError("source reviewer self-guard must remain false")
    if any(
        source_guards.get(name) is not True
        for name in EVIDENCE_GUARD_NAMES
        if name != "independent_review_passed"
    ):
        raise ValueError("source reviewer non-self evidence guard failed")
    derived_guards = dict(source_guards)
    derived_guards["independent_review_passed"] = True
    coverage = _mapping(metrics, "coverage")
    safety = _mapping(metrics, "safety_cost_delta")
    better_tie_worse = _mapping(safety, "better_tie_worse")
    events = _mapping(metrics, "additional_event_pairs")
    for name in ("better", "tie", "worse"):
        _exact_int(better_tie_worse.get(name), f"better/tie/worse {name}")
    for name in MAJOR_EVENT_FIELDS:
        _exact_int(events.get(name), f"additional event {name}")
    gates = {
        "retention_rate": _finite_number(coverage.get("retention_rate"), "retention rate") == 1.0,
        "paired_complete_rate": _finite_number(coverage.get("paired_complete_rate"), "paired complete rate") == 1.0,
        "source_invalid_rate": _finite_number(coverage.get("source_invalid_rate"), "source invalid rate") == 0.0,
        "execution_invalid_rate": _finite_number(coverage.get("execution_invalid_rate"), "execution invalid rate") == 0.0,
        "safety_cost_mean_delta_below_zero": _finite_number(safety.get("mean"), "SafetyCost mean delta") < 0.0,
        "clustered_ci95_upper_below_zero": _finite_number(safety.get("ci95_high"), "SafetyCost CI95 upper") < 0.0,
        "better_exceeds_worse": better_tie_worse["better"] > better_tie_worse["worse"],
        "no_additional_collision_pairs": events["collision_any"] == 0,
        "no_additional_offroad_pairs": events["offroad_rate"] == 0,
        "no_additional_red_light_pairs": events["red_light_violation_any"] == 0,
        "no_additional_wrong_way_pairs": events["wrong_way_rate"] == 0,
        "evidence_guards": all(value is True for value in derived_guards.values()),
    }
    if tuple(gates) != CLAIM_GATE_NAMES:
        raise AssertionError("independent claim gate order drift")
    failed = [name for name in CLAIM_GATE_NAMES if gates[name] is not True]
    return {
        "derived_evidence_guards": derived_guards,
        "gates": gates,
        "failed_gates": failed,
        "decision": "limited_claim_gates_passed" if not failed else "honest_no_claim",
        "final_claim_authorized": not failed,
    }


def _verify_static_preflight(
    seal: Mapping[str, Any],
    *,
    implementation_source_head: str,
    reviewer_script_sha256: str,
    reviewer_test_sha256: str,
) -> dict[str, Any]:
    result = _sealed_json(seal, "static_preflight.json", "static preflight")
    stdout = _sealed_json(seal, "stdout.txt", "static preflight")
    heads = _parse_static_preflight_heads(
        _read_verified_bytes(seal, "HEADS.txt", "static preflight")
    )
    expected_keys = {
        "schema",
        "status",
        "implementation_source_head",
        "package_camp_head",
        "fixed_dp_head",
        "reviewer_script_sha256",
        "reviewer_test_sha256",
        "preflight_scope",
        "real_artifacts_unopened",
        "consumed_artifact_roots",
        "operations",
        "checks",
        "failed_checks",
    }
    if set(result) != expected_keys:
        raise ValueError("static preflight JSON key set mismatch")
    checks = _mapping(result, "checks")
    operations = _mapping(result, "operations")
    if (
        result.get("schema") != STATIC_PREFLIGHT_SCHEMA
        or result.get("status") != "passed"
        or result.get("implementation_source_head")
        != implementation_source_head
        or result.get("package_camp_head") != PACKAGE_CAMP_HEAD
        or result.get("fixed_dp_head") != FIXED_DP_HEAD
        or result.get("reviewer_script_sha256") != reviewer_script_sha256
        or result.get("reviewer_test_sha256") != reviewer_test_sha256
        or result.get("preflight_scope") != "static_preflight_process_only"
        or result.get("real_artifacts_unopened") is not True
        or result.get("consumed_artifact_roots") != []
        or set(checks) != STATIC_PREFLIGHT_CHECK_NAMES
        or any(value is not True for value in checks.values())
        or result.get("failed_checks") != []
        or set(operations) != STATIC_PREFLIGHT_OPERATION_NAMES
        or any(value is not False for value in operations.values())
    ):
        raise ValueError("static preflight contract did not pass")
    if _canonical_json(stdout, "static preflight stdout") != _canonical_json(
        result, "static preflight result"
    ):
        raise ValueError("static preflight stdout differs from result")
    if heads != {
        "IMPLEMENTATION_SOURCE_HEAD": implementation_source_head,
        "PACKAGE_CAMP_HEAD": PACKAGE_CAMP_HEAD,
        "FIXED_DP_HEAD": FIXED_DP_HEAD,
        "REVIEWER_SCRIPT_SHA256": reviewer_script_sha256,
        "REVIEWER_TEST_SHA256": reviewer_test_sha256,
    }:
        raise ValueError("static preflight HEADS/code binding mismatch")
    for stem in ("py_compile", "pytest", "git_diff_check"):
        if _read_verified_bytes(seal, f"{stem}.exit", "static preflight") != b"0\n":
            raise ValueError(f"static preflight {stem} did not pass")
        if _read_verified_bytes(
            seal, f"{stem}.stderr.txt", "static preflight"
        ) != b"":
            raise ValueError(f"static preflight {stem} stderr is not empty")
    if _read_verified_bytes(seal, "run.exit", "static preflight") != b"0\n":
        raise ValueError("static preflight run.exit did not pass")
    if _read_verified_bytes(seal, "stderr.txt", "static preflight") != b"":
        raise ValueError("static preflight stderr is not empty")
    return {"result": result, "heads": heads}


def _validate_source_root_inventory(
    review: Mapping[str, Any],
) -> Mapping[str, Any]:
    roots = _mapping(review, "source_roots")
    if set(roots) != SOURCE_ROOT_NAMES:
        raise ValueError("source reviewer root inventory name set mismatch")
    for name in sorted(SOURCE_ROOT_NAMES):
        receipt = _mapping(roots, name)
        if set(receipt) != SOURCE_ROOT_RECEIPT_KEYS:
            raise ValueError(f"source reviewer {name} root receipt key set mismatch")
        root = receipt.get("root")
        if (
            receipt.get("label") != name
            or not isinstance(root, str)
            or not root.startswith("/")
            or not PurePosixPath(root).is_absolute()
        ):
            raise ValueError(f"source reviewer {name} root receipt mismatch")
        _require_sha256(receipt.get("root_sha256"), f"source {name} root")
        file_count = _exact_int(
            receipt.get("file_count"), f"source {name} file count"
        )
        manifest_paths = receipt.get("manifest_paths")
        if (
            file_count <= 0
            or not isinstance(manifest_paths, list)
            or len(manifest_paths) != file_count
            or any(not isinstance(relative, str) for relative in manifest_paths)
            or manifest_paths != sorted(set(manifest_paths))
        ):
            raise ValueError(f"source reviewer {name} manifest inventory mismatch")
        for relative in manifest_paths:
            pure = PurePosixPath(relative)
            if (
                not relative
                or pure.is_absolute()
                or ".." in pure.parts
                or "\\" in relative
                or pure.as_posix() != relative
            ):
                raise ValueError(f"source reviewer {name} manifest path is unsafe")
    if (
        _mapping(roots, "training").get("root_sha256")
        != EXPECTED_TRAINING_ROOT_SHA256
        or _mapping(roots, "training_review").get("root_sha256")
        != EXPECTED_TRAINING_REVIEW_ROOT_SHA256
        or _mapping(roots, "runtime_selector").get("root_sha256")
        != EXPECTED_RUNTIME_SELECTOR_ROOT_SHA256
        or _mapping(roots, "runtime_selector").get("file_count") != 2
        or _mapping(roots, "runtime_selector").get("manifest_paths")
        != ["atom_scales.json", "weights.npy"]
    ):
        raise ValueError("source reviewer training/runtime root binding mismatch")
    return roots


def _validate_source_holdout_state(
    review: Mapping[str, Any], roots: Mapping[str, Any]
) -> None:
    state = _mapping(review, "holdout_state")
    if set(state) != SOURCE_HOLDOUT_STATE_KEYS:
        raise ValueError("source reviewer holdout-state key set mismatch")
    authorization = _mapping(roots, "authorization")
    preflight = _mapping(roots, "preflight")
    execution = _mapping(roots, "execution")
    if (
        state.get("schema") != "camp_dp_v24_holdout_once_state_v1"
        or state.get("holdout_opened") is not True
        or state.get("holdout_open_count") != 1
        or state.get("rerun_authorized") is not False
        or state.get("camp_head") != EXECUTION_SOURCE_HEAD
        or state.get("authorization_root_sha256")
        != authorization.get("root_sha256")
        or state.get("preflight_root_sha256") != preflight.get("root_sha256")
        or state.get("output_dir") != execution.get("root")
        or review.get("holdout_open_count") != state.get("holdout_open_count")
        or review.get("preflight_config_sha256") != CONFIG_SHA256
    ):
        raise ValueError("source reviewer holdout-state/root binding mismatch")


def _validate_source_launch(review: Mapping[str, Any]) -> None:
    launch = _mapping(review, "launch")
    if set(launch) != SOURCE_LAUNCH_KEYS:
        raise ValueError("source reviewer launch key set mismatch")
    if (
        launch.get("output_path_file") not in {"OUTPUT_PATH", "OUTPUT_PATH.txt"}
        or launch.get("state_path_file") not in {"STATE_PATH", "STATE_PATH.txt"}
        or launch.get("heads_file") not in {"HEADS", "HEADS.txt"}
        or launch.get("command_file") not in {"COMMAND", "COMMAND.txt"}
        or _exact_int(launch.get("stderr_bytes"), "source launch stderr bytes")
        < 0
    ):
        raise ValueError("source reviewer launch receipt mismatch")


def _validate_source_runtime_selector(review: Mapping[str, Any]) -> list[float]:
    selector = _mapping(review, "runtime_selector")
    if set(selector) != SOURCE_RUNTIME_SELECTOR_KEYS:
        raise ValueError("source reviewer runtime-selector key set mismatch")
    if (
        selector.get("weights_sha256") != EXPECTED_RUNTIME_WEIGHTS_SHA256
        or selector.get("atom_scales_sha256")
        != EXPECTED_RUNTIME_ATOM_SCALES_SHA256
    ):
        raise ValueError("source reviewer runtime-selector SHA binding mismatch")
    weights = selector.get("weights")
    scales = selector.get("atom_scales")
    if (
        not isinstance(weights, list)
        or not isinstance(scales, list)
        or len(weights) != 14
        or len(scales) != 14
    ):
        raise ValueError("source reviewer runtime selector is not 14D")
    numeric_weights = [
        _finite_number(value, f"runtime selector weight {index}")
        for index, value in enumerate(weights)
    ]
    numeric_scales = [
        _finite_number(value, f"runtime selector scale {index}")
        for index, value in enumerate(scales)
    ]
    if (
        any(value < 0.0 for value in numeric_weights)
        or not math.isclose(sum(numeric_weights), 1.0, rel_tol=0.0, abs_tol=1e-12)
        or any(value <= 0.0 for value in numeric_scales)
        or numeric_weights != EXPECTED_RUNTIME_WEIGHTS
        or numeric_scales != EXPECTED_RUNTIME_ATOM_SCALES
    ):
        raise ValueError("source reviewer runtime selector violates simplex/scale contract")
    return numeric_weights


def _validate_source_request_assets(
    review: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    assets = _mapping(review, "request_assets")
    if set(assets) != SOURCE_REQUEST_ASSET_KEYS:
        raise ValueError("source reviewer request-asset key set mismatch")
    fixed_dp_assets = _mapping(assets, "fixed_dp_assets")
    if dict(fixed_dp_assets) != EXPECTED_FIXED_DP_ASSETS:
        raise ValueError("source reviewer fixed-DP asset inventory mismatch")
    route_assets = _mapping(assets, "route_asset_sha256")
    if (
        _exact_int(assets.get("route_asset_count"), "source route asset count")
        != 24
        or len(route_assets) != 24
        or any(not _is_sha256(identity) or not _is_sha256(digest) for identity, digest in route_assets.items())
    ):
        raise ValueError("source reviewer route-asset inventory mismatch")
    map_assets = _mapping(assets, "map_asset_sha256")
    map_count = _exact_int(assets.get("map_asset_count"), "source map asset count")
    if (
        map_count != 1
        or len(map_assets) != map_count
        or any(
            not isinstance(path, str)
            or not PurePosixPath(path).is_absolute()
            or not _is_sha256(digest)
            for path, digest in map_assets.items()
        )
        or assets.get("same_fixed_dp_request_all_pairs") is not True
    ):
        raise ValueError("source reviewer map/fixed-request asset inventory mismatch")
    return route_assets, map_assets


def _validate_source_route_bindings(
    review: Mapping[str, Any],
    route_assets: Mapping[str, Any],
    map_assets: Mapping[str, Any],
) -> None:
    bindings = _mapping(review, "route_source_bindings")
    if len(bindings) != 24 or set(bindings) != set(route_assets):
        raise ValueError("source reviewer route binding population mismatch")
    record_keys: set[str] = set()
    families: set[str] = set()
    corridors: set[str] = set()
    logical_maps: set[str] = set()
    source_map_paths: set[str] = set()
    for identity, raw in bindings.items():
        _require_sha256(identity, "source route binding identity key")
        binding = _mapping(bindings, identity)
        if set(binding) != SOURCE_ROUTE_BINDING_KEYS:
            raise ValueError("source reviewer route binding key set mismatch")
        record_key = binding.get("record_key")
        family = binding.get("map_family_id")
        source_map_path = binding.get("source_map_path")
        if (
            not isinstance(record_key, str)
            or not record_key
            or record_key in record_keys
            or not isinstance(family, str)
            or not family
            or not isinstance(source_map_path, str)
            or not PurePosixPath(source_map_path).is_absolute()
        ):
            raise ValueError("source reviewer route binding identity/path mismatch")
        logical_map = _require_sha256(
            binding.get("logical_map_sha256"), "source route logical map"
        )
        source_geometry = _require_sha256(
            binding.get("source_geometry_sha256"), "source route geometry"
        )
        expected_identity = _sha256_bytes(
            _canonical_json(
                {
                    "logical_map_sha256": logical_map,
                    "source_geometry_sha256": source_geometry,
                },
                "source route identity",
            )
        )
        source_map_sha256 = _require_sha256(
            binding.get("source_map_sha256"), "source route map"
        )
        _require_sha256(
            binding.get("route_serialization_sha256"), "source route serialization"
        )
        corridor = _require_sha256(
            binding.get("corridor_group_sha256"), "source route corridor"
        )
        arc_length = _finite_number(
            binding.get("source_arc_length_m"), "source route arc length"
        )
        route_length = _finite_number(
            binding.get("source_route_length_m"), "source route length"
        )
        if (
            binding.get("identity_sha256") != identity
            or expected_identity != identity
            or map_assets.get(source_map_path) != source_map_sha256
            or binding.get("seeds") != [24201, 24202, 24203, 24204, 24205]
            or arc_length <= 0.0
            or route_length <= 0.0
            or not math.isclose(arc_length, route_length, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise ValueError("source reviewer route source/hash/seed binding mismatch")
        record_keys.add(record_key)
        families.add(family)
        corridors.add(corridor)
        logical_maps.add(logical_map)
        source_map_paths.add(source_map_path)
    if (
        len(families) != 1
        or len(logical_maps) != 1
        or len(corridors) != 3
        or source_map_paths != set(map_assets)
    ):
        raise ValueError("source reviewer map-family/corridor binding mismatch")


def _validate_source_frozen_metric_contract(
    review: Mapping[str, Any], runtime_weights: Sequence[float]
) -> None:
    contract = _mapping(review, "frozen_metric_contract")
    if set(contract) != {
        "train_route_seed_source_coverage_disclosure",
        "learning_curve_stability",
        "distribution_concentration_risk_disclosed",
        "calibration_or_holdout_repair_authorized",
    }:
        raise ValueError("source reviewer frozen metric contract key set mismatch")
    if (
        contract.get("train_route_seed_source_coverage_disclosure")
        != EXPECTED_TRAIN_SOURCE_COVERAGE
        or contract.get("learning_curve_stability")
        != EXPECTED_LEARNING_CURVE_STABILITY
        or contract.get("distribution_concentration_risk_disclosed") is not True
        or contract.get("calibration_or_holdout_repair_authorized") is not False
    ):
        raise ValueError("source reviewer frozen metric/risk disclosure mismatch")
    stability = _mapping(contract, "learning_curve_stability")
    active_indices = stability.get("full_effective_support_indices")
    active_weights = stability.get("full_effective_support_weights")
    if (
        active_indices != [7, 8, 13]
        or active_weights
        != [runtime_weights[index] for index in active_indices]
        or [index for index, value in enumerate(runtime_weights) if value > 1e-6]
        != active_indices
        or review.get("preflight_config_sha256") != CONFIG_SHA256
    ):
        raise ValueError(
            "source reviewer runtime weights are not bound to frozen training risk/config"
        )


def _verify_source_review(
    seal: Mapping[str, Any], expected_root_sha256: str
) -> dict[str, Any]:
    review = _sealed_json(seal, "review_result.json", "source reviewer")
    metrics = _sealed_json(seal, "recomputed_metrics.json", "source reviewer")
    schedule = _sealed_json(seal, "schedule_receipt.json", "source reviewer")
    provenance = _sealed_json(seal, "provenance.json", "source reviewer")
    stdout = _sealed_json(seal, "stdout.txt", "source reviewer")
    heads = _parse_source_review_heads(
        _read_verified_bytes(seal, "HEADS.txt", "source reviewer")
    )
    checks = review.get("checks")
    if set(review) != SOURCE_REVIEW_TOP_LEVEL_KEYS:
        raise ValueError("source reviewer top-level key set mismatch")
    if set(schedule) != SOURCE_SCHEDULE_TOP_LEVEL_KEYS:
        raise ValueError("source reviewer schedule top-level key set mismatch")
    if set(provenance) != SOURCE_PROVENANCE_TOP_LEVEL_KEYS:
        raise ValueError("source reviewer provenance top-level key set mismatch")
    if (
        review.get("schema") != SOURCE_REVIEW_SCHEMA
        or review.get("status") != "passed"
        or type(review.get("check_count")) is not int
        or review.get("check_count") != EXPECTED_SOURCE_REVIEW_CHECK_COUNT
        or type(review.get("failed_count")) is not int
        or review.get("failed_count") != 0
        or review.get("failed_checks") != []
        or not isinstance(checks, Mapping)
        or set(checks) != EXPECTED_SOURCE_REVIEW_CHECK_NAMES
        or any(value is not True for value in checks.values())
    ):
        raise ValueError("source reviewer schema/status/check contract mismatch")
    roots = _validate_source_root_inventory(review)
    _validate_source_holdout_state(review, roots)
    _validate_source_launch(review)
    runtime_weights = _validate_source_runtime_selector(review)
    route_assets, map_assets = _validate_source_request_assets(review)
    _validate_source_route_bindings(review, route_assets, map_assets)
    _validate_source_frozen_metric_contract(review, runtime_weights)
    if _read_verified_bytes(seal, "run.exit", "source reviewer") != b"0\n":
        raise ValueError("source reviewer run.exit did not pass")
    if _read_verified_bytes(seal, "stderr.txt", "source reviewer") != b"":
        raise ValueError("source reviewer stderr is not empty")
    for embedded_name, standalone, label in (
        ("metrics", metrics, "metrics"),
        ("schedule", schedule, "schedule"),
        ("provenance", provenance, "provenance"),
    ):
        if _canonical_json(
            _mapping(review, embedded_name), f"source embedded {label}"
        ) != _canonical_json(standalone, f"source standalone {label}"):
            raise ValueError(
                f"source reviewer embedded and standalone {label} differ"
            )
    if _canonical_json(stdout, "source stdout") != _canonical_json(
        review, "source review result"
    ):
        raise ValueError("source reviewer stdout does not equal review_result")
    if (
        review.get("camp_head") != SOURCE_REVIEWER_CAMP_HEAD
        or review.get("execution_source_head") != EXECUTION_SOURCE_HEAD
        or review.get("fixed_dp_head") != FIXED_DP_HEAD
        or heads["CAMP_HEAD"] != SOURCE_REVIEWER_CAMP_HEAD
        or heads["EXECUTION_SOURCE_HEAD"] != EXECUTION_SOURCE_HEAD
        or heads["FIXED_DP_HEAD"] != FIXED_DP_HEAD
        or heads["PREFLIGHT_CAMP_HEAD"] != PREFLIGHT_CAMP_HEAD
        or review.get("preflight_camp_head") != PREFLIGHT_CAMP_HEAD
        or heads["PILOT_REVIEW_CAMP_HEAD"]
        != PILOT_REVIEW_CAMP_HEAD
        or review.get("pilot_review_camp_head") != PILOT_REVIEW_CAMP_HEAD
        or heads["PILOT_EXECUTION_SOURCE_HEAD"]
        != PILOT_EXECUTION_SOURCE_HEAD
        or review.get("pilot_execution_source_head")
        != PILOT_EXECUTION_SOURCE_HEAD
    ):
        raise ValueError("source reviewer HEAD provenance mismatch")
    if (
        provenance.get("live_camp_head") != SOURCE_REVIEWER_CAMP_HEAD
        or provenance.get("execution_source_head") != EXECUTION_SOURCE_HEAD
        or provenance.get("execution_source_is_ancestor") is not True
        or provenance.get("fixed_dp_head") != FIXED_DP_HEAD
        or provenance.get("live_camp_tracked_clean") is not True
        or provenance.get("fixed_dp_tracked_clean") is not True
        or provenance.get("config_blob_sha256") != CONFIG_SHA256
        or provenance.get("expected_config_sha256") != CONFIG_SHA256
        or provenance.get("evaluator_blob_sha256") != EVALUATOR_SHA256
        or provenance.get("expected_evaluator_sha256") != EVALUATOR_SHA256
    ):
        raise ValueError("source reviewer producer provenance mismatch")
    prior_ancestry = _mapping(
        provenance, "prior_gate_heads_are_execution_source_ancestors"
    )
    if set(prior_ancestry) != {
        "preflight_camp_head",
        "pilot_review_camp_head",
        "pilot_execution_source_head",
    } or any(value is not True for value in prior_ancestry.values()):
        raise ValueError("source reviewer prior-gate ancestry mismatch")
    handoff = _mapping(review, "claim_guard_handoff")
    if handoff != {
        "independent_review_passed": False,
        "status": "pending_separate_claim_decision_rehash_of_sealed_reviewer_root",
        "reviewer_self_authorization_forbidden": True,
    }:
        raise ValueError("source reviewer self-guard handoff mismatch")
    if (
        review.get("final_claim_authorized") is not False
        or review.get("latency_comparison_authorized") is not False
        or review.get("map_family_level_ci_authorized") is not False
        or review.get("unseen_map_generalization_authorized") is not False
        or review.get("native_ranked_k8_claim_authorized") is not False
        or review.get("holdout_open_count") != 1
        or review.get("next_work_target")
        != "v24_evidence_package_and_preregistered_claim_decision"
        or type(review.get("free_bytes_after_review")) is not int
        or review.get("free_bytes_after_review") <= MINIMUM_FREE_BYTES
        or any(
            review.get(name) is not False
            for name in SOURCE_REVIEW_FORBIDDEN_OPERATION_FIELDS
        )
    ):
        raise ValueError("source reviewer boundary mismatch")
    execution = _mapping(review, "execution")
    for name, expected in {
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": 120,
        "source_invalid_pair_count": 0,
        "execution_failure_pair_count": 0,
        "dp_tick_count": 7680,
        "camp_tick_count": 7680,
        "all_k_high_risk_tick_count": 36,
    }.items():
        _exact_int(execution.get(name), f"source execution {name}", expected)
    if schedule.get("pair_count") != 120 or schedule.get(
        "unique_pair_count"
    ) != 120 or schedule.get("route_count") != 24 or schedule.get(
        "seed_count_per_route"
    ) != 5 or schedule.get("seeds") != [
        24201,
        24202,
        24203,
        24204,
        24205,
    ] or schedule.get("map_family_count") != 1 or schedule.get(
        "corridor_group_count"
    ) != 3 or schedule.get("arm_order_counts") != {
        "dp_camp": 60,
        "camp_dp": 60,
    } or schedule.get(
        "arm_order_domain_separator"
    ) != "camp-v24-paired-arm-order-v1" or schedule.get(
        "deterministic_hash_rank_verified"
    ) is not True or schedule.get(
        "outcome_blind_preregistered_order_control_verified"
    ) is not True or schedule.get(
        "independent_reset_per_arm_verified"
    ) is not True or schedule.get(
        "latency_comparative_conclusion_authorized"
    ) is not False:
        raise ValueError("source reviewer schedule contract mismatch")
    limitations = _mapping(review, "evidence_limitations")
    if (
        limitations.get("raw_candidate_tensor_bytes_present") is not False
        or limitations.get("raw_atom_matrix_bytes_present") is not False
        or limitations.get("affine_score_receipt_consistency_verified") is not True
        or limitations.get("affine_scores_recomputed_from_raw_atoms") is not False
        or limitations.get("candidate_hashes_recomputed_from_raw_tensor_bytes") is not False
        or limitations.get("candidate_and_atom_hash_scope")
        != "complete_sealed_receipt_consistency_only"
        or limitations.get("raw_byte_proof_claimed") is not False
    ):
        raise ValueError("source reviewer raw-byte evidence limitation mismatch")
    _validate_fixed_source_metrics(metrics)
    derived = _independently_recompute_claim(metrics)
    source_gates = dict(_mapping(derived, "gates"))
    source_gates["evidence_guards"] = False
    source_failed = [
        name for name in CLAIM_GATE_NAMES if source_gates[name] is not True
    ]
    source_claim = _mapping(metrics, "claim_gate_result")
    if (
        source_claim.get("decision") != "honest_no_claim"
        or source_claim.get("final_claim_authorized") is not False
        or source_claim.get("gates") != source_gates
        or source_claim.get("failed_gates") != source_failed
        or source_claim.get("claim_scope")
        != "frozen_held_out_map_family_and_three_corridor_groups_only"
        or source_claim.get("map_family_level_ci") is not False
        or source_claim.get("unseen_map_generalization") is not False
        or source_claim.get("native_ranked_k8_superiority") is not False
        or source_claim.get("latency_comparative_conclusion") is not False
        or source_failed
        != ["clustered_ci95_upper_below_zero", "evidence_guards"]
        or derived["failed_gates"] != EXPECTED_FAILED_GATES
    ):
        raise ValueError("source reviewer preregistered claim contract mismatch")
    return {
        "review": review,
        "metrics": metrics,
        "metrics_bytes": _canonical_json(metrics, "source metrics"),
        "source_camp_head": SOURCE_REVIEWER_CAMP_HEAD,
        "execution_source_head": EXECUTION_SOURCE_HEAD,
        "config_sha256": CONFIG_SHA256,
        "evaluator_sha256": EVALUATOR_SHA256,
        "schedule": schedule,
        "provenance": provenance,
        "heads": heads,
        "limitations": dict(limitations),
        "derived_claim": derived,
        "root_sha256": expected_root_sha256,
    }


def _validate_evidence_live_authority(
    evidence: Mapping[str, Any], source_root_sha256: str
) -> None:
    live = _mapping(evidence, "live_authority")
    if set(live) != EVIDENCE_LIVE_AUTHORITY_KEYS:
        raise ValueError("evidence live-authority key set mismatch")
    fields = _mapping(live, "fields")
    if set(fields) != BUILDER_AUTHORITY_FIELD_KEYS:
        raise ValueError("evidence builder-authority field set mismatch")
    expected_fields = {
        "current_v24_status": BUILDER_AUTHORIZED_CURRENT_STATUS,
        "current_v24_artifact_source_head": BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD,
        "current_v24_final_synced_head": "pending_current_docs_commit_not_source_drift",
        "current_v24_artifact": BUILDER_STATIC_PREFLIGHT_PATH,
        "current_v24_artifact_root_sha256": BUILDER_STATIC_PREFLIGHT_ROOT_SHA256,
        "current_v24_reviewer_artifact": BUILDER_SOURCE_REVIEW_PATH,
        "current_v24_reviewer_artifact_root_sha256": source_root_sha256,
        "current_v24_reviewer_source_head": SOURCE_REVIEWER_CAMP_HEAD,
        "current_v24_holdout_state": CANONICAL_HOLDOUT_STATE_PATH.as_posix(),
        "current_v24_holdout_state_sha256": HOLDOUT_STATE_SHA256,
        "current_v24_holdout_open_count": "1",
        "current_v24_holdout_rerun_authorized": "false",
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_a_status": "source_ineligible_missing_authorized_build_prerequisites",
        "source_a_terminal": "true",
        "source_b_status": BUILDER_AUTHORIZED_SOURCE_B_STATUS,
        "source_b_terminal": "false",
        "authorized_source_count": "2",
        "source_terminal_count": "1",
        "global_stop_authorized": "false",
        "global_stop_reason": "none",
        "next_work_target": BUILDER_AUTHORIZED_NEXT_WORK_TARGET,
    }
    if dict(fields) != expected_fields:
        raise ValueError("evidence builder-authority values mismatch")
    if (
        not _is_sha256(live.get("audit_sha256"))
        or not _is_sha256(live.get("current_status_sha256"))
        or live.get("verified_before_and_after") is not True
    ):
        raise ValueError("evidence live-authority digest/verification mismatch")
    static = _mapping(live, "static_preflight")
    manifests = _mapping(static, "manifest_digests")
    if (
        set(static) != EVIDENCE_STATIC_PREFLIGHT_KEYS
        or static.get("source_head") != BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD
        or static.get("path") != BUILDER_STATIC_PREFLIGHT_PATH
        or static.get("root_sha256") != BUILDER_STATIC_PREFLIGHT_ROOT_SHA256
        or static.get("file_count") != 16
        or len(manifests) != 16
        or any(
            not isinstance(path, str)
            or not path
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
            or "\\" in path
            or not _is_sha256(digest)
            for path, digest in manifests.items()
        )
    ):
        raise ValueError("evidence builder static-preflight binding mismatch")


def _verify_evidence(
    seal: Mapping[str, Any], source: Mapping[str, Any], source_root: Path
) -> dict[str, Any]:
    source_root = _require_absolute_no_symlink_components(
        Path(source_root), label="source reviewer root"
    )
    claim = _sealed_json(seal, "claim_decision.json", "evidence")
    evidence = _sealed_json(seal, "evidence_package.json", "evidence")
    stdout = _sealed_json(seal, "stdout.txt", "evidence")
    source_root_sha256 = str(source["root_sha256"])
    derived = _mapping(source, "derived_claim")
    if set(claim) != CLAIM_DECISION_TOP_LEVEL_KEYS:
        raise ValueError("evidence claim-decision top-level key set mismatch")
    if set(evidence) != EVIDENCE_PACKAGE_TOP_LEVEL_KEYS:
        raise ValueError("evidence package top-level key set mismatch")
    if (
        claim.get("schema") != CLAIM_SCHEMA
        or claim.get("status") != "passed_honest_no_claim"
        or claim.get("decision") != "honest_no_claim"
        or claim.get("final_claim_authorized") is not False
        or claim.get("failed_gates") != EXPECTED_FAILED_GATES
        or claim.get("source_reviewer_root_sha256") != source_root_sha256
    ):
        raise ValueError("evidence claim decision mismatch")
    if (
        claim.get("claim_scope")
        != "frozen_held_out_map_family_and_three_corridor_groups_only"
        or claim.get("map_family_level_ci") is not False
        or claim.get("unseen_map_generalization") is not False
        or claim.get("native_ranked_k8_superiority") is not False
        or claim.get("latency_comparative_conclusion") is not False
        or claim.get("allowed_claim_text") != ALLOWED_CLAIM_TEXT
        or claim.get("forbidden_claims") != list(FORBIDDEN_CLAIMS)
    ):
        raise ValueError("evidence claim scope or forbidden-claim boundary mismatch")
    if _canonical_json(
        _mapping(claim, "derived_evidence_guards"), "claim derived guards"
    ) != _canonical_json(
        _mapping(derived, "derived_evidence_guards"), "independent derived guards"
    ):
        raise ValueError("evidence derived guard path mismatch")
    if claim["derived_evidence_guards"].get("independent_review_passed") is not True:
        raise ValueError("evidence derived independent-review guard is not closed")
    if _canonical_json(_mapping(claim, "gates"), "claim gates") != _canonical_json(
        _mapping(derived, "gates"), "independent claim gates"
    ):
        raise ValueError("evidence claim gates differ from independent recomputation")
    if claim["gates"].get("evidence_guards") is not True:
        raise ValueError("evidence aggregate guard gate is not true")
    false_gates = [
        name for name, passed in claim["gates"].items() if passed is not True
    ]
    if false_gates != EXPECTED_FAILED_GATES:
        raise ValueError("evidence does not have the unique expected failed gate")
    guard_closure = _mapping(claim, "guard_closure")
    expected_closure = {
        "source_reviewer_root_sha256": source_root_sha256,
        "source_self_guard": False,
        "derived_independent_review_passed": True,
        "authority": "external_complete_seal_rehash_of_reviewer_root",
        "source_reviewer_json_modified": False,
        "only_guard_changed": "independent_review_passed",
    }
    if guard_closure != expected_closure:
        raise ValueError("evidence guard closure mismatch")
    directional = _mapping(claim, "directional_safety_cost_summary")
    if directional != {
        "mean_delta": EXPECTED_MEAN_DELTA,
        "ci95": [EXPECTED_CI95_LOW, EXPECTED_CI95_HIGH],
        "better_tie_worse": EXPECTED_BETTER_TIE_WORSE,
        "additional_major_event_pairs": {name: 0 for name in MAJOR_EVENT_FIELDS},
    }:
        raise ValueError("evidence directional SafetyCost summary mismatch")
    if evidence.get("schema") != EVIDENCE_SCHEMA or evidence.get("status") != "passed":
        raise ValueError("evidence package schema or status mismatch")
    reviewer_root = _mapping(evidence, "reviewer_root")
    if (
        set(reviewer_root) != EVIDENCE_REVIEWER_ROOT_KEYS
        or reviewer_root.get("path") != BUILDER_SOURCE_REVIEW_PATH
        or Path(str(reviewer_root.get("path"))) != Path(source_root)
        or reviewer_root.get("root_sha256") != source_root_sha256
        or reviewer_root.get("file_count") != len(SOURCE_REVIEW_PAYLOAD_PATHS)
        or reviewer_root.get("manifest_digests")
        != seal_from_source(source).get("manifest_digests")
        or reviewer_root.get("review_result_sha256")
        != seal_from_source(source)["manifest_digests"]["review_result.json"]
        or reviewer_root.get("recomputed_metrics_sha256")
        != seal_from_source(source)["manifest_digests"]["recomputed_metrics.json"]
        or reviewer_root.get("source_bytes_unchanged") is not True
        or reviewer_root.get("complete_seal_rehashed_before_and_after") is not True
    ):
        raise ValueError("evidence source-reviewer receipt mismatch")
    if _mapping(evidence, "guard_closure") != expected_closure:
        raise ValueError("evidence package guard closure mismatch")
    _validate_evidence_live_authority(evidence, source_root_sha256)
    if _canonical_json(
        _mapping(evidence, "source_root_inventory"),
        "evidence source-root inventory",
    ) != _canonical_json(
        _mapping(_mapping(source, "review"), "source_roots"),
        "source reviewer root inventory",
    ):
        raise ValueError("evidence source-root inventory differs from reviewer")
    if _canonical_json(
        _mapping(evidence, "reviewed_metrics"), "evidence reviewed metrics"
    ) != source["metrics_bytes"]:
        raise ValueError("evidence reviewed_metrics differ from source reviewer")
    if _mapping(evidence, "claim_decision") != {
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "failed_gates": EXPECTED_FAILED_GATES,
    }:
        raise ValueError("evidence package claim summary mismatch")
    if _canonical_json(
        _mapping(evidence, "frozen_training_risk_disclosure"),
        "evidence frozen training risk",
    ) != _canonical_json(
        _mapping(_mapping(source, "review"), "frozen_metric_contract"),
        "source frozen training risk",
    ):
        raise ValueError("evidence frozen training-risk disclosure mismatch")
    if _mapping(evidence, "evaluation_summary") != {
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
    }:
        raise ValueError("evidence evaluation summary mismatch")
    limitations = _mapping(evidence, "evidence_limitations")
    if (
        _canonical_json(limitations, "evidence limitations")
        != _canonical_json(source["limitations"], "source limitations")
        or evidence.get("transitive_source_roots_rehashed_by_this_gate") is not False
        or evidence.get("transitive_source_roots_role")
        != "inventory_from_complete_sealed_independent_reviewer"
    ):
        raise ValueError("evidence package upgraded its evidence limitations")
    if (
        evidence.get("reviewer_camp_head") != source["source_camp_head"]
        or evidence.get("execution_source_head") != EXECUTION_SOURCE_HEAD
        or evidence.get("config_sha256") != CONFIG_SHA256
        or evidence.get("evaluator_sha256") != EVALUATOR_SHA256
        or evidence.get("fixed_dp_head") != FIXED_DP_HEAD
        or any(evidence.get(name) is not False for name in FORBIDDEN_OPERATION_FIELDS)
        or evidence.get("promotion_authorized") is not False
        or evidence.get("deployment_authorized") is not False
        or evidence.get("online_activation_authorized") is not False
        or evidence.get("latency_comparison_authorized") is not False
        or evidence.get("latency_reporting_role")
        != "descriptive_instrumented_only"
        or type(evidence.get("free_bytes_before_package")) is not int
        or evidence.get("free_bytes_before_package") <= MINIMUM_FREE_BYTES
        or evidence.get("final_post_publication_checks_required") is not True
        or evidence.get("free_bytes_after_gate_recorded_in_return_and_launch_receipt")
        is not True
        or evidence.get("next_work_target") != EXPECTED_BUILDER_NEXT_WORK_TARGET
    ):
        raise ValueError("evidence package execution or claim boundary mismatch")
    repository = _mapping(evidence, "repository_provenance")
    if (
        set(repository)
        != {
            "package_camp_head",
            "camp_origin_main",
            "camp_remote_main",
            "camp_branch",
            "camp_origin_url",
            "review_camp_head_is_ancestor",
            "execution_source_is_review_ancestor",
            "camp_tracked_clean",
            "fixed_dp_head",
            "fixed_dp_tracked_clean",
            "static_preflight_source_head",
            "static_preflight_source_is_package_ancestor",
        }
        or repository.get("package_camp_head") != PACKAGE_CAMP_HEAD
        or repository.get("camp_origin_main") != PACKAGE_CAMP_HEAD
        or repository.get("camp_remote_main") != PACKAGE_CAMP_HEAD
        or repository.get("camp_tracked_clean") is not True
        or repository.get("camp_branch") != "main"
        or repository.get("camp_origin_url") != CANONICAL_ORIGIN_URL
        or repository.get("review_camp_head_is_ancestor") is not True
        or repository.get("execution_source_is_review_ancestor") is not True
        or repository.get("fixed_dp_head") != FIXED_DP_HEAD
        or repository.get("fixed_dp_tracked_clean") is not True
        or repository.get("static_preflight_source_head")
        != BUILDER_STATIC_PREFLIGHT_SOURCE_HEAD
        or repository.get("static_preflight_source_is_package_ancestor") is not True
    ):
        raise ValueError("evidence repository provenance mismatch")
    heads = _parse_heads(_read_verified_bytes(seal, "HEADS.txt", "evidence"))
    if (
        heads["PACKAGE_CAMP_HEAD"] != PACKAGE_CAMP_HEAD
        or heads["REVIEWER_CAMP_HEAD"] != source["source_camp_head"]
        or heads["EXECUTION_SOURCE_HEAD"] != EXECUTION_SOURCE_HEAD
        or heads["FIXED_DP_HEAD"] != FIXED_DP_HEAD
        or heads["REVIEWER_ROOT_SHA256"] != source_root_sha256
        or heads["CONFIG_SHA256"] != CONFIG_SHA256
        or heads["EVALUATOR_SHA256"] != EVALUATOR_SHA256
    ):
        raise ValueError("evidence HEADS provenance mismatch")
    if _read_verified_bytes(seal, "run.exit", "evidence") != b"0\n":
        raise ValueError("evidence builder exit is not zero")
    if _read_verified_bytes(seal, "stderr.txt", "evidence") != b"":
        raise ValueError("evidence builder stderr is not empty")
    expected_stdout = {
        "status": "passed",
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "failed_gates": EXPECTED_FAILED_GATES,
        "next_work_target": EXPECTED_BUILDER_NEXT_WORK_TARGET,
    }
    if set(stdout) != EVIDENCE_STDOUT_KEYS or dict(stdout) != expected_stdout:
        raise ValueError("evidence builder stdout contract mismatch")
    return {
        "claim": claim,
        "evidence": evidence,
        "heads": heads,
        "live_holdout_once": _mapping(evidence, "live_holdout_once"),
    }


def seal_from_source(source: Mapping[str, Any]) -> Mapping[str, Any]:
    seal = source.get("seal")
    if not isinstance(seal, Mapping):
        raise ValueError("source reviewer seal receipt is missing")
    return seal


def _verify_launch(
    seal: Mapping[str, Any],
    evidence_root: Path,
    evidence_root_sha256: str,
    source: Mapping[str, Any],
) -> Mapping[str, Any]:
    evidence_root = _require_absolute_no_symlink_components(
        Path(evidence_root), label="evidence root"
    )
    receipt = _sealed_json(seal, "launch_receipt.json", "launch")
    stdout = _sealed_json(seal, "stdout.txt", "launch")
    heads = _parse_launch_heads(_read_verified_bytes(seal, "HEADS.txt", "launch"))
    expected_keys = {
        "schema",
        "status",
        "builder_exit",
        "builder_stderr_empty",
        "config_sha256",
        "decision",
        "duration_s",
        "evaluator_sha256",
        "execution_source_head",
        "failed_gates",
        "final_claim_authorized",
        "final_post_publication_checks_passed",
        "fixed_dp_head",
        "free_bytes_after",
        "global_lock_free_after",
        "holdout_open_count",
        "holdout_reopened",
        "holdout_rerun_authorized",
        "holdout_state_sha256",
        "marker_unchanged",
        "model_loaded",
        "next_work_target",
        "output_dir",
        "output_exists",
        "output_file_count",
        "output_root_sha256",
        "package_camp_head",
        "related_process_count_after",
        "reviewer_camp_head",
        "reviewer_or_execution_rerun",
        "reviewer_root_sha256",
        "runner_built",
        "simulator_executed",
        "validation_error",
    }
    if set(receipt) != expected_keys:
        raise ValueError("launch receipt key set is not the frozen real wrapper schema")
    expected = {
        "schema": LAUNCH_SCHEMA,
        "status": "failed_closed",
        "builder_exit": 0,
        "builder_stderr_empty": True,
        "output_dir": Path(evidence_root).resolve().as_posix(),
        "output_exists": True,
        "output_file_count": len(EVIDENCE_PAYLOAD_PATHS),
        "output_root_sha256": evidence_root_sha256,
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "failed_gates": EXPECTED_FAILED_GATES,
        "final_post_publication_checks_passed": True,
        "validation_error": EXPECTED_WRAPPER_VALIDATION_ERROR,
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
        "config_sha256": CONFIG_SHA256,
        "evaluator_sha256": EVALUATOR_SHA256,
        "execution_source_head": EXECUTION_SOURCE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "holdout_state_sha256": HOLDOUT_STATE_SHA256,
        "next_work_target": EXPECTED_LAUNCH_NEXT_WORK_TARGET,
        "package_camp_head": PACKAGE_CAMP_HEAD,
        "reviewer_camp_head": SOURCE_REVIEWER_CAMP_HEAD,
        "reviewer_root_sha256": source["root_sha256"],
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("launch receipt is not the exact frozen wrapper false-negative")
    if _finite_number(receipt.get("duration_s"), "launch duration") <= 0.0:
        raise ValueError("launch duration must be finite and positive")
    if (
        type(receipt.get("free_bytes_after")) is not int
        or receipt["free_bytes_after"] <= MINIMUM_FREE_BYTES
    ):
        raise ValueError("launch receipt violates the 10 GiB disk floor")
    if _read_verified_bytes(seal, "run.exit", "launch") != b"0\n":
        raise ValueError("launch run.exit does not preserve builder success")
    if _read_verified_bytes(seal, "stderr.txt", "launch") != b"":
        raise ValueError("launch stderr must remain empty for builder success")
    expected_stdout_keys = {
        "status",
        "decision",
        "final_claim_authorized",
        "output_dir",
        "root_sha256",
        "free_bytes_after_gate",
        "final_post_publication_checks_passed",
        "next_work_target",
    }
    if set(stdout) != expected_stdout_keys or any(
        stdout.get(key) != value
        for key, value in {
            "status": "passed",
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "output_dir": Path(evidence_root).resolve().as_posix(),
            "root_sha256": evidence_root_sha256,
            "final_post_publication_checks_passed": True,
            "next_work_target": EXPECTED_BUILDER_NEXT_WORK_TARGET,
        }.items()
    ):
        raise ValueError("launch stdout is not the exact builder-success return")
    if (
        type(stdout.get("free_bytes_after_gate")) is not int
        or stdout["free_bytes_after_gate"] <= MINIMUM_FREE_BYTES
    ):
        raise ValueError("launch builder stdout violates the 10 GiB disk floor")
    expected_heads = {
        "PACKAGE_CAMP_HEAD": PACKAGE_CAMP_HEAD,
        "REVIEWER_CAMP_HEAD": SOURCE_REVIEWER_CAMP_HEAD,
        "EXECUTION_SOURCE_HEAD": EXECUTION_SOURCE_HEAD,
        "FIXED_DP_HEAD": FIXED_DP_HEAD,
        "REVIEWER_ROOT_SHA256": source["root_sha256"],
        "CONFIG_SHA256": CONFIG_SHA256,
        "EVALUATOR_SHA256": EVALUATOR_SHA256,
        "HOLDOUT_STATE_SHA256": HOLDOUT_STATE_SHA256,
    }
    if heads != expected_heads:
        raise ValueError("launch HEADS receipt is not cross-bound to frozen sources")
    return receipt


def _final_receipt_from_text(value: bytes, name: str) -> dict[str, str]:
    try:
        lines = value.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8") from exc
    while lines and not lines[-1].strip():
        lines.pop()
    pattern = re.compile(r"^([a-z0-9_]+)=(.+)$")
    result: dict[str, str] = {}
    for line in reversed(lines):
        match = pattern.fullmatch(line)
        if match is None:
            break
        key, item = match.groups()
        if key in result:
            raise ValueError(f"{name} final receipt has a duplicate field: {key}")
        result[key] = item
    if not result:
        raise ValueError(f"{name} has no final authority receipt")
    return result


def _current_v24_receipt(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("current status is not valid UTF-8") from exc
    start_marker = "## Current V24 Status"
    end_marker = "## Current V23 Status"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise ValueError("current status v24 named-section markers mismatch")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    if end <= start:
        raise ValueError("current status v24 named section is malformed")
    return _final_receipt_from_text(
        text[start:end].encode("utf-8"), "current status v24 section"
    )


def _git_text(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_bytes(repo: Path, object_name: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", object_name],
        check=True,
        capture_output=True,
    ).stdout


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        capture_output=True,
    ).returncode == 0


def _verify_repositories(
    camp_repo: Path,
    package_camp_head: str,
    authority_source_head: str,
    expected_current_camp_head: str,
    dp_repo: Path,
    expected_dp_head: str,
    source_reviewer_head: str,
    implementation_source_head: str,
    reviewer_script_sha256: str,
    reviewer_test_sha256: str,
) -> dict[str, Any]:
    if package_camp_head != PACKAGE_CAMP_HEAD:
        raise ValueError("package CAMP head differs from frozen f5907606 head")
    if expected_dp_head != FIXED_DP_HEAD:
        raise ValueError("expected DP head differs from the fixed DP commit")
    authority_source_head = _require_git_oid(authority_source_head, "authority source head")
    expected_current_camp_head = _require_git_oid(
        expected_current_camp_head, "current CAMP head"
    )
    implementation_source_head = _require_git_oid(
        implementation_source_head, "reviewer implementation source head"
    )
    reviewer_script_sha256 = _require_sha256(
        reviewer_script_sha256, "reviewer script"
    )
    reviewer_test_sha256 = _require_sha256(
        reviewer_test_sha256, "reviewer test"
    )
    if authority_source_head != expected_current_camp_head:
        raise ValueError("authority source head must equal the current CAMP head")
    raw_camp_repo = _require_absolute_no_symlink_components(
        Path(camp_repo), label="CAMP repo"
    )
    raw_dp_repo = _require_absolute_no_symlink_components(
        Path(dp_repo), label="fixed DP repo"
    )
    canonical_camp_repo = _require_absolute_no_symlink_components(
        CANONICAL_CAMP_REPO, label="canonical CAMP repo"
    )
    canonical_dp_repo = _require_absolute_no_symlink_components(
        CANONICAL_DP_REPO, label="canonical fixed DP repo"
    )
    camp_repo = raw_camp_repo.resolve()
    dp_repo = raw_dp_repo.resolve()
    if camp_repo != canonical_camp_repo.resolve():
        raise ValueError("CAMP repo path is not canonical")
    if dp_repo != canonical_dp_repo.resolve():
        raise ValueError("DP repo path is not canonical")
    camp_top_level = _require_absolute_no_symlink_components(
        Path(_git_text(camp_repo, "rev-parse", "--show-toplevel")),
        label="reported CAMP Git top-level",
    )
    dp_top_level = _require_absolute_no_symlink_components(
        Path(_git_text(dp_repo, "rev-parse", "--show-toplevel")),
        label="reported fixed DP Git top-level",
    )
    if camp_top_level.resolve() != camp_repo:
        raise ValueError("CAMP repo is not its canonical Git top-level")
    if dp_top_level.resolve() != dp_repo:
        raise ValueError("DP repo is not its canonical Git top-level")
    camp_head = _git_text(camp_repo, "rev-parse", "HEAD")
    origin_main = _git_text(camp_repo, "rev-parse", "origin/main")
    branch = _git_text(camp_repo, "symbolic-ref", "--short", "HEAD")
    origin_url = _git_text(camp_repo, "remote", "get-url", "origin")
    remote_main = _git_text(camp_repo, "ls-remote", "origin", "refs/heads/main")
    camp_status = _git_text(camp_repo, "status", "--porcelain", "--untracked-files=no")
    dp_head = _git_text(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_text(dp_repo, "status", "--porcelain", "--untracked-files=no")
    if (
        camp_head != expected_current_camp_head
        or origin_main != expected_current_camp_head
        or branch != "main"
        or origin_url != CANONICAL_ORIGIN_URL
        or remote_main != f"{expected_current_camp_head}\trefs/heads/main"
        or camp_status
    ):
        raise ValueError("live CAMP HEAD/origin/remote/branch/tracked state mismatch")
    if dp_head != FIXED_DP_HEAD or dp_status:
        raise ValueError("live fixed DP HEAD or tracked state mismatch")
    for head, label in (
        (PACKAGE_CAMP_HEAD, "package CAMP head"),
        (authority_source_head, "authority source head"),
        (source_reviewer_head, "source reviewer CAMP head"),
        (implementation_source_head, "reviewer implementation source head"),
    ):
        if _git_text(camp_repo, "cat-file", "-t", head) != "commit":
            raise ValueError(f"{label} is not a commit")
    if (
        not _git_is_ancestor(camp_repo, source_reviewer_head, PACKAGE_CAMP_HEAD)
        or not _git_is_ancestor(
            camp_repo, PACKAGE_CAMP_HEAD, implementation_source_head
        )
        or not _git_is_ancestor(
            camp_repo, implementation_source_head, expected_current_camp_head
        )
    ):
        raise ValueError("CAMP source/package/implementation/current ancestry mismatch")
    script_blob = _git_bytes(
        camp_repo,
        f"{implementation_source_head}:{REVIEWER_SCRIPT_RELATIVE_PATH.as_posix()}",
    )
    test_blob = _git_bytes(
        camp_repo,
        f"{implementation_source_head}:{REVIEWER_TEST_RELATIVE_PATH.as_posix()}",
    )
    live_script_path = _require_absolute_no_symlink_components(
        camp_repo / REVIEWER_SCRIPT_RELATIVE_PATH, label="live reviewer script"
    )
    live_test_path = _require_absolute_no_symlink_components(
        camp_repo / REVIEWER_TEST_RELATIVE_PATH, label="live reviewer test"
    )
    live_script = live_script_path.read_bytes()
    live_test = live_test_path.read_bytes()
    if (
        script_blob != live_script
        or test_blob != live_test
        or _sha256_bytes(script_blob) != reviewer_script_sha256
        or _sha256_bytes(test_blob) != reviewer_test_sha256
    ):
        raise ValueError("reviewer implementation source blobs differ from live code")
    return {
        "package_camp_head": PACKAGE_CAMP_HEAD,
        "authority_source_head": authority_source_head,
        "implementation_source_head": implementation_source_head,
        "reviewer_script_sha256": reviewer_script_sha256,
        "reviewer_test_sha256": reviewer_test_sha256,
        "current_camp_head": camp_head,
        "camp_origin_main": origin_main,
        "camp_remote_main": expected_current_camp_head,
        "camp_branch": branch,
        "camp_origin_url": origin_url,
        "camp_tracked_clean": True,
        "source_reviewer_is_package_ancestor": True,
        "package_is_implementation_ancestor": True,
        "implementation_is_current_ancestor": True,
        "authority_equals_current": True,
        "fixed_dp_head": dp_head,
        "fixed_dp_tracked_clean": True,
    }


def _verify_live_authority(
    camp_repo: Path,
    authority_source_head: str,
    *,
    evidence_root: Path,
    evidence_root_sha256: str,
    launch_root: Path,
    launch_root_sha256: str,
    source_review_root: Path,
    source_review_root_sha256: str,
    source_reviewer_head: str,
    static_preflight_root: Path,
    static_preflight_root_sha256: str,
    implementation_source_head: str,
    reviewer_script_sha256: str,
    reviewer_test_sha256: str,
    holdout_state_path: Path,
    holdout_state_sha256: str,
) -> dict[str, Any]:
    raw_camp_repo = _require_absolute_no_symlink_components(
        Path(camp_repo), label="live authority CAMP repo"
    )
    camp_repo = raw_camp_repo.resolve()
    audit_path = _require_absolute_no_symlink_components(
        camp_repo / AUDIT_RELATIVE_PATH, label="live v24 audit"
    )
    status_path = _require_absolute_no_symlink_components(
        camp_repo / CURRENT_STATUS_RELATIVE_PATH, label="live current status"
    )
    authority_paths = {
        "evidence": _require_absolute_no_symlink_components(
            Path(evidence_root), label="live authority evidence root"
        ),
        "launch": _require_absolute_no_symlink_components(
            Path(launch_root), label="live authority launch root"
        ),
        "source_reviewer": _require_absolute_no_symlink_components(
            Path(source_review_root), label="live authority source reviewer root"
        ),
        "static_preflight": _require_absolute_no_symlink_components(
            Path(static_preflight_root), label="live authority static preflight root"
        ),
        "holdout": _require_absolute_no_symlink_components(
            Path(holdout_state_path), label="live authority holdout marker"
        ),
    }
    if (
        audit_path.is_symlink()
        or status_path.is_symlink()
        or not audit_path.is_file()
        or not status_path.is_file()
    ):
        raise ValueError("live v24 authority files are missing or symlinked")
    audit_bytes = audit_path.read_bytes()
    status_bytes = status_path.read_bytes()
    if (
        audit_bytes
        != _git_bytes(
            camp_repo, f"{authority_source_head}:{AUDIT_RELATIVE_PATH.as_posix()}"
        )
        or status_bytes
        != _git_bytes(
            camp_repo,
            f"{authority_source_head}:{CURRENT_STATUS_RELATIVE_PATH.as_posix()}",
        )
    ):
        raise ValueError("live v24 authority bytes differ from authority source commit")
    audit = _final_receipt_from_text(audit_bytes, "live v24 audit EOF")
    status = _current_v24_receipt(status_bytes)
    if audit != status:
        raise ValueError("audit EOF and current-status v24 authority receipts differ")
    if not AUTHORITY_REQUIRED_FIELDS <= set(audit):
        raise ValueError("live v24 authority required field is missing")
    expected = {
        "current_v24_status": AUTHORIZED_CURRENT_STATUS,
        "current_v24_artifact_source_head": PACKAGE_CAMP_HEAD,
        "current_v24_artifact": authority_paths["evidence"].resolve().as_posix(),
        "current_v24_artifact_root_sha256": evidence_root_sha256,
        "current_v24_launch_artifact": authority_paths["launch"].resolve().as_posix(),
        "current_v24_launch_artifact_root_sha256": launch_root_sha256,
        "current_v24_launch_status": AUTHORIZED_LAUNCH_STATUS,
        "current_v24_reviewer_artifact": authority_paths[
            "source_reviewer"
        ].resolve().as_posix(),
        "current_v24_reviewer_artifact_root_sha256": source_review_root_sha256,
        "current_v24_reviewer_source_head": source_reviewer_head,
        "current_v24_independent_review_source_head": implementation_source_head,
        "current_v24_independent_review_script_sha256": reviewer_script_sha256,
        "current_v24_independent_review_test_sha256": reviewer_test_sha256,
        "current_v24_independent_review_static_artifact": authority_paths[
            "static_preflight"
        ].resolve().as_posix(),
        "current_v24_independent_review_static_artifact_root_sha256": (
            static_preflight_root_sha256
        ),
        "current_v24_holdout_state": authority_paths["holdout"].resolve().as_posix(),
        "current_v24_holdout_state_sha256": holdout_state_sha256,
        "current_v24_holdout_open_count": "1",
        "current_v24_holdout_rerun_authorized": "false",
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_a_status": AUTHORIZED_SOURCE_A_STATUS,
        "source_b_status": AUTHORIZED_SOURCE_B_STATUS,
        "next_work_target": AUTHORIZED_NEXT_WORK_TARGET,
    }
    if any(audit.get(key) != value for key, value in expected.items()):
        raise ValueError("live v24 authority binding mismatch")
    if (
        audit["source_a_terminal"] != "true"
        or audit["source_b_terminal"] != "false"
        or audit["authorized_source_count"] != "2"
        or audit["source_terminal_count"] != "1"
        or audit["global_stop_authorized"] != "false"
        or audit["global_stop_reason"] != "none"
    ):
        raise ValueError("live v24 source/global authority control mismatch")
    return {
        "fields": audit,
        "audit_sha256": _sha256_bytes(audit_bytes),
        "current_status_sha256": _sha256_bytes(status_bytes),
        "audit_bytes": audit_bytes,
        "current_status_bytes": status_bytes,
    }


def _verify_holdout_marker(
    path: Path,
    evidence_receipt: Mapping[str, Any],
    source_state: Mapping[str, Any],
) -> dict[str, Any]:
    raw = _require_absolute_no_symlink_components(
        Path(path), label="holdout marker"
    )
    canonical = _require_absolute_no_symlink_components(
        CANONICAL_HOLDOUT_STATE_PATH, label="canonical holdout marker"
    )
    if raw.resolve() != canonical.resolve():
        raise ValueError("holdout marker path is not canonical")
    if raw.is_symlink() or not raw.is_file():
        raise ValueError("holdout marker is missing or symlinked")
    value = raw.read_bytes()
    sha256 = _sha256_bytes(value)
    if (
        sha256 != HOLDOUT_STATE_SHA256
        or evidence_receipt.get("path") != raw.resolve().as_posix()
        or evidence_receipt.get("sha256") != sha256
        or evidence_receipt.get("open_count") != 1
        or evidence_receipt.get("rerun_authorized") is not False
        or evidence_receipt.get("marker_bytes_unchanged_before_and_after") is not True
        or evidence_receipt.get("global_lock_exclusively_held_by_this_gate") is not True
        or evidence_receipt.get("active_evaluator_or_reviewer_process_count") != 0
    ):
        raise ValueError("evidence holdout marker receipt mismatch")
    state = _loads_json_bytes(value, "live holdout marker")
    if not isinstance(state, Mapping):
        raise ValueError("live holdout marker must be a mapping")
    if _canonical_json(state, "live holdout marker") != _canonical_json(
        source_state, "source reviewer holdout state"
    ):
        raise ValueError("live holdout marker differs from source reviewer state")
    if (
        state.get("schema") != "camp_dp_v24_holdout_once_state_v1"
        or state.get("holdout_opened") is not True
        or state.get("holdout_open_count") != 1
        or state.get("rerun_authorized") is not False
    ):
        raise ValueError("live holdout marker contract mismatch")
    return {"path": raw.resolve().as_posix(), "sha256": sha256, "bytes": value}


def _proc_ancestor_pids(proc_root: Path, current_pid: int) -> set[int]:
    ancestors: set[int] = set()
    pid = current_pid
    while pid > 0 and pid not in ancestors:
        ancestors.add(pid)
        stat_path = proc_root / str(pid) / "stat"
        try:
            stat = stat_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError("cannot inspect current process ancestry") from exc
        right = stat.rfind(")")
        fields = stat[right + 2 :].split() if right >= 0 else []
        if len(fields) < 2:
            raise RuntimeError("cannot parse current process ancestry")
        try:
            parent = int(fields[1])
        except ValueError as exc:
            raise RuntimeError("cannot parse current process ancestry") from exc
        if parent == pid:
            break
        pid = parent
    return ancestors


def _active_v24_processes(
    *, proc_root: Path = Path("/proc"), current_pid: int | None = None
) -> list[int]:
    proc = Path(proc_root)
    if not proc.is_dir():
        raise RuntimeError("/proc is required for fail-closed process inspection")
    current = os.getpid() if current_pid is None else current_pid
    excluded = _proc_ancestor_pids(proc, current)
    active: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) in excluded:
            continue
        try:
            command_bytes = (entry / "cmdline").read_bytes()
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as exc:
            raise RuntimeError(
                f"cannot inspect non-ancestor process cmdline: {entry.name}"
            ) from exc
        command = command_bytes.replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        )
        if any(token in command for token in FORBIDDEN_LIVE_PROCESS_TOKENS):
            active.append(int(entry.name))
    return sorted(active)


@contextlib.contextmanager
def _exclusive_global_lock(path: Path):
    path = _require_absolute_no_symlink_components(
        Path(path), label="global lock"
    )
    canonical_lock = _require_absolute_no_symlink_components(
        GLOBAL_LOCK_PATH, label="canonical global lock"
    )
    if path.resolve() != canonical_lock.resolve():
        raise ValueError("global lock path is not canonical")
    if path.is_symlink() or not path.is_file():
        raise ValueError("global lock sentinel is missing or symlinked")
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - AutoDL is Linux
        raise RuntimeError("fcntl is required for the v24 global lock") from exc
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("v24 global lock is already held") from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _expected_output_path(
    expected_current_camp_head: str, expected_evidence_root_sha256: str
) -> Path:
    current_head = _require_git_oid(
        expected_current_camp_head, "current CAMP head"
    )
    evidence_sha256 = _require_sha256(
        expected_evidence_root_sha256, "evidence root"
    )
    output_parent = _require_absolute_no_symlink_components(
        CANONICAL_OUTPUT_PARENT, label="canonical output parent"
    )
    return output_parent.resolve() / (
        f"{OUTPUT_NAME_PREFIX}{current_head}_{evidence_sha256}"
    )


def _verify_output_isolation(
    output: Path,
    staging: Path,
    *,
    protected_paths: Sequence[Path],
) -> None:
    if not output.is_absolute() or not staging.is_absolute():
        raise ValueError("output and staging paths must be absolute")
    output_parent = _require_absolute_no_symlink_components(
        output.parent, label="output parent"
    )
    canonical_output_parent = _require_absolute_no_symlink_components(
        CANONICAL_OUTPUT_PARENT, label="canonical output parent"
    )
    if output_parent.is_symlink() or not output_parent.is_dir():
        raise ValueError("output parent directory is missing or symlinked")
    if output_parent.resolve() != canonical_output_parent.resolve():
        raise ValueError("output must be a direct child of the canonical artifact root")
    if not output.name.startswith(OUTPUT_NAME_PREFIX):
        raise ValueError("output artifact name prefix mismatch")
    candidates = (output.resolve(), staging.resolve())
    protected = tuple(
        _require_absolute_no_symlink_components(
            Path(path), label="protected review path"
        ).resolve()
        for path in protected_paths
    )
    if candidates[0] == candidates[1]:
        raise ValueError("output and staging paths collide")
    for candidate in candidates:
        for boundary in protected:
            if (
                candidate == boundary
                or boundary in candidate.parents
                or candidate in boundary.parents
            ):
                raise ValueError("output/staging path is not isolated")


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    directories = [Path(root)]
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("review staging artifact contains a symlink")
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    for directory in reversed(directories):
        _fsync_directory(directory)


def _directory_identity(path: Path, *, label: str) -> tuple[int, int]:
    raw = Path(path)
    try:
        metadata = os.lstat(raw)
    except FileNotFoundError as exc:
        raise ValueError(f"{label} directory disappeared") from exc
    if raw.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{label} is not an owned regular directory")
    return metadata.st_dev, metadata.st_ino


def _remove_owned_tree(path: Path, identity: tuple[int, int] | None) -> bool:
    """Remove only the directory inode created by this process.

    This deliberately leaves a path in place if another actor has replaced it.
    """

    if identity is None:
        return False
    raw = Path(path)
    try:
        current = _directory_identity(raw, label="cleanup candidate")
    except (FileNotFoundError, ValueError):
        return False
    if current != identity:
        return False
    shutil.rmtree(raw)
    return True


def _rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RuntimeError("renameat2(RENAME_NOREPLACE) is required")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100, os.fsencode(source), -100, os.fsencode(destination), 1
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise FileExistsError(destination)
    raise OSError(error, os.strerror(error), destination)


def _same_source_seals(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> bool:
    return all(
        before[name]["root_sha256"] == after[name]["root_sha256"]
        and before[name]["manifest_digests"] == after[name]["manifest_digests"]
        for name in before
    )


def _review_locked(
    *,
    evidence_root: Path,
    expected_evidence_root_sha256: str,
    launch_root: Path,
    expected_launch_root_sha256: str,
    source_review_root: Path,
    expected_source_review_root_sha256: str,
    static_preflight_root: Path,
    expected_static_preflight_root_sha256: str,
    implementation_source_head: str,
    expected_reviewer_script_sha256: str,
    expected_reviewer_test_sha256: str,
    camp_repo: Path,
    package_camp_head: str,
    authority_source_head: str,
    expected_current_camp_head: str,
    dp_repo: Path,
    expected_dp_head: str,
    holdout_state_path: Path,
    output_dir: Path,
    command: Sequence[str] | None,
    minimum_free_bytes: int,
) -> dict[str, Any]:
    raw_evidence_root = Path(evidence_root)
    raw_launch_root = Path(launch_root)
    raw_source_review_root = Path(source_review_root)
    raw_static_preflight_root = Path(static_preflight_root)
    for raw, label in (
        (raw_evidence_root, "evidence"),
        (raw_launch_root, "launch"),
        (raw_source_review_root, "source reviewer"),
        (raw_static_preflight_root, "static preflight"),
    ):
        _require_absolute_no_symlink_components(
            raw, label=f"{label} artifact root"
        )
    evidence_root = raw_evidence_root.resolve()
    launch_root = raw_launch_root.resolve()
    source_review_root = raw_source_review_root.resolve()
    static_preflight_root = raw_static_preflight_root.resolve()
    output = Path(output_dir)
    expected_output = _expected_output_path(
        expected_current_camp_head, expected_evidence_root_sha256
    )
    if not output.is_absolute() or output.resolve() != expected_output:
        raise ValueError("output path is not the deterministic independent-review path")
    staging = output.with_name(output.name + ".tmp")
    _verify_output_isolation(
        output,
        staging,
        protected_paths=(
            evidence_root,
            launch_root,
            source_review_root,
            static_preflight_root,
            Path(camp_repo),
            Path(dp_repo),
            Path(holdout_state_path),
            GLOBAL_LOCK_PATH,
        ),
    )
    if (
        output.exists()
        or output.is_symlink()
        or staging.exists()
        or staging.is_symlink()
    ):
        raise FileExistsError(
            output if output.exists() or output.is_symlink() else staging
        )
    source_seals = {
        "static_preflight": verify_complete_seal(
            static_preflight_root,
            expected_static_preflight_root_sha256,
            label="static preflight",
            exact_manifest_paths=STATIC_PREFLIGHT_PAYLOAD_PATHS,
        ),
        "evidence": verify_complete_seal(
            evidence_root,
            expected_evidence_root_sha256,
            label="evidence",
            exact_manifest_paths=EVIDENCE_PAYLOAD_PATHS,
        ),
        "launch": verify_complete_seal(
            launch_root,
            expected_launch_root_sha256,
            label="launch",
            exact_manifest_paths=LAUNCH_PAYLOAD_PATHS,
        ),
        "source_reviewer": verify_complete_seal(
            source_review_root,
            expected_source_review_root_sha256,
            label="source reviewer",
            exact_manifest_paths=SOURCE_REVIEW_PAYLOAD_PATHS,
        ),
    }
    static_preflight = _verify_static_preflight(
        source_seals["static_preflight"],
        implementation_source_head=implementation_source_head,
        reviewer_script_sha256=expected_reviewer_script_sha256,
        reviewer_test_sha256=expected_reviewer_test_sha256,
    )
    source = _verify_source_review(
        source_seals["source_reviewer"], expected_source_review_root_sha256
    )
    source["seal"] = source_seals["source_reviewer"]
    evidence = _verify_evidence(source_seals["evidence"], source, source_review_root)
    launch = _verify_launch(
        source_seals["launch"],
        evidence_root,
        expected_evidence_root_sha256,
        source,
    )
    source_state = _mapping(_mapping(source, "review"), "holdout_state")
    marker_before = _verify_holdout_marker(
        Path(holdout_state_path), evidence["live_holdout_once"], source_state
    )
    repository_before = _verify_repositories(
        Path(camp_repo),
        package_camp_head,
        authority_source_head,
        expected_current_camp_head,
        Path(dp_repo),
        expected_dp_head,
        str(source["source_camp_head"]),
        implementation_source_head,
        expected_reviewer_script_sha256,
        expected_reviewer_test_sha256,
    )
    authority_before = _verify_live_authority(
        Path(camp_repo),
        authority_source_head,
        evidence_root=evidence_root,
        evidence_root_sha256=expected_evidence_root_sha256,
        launch_root=launch_root,
        launch_root_sha256=expected_launch_root_sha256,
        source_review_root=source_review_root,
        source_review_root_sha256=expected_source_review_root_sha256,
        source_reviewer_head=str(source["source_camp_head"]),
        static_preflight_root=static_preflight_root,
        static_preflight_root_sha256=expected_static_preflight_root_sha256,
        implementation_source_head=implementation_source_head,
        reviewer_script_sha256=expected_reviewer_script_sha256,
        reviewer_test_sha256=expected_reviewer_test_sha256,
        holdout_state_path=Path(holdout_state_path),
        holdout_state_sha256=marker_before["sha256"],
    )
    active = _active_v24_processes()
    if active:
        raise ValueError("a v24 evaluator/runner/reviewer process is active")
    free_bytes_before = shutil.disk_usage(output.parent).free
    if free_bytes_before <= minimum_free_bytes:
        raise ValueError("independent review violates the 10 GiB disk floor")
    checks = {name: True for name in REVIEW_CHECK_NAMES}
    staging.mkdir()
    staging_identity = _directory_identity(staging, label="review staging")
    published_identity: tuple[int, int] | None = None
    published = False
    try:
        review_result = {
            "schema": REVIEW_SCHEMA,
            "status": "passed",
            "classification": "launch_wrapper_validation_false_negative",
            "builder_succeeded": True,
            "sealed_output_authoritative": True,
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "failed_gates": EXPECTED_FAILED_GATES,
            "checks": checks,
            "check_count": len(checks),
            "failed_checks": [],
            "claim_guard_path_verified": "derived_evidence_guards.independent_review_passed",
            "aggregate_guard_gate_path_verified": "gates.evidence_guards",
            "guard_closure_verified": True,
            "claim_independently_recomputed_from_source_reviewer_metrics": True,
            "source_metrics_deep_equal": True,
            "source_complete_seals_rehashed": {
                name: {
                    "root_sha256": receipt["root_sha256"],
                    "file_count": receipt["file_count"],
                    "manifest_digests": receipt["manifest_digests"],
                }
                for name, receipt in source_seals.items()
            },
            "launch_wrapper": {
                "schema": launch["schema"],
                "status": launch["status"],
                "builder_exit": launch["builder_exit"],
                "validation_error": launch["validation_error"],
                "classification": "exact_old_guard_path_validation_false_negative",
                "status_does_not_override_sealed_output": True,
                "global_lock_free_after_inconclusive": True,
                "global_lock_independently_acquired_by_this_review": True,
            },
            "live_authority": {
                "fields": authority_before["fields"],
                "audit_sha256": authority_before["audit_sha256"],
                "current_status_sha256": authority_before["current_status_sha256"],
                "authority_source_head": authority_source_head,
            },
            "repository_provenance": repository_before,
            "static_preflight": {
                "path": static_preflight_root.as_posix(),
                "root_sha256": expected_static_preflight_root_sha256,
                "implementation_source_head": implementation_source_head,
                "reviewer_script_sha256": expected_reviewer_script_sha256,
                "reviewer_test_sha256": expected_reviewer_test_sha256,
                "preflight_scope": static_preflight["result"]["preflight_scope"],
                "consumed_artifact_roots": [],
            },
            "holdout_marker": {
                "path": marker_before["path"],
                "sha256": marker_before["sha256"],
                "open_count": 1,
                "rerun_authorized": False,
                "bytes_unchanged": True,
            },
            "evidence_limitations": source["limitations"],
            "transitive_source_roots_rehashed_by_this_review": False,
            "raw_candidate_or_atom_bytes_recomputed_by_this_review": False,
            "operations": {
                "evaluator_executed": False,
                "runner_built": False,
                "model_loaded": False,
                "simulator_executed": False,
                "holdout_reopened": False,
            },
            "promotion_authorized": False,
            "deployment_authorized": False,
            "online_activation_authorized": False,
            "latency_comparison_authorized": False,
            "source_bytes_unchanged": True,
            "final_post_publication_checks_required": True,
            "next_work_target": "v24_honest_no_claim_record_only_closeout",
        }
        provenance = {
            "package_camp_head": PACKAGE_CAMP_HEAD,
            "authority_source_head": authority_source_head,
            "reviewer_source_head": expected_current_camp_head,
            "source_reviewer_camp_head": source["source_camp_head"],
            "fixed_dp_head": FIXED_DP_HEAD,
            "evidence_root": evidence_root.as_posix(),
            "evidence_root_sha256": expected_evidence_root_sha256,
            "launch_root": launch_root.as_posix(),
            "launch_root_sha256": expected_launch_root_sha256,
            "source_reviewer_root": source_review_root.as_posix(),
            "source_reviewer_root_sha256": expected_source_review_root_sha256,
            "static_preflight_root": static_preflight_root.as_posix(),
            "static_preflight_root_sha256": expected_static_preflight_root_sha256,
            "implementation_source_head": implementation_source_head,
            "reviewer_script_sha256": expected_reviewer_script_sha256,
            "reviewer_test_sha256": expected_reviewer_test_sha256,
        }
        _write_json(staging / "review_result.json", review_result)
        _write_json(staging / "provenance.json", provenance)
        (staging / "summary.md").write_text(
            "# v24 evidence-package and claim-decision independent review\n\n"
            "- Status: `passed`.\n"
            "- Builder result: sealed output is valid and authoritative.\n"
            "- Launch wrapper result: exact guard-path validation false-negative.\n"
            "- Claim decision remains `honest_no_claim`; the unique failed gate is "
            "`clustered_ci95_upper_below_zero`.\n"
            "- No evaluator, runner, model, simulator, holdout reopen, promotion, or "
            "deployment action was performed.\n",
            encoding="utf-8",
        )
        (staging / "HEADS.txt").write_text(
            f"PACKAGE_CAMP_HEAD={PACKAGE_CAMP_HEAD}\n"
            f"AUTHORITY_SOURCE_HEAD={authority_source_head}\n"
            f"REVIEWER_SOURCE_HEAD={expected_current_camp_head}\n"
            f"IMPLEMENTATION_SOURCE_HEAD={implementation_source_head}\n"
            f"SOURCE_REVIEWER_CAMP_HEAD={source['source_camp_head']}\n"
            f"EXECUTION_SOURCE_HEAD={EXECUTION_SOURCE_HEAD}\n"
            f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
            f"REVIEWER_SCRIPT_SHA256={expected_reviewer_script_sha256}\n"
            f"REVIEWER_TEST_SHA256={expected_reviewer_test_sha256}\n"
            f"CONFIG_SHA256={CONFIG_SHA256}\n"
            f"EVALUATOR_SHA256={EVALUATOR_SHA256}\n"
            f"HOLDOUT_STATE_SHA256={HOLDOUT_STATE_SHA256}\n"
            f"EVIDENCE_ROOT_SHA256={expected_evidence_root_sha256}\n"
            f"LAUNCH_ROOT_SHA256={expected_launch_root_sha256}\n"
            f"SOURCE_REVIEWER_ROOT_SHA256={expected_source_review_root_sha256}\n"
            f"STATIC_PREFLIGHT_ROOT_SHA256={expected_static_preflight_root_sha256}\n",
            encoding="ascii",
        )
        rendered_command = list(command) if command is not None else list(sys.argv)
        (staging / "COMMAND.txt").write_text(
            " ".join(str(item) for item in rendered_command) + "\n", encoding="utf-8"
        )
        stdout = {
            "status": "passed",
            "classification": "launch_wrapper_validation_false_negative",
            "builder_succeeded": True,
            "sealed_output_authoritative": True,
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "failed_gates": EXPECTED_FAILED_GATES,
            "check_count": len(checks),
            "next_work_target": "v24_honest_no_claim_record_only_closeout",
        }
        _write_json(staging / "stdout.txt", stdout)
        (staging / "stderr.txt").write_bytes(b"")
        (staging / "run.exit").write_bytes(b"0\n")

        repository_after = _verify_repositories(
            Path(camp_repo),
            package_camp_head,
            authority_source_head,
            expected_current_camp_head,
            Path(dp_repo),
            expected_dp_head,
            str(source["source_camp_head"]),
            implementation_source_head,
            expected_reviewer_script_sha256,
            expected_reviewer_test_sha256,
        )
        if repository_after != repository_before:
            raise ValueError("repository provenance changed during independent review")
        authority_after = _verify_live_authority(
            Path(camp_repo),
            authority_source_head,
            evidence_root=evidence_root,
            evidence_root_sha256=expected_evidence_root_sha256,
            launch_root=launch_root,
            launch_root_sha256=expected_launch_root_sha256,
            source_review_root=source_review_root,
            source_review_root_sha256=expected_source_review_root_sha256,
            source_reviewer_head=str(source["source_camp_head"]),
            static_preflight_root=static_preflight_root,
            static_preflight_root_sha256=expected_static_preflight_root_sha256,
            implementation_source_head=implementation_source_head,
            reviewer_script_sha256=expected_reviewer_script_sha256,
            reviewer_test_sha256=expected_reviewer_test_sha256,
            holdout_state_path=Path(holdout_state_path),
            holdout_state_sha256=marker_before["sha256"],
        )
        if (
            authority_after["audit_bytes"] != authority_before["audit_bytes"]
            or authority_after["current_status_bytes"]
            != authority_before["current_status_bytes"]
        ):
            raise ValueError("live authority changed during independent review")
        marker_after = _verify_holdout_marker(
            Path(holdout_state_path), evidence["live_holdout_once"], source_state
        )
        if marker_after["bytes"] != marker_before["bytes"]:
            raise ValueError("holdout marker changed during independent review")
        if _active_v24_processes():
            raise ValueError("a v24 evaluator/runner/reviewer process started")
        source_after = {
            "static_preflight": verify_complete_seal(
                static_preflight_root,
                expected_static_preflight_root_sha256,
                label="static preflight",
                exact_manifest_paths=STATIC_PREFLIGHT_PAYLOAD_PATHS,
            ),
            "evidence": verify_complete_seal(
                evidence_root,
                expected_evidence_root_sha256,
                label="evidence",
                exact_manifest_paths=EVIDENCE_PAYLOAD_PATHS,
            ),
            "launch": verify_complete_seal(
                launch_root,
                expected_launch_root_sha256,
                label="launch",
                exact_manifest_paths=LAUNCH_PAYLOAD_PATHS,
            ),
            "source_reviewer": verify_complete_seal(
                source_review_root,
                expected_source_review_root_sha256,
                label="source reviewer",
                exact_manifest_paths=SOURCE_REVIEW_PAYLOAD_PATHS,
            ),
        }
        if not _same_source_seals(source_seals, source_after):
            raise ValueError("a sealed source changed during independent review")
        output_root_sha256 = _seal_artifact(staging)
        staged_seal = verify_complete_seal(
            staging,
            output_root_sha256,
            label="review",
            exact_manifest_paths=REVIEW_PAYLOAD_PATHS,
        )
        _fsync_tree(staging)
        _rename_noreplace(staging, output)
        published = True
        published_identity = staging_identity
        if _directory_identity(output, label="published review") != published_identity:
            raise ValueError("published review inode differs from owned staging inode")
        _fsync_directory(output.parent)
        final_seal = verify_complete_seal(
            output,
            output_root_sha256,
            label="review",
            exact_manifest_paths=REVIEW_PAYLOAD_PATHS,
        )
        if final_seal["manifest_digests"] != staged_seal["manifest_digests"]:
            raise ValueError("published independent-review seal changed")
        final_sources = {
            "static_preflight": verify_complete_seal(
                static_preflight_root,
                expected_static_preflight_root_sha256,
                label="static preflight",
                exact_manifest_paths=STATIC_PREFLIGHT_PAYLOAD_PATHS,
            ),
            "evidence": verify_complete_seal(
                evidence_root,
                expected_evidence_root_sha256,
                label="evidence",
                exact_manifest_paths=EVIDENCE_PAYLOAD_PATHS,
            ),
            "launch": verify_complete_seal(
                launch_root,
                expected_launch_root_sha256,
                label="launch",
                exact_manifest_paths=LAUNCH_PAYLOAD_PATHS,
            ),
            "source_reviewer": verify_complete_seal(
                source_review_root,
                expected_source_review_root_sha256,
                label="source reviewer",
                exact_manifest_paths=SOURCE_REVIEW_PAYLOAD_PATHS,
            ),
        }
        if not _same_source_seals(source_seals, final_sources):
            raise ValueError("a sealed source changed after review publication")
        if _verify_repositories(
            Path(camp_repo),
            package_camp_head,
            authority_source_head,
            expected_current_camp_head,
            Path(dp_repo),
            expected_dp_head,
            str(source["source_camp_head"]),
            implementation_source_head,
            expected_reviewer_script_sha256,
            expected_reviewer_test_sha256,
        ) != repository_before:
            raise ValueError("repository provenance changed after review publication")
        final_authority = _verify_live_authority(
            Path(camp_repo),
            authority_source_head,
            evidence_root=evidence_root,
            evidence_root_sha256=expected_evidence_root_sha256,
            launch_root=launch_root,
            launch_root_sha256=expected_launch_root_sha256,
            source_review_root=source_review_root,
            source_review_root_sha256=expected_source_review_root_sha256,
            source_reviewer_head=str(source["source_camp_head"]),
            static_preflight_root=static_preflight_root,
            static_preflight_root_sha256=expected_static_preflight_root_sha256,
            implementation_source_head=implementation_source_head,
            reviewer_script_sha256=expected_reviewer_script_sha256,
            reviewer_test_sha256=expected_reviewer_test_sha256,
            holdout_state_path=Path(holdout_state_path),
            holdout_state_sha256=marker_before["sha256"],
        )
        if (
            final_authority["audit_bytes"] != authority_before["audit_bytes"]
            or final_authority["current_status_bytes"]
            != authority_before["current_status_bytes"]
        ):
            raise ValueError("live authority changed after review publication")
        final_marker = _verify_holdout_marker(
            Path(holdout_state_path), evidence["live_holdout_once"], source_state
        )
        if final_marker["bytes"] != marker_before["bytes"]:
            raise ValueError("holdout marker changed after review publication")
        if _active_v24_processes():
            raise ValueError("a v24 evaluator/runner/reviewer process exists after publication")
        free_bytes_after = shutil.disk_usage(output.parent).free
        if free_bytes_after <= minimum_free_bytes:
            raise ValueError("post-publication review violates the 10 GiB disk floor")
    except BaseException:
        _remove_owned_tree(staging, staging_identity)
        if published:
            _remove_owned_tree(output, published_identity)
            _fsync_directory(output.parent)
        raise
    return {
        "status": "passed",
        "classification": "launch_wrapper_validation_false_negative",
        "builder_succeeded": True,
        "sealed_output_authoritative": True,
        "decision": "honest_no_claim",
        "final_claim_authorized": False,
        "failed_gates": EXPECTED_FAILED_GATES,
        "check_count": len(checks),
        "output_dir": output.as_posix(),
        "root_sha256": output_root_sha256,
        "free_bytes_after_gate": free_bytes_after,
        "final_post_publication_checks_passed": True,
        "next_work_target": "v24_honest_no_claim_record_only_closeout",
    }


def review_evidence_claim(
    *,
    evidence_root: Path,
    expected_evidence_root_sha256: str,
    launch_root: Path,
    expected_launch_root_sha256: str,
    source_review_root: Path,
    expected_source_review_root_sha256: str,
    static_preflight_root: Path,
    expected_static_preflight_root_sha256: str,
    implementation_source_head: str,
    expected_reviewer_script_sha256: str,
    expected_reviewer_test_sha256: str,
    camp_repo: Path,
    package_camp_head: str,
    authority_source_head: str,
    expected_current_camp_head: str,
    dp_repo: Path,
    expected_dp_head: str,
    holdout_state_path: Path,
    output_dir: Path,
    enable_independent_review: bool,
    command: Sequence[str] | None = None,
    minimum_free_bytes: int = MINIMUM_FREE_BYTES,
) -> dict[str, Any]:
    if enable_independent_review is not True:
        raise ValueError("explicit --enable-independent-review is required")
    if type(minimum_free_bytes) is not int or minimum_free_bytes != MINIMUM_FREE_BYTES:
        raise ValueError("minimum free bytes must equal the frozen 10 GiB floor")
    _verify_frozen_production_path_components()
    frozen_roots = (
        (Path(source_review_root), CANONICAL_SOURCE_REVIEW_ROOT, "source reviewer"),
        (Path(evidence_root), CANONICAL_EVIDENCE_ROOT, "evidence"),
        (Path(launch_root), CANONICAL_LAUNCH_ROOT, "launch"),
    )
    for supplied, frozen, label in frozen_roots:
        if not supplied.is_absolute() or supplied != frozen:
            raise ValueError(f"{label} root differs from the frozen production root")
        _require_absolute_no_symlink_components(
            supplied, label=f"{label} artifact root"
        )
    for supplied, label in (
        (Path(static_preflight_root), "static preflight artifact root"),
        (Path(camp_repo), "CAMP repo"),
        (Path(dp_repo), "fixed DP repo"),
        (Path(holdout_state_path), "holdout marker"),
        (Path(output_dir).parent, "output parent"),
    ):
        _require_absolute_no_symlink_components(supplied, label=label)
    for supplied, frozen, label in (
        (
            expected_source_review_root_sha256,
            EXPECTED_SOURCE_REVIEW_ROOT_SHA256,
            "source reviewer",
        ),
        (expected_evidence_root_sha256, EXPECTED_EVIDENCE_ROOT_SHA256, "evidence"),
        (expected_launch_root_sha256, EXPECTED_LAUNCH_ROOT_SHA256, "launch"),
    ):
        if supplied != frozen:
            raise ValueError(f"{label} root SHA256 differs from the frozen production root")
    with _exclusive_global_lock(GLOBAL_LOCK_PATH):
        return _review_locked(
            evidence_root=evidence_root,
            expected_evidence_root_sha256=expected_evidence_root_sha256,
            launch_root=launch_root,
            expected_launch_root_sha256=expected_launch_root_sha256,
            source_review_root=source_review_root,
            expected_source_review_root_sha256=expected_source_review_root_sha256,
            static_preflight_root=static_preflight_root,
            expected_static_preflight_root_sha256=(
                expected_static_preflight_root_sha256
            ),
            implementation_source_head=implementation_source_head,
            expected_reviewer_script_sha256=expected_reviewer_script_sha256,
            expected_reviewer_test_sha256=expected_reviewer_test_sha256,
            camp_repo=camp_repo,
            package_camp_head=package_camp_head,
            authority_source_head=authority_source_head,
            expected_current_camp_head=expected_current_camp_head,
            dp_repo=dp_repo,
            expected_dp_head=expected_dp_head,
            holdout_state_path=holdout_state_path,
            output_dir=output_dir,
            command=command,
            minimum_free_bytes=minimum_free_bytes,
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--expected-evidence-root-sha256", required=True)
    parser.add_argument("--launch-root", type=Path, required=True)
    parser.add_argument("--expected-launch-root-sha256", required=True)
    parser.add_argument("--source-review-root", type=Path, required=True)
    parser.add_argument("--expected-source-review-root-sha256", required=True)
    parser.add_argument("--static-preflight-root", type=Path, required=True)
    parser.add_argument("--expected-static-preflight-root-sha256", required=True)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--expected-reviewer-script-sha256", required=True)
    parser.add_argument("--expected-reviewer-test-sha256", required=True)
    parser.add_argument("--camp-repo", type=Path, required=True)
    parser.add_argument("--package-camp-head", required=True)
    parser.add_argument("--authority-source-head", required=True)
    parser.add_argument("--expected-current-camp-head", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--expected-dp-head", required=True)
    parser.add_argument("--holdout-state-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-independent-review", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = review_evidence_claim(
        evidence_root=args.evidence_root,
        expected_evidence_root_sha256=args.expected_evidence_root_sha256,
        launch_root=args.launch_root,
        expected_launch_root_sha256=args.expected_launch_root_sha256,
        source_review_root=args.source_review_root,
        expected_source_review_root_sha256=args.expected_source_review_root_sha256,
        static_preflight_root=args.static_preflight_root,
        expected_static_preflight_root_sha256=(
            args.expected_static_preflight_root_sha256
        ),
        implementation_source_head=args.implementation_source_head,
        expected_reviewer_script_sha256=args.expected_reviewer_script_sha256,
        expected_reviewer_test_sha256=args.expected_reviewer_test_sha256,
        camp_repo=args.camp_repo,
        package_camp_head=args.package_camp_head,
        authority_source_head=args.authority_source_head,
        expected_current_camp_head=args.expected_current_camp_head,
        dp_repo=args.dp_repo,
        expected_dp_head=args.expected_dp_head,
        holdout_state_path=args.holdout_state_path,
        output_dir=args.output_dir,
        enable_independent_review=args.enable_independent_review,
    )
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
