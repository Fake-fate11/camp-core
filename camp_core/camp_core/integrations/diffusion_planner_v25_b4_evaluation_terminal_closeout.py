from __future__ import annotations

from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    strict_equal,
)


SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_post_exposure_evaluation_control_fatal_closeout_v1"
)
STATUS = "post_exposure_evaluation_control_fatal_honest_no_claim"
BENCHMARK = "fresh_b4"
PHASE = "evaluation"
BLOCK_CLASS = "holdout_evaluation_control_fatal"
ERROR_TYPE = "ValueError"
ERROR_MESSAGE = "holdout execution/evaluation role HEAD drifted"
UNAVAILABLE = "unavailable_due_to_post_exposure_evaluation_fatal"
NEXT_AUTHORITY = "final_report_and_ultra_terminal_review_only"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

_BINDING_FIELDS = frozenset({"path", "root_sha256"})
_FILE_BINDING_FIELDS = frozenset({"path", "sha256"})
_LEDGER_BINDING_FIELDS = frozenset({"path", "sha256", "state"})
_CONTROL_FIELDS = frozenset(
    {
        "directory",
        "command",
        "command_receipt",
        "run_exit_file",
        "run_exit",
        "stderr",
    }
)
_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "benchmark",
        "phase",
        "block_class",
        "error_type",
        "error_message",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "execution_plan_sha256",
        "run_nonce",
        "controller_decision",
        "opening_release",
        "execution",
        "execution_review",
        "evaluation_output_dir",
        "evaluation_control",
        "evaluation_artifact_created",
        "evaluation_root_sha256",
        "evaluation_review_output_dir",
        "evaluation_review_started",
        "evaluation_review_artifact_created",
        "related_process_count",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "reporting_machinery_head",
        "scientific_ledger_before",
        "planned_pair_count",
        "complete_paired_row_count",
        "planned_arm_run_count",
        "complete_arm_run_count",
        "terminal_arm_run_count",
        "full_denominator_formed",
        "outcome_fields_consumed",
        "raw_outcome_values_inspected",
        "rerun_allowed",
        "new_nonce_allowed",
        "alternate_directory_allowed",
        "suffix_allowed",
        "claim_authorized",
        "evaluation_result_status",
        "next_authority",
        "closeout_payload_sha256",
    }
)


