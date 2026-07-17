#!/usr/bin/env python3
"""Independently validate a sealed V25 corrected 1500-identity corpus."""

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
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
    validate_causal_signal_atom_input,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    verify_dual_head_contract,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_review_v2"
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
        "controlled_signal_source_receipt",
        "causal_signal_atom_input",
        "offline_label_provenance",
        "outcome_fields_consumed",
        "fresh_b_opened",
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
        "schema_version", "scenario_id", "tick_index", "decision_time_s",
        "source_mode", "current_phase", "regulatory_element_id",
        "physical_light_ids", "bulb_ids", "controlled_lanelet_ids",
        "stop_line_id", "stop_line_geometry_sha256", "route_geometry_sha256",
        "route_arc_m", "route_tangent_world", "source_chain_sha256",
        "semantic_clone_sha256", "applied_route_lanelet_ids",
        "applied_map_lanelet_ids", "phase_remaining_available", "source_valid",
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
        "red_scientific_coverage", "retained_identity_count", "snapshot_count",
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
            if (
                type(row.get("failure_type")) is not str
                or type(row.get("failure_reason")) is not str
                or type(failure) is not dict
                or set(failure) != {"scenario_id", "family", "reason"}
                or any(type(value) is not str for value in failure.values())
            ):
                raise ValueError("failed result capability receipt schema drifted")
        else:
            raise ValueError("result status is invalid")


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
    mode = receipt.get("source_mode")
    expected_fields = (
        RUNTIME_SIGNAL_RECEIPT_FIELDS
        if mode == "same_tick_current_phase_no_v2i"
        else RUNTIME_NO_SIGNAL_RECEIPT_FIELDS
        if mode == "same_tick_no_signal_rule_no_v2i"
        else frozenset()
    )
    if set(receipt) != expected_fields:
        raise ValueError("runtime signal receipt exact schema drifted")
    if (
        receipt.get("schema_version") != RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION
        or type(receipt.get("tick_index")) is not int
        or type(receipt.get("decision_time_s")) is not float
        or not np.isfinite(receipt["decision_time_s"])
        or type(receipt.get("phase_remaining_available")) is not bool
        or receipt.get("phase_remaining_available") is not False
        or type(receipt.get("source_valid")) is not bool
        or receipt.get("source_valid") is not True
    ):
        raise ValueError("runtime signal receipt type/value contract drifted")
    if mode == "same_tick_current_phase_no_v2i":
        for field in (
            "regulatory_element_id",
            "stop_line_id",
        ):
            _native_int(receipt.get(field), f"runtime receipt {field}")
        for field in (
            "physical_light_ids",
            "bulb_ids",
            "controlled_lanelet_ids",
            "applied_route_lanelet_ids",
            "applied_map_lanelet_ids",
        ):
            values = receipt.get(field)
            if type(values) is not list or any(type(value) is not int for value in values):
                raise ValueError(f"runtime receipt {field} must be native int list")
        _native_finite_number(receipt.get("route_arc_m"), "runtime receipt route_arc_m")
        _native_numeric_array(
            receipt.get("route_tangent_world"), (2,), "runtime route tangent"
        )
        if receipt.get("current_phase") not in {"green", "yellow", "red"}:
            raise ValueError("runtime signal phase is invalid")
    else:
        for field in (
            "route_lanelet_ids",
            "traffic_light_regulatory_element_ids",
        ):
            values = receipt.get(field)
            if type(values) is not list or any(type(value) is not int for value in values):
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


def _validate_snapshot_field_schema(snapshot: Any) -> None:
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
    ):
        if type(sidecar.get(field)) is not str:
            raise ValueError(f"sidecar {field} must be a native string")
    for field in (
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "candidate0_sha256",
        "causal_input_sha256",
        "selected_trajectory_sha256",
        "normalized_atom_matrix_sha256",
        "generation_behavior_scale_sha256",
    ):
        if not _is_sha256(sidecar.get(field)):
            raise ValueError(f"sidecar {field} must be a SHA256 string")
    semantic = sidecar.get("canonical_semantic_clone_sha256")
    if semantic is not None and not _is_sha256(semantic):
        raise ValueError("canonical semantic clone must be null or SHA256")
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
    data = path.read_bytes()
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ValueError("snapshot bytes do not end in exactly one LF")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("snapshot bytes are not canonical UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("snapshot payload is not an object")
    canonical = _oracle_canonical_snapshot_bytes(payload)
    digest = hashlib.sha256(canonical).hexdigest()
    if (
        data != canonical
        or digest != expected_sha256
        or path.name != f"{expected_sha256}.json"
    ):
        raise ValueError("snapshot canonical bytes/content address drifted")
    return payload


def review(corpus: Path, expected_root: str) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(corpus, expected_root, label="V25 corrected corpus")
    report = _json(corpus / "report.json")
    progress = _json(corpus / "progress.json")
    results = _jsonl(corpus / "results.jsonl")
    index = _jsonl(corpus / "snapshot_index.jsonl")
    _validate_terminal_schemas(report, progress, results)
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=report["implementation_source_head"],
        current_pointer_head=report["camp_head"],
        implementation_manifest=report["critical_implementation_manifest"],
    )
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=report["implementation_source_head"],
        current_pointer_head=head,
        implementation_manifest=report["critical_implementation_manifest"],
    )
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
            if (
                count != 0
                or row.get("failure_type") != "RetainedScenarioCapabilityFailure"
                or not isinstance(failure, Mapping)
                or failure.get("scenario_id") != scenario_id
                or failure.get("family") != row.get("family")
            ):
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
    seen_ticks: set[tuple[str, int]] = set()
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
        ):
            raise ValueError("snapshot index authority is invalid")
        path = corpus / relative
        digest = row.get("sha256")
        snapshot = _read_verified_content_addressed_snapshot(path, digest)
        _validate_snapshot_field_schema(snapshot)
        features = snapshot["feature_payload"]
        sidecar = snapshot["sidecar"]
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
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_full_corpus_review",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(corpus),
        "reviewed_root_sha256": seal["root_sha256"],
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
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.corpus_artifact, args.corpus_root_sha256)
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
