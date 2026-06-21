from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_external_source_visibility_inventory import (
    analyze,
    main,
    render_markdown,
)


def _contract(
    status: str = "scenario_objective_redesign_boundary_and_external_source_contract_ready",
) -> dict:
    return {
        "external_source_visibility_contract": {
            "required_properties": [
                "current_tick_available_before_selection",
                "candidate_level_or_candidate_context_joinable",
                "finite_and_deterministic_for_fixed_tick",
                "not_a_closed_score_family_or_proxy",
                "not_future_outcome_label",
                "does_not_require_dp_modification_or_retraining",
                "latency_measurable_default_off",
                "atomizable_as_nonnegative_or_signed_split_coefficient",
                "preserves_affine_score_and_convex_master",
            ]
        },
        "final_decision": {
            "status": status,
            "passed": status
            == "scenario_objective_redesign_boundary_and_external_source_contract_ready",
            "external_source_contract_ready": status
            == "scenario_objective_redesign_boundary_and_external_source_contract_ready",
            "authorized_next_work": "external_source_visibility_inventory_or_pause_only",
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def test_inventory_finds_runtime_context_design_candidates(tmp_path) -> None:
    source_root = tmp_path / "Diffusion-Planner"
    traffic = source_root / "scenario_generation" / "traffic_light.py"
    converter = source_root / "scenario_generation" / "tensor_converter.py"
    traffic.parent.mkdir(parents=True)
    converter.parent.mkdir(parents=True, exist_ok=True)
    traffic.write_text(
        "\n".join(
            [
                "class TrafficLightController:",
                "    def tick(self, scene, sim_time_s): pass",
                "class _GroupState:",
                "    duration = 1.0",
                "    last_change_time = 0.0",
            ]
        ),
        encoding="utf-8",
    )
    converter.write_text(
        "\n".join(
            [
                "def to_model_tensors(scene):",
                "    route_lanes_speed_limit = scene.route_speed_limit",
                "    route_lanes_has_speed_limit = scene.route_has_speed_limit",
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        source_contract=_contract(),
        source_files=[],
        source_roots=[source_root],
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_source_visibility_inventory_has_design_candidate"
    assert decision["authorized_next_work"] == (
        "predeclare_default_off_external_context_payload_design_only"
    )
    assert decision["design_candidate_names"] == [
        "traffic_signal_phase_timing_or_right_of_way_state",
        "route_speed_limit_and_control_context",
    ]
    assert decision["training_execution_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_inventory_rejects_training_only_log_prob(tmp_path) -> None:
    source_root = tmp_path / "Diffusion-Planner"
    train = source_root / "rlvr" / "grpo_loss.py"
    train.parent.mkdir(parents=True)
    train.write_text("log_prob = policy.log_prob(sample)", encoding="utf-8")

    report = analyze(
        source_contract=_contract(),
        source_files=[],
        source_roots=[source_root],
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_source_visibility_inventory_no_deployable_source"
    rows = {row["name"]: row for row in report["source_rows"]}
    assert rows["dp_native_log_probability_or_candidate_score"][
        "admissibility_status"
    ] == "visible_only_in_training_or_research_paths"
    assert decision["online_selector_authorized"] is False


def test_inventory_does_not_reopen_closed_turn_logits(tmp_path) -> None:
    source_root = tmp_path / "Diffusion-Planner"
    decoder = (
        source_root
        / "diffusion_planner"
        / "diffusion_planner"
        / "model"
        / "module"
        / "decoder.py"
    )
    decoder.parent.mkdir(parents=True)
    decoder.write_text(
        "return {'prediction': x, 'turn_indicator_logit': turn_indicator_logit}",
        encoding="utf-8",
    )

    report = analyze(
        source_contract=_contract(),
        source_files=[],
        source_roots=[source_root],
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_source_visibility_inventory_no_deployable_source"
    rows = {row["name"]: row for row in report["source_rows"]}
    assert rows["turn_indicator_logits"]["admissibility_status"] == (
        "visible_but_closed_score_family"
    )
    assert rows["turn_indicator_logits"]["closed_by_score_inventory"] is True


def test_inventory_fails_closed_when_contract_not_ready(tmp_path) -> None:
    source = tmp_path / "scenario_generation" / "traffic_light.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "class TrafficLightController:\n    def tick(self, scene, sim_time_s): pass\n",
        encoding="utf-8",
    )

    report = analyze(
        source_contract=_contract(status="wrong_status"),
        source_files=[source],
        source_roots=[],
    )

    decision = report["final_decision"]
    assert decision["status"] == "external_source_visibility_inventory_source_not_ready"
    assert decision["authorized_next_work"] == "fix_external_source_contract_before_inventory"
    assert decision["formal_seeds_authorized"] is False


def test_inventory_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "contract.json"
    source_root = tmp_path / "Diffusion-Planner"
    traffic = source_root / "scenario_generation" / "traffic_light.py"
    output_json = tmp_path / "inventory.json"
    output_md = tmp_path / "inventory.md"
    traffic.parent.mkdir(parents=True)
    contract.write_text(json.dumps(_contract()), encoding="utf-8")
    traffic.write_text(
        "\n".join(
            [
                "class TrafficLightController:",
                "    def tick(self, scene, sim_time_s): pass",
                "class _GroupState:",
                "    duration = 1.0",
                "    last_change_time = 0.0",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "inventory",
            "--source_contract_json",
            str(contract),
            "--source_root",
            str(source_root),
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
    assert payload["final_decision"]["status"] == (
        "external_source_visibility_inventory_has_design_candidate"
    )
    assert "External Source Visibility Inventory" in output_md.read_text(
        encoding="utf-8"
    )
