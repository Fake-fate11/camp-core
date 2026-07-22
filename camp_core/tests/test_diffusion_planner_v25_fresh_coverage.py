from __future__ import annotations

import copy
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_coverage import (
    build_fresh_b2_explicit_coverage,
    validate_fresh_b2_explicit_coverage,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)


def _fixture(tmp_path: Path) -> tuple[dict, list[dict]]:
    suite = build_signal_complete_suite("fresh_b2")
    for relative, payload in suite["map_payloads"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    plan = build_signal_complete_execution_plan("fresh_b2")
    prepared = [
        build_signal_complete_runtime_case(
            identity, map_artifact=tmp_path, seeds=plan["seeds"]
        )
        for identity in plan["identities"]
    ]
    return plan, prepared


def test_explicit_coverage_uses_physical_inputs_without_fresh_execution(
    tmp_path: Path,
) -> None:
    plan, prepared = _fixture(tmp_path)
    value = build_fresh_b2_explicit_coverage(
        plan, prepared_runtime_cases=prepared
    )
    reopened = validate_fresh_b2_explicit_coverage(value, plan=plan)
    census = reopened["census"]
    assert census["map_count"] == 25
    assert census["route_count"] == 100
    assert census["paired_unit_count"] == 500
    assert census["arm_run_count"] == 1500
    assert census["tick_capacity"] == 96_000
    assert census["static_signal_chain_qualified_count"] == 100
    assert set(census["movement_counts"]) == {"straight", "turn"}
    assert set(census["controlled_phase_fixture_counts"]) == {
        "green",
        "yellow",
        "red",
    }
    for field in ("lead_stop", "occlusion", "dilemma_zone", "all_k_bad_eligibility"):
        assert census["boolean_coverage_counts"][field]["true"] > 0
    assert reopened["preopen_dp_forward_executed"] is False
    assert reopened["fresh_b2_opened"] is False


def test_explicit_coverage_rejects_source_and_outcome_mutation(tmp_path: Path) -> None:
    plan, prepared = _fixture(tmp_path)
    bad = copy.deepcopy(prepared)
    bad[0]["candidate_generation_executed"] = True
    with pytest.raises(ValueError, match="static runtime"):
        build_fresh_b2_explicit_coverage(plan, prepared_runtime_cases=bad)

    value = build_fresh_b2_explicit_coverage(plan, prepared_runtime_cases=prepared)
    mutated = copy.deepcopy(value)
    mutated["coverage_rows"][0]["outcome_fields_consumed"] = ["collision"]
    with pytest.raises(ValueError):
        validate_fresh_b2_explicit_coverage(mutated, plan=plan)
