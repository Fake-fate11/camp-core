from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from camp_core.evaluation.diffusion_planner_v24_statistics import (
    REQUIRED_EVIDENCE_GUARDS,
    analyze_retained_pairs,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v24_paired_evaluation.json"
)
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-17-v24-paired-closed-loop-evaluation-design.md"
)


def _module():
    from scripts.integrations import prepare_diffusion_planner_v24_paired_evaluation

    return prepare_diffusion_planner_v24_paired_evaluation


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


def _evaluator():
    from scripts.integrations import evaluate_diffusion_planner_v24_pairs

    return evaluate_diffusion_planner_v24_pairs


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _route(index: int, split: str, family: str, corridor: str) -> dict:
    identity = _sha(f"route:{index}")
    map_sha = _sha(f"map:{family}")
    return {
        "record_key": f"{family}/{index}/{identity[:16]}",
        "identity_sha256": identity,
        "map_family_id": family,
        "logical_map_name": family,
        "logical_map_sha256": map_sha,
        "source_map_path": f"/maps/{family}.osm",
        "source_map_sha256": map_sha,
        "source_stratum": {"tight_corridor": False},
        "route_spec": {
            "map_path": f"/maps/{family}.osm",
            "lanelet_ids": [index + 1],
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [100.0, 0.0, 0.0],
            "route_length_m": 100.0,
        },
        "route_serialization_sha256": _sha(f"serialized:{index}"),
        "corridor_group_sha256": corridor,
        "split": split,
    }


def _sources() -> tuple[dict, dict]:
    route_specs = []
    index = 0
    for _ in range(375):
        route_specs.append(
            _route(index, "train", "map_family_train", _sha(f"train:{index // 5}"))
        )
        index += 1
    for _ in range(2):
        route_specs.append(
            _route(index, "calibration", "map_family_cal", _sha("calibration"))
        )
        index += 1
    for holdout_index in range(24):
        route_specs.append(
            _route(
                index,
                "holdout",
                "map_family_holdout",
                _sha(f"holdout-corridor:{holdout_index % 3}"),
            )
        )
        index += 1
    records = [
        {
            "record_key": route["record_key"],
            "identity_sha256": route["identity_sha256"],
            "map_family_id": route["map_family_id"],
            "corridor_group_sha256": route["corridor_group_sha256"],
            "split": route["split"],
            "seeds": list(_module().EXPECTED_SEEDS[route["split"]]),
        }
        for route in route_specs
    ]
    split = {
        "schema": "camp_dp_v24_map_family_split_manifest_v1",
        "plan_sha256": _module().SPLIT_PLAN_SHA256,
        "manifest_sha256": _module().SPLIT_MANIFEST_SHA256,
        "seed_namespaces": copy.deepcopy(_module().EXPECTED_SEEDS),
        "records": records,
        "outcome_fields_consumed": [],
        "holdout_opened": False,
        "claim_authorized": False,
    }
    census = {
        "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "retained_routes": [
            {name: value for name, value in route.items() if name not in {"split", "corridor_group_sha256"}}
            for route in route_specs
        ],
    }
    return split, census


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_v24_config_and_design_freeze_correct_policy_pairing_contract() -> None:
    config = _config()
    _module().validate_evaluation_config(config, require_all_execution_closed=False)
    assert config["pilot_execution_authorized"] is True
    assert config["main_execution_authorized"] is False
    candidate = config["candidate_contract"]
    assert candidate["per_arm_candidate_tensor_immutability_required_every_tick"]
    assert candidate["per_arm_candidate0_default_byte_identity_required_every_tick"]
    assert candidate["t0_cross_arm_input_and_candidate_hash_identity_required"]
    assert not candidate["post_divergence_cross_arm_tensor_identity_required"]
    assert not candidate["policy_level_closed_loop_claim_preclosed"]
    assert config["arm_order_policy"]["main_required_counts"] == {
        "dp_camp": 60,
        "camp_dp": 60,
    }
    text = " ".join(DESIGN.read_text(encoding="utf-8").split())
    for phrase in (
        "expected to be non-comparable across arms",
        "Pilot is exactly `1/1` and main exactly `60/60`",
        "map-family bootstrap is forbidden",
        "1,054 complete and 821 failed receipts",
        "distribution-risk disclosure",
    ):
        assert phrase in text


