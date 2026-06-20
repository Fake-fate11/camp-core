from __future__ import annotations

import json
from dataclasses import replace

from scripts.integrations.plan_diffusion_planner_matched_observable_outcome_label_pass import (
    MatchedPlanSpec,
    MatchedRunSpec,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def test_matched_plan_authorizes_small_nonformal_scope() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["analysis"]["future_outcome_leakage"] is False
    assert report["coverage_targets"]["matched_records"] == 48
    assert report["coverage_targets"]["matched_candidate_rows"] == 384

    replay_commands = report["commands"]["paired_replays"]
    baseline_commands = [
        item["command"] for item in replay_commands if item["variant"] == "baseline"
    ]
    matched_commands = [
        item["command"]
        for item in replay_commands
        if item["variant"] == "matched_observable_outcomes"
    ]
    assert len(baseline_commands) == 4
    assert len(matched_commands) == 4
    assert all("--camp_observable_state_logging" not in command for command in baseline_commands)
    assert all("--camp_collect_closed_loop_outcomes" not in command for command in baseline_commands)
    assert all("--camp_observable_state_logging" in command for command in matched_commands)
    assert all("--camp_collect_closed_loop_outcomes" in command for command in matched_commands)
    assert all("--camp_outcome_horizon_steps" in command for command in matched_commands)

    dataset_command = report["commands"]["dataset_required_outcome_audit"]
    assert "--closed_loop_outcome_policy" in dataset_command
    assert dataset_command[dataset_command.index("--closed_loop_outcome_policy") + 1] == "required"
    assert "--forbid_seed" in dataset_command

    contract_command = report["commands"]["matched_contract_audit"]
    assert "--require_pass" in contract_command
    assert "--expected_records" in contract_command
    assert contract_command[contract_command.index("--expected_records") + 1] == "12"


def test_matched_plan_rejects_formal_seed() -> None:
    base = MatchedPlanSpec()
    spec = replace(
        base,
        runs=(
            MatchedRunSpec(
                run_id="formal_seed",
                route_name="sample_map_tl_route_59_to_86",
                route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
                seed=11,
                max_npcs=0,
                spawn_probability=0.3,
                traffic_lights="on",
                scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
            ),
            *base.runs[1:],
        ),
    )

    report = build_report(spec=spec)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["passed"] is False
    formal_check = next(
        check for check in report["plan_checks"] if check["name"] == "formal_seeds_excluded"
    )
    assert formal_check["passed"] is False


def test_matched_plan_rejects_missing_contract_audit(tmp_path) -> None:
    report = build_report(matched_contract_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["matched_contract_audit_available"]


def test_matched_plan_cli_writes_outputs(tmp_path, monkeypatch) -> None:
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_matched_observable_outcome_label_pass.py",
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/matched",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["plan_spec"]["root"] == "/tmp/matched"
    markdown = output_md.read_text(encoding="utf-8")
    assert "--camp_observable_state_logging" in markdown
    assert "--camp_collect_closed_loop_outcomes" in markdown
