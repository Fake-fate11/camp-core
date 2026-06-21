from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_external_context_next_materiality_gate import (
    SIGNAL_WIRING_NEXT_WORK,
    build_report,
    main,
    render_markdown,
)


def _gap(*, status: str = "external_context_materiality_gap_diagnosed") -> dict:
    ready = status == "external_context_materiality_gap_diagnosed"
    return {
        "final_decision": {
            "status": status,
            "passed": ready,
            "authorized_next_work": (
                "external_context_targeted_materiality_smoke_plan_only"
            ),
            "gap_names": [
                "traffic_signal_context_absent",
                "route_speed_context_available_but_no_candidate_excess",
                "route_speed_availability_constant",
                "nonmaterial_constant_speed_limit",
            ],
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _write_camp_replay(path, *, signal_context_none: bool = True) -> None:
    signal_line = "signal_context=None," if signal_context_none else "signal_context=ctx,"
    path.write_text(
        "\n".join(
            [
                "def run():",
                "    build_external_context_payload(",
                "        candidates=candidates,",
                f"        {signal_line}",
                "    )",
            ]
        ),
        encoding="utf-8",
    )


def _write_dp_signal_source(root) -> None:
    traffic = root / "scenario_generation" / "traffic_light.py"
    replay = root / "scenario_generation" / "replay.py"
    traffic.parent.mkdir(parents=True)
    traffic.write_text(
        "\n".join(
            [
                "class _GroupState:",
                "    duration = 1.0",
                "class TrafficLightController:",
                "    def tick(self, scene, sim_time_s): pass",
                "    def write_to_route_lanes(self, route_lanes, window, t): pass",
            ]
        ),
        encoding="utf-8",
    )
    replay.write_text(
        "tl_controller = TrafficLightController(); tl_controller.tick(scene, 0.0)",
        encoding="utf-8",
    )


def test_next_materiality_gate_prioritizes_signal_wiring_preflight(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp)
    _write_dp_signal_source(dp_root)

    report = build_report(
        gap=_gap(),
        camp_replay_source=camp,
        dp_source_root=dp_root,
        route_assets=[
            tmp_path / "sample_map_tl_route_59_to_86.pkl",
            tmp_path / "nishishinjuku_lane_change_route_7_via_8_to_1.pkl",
        ],
        targeted_route_speed_probe_executed=True,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_context_next_materiality_gate_ready"
    assert decision["authorized_next_work"] == SIGNAL_WIRING_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["route_speed_path_closed_for_current_route"] is True
    assert report["signal_wiring_candidate"] is True
    assert "No DP-side classical Benders" in render_markdown(report)


def test_next_materiality_gate_does_not_close_route_speed_without_probe(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp, signal_context_none=False)
    _write_dp_signal_source(dp_root)

    report = build_report(
        gap=_gap(),
        camp_replay_source=camp,
        dp_source_root=dp_root,
        route_assets=[tmp_path / "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"],
        targeted_route_speed_probe_executed=False,
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_context_next_materiality_gate_rejected"
    assert decision["authorized_next_work"] == (
        "pause_external_context_route_or_supply_new_source"
    )
    assert report["route_speed_path_closed_for_current_route"] is False


def test_next_materiality_gate_fails_closed_when_gap_not_ready(tmp_path) -> None:
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    dp_root = tmp_path / "Diffusion-Planner"
    _write_camp_replay(camp)
    _write_dp_signal_source(dp_root)

    report = build_report(
        gap=_gap(status="wrong_status"),
        camp_replay_source=camp,
        dp_source_root=dp_root,
        route_assets=[],
        targeted_route_speed_probe_executed=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_context_next_materiality_gate_rejected"
    assert decision["passed"] is False
    assert decision["authorized_next_work"] is None
    assert decision["formal_seeds_authorized"] is False


def test_next_materiality_gate_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gap_path = tmp_path / "gap.json"
    camp = tmp_path / "run_diffusion_planner_camp_replay.py"
    dp_root = tmp_path / "Diffusion-Planner"
    output_json = tmp_path / "next_gate.json"
    output_md = tmp_path / "next_gate.md"
    gap_path.write_text(json.dumps(_gap()), encoding="utf-8")
    _write_camp_replay(camp)
    _write_dp_signal_source(dp_root)

    monkeypatch.setattr(
        "sys.argv",
        [
            "next-gate",
            "--gap_json",
            str(gap_path),
            "--camp_replay_source",
            str(camp),
            "--dp_source_root",
            str(dp_root),
            "--route_asset",
            str(tmp_path / "sample_map_tl_route_59_to_86.pkl"),
            "--targeted_route_speed_probe_executed",
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
    assert payload["final_decision"]["authorized_next_work"] == SIGNAL_WIRING_NEXT_WORK
    assert "External Context Next Materiality Gate" in output_md.read_text(
        encoding="utf-8"
    )
