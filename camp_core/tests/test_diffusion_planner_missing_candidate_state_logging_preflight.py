from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_missing_candidate_state_logging_preflight import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _post_inventory_plan(
    *,
    status: str = "post_inventory_next_design_plan_ready",
    families: list[str] | None = None,
) -> dict[str, object]:
    families = families or [
        "candidate_lane_topology",
        "candidate_traffic_light_path_relation",
        "route_curvature_turn_context",
        "neighbor_interaction_clearance",
    ]
    return {
        "final_decision": {
            "status": status,
            "passed": status == "post_inventory_next_design_plan_ready",
            "authorized_next_work": (
                "predeclare_default_off_missing_candidate_state_logging_preflight_only"
                if status == "post_inventory_next_design_plan_ready"
                else None
            ),
            "recommended_first_action": (
                "default_off_missing_candidate_state_logging_preflight"
                if status == "post_inventory_next_design_plan_ready"
                else None
            ),
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "default_off_logging_contract": {
            "must_be": [
                "default-off",
                "selection-effect-free",
                "current-tick only",
                "candidate-level where used for atoms",
                "deterministic for fixed DP candidates and map/context",
                "validated for finite values and exact baseline equivalence",
            ],
            "candidate_state_families": families,
            "must_not_include": [
                "candidate_closed_loop_outcomes",
                "future collision/red/near-miss/completion labels",
                "DP weight or source changes",
                "online selector behavior changes",
            ],
        },
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


def test_missing_candidate_state_logging_preflight_is_ready(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)

    report = build_report(
        post_inventory_plan=_post_inventory_plan(),
        replay_source=replay,
        integration_source=integration,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["design_checks"]["passed"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    contract = report["implementation_contract"]
    assert "baseline equivalence tests that logging does not change selection" in (
        contract["allowed_next"]
    )
    assert "closed-loop replay" in contract["blocked_until_next_gate"]

    markdown = render_markdown(report)
    assert "Missing Candidate-State Logging Preflight" in markdown
    assert "design-only" in markdown


def test_missing_candidate_state_logging_preflight_blocks_wrong_source(
    tmp_path: Path,
) -> None:
    replay, integration = _write_sources(tmp_path)

    report = build_report(
        post_inventory_plan=_post_inventory_plan(
            status="post_inventory_next_design_plan_blocked"
        ),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert any(
        check["name"] == "source_status_ready" and check["passed"] is False
        for check in report["source_checks"]
    )


def test_missing_candidate_state_logging_preflight_blocks_missing_family(
    tmp_path: Path,
) -> None:
    replay, integration = _write_sources(tmp_path)

    report = build_report(
        post_inventory_plan=_post_inventory_plan(
            families=["candidate_lane_topology"]
        ),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [
        check["name"] for check in report["source_checks"] if not check["passed"]
    ]
    assert failed == ["source_candidate_families_match_required"]


def test_missing_candidate_state_logging_preflight_blocks_missing_hooks(
    tmp_path: Path,
) -> None:
    replay, integration = _write_sources(tmp_path, include_hooks=False)

    report = build_report(
        post_inventory_plan=_post_inventory_plan(),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["design_checks"]["missing_source_hooks"]


def test_missing_candidate_state_logging_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    replay, integration = _write_sources(tmp_path)
    plan_path = tmp_path / "post_inventory_plan.json"
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    plan_path.write_text(json.dumps(_post_inventory_plan()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "preflight",
            "--post_inventory_plan_json",
            str(plan_path),
            "--replay_source",
            str(replay),
            "--integration_source",
            str(integration),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Missing Candidate-State" in output_md.read_text(encoding="utf-8")
