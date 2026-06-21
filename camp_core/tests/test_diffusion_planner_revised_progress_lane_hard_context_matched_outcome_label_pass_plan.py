from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_broader_nonformal_smoke import (
    BroaderSmokeSpec,
    EvidenceRunSpec,
)
from scripts.integrations.plan_diffusion_planner_revised_progress_lane_hard_context_matched_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _tiny_contract(*, status: str = "revised_progress_lane_hard_context_atom_separability_missing_outcome_labels") -> dict:
    passed_status = (
        status
        == "revised_progress_lane_hard_context_atom_separability_missing_outcome_labels"
    )
    return {
        "final_decision": {
            "status": status,
            "passed": False,
            "authorized_next_work": (
                "revised_progress_lane_hard_context_matched_outcome_label_plan_only"
                if passed_status
                else None
            ),
        },
        "records": {
            "candidate_rows": 24,
            "missing_outcome_records": 3,
            "formal_seed_records": 0,
        },
        "payload_descriptor_coverage": {
            "revised_atom_route_progress_shortfall_vs_candidate_best_v1": {
                "finite": 24,
                "total": 24,
            },
            "revised_atom_route_progress_efficiency_shortfall_v1": {
                "finite": 24,
                "total": 24,
            },
        },
    }


def _source_smoke(*, passed: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "progress_lane_hard_context_logging_smoke_passed"
                if passed
                else "progress_lane_hard_context_logging_smoke_rejected"
            ),
            "passed": passed,
        }
    }


def _selector_equivalence(*, equivalent: bool = True) -> dict:
    return {"equivalent": equivalent}


def _dataset_audit(*, passed: bool = True) -> dict:
    return {"passed": passed}


def _ready_report(**kwargs) -> dict:
    return build_report(
        tiny_contract=kwargs.pop("tiny_contract", _tiny_contract()),
        source_smoke_audit=kwargs.pop("source_smoke", _source_smoke()),
        selector_equivalence=kwargs.pop(
            "selector_equivalence",
            _selector_equivalence(),
        ),
        dataset_audit=kwargs.pop("dataset_audit", _dataset_audit()),
        **kwargs,
    )


def test_revised_context_matched_outcome_plan_ready_for_exact_scope() -> None:
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
        if item["variant"] == "matched_revised_context_outcomes"
    ]
    assert len(baseline_commands) == 4
    assert len(matched_commands) == 4
    for command in baseline_commands:
        assert "--camp_progress_lane_hard_context_logging" not in command
        assert "--camp_collect_closed_loop_outcomes" not in command
    for command in matched_commands:
        assert "--camp_progress_lane_hard_context_logging" in command
        assert "--camp_collect_closed_loop_outcomes" in command

    revised_command = report["commands"]["revised_atom_separability_audit"]
    assert (
        "scripts/integrations/analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability.py"
        in revised_command
    )
    assert "--fail_on_formal_seeds" in revised_command
    dataset_command = report["commands"]["dataset_required_outcome_audit"]
    assert dataset_command[dataset_command.index("--closed_loop_outcome_policy") + 1] == "required"


def test_revised_context_matched_outcome_plan_rejects_wrong_tiny_contract() -> None:
    report = _ready_report(
        tiny_contract=_tiny_contract(
            status="revised_progress_lane_hard_context_atom_separability_promising_for_certificate_design"
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["tiny_revised_atom_contract_missing_outcomes"]


def test_revised_context_matched_outcome_plan_rejects_formal_seed() -> None:
    base = BroaderSmokeSpec()
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
        *base.runs[1:],
    )

    report = _ready_report(spec=replace(base, runs=runs))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["formal_seeds_excluded"]


def test_revised_context_matched_outcome_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tiny_path = tmp_path / "tiny.json"
    smoke_path = tmp_path / "smoke.json"
    selector_path = tmp_path / "selector.json"
    dataset_path = tmp_path / "dataset.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    tiny_path.write_text(json.dumps(_tiny_contract()), encoding="utf-8")
    smoke_path.write_text(json.dumps(_source_smoke()), encoding="utf-8")
    selector_path.write_text(json.dumps(_selector_equivalence()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset_audit()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_revised_progress_lane_hard_context_matched_outcome_label_pass.py",
            "--tiny_separability_contract_json",
            str(tiny_path),
            "--source_smoke_audit_json",
            str(smoke_path),
            "--selector_equivalence_json",
            str(selector_path),
            "--dataset_audit_json",
            str(dataset_path),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/revised_context_matched",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["plan_spec"]["root"] == "/tmp/revised_context_matched"
    markdown = output_md.read_text(encoding="utf-8")
    assert "--camp_progress_lane_hard_context_logging" in markdown
    assert "--camp_collect_closed_loop_outcomes" in markdown
    assert "revised_context_atom_separability" in markdown
