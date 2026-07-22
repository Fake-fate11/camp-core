from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration_corpus import (
    FAILURE_SCHEMA_VERSION,
    RUN_RESULT_SCHEMA_VERSION,
    project_candidate0_calibration_corpus,
    validate_candidate0_calibration_corpus,
)
from camp_core.integrations.diffusion_planner_v25_calibration import (
    CALIBRATION_ROOT_BINDINGS,
)
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (
    build_calibration_freeze_payload_from_corpus,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _native(route: str, seed: int, ordinal: int) -> dict:
    ticks = [
        {
            "tick_index": index,
            "selected_index": 0,
            "input_sha256": f"{ordinal * 1000 + index + 1:064x}",
            "default_output_sha256": f"{ordinal * 1000 + index + 101:064x}",
            "candidate_tensor_sha256_before": f"{ordinal * 1000 + index + 201:064x}",
            "candidate_tensor_sha256_after": f"{ordinal * 1000 + index + 201:064x}",
            "pre_decision_speed_mps": 8.0,
            "safety": {"speed_mps": 7.9 if index == 0 else 8.0},
        }
        for index in range(64)
    ]
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "dp",
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_name": route,
        "route_sha256": route,
        "scenario_seed": seed,
        "initial_state_sha256": f"{ordinal + 30001:064x}",
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "secondary": {
            "route_progress_m": 100.0,
            "route_completion_rate": 0.9,
            "mean_abs_jerk_mps3": 0.5,
            "max_jerk_mps3": 1.0,
            "mean_abs_lateral_acceleration_mps2": 0.2,
            "max_abs_lateral_acceleration_mps2": 0.5,
        },
        "claim_authorized": False,
    }


def _results(*, failures: set[int] | None = None) -> tuple[dict, list[dict]]:
    plan = build_signal_complete_execution_plan("calibration")
    identities = {row["scenario_identity_sha256"]: row for row in plan["identities"]}
    rows = []
    for unit in plan["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        failed = unit["unit_ordinal"] in (failures or set())
        failure = None
        native = None
        status = "complete"
        if failed:
            status = "retained_fixed_dp_capability_failure"
            failure = {
                "schema_version": FAILURE_SCHEMA_VERSION,
                "scenario_identity_sha256": identity["scenario_identity_sha256"],
                "route_identity_sha256": identity["route_identity_sha256"],
                "seed": unit["seed"],
                "fixed_dp_head": FIXED_DP_HEAD,
                "failure_class": "fixed_dp_candidate_generation_capability_failure",
                "reason": "invalid_k8_heading_norm_envelope",
                "raw_failure_receipt_sha256": f"{unit['unit_ordinal'] + 50001:064x}",
                "training_eligible": False,
                "calibration_eligible": False,
                "evaluation_eligible": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            }
        else:
            native = _native(
                identity["route_identity_sha256"], unit["seed"], unit["unit_ordinal"]
            )
        rows.append(
            {
                "schema_version": RUN_RESULT_SCHEMA_VERSION,
                "unit_ordinal": unit["unit_ordinal"],
                "unit_sha256": unit["unit_sha256"],
                "scenario_identity_sha256": unit["scenario_identity_sha256"],
                "route_identity_sha256": identity["route_identity_sha256"],
                "seed": unit["seed"],
                "status": status,
                "native_receipt": native,
                "failure_receipt": failure,
                "fresh_b2_opened": False,
                "fresh_outcome_fields_consumed": [],
            }
        )
    return plan, rows


def test_calibration_projection_preserves_100_run_denominator() -> None:
    plan, rows = _results(failures={7, 18, 39})
    result = project_candidate0_calibration_corpus(plan, rows)
    assert result["planned_run_count"] == 100
    assert result["complete_run_count"] == 97
    assert result["retained_fixed_dp_capability_failure_count"] == 3
    assert result["paired_eligible_rate"] == 0.97
    assert result["independent_calibration_cluster_count"] == 5
    assert result["status"] == "passed_candidate0_calibration_corpus_projection"
    assert validate_candidate0_calibration_corpus(copy.deepcopy(result)) == result
    frozen = build_calibration_freeze_payload_from_corpus(
        root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
        calibration_corpus=result,
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )
    assert frozen["inventory"]["planned_paired_run_count"] == 100
    assert frozen["inventory"]["paired_eligible_run_count"] == 97
    assert frozen["inventory"]["retained_failure_run_count"] == 3
    assert frozen["candidate0_row_count"] == 97
    assert frozen["calibration_contract"]["fresh_open_authorized"] is False


def test_calibration_projection_fails_closed_below_coverage() -> None:
    plan, rows = _results(failures=set(range(6)))
    result = project_candidate0_calibration_corpus(plan, rows)
    assert result["complete_run_count"] == 94
    assert result["status"] == "candidate0_calibration_corpus_scientifically_ineligible"


@pytest.mark.parametrize("mutation", ("order", "route", "status", "camp_selected"))
def test_calibration_projection_rejects_plan_or_candidate0_drift(mutation: str) -> None:
    plan, rows = _results()
    if mutation == "order":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "route":
        rows[0]["route_identity_sha256"] = "f" * 64
    elif mutation == "status":
        rows[0]["status"] = "skipped"
    else:
        rows[0]["native_receipt"]["ticks"][3]["selected_index"] = 1
    with pytest.raises(ValueError):
        project_candidate0_calibration_corpus(plan, rows)
