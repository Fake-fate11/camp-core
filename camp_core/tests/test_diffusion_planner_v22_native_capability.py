import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_v22_capability_config_is_diagnostic_and_not_holdout() -> None:
    module = _runner()
    config = _config()

    module.validate_v22_capability_config(config)

    assert config["selector"]["selection_policy"] == "v22_source_valid"
    assert config["selector"]["role"] == "v18_ablation_capability_only"
    assert config["protocol"]["safety_schema"] == "safety_cost_native_v22"
    assert config["protocol"]["tiny_steps"] == 4
    assert config["protocol"]["route_role"] == (
        "diagnostic_v21_observed_not_holdout"
    )
    assert config["protocol"]["claim_authorized"] is False
    assert config["protocol"]["training_authorized"] is False
    assert config["protocol"]["holdout_access_authorized"] is False
    assert config["seeds"]["formal_forbidden"] == [11, 12, 13]


def test_v22_capability_normalization_preserves_v21_frozen_base() -> None:
    module = _runner()
    config = _config()
    before = json.loads(json.dumps(config))

    normalized = module._v21_compatible_capability_config(config)

    module.validate_smoke_config(normalized)
    assert config == before
    assert normalized["schema_version"] == "camp_dp_v21_native_smoke_v1"
    assert normalized["protocol"]["safety_schema"] == "safety_cost_native_v1"
    assert "selection_policy" not in normalized["selector"]


def test_existing_native_runner_reads_v22_selection_policy() -> None:
    module = _runner()
    config = _config()

    assert module._selection_policy(config) == "v22_source_valid"


def _v22_camp_tick() -> dict:
    digest = "1" * 64
    rows = [f"{index:x}" * 64 for index in range(8)]
    rows[0] = digest
    rows[3] = "5" * 64
    return {
        "tick_index": 0,
        "input_sha256": "2" * 64,
        "padding": {
            "observed_frames": 1,
            "padded_frames": 30,
            "padding_policy": "native_zero_left_pad_to_31_v1",
        },
        "tracker": {"status": "ok"},
        "safety": {"source_complete": True},
        "latency_ms": {"total_planning": 1.0},
        "default_output_sha256": digest,
        "selection_policy": "v22_source_valid",
        "score_contract": "score_k(w)=a_k^T w",
        "eligibility_mask_name": "source_valid_mask",
        "scores": [8.0, 7.0, 6.0, 0.0, 4.0, 3.0, 2.0, 1.0],
        "candidate_tensor_sha256_before": "3" * 64,
        "candidate_tensor_sha256_after": "3" * 64,
        "atom_matrix_sha256": "4" * 64,
        "selected_trajectory_sha256": "5" * 64,
        "candidate_row_sha256": rows,
        "selected_index": 3,
        "default_candidate0_identity": {
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "default_output_sha256": digest,
            "candidate0_sha256": digest,
            "native_ranked_k8": False,
        },
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [True] * 8,
        "source_complete_mask": [True] * 8,
        "all_k_high_risk": False,
    }


def test_public_v22_tick_retains_selection_policy() -> None:
    module = _runner()
    tick = _v22_camp_tick()
    tick.update(
        {
            "causal_input": {
                "input_sha256": tick["input_sha256"],
                "observed_frames": 1,
                "padded_frames": 30,
                "padding_policy": "native_zero_left_pad_to_31_v1",
            },
            "_safety_record": tick["safety"],
            "candidate_neighbor_sha256": "6" * 64,
            "global_rng_sha256_before": "7" * 64,
            "global_rng_sha256_after": "7" * 64,
        }
    )

    public = module._public_tick_receipt(tick, "camp")

    assert public["selection_policy"] == "v22_source_valid"
    assert public["score_contract"] == "score_k(w)=a_k^T w"
    assert public["eligibility_mask_name"] == "source_valid_mask"
    assert public["scores"] == tick["scores"]
    assert public["scores"][public["selected_index"]] == min(public["scores"])


