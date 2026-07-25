"""Separate-role literal oracle for the V25 calibration hard-stop closeout."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA = "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_closeout_v1"
REVIEW_SCHEMA = (
    "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_review_v1"
)
STATUS = "calibration_hard_stop_scientific_contract_review_required"
CLASSIFICATION = (
    "first_calibration_run_k8_validity_compound_gate_triggered;"
    " exact_subcondition_unresolved_from_preserved_evidence"
)
HIGH_SHA = "ed0d298cbde0e66d7ed2b0bdd90e6be5f2ebbc49f4d818a6c97ff47440f88f59"
ROOTS = {
    "calibration_authority_root_sha256": (
        "bd6fee62418d062266e8f922d2f2dd3672ced115f9c1065e922db4b207054820"
    ),
    "input_only_preflight_root_sha256": (
        "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
    ),
    "input_only_preflight_review_root_sha256": (
        "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
    ),
}
POSSIBLE = [
    "candidate_tensor_contains_nonfinite_value",
    "neighbor_tensor_contains_nonfinite_value",
    "candidate_row_sha256_not_unique_across_k8",
]
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _canonical(value: Any) -> bytes:
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


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise ValueError(f"literal reviewer {label} SHA drifted")
    return value


def literal_review_calibration_hard_stop(
    value: Mapping[str, Any],
    *,
    observed_source_predicate_sha256: str,
    observed_file_sha256: Mapping[str, str],
    observed_absence: Mapping[str, bool],
    process_running: bool,
    observed_reporting_head: str,
) -> dict[str, Any]:
    top = {
        "schema_version",
        "status",
        "classification",
        "high_authority_decision_sha256",
        "stage_identity",
        "authority_bindings",
        "first_run",
        "compound_gate",
        "control_evidence",
        "artifact_state",
        "forbidden_run_counts",
        "pre_artifact_diagnostics",
        "scientific_interpretation",
        "root_sha256",
    }
    if type(value) is not dict or set(value) != top:
        raise ValueError("literal reviewer closeout schema drifted")
    payload = dict(value)
    supplied = payload.pop("root_sha256")
    if (
        value["schema_version"] != SCHEMA
        or value["status"] != STATUS
        or value["classification"] != CLASSIFICATION
        or value["high_authority_decision_sha256"] != HIGH_SHA
        or supplied != _digest(payload)
    ):
        raise ValueError("literal reviewer closeout identity drifted")
    authority = value["authority_bindings"]
    if type(authority) is not dict or set(authority) != {
        "authorized_pointer_head",
        "reporting_head",
        "implementation_head",
        "fixed_dp_head",
        *ROOTS,
    }:
        raise ValueError("literal reviewer authority schema drifted")
    if (
        authority["authorized_pointer_head"]
        != "76f484f46ea569430e436b566a26fd863e1ebe31"
        or authority["reporting_head"] != observed_reporting_head
        or authority["implementation_head"]
        != "67308ac05e64808edf6f37dd2ad930ccf31899e1"
        or authority["fixed_dp_head"]
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or any(authority[key] != expected for key, expected in ROOTS.items())
    ):
        raise ValueError("literal reviewer authority value drifted")
    if value["first_run"] != {
        "state_spec_id": "development_calibration:000",
        "mode": "sequential_batch1_x8",
        "repeat_index": 0,
        "model_call_count": 8,
        "selector_call_count": 0,
    }:
        raise ValueError("literal reviewer first-run binding drifted")
    gate = value["compound_gate"]
    if type(gate) is not dict or set(gate) != {
        "possible_subconditions",
        "resolved_subcondition",
        "exact_subcondition_recoverable_from_preserved_evidence",
        "source_predicate",
    }:
        raise ValueError("literal reviewer compound gate schema drifted")
    source = gate["source_predicate"]
    if type(source) is not dict or set(source) != {
        "producer_path",
        "producer_sha256",
        "predicate_line_start",
        "predicate_line_end",
        "predicate_sha256",
        "exception_literal",
    }:
        raise ValueError("literal reviewer source predicate schema drifted")
    if (
        gate["possible_subconditions"] != POSSIBLE
        or gate["resolved_subcondition"] != "unknown"
        or gate["exact_subcondition_recoverable_from_preserved_evidence"]
        is not False
        or source["predicate_line_start"] != 509
        or source["predicate_line_end"] != 514
        or source["predicate_sha256"] != observed_source_predicate_sha256
        or source["exception_literal"]
        != "calibration K8 invalid: development_calibration:000/sequential_batch1_x8/0"
    ):
        raise ValueError("literal reviewer compound gate value drifted")
    control = value["control_evidence"]
    if type(control) is not dict or set(control) != {
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
        raise ValueError("literal reviewer control evidence schema drifted")
    expected_sha_keys = {
        "run_script_sha256": "run_script",
        "stdout_sha256": "stdout",
        "stderr_sha256": "stderr",
        "exit_sha256": "exit",
        "pid_sha256": "pid",
    }
    for field, observed_key in expected_sha_keys.items():
        if control[field] != observed_file_sha256[observed_key]:
            raise ValueError("literal reviewer control byte binding drifted")
        _sha(control[field], field)
    if source["producer_sha256"] != observed_file_sha256["producer"]:
        raise ValueError("literal reviewer producer byte binding drifted")
    if (
        control["control_exit"] != 1
        or control["pid"] != 204002
        or control["process_running"] is not False
        or process_running
    ):
        raise ValueError("literal reviewer terminal process state drifted")
    artifact = value["artifact_state"]
    if type(artifact) is not dict or set(artifact) != {
        "raw_artifact_absent",
        "raw_review_artifact_absent",
        "threshold_freeze_artifact_absent",
        "threshold_freeze_review_artifact_absent",
        "completed_raw_run_count",
        "planned_raw_run_count",
        "completed_pair_receipt_count",
        "planned_pair_receipt_count",
        "threshold_not_formed",
    }:
        raise ValueError("literal reviewer artifact-state schema drifted")
    absence_keys = (
        "raw_artifact_absent",
        "raw_review_artifact_absent",
        "threshold_freeze_artifact_absent",
        "threshold_freeze_review_artifact_absent",
    )
    if any(
        artifact[key] is not True or observed_absence.get(key) is not True
        for key in absence_keys
    ):
        raise ValueError("literal reviewer artifact absence drifted")
    if (
        artifact["completed_raw_run_count"] != 0
        or artifact["planned_raw_run_count"] != 640
        or artifact["completed_pair_receipt_count"] != 0
        or artifact["planned_pair_receipt_count"] != 1600
        or artifact["threshold_not_formed"] is not True
    ):
        raise ValueError("literal reviewer denominator drifted")
    if type(value["forbidden_run_counts"]) is not dict or set(
        value["forbidden_run_counts"]
    ) != {
        "replacement_calibration_run_count",
        "raw_review_run_count",
        "threshold_freeze_run_count",
        "threshold_review_run_count",
        "independent_validation_run_count",
        "closed_loop_run_count",
        "fresh_or_holdout_run_count",
        "training_or_retraining_run_count",
        "old_artifact_or_cas_write_count",
    }:
        raise ValueError("literal reviewer forbidden-run schema drifted")
    if any(value["forbidden_run_counts"].values()):
        raise ValueError("literal reviewer forbidden run count drifted")
    if (
        len(value["pre_artifact_diagnostics"]) != 3
        or any(
            row["control_exit"] != 1
            or row["raw_artifact_created"] is not False
            or row["model_call_count_before_failure"] != 0
            for row in value["pre_artifact_diagnostics"]
        )
    ):
        raise ValueError("literal reviewer diagnostic boundary drifted")
    interpretation = value["scientific_interpretation"]
    if interpretation != {
        "model_failure_claimed": False,
        "batch8_architecture_failure_claimed": False,
        "ood_drift_claimed": False,
        "retraining_required_claimed": False,
        "benefit_or_safety_claim_authorized": False,
        "raw_fresh_or_b4_outcome_inspected": False,
        "next_authority": "High_or_control_decision_only",
    }:
        raise ValueError("literal reviewer scientific boundary drifted")
    return {
        "schema_version": REVIEW_SCHEMA,
        "status": "passed_independent_calibration_hard_stop_review",
        "source_root_sha256": supplied,
        "compound_predicate_rebuilt": True,
        "resolved_subcondition": "unknown",
        "raw_artifact_absent": True,
        "threshold_not_formed": True,
        "validation_execution_count": 0,
        "model_pool_selector_call_count": 0,
        "producer_module_imported": False,
        "raw_outcome_inspected": False,
    }
