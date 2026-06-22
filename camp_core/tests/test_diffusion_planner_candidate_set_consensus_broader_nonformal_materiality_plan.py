from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    BroaderMaterialitySpec,
    EvidenceRunSpec,
    build_report,
    main,
    render_bash,
    render_markdown,
)


def _tiny_materiality(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_tiny_materiality_diagnosis_ready",
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_broader_nonformal_materiality_plan_only"
        ),
        "signal_present": True,
        "materiality_gate_passed": False,
        "sample_too_small_for_promotion": True,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "record_summary": {
            "records": 3,
            "available_records": 3,
            "valid_records": 3,
            "positive_spread_records": 3,
            "selected_not_consensus_best_records": 3,
            "finite_lambda_records": 3,
            "selected_rank_mean": 6.0,
            "selected_rank_max": 7.0,
            "min_lambda_to_change_any_record": 0.20212395639810232,
        },
    }


def test_candidate_set_consensus_broader_materiality_plan_ready_but_plan_only() -> None:
    report = build_report(tiny_materiality=_tiny_materiality(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["plan_only"] is True
    assert decision["plan_artifact_ready"] is True
    assert decision["broader_replay_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["coverage_targets"]["planned_logs"] == 6
    assert report["coverage_targets"]["planned_records"] == 60
    assert report["coverage_targets"]["planned_candidate_rows"] == 480
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert "DP Top-1" in " ".join(report["safety_score_evaluation_boundary"]["forbidden"])

    replay_commands = report["commands"]["paired_replays"]
    assert len(replay_commands) == 12
    baseline_commands = [
        item["command"] for item in replay_commands if item["variant"] == "baseline"
    ]
    candidate_commands = [
        item["command"]
        for item in replay_commands
        if item["variant"] == "logging_enabled"
    ]
    assert all(
        "--camp_candidate_set_consensus_payload_logging" not in command
        for command in baseline_commands
    )
    assert all(
        "--camp_candidate_set_consensus_payload_logging" in command
        for command in candidate_commands
    )
    assert {
        command[command.index("--traffic_lights") + 1]
        for command in candidate_commands
    } == {"on", "off"}
    assert {
        command[command.index("--seed") + 1] for command in candidate_commands
    } == {"1", "2", "3", "4"}
    assert any(
        "/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl"
        in command
        for command in candidate_commands
    )
    assert any(
        "/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
        in command
        for command in candidate_commands
    )

    payload_audit = report["commands"]["payload_audit"]
    assert payload_audit[payload_audit.index("--expected_logs") + 1] == "6"
    assert payload_audit[payload_audit.index("--expected_records") + 1] == "10"
    assert payload_audit[payload_audit.index("--min_available_records") + 1] == "60"
    assert "--require_pass" in payload_audit

    dataset_audit = report["commands"]["dataset_audit"]
    assert "--root" in dataset_audit
    assert "--closed_loop_outcome_policy" in dataset_audit
    assert dataset_audit[dataset_audit.index("--expected_logs") + 1] == "6"


def test_candidate_set_consensus_broader_materiality_plan_rejects_bad_source() -> None:
    report = build_report(
        tiny_materiality=_tiny_materiality(
            status="candidate_set_consensus_tiny_materiality_diagnosis_rejected",
            passed=False,
            authorized_next_work=None,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["new_replay_authorized"] is False
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "source_tiny_materiality_status" in failed
    assert "source_tiny_materiality_passed" in failed
    assert "source_authorizes_broader_plan" in failed


def test_candidate_set_consensus_broader_materiality_plan_rejects_formal_seed() -> None:
    base = BroaderMaterialitySpec()
    runs = (
        replace(base.runs[0], run_id="formal_seed", seed=11),
        *base.runs[1:],
    )

    report = build_report(
        tiny_materiality=_tiny_materiality(),
        spec=replace(base, runs=runs),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["formal_seeds_excluded"]


def test_candidate_set_consensus_broader_materiality_plan_rejects_missing_nishi() -> None:
    base = BroaderMaterialitySpec()
    replacement = EvidenceRunSpec(
        run_id="sample_extra_seed4_npc4_tloff",
        map_name="sample_map",
        map_path=base.runs[0].map_path,
        route_name="sample_map_tl_route_59_to_86",
        route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
        seed=4,
        max_npcs=4,
        spawn_probability=0.3,
        traffic_lights="off",
        scenario_buckets=("sharp_turn", "npc_interaction"),
    )
    runs = (*base.runs[:4], replacement, replacement)

    report = build_report(
        tiny_materiality=_tiny_materiality(),
        spec=replace(base, runs=runs),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == [
        "sample_and_nishishinjuku_maps_covered",
        "required_routes_covered",
        "scenario_buckets_cover_required_contexts",
    ]


def test_candidate_set_consensus_broader_materiality_plan_runbook_is_guarded() -> None:
    report = build_report(tiny_materiality=_tiny_materiality(), label="unit")

    bash = render_bash(report)

    assert bash.startswith("#!/usr/bin/env bash")
    assert "CANDIDATE_SET_CONSENSUS_BROADER_MATERIALITY_REPLAY_APPROVED" in bash
    assert "plan-only runbook: replay is not authorized in this gate" in bash
    assert "cd /root/autodl-tmp/camp_core" in bash
    assert "== camp_sync ==" in bash
    assert "== asset_audit ==" in bash
    assert "== head_audit ==" in bash
    assert "nishi_lanechange_seed4_npc4_tloff" in bash
    assert "--camp_candidate_set_consensus_payload_logging" in bash
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in bash
    assert "Full36" in bash


def test_candidate_set_consensus_broader_materiality_markdown_includes_boundaries() -> None:
    report = build_report(tiny_materiality=_tiny_materiality(), label="unit")

    markdown = render_markdown(report)

    assert "Candidate-Set Consensus Broader Nonformal Materiality Plan" in markdown
    assert "broader replay authorized now: `False`" in markdown
    assert "sample_tl59_seed1_npc0_tlon" in markdown
    assert "nishi_release_seed2_npc4_tlon" in markdown
    assert "Safety-Score Boundary" in markdown
    assert "Artifact Recording" in markdown


def test_candidate_set_consensus_broader_materiality_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tiny = tmp_path / "tiny_materiality.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "run.sh"
    tiny.write_text(json.dumps(_tiny_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-broader-materiality-plan",
            "--tiny_materiality_json",
            str(tiny),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/candidate_set_consensus_broader",
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
    assert payload["plan_spec"]["root"] == "/tmp/candidate_set_consensus_broader"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["new_replay_authorized"] is False
    assert "Candidate-Set Consensus Broader Nonformal Materiality Plan" in (
        output_md.read_text(encoding="utf-8")
    )
    assert "CANDIDATE_SET_CONSENSUS_BROADER_MATERIALITY_REPLAY_APPROVED" in (
        output_bash.read_text(encoding="utf-8")
    )
