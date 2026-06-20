from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_logging_wiring import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_NEXT_WORK,
    SOURCE_READY_STATUS,
    build_report,
)


def _context_preflight_report(
    *,
    status: str = SOURCE_READY_STATUS,
    authorized_next_work: str | None = SOURCE_NEXT_WORK,
    passed: bool = True,
    formal_seed_records: int = 0,
) -> dict:
    return {
        "analysis": {
            "formal_seed_records": formal_seed_records,
            "math_boundary": (
                "fixed coefficients preserve affine score_k(w)=a_k^T w; "
                "no DP-side classical Benders master/subproblem is claimed"
            ),
        },
        "formal_seed_records": formal_seed_records,
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": authorized_next_work,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def test_context_logging_wiring_plan_authorizes_only_wiring_unit_tests() -> None:
    report = build_report(
        context_preflight_report=_context_preflight_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["analysis"]["training"] is False
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["analysis"]["wiring_plan_only"] is True
    assert report["analysis"]["future_outcome_labels_used_for_plan"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])

    planned = report["planned_wiring"]
    assert planned["planned_flag"] == "--camp_progress_lane_hard_context_logging"
    assert planned["planned_payload_key"] == "progress_lane_hard_context_logging"
    assert (
        planned["planned_builder"]
        == "build_progress_lane_hard_context_logging_payload"
    )
    assert planned["required_metadata"]["selection_effect"] is False
    assert planned["required_metadata"]["future_outcome_leakage"] is False
    assert planned["required_metadata"]["closed_loop_outcome_fields_read"] is False
    assert planned["required_metadata"]["classical_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_context_logging_wiring_plan_blocks_when_source_not_ready() -> None:
    report = build_report(
        context_preflight_report=_context_preflight_report(
            status="progress_lane_hard_context_logging_preflight_rejected",
            authorized_next_work=None,
            passed=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    source = {
        check["name"]: check["passed"] for check in report["source_checks"]
    }
    assert source["context_preflight_ready"] is False


def test_context_logging_wiring_plan_blocks_wrong_source_next_work() -> None:
    report = build_report(
        context_preflight_report=_context_preflight_report(
            authorized_next_work="default_off_progress_lane_hard_context_replay_smoke"
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    source = {
        check["name"]: check["passed"] for check in report["source_checks"]
    }
    assert source["context_preflight_ready"] is False


def test_context_logging_wiring_plan_accepts_existing_audit_alias_flags() -> None:
    source = _context_preflight_report()
    final = source["final_decision"]
    del final["full36_authorized"]
    del final["camp_retraining_authorized"]
    del final["dp_modification_authorized"]

    report = build_report(context_preflight_report=source)

    assert report["final_decision"]["status"] == READY_STATUS


def test_context_logging_wiring_plan_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        build_report(
            context_preflight_report=_context_preflight_report(
                formal_seed_records=1
            ),
            fail_on_formal_seeds=True,
        )


def test_context_logging_wiring_plan_rejects_missing_replay_insertion_token(
    tmp_path,
) -> None:
    broken_replay = tmp_path / "runner.py"
    broken_replay.write_text(
        "--camp_progress_support_logging\n"
        "progress_support_logging_payload = None\n"
        "build_progress_support_logging_payload(\n",
        encoding="utf-8",
    )

    report = build_report(
        context_preflight_report=_context_preflight_report(),
        replay_source=broken_replay,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [
        check for check in report["source_checks"] if check["passed"] is False
    ]
    assert any(
        check["name"] == "replay_has_adjacent_default_off_logging_hooks"
        for check in failed
    )


def test_context_logging_wiring_plan_rejects_missing_payload_schema_token(
    tmp_path,
) -> None:
    broken_payload = tmp_path / "payload.py"
    broken_payload.write_text("def build_progress_lane_hard_context_logging_payload(): pass\n")

    report = build_report(
        context_preflight_report=_context_preflight_report(),
        payload_module_source=broken_payload,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [
        check for check in report["source_checks"] if check["passed"] is False
    ]
    assert any(
        check["name"] == "payload_module_exports_default_off_context_builder"
        for check in failed
    )


def test_context_logging_wiring_plan_cli_shape(tmp_path) -> None:
    source = tmp_path / "context_preflight.json"
    source.write_text(json.dumps(_context_preflight_report()), encoding="utf-8")

    report = build_report(
        context_preflight_report=json.loads(source.read_text(encoding="utf-8")),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
