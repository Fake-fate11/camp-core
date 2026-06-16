from __future__ import annotations

import pytest

from scripts.integrations.compare_diffusion_planner_alternative_candidates import (
    compare_reports,
)


GUARDS = (
    "prefix_tracker_jerk_nonworse",
    "prefix_rollout_h3_jerk_nonworse",
)


def _guard(name: str, failures: int, success: int) -> dict:
    return {
        "name": name,
        "with_guarded_success": success,
        "guarded_success_rate": success / failures if failures else 1.0,
    }


def _screen(name: str, *, failures: int, any_success: int, guarded: int) -> dict:
    return {
        "name": name,
        "failure_records": failures,
        "with_any_admissible_posterior_success": any_success,
        "guard_sets": [
            _guard(GUARDS[0], failures, guarded),
            _guard(GUARDS[1], failures, max(0, guarded - 2)),
        ],
    }


def _report(*, failures: int, any_success: int, guarded: int) -> dict:
    return {
        "records": {"nonfallback": 100},
        "screens": [
            _screen(
                "balanced_lateral_jerk_nondegrading",
                failures=failures,
                any_success=any_success,
                guarded=guarded,
            ),
            _screen(
                "relaxed_lateral_jerk_nondegrading",
                failures=failures,
                any_success=any_success,
                guarded=guarded,
            ),
        ],
    }


def test_alternative_candidate_comparison_advances_after_all_gates() -> None:
    baseline = _report(failures=100, any_success=10, guarded=5)
    candidate = _report(failures=100, any_success=55, guarded=30)

    report = compare_reports(
        baseline=baseline,
        candidates=[("k16_noise", None, candidate)],
    )

    compared = report["candidates"][0]
    assert compared["gates"]["alternative_candidate_gate_pass"] is True
    assert compared["gates"]["latency_gate_pass"] is None
    assert compared["next_step"] == "advance_to_generator_side_latency_and_pairing_design"
    for screen in compared["screens"]:
        assert screen["gates"]["screen_gate_pass"] is True
        assert screen["best_guard_set"]["name"] == GUARDS[0]


def test_alternative_candidate_comparison_rejects_weak_guarded_coverage() -> None:
    baseline = _report(failures=100, any_success=10, guarded=5)
    candidate = _report(failures=100, any_success=55, guarded=12)

    report = compare_reports(
        baseline=baseline,
        candidates=[("weak_guard", None, candidate)],
    )

    compared = report["candidates"][0]
    assert compared["gates"]["alternative_candidate_gate_pass"] is False
    assert compared["screens"][0]["gates"]["any_success_gate_pass"] is True
    assert compared["screens"][0]["gates"]["guarded_success_gate_pass"] is False
    assert compared["next_step"] == "reject_current_candidate_generation_grid"


def test_alternative_candidate_comparison_requires_declared_screens() -> None:
    baseline = _report(failures=100, any_success=10, guarded=5)
    candidate = _report(failures=100, any_success=55, guarded=30)
    candidate["screens"] = candidate["screens"][:1]

    with pytest.raises(ValueError, match="missing required screens"):
        compare_reports(
            baseline=baseline,
            candidates=[("missing", None, candidate)],
        )
