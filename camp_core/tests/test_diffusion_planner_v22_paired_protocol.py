from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v22_native import (
    summarize_safety_cost_native_v22,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "integrations" / "diffusion_planner_v22_evaluation.json"


def _module():
    from scripts.integrations import evaluate_diffusion_planner_v22_pairs

    return evaluate_diffusion_planner_v22_pairs


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _route(name: str, *, group: str = "group") -> dict:
    identity = _sha(name)
    return {
        "identity_sha256": identity,
        "logical_map_sha256": _sha("map"),
        "group_sha256": _sha(group),
        "route_asset": {"path": f"/{name}.pkl", "sha256": _sha(f"asset:{name}")},
        "route_spec": {"map_path": "/map.osm"},
        "source_stratum": {"tight_corridor": name.endswith("stress")},
    }


def _manifest() -> dict:
    calibration = [_route("normal"), _route("stress")]
    holdout = _route("holdout", group="holdout-group")
    splits = {
        "train": {"routes": [], "group_sha256": [], "seed_namespace": [22001]},
        "calibration": {
            "routes": calibration,
            "group_sha256": [_sha("group")],
            "seed_namespace": [22101, 22102],
        },
        "holdout": {
            "routes": [holdout],
            "group_sha256": [_sha("holdout-group")],
            "seed_namespace": [22201],
        },
    }
    pairs = []
    for split, payload in splits.items():
        for route in payload["routes"]:
            for seed in payload["seed_namespace"]:
                pairs.append(
                    {
                        "split": split,
                        "route_identity_sha256": route["identity_sha256"],
                        "seed": seed,
                        "expected_arms": ["dp", "camp"],
                        "receipt_key": f"{split}/{route['identity_sha256']}/seed_{seed}/pair.json",
                    }
                )
    return {
        "schema_version": "v22_route_family_split_manifest_v1",
        "source_only": True,
        "outcome_fields_consumed": [],
        "split_freeze_sha256": _sha("split"),
        "splits": splits,
        "expected_pairs": pairs,
        "pilot_route_identity_sha256": [item["identity_sha256"] for item in calibration],
        "main_route_identity_sha256": [holdout["identity_sha256"]],
    }


def _config() -> dict:
    return {
        "schema_version": "camp_dp_v22_native_evaluation_v1",
        "source_split": {"split_freeze_sha256": _sha("split")},
        "frozen_selector": {
            "artifact": "/freeze",
            "artifact_root_sha256": _sha("freeze-root"),
            "model_sha256": _sha("frozen-model"),
            "weights": {"path": "/freeze/runtime/weights.npy", "sha256": _sha("weights")},
            "atom_scales": {"path": "/freeze/runtime/atom_scales.json", "sha256": _sha("scales")},
        },
        "maps": [{"path": "/map.osm", "sha256": _sha("map")}],
        "modes": {
            "capability": {"split": "calibration", "single_tick_route_count": 1, "route_count": 2, "seed_count": 1, "max_steps": 4},
            "pilot": {"split": "calibration", "route_count": 2, "seed_count": 2, "max_steps": 64},
            "main": {"split": "holdout", "route_count": 1, "seed_count": 1, "max_steps": 64},
        },
        "arm_order": ["dp", "camp"],
        "candidate_k": 8,
        "selection_policy": "v22_source_valid",
        "score_contract": "score_k(w)=a_k^T w",
        "nonnegative_simplex": True,
        "safety_schema": "safety_cost_native_v22",
        "primary_speed_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "route_retention": "all_preregistered_routes_and_failures",
        "claim_contract": {
            "overall_mean_delta_strictly_below_zero": True,
            "cluster_ci95_upper_strictly_below_zero": True,
            "better_pairs_must_exceed_worse_pairs": True,
            "additional_collision_pairs_max": 0,
            "additional_red_light_pairs_max": 0,
            "offroad_wrong_way_mean_delta_max": 0.0,
            "offroad_wrong_way_ci95_upper_max": 0.005,
        },
        "pilot_execution_authorized": True,
        "main_execution_authorized": False,
        "holdout_opened": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "claim_authorized": False,
    }


def _base_config() -> dict:
    spawn = {name: None for name in _module().SPAWN_CONFIG_FIELDS}
    spawn.update(
        {
            "advance_mode": "mpc",
            "mpc_horizon_steps": 20,
            "mpc_n_knots": 5,
            "sequential_inference": False,
            "sg_smooth_enabled": False,
            "dump_npz_dir": None,
            "reward_config_path": None,
            "enable_traffic_lights": True,
            "map_refresh_steps": 5,
        }
    )
    return {
        "schema_version": "camp_dp_v22_native_capability_v1",
        "fixed_dp": {
            "repo": "/dp",
            "head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "checkpoint": {"path": "/model.pth", "sha256": _sha("model")},
            "args_json": {"path": "/args.json", "sha256": _sha("args")},
            "native_source_sha256": _module().NATIVE_SOURCE_SHA256,
        },
        "selector": {},
        "map": {"path": "/map.osm", "sha256": _sha("map")},
        "routes": [],
        "seeds": {},
        "spawn_config": spawn,
        "protocol": {},
    }


def _freeze() -> dict:
    return {
        "status": "complete",
        "primary_model_frozen": True,
        "model_retrained": False,
        "solver_invoked": False,
        "holdout_executed": False,
        "claim_authorized": False,
        "selected_model": {
            "model_sha256": _sha("frozen-model"),
            "score_contract": "score_k(w)=a_k^T w",
        },
        "runtime_assets": {
            "weights": {"path": "runtime/weights.npy", "sha256": _sha("weights")},
            "atom_scales": {"path": "runtime/atom_scales.json", "sha256": _sha("scales")},
        },
        "primary_operational_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
    }


def _arm(route: dict, arm: str, run_config: dict, *, all_high: bool = False) -> dict:
    count = int(run_config["protocol"]["evaluation_steps"])
    initial = _sha(f"initial:{route['name']}:{run_config['seeds']['scenario']}")
    rows = [_sha(f"row:{index}") for index in range(8)]
    selected = 3 if all_high else 0
    scores = [2.0] * 8
    scores[selected] = 0.0
    ticks = []
    records = []
    for index in range(count):
        tick = {
            "tick_index": index,
            "input_sha256": initial if index == 0 else _sha(f"input:{arm}:{index}"),
            "padding": {"observed_frames": 31, "padded_frames": 0, "padding_policy": "native_zero_left_pad_to_31_v1"},
            "tracker": {"status": "ok"},
            "safety": {"source_complete": True},
            "latency_ms": {"total_planning": 1.0},
            "default_output_sha256": rows[0],
        }
        if arm == "camp":
            tick.update(
                {
                    "candidate_tensor_sha256_before": _sha(f"tensor:{index}"),
                    "candidate_tensor_sha256_after": _sha(f"tensor:{index}"),
                    "candidate_neighbor_sha256": _sha(f"neighbor:{index}"),
                    "atom_matrix_sha256": _sha(f"atoms:{index}"),
                    "selected_trajectory_sha256": rows[selected],
                    "candidate_row_sha256": rows,
                    "global_rng_sha256_before": _sha("rng"),
                    "global_rng_sha256_after": _sha("rng"),
                    "selection_policy": "v22_source_valid",
                    "score_contract": "score_k(w)=a_k^T w",
                    "eligibility_mask_name": "source_valid_mask",
                    "scores": scores,
                    "selected_index": selected,
                    "default_candidate0_identity": {
                        "elementwise_equal": True,
                        "max_abs_difference": 0.0,
                        "native_ranked_k8": False,
                        "default_output_sha256": rows[0],
                        "candidate0_sha256": rows[0],
                    },
                    "physical_feasible_mask": [not all_high] * 8,
                    "source_valid_mask": [True] * 8,
                    "source_complete_mask": [True] * 8,
                    "all_k_high_risk": all_high,
                }
            )
        ticks.append(tick)
        records.append(
            {
                "tick_index": index,
                "position_xy": [float(index), 0.0],
                "speed_mps": 5.0,
                "ego_heading_rad": 0.0,
                "route_heading_rad": 0.0,
                "route_progress_m": float(index),
                "five_point_drivable_coverage": True,
                "min_obb_clearance_m": 10.0,
                "red_light_at_interval_start": False,
                "front_center_prev_xy": [float(index), 0.0],
                "front_center_xy": [float(index) + 0.1, 0.0],
                "red_stop_lines": [],
                "speed_limit_mps": 10.0,
                "constant_velocity_circle_ttc_diagnostic_s": None,
                "source_complete": True,
            }
        )
    safety = summarize_safety_cost_native_v22(records)
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "route_name": route["name"],
        "route_sha256": route["sha256"],
        "logical_map_sha256": run_config["map"]["sha256"],
        "fixed_dp_head": run_config["fixed_dp"]["head"],
        "checkpoint_sha256": run_config["fixed_dp"]["checkpoint"]["sha256"],
        "args_sha256": run_config["fixed_dp"]["args_json"]["sha256"],
        "arm": arm,
        "scenario_seed": run_config["seeds"]["scenario"],
        "spawn_config_sha256": _module().canonical_spawn_config_sha256(run_config, count),
        "initial_state_sha256": initial,
        "initial_input_sha256": initial,
        "ticks": ticks,
        "safety": safety,
        "secondary": {"route_completion_rate": 1.0},
        "latency": {"total_planning": {"count": count, "mean": 1.0}},
        "claim_authorized": False,
    }


