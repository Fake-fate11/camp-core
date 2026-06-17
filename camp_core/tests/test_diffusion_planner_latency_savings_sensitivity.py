from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_latency_savings_sensitivity import (
    analyze,
    render_markdown,
)


def test_latency_savings_sensitivity_marks_admissible_camp_atom_upper_bound(
    tmp_path,
) -> None:
    root = tmp_path / "grid"
    over = root / "route_a" / "seed_1" / "npc_4" / "tl_off" / "static"
    under = root / "route_b" / "seed_2" / "npc_0" / "tl_on" / "static"
    over.mkdir(parents=True)
    under.mkdir(parents=True)
    (over / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=110.0, clearance=10.0, atom=8.0, candidate=60.0),
                _record(total=120.0, clearance=20.0, atom=10.0, candidate=70.0),
            ]
        ),
        encoding="utf-8",
    )
    (under / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=90.0, clearance=2.0, atom=4.0, candidate=40.0),
                _record(total=95.0, clearance=3.0, atom=4.0, candidate=42.0),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [root],
        label="unit",
        reference_old_clearance_p95_ms=20.0,
        reference_new_clearance_p95_ms=1.0,
        reference_source="unit-smoke",
    )

    assert report["analysis"]["component_savings_are_hypothetical"] is True
    assert report["records"]["logs"] == 2
    mode = report["projection_modes"]["constant_new_p95"]
    assert mode["no_extra_saving_runs_over_budget"] == 1
    scenarios = mode["scenarios"]
    assert scenarios["no_extra_saving"]["runs_over_budget"] == 1
    assert scenarios["camp_atom_computation_25pct_saving"][
        "runs_over_budget"
    ] == 0
    assert scenarios["camp_atom_computation_25pct_saving"][
        "camp_side_exact_equivalence_candidate"
    ] is True
    assert scenarios["candidate_generation_zero_inadmissible_upper_bound"][
        "camp_side_exact_equivalence_candidate"
    ] is False
    assert scenarios["camp_atom_computation_50pct_saving"][
        "mean_record_saving_ms"
    ]["mean"] == pytest.approx(3.25)
    assert scenarios["no_extra_saving"]["per_run_shortfall_ms"][
        "max"
    ] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "DP-CAMP Latency Savings Sensitivity" in markdown
    assert "component savings are hypothetical" in markdown
    assert "do not change selector semantics" in markdown
    assert "does not change finite candidates" in markdown


def test_latency_savings_sensitivity_rejects_missing_usable_records(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "latency_ms_including_candidate_generation": 100.0,
                    "latency_ms_shadow_obstacle_clearance": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="No records had finite"):
        analyze(
            [log_path],
            reference_old_clearance_p95_ms=20.0,
            reference_new_clearance_p95_ms=1.0,
        )


def _record(
    *,
    total: float,
    clearance: float,
    atom: float,
    candidate: float,
) -> dict:
    return {
        "selection_step": 0,
        "latency_ms_including_candidate_generation": total,
        "latency_ms_shadow_obstacle_clearance": clearance,
        "latency_ms_camp_atom_computation": atom,
        "latency_ms_camp_selection": atom + 2.0,
        "latency_ms_reward_scoring": 20.0,
        "latency_ms_candidate_generation": candidate,
    }
