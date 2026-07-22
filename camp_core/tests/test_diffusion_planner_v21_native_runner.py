import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "diffusion_planner_v21_native_smoke.json"


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


SPAWN_FIELDS = {
    "spawn_period_steps",
    "max_active_npcs",
    "spawn_probability",
    "min_spawn_distance",
    "max_spawn_distance",
    "despawn_distance",
    "forward_bias",
    "min_npc_separation",
    "goal_tolerance_m",
    "max_steps",
    "seed",
    "ego_overlap_ratio",
    "npc_min_speed",
    "npc_max_speed",
    "npc_route_length_m",
    "npc_goal_min_dist_from_ego_route",
    "curvature_threshold",
    "goal_pass_window_m",
    "map_refresh_steps",
    "max_map_lanelets",
    "map_mask_range_m",
    "sg_smooth_enabled",
    "sg_filter_window",
    "sg_filter_order",
    "advance_mode",
    "mpc_horizon_steps",
    "mpc_n_knots",
    "ego_length",
    "ego_width",
    "ego_wheelbase",
    "ego_max_steer",
    "inference_delay",
    "enable_traffic_lights",
    "overlay_metrics_on_png",
    "dump_npz_dir",
    "dump_neighbor_count",
    "reward_config_path",
    "ego_init_speed",
    "sequential_inference",
    "static_npc_count",
    "static_npc_spacing_m",
    "static_npc_shoulder_margin_m",
    "static_npc_seed",
    "parked_vehicles_yaml",
    "parked_vehicle_visibility_m",
    "turn_indicator_keep_bias",
    "turn_indicator_hold_steps",
}


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _arm(route, arm: str, *, mismatch_initial=False, duplicate=False, missing=False):
    route_name = route["name"]
    initial = hashlib.sha256(route_name.encode()).hexdigest()
    if mismatch_initial and arm == "camp":
        initial = "f" * 64
    ticks = []
    for index in range(2):
        tick = {
            "tick_index": 0 if duplicate else index,
            "input_sha256": initial
            if index == 0
            else hashlib.sha256(f"{route_name}:{arm}:{index}".encode()).hexdigest(),
            "padding": {
                "observed_frames": 31,
                "padded_frames": 0,
                "padding_policy": "native_zero_left_pad_to_31_v1",
            },
            "tracker": {"status": "ok"},
            "safety": {"source_complete": True},
            "latency_ms": {"total_planning": 1.0},
        }
        if arm == "camp":
            tick.update(
                {
                    "candidate_tensor_sha256_before": "1" * 64,
                    "candidate_tensor_sha256_after": "1" * 64,
                    "atom_matrix_sha256": "2" * 64,
                    "normalized_atom_matrix_sha256": "2" * 64,
                    "selected_trajectory_sha256": "3" * 64,
                }
            )
        ticks.append(tick)
    if missing:
        ticks[0].pop("safety")
    cost = 10.0 if arm == "dp" else 8.0
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "route_name": route_name,
        "route_sha256": route["sha256"],
        "arm": arm,
        "initial_state_sha256": initial,
        "initial_input_sha256": initial,
        "ticks": ticks,
        "safety": {
            "schema_version": "safety_cost_native_v1",
            "safety_cost": cost,
            "components": {
                "collision_any": 0.0,
                "near_miss_noncollision_rate": 0.0,
                "offroad_rate": 0.0,
                "wrong_way_rate": 0.0,
                "red_light_violation_any": 0.0,
                "speed_limit_violation_rate": 1.0 if arm == "dp" else 0.8,
            },
        },
        "secondary": {"route_completion_rate": 0.1},
        "latency": {"total_planning": {"count": 2, "mean": 1.0}},
        "claim_authorized": False,
    }


