from __future__ import annotations

from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    freeze_experiment_protocol,
    freeze_holdout_identity,
    freeze_tombstone,
    strict_equal,
    validate_experiment_protocol,
    validate_holdout_identity,
    validate_tombstone,
)


SCHEMA_VERSION = "camp_dp_v25_consumed_holdout_failure_closeout_v1"
REVIEW_SCHEMA_VERSION = "camp_dp_v25_consumed_holdout_failure_review_v1"

CLOSEOUT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "benchmark",
        "holdout_identity",
        "experiment_protocol",
        "reservation_commitment_sha256",
        "controller_decision",
        "opening_release",
        "consumed_marker",
        "failure_artifact",
        "cas_tombstone",
        "attempted_unit_ordinal",
        "attempted_arm",
        "raw_run_count",
        "complete_paired_row_count",
        "planned_paired_unit_count",
        "planned_arm_run_count",
        "unattempted_arm_run_count",
        "dataset_disposition",
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
        "pooling_into_future_experiment_allowed",
        "outcome_fields_consumed_for_closeout",
        "next_authority",
        "closeout_payload_sha256",
    }
)


def build_historical_b2_holdout_identity() -> dict[str, Any]:
    from .diffusion_planner_v25_signal_complete_maps import (
        build_signal_complete_suite,
        validate_signal_complete_suite,
    )
    from .diffusion_planner_v25_signal_complete_plan import (
        build_signal_complete_execution_plan,
    )

    suite = validate_signal_complete_suite(
        build_signal_complete_suite("fresh_b2")
    )
    plan = build_signal_complete_execution_plan("fresh_b2")
    return freeze_holdout_identity(
        split="fresh_b2",
        scenario_manifest_sha256=canonical_sha256(plan["identities"]),
        map_suite_payload_sha256=canonical_sha256(suite),
        route_census_sha256=canonical_sha256(
            sorted(row["route_identity_sha256"] for row in plan["identities"])
        ),
        corridor_census_sha256=canonical_sha256(
            sorted(row["corridor_sha256"] for row in plan["identities"])
        ),
        semantic_census_sha256=canonical_sha256(
            sorted(
                row["semantic_parameter_block_sha256"]
                for row in plan["identities"]
            )
        ),
        execution_plan_sha256=canonical_sha256(plan),
        seeds=plan["seeds"],
        arm_order_commit_sha256=canonical_sha256(
            [
                {
                    "unit_ordinal": row["unit_ordinal"],
                    "unit_sha256": row["unit_sha256"],
                    "ordered_arms": row["ordered_arms"],
                }
                for row in plan["execution_units"]
            ]
        ),
        paired_unit_count=plan["execution_unit_count"],
        arm_run_count=plan["planned_arm_run_count"],
        tick_capacity=plan["planned_arm_run_count"]
        * plan["ticks_per_arm_run"],
    )


