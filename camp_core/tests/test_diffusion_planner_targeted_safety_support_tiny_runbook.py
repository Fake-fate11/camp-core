from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_targeted_safety_support_design import (
    build_report as build_design_report,
)
from scripts.integrations.plan_diffusion_planner_targeted_safety_support_tiny_runbook import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
)


def _materiality() -> dict:
    return {
        "final_decision": {
            "status": "alternative_safety_source_materiality_ready",
            "passed": True,
            "authorized_next_work": "targeted_safety_support_scenario_or_source_design_only",
            "has_actionable_existing_safety_source": False,
            "has_material_safety_source": True,
            "actionable_existing_safety_sources": [],
            "material_but_current_selection_already_best": [
                "h30_union_planned_red_light_cost"
            ],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "materiality_summary": {"by_source": []},
    }


def _design() -> dict:
    return build_design_report(materiality_report=_materiality())


def test_targeted_safety_support_tiny_runbook_accepts_design() -> None:
    report = build_report(
        design_report=_design(),
        output_root="/tmp/targeted_support",
        check_assets=False,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["run_count"] == 5
    assert decision["expected_records"] == 50
    assert decision["expected_available_records"] == 50
    assert decision["new_replay_authorized"] is True
    assert decision["closed_loop_replay_authorized"] is False
    assert report["analysis"]["label"] == "unit"
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert len(report["commands"]["replays"]) == 5
    materiality_command = report["commands"]["materiality_audit"]
    assert "--availability_mode" in materiality_command
    assert "candidate_safety_fields" in materiality_command
    assert any(
        row["route_name"] == "nishishinjuku_lane_change"
        for row in report["runbook_manifest"]["rows"]
    )


def test_targeted_safety_support_tiny_runbook_rejects_source_not_ready() -> None:
    design = _design()
    design["final_decision"]["status"] = "targeted_safety_support_rejected"
    design["final_decision"]["passed"] = False
    design["final_decision"]["authorized_next_work"] = None

    report = build_report(design_report=design)

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "source_status" in decision["failed_checks"]
    assert "source_passed" in decision["failed_checks"]


def test_targeted_safety_support_tiny_runbook_rejects_formal_seed() -> None:
    design = copy.deepcopy(_design())
    design["design_contract"]["tiny_support_discovery"]["rows"][0]["seed"] = 11

    report = build_report(design_report=design)

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "no_formal_seeds" in decision["failed_checks"]
    assert decision["new_replay_authorized"] is False


def test_targeted_safety_support_tiny_runbook_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    design_path = tmp_path / "design.json"
    output_json = tmp_path / "runbook.json"
    output_md = tmp_path / "runbook.md"
    output_bash = tmp_path / "runbook.sh"
    design_path.write_text(json.dumps(_design()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted-safety-support-runbook",
            "--design_json",
            str(design_path),
            "--output_root",
            "/tmp/targeted_support",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Targeted Safety Support Tiny Runbook" in output_md.read_text(
        encoding="utf-8"
    )
    assert "targeted_safety_support_tiny_runbook_complete" in output_bash.read_text(
        encoding="utf-8"
    )