def test_config_freezes_every_native_field_asset_route_and_seed() -> None:
    module = _runner()
    config = _config()
    module.validate_smoke_config(config)

    assert set(config["spawn_config"]) == SPAWN_FIELDS
    assert config["spawn_config"]["advance_mode"] == "mpc"
    assert config["spawn_config"]["mpc_horizon_steps"] == 20
    assert config["spawn_config"]["mpc_n_knots"] == 5
    assert config["spawn_config"]["sequential_inference"] is False
    assert config["spawn_config"]["sg_smooth_enabled"] is False
    assert config["spawn_config"]["dump_npz_dir"] is None
    assert config["spawn_config"]["reward_config_path"] is None
    assert config["spawn_config"]["max_steps"] == 64
    assert config["seeds"] == {
        "scenario": 3417,
        "candidate": 3418,
        "bootstrap": 3419,
        "formal_forbidden": [11, 12, 13],
    }
    assert [(item["name"], item["sha256"]) for item in config["routes"]] == [
        (
            "sample_map_smoke_route",
            "b8b5417c3269bbdbe72efe49388d32af04751b25cffcec297a04b25a50140c13",
        ),
        (
            "sample_map_tl_route_59_to_86",
            "dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4",
        ),
    ]
    assert config["fixed_dp"]["head"] == (
        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    )
    assert config["fixed_dp"]["checkpoint"]["sha256"] == (
        "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
    )
    assert config["fixed_dp"]["args_json"]["sha256"] == (
        "42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa"
    )
    assert config["selector"]["root_sha256"] == (
        "afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7"
    )
    assert config["selector"]["atom_scales"]["sha256"] == (
        "a4122b0fa56912818af92eacf90449633addf9872966aed975317b4307076952"
    )
    assert config["selector"]["weights"]["sha256"] == (
        "922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134"
    )


def _all_offroad_native_hook_state(module):
    input_sha = "1" * 64
    receipts = []
    for index in range(64):
        safety = {
            "tick_index": index,
            "min_obb_clearance_m": 3.0,
            "five_point_drivable_coverage": False,
            "speed_mps": 1.0,
            "ego_heading_rad": 0.0,
            "route_heading_rad": 0.0,
            "front_center_prev_xy": [float(index), -1.0],
            "front_center_xy": [float(index), 0.0],
            "red_light_at_interval_start": False,
            "red_stop_lines": [],
            "speed_limit_mps": None,
            "position_xy": [float(index), 0.0],
            "route_progress_m": float(index),
            "source_complete": True,
        }
        receipts.append(
            {
                "tick_index": index,
                "status": "ok",
                "causal_input": {
                    "input_sha256": input_sha,
                    "observed_frames": 31,
                    "padded_frames": 0,
                    "padding_policy": "native_zero_left_pad_to_31_v1",
                },
                "tracker": {"status": "ok"},
                "_safety_record": safety,
                "_safety_pre": {"pre_decision_speed_mps": 1.0},
                "latency_ms": {"total_planning": 1.0},
                "default_output_sha256": "2" * 64,
            }
        )
    return module.NativeHookState(tick_index=64, receipts=receipts)


def test_controlled_train_receipt_skips_only_derived_run_summaries() -> None:
    module = _runner()
    assert (
        module._derive_run_summaries_for_config(
            {"schema_version": "camp_dp_v25_controlled_train_v2"}
        )
        is False
    )
    assert (
        module._derive_run_summaries_for_config(
            {"schema_version": "camp_dp_v24_native_evaluation_run_v1"}
        )
        is True
    )
    state = _all_offroad_native_hook_state(module)
    common = {
        "route": {"name": "route", "sha256": "3" * 64},
        "arm": "dp",
        "config": {
            "map": {"sha256": "4" * 64},
            "fixed_dp": {
                "head": "5" * 40,
                "checkpoint": {"sha256": "6" * 64},
                "args_json": {"sha256": "7" * 64},
            },
            "seeds": {"scenario": 25001},
            "protocol": {"safety_schema": "safety_cost_native_v22"},
            "spawn_config": {},
        },
        "max_steps": 64,
        "state": state,
        "native_result": {"reason": "max_steps"},
        "builder": SimpleNamespace(
            _cache={1: SimpleNamespace(arc_length=10.0)}
        ),
        "route_ids": [1],
        "selector_scale_contract": None,
    }

    receipt = module._build_native_arm_receipt(
        **common, derive_run_summaries=False
    )

    assert len(receipt["ticks"]) == 64
    assert not {"safety", "secondary", "latency"}.intersection(receipt)
    assert all(
        tick["safety"]["source_complete"] is True for tick in receipt["ticks"]
    )
    with pytest.raises(ValueError, match="moving_onroad_ticks denominator is zero"):
        module._build_native_arm_receipt(
            **common, derive_run_summaries=True
        )
    with pytest.raises(TypeError, match="native bool"):
        module._build_native_arm_receipt(
            **common, derive_run_summaries=0
        )