def test_v24_plan_covers_frozen_population_and_balances_arm_order() -> None:
    split, census = _sources()
    plan = _module().build_evaluation_plan(_config(), split, census)
    assert plan["route_counts"] == {"train": 375, "calibration": 2, "holdout": 24}
    assert plan["planned_pair_counts"] == {"capability": 1, "pilot": 2, "main": 120}
    assert plan["arm_order_counts"]["pilot"] == {"dp_camp": 1, "camp_dp": 1}
    assert plan["arm_order_counts"]["main"] == {"dp_camp": 60, "camp_dp": 60}
    assert plan["holdout_map_family_count"] == 1
    assert plan["holdout_corridor_group_count"] == 3
    assert plan["primary_ci_cluster_hierarchy"] == [
        "corridor_group_sha256",
        "route_identity_sha256",
        "seed",
    ]
    assert not plan["map_family_level_ci_authorized"]
    assert all(row["replacement_authorized"] is False for row in plan["schedules"]["main"])


def test_arm_order_is_deterministic_and_outcome_blind() -> None:
    split, census = _sources()
    first = _module().build_evaluation_plan(_config(), split, census)
    second = _module().build_evaluation_plan(_config(), split, census)
    first_order = {
        row["pair_key"]: (row["arm_order"], row["arm_order_rank_sha256"])
        for row in first["schedules"]["main"]
    }
    second_order = {
        row["pair_key"]: (row["arm_order"], row["arm_order_rank_sha256"])
        for row in second["schedules"]["main"]
    }
    assert first_order == second_order


def test_v24_plan_rejects_holdout_open_or_seed_drift() -> None:
    split, census = _sources()
    split["holdout_opened"] = True
    with pytest.raises(ValueError, match="split boundary"):
        _module().build_evaluation_plan(_config(), split, census)
    split, census = _sources()
    split["seed_namespaces"]["holdout"][-1] = 99999
    with pytest.raises(ValueError, match="seed namespaces"):
        _module().build_evaluation_plan(_config(), split, census)


def test_disabled_v24_run_configs_validate_but_cannot_authorize_holdout() -> None:
    split, census = _sources()
    plan = _module().build_evaluation_plan(_config(), split, census)
    template = json.loads(
        (ROOT / "configs" / "diffusion_planner_v22_native_capability.json").read_text(
            encoding="utf-8"
        )
    )
    planned = plan["schedules"]["main"][0]
    runtime = {
        "runtime_weights_path": "/runtime/weights.npy",
        "runtime_weights_sha256": _sha("runtime-weights"),
        "runtime_scales_path": "/runtime/scales.json",
        "runtime_scales_sha256": _sha("runtime-scales"),
        "root_sha256": _sha("runtime-root"),
        "source_model_sha256": _sha("model"),
    }
    asset = {"path": "/runtime/route.pkl", "sha256": _sha("route")}
    run_config = _module().build_evaluation_run_config(
        template, runtime, planned, asset
    )
    _runner().validate_v24_evaluation_run_config(run_config)
    assert not run_config["protocol"]["execution_authorized"]
    assert not run_config["protocol"]["holdout_access_authorized"]
    enabled = copy.deepcopy(run_config)
    enabled["protocol"]["execution_authorized"] = True
    with pytest.raises(ValueError, match="protocol"):
        _runner().validate_v24_evaluation_run_config(enabled)
    enabled["protocol"]["holdout_access_authorized"] = True
    _runner().validate_v24_evaluation_run_config(enabled)


def _candidate_tick(arm: str, tick_index: int, suffix: str) -> dict:
    rows = [_sha(f"row:{suffix}:{index}") for index in range(8)]
    selected = 0 if arm == "dp" else 3
    tick = {
        "tick_index": tick_index,
        "input_sha256": _sha(f"input:{suffix}"),
        "default_output_sha256": rows[0],
        "candidate_tensor_sha256_before": _sha(f"tensor:{suffix}"),
        "candidate_tensor_sha256_after": _sha(f"tensor:{suffix}"),
        "candidate_row_sha256": rows,
        "candidate_neighbor_sha256": _sha(f"neighbors:{suffix}"),
        "selected_trajectory_sha256": rows[selected],
        "global_rng_sha256_before": _sha("rng"),
        "global_rng_sha256_after": _sha("rng"),
        "selected_index": selected,
        "default_candidate0_identity": {
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
        },
        "selection_policy": (
            "candidate0_operational_default" if arm == "dp" else "v22_source_valid"
        ),
        "score_contract": (
            "candidate0_operational_default" if arm == "dp" else "score_k(w)=a_k^T w"
        ),
    }
    if arm == "dp":
        tick["candidate0_operational_default"] = True
    return tick


