from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_post_inventory_next_design import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _inventory(
    *,
    status: str = "current_tick_no_leak_atom_support_inventory_no_unclosed_fields",
    admissible: list[str] | None = None,
) -> dict[str, object]:
    admissible = admissible or []
    return {
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "no_admissible_unclosed_current_tick_candidate_support",
            "admissible_unclosed_candidate_families": admissible,
            "partial_candidate_families": [],
            "available_existing_or_closed_proxy_families": [
                "dp_reward_lane_proxy",
                "dp_reward_neighbor_proxy",
                "dp_scene_aggregate",
                "existing_comfort_proxy",
                "existing_shape_support_proxy",
                "existing_traffic_proxy",
            ],
            "authorized_next_work": (
                "proof_objective_v2_or_default_off_logging_preflight_design_only"
                if status
                == "current_tick_no_leak_atom_support_inventory_no_unclosed_fields"
                else None
            ),
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def test_post_inventory_plan_authorizes_default_off_logging_preflight_only() -> None:
    report = build_report(support_inventory=_inventory(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert (
        decision["recommended_first_action"]
        == "default_off_missing_candidate_state_logging_preflight"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    rejected = {route["name"] for route in report["rejected_routes"]}
    assert "train_new_camp_weights_from_current_logs" in rejected
    assert "proof_objective_only_as_performance_claim" in rejected

    contract = report["default_off_logging_contract"]
    assert "candidate_lane_topology" in contract["candidate_state_families"]
    assert "candidate_closed_loop_outcomes" in contract["must_not_include"]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    markdown = render_markdown(report)
    assert "Post-Inventory Next Design Plan" in markdown
    assert "not a classical Benders decomposition" in markdown


def test_post_inventory_plan_blocks_if_inventory_has_admissible_fields() -> None:
    report = build_report(
        support_inventory=_inventory(admissible=["candidate_lane_topology"]),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    failed = [
        check["name"] for check in report["plan_checks"] if not check["passed"]
    ]
    assert failed == ["no_admissible_current_log_fields"]


def test_post_inventory_plan_blocks_wrong_source_status() -> None:
    report = build_report(
        support_inventory=_inventory(
            status="current_tick_no_leak_atom_support_inventory_has_admissible_unclosed_fields"
        ),
        label="unit",
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_post_inventory_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "inventory.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source.write_text(json.dumps(_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "post_inventory",
            "--support_inventory_json",
            str(source),
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
    assert "Post-Inventory" in output_md.read_text(encoding="utf-8")
