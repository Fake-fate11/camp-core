from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_temporal_consistency_payload_runtime_preflight import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _design_gate(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "temporal_consistency_payload_design_predeclared",
        "passed": True,
        "payload_design_ready": True,
        "authorized_next_work": (
            "default_off_temporal_consistency_payload_runtime_preflight_only"
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
    return {"final_decision": decision}


def _runner_source() -> str:
    return "\n".join(
        [
            "--camp_temporal_consistency_payload_logging",
            "build_temporal_consistency_payload(",
            "previous_selected_plan_memory",
            "previous_selected_plan=previous_selected_plan_memory",
            "temporal_consistency_payload_logging=bool(",
            "args.camp_temporal_consistency_payload_logging",
            '"temporal_consistency_payload_logging": (',
            '"camp_temporal_consistency_payload_logging": (',
            'validation["camp_temporal_consistency_payload_logging"]',
            "**temporal_consistency_payload_latency_ms",
            "default_off_temporal_consistency_payload_runtime_preflight_only",
        ]
    )


def test_temporal_consistency_runtime_preflight_accepts_default_off_wiring() -> None:
    report = build_report(
        payload_design_gate=_design_gate(),
        runner_source=_runner_source(),
        summary_source='"camp_temporal_consistency_payload_logging"',
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["runtime_preflight_ready"] is True
    assert decision["authorized_next_work"] == (
        "default_off_temporal_consistency_tiny_paired_smoke_plan_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["pure_payload_runtime"]["missing_previous_plan_reason"] == (
        "previous_selected_plan_absent"
    )
    assert report["pure_payload_runtime"]["available_costs"] == [0.0, 1.0]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_runtime_preflight_blocks_if_design_not_ready() -> None:
    report = build_report(
        payload_design_gate=_design_gate(
            status="temporal_consistency_payload_design_blocked",
            passed=False,
            payload_design_ready=False,
            authorized_next_work=None,
        ),
        runner_source=_runner_source(),
        summary_source='"camp_temporal_consistency_payload_logging"',
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert "design_status" in decision["failed_checks"]
    assert "payload_design_ready" in decision["failed_checks"]


def test_temporal_consistency_runtime_preflight_blocks_missing_runner_wiring() -> None:
    report = build_report(
        payload_design_gate=_design_gate(),
        runner_source="",
        summary_source="",
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert any(name.startswith("runner_contains::") for name in decision["failed_checks"])
    assert any(name.startswith("summary_contains::") for name in decision["failed_checks"])


def test_temporal_consistency_runtime_preflight_markdown_states_boundary() -> None:
    markdown = render_markdown(
        build_report(
            payload_design_gate=_design_gate(),
            runner_source=_runner_source(),
            summary_source='"camp_temporal_consistency_payload_logging"',
        )
    )

    assert "Temporal Consistency Payload Runtime Preflight" in markdown
    assert "previous_selected_plan_absent" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "does not authorize DP replay" in markdown


def test_temporal_consistency_runtime_preflight_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    design = tmp_path / "design.json"
    runner = tmp_path / "runner.py"
    summary = tmp_path / "summary.py"
    output_json = tmp_path / "runtime.json"
    output_md = tmp_path / "runtime.md"
    design.write_text(json.dumps(_design_gate()), encoding="utf-8")
    runner.write_text(_runner_source(), encoding="utf-8")
    summary.write_text('"camp_temporal_consistency_payload_logging"', encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--payload_design_gate_json",
            str(design),
            "--runner_path",
            str(runner),
            "--summary_script_path",
            str(summary),
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
    assert "Temporal Consistency Payload Runtime Preflight" in output_md.read_text(
        encoding="utf-8"
    )
