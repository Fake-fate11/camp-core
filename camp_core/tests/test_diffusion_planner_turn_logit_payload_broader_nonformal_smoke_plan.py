from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_turn_logit_payload_broader_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    BroaderSmokeSpec,
    EvidenceRunSpec,
    build_report,
)


def _source_smoke(*, passed: bool = True) -> dict:
    return {
        "counts": {
            "available_payload_records": 3 if passed else 0,
            "invalid_payload_records": 0 if passed else 1,
        },
        "latency_ms": {"latency_ms_turn_logit_payload": 0.15},
        "final_decision": {
            "status": "turn_logit_payload_smoke_passed"
            if passed
            else "turn_logit_payload_smoke_rejected",
            "passed": passed,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _selector_equivalence(*, equivalent: bool = True) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {"selected_index": 0},
        "numeric_field_mismatches": {"scores": 0},
        "numeric_shape_mismatches": {"scores": 0},
        "numeric_nonexact_entries": {"scores": 0},
    }


def _dataset_audit(*, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "checks": {
            "closed_loop_outcomes_forbidden": True,
            "finite_candidate_contract_verified": True,
        },
    }


def test_turn_logit_broader_plan_authorizes_predeclared_matrix() -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["paired_smoke_execution_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["planned_candidate_rows"] == 384
    assert len(report["commands"]["replays"]) == 8
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
    assert all("--camp_turn_logit_payload_logging" not in cmd for cmd in baseline_commands)
    assert all("--camp_turn_logit_payload_logging" in cmd for cmd in candidate_commands)
    assert report["commands"]["payload_audit"][
        report["commands"]["payload_audit"].index("--expected_logs") + 1
    ] == "4"
    assert report["commands"]["payload_audit"][
        report["commands"]["payload_audit"].index("--expected_records") + 1
    ] == "12"
    assert "--root" in report["commands"]["dataset_audit"]


def test_turn_logit_broader_plan_rejects_failed_source_smoke() -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(passed=False),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        label="unit",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["paired_smoke_execution_authorized"] is False
    check = next(
        item
        for item in report["source_checks"]
        if item["name"] == "source_turn_logit_smoke_passed"
    )
    assert check["passed"] is False


def test_turn_logit_broader_plan_rejects_formal_seed() -> None:
    spec = replace(
        BroaderSmokeSpec(),
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
        ),
    )
    report = build_report(
        source_smoke_audit=_source_smoke(),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        spec=spec,
    )

    assert report["final_decision"]["status"] != READY_STATUS
    check = next(
        item for item in report["plan_checks"] if item["name"] == "formal_seeds_excluded"
    )
    assert check["passed"] is False


def test_turn_logit_broader_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        payload_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    check = next(
        item
        for item in report["source_checks"]
        if item["name"] == "turn_logit_payload_audit_available"
    )
    assert check["passed"] is False
