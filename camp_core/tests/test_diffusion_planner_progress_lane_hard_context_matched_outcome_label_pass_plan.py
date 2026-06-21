from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_broader_nonformal_smoke import (
    BroaderSmokeSpec,
    EvidenceRunSpec,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_matched_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _source_smoke(*, passed: bool = True, logging_ms: float = 5.4) -> dict:
    return {
        "final_decision": {
            "status": (
                "progress_lane_hard_context_logging_smoke_passed"
                if passed
                else "progress_lane_hard_context_logging_smoke_rejected"
            ),
            "passed": passed,
        },
        "counts": {"records": 48, "candidate_payload_records": 48},
        "latency_ms": {
            "latency_ms_progress_lane_hard_context_logging": logging_ms,
        },
    }


def _coverage_audit(
    *,
    status: str = (
        "progress_lane_hard_context_payload_coverage_ready_for_offline_separability_design"
    ),
    materiality_gate_passed: bool = True,
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "validation_passed": status
            == "progress_lane_hard_context_payload_coverage_ready_for_offline_separability_design",
            "materiality_gate_passed": materiality_gate_passed,
        },
        "counts": {
            "records": 48,
            "payload_records": 48,
            "candidate_rows": 384,
        },
        "context": {"context_records": 48},
        "material_atom_fields": [
            "curvature_conditioned_lateral_rate_excess_v1",
            "heading_curvature_residual_v1",
            "lane_progress_coherence_excess_v1",
        ],
        "validation": {"errors": [], "warnings": []},
    }


def _selector_equivalence(*, equivalent: bool = True, mismatches: int = 0) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {"selected_index": mismatches},
        "numeric_field_mismatches": {"atoms": 0},
        "numeric_shape_mismatches": {"atoms": 0},
        "numeric_nonexact_entries": {"atoms": 0},
    }


def _dataset_audit(*, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "checks": {
            "forbidden_seed_check": True,
            "closed_loop_outcomes_forbidden": True,
        },
    }


def _ready_report(**kwargs) -> dict:
    return build_report(
        broader_smoke_audit=kwargs.pop("source_smoke", _source_smoke()),
        broader_selector_equivalence=kwargs.pop(
            "selector_equivalence",
            _selector_equivalence(),
        ),
        broader_dataset_audit=kwargs.pop("dataset_audit", _dataset_audit()),
        broader_coverage_audit=kwargs.pop("coverage_audit", _coverage_audit()),
        **kwargs,
    )


def test_context_matched_outcome_plan_ready_for_exact_scope() -> None:
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
        if item["variant"] == "matched_progress_lane_hard_context_outcomes"
    ]
    assert len(baseline_commands) == 4
    assert len(matched_commands) == 4
    for command in baseline_commands:
        assert "--camp_progress_lane_hard_context_logging" not in command
        assert "--camp_collect_closed_loop_outcomes" not in command
    for command in matched_commands:
        assert "--camp_progress_lane_hard_context_logging" in command
        assert "--camp_collect_closed_loop_outcomes" in command

    dataset_command = report["commands"]["dataset_required_outcome_audit"]
    assert dataset_command[dataset_command.index("--closed_loop_outcome_policy") + 1] == "required"
    assert "--forbid_seed" in dataset_command

    contract_command = report["commands"]["matched_context_contract_audit"]
    assert "--require_pass" in contract_command
    assert contract_command[contract_command.index("--expected_records") + 1] == "12"


def test_context_matched_outcome_plan_rejects_coverage_not_ready() -> None:
    report = _ready_report(
        coverage_audit=_coverage_audit(
            status="progress_lane_hard_context_payload_coverage_insufficient_for_materiality",
            materiality_gate_passed=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["broader_context_coverage_ready"]


def test_context_matched_outcome_plan_rejects_missing_contract_source(
    tmp_path: Path,
) -> None:
    report = _ready_report(
        matched_context_contract_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "matched_context_contract_audit_available" in failed


def test_context_matched_outcome_plan_rejects_formal_seed() -> None:
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


def test_context_matched_outcome_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke_path = tmp_path / "smoke.json"
    selector_path = tmp_path / "selector.json"
    dataset_path = tmp_path / "dataset.json"
    coverage_path = tmp_path / "coverage.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    smoke_path.write_text(json.dumps(_source_smoke()), encoding="utf-8")
    selector_path.write_text(json.dumps(_selector_equivalence()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset_audit()), encoding="utf-8")
    coverage_path.write_text(json.dumps(_coverage_audit()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_progress_lane_hard_context_matched_outcome_label_pass.py",
            "--broader_smoke_audit_json",
            str(smoke_path),
            "--broader_selector_equivalence_json",
            str(selector_path),
            "--broader_dataset_audit_json",
            str(dataset_path),
            "--broader_coverage_audit_json",
            str(coverage_path),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/context_matched",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["plan_spec"]["root"] == "/tmp/context_matched"
    markdown = output_md.read_text(encoding="utf-8")
    assert "--camp_progress_lane_hard_context_logging" in markdown
    assert "--camp_collect_closed_loop_outcomes" in markdown
