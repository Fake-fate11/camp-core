from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_joint_cologged_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK,
    JointCologgedSpec,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.plan_diffusion_planner_progress_support_broader_nonformal_smoke import (
    EvidenceRunSpec,
)


def _joint_preflight(*, status: str = "progress_lane_hard_joint_screen_preflight_ready") -> dict:
    return {
        "analysis": {
            "next_gate_accept_criteria": {
                "requires_same_record_cologged_progress_and_lane_hard_payloads": True,
                "formal_seed_records": 0,
                "selector_effect": False,
            }
        },
        "complementarity_evidence": {
            "complementary_blind_spots_established": True,
            "primary_gap": "complementary_blind_spots_established",
        },
        "final_decision": {
            "status": status,
            "passed": status == "progress_lane_hard_joint_screen_preflight_ready",
            "authorized_next_work": "progress_lane_hard_joint_cologged_outcome_plan_only",
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "dp_modification_authorized": False,
            "formal_seeds_authorized": False,
        },
    }


def _ready_report(**kwargs) -> dict:
    return build_report(
        joint_preflight_report=kwargs.pop("joint_preflight", _joint_preflight()),
        **kwargs,
    )


def test_joint_cologged_plan_ready_for_exact_scope() -> None:
    report = _ready_report(label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["paired_smoke_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["Full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    assert decision["DP_modification_authorized"] is False
    assert report["analysis"]["future_outcome_leakage"] is False
    assert report["analysis"]["same_record_cologging_required"] is True
    assert report["coverage_targets"]["matched_records"] == 48
    assert report["coverage_targets"]["matched_candidate_rows"] == 384
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])

    replay_commands = report["commands"]["paired_replays"]
    baseline_commands = [
        item["command"] for item in replay_commands if item["variant"] == "baseline"
    ]
    matched_commands = [
        item["command"]
        for item in replay_commands
        if item["variant"] == "matched_progress_lane_hard_joint_outcomes"
    ]
    assert len(baseline_commands) == 4
    assert len(matched_commands) == 4
    for command in baseline_commands:
        assert "--camp_progress_support_logging" not in command
        assert "--camp_lane_hard_violation_support_logging" not in command
        assert "--camp_collect_closed_loop_outcomes" not in command
    for command in matched_commands:
        assert "--camp_progress_support_logging" in command
        assert "--camp_lane_hard_violation_support_logging" in command
        assert "--camp_collect_closed_loop_outcomes" in command

    dataset_command = report["commands"]["dataset_required_outcome_audit"]
    assert "--closed_loop_outcome_policy" in dataset_command
    assert dataset_command[dataset_command.index("--closed_loop_outcome_policy") + 1] == "required"
    assert "--forbid_seed" in dataset_command

    progress_contract = report["commands"]["matched_progress_contract_audit"]
    lane_contract = report["commands"]["matched_lane_hard_contract_audit"]
    assert "--require_pass" in progress_contract
    assert "--require_pass" in lane_contract
    assert progress_contract[progress_contract.index("--expected_records") + 1] == "12"
    assert lane_contract[lane_contract.index("--expected_records") + 1] == "12"


def test_joint_cologged_plan_rejects_source_not_ready() -> None:
    report = _ready_report(
        joint_preflight=_joint_preflight(
            status="progress_lane_hard_joint_screen_preflight_rejected"
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["joint_preflight_ready"]


def test_joint_cologged_plan_rejects_missing_complementarity() -> None:
    source = _joint_preflight()
    source["complementarity_evidence"]["complementary_blind_spots_established"] = False

    report = _ready_report(joint_preflight=source)

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["complementary_blind_spots_established"]


def test_joint_cologged_plan_rejects_formal_seed() -> None:
    spec = JointCologgedSpec()
    runs = (
        EvidenceRunSpec(
            run_id="formal_seed",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=11,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        *spec.runs[1:],
    )

    report = _ready_report(spec=replace(spec, runs=runs))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["formal_seeds_excluded"]


def test_joint_cologged_plan_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "joint_preflight.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_path.write_text(json.dumps(_joint_preflight()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_progress_lane_hard_joint_cologged_outcome_label_pass.py",
            "--joint_preflight_json",
            str(source_path),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/joint_cologged",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["plan_spec"]["root"] == "/tmp/joint_cologged"
    markdown = output_md.read_text(encoding="utf-8")
    assert "--camp_progress_support_logging" in markdown
    assert "--camp_lane_hard_violation_support_logging" in markdown
    assert "--camp_collect_closed_loop_outcomes" in markdown
