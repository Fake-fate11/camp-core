from __future__ import annotations

from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    strict_equal,
    validate_fatal_artifact,
    validate_tombstone,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_terminal_failure_closeout_v1"
REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_terminal_failure_closeout_review_v1"
)
STATUS = "consumed_one_shot_engineering_failure_no_evaluation_no_claim"
REVIEW_STATUS = "passed_independent_holdout_terminal_failure_closeout_review"
_BINDING_FIELDS = frozenset({"path", "root_sha256"})
_FILE_BINDING_FIELDS = frozenset({"path", "sha256"})
_FAILURE_SIGNATURE_FIELDS = frozenset(
    {
        "exception_type",
        "missing_required_field",
        "producer_contract",
        "consumer_contract",
        "failure_stage",
        "scientific_result",
    }
)
_CLOSEOUT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "benchmark",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "run_nonce",
        "controller_decision",
        "opening_release",
        "failure_artifact",
        "failure_review",
        "cas_tombstone_path",
        "cas_tombstone_sha256",
        "cas_tombstone",
        "worker_stderr",
        "failure_signature",
        "planned_arm_run_count",
        "attempted_arm_run_count",
        "complete_arm_run_count",
        "unattempted_arm_run_count",
        "complete_paired_row_count",
        "full_denominator_formed",
        "outcome_fields_consumed",
        "raw_outcome_values_inspected",
        "resume_allowed",
        "new_nonce_allowed",
        "alternate_directory_allowed",
        "suffix_allowed",
        "remaining_units_allowed",
        "fresh_evaluation_authorized",
        "training_eligible",
        "calibration_eligible",
        "evaluation_eligible",
        "claim_authorized",
        "next_authority",
        "closeout_payload_sha256",
    }
)


def freeze_terminal_failure_closeout(
    *,
    benchmark: str,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    controller_decision: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    failure_artifact: Mapping[str, Any],
    failure_review: Mapping[str, Any],
    cas_tombstone_path: str,
    cas_tombstone_sha256: str,
    cas_tombstone: Mapping[str, Any],
    worker_stderr: Mapping[str, Any],
    fatal_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    if benchmark != "fresh_b3":
        raise ValueError("terminal closeout is frozen to Fresh B3")
    identity = _sha(holdout_identity_sha256, "holdout identity")
    protocol = _sha(experiment_protocol_sha256, "experiment protocol")
    nonce = _sha(run_nonce, "run nonce")
    controller = _binding(controller_decision, "controller decision")
    release = _binding(opening_release, "opening release")
    failure = _binding(failure_artifact, "failure artifact")
    review = _binding(failure_review, "failure review")
    cas_sha = _sha(cas_tombstone_sha256, "CAS tombstone file")
    stderr = _file_binding(worker_stderr, "worker stderr")
    tombstone = validate_tombstone(cas_tombstone)
    fatal = validate_fatal_artifact(fatal_artifact)
    if (
        tombstone["holdout_identity_sha256"] != identity
        or tombstone["experiment_protocol_sha256"] != protocol
        or tombstone["state"] != "terminal_failure"
        or tombstone["terminal_artifact_root_sha256"]
        != failure["root_sha256"]
        or tombstone["terminal_reason"] != "artifact_fatal"
        or tombstone["outcome_evaluation_completed"] is not False
        or tombstone["second_opening_allowed"] is not False
        or fatal["holdout_identity_sha256"] != identity
        or fatal["experiment_protocol_sha256"] != protocol
        or fatal["controller_decision_root_sha256"]
        != controller["root_sha256"]
        or fatal["opening_release_root_sha256"] != release["root_sha256"]
        or fatal["block_class"] != "holdout_execution_artifact_fatal"
        or fatal["reason"] != "'candidate_tensor_sha256_before'"
        or fatal["attempted_unit_ordinal"] != 0
        or fatal["attempted_arm"] != "candidate0"
        or fatal["planned_arm_run_count"] != 1500
        or fatal["attempted_arm_run_count"] != 1
        or fatal["complete_arm_run_count"] != 0
        or fatal["unattempted_arm_run_count"] != 1499
        or fatal["outcome_fields_consumed"] != []
        or fatal["fresh_opened_once"] is not True
        or fatal["resume_allowed"] is not False
        or fatal["new_nonce_allowed"] is not False
        or fatal["suffix_allowed"] is not False
        or fatal["full_denominator_formed"] is not False
    ):
        raise ValueError("Fresh B3 terminal evidence drifted")
    if (
        type(cas_tombstone_path) is not str
        or not cas_tombstone_path.endswith(f"/{identity}.json")
    ):
        raise ValueError("Fresh B3 CAS tombstone path drifted")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "benchmark": benchmark,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "run_nonce": nonce,
        "controller_decision": controller,
        "opening_release": release,
        "failure_artifact": failure,
        "failure_review": review,
        "cas_tombstone_path": cas_tombstone_path,
        "cas_tombstone_sha256": cas_sha,
        "cas_tombstone": tombstone,
        "worker_stderr": stderr,
        "failure_signature": {
            "exception_type": "KeyError",
            "missing_required_field": "candidate_tensor_sha256_before",
            "producer_contract": "actual_native_candidate0_action_first_tick_v1",
            "consumer_contract": (
                "candidate0_pool_projection_same_forward_tick_v2"
            ),
            "failure_stage": "unit0_candidate0_receipt_projection",
            "scientific_result": False,
        },
        "planned_arm_run_count": 1500,
        "attempted_arm_run_count": 1,
        "complete_arm_run_count": 0,
        "unattempted_arm_run_count": 1499,
        "complete_paired_row_count": 0,
        "full_denominator_formed": False,
        "outcome_fields_consumed": [],
        "raw_outcome_values_inspected": False,
        "resume_allowed": False,
        "new_nonce_allowed": False,
        "alternate_directory_allowed": False,
        "suffix_allowed": False,
        "remaining_units_allowed": False,
        "fresh_evaluation_authorized": False,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "claim_authorized": False,
        "next_authority": "fresh_b4_engineering_recovery_preopen_only",
    }
    payload["closeout_payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_terminal_failure_closeout(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _CLOSEOUT_FIELDS:
        raise ValueError("terminal failure closeout field set drifted")
    signature = value.get("failure_signature")
    if type(signature) is not dict or set(signature) != _FAILURE_SIGNATURE_FIELDS:
        raise ValueError("terminal failure signature field set drifted")
    expected = freeze_terminal_failure_closeout(
        benchmark=value["benchmark"],
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        run_nonce=value["run_nonce"],
        controller_decision=value["controller_decision"],
        opening_release=value["opening_release"],
        failure_artifact=value["failure_artifact"],
        failure_review=value["failure_review"],
        cas_tombstone_path=value["cas_tombstone_path"],
        cas_tombstone_sha256=value["cas_tombstone_sha256"],
        cas_tombstone=value["cas_tombstone"],
        worker_stderr=value["worker_stderr"],
        fatal_artifact=_fatal_from_closeout(value),
    )
    if not strict_equal(value, expected):
        raise ValueError("terminal failure closeout exact value drifted")
    return expected


def independent_terminal_failure_review(
    closeout: Mapping[str, Any],
    *,
    fatal_artifact: Mapping[str, Any],
    reviewed_root_sha256: str,
) -> dict[str, Any]:
    value = dict(closeout)
    if type(value) is not dict or set(value) != _CLOSEOUT_FIELDS:
        raise ValueError("terminal failure closeout field set drifted")
    expected = freeze_terminal_failure_closeout(
        benchmark=value["benchmark"],
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        run_nonce=value["run_nonce"],
        controller_decision=value["controller_decision"],
        opening_release=value["opening_release"],
        failure_artifact=value["failure_artifact"],
        failure_review=value["failure_review"],
        cas_tombstone_path=value["cas_tombstone_path"],
        cas_tombstone_sha256=value["cas_tombstone_sha256"],
        cas_tombstone=value["cas_tombstone"],
        worker_stderr=value["worker_stderr"],
        fatal_artifact=fatal_artifact,
    )
    if not strict_equal(value, expected):
        raise ValueError("terminal failure closeout independent rebuild drifted")
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": REVIEW_STATUS,
        "reviewed_root_sha256": _sha(
            reviewed_root_sha256, "reviewed root"
        ),
        "holdout_identity_sha256": value["holdout_identity_sha256"],
        "experiment_protocol_sha256": value["experiment_protocol_sha256"],
        "planned_arm_run_count": 1500,
        "attempted_arm_run_count": 1,
        "complete_arm_run_count": 0,
        "unattempted_arm_run_count": 1499,
        "complete_paired_row_count": 0,
        "full_denominator_formed": False,
        "outcome_fields_consumed": [],
        "raw_outcome_values_inspected": False,
        "fresh_evaluation_authorized": False,
        "claim_authorized": False,
        "b4_engineering_recovery_preopen_only": True,
    }