def test_paired_protocol_is_fresh_ordered_symmetric_and_writes_atomic_receipts(
    tmp_path,
) -> None:
    module = _runner()
    config = _config()
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del config, output_dir
        calls.append((route["name"], arm, max_steps))
        return _arm(route, arm)

    output = tmp_path / "paired"
    result = module.execute_smoke(
        config,
        output,
        mode="paired-smoke",
        run_arm=run_arm,
    )

    assert calls == [
        ("sample_map_smoke_route", "dp", 64),
        ("sample_map_smoke_route", "camp", 64),
        ("sample_map_tl_route_59_to_86", "dp", 64),
        ("sample_map_tl_route_59_to_86", "camp", 64),
    ]
    assert result["claim_authorized"] is False
    assert result["aggregate"]["better_tie_worse"] == {
        "better": 2,
        "tie": 0,
        "worse": 0,
    }
    assert result["padding_strata"] == {"0": 8, "1-5": 0, "6-15": 0, "16-30": 0}
    assert (output / "summary.json").is_file()
    assert (output / "summary.md").is_file()
    assert (output / "stdout.txt").is_file()
    assert (output / "stderr.txt").read_bytes() == b""
    assert (output / "run.exit").read_text().strip() == "0"
    assert (output / "SHA256SUMS").is_file()
    assert (output / "ROOT_SHA256SUMS").is_file()
    assert "camp_source_head=" in (output / "HEADS").read_text()
    assert "mode=paired-smoke" in (output / "COMMAND").read_text()
    assert json.loads((output / "smoke_config.json").read_text()) == config
    for route in config["routes"]:
        for arm in ("dp", "camp"):
            assert (output / "receipts" / route["name"] / f"{arm}.json").is_file()
            assert (
                output / "receipts" / route["name"] / arm / "tick_0000.json"
            ).is_file()
        assert (output / "receipts" / route["name"] / "pair.json").is_file()
    assert module.verify_evidence_hashes(output)["root_sha256"] == result[
        "root_sha256"
    ]
    with pytest.raises(FileExistsError):
        module.execute_smoke(
            config,
            output,
            mode="paired-smoke",
            run_arm=run_arm,
        )


@pytest.mark.parametrize(
    ("failure", "match"),
    (
        ("initial", "initial"),
        ("duplicate", "tick"),
        ("missing", "safety"),
        ("arm", "arm failed"),
    ),
)
def test_pair_validation_rejects_asymmetry_partial_duplicate_or_arm_failure(
    failure: str, match: str
) -> None:
    module = _runner()
    route = _config()["routes"][0]
    dp = _arm(route, "dp")
    camp = _arm(
        route,
        "camp",
        mismatch_initial=failure == "initial",
        duplicate=failure == "duplicate",
        missing=failure == "missing",
    )
    if failure == "arm":
        camp["status"] = "failed"
    with pytest.raises(ValueError, match=match):
        module.validate_pair_receipts(dp, camp)


def test_failed_paired_smoke_seals_provenance_and_partial_receipts(tmp_path) -> None:
    module = _runner()
    config = _config()
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del config, output_dir, max_steps
        calls.append((route["name"], arm))
        if route["name"] == config_routes[1]["name"] and arm == "camp":
            raise RuntimeError("all_candidates_physically_infeasible")
        return _arm(route, arm)

    config_routes = config["routes"]
    output = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="all_candidates_physically_infeasible"):
        module.execute_smoke(
            config,
            output,
            mode="paired-smoke",
            run_arm=run_arm,
            command="frozen paired command",
        )

    assert calls == [
        (config_routes[0]["name"], "dp"),
        (config_routes[0]["name"], "camp"),
        (config_routes[1]["name"], "dp"),
        (config_routes[1]["name"], "camp"),
    ]
    failure = json.loads((output / "failure.json").read_text())
    assert failure["completed_arm_count"] == 3
    assert failure["completed_pair_count"] == 1
    assert "camp_source_head=" in (output / "HEADS").read_text()
    assert "frozen paired command" in (output / "COMMAND").read_text()
    assert json.loads((output / "smoke_config.json").read_text()) == config
    assert (output / "receipts" / config_routes[0]["name"] / "pair.json").is_file()
    assert (
        output / "receipts" / config_routes[1]["name"] / "dp.json"
    ).is_file()
    assert (output / "run.exit").read_text().strip() == "1"
    assert module.verify_evidence_hashes(output)["root_sha256"]


