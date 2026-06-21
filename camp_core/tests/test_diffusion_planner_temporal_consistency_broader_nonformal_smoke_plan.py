from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_temporal_consistency_broader_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    BroaderSmokeSpec,
    EvidenceRunSpec,
    build_report,
    main,
    render_bash,
)


def _smoke_result(**decision_overrides: object) -> dict:
    decision = {
        "status": "temporal_consistency_payload_smoke_result_ready",
        "passed": True,
        "runtime_equivalence_ready": True,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "authorized_next_work": (
            "default_off_temporal_consistency_broader_nonformal_coverage_plan_only"
        ),
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "payload_summary": {
            "candidate_records": 3,
            "available_payload_records": 2,
            "first_tick_fail_closed_records": 1,
            "latency_max_ms": 0.08,
        },
        "materiality_summary": {
            "sufficient_for_broader_plan": True,
            "sufficient_for_atom_promotion": False,
            "sufficient_for_training": False,
        },
    }


def test_temporal_consistency_broader_plan_authorizes_predeclared_matrix() -> None:
    report = build_report(smoke_result=_smoke_result(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is True
    assert report["final_decision"]["full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["coverage_targets"]["planned_records"] == 50
    assert report["coverage_targets"]["planned_candidate_rows"] == 400
    assert report["coverage_targets"]["expected_available_payload_records_min_per_run"] == 9
    assert len(report["commands"]["replays"]) == 10
    assert len(report["commands"]["payload_audits"]) == 5

    baseline_commands = [
        item["command"]
        for item in report["commands"]["replays"]
        if item["variant"] == "baseline"
    ]
    candidate_commands = [
        item["command"]
        for item in report["commands"]["replays"]
        if item["variant"] == "logging_enabled"
    ]
    assert all(
        "--camp_temporal_consistency_payload_logging" not in command
        for command in baseline_commands
    )
    assert all(
        "--camp_temporal_consistency_payload_logging" in command
        for command in candidate_commands
    )
    assert any(
        "/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm" in command
        for command in candidate_commands
    )
    assert "--root" in report["commands"]["dataset_audit"]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_broader_plan_rejects_source_not_ready() -> None:
    report = build_report(
        smoke_result=_smoke_result(
            status="temporal_consistency_payload_smoke_result_rejected",
            passed=False,
            authorized_next_work=None,
        ),
        label="unit",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "source_result_status" in failed
    assert "source_result_passed" in failed


def test_temporal_consistency_broader_plan_rejects_formal_seed() -> None:
    spec = replace(
        BroaderSmokeSpec(),
        runs=(
            EvidenceRunSpec(
                run_id="formal_seed",
                map_name="sample_map",
                map_path=(
                    "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                    "sample-map-planning/lanelet2_map_no_ros.osm"
                ),
                route_name="sample_map_tl_route_59_to_86",
                route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
                seed=11,
                max_npcs=0,
                spawn_probability=0.3,
                traffic_lights="on",
                scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
            ),
        ),
    )
    report = build_report(smoke_result=_smoke_result(), spec=spec)

    assert report["final_decision"]["status"] != READY_STATUS
    check = next(
        item for item in report["plan_checks"] if item["name"] == "formal_seeds_excluded"
    )
    assert check["passed"] is False


def test_temporal_consistency_broader_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(
        smoke_result=_smoke_result(),
        payload_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    check = next(
        item
        for item in report["source_checks"]
        if item["name"] == "payload_audit_available"
    )
    assert check["passed"] is False


def test_temporal_consistency_broader_plan_renders_bash_runbook() -> None:
    report = build_report(smoke_result=_smoke_result(), label="unit")

    bash = render_bash(report)

    assert bash.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in bash
    assert "cd /root/autodl-tmp/camp_core" in bash
    assert "== asset_audit ==" in bash
    assert "== head_audit ==" in bash
    assert "nishi_lanechange_seed4_npc4_tloff" in bash
    assert "--camp_temporal_consistency_payload_logging" in bash
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in bash
    assert "Full36" in bash
    assert "temporal_consistency_broader_nonformal_smoke_complete" in bash


def test_temporal_consistency_broader_plan_cli_writes_bash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke_result = tmp_path / "smoke_result.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "run.sh"
    smoke_result.write_text(json.dumps(_smoke_result()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-broader-plan",
            "--smoke_result_json",
            str(smoke_result),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/temporal_broader",
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
    assert "Temporal Consistency Broader Nonformal Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "temporal_consistency_broader_nonformal_smoke_complete" in (
        output_bash.read_text(encoding="utf-8")
    )