def test_tracked_evaluation_config_freezes_pilot_and_keeps_main_closed() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["modes"]["pilot"] == {"split": "calibration", "route_count": 30, "seed_count": 3, "max_steps": 64}
    assert config["modes"]["capability"] == {"split": "calibration", "single_tick_route_count": 1, "route_count": 2, "seed_count": 1, "max_steps": 4}
    assert config["modes"]["main"] == {"split": "holdout", "route_count": 100, "seed_count": 5, "max_steps": 64}
    assert config["frozen_selector"]["artifact_root_sha256"] == "5e8ebdff441d10f8c824ed3104eda3f4d484c2235ad85184b45223c780b41fed"
    assert config["primary_speed_tolerance_mps"] == 0.1
    assert config["main_execution_authorized"] is False
    assert config["holdout_opened"] is False


def test_pilot_schedule_is_complete_outcome_blind_cross_product() -> None:
    schedule = _module().build_pair_schedule(_config(), _manifest(), mode="pilot")

    assert len(schedule) == 4
    assert [item["seed"] for item in schedule] == [22101, 22102, 22101, 22102]
    assert all(item["split"] == "calibration" for item in schedule)
    assert all(item["included_in_denominator"] is True for item in schedule)


def test_fake_paired_execution_reuses_shared_runner_and_exact_arm_inputs(tmp_path: Path) -> None:
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del output_dir
        calls.append((route["name"], arm, config["seeds"]["scenario"], max_steps))
        return _arm(route, arm, config, all_high=route["name"] == _sha("stress"))

    result = _module().execute_paired_evaluation(
        _config(), _manifest(), _base_config(), _freeze(),
        mode="pilot", output_dir=tmp_path / "pilot", run_arm=run_arm,
    )

    assert len(calls) == 8
    assert result["planned_pair_count"] == result["retained_pair_count"] == 4
    assert result["paired_complete_count"] == 4
    assert result["hard_invalid_pair_count"] == 0
    assert result["execution_failure_pair_count"] == 0
    assert result["final_claim_authorized"] is False
    assert result["all_k_high_risk_pair_count"] == 2
    assert (tmp_path / "pilot" / "summary.json").is_file()
    rows = json.loads((tmp_path / "pilot" / "pair_rows.json").read_text())
    assert len(rows) == 4
    assert all(row["included_in_denominator"] for row in rows)


