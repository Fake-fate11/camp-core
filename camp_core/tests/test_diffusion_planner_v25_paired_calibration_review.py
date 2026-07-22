from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_paired_calibration import (
    build_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration_execution import (
    project_paired_calibration_corpus,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from scripts.integrations.review_diffusion_planner_v25_paired_calibration import (
    _independent_corpus,
    _review_initial_pairing,
)


ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)


def _results(plan: dict) -> list[dict]:
    result = []
    ordinal = 0
    for unit in plan["execution_units"]:
        identity = next(
            row
            for row in plan["identities"]
            if row["scenario_identity_sha256"] == unit["scenario_identity_sha256"]
        )
        for arm_index, arm in enumerate(unit["ordered_arms"]):
            result.append(
                {
                    "run_ordinal": ordinal,
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": unit["unit_sha256"],
                    "arm_order_index": arm_index,
                    "plan_arm": arm,
                    "scenario_identity_sha256": unit["scenario_identity_sha256"],
                    "scenario_family": identity["scenario_family"],
                    "risk_tier": identity["risk_tier"],
                    "signal_source_class": identity["signal_source_class"],
                    "status": "complete",
                }
            )
            ordinal += 1
    return result


def test_independent_corpus_matches_producer_projection() -> None:
    base = build_signal_complete_execution_plan("calibration")
    plan = build_paired_calibration_execution_plan(base)
    results = _results(plan)
    assert _independent_corpus(plan, results) == project_paired_calibration_corpus(
        plan=plan, results=results
    )


def test_independent_corpus_rejects_run_order_drift() -> None:
    plan = build_paired_calibration_execution_plan(
        build_signal_complete_execution_plan("calibration")
    )
    results = _results(plan)
    results[0]["run_ordinal"] = 1
    with pytest.raises(ValueError, match="order drifted"):
        _independent_corpus(plan, results)


def test_initial_pairing_rejects_candidate_tensor_drift() -> None:
    def native(candidate_sha: str) -> dict:
        return {
            "route_sha256": "1" * 64,
            "initial_state_sha256": "2" * 64,
            "initial_input_sha256": "3" * 64,
            "ticks": [
                {
                    "input_sha256": "3" * 64,
                    "candidate_tensor_sha256_before": candidate_sha,
                    "default_output_sha256": "5" * 64,
                    "candidate_row_sha256": ["5" * 64] * 8,
                }
            ],
        }

    rows = {
        arm: {"status": "complete", "native_receipt": native("4" * 64)}
        for arm in ARMS
    }
    pairs = {index: copy.deepcopy(rows) for index in range(100)}
    pairs[0]["camp_scene14d_no_v2i"]["native_receipt"]["ticks"][0][
        "candidate_tensor_sha256_before"
    ] = "6" * 64
    with pytest.raises(ValueError, match="tick0 candidate_tensor"):
        _review_initial_pairing(pairs)