def test_capability_smoke_runs_only_one_camp_tick_and_never_claims(tmp_path) -> None:
    module = _runner()
    config = _config()
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps):
        del config, output_dir
        calls.append((route["name"], arm, max_steps))
        receipt = _arm(route, arm)
        receipt["ticks"] = receipt["ticks"][:1]
        receipt["latency"]["total_planning"]["count"] = 1
        return receipt

    result = module.execute_smoke(
        config,
        tmp_path / "capability",
        mode="capability-smoke",
        run_arm=run_arm,
    )
    assert calls == [("sample_map_smoke_route", "camp", 1)]
    assert result["claim_authorized"] is False
    assert result["mode"] == "capability-smoke"


def test_cli_requires_exactly_one_mode_and_single_use_output(tmp_path) -> None:
    module = _runner()
    output = tmp_path / "preflight"
    args = module.parse_args(
        [
            "--preflight",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(output),
        ]
    )
    assert args.mode == "preflight"
    assert args.config == CONFIG
    assert args.output_dir == output
    with pytest.raises(SystemExit):
        module.parse_args(
            [
                "--preflight",
                "--capability-smoke",
                "--config",
                str(CONFIG),
                "--output-dir",
                str(output),
            ]
        )


def test_direct_script_bootstraps_repo_root_for_reused_integration_imports() -> None:
    script = ROOT / "scripts" / "integrations" / "run_diffusion_planner_dp_camp_v21_native.py"
    package_root = ROOT / "camp_core"
    code = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(package_root)!r});"
        f"runpy.run_path({str(script)!r},run_name='v21_native_test');"
        f"assert {str(ROOT)!r} in sys.path"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_frozen_selector_scale_loader_accepts_exact_legacy_metadata_only(
    tmp_path,
) -> None:
    module = _runner()
    from camp_core.integrations.diffusion_planner import atom_schema_for_dimension

    version, names = atom_schema_for_dimension(14)
    path = tmp_path / "scales.json"
    path.write_text(
        json.dumps({"atom_names": list(names), "scales": [1.0] * 14}),
        encoding="utf-8",
    )
    scales, contract = module._load_frozen_selector_scales(path)
    assert scales.tolist() == [1.0] * 14
    assert contract == {
        "declared_atom_schema_version": None,
        "effective_atom_schema_version": version,
        "compatibility_policy": "exact_atom_names_on_frozen_sha_v1",
    }
    payload = json.loads(path.read_text())
    payload["atom_names"][0] = "wrong"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        module._load_frozen_selector_scales(path)

    weights_path = tmp_path / "weights.npy"
    import numpy as np

    np.save(weights_path, np.full(14, 1.0 / 14.0))
    weights = module._load_frozen_selector_weights(weights_path)
    assert weights.shape == (14,)
    solver_feasible = np.full(14, 1.0 / 14.0)
    solver_feasible[1] += solver_feasible[0] + 5e-18
    solver_feasible[0] = -5e-18
    np.save(weights_path, solver_feasible)
    with pytest.raises(ValueError, match="simplex"):
        module._load_frozen_selector_weights(weights_path)
    accepted = module._load_frozen_selector_weights(
        weights_path, nonnegative_atol=1e-9
    )
    np.testing.assert_array_equal(accepted, solver_feasible)
    solver_feasible[0] = -2e-9
    solver_feasible[1] += 2e-9 - 5e-18
    np.save(weights_path, solver_feasible)
    with pytest.raises(ValueError, match="simplex"):
        module._load_frozen_selector_weights(
            weights_path, nonnegative_atol=1e-9
        )
    np.save(weights_path, np.array([-1.0] + [2.0 / 13.0] * 13))
    with pytest.raises(ValueError, match="simplex"):
        module._load_frozen_selector_weights(weights_path)