def _paired_arm(run_config: dict, arm: str) -> dict:
    first = _candidate_tick(arm, 0, "shared-t0")
    second = _candidate_tick(arm, 1, f"diverged-{arm}")
    return {
        "status": "ok",
        "route_name": run_config["routes"][0]["name"],
        "route_sha256": run_config["routes"][0]["sha256"],
        "logical_map_sha256": run_config["map"]["sha256"],
        "fixed_dp_head": run_config["fixed_dp"]["head"],
        "checkpoint_sha256": run_config["fixed_dp"]["checkpoint"]["sha256"],
        "args_sha256": run_config["fixed_dp"]["args_json"]["sha256"],
        "scenario_seed": run_config["seeds"]["scenario"],
        "initial_state_sha256": _sha("initial-state"),
        "initial_input_sha256": first["input_sha256"],
        "ticks": [first, second],
    }


def test_pair_validator_requires_t0_identity_but_not_post_divergence(monkeypatch) -> None:
    split, census = _sources()
    plan = _module().build_evaluation_plan(_config(), split, census)
    template = json.loads(
        (ROOT / "configs" / "diffusion_planner_v22_native_capability.json").read_text(
            encoding="utf-8"
        )
    )
    runtime = {
        "runtime_weights_path": "/runtime/weights.npy",
        "runtime_weights_sha256": _sha("runtime-weights"),
        "runtime_scales_path": "/runtime/scales.json",
        "runtime_scales_sha256": _sha("runtime-scales"),
        "root_sha256": _sha("runtime-root"),
        "source_model_sha256": _sha("model"),
    }
    planned = plan["schedules"]["pilot"][0]
    run_config = _module().build_evaluation_run_config(
        template,
        runtime,
        planned,
        {"path": "/runtime/route.pkl", "sha256": _sha("route")},
    )
    evaluator = _evaluator()
    monkeypatch.setattr(evaluator, "validate_native_arm_receipt", lambda *a, **k: None)
    dp = _paired_arm(run_config, "dp")
    camp = _paired_arm(run_config, "camp")
    guards = evaluator.validate_successful_pair(dp, camp, run_config)
    assert guards["t0_cross_arm_input_and_candidate_identity_verified"]
    assert not guards["post_divergence_cross_arm_tensor_compared"]
    assert dp["ticks"][1]["candidate_tensor_sha256_before"] != camp["ticks"][1][
        "candidate_tensor_sha256_before"
    ]
    camp["ticks"][0]["candidate_tensor_sha256_before"] = _sha("wrong-t0")
    camp["ticks"][0]["candidate_tensor_sha256_after"] = _sha("wrong-t0")
    with pytest.raises(ValueError, match="t0 cross-arm"):
        evaluator.validate_successful_pair(dp, camp, run_config)


def _speed_protocol() -> dict:
    return {
        "sensitivity": {
            value: {"event_rate": 0.0} for value in ("0.0", "0.05", "0.1", "0.2")
        },
        "continuous": {"magnitude_duration_m": 0.0, "excess_duration_s": 0.0},
    }


def _safety(near_miss: float) -> dict:
    components = {
        "collision_any": 0.0,
        "near_miss_noncollision_rate": near_miss,
        "offroad_rate": 0.0,
        "wrong_way_rate": 0.0,
        "red_light_violation_any": 0.0,
        "speed_limit_violation_rate": 0.0,
    }
    return {
        "schema_version": "safety_cost_native_v22",
        "safety_cost": 10.0 * near_miss,
        "components": components,
        "speed_protocol": _speed_protocol(),
    }


