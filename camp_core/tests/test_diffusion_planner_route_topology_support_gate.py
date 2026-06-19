from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.integrations.analyze_diffusion_planner_route_topology_support_gate import (
    READY_STATUS,
    SOURCE_CONFLICT_STATUS,
    RouteTopologyGateConfig,
    analyze,
    build_report_from_rows,
    render_markdown,
)


def _source_donor_report(
    *,
    status: str = "source_donor_support_insufficient",
    full36_authorized: bool = False,
) -> dict[str, object]:
    return {
        "support": {
            "hard_feasible_snapshot_support_rate": 1.0 / 57.0,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "required_min_snapshot_support_rate": 0.25,
        },
        "final_decision": {
            "status": status,
            "online_selector_authorized": False,
            "closed_loop_smoke_authorized": False,
            "full36_authorized": full36_authorized,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _write_snapshot(
    root: Path,
    *,
    name: str = "camp_microbenchmark_step_0001.npz",
    candidate_y_offset: float = 0.0,
    red_y_offset: float = 0.0,
) -> None:
    x = np.linspace(0.0, 120.0, 121)
    lane = np.column_stack([x, np.zeros_like(x)])
    route_lanes = np.zeros((1, 121, 33), dtype=float)
    route_lanes[0, :, 0] = x
    route_lanes[0, :, 1] = 0.0
    red_x = x[20:28]
    red = np.column_stack(
        [
            red_x,
            np.full_like(red_x, red_y_offset),
            np.ones_like(red_x),
            np.zeros_like(red_x),
        ]
    )
    candidate_x = np.linspace(0.0, 30.0, 30)
    candidate = np.zeros((3, 30, 4), dtype=float)
    for idx, offset in enumerate((0.0, 0.2, -0.2)):
        candidate[idx, :, 0] = candidate_x
        candidate[idx, :, 1] = candidate_y_offset + offset
        candidate[idx, :, 2] = 1.0
    np.savez(
        root / name,
        candidates=candidate,
        lane_centerline=lane,
        red_route_points=red,
        reward_input__route_lanes=route_lanes,
    )


def _write_source_report(path: Path, report: dict[str, object]) -> None:
    import json

    path.write_text(json.dumps(report), encoding="utf-8")


def test_route_topology_gate_ready_for_offline_design(tmp_path: Path) -> None:
    _write_snapshot(tmp_path)
    source_json = tmp_path / "source.json"
    _write_source_report(source_json, _source_donor_report())

    report = analyze(
        snapshot_dir=tmp_path,
        source_donor_support_json=source_json,
        label="unit",
    )

    assert report["snapshot_aggregate"]["snapshots"] == 1
    assert report["snapshot_aggregate"]["ready_snapshot_rate"] == 1.0
    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["offline_candidate_augmentation_screen_authorized"] is True
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False

    markdown = render_markdown(report)
    assert "Route/Topology Candidate-Support Readiness Gate" in markdown
    assert "not classical Benders" in markdown


def test_route_topology_gate_blocks_coordinate_mismatch() -> None:
    report = build_report_from_rows(
        [
            {
                "snapshot": "bad.npz",
                "ready": False,
                "failure_reasons": ["candidate_lane_coordinate_mismatch"],
                "candidate_count": 3,
                "candidate_horizon": 30,
                "lane_points": 121,
                "red_points": 8,
                "route_lane_points": 121,
                "lane_span_m": 120.0,
                "route_lane_span_m": 120.0,
                "candidate_lane_p95_m": 10.0,
                "red_lane_p95_m": 0.0,
            }
        ],
        source_donor=_source_donor_report(),
    )

    assert report["final_decision"]["status"] == "route_topology_candidate_design_blocked"
    assert report["snapshot_aggregate"]["failure_reason_counts"] == {
        "candidate_lane_coordinate_mismatch": 1
    }


def test_route_topology_gate_fails_closed_on_source_conflict() -> None:
    report = build_report_from_rows(
        [
            {
                "snapshot": "ready.npz",
                "ready": True,
                "failure_reasons": [],
                "candidate_count": 3,
                "candidate_horizon": 30,
                "lane_points": 121,
                "red_points": 8,
                "route_lane_points": 121,
                "lane_span_m": 120.0,
                "route_lane_span_m": 120.0,
                "candidate_lane_p95_m": 0.2,
                "red_lane_p95_m": 0.0,
            }
        ],
        source_donor=_source_donor_report(full36_authorized=True),
    )

    decision = report["final_decision"]
    assert decision["status"] == SOURCE_CONFLICT_STATUS
    assert decision["offline_candidate_augmentation_screen_authorized"] is False
    assert decision["source_authorization_conflicts"] == [
        "source_donor_support:full36_authorized"
    ]


def test_route_topology_gate_validates_config() -> None:
    try:
        build_report_from_rows(
            [],
            source_donor=_source_donor_report(),
            config=RouteTopologyGateConfig(min_ready_snapshot_rate=1.2),
        )
    except ValueError as exc:
        assert "min_ready_snapshot_rate" in str(exc)
    else:
        raise AssertionError("invalid config should be rejected")
