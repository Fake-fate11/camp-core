from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_external_context_signal_wiring_preflight import (
    AUTHORIZED_NEXT_WORK,
    build_report,
    main,
    render_markdown,
)


def _next_gate(*, status: str = "external_context_next_materiality_gate_ready") -> dict:
    ready = status == "external_context_next_materiality_gate_ready"
    return {
        "final_decision": {
            "status": status,
            "passed": ready,
            "authorized_next_work": (
                "external_context_signal_context_wiring_preflight_design_only"
            ),
            "primary_gap": "traffic_signal_source_visible_but_signal_context_not_wired",
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _write_camp_replay(path) -> None:
    path.write_text(
        "\n".join(
            [
                "def run():",
                "    parser.add_argument('--camp_external_context_payload_logging')",
                "    build_external_context_payload(",
                "        candidates=candidates,",
                "        signal_context=None,",
                "    )",
            ]
        ),
        encoding="utf-8",
    )


def _write_payload_source(path) -> None:
    path.write_text(
        "\n".join(
            [
                "def build_external_context_payload(signal_context=None): pass",
                "signal_context.get('signal_s_m')",
                "signal_context.get('signal_distance_m')",
                "signal_context.get('signal_position_ego')",
                "signal_context.get('current_phase')",
                "signal_context.get('phase_remaining_s')",
                "signal_context.get('blocked_phases')",
            ]
        ),
        encoding="utf-8",
    )


def _write_dp_source(root) -> None:
    traffic = root / "scenario_generation" / "traffic_light.py"
    traffic.parent.mkdir(parents=True)
    traffic.write_text(
        "\n".join(
            [
                "class _GroupState:",
                "    last_change_time = 0.0",
                "    duration = 10.0",
                "class TrafficLightController:",
                "    def write_to_route_lanes(self, route_lanes, window, t): pass",
            ]
        ),
        encoding="utf-8",
    )


def test_signal_wiring_preflight_ready(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    payload = tmp_path / "diffusion_planner_external_context_payload.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp)
    _write_payload_source(payload)
    _write_dp_source(dp_root)

    report = build_report(
        next_gate=_next_gate(),
        camp_replay_source=camp,
        payload_source=payload,
        dp_source_root=dp_root,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_context_signal_context_wiring_preflight_ready"
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["wiring_contract"]["payload_fields"]["blocked_phases"] == [
        "red",
        "yellow",
    ]
    assert "no DP-side classical Benders" in render_markdown(report)


def test_signal_wiring_preflight_blocks_when_next_gate_not_ready(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    payload = tmp_path / "diffusion_planner_external_context_payload.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp)
    _write_payload_source(payload)
    _write_dp_source(dp_root)

    report = build_report(
        next_gate=_next_gate(status="wrong_status"),
        camp_replay_source=camp,
        payload_source=payload,
        dp_source_root=dp_root,
    )

    decision = report["final_decision"]
    assert decision["status"] == (
        "external_context_signal_context_wiring_preflight_source_not_ready"
    )
    assert decision["authorized_next_work"] is None
    assert decision["formal_seeds_authorized"] is False


def test_signal_wiring_preflight_blocks_when_payload_schema_missing(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    payload = tmp_path / "diffusion_planner_external_context_payload.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp)
    payload.write_text("def build_external_context_payload(): pass", encoding="utf-8")
    _write_dp_source(dp_root)

    report = build_report(
        next_gate=_next_gate(),
        camp_replay_source=camp,
        payload_source=payload,
        dp_source_root=dp_root,
    )

    decision = report["final_decision"]
    assert decision["status"] == (
        "external_context_signal_context_wiring_preflight_source_not_ready"
    )
    assert report["payload_contract"]["has_required_tokens"] is False


def test_signal_wiring_preflight_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    next_gate = tmp_path / "next_gate.json"
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    payload = tmp_path / "diffusion_planner_external_context_payload.py"
    dp_root = tmp_path / "Diffusion-Planner"
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    next_gate.write_text(json.dumps(_next_gate()), encoding="utf-8")
    _write_camp_replay(camp)
    _write_payload_source(payload)
    _write_dp_source(dp_root)

    monkeypatch.setattr(
        "sys.argv",
        [
            "signal-preflight",
            "--next_gate_json",
            str(next_gate),
            "--camp_replay_source",
            str(camp),
            "--payload_source",
            str(payload),
            "--dp_source_root",
            str(dp_root),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["analysis"]["label"] == "unit_cli"
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "External Context Signal Wiring Preflight" in output_md.read_text(
        encoding="utf-8"
    )