def _pair(index: int) -> dict:
    corridor = _sha(f"corridor:{index % 3}")
    latency_dp = {
        "default_inference": 1.0 + index,
        "tracker": 0.5,
        "total_planning": 2.0 + index,
    }
    latency_camp = {
        "default_inference": 1.0 + index,
        "candidate_inference": 2.0,
        "atom_materialization": 0.2,
        "selector": 0.1,
        "tracker": 0.5,
        "total_planning": 4.0 + index,
    }
    return {
        "pair_key": f"holdout/route-{index}/seed_24201",
        "route_retained": True,
        "included_in_denominator": True,
        "replacement_used": False,
        "paired_complete": True,
        "source_invalid": False,
        "execution_failure": False,
        "dp_status": "ok",
        "camp_status": "ok",
        "failure_class": None,
        "map_family_id": "one-held-out-family",
        "corridor_group_sha256": corridor,
        "route_identity_sha256": _sha(f"route:{index}"),
        "seed": 24201,
        "dp_safety": _safety(0.1),
        "camp_safety": _safety(0.0),
        "dp_secondary": {"route_progress_m": 10.0, "jerk_rms_mps3": 1.0},
        "camp_secondary": {"route_progress_m": 11.0, "jerk_rms_mps3": 0.8},
        "dp_tick_latency_ms": [latency_dp],
        "camp_tick_latency_ms": [latency_camp],
        "camp_selected_indices": [0, 1],
        "all_k_high_risk": index == 0,
    }


def test_v24_statistics_use_corridor_route_ci_and_strict_claim_gates() -> None:
    rows = [_pair(index) for index in range(3)]
    guards = {name: True for name in REQUIRED_EVIDENCE_GUARDS}
    result = analyze_retained_pairs(
        [row["pair_key"] for row in rows],
        rows,
        bootstrap_resamples=100,
        bootstrap_seed=24047,
        evidence_guards=guards,
        claim_evaluation=True,
    )
    assert result["bootstrap_contract"]["primary_hierarchy"] == [
        "corridor_group_sha256",
        "route_identity_sha256",
        "seed",
    ]
    assert not result["bootstrap_contract"]["map_family_cluster_level_authorized"]
    assert result["claim_decision"]["decision"] == "limited_claim"
    assert result["strata"]["overall"]["mean"] == pytest.approx(-1.0)
    assert result["candidate_selection"] == {
        "tick_count": 6,
        "candidate0_selection_count": 3,
        "non_candidate0_selection_count": 3,
        "all_k_high_risk_pair_count": 1,
    }
    camp_total = result["latency"]["camp"]["total"]
    assert camp_total["count"] == 3
    assert set(camp_total) == {"count", "mean", "median", "p95", "p99", "max"}
    assert not result["latency_comparison_authorized"]


def test_any_failed_arm_is_retained_and_forces_honest_no_claim() -> None:
    rows = [_pair(index) for index in range(3)]
    failed = rows[-1]
    failed["paired_complete"] = False
    failed["execution_failure"] = True
    failed["camp_status"] = "failed"
    failed["failure_class"] = "execution_failure"
    failed.pop("camp_safety")
    guards = {name: True for name in REQUIRED_EVIDENCE_GUARDS}
    result = analyze_retained_pairs(
        [row["pair_key"] for row in rows],
        rows,
        bootstrap_resamples=20,
        evidence_guards=guards,
        claim_evaluation=True,
    )
    assert result["coverage"]["retention_rate"] == 1.0
    assert result["coverage"]["paired_complete_rate"] == pytest.approx(2 / 3)
    assert result["claim_decision"]["decision"] == "honest_no_claim"
    assert result["failure_accounting"]["camp_status"]["failed"] == 1


def test_learning_curve_concentration_is_disclosed_not_repaired() -> None:
    config = _config()
    stability = config["learning_curve_stability"]
    assert stability["effective_support_gt_1e_6"] == [3, 3, 3, 3]
    assert stability["full_effective_support_names"] == [
        "lane_deviation",
        "clearance",
        "dp_prior_jerk_excess_cost",
    ]
    assert stability["risk_disclosure_required"]
    assert not stability["distribution_concentration_is_automatic_failure"]
    assert not stability["calibration_or_holdout_repair_authorized"]


def test_static_preflight_and_reviewer_cannot_execute_runtime() -> None:
    producer = (
        ROOT
        / "scripts"
        / "integrations"
        / "prepare_diffusion_planner_v24_paired_evaluation.py"
    ).read_text(encoding="utf-8")
    reviewer = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v24_paired_preflight.py"
    ).read_text(encoding="utf-8")
    for source in (producer, reviewer):
        calls = {
            node.func.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls.intersection(
            {"run_route_replay", "build_native_arm_runner", "execute_mode"}
        )
