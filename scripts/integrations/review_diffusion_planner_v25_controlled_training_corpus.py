#!/usr/bin/env python3
"""Independently validate a sealed V25 corrected 1500-identity corpus."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
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
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    EXPECTED_EXECUTABLE_IDENTITIES,
    SCHEMA_VERSION as EXECUTION_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    _git_head,
    _tracked_dirty,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_causal_evidence_review import (  # noqa: E402
    expected_shard_manifest_paths,
    independently_materialize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_review import (  # noqa: E402
    SNAPSHOT_SUFFIX,
    independently_read_snapshot,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
    validate_causal_signal_atom_input,
)
from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (  # noqa: E402
    MAPPED_SIGNAL_RUNTIME_RECEIPT_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    FIXED_DP_FAILURE_CLASS,
    FIXED_DP_FAILURE_REASON,
    FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    CRITICAL_IMPLEMENTATION_PATHS,
    POINTER_ONLY_PATHS,
)
from camp_core.integrations.diffusion_planner_v25_a17_full_corpus_authority import (  # noqa: E402
    UPSTREAM_ROLES as A17_UPSTREAM_ROLES,
    verify_release as verify_a17_full_corpus_release,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_review_v8"
POSTHOC_REVIEW_CORRECTION_PATHS = frozenset(
    {
        "camp_core/tests/test_diffusion_planner_v25_a14_r04.py",
        "camp_core/tests/test_diffusion_planner_v25_controlled_training_corpus.py",
        "scripts/integrations/review_diffusion_planner_v25_controlled_training_corpus.py",
    }
)
SNAPSHOT_INDEX_FIELDS = frozenset(
    {"scenario_id", "tick_index", "relative_path", "sha256"}
)
SNAPSHOT_FIELDS = frozenset({"schema_version", "feature_payload", "sidecar"})
FEATURE_PAYLOAD_FIELDS = frozenset(
    {
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
)
SIDECAR_FIELDS = frozenset(
    {
        "tick_index",
        "dt_s",
        "scenario_id",
        "family",
        "tier",
        "parameter_block_id",
        "route_identity_sha256",
        "corridor_group_sha256",
        "map_family_id",
        "seed",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "candidate0_sha256",
        "default_candidate0_identity",
        "candidate0_semantics",
        "candidate0_independent_second_forward",
        "causal_input_sha256",
        "causal_evidence_sha256",
        "route_lanes_sha256",
        "route_lanes_speed_limit_sha256",
        "route_lanes_has_speed_limit_sha256",
        "physical_feasible_mask",
        "source_valid_mask",
        "all_k_high_risk",
        "selected_index",
        "selected_trajectory_sha256",
        "score_contract",
        "tie_break_contract",
        "normalized_atom_matrix_sha256",
        "context_schema_version",
        "context_source_receipt",
        "generation_behavior_scale_sha256",
        "canonical_semantic_clone_sha256",
        "source_map_sha256",
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
    }
)
MODEL_INPUT_CACHE_RECEIPT_FIELDS = frozenset(
    {
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
)
ROUTE_SOURCE_ROW_FIELDS = frozenset(
    {
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
)
DEFAULT_CANDIDATE0_IDENTITY_FIELDS = frozenset(
    {
        "elementwise_equal",
        "default_output_sha256",
        "candidate0_sha256",
        "native_ranked_k8",
    }
)
CONTEXT_SOURCE_RECEIPT_FIELDS = frozenset(
    {"mode", "phase_remaining_available", "regulatory_signal_mapped"}
)
RUNTIME_SIGNAL_RECEIPT_FIELDS = frozenset(
    {
        "schema_version", "scenario_id", "tick_index", "phase_authority_mode",
        "current_phase", "decision_timestamp_s", "source_timestamp_s",
        "source_age_s", "freshness", "source_id", "regulatory_element_id",
        "physical_light_ids", "bulb_ids", "controlled_lanelet_ids",
        "stop_line_id", "stop_line_geometry_sha256", "route_geometry_sha256",
        "route_arc_m", "source_chain_sha256", "observed_route_lanelet_ids",
        "observed_map_lanelet_ids", "route_signal_tensor_sha256",
        "map_signal_tensor_sha256", "phase_remaining_available", "source_valid",
        "applicable",
    }
)
SIGNAL_TENSOR_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version", "tick_index", "decision_timestamp_s",
        "source_timestamp_s", "route_signal_rows", "map_signal_rows",
        "current_phase", "route_signal_tensor_sha256",
        "map_signal_tensor_sha256", "future_schedule_consumed",
        "phase_remaining_available",
    }
)
RUNTIME_NO_SIGNAL_RECEIPT_FIELDS = frozenset(
    {
        "schema_version", "scenario_id", "tick_index", "decision_time_s",
        "source_mode", "current_phase", "route_geometry_sha256",
        "route_lanelet_ids", "traffic_light_regulatory_element_ids",
        "source_chain_sha256", "semantic_clone_sha256",
        "phase_remaining_available", "source_valid", "applicable",
    }
)
CAUSAL_SIGNAL_ATOM_INPUT_FIELDS = frozenset(
    {
        "schema_version", "source_state", "source_valid", "applicable",
        "current_phase", "decision_time_s", "ego_position_world_m",
        "ego_heading_rad", "regulatory_element_id", "stop_line_id",
        "stop_line_geometry_world_m", "stop_line_geometry_ego_m",
        "stop_line_geometry_sha256", "route_tangent_world",
        "route_tangent_ego", "route_geometry_sha256", "route_arc_m",
        "source_chain_sha256", "runtime_receipt", "runtime_receipt_sha256",
    }
)
PROGRESS_FIELDS = frozenset(
    {
        "schema_version", "status", "completed", "total", "complete", "failed",
        "snapshot_count", "elapsed_seconds", "free_bytes", "fresh_b_opened",
    }
)
RESULT_FIELDS = frozenset(
    {
        "ordinal", "scenario_id", "family", "tier", "route_identity_sha256",
        "seed", "status", "snapshot_count", "failure_type", "failure_reason",
        "capability_failure", "wall_seconds", "retained",
        "outcome_fields_consumed", "fresh_b_opened",
    }
)
CAPABILITY_FAILURE_FIELDS = frozenset(
    {
        "scenario_id",
        "family",
        "source_class",
        "phase_authority_mode",
        "reason",
    }
)
FIXED_DP_CAPABILITY_FAILURE_FIELDS = frozenset(
    {
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
)
REPORT_FIELDS = frozenset(
    {
        "schema_version", "canonical_json_byte_spec", "camp_head",
        "implementation_source_head", "released_camp_source_head",
        "current_repo_head_at_run", "fixed_dp_head", "dp_repo",
        "formal_artifact", "formal_root_sha256", "probe_template",
        "probe_template_sha256", "generation_scales", "static_weights", "seed",
        "corpus_steps", "snapshot_capacity", "train_lock", "minimum_free_bytes",
        "rejected_roots", "r0_review_artifact", "r0_review_root_sha256",
        "r0_source_artifact", "r0_source_root_sha256", "seven_root_bindings",
        "seven_root_bindings_sha256", "release_run_nonce",
        "release_nonce_consumption_marker", "authorized_output_dir",
        "critical_implementation_manifest",
        "ultra_full_config_preflight_release_artifact",
        "ultra_full_config_preflight_release_root_sha256",
        "semantic_authority_root_sha256", "semantic_authority_identity_count",
        "semantic_authority_chains_root_sha256", "terminal_lock_scope",
        "free_bytes_at_start", "fresh_b_opened", "outcome_fields_consumed",
        "preflight_review_artifact", "preflight_review_root_sha256",
        "ultra_full_r_execute_release_artifact",
        "ultra_full_r_execute_release_root_sha256", "config_receipts_root_sha256",
        "mode", "status", "preflight_artifact", "preflight_root_sha256",
        "attempted_identity_count", "source_ineligible_retained_identity_count",
        "formal_train_manifest_identity_count", "complete_identity_count",
        "failed_identity_count", "retained_capability_failure_count",
        "retained_scenario_capability_failure_count",
        "retained_fixed_dp_capability_failure_count",
        "red_scientific_coverage", "retained_identity_count", "snapshot_count",
        "fixed_dp_support_coverage",
        "family_identity_counts", "family_snapshot_counts", "failure_reason_counts",
        "wall_seconds", "candidate_tensors_modified",
        "training_snapshot_outcome_fields",
        "runtime_outcomes_not_read_or_copied_to_training_snapshots",
        "selector_training_executed", "calibration_executed", "claim_authorized",
    }
)
_SHA_CHARS = frozenset("0123456789abcdef")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSONL objects: {path}")
        rows.append(value)
    return rows


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _oracle_canonical_snapshot_bytes(payload: Any) -> bytes:
    """Locally implement the frozen V25 snapshot byte contract."""
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _oracle_sha256(payload: Any) -> str:
    return hashlib.sha256(_oracle_canonical_snapshot_bytes(payload)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and not set(value) - _SHA_CHARS


def _native_bool_list(value: Any, length: int, label: str) -> None:
    if type(value) is not list or len(value) != length or any(
        type(item) is not bool for item in value
    ):
        raise ValueError(f"{label} must be a native boolean list[{length}]")


def _native_numeric_array(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    def flatten(node: Any, depth: int) -> list[float]:
        if depth == len(shape):
            if type(node) not in (int, float) or not np.isfinite(float(node)):
                raise ValueError(f"{label} must contain finite native numbers")
            return [float(node)]
        if type(node) is not list or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        values: list[float] = []
        for child in node:
            values.extend(flatten(child, depth + 1))
        return values

    return np.asarray(flatten(value, 0), dtype=np.float64).reshape(shape)


def _canonical_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_changed_paths(repo: Path, start: str, end: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", start, end, "--"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    paths = [line.replace("\\", "/") for line in completed.stdout.splitlines()]
    if len(paths) != len(set(paths)):
        raise ValueError("git diff returned duplicate paths")
    return paths


def _critical_manifest_at_head(repo: Path, head: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative in CRITICAL_IMPLEMENTATION_PATHS:
        completed = subprocess.run(
            ["git", "show", f"{head}:{relative}"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        manifest[relative] = hashlib.sha256(completed.stdout).hexdigest()
    return manifest


def _verify_historical_producer_and_posthoc_review_contract(
    *,
    repo: Path,
    implementation_source_head: Any,
    artifact_pointer_head: Any,
    current_review_head: Any,
    implementation_manifest: Any,
) -> dict[str, Any]:
    for label, value in (
        ("implementation source", implementation_source_head),
        ("artifact pointer", artifact_pointer_head),
        ("current review", current_review_head),
    ):
        if (
            type(value) is not str
            or len(value) != 40
            or set(value) - set("0123456789abcdef")
        ):
            raise ValueError(f"{label} HEAD is invalid")
    expected_manifest = _critical_manifest_at_head(repo, implementation_source_head)
    if (
        type(implementation_manifest) is not dict
        or set(implementation_manifest) != set(CRITICAL_IMPLEMENTATION_PATHS)
        or any(not _is_sha256(value) for value in implementation_manifest.values())
        or implementation_manifest != expected_manifest
    ):
        raise ValueError("historical producer critical manifest drifted")
    pointer_paths = _git_changed_paths(
        repo, implementation_source_head, artifact_pointer_head
    )
    if set(pointer_paths) - set(POINTER_ONLY_PATHS):
        raise ValueError("artifact source-to-pointer diff exceeds the frozen allowlist")
    correction_paths = _git_changed_paths(
        repo, artifact_pointer_head, current_review_head
    )
    if set(correction_paths) != set(POSTHOC_REVIEW_CORRECTION_PATHS):
        raise ValueError("post-hoc independent-review correction path set drifted")
    return {
        "implementation_source_head": implementation_source_head,
        "artifact_pointer_head": artifact_pointer_head,
        "current_review_head": current_review_head,
        "producer_manifest_sha256": _canonical_sha256(expected_manifest),
        "pointer_only_changed_paths": pointer_paths,
        "posthoc_review_correction_paths": correction_paths,
    }


def _native_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be a native integer")
    return value


def _native_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a native boolean")
    return value


def _json_type_exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _json_type_exact_equal(actual[key], value)
            for key, value in expected.items()
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _json_type_exact_equal(left, right)
            for left, right in zip(actual, expected)
        )
    return actual == expected


def _native_finite_number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not np.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _native_string(value: Any, label: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{label} must be a native string")
    return value


def _validate_string_int_mapping(value: Any, label: str) -> None:
    if type(value) is not dict or any(
        type(key) is not str or type(count) is not int or count < 0
        for key, count in value.items()
    ):
        raise ValueError(f"{label} must be an exact string-to-native-int object")


def _validate_terminal_schemas(
    report: Any, progress: Any, results: Any
) -> None:
    """Freeze terminal JSON field sets and discrete JSON-native types."""
    if type(report) is not dict or set(report) != REPORT_FIELDS:
        raise ValueError("corrected corpus report exact field set drifted")
    if type(progress) is not dict or set(progress) != PROGRESS_FIELDS:
        raise ValueError("corrected corpus progress exact field set drifted")
    if type(results) is not list:
        raise ValueError("corrected corpus results must be a list")
    for field in (
        "seed",
        "corpus_steps",
        "snapshot_capacity",
        "minimum_free_bytes",
        "free_bytes_at_start",
        "semantic_authority_identity_count",
        "attempted_identity_count",
        "source_ineligible_retained_identity_count",
        "formal_train_manifest_identity_count",
        "complete_identity_count",
        "failed_identity_count",
        "retained_capability_failure_count",
        "retained_scenario_capability_failure_count",
        "retained_fixed_dp_capability_failure_count",
        "retained_identity_count",
        "snapshot_count",
    ):
        if _native_int(report.get(field), f"report.{field}") < 0:
            raise ValueError(f"report.{field} must be nonnegative")
    for field in (
        "fresh_b_opened",
        "candidate_tensors_modified",
        "runtime_outcomes_not_read_or_copied_to_training_snapshots",
        "selector_training_executed",
        "calibration_executed",
        "claim_authorized",
    ):
        _native_bool(report.get(field), f"report.{field}")
    _native_finite_number(report.get("wall_seconds"), "report.wall_seconds")
    for field in (
        "family_identity_counts",
        "family_snapshot_counts",
        "failure_reason_counts",
    ):
        _validate_string_int_mapping(report.get(field), f"report.{field}")
    if (
        type(report.get("rejected_roots")) is not list
        or any(not _is_sha256(value) for value in report["rejected_roots"])
        or type(report.get("outcome_fields_consumed")) is not list
        or report["outcome_fields_consumed"] != []
        or type(report.get("training_snapshot_outcome_fields")) is not list
        or report["training_snapshot_outcome_fields"] != []
        or type(report.get("critical_implementation_manifest")) is not dict
    ):
        raise ValueError("corrected corpus report list/mapping contract drifted")
    for field in ("generation_scales", "static_weights", "release_nonce_consumption_marker"):
        value = report.get(field)
        if type(value) is not dict or set(value) != {"path", "sha256"}:
            raise ValueError(f"report.{field} exact receipt schema drifted")
        _native_string(value.get("path"), f"report.{field}.path")
        if not _is_sha256(value.get("sha256")):
            raise ValueError(f"report.{field}.sha256 is invalid")
    if (
        not _is_sha256(report.get("release_run_nonce"))
        or type(report.get("authorized_output_dir")) is not str
        or not Path(report["authorized_output_dir"]).is_absolute()
        or report["authorized_output_dir"]
        != str(Path(report["authorized_output_dir"]).resolve())
        or type(report.get("seven_root_bindings")) is not dict
        or not _is_sha256(report.get("seven_root_bindings_sha256"))
    ):
        raise ValueError("corrected corpus release/root authority type drifted")
    coverage = report.get("red_scientific_coverage")
    coverage_fields = {
        "formal_identity_count", "formal_by_tier",
        "formal_distinct_source_map_count", "complete_by_tier",
        "complete_distinct_source_map_count", "minimum_complete_by_tier",
        "minimum_distinct_source_maps", "passed",
    }
    if type(coverage) is not dict or set(coverage) != coverage_fields:
        raise ValueError("report.red_scientific_coverage exact schema drifted")
    for field in (
        "formal_identity_count", "formal_distinct_source_map_count",
        "complete_distinct_source_map_count", "minimum_distinct_source_maps",
    ):
        if _native_int(coverage.get(field), f"red coverage {field}") < 0:
            raise ValueError(f"red coverage {field} must be nonnegative")
    for field in ("formal_by_tier", "complete_by_tier", "minimum_complete_by_tier"):
        value = coverage.get(field)
        if type(value) is not dict or set(value) != {"easy", "borderline", "high_risk"}:
            raise ValueError(f"red coverage {field} tier schema drifted")
        _validate_string_int_mapping(value, f"red coverage {field}")
    _native_bool(coverage.get("passed"), "red coverage passed")
    for field in (
        "completed",
        "total",
        "complete",
        "failed",
        "snapshot_count",
        "free_bytes",
    ):
        if _native_int(progress.get(field), f"progress.{field}") < 0:
            raise ValueError(f"progress.{field} must be nonnegative")
    _native_finite_number(progress.get("elapsed_seconds"), "progress.elapsed_seconds")
    _native_bool(progress.get("fresh_b_opened"), "progress.fresh_b_opened")
    _native_string(progress.get("schema_version"), "progress.schema_version")
    _native_string(progress.get("status"), "progress.status")
    for ordinal, row in enumerate(results):
        if type(row) is not dict or set(row) != RESULT_FIELDS:
            raise ValueError("corrected corpus result exact field set drifted")
        if _native_int(row.get("ordinal"), "result.ordinal") != ordinal:
            raise ValueError("corrected corpus result ordinal drifted")
        if _native_int(row.get("seed"), "result.seed") < 0:
            raise ValueError("corrected corpus result seed is invalid")
        if _native_int(row.get("snapshot_count"), "result.snapshot_count") < 0:
            raise ValueError("corrected corpus result snapshot_count is invalid")
        for field in (
            "scenario_id",
            "family",
            "tier",
            "route_identity_sha256",
            "status",
        ):
            _native_string(row.get(field), f"result.{field}")
        _native_bool(row.get("retained"), "result.retained")
        _native_bool(row.get("fresh_b_opened"), "result.fresh_b_opened")
        _native_finite_number(row.get("wall_seconds"), "result.wall_seconds")
        if type(row.get("outcome_fields_consumed")) is not list:
            raise ValueError("result.outcome_fields_consumed must be a list")
        if row["outcome_fields_consumed"] != []:
            raise ValueError("result consumed forbidden outcome fields")
        if not _is_sha256(row["scenario_id"]) or not _is_sha256(
            row["route_identity_sha256"]
        ):
            raise ValueError("result identity SHA contract drifted")
        if row["status"] == "complete":
            if any(
                row[field] is not None
                for field in ("failure_type", "failure_reason", "capability_failure")
            ):
                raise ValueError("complete result carries failure metadata")
        elif row["status"] == "failed":
            failure = row.get("capability_failure")
            if row.get("failure_type") == "RetainedScenarioCapabilityFailure":
                if (
                    type(row.get("failure_reason")) is not str
                    or type(failure) is not dict
                    or set(failure) != CAPABILITY_FAILURE_FIELDS
                    or any(type(value) is not str for value in failure.values())
                    or failure.get("scenario_id") != row.get("scenario_id")
                    or failure.get("family") != row.get("family")
                    or failure.get("source_class") != "mapped_signal"
                    or failure.get("phase_authority_mode")
                    not in {
                        "controlled_same_tick_override",
                        "observe_same_tick_request",
                    }
                    or failure.get("reason")
                    != "mapped_current_signal_source_unavailable"
                ):
                    raise ValueError("failed scenario capability receipt drifted")
            elif row.get("failure_type") == FixedDpCandidateGenerationCapabilityFailure.__name__:
                _validate_fixed_dp_failure_receipt(
                    failure, result=row, artifact=None
                )
            else:
                raise ValueError("failed result capability class drifted")
        else:
            raise ValueError("result status is invalid")


def _validate_fixed_dp_failure_receipt(
    value: Any,
    *,
    result: Mapping[str, Any],
    artifact: Path | None,
) -> str:
    if type(value) is not dict or set(value) != FIXED_DP_CAPABILITY_FAILURE_FIELDS:
        raise ValueError("fixed-DP capability receipt schema drifted")
    exact = {
        "schema_version": FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
        "failure_class": FIXED_DP_FAILURE_CLASS,
        "reason": FIXED_DP_FAILURE_REASON,
        "scenario_id": result.get("scenario_id"),
        "route_identity_sha256": result.get("route_identity_sha256"),
        "family": result.get("family"),
        "tier": result.get("tier"),
        "fixed_dp_head": FIXED_DP_HEAD,
        "heading_norm_minimum": 0.5,
        "heading_norm_maximum": 1.5,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not _json_type_exact_equal(value.get(key), expected) for key, expected in exact.items()):
        raise ValueError("fixed-DP capability receipt authority drifted")
    if (
        type(value.get("tick_index")) is not int
        or not 0 <= value["tick_index"] < CORPUS_STEPS
        or type(value.get("invalid_count")) is not int
        or value["invalid_count"] <= 0
        or type(value.get("invalid_indices")) is not list
        or len(value["invalid_indices"]) != value["invalid_count"]
    ):
        raise ValueError("fixed-DP capability receipt index drifted")
    pairs = []
    for row in value["invalid_indices"]:
        if (
            type(row) is not dict
            or set(row) != {"candidate_index", "step_index"}
            or type(row.get("candidate_index")) is not int
            or type(row.get("step_index")) is not int
            or not 0 <= row["candidate_index"] < 8
            or not 0 <= row["step_index"] < 80
        ):
            raise ValueError("fixed-DP capability invalid-index drifted")
        pairs.append((row["candidate_index"], row["step_index"]))
    if pairs != sorted(set(pairs)):
        raise ValueError("fixed-DP capability invalid indices are not canonical")
    preimage = value.get("raw_preimage")
    if (
        type(preimage) is not dict
        or set(preimage)
        != {"relative_path", "file_sha256", "array_sha256", "shape", "dtype"}
        or preimage.get("relative_path")
        != f"fixed_dp_capability_failures/{value.get('raw_k8_sha256')}.bin"
        or preimage.get("file_sha256") != value.get("raw_k8_sha256")
        or preimage.get("array_sha256") != value.get("raw_k8_sha256")
        or preimage.get("shape") != [8, 80, 4]
        or preimage.get("dtype") != "float32"
    ):
        raise ValueError("fixed-DP capability preimage receipt drifted")
    identity = value.get("default_candidate0_identity")
    if (
        type(identity) is not dict
        or set(identity)
        != {
            "elementwise_equal", "max_abs_difference", "default_output_sha256",
            "candidate0_sha256", "native_ranked_k8",
        }
        or identity.get("elementwise_equal") is not True
        or identity.get("max_abs_difference") != 0.0
        or identity.get("native_ranked_k8") is not False
        or identity.get("candidate0_sha256") != value.get("candidate0_sha256")
        or identity.get("default_output_sha256")
        != value.get("default_output_sha256")
        or value.get("candidate0_sha256") != value.get("default_output_sha256")
    ):
        raise ValueError("fixed-DP capability candidate0 authority drifted")
    if artifact is None:
        return str(preimage["relative_path"])
    path = artifact / preimage["relative_path"]
    if path.is_symlink() or not path.is_file():
        raise ValueError("fixed-DP capability preimage is unavailable")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != value.get("raw_k8_sha256") or len(data) != 8 * 80 * 4 * 4:
        raise ValueError("fixed-DP capability preimage digest/size drifted")
    tensor = np.frombuffer(data, dtype=np.float32).reshape(8, 80, 4)
    if not np.isfinite(tensor).all():
        raise ValueError("fixed-DP capability preimage is nonfinite")
    norms = np.linalg.norm(tensor[..., 2:4].astype(np.float64), axis=2)
    invalid = np.abs(norms - 1.0) > 0.5
    rebuilt = [
        {"candidate_index": int(candidate), "step_index": int(step)}
        for candidate, step in np.argwhere(invalid)
    ]
    candidate0 = hashlib.sha256(
        np.ascontiguousarray(tensor[0]).tobytes(order="C")
    ).hexdigest()
    if (
        not rebuilt
        or rebuilt != value["invalid_indices"]
        or len(rebuilt) != value["invalid_count"]
        or value.get("minimum_heading_norm") != float(norms.min())
        or value.get("maximum_heading_norm") != float(norms.max())
        or value.get("candidate0_sha256") != candidate0
    ):
        raise ValueError("fixed-DP capability independent numeric oracle failed")
    return str(preimage["relative_path"])


def _independent_full_support_coverage(
    *, results: list[Mapping[str, Any]], source_rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    rows = []
    for result in results:
        source = source_rows.get(str(result["scenario_id"]))
        if type(source) is not dict:
            raise ValueError("full support source row is unavailable")
        rows.append(
            {
                "family": str(result["family"]),
                "tier": str(result["tier"]),
                "source_class": str(source["source_class"]),
                "phase_authority_mode": str(source["phase_authority_mode"]),
                "status": str(result["status"]),
            }
        )

    def grouped(fields: tuple[str, ...], minimum: int) -> dict[str, Any]:
        totals: collections.Counter[tuple[str, ...]] = collections.Counter()
        completes: collections.Counter[tuple[str, ...]] = collections.Counter()
        for row in rows:
            key = tuple(row[field] for field in fields)
            totals[key] += 1
            if row["status"] == "complete":
                completes[key] += 1
        table = []
        passed = True
        for key in sorted(totals):
            ok = completes[key] > 0 and completes[key] * 100 > totals[key] * minimum
            passed = passed and ok
            table.append({"key": list(key), "planned": totals[key], "complete": completes[key], "passed": ok})
        return {"fields": list(fields), "minimum_percent_exclusive": minimum, "rows": table, "passed": passed}

    complete = sum(row["status"] == "complete" for row in rows)
    family = grouped(("family",), 90)
    source = grouped(("source_class", "phase_authority_mode"), 90)
    family_tier = grouped(("family", "tier"), 80)
    return {
        "planned_identity_count": len(rows),
        "complete_identity_count": complete,
        "minimum_complete_identity_count": 1425,
        "family": family,
        "source_mode": source,
        "family_tier": family_tier,
        "passed": bool(
            len(rows) == EXPECTED_EXECUTABLE_IDENTITIES
            and complete >= 1425
            and family["passed"]
            and source["passed"]
            and family_tier["passed"]
        ),
    }


def _reject_forbidden_nested_fields(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if type(key) is not str:
                raise ValueError("snapshot contains a non-string JSON key")
            lowered = key.lower()
            normalized = "".join(
                character for character in lowered if character.isalnum()
            )
            forbidden = (
                "future" in normalized
                or "holdout" in normalized
                or "idproxy" in normalized
                or "identityproxy" in normalized
                or (
                    "outcome" in normalized
                    and key != "outcome_fields_consumed"
                )
                or (
                    "label" in normalized
                    and key != "offline_label_provenance"
                )
            )
            if (
                key == "future_schedule_consumed"
                and child is False
                and path
                in {
                    ("sidecar", "controlled_signal_tensor_evidence"),
                    ("sidecar", "controlled_model_input_cache_receipt"),
                }
            ):
                forbidden = False
            if forbidden:
                raise ValueError(
                    "snapshot contains forbidden field: " + ".".join((*path, key))
                )
            _reject_forbidden_nested_fields(child, (*path, key))
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_nested_fields(child, path)


def _validate_context_and_signal_receipts(sidecar: Mapping[str, Any]) -> None:
    context = sidecar.get("context_source_receipt")
    if type(context) is not dict or set(context) != CONTEXT_SOURCE_RECEIPT_FIELDS:
        raise ValueError("context_source_receipt exact schema drifted")
    if (
        context.get("mode") != "no_v2i"
        or type(context.get("phase_remaining_available")) is not bool
        or context.get("phase_remaining_available") is not False
        or type(context.get("regulatory_signal_mapped")) is not bool
    ):
        raise ValueError("context_source_receipt no-V2I contract drifted")

    receipt = sidecar.get("controlled_signal_source_receipt")
    causal = sidecar.get("causal_signal_atom_input")
    if type(receipt) is not dict or type(causal) is not dict:
        raise ValueError("signal/no-signal receipts must be exact objects")
    source_class = sidecar.get("signal_source_class")
    phase_mode = sidecar.get("phase_authority_mode")
    evidence = sidecar.get("controlled_signal_tensor_evidence")
    mode = receipt.get("source_mode")
    expected_fields = RUNTIME_SIGNAL_RECEIPT_FIELDS if source_class == "mapped_signal" else (
        RUNTIME_NO_SIGNAL_RECEIPT_FIELDS
        if source_class == "no_signal" and mode == "same_tick_no_signal_rule_no_v2i"
        else frozenset()
    )
    if set(receipt) != expected_fields:
        raise ValueError("runtime signal receipt exact schema drifted")
    if source_class == "mapped_signal":
        if (
            receipt.get("schema_version")
            != MAPPED_SIGNAL_RUNTIME_RECEIPT_SCHEMA_VERSION
            or phase_mode not in {
                "controlled_same_tick_override",
                "observe_same_tick_request",
            }
            or receipt.get("phase_authority_mode") != phase_mode
            or type(receipt.get("tick_index")) is not int
            or any(
                type(receipt.get(field)) is not float
                or not np.isfinite(receipt[field])
                for field in (
                    "decision_timestamp_s",
                    "source_timestamp_s",
                    "source_age_s",
                )
            )
            or receipt.get("source_age_s") != 0.0
            or not np.isclose(
                receipt.get("decision_timestamp_s")
                - receipt.get("source_timestamp_s"),
                receipt.get("source_age_s"),
                rtol=0.0,
                atol=1e-12,
            )
            or not np.isclose(
                receipt.get("decision_timestamp_s"),
                0.1 * receipt.get("tick_index"),
                rtol=0.0,
                atol=1e-12,
            )
            or receipt.get("freshness") != "same_tick"
            or receipt.get("source_id")
            != "fixed_dp_current_request_route_map_signal_one_hot"
            or receipt.get("phase_remaining_available") is not False
            or receipt.get("source_valid") is not True
            or type(receipt.get("applicable")) is not bool
            or receipt.get("applicable") is not (receipt.get("current_phase") == "red")
        ):
            raise ValueError("mapped runtime signal receipt type/value contract drifted")
        for field in (
            "regulatory_element_id",
            "stop_line_id",
        ):
            _native_int(receipt.get(field), f"runtime receipt {field}")
        for field in (
            "physical_light_ids",
            "bulb_ids",
            "controlled_lanelet_ids",
            "observed_route_lanelet_ids",
            "observed_map_lanelet_ids",
        ):
            values = receipt.get(field)
            if (
                type(values) is not list
                or any(type(value) is not int for value in values)
                or len(values) != len(set(values))
            ):
                raise ValueError(f"runtime receipt {field} must be native int list")
        _native_finite_number(receipt.get("route_arc_m"), "runtime receipt route_arc_m")
        if receipt.get("current_phase") not in {"green", "yellow", "red"}:
            raise ValueError("runtime signal phase is invalid")
        if type(evidence) is not dict or set(evidence) != SIGNAL_TENSOR_EVIDENCE_FIELDS:
            raise ValueError("production signal tensor evidence exact schema drifted")
        if (
            evidence.get("schema_version")
            != "camp_dp_v25_production_signal_tensor_evidence_v2"
            or type(evidence.get("tick_index")) is not int
            or evidence.get("tick_index") != receipt.get("tick_index")
            or evidence.get("decision_timestamp_s")
            != receipt.get("decision_timestamp_s")
            or evidence.get("source_timestamp_s") != receipt.get("source_timestamp_s")
            or evidence.get("current_phase") != receipt.get("current_phase")
            or evidence.get("future_schedule_consumed") is not False
            or evidence.get("phase_remaining_available") is not False
        ):
            raise ValueError("production signal tensor evidence values drifted")

        def validate_rows(rows: Any, label: str) -> tuple[list[int], set[str]]:
            if type(rows) is not list:
                raise ValueError(f"{label} signal rows must be a list")
            ids: list[int] = []
            phases: set[str] = set()
            for row in rows:
                if type(row) is not dict or set(row) != {
                    "lanelet_id", "signal_channels_8_12"
                } or type(row.get("lanelet_id")) is not int:
                    raise ValueError(f"{label} signal row schema drifted")
                values_raw = row.get("signal_channels_8_12")
                if type(values_raw) is not list or not values_raw:
                    raise ValueError(f"{label} signal row values are missing")
                values = _native_numeric_array(
                    values_raw, (len(values_raw), 5), f"{label} signal row"
                )
                active = np.any(np.abs(values) > 1e-12, axis=1)
                if not np.any(active):
                    raise ValueError(f"{label} signal row has no active source")
                row_phases: set[str] = set()
                for phase, column in {"green": 0, "yellow": 1, "red": 2}.items():
                    matches = np.isclose(
                        values[active, column], 1.0, rtol=0.0, atol=1e-8
                    )
                    other = np.delete(values[active], column, axis=1)
                    matches &= np.all(
                        np.isclose(other, 0.0, rtol=0.0, atol=1e-8), axis=1
                    )
                    if np.any(matches):
                        row_phases.add(phase)
                    if not np.all(matches) and np.any(matches):
                        raise ValueError(f"{label} signal row phase is not uniform")
                if len(row_phases) != 1:
                    raise ValueError(f"{label} signal row is missing/multihot/unknown")
                ids.append(row["lanelet_id"])
                phases.update(row_phases)
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} signal row lanelet IDs are duplicated")
            return ids, phases

        route_ids, route_phases = validate_rows(evidence["route_signal_rows"], "route")
        map_ids, map_phases = validate_rows(evidence["map_signal_rows"], "map")
        phases = route_phases | map_phases
        if (
            not phases
            or phases != {receipt["current_phase"]}
            or route_ids != receipt["observed_route_lanelet_ids"]
            or map_ids != receipt["observed_map_lanelet_ids"]
            or _oracle_sha256(evidence["route_signal_rows"])
            != receipt["route_signal_tensor_sha256"]
            or _oracle_sha256(evidence["map_signal_rows"])
            != receipt["map_signal_tensor_sha256"]
            or evidence["route_signal_tensor_sha256"]
            != receipt["route_signal_tensor_sha256"]
            or evidence["map_signal_tensor_sha256"]
            != receipt["map_signal_tensor_sha256"]
        ):
            raise ValueError("mapped signal tensor evidence/receipt binding drifted")
    else:
        if (
            phase_mode is not None
            or evidence is not None
            or receipt.get("schema_version") != RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION
            or type(receipt.get("tick_index")) is not int
            or type(receipt.get("decision_time_s")) is not float
            or not np.isfinite(receipt["decision_time_s"])
            or receipt.get("phase_remaining_available") is not False
            or receipt.get("source_valid") is not True
        ):
            raise ValueError("runtime no-signal receipt type/value contract drifted")
        for field in (
            "route_lanelet_ids",
            "traffic_light_regulatory_element_ids",
        ):
            values = receipt.get(field)
            if (
                type(values) is not list
                or any(type(value) is not int for value in values)
                or len(values) != len(set(values))
            ):
                raise ValueError(f"runtime no-signal {field} must be native int list")
        _native_bool(receipt.get("applicable"), "runtime no-signal applicable")
        if receipt.get("current_phase") != "none":
            raise ValueError("runtime no-signal phase is invalid")
    if set(causal) != CAUSAL_SIGNAL_ATOM_INPUT_FIELDS:
        raise ValueError("causal signal atom input exact schema drifted")
    if (
        causal.get("schema_version") != CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION
        or type(causal.get("source_valid")) is not bool
        or type(causal.get("applicable")) is not bool
        or type(causal.get("decision_time_s")) is not float
        or not np.isfinite(causal["decision_time_s"])
        or not _json_type_exact_equal(causal.get("runtime_receipt"), receipt)
    ):
        raise ValueError("causal signal atom input type/value contract drifted")
    if causal.get("source_state") not in {"available", "not_applicable"}:
        raise ValueError("causal signal source state is invalid")
    if causal.get("source_state") == "available":
        _native_numeric_array(
            causal.get("ego_position_world_m"), (2,), "causal ego position"
        )
        _native_finite_number(causal.get("ego_heading_rad"), "causal ego heading")
        stop_world = causal.get("stop_line_geometry_world_m")
        stop_ego = causal.get("stop_line_geometry_ego_m")
        if (
            type(stop_world) is not list
            or len(stop_world) < 2
            or type(stop_ego) is not list
            or len(stop_ego) != len(stop_world)
        ):
            raise ValueError("causal stop-line geometry shape drifted")
        _native_numeric_array(
            stop_world, (len(stop_world), 2), "causal world stop line"
        )
        _native_numeric_array(
            stop_ego, (len(stop_ego), 2), "causal ego stop line"
        )
        _native_numeric_array(
            causal.get("route_tangent_world"), (2,), "causal world route tangent"
        )
        _native_numeric_array(
            causal.get("route_tangent_ego"), (2,), "causal ego route tangent"
        )
        _native_finite_number(causal.get("route_arc_m"), "causal route arc")
        _native_int(causal.get("regulatory_element_id"), "causal regulatory id")
        _native_int(causal.get("stop_line_id"), "causal stop line id")
    else:
        for field in (
            "ego_position_world_m",
            "ego_heading_rad",
            "regulatory_element_id",
            "stop_line_id",
            "stop_line_geometry_world_m",
            "stop_line_geometry_ego_m",
            "stop_line_geometry_sha256",
            "route_tangent_world",
            "route_tangent_ego",
            "route_arc_m",
        ):
            if causal.get(field) is not None:
                raise ValueError(f"causal no-signal {field} must be null")
    validate_causal_signal_atom_input(causal)

    cache = sidecar.get("controlled_model_input_cache_receipt")
    if type(cache) is not dict or set(cache) != MODEL_INPUT_CACHE_RECEIPT_FIELDS:
        raise ValueError("model-input signal cache receipt exact schema drifted")
    if (
        cache.get("schema_version")
        != MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION
        or cache.get("scenario_id") != sidecar.get("scenario_id")
        or type(cache.get("tick_index")) is not int
        or cache.get("tick_index") != sidecar.get("tick_index")
        or cache.get("signal_source_class") != source_class
        or cache.get("phase_authority_mode") != phase_mode
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
            phase_mode != "controlled_same_tick_override"
            and cache.get("observe_cache_unchanged") is not True
        )
    ):
        raise ValueError("model-input signal cache receipt value contract drifted")


def _validate_snapshot_index_row(row: Any) -> None:
    if type(row) is not dict or set(row) != SNAPSHOT_INDEX_FIELDS:
        raise ValueError("snapshot index row exact field set drifted")
    if not _is_sha256(row.get("scenario_id")):
        raise ValueError("snapshot index scenario_id must be a SHA256 string")
    if type(row.get("tick_index")) is not int:
        raise ValueError("snapshot index tick_index must be a native integer")
    relative = row.get("relative_path")
    if type(relative) is not str:
        raise ValueError("snapshot index relative_path must be a native string")
    if not _is_sha256(row.get("sha256")):
        raise ValueError("snapshot index sha256 must be a SHA256 string")


def _validate_snapshot_field_schema(
    snapshot: Any, *, artifact_root: Path
) -> set[str]:
    if type(snapshot) is not dict or set(snapshot) != SNAPSHOT_FIELDS:
        raise ValueError("snapshot top-level exact field set drifted")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    if type(features) is not dict or set(features) != FEATURE_PAYLOAD_FIELDS:
        raise ValueError("snapshot feature_payload exact field set drifted")
    if type(sidecar) is not dict or set(sidecar) != SIDECAR_FIELDS:
        raise ValueError("snapshot sidecar exact field set drifted")
    if type(snapshot.get("schema_version")) is not str:
        raise ValueError("snapshot schema_version must be a native string")

    _native_bool_list(features.get("source_valid_mask"), 8, "source_valid_mask")
    _native_bool_list(
        features.get("physical_feasible_mask"), 8, "physical_feasible_mask"
    )
    for field in ("atom_source_valid_mask", "atom_applicable_mask"):
        matrix = features.get(field)
        if type(matrix) is not list or len(matrix) != 8 or any(
            type(row) is not list
            or len(row) != 14
            or any(type(item) is not bool for item in row)
            for row in matrix
        ):
            raise ValueError(f"{field} must be native bool[8,14]")
    rows = features.get("candidate_row_sha256")
    if type(rows) is not list or len(rows) != 8 or any(
        not _is_sha256(value) for value in rows
    ):
        raise ValueError("candidate_row_sha256 must be eight SHA256 strings")
    atoms = _native_numeric_array(features.get("atom_matrix"), (8, 14), "atom_matrix")
    candidates = _native_numeric_array(
        features.get("candidate_tensor"), (8, 80, 4), "candidate_tensor"
    ).astype(np.float32)
    validate_fixed_k8_candidate_tensor(candidates)
    default = _native_numeric_array(
        features.get("default_output"), (80, 4), "default_output"
    ).astype(np.float32)
    if np.any(atoms < 0.0):
        raise ValueError("atom_matrix must be nonnegative")
    raw_context = features.get("raw_context")
    source_complete = features.get("context_source_complete")
    if type(raw_context) is not dict or set(raw_context) != set(RAW_FEATURE_NAMES) or any(
        type(value) not in (int, float) or not np.isfinite(float(value))
        for value in raw_context.values()
    ):
        raise ValueError("raw_context must exactly match finite RAW_FEATURE_NAMES")
    if type(source_complete) is not dict or set(source_complete) != set(RAW_FEATURE_NAMES) or any(
        type(value) is not bool for value in source_complete.values()
    ):
        raise ValueError(
            "context_source_complete must exactly match boolean RAW_FEATURE_NAMES"
        )
    causal_reference = features.get("causal_evidence")
    causal, referenced_shards = independently_materialize_causal_evidence(
        artifact_root=artifact_root,
        reference=causal_reference,
    )
    causal_fields = {
        "schema_version", "ego_current_state", "ego_shape", "neighbor_agents_past",
        "neighbor_valid_mask", "candidate_neighbor_predictions", "static_objects",
        "route_lanes", "route_lanes_speed_limit", "route_lanes_has_speed_limit",
        "signal_mask", "fixed_dp_planned_red_light_cost",
    }
    if (
        type(causal) is not dict
        or set(causal) != causal_fields
        or causal.get("schema_version") != "camp_dp_v25_bounded_causal_evidence_v1"
    ):
        raise ValueError("causal_evidence exact field/schema contract drifted")
    causal_arrays = {
        "ego_current_state": _native_numeric_array(causal.get("ego_current_state"), (10,), "ego_current_state").astype(np.float32),
        "ego_shape": _native_numeric_array(causal.get("ego_shape"), (3,), "ego_shape").astype(np.float32),
        "neighbor_agents_past": _native_numeric_array(causal.get("neighbor_agents_past"), (32, 31, 11), "neighbor_agents_past").astype(np.float32),
        "candidate_neighbor_predictions": _native_numeric_array(causal.get("candidate_neighbor_predictions"), (8, 32, 80, 4), "candidate_neighbor_predictions").astype(np.float32),
        "static_objects": _native_numeric_array(causal.get("static_objects"), (5, 10), "static_objects").astype(np.float32),
        "route_lanes": _native_numeric_array(causal.get("route_lanes"), (25, 20, 33), "route_lanes").astype(np.float32),
        "route_lanes_speed_limit": _native_numeric_array(causal.get("route_lanes_speed_limit"), (25, 1), "route_lanes_speed_limit").astype(np.float32),
        "fixed_dp_planned_red_light_cost": _native_numeric_array(causal.get("fixed_dp_planned_red_light_cost"), (8,), "fixed_dp_planned_red_light_cost"),
    }
    for field, shape in (
        ("neighbor_valid_mask", (32,)),
        ("route_lanes_has_speed_limit", (25, 1)),
        ("signal_mask", (8,)),
    ):
        raw_mask = causal.get(field)
        mask = np.asarray(raw_mask)
        if type(raw_mask) is not list or mask.shape != shape or mask.dtype != np.bool_:
            raise ValueError(f"causal {field} must be native bool{shape}")
        causal_arrays[field] = mask

    if type(sidecar.get("tick_index")) is not int:
        raise ValueError("sidecar tick_index must be a native integer")
    if type(sidecar.get("dt_s")) is not float or not np.isfinite(sidecar["dt_s"]):
        raise ValueError("sidecar dt_s must be a finite native float")
    if type(sidecar.get("seed")) is not int:
        raise ValueError("sidecar seed must be a native integer")
    for field in (
        "scenario_id",
        "family",
        "tier",
        "parameter_block_id",
        "route_identity_sha256",
        "corridor_group_sha256",
        "map_family_id",
        "candidate0_semantics",
        "score_contract",
        "tie_break_contract",
        "context_schema_version",
        "offline_label_provenance",
        "signal_source_class",
    ):
        if type(sidecar.get(field)) is not str:
            raise ValueError(f"sidecar {field} must be a native string")
    for field in (
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "candidate0_sha256",
        "causal_input_sha256",
        "causal_evidence_sha256",
        "route_lanes_sha256",
        "route_lanes_speed_limit_sha256",
        "route_lanes_has_speed_limit_sha256",
        "selected_trajectory_sha256",
        "normalized_atom_matrix_sha256",
        "generation_behavior_scale_sha256",
        "source_map_sha256",
        "route_signal_source_artifact_root_sha256",
        "route_signal_source_row_sha256",
    ):
        if not _is_sha256(sidecar.get(field)):
            raise ValueError(f"sidecar {field} must be a SHA256 string")
    if (
        sidecar["causal_evidence_sha256"] != _canonical_sha256(causal)
        or sidecar["route_lanes_sha256"]
        != hashlib.sha256(np.ascontiguousarray(causal_arrays["route_lanes"]).tobytes()).hexdigest()
        or sidecar["route_lanes_speed_limit_sha256"]
        != hashlib.sha256(np.ascontiguousarray(causal_arrays["route_lanes_speed_limit"]).tobytes()).hexdigest()
        or sidecar["route_lanes_has_speed_limit_sha256"]
        != hashlib.sha256(np.ascontiguousarray(causal_arrays["route_lanes_has_speed_limit"]).tobytes()).hexdigest()
    ):
        raise ValueError("causal evidence SHA binding drifted")
    semantic = sidecar.get("canonical_semantic_clone_sha256")
    if semantic is not None and not _is_sha256(semantic):
        raise ValueError("canonical semantic clone must be null or SHA256")
    if sidecar.get("signal_source_class") == "mapped_signal":
        if sidecar.get("phase_authority_mode") not in {
            "controlled_same_tick_override",
            "observe_same_tick_request",
        }:
            raise ValueError("mapped signal phase-authority mode is invalid")
    elif sidecar.get("signal_source_class") == "no_signal":
        if sidecar.get("phase_authority_mode") is not None:
            raise ValueError("no-signal phase-authority mode must be null")
    else:
        raise ValueError("snapshot signal source class is invalid")
    for field in (
        "candidate0_independent_second_forward",
        "all_k_high_risk",
        "fresh_b_opened",
    ):
        if type(sidecar.get(field)) is not bool:
            raise ValueError(f"sidecar {field} must be a native boolean")
    if type(sidecar.get("selected_index")) is not int:
        raise ValueError("sidecar selected_index must be a native integer")
    _native_bool_list(
        sidecar.get("physical_feasible_mask"), 8, "sidecar physical_feasible_mask"
    )
    _native_bool_list(
        sidecar.get("source_valid_mask"), 8, "sidecar source_valid_mask"
    )
    identity = sidecar.get("default_candidate0_identity")
    if type(identity) is not dict or set(identity) != DEFAULT_CANDIDATE0_IDENTITY_FIELDS:
        raise ValueError("default_candidate0_identity exact field set drifted")
    if (
        type(identity.get("elementwise_equal")) is not bool
        or type(identity.get("native_ranked_k8")) is not bool
        or not _is_sha256(identity.get("default_output_sha256"))
        or not _is_sha256(identity.get("candidate0_sha256"))
    ):
        raise ValueError("default_candidate0_identity type contract drifted")
    _validate_context_and_signal_receipts(sidecar)
    if type(sidecar.get("outcome_fields_consumed")) is not list:
        raise ValueError("outcome_fields_consumed must be a list")
    source_valid = features["source_valid_mask"]
    source_matrix = features["atom_source_valid_mask"]
    applicable = features["atom_applicable_mask"]
    physical = features["physical_feasible_mask"]
    sidecar_source = sidecar["source_valid_mask"]
    sidecar_physical = sidecar["physical_feasible_mask"]
    candidate_rows = [
        hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest()
        for row in candidates
    ]
    tensor_sha = hashlib.sha256(
        np.ascontiguousarray(candidates).tobytes()
    ).hexdigest()
    default_sha = hashlib.sha256(np.ascontiguousarray(default).tobytes()).hexdigest()
    selected = sidecar["selected_index"]
    causal_signal = sidecar["causal_signal_atom_input"]
    signal_applicable = (
        causal_signal["source_state"] == "available"
        and causal_signal["current_phase"] == "red"
    )
    signal_columns = (10, 12)
    if (
        not any(source_valid)
        or source_valid != [all(row) for row in source_matrix]
        or any(
            applicable[row][column] and not source_matrix[row][column]
            for row in range(8)
            for column in range(14)
        )
        or sidecar_source != source_valid
        or sidecar_physical != physical
        or any(physical[index] and not source_valid[index] for index in range(8))
        or sidecar["all_k_high_risk"]
        is not (all(source_valid) and not any(physical))
        or features["candidate_row_sha256"] != candidate_rows
        or sidecar["candidate_tensor_sha256_before"] != tensor_sha
        or sidecar["candidate_tensor_sha256_after"] != tensor_sha
        or sidecar["default_output_sha256"] != default_sha
        or sidecar["candidate0_sha256"] != candidate_rows[0]
        or not np.array_equal(default, candidates[0])
        or identity["elementwise_equal"] is not True
        or identity["native_ranked_k8"] is not False
        or identity["default_output_sha256"] != default_sha
        or identity["candidate0_sha256"] != candidate_rows[0]
        or sidecar["candidate0_semantics"]
        != "operational_default_alias_from_same_forward"
        or sidecar["candidate0_independent_second_forward"] is not False
        or not 0 <= selected < 8
        or not source_valid[selected]
        or sidecar["selected_trajectory_sha256"] != candidate_rows[selected]
        or any(
            applicable[row][column] is not signal_applicable
            for row in range(8)
            for column in signal_columns
        )
        or (
            not signal_applicable
            and any(atoms[row, column] != 0.0 for row in range(8) for column in signal_columns)
        )
        or sidecar["outcome_fields_consumed"] != []
        or sidecar["fresh_b_opened"] is not False
    ):
        raise ValueError("snapshot candidate0/mask/source/all-K contract drifted")
    _reject_forbidden_nested_fields(snapshot)


def _read_verified_content_addressed_snapshot(
    path: Path, expected_sha256: Any
) -> dict[str, Any]:
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(
            character not in "0123456789abcdef" for character in expected_sha256
        )
    ):
        raise ValueError("snapshot index SHA256 is invalid")
    payload = independently_read_snapshot(path, expected_sha256)
    if not isinstance(payload, dict):
        raise ValueError("snapshot payload is not an object")
    return payload


def _open_route_source_authority(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    source_review_artifact: Path,
    source_review_root_sha256: str,
) -> dict[str, Mapping[str, Any]]:
    source_seal = verify_complete_seal(
        source_artifact, source_root_sha256, label="V25 route source census"
    )
    review_seal = verify_complete_seal(
        source_review_artifact,
        source_review_root_sha256,
        label="V25 route source census review",
    )
    if source_seal["manifest_paths"] != sorted(
        {
            "COMMAND",
            "HEADS",
            "formal_route_source_contract_supplement.json",
            "report.json",
            "route_signal_source_receipts.json",
            "run.exit",
        }
    ) or review_seal["manifest_paths"] != sorted(
        {"COMMAND", "HEADS", "report.json", "run.exit"}
    ):
        raise ValueError("route source census/review inventory drifted")
    if (source_artifact / "run.exit").read_bytes() != b"0\n" or (
        source_review_artifact / "run.exit"
    ).read_bytes() != b"0\n":
        raise ValueError("route source census/review did not exit zero")
    source_report = _json(source_artifact / "report.json")
    review_report = _json(source_review_artifact / "report.json")
    payload = _json(source_artifact / "route_signal_source_receipts.json")
    rows = payload.get("cases")
    if (
        source_report.get("status")
        != "passed_source_only_route_signal_authority_census"
        or review_report.get("status")
        != "passed_independent_route_signal_source_review"
        or Path(str(review_report.get("reviewed_artifact"))).resolve()
        != source_artifact.resolve()
        or review_report.get("reviewed_root_sha256") != source_root_sha256
        or payload.get("source_failures") != []
        or type(rows) is not list
        or len(rows) != EXPECTED_EXECUTABLE_IDENTITIES + 153
        or any(type(row) is not dict or set(row) != ROUTE_SOURCE_ROW_FIELDS for row in rows)
    ):
        raise ValueError("route source census/review authority drifted")
    by_id = {row["scenario_id"]: row for row in rows}
    if len(by_id) != len(rows) or any(not _is_sha256(key) for key in by_id):
        raise ValueError("route source census identities are duplicated or invalid")
    return by_id


def _validate_route_source_row_binding(
    sidecar: Mapping[str, Any],
    *,
    source_rows: Mapping[str, Mapping[str, Any]],
    source_root_sha256: str,
) -> None:
    scenario_id = sidecar.get("scenario_id")
    row = source_rows.get(scenario_id)
    if row is None or row.get("runner_eligible") is not True:
        raise ValueError("snapshot lacks sealed executable route-source row")
    if (
        sidecar.get("route_signal_source_artifact_root_sha256")
        != source_root_sha256
        or sidecar.get("route_signal_source_row_sha256") != _oracle_sha256(row)
        or sidecar.get("family") != row.get("family")
        or sidecar.get("tier") != row.get("tier")
        or sidecar.get("seed") != row.get("seed")
        or sidecar.get("source_map_sha256") != row.get("source_map_sha256")
        or sidecar.get("route_identity_sha256") != row.get("route_identity_sha256")
        or sidecar.get("signal_source_class") != row.get("source_class")
        or sidecar.get("phase_authority_mode") != row.get("phase_authority_mode")
    ):
        raise ValueError("snapshot route-source row identity binding drifted")
    chain = row.get("source_chain")
    receipt = sidecar.get("controlled_signal_source_receipt")
    causal = sidecar.get("causal_signal_atom_input")
    cache = sidecar.get("controlled_model_input_cache_receipt")
    if type(chain) is not dict or type(receipt) is not dict or type(causal) is not dict:
        raise ValueError("snapshot route-source chain binding is malformed")
    if (
        cache.get("scenario_id") != scenario_id
        or receipt.get("scenario_id") != scenario_id
        or receipt.get("source_chain_sha256") != chain.get("source_chain_sha256")
        or causal.get("source_chain_sha256") != chain.get("source_chain_sha256")
        or receipt.get("route_geometry_sha256") != chain.get("route_geometry_sha256")
        or causal.get("route_geometry_sha256") != chain.get("route_geometry_sha256")
    ):
        raise ValueError("snapshot runtime receipt was swapped across source identities")
    if row.get("source_class") == "mapped_signal":
        regulatory_ids = chain.get("regulatory_element_ids")
        if (
            type(regulatory_ids) is not list
            or len(regulatory_ids) != 1
            or receipt.get("regulatory_element_id") != regulatory_ids[0]
            or receipt.get("physical_light_ids") != chain.get("physical_light_ids")
            or receipt.get("bulb_ids") != chain.get("bulb_ids")
            or receipt.get("controlled_lanelet_ids")
            != chain.get("controlled_lanelet_ids")
            or receipt.get("stop_line_id") != chain.get("stop_line_id")
            or receipt.get("stop_line_geometry_sha256")
            != chain.get("stop_line_geometry_sha256")
            or causal.get("stop_line_geometry_sha256")
            != chain.get("stop_line_geometry_sha256")
            or causal.get("regulatory_element_id") != regulatory_ids[0]
            or causal.get("stop_line_id") != chain.get("stop_line_id")
        ):
            raise ValueError("snapshot mapped source-chain binding drifted")
    elif row.get("source_class") == "no_signal":
        if (
            receipt.get("route_lanelet_ids") != chain.get("route_lanelet_ids")
            or receipt.get("traffic_light_regulatory_element_ids") != []
            or chain.get("traffic_light_regulatory_element_ids") != []
        ):
            raise ValueError("snapshot no-signal source-chain binding drifted")
    else:
        raise ValueError("snapshot route-source class drifted")
    return referenced_shards


def review(
    corpus: Path,
    expected_root: str,
    *,
    route_source_artifact: Path,
    route_source_root_sha256: str,
    route_source_review_artifact: Path,
    route_source_review_root_sha256: str,
) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(corpus, expected_root, label="V25 corrected corpus")
    report = _json(corpus / "report.json")
    progress = _json(corpus / "progress.json")
    results = _jsonl(corpus / "results.jsonl")
    index = _jsonl(corpus / "snapshot_index.jsonl")
    source_rows = _open_route_source_authority(
        source_artifact=route_source_artifact,
        source_root_sha256=route_source_root_sha256,
        source_review_artifact=route_source_review_artifact,
        source_review_root_sha256=route_source_review_root_sha256,
    )
    _validate_terminal_schemas(report, progress, results)
    producer_review_contract = _verify_historical_producer_and_posthoc_review_contract(
        repo=ROOT,
        implementation_source_head=report["implementation_source_head"],
        artifact_pointer_head=report["camp_head"],
        current_review_head=head,
        implementation_manifest=report["critical_implementation_manifest"],
    )
    if set(report.get("seven_root_bindings") or {}) == set(A17_UPSTREAM_ROLES):
        release = verify_a17_full_corpus_release(
            repo=ROOT,
            release_artifact=Path(
                str(report["ultra_full_r_execute_release_artifact"])
            ),
            release_root_sha256=str(
                report["ultra_full_r_execute_release_root_sha256"]
            ),
            requested_output_dir=str(corpus.resolve()),
            current_pointer_head=report["camp_head"],
            dp_repo=Path(str(report["dp_repo"])),
            probe_template=Path(str(report["probe_template"])),
            mode="execute",
            consume=False,
        )
        roots = release["decision"]["root_artifacts"]
        if (
            report["seven_root_bindings"] != roots
            or report["seven_root_bindings_sha256"] != _oracle_sha256(roots)
            or Path(str(roots["source"]["path"])).resolve()
            != route_source_artifact.resolve()
            or roots["source"]["root_sha256"] != route_source_root_sha256
            or Path(str(roots["source_review"]["path"])).resolve()
            != route_source_review_artifact.resolve()
            or roots["source_review"]["root_sha256"]
            != route_source_review_root_sha256
        ):
            raise ValueError("A1.7 full-corpus execute/source authority drifted")
    if (
        (corpus / "run.exit").read_text(encoding="ascii") != "0\n"
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "execute"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("attempted_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("retained_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or len(results) != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("status") != "complete"
        or progress.get("completed") != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("total") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("fresh_b_opened") is not False
        or report.get("training_snapshot_outcome_fields") != []
        or report.get("selector_training_executed") is not False
        or report.get("calibration_executed") is not False
    ):
        raise ValueError("corrected corpus terminal report contract drifted")
    seen_results: set[str] = set()
    expected_snapshots = 0
    referenced_fixed_dp_failures: set[str] = set()
    for ordinal, row in enumerate(results):
        scenario_id = row.get("scenario_id")
        status = row.get("status")
        count = row.get("snapshot_count")
        if (
            row.get("ordinal") != ordinal
            or not isinstance(scenario_id, str)
            or len(scenario_id) != 64
            or scenario_id in seen_results
            or row.get("retained") is not True
            or row.get("fresh_b_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("corpus result denominator drifted")
        if status == "complete":
            if count != CORPUS_STEPS or row.get("capability_failure") is not None:
                raise ValueError("complete corpus identity is not exactly 64 ticks")
            expected_snapshots += CORPUS_STEPS
        elif status == "failed":
            failure = row.get("capability_failure")
            if count != 0:
                raise ValueError("failed corpus identity retained partial snapshots")
            if row.get("failure_type") == "RetainedScenarioCapabilityFailure":
                if (
                    not isinstance(failure, Mapping)
                    or failure.get("scenario_id") != scenario_id
                    or failure.get("family") != row.get("family")
                    or set(failure) != CAPABILITY_FAILURE_FIELDS
                    or any(type(value) is not str for value in failure.values())
                    or failure.get("source_class") != "mapped_signal"
                    or failure.get("phase_authority_mode")
                    not in {
                        "controlled_same_tick_override",
                        "observe_same_tick_request",
                    }
                    or failure.get("reason")
                    != "mapped_current_signal_source_unavailable"
                ):
                    raise ValueError("scenario capability failure drifted")
            elif row.get("failure_type") == FixedDpCandidateGenerationCapabilityFailure.__name__:
                relative = _validate_fixed_dp_failure_receipt(
                    failure, result=row, artifact=corpus
                )
                source_row = source_rows.get(scenario_id)
                if (
                    type(source_row) is not dict
                    or failure.get("source_class") != source_row.get("source_class")
                    or failure.get("phase_authority_mode")
                    != source_row.get("phase_authority_mode")
                ):
                    raise ValueError("fixed-DP capability source authority drifted")
                referenced_fixed_dp_failures.add(relative)
            else:
                raise ValueError("failed corpus identity is not a typed retained failure")
        else:
            raise ValueError("corpus identity has an illegal terminal status")
        seen_results.add(scenario_id)
    if (
        len(index) != expected_snapshots
        or report.get("snapshot_count") != expected_snapshots
        or progress.get("snapshot_count") != expected_snapshots
    ):
        raise ValueError("corpus snapshot denominator is inconsistent")
    actual_fixed_dp_failures = {
        path for path in seal["manifest_paths"]
        if path.startswith("fixed_dp_capability_failures/")
    }
    if actual_fixed_dp_failures != referenced_fixed_dp_failures:
        raise ValueError("fixed-DP capability failure inventory is not exact")
    support_coverage = _independent_full_support_coverage(
        results=results, source_rows=source_rows
    )
    scenario_failure_count = sum(
        row.get("failure_type") == "RetainedScenarioCapabilityFailure"
        for row in results
    )
    fixed_dp_failure_count = sum(
        row.get("failure_type")
        == FixedDpCandidateGenerationCapabilityFailure.__name__
        for row in results
    )
    if (
        support_coverage["passed"] is not True
        or not _json_type_exact_equal(
            report.get("fixed_dp_support_coverage"), support_coverage
        )
        or report.get("retained_scenario_capability_failure_count")
        != scenario_failure_count
        or report.get("retained_fixed_dp_capability_failure_count")
        != fixed_dp_failure_count
        or report.get("retained_capability_failure_count")
        != scenario_failure_count + fixed_dp_failure_count
    ):
        raise ValueError("fixed-DP support coverage report drifted")
    seen_ticks: set[tuple[str, int]] = set()
    referenced_causal_shards: set[str] = set()
    for row in index:
        _validate_snapshot_index_row(row)
        key = (row["scenario_id"], row["tick_index"])
        relative = row.get("relative_path")
        if (
            key in seen_ticks
            or key[0] not in seen_results
            or type(key[1]) is not int
            or not 0 <= key[1] < CORPUS_STEPS
            or not isinstance(relative, str)
            or not relative.startswith("snapshots/")
            or ".." in Path(relative).parts
            or relative != f"snapshots/{row.get('sha256')}{SNAPSHOT_SUFFIX}"
        ):
            raise ValueError("snapshot index authority is invalid")
        path = corpus / relative
        digest = row.get("sha256")
        snapshot = _read_verified_content_addressed_snapshot(path, digest)
        referenced_causal_shards.update(
            _validate_snapshot_field_schema(snapshot, artifact_root=corpus)
        )
        features = snapshot["feature_payload"]
        sidecar = snapshot["sidecar"]
        _validate_route_source_row_binding(
            sidecar,
            source_rows=source_rows,
            source_root_sha256=route_source_root_sha256,
        )
        source = np.asarray(features["atom_source_valid_mask"], dtype=np.bool_)
        applicable = np.asarray(features["atom_applicable_mask"], dtype=np.bool_)
        physical = features.get("physical_feasible_mask")
        atoms = _native_numeric_array(features["atom_matrix"], (8, 14), "atom_matrix")
        candidates = _native_numeric_array(
            features["candidate_tensor"], (8, 80, 4), "candidate_tensor"
        ).astype(np.float32)
        default = _native_numeric_array(
            features["default_output"], (80, 4), "default_output"
        ).astype(np.float32)
        candidate_rows = (
            [
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
                for value in candidates
            ]
            if candidates.ndim == 3 and candidates.shape[0] == 8
            else []
        )
        tensor_sha = (
            hashlib.sha256(np.ascontiguousarray(candidates).tobytes()).hexdigest()
            if candidate_rows
            else None
        )
        default_sha = (
            hashlib.sha256(np.ascontiguousarray(default).tobytes()).hexdigest()
            if default.shape == (80, 4)
            else None
        )
        selected = sidecar.get("selected_index")
        if (
            snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
            or sidecar.get("scenario_id") != key[0]
            or sidecar.get("tick_index") != key[1]
            or source.dtype != np.bool_
            or applicable.dtype != np.bool_
            or source.shape != (8, 14)
            or applicable.shape != (8, 14)
            or np.any(applicable & ~source)
            or atoms.shape != (8, 14)
            or not np.isfinite(atoms).all()
            or np.any(atoms < 0.0)
            or candidates.shape != (8, 80, 4)
            or default.shape != (80, 4)
            or features.get("candidate_row_sha256") != candidate_rows
            or sidecar.get("candidate_tensor_sha256_before") != tensor_sha
            or sidecar.get("candidate_tensor_sha256_after") != tensor_sha
            or sidecar.get("default_output_sha256") != default_sha
            or sidecar.get("candidate0_sha256") != candidate_rows[0]
            or not np.array_equal(default, candidates[0])
            or type(selected) is not int
            or not 0 <= selected < 8
            or sidecar.get("selected_trajectory_sha256")
            != candidate_rows[selected]
            or type(physical) is not list
            or len(physical) != 8
            or any(type(value) is not bool for value in physical)
            or sidecar.get("fresh_b_opened") is not False
            or sidecar.get("outcome_fields_consumed") != []
        ):
            raise ValueError("snapshot schema/source/hash contract drifted")
        seen_ticks.add(key)
    for row in results:
        if row["status"] == "complete":
            keys = {key[1] for key in seen_ticks if key[0] == row["scenario_id"]}
            if keys != set(range(CORPUS_STEPS)):
                raise ValueError("complete identity has missing or duplicate tick index")
    if expected_shard_manifest_paths(seal["manifest_paths"]) != referenced_causal_shards:
        raise ValueError("corpus causal-evidence shard inventory is not exact")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_full_corpus_review",
        "review_head": head,
        "producer_review_contract": producer_review_contract,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(corpus),
        "reviewed_root_sha256": seal["root_sha256"],
        "route_source_artifact": str(route_source_artifact),
        "route_source_root_sha256": route_source_root_sha256,
        "route_source_review_artifact": str(route_source_review_artifact),
        "route_source_review_root_sha256": route_source_review_root_sha256,
        "identity_denominator": len(results),
        "complete_identity_count": sum(row["status"] == "complete" for row in results),
        "typed_retained_failure_count": sum(row["status"] == "failed" for row in results),
        "snapshot_count": expected_snapshots,
        "partial_snapshot_count": 0,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-artifact", type=Path, required=True)
    parser.add_argument("--corpus-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--route-source-artifact", type=Path, required=True)
    parser.add_argument("--route-source-root-sha256", required=True)
    parser.add_argument("--route-source-review-artifact", type=Path, required=True)
    parser.add_argument("--route-source-review-root-sha256", required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(
            args.corpus_artifact,
            args.corpus_root_sha256,
            route_source_artifact=args.route_source_artifact,
            route_source_root_sha256=args.route_source_root_sha256,
            route_source_review_artifact=args.route_source_review_artifact,
            route_source_review_root_sha256=args.route_source_review_root_sha256,
        )
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 corrected corpus review")
        print(json.dumps({"status": report["status"], "root_sha256": root}))
    except BaseException as exc:
        _write(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed corrected corpus review")
        raise


if __name__ == "__main__":
    main()
