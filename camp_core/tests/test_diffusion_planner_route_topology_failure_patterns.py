from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_route_topology_failure_patterns import (
    build_report,
    render_markdown,
)


def _candidate(
    *,
    index: int,
    hard: bool,
    progress: bool,
    comfort: bool,
    hard_reasons: list[str] | None = None,
    failure_classes: list[str] | None = None,
    backup: float = 0.0,
) -> dict[str, object]:
    return {
        "candidate_index": index,
        "candidate_meta": {
            "backup_stop_offset_m": backup,
            "lateral_offset_scale": 0.5,
            "variant": "prefix_lane_projected_latest_safe_red_stop",
        },
        "selected_union_red": 40.0,
        "candidate_union_red": 10.0 - backup,
        "lower_union_red": True,
        "hard_feasible": hard,
        "hard_reasons": [] if hard_reasons is None else hard_reasons,
        "progress_feasible": progress,
        "comfort_admissible": comfort,
        "failure_classes": [] if failure_classes is None else failure_classes,
        "progress_loss_m": 0.2 + backup,
        "smoothness_loss": 0.4 + backup,
    }


def _screen(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "config": {
            "generator_policy": "prefix_lane_projected_latest_safe_red_stop",
        },
        "final_decision": {
            "status": "route_topology_candidate_support_insufficient",
        },
        "records": {"generated_candidate_rows": sum(len(r["candidate_rows"]) for r in rows)},
        "support_gate": {"min_snapshot_support_rate": 0.25},
        "rows": rows,
        "by_snapshot": [
            {
                "selection_step": row["selection_step"],
                "snapshot_path": row["snapshot_path"],
                "lower_union_red": len(row["candidate_rows"]),
                "lower_union_red_hard_feasible": sum(
                    1 for cand in row["candidate_rows"] if cand["hard_feasible"]
                ),
                "lower_union_red_progress_feasible": sum(
                    1 for cand in row["candidate_rows"] if cand["progress_feasible"]
                ),
                "lower_union_red_comfort_admissible": sum(
                    1 for cand in row["candidate_rows"] if cand["comfort_admissible"]
                ),
                "failure_class_counts": {},
            }
            for row in rows
        ],
    }


def test_failure_patterns_rejects_hard_support_insufficient() -> None:
    report = build_report(
        _screen(
            [
                {
                    "selection_step": 1,
                    "snapshot_path": "/tmp/step1.npz",
                    "selected_union_red": 40.0,
                    "candidate_rows": [
                        _candidate(
                            index=0,
                            hard=True,
                            progress=True,
                            comfort=False,
                            failure_classes=["comfort_blocked"],
                        )
                    ],
                },
                {
                    "selection_step": 2,
                    "snapshot_path": "/tmp/step2.npz",
                    "selected_union_red": 40.0,
                    "candidate_rows": [
                        _candidate(
                            index=0,
                            hard=False,
                            progress=False,
                            comfort=False,
                            hard_reasons=["dp_lane_crossing"],
                            failure_classes=["route_topology_lane_invalid"],
                            backup=1.0,
                        )
                    ],
                },
            ]
        ),
        label="unit",
        min_snapshot_support_rate=0.75,
    )

    assert (
        report["final_decision"]["status"]
        == "route_topology_failure_patterns_hard_support_insufficient"
    )
    assert report["support"]["hard_feasible_snapshot_rate"] == pytest.approx(0.5)
    assert report["support"]["comfort_admissible_snapshot_rate"] == pytest.approx(0.0)
    assert report["failures"]["hard_reason_snapshot_counts"] == {
        "dp_lane_crossing": 1
    }
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False

    markdown = render_markdown(report)
    assert "Route-Topology Failure-Pattern Audit" in markdown
    assert "read-only finite-candidate diagnostic" in markdown
    assert "classical Benders decomposition" in markdown


def test_failure_patterns_identifies_comfort_limited_after_hard_support() -> None:
    report = build_report(
        _screen(
            [
                {
                    "selection_step": 1,
                    "snapshot_path": "/tmp/step1.npz",
                    "selected_union_red": 40.0,
                    "candidate_rows": [
                        _candidate(
                            index=0,
                            hard=True,
                            progress=True,
                            comfort=False,
                            failure_classes=["comfort_blocked"],
                        )
                    ],
                },
                {
                    "selection_step": 2,
                    "snapshot_path": "/tmp/step2.npz",
                    "selected_union_red": 40.0,
                    "candidate_rows": [
                        _candidate(
                            index=1,
                            hard=True,
                            progress=True,
                            comfort=False,
                            failure_classes=["comfort_blocked"],
                            backup=1.0,
                        )
                    ],
                },
            ]
        ),
        min_snapshot_support_rate=0.75,
    )

    assert (
        report["final_decision"]["status"]
        == "route_topology_failure_patterns_comfort_limited"
    )
    assert report["support"]["hard_feasible_snapshot_rate"] == pytest.approx(1.0)
    assert report["support"]["progress_feasible_snapshot_rate"] == pytest.approx(1.0)
    assert report["support"]["comfort_admissible_snapshot_rate"] == pytest.approx(0.0)


def test_failure_patterns_validates_support_threshold() -> None:
    with pytest.raises(ValueError, match="min_snapshot_support_rate"):
        build_report(_screen([]), min_snapshot_support_rate=1.5)