def freeze_b4_evaluation_terminal_closeout(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    execution_plan_sha256: str,
    run_nonce: str,
    controller_decision: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    execution: Mapping[str, Any],
    execution_review: Mapping[str, Any],
    evaluation_output_dir: str,
    evaluation_control: Mapping[str, Any],
    evaluation_review_output_dir: str,
    implementation_source_head: str,
    pointer_head_at_release: str,
    reporting_machinery_head: str,
    scientific_ledger_before: Mapping[str, Any],
) -> dict[str, Any]:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    protocol = _sha(experiment_protocol_sha256, "experiment protocol")
    plan = _sha(execution_plan_sha256, "execution plan")
    nonce = _sha(run_nonce, "run nonce")
    controller = _binding(controller_decision, "controller decision")
    release = _binding(opening_release, "opening release")
    execution_binding = _binding(execution, "execution")
    execution_review_binding = _binding(
        execution_review, "execution review"
    )
    control = _control(evaluation_control)
    ledger = _ledger_binding(scientific_ledger_before)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "benchmark": BENCHMARK,
        "phase": PHASE,
        "block_class": BLOCK_CLASS,
        "error_type": ERROR_TYPE,
        "error_message": ERROR_MESSAGE,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "execution_plan_sha256": plan,
        "run_nonce": nonce,
        "controller_decision": controller,
        "opening_release": release,
        "execution": execution_binding,
        "execution_review": execution_review_binding,
        "evaluation_output_dir": _absolute_posix(
            evaluation_output_dir, "evaluation output"
        ),
        "evaluation_control": control,
        "evaluation_artifact_created": False,
        "evaluation_root_sha256": None,
        "evaluation_review_output_dir": _absolute_posix(
            evaluation_review_output_dir, "evaluation review output"
        ),
        "evaluation_review_started": False,
        "evaluation_review_artifact_created": False,
        "related_process_count": 0,
        "implementation_source_head": _git_head(
            implementation_source_head, "implementation source"
        ),
        "pointer_head_at_release": _git_head(
            pointer_head_at_release, "pointer at release"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reporting_machinery_head": _git_head(
            reporting_machinery_head, "reporting machinery"
        ),
        "scientific_ledger_before": ledger,
        "planned_pair_count": 500,
        "complete_paired_row_count": 500,
        "planned_arm_run_count": 1500,
        "complete_arm_run_count": 1500,
        "terminal_arm_run_count": 1500,
        "full_denominator_formed": True,
        "outcome_fields_consumed": [],
        "raw_outcome_values_inspected": False,
        "rerun_allowed": False,
        "new_nonce_allowed": False,
        "alternate_directory_allowed": False,
        "suffix_allowed": False,
        "claim_authorized": False,
        "evaluation_result_status": UNAVAILABLE,
        "next_authority": NEXT_AUTHORITY,
    }
    if (
        control["run_exit"] != 1
        or ledger["state"] != "full_denominator_formed"
    ):
        raise ValueError("Fresh B4 evaluation terminal state drifted")
    payload["closeout_payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_b4_evaluation_terminal_closeout(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("Fresh B4 evaluation closeout field set drifted")
    expected = freeze_b4_evaluation_terminal_closeout(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        execution_plan_sha256=value["execution_plan_sha256"],
        run_nonce=value["run_nonce"],
        controller_decision=value["controller_decision"],
        opening_release=value["opening_release"],
        execution=value["execution"],
        execution_review=value["execution_review"],
        evaluation_output_dir=value["evaluation_output_dir"],
        evaluation_control=value["evaluation_control"],
        evaluation_review_output_dir=value["evaluation_review_output_dir"],
        implementation_source_head=value["implementation_source_head"],
        pointer_head_at_release=value["pointer_head_at_release"],
        reporting_machinery_head=value["reporting_machinery_head"],
        scientific_ledger_before=value["scientific_ledger_before"],
    )
    if not strict_equal(value, expected):
        raise ValueError("Fresh B4 evaluation closeout exact value drifted")
    return expected


def _binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _BINDING_FIELDS:
        raise ValueError(f"{label} binding field set drifted")
    return {
        "path": _absolute_posix(value["path"], label),
        "root_sha256": _sha(value["root_sha256"], label),
    }


def _file_binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _FILE_BINDING_FIELDS:
        raise ValueError(f"{label} binding field set drifted")
    return {
        "path": _absolute_posix(value["path"], label),
        "sha256": _sha(value["sha256"], label),
    }


def _ledger_binding(
    value: Mapping[str, Any],
) -> dict[str, str]:
    if type(value) is not dict or set(value) != _LEDGER_BINDING_FIELDS:
        raise ValueError("scientific ledger binding field set drifted")
    if value["state"] != "full_denominator_formed":
        raise ValueError("scientific ledger state drifted")
    return {
        "path": _absolute_posix(value["path"], "scientific ledger"),
        "sha256": _sha(value["sha256"], "scientific ledger"),
        "state": value["state"],
    }


def _control(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _CONTROL_FIELDS:
        raise ValueError("evaluation control field set drifted")
    run_exit = value["run_exit"]
    if type(run_exit) is not int or run_exit != 1:
        raise ValueError("evaluation control run.exit drifted")
    return {
        "directory": _absolute_posix(
            value["directory"], "evaluation control directory"
        ),
        "command": _file_binding(value["command"], "evaluation control command"),
        "command_receipt": _file_binding(
            value["command_receipt"], "evaluation control command receipt"
        ),
        "run_exit_file": _file_binding(
            value["run_exit_file"], "evaluation control run.exit"
        ),
        "run_exit": run_exit,
        "stderr": _file_binding(value["stderr"], "evaluation control stderr"),
    }


def _absolute_posix(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("/")
        or value.endswith("/")
        or "/../" in f"{value}/"
        or "/./" in f"{value}/"
    ):
        raise ValueError(f"{label} path drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} SHA drifted")
    return value


def _git_head(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} HEAD drifted")
    return value
