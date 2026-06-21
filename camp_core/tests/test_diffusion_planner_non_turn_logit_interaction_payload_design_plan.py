from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_payload_design import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    PayloadFieldPlan,
    build_report,
    main,
)


def _preflight_report(*, ready: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "non_turn_logit_interaction_atom_preflight_promising_for_payload_design"
                if ready
                else "non_turn_logit_interaction_atom_preflight_rejected"
            ),
            "passed": ready,
            "authorized_next_work": (
                "non_turn_logit_interaction_atom_payload_design_plan_only"
                if ready
                else None
            ),
            "promising_screen_count": 2 if ready else 0,
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
        },
        "records": {
            "formal_seed_records": 0,
            "missing_feature_records": 0,
            "alternative_rows": 14,
            "class_counts": {
                "beneficial_alternative": 3,
                "harmful_alternative": 4,
                "neutral_alternative": 7,
            },
        },
        "ranked_screens": [
            {
                "screen_name": (
                    "affine_simplex:0.750*route_progress_deficit_vs_top1_m+"
                    "0.250*dp_prior_jerk_excess_cost"
                ),
                "descriptor_names": [
                    "route_progress_deficit_vs_top1_m",
                    "dp_prior_jerk_excess_cost",
                ],
                "promising_screen": True,
            },
            {
                "screen_name": (
                    "affine_simplex:0.500*route_progress_deficit_vs_top1_m+"
                    "0.250*dp_prior_jerk_excess_cost+"
                    "0.250*comfort_progress_interaction_cost"
                ),
                "descriptor_names": [
                    "route_progress_deficit_vs_top1_m",
                    "dp_prior_jerk_excess_cost",
                    "comfort_progress_interaction_cost",
                ],
                "promising_screen": True,
            },
        ],
    }


def test_payload_design_plan_authorizes_only_default_off_payload() -> None:
    report = build_report(preflight_report=_preflight_report(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["payload_implementation_authorized"] is True
    assert decision["schema_promotion_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    fields = {field["name"]: field for field in report["selected_payload_fields"]}
    assert fields["route_progress_deficit_vs_top1_m"]["add_as_new_atom_candidate"] is False
    assert fields["dp_prior_jerk_excess_cost"]["add_as_new_atom_candidate"] is False
    assert fields["comfort_progress_interaction_cost"]["add_as_new_atom_candidate"] is True
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["overlap_checks"])
    assert all(check["passed"] for check in report["design_checks"])


def test_payload_design_plan_rejects_failed_source() -> None:
    report = build_report(preflight_report=_preflight_report(ready=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "source_preflight_promising" in failed


def test_payload_design_plan_rejects_exact_duplicate_new_atom() -> None:
    duplicate_new = (
        PayloadFieldPlan(
            name="dp_prior_jerk_excess_cost",
            expression="max(candidate_dp_prior_jerk_excess_cost[k], 0)",
            source_fields=("candidate_dp_prior_jerk_excess_cost",),
            role="new_atom_candidate",
            add_as_new_atom_candidate=True,
            duplicate_status="exact_existing_dp_camp_v10_atom",
            rationale="bad duplicate",
        ),
    )

    report = build_report(
        preflight_report=_preflight_report(),
        payload_fields=duplicate_new,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["overlap_checks"] if not check["passed"]]
    assert "new_atom_candidates_not_existing_schema_duplicates" in failed


def test_payload_design_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "preflight.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source.write_text(json.dumps(_preflight_report()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_non_turn_logit_interaction_payload_design.py",
            "--preflight_json",
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
    assert payload["final_decision"]["status"] == READY_STATUS
    markdown = output_md.read_text(encoding="utf-8")
    assert "comfort_progress_interaction_cost" in markdown
    assert "schema promotion authorized: `False`" in markdown
