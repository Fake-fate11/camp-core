from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_external_context_signal_arrival_targeted_materiality_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    TARGET_PAYLOAD_STEPS,
    build_report,
    main,
)


def _gap(*, ready: bool = True, include_signal_gap: bool = True) -> dict:
    gap_names = [
        "traffic_signal_right_of_way_indicator_constant_clear",
        "route_speed_context_available_but_no_candidate_excess",
    ]
    if include_signal_gap:
        gap_names.insert(0, "traffic_signal_context_available_but_no_candidate_arrival")
    return {
        "final_decision": {
            "status": (
                "external_context_materiality_gap_diagnosed"
                if ready
                else "external_context_materiality_gap_diagnosis_rejected"
            ),
            "passed": ready,
            "authorized_next_work": (
                "external_context_targeted_materiality_smoke_plan_only"
                if ready
                else None
            ),
            "gap_names": gap_names,
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
        }
    }


def test_signal_arrival_materiality_smoke_plan_accepts_signal_horizon_gap() -> None:
    report = build_report(gap=_gap(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is True
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["payload_steps"] == TARGET_PAYLOAD_STEPS
    assert report["payload_smoke_plan"]["smoke_spec"]["traffic_lights"] == "on"
    assert report["payload_smoke_plan"]["smoke_spec"]["payload_steps"] == TARGET_PAYLOAD_STEPS
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    candidate = report["payload_smoke_plan"]["commands"]["candidate_replay"]
    assert "--camp_external_context_payload_logging" in candidate
    assert "--traffic_lights" in candidate
    traffic_index = candidate.index("--traffic_lights")
    assert candidate[traffic_index + 1] == "on"
    steps_index = candidate.index("--camp_external_context_payload_steps")
    assert candidate[steps_index + 1] == str(TARGET_PAYLOAD_STEPS)


def test_signal_arrival_materiality_smoke_plan_rejects_failed_gap_source() -> None:
    report = build_report(gap=_gap(ready=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_gap_status_ready",
        "source_gap_passed",
        "source_authorizes_plan_only_targeted_design",
    ]


def test_signal_arrival_materiality_smoke_plan_rejects_without_signal_gap() -> None:
    report = build_report(gap=_gap(include_signal_gap=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["signal_horizon_gap_is_targeted"]


def test_signal_arrival_materiality_smoke_plan_rejects_unbounded_payload_steps() -> None:
    report = build_report(gap=_gap(), payload_steps=80)

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["payload_support_is_bounded_development_probe"]


def test_signal_arrival_materiality_smoke_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gap_path = tmp_path / "gap.json"
    output_json = tmp_path / "signal_arrival_plan.json"
    output_md = tmp_path / "signal_arrival_plan.md"
    output_bash = tmp_path / "signal_arrival_plan.sh"
    gap_path.write_text(json.dumps(_gap()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-signal-arrival-materiality-smoke-plan",
            "--gap_json",
            str(gap_path),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Signal-Arrival Materiality" in output_md.read_text(encoding="utf-8")
    bash = output_bash.read_text(encoding="utf-8")
    assert "--traffic_lights on" in bash
    assert f"--camp_external_context_payload_steps {TARGET_PAYLOAD_STEPS}" in bash