def test_failed_arm_is_retained_without_retry_replacement_or_denominator_drop(tmp_path: Path) -> None:
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del output_dir, max_steps
        calls.append((route["name"], arm, config["seeds"]["scenario"]))
        if route["name"] == _sha("normal") and arm == "camp" and config["seeds"]["scenario"] == 22101:
            raise RuntimeError("tracker objectively cannot execute")
        return _arm(route, arm, config)

    result = _module().execute_paired_evaluation(
        _config(), _manifest(), _base_config(), _freeze(),
        mode="pilot", output_dir=tmp_path / "failed", run_arm=run_arm,
    )

    assert len(calls) == 8
    assert result["planned_pair_count"] == result["retained_pair_count"] == 4
    assert result["paired_complete_count"] == 3
    assert result["execution_failure_pair_count"] == 1
    rows = json.loads((tmp_path / "failed" / "pair_rows.json").read_text())
    failed = [row for row in rows if not row["paired_complete"]]
    assert len(failed) == 1
    assert failed[0]["failure_class"] == "execution_failure"
    assert failed[0]["included_in_denominator"] is True


def test_main_rejected_until_post_pilot_freeze_and_holdout_open_marker_absent() -> None:
    with pytest.raises(ValueError, match="main execution"):
        _module().build_pair_schedule(_config(), _manifest(), mode="main")


@pytest.mark.parametrize(
    ("mutation", "match"),
    (("map", "logical_map"), ("selected_row", "indexed row")),
)
def test_successful_pair_rejects_arm_asymmetry_or_nonindexed_selection(
    mutation: str, match: str,
) -> None:
    module = _module()
    planned = module.build_pair_schedule(_config(), _manifest(), mode="pilot")[0]
    run_config = module.build_evaluation_run_config(
        _config(), _base_config(), planned, mode="pilot"
    )
    route = run_config["routes"][0]
    dp = _arm(route, "dp", run_config)
    camp = _arm(route, "camp", run_config)
    if mutation == "map":
        camp["logical_map_sha256"] = _sha("different-map")
    else:
        camp["ticks"][0]["selected_trajectory_sha256"] = _sha("not-row-zero")

    with pytest.raises(ValueError, match=match):
        module.validate_successful_pair(dp, camp, planned, run_config)


def test_evaluator_has_no_parallel_native_replay_loop() -> None:
    source = (ROOT / "scripts" / "integrations" / "evaluate_diffusion_planner_v22_pairs.py").read_text(encoding="utf-8")

    assert "build_native_arm_runner" in source
    assert "run_route_replay" not in source


def test_capability_chain_runs_single_tick_then_tiny_multi_route(tmp_path: Path) -> None:
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del output_dir
        calls.append((route["name"], arm, max_steps))
        return _arm(route, arm, config)

    result = _module().execute_capability_chain(
        _config(), _manifest(), _base_config(), _freeze(),
        output_dir=tmp_path / "capability", run_arm=run_arm,
    )

    assert [steps for _route_name, _arm_name, steps in calls] == [1, 1, 4, 4, 4, 4]
    assert result["planned_pair_count"] == 3
    assert result["retained_pair_count"] == 3
    assert result["paired_complete_count"] == 3
    assert result["pilot_executed"] is False
    assert result["holdout_opened"] is False
