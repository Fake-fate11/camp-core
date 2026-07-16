from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "camp_core"
for _path in (REPO_ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.evaluation.diffusion_planner_v24_statistics import (
    analyze_retained_pairs,
)
from scripts.integrations import (
    review_diffusion_planner_v24_holdout_main_result as review,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git_oid(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _main_config(route_index: int, seed: int) -> dict:
    route_name = _sha(f"route-{route_index}")
    corridor = _sha(f"corridor-{route_index % 3}")
    return {
        "schema_version": "camp_dp_v24_native_evaluation_run_v1",
        "fixed_dp": {
            "repo": "/fixed/dp",
            "head": review.FIXED_DP_HEAD,
            "checkpoint": {"path": "/fixed/model.pth", "sha256": _sha("checkpoint")},
            "args_json": {"path": "/fixed/args.json", "sha256": _sha("args")},
            "native_source_sha256": {"opaque": _sha("native")},
        },
        "selector": {
            "root": "/preflight/runtime_selector",
            "root_sha256": _sha("selector-root"),
            "model_sha256": _sha("selector-model"),
            "atom_scales": {"path": "/preflight/runtime_selector/atom_scales.json", "sha256": _sha("scales")},
            "weights": {"path": "/preflight/runtime_selector/weights.npy", "sha256": _sha("weights")},
            "score_contract": "score_k(w)=a_k^T w",
            "nonnegative_simplex": True,
            "candidate_k": 8,
            "selection_policy": "v22_source_valid",
            "role": "v24_primary_frozen_train_only",
        },
        "map": {
            "path": "/map.osm",
            "sha256": _sha("map-file"),
            "map_family_id": "held-out-family",
            "logical_map_sha256": _sha("logical-map"),
            "corridor_group_sha256": corridor,
        },
        "routes": [
            {"name": route_name, "path": f"/routes/{route_name}.pkl", "sha256": _sha(f"route-asset-{route_index}")}
        ],
        "seeds": {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13],
        },
        "spawn_config": {
            "seed": seed,
            "max_steps": 64,
            "advance_mode": "mpc",
        },
        "protocol": {
            "evaluation_mode": "main",
            "evaluation_split": "holdout",
            "evaluation_steps": 64,
            "arm_order": None,
            "arm_order_rank_sha256": None,
            "independent_reset_per_arm": True,
            "same_initial_state_and_exogenous_seed_per_pair": True,
            "safety_schema": "safety_cost_native_v22",
            "route_retention": "all_preregistered_routes_and_failures_no_replacement",
            "training_authorized": False,
            "calibration_tuning_authorized": False,
            "execution_authorized": False,
            "holdout_access_authorized": False,
            "formal_seeds_authorized": False,
            "candidate_tensor_modification_authorized": False,
            "trajectory_postprocess_authorized": False,
            "per_arm_candidate_tensor_immutability_required": True,
            "per_arm_candidate0_default_identity_required": True,
            "t0_cross_arm_input_and_candidate_hash_identity_required": True,
            "post_divergence_cross_arm_tensor_identity_required": False,
            "native_ranked_k8_provenance_claim_authorized": False,
            "latency_comparison_authorized": False,
            "latency_reporting_role": "descriptive_instrumented_only",
            "claim_authorized": False,
        },
    }


def _write_synthetic_preflight(root: Path) -> list[dict]:
    main = [
        _main_config(route_index, seed)
        for route_index in range(24)
        for seed in review.HOLDOUT_SEEDS
    ]
    keys = [
        f"holdout/{item['routes'][0]['name']}/seed_{item['seeds']['scenario']}"
        for item in main
    ]
    ranked = sorted(keys, key=review._rank_sha256)
    orders = {
        key: ["dp", "camp"] if index < 60 else ["camp", "dp"]
        for index, key in enumerate(ranked)
    }
    public = []
    receipts = []
    for item, key in zip(main, keys):
        protocol = item["protocol"]
        protocol["arm_order"] = orders[key]
        protocol["arm_order_rank_sha256"] = review._rank_sha256(key)
        public.append(
            {
                "schema": "camp_dp_v24_planned_pair_v1",
                "mode": "main",
                "split": "holdout",
                "pair_key": key,
                "receipt_key": f"{key}/pair.json",
                "record_key": f"record-{key}",
                "route_identity_sha256": item["routes"][0]["name"],
                "map_family_id": item["map"]["map_family_id"],
                "logical_map_sha256": item["map"]["logical_map_sha256"],
                "corridor_group_sha256": item["map"]["corridor_group_sha256"],
                "seed": item["seeds"]["scenario"],
                "max_steps": 64,
                "expected_arms": ["dp", "camp"],
                "included_in_denominator": True,
                "replacement_authorized": False,
                "arm_order": protocol["arm_order"],
                "arm_order_rank_sha256": protocol["arm_order_rank_sha256"],
            }
        )
        receipts.append(
            {
                "pair_key": key,
                "mode": "main",
                "config_sha256": review._canonical_sha256(item),
                "execution_authorized": False,
                "holdout_access_authorized": False,
            }
        )
    dummy = [
        {"protocol": {"evaluation_mode": "capability"}},
        {"protocol": {"evaluation_mode": "pilot"}},
        {"protocol": {"evaluation_mode": "pilot"}},
    ]
    root.mkdir()
    (root / "disabled_run_configs.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in dummy + main),
        encoding="utf-8",
    )
    _write_json(root / "run_config_receipts.json", receipts)
    plan = {
        "schema": "camp_dp_v24_native_paired_evaluation_plan_v1",
        "schedules": {"capability": [], "pilot": [], "main": public},
    }
    plan["plan_sha256"] = review._canonical_sha256(plan)
    _write_json(root / "evaluation_plan.json", plan)
    return main


def _safety_record(index: int) -> dict:
    return {
        "tick_index": index,
        "position_xy": [0.1 * index, 0.0],
        "speed_mps": 1.0,
        "ego_heading_rad": 0.0,
        "route_heading_rad": 0.0,
        "route_progress_m": 0.1 * index,
        "five_point_drivable_coverage": True,
        "min_obb_clearance_m": 10.0,
        "red_light_at_interval_start": False,
        "front_center_prev_xy": [0.1 * index, 0.0],
        "front_center_xy": [0.1 * index + 0.1, 0.0],
        "red_stop_lines": [],
        "speed_limit_mps": 2.0,
        "constant_velocity_circle_ttc_diagnostic_s": None,
        "source_complete": True,
    }


def _tick(arm: str, index: int, *, shared: bool = False) -> dict:
    prefix = "shared" if shared else arm
    rows = [_sha(f"{prefix}-row-{index}-{candidate}") for candidate in range(8)]
    selected = 0 if arm == "dp" else 1
    latency = {
        "default_inference": 1.0,
        "candidate_inference": 2.0,
        "tracker": 3.0,
        "total_planning": 8.0,
    }
    if arm == "camp":
        latency.update({"atom_materialization": 1.0, "selector": 0.1})
    tick = {
        # Deliberately no top-level native_ranked_k8: this matches public receipts.
        "tick_index": index,
        "input_sha256": _sha(f"{prefix}-input-{index}"),
        "padding": {
            "observed_frames": 31,
            "padded_frames": 0,
            "padding_policy": "native_zero_left_pad_to_31_v1",
        },
        "tracker": {"status": "ok"},
        "safety": _safety_record(index),
        "latency_ms": latency,
        "default_output_sha256": rows[0],
        "candidate_tensor_sha256_before": _sha(f"{prefix}-tensor-{index}"),
        "candidate_tensor_sha256_after": _sha(f"{prefix}-tensor-{index}"),
        "candidate_neighbor_sha256": _sha(f"{prefix}-neighbors-{index}"),
        "candidate_row_sha256": rows,
        "selected_trajectory_sha256": rows[selected],
        "global_rng_sha256_before": _sha(f"{prefix}-rng-{index}"),
        "global_rng_sha256_after": _sha(f"{prefix}-rng-{index}"),
        "selected_index": selected,
        "default_candidate0_identity": {
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "native_ranked_k8": False,
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
        },
        "npc_operational_outputs_unchanged": True,
    }
    if arm == "dp":
        tick.update(
            {
                "selection_policy": "candidate0_operational_default",
                "score_contract": "candidate0_operational_default",
                "eligibility_mask_name": "candidate0_operational_default",
                "candidate0_operational_default": True,
                "post_divergence_cross_arm_tensor_identity_required": False,
            }
        )
    else:
        tick.update(
            {
                "selection_policy": "v22_source_valid",
                "score_contract": "score_k(w)=a_k^T w",
                "eligibility_mask_name": "source_valid_mask",
                "atom_matrix_sha256": _sha(f"{prefix}-atoms-{index}"),
                "scores": [1.0, 0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                "source_valid_mask": [True] * 8,
                "source_complete_mask": [True] * 8,
                "physical_feasible_mask": [True] * 8,
                "all_k_high_risk": False,
                # Deliberately no per-tick post-divergence flag on CAMP.
            }
        )
    return tick


def _arm_receipt(config: dict, arm: str) -> dict:
    ticks = [_tick(arm, index, shared=index == 0) for index in range(64)]
    initial_input = ticks[0]["input_sha256"]
    initial_state = hashlib.sha256(
        ("v21_native_scene_context_v1\0" + initial_input).encode("ascii")
    ).hexdigest()
    secondary_stub = {
        "route_progress_m": ticks[-1]["safety"]["route_progress_m"],
        "route_length_m": 10.0,
        "termination_reason": "max_steps",
    }
    native_result = {"reason": "max_steps"}
    secondary = review.recompute_secondary(
        ticks,
        secondary_stub,
        native_result,
        expected_route_length_m=10.0,
    )
    receipt = {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": arm,
        "route_name": config["routes"][0]["name"],
        "route_sha256": config["routes"][0]["sha256"],
        "logical_map_sha256": config["map"]["sha256"],
        "fixed_dp_head": review.FIXED_DP_HEAD,
        "checkpoint_sha256": config["fixed_dp"]["checkpoint"]["sha256"],
        "args_sha256": config["fixed_dp"]["args_json"]["sha256"],
        "scenario_seed": config["seeds"]["scenario"],
        "spawn_config_sha256": review._spawn_sha256(config),
        "initial_state_sha256": initial_state,
        "initial_input_sha256": initial_input,
        "ticks": ticks,
        "native_result": native_result,
        "safety": review.recompute_safety(ticks),
        "secondary": secondary,
        "latency": review._recompute_arm_latency(ticks),
        "claim_authorized": False,
        "evaluation_wall_clock_s": 2.0,
    }
    if arm == "camp":
        receipt["selector_scale_contract"] = {
            "declared_atom_schema_version": "dp_camp_v10_14d",
            "effective_atom_schema_version": "dp_camp_v10_14d",
            "compatibility_policy": "exact_atom_names_on_frozen_sha_v1",
        }
    return receipt


def _statistics_row(index: int) -> dict:
    dp_cost = 10.0 + index
    camp_cost = dp_cost - 1.0
    components = {
        "collision_any": 0.0,
        "near_miss_noncollision_rate": 0.0,
        "offroad_rate": 0.0,
        "wrong_way_rate": 0.0,
        "red_light_violation_any": 0.0,
        "speed_limit_violation_rate": 0.0,
    }

    def safety(cost: float) -> dict:
        return {
            "schema_version": "safety_cost_native_v22",
            "safety_cost": cost,
            "components": components,
            "speed_protocol": {
                "sensitivity": {
                    key: {"event_rate": 0.0} for key in review.SPEED_TOLERANCES
                },
                "continuous": {
                    "maximum_excess_mps": 0.0,
                    "mean_excess_mps": 0.0,
                    "excess_duration_s": 0.0,
                    "magnitude_duration_m": 0.0,
                },
            },
        }

    dp_latency = {"default_inference": 1.0, "tracker": 2.0, "total_planning": 3.0}
    camp_latency = {
        "default_inference": 1.0,
        "candidate_inference": 2.0,
        "atom_materialization": 0.5,
        "selector": 0.1,
        "tracker": 2.0,
        "total_planning": 5.0,
    }
    return {
        "pair_key": f"pair-{index}",
        "route_retained": True,
        "included_in_denominator": True,
        "replacement_used": False,
        "paired_complete": True,
        "source_invalid": False,
        "execution_failure": False,
        "dp_status": "ok",
        "camp_status": "ok",
        "failure_class": None,
        "map_family_id": "family",
        "corridor_group_sha256": f"corridor-{index % 3}",
        "route_identity_sha256": f"route-{index % 3}",
        "seed": 100 + index,
        "all_k_high_risk": index == 0,
        "dp_safety": safety(dp_cost),
        "camp_safety": safety(camp_cost),
        "dp_secondary": {"route_progress_m": 5.0, "mean_abs_jerk_mps3": 1.0},
        "camp_secondary": {"route_progress_m": 6.0, "mean_abs_jerk_mps3": 0.5},
        "dp_tick_latency_ms": [dp_latency],
        "camp_tick_latency_ms": [camp_latency],
        "camp_selected_indices": [index % 8],
        "camp_tick_receipts": [{"all_k_high_risk": index == 0}],
    }


def _synthetic_route_census_and_split() -> tuple[dict, dict]:
    retained = []
    records = []
    for index in range(401):
        split = "train" if index < 375 else "calibration" if index < 377 else "holdout"
        family = f"{split}-family"
        logical_map = _sha(f"logical-{family}")
        geometry = _sha(f"geometry-{index}")
        identity = review._canonical_sha256(
            {
                "logical_map_sha256": logical_map,
                "source_geometry_sha256": geometry,
            }
        )
        source_map_path = f"/maps/{family}.osm"
        route_length = 80.0 + index / 100.0
        route_spec = {
            "map_path": source_map_path,
            "lanelet_ids": [index + 1],
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [route_length, 0.0, 0.0],
            "route_length_m": route_length,
        }
        record_key = f"{family}/record-{index}"
        retained.append(
            {
                "record_key": record_key,
                "identity_sha256": identity,
                "logical_map_sha256": logical_map,
                "map_family_id": family,
                "source_map_path": source_map_path,
                "source_map_sha256": _sha(f"map-{family}"),
                "lanelet_ids": [index + 1],
                "route_spec": route_spec,
                "route_serialization_sha256": review._canonical_sha256(route_spec),
                "source_geometry_sha256": geometry,
                "source_arc_length_m": 90.0 + index / 100.0,
                "source_route_length_m": route_length,
            }
        )
        records.append(
            {
                "record_key": record_key,
                "identity_sha256": identity,
                "map_family_id": family,
                "corridor_group_sha256": _sha(
                    f"corridor-{index % 3 if split == 'holdout' else split}"
                ),
                "split": split,
                "seeds": list(review.HOLDOUT_SEEDS) if split == "holdout" else [1],
            }
        )
    return (
        {
            "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
            "route_census_completed": True,
            "model_loaded": False,
            "candidate_generation_started": False,
            "outcome_accessed": False,
            "holdout_opened": False,
            "retained_routes": retained,
        },
        {"records": records},
    )


def test_source_is_independent_and_has_no_simulator_or_dynamic_escape() -> None:
    source = Path(review.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_modules = (
        "evaluate_diffusion_planner_v24_pairs",
        "prepare_diffusion_planner_v24_paired_evaluation",
        "diffusion_planner_v24_statistics",
        "run_diffusion_planner_dp_camp_v21_native",
    )
    imported = []
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.append(node.func.attr)
    assert not any(token in name for token in forbidden_modules for name in imported)
    assert not {"eval", "exec", "__import__"} & set(called)
    assert "importlib" not in imported
    assert "run_route_replay(" not in source
    assert "build_native_arm_runner(" not in source


def test_strict_json_and_numeric_types_reject_ambiguous_inputs() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        review._loads_json('{"outer":{"value":1,"value":2}}')
    for value in (
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
        '{"outer":{"value":1e999}}',
    ):
        with pytest.raises(ValueError, match="non-finite"):
            review._loads_json(value)
    with pytest.raises(ValueError, match="numeric"):
        review._finite("1.0", "value")
    with pytest.raises(ValueError, match="integer"):
        review._integer(True, "count")


def test_complete_seal_rejects_mutation_extra_duplicate_backslash_and_symlink(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "payload.txt").write_text("payload\n", encoding="utf-8")
    digest = review.seal_artifact(root)
    assert review.verify_complete_seal(root, digest, "test")["file_count"] == 1

    (root / "extra.txt").write_text("extra\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        review.verify_complete_seal(root, digest, "test")
    (root / "extra.txt").unlink()

    line = (root / "SHA256SUMS").read_text(encoding="utf-8").strip()
    (root / "SHA256SUMS").write_text(f"{line}\n{line}\n", encoding="utf-8")
    duplicate_root = review._sha256_file(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{duplicate_root}  SHA256SUMS\n", encoding="ascii"
    )
    with pytest.raises(ValueError, match="duplicate"):
        review.verify_complete_seal(root, duplicate_root, "test")

    digest = review.seal_artifact(root)
    payload_sha = review._sha256_file(root / "payload.txt")
    (root / "SHA256SUMS").write_text(
        f"{payload_sha}  ..\\escape\n", encoding="utf-8"
    )
    backslash_root = review._sha256_file(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{backslash_root}  SHA256SUMS\n", encoding="ascii"
    )
    with pytest.raises(ValueError, match="unsafe"):
        review.verify_complete_seal(root, backslash_root, "test")

    digest = review.seal_artifact(root)
    nested = root / "nested"
    nested.mkdir()
    (nested / "SHA256SUMS").write_text("unsealed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        review.verify_complete_seal(root, digest, "test")

    link = tmp_path / "artifact-link"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError:
        return
    with pytest.raises(ValueError, match="symlink"):
        review.verify_complete_seal(link, digest, "test")


def test_schedule_reconstructs_exact_hash_rank_and_rejects_balanced_swap(
    tmp_path: Path,
) -> None:
    root = tmp_path / "preflight"
    _write_synthetic_preflight(root)
    schedule = review.reconstruct_main_schedule(root)
    assert schedule["receipt"]["arm_order_counts"] == {"dp_camp": 60, "camp_dp": 60}
    assert schedule["receipt"]["deterministic_hash_rank_verified"] is True
    assert schedule["receipt"]["outcome_blind_preregistered_order_control_verified"] is True
    assert schedule["receipt"]["independent_reset_per_arm_verified"] is True
    assert schedule["receipt"]["latency_comparative_conclusion_authorized"] is False

    lines = (root / "disabled_run_configs.jsonl").read_text(encoding="utf-8").splitlines()
    payloads = [json.loads(line) for line in lines]
    main_indices = [index for index, item in enumerate(payloads) if item["protocol"]["evaluation_mode"] == "main"]
    dp_index = next(index for index in main_indices if payloads[index]["protocol"]["arm_order"] == ["dp", "camp"])
    camp_index = next(index for index in main_indices if payloads[index]["protocol"]["arm_order"] == ["camp", "dp"])
    payloads[dp_index]["protocol"]["arm_order"] = ["camp", "dp"]
    payloads[camp_index]["protocol"]["arm_order"] = ["dp", "camp"]
    (root / "disabled_run_configs.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in payloads),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="deterministic balanced"):
        review.reconstruct_main_schedule(root)

    metadata_root = tmp_path / "metadata-preflight"
    _write_synthetic_preflight(metadata_root)
    payloads = [
        json.loads(line)
        for line in (metadata_root / "disabled_run_configs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    first_main = next(
        item
        for item in payloads
        if item["protocol"]["evaluation_mode"] == "main"
    )
    same_route_other_seed = next(
        item
        for item in payloads
        if item["protocol"]["evaluation_mode"] == "main"
        and item["routes"][0]["name"] == first_main["routes"][0]["name"]
        and item["seeds"]["scenario"] != first_main["seeds"]["scenario"]
    )
    same_route_other_seed["map"]["corridor_group_sha256"] = _sha(
        "different-corridor"
    )
    (metadata_root / "disabled_run_configs.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in payloads),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="changes metadata"):
        review.reconstruct_main_schedule(metadata_root)


def test_arm_receipts_validate_real_public_schema_and_mutations() -> None:
    config = _main_config(0, review.HOLDOUT_SEEDS[0])
    key = f"holdout/{config['routes'][0]['name']}/seed_{config['seeds']['scenario']}"
    config["protocol"]["arm_order"] = ["dp", "camp"]
    config["protocol"]["arm_order_rank_sha256"] = review._rank_sha256(key)
    dp = _arm_receipt(config, "dp")
    camp = _arm_receipt(config, "camp")
    assert review.validate_arm_receipt(
        dp, "dp", config, expected_route_length_m=10.0
    )["status"] == "ok"
    assert review.validate_arm_receipt(
        camp, "camp", config, expected_route_length_m=10.0
    )["status"] == "ok"
    review.validate_paired_reset_and_t0(dp, camp, key)

    # Post-t=0 state-conditioned tensors may diverge and are never compared.
    assert dp["ticks"][1]["candidate_tensor_sha256_before"] != camp["ticks"][1]["candidate_tensor_sha256_before"]
    review.validate_paired_reset_and_t0(dp, camp, key)

    mutations = []
    changed = copy.deepcopy(camp)
    changed["ticks"][2]["candidate_tensor_sha256_after"] = _sha("changed")
    mutations.append(changed)
    changed = copy.deepcopy(camp)
    changed["ticks"][2]["selected_index"] = 2
    changed["ticks"][2]["selected_trajectory_sha256"] = changed["ticks"][2]["candidate_row_sha256"][2]
    mutations.append(changed)
    changed = copy.deepcopy(camp)
    changed["ticks"][2]["global_rng_sha256_after"] = _sha("changed-rng")
    mutations.append(changed)
    changed = copy.deepcopy(camp)
    changed["ticks"][2]["npc_operational_outputs_unchanged"] = False
    mutations.append(changed)
    changed = copy.deepcopy(camp)
    changed["ticks"][2]["safety"]["min_obb_clearance_m"] = 0.0
    # Stored arm safety is deliberately unchanged: raw-tick recomputation catches it.
    mutations.append(changed)
    for mutated in mutations:
        with pytest.raises(ValueError):
            review.validate_arm_receipt(
                mutated, "camp", config, expected_route_length_m=10.0
            )

    t0_changed = copy.deepcopy(camp)
    t0_changed["ticks"][0]["candidate_neighbor_sha256"] = _sha("different-neighbor")
    with pytest.raises(ValueError, match="t0 cross-arm"):
        review.validate_paired_reset_and_t0(dp, t0_changed, key)

    length_changed = copy.deepcopy(camp)
    length_changed["secondary"]["route_length_m"] = 11.0
    with pytest.raises(ValueError, match="route-length denominator"):
        review.validate_paired_reset_and_t0(dp, length_changed, key)

    jointly_wrong_dp = copy.deepcopy(dp)
    jointly_wrong_camp = copy.deepcopy(camp)
    jointly_wrong_dp["secondary"]["route_length_m"] = 11.0
    jointly_wrong_camp["secondary"]["route_length_m"] = 11.0
    # Cross-arm equality alone passes, but each arm must match sealed source census.
    review.validate_paired_reset_and_t0(jointly_wrong_dp, jointly_wrong_camp, key)
    for arm_name, arm_receipt in (
        ("dp", jointly_wrong_dp),
        ("camp", jointly_wrong_camp),
    ):
        with pytest.raises(ValueError, match="source-census arc length"):
            review.validate_arm_receipt(
                arm_receipt,
                arm_name,
                config,
                expected_route_length_m=10.0,
            )


def test_request_assets_are_independently_hashed_and_route_bound(
    tmp_path: Path,
) -> None:
    dp_root = tmp_path / "fixed-dp"
    dp_root.mkdir()
    checkpoint = dp_root / "model.pth"
    args_json = dp_root / "args.json"
    native_source = dp_root / "native.py"
    checkpoint.write_bytes(b"checkpoint\n")
    args_json.write_text("{}\n", encoding="utf-8")
    native_source.write_text("NATIVE = True\n", encoding="utf-8")

    preflight = tmp_path / "preflight"
    route_root = preflight / "routes"
    route_root.mkdir(parents=True)
    map_path = tmp_path / "map.osm"
    map_path.write_text("<osm version=\"0.6\"/>\n", encoding="utf-8")

    fixed_dp = {
        "repo": str(dp_root),
        "head": review.FIXED_DP_HEAD,
        "checkpoint": {
            "path": str(checkpoint),
            "sha256": review._sha256_file(checkpoint),
        },
        "args_json": {
            "path": str(args_json),
            "sha256": review._sha256_file(args_json),
        },
        "native_source_sha256": {
            "native.py": review._sha256_file(native_source),
        },
    }
    configs = []
    for route_index in range(24):
        config = _main_config(route_index, review.HOLDOUT_SEEDS[0])
        route_path = route_root / f"route-{route_index}.pkl"
        route_path.write_bytes(f"route-{route_index}\n".encode("ascii"))
        config["fixed_dp"] = fixed_dp
        config["routes"][0].update(
            {
                "path": str(route_path),
                "sha256": review._sha256_file(route_path),
            }
        )
        config["map"].update(
            {"path": str(map_path), "sha256": review._sha256_file(map_path)}
        )
        configs.append(config)

    receipt = review._verify_request_assets({"configs": configs}, preflight)
    assert receipt["route_asset_count"] == 24
    assert receipt["map_asset_count"] == 1
    assert receipt["same_fixed_dp_request_all_pairs"] is True

    changed_asset = copy.deepcopy(configs[0])
    changed_path = route_root / "route-0-other-seed.pkl"
    changed_path.write_bytes(b"different serialized route\n")
    changed_asset["routes"][0].update(
        {
            "path": str(changed_path),
            "sha256": review._sha256_file(changed_path),
        }
    )
    with pytest.raises(ValueError, match="changes route-asset SHA"):
        review._verify_request_assets(
            {"configs": [*configs, changed_asset]}, preflight
        )

    Path(configs[0]["routes"][0]["path"]).write_bytes(b"mutated\n")
    with pytest.raises(ValueError, match="route asset"):
        review._verify_request_assets({"configs": configs}, preflight)


def test_route_census_arc_lengths_and_split_schedule_join_are_independent() -> None:
    census, split = _synthetic_route_census_and_split()
    sources = review._build_route_source_bindings(census, split)
    assert len(sources) == 24
    assert all(source["source_arc_length_m"] > 0.0 for source in sources.values())

    metadata = {}
    public = []
    for identity, source in sources.items():
        metadata[identity] = {
            "map_family_id": source["map_family_id"],
            "logical_map_sha256": source["logical_map_sha256"],
            "corridor_group_sha256": source["corridor_group_sha256"],
            "source_map_path": source["source_map_path"],
            "source_map_sha256": source["source_map_sha256"],
            "route_asset_path": f"/routes/{identity}.pkl",
            "route_asset_sha256": _sha(f"asset-{identity}"),
        }
        public.extend(
            {
                "route_identity_sha256": identity,
                "record_key": source["record_key"],
                "seed": seed,
            }
            for seed in review.HOLDOUT_SEEDS
        )
    schedule = {
        "route_metadata": metadata,
        "plan": {"schedules": {"main": public}},
    }
    review._verify_schedule_route_source_bindings(schedule, sources)

    wrong_corridor = copy.deepcopy(schedule)
    identity = next(iter(sources))
    wrong_corridor["route_metadata"][identity]["corridor_group_sha256"] = _sha(
        "wrong-corridor"
    )
    with pytest.raises(ValueError, match="schedule source route"):
        review._verify_schedule_route_source_bindings(wrong_corridor, sources)

    wrong_record = copy.deepcopy(schedule)
    wrong_record["plan"]["schedules"]["main"][0]["record_key"] = "wrong-record"
    with pytest.raises(ValueError, match="record key"):
        review._verify_schedule_route_source_bindings(wrong_record, sources)

    bad_census = copy.deepcopy(census)
    bad_census["retained_routes"][-1]["source_arc_length_m"] = 0.0
    with pytest.raises(ValueError, match="source length"):
        review._build_route_source_bindings(bad_census, split)


def test_frozen_metric_contract_validates_train_and_learning_curve_risk() -> None:
    config_path = REPO_ROOT / "configs/integrations/diffusion_planner_v24_paired_evaluation.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    receipt = review._verify_frozen_metric_contract(config)
    assert receipt["train_route_seed_source_coverage_disclosure"] == {
        "retained": 1875,
        "complete": 1054,
        "failed": 821,
        "failure_rate": pytest.approx(821 / 1875),
    }
    assert receipt["learning_curve_stability"]["levels_percent"] == [25, 50, 75, 100]
    assert receipt["learning_curve_stability"]["effective_support_gt_1e_6"] == [3, 3, 3, 3]
    assert receipt["learning_curve_stability"]["full_effective_support_indices"] == [7, 8, 13]
    assert receipt["distribution_concentration_risk_disclosed"] is True

    mutations = []
    changed = copy.deepcopy(config)
    changed["coverage_execution_contract"]["train_route_seed_source_coverage_disclosure"]["failed"] = 820
    mutations.append(changed)
    changed = copy.deepcopy(config)
    changed["learning_curve_stability"]["weights_l1_to_full"][0] += 0.01
    mutations.append(changed)
    changed = copy.deepcopy(config)
    changed["statistics"]["latency_quantiles"] = [0.5, 0.9, 0.99]
    mutations.append(changed)
    changed = copy.deepcopy(config)
    changed["claim_contract"]["paired_complete_rate_required"] = 0.9
    mutations.append(changed)
    for mutated in mutations:
        with pytest.raises(ValueError):
            review._verify_frozen_metric_contract(mutated)


def test_preflight_and_gate50_pilot_review_are_strictly_cross_bound(
    tmp_path: Path,
) -> None:
    preflight_sha = _sha("preflight-root")
    pilot_review_sha = _sha("pilot-review-root")
    authorization_sha = _sha("authorization-root")
    config_sha = _sha("config")
    preflight_head = _git_oid("preflight-head")
    pilot_review_head = _git_oid("pilot-review-head")
    pilot_execution_head = _git_oid("pilot-execution-head")
    roots = {
        name: tmp_path / name
        for name in (
            "preflight",
            "preflight-review",
            "pilot-review",
            "authorization",
            "authorization-review",
        )
    }
    for root in roots.values():
        root.mkdir()
    preflight = {
        "schema": "camp_dp_v24_native_paired_evaluation_static_preflight_v1",
        "status": "passed",
        "check_count": 1,
        "failed_count": 0,
        "failed_checks": [],
        "checks": {"all_static_checks": True},
        "config_sha256": config_sha,
        "camp_head": preflight_head,
        "fixed_dp_head": review.FIXED_DP_HEAD,
        "planned_pair_counts": {"main": 120},
        "holdout_opened": False,
        "holdout_open_count": 0,
        "outcome_fields_consumed": [],
    }
    preflight_review = {
        "status": "passed",
        "failed_count": 0,
        "source_preflight_root_sha256": preflight_sha,
    }
    pilot_review = {
        "schema": "camp_dp_v24_paired_calibration_pilot_independent_review_v1",
        "status": "passed",
        "check_count": 1,
        "failed_count": 0,
        "failed_checks": [],
        "checks": {"all_pilot_checks": True},
        "source_roots": {"preflight": {"root_sha256": preflight_sha}},
        "camp_head": pilot_review_head,
        "execution_source_head": pilot_execution_head,
        "fixed_dp_head": review.FIXED_DP_HEAD,
        "source_execution_reexecuted": False,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "latency_comparison_authorized": False,
        "main_execution_authorized": False,
    }
    authorization = {
        "status": "passed",
        "failed_count": 0,
        "main_pair_count": 120,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "main_execution_authorized": False,
        "source_roots": {
            "preflight": {"root_sha256": preflight_sha},
            "pilot_review": {"root_sha256": pilot_review_sha},
        },
    }
    authorization_review = {
        "status": "passed",
        "failed_count": 0,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "source_roots": {
            "authorization": {"root_sha256": authorization_sha},
            "preflight": {"root_sha256": preflight_sha},
            "pilot_review": {"root_sha256": pilot_review_sha},
        },
    }

    def write_receipts() -> None:
        _write_json(roots["preflight"] / "preflight_result.json", preflight)
        _write_json(
            roots["preflight-review"] / "review_result.json", preflight_review
        )
        _write_json(roots["pilot-review"] / "review_result.json", pilot_review)
        _write_json(
            roots["authorization"] / "authorization_result.json", authorization
        )
        _write_json(
            roots["authorization-review"] / "review_result.json",
            authorization_review,
        )

    def verify() -> None:
        review._verify_chain_receipts(
            preflight_root=roots["preflight"],
            preflight_review_root=roots["preflight-review"],
            pilot_review_root=roots["pilot-review"],
            authorization_root=roots["authorization"],
            authorization_review_root=roots["authorization-review"],
            expected_preflight_root_sha256=preflight_sha,
            expected_pilot_review_root_sha256=pilot_review_sha,
            expected_authorization_root_sha256=authorization_sha,
            expected_preflight_config_sha256=config_sha,
            expected_preflight_camp_head=preflight_head,
            expected_pilot_review_camp_head=pilot_review_head,
            expected_pilot_execution_source_head=pilot_execution_head,
        )

    write_receipts()
    verify()
    mutations = (
        (preflight, "config_sha256", _sha("wrong-config")),
        (pilot_review["source_roots"]["preflight"], "root_sha256", _sha("wrong-preflight")),
        (pilot_review, "execution_source_head", _git_oid("wrong-source")),
        (pilot_review["checks"], "all_pilot_checks", False),
    )
    for target, field, wrong in mutations:
        original = target[field]
        target[field] = wrong
        write_receipts()
        with pytest.raises(ValueError):
            verify()
        target[field] = original
    write_receipts()


def test_config_and_evaluator_blob_pins_reject_wrong_sha_or_live_bytes() -> None:
    config_blob = b'{"schema":"frozen"}\n'
    evaluator_blob = b"def evaluate():\n    return None\n"
    receipt = review._verify_pinned_source_blobs(
        config_blob=config_blob,
        live_config_blob=config_blob,
        expected_config_sha256=hashlib.sha256(config_blob).hexdigest(),
        evaluator_blob=evaluator_blob,
        expected_evaluator_sha256=hashlib.sha256(evaluator_blob).hexdigest(),
    )
    assert receipt == {
        "config_blob_sha256": hashlib.sha256(config_blob).hexdigest(),
        "evaluator_blob_sha256": hashlib.sha256(evaluator_blob).hexdigest(),
    }
    with pytest.raises(ValueError, match="config"):
        review._verify_pinned_source_blobs(
            config_blob=config_blob,
            live_config_blob=b"mutated\n",
            expected_config_sha256=hashlib.sha256(config_blob).hexdigest(),
            evaluator_blob=evaluator_blob,
            expected_evaluator_sha256=hashlib.sha256(evaluator_blob).hexdigest(),
        )
    with pytest.raises(ValueError, match="evaluator"):
        review._verify_pinned_source_blobs(
            config_blob=config_blob,
            live_config_blob=config_blob,
            expected_config_sha256=hashlib.sha256(config_blob).hexdigest(),
            evaluator_blob=evaluator_blob,
            expected_evaluator_sha256=_sha("wrong-evaluator"),
        )
def test_hand_derived_raw_tick_safety_secondary_and_latency_oracle() -> None:
    positions = ([0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [2.0, 1.0])
    speeds = (2.2, 1.0, 0.4, 2.05)
    headings = (0.0, np.pi, 0.0, 0.0)
    coverages = (True, True, False, True)
    clearances = (0.0, 1.0, 3.0, 10.0)
    ticks = []
    for index in range(4):
        safety = _safety_record(index)
        safety.update(
            {
                "position_xy": list(positions[index]),
                "speed_mps": speeds[index],
                "ego_heading_rad": headings[index],
                "route_heading_rad": 0.0,
                "route_progress_m": float(index),
                "five_point_drivable_coverage": coverages[index],
                "min_obb_clearance_m": clearances[index],
                "speed_limit_mps": 2.0 if coverages[index] else None,
                "red_light_at_interval_start": index == 1,
                "front_center_prev_xy": [0.0, -1.0] if index == 1 else [0.0, 0.0],
                "front_center_xy": [0.0, 1.0] if index == 1 else [0.1, 0.0],
                "red_stop_lines": [[[-1.0, 0.0], [1.0, 0.0]]] if index == 1 else [],
            }
        )
        ticks.append({"safety": safety})

    safety = review.recompute_safety(ticks)
    assert safety["safety_cost"] == pytest.approx(147.5)
    assert safety["components"] == pytest.approx(
        {
            "collision_any": 1.0,
            "near_miss_noncollision_rate": 0.25,
            "offroad_rate": 0.25,
            "wrong_way_rate": 1 / 3,
            "red_light_violation_any": 1.0,
            "speed_limit_violation_rate": 1 / 3,
        }
    )
    assert safety["raw_counts"] == {
        "collision_ticks": 1,
        "near_miss_noncollision_ticks": 1,
        "offroad_ticks": 1,
        "wrong_way_ticks": 1,
        "red_light_violation_intervals": 1,
        "speed_limit_violation_ticks": 1,
        "strict_speed_limit_violation_ticks": 2,
    }
    assert safety["denominators"] == {
        "clearance_ticks": 4,
        "drivable_area_ticks": 4,
        "moving_onroad_ticks": 3,
        "speed_limit_ticks": 3,
    }
    sensitivity = safety["speed_protocol"]["sensitivity"]
    assert {key: value["event_rate"] for key, value in sensitivity.items()} == pytest.approx(
        {"0.0": 2 / 3, "0.05": 1 / 3, "0.1": 1 / 3, "0.2": 0.0}
    )
    assert safety["speed_protocol"]["continuous"] == pytest.approx(
        {
            "maximum_excess_mps": 0.2,
            "mean_excess_mps": 1 / 12,
            "excess_duration_s": 0.2,
            "magnitude_duration_m": 0.025,
            "positive_excess_ticks": [0, 3],
        }
    )

    secondary = review.recompute_secondary(
        ticks,
        {
            "route_progress_m": 3.0,
            "route_length_m": 4.0,
            "termination_reason": "max_steps",
        },
        {"reason": "max_steps"},
        expected_route_length_m=4.0,
    )
    expected_secondary = {
        "route_completion_rate": 0.75,
        "distance_traveled_m": 3.0,
        "stopped_fraction": 0.25,
        "mean_speed_mps": 1.4125,
        "max_speed_mps": 2.2,
        "mean_abs_acceleration_mps2": 11.5,
        "max_acceleration_mps2": 16.5,
        "mean_abs_jerk_mps3": 142.5,
        "max_jerk_mps3": 225.0,
        "mean_abs_yaw_rate_radps": 20.943951023931955,
        "max_abs_yaw_rate_radps": 31.41592653589793,
        "mean_abs_lateral_acceleration_mps2": 14.660765716752367,
        "max_abs_lateral_acceleration_mps2": 31.41592653589793,
    }
    for field, expected in expected_secondary.items():
        assert secondary[field] == pytest.approx(expected)

    assert review._distribution([1.0, 2.0, 3.0, 4.0]) == pytest.approx(
        {
            "count": 4,
            "mean": 2.5,
            "median": 2.5,
            "p95": 3.85,
            "p99": 3.97,
            "max": 4.0,
        }
    )


def test_hierarchical_bootstrap_5000_seed_24047_matches_hardcoded_oracle() -> None:
    route_bases = {
        "corridor-0": {"route-a": -6.0, "route-b": -2.0},
        "corridor-1": {"route-c": 0.0, "route-d": 4.0},
        "corridor-2": {"route-e": 8.0, "route-f": 12.0},
    }
    offsets = (-2.0, -1.0, 0.0, 1.0, 2.0)
    rows = [
        {
            "corridor_group_sha256": corridor,
            "route_identity_sha256": route,
            "seed": review.HOLDOUT_SEEDS[index],
            "value": base + offset,
        }
        for corridor, routes in route_bases.items()
        for route, base in routes.items()
        for index, offset in enumerate(offsets)
    ]
    summary = review._paired_summary(
        rows,
        lambda row: row["value"],
        resamples=5000,
        seed=24047,
    )
    assert summary["pair_count"] == 30
    assert summary["mean"] == pytest.approx(2.6666666666666665)
    assert summary["median"] == pytest.approx(2.0)
    assert summary["ci95_low"] == pytest.approx(-3.7)
    assert summary["ci95_high"] == pytest.approx(9.600833333333322)
    assert summary["better_tie_worse"] == {"better": 11, "tie": 2, "worse": 17}

    tie_rows = [
        {
            "corridor_group_sha256": "one-corridor",
            "route_identity_sha256": f"route-{index}",
            "seed": 1,
            "value": value,
        }
        for index, value in enumerate(
            (-1e-12, 1e-12, -(1e-12 + 1e-9), 1e-12 + 1e-9)
        )
    ]
    tied = review._paired_summary(
        tie_rows,
        lambda row: row["value"],
        resamples=20,
        seed=24047,
    )
    assert tied["better_tie_worse"] == {"better": 1, "tie": 2, "worse": 1}


def test_failed_pairs_remain_in_denominator_without_replacement() -> None:
    complete = _statistics_row(0)
    complete["pair_key"] = "complete"
    source_failure = {
        "pair_key": "source-failure",
        "route_retained": True,
        "included_in_denominator": True,
        "replacement_used": False,
        "paired_complete": False,
        "source_invalid": True,
        "execution_failure": False,
        "dp_status": "source_invalid",
        "camp_status": "source_invalid",
        "failure_class": "source_failure",
        "map_family_id": "family",
        "corridor_group_sha256": "corridor-1",
        "route_identity_sha256": "route-1",
        "seed": 101,
        "all_k_high_risk": False,
    }
    execution_failure = {
        **source_failure,
        "pair_key": "execution-failure",
        "source_invalid": False,
        "execution_failure": True,
        "dp_status": "ok",
        "camp_status": "failed",
        "failure_class": "execution_failure",
        "corridor_group_sha256": "corridor-2",
        "route_identity_sha256": "route-2",
        "seed": 102,
    }
    rows = [complete, source_failure, execution_failure]
    metrics = review.aggregate_metrics(
        [row["pair_key"] for row in rows],
        rows,
        evidence_guards={},
        bootstrap_resamples=20,
        bootstrap_seed=24047,
    )
    assert metrics["coverage"] == pytest.approx(
        {
            "planned_pair_count": 3,
            "retained_pair_count": 3,
            "paired_complete_count": 1,
            "source_invalid_pair_count": 1,
            "execution_invalid_pair_count": 1,
            "retention_rate": 1.0,
            "paired_complete_rate": 1 / 3,
            "source_invalid_rate": 1 / 3,
            "execution_invalid_rate": 1 / 3,
        }
    )
    assert metrics["safety_cost_delta"]["pair_count"] == 1
    assert metrics["failure_accounting"]["failed_pairs_dropped"] is False
    assert metrics["failure_accounting"]["replacement_or_resampling_used"] is False
    assert metrics["claim_gate_result"]["decision"] == "honest_no_claim"

    missing = rows[:-1]
    with pytest.raises(ValueError, match="frozen denominator"):
        review.aggregate_metrics(
            [row["pair_key"] for row in rows],
            missing,
            evidence_guards={},
        )
    replaced = copy.deepcopy(rows)
    replaced[1]["replacement_used"] = True
    with pytest.raises(ValueError, match="no-replacement"):
        review.aggregate_metrics(
            [row["pair_key"] for row in replaced],
            replaced,
            evidence_guards={},
        )


def test_independent_metrics_equal_reference_common_fields_and_keep_claim_boundaries() -> None:
    rows = [_statistics_row(index) for index in range(6)]
    keys = [row["pair_key"] for row in rows]
    guards = {name: True for name in review.EVIDENCE_GUARD_NAMES}
    independent = review.aggregate_metrics(
        keys,
        rows,
        evidence_guards=guards,
        bootstrap_resamples=200,
        bootstrap_seed=review.BOOTSTRAP_SEED,
    )
    reference = analyze_retained_pairs(
        keys,
        rows,
        evidence_guards=guards,
        bootstrap_resamples=200,
        bootstrap_seed=review.BOOTSTRAP_SEED,
        claim_evaluation=False,
    )
    review._compare_source_statistics(reference, independent)
    assert independent["safety_cost_delta"]["mean"] == -1.0
    assert independent["secondary"]["route_progress_m"]["median"] == 1.0
    assert independent["secondary"]["route_progress_m"]["direction"] == "higher_is_better"
    assert independent["secondary"]["route_progress_m"]["better_tie_worse"] == {
        "better": 6,
        "tie": 0,
        "worse": 0,
    }
    assert independent["latency_comparison_authorized"] is False
    assert independent["latency_reporting_role"] == "descriptive_instrumented_only"
    decision = independent["claim_gate_result"]
    assert decision["map_family_level_ci"] is False
    assert decision["unseen_map_generalization"] is False
    assert decision["native_ranked_k8_superiority"] is False
    assert decision["latency_comparative_conclusion"] is False
    assert decision["final_claim_authorized"] is False


def test_cli_requires_explicit_independent_review_switch() -> None:
    required = [
        "--config", "config.json",
        "--expected-config-sha256", _sha("config"),
        "--expected-preflight-config-sha256", _sha("preflight-config"),
        "--expected-evaluator-sha256", _sha("evaluator"),
        "--execution-root", "execution",
        "--expected-execution-root-sha256", _sha("execution"),
        "--launch-root", "launch",
        "--expected-launch-root-sha256", _sha("launch"),
        "--preflight-root", "preflight",
        "--expected-preflight-root-sha256", _sha("preflight"),
        "--preflight-review-root", "preflight-review",
        "--expected-preflight-review-root-sha256", _sha("preflight-review"),
        "--pilot-review-root", "pilot-review",
        "--expected-pilot-review-root-sha256", _sha("pilot-review"),
        "--authorization-root", "authorization",
        "--expected-authorization-root-sha256", _sha("authorization"),
        "--authorization-review-root", "authorization-review",
        "--expected-authorization-review-root-sha256", _sha("authorization-review"),
        "--expected-preflight-camp-head", _git_oid("preflight-head"),
        "--expected-pilot-review-camp-head", _git_oid("pilot-review-head"),
        "--expected-pilot-execution-source-head", _git_oid("pilot-execution-head"),
        "--expected-execution-source-head", _git_oid("source-head"),
        "--camp-head", _git_oid("camp-head"),
        "--output-dir", "review",
    ]
    assert review.parse_args(required).enable_independent_review is False
    assert review.parse_args(required + ["--enable-independent-review"]).enable_independent_review is True


def test_git_head_pins_require_lowercase_40_character_oids() -> None:
    oid = _git_oid("camp-head")
    assert review._require_git_oid(oid, "CAMP head") == oid
    for invalid in (
        _sha("camp-head"),
        oid.upper(),
        oid[:-1],
        oid + "0",
        "g" * 40,
        None,
    ):
        with pytest.raises(ValueError, match="40-character Git OID"):
            review._require_git_oid(invalid, "CAMP head")
    assert review._require_sha256(_sha("config"), "config") == _sha("config")
    with pytest.raises(ValueError, match="lowercase SHA256"):
        review._require_sha256(oid, "config")


def test_review_entry_accepts_git_oids_before_opening_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n", encoding="utf-8")
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    seal_calls = 0

    def stop_at_first_seal(*_args: object, **_kwargs: object) -> object:
        nonlocal seal_calls
        seal_calls += 1
        raise RuntimeError("first-seal-sentinel")

    monkeypatch.setattr(review, "verify_complete_seal", stop_at_first_seal)
    kwargs = {
        "config_path": config_path,
        "expected_config_sha256": config_sha,
        "expected_preflight_config_sha256": _sha("preflight-config"),
        "expected_evaluator_sha256": _sha("evaluator"),
        "execution_root": tmp_path / "execution",
        "expected_execution_root_sha256": _sha("execution"),
        "launch_root": tmp_path / "launch",
        "expected_launch_root_sha256": _sha("launch"),
        "preflight_root": tmp_path / "preflight",
        "expected_preflight_root_sha256": _sha("preflight"),
        "preflight_review_root": tmp_path / "preflight-review",
        "expected_preflight_review_root_sha256": _sha("preflight-review"),
        "pilot_review_root": tmp_path / "pilot-review",
        "expected_pilot_review_root_sha256": _sha("pilot-review"),
        "authorization_root": tmp_path / "authorization",
        "expected_authorization_root_sha256": _sha("authorization"),
        "authorization_review_root": tmp_path / "authorization-review",
        "expected_authorization_review_root_sha256": _sha("authorization-review"),
        "expected_preflight_camp_head": _git_oid("preflight-head"),
        "expected_pilot_review_camp_head": _git_oid("pilot-review-head"),
        "expected_pilot_execution_source_head": _git_oid("pilot-source-head"),
        "expected_execution_source_head": _git_oid("execution-source-head"),
        "camp_head": _git_oid("camp-head"),
        "output_dir": tmp_path / "output",
        "enable_independent_review": True,
    }
    with pytest.raises(RuntimeError, match="first-seal-sentinel"):
        review.review_holdout_main_result(**kwargs)
    assert seal_calls == 1

    invalid = dict(kwargs)
    invalid["camp_head"] = _sha("camp-head")
    seal_calls = 0
    with pytest.raises(ValueError, match="40-character Git OID"):
        review.review_holdout_main_result(**invalid)
    assert seal_calls == 0

    invalid = dict(kwargs)
    invalid["expected_config_sha256"] = _git_oid("config")
    with pytest.raises(ValueError, match="lowercase SHA256"):
        review.review_holdout_main_result(**invalid)
    assert seal_calls == 0


def test_evidence_limitations_and_descriptive_latency_are_explicit_in_source() -> None:
    source = Path(review.__file__).read_text(encoding="utf-8")
    for required in (
        '"affine_score_receipt_consistency_verified": True',
        '"affine_scores_recomputed_from_raw_atoms": False',
        '"candidate_hashes_recomputed_from_raw_tensor_bytes": False',
        '"raw_byte_proof_claimed": False',
        '"latency_comparison_authorized": False',
        '"map_family_level_ci_authorized": False',
        '"unseen_map_generalization_authorized": False',
    ):
        assert required in source
