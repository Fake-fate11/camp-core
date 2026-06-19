from __future__ import annotations

from pathlib import Path

from scripts.integrations.design_diffusion_planner_observable_state_logging import (
    FieldSpec,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _inventory_report(
    status: str = "observable_state_inventory_missing_new_logged_state",
    bottleneck: str = "missing_logged_candidate_state",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "primary_bottleneck": bottleneck,
            "authorized_next_work": "default_off_logging_preflight_design_only",
        },
        "records": {"total": 2, "candidate_rows": 16},
    }


def _write_sources(tmp_path: Path, *, include_hooks: bool = True) -> tuple[Path, Path]:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    integration = tmp_path / "diffusion_planner.py"
    if include_hooks:
        replay.write_text(
            "\n".join(
                [
                    "generate_candidate_trajectories(",
                    "candidates, neighbor_predictions, turn_logits = 1, 2, 3",
                    "def _candidate_route_progress(): pass",
                    "def _ego_frame_xy(): pass",
                    "route_centerline = []",
                    "red_route_points_from_scene(scene, ego_id)",
                    "red_route_points = []",
                    "def _candidate_obstacles(): pass",
                    "neighbor_predictions = []",
                    "obstacles = []",
                    "records.append({})",
                    "latency_ms_observable_state = 0.0",
                    "candidate_obstacle_clearance = None",
                ]
            ),
            encoding="utf-8",
        )
        integration.write_text(
            "\n".join(
                [
                    "def compute_candidate_obstacle_clearance_diagnostics():",
                    "    return {'future_outcome_leakage': False, 'selection_effect': False}",
                    "def _route_centerline(): pass",
                    "ego.route_lanes",
                    "DriverAtomContext",
                ]
            ),
            encoding="utf-8",
        )
    else:
        replay.write_text("records.append({})", encoding="utf-8")
        integration.write_text("DriverAtomContext", encoding="utf-8")
    return replay, integration


def test_logging_design_ready_when_inventory_rejected_and_hooks_exist(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)

    report = analyze(
        inventory_report=_inventory_report(),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "default_off_logging_preflight_implementation_unit_tests_only"
    )
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert report["analysis"]["diffusion_planner_modification"] is False
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["design_checks"]["passed"] is True


def test_logging_design_blocks_wrong_source_gate(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)

    report = analyze(
        inventory_report=_inventory_report(
            status="observable_state_inventory_has_new_logged_state",
            bottleneck="new_candidate_state_available",
        ),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_logging_design_rejects_missing_source_hooks(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path, include_hooks=False)

    report = analyze(
        inventory_report=_inventory_report(),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["design_checks"]["missing_source_hooks"]


def test_logging_design_rejects_outcome_leak_field(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)
    bad_field = FieldSpec(
        name="candidate_future_collision",
        family="neighbor_interaction_clearance",
        shape="[K]",
        dtype="bool",
        source="candidate_closed_loop_outcomes",
        derivation="future collision outcome",
        finite_check="boolean",
        latency_bucket="latency_ms_outcome_collection",
        atomization="invalid",
        convexity_note="invalid",
        uses_future_outcomes=True,
    )

    report = analyze(
        inventory_report=_inventory_report(),
        replay_source=replay,
        integration_source=integration,
        field_specs=(bad_field,),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["design_checks"]["invalid_fields"] == ["candidate_future_collision"]
