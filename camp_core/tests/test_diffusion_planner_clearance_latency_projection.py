from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_clearance_latency_projection import (
    analyze,
    render_markdown,
)


def test_clearance_latency_projection_reports_budget_sensitivity(tmp_path) -> None:
    root = tmp_path / "grid"
    run_a = root / "route_a" / "seed_1" / "npc_4" / "tl_off" / "static"
    run_b = root / "route_b" / "seed_2" / "npc_0" / "tl_on" / "static"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)
    (run_a / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=105.0, clearance=10.0),
                _record(total=115.0, clearance=20.0),
            ]
        ),
        encoding="utf-8",
    )
    (run_b / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=90.0, clearance=2.0),
                _record(total=95.0, clearance=3.0),
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

    assert report["analysis"]["projection_not_replay_measurement"] is True
    assert report["analysis"]["online_selector_change"] is False
    assert report["records"] == {
        "logs": 2,
        "total": 4,
        "usable": 4,
        "missing_total_latency": 0,
        "missing_clearance_latency": 0,
    }
    assert report["baseline"]["runs_over_budget"] == 1
    assert report["baseline"]["per_run_total_p95_ms"]["p95"] == pytest.approx(
        113.5125
    )
    assert report["projection_modes"]["constant_new_p95"][
        "runs_over_budget"
    ] == 0
    assert report["projection_modes"]["cap_at_new_p95"]["runs_over_budget"] == 0
    assert report["projection_modes"]["scale_by_smoke_p95_ratio"][
        "runs_over_budget"
    ] == 0
    assert report["projection_modes"]["constant_new_p95"][
        "total_latency_ms"
    ]["p95"] == pytest.approx(96.0)
    assert report["projection_modes"]["scale_by_smoke_p95_ratio"][
        "projected_clearance_latency_ms"
    ]["p95"] == pytest.approx(0.925)

    markdown = render_markdown(report)
    assert "DP-CAMP Clearance Latency Projection" in markdown
    assert "Projection only" in markdown
    assert "not replay-measured latency" in markdown
    assert "does not define CAMP atoms" in markdown


def test_clearance_latency_projection_rejects_missing_usable_records(tmp_path) -> None:
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


def _record(*, total: float, clearance: float) -> dict:
    return {
        "selection_step": 0,
        "latency_ms_including_candidate_generation": total,
        "latency_ms_shadow_obstacle_clearance": clearance,
    }
