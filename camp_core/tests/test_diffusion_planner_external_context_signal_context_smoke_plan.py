from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_external_context_signal_context_smoke import (
    AUTHORIZED_NEXT_WORK,
    build_report,
    main,
    render_markdown,
)


def _implementation_smoke(*, available: bool = True) -> dict:
    return {
        "schema_version": "dp_camp_signal_context_wiring_impl_unit_smoke_v1",
        "selection_effect": False,
        "closed_loop_replay": False,
        "diffusion_planner_execution": False,
        "training": False,
        "payload_traffic_signal_context_available": available,
        "finite_checks_all": available,
        "signal_context": {
            "signal_s_m": 1.5,
            "current_phase": "red",
            "phase_remaining_s": None,
            "blocked_phases": ["red", "yellow"],
        }
        if available
        else None,
    }


def test_signal_context_smoke_plan_ready() -> None:
    report = build_report(implementation_smoke=_implementation_smoke(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == "external_context_signal_context_smoke_plan_ready"
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is True
    assert decision["closed_loop_smoke_authorized"] is True
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["payload_smoke_plan"]["smoke_spec"]["traffic_lights"] == "on"
    assert "traffic_lights_on" in decision["closed_loop_replay_scope"]
    assert "score_k(w)=a_k^T w" in render_markdown(report)


def test_signal_context_smoke_plan_rejects_unavailable_signal_payload() -> None:
    report = build_report(implementation_smoke=_implementation_smoke(available=False))

    decision = report["final_decision"]
    assert decision["status"] == "external_context_signal_context_smoke_plan_rejected"
    assert decision["authorized_next_work"] is None
    assert decision["new_replay_authorized"] is False
    failed = [
        check["name"]
        for check in report["source_checks"]
        if not check["passed"]
    ]
    assert "source_signal_payload_available" in failed


def test_signal_context_smoke_plan_cli_writes_json_markdown_and_bash(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "implementation_smoke.json"
    output_json = tmp_path / "signal_smoke_plan.json"
    output_md = tmp_path / "signal_smoke_plan.md"
    output_bash = tmp_path / "run_signal_smoke.sh"
    source.write_text(json.dumps(_implementation_smoke()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "signal-smoke-plan",
            "--implementation_smoke_json",
            str(source),
            "--label",
            "unit_cli",
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "External Context Signal-Context Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    bash = output_bash.read_text(encoding="utf-8")
    assert "--traffic_lights on" in bash
    assert "--camp_external_context_payload_logging" in bash