def _fatal_from_closeout(value: Mapping[str, Any]) -> dict[str, Any]:
    tombstone = validate_tombstone(value["cas_tombstone"])
    return {
        "schema_version": "camp_dp_v25_holdout_artifact_fatal_v1",
        "status": "artifact_fatal",
        "block_class": "holdout_execution_artifact_fatal",
        "reason": "'candidate_tensor_sha256_before'",
        "controller_decision_root_sha256": value["controller_decision"][
            "root_sha256"
        ],
        "opening_release_root_sha256": value["opening_release"]["root_sha256"],
        "marker_path": value["cas_tombstone_path"],
        "marker_sha256": tombstone["marker_sha256"],
        "holdout_identity_sha256": value["holdout_identity_sha256"],
        "experiment_protocol_sha256": value["experiment_protocol_sha256"],
        "attempted_unit_ordinal": 0,
        "attempted_arm": "candidate0",
        "planned_arm_run_count": 1500,
        "attempted_arm_run_count": 1,
        "complete_arm_run_count": 0,
        "unattempted_arm_run_count": 1499,
        "outcome_fields_consumed": [],
        "fresh_opened_once": True,
        "resume_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "full_denominator_formed": False,
        "next_authority": "ultra_read_only_failure_closeout",
    }


def _binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _BINDING_FIELDS:
        raise ValueError(f"{label} binding field set drifted")
    if type(value["path"]) is not str or not value["path"].startswith("/"):
        raise ValueError(f"{label} path drifted")
    return {
        "path": value["path"],
        "root_sha256": _sha(value["root_sha256"], label),
    }


def _file_binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _FILE_BINDING_FIELDS:
        raise ValueError(f"{label} binding field set drifted")
    if type(value["path"]) is not str or not value["path"].startswith("/"):
        raise ValueError(f"{label} path drifted")
    return {
        "path": value["path"],
        "sha256": _sha(value["sha256"], label),
    }


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} SHA drifted")
    return value
