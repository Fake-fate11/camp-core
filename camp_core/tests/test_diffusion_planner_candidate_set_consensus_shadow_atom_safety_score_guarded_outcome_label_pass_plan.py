from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK,
    GUARD_ENV_ASSIGNMENT,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_bash,
    render_markdown,
)


RUN_IDS = (
    "sample_tl59_seed1_npc0_tlon",
    "sample_tl59_seed2_npc4_tlon",
    "sample_tl59_seed3_npc4_tloff",
    "sample_normal2_seed1_npc0_tloff",
    "nishi_release_seed2_npc4_tlon",
    "nishi_lanechange_seed4_npc4_tloff",
)


def _source_search(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "outcome_label_existing_source_search_no_compatible_source"
        ),
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "guarded_outcome_label_pass_consideration_plan_only"
        ),
        "compatible_source_found": False,
        "guarded_outcome_label_pass_consideration_plan_authorized": True,
        "outcome_label_generation_authorized": False,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "source_summary": {
            "route_seed_matrix": [
                {"run_id": run_id, "seed": seed}
                for run_id, seed in zip(RUN_IDS, (1, 2, 3, 1, 2, 4))
            ],
        },
        "expected_scope": {
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "run_ids": sorted(RUN_IDS),
        },
        "search_summary": {
            "complete_outcome_log_count": 0,
            "formal_seed_log_count": 0,
        },
    }


def test_guarded_outcome_label_pass_plan_is_ready_and_plan_only() -> None:
    report = build_report(source_search=_source_search(), label="unit_plan")
    decision = report["final_decision"]
    plan = report["guarded_outcome_label_pass_plan"]
    runbook = render_bash(report)

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["outcome_label_pass_execution_authorized"] is False
    assert decision["outcome_label_generation_authorized"] is False
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT
    assert plan["expected_logs"] == 6
    assert plan["expected_records"] == 60
    assert len(plan["route_seed_matrix"]) == 6
    assert "traffic_light" in plan["scenario_coverage"]
    assert "normal" in plan["scenario_coverage"]
    assert "--camp_collect_closed_loop_outcomes" in runbook
    assert GUARD_ENV_ASSIGNMENT.split("=")[0] in runbook


def test_guarded_outcome_label_pass_plan_rejects_compatible_source() -> None:
    report = build_report(
        source_search=_source_search(
            status=(
                "candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_existing_source_search_ready"
            ),
            authorized_next_work=(
                "candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_source_review_only"
            ),
            compatible_source_found=True,
            guarded_outcome_label_pass_consideration_plan_authorized=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_guarded_outcome_label_pass_plan_rejects_source_label_generation() -> None:
    report = build_report(
        source_search=_source_search(outcome_label_generation_authorized=True)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_plan_rejects_formal_source_seed() -> None:
    source = _source_search()
    source["source_summary"]["route_seed_matrix"][0]["seed"] = 11

    report = build_report(source_search=source)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_route_seeds_nonformal" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_plan_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(source_search=_source_search()))

    assert "Guarded Outcome-Label Pass Consideration Plan" in markdown
    assert "Outcome-label pass execution authorized: `False`" in markdown
    assert "Outcome-label generation authorized now: `False`" in markdown
    assert "classical Benders" in markdown
    assert "candidate_index 0..7" in markdown


def test_guarded_outcome_label_pass_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "source_search.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "runbook.sh"
    source_json.write_text(json.dumps(_source_search()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-guarded-outcome-label-pass-plan",
            "--source_search_json",
            str(source_json),
            "--label_output_root",
            "/out/outcome_labels",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Outcome-Label Pass Consideration Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "--camp_collect_closed_loop_outcomes" in output_bash.read_text(
        encoding="utf-8"
    )
