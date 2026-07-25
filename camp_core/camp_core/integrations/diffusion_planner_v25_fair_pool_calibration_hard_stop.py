"""Outcome-blind closeout schema for the V25 fair-pool calibration hard stop."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_closeout_v1"
)
STATUS = "calibration_hard_stop_scientific_contract_review_required"
CLASSIFICATION = (
    "first_calibration_run_k8_validity_compound_gate_triggered;"
    " exact_subcondition_unresolved_from_preserved_evidence"
)
HIGH_AUTHORITY_DECISION_SHA256 = (
    "ed0d298cbde0e66d7ed2b0bdd90e6be5f2ebbc49f4d818a6c97ff47440f88f59"
)
STAGE_IDENTITY = "67308ac0_ed0d298c"
POINTER_HEAD = "76f484f46ea569430e436b566a26fd863e1ebe31"
IMPLEMENTATION_HEAD = "67308ac05e64808edf6f37dd2ad930ccf31899e1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
AUTHORITY_ROOT_SHA256 = (
    "bd6fee62418d062266e8f922d2f2dd3672ced115f9c1065e922db4b207054820"
)
PREFLIGHT_ROOT_SHA256 = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
PREFLIGHT_REVIEW_ROOT_SHA256 = (
    "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
)
FIRST_RUN = {
    "state_spec_id": "development_calibration:000",
    "mode": "sequential_batch1_x8",
    "repeat_index": 0,
    "model_call_count": 8,
    "selector_call_count": 0,
}
POSSIBLE_SUBCONDITIONS = (
    "candidate_tensor_contains_nonfinite_value",
    "neighbor_tensor_contains_nonfinite_value",
    "candidate_row_sha256_not_unique_across_k8",
)
RAW_RUN_PLANNED_COUNT = 640
PAIR_RECEIPT_PLANNED_COUNT = 1600
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_HEAD_RE = re.compile(r"[0-9a-f]{40}\Z")
_FORBIDDEN_FIELD_PARTS = (
    "outcome_value",
    "fresh_result",
    "benefit_claim",
    "threshold_override",
    "candidate_bytes",
    "neighbor_bytes",
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return value


def _head(value: Any, label: str) -> str:
    if type(value) is not str or not _GIT_HEAD_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 40-hex Git commit")
    return value


def _exact_bool_map(value: Any, *, expected: Mapping[str, bool], label: str) -> dict[str, bool]:
    if type(value) is not dict or value != dict(expected):
        raise ValueError(f"{label} drifted")
    return dict(value)


def _diagnostics(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != 3:
        raise ValueError("pre-artifact diagnostics denominator drifted")
    expected_classes = (
        "lanelet2_projection_compatibility_fixture",
        "causal_map_cache_fixture",
        "sealed_model_input_vs_unpinned_scene_history_fixture",
    )
    rows = []
    for index, row in enumerate(value):
        if type(row) is not dict or set(row) != {
            "classification",
            "control_exit",
            "raw_artifact_created",
            "model_call_count_before_failure",
            "stderr_sha256",
        }:
            raise ValueError("pre-artifact diagnostic schema drifted")
        if (
            row["classification"] != expected_classes[index]
            or row["control_exit"] != 1
            or row["raw_artifact_created"] is not False
            or row["model_call_count_before_failure"] != 0
        ):
            raise ValueError("pre-artifact diagnostic value drifted")
        _sha(row["stderr_sha256"], "diagnostic stderr")
        rows.append(dict(row))
    return rows


def freeze_calibration_hard_stop_closeout(
    *,
    reporting_head: str,
    source_predicate: Mapping[str, Any],
    control_evidence: Mapping[str, Any],
    artifact_absence: Mapping[str, bool],
    pre_artifact_diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    _head(reporting_head, "reporting head")
    if type(source_predicate) is not dict or set(source_predicate) != {
        "producer_path",
        "producer_sha256",
        "predicate_line_start",
        "predicate_line_end",
        "predicate_sha256",
        "exception_literal",
    }:
        raise ValueError("source predicate schema drifted")
    if (
        source_predicate["producer_path"]
        != "/root/autodl-tmp/.camp_dp_v25_calibration_raw_67308ac0_ed0d298c.py"
        or source_predicate["predicate_line_start"] != 509
        or source_predicate["predicate_line_end"] != 514
        or source_predicate["exception_literal"]
        != "calibration K8 invalid: development_calibration:000/sequential_batch1_x8/0"
    ):
        raise ValueError("source predicate binding drifted")
    _sha(source_predicate["producer_sha256"], "raw producer")
    _sha(source_predicate["predicate_sha256"], "source predicate")

    if type(control_evidence) is not dict or set(control_evidence) != {
        "run_script_path",
        "run_script_sha256",
        "stdout_path",
        "stdout_sha256",
        "stderr_path",
        "stderr_sha256",
        "exit_path",
        "exit_sha256",
        "control_exit",
        "pid_path",
        "pid_sha256",
        "pid",
        "process_running",
    }:
        raise ValueError("control evidence schema drifted")
    for key in (
        "run_script_sha256",
        "stdout_sha256",
        "stderr_sha256",
        "exit_sha256",
        "pid_sha256",
    ):
        _sha(control_evidence[key], key)
    if (
        control_evidence["control_exit"] != 1
        or control_evidence["pid"] != 204002
        or control_evidence["process_running"] is not False
    ):
        raise ValueError("control terminal state drifted")

    absence = _exact_bool_map(
        artifact_absence,
        expected={
            "raw_artifact_absent": True,
            "raw_review_artifact_absent": True,
            "threshold_freeze_artifact_absent": True,
            "threshold_freeze_review_artifact_absent": True,
        },
        label="artifact absence",
    )
    diagnostics = _diagnostics(pre_artifact_diagnostics)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "classification": CLASSIFICATION,
        "high_authority_decision_sha256": HIGH_AUTHORITY_DECISION_SHA256,
        "stage_identity": STAGE_IDENTITY,
        "authority_bindings": {
            "authorized_pointer_head": POINTER_HEAD,
            "reporting_head": reporting_head,
            "implementation_head": IMPLEMENTATION_HEAD,
            "fixed_dp_head": FIXED_DP_HEAD,
            "calibration_authority_root_sha256": AUTHORITY_ROOT_SHA256,
            "input_only_preflight_root_sha256": PREFLIGHT_ROOT_SHA256,
            "input_only_preflight_review_root_sha256": (
                PREFLIGHT_REVIEW_ROOT_SHA256
            ),
        },
        "first_run": dict(FIRST_RUN),
        "compound_gate": {
            "possible_subconditions": list(POSSIBLE_SUBCONDITIONS),
            "resolved_subcondition": "unknown",
            "exact_subcondition_recoverable_from_preserved_evidence": False,
            "source_predicate": dict(source_predicate),
        },
        "control_evidence": dict(control_evidence),
        "artifact_state": {
            **absence,
            "completed_raw_run_count": 0,
            "planned_raw_run_count": RAW_RUN_PLANNED_COUNT,
            "completed_pair_receipt_count": 0,
            "planned_pair_receipt_count": PAIR_RECEIPT_PLANNED_COUNT,
            "threshold_not_formed": True,
        },
        "forbidden_run_counts": {
            "replacement_calibration_run_count": 0,
            "raw_review_run_count": 0,
            "threshold_freeze_run_count": 0,
            "threshold_review_run_count": 0,
            "independent_validation_run_count": 0,
            "closed_loop_run_count": 0,
            "fresh_or_holdout_run_count": 0,
            "training_or_retraining_run_count": 0,
            "old_artifact_or_cas_write_count": 0,
        },
        "pre_artifact_diagnostics": diagnostics,
        "scientific_interpretation": {
            "model_failure_claimed": False,
            "batch8_architecture_failure_claimed": False,
            "ood_drift_claimed": False,
            "retraining_required_claimed": False,
            "benefit_or_safety_claim_authorized": False,
            "raw_fresh_or_b4_outcome_inspected": False,
            "next_authority": "High_or_control_decision_only",
        },
    }
    payload["root_sha256"] = sha256_json(payload)
    return payload


def validate_calibration_hard_stop_closeout(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("calibration hard-stop closeout must be an object")
    forbidden = [
        key
        for key in value
        if any(part in key.lower() for part in _FORBIDDEN_FIELD_PARTS)
    ]
    if forbidden:
        raise ValueError("forbidden closeout field present")
    expected = freeze_calibration_hard_stop_closeout(
        reporting_head=value.get("authority_bindings", {}).get(
            "reporting_head", ""
        ),
        source_predicate=value.get("compound_gate", {}).get(
            "source_predicate", {}
        ),
        control_evidence=value.get("control_evidence", {}),
        artifact_absence={
            key: value.get("artifact_state", {}).get(key)
            for key in (
                "raw_artifact_absent",
                "raw_review_artifact_absent",
                "threshold_freeze_artifact_absent",
                "threshold_freeze_review_artifact_absent",
            )
        },
        pre_artifact_diagnostics=value.get("pre_artifact_diagnostics", []),
    )
    if dict(value) != expected:
        raise ValueError("calibration hard-stop closeout exact value drifted")
    return deepcopy(expected)