def build_historical_b2_experiment_protocol(
    protocol_assets: Mapping[str, str],
) -> dict[str, Any]:
    return freeze_experiment_protocol(
        **dict(protocol_assets),
        candidate0_semantics=(
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        same_forward_contract=(
            "forward_execution_id_plus_input_model_action_digest"
        ),
        latency_contract=(
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        terminal_truth_table=(
            "exclusive_scientific_terminal_or_artifact_fatal_v1"
        ),
    )


def freeze_historical_b2_reservation_commitment(
    *,
    controller_decision_root_sha256: str,
    opening_release_root_sha256: str,
    consumed_marker_sha256: str,
    failure_artifact_root_sha256: str,
) -> str:
    values = {
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "consumed_marker_sha256": consumed_marker_sha256,
        "failure_artifact_root_sha256": failure_artifact_root_sha256,
    }
    for name, value in values.items():
        _require_sha(value, name)
    return canonical_sha256(
        {
            "schema_version": (
                "camp_dp_v25_fresh_b2_historical_opening_commitment_v1"
            ),
            **values,
            "historical_backfill_only": True,
            "raw_outcome_values_inspected": False,
        }
    )


def freeze_consumed_holdout_failure_closeout(
    *,
    benchmark: str,
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    reservation_commitment_sha256: str,
    controller_decision: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    consumed_marker: Mapping[str, Any],
    failure_artifact: Mapping[str, Any],
    attempted_unit_ordinal: int,
    attempted_arm: str,
    raw_run_count: int,
    complete_paired_row_count: int,
) -> dict[str, Any]:
    if benchmark != "fresh_b2":
        raise ValueError("consumed historical closeout is frozen to Fresh B2")
    identity = validate_holdout_identity(holdout_identity)
    protocol = validate_experiment_protocol(experiment_protocol)
    commitment = _require_sha(
        reservation_commitment_sha256, "reservation_commitment_sha256"
    )
    bindings = {
        "controller_decision": _binding(
            controller_decision, "controller_decision"
        ),
        "opening_release": _binding(opening_release, "opening_release"),
        "consumed_marker": _binding(consumed_marker, "consumed_marker"),
        "failure_artifact": _binding(failure_artifact, "failure_artifact"),
    }
    if (
        type(attempted_unit_ordinal) is not int
        or attempted_unit_ordinal != 0
        or attempted_arm != "candidate0"
        or type(raw_run_count) is not int
        or raw_run_count != 1
        or type(complete_paired_row_count) is not int
        or complete_paired_row_count != 0
    ):
        raise ValueError("consumed B2 failure denominator drifted")
    tombstone = freeze_tombstone(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        reservation_commitment_sha256=commitment,
        state="terminal_failure",
        history=[
            {"state": "reserved"},
            {"state": "opened_consumed"},
            {"state": "terminal_failure"},
        ],
        opening_attempt_count=1,
        opening_release_root_sha256=bindings["opening_release"]["root_sha256"],
        marker_sha256=bindings["consumed_marker"]["root_sha256"],
        terminal_artifact_root_sha256=bindings["failure_artifact"][
            "root_sha256"
        ],
        terminal_reason="consumed_one_shot_engineering_failure_no_fresh_evaluation",
        outcome_evaluation_completed=False,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "terminal_consumed_one_shot_engineering_failure",
        "benchmark": benchmark,
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "reservation_commitment_sha256": commitment,
        **bindings,
        "cas_tombstone": tombstone,
        "attempted_unit_ordinal": 0,
        "attempted_arm": "candidate0",
        "raw_run_count": 1,
        "complete_paired_row_count": 0,
        "planned_paired_unit_count": identity["paired_unit_count"],
        "planned_arm_run_count": identity["arm_run_count"],
        "unattempted_arm_run_count": identity["arm_run_count"] - 1,
        "dataset_disposition": (
            "immutable_engineering_diagnostic_training_calibration_"
            "evaluation_and_future_pool_ineligible"
        ),
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
        "pooling_into_future_experiment_allowed": False,
        "outcome_fields_consumed_for_closeout": [],
        "next_authority": "fresh_b3_outcome_blind_preopen_only",
    }
    payload["closeout_payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_consumed_holdout_failure_closeout(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != CLOSEOUT_FIELDS:
        raise ValueError("consumed holdout closeout field set drifted")
    expected = freeze_consumed_holdout_failure_closeout(
        benchmark=value["benchmark"],
        holdout_identity=value["holdout_identity"],
        experiment_protocol=value["experiment_protocol"],
        reservation_commitment_sha256=value[
            "reservation_commitment_sha256"
        ],
        controller_decision=value["controller_decision"],
        opening_release=value["opening_release"],
        consumed_marker=value["consumed_marker"],
        failure_artifact=value["failure_artifact"],
        attempted_unit_ordinal=value["attempted_unit_ordinal"],
        attempted_arm=value["attempted_arm"],
        raw_run_count=value["raw_run_count"],
        complete_paired_row_count=value["complete_paired_row_count"],
    )
    if not strict_equal(value, expected):
        raise ValueError("consumed holdout closeout exact value drifted")
    return expected


def independent_failure_review(
    closeout: Mapping[str, Any], *, reviewed_root_sha256: str
) -> dict[str, Any]:
    value = validate_consumed_holdout_failure_closeout(closeout)
    root = _require_sha(reviewed_root_sha256, "reviewed_root_sha256")
    tombstone = validate_tombstone(value["cas_tombstone"])
    if (
        tombstone["state"] != "terminal_failure"
        or tombstone["second_opening_allowed"] is not False
        or value["raw_outcome_values_inspected"] is not False
        or value["complete_paired_row_count"] != 0
    ):
        raise ValueError("consumed B2 failure review contract drifted")
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": "passed_independent_consumed_holdout_failure_review",
        "reviewed_root_sha256": root,
        "holdout_identity_sha256": value["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": value["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "terminal_state": "terminal_failure",
        "raw_run_count": 1,
        "complete_paired_row_count": 0,
        "second_opening_allowed": False,
        "fresh_evaluation_authorized": False,
        "raw_outcome_values_inspected": False,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "pooling_into_future_experiment_allowed": False,
        "outcome_fields_consumed_for_review": [],
    }


def _binding(value: Mapping[str, Any], name: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"{name} binding field set drifted")
    path = value["path"]
    if type(path) is not str or not path.startswith("/root/autodl-tmp/"):
        raise ValueError(f"{name} path drifted")
    return {
        "path": path,
        "root_sha256": _require_sha(
            value["root_sha256"], f"{name}.root_sha256"
        ),
    }


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