def test_v22_capability_receipt_validator_requires_identity_and_policy() -> None:
    module = _runner()
    tick = _v22_camp_tick()
    receipt = {
        "status": "ok",
        "route_name": "diagnostic",
        "route_sha256": "8" * 64,
        "arm": "camp",
        "initial_state_sha256": "9" * 64,
        "initial_input_sha256": tick["input_sha256"],
        "ticks": [tick],
        "claim_authorized": False,
    }

    module._validate_arm_receipt(
        receipt,
        "camp",
        expected_ticks=1,
        require_summary=False,
        expected_selection_policy="v22_source_valid",
    )

    tick["default_candidate0_identity"]["candidate0_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="candidate 0 identity"):
        module._validate_arm_receipt(
            receipt,
            "camp",
            expected_ticks=1,
            require_summary=False,
            expected_selection_policy="v22_source_valid",
        )

    tick["default_candidate0_identity"]["candidate0_sha256"] = tick[
        "default_output_sha256"
    ]
    tick["scores"][0] = -1.0
    with pytest.raises(ValueError, match="affine argmin"):
        module._validate_arm_receipt(
            receipt,
            "camp",
            expected_ticks=1,
            require_summary=False,
            expected_selection_policy="v22_source_valid",
        )


def _v22_camp_arm(route: dict) -> dict:
    ticks = []
    for index in range(4):
        tick = _v22_camp_tick()
        tick["tick_index"] = index
        tick["input_sha256"] = f"{index + 2:x}" * 64
        tick["padding"]["observed_frames"] = index + 1
        tick["padding"]["padded_frames"] = 30 - index
        ticks.append(tick)
    components = {
        "collision_any": 0.0,
        "near_miss_noncollision_rate": 0.0,
        "offroad_rate": 0.0,
        "wrong_way_rate": 0.0,
        "red_light_violation_any": 0.0,
        "speed_limit_violation_rate": 0.0,
    }
    return {
        "status": "ok",
        "route_name": route["name"],
        "route_sha256": route["sha256"],
        "arm": "camp",
        "initial_state_sha256": "b" * 64,
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "safety": {
            "schema_version": "safety_cost_native_v22",
            "safety_cost": 0.0,
            "components": components,
            "speed_protocol": {
                "schema_version": "speed_protocol_v22",
                "operational_tolerance_mps": 0.1,
            },
        },
        "secondary": {},
        "latency": {},
        "claim_authorized": False,
    }


def test_tiny_capability_runs_two_diagnostic_routes_four_camp_ticks(tmp_path) -> None:
    module = _runner()
    config = _config()
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del config, output_dir
        calls.append((route["name"], arm, max_steps))
        return _v22_camp_arm(route)

    output = tmp_path / "tiny"
    result = module.execute_smoke(
        config,
        output,
        mode="tiny-capability-smoke",
        run_arm=run_arm,
    )

    assert calls == [
        ("sample_map_smoke_route", "camp", 4),
        ("sample_map_tl_route_59_to_86", "camp", 4),
    ]
    assert result["route_count"] == 2
    assert result["arm_count"] == 2
    assert len(result["capability_arms"]) == 2
    assert result["claim_authorized"] is False
    for route in config["routes"]:
        receipt = output / "receipts" / route["name"] / "camp.json"
        assert len(json.loads(receipt.read_text())["ticks"]) == 4


def test_cli_exposes_tiny_capability_as_exclusive_mode(tmp_path) -> None:
    module = _runner()
    args = module.parse_args(
        [
            "--tiny-capability-smoke",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(tmp_path / "tiny"),
        ]
    )

    assert args.mode == "tiny-capability-smoke"


def test_v22_capability_preflight_writes_no_execution_receipt(tmp_path) -> None:
    module = _runner()
    config = _config()
    output = tmp_path / "preflight"

    result = module.execute_smoke(
        config,
        output,
        mode="preflight",
        run_arm=None,
        verified_assets={"fixed_dp_head": config["fixed_dp"]["head"]},
        command="v22 capability preflight unit test",
    )

    assert result["status"] == "passed"
    assert result["mode"] == "preflight"
    assert result["arm_count"] == 0
    assert result["route_count"] == 0
    assert result["claim_authorized"] is False
    assert result["preflight"]["config_valid"] is True
    assert not (output / "receipts").exists()
