#!/usr/bin/env python3
"""Independently review a sealed A1.6.10 bounded K8 execution."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import json
import lzma
import math
from pathlib import Path
import pickle
import random
import re
import subprocess
import sys
from typing import Any, Mapping
import zipfile

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
from camp_core.integrations.diffusion_planner import (  # noqa: E402
    install_lanelet2_projection_fallback,
    require_source_preserving_lanelet2_regulatory_adapter,
)
from camp_core.integrations import (  # noqa: E402
    diffusion_planner_v25_a163_bounded_authority as bounded_authority,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    CRITICAL_IMPLEMENTATION_PATHS,
    POINTER_ONLY_PATHS,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    FIXED_DP_FAILURE_CLASS,
    FIXED_DP_FAILURE_REASON,
    FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    RUN_EVIDENCE_SCHEMA_VERSION,
    canonical_sha256,
)
from camp_core.integrations.diffusion_planner_v25_causal_evidence_review import (  # noqa: E402
    expected_shard_manifest_paths,
    independently_materialize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_review import (  # noqa: E402
    SNAPSHOT_SUFFIX,
    independently_read_snapshot,
)


SCHEMA_VERSION = "camp_dp_v25_a17_bounded_execution_review_v11"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_a1610_bounded_execution_v8"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_a17_bounded_snapshot_v7"
INDEX_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_index_row_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_UNIQUE_IDENTITIES = 243
EXPECTED_RUNS = 244
EXPECTED_TICKS = 15616
EXPECTED_SEED = 25001
RELEASE_GATE = "a1610_bounded_execute"
NONCE_LEDGER = Path("/root/autodl-tmp/.camp_dp_v25_a1610_bounded_execute_nonces")
EXPECTED_DEVICE = "cuda"
EXPECTED_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
EXPECTED_FORMAL_ROOT_SHA256 = "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
EXPECTED_FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
EXPECTED_PROBE_TEMPLATE = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)
EXPECTED_PROBE_TEMPLATE_SHA256 = (
    "1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc"
)
EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION = "camp_dp_v24_single_record_source_probe_v1"
EXPECTED_GENERATION_SCALES = {
    "path": (
        "/root/autodl-tmp/camp_core/configs/integrations/"
        "diffusion_planner_v25_atom_scales_correction_v2.json"
    ),
    "sha256": "e844d159dc6c9c21b099084f5a46bf90fb77ca92571749f529e61e08814fe316",
}
EXPECTED_STATIC_WEIGHTS = {
    "path": (
        "/root/autodl-tmp/"
        "camp_dp_v18_nuplan_causal_10k_static_14d_train_calibrate_"
        "79c9570b_0c22f85e/models/corrected14d_weights.npy"
    ),
    "sha256": "922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134",
}
EXPECTED_STATIC_WEIGHT_VALUES = (
    0.10947278201682221,
    4.5339121051258635e-14,
    4.436657731585812e-14,
    0.33777087074295037,
    7.284723165939581e-10,
    0.0,
    0.0,
    0.0,
    0.34158690923521606,
    0.10033962151340078,
    0.0,
    0.1108291578563568,
    6.579066917788303e-07,
    0.0,
)
EXPECTED_FIXED_DP_CHECKPOINT = {
    "path": "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth",
    "sha256": "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75",
}
EXPECTED_FIXED_DP_ARGS = {
    "path": (
        "/root/autodl-tmp/"
        "camp_dp_v18_nuplan_mini_smoke_split_candidate_preflight_"
        "20260710T220921CST/fixed_dp_args.json"
    ),
    "sha256": "42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa",
}
EXPECTED_DP_NATIVE_SOURCE_SHA256 = {
    "scenario_generation/mpc_tracker.py": "bf2fdc6398898a42eda4ab3d12045c5204eb5ce8a993dbf96feee975de04395a",
    "scenario_generation/replay.py": "92158e32f8e2626a20aeee1783501d1afad228f06d5948f3426716d93320c5eb",
    "scenario_generation/simulate.py": "de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e",
    "scenario_generation/tensor_converter.py": "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7",
    "scenario_generation/traffic_light.py": "5a1659fe753102c514528c0bd93c261124bdf8de11bbc00ba5b941c151956af4",
}
GOAL_TOLERANCE_M = 2.0
GOAL_PASS_WINDOW_M = 25.0
# Frozen fixed-DP replay.py::_CLEARANCE_LOG_MAX_M at FIXED_DP_HEAD.
EXPECTED_CLEARANCE_MAX_RANGE_M = 30.0
FIXED_K8_HEADING_NORM_MIN = 0.5
FIXED_K8_HEADING_NORM_MAX = 1.5
REVIEW_CORRECTION_PATHS = frozenset(
    {
        "scripts/integrations/review_diffusion_planner_v25_a163_bounded_execution.py",
        "camp_core/tests/test_diffusion_planner_v25_a163_bounded_execution.py",
    }
)
SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION = (
    "camp_dp_v25_a1610_causal_scene_materialization_evidence_v2"
)
SCENE_MATERIALIZATION_EVIDENCE_FIELDS = {
    "schema_version", "relative_path", "sha256", "tick_count", "arrays",
}
# Frozen locally rather than imported from the producer/hash implementation.
SCENE_MATERIALIZATION_ARRAY_SCHEMA = {
    "ego_agent_past": ((31, 3), "float32"),
    "ego_current_state": ((10,), "float32"),
    "ego_shape": ((3,), "float32"),
    "goal_pose": ((3,), "float32"),
    "lanes": ((140, 20, 33), "float32"),
    "lanes_has_speed_limit": ((140, 1), "bool"),
    "lanes_speed_limit": ((140, 1), "float32"),
    "line_strings": ((60, 20, 4), "float32"),
    "neighbor_agents_past": ((32, 31, 11), "float32"),
    "polygons": ((10, 40, 3), "float32"),
    "route_lanes": ((25, 20, 33), "float32"),
    "route_lanes_has_speed_limit": ((25, 1), "bool"),
    "route_lanes_speed_limit": ((25, 1), "float32"),
    "static_objects": ((5, 10), "float32"),
    "turn_indicators": ((31,), "int32"),
    "version": ((), "int64"),
}
EXECUTION_FILE_BYTE_POLICIES = (
    (r"(?:COMMAND|HEADS|run\.exit)", "exact-control-text-v1"),
    (
        r"(?:report|source_receipt|progress)\.json",
        "canonical-json-utf8-sort-compact-single-lf-v1",
    ),
    (
        r"(?:results|snapshot_index|run_evidence)\.jsonl",
        "canonical-jsonl-each-row-single-lf-v1",
    ),
    (r"routes/[0-9a-f]{64}\.pkl", "fixed-dp-route-pickle-v1"),
    (r"snapshots/[0-9a-f]{64}\.json\.xz", "canonical-content-address-json-xz-v1"),
    (
        r"causal_evidence_shards/[0-9a-f]{64}\.bin\.xz",
        "deterministic-causal-evidence-array-shard-v1",
    ),
    (
        r"causal_scene_materializations/[0-9a-f]{64}\.npz",
        "strict-causal-scene-materialization-npz-v1",
    ),
    (
        r"fixed_dp_capability_failures/[0-9a-f]{64}\.bin",
        "fixed-dp-capability-raw-k8-float32-v1",
    ),
    (
        r"native_runs/[^/]+/bounded_native_receipt\.json",
        "canonical-json-utf8-sort-compact-single-lf-v1",
    ),
    (
        r"native_runs/[^/]+/(?:trajectory_log|clearance_log)\.json",
        "fixed-dp-strict-json-exact-schema-v1",
    ),
    (
        r"native_runs/[^/]+/native\.(?:stdout|stderr)\.txt",
        "diagnostic-utf8-text-nonauthoritative-v1",
    ),
)
RAW_CONTEXT_NAMES = (
    "ego_speed_mps",
    "ego_longitudinal_acceleration_mps2",
    "ego_lateral_acceleration_mps2",
    "ego_yaw_rate_radps",
    "route_curvature_mean_abs_radpm",
    "route_curvature_max_abs_radpm",
    "route_lane_width_min_m",
    "route_lane_width_p50_m",
    "route_speed_limit_min_mps",
    "route_speed_limit_current_mps",
    "traffic_phase_red",
    "traffic_phase_yellow",
    "traffic_phase_green",
    "traffic_phase_unknown",
    "traffic_signal_distance_m",
    "traffic_signal_phase_remaining_s",
    "neighbor_count",
    "neighbor_min_distance_m",
    "neighbor_min_ttc_s",
    "neighbor_closing_speed_mps",
    "neighbor_lateral_gap_min_m",
    "candidate_consensus_rms_median_m",
    "candidate_consensus_rms_mad_m",
    "candidate_endpoint_xy_std_m",
    "candidate_progress_std_m",
    "candidate_source_valid_fraction",
)
RESULT_FIELDS = {
    "schema_version",
    "run_ordinal",
    "scenario_id",
    "occurrence",
    "status",
    "tick_count",
    "retained_capability_failure",
    "failure_class",
    "fresh_b2_opened",
    "outcome_fields_consumed",
    "family",
    "tier",
    "source_class",
    "phase_authority_mode",
    "source_map_sha256",
    "corridor_group_sha256",
}
EXECUTION_REPORT_FIELDS = {
    "schema_version",
    "status",
    "unique_identity_count",
    "run_count",
    "snapshot_count",
    "snapshot_capacity",
    "device",
    "terminal",
    "wall_seconds",
    "retained_capability_failure_count",
    "mapped_runtime_source_failure_count",
    "candidate0_semantics",
    "sequential_fixed_k8",
    "candidate_tensors_modified",
    "full_r_execute_authorized",
    "training_executed",
    "calibration_executed",
    "scene_runtime_enabled",
    "v2i_enabled",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}
SOURCE_RECEIPT_FIELDS = {
    "schema_version",
    "release_artifact",
    "release_root_sha256",
    "release_run_nonce",
    "nonce_marker",
    "root_artifacts",
    "formal_root_sha256",
    "critical_implementation_manifest",
    "unique_identity_count",
    "run_count",
    "snapshot_capacity",
    "device",
    "full_r_execute_authorized",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}
SNAPSHOT_FIELDS = {"schema_version", "feature_payload", "sidecar"}
FEATURE_FIELDS = {
    "atom_matrix",
    "source_valid_mask",
    "atom_source_valid_mask",
    "atom_applicable_mask",
    "physical_feasible_mask",
    "candidate_row_sha256",
    "candidate_tensor",
    "default_output",
    "raw_context",
    "context_source_complete",
    "causal_evidence",
}
SIDECAR_FIELDS = {
    "tick_index",
    "dt_s",
    "scenario_id",
    "family",
    "tier",
    "parameter_block_id",
    "route_identity_sha256",
    "corridor_group_sha256",
    "map_family_id",
    "source_map_sha256",
    "seed",
    "candidate_tensor_sha256_before",
    "candidate_tensor_sha256_after",
    "default_output_sha256",
    "candidate0_sha256",
    "default_candidate0_identity",
    "candidate0_semantics",
    "candidate0_independent_second_forward",
    "scene_materialization_sha256",
    "causal_evidence_sha256",
    "route_lanes_sha256",
    "route_lanes_speed_limit_sha256",
    "route_lanes_has_speed_limit_sha256",
    "physical_feasible_mask",
    "source_valid_mask",
    "all_k_high_risk",
    "selected_index",
    "selected_trajectory_sha256",
    "scores",
    "score_contract",
    "tie_break_contract",
    "normalized_atom_matrix_sha256",
    "context_schema_version",
    "context_source_receipt",
    "generation_behavior_scale_sha256",
    "canonical_semantic_clone_sha256",
    "route_signal_source_artifact_root_sha256",
    "route_signal_source_row_sha256",
    "signal_source_class",
    "phase_authority_mode",
    "controlled_signal_source_receipt",
    "controlled_signal_tensor_evidence",
    "controlled_model_input_cache_receipt",
    "causal_signal_atom_input",
    "offline_label_provenance",
    "outcome_fields_consumed",
    "fresh_b_opened",
    "run_ordinal",
    "occurrence",
}
SOURCE_ROW_FIELDS = {
    "scenario_id",
    "formal_case_sha256",
    "runner_eligible",
    "retention_role",
    "family",
    "tier",
    "seed",
    "source_map_sha256",
    "route_identity_sha256",
    "actual_mapped_signal",
    "id_free_tensor_layout",
    "source_class",
    "phase_authority_mode",
    "source_chain",
    "runtime_receipt",
    "tensor_evidence",
}
MAPPED_CHAIN_FIELDS = {
    "schema_version",
    "scenario_id",
    "route_identity_sha256",
    "source_map_sha256",
    "phase_authority_mode",
    "expected_current_phase",
    "formal_phase",
    "formal_mapped_source_required",
    "formal_route_mapped_traffic_light",
    "phase_remaining_available",
    "regulatory_element_ids",
    "physical_light_ids",
    "bulb_ids",
    "controlled_lanelet_ids",
    "route_lanelet_ids",
    "route_geometry_sha256",
    "stop_line_id",
    "stop_line_geometry_m",
    "stop_line_geometry_sha256",
    "stop_line_route_distance_m",
    "route_arc_m",
    "route_length_m",
    "route_tangent_world",
    "semantic_clone_payload",
    "semantic_clone_sha256",
    "source_chain_sha256",
}
NO_SIGNAL_CHAIN_FIELDS = {
    "schema_version",
    "scenario_id",
    "route_identity_sha256",
    "source_map_sha256",
    "route_lanelet_ids",
    "route_geometry_sha256",
    "traffic_light_regulatory_element_ids",
    "semantic_clone_payload",
    "semantic_clone_sha256",
    "source_chain_sha256",
}
MAPPED_RECEIPT_FIELDS = {
    "schema_version",
    "scenario_id",
    "tick_index",
    "phase_authority_mode",
    "current_phase",
    "decision_timestamp_s",
    "source_timestamp_s",
    "source_age_s",
    "freshness",
    "source_id",
    "regulatory_element_id",
    "physical_light_ids",
    "bulb_ids",
    "controlled_lanelet_ids",
    "stop_line_id",
    "stop_line_geometry_sha256",
    "route_geometry_sha256",
    "route_arc_m",
    "source_chain_sha256",
    "observed_route_lanelet_ids",
    "observed_map_lanelet_ids",
    "route_signal_tensor_sha256",
    "map_signal_tensor_sha256",
    "phase_remaining_available",
    "source_valid",
    "applicable",
}
SIGNAL_TENSOR_FIELDS = {
    "schema_version",
    "tick_index",
    "decision_timestamp_s",
    "source_timestamp_s",
    "route_signal_rows",
    "map_signal_rows",
    "current_phase",
    "route_signal_tensor_sha256",
    "map_signal_tensor_sha256",
    "future_schedule_consumed",
    "phase_remaining_available",
}
NO_SIGNAL_RECEIPT_FIELDS = {
    "schema_version",
    "scenario_id",
    "tick_index",
    "decision_time_s",
    "source_mode",
    "current_phase",
    "route_geometry_sha256",
    "route_lanelet_ids",
    "traffic_light_regulatory_element_ids",
    "source_chain_sha256",
    "semantic_clone_sha256",
    "phase_remaining_available",
    "source_valid",
    "applicable",
}
CAUSAL_SIGNAL_FIELDS = {
    "schema_version",
    "source_state",
    "source_valid",
    "applicable",
    "current_phase",
    "decision_time_s",
    "ego_position_world_m",
    "ego_heading_rad",
    "regulatory_element_id",
    "stop_line_id",
    "stop_line_geometry_world_m",
    "stop_line_geometry_ego_m",
    "stop_line_geometry_sha256",
    "route_tangent_world",
    "route_tangent_ego",
    "route_geometry_sha256",
    "route_arc_m",
    "source_chain_sha256",
    "runtime_receipt",
    "runtime_receipt_sha256",
}
CACHE_RECEIPT_FIELDS = {
    "schema_version",
    "scenario_id",
    "tick_index",
    "signal_source_class",
    "phase_authority_mode",
    "scene_map_tl_sha256",
    "model_cache_tl_sha256_before",
    "model_cache_tl_sha256_after",
    "model_route_lanes_tl_sha256",
    "cache_matches_scene_after",
    "observe_cache_unchanged",
    "sync_applied_before_tensor_conversion",
    "future_schedule_consumed",
    "phase_remaining_available",
}
DEFAULT_IDENTITY_FIELDS = {
    "elementwise_equal",
    "max_abs_difference",
    "default_output_sha256",
    "candidate0_sha256",
    "native_ranked_k8",
}
CAUSAL_EVIDENCE_FIELDS = {
    "schema_version", "ego_current_state", "ego_shape", "neighbor_agents_past",
    "neighbor_valid_mask", "candidate_neighbor_predictions", "static_objects",
    "route_lanes", "route_lanes_speed_limit", "route_lanes_has_speed_limit",
    "signal_mask", "fixed_dp_planned_red_light_cost",
}
PUBLIC_TICK_FIELDS = {
    "tick_index", "status", "scene_materialization_sha256", "padding", "tracker", "safety",
    "latency_ms", "pre_decision_speed_mps", "default_output_sha256", "candidate_tensor_sha256_before",
    "candidate_tensor_sha256_after", "candidate_neighbor_sha256",
    "selected_trajectory_sha256", "global_rng_sha256_before",
    "global_rng_sha256_after", "causal_evidence_sha256", "route_lanes_sha256",
    "route_lanes_speed_limit_sha256", "route_lanes_has_speed_limit_sha256",
    "candidate_row_sha256", "selection_policy", "score_contract",
    "tie_break_contract", "eligibility_mask_name", "selected_index",
    "default_candidate0_identity", "atom_matrix_sha256",
    "normalized_atom_matrix_sha256", "npc_operational_outputs_unchanged",
    "scores", "physical_feasible_mask", "source_valid_mask",
    "source_complete_mask", "candidate_reasons", "all_k_high_risk",
    "controlled_scene", "v25_context",
}
SAFETY_FIELDS = {
    "tick_index", "position_xy", "speed_mps", "ego_heading_rad",
    "route_heading_rad", "route_progress_m", "five_point_drivable_coverage",
    "min_obb_clearance_m", "red_light_at_interval_start",
    "front_center_prev_xy", "front_center_xy", "red_stop_lines",
    "speed_limit_mps", "constant_velocity_circle_ttc_diagnostic_s",
    "source_complete",
}
LATENCY_FIELDS = {
    "input_materialization", "default_inference", "candidate_inference",
    "atom_materialization", "selector", "hook_total", "tracker", "total_planning",
}
NATIVE_RECEIPT_FIELDS = {
    "schema_version", "status", "route_name", "route_sha256",
    "logical_map_sha256", "fixed_dp_head", "checkpoint_sha256", "args_sha256",
    "arm", "scenario_seed", "spawn_config_sha256", "initial_world_state_sha256",
    "initial_scene_materialization_sha256", "ticks", "native_result", "claim_authorized",
    "selector_scale_contract", "runtime_annotation_compatibility",
    "causal_scene_materialization_evidence",
}
INITIAL_WORLD_STATE_SCHEMA_VERSION = "camp_dp_v25_a1610_initial_world_state_v2"
NATIVE_HEADER_RESULT_FIELDS = NATIVE_RECEIPT_FIELDS - {"ticks"}
EXPECTED_SELECTOR_SCALE_CONTRACT = {
    "declared_atom_schema_version": "dp_camp_v10_14d",
    "effective_atom_schema_version": "dp_camp_v10_14d",
    "compatibility_policy": "exact_atom_names_on_frozen_sha_v1",
}
EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY = "not_required_python310_or_newer"
SEMANTIC_REQUIRED_FIELDS = {
    "schema_version",
    "family",
    "tier",
    "semantic_variant",
    "parameters",
    "actors",
    "signal",
    "route_polyline_local_m",
}
SEMANTIC_ACTOR_FIELDS = {
    "agent_type",
    "initial_xy_local_m",
    "initial_heading_local_unit",
    "route_tangent_local",
    "route_normal_local",
    "trigger_time_s",
    "longitudinal_speed_mps",
    "lateral_offset_m",
    "lateral_speed_mps",
    "lateral_target_m",
    "longitudinal_acceleration_mps2",
    "length_m",
    "width_m",
    "wheelbase_m",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True
    ).stdout


def _historical_critical_manifest(repo: Path, head: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative_path in CRITICAL_IMPLEMENTATION_PATHS:
        payload = _git_bytes(repo, "show", f"{head}:{relative_path}")
        manifest[relative_path] = hashlib.sha256(payload).hexdigest()
    return manifest


def _changed_paths(repo: Path, start: str, end: str) -> list[str]:
    if start == end:
        return []
    return [
        line.replace("\\", "/")
        for line in _git(repo, "diff", "--name-only", start, end, "--").splitlines()
        if line
    ]


def _parse_heads_bytes(path: Path) -> dict[str, str]:
    try:
        text = path.read_bytes().decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("bounded authority HEADS is not strict ASCII") from exc
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("bounded authority HEADS framing drifted")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            raise ValueError("bounded authority HEADS line drifted")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError("bounded authority HEADS key drifted")
        fields[key] = value
    expected = (
        f"camp_source_head={fields.get('camp_source_head', '')}\n"
        f"camp_pointer_head={fields.get('camp_pointer_head', '')}\n"
        f"fixed_dp_head={fields.get('fixed_dp_head', '')}\n"
    ).encode("ascii")
    if path.read_bytes() != expected:
        raise ValueError("bounded authority HEADS key set/order drifted")
    return fields


def _verify_archived_bounded_release_for_review(
    *,
    repo: Path,
    review_head: str,
    release_artifact: Path,
    release_root_sha256: str,
    requested_output_dir: str,
    dp_repo: Path,
    probe_template: Path,
) -> dict[str, Any]:
    """Open an immutable producer release under a later review-only commit.

    The producer implementation remains bound to its historical git blobs.  The
    only permitted later changes are this independent reviewer and its focused
    tests; execution authority is never reissued or consumed here.
    """

    seal = verify_complete_seal(
        release_artifact,
        release_root_sha256,
        label="V25 A1.7 archived bounded release for independent review",
    )
    if (
        seal["manifest_paths"] != bounded_authority.RELEASE_PAYLOADS
        or (release_artifact / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("bounded archived release inventory/run.exit drifted")
    decision = _load(release_artifact / "decision.json", canonical=True)
    heads = _parse_heads_bytes(release_artifact / "HEADS")
    if type(decision) is not dict or set(decision) != bounded_authority.RELEASE_FIELDS:
        raise ValueError("bounded archived release field set drifted")
    exact = {
        "schema_version": bounded_authority.RELEASE_SCHEMA_VERSION,
        "status": bounded_authority.RELEASE_STATUS,
        "gate": bounded_authority.RELEASE_GATE,
        "fixed_dp_head": FIXED_DP_HEAD,
        "seed": EXPECTED_SEED,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "device": EXPECTED_DEVICE,
        "bounded_execute_authorized": True,
        "full_config_preflight_authorized": False,
        "full_r_execute_authorized": False,
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    for key, expected_value in exact.items():
        if not _strict_equal(decision.get(key), expected_value):
            raise ValueError(f"bounded archived release value drifted: {key}")
    source_head = decision.get("implementation_source_head")
    producer_pointer_head = decision.get("pointer_head_at_release")
    if (
        type(source_head) is not str
        or not re.fullmatch(r"[0-9a-f]{40}", source_head)
        or type(producer_pointer_head) is not str
        or not re.fullmatch(r"[0-9a-f]{40}", producer_pointer_head)
        or type(review_head) is not str
        or not re.fullmatch(r"[0-9a-f]{40}", review_head)
        or heads
        != {
            "camp_source_head": source_head,
            "camp_pointer_head": producer_pointer_head,
            "fixed_dp_head": FIXED_DP_HEAD,
        }
        or decision.get("critical_implementation_manifest_sha256")
        != _sha(decision.get("critical_implementation_manifest"))
        or decision.get("execution_assets_sha256")
        != _sha(decision.get("execution_assets"))
        or decision.get("root_artifacts_sha256")
        != _sha(decision.get("root_artifacts"))
    ):
        raise ValueError("bounded archived release hashes/HEADS drifted")
    historical_manifest = _historical_critical_manifest(repo, source_head)
    if not _strict_equal(
        decision.get("critical_implementation_manifest"), historical_manifest
    ):
        raise ValueError("bounded archived producer implementation drifted")
    source_pointer_delta = _changed_paths(repo, source_head, producer_pointer_head)
    if set(source_pointer_delta) - POINTER_ONLY_PATHS:
        raise ValueError("bounded archived producer dual-HEAD contract drifted")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", producer_pointer_head, review_head],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    review_delta = _changed_paths(repo, producer_pointer_head, review_head)
    if (
        "scripts/integrations/review_diffusion_planner_v25_a163_bounded_execution.py"
        not in review_delta
        or set(review_delta) - REVIEW_CORRECTION_PATHS
    ):
        raise ValueError("bounded review HEAD exceeds the frozen review-only delta")
    assets = bounded_authority.verify_frozen_execution_assets(
        repo=repo, dp_repo=dp_repo, probe_template=probe_template
    )
    if (
        Path(str(decision.get("dp_repo"))).resolve() != dp_repo.resolve()
        or decision.get("dp_repo") != str(dp_repo.resolve())
        or Path(str(decision.get("probe_template"))).resolve()
        != probe_template.resolve()
        or decision.get("probe_template") != str(probe_template.resolve())
        or decision.get("probe_template_sha256")
        != EXPECTED_PROBE_TEMPLATE_SHA256
        or not _strict_equal(decision.get("execution_assets"), assets)
    ):
        raise ValueError("bounded archived release execution assets drifted")
    chain = bounded_authority.verify_four_root_chain(
        bindings=decision["root_artifacts"],
        implementation_source_head=source_head,
        fixed_dp_head=decision["fixed_dp_head"],
    )
    authorized = Path(str(decision.get("authorized_output_dir")))
    if (
        not authorized.is_absolute()
        or str(authorized.resolve()) != decision.get("authorized_output_dir")
        or requested_output_dir != decision.get("authorized_output_dir")
        or Path(requested_output_dir).resolve() != authorized.resolve()
    ):
        raise ValueError("bounded archived release output binding drifted")
    return {
        "release_artifact": str(release_artifact.resolve()),
        "release_root_sha256": seal["root_sha256"],
        "decision": decision,
        "plan": chain["plan"],
        "producer_pointer_head": producer_pointer_head,
        "review_head": review_head,
        "review_only_changed_paths": review_delta,
        "nonce_marker": None,
    }


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant is forbidden: {value}")


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _parse_strict_json_bytes(data: bytes, *, label: str) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not strict UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} is not strict JSON") from exc


def _load(path: Path, *, canonical: bool = False) -> Any:
    data = path.read_bytes()
    value = _parse_strict_json_bytes(data, label=str(path))
    if canonical and data != _canonical_bytes(value):
        raise ValueError(f"{path} violates canonical JSON bytes/single-LF")
    return value


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _jsonl(path: Path) -> list[Any]:
    data = path.read_bytes()
    if not data or not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ValueError(f"{path} violates canonical JSONL framing")
    rows: list[Any] = []
    for index, line in enumerate(data.splitlines(keepends=True)):
        if not line.endswith(b"\n") or line == b"\n":
            raise ValueError(f"{path} JSONL row {index} framing drifted")
        value = _parse_strict_json_bytes(
            line, label=f"{path} JSONL row {index}"
        )
        if line != _canonical_bytes(value):
            raise ValueError(f"{path} JSONL row {index} is noncanonical")
        rows.append(value)
    return rows


def _execution_file_byte_policy(relative_path: str) -> str:
    matches = [
        policy
        for pattern, policy in EXECUTION_FILE_BYTE_POLICIES
        if re.fullmatch(pattern, relative_path)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"bounded execution file has no unique byte/schema policy: {relative_path}"
        )
    return matches[0]


def _validate_diagnostic_text(path: Path, *, require_single_lf: bool) -> None:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"bounded diagnostic text is not strict UTF-8: {path}") from exc
    if "\x00" in text or "\r" in text:
        raise ValueError(f"bounded diagnostic text framing drifted: {path}")
    if require_single_lf and (
        not text or not text.endswith("\n") or text.endswith("\n\n")
    ):
        raise ValueError(f"bounded control text framing drifted: {path}")


def _validate_execution_policy_file(
    *, artifact: Path, relative_path: str, policy: str
) -> None:
    path = artifact / relative_path
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"bounded policy file is unavailable: {relative_path}")
    if policy == "exact-control-text-v1":
        if relative_path == "run.exit":
            if path.read_bytes() != b"0\n":
                raise ValueError("bounded execution run.exit exact bytes drifted")
        elif relative_path == "HEADS":
            _validate_diagnostic_text(path, require_single_lf=True)
            data = path.read_bytes()
            try:
                lines = data.decode("ascii", errors="strict").splitlines()
            except UnicodeDecodeError as exc:
                raise ValueError("bounded execution HEADS is not strict ASCII") from exc
            fields: dict[str, str] = {}
            for line in lines:
                if line.count("=") != 1:
                    raise ValueError("bounded execution HEADS line drifted")
                key, value = line.split("=", 1)
                if not key or not value or key in fields:
                    raise ValueError("bounded execution HEADS key/value drifted")
                fields[key] = value
            order = ("camp_source_head", "camp_pointer_head", "fixed_dp_head")
            if tuple(fields) != order:
                raise ValueError("bounded execution HEADS order/key set drifted")
            expected = "".join(f"{key}={fields[key]}\n" for key in order).encode(
                "ascii"
            )
            if data != expected:
                raise ValueError("bounded execution HEADS exact bytes drifted")
        elif relative_path == "COMMAND":
            # COMMAND is a sealed diagnostic only; it is intentionally not an
            # execution-authority argv oracle because shell quoting is external.
            _validate_diagnostic_text(path, require_single_lf=True)
            if path.read_bytes() == b"\n":
                raise ValueError("bounded execution COMMAND diagnostic is empty")
        else:
            raise ValueError("unknown bounded control-text path")
    elif policy in {
        "canonical-json-utf8-sort-compact-single-lf-v1",
        "canonical-content-address-json-v1",
    }:
        _load(path, canonical=True)
    elif policy == "canonical-content-address-json-xz-v1":
        digest = path.name[: -len(SNAPSHOT_SUFFIX)]
        independently_read_snapshot(path, digest)
    elif policy == "deterministic-causal-evidence-array-shard-v1":
        suffix = ".bin.xz"
        digest = path.name[: -len(suffix)]
        data = path.read_bytes()
        if (
            not path.name.endswith(suffix)
            or not _is_sha256(digest)
            or hashlib.sha256(data).hexdigest() != digest
        ):
            raise ValueError("bounded causal shard content address drifted")
        try:
            if not lzma.decompress(data, format=lzma.FORMAT_XZ):
                raise ValueError("bounded causal shard is empty")
        except lzma.LZMAError as exc:
            raise ValueError("bounded causal shard XZ stream is invalid") from exc
    elif policy == "canonical-jsonl-each-row-single-lf-v1":
        _jsonl(path)
    elif policy == "fixed-dp-route-pickle-v1":
        if not path.read_bytes():
            raise ValueError("bounded fixed-DP route pickle is empty")
    elif policy == "strict-causal-scene-materialization-npz-v1":
        try:
            with zipfile.ZipFile(path, "r") as archive:
                members = archive.namelist()
                if (
                    not members
                    or len(members) != len(set(members))
                    or any(
                        info.is_dir()
                        or info.filename.startswith(("/", "\\"))
                        or ".." in Path(info.filename).parts
                        for info in archive.infolist()
                    )
                ):
                    raise ValueError("bounded scene materialization archive drifted")
        except zipfile.BadZipFile as exc:
            raise ValueError("bounded scene materialization archive is invalid") from exc
    elif policy == "fixed-dp-strict-json-exact-schema-v1":
        _load(path, canonical=False)
    elif policy == "fixed-dp-capability-raw-k8-float32-v1":
        digest = path.stem
        data = path.read_bytes()
        if (
            not _is_sha256(digest)
            or len(data) != 8 * 80 * 4 * np.dtype(np.float32).itemsize
            or hashlib.sha256(data).hexdigest() != digest
        ):
            raise ValueError("fixed-DP capability raw K8 preimage drifted")
        tensor = np.frombuffer(data, dtype=np.float32).reshape(8, 80, 4)
        if not np.isfinite(tensor).all():
            raise ValueError("fixed-DP capability raw K8 is nonfinite")
    elif policy == "diagnostic-utf8-text-nonauthoritative-v1":
        _validate_diagnostic_text(path, require_single_lf=False)
    else:
        raise ValueError(f"unknown bounded execution byte policy: {policy}")


def _validate_execution_manifest_policies(
    *, artifact: Path, paths: list[str]
) -> dict[str, str]:
    if type(paths) is not list or not paths:
        raise ValueError("bounded execution manifest paths are unavailable")
    policies = {path: _execution_file_byte_policy(path) for path in paths}
    for relative_path, policy in policies.items():
        _validate_execution_policy_file(
            artifact=artifact, relative_path=relative_path, policy=policy
        )
    return policies


def _native_numeric_array(value: Any, shape: tuple[int, ...], *, label: str) -> np.ndarray:
    def walk(node: Any, depth: int) -> list[float]:
        if depth == len(shape):
            if type(node) not in (int, float) or not math.isfinite(float(node)):
                raise ValueError(f"{label} contains a non-native/nonfinite value")
            return [float(node)]
        if type(node) is not list or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        flattened: list[float] = []
        for child in node:
            flattened.extend(walk(child, depth + 1))
        return flattened

    return np.asarray(walk(value, 0), dtype=np.float64).reshape(shape)


def _native_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _strict_bool_array(value: Any, shape: tuple[int, ...], *, label: str) -> np.ndarray:
    def walk(node: Any, depth: int) -> list[bool]:
        if depth == len(shape):
            if type(node) is not bool:
                raise ValueError(f"{label} contains a non-bool value")
            return [node]
        if type(node) is not list or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        result: list[bool] = []
        for child in node:
            result.extend(walk(child, depth + 1))
        return result

    return np.asarray(walk(value, 0), dtype=np.bool_).reshape(shape)


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _independent_array_mapping_sha256(data: Mapping[str, np.ndarray]) -> str:
    """Local digest oracle for the saved causal scene materialization."""

    digest = hashlib.sha256()
    for key in sorted(data):
        if type(key) is not str:
            raise ValueError("independent scene materialization has a non-string key")
        array = np.asarray(data[key])
        if array.ndim and not array.flags.c_contiguous:
            array = np.ascontiguousarray(array)
        if array.dtype.hasobject:
            raise ValueError(f"independent scene materialization object dtype: {key}")
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(b"\0")
        digest.update(
            json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
        )
        digest.update(b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def _load_scene_materialization_evidence(
    *, artifact: Path, receipt: Mapping[str, Any]
) -> tuple[list[dict[str, np.ndarray]], list[str]]:
    reference = receipt.get("causal_scene_materialization_evidence")
    if (
        type(reference) is not dict
        or set(reference) != SCENE_MATERIALIZATION_EVIDENCE_FIELDS
        or reference.get("schema_version")
        != SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION
        or type(reference.get("relative_path")) is not str
        or type(reference.get("sha256")) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])
        or reference["relative_path"]
        != f"causal_scene_materializations/{reference['sha256']}.npz"
        or type(reference.get("tick_count")) is not int
        or reference["tick_count"] != 64
        or type(reference.get("arrays")) is not dict
        or set(reference["arrays"]) != set(SCENE_MATERIALIZATION_ARRAY_SCHEMA)
    ):
        raise ValueError("bounded scene materialization evidence reference drifted")
    path = artifact / reference["relative_path"]
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve().parent
        != (artifact / "causal_scene_materializations").resolve()
        or hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]
    ):
        raise ValueError("bounded scene materialization evidence file/root drifted")
    expected_members = {
        f"{name}.npy" for name in SCENE_MATERIALIZATION_ARRAY_SCHEMA
    }
    try:
        with zipfile.ZipFile(path, "r") as archive:
            members = archive.namelist()
            if len(members) != len(set(members)) or set(members) != expected_members:
                raise ValueError("bounded scene materialization NPZ member set drifted")
            if any(
                info.is_dir()
                or info.filename.startswith(("/", "\\"))
                or ".." in Path(info.filename).parts
                for info in archive.infolist()
            ):
                raise ValueError("bounded scene materialization NPZ member path drifted")
        arrays: dict[str, np.ndarray] = {}
        with np.load(path, allow_pickle=False) as shard:
            if set(shard.files) != set(SCENE_MATERIALIZATION_ARRAY_SCHEMA):
                raise ValueError("bounded scene materialization shard key set drifted")
            for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
                array = np.asarray(shard[name])
                expected_shape = (64, *shape)
                expected_dtype = np.dtype(dtype_name)
                metadata = reference["arrays"].get(name)
                if (
                    array.shape != expected_shape
                    or array.dtype != expected_dtype
                    or not np.isfinite(array).all()
                    or type(metadata) is not dict
                    or set(metadata) != {"dtype", "shape", "sha256"}
                    or metadata.get("dtype") != array.dtype.str
                    or metadata.get("shape") != list(array.shape)
                    or metadata.get("sha256") != _array_sha(array)
                ):
                    raise ValueError(
                        f"bounded scene materialization shard metadata drifted for {name}"
                    )
                arrays[name] = np.array(array, copy=True, order="C")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("bounded scene"):
            raise
        raise ValueError("bounded scene materialization archive is invalid") from exc
    rows = [
        {name: arrays[name][tick_index].copy() for name in arrays}
        for tick_index in range(64)
    ]
    hashes = [_independent_array_mapping_sha256(row) for row in rows]
    return rows, hashes


def _validate_scene_materialization_snapshot_binding(
    *,
    evidence: Mapping[str, np.ndarray],
    scene_materialization: Mapping[str, np.ndarray],
) -> None:
    for name in (
        "ego_current_state",
        "ego_shape",
        "neighbor_agents_past",
        "static_objects",
        "route_lanes",
        "route_lanes_speed_limit",
        "route_lanes_has_speed_limit",
    ):
        if not np.array_equal(evidence[name], scene_materialization[name]):
            raise ValueError(
                f"bounded scene materialization/snapshot binding drifted for {name}"
            )


def _validate_scene_materialization_hash_sequence(
    *, receipt: Mapping[str, Any], hashes: list[str]
) -> None:
    ticks = receipt.get("ticks")
    if (
        type(ticks) is not list
        or len(ticks) != 64
        or type(hashes) is not list
        or len(hashes) != 64
        or any(
            ticks[index].get("scene_materialization_sha256") != hashes[index]
            for index in range(64)
        )
        or receipt.get("initial_scene_materialization_sha256") != hashes[0]
    ):
        raise ValueError("bounded native scene materialization hash sequence drifted")


def _validate_causal_evidence(
    *,
    artifact_root: Path,
    feature: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    native_tick: Mapping[str, Any],
    referenced_shards: set[str],
) -> dict[str, np.ndarray]:
    raw, references = independently_materialize_causal_evidence(
        artifact_root=artifact_root,
        reference=feature.get("causal_evidence"),
    )
    referenced_shards.update(references)
    if (
        type(raw) is not dict
        or set(raw) != CAUSAL_EVIDENCE_FIELDS
        or raw.get("schema_version") != "camp_dp_v25_bounded_causal_evidence_v1"
    ):
        raise ValueError("bounded causal-evidence exact schema drifted")
    arrays = {
        "ego_current_state": _native_numeric_array(raw.get("ego_current_state"), (10,), label="ego state").astype(np.float32),
        "ego_shape": _native_numeric_array(raw.get("ego_shape"), (3,), label="ego shape").astype(np.float32),
        "neighbor_agents_past": _native_numeric_array(raw.get("neighbor_agents_past"), (32, 31, 11), label="neighbor history").astype(np.float32),
        "neighbor_valid_mask": _strict_bool_array(raw.get("neighbor_valid_mask"), (32,), label="neighbor valid"),
        "candidate_neighbor_predictions": _native_numeric_array(raw.get("candidate_neighbor_predictions"), (8, 32, 80, 4), label="candidate neighbors").astype(np.float32),
        "static_objects": _native_numeric_array(raw.get("static_objects"), (5, 10), label="static objects").astype(np.float32),
        "route_lanes": _native_numeric_array(raw.get("route_lanes"), (25, 20, 33), label="route lanes").astype(np.float32),
        "route_lanes_speed_limit": _native_numeric_array(raw.get("route_lanes_speed_limit"), (25, 1), label="route speed limits").astype(np.float32),
        "route_lanes_has_speed_limit": _strict_bool_array(raw.get("route_lanes_has_speed_limit"), (25, 1), label="route has speed limits"),
        "signal_mask": _strict_bool_array(raw.get("signal_mask"), (8,), label="signal mask"),
        "fixed_dp_planned_red_light_cost": _native_numeric_array(raw.get("fixed_dp_planned_red_light_cost"), (8,), label="fixed DP planned red cost"),
    }
    causal_sha = _sha(raw)
    route_sha = _array_sha(arrays["route_lanes"])
    speed_sha = _array_sha(arrays["route_lanes_speed_limit"])
    has_speed_sha = _array_sha(arrays["route_lanes_has_speed_limit"])
    if (
        sidecar.get("causal_evidence_sha256") != causal_sha
        or native_tick.get("causal_evidence_sha256") != causal_sha
        or sidecar.get("route_lanes_sha256") != route_sha
        or native_tick.get("route_lanes_sha256") != route_sha
        or sidecar.get("route_lanes_speed_limit_sha256") != speed_sha
        or native_tick.get("route_lanes_speed_limit_sha256") != speed_sha
        or sidecar.get("route_lanes_has_speed_limit_sha256") != has_speed_sha
        or native_tick.get("route_lanes_has_speed_limit_sha256") != has_speed_sha
        or native_tick.get("candidate_neighbor_sha256")
        != _array_sha(arrays["candidate_neighbor_predictions"])
        or not math.isclose(
            _native_number(
                native_tick.get("pre_decision_speed_mps"),
                label="native pre-decision speed",
            ),
            float(arrays["ego_current_state"][4]),
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    ):
        raise ValueError("bounded raw causal evidence SHA/native binding drifted")
    return arrays


def _independent_route_projection(
    candidates: np.ndarray, route: np.ndarray, limits: np.ndarray, has_limits: np.ndarray
) -> dict[str, np.ndarray]:
    centers_parts: list[np.ndarray] = []
    left_parts: list[np.ndarray] = []
    right_parts: list[np.ndarray] = []
    speed_parts: list[np.ndarray] = []
    flat_limits = limits.reshape(25)
    flat_has = has_limits.reshape(25)
    for slot in range(25):
        valid = np.any(np.abs(route[slot, :, :8]) > 1e-8, axis=1)
        if not valid.any():
            continue
        rows = route[slot, valid].astype(np.float64)
        if rows.shape[0] < 2:
            raise ValueError("bounded route slot has fewer than two points")
        available = bool(flat_has[slot] and np.isfinite(flat_limits[slot]) and flat_limits[slot] > 0.0)
        if not available:
            raise ValueError("bounded route slot lacks its frozen positive speed source")
        centers_parts.append(rows[:, :2])
        left_parts.append(rows[:, 4:6])
        right_parts.append(rows[:, 6:8])
        speed_parts.append(np.full(rows.shape[0], flat_limits[slot] if available else np.nan))
    if not centers_parts:
        raise ValueError("bounded route evidence has no visible route")
    centers = np.concatenate(centers_parts)
    left = np.concatenate(left_parts)
    right = np.concatenate(right_parts)
    point_speeds = np.concatenate(speed_parts)
    delta = np.diff(centers, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    keep = lengths > 1e-6
    if not keep.any():
        raise ValueError("bounded route evidence has no nonzero segment")
    starts = centers[:-1][keep]
    directions = delta[keep] / lengths[keep, None]
    segment_lengths = lengths[keep]
    left_start, left_end = left[:-1][keep], left[1:][keep]
    right_start, right_end = right[:-1][keep], right[1:][keep]
    speed_start, speed_end = point_speeds[:-1][keep], point_speeds[1:][keep]
    arc_starts = np.r_[0.0, np.cumsum(segment_lengths[:-1])]
    lateral = np.empty((8, 80)); left_width = np.empty((8, 80)); right_width = np.empty((8, 80))
    speed = np.empty((8, 80)); arc = np.empty((8, 80))
    for k, trajectory in enumerate(candidates.astype(np.float64)):
        for t, point in enumerate(trajectory[:, :2]):
            relative = point - starts
            along = np.clip(np.einsum("ij,ij->i", relative, directions), 0.0, segment_lengths)
            projected = starts + directions * along[:, None]
            segment = int(np.argmin(np.linalg.norm(point - projected, axis=1)))
            fraction = along[segment] / segment_lengths[segment]
            normal = np.asarray([-directions[segment, 1], directions[segment, 0]])
            l_off = left_start[segment] + fraction * (left_end[segment] - left_start[segment])
            r_off = right_start[segment] + fraction * (right_end[segment] - right_start[segment])
            lateral[k, t] = float((point - projected[segment]) @ normal)
            left_width[k, t] = float(l_off @ normal)
            right_width[k, t] = float(-(r_off @ normal))
            speed[k, t] = speed_start[segment] + fraction * (speed_end[segment] - speed_start[segment])
            arc[k, t] = arc_starts[segment] + along[segment]
    source = np.isfinite(speed).all(axis=1) & (speed > 0.0).all(axis=1)
    if np.any(left_width <= 0.0) or np.any(right_width <= 0.0) or not source.all():
        raise ValueError("bounded projected route boundary/speed source is invalid")
    return {
        "lateral": lateral, "left": left_width, "right": right_width,
        "speed": speed, "arc": arc, "source": source,
    }


def _obb_corners_local(x: float, y: float, heading: float, length: float, width: float, wheelbase: float | None = None) -> np.ndarray:
    c, s = math.cos(heading), math.sin(heading)
    if wheelbase is not None and math.isfinite(wheelbase) and wheelbase > 0.0:
        rear = (length - wheelbase) / 2.0; lo, hi = -rear, length - rear
    else:
        lo, hi = -length / 2.0, length / 2.0
    local = np.asarray([[lo, -width/2], [hi, -width/2], [hi, width/2], [lo, width/2]])
    return local @ np.asarray([[c, -s], [s, c]]).T + np.asarray([x, y])


def _obb_collides_local(a: np.ndarray, b: np.ndarray) -> bool:
    for corners in (a, b):
        for index in range(4):
            edge = corners[(index + 1) % 4] - corners[index]
            axis = np.asarray([-edge[1], edge[0]])
            norm = float(np.linalg.norm(axis))
            if norm < 1e-9:
                continue
            axis /= norm
            pa, pb = a @ axis, b @ axis
            if float(pa.max()) < float(pb.min()) or float(pb.max()) < float(pa.min()):
                return False
    return True


def _independent_physical_mask(
    candidates: np.ndarray, projection: Mapping[str, np.ndarray], evidence: Mapping[str, np.ndarray]
) -> tuple[list[bool], list[list[str]]]:
    neighbors = evidence["candidate_neighbor_predictions"].astype(np.float64)
    valid = evidence["neighbor_valid_mask"]
    history = evidence["neighbor_agents_past"].astype(np.float64)
    static = evidence["static_objects"].astype(np.float64)
    obstacles = np.zeros((8, 37, 80, 5), dtype=np.float64)
    for slot in np.flatnonzero(valid):
        width, length = history[slot, -1, 6:8]
        headings = neighbors[:, slot, :, 2:4]
        if width <= 0.0 or length <= 0.0 or np.any(np.linalg.norm(headings, axis=2) < 1e-6):
            raise ValueError("bounded neighbor OBB evidence is invalid")
        obstacles[:, slot, :, :2] = neighbors[:, slot, :, :2]
        obstacles[:, slot, :, 2] = np.arctan2(headings[:, :, 1], headings[:, :, 0])
        obstacles[:, slot, :, 3] = length; obstacles[:, slot, :, 4] = width
    for slot, row in enumerate(static):
        if not np.any(np.abs(row[:6]) > 1e-8):
            continue
        width, length = row[4:6]
        if np.linalg.norm(row[2:4]) < 0.5 or width <= 0.0 or length <= 0.0:
            raise ValueError("bounded static OBB evidence is invalid")
        obstacles[:, 32 + slot, :, :] = np.asarray([row[0], row[1], math.atan2(row[3], row[2]), length, width])
    lateral, left, right = projection["lateral"], projection["left"], projection["right"]
    lane = ~(((lateral > left + 1.0) | (lateral < -(right + 1.0))).any(axis=1))
    wheelbase, ego_length, ego_width = evidence["ego_shape"].astype(np.float64)
    if wheelbase <= 0.0 or ego_length <= 0.0 or ego_width <= 0.0:
        raise ValueError("bounded ego OBB shape must be finite positive")
    collision_free = np.ones(8, dtype=np.bool_)
    headings = np.arctan2(candidates[:, :, 3], candidates[:, :, 2])
    for k in range(8):
        for t in range(80):
            ego_box = _obb_corners_local(*candidates[k, t, :2], headings[k, t], ego_length, ego_width, wheelbase)
            for obstacle in obstacles[k, :, t]:
                if obstacle[3] <= 0.0 or obstacle[4] <= 0.0:
                    continue
                other = _obb_corners_local(obstacle[0], obstacle[1], obstacle[2], obstacle[3], obstacle[4])
                if _obb_collides_local(ego_box, other):
                    collision_free[k] = False
                    break
            if not collision_free[k]:
                break
    signal = evidence["signal_mask"]
    physical = signal & lane & collision_free
    reasons: list[list[str]] = []
    for k in range(8):
        row: list[str] = []
        if not signal[k]: row.append("signal_source_unavailable")
        if not lane[k]: row.append("lane_corridor")
        if not collision_free[k]: row.append("obb_collision")
        if not projection["source"][k]: row.append("route_speed_source_unavailable")
        reasons.append(row)
    return physical.tolist(), reasons


def _independent_planned_red_cost(candidates: np.ndarray, route: np.ndarray) -> np.ndarray:
    red_rows = route[route[:, :, 10] > 0.5].astype(np.float64)
    if red_rows.size == 0:
        return np.zeros(8, dtype=np.float64)
    valid = np.linalg.norm(red_rows[:, :2], axis=1) > 0.1
    red_rows = red_rows[valid]
    if red_rows.size == 0:
        return np.zeros(8, dtype=np.float64)
    red_xy = red_rows[:, :2]
    red_dir = red_rows[:, 2:4]
    red_dir /= np.maximum(np.linalg.norm(red_dir, axis=1, keepdims=True), 1e-6)
    xy = candidates[:, :, :2].astype(np.float64)
    heading = candidates[:, :, 2:4].astype(np.float64)
    dist = np.linalg.norm(xy[:, :, None, :] - red_xy[None, None, :, :], axis=3)
    aligned = np.einsum("ntd,rd->ntr", heading, red_dir) > 0.5
    speed = np.linalg.norm(np.diff(xy, axis=1), axis=2) / 0.1
    speed = np.concatenate((speed, speed[:, -1:]), axis=1)
    count = ((dist < 3.0) & aligned).any(axis=2) & (speed > 0.5)
    violations = count.sum(axis=1).astype(np.float64)
    return np.where(violations > 0.0, 10.0 + 0.5 * violations, 0.0)


def _independent_raw_context(
    *, evidence: Mapping[str, np.ndarray], candidates: np.ndarray, source_valid: list[bool]
) -> tuple[dict[str, float], dict[str, bool]]:
    ego = evidence["ego_current_state"].astype(np.float64)
    speed = max(float(ego[4]), 0.0); accel = float(ego[6]); yaw = float(ego[9])
    route = evidence["route_lanes"].astype(np.float64)
    rows = []
    for slot in route:
        valid = np.any(np.abs(slot[:, :8]) > 1e-8, axis=1)
        rows.extend(slot[valid])
    route_rows = np.asarray(rows, dtype=np.float64)
    keep = np.r_[True, np.linalg.norm(np.diff(route_rows[:, :2], axis=0), axis=1) > 1e-8]
    route_rows = route_rows[keep]
    delta = np.diff(route_rows[:, :2], axis=0); lengths = np.linalg.norm(delta, axis=1)
    headings = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0])); curvature = np.zeros(len(route_rows))
    if len(headings) > 1:
        interior = np.abs(np.diff(headings)) / np.maximum(0.5 * (lengths[:-1] + lengths[1:]), 1e-8)
        curvature[1:-1] = interior; curvature[0] = interior[0]; curvature[-1] = interior[-1]
    widths = np.linalg.norm(route_rows[:, 4:6], axis=1) + np.linalg.norm(route_rows[:, 6:8], axis=1)
    limits = evidence["route_lanes_speed_limit"].reshape(25).astype(np.float64)
    has = evidence["route_lanes_has_speed_limit"].reshape(25)
    available = limits[has]
    arc = np.r_[0.0, np.cumsum(lengths)]
    states = route_rows[:, 8:13]; known = np.flatnonzero(states[:, :4].sum(axis=1) > 0.5)
    if known.size:
        phase_index = int(np.argmax(states[int(known[0]), :4])); phase = ("green", "yellow", "red", "unknown")[phase_index]
        signal_distance = float(arc[int(known[0])]); phase_known = True
    else:
        phase = "unknown"; signal_distance = float(arc[-1]); phase_known = False
    current = evidence["neighbor_agents_past"].astype(np.float64)[:, -1]
    active = (current[:, 6] > 0.0) & (current[:, 7] > 0.0)
    if active.any():
        neighbors = current[active]; positions = neighbors[:, :2]; distances = np.linalg.norm(positions, axis=1)
        rel_v = neighbors[:, 4:6] - np.asarray([speed, 0.0])
        closing = -np.einsum("ij,ij->i", positions, rel_v) / np.maximum(distances, 1e-6)
        ttc = np.where(closing > 1e-6, distances / closing, 30.0); closest = int(np.argmin(distances))
        neighbor_values = (float(len(neighbors)), float(distances.min()), float(min(ttc.min(), 30.0)), float(closing[closest]), float(np.abs(positions[:, 1]).min()))
    else:
        neighbor_values = (0.0, 100.0, 30.0, 0.0, 100.0)
    xy = candidates[:, :, :2].astype(np.float64); center = np.median(xy, axis=0)
    rms = np.sqrt(np.mean(np.sum((xy - center[None]) ** 2, axis=2), axis=1))
    endpoints = xy[:, -1]; endpoint_std = float(np.sqrt(np.var(endpoints[:, 0]) + np.var(endpoints[:, 1])))
    starts = route_rows[:-1, :2]; route_delta = np.diff(route_rows[:, :2], axis=0); route_lengths = np.linalg.norm(route_delta, axis=1)
    valid_seg = route_lengths > 1e-8; starts = starts[valid_seg]; directions = route_delta[valid_seg] / route_lengths[valid_seg, None]
    seg_lengths = route_lengths[valid_seg]; arc_starts = np.r_[0.0, np.cumsum(route_lengths)[:-1]][valid_seg]
    progress = []
    for candidate_xy in xy:
        relative = candidate_xy[:, None] - starts[None]
        along = np.clip(np.einsum("tsd,sd->ts", relative, directions), 0.0, seg_lengths[None])
        projected = starts[None] + directions[None] * along[:, :, None]
        nearest = np.argmin(np.linalg.norm(candidate_xy[:, None] - projected, axis=2), axis=1)
        progress.append(float(np.max(arc_starts[nearest] + along[np.arange(80), nearest])))
    phase_values = {"red": (1.,0.,0.,0.), "yellow": (0.,1.,0.,0.), "green": (0.,0.,1.,0.), "unknown": (0.,0.,0.,1.)}[phase]
    values = (
        speed, accel, speed*yaw, yaw, float(curvature.mean()), float(curvature.max()),
        float(widths.min()), float(np.median(widths)), float(available.min()), float(available[0]),
        *phase_values, signal_distance, 0.0, *neighbor_values, float(np.median(rms)),
        float(np.median(np.abs(rms - np.median(rms)))), endpoint_std,
        float(np.std(progress)), float(np.mean(source_valid)),
    )
    raw = {name: float(value) for name, value in zip(RAW_CONTEXT_NAMES, values)}
    complete_values = (*([True]*10), *([phase_known]*5), False, *([True]*5), *([True]*5))
    return raw, {name: bool(value) for name, value in zip(RAW_CONTEXT_NAMES, complete_values)}


def _validate_independent_context(
    *,
    feature: Mapping[str, Any],
    evidence: Mapping[str, np.ndarray],
    candidates: np.ndarray,
    source_valid: list[bool],
) -> None:
    expected_raw, expected_complete = _independent_raw_context(
        evidence=evidence, candidates=candidates, source_valid=source_valid
    )
    if (
        not _strict_equal(feature.get("raw_context"), expected_raw)
        or not _strict_equal(feature.get("context_source_complete"), expected_complete)
    ):
        raise ValueError("bounded 26D context differs from independent causal oracle")


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _exact_asset(contract: Mapping[str, Any], *, label: str) -> Path:
    if type(contract) is not dict or set(contract) != {"path", "sha256"}:
        raise ValueError(f"{label} contract drifted")
    path = Path(contract["path"])
    if (
        not path.is_absolute()
        or str(path) != str(path.resolve())
        or path.is_symlink()
        or not path.is_file()
        or _file_sha256(path) != contract["sha256"]
    ):
        raise ValueError(f"{label} path/bytes drifted")
    return path


def _independent_execution_assets(
    *, repo: Path, dp_repo: Path, probe_template: Path
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, str]:
    if (
        str(repo.resolve()) != "/root/autodl-tmp/camp_core"
        or not dp_repo.is_absolute()
        or str(dp_repo) != str(EXPECTED_DP_REPO)
        or dp_repo.is_symlink()
        or dp_repo.resolve() != EXPECTED_DP_REPO.resolve()
        or not probe_template.is_absolute()
        or str(probe_template) != str(EXPECTED_PROBE_TEMPLATE)
        or probe_template.is_symlink()
        or probe_template.resolve() != EXPECTED_PROBE_TEMPLATE.resolve()
    ):
        raise ValueError("independent canonical asset path authority drifted")
    if (
        _git(dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(dp_repo, "status", "--porcelain")
        or _file_sha256(probe_template) != EXPECTED_PROBE_TEMPLATE_SHA256
    ):
        raise ValueError("independent DP/template bytes drifted")
    template = _load(probe_template)
    fixed = template.get("fixed_dp") if type(template) is dict else None
    selector = template.get("selector") if type(template) is dict else None
    if (
        template.get("schema_version") != EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION
        or type(fixed) is not dict
        or set(fixed)
        != {"repo", "head", "checkpoint", "args_json", "native_source_sha256"}
        or fixed.get("repo") != str(EXPECTED_DP_REPO)
        or fixed.get("head") != FIXED_DP_HEAD
        or not _strict_equal(fixed.get("checkpoint"), EXPECTED_FIXED_DP_CHECKPOINT)
        or not _strict_equal(fixed.get("args_json"), EXPECTED_FIXED_DP_ARGS)
        or not _strict_equal(
            fixed.get("native_source_sha256"), EXPECTED_DP_NATIVE_SOURCE_SHA256
        )
        or type(selector) is not dict
        or not _strict_equal(selector.get("weights"), EXPECTED_STATIC_WEIGHTS)
        or selector.get("candidate_k") != 8
        or selector.get("nonnegative_simplex") is not True
        or selector.get("selection_policy") != "v22_source_valid"
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
    ):
        raise ValueError("independent canonical template content drifted")
    scale_path = _exact_asset(EXPECTED_GENERATION_SCALES, label="generation scales")
    weight_path = _exact_asset(EXPECTED_STATIC_WEIGHTS, label="static weights")
    checkpoint = _exact_asset(EXPECTED_FIXED_DP_CHECKPOINT, label="DP checkpoint")
    args_path = _exact_asset(EXPECTED_FIXED_DP_ARGS, label="DP args")
    args_payload = _load(args_path)
    if type(args_payload) is not dict or not args_payload:
        raise ValueError("fixed-DP args JSON content drifted")
    scale_payload = _load(scale_path)
    scales = _native_numeric_array(
        scale_payload.get("scales") if type(scale_payload) is dict else None,
        (14,),
        label="generation scales",
    )
    if np.any(scales <= 0.0):
        raise ValueError("generation scales are not finite positive")
    weights = np.load(weight_path, allow_pickle=False)
    expected_weights = np.asarray(EXPECTED_STATIC_WEIGHT_VALUES, dtype=np.float64)
    if (
        weights.dtype != np.dtype(np.float64)
        or weights.shape != (14,)
        or not np.array_equal(weights, expected_weights)
        or np.any(weights < 0.0)
        or not np.isclose(float(weights.sum()), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("independent static weight content/value drifted")
    native: dict[str, dict[str, str]] = {}
    for relative, expected_sha in EXPECTED_DP_NATIVE_SOURCE_SHA256.items():
        source = dp_repo / relative
        committed = subprocess.run(
            ["git", "show", f"{FIXED_DP_HEAD}:{relative}"],
            cwd=dp_repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        actual = source.read_bytes()
        digest = hashlib.sha256(actual).hexdigest()
        if source.is_symlink() or actual != committed or digest != expected_sha:
            raise ValueError("independent fixed-DP native source drifted")
        native[relative] = {"path": str(source.resolve()), "sha256": digest}
    assets = {
        "probe_template": {
            "path": str(probe_template),
            "sha256": EXPECTED_PROBE_TEMPLATE_SHA256,
            "schema_version": EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION,
        },
        "generation_scales": dict(EXPECTED_GENERATION_SCALES),
        "static_weights": {
            **EXPECTED_STATIC_WEIGHTS,
            "dtype": "float64",
            "shape": [14],
            "values": expected_weights.tolist(),
        },
        "fixed_dp_checkpoint": {
            **EXPECTED_FIXED_DP_CHECKPOINT,
            "size_bytes": checkpoint.stat().st_size,
        },
        "fixed_dp_args_json": {
            **EXPECTED_FIXED_DP_ARGS,
            "content_sha256": _sha(args_payload),
        },
        "native_sources": native,
        "generation_scales_size_bytes": scale_path.stat().st_size,
    }
    return assets, scales, weights, _file_sha256(scale_path)


def _independent_formal_cases() -> dict[str, dict[str, Any]]:
    if (
        not EXPECTED_FORMAL_ARTIFACT.is_absolute()
        or EXPECTED_FORMAL_ARTIFACT.is_symlink()
        or str(EXPECTED_FORMAL_ARTIFACT.resolve()) != str(EXPECTED_FORMAL_ARTIFACT)
    ):
        raise ValueError("independent formal artifact path authority drifted")
    seal = verify_complete_seal(
        EXPECTED_FORMAL_ARTIFACT,
        EXPECTED_FORMAL_ROOT_SHA256,
        label="V25 A1.6.10 independent formal authority",
    )
    if seal["root_sha256"] != EXPECTED_FORMAL_ROOT_SHA256:
        raise ValueError("independent formal root drifted")
    report = _load(EXPECTED_FORMAL_ARTIFACT / "report.json")
    formal = _load(EXPECTED_FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    train = formal.get("train") if type(formal) is dict else None
    if (
        type(report) is not dict
        or report.get("status") != "passed"
        or report.get("mode") != "freeze_formal"
        or formal.get("schema_version")
        != "camp_dp_v25_controlled_corpus_final_plan_v1"
        or formal.get("outcome_blind") is not True
        or formal.get("outcome_fields_consumed") != []
        or formal.get("fresh_b_outcome_opened") is not False
        or type(train) is not list
        or len(train) != 1653
    ):
        raise ValueError("independent formal universe contract drifted")
    executable = [case for case in train if case.get("runner_eligible") is True]
    retained = [case for case in train if case.get("runner_eligible") is False]
    by_id = {str(case.get("scenario_id")): case for case in executable}
    if (
        len(executable) != 1500
        or len(retained) != 153
        or len(by_id) != 1500
        or any(not _is_sha256(scenario_id) for scenario_id in by_id)
        or any(case.get("split") != "train" for case in train)
        or any(case.get("seeds") != [25001] for case in train)
    ):
        raise ValueError("independent formal denominator/seed drifted")
    return by_id


def _independent_spawn_config_payload(
    *, template: Mapping[str, Any], formal_case: Mapping[str, Any]
) -> dict[str, Any]:
    spawn = template.get("spawn_config") if type(template) is dict else None
    parameters = formal_case.get("parameters") if type(formal_case) is dict else None
    if type(spawn) is not dict or type(parameters) is not dict:
        raise ValueError("independent spawn authority is unavailable")
    ego_speed = _native_number(
        parameters.get("ego_speed_mps"), label="formal ego speed"
    )
    payload = dict(spawn)
    payload.update(
        {
            "seed": 25001,
            "max_steps": 64,
            "max_active_npcs": 0,
            "spawn_probability": 0.0,
            "static_npc_count": 0,
            "parked_vehicles_yaml": None,
            "ego_init_speed": ego_speed,
        }
    )
    return payload


def _independent_spawn_config_sha256(
    *, template: Mapping[str, Any], formal_case: Mapping[str, Any]
) -> str:
    payload = _independent_spawn_config_payload(
        template=template, formal_case=formal_case
    )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _independent_route_sha256(
    *, artifact: Path, formal_case: Mapping[str, Any], dp_repo: Path
) -> tuple[Path, str]:
    identity = formal_case.get("route_identity_sha256")
    spec = formal_case.get("route_spec")
    if not _is_sha256(identity) or type(spec) is not dict:
        raise ValueError("independent route identity/spec drifted")
    route_source = dp_repo / "scenario_generation" / "route.py"
    tracked = subprocess.run(
        ["git", "show", f"{FIXED_DP_HEAD}:scenario_generation/route.py"],
        cwd=dp_repo,
        check=True,
        capture_output=True,
    ).stdout
    if route_source.is_symlink() or route_source.read_bytes() != tracked:
        raise ValueError("independent fixed-DP Route source drifted")
    for value in (str(dp_repo), str(dp_repo / "diffusion_planner")):
        if value not in sys.path:
            sys.path.insert(0, value)
    route_module = importlib.import_module("scenario_generation.route")
    if Path(route_module.__file__).resolve() != route_source.resolve():
        raise ValueError("independent Route import escaped canonical fixed DP")
    lanelet_ids = spec.get("lanelet_ids")
    start_pose = _native_numeric_array(
        spec.get("start_pose"), (3,), label="formal route start pose"
    ).astype(np.float32)
    goal_pose = _native_numeric_array(
        spec.get("goal_pose"), (3,), label="formal route goal pose"
    ).astype(np.float32)
    if (
        type(lanelet_ids) is not list
        or not lanelet_ids
        or any(type(value) is not int for value in lanelet_ids)
    ):
        raise ValueError("independent formal route lanelets drifted")
    route = route_module.Route(
        map_path=str(formal_case["source_map_path"]),
        start_pose=start_pose,
        goal_pose=goal_pose,
        start_lanelet_id=lanelet_ids[0],
        goal_lanelet_id=lanelet_ids[-1],
        route_lanelet_ids=list(lanelet_ids),
    )
    expected_sha = hashlib.sha256(pickle.dumps(route)).hexdigest()
    route_path = artifact / "routes" / f"{identity}.pkl"
    if (
        route_path.is_symlink()
        or not route_path.is_file()
        or _file_sha256(route_path) != expected_sha
    ):
        raise ValueError("bounded route bytes differ from independent formal rebuild")
    map_path = Path(str(formal_case.get("source_map_path")))
    if (
        not map_path.is_absolute()
        or map_path.is_symlink()
        or str(map_path.resolve()) != str(map_path)
        or not map_path.is_file()
        or _file_sha256(map_path) != formal_case.get("source_map_sha256")
    ):
        raise ValueError("bounded formal map path/bytes drifted")
    return route_path, expected_sha


_INITIAL_STATE_BUILDERS: dict[str, Any] = {}


def _independent_fixed_dp_initial_speed(
    *,
    builder: Any,
    snapped_xy: np.ndarray,
    heading: float,
    init_speed: float,
    start_lanelet: int,
    explicit_route_ids: list[int],
) -> float:
    """Reproduce the pinned replay generate-history/velocity chain locally."""

    if (
        type(explicit_route_ids) is not list
        or not explicit_route_ids
        or any(type(value) is not int for value in explicit_route_ids)
    ):
        raise ValueError(
            "independent history requires explicit route lanelets before RNG seeding"
        )

    n_steps = 31
    dt = 0.1
    history = np.zeros((n_steps, 3), dtype=np.float32)
    history[-1] = [snapped_xy[0], snapped_xy[1], heading]
    if init_speed < 0.1 or start_lanelet not in builder._cache:
        history[:, 0] = snapped_xy[0]
        history[:, 1] = snapped_xy[1]
        history[:, 2] = heading
    else:
        python_random_state = random.getstate()
        try:
            random.seed(EXPECTED_SEED)
            bw_pts, _ = builder._build_backward_polyline(
                start_lanelet, snapped_xy, heading, n_steps, init_speed, dt
            )
        finally:
            random.setstate(python_random_state)
        bw_pts = np.asarray(bw_pts)
        if (
            bw_pts.ndim != 2
            or bw_pts.shape[1] != 2
            or len(bw_pts) == 0
            or not np.isfinite(bw_pts).all()
        ):
            raise ValueError("independent fixed-DP backward history drifted")
        diffs = np.linalg.norm(np.diff(bw_pts, axis=0), axis=1)
        arc = np.concatenate([[0.0], np.cumsum(diffs)])
        seg_idx = 0
        rng = np.random.RandomState(EXPECTED_SEED)
        for step in range(n_steps - 2, -1, -1):
            backward_dist = (n_steps - 1 - step) * init_speed * dt
            while seg_idx + 1 < len(arc) and arc[seg_idx + 1] < backward_dist:
                seg_idx += 1
            if seg_idx >= len(bw_pts) - 1:
                pos = bw_pts[-1]
                if len(bw_pts) >= 2:
                    fwd = bw_pts[-2] - bw_pts[-1]
                    frame_heading = math.atan2(fwd[1], fwd[0])
                else:
                    frame_heading = heading
            else:
                seg_len = arc[seg_idx + 1] - arc[seg_idx]
                safe_len = max(seg_len, 1e-6)
                fraction = (backward_dist - arc[seg_idx]) / safe_len
                fraction = max(0.0, min(1.0, fraction))
                pos = bw_pts[seg_idx] + fraction * (
                    bw_pts[seg_idx + 1] - bw_pts[seg_idx]
                )
                fwd = bw_pts[seg_idx] - bw_pts[seg_idx + 1]
                frame_heading = math.atan2(fwd[1], fwd[0])
            lateral = np.asarray(
                [-math.sin(frame_heading), math.cos(frame_heading)]
            )
            pos = pos + lateral * rng.normal(0, 0.05)
            history[step] = [pos[0], pos[1], frame_heading]
    history[-1, 2] = heading
    velocities = np.zeros((history.shape[0], 2), dtype=np.float32)
    for index in range(1, history.shape[0]):
        velocities[index] = (history[index, :2] - history[index - 1, :2]) / dt
    velocities[0] = velocities[1]
    return float(np.linalg.norm(velocities[-1]))


def _independent_initial_world_state(
    *, formal_case: Mapping[str, Any], template: Mapping[str, Any], dp_repo: Path
) -> dict[str, Any]:
    spec = formal_case.get("route_spec")
    if type(spec) is not dict:
        raise ValueError("independent initial route spec is unavailable")
    route_ids = spec.get("lanelet_ids")
    start_pose = _native_numeric_array(
        spec.get("start_pose"), (3,), label="formal route start pose"
    ).astype(np.float32)
    if (
        type(route_ids) is not list
        or not route_ids
        or any(type(value) is not int for value in route_ids)
    ):
        raise ValueError("independent initial route lanelets drifted")
    map_path = Path(str(formal_case.get("source_map_path")))
    if (
        not map_path.is_absolute()
        or map_path.is_symlink()
        or str(map_path.resolve()) != str(map_path)
        or not map_path.is_file()
        or _file_sha256(map_path) != formal_case.get("source_map_sha256")
    ):
        raise ValueError("independent initial map authority drifted")
    builder_source = (
        dp_repo / "scenario_generation" / "gui" / "lanelet_scene_builder.py"
    )
    committed = subprocess.run(
        [
            "git",
            "show",
            f"{FIXED_DP_HEAD}:scenario_generation/gui/lanelet_scene_builder.py",
        ],
        cwd=dp_repo,
        check=True,
        capture_output=True,
    ).stdout
    if builder_source.is_symlink() or builder_source.read_bytes() != committed:
        raise ValueError("independent initial-state fixed-DP builder source drifted")
    key = str(map_path)
    builder = _INITIAL_STATE_BUILDERS.get(key)
    if builder is None:
        for value in (str(dp_repo), str(dp_repo / "diffusion_planner")):
            if value not in sys.path:
                sys.path.insert(0, value)
        require_source_preserving_lanelet2_regulatory_adapter(map_path)
        sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
        sys.modules.pop("autoware_lanelet2_extension_python", None)
        install_lanelet2_projection_fallback(map_path)
        module = importlib.import_module(
            "scenario_generation.gui.lanelet_scene_builder"
        )
        if Path(module.__file__).resolve() != builder_source.resolve():
            raise ValueError("independent initial-state builder import escaped fixed DP")
        builder = module.LaneletSceneBuilder(str(map_path))
        _INITIAL_STATE_BUILDERS[key] = builder
    start_lanelet = builder.snap_to_nearest_ll(
        start_pose[:2], candidate_ids=list(route_ids)
    ) or route_ids[0]
    if start_lanelet not in builder._cache:
        raise ValueError("independent snapped start lanelet is unavailable")
    centerline = np.asarray(builder._cache[start_lanelet].raw_centerline)
    if centerline.ndim != 2 or centerline.shape[1] != 2 or not np.isfinite(centerline).all():
        raise ValueError("independent snapped start centerline drifted")
    closest = int(np.argmin(np.linalg.norm(centerline - start_pose[:2], axis=1)))
    snapped_xy = centerline[closest].astype(np.float32)
    spawn = _independent_spawn_config_payload(
        template=template, formal_case=formal_case
    )
    init_speed_raw = spawn.get("ego_init_speed")
    if init_speed_raw is None:
        init_speed = 0.5 * (
            _native_number(spawn.get("npc_min_speed"), label="spawn npc min speed")
            + _native_number(spawn.get("npc_max_speed"), label="spawn npc max speed")
        )
    else:
        init_speed = _native_number(init_speed_raw, label="initial ego history speed")
    heading = float(start_pose[2])
    initial_speed = _independent_fixed_dp_initial_speed(
        builder=builder,
        snapped_xy=snapped_xy,
        heading=heading,
        init_speed=init_speed,
        start_lanelet=start_lanelet,
        explicit_route_ids=list(route_ids),
    )
    return {
        "schema_version": INITIAL_WORLD_STATE_SCHEMA_VERSION,
        "position_xy": [float(snapped_xy[0]), float(snapped_xy[1])],
        "heading_rad": heading,
        "speed_mps": initial_speed,
    }


def _expected_native_header_result(
    *, artifact: Path, native_dir: Path, initial_scene_materialization_sha256: str,
    scene_materialization_evidence: Mapping[str, Any],
    derived_native_result: Mapping[str, Any],
    formal_case: Mapping[str, Any], source_row: Mapping[str, Any],
    template: Mapping[str, Any], dp_repo: Path,
) -> dict[str, Any]:
    if (
        source_row.get("formal_case_sha256") != _sha(formal_case)
        or source_row.get("route_identity_sha256")
        != formal_case.get("route_identity_sha256")
        or source_row.get("source_map_sha256")
        != formal_case.get("source_map_sha256")
        or source_row.get("family") != formal_case.get("family")
        or source_row.get("tier") != formal_case.get("tier")
    ):
        raise ValueError("bounded source row/formal case binding drifted")
    _route_path, route_sha = _independent_route_sha256(
        artifact=artifact, formal_case=formal_case, dp_repo=dp_repo
    )
    if not _is_sha256(initial_scene_materialization_sha256):
        raise ValueError("bounded native initial scene materialization SHA drifted")
    initial_world = _independent_initial_world_state(
        formal_case=formal_case, template=template, dp_repo=dp_repo
    )
    return {
        "schema_version": "camp_dp_v25_a1610_bounded_native_receipt_v2",
        "status": "ok",
        "route_name": formal_case["route_identity_sha256"],
        "route_sha256": route_sha,
        "logical_map_sha256": formal_case["source_map_sha256"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": EXPECTED_FIXED_DP_CHECKPOINT["sha256"],
        "args_sha256": EXPECTED_FIXED_DP_ARGS["sha256"],
        "arm": "camp",
        "scenario_seed": 25001,
        "spawn_config_sha256": _independent_spawn_config_sha256(
            template=template, formal_case=formal_case
        ),
        "initial_world_state_sha256": _sha(initial_world),
        "initial_scene_materialization_sha256": (
            initial_scene_materialization_sha256
        ),
        "native_result": dict(derived_native_result),
        "claim_authorized": False,
        "selector_scale_contract": EXPECTED_SELECTOR_SCALE_CONTRACT,
        "runtime_annotation_compatibility": EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY,
        "causal_scene_materialization_evidence": dict(
            scene_materialization_evidence
        ),
    }


def _validate_native_red_stop_lines(
    *, safety: Mapping[str, Any], source_row: Mapping[str, Any]
) -> None:
    raw = safety.get("red_stop_lines")
    if type(raw) is not list:
        raise ValueError("bounded native red stop-line schema drifted")
    if not safety.get("red_light_at_interval_start"):
        if raw != []:
            raise ValueError("bounded native non-red tick retained stop lines")
        return
    if source_row.get("source_class") != "mapped_signal":
        raise ValueError("bounded native red tick lacks mapped source authority")
    chain = source_row.get("source_chain")
    certified = chain.get("stop_line_geometry_m") if type(chain) is dict else None
    if type(certified) is not list or len(certified) < 2:
        raise ValueError("bounded native red tick lacks certified stop line")
    expected = np.asarray([certified[0], certified[-1]], dtype=np.float64)
    actual = _native_numeric_array(raw, (1, 2, 2), label="native red stop lines")
    if not np.allclose(actual[0], expected, rtol=0.0, atol=1e-6):
        raise ValueError("bounded native red stop line is not the certified source")


def _nonnegative_float32_ulp_distance(left: Any, right: Any) -> int:
    """Return the exact ULP distance between two nonnegative float32 values."""

    left_value = _native_number(left, label="trajectory ego speed")
    right_value = _native_number(right, label="post-tracker ego speed")
    if left_value < 0.0 or right_value < 0.0:
        raise ValueError("bounded native speed must be nonnegative")
    left32 = np.float32(left_value)
    right32 = np.float32(right_value)
    if float(left32) != left_value:
        raise ValueError("bounded trajectory speed is not an exact float32 value")
    left_bits = int(np.asarray([left32], dtype=np.float32).view(np.uint32)[0])
    right_bits = int(np.asarray([right32], dtype=np.float32).view(np.uint32)[0])
    return abs(left_bits - right_bits)


def _validate_fixed_k8_heading_envelope(candidate: np.ndarray) -> np.ndarray:
    if candidate.shape != (8, 80, 4) or candidate.dtype != np.float32:
        raise ValueError("bounded fixed-K8 tensor shape/dtype drifted")
    heading_norms = np.linalg.norm(
        candidate[:, :, 2:4].astype(np.float64), axis=2
    )
    if (
        not np.all(np.isfinite(heading_norms))
        or np.any(heading_norms < FIXED_K8_HEADING_NORM_MIN)
        or np.any(heading_norms > FIXED_K8_HEADING_NORM_MAX)
    ):
        raise ValueError("bounded fixed-K8 heading norm envelope drifted")
    return heading_norms


def _validate_native_log_files(
    *,
    native_dir: Path,
    receipt: Mapping[str, Any],
    formal_case: Mapping[str, Any],
    template: Mapping[str, Any],
    source_row: Mapping[str, Any],
    dp_repo: Path,
) -> dict[str, Any]:
    ticks = receipt["ticks"]
    trajectory_path = native_dir / "trajectory_log.json"
    clearance_path = native_dir / "clearance_log.json"
    if (
        trajectory_path.is_symlink() or clearance_path.is_symlink()
        or not trajectory_path.is_file() or not clearance_path.is_file()
    ):
        raise ValueError("bounded native terminal log files are unavailable")
    trajectory = _load(trajectory_path, canonical=False)
    clearance = _load(clearance_path, canonical=False)
    if type(trajectory) is not list or len(trajectory) != 64:
        raise ValueError("bounded native trajectory log denominator drifted")
    route_spec = formal_case.get("route_spec")
    goal_pose = _native_numeric_array(
        route_spec.get("goal_pose") if type(route_spec) is dict else None,
        (3,),
        label="formal goal pose",
    ).astype(np.float32)
    min_goal_distance = float("inf")
    initial_world = _independent_initial_world_state(
        formal_case=formal_case, template=template, dp_repo=dp_repo
    )
    for index, row in enumerate(trajectory):
        if (
            type(row) is not dict
            or set(row) != {"step", "x", "y", "heading", "speed", "goal_d"}
            or type(row.get("step")) is not int
            or row["step"] != index
        ):
            raise ValueError("bounded native trajectory row schema drifted")
        position = _native_numeric_array(
            [row.get("x"), row.get("y")], (2,), label="trajectory position"
        ).astype(np.float32)
        heading = _native_number(
            row.get("heading"), label="trajectory ego heading"
        )
        speed = _native_number(row.get("speed"), label="trajectory ego speed")
        goal_distance = float(np.linalg.norm(position - goal_pose[:2]))
        min_goal_distance = min(min_goal_distance, goal_distance)
        if (
            type(row.get("goal_d")) is not float
            or _native_number(row["goal_d"], label="trajectory goal distance")
            != goal_distance
        ):
            raise ValueError("bounded native trajectory goal oracle drifted")
        if index == 0 and not np.allclose(
            [position[0], position[1], heading, speed],
            [
                initial_world["position_xy"][0],
                initial_world["position_xy"][1],
                initial_world["heading_rad"],
                initial_world["speed_mps"],
            ],
            rtol=0.0,
            atol=0.0,
        ):
            raise ValueError("bounded trajectory[0] is not the snapped initial world state")
        reason_at_tick: str | None = None
        if goal_distance <= GOAL_TOLERANCE_M:
            reason_at_tick = "goal_reached"
        else:
            forward = np.asarray(
                [math.cos(heading), math.sin(heading)], dtype=np.float32
            )
            to_goal = goal_pose[:2] - position
            if (
                float(np.dot(to_goal, forward)) < 0.0
                and min_goal_distance <= GOAL_PASS_WINDOW_M
            ):
                reason_at_tick = "goal_passed"
        if reason_at_tick is not None:
            raise ValueError(
                "bounded 64-post-safety run cannot coexist with pre-advance "
                f"{reason_at_tick} at trajectory row {index}"
            )
    for index in range(63):
        post_safety = ticks[index]["safety"]
        next_row = trajectory[index + 1]
        if not np.allclose(
            [
                next_row["x"],
                next_row["y"],
                next_row["heading"],
            ],
            [
                post_safety["position_xy"][0],
                post_safety["position_xy"][1],
                post_safety["ego_heading_rad"],
            ],
            rtol=0.0,
            atol=1e-9,
        ) or _nonnegative_float32_ulp_distance(
            next_row["speed"], post_safety["speed_mps"]
        ) > 1:
            raise ValueError("bounded pre/post tracker temporal binding drifted")
    for tick in ticks:
        _validate_native_red_stop_lines(
            safety=tick["safety"], source_row=source_row
        )
    records = clearance.get("records") if type(clearance) is dict else None
    spawn = _independent_spawn_config_payload(
        template=template, formal_case=formal_case
    )
    expected_ego_shape = [
        _native_number(spawn.get(name), label=f"spawn {name}")
        for name in ("ego_wheelbase", "ego_length", "ego_width")
    ]
    if (
        type(clearance) is not dict
        or set(clearance) != {"ego_shape", "max_range_m", "png_dir", "records"}
        or type(clearance.get("ego_shape")) is not list
        or len(clearance["ego_shape"]) != 3
        or any(type(value) is not float for value in clearance["ego_shape"])
        or not np.allclose(
            clearance["ego_shape"], expected_ego_shape, rtol=0.0, atol=1e-12
        )
        or type(clearance.get("max_range_m")) is not float
        or clearance["max_range_m"] != EXPECTED_CLEARANCE_MAX_RANGE_M
        or clearance.get("png_dir") != str(native_dir)
        or type(records) is not list or len(records) != 64
    ):
        raise ValueError("bounded native clearance log contract drifted")
    fields = {"step", "ego_x", "ego_y", "ego_yaw", "rb_dist", "stopped_dist",
              "stopped_id", "moving_dist", "moving_id", "png"}
    for index, (row, trajectory_row) in enumerate(zip(records, trajectory)):
        if (
            type(row) is not dict or set(row) != fields
            or type(row.get("step")) is not int or row["step"] != index
            or row.get("png") != f"step_{index:04d}.png"
            or not np.allclose(
                [row.get("ego_x"), row.get("ego_y"), row.get("ego_yaw")],
                [trajectory_row["x"], trajectory_row["y"],
                 trajectory_row["heading"]], rtol=0.0, atol=1e-9,
            )
        ):
            raise ValueError("bounded clearance/pre-advance trajectory binding drifted")
        for field in ("rb_dist", "stopped_dist", "moving_dist"):
            if row[field] is not None:
                if (
                    type(row[field]) is not float
                    or _native_number(row[field], label=f"clearance {field}") < 0.0
                ):
                    raise ValueError("bounded native clearance distance drifted")
        for distance_field, id_field in (
            ("stopped_dist", "stopped_id"),
            ("moving_dist", "moving_id"),
        ):
            identifier = row[id_field]
            if row[distance_field] is None:
                if identifier is not None:
                    raise ValueError("bounded native clearance ID/source drifted")
            elif type(identifier) is not str or not identifier:
                raise ValueError("bounded native clearance ID/source drifted")
    return {
        "final_step": 63,
        "goal_reached": False,
        "reason": "max_steps",
        "n_npc_spawned": 0,
        "trajectory_log_path": str(trajectory_path),
        "clearance_log_path": str(clearance_path),
    }


def _strict_int_list(value: Any, *, label: str, nonempty: bool = False) -> list[int]:
    if (
        type(value) is not list
        or (nonempty and not value)
        or any(type(item) is not int for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"{label} must be a unique native-int list")
    return list(value)


def _validate_semantic_payload(payload: Any, *, mapped: bool) -> dict[str, Any]:
    allowed = SEMANTIC_REQUIRED_FIELDS | ({"stop_line_local_m"} if mapped else set())
    if (
        type(payload) is not dict
        or set(payload) != allowed
        or payload.get("schema_version") != "camp_dp_v25_semantic_clone_payload_v3"
        or any(type(payload.get(key)) is not str or not payload[key] for key in ("family", "tier", "semantic_variant"))
        or type(payload.get("parameters")) is not dict
        or type(payload.get("actors")) is not list
        or type(payload.get("signal")) is not dict
        or set(payload["signal"])
        != {"current_phase", "mapped_source_required", "source_mode"}
        or payload["signal"].get("source_mode") != "no_v2i"
        or type(payload["signal"].get("mapped_source_required")) is not bool
    ):
        raise ValueError("independent semantic-v3 payload schema drifted")
    forbidden = ("future", "outcome", "fresh", "holdout", "split", "scenario_id", "route_id", "map_id")
    if any(any(token in str(key).lower() for token in forbidden) for key in payload["parameters"]):
        raise ValueError("semantic payload contains forbidden authority proxy")
    if any(
        type(value) not in (int, float) or not math.isfinite(float(value))
        for value in payload["parameters"].values()
    ):
        raise ValueError("semantic parameters are not finite native numbers")
    for actor in payload["actors"]:
        if type(actor) is not dict or set(actor) != SEMANTIC_ACTOR_FIELDS:
            raise ValueError("semantic actor schema drifted")
        for vector in (
            "initial_xy_local_m",
            "initial_heading_local_unit",
            "route_tangent_local",
            "route_normal_local",
        ):
            values = _native_numeric_array(actor.get(vector), (2,), label=vector)
            if vector != "initial_xy_local_m" and not np.isclose(
                np.linalg.norm(values), 1.0, rtol=0.0, atol=2e-6
            ):
                raise ValueError("semantic actor route frame is not unit")
    route = _native_numeric_array(
        payload.get("route_polyline_local_m"), (64, 2), label="semantic route"
    )
    if not np.allclose(route[0], np.zeros(2), rtol=0.0, atol=1e-9):
        raise ValueError("semantic route local origin drifted")
    if mapped:
        stop = payload.get("stop_line_local_m")
        if type(stop) is not list or len(stop) < 2:
            raise ValueError("semantic mapped stop line is absent")
        _native_numeric_array(stop, (len(stop), 2), label="semantic stop line")
    return payload


def _validate_source_row(row: Any) -> dict[str, Any]:
    if (
        type(row) is not dict
        or set(row) != SOURCE_ROW_FIELDS
        or not _is_sha256(row.get("scenario_id"))
        or not _is_sha256(row.get("formal_case_sha256"))
        or not _is_sha256(row.get("source_map_sha256"))
        or not _is_sha256(row.get("route_identity_sha256"))
        or row.get("runner_eligible") is not True
        or row.get("retention_role") != "executable"
        or type(row.get("family")) is not str
        or type(row.get("tier")) is not str
        or type(row.get("seed")) is not int
        or row["seed"] != 25001
        or type(row.get("actual_mapped_signal")) is not bool
        or type(row.get("id_free_tensor_layout")) is not dict
    ):
        raise ValueError("sealed route-source row schema/type drifted")
    chain = row.get("source_chain")
    mapped = row.get("source_class") == "mapped_signal"
    if mapped:
        if (
            row.get("actual_mapped_signal") is not True
            or row.get("phase_authority_mode")
            not in {"controlled_same_tick_override", "observe_same_tick_request"}
            or type(chain) is not dict
            or set(chain) != MAPPED_CHAIN_FIELDS
            or chain.get("schema_version")
            != "camp_dp_v25_family_independent_mapped_signal_source_chain_v1"
        ):
            raise ValueError("mapped route-source authority drifted")
        mode = chain.get("phase_authority_mode")
        expected_phase = chain.get("expected_current_phase")
        formal_phase = chain.get("formal_phase")
        formal_required = chain.get("formal_mapped_source_required")
        if (
            chain.get("formal_route_mapped_traffic_light") is not True
            or chain.get("phase_remaining_available") is not False
            or (
                mode == "controlled_same_tick_override"
                and (
                    expected_phase not in {"green", "yellow", "red"}
                    or formal_phase != expected_phase
                    or formal_required is not True
                )
            )
            or (
                mode == "observe_same_tick_request"
                and (
                    expected_phase is not None
                    or formal_phase != "none"
                    or formal_required is not False
                )
            )
        ):
            raise ValueError("mapped controlled/observe phase authority drifted")
        for field in (
            "scenario_id", "route_identity_sha256", "source_map_sha256",
            "route_geometry_sha256", "stop_line_geometry_sha256",
            "semantic_clone_sha256", "source_chain_sha256",
        ):
            if not _is_sha256(chain.get(field)):
                raise ValueError("mapped chain SHA field drifted")
        regulatory = _strict_int_list(chain.get("regulatory_element_ids"), label="regulatory IDs", nonempty=True)
        physical = _strict_int_list(chain.get("physical_light_ids"), label="physical IDs", nonempty=True)
        bulbs = _strict_int_list(chain.get("bulb_ids"), label="bulb IDs", nonempty=True)
        controlled = _strict_int_list(chain.get("controlled_lanelet_ids"), label="controlled lanelets", nonempty=True)
        route_ids = _strict_int_list(chain.get("route_lanelet_ids"), label="route lanelets", nonempty=True)
        if len(regulatory) != 1 or not physical or not bulbs or not set(controlled) <= set(route_ids):
            raise ValueError("mapped regulatory chain relation drifted")
        stop_raw = chain.get("stop_line_geometry_m")
        if type(stop_raw) is not list or len(stop_raw) < 2:
            raise ValueError("mapped certified stop line is absent")
        stop = _native_numeric_array(stop_raw, (len(stop_raw), 2), label="certified stop line")
        tangent = _native_numeric_array(chain.get("route_tangent_world"), (2,), label="route tangent")
        if (
            type(chain.get("stop_line_id")) is not int
            or _sha(stop.tolist()) != chain["stop_line_geometry_sha256"]
            or not np.isclose(np.linalg.norm(tangent), 1.0, rtol=0.0, atol=1e-6)
        ):
            raise ValueError("mapped stop-line/tangent authority drifted")
        semantic = _validate_semantic_payload(chain.get("semantic_clone_payload"), mapped=True)
        if (
            row["scenario_id"] != chain["scenario_id"]
            or row["route_identity_sha256"] != chain["route_identity_sha256"]
            or row["source_map_sha256"] != chain["source_map_sha256"]
            or row["phase_authority_mode"] != chain["phase_authority_mode"]
            or chain["route_geometry_sha256"]
            != _sha({"route_polyline_local_m": semantic["route_polyline_local_m"], "stop_line_local_m": semantic["stop_line_local_m"]})
            or chain["semantic_clone_sha256"] != _sha(semantic)
            or chain["source_chain_sha256"]
            != _sha({key: value for key, value in chain.items() if key != "source_chain_sha256"})
        ):
            raise ValueError("mapped source-chain hash/row binding drifted")
    elif row.get("source_class") == "no_signal":
        if (
            row.get("actual_mapped_signal") is not False
            or row.get("phase_authority_mode") is not None
            or type(chain) is not dict
            or set(chain) != NO_SIGNAL_CHAIN_FIELDS
            or chain.get("schema_version") != "camp_dp_v25_no_signal_source_chain_v1"
            or chain.get("traffic_light_regulatory_element_ids") != []
        ):
            raise ValueError("no-signal route-source authority drifted")
        route_ids = _strict_int_list(chain.get("route_lanelet_ids"), label="no-signal route lanelets", nonempty=True)
        semantic = _validate_semantic_payload(chain.get("semantic_clone_payload"), mapped=False)
        if (
            not route_ids
            or row["scenario_id"] != chain.get("scenario_id")
            or row["route_identity_sha256"] != chain.get("route_identity_sha256")
            or row["source_map_sha256"] != chain.get("source_map_sha256")
            or chain.get("route_geometry_sha256")
            != _sha({"route_polyline_local_m": semantic["route_polyline_local_m"]})
            or chain.get("semantic_clone_sha256") != _sha(semantic)
            or chain.get("source_chain_sha256")
            != _sha({key: value for key, value in chain.items() if key != "source_chain_sha256"})
        ):
            raise ValueError("no-signal source-chain hash/row binding drifted")
    else:
        raise ValueError("route-source class is invalid")
    if mapped:
        _validate_signal_receipts(
            sidecar={
                "signal_source_class": row["source_class"],
                "phase_authority_mode": row["phase_authority_mode"],
                "controlled_signal_source_receipt": row["runtime_receipt"],
                "controlled_signal_tensor_evidence": row["tensor_evidence"],
            },
            source_row=row,
            tick_index=0,
        )
    elif row.get("runtime_receipt") is not None or row.get("tensor_evidence") is not None:
        raise ValueError("source-only no-signal runtime evidence must be absent")
    return row


def _signal_row_oracle(rows: Any, *, label: str) -> tuple[list[int], str]:
    if type(rows) is not list or not rows:
        raise ValueError(f"{label} signal rows are absent")
    ids: list[int] = []
    phases: set[str] = set()
    for row in rows:
        if (
            type(row) is not dict
            or set(row) != {"lanelet_id", "signal_channels_8_12"}
            or type(row.get("lanelet_id")) is not int
        ):
            raise ValueError(f"{label} signal row schema drifted")
        raw = row.get("signal_channels_8_12")
        if type(raw) is not list or not raw:
            raise ValueError(f"{label} signal row tensor is absent")
        values = _native_numeric_array(raw, (len(raw), 5), label=f"{label} signal rows")
        active = np.any(values != 0.0, axis=1)
        if not np.any(active):
            raise ValueError(f"{label} signal row has no active source")
        phase_for_row: set[str] = set()
        for vector in values[active]:
            matches = []
            for phase, column in (("green", 0), ("yellow", 1), ("red", 2)):
                expected = np.zeros(5, dtype=np.float64)
                expected[column] = 1.0
                if np.array_equal(vector, expected):
                    matches.append(phase)
            if len(matches) != 1:
                raise ValueError(f"{label} signal row is non-one-hot/multiphase")
            phase_for_row.add(matches[0])
        if len(phase_for_row) != 1:
            raise ValueError(f"{label} signal row phase is not uniform")
        ids.append(row["lanelet_id"])
        phases.update(phase_for_row)
    if len(ids) != len(set(ids)) or len(phases) != 1:
        raise ValueError(f"{label} signal rows are duplicated/conflicting")
    return ids, next(iter(phases))


def _validate_signal_receipts(
    *, sidecar: Mapping[str, Any], source_row: Mapping[str, Any], tick_index: int
) -> dict[str, Any]:
    source_class = sidecar.get("signal_source_class")
    phase_mode = sidecar.get("phase_authority_mode")
    chain = source_row["source_chain"]
    receipt = sidecar.get("controlled_signal_source_receipt")
    evidence = sidecar.get("controlled_signal_tensor_evidence")
    if type(receipt) is not dict:
        raise ValueError("runtime signal receipt is absent")
    if source_class == "mapped_signal":
        if (
            set(receipt) != MAPPED_RECEIPT_FIELDS
            or receipt.get("schema_version")
            != "camp_dp_v25_family_independent_current_signal_receipt_v1"
            or phase_mode != source_row["phase_authority_mode"]
            or receipt.get("phase_authority_mode") != phase_mode
            or receipt.get("scenario_id") != source_row["scenario_id"]
            or type(receipt.get("tick_index")) is not int
            or receipt["tick_index"] != tick_index
            or receipt.get("current_phase") not in {"green", "yellow", "red"}
            or any(
                type(receipt.get(name)) is not float
                or not math.isfinite(receipt[name])
                for name in ("decision_timestamp_s", "source_timestamp_s", "source_age_s")
            )
            or receipt.get("decision_timestamp_s") != 0.1 * tick_index
            or receipt.get("source_timestamp_s") != receipt.get("decision_timestamp_s")
            or receipt.get("source_age_s") != 0.0
            or receipt.get("freshness") != "same_tick"
            or receipt.get("source_id")
            != "fixed_dp_current_request_route_map_signal_one_hot"
            or receipt.get("phase_remaining_available") is not False
            or receipt.get("source_valid") is not True
            or type(receipt.get("applicable")) is not bool
            or receipt["applicable"] is not (receipt["current_phase"] == "red")
            or (
                phase_mode == "controlled_same_tick_override"
                and receipt.get("current_phase")
                != chain.get("expected_current_phase")
            )
            or (
                phase_mode == "observe_same_tick_request"
                and chain.get("expected_current_phase") is not None
            )
        ):
            raise ValueError("mapped same-tick receipt contract drifted")
        regulatory = chain["regulatory_element_ids"]
        if (
            receipt.get("regulatory_element_id") != regulatory[0]
            or receipt.get("physical_light_ids") != chain["physical_light_ids"]
            or receipt.get("bulb_ids") != chain["bulb_ids"]
            or receipt.get("controlled_lanelet_ids") != chain["controlled_lanelet_ids"]
            or receipt.get("stop_line_id") != chain["stop_line_id"]
            or receipt.get("stop_line_geometry_sha256")
            != chain["stop_line_geometry_sha256"]
            or receipt.get("route_geometry_sha256") != chain["route_geometry_sha256"]
            or receipt.get("route_arc_m") != chain["route_arc_m"]
            or receipt.get("source_chain_sha256") != chain["source_chain_sha256"]
            or type(evidence) is not dict
            or set(evidence) != SIGNAL_TENSOR_FIELDS
            or evidence.get("schema_version")
            != "camp_dp_v25_production_signal_tensor_evidence_v2"
            or evidence.get("tick_index") != tick_index
            or evidence.get("decision_timestamp_s") != receipt["decision_timestamp_s"]
            or evidence.get("source_timestamp_s") != receipt["source_timestamp_s"]
            or evidence.get("current_phase") != receipt["current_phase"]
            or evidence.get("future_schedule_consumed") is not False
            or evidence.get("phase_remaining_available") is not False
        ):
            raise ValueError("mapped regulatory/tensor receipt binding drifted")
        route_ids, route_phase = _signal_row_oracle(
            evidence["route_signal_rows"], label="route"
        )
        map_ids, map_phase = _signal_row_oracle(evidence["map_signal_rows"], label="map")
        if (
            route_phase != receipt["current_phase"]
            or map_phase != receipt["current_phase"]
            or route_ids != receipt["observed_route_lanelet_ids"]
            or map_ids != receipt["observed_map_lanelet_ids"]
            or not set(route_ids + map_ids) <= set(chain["controlled_lanelet_ids"])
            or _sha(evidence["route_signal_rows"])
            != receipt["route_signal_tensor_sha256"]
            or _sha(evidence["map_signal_rows"])
            != receipt["map_signal_tensor_sha256"]
            or evidence["route_signal_tensor_sha256"]
            != receipt["route_signal_tensor_sha256"]
            or evidence["map_signal_tensor_sha256"]
            != receipt["map_signal_tensor_sha256"]
        ):
            raise ValueError("mapped current tensor/source-chain evidence drifted")
    elif source_class == "no_signal":
        if (
            phase_mode is not None
            or evidence is not None
            or set(receipt) != NO_SIGNAL_RECEIPT_FIELDS
            or receipt.get("schema_version") != "camp_dp_v25_runtime_signal_receipt_v2"
            or receipt.get("scenario_id") != source_row["scenario_id"]
            or type(receipt.get("tick_index")) is not int
            or receipt["tick_index"] != tick_index
            or type(receipt.get("decision_time_s")) is not float
            or receipt["decision_time_s"] != 0.1 * tick_index
            or receipt.get("source_mode") != "same_tick_no_signal_rule_no_v2i"
            or receipt.get("current_phase") != "none"
            or receipt.get("route_geometry_sha256") != chain["route_geometry_sha256"]
            or receipt.get("route_lanelet_ids") != chain["route_lanelet_ids"]
            or receipt.get("traffic_light_regulatory_element_ids") != []
            or receipt.get("source_chain_sha256") != chain["source_chain_sha256"]
            or receipt.get("semantic_clone_sha256") != chain["semantic_clone_sha256"]
            or receipt.get("phase_remaining_available") is not False
            or receipt.get("source_valid") is not True
            or receipt.get("applicable") is not False
        ):
            raise ValueError("same-tick no-signal receipt contract drifted")
    else:
        raise ValueError("runtime source class drifted")
    return receipt


def _validate_causal_signal(
    *, sidecar: Mapping[str, Any], source_row: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    causal = sidecar.get("causal_signal_atom_input")
    chain = source_row["source_chain"]
    if (
        type(causal) is not dict
        or set(causal) != CAUSAL_SIGNAL_FIELDS
        or causal.get("schema_version") != "camp_dp_v25_causal_signal_atom_input_v2"
        or causal.get("runtime_receipt_sha256") != _sha(receipt)
        or not _strict_equal(causal.get("runtime_receipt"), receipt)
        or causal.get("source_valid") is not True
        or type(causal.get("applicable")) is not bool
        or causal.get("source_chain_sha256") != chain["source_chain_sha256"]
        or causal.get("route_geometry_sha256") != chain["route_geometry_sha256"]
    ):
        raise ValueError("causal signal input receipt/hash binding drifted")
    if source_row["source_class"] == "mapped_signal":
        if (
            causal.get("source_state") != "available"
            or causal.get("current_phase") != receipt["current_phase"]
            or causal.get("applicable") is not (receipt["current_phase"] == "red")
            or causal.get("decision_time_s") != receipt["decision_timestamp_s"]
            or causal.get("regulatory_element_id") != chain["regulatory_element_ids"][0]
            or causal.get("stop_line_id") != chain["stop_line_id"]
            or causal.get("stop_line_geometry_sha256")
            != chain["stop_line_geometry_sha256"]
            or causal.get("route_arc_m") != chain["route_arc_m"]
        ):
            raise ValueError("mapped causal source-state binding drifted")
        stop_world = _native_numeric_array(
            causal.get("stop_line_geometry_world_m"),
            (len(chain["stop_line_geometry_m"]), 2),
            label="causal world stop line",
        )
        stop_ego = _native_numeric_array(
            causal.get("stop_line_geometry_ego_m"), stop_world.shape,
            label="causal ego stop line",
        )
        ego = _native_numeric_array(
            causal.get("ego_position_world_m"), (2,), label="causal ego position"
        )
        heading = _native_number(causal.get("ego_heading_rad"), label="causal ego heading")
        tangent_world = _native_numeric_array(
            causal.get("route_tangent_world"), (2,), label="causal tangent world"
        )
        tangent_ego = _native_numeric_array(
            causal.get("route_tangent_ego"), (2,), label="causal tangent ego"
        )
        c, s = math.cos(heading), math.sin(heading)
        rotation = np.asarray([[c, s], [-s, c]], dtype=np.float64)
        if (
            not np.array_equal(stop_world, np.asarray(chain["stop_line_geometry_m"], dtype=np.float64))
            or not np.allclose(stop_ego, (stop_world - ego) @ rotation.T, rtol=0.0, atol=1e-12)
            or not np.array_equal(tangent_world, np.asarray(chain["route_tangent_world"], dtype=np.float64))
            or not np.allclose(tangent_ego, rotation @ tangent_world, rtol=0.0, atol=1e-12)
        ):
            raise ValueError("certified stop-line ego-frame transform drifted")
    else:
        null_fields = {
            "ego_position_world_m", "ego_heading_rad", "regulatory_element_id",
            "stop_line_id", "stop_line_geometry_world_m", "stop_line_geometry_ego_m",
            "stop_line_geometry_sha256", "route_tangent_world", "route_tangent_ego",
            "route_arc_m",
        }
        if (
            causal.get("source_state") != "not_applicable"
            or causal.get("current_phase") != "none"
            or causal.get("applicable") is not False
            or causal.get("decision_time_s") != receipt["decision_time_s"]
            or any(causal.get(field) is not None for field in null_fields)
        ):
            raise ValueError("no-signal causal source-state drifted")
    return causal


def _validate_context(
    *, feature: Mapping[str, Any], sidecar: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    raw = feature.get("raw_context")
    complete = feature.get("context_source_complete")
    context_receipt = sidecar.get("context_source_receipt")
    if (
        sidecar.get("context_schema_version") != "camp_dp_v25_causal_context_raw_v2"
        or type(raw) is not dict
        or set(raw) != set(RAW_CONTEXT_NAMES)
        or type(complete) is not dict
        or set(complete) != set(RAW_CONTEXT_NAMES)
        or any(type(raw[name]) is not float or not math.isfinite(raw[name]) for name in RAW_CONTEXT_NAMES)
        or any(type(complete[name]) is not bool for name in RAW_CONTEXT_NAMES)
        or type(context_receipt) is not dict
        or set(context_receipt)
        != {"mode", "phase_remaining_available", "regulatory_signal_mapped"}
        or context_receipt.get("mode") != "no_v2i"
        or context_receipt.get("phase_remaining_available") is not False
        or type(context_receipt.get("regulatory_signal_mapped")) is not bool
        or raw["traffic_signal_phase_remaining_s"] != 0.0
        or complete["traffic_signal_phase_remaining_s"] is not False
    ):
        raise ValueError("bounded exact 26D no-V2I context contract drifted")
    phase_names = (
        "traffic_phase_red",
        "traffic_phase_yellow",
        "traffic_phase_green",
        "traffic_phase_unknown",
    )
    phase = np.asarray([raw[name] for name in phase_names], dtype=np.float64)
    if not np.array_equal(phase, np.eye(4, dtype=np.float64)[int(np.argmax(phase))]):
        raise ValueError("bounded context signal phase is not exact one-hot")
    expected_phase = receipt.get("current_phase")
    expected_index = {"red": 0, "yellow": 1, "green": 2, "none": 3}.get(expected_phase)
    mapped = sidecar.get("signal_source_class") == "mapped_signal"
    if (
        expected_index is None
        or int(np.argmax(phase)) != expected_index
        or context_receipt["regulatory_signal_mapped"] is not mapped
        or any(complete[name] is not mapped for name in phase_names[:3])
        or complete["traffic_phase_unknown"] is not mapped
        or complete["traffic_signal_distance_m"] is not mapped
    ):
        raise ValueError("bounded 26D context/source receipt phase binding drifted")


def _validate_cache(
    *, sidecar: Mapping[str, Any], source_row: Mapping[str, Any], tick_index: int
) -> None:
    cache = sidecar.get("controlled_model_input_cache_receipt")
    mode = source_row["phase_authority_mode"]
    if (
        type(cache) is not dict
        or set(cache) != CACHE_RECEIPT_FIELDS
        or cache.get("schema_version")
        != "camp_dp_v25_model_input_signal_cache_receipt_v1"
        or cache.get("scenario_id") != source_row["scenario_id"]
        or type(cache.get("tick_index")) is not int
        or cache["tick_index"] != tick_index
        or cache.get("signal_source_class") != source_row["source_class"]
        or cache.get("phase_authority_mode") != mode
        or any(
            not _is_sha256(cache.get(field))
            for field in (
                "scene_map_tl_sha256",
                "model_cache_tl_sha256_before",
                "model_cache_tl_sha256_after",
                "model_route_lanes_tl_sha256",
            )
        )
        or cache.get("model_cache_tl_sha256_after")
        != cache.get("scene_map_tl_sha256")
        or cache.get("cache_matches_scene_after") is not True
        or type(cache.get("observe_cache_unchanged")) is not bool
        or cache.get("sync_applied_before_tensor_conversion") is not True
        or cache.get("future_schedule_consumed") is not False
        or cache.get("phase_remaining_available") is not False
        or (
            mode != "controlled_same_tick_override"
            and cache.get("observe_cache_unchanged") is not True
        )
        or (
            mode != "controlled_same_tick_override"
            and cache.get("model_cache_tl_sha256_before")
            != cache.get("model_cache_tl_sha256_after")
        )
    ):
        raise ValueError("bounded model-consumed cache contract drifted")


def _independent_red_stopping_oracle(
    candidates: np.ndarray, causal: Mapping[str, Any], dt_s: float
) -> np.ndarray:
    """Independent scalar implementation of the frozen stopping envelope."""
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.shape != (8, 80, 4) or not np.isfinite(trajectories).all():
        raise ValueError("red stopping oracle requires finite [8,80,4]")
    if type(dt_s) is not float or not math.isfinite(dt_s) or dt_s != 0.1:
        raise ValueError("red stopping oracle dt contract drifted")
    if causal.get("applicable") is not True:
        return np.zeros(8, dtype=np.float64)
    raw_stop = causal.get("stop_line_geometry_ego_m")
    if type(raw_stop) is not list or len(raw_stop) < 2:
        raise ValueError("red stopping oracle lacks certified stop line")
    stop = _native_numeric_array(raw_stop, (len(raw_stop), 2), label="stop line ego")
    tangent = _native_numeric_array(causal.get("route_tangent_ego"), (2,), label="route tangent ego")
    norm = float(np.linalg.norm(tangent))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("red stopping oracle tangent is invalid")
    direction = (tangent / norm)[None, :]
    red_xy = stop.mean(axis=0)[None, :]
    costs = np.zeros(8, dtype=np.float64)
    for candidate_index, trajectory in enumerate(trajectories):
        xy = trajectory[:, :2]
        speeds = np.linalg.norm(np.diff(xy, axis=0), axis=1) / dt_s
        headings = np.arctan2(trajectory[:, 3], trajectory[:, 2])[1:]
        heading_vectors = np.column_stack((np.cos(headings), np.sin(headings)))
        relative = red_xy[None, :, :] - xy[1:, None, :]
        distances = np.linalg.norm(relative, axis=2)
        aligned = heading_vectors @ direction.T > 0.5
        ahead = np.einsum("trd,td->tr", relative, heading_vectors) > 0.0
        eligible = aligned & ahead & (distances <= 40.0)
        nearest = np.min(np.where(eligible, distances, np.inf), axis=1)
        active = np.isfinite(nearest)
        if not np.any(active):
            continue
        safe_speed = np.sqrt(4.0 * np.maximum(nearest[active] - 3.0, 0.0))
        excess = np.maximum(speeds[active] - safe_speed, 0.0)
        proximity = np.maximum(1.0 - nearest[active] / 40.0, 0.0)
        costs[candidate_index] = dt_s * float(np.sum(proximity * excess**2))
    if not np.all(np.isfinite(costs)) or np.any(costs < 0.0):
        raise ValueError("red stopping oracle violated finite/nonnegative contract")
    return costs


def _strict_bool_mask(value: Any, *, label: str) -> list[bool]:
    if (
        type(value) is not list
        or len(value) != 8
        or any(type(item) is not bool for item in value)
    ):
        raise ValueError(f"{label} must be native bool[8]")
    return list(value)


def _validate_native_source_context(
    *,
    native_tick: Mapping[str, Any],
    feature: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    source_row: Mapping[str, Any],
    tick_index: int,
) -> None:
    """Bind native-hook source/context evidence to the persisted snapshot."""

    if native_tick.get("status") != "ok":
        raise ValueError("bounded native tick is not successful")
    controlled = native_tick.get("controlled_scene")
    expected_controlled_fields = {
        "scenario_id",
        "tick_index",
        "sim_time_s",
        "actor_count",
        "actors",
        "signal",
        "outcome_fields_consumed",
        "candidate_tensor_consumed",
        "selected_trajectory_consumed",
        "model_input_cache",
    }
    if (
        type(controlled) is not dict
        or set(controlled) != expected_controlled_fields
        or controlled.get("scenario_id") != source_row["scenario_id"]
        or type(controlled.get("tick_index")) is not int
        or controlled["tick_index"] != tick_index
        or type(controlled.get("sim_time_s")) is not float
        or controlled["sim_time_s"] != 0.1 * tick_index
        or type(controlled.get("actor_count")) is not int
        or type(controlled.get("actors")) is not list
        or controlled["actor_count"] != len(controlled["actors"])
        or controlled.get("outcome_fields_consumed") != []
        or controlled.get("candidate_tensor_consumed") is not False
        or controlled.get("selected_trajectory_consumed") is not False
        or not _strict_equal(
            controlled.get("model_input_cache"),
            sidecar.get("controlled_model_input_cache_receipt"),
        )
    ):
        raise ValueError("bounded native controlled-scene binding drifted")
    signal = controlled.get("signal")
    mapped = source_row["source_class"] == "mapped_signal"
    expected_signal_fields = {
        "phase",
        "source_row_count",
        "applied",
        "source_receipt",
    } | ({"tensor_evidence"} if mapped else set())
    receipt = sidecar.get("controlled_signal_source_receipt")
    if (
        type(signal) is not dict
        or type(receipt) is not dict
        or set(signal) != expected_signal_fields
        or signal.get("phase") != receipt.get("current_phase")
        or type(signal.get("source_row_count")) is not int
        or type(signal.get("applied")) is not bool
        or signal["applied"]
        is not (source_row["phase_authority_mode"] == "controlled_same_tick_override")
        or not _strict_equal(signal.get("source_receipt"), receipt)
        or (
            mapped
            and not _strict_equal(
                signal.get("tensor_evidence"),
                sidecar.get("controlled_signal_tensor_evidence"),
            )
        )
        or (not mapped and sidecar.get("controlled_signal_tensor_evidence") is not None)
    ):
        raise ValueError("bounded native signal receipt/tensor binding drifted")
    expected_source_rows = (
        len(receipt.get("observed_route_lanelet_ids", []))
        + len(receipt.get("observed_map_lanelet_ids", []))
        if mapped
        else 0
    )
    if signal["source_row_count"] != expected_source_rows:
        raise ValueError("bounded native signal source-row denominator drifted")

    native_context = native_tick.get("v25_context")
    expected_context = {
        "schema_version": sidecar.get("context_schema_version"),
        "raw_context": feature.get("raw_context"),
        "source_complete": feature.get("context_source_complete"),
        "source_receipt": sidecar.get("context_source_receipt"),
    }
    if not _strict_equal(native_context, expected_context):
        raise ValueError("bounded native V25 context/snapshot binding drifted")


def _reject_unknown_failure_fields(value: Any, *, path: str = "native") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("bounded native evidence has a non-string key")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if (
                any(token in normalized for token in ("error", "exception", "failure"))
                or normalized
                in {"fault", "success", "aborted", "crash", "exitcode", "statuscode"}
            ):
                raise ValueError(f"bounded native evidence has an unknown failure field: {path}.{key}")
            if "outcome" in normalized and key != "outcome_fields_consumed":
                raise ValueError(f"bounded native evidence has an unknown outcome field: {path}.{key}")
            if "future" in normalized and key != "future_schedule_consumed":
                raise ValueError(f"bounded native evidence has an unknown future field: {path}.{key}")
            if key == "outcome_fields_consumed" and item != []:
                raise ValueError("bounded native evidence consumed outcome fields")
            if key == "future_schedule_consumed" and item is not False:
                raise ValueError("bounded native evidence consumed a future schedule")
            _reject_unknown_failure_fields(item, path=f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_unknown_failure_fields(item, path=f"{path}[{index}]")


def _validate_public_success_tick(tick: Any, *, tick_index: int) -> None:
    if type(tick) is not dict or set(tick) != PUBLIC_TICK_FIELDS:
        raise ValueError("bounded native public tick exact field set drifted")
    if type(tick.get("tick_index")) is not int or tick["tick_index"] != tick_index or tick.get("status") != "ok":
        raise ValueError("bounded native public tick index/status drifted")
    padding, tracker, safety, latency = (
        tick.get("padding"), tick.get("tracker"), tick.get("safety"), tick.get("latency_ms")
    )
    if (
        type(padding) is not dict
        or set(padding) != {"observed_frames", "padded_frames", "padding_policy"}
        or type(padding.get("observed_frames")) is not int
        or type(padding.get("padded_frames")) is not int
        or padding["observed_frames"] < 1
        or padding["observed_frames"] > 31
        or padding["padded_frames"] != 31 - padding["observed_frames"]
        or padding.get("padding_policy") != "native_zero_left_pad_to_31_v1"
        or tracker != {"status": "ok"}
        or type(safety) is not dict
        or set(safety) != SAFETY_FIELDS
        or type(latency) is not dict
        or set(latency) != LATENCY_FIELDS
    ):
        raise ValueError("bounded native padding/tracker/safety/latency schema drifted")
    if type(safety.get("tick_index")) is not int or safety["tick_index"] != tick_index:
        raise ValueError("bounded native safety tick index drifted")
    for name in ("position_xy", "front_center_prev_xy", "front_center_xy"):
        value = safety.get(name)
        if type(value) is not list or len(value) != 2:
            raise ValueError(f"bounded safety {name} shape drifted")
        for item in value:
            _native_number(item, label=f"safety.{name}")
    for name in ("speed_mps", "ego_heading_rad", "route_heading_rad", "route_progress_m", "min_obb_clearance_m", "speed_limit_mps"):
        _native_number(safety.get(name), label=f"safety.{name}")
    if safety.get("constant_velocity_circle_ttc_diagnostic_s") is not None:
        _native_number(safety["constant_velocity_circle_ttc_diagnostic_s"], label="safety.ttc")
    if (
        type(safety.get("five_point_drivable_coverage")) is not bool
        or type(safety.get("red_light_at_interval_start")) is not bool
        or safety.get("source_complete") is not True
        or type(safety.get("red_stop_lines")) is not list
    ):
        raise ValueError("bounded native safety exact type/value contract drifted")
    for name, value in latency.items():
        if _native_number(value, label=f"latency_ms.{name}") < 0.0:
            raise ValueError("bounded native latency is negative")
    if _native_number(
        tick.get("pre_decision_speed_mps"), label="pre-decision speed"
    ) < 0.0:
        raise ValueError("bounded native pre-decision speed is negative")
    for name in ("physical_feasible_mask", "source_valid_mask", "source_complete_mask"):
        _strict_bool_mask(tick.get(name), label=f"native {name}")
    reasons = tick.get("candidate_reasons")
    if (
        type(reasons) is not list
        or len(reasons) != 8
        or any(type(row) is not list or any(type(item) is not str for item in row) for row in reasons)
    ):
        raise ValueError("bounded native candidate reasons schema drifted")


def _validate_native_header_result_exact(
    *, receipt: Any, expected: Mapping[str, Any]
) -> None:
    """Compare every authoritative native header/result leaf with strict JSON types."""

    if (
        type(receipt) is not dict
        or set(receipt) != NATIVE_RECEIPT_FIELDS
        or type(expected) is not dict
        or set(expected) != NATIVE_HEADER_RESULT_FIELDS
    ):
        raise ValueError("bounded native header/result field contract drifted")
    actual = {key: receipt[key] for key in NATIVE_HEADER_RESULT_FIELDS}
    if not _strict_equal(actual, dict(expected)):
        raise ValueError("bounded native header/result exact value/type drifted")


def _validate_native_static_contract(receipt: Mapping[str, Any]) -> None:
    if type(receipt) is not dict or set(receipt) != NATIVE_RECEIPT_FIELDS:
        raise ValueError("bounded native receipt exact field set drifted")
    ticks = receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("bounded native tick denominator drifted")
    for index, tick in enumerate(ticks):
        _validate_public_success_tick(tick, tick_index=index)
    sha_fields = (
        "route_name",
        "route_sha256",
        "logical_map_sha256",
        "spawn_config_sha256",
        "initial_world_state_sha256",
        "initial_scene_materialization_sha256",
    )
    if (
        receipt.get("schema_version")
        != "camp_dp_v25_a1610_bounded_native_receipt_v2"
        or receipt.get("status") != "ok"
        or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or receipt.get("checkpoint_sha256")
        != EXPECTED_FIXED_DP_CHECKPOINT["sha256"]
        or receipt.get("args_sha256") != EXPECTED_FIXED_DP_ARGS["sha256"]
        or receipt.get("arm") != "camp"
        or type(receipt.get("scenario_seed")) is not int
        or receipt.get("scenario_seed") != 25001
        or receipt.get("claim_authorized") is not False
        or not _strict_equal(
            receipt.get("selector_scale_contract"),
            EXPECTED_SELECTOR_SCALE_CONTRACT,
        )
        or receipt.get("runtime_annotation_compatibility")
        != EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY
        or any(not _is_sha256(receipt.get(name)) for name in sha_fields)
    ):
        raise ValueError("bounded native static header contract drifted")
    native_result = receipt.get("native_result")
    if (
        type(native_result) is not dict
        or set(native_result)
        != {
            "final_step",
            "goal_reached",
            "reason",
            "n_npc_spawned",
            "trajectory_log_path",
            "clearance_log_path",
        }
        or type(native_result.get("final_step")) is not int
        or type(native_result.get("goal_reached")) is not bool
        or type(native_result.get("reason")) is not str
        or type(native_result.get("n_npc_spawned")) is not int
        or type(native_result.get("trajectory_log_path")) is not str
        or type(native_result.get("clearance_log_path")) is not str
    ):
        raise ValueError("bounded native terminal contract drifted")
    trajectory = Path(native_result["trajectory_log_path"])
    clearance = Path(native_result["clearance_log_path"])
    if (
        not trajectory.is_absolute()
        or not clearance.is_absolute()
        or str(trajectory.resolve()) != str(trajectory)
        or str(clearance.resolve()) != str(clearance)
        or trajectory.name != "trajectory_log.json"
        or clearance.name != "clearance_log.json"
        or trajectory.parent != clearance.parent
    ):
        raise ValueError("bounded native terminal path contract drifted")


def _derive_native_failure_class(receipt: Any) -> str:
    if type(receipt) is not dict:
        return "native_receipt_malformed"
    _reject_unknown_failure_fields(receipt)
    try:
        _validate_native_static_contract(receipt)
    except ValueError:
        return "native_evidence_schema_invalid"
    return "none"


def _validate_native_cross_binding(
    *,
    native_tick: Any,
    tick_index: int,
    feature: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    source_row: Mapping[str, Any],
    candidate: np.ndarray,
    atoms: np.ndarray,
    normalized: np.ndarray,
    scores: np.ndarray,
    row_shas: list[str],
    tensor_sha: str,
) -> None:
    if type(native_tick) is not dict or native_tick.get("tick_index") != tick_index:
        raise ValueError("bounded native tick schema/index drifted")
    native_source = native_tick.get("source_valid_mask")
    native_physical = native_tick.get("physical_feasible_mask")
    native_complete = native_tick.get("source_complete_mask")
    identity = native_tick.get("default_candidate0_identity")
    if (
        _strict_bool_mask(native_source, label="native source-valid") != feature["source_valid_mask"]
        or _strict_bool_mask(native_physical, label="native physical-feasible")
        != feature["physical_feasible_mask"]
        or _strict_bool_mask(native_complete, label="native route-speed source-complete")
        != [all(row[column] for column in range(4, 7)) for row in feature["atom_source_valid_mask"]]
        or native_tick.get("candidate_tensor_sha256_before") != tensor_sha
        or native_tick.get("candidate_tensor_sha256_after") != tensor_sha
        or native_tick.get("candidate_row_sha256") != row_shas
        or native_tick.get("default_output_sha256") != row_shas[0]
        or native_tick.get("scene_materialization_sha256")
        != sidecar.get("scene_materialization_sha256")
        or native_tick.get("selected_trajectory_sha256")
        != row_shas[sidecar["selected_index"]]
        or native_tick.get("selected_index") != sidecar["selected_index"]
        or native_tick.get("scores") != sidecar["scores"]
        or native_tick.get("score_contract") != "score_k=clip(a_k/s,0,10)^T w"
        or native_tick.get("selection_policy") != "v22_source_valid"
        or native_tick.get("eligibility_mask_name") != "source_valid_mask"
        or native_tick.get("tie_break_contract") != "lowest_eligible_candidate_index"
        or native_tick.get("all_k_high_risk") is not sidecar["all_k_high_risk"]
        or type(identity) is not dict
        or set(identity) != DEFAULT_IDENTITY_FIELDS
        or not _strict_equal(identity, sidecar["default_candidate0_identity"])
        or native_tick.get("atom_matrix_sha256")
        != hashlib.sha256(np.ascontiguousarray(atoms).tobytes()).hexdigest()
        or native_tick.get("normalized_atom_matrix_sha256")
        != hashlib.sha256(np.ascontiguousarray(normalized).tobytes()).hexdigest()
        or sidecar.get("normalized_atom_matrix_sha256")
        != native_tick.get("normalized_atom_matrix_sha256")
        or not np.array_equal(
            _native_numeric_array(native_tick.get("scores"), (8,), label="native scores"),
            scores,
        )
    ):
        raise ValueError("bounded native/snapshot candidate-atom-score-selection binding drifted")
    _validate_native_source_context(
        native_tick=native_tick,
        feature=feature,
        sidecar=sidecar,
        source_row=source_row,
        tick_index=tick_index,
    )


def _context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    feature = payload["feature_payload"]
    sidecar = payload["sidecar"]
    return {
        "raw_context": feature["raw_context"],
        "context_source_complete": feature["context_source_complete"],
        "context_source_receipt": sidecar["context_source_receipt"],
        "signal_source_class": sidecar["signal_source_class"],
        "phase_authority_mode": sidecar["phase_authority_mode"],
        "controlled_signal_source_receipt": sidecar[
            "controlled_signal_source_receipt"
        ],
        "controlled_signal_tensor_evidence": sidecar[
            "controlled_signal_tensor_evidence"
        ],
        "controlled_model_input_cache_receipt": sidecar[
            "controlled_model_input_cache_receipt"
        ],
        "causal_signal_atom_input": sidecar["causal_signal_atom_input"],
    }


def _review_tick(
    *,
    payload: Mapping[str, Any],
    run: Mapping[str, Any],
    tick_index: int,
    source_row: Mapping[str, Any],
    source_root_sha256: str,
    native_tick: Mapping[str, Any],
    scene_materialization: Mapping[str, np.ndarray],
    scales: np.ndarray,
    weights: np.ndarray,
    scale_sha256: str,
    artifact_root: Path | None = None,
    referenced_shards: set[str] | None = None,
) -> dict[str, Any]:
    if referenced_shards is None:
        referenced_shards = set()
    if artifact_root is None:
        artifact_root = Path(".")
    if (
        type(payload) is not dict
        or set(payload) != SNAPSHOT_FIELDS
        or payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
    ):
        raise ValueError("bounded snapshot schema drifted")
    feature = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if (
        type(feature) is not dict
        or set(feature) != FEATURE_FIELDS
        or type(sidecar) is not dict
        or set(sidecar) != SIDECAR_FIELDS
    ):
        raise ValueError("bounded snapshot feature/sidecar drifted")
    if (
        type(sidecar.get("run_ordinal")) is not int
        or sidecar["run_ordinal"] != run["run_ordinal"]
        or sidecar.get("occurrence") != run["occurrence"]
        or sidecar.get("scenario_id") != run["scenario_id"]
        or source_row.get("scenario_id") != run["scenario_id"]
        or type(sidecar.get("tick_index")) is not int
        or sidecar["tick_index"] != tick_index
        or type(sidecar.get("dt_s")) is not float
        or sidecar["dt_s"] != 0.1
        or sidecar.get("family") != source_row["family"]
        or sidecar.get("tier") != source_row["tier"]
        or sidecar.get("route_identity_sha256")
        != source_row["route_identity_sha256"]
        or sidecar.get("source_map_sha256") != source_row["source_map_sha256"]
        or type(sidecar.get("seed")) is not int
        or sidecar["seed"] != source_row["seed"]
        or sidecar.get("route_signal_source_artifact_root_sha256")
        != source_root_sha256
        or sidecar.get("route_signal_source_row_sha256") != _sha(source_row)
        or sidecar.get("signal_source_class") != source_row["source_class"]
        or sidecar.get("phase_authority_mode")
        != source_row["phase_authority_mode"]
        or sidecar.get("fresh_b_opened") is not False
        or sidecar.get("outcome_fields_consumed") != []
        or sidecar.get("generation_behavior_scale_sha256") != scale_sha256
        or sidecar.get("canonical_semantic_clone_sha256")
        != source_row["source_chain"]["semantic_clone_sha256"]
        or sidecar.get("offline_label_provenance")
        != "pending_train_only_causal_label"
        or sidecar.get("candidate0_semantics")
        != "operational_default_alias_from_same_forward"
        or sidecar.get("score_contract") != "score_k=clip(a_k/s,0,10)^T w"
    ):
        raise ValueError("bounded snapshot run/source/Fresh binding drifted")
    candidate = _native_numeric_array(
        feature.get("candidate_tensor"), (8, 80, 4), label="candidate tensor"
    ).astype(np.float32)
    default = _native_numeric_array(
        feature.get("default_output"), (80, 4), label="default output"
    ).astype(np.float32)
    atoms = _native_numeric_array(feature.get("atom_matrix"), (8, 14), label="atoms")
    _validate_fixed_k8_heading_envelope(candidate)
    if np.any(atoms < 0.0):
        raise ValueError("bounded raw atoms or fixed-K8 heading contract drifted")
    row_shas = [
        hashlib.sha256(np.ascontiguousarray(candidate[index]).tobytes()).hexdigest()
        for index in range(8)
    ]
    tensor_sha = hashlib.sha256(np.ascontiguousarray(candidate).tobytes()).hexdigest()
    raw_rows = feature.get("candidate_row_sha256")
    identity = sidecar.get("default_candidate0_identity")
    if (
        raw_rows != row_shas
        or not np.array_equal(default, candidate[0])
        or sidecar.get("candidate0_sha256") != row_shas[0]
        or sidecar.get("default_output_sha256") != row_shas[0]
        or sidecar.get("candidate_tensor_sha256_before") != tensor_sha
        or sidecar.get("candidate_tensor_sha256_after") != tensor_sha
        or type(identity) is not dict
        or set(identity) != DEFAULT_IDENTITY_FIELDS
        or identity.get("elementwise_equal") is not True
        or type(identity.get("max_abs_difference")) is not float
        or identity.get("max_abs_difference") != 0.0
        or identity.get("candidate0_sha256") != row_shas[0]
        or identity.get("default_output_sha256") != row_shas[0]
        or identity.get("native_ranked_k8") is not False
        or sidecar.get("candidate0_independent_second_forward") is not False
    ):
        raise ValueError("bounded K8/candidate0 same-forward evidence drifted")
    atom_source = feature.get("atom_source_valid_mask")
    applicable = feature.get("atom_applicable_mask")
    source_valid = feature.get("source_valid_mask")
    physical = feature.get("physical_feasible_mask")
    if (
        type(atom_source) is not list
        or len(atom_source) != 8
        or any(type(row) is not list or len(row) != 14 for row in atom_source)
        or any(type(value) is not bool for row in atom_source for value in row)
        or type(applicable) is not list
        or len(applicable) != 8
        or any(type(row) is not list or len(row) != 14 for row in applicable)
        or any(type(value) is not bool for row in applicable for value in row)
        or type(source_valid) is not list
        or len(source_valid) != 8
        or any(type(value) is not bool for value in source_valid)
        or type(physical) is not list
        or len(physical) != 8
        or any(type(value) is not bool for value in physical)
    ):
        raise ValueError("bounded atom/source/applicability mask schema drifted")
    receipt = _validate_signal_receipts(
        sidecar=sidecar, source_row=source_row, tick_index=tick_index
    )
    causal = _validate_causal_signal(
        sidecar=sidecar, source_row=source_row, receipt=receipt
    )
    _validate_context(feature=feature, sidecar=sidecar, receipt=receipt)
    _validate_cache(sidecar=sidecar, source_row=source_row, tick_index=tick_index)
    evidence = _validate_causal_evidence(
        artifact_root=artifact_root,
        feature=feature,
        sidecar=sidecar,
        native_tick=native_tick,
        referenced_shards=referenced_shards,
    )
    _validate_scene_materialization_snapshot_binding(
        evidence=evidence, scene_materialization=scene_materialization
    )
    projection = _independent_route_projection(
        candidate,
        evidence["route_lanes"],
        evidence["route_lanes_speed_limit"],
        evidence["route_lanes_has_speed_limit"],
    )
    independent_speed_source = projection["source"].tolist()
    if _strict_bool_mask(
        native_tick.get("source_complete_mask"),
        label="native route-speed source-complete",
    ) != independent_speed_source:
        raise ValueError("bounded native speed-source mask differs from route oracle")
    signal_applicable = receipt["current_phase"] == "red"
    expected_atom_source = [[True] * 14 for _ in range(8)]
    expected_applicable = [[True] * 14 for _ in range(8)]
    for row_index in range(8):
        for column in range(4, 7):
            expected_atom_source[row_index][column] = independent_speed_source[row_index]
        expected_applicable[row_index][10] = signal_applicable
        expected_applicable[row_index][12] = signal_applicable
    expected_source_valid = [all(row) for row in expected_atom_source]
    expected_physical, expected_reasons = _independent_physical_mask(
        candidate.astype(np.float64), projection, evidence
    )
    expected_physical = [
        feasible and valid
        for feasible, valid in zip(expected_physical, expected_source_valid)
    ]
    if (
        atom_source != expected_atom_source
        or applicable != expected_applicable
        or source_valid != expected_source_valid
        or not any(source_valid)
        or sidecar.get("source_valid_mask") != source_valid
        or sidecar.get("physical_feasible_mask") != physical
        or physical != expected_physical
        or native_tick.get("candidate_reasons") != expected_reasons
        or any(feasible and not valid for feasible, valid in zip(physical, source_valid))
        or sidecar.get("all_k_high_risk")
        is not (all(source_valid) and not any(physical))
    ):
        raise ValueError("bounded canonical atom/source/applicability mask drifted")
    for row_index in range(8):
        if (
            atom_source[row_index][10] is not True
            or atom_source[row_index][12] is not True
            or applicable[row_index][10] is not signal_applicable
            or applicable[row_index][12] is not signal_applicable
            or (
                not signal_applicable
                and (atoms[row_index, 10] != 0.0 or atoms[row_index, 12] != 0.0)
            )
        ):
            raise ValueError("bounded signal atom source/applicability binding drifted")
    expected_red_stopping = _independent_red_stopping_oracle(candidate, causal, 0.1)
    if not np.allclose(atoms[:, 12], expected_red_stopping, rtol=0.0, atol=1e-12):
        raise ValueError("bounded red-stopping atom differs from independent oracle")
    expected_planned_red = _independent_planned_red_cost(
        candidate, evidence["route_lanes"]
    )
    if (
        not np.allclose(
            evidence["fixed_dp_planned_red_light_cost"],
            expected_planned_red,
            rtol=0.0,
            atol=1e-12,
        )
        or not np.allclose(atoms[:, 10], expected_planned_red, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("bounded planned-red atom differs from independent NumPy oracle")
    _validate_independent_context(
        feature=feature,
        evidence=evidence,
        candidates=candidate,
        source_valid=source_valid,
    )
    scores = _native_numeric_array(sidecar.get("scores"), (8,), label="scores")
    normalized = np.clip(atoms / scales.reshape(1, 14), 0.0, 10.0)
    expected_scores = normalized @ weights
    selected = sidecar.get("selected_index")
    expected_selected = int(
        np.argmin(np.where(np.asarray(source_valid, dtype=bool), scores, np.inf))
    )
    if (
        type(selected) is not int
        or not np.allclose(scores, expected_scores, rtol=0.0, atol=1e-12)
        or selected != expected_selected
        or sidecar.get("selected_trajectory_sha256") != row_shas[selected]
        or sidecar.get("tie_break_contract") != "lowest_eligible_candidate_index"
    ):
        raise ValueError("bounded selector argmin/tie evidence drifted")
    _validate_native_cross_binding(
        native_tick=native_tick,
        tick_index=tick_index,
        feature=feature,
        sidecar=sidecar,
        source_row=source_row,
        candidate=candidate,
        atoms=atoms,
        normalized=normalized,
        scores=scores,
        row_shas=row_shas,
        tensor_sha=tensor_sha,
    )
    return {
        "candidate0": row_shas[0],
        "rows": row_shas,
        "atoms": _sha(feature["atom_matrix"]),
        "context": _sha(_context_payload(payload)),
        "selected": selected,
    }


def _review_run(
    *,
    artifact: Path,
    run: Mapping[str, Any],
    index_rows: list[Mapping[str, Any]],
    source_row: Mapping[str, Any],
    formal_case: Mapping[str, Any],
    template: Mapping[str, Any],
    dp_repo: Path,
    source_root_sha256: str,
    scales: np.ndarray,
    weights: np.ndarray,
    scale_sha256: str,
    referenced_shards: set[str],
) -> dict[str, Any]:
    ordinal = run["run_ordinal"]
    native_dir = (
        artifact
        / "native_runs"
        / f"run_{ordinal:03d}_{run['occurrence']}_{run['scenario_id']}"
    )
    receipt = _load(
        native_dir / "bounded_native_receipt.json", canonical=True
    )
    _validate_native_static_contract(receipt)
    scene_materializations, scene_materialization_hashes = (
        _load_scene_materialization_evidence(
        artifact=artifact, receipt=receipt
        )
    )
    _validate_scene_materialization_hash_sequence(
        receipt=receipt, hashes=scene_materialization_hashes
    )
    ticks = receipt["ticks"]
    derived_native_result = _validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=dp_repo,
    )
    expected_native = _expected_native_header_result(
        artifact=artifact,
        native_dir=native_dir,
        initial_scene_materialization_sha256=scene_materialization_hashes[0],
        scene_materialization_evidence=receipt[
            "causal_scene_materialization_evidence"
        ],
        derived_native_result=derived_native_result,
        formal_case=formal_case,
        source_row=source_row,
        template=template,
        dp_repo=dp_repo,
    )
    _validate_native_header_result_exact(receipt=receipt, expected=expected_native)
    failure_class = _derive_native_failure_class(receipt)
    if failure_class != "none":
        raise ValueError(f"bounded native failure evidence: {failure_class}")
    selected_rows = [row for row in index_rows if row.get("run_ordinal") == ordinal]
    if len(selected_rows) != 64:
        raise ValueError("bounded run snapshot denominator drifted")
    selected_rows.sort(key=lambda row: row.get("tick_index", -1))
    tick_oracles = []
    for tick_index, index_row in enumerate(selected_rows):
        if (
            type(index_row) is not dict
            or set(index_row) != {
                "schema_version",
                "run_ordinal",
                "occurrence",
                "scenario_id",
                "tick_index",
                "relative_path",
                "sha256",
            }
            or index_row.get("schema_version") != INDEX_SCHEMA_VERSION
            or index_row.get("occurrence") != run["occurrence"]
            or index_row.get("scenario_id") != run["scenario_id"]
            or type(index_row.get("tick_index")) is not int
            or index_row["tick_index"] != tick_index
            or type(index_row.get("relative_path")) is not str
            or index_row["relative_path"]
            != f"snapshots/{index_row.get('sha256')}{SNAPSHOT_SUFFIX}"
        ):
            raise ValueError("bounded snapshot index schema/order drifted")
        path = artifact / index_row["relative_path"]
        payload = independently_read_snapshot(path, index_row["sha256"])
        tick_oracles.append(
            _review_tick(
                payload=payload,
                run=run,
                tick_index=tick_index,
                source_row=source_row,
                source_root_sha256=source_root_sha256,
                native_tick=ticks[tick_index],
                scene_materialization=scene_materializations[tick_index],
                scales=scales,
                weights=weights,
                scale_sha256=scale_sha256,
                artifact_root=artifact,
                referenced_shards=referenced_shards,
            )
        )
    trajectory = []
    speeds = []
    for tick_index, tick in enumerate(ticks):
        safety = tick.get("safety") if type(tick) is dict else None
        position = safety.get("position_xy") if type(safety) is dict else None
        if type(position) is not list or len(position) != 2:
            raise ValueError("bounded native trajectory evidence drifted")
        trajectory.append(
            {
                "tick_index": tick_index,
                "position_xy": [
                    _native_number(position[0], label="position x"),
                    _native_number(position[1], label="position y"),
                ],
                "ego_heading_rad": _native_number(
                    safety.get("ego_heading_rad"), label="ego heading"
                ),
                "route_progress_m": _native_number(
                    safety.get("route_progress_m"), label="route progress"
                ),
            }
        )
        speeds.append(_native_number(safety.get("speed_mps"), label="speed"))
    return {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": ordinal,
        "scenario_id": run["scenario_id"],
        "occurrence": run["occurrence"],
        "tick_count": 64,
        "candidate0_sha256_sequence": [row["candidate0"] for row in tick_oracles],
        "k8_row_sha256_sequence": [row["rows"] for row in tick_oracles],
        "atom_matrix_sha256_sequence": [row["atoms"] for row in tick_oracles],
        "context_sha256_sequence": [row["context"] for row in tick_oracles],
        "selected_index_sequence": [row["selected"] for row in tick_oracles],
        "failure_class": failure_class,
        "closed_loop_trajectory_sha256": _sha(trajectory),
        "speed_probe_sha256": _sha(speeds),
        "capability_failure_sha256": None,
    }


def _review_fixed_dp_capability_failure(
    *,
    artifact: Path,
    run: Mapping[str, Any],
    result: Mapping[str, Any],
    source_row: Mapping[str, Any],
    formal_case: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = result.get("retained_capability_failure")
    fields = {
        "schema_version", "failure_class", "reason", "scenario_id",
        "route_identity_sha256", "family", "tier", "source_class",
        "phase_authority_mode", "source_map_sha256", "corridor_group_sha256",
        "fixed_dp_head", "tick_index", "invalid_indices", "invalid_count",
        "minimum_heading_norm", "maximum_heading_norm",
        "heading_norm_minimum", "heading_norm_maximum", "raw_k8_sha256",
        "candidate0_sha256", "default_output_sha256",
        "default_candidate0_identity", "raw_preimage", "training_eligible",
        "calibration_eligible", "evaluation_eligible", "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(receipt) is not dict or set(receipt) != fields:
        raise ValueError("fixed-DP capability failure receipt schema drifted")
    source_class = source_row.get("source_class")
    phase_mode = source_row.get("phase_authority_mode")
    expected_values = {
        "schema_version": FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
        "failure_class": FIXED_DP_FAILURE_CLASS,
        "reason": FIXED_DP_FAILURE_REASON,
        "scenario_id": str(run["scenario_id"]),
        "route_identity_sha256": str(formal_case["route_identity_sha256"]),
        "family": str(formal_case["family"]),
        "tier": str(formal_case["tier"]),
        "source_class": source_class,
        "phase_authority_mode": phase_mode,
        "source_map_sha256": str(formal_case["source_map_sha256"]),
        "corridor_group_sha256": str(formal_case["corridor_group_sha256"]),
        "fixed_dp_head": FIXED_DP_HEAD,
        "heading_norm_minimum": 0.5,
        "heading_norm_maximum": 1.5,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not _strict_equal(receipt.get(key), value) for key, value in expected_values.items()):
        raise ValueError("fixed-DP capability failure authority drifted")
    preimage = receipt.get("raw_preimage")
    if (
        type(preimage) is not dict
        or set(preimage)
        != {"relative_path", "file_sha256", "array_sha256", "shape", "dtype"}
        or preimage.get("shape") != [8, 80, 4]
        or preimage.get("dtype") != "float32"
        or preimage.get("relative_path")
        != f"fixed_dp_capability_failures/{receipt.get('raw_k8_sha256')}.bin"
        or preimage.get("file_sha256") != receipt.get("raw_k8_sha256")
        or preimage.get("array_sha256") != receipt.get("raw_k8_sha256")
    ):
        raise ValueError("fixed-DP capability raw preimage receipt drifted")
    path = artifact / preimage["relative_path"]
    if path.is_symlink() or not path.is_file():
        raise ValueError("fixed-DP capability raw preimage is unavailable")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != receipt.get("raw_k8_sha256"):
        raise ValueError("fixed-DP capability raw preimage digest drifted")
    tensor = np.frombuffer(data, dtype=np.float32).reshape(8, 80, 4)
    if not np.isfinite(tensor).all():
        raise ValueError("fixed-DP capability raw tensor is nonfinite")
    norms = np.linalg.norm(tensor[..., 2:4].astype(np.float64), axis=2)
    invalid = np.abs(norms - 1.0) > 0.5
    pairs = [
        {"candidate_index": int(candidate), "step_index": int(step)}
        for candidate, step in np.argwhere(invalid)
    ]
    candidate0_sha = hashlib.sha256(
        np.ascontiguousarray(tensor[0]).tobytes(order="C")
    ).hexdigest()
    identity = receipt.get("default_candidate0_identity")
    if (
        not pairs
        or receipt.get("invalid_indices") != pairs
        or receipt.get("invalid_count") != len(pairs)
        or receipt.get("minimum_heading_norm") != float(norms.min())
        or receipt.get("maximum_heading_norm") != float(norms.max())
        or receipt.get("candidate0_sha256") != candidate0_sha
        or type(identity) is not dict
        or set(identity)
        != {
            "elementwise_equal", "max_abs_difference", "default_output_sha256",
            "candidate0_sha256", "native_ranked_k8",
        }
        or identity.get("elementwise_equal") is not True
        or identity.get("max_abs_difference") != 0.0
        or identity.get("native_ranked_k8") is not False
        or identity.get("candidate0_sha256") != candidate0_sha
        or identity.get("default_output_sha256")
        != receipt.get("default_output_sha256")
        or receipt.get("default_output_sha256") != candidate0_sha
        or type(receipt.get("tick_index")) is not int
        or not 0 <= receipt["tick_index"] < 64
    ):
        raise ValueError("fixed-DP capability failure independent oracle failed")
    return {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": run["run_ordinal"],
        "scenario_id": run["scenario_id"],
        "occurrence": run["occurrence"],
        "tick_count": 0,
        "candidate0_sha256_sequence": [],
        "k8_row_sha256_sequence": [],
        "atom_matrix_sha256_sequence": [],
        "context_sha256_sequence": [],
        "selected_index_sequence": [],
        "failure_class": FIXED_DP_FAILURE_CLASS,
        "closed_loop_trajectory_sha256": None,
        "speed_probe_sha256": None,
        "capability_failure_sha256": canonical_sha256(receipt),
    }


def _expected_execution_source_receipt(
    *, authority: Mapping[str, Any], nonce_marker: Mapping[str, Any]
) -> dict[str, Any]:
    decision = authority["decision"]
    return {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "release_artifact": authority["release_artifact"],
        "release_root_sha256": authority["release_root_sha256"],
        "release_run_nonce": decision["run_nonce"],
        "nonce_marker": dict(nonce_marker),
        "root_artifacts": decision["root_artifacts"],
        "formal_root_sha256": EXPECTED_FORMAL_ROOT_SHA256,
        "critical_implementation_manifest": decision[
            "critical_implementation_manifest"
        ],
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "device": EXPECTED_DEVICE,
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _expected_execution_report(
    *, terminal: Mapping[str, Any], wall_seconds: int | float
) -> dict[str, Any]:
    wall = _native_number(wall_seconds, label="bounded execution wall seconds")
    if wall < 0.0:
        raise ValueError("bounded execution wall seconds must be nonnegative")
    return {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "status": "passed_exact_bounded_execution",
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_count": terminal["tick_count"],
        "snapshot_capacity": EXPECTED_TICKS,
        "device": EXPECTED_DEVICE,
        "terminal": dict(terminal),
        "wall_seconds": wall_seconds,
        "retained_capability_failure_count": terminal[
            "retained_capability_failure_count"
        ],
        "mapped_runtime_source_failure_count": 0,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "sequential_fixed_k8": True,
        "candidate_tensors_modified": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _independent_terminal(
    *, plan: Mapping[str, Any], results: list[Mapping[str, Any]], evidence: list[Mapping[str, Any]]
) -> dict[str, Any]:
    if (
        type(plan) is not dict
        or type(results) is not list
        or type(evidence) is not list
        or len(results) != EXPECTED_RUNS
        or len(evidence) != EXPECTED_RUNS
        or len(plan.get("runs", [])) != EXPECTED_RUNS
        or type(plan.get("unique_identity_count")) is not int
        or plan.get("unique_identity_count") != EXPECTED_UNIQUE_IDENTITIES
    ):
        raise ValueError("bounded independent terminal denominator drifted")
    first, final = evidence[0], evidence[-1]
    if (
        first.get("occurrence") != "identity0_first"
        or final.get("occurrence") != "identity0_final_repeat"
        or first.get("scenario_id") != final.get("scenario_id")
    ):
        raise ValueError("bounded independent identity0 terminal order drifted")
    comparison = {
        "candidate0_sha256_sequence_equal": first["candidate0_sha256_sequence"]
        == final["candidate0_sha256_sequence"],
        "k8_row_sha256_sequence_equal": first["k8_row_sha256_sequence"]
        == final["k8_row_sha256_sequence"],
        "atom_matrix_sequence_equal": first["atom_matrix_sha256_sequence"]
        == final["atom_matrix_sha256_sequence"],
        "context_sequence_equal": first["context_sha256_sequence"]
        == final["context_sha256_sequence"],
        "selected_index_sequence_equal": first["selected_index_sequence"]
        == final["selected_index_sequence"],
        "failure_class_equal": first["failure_class"] == final["failure_class"],
        "closed_loop_trajectory_equal": first["closed_loop_trajectory_sha256"]
        == final["closed_loop_trajectory_sha256"],
        "speed_probe_equal": first["speed_probe_sha256"]
        == final["speed_probe_sha256"],
    }
    if (
        results[0].get("status") != "complete"
        or results[-1].get("status") != "complete"
        or any(value is not True for value in comparison.values())
    ):
        raise ValueError("bounded independent identity0 terminal comparison failed")
    unique: dict[str, Mapping[str, Any]] = {}
    for row in results:
        scenario_id = str(row.get("scenario_id"))
        prior = unique.get(scenario_id)
        if prior is not None and (
            prior.get("occurrence") != "identity0_first"
            or row.get("occurrence") != "identity0_final_repeat"
            or prior.get("status") != "complete"
            or row.get("status") != "complete"
        ):
            raise ValueError("bounded independent duplicate identity drifted")
        unique.setdefault(scenario_id, row)
    if len(unique) != EXPECTED_UNIQUE_IDENTITIES:
        raise ValueError("bounded independent unique denominator drifted")
    coverage = _independent_bounded_coverage(list(unique.values()))
    if coverage["passed"] is not True:
        raise ValueError("bounded independent support coverage gate failed")
    complete_runs = sum(row.get("status") == "complete" for row in results)
    retained_runs = len(results) - complete_runs
    return {
        "schema_version": "camp_dp_v25_a17_route_level_bounded_terminal_v3",
        "status": "passed_exact_bounded_terminal",
        "run_count": EXPECTED_RUNS,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "tick_count": complete_runs * 64,
        "retained_capability_failure_count": retained_runs,
        "mapped_runtime_source_failure_count": 0,
        "fixed_dp_support_coverage": coverage,
        "identity0_repeat_deterministic": True,
        "repeat_comparison": comparison,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _independent_bounded_coverage(
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    def grouped(fields: tuple[str, ...], minimum: int) -> dict[str, Any]:
        totals: collections.Counter[tuple[str, ...]] = collections.Counter()
        completes: collections.Counter[tuple[str, ...]] = collections.Counter()
        for row in rows:
            key = tuple(str(row[field]) for field in fields)
            totals[key] += 1
            if row.get("status") == "complete":
                completes[key] += 1
        table = []
        passed = True
        for key in sorted(totals):
            ok = completes[key] * 100 > totals[key] * minimum
            passed = passed and ok
            table.append(
                {"key": list(key), "planned": totals[key], "complete": completes[key], "passed": ok}
            )
        return {"fields": list(fields), "minimum_percent_exclusive": minimum, "rows": table, "passed": passed}

    complete = [row for row in rows if row.get("status") == "complete"]
    family = grouped(("family",), 90)
    source = grouped(("source_class", "phase_authority_mode"), 90)
    family_tier = grouped(("family", "tier"), 80)
    red_complete = [
        row for row in complete
        if row.get("family") == "red_light_phase_timing"
    ]
    red_by_tier = collections.Counter(str(row["tier"]) for row in red_complete)
    red_maps = {str(row["source_map_sha256"]) for row in red_complete}
    red_planned = [
        row for row in rows
        if row.get("family") == "red_light_phase_timing"
    ]
    red_pass = not red_planned or (
        red_by_tier["easy"] >= 4
        and red_by_tier["borderline"] >= 7
        and red_by_tier["high_risk"] >= 4
        and len(red_maps) >= 3
    )
    minimum_complete = math.ceil(len(rows) * 0.95)
    passed = bool(
        len(rows) > 0 and len(complete) >= minimum_complete and family["passed"]
        and source["passed"] and family_tier["passed"] and red_pass
    )
    return {
        "planned_unique_identity_count": len(rows),
        "complete_unique_identity_count": len(complete),
        "minimum_complete_unique_identity_count": minimum_complete,
        "family": family,
        "source_mode": source,
        "family_tier": family_tier,
        "red_complete_by_tier": {tier: int(red_by_tier[tier]) for tier in ("easy", "borderline", "high_risk")},
        "red_complete_distinct_source_map_count": len(red_maps),
        "red_minimum_complete_by_tier": {"easy": 4, "borderline": 7, "high_risk": 4},
        "red_minimum_distinct_source_maps": 3,
        "passed": passed,
    }


def _validate_execution_source_authority(
    *,
    source_receipt: Any,
    report: Any,
    authority: Mapping[str, Any],
    nonce_marker: Mapping[str, Any],
    expected_terminal: Mapping[str, Any],
) -> None:
    try:
        expected_source = _expected_execution_source_receipt(
            authority=authority, nonce_marker=nonce_marker
        )
        expected_report = _expected_execution_report(
            terminal=expected_terminal,
            wall_seconds=report.get("wall_seconds") if type(report) is dict else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("bounded execution report/source authority drifted") from exc
    if (
        type(source_receipt) is not dict
        or set(source_receipt) != SOURCE_RECEIPT_FIELDS
        or not _strict_equal(source_receipt, expected_source)
        or type(report) is not dict
        or set(report) != EXECUTION_REPORT_FIELDS
        or not _strict_equal(report, expected_report)
    ):
        raise ValueError("bounded execution report/source authority drifted")


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    seal = verify_complete_seal(
        args.execution_artifact,
        args.execution_root_sha256,
        label="V25 A1.6.10 bounded execution",
    )
    if (args.execution_artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("bounded execution run.exit is not zero")
    file_policies = _validate_execution_manifest_policies(
        artifact=args.execution_artifact, paths=seal["manifest_paths"]
    )
    if any(
        token in path.lower()
        for path in seal["manifest_paths"]
        for token in ("outcome", "fresh", "holdout")
    ):
        raise ValueError("bounded execution inventory contains a forbidden path")
    report = _load(args.execution_artifact / "report.json", canonical=True)
    source_receipt = _load(
        args.execution_artifact / "source_receipt.json", canonical=True
    )
    progress = _load(args.execution_artifact / "progress.json", canonical=True)
    if (
        type(progress) is not dict
        or set(progress)
        != {
            "schema_version", "status", "completed_runs", "total_runs",
            "snapshot_count", "fresh_b2_opened", "outcome_fields_consumed",
        }
        or progress.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or progress.get("status") != "complete"
        or type(progress.get("completed_runs")) is not int
        or progress["completed_runs"] != EXPECTED_RUNS
        or type(progress.get("total_runs")) is not int
        or progress["total_runs"] != EXPECTED_RUNS
        or type(progress.get("snapshot_count")) is not int
        or progress["snapshot_count"] < 0
        or progress["snapshot_count"] > EXPECTED_TICKS
        or progress["snapshot_count"] % 64 != 0
        or progress.get("fresh_b2_opened") is not False
        or progress.get("outcome_fields_consumed") != []
    ):
        raise ValueError("bounded execution progress authority drifted")
    authority = _verify_archived_bounded_release_for_review(
        repo=ROOT,
        review_head=head,
        release_artifact=args.release_artifact,
        release_root_sha256=args.release_root_sha256,
        requested_output_dir=str(args.execution_artifact),
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
    )
    decision = authority["decision"]
    plan = authority["plan"]
    expected_execution_heads = (
        f"camp_source_head={decision['implementation_source_head']}\n"
        f"camp_pointer_head={decision['pointer_head_at_release']}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n"
    ).encode("ascii")
    if (args.execution_artifact / "HEADS").read_bytes() != expected_execution_heads:
        raise ValueError("bounded execution HEADS authority values drifted")
    execution_assets, scales, weights, scale_sha256 = _independent_execution_assets(
        repo=ROOT,
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
    )
    if (
        not _strict_equal(decision.get("execution_assets"), execution_assets)
        or decision.get("execution_assets_sha256") != _sha(execution_assets)
    ):
        raise ValueError("bounded release execution assets fail independent oracle")
    formal_cases = _independent_formal_cases()
    template = _load(args.probe_template)
    marker = NONCE_LEDGER / f"v25_{RELEASE_GATE}_{decision['run_nonce']}.consumed.json"
    marker_payload = _load(marker, canonical=True)
    if (
        marker.is_symlink()
        or set(marker_payload) != {"gate", "nonce", "authorized_output_dir"}
        or marker_payload.get("gate") != RELEASE_GATE
        or marker_payload.get("nonce") != decision["run_nonce"]
        or marker_payload.get("authorized_output_dir")
        != str(args.execution_artifact.resolve())
        or source_receipt.get("nonce_marker", {}).get("path") != str(marker)
        or source_receipt.get("nonce_marker", {}).get("sha256")
        != hashlib.sha256(marker.read_bytes()).hexdigest()
    ):
        raise ValueError("bounded nonce consumption marker drifted")
    expected_source_receipt = _expected_execution_source_receipt(
        authority=authority,
        nonce_marker={
            "path": str(marker),
            "sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
        },
    )
    if not _strict_equal(source_receipt, expected_source_receipt):
        raise ValueError("bounded execution source authority drifted")
    if (
        type(report.get("unique_identity_count")) is not int
        or report["unique_identity_count"] != EXPECTED_UNIQUE_IDENTITIES
        or type(report.get("run_count")) is not int
        or report["run_count"] != EXPECTED_RUNS
        or type(report.get("snapshot_count")) is not int
        or report["snapshot_count"] < 0
        or report["snapshot_count"] > EXPECTED_TICKS
        or report["snapshot_count"] % 64 != 0
        or type(report.get("snapshot_capacity")) is not int
        or report["snapshot_capacity"] != EXPECTED_TICKS
        or type(report.get("retained_capability_failure_count")) is not int
        or report["retained_capability_failure_count"] < 0
        or report["retained_capability_failure_count"] > 12
        or report.get("mapped_runtime_source_failure_count") != 0
        or report.get("full_r_execute_authorized") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("bounded execution report/authority drifted")

    source_artifact = Path(decision["root_artifacts"]["source"]["path"])
    source_root_sha256 = decision["root_artifacts"]["source"]["root_sha256"]
    source_payload = _load(source_artifact / "route_signal_source_receipts.json")
    source_rows = source_payload.get("cases")
    if type(source_rows) is not list:
        raise ValueError("bounded source rows are unavailable")
    rows_by_id = {str(row.get("scenario_id")): row for row in source_rows}
    if len(rows_by_id) != len(source_rows):
        raise ValueError("bounded source row IDs are duplicated")
    results = _jsonl(args.execution_artifact / "results.jsonl")
    evidence = _jsonl(args.execution_artifact / "run_evidence.jsonl")
    index_rows = _jsonl(args.execution_artifact / "snapshot_index.jsonl")
    if (
        len(results) != EXPECTED_RUNS
        or len(evidence) != EXPECTED_RUNS
        or len(index_rows) != report["snapshot_count"]
        or len(index_rows) != progress["snapshot_count"]
    ):
        raise ValueError("bounded results/evidence/index denominator drifted")
    rebuilt = []
    referenced_causal_shards: set[str] = set()
    for run, result in zip(plan["runs"], results):
        source_row = _validate_source_row(rows_by_id[str(run["scenario_id"])])
        complete = result.get("status") == "complete" if type(result) is dict else False
        retained = (
            result.get("status") == "retained_fixed_dp_capability_failure"
            if type(result) is dict
            else False
        )
        expected_result_values = {
            "family": str(formal_cases[str(run["scenario_id"])]["family"]),
            "tier": str(formal_cases[str(run["scenario_id"])]["tier"]),
            "source_class": source_row["source_class"],
            "phase_authority_mode": source_row["phase_authority_mode"],
            "source_map_sha256": str(
                formal_cases[str(run["scenario_id"])]["source_map_sha256"]
            ),
            "corridor_group_sha256": str(
                formal_cases[str(run["scenario_id"])]["corridor_group_sha256"]
            ),
        }
        if (
            type(result) is not dict
            or set(result) != RESULT_FIELDS
            or result.get("schema_version") != RESULT_SCHEMA_VERSION
            or result.get("run_ordinal") != run["run_ordinal"]
            or result.get("scenario_id") != run["scenario_id"]
            or result.get("occurrence") != run["occurrence"]
            or not (complete or retained)
            or type(result.get("tick_count")) is not int
            or result["tick_count"] != (64 if complete else 0)
            or (
                complete
                and (
                    result.get("retained_capability_failure") is not None
                    or result.get("failure_class") != "none"
                )
            )
            or (
                retained
                and result.get("failure_class") != FIXED_DP_FAILURE_CLASS
            )
            or any(result.get(key) != value for key, value in expected_result_values.items())
            or result.get("fresh_b2_opened") is not False
            or result.get("outcome_fields_consumed") != []
        ):
            raise ValueError("bounded result/order/failure contract drifted")
        if complete:
            rebuilt.append(
                _review_run(
                artifact=args.execution_artifact,
                run=run,
                index_rows=index_rows,
                source_row=source_row,
                formal_case=formal_cases[str(run["scenario_id"])],
                template=template,
                dp_repo=args.dp_repo,
                source_root_sha256=source_root_sha256,
                scales=scales,
                weights=weights,
                scale_sha256=scale_sha256,
                referenced_shards=referenced_causal_shards,
                )
            )
        else:
            rebuilt.append(
                _review_fixed_dp_capability_failure(
                    artifact=args.execution_artifact,
                    run=run,
                    result=result,
                    source_row=source_row,
                    formal_case=formal_cases[str(run["scenario_id"])],
                )
            )
    if expected_shard_manifest_paths(seal["manifest_paths"]) != referenced_causal_shards:
        raise ValueError("bounded causal-evidence shard inventory is not exact")
    if _canonical_bytes(rebuilt) != _canonical_bytes(evidence):
        raise ValueError("bounded producer run evidence differs from independent rebuild")
    expected_terminal = _independent_terminal(
        plan=plan, results=results, evidence=rebuilt
    )
    _validate_execution_source_authority(
        source_receipt=source_receipt,
        report=report,
        authority=authority,
        nonce_marker={
            "path": str(marker),
            "sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
        },
        expected_terminal=expected_terminal,
    )
    first, final = rebuilt[0], rebuilt[-1]
    repeat_fields = (
        "candidate0_sha256_sequence",
        "k8_row_sha256_sequence",
        "atom_matrix_sha256_sequence",
        "context_sha256_sequence",
        "selected_index_sequence",
        "failure_class",
        "closed_loop_trajectory_sha256",
        "speed_probe_sha256",
    )
    comparison = {f"{field}_equal": first[field] == final[field] for field in repeat_fields}
    if any(value is not True for value in comparison.values()):
        raise ValueError("bounded identity0 repeat independent comparison failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_bounded_execution_review",
        "review_head": head,
        "producer_pointer_head": authority["producer_pointer_head"],
        "review_only_changed_paths": authority["review_only_changed_paths"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "device": EXPECTED_DEVICE,
        "reviewed_artifact": str(args.execution_artifact.resolve()),
        "reviewed_root_sha256": seal["root_sha256"],
        "release_root_sha256": authority["release_root_sha256"],
        "root_artifacts": decision["root_artifacts"],
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_count": expected_terminal["tick_count"],
        "execution_file_policy_count": len(file_policies),
        "execution_file_policies_sha256": _sha(file_policies),
        "identity0_repeat_comparison": comparison,
        "retained_capability_failure_count": expected_terminal[
            "retained_capability_failure_count"
        ],
        "mapped_runtime_source_failure_count": 0,
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-artifact", type=Path, required=True)
    parser.add_argument("--execution-root-sha256", required=True)
    parser.add_argument("--release-artifact", type=Path, required=True)
    parser.add_argument("--release-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"review_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(args.output_dir, label="V25 A1.6.10 bounded review")
        print(json.dumps({**report, "artifact_root_sha256": root}, sort_keys=True))
    except Exception as exc:
        _write(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed_independent_bounded_execution_review",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "full_r_execute_authorized": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(args.output_dir, label="failed V25 A1.6.10 bounded review")
        raise


if __name__ == "__main__":
    main()
