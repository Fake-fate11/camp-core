from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_missing_candidate_state_broader_coverage import (
    AUTHORIZED_NEXT_WORK,
    DEFAULT_ROOT,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.plan_diffusion_planner_observable_state_logging_coverage import (
    CoveragePlanSpec,
    EvidenceRunSpec,
)


def _selector(*, equivalent: bool = True) -> dict[str, object]:
    return {
        "equivalent": equivalent,
        "records": 3,
        "exact_field_mismatches": {"selected_index": 0, "feasible_mask": 0},
        "numeric_field_mismatches": {"scores": 0, "atoms": 0},
    }


def _payload(*, passed: bool = True) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "observable_state_logging_smoke_passed"
                if passed
                else "observable_state_logging_smoke_rejected"
            ),
            "passed": passed,
        },
        "counts": {
            "baseline_payload_records": 0,
            "candidate_payload_records": 3,
            "paired_logs": 1,
            "records": 3,
        },
        "errors": [] if passed else ["payload_error"],
    }


def _dataset(*, passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "counts": {"records": 3, "candidates": 24, "logs": 1},
        "checks": {
            "closed_loop_outcomes_forbidden": True,
            "forbidden_seed_check": True,
            "finite_candidate_contract_verified": True,
        },
    }


def _summary(*, enabled: bool, records: int) -> dict[str, object]:
    return {
        "camp_observable_state_logging": {
            "enabled": enabled,
            "records": records,
            "future_outcome_leakage": False,
            "selection_effect": False,
        }
    }


def test_missing_candidate_state_broader_coverage_plan_ready() -> None:
    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is True
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["base_coverage_plan"]["final_decision"]["passed"] is True

    replay_commands = report["commands"]["paired_replays"]
    assert len(replay_commands) == 8
    assert all(
        any(DEFAULT_ROOT in part for part in item["command"])
        for item in replay_commands
    )
    candidate_commands = [
        item["command"]
        for item in replay_commands
        if item["variant"] == "logging_enabled"
    ]
    assert all("--camp_observable_state_logging" in command for command in candidate_commands)


def test_missing_candidate_state_broader_coverage_plan_blocks_failed_tiny_smoke() -> None:
    report = build_report(
        selector_equivalence=_selector(equivalent=False),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    failed = [
        check["name"]
        for check in report["source_tiny_smoke_checks"]
        if not check["passed"]
    ]
    assert failed == ["tiny_selector_equivalent"]


def test_missing_candidate_state_broader_coverage_plan_blocks_formal_seed() -> None:
    base = CoveragePlanSpec()
    spec = replace(
        base,
        runs=(
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
        ),
    )

    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
        spec=spec,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["base_coverage_plan"]["final_decision"]["status"] == (
        "observable_state_logging_broader_nonformal_plan_rejected"
    )


def test_missing_candidate_state_broader_coverage_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selector_path = tmp_path / "selector.json"
    payload_path = tmp_path / "payload.json"
    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline_summary.json"
    candidate_path = tmp_path / "candidate_summary.json"
    output_json = tmp_path / "broader_plan.json"
    output_md = tmp_path / "broader_plan.md"
    selector_path.write_text(json.dumps(_selector()), encoding="utf-8")
    payload_path.write_text(json.dumps(_payload()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset()), encoding="utf-8")
    baseline_path.write_text(json.dumps(_summary(enabled=False, records=0)), encoding="utf-8")
    candidate_path.write_text(json.dumps(_summary(enabled=True, records=3)), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "broader_coverage_plan",
            "--selector_equivalence_json",
            str(selector_path),
            "--payload_smoke_json",
            str(payload_path),
            "--dataset_audit_json",
            str(dataset_path),
            "--baseline_summary_json",
            str(baseline_path),
            "--candidate_summary_json",
            str(candidate_path),
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
    assert "Broader Coverage Plan" in output_md.read_text(encoding="utf-8")
