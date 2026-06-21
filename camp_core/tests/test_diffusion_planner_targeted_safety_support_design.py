from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_targeted_safety_support_design import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
)


def _materiality(**decision_overrides: object) -> dict:
    decision = {
        "status": "alternative_safety_source_materiality_ready",
        "passed": True,
        "authorized_next_work": "targeted_safety_support_scenario_or_source_design_only",
        "has_actionable_existing_safety_source": False,
        "has_material_safety_source": True,
        "actionable_existing_safety_sources": [],
        "material_but_current_selection_already_best": [
            "h30_union_planned_red_light_cost",
            "h80_full_planned_red_light_cost",
            "red_stopping_margin_cost",
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
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "materiality_summary": {
            "by_source": [
                {
                    "name": "h30_union_planned_red_light_cost",
                    "nonzero_range_records": 2,
                    "selected_not_best_records": 0,
                }
            ]
        },
    }


def test_targeted_safety_support_design_accepts_valid_source() -> None:
    report = build_report(materiality_report=_materiality(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["tiny_support_row_count"] == 5
    assert decision["candidate_source_family_count"] == 3
    assert decision["new_replay_authorized"] is False
    assert report["analysis"]["label"] == "unit"
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    seeds = [
        row["seed"]
        for row in report["design_contract"]["tiny_support_discovery"]["rows"]
    ]
    assert not ({11, 12, 13} & set(seeds))


def test_targeted_safety_support_design_rejects_actionable_existing_source() -> None:
    report = build_report(
        materiality_report=_materiality(
            has_actionable_existing_safety_source=True,
            actionable_existing_safety_sources=["h30_union_planned_red_light_cost"],
            authorized_next_work=(
                "predeclare_no_leak_atom_schema_from_existing_safety_source_only"
            ),
        )
    )

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "source_authorizes_targeted_support_design" in decision["failed_checks"]
    assert "source_has_no_actionable_existing_safety_source" in (
        decision["failed_checks"]
    )


def test_targeted_safety_support_design_rejects_source_without_materiality() -> None:
    report = build_report(
        materiality_report=_materiality(has_material_safety_source=False)
    )

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "source_has_material_safety_source" in decision["failed_checks"]


def test_targeted_safety_support_design_rejects_source_not_ready() -> None:
    report = build_report(
        materiality_report=_materiality(
            status="alternative_safety_source_materiality_rejected",
            passed=False,
            authorized_next_work=None,
        )
    )

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "source_status" in decision["failed_checks"]
    assert "source_passed" in decision["failed_checks"]


def test_targeted_safety_support_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "materiality.json"
    output_json = tmp_path / "design.json"
    output_md = tmp_path / "design.md"
    source.write_text(json.dumps(_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted-safety-support-design",
            "--materiality_json",
            str(source),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Targeted Safety Support Design" in output_md.read_text(
        encoding="utf-8"
    )
