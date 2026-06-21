from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_targeted_candidate_oracle_input_readiness import (
    AUTHORIZED_NEXT_WORK,
    INCOMPLETE_STATUS,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    build_report,
    main,
    render_markdown,
)


def _manifest(*, passed: bool = True, planned: int = 108) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_targeted_safety_scenario_manifest_gate_v1"},
        "matrix_source": {
            "planned_run_count": planned,
            "target_missing_buckets": [],
            "guard_missing_buckets": [],
            "formal_seeds": [],
        },
        "final_decision": {
            "status": (
                "targeted_safety_intervention_scenario_manifest_predeclared"
                if passed
                else "targeted_safety_intervention_scenario_manifest_incomplete"
            ),
            "passed": passed,
            "authorized_next_work": (
                "targeted_candidate_branch_oracle_input_readiness_gate"
                if passed
                else None
            ),
            "training_execution_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _readiness(
    *,
    logs: int = 108,
    outcomes: bool = True,
    proxies: bool = True,
    missing: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    oracle_ready = outcomes and proxies
    return {
        "analysis": {
            "name": "dp_camp_candidate_availability_input_readiness_v1"
        },
        "records": {
            "logs": logs,
            "records": logs * 200,
            "nonfallback_records": logs * 190,
            "fallback_records": logs * 10,
        },
        "missing_examples": missing or {},
        "readiness": {
            "candidate_availability_oracle_ready": oracle_ready,
            "outcome_labels_ready": outcomes,
            "current_tick_proxy_inputs_ready": proxies,
            "next_step": (
                "run_outcome_labeled_candidate_availability_oracle"
                if oracle_ready
                else "repair_selection_log_schema_before_candidate_availability_oracle"
            ),
        },
    }


def test_targeted_oracle_input_readiness_authorizes_oracle_only() -> None:
    report = build_report(
        targeted_manifest_gate=_manifest(),
        candidate_readiness=_readiness(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["recommended_first_action"] == "targeted_safety_cost_oracle_audit"
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["candidate_readiness_source"]["log_count_matches_plan"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_targeted_oracle_input_readiness_blocks_missing_outcomes() -> None:
    report = build_report(
        targeted_manifest_gate=_manifest(),
        candidate_readiness=_readiness(outcomes=False),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert "candidate_closed_loop_outcomes_incomplete" in report["final_decision"][
        "reasons"
    ]
    assert report["final_decision"]["authorized_next_work"] is None


def test_targeted_oracle_input_readiness_blocks_log_count_mismatch() -> None:
    report = build_report(
        targeted_manifest_gate=_manifest(planned=108),
        candidate_readiness=_readiness(logs=36),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert "readiness_log_count_does_not_match_manifest_plan" in report[
        "final_decision"
    ]["reasons"]


def test_targeted_oracle_input_readiness_blocks_missing_proxy_examples() -> None:
    report = build_report(
        targeted_manifest_gate=_manifest(),
        candidate_readiness=_readiness(
            proxies=False,
            missing={"proxy_jerk": ["/tmp/log#0"]},
        ),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert "current_tick_proxy_inputs_incomplete" in report["final_decision"][
        "reasons"
    ]
    assert "readiness_audit_has_missing_examples" in report["final_decision"][
        "reasons"
    ]


def test_targeted_oracle_input_readiness_blocks_source_not_ready() -> None:
    report = build_report(
        targeted_manifest_gate=_manifest(passed=False),
        candidate_readiness=_readiness(),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["targeted_manifest_source"]["passed"] is False


def test_targeted_oracle_input_readiness_markdown_states_boundary() -> None:
    report = build_report(targeted_manifest_gate=_manifest(), candidate_readiness=_readiness())
    markdown = render_markdown(report)

    assert "Targeted Candidate Oracle Input Readiness" in markdown
    assert "does not run DP" in markdown
    assert "classical Benders" in markdown


def test_targeted_oracle_input_readiness_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_path = tmp_path / "manifest_gate.json"
    readiness_path = tmp_path / "readiness.json"
    output_json = tmp_path / "targeted_readiness.json"
    output_md = tmp_path / "targeted_readiness.md"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    readiness_path.write_text(json.dumps(_readiness()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted_candidate_readiness",
            "--targeted_manifest_gate_json",
            str(manifest_path),
            "--candidate_readiness_json",
            str(readiness_path),
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
    assert "Targeted Candidate Oracle" in output_md.read_text(encoding="utf-8")
