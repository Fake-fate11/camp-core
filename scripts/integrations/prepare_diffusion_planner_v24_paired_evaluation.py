#!/usr/bin/env python3
"""Outcome-blind v24 paired-evaluation plan and static preflight."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SPLIT_PLAN_SHA256 = (
    "52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539"
)
SPLIT_MANIFEST_SHA256 = (
    "ba814ee3da89fc6d9b3ae1ce9a9929e38bebc6349f3871f8d105f285207bf5fa"
)
EXPECTED_ROUTE_COUNTS = {"train": 375, "calibration": 2, "holdout": 24}
EXPECTED_SEEDS = {
    "train": [24001, 24002, 24003, 24004, 24005],
    "calibration": [24101, 24102, 24103, 24104, 24105],
    "holdout": [24201, 24202, 24203, 24204, 24205],
}
EXPECTED_ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
SAFETY_WEIGHTS = {
    "collision_any": 100.0,
    "near_miss_noncollision_rate": 10.0,
    "offroad_rate": 20.0,
    "wrong_way_rate": 20.0,
    "red_light_violation_any": 30.0,
    "speed_limit_violation_rate": 10.0,
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in Path(root).rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha256 = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha256}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha256


def _verify_artifact_root(
    path_value: Any, expected_root_sha256: Any, label: str
) -> dict[str, Any]:
    root = Path(str(path_value)).resolve()
    sums = root / "SHA256SUMS"
    if not root.is_dir() or not sums.is_file():
        raise ValueError(f"{label} artifact or SHA256SUMS is missing")
    actual_root = _file_sha256(sums)
    if actual_root != expected_root_sha256:
        raise ValueError(f"{label} root SHA256 mismatch")
    count = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = (root / relative).resolve()
        if root != path and root not in path.parents:
            raise ValueError(f"{label} manifest escapes artifact root")
        if not path.is_file() or _file_sha256(path) != digest:
            raise ValueError(f"{label} file SHA256 mismatch: {relative}")
        count += 1
    root_receipt = root / "ROOT_SHA256SUMS"
    if root_receipt.is_file():
        expected_line = f"{actual_root}  SHA256SUMS"
        if root_receipt.read_text(encoding="utf-8").strip() != expected_line:
            raise ValueError(f"{label} ROOT_SHA256SUMS mismatch")
    return {"label": label, "root": root.as_posix(), "root_sha256": actual_root, "file_count": count}


def validate_evaluation_config(
    config: Mapping[str, Any], *, require_all_execution_closed: bool = True
) -> None:
    if config.get("schema_version") != "camp_dp_v24_native_paired_evaluation_v1":
        raise ValueError("v24 paired-evaluation config schema mismatch")
    modes = _mapping(config, "modes")
    if set(modes) != {"capability", "pilot", "main"}:
        raise ValueError("v24 evaluation modes mismatch")
    expected_modes = {
        "capability": ("calibration", 1, [24101], 1),
        "pilot": ("calibration", 2, [24101], 64),
        "main": ("holdout", 24, [24201, 24202, 24203, 24204, 24205], 64),
    }
    for mode, expected in expected_modes.items():
        item = _mapping(modes, mode)
        actual = (
            item.get("split"),
            item.get("route_count"),
            item.get("seeds"),
            item.get("max_steps"),
        )
        if actual != expected:
            raise ValueError(f"v24 {mode} schedule mismatch")
    candidate = _mapping(config, "candidate_contract")
    claim = _mapping(config, "claim_contract")
    statistics = _mapping(config, "statistics")
    calibration = _mapping(config, "calibration_contract")
    coverage = _mapping(config, "coverage_execution_contract")
    arm_order = _mapping(config, "arm_order_policy")
    stability = _mapping(config, "learning_curve_stability")
    if (
        arm_order.get("schema") != "camp_dp_v24_hash_rank_balanced_ab_ba_v1"
        or arm_order.get("domain_separator") != "camp-v24-paired-arm-order-v1"
        or arm_order.get("orders") != [["dp", "camp"], ["camp", "dp"]]
        or arm_order.get("pilot_required_counts") != {"dp_camp": 1, "camp_dp": 1}
        or arm_order.get("main_required_counts") != {"dp_camp": 60, "camp_dp": 60}
        or arm_order.get("independent_reset_per_arm") is not True
        or arm_order.get("latency_comparison_authorized") is not False
        or config.get("candidate_k") != 8
        or config.get("selection_policy") != "v22_source_valid"
        or config.get("score_contract") != "score_k(w)=a_k^T w"
        or config.get("nonnegative_simplex") is not True
        or config.get("safety_schema") != "safety_cost_native_v22"
        or config.get("safety_component_weights") != SAFETY_WEIGHTS
        or config.get("primary_speed_tolerance_mps") != 0.1
        or config.get("speed_sensitivity_tolerances_mps")
        != [0.0, 0.05, 0.1, 0.2]
        or config.get("route_retention")
        != "all_preregistered_routes_and_failures_no_replacement"
        or coverage.get("planned_pair_retention_rate_min") != 1.0
        or coverage.get("paired_complete_rate_min_for_claim") != 1.0
        or coverage.get("source_invalid_pair_rate_max_for_claim") != 0.0
        or coverage.get("execution_invalid_pair_rate_max_for_claim") != 0.0
        or coverage.get("replacement_or_resampling_authorized") is not False
        or _mapping(coverage, "train_route_seed_source_coverage_disclosure")
        != {
            "retained": 1875,
            "complete": 1054,
            "failed": 821,
            "failure_rate": 0.4378666666666667,
        }
        or calibration.get("model_or_weight_tuning_authorized") is not False
        or calibration.get("atom_scale_reselection_authorized") is not False
        or calibration.get("selector_thresholds") != []
        or candidate.get("per_arm_candidate_tensor_immutability_required_every_tick")
        is not True
        or candidate.get("per_arm_candidate0_default_byte_identity_required_every_tick")
        is not True
        or candidate.get("selected_trajectory_must_be_exact_indexed_candidate")
        is not True
        or candidate.get("dp_policy")
        != "candidate0_operational_default_not_native_ranked_top1"
        or candidate.get("t0_cross_arm_input_and_candidate_hash_identity_required")
        is not True
        or candidate.get("post_divergence_cross_arm_tensor_identity_required")
        is not False
        or candidate.get("policy_level_closed_loop_claim_preclosed") is not False
        or claim.get("paired_retention_rate_required") != 1.0
        or claim.get("paired_complete_rate_required") != 1.0
        or claim.get("per_arm_candidate_immutability_required") is not True
        or claim.get("per_arm_candidate0_default_identity_required") is not True
        or claim.get("t0_cross_arm_identity_required") is not True
        or statistics.get("primary_bootstrap_hierarchy")
        != ["corridor_group_sha256", "route_identity_sha256", "seed"]
        or statistics.get("map_family_cluster_level_authorized") is not False
        or statistics.get("holdout_map_family_count") != 1
        or statistics.get("holdout_corridor_group_count") != 3
        or statistics.get("bootstrap_resamples") != 5000
        or statistics.get("bootstrap_seed") != 24047
        or statistics.get("tie_tolerance") != 1e-12
        or stability.get("levels_percent") != [25, 50, 75, 100]
        or stability.get("effective_support_gt_1e_6") != [3, 3, 3, 3]
        or stability.get("full_effective_support_indices") != [7, 8, 13]
        or stability.get("risk_disclosure_required") is not True
        or stability.get("calibration_or_holdout_repair_authorized") is not False
        or not isinstance(config.get("pilot_execution_authorized"), bool)
        or not isinstance(config.get("main_execution_authorized"), bool)
        or (
            require_all_execution_closed
            and config.get("pilot_execution_authorized") is not False
        )
        or (
            require_all_execution_closed
            and config.get("main_execution_authorized") is not False
        )
        or config.get("holdout_opened") is not False
        or config.get("holdout_open_count") != 0
        or config.get("outcome_fields_consumed") != []
        or config.get("claim_authorized") is not False
        or config.get("minimum_free_disk_gib") != 10
    ):
        raise ValueError("v24 paired-evaluation scientific contract mismatch")


def _assign_balanced_arm_orders(
    rows: list[dict[str, Any]], policy: Mapping[str, Any]
) -> None:
    domain = str(policy["domain_separator"])
    ranked = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"{domain}\0{row['pair_key']}".encode("utf-8")
        ).hexdigest(),
    )
    midpoint = (len(ranked) + 1) // 2
    for index, row in enumerate(ranked):
        row["arm_order"] = ["dp", "camp"] if index < midpoint else ["camp", "dp"]
        row["arm_order_rank_sha256"] = hashlib.sha256(
            f"{domain}\0{row['pair_key']}".encode("utf-8")
        ).hexdigest()


def _arm_order_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "dp_camp": sum(row.get("arm_order") == ["dp", "camp"] for row in rows),
        "camp_dp": sum(row.get("arm_order") == ["camp", "dp"] for row in rows),
    }


def build_evaluation_plan(
    config: Mapping[str, Any],
    split_manifest: Mapping[str, Any],
    route_census: Mapping[str, Any],
) -> dict[str, Any]:
    validate_evaluation_config(config)
    if (
        split_manifest.get("schema")
        != "camp_dp_v24_map_family_split_manifest_v1"
        or split_manifest.get("plan_sha256") != SPLIT_PLAN_SHA256
        or split_manifest.get("manifest_sha256") != SPLIT_MANIFEST_SHA256
        or split_manifest.get("outcome_fields_consumed") != []
        or split_manifest.get("holdout_opened") is not False
        or split_manifest.get("claim_authorized") is not False
    ):
        raise ValueError("corrected v24 split boundary mismatch")
    if split_manifest.get("seed_namespaces") != EXPECTED_SEEDS:
        raise ValueError("corrected v24 seed namespaces mismatch")
    if (
        route_census.get("schema")
        != "diffusion_planner_v24_outcome_blind_route_census_v1"
        or route_census.get("route_census_completed") is not True
        or route_census.get("model_loaded") is not False
        or route_census.get("candidate_generation_started") is not False
        or route_census.get("outcome_accessed") is not False
        or route_census.get("holdout_opened") is not False
    ):
        raise ValueError("v24 route-census source-only boundary mismatch")

    records = [dict(item) for item in split_manifest.get("records", [])]
    routes_by_key = {
        str(item["record_key"]): dict(item)
        for item in route_census.get("retained_routes", [])
    }
    if len(records) != 401 or len(routes_by_key) != 401:
        raise ValueError("v24 evaluation requires all 401 frozen routes")
    if {str(item["record_key"]) for item in records} != set(routes_by_key):
        raise ValueError("split and route-census keys differ")

    joined: dict[str, list[dict[str, Any]]] = {
        split: [] for split in EXPECTED_ROUTE_COUNTS
    }
    for record in records:
        split = str(record.get("split"))
        if split not in joined:
            raise ValueError("unknown v24 split")
        route = routes_by_key[str(record["record_key"])]
        if (
            str(record.get("identity_sha256")) != str(route.get("identity_sha256"))
            or str(record.get("map_family_id")) != str(route.get("map_family_id"))
            or list(record.get("seeds", [])) != EXPECTED_SEEDS[split]
        ):
            raise ValueError("split/route identity or seed mismatch")
        route["split"] = split
        route["corridor_group_sha256"] = str(record["corridor_group_sha256"])
        route["seeds"] = list(record["seeds"])
        joined[split].append(route)
    counts = {name: len(values) for name, values in joined.items()}
    if counts != EXPECTED_ROUTE_COUNTS:
        raise ValueError("v24 paired-evaluation route counts mismatch")
    for values in joined.values():
        values.sort(key=lambda item: str(item["record_key"]))

    calibration = joined["calibration"]
    holdout = joined["holdout"]
    train = joined["train"]
    train_keys = {str(item["record_key"]) for item in train}
    calibration_keys = {str(item["record_key"]) for item in calibration}
    holdout_keys = {str(item["record_key"]) for item in holdout}
    if train_keys & calibration_keys or train_keys & holdout_keys or calibration_keys & holdout_keys:
        raise ValueError("route overlap across v24 splits")
    for field in ("map_family_id", "corridor_group_sha256", "identity_sha256"):
        sets = [
            {str(item[field]) for item in joined[name]}
            for name in ("train", "calibration", "holdout")
        ]
        if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
            raise ValueError(f"{field} overlap across v24 splits")

    schedules: dict[str, list[dict[str, Any]]] = {}
    for mode in ("capability", "pilot", "main"):
        mode_config = _mapping(_mapping(config, "modes"), mode)
        split = str(mode_config["split"])
        routes = joined[split]
        selected_routes = routes[: int(mode_config["route_count"])]
        seeds = [int(value) for value in mode_config["seeds"]]
        schedules[mode] = [
            {
                "schema": "camp_dp_v24_planned_pair_v1",
                "mode": mode,
                "split": split,
                "pair_key": f"{split}/{route['identity_sha256']}/seed_{seed}",
                "receipt_key": f"{split}/{route['identity_sha256']}/seed_{seed}/pair.json",
                "record_key": str(route["record_key"]),
                "route_identity_sha256": str(route["identity_sha256"]),
                "map_family_id": str(route["map_family_id"]),
                "logical_map_sha256": str(route["logical_map_sha256"]),
                "corridor_group_sha256": str(route["corridor_group_sha256"]),
                "seed": seed,
                "max_steps": int(mode_config["max_steps"]),
                "expected_arms": ["dp", "camp"],
                "included_in_denominator": True,
                "replacement_authorized": False,
                "route": copy.deepcopy(route),
            }
            for route in selected_routes
            for seed in seeds
        ]
        _assign_balanced_arm_orders(
            schedules[mode], _mapping(config, "arm_order_policy")
        )
    if {name: len(rows) for name, rows in schedules.items()} != {
        "capability": 1,
        "pilot": 2,
        "main": 120,
    }:
        raise ValueError("v24 paired schedule count mismatch")
    if _arm_order_counts(schedules["pilot"]) != {"dp_camp": 1, "camp_dp": 1}:
        raise ValueError("v24 pilot AB/BA arm-order balance mismatch")
    if _arm_order_counts(schedules["main"]) != {"dp_camp": 60, "camp_dp": 60}:
        raise ValueError("v24 main AB/BA arm-order balance mismatch")
    holdout_families = {str(row["map_family_id"]) for row in holdout}
    holdout_corridors = {str(row["corridor_group_sha256"]) for row in holdout}
    if len(holdout_families) != 1 or len(holdout_corridors) != 3:
        raise ValueError("v24 holdout family/corridor cluster count mismatch")

    plan = {
        "schema": "camp_dp_v24_native_paired_evaluation_plan_v1",
        "source_split_plan_sha256": SPLIT_PLAN_SHA256,
        "source_split_manifest_sha256": SPLIT_MANIFEST_SHA256,
        "route_counts": counts,
        "seed_namespaces": copy.deepcopy(EXPECTED_SEEDS),
        "planned_pair_counts": {name: len(rows) for name, rows in schedules.items()},
        "candidate_k": 8,
        "score_contract": "score_k(w)=a_k^T w",
        "safety_schema": "safety_cost_native_v22",
        "primary_speed_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "failure_accounting": "retain_all_planned_pairs_without_replacement",
        "coverage_execution_thresholds": {
            "retention_rate_min": 1.0,
            "paired_complete_rate_min_for_claim": 1.0,
            "source_invalid_rate_max_for_claim": 0.0,
            "execution_invalid_rate_max_for_claim": 0.0,
        },
        "train_source_coverage_disclosure": dict(
            _mapping(
                _mapping(config, "coverage_execution_contract"),
                "train_route_seed_source_coverage_disclosure",
            )
        ),
        "pilot_role": "execution_capability_only_no_tuning",
        "main_holdout_once": True,
        "arm_order_policy": copy.deepcopy(dict(_mapping(config, "arm_order_policy"))),
        "arm_order_counts": {
            name: _arm_order_counts(rows) for name, rows in schedules.items()
        },
        "per_arm_candidate_tensor_immutability_required": True,
        "per_arm_candidate0_default_identity_required": True,
        "t0_cross_arm_input_and_candidate_hash_identity_required": True,
        "post_divergence_cross_arm_tensor_identity_required": False,
        "post_divergence_cross_arm_tensor_semantics": "expected_noncomparable_state_conditioned_fixed_dp_outputs",
        "native_ranked_k8_provenance_claim_authorized": False,
        "holdout_map_family_count": len(holdout_families),
        "holdout_corridor_group_count": len(holdout_corridors),
        "primary_ci_cluster_hierarchy": [
            "corridor_group_sha256",
            "route_identity_sha256",
            "seed",
        ],
        "map_family_level_ci_authorized": False,
        "schedules": schedules,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "pilot_execution_authorized": False,
        "main_execution_authorized": False,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "claim_authorized": False,
    }
    hashable = copy.deepcopy(plan)
    for rows in hashable["schedules"].values():
        for row in rows:
            row.pop("route", None)
    plan["plan_sha256"] = _canonical_sha256(hashable)
    return plan


def _load_and_validate_selector(
    config: Mapping[str, Any]
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    frozen = _mapping(config, "frozen_selector")
    model_path = Path(str(frozen["model_path"]))
    weights_path = Path(str(frozen["weights_f64le_path"]))
    if _file_sha256(model_path) != frozen.get("model_sha256"):
        raise ValueError("v24 full-train model SHA256 mismatch")
    if _file_sha256(weights_path) != frozen.get("weights_f64le_sha256"):
        raise ValueError("v24 full-train f64le weights SHA256 mismatch")
    model = json.loads(model_path.read_text(encoding="utf-8"))
    weights = np.fromfile(weights_path, dtype="<f8")
    model_weights = np.asarray(model.get("weights"), dtype=np.float64)
    scales = np.asarray(model.get("atom_scales"), dtype=np.float64)
    if (
        model.get("schema") != "camp_dp_v24_static_affine_selector_model_v1"
        or model.get("level_percent") != 100
        or model.get("primary_model") is not True
        or model.get("score_contract") != "score_k(w)=a_k^T w"
        or model.get("atom_schema_version") != "dp_camp_v10_14d"
        or tuple(model.get("atom_names", ())) != EXPECTED_ATOM_NAMES
        or model.get("active_atom_mask") != [True] * 14
        or weights.shape != (14,)
        or model_weights.shape != (14,)
        or not np.array_equal(weights, model_weights)
        or not np.isfinite(weights).all()
        or np.any(weights < 0.0)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-8)
        or scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or model.get("actual_closed_loop_outcomes_read") is not False
        or model.get("calibration_accessed") is not False
        or model.get("holdout_opened") is not False
        or model.get("claim_authorized") is not False
    ):
        raise ValueError("v24 full-train selector receipt mismatch")
    return model, weights, scales


def review_learning_curve_stability(
    config: Mapping[str, Any]
) -> dict[str, Any]:
    frozen = _mapping(config, "frozen_selector")
    expected = _mapping(config, "learning_curve_stability")
    model_dir = Path(str(frozen["training_artifact"])) / "models"
    levels = [25, 50, 75, 100]
    models = {
        level: json.loads(
            (model_dir / f"level_{level}.json").read_text(encoding="utf-8")
        )
        for level in levels
    }
    full = np.asarray(models[100]["weights"], dtype=np.float64)
    l1_to_full = []
    effective_support = []
    candidate0_rates = []
    histogram_l1 = []
    selected_argmax = []
    for level in levels:
        model = models[level]
        weights = np.asarray(model["weights"], dtype=np.float64)
        histogram = np.asarray(
            _mapping(model, "train_metrics")["selection_histogram"],
            dtype=np.float64,
        )
        full_histogram = np.asarray(
            _mapping(models[100], "train_metrics")["selection_histogram"],
            dtype=np.float64,
        )
        l1_to_full.append(float(np.abs(weights - full).sum()))
        effective_support.append(int(np.count_nonzero(weights > 1e-6)))
        probabilities = histogram / histogram.sum()
        full_probabilities = full_histogram / full_histogram.sum()
        candidate0_rates.append(float(probabilities[0]))
        histogram_l1.append(float(np.abs(probabilities - full_probabilities).sum()))
        selected_argmax.append(int(np.argmax(probabilities)))
    effective_indices = np.flatnonzero(full > 1e-6).astype(int).tolist()
    effective_weights = full[effective_indices].tolist()
    receipt = {
        "schema": "camp_dp_v24_learning_curve_stability_review_v1",
        "levels_percent": levels,
        "weights_l1_to_full": l1_to_full,
        "effective_support_gt_1e_6": effective_support,
        "candidate0_selection_rate": candidate0_rates,
        "selected_index_histogram_l1_to_full": histogram_l1,
        "selected_index_argmax": selected_argmax,
        "full_effective_support_indices": effective_indices,
        "full_effective_support_names": [EXPECTED_ATOM_NAMES[index] for index in effective_indices],
        "full_effective_support_weights": effective_weights,
        "distribution_concentration_is_automatic_failure": False,
        "risk_disclosure_required": True,
        "calibration_or_holdout_repair_authorized": False,
        "outcome_fields_consumed": [],
    }
    for name in (
        "weights_l1_to_full",
        "candidate0_selection_rate",
        "selected_index_histogram_l1_to_full",
        "full_effective_support_weights",
    ):
        if not np.allclose(
            np.asarray(receipt[name], dtype=np.float64),
            np.asarray(expected[name], dtype=np.float64),
            rtol=0.0,
            atol=1e-15,
        ):
            raise ValueError(f"v24 learning-curve stability mismatch: {name}")
    for name in (
        "levels_percent",
        "effective_support_gt_1e_6",
        "selected_index_argmax",
        "full_effective_support_indices",
        "full_effective_support_names",
    ):
        if receipt[name] != expected[name]:
            raise ValueError(f"v24 learning-curve stability mismatch: {name}")
    return receipt


def materialize_selector_runtime(
    config: Mapping[str, Any], output_dir: Path
) -> dict[str, Any]:
    model, weights, scales = _load_and_validate_selector(config)
    output = Path(output_dir)
    output.mkdir()
    weights_path = output / "weights.npy"
    scales_path = output / "atom_scales.json"
    np.save(weights_path, weights, allow_pickle=False)
    _write_json(
        scales_path,
        {
            "atom_schema_version": "dp_camp_v10_14d",
            "atom_names": list(EXPECTED_ATOM_NAMES),
            "scales": scales.tolist(),
            "source": "v24_full_train_level_100_exact_serialization_adapter",
        },
    )
    if not np.array_equal(np.load(weights_path, allow_pickle=False), weights):
        raise ValueError("runtime weights serialization changed numeric values")
    scales_roundtrip = json.loads(scales_path.read_text(encoding="utf-8"))
    if not np.array_equal(np.asarray(scales_roundtrip["scales"]), scales):
        raise ValueError("runtime scales serialization changed numeric values")
    frozen = _mapping(config, "frozen_selector")
    receipt = {
        "schema": "camp_dp_v24_selector_runtime_adapter_v1",
        "source_model_sha256": str(frozen["model_sha256"]),
        "source_weights_f64le_sha256": str(frozen["weights_f64le_sha256"]),
        "runtime_weights_path": weights_path.as_posix(),
        "runtime_weights_sha256": _file_sha256(weights_path),
        "runtime_scales_path": scales_path.as_posix(),
        "runtime_scales_sha256": _file_sha256(scales_path),
        "weights_elementwise_equal": True,
        "scales_elementwise_equal": True,
        "weight_count": int(weights.size),
        "simplex_sum": float(weights.sum()),
        "minimum_weight": float(weights.min()),
        "model_primary": bool(model["primary_model"]),
        "training_executed": False,
        "model_retrained": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    _write_json(output / "adapter_receipt.json", receipt)
    receipt["root_sha256"] = _seal(output)
    return receipt


def build_evaluation_run_config(
    template: Mapping[str, Any],
    selector_runtime: Mapping[str, Any],
    planned: Mapping[str, Any],
    route_asset: Mapping[str, str],
) -> dict[str, Any]:
    route = _mapping(planned, "route")
    seed = int(planned["seed"])
    steps = int(planned["max_steps"])
    config = copy.deepcopy(dict(template))
    config["schema_version"] = "camp_dp_v24_native_evaluation_run_v1"
    config["selector"] = {
        "root": str(Path(str(selector_runtime["runtime_weights_path"])).parent),
        "root_sha256": str(selector_runtime["root_sha256"]),
        "model_sha256": str(selector_runtime["source_model_sha256"]),
        "atom_scales": {
            "path": str(selector_runtime["runtime_scales_path"]),
            "sha256": str(selector_runtime["runtime_scales_sha256"]),
        },
        "weights": {
            "path": str(selector_runtime["runtime_weights_path"]),
            "sha256": str(selector_runtime["runtime_weights_sha256"]),
        },
        "score_contract": "score_k(w)=a_k^T w",
        "nonnegative_simplex": True,
        "candidate_k": 8,
        "selection_policy": "v22_source_valid",
        "role": "v24_primary_frozen_train_only",
    }
    config["map"] = {
        "path": str(route["source_map_path"]),
        "sha256": str(route["source_map_sha256"]),
        "map_family_id": str(route["map_family_id"]),
        "logical_map_sha256": str(route["logical_map_sha256"]),
        "corridor_group_sha256": str(route["corridor_group_sha256"]),
    }
    config["routes"] = [
        {
            "name": str(planned["route_identity_sha256"]),
            "path": str(route_asset["path"]),
            "sha256": str(route_asset["sha256"]),
        }
    ]
    config["seeds"] = {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [11, 12, 13],
    }
    config["spawn_config"]["seed"] = seed
    config["spawn_config"]["max_steps"] = steps
    config["protocol"] = {
        "evaluation_mode": str(planned["mode"]),
        "evaluation_split": str(planned["split"]),
        "evaluation_steps": steps,
        "arm_order": list(planned["arm_order"]),
        "arm_order_rank_sha256": str(planned["arm_order_rank_sha256"]),
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
    }
    return config


def _git_head_and_status(repo: Path) -> tuple[str, str]:
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return head, status


def run_static_preflight(
    *,
    config_path: Path,
    dp_repo: Path,
    camp_head: str,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {output_dir}")
    config_bytes = Path(config_path).read_bytes()
    config = json.loads(config_bytes)
    validate_evaluation_config(config)
    roots = []
    split_source = _mapping(config, "source_split")
    route_source = _mapping(config, "source_route_census")
    frozen = _mapping(config, "frozen_selector")
    roots.extend(
        [
            _verify_artifact_root(split_source["artifact"], split_source["artifact_root_sha256"], "source_split"),
            _verify_artifact_root(split_source["independent_review_artifact"], split_source["independent_review_root_sha256"], "source_split_review"),
            _verify_artifact_root(route_source["artifact"], route_source["artifact_root_sha256"], "route_census"),
            _verify_artifact_root(route_source["independent_review_artifact"], route_source["independent_review_root_sha256"], "route_census_review"),
            _verify_artifact_root(frozen["training_artifact"], frozen["training_artifact_root_sha256"], "training"),
            _verify_artifact_root(frozen["independent_review_artifact"], frozen["independent_review_root_sha256"], "training_review"),
        ]
    )
    split_path = Path(str(split_source["manifest_path"]))
    census_path = Path(str(route_source["census_path"]))
    base_entry = _mapping(config, "base_native_config")
    base_path = Path(str(base_entry["path"]))
    if _file_sha256(split_path) != split_source.get("file_sha256"):
        raise ValueError("source split file SHA256 mismatch")
    if _file_sha256(census_path) != route_source.get("file_sha256"):
        raise ValueError("route census file SHA256 mismatch")
    if _file_sha256(base_path) != base_entry.get("sha256"):
        raise ValueError("base native config SHA256 mismatch")
    split_manifest = json.loads(split_path.read_text(encoding="utf-8"))
    route_census = json.loads(census_path.read_text(encoding="utf-8"))
    template = json.loads(base_path.read_text(encoding="utf-8"))
    plan = build_evaluation_plan(config, split_manifest, route_census)
    dp_head, dp_status = _git_head_and_status(dp_repo)
    if dp_head != FIXED_DP_HEAD or dp_status:
        raise ValueError("fixed DP HEAD drift or tracked dirt")
    if _mapping(template, "fixed_dp").get("head") != FIXED_DP_HEAD:
        raise ValueError("base native config fixed DP HEAD mismatch")

    unique_maps = {
        (str(row["route"]["source_map_path"]), str(row["route"]["source_map_sha256"]))
        for mode in ("pilot", "main")
        for row in plan["schedules"][mode]
    }
    for map_path, expected_sha256 in sorted(unique_maps):
        if _file_sha256(Path(map_path)) != expected_sha256:
            raise ValueError("frozen source map SHA256 mismatch")

    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_evaluation_run_config,
    )

    output_dir.mkdir(parents=True)
    selector_runtime = materialize_selector_runtime(
        config, output_dir / "runtime_selector"
    )
    learning_curve_stability = review_learning_curve_stability(config)
    _write_json(
        output_dir / "learning_curve_stability.json", learning_curve_stability
    )
    route_dir = output_dir / "routes"
    route_dir.mkdir()
    route_assets: dict[str, dict[str, str]] = {}
    route_records: dict[str, dict[str, Any]] = {}
    for mode in ("capability", "pilot", "main"):
        for planned in plan["schedules"][mode]:
            identity = str(planned["route_identity_sha256"])
            if identity in route_assets:
                continue
            route = planned["route"]
            spec = route["route_spec"]
            lanelet_ids = [int(value) for value in spec["lanelet_ids"]]
            asset_path = route_dir / f"{identity}.pkl"
            route_object = Route(
                map_path=str(route["source_map_path"]),
                start_pose=np.asarray(spec["start_pose"], dtype=np.float32),
                goal_pose=np.asarray(spec["goal_pose"], dtype=np.float32),
                start_lanelet_id=lanelet_ids[0],
                goal_lanelet_id=lanelet_ids[-1],
                route_lanelet_ids=lanelet_ids,
            )
            route_object.save(asset_path)
            route_assets[identity] = {
                "path": asset_path.as_posix(),
                "sha256": _file_sha256(asset_path),
            }
            route_records[identity] = {
                "record_key": str(route["record_key"]),
                "route_identity_sha256": identity,
                "split": str(route["split"]),
                "map_family_id": str(route["map_family_id"]),
                "logical_map_sha256": str(route["logical_map_sha256"]),
                "corridor_group_sha256": str(route["corridor_group_sha256"]),
                "source_map_path": str(route["source_map_path"]),
                "source_map_sha256": str(route["source_map_sha256"]),
                "route_asset": route_assets[identity],
            }

    run_config_receipts = []
    with (output_dir / "disabled_run_configs.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for mode in ("capability", "pilot", "main"):
            for planned in plan["schedules"][mode]:
                identity = str(planned["route_identity_sha256"])
                run_config = build_evaluation_run_config(
                    template, selector_runtime, planned, route_assets[identity]
                )
                validate_v24_evaluation_run_config(run_config)
                handle.write(json.dumps(run_config, sort_keys=True) + "\n")
                run_config_receipts.append(
                    {
                        "pair_key": str(planned["pair_key"]),
                        "mode": mode,
                        "split": str(planned["split"]),
                        "route_identity_sha256": identity,
                        "seed": int(planned["seed"]),
                        "max_steps": int(planned["max_steps"]),
                        "config_sha256": _canonical_sha256(run_config),
                        "execution_authorized": False,
                        "holdout_access_authorized": False,
                    }
                )
    public_plan = copy.deepcopy(plan)
    for rows in public_plan["schedules"].values():
        for row in rows:
            row.pop("route", None)
    _write_json(output_dir / "evaluation_plan.json", public_plan)
    _write_json(output_dir / "route_assets.json", list(route_records.values()))
    _write_json(output_dir / "run_config_receipts.json", run_config_receipts)

    free_bytes = shutil.disk_usage(output_dir).free
    checks = {
        "upstream_root_count_6": len(roots) == 6,
        "all_401_routes_joined": plan["route_counts"] == EXPECTED_ROUTE_COUNTS,
        "calibration_routes_2": sum(row["split"] == "calibration" for row in route_records.values()) == 2,
        "holdout_routes_24": sum(row["split"] == "holdout" for row in route_records.values()) == 24,
        "unique_route_assets_26": len(route_assets) == 26,
        "disabled_run_configs_123": len(run_config_receipts) == 123,
        "capability_pairs_1": len(plan["schedules"]["capability"]) == 1,
        "pilot_pairs_2": len(plan["schedules"]["pilot"]) == 2,
        "main_pairs_120": len(plan["schedules"]["main"]) == 120,
        "pilot_arm_order_balanced_1_1": plan["arm_order_counts"]["pilot"] == {"dp_camp": 1, "camp_dp": 1},
        "main_arm_order_balanced_60_60": plan["arm_order_counts"]["main"] == {"dp_camp": 60, "camp_dp": 60},
        "all_run_configs_disabled": all(not row["execution_authorized"] for row in run_config_receipts),
        "holdout_access_disabled": all(not row["holdout_access_authorized"] for row in run_config_receipts),
        "fixed_dp_head": dp_head == FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": not bool(dp_status),
        "selector_exact_weights": selector_runtime["weights_elementwise_equal"] is True,
        "selector_exact_scales": selector_runtime["scales_elementwise_equal"] is True,
        "per_arm_candidate_contract_frozen": plan["per_arm_candidate_tensor_immutability_required"] is True and plan["per_arm_candidate0_default_identity_required"] is True,
        "t0_cross_arm_identity_frozen": plan["t0_cross_arm_input_and_candidate_hash_identity_required"] is True,
        "post_divergence_tensor_noncomparability_frozen": plan["post_divergence_cross_arm_tensor_identity_required"] is False,
        "one_holdout_map_family": plan["holdout_map_family_count"] == 1,
        "three_holdout_corridor_groups": plan["holdout_corridor_group_count"] == 3,
        "map_family_level_ci_forbidden": plan["map_family_level_ci_authorized"] is False,
        "learning_curve_stability_recomputed": learning_curve_stability["effective_support_gt_1e_6"] == [3, 3, 3, 3],
        "weight_concentration_risk_disclosed": learning_curve_stability["risk_disclosure_required"] is True,
        "model_not_loaded": plan["model_loaded"] is False,
        "simulator_not_executed": plan["simulator_executed"] is False,
        "candidate_generation_not_started": plan["candidate_generation_started"] is False,
        "outcomes_not_consumed": plan["outcome_fields_consumed"] == [],
        "holdout_not_opened": plan["holdout_opened"] is False and plan["holdout_open_count"] == 0,
        "disk_floor": free_bytes > int(config["minimum_free_disk_gib"]) * 1024**3,
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "schema": "camp_dp_v24_native_paired_evaluation_static_preflight_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "plan_sha256": plan["plan_sha256"],
        "source_roots": roots,
        "selector_runtime_root_sha256": selector_runtime["root_sha256"],
        "route_counts": plan["route_counts"],
        "planned_pair_counts": plan["planned_pair_counts"],
        "arm_order_counts": plan["arm_order_counts"],
        "holdout_map_family_count": plan["holdout_map_family_count"],
        "holdout_corridor_group_count": plan["holdout_corridor_group_count"],
        "primary_ci_cluster_hierarchy": plan["primary_ci_cluster_hierarchy"],
        "learning_curve_stability": learning_curve_stability,
        "train_source_coverage_disclosure": plan["train_source_coverage_disclosure"],
        "route_asset_count": len(route_assets),
        "validated_disabled_run_config_count": len(run_config_receipts),
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "fixed_dp_tracked_clean": not bool(dp_status),
        "free_bytes_after_preflight": free_bytes,
        "model_loaded": False,
        "runner_built": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "pilot_execution_authorized": False,
        "main_execution_authorized": False,
        "holdout_opened": False,
        "holdout_open_count": 0,
        "per_arm_candidate_tensor_validation_pending_pilot": True,
        "t0_cross_arm_identity_validation_pending_pilot": True,
        "post_divergence_cross_arm_tensor_identity_required": False,
        "latency_comparison_authorized": False,
        "claim_authorized": False,
        "next_work_target": "v24_paired_calibration_capability_pilot_execution_only",
    }
    _write_json(output_dir / "preflight_result.json", result)
    (output_dir / "summary.md").write_text(
        "# v24 paired closed-loop static preflight\n\n"
        f"- status: `{result['status']}`\n"
        f"- routes train/calibration/holdout: `375 / 2 / 24`\n"
        f"- planned capability/pilot/main pairs: `1 / 2 / 120`\n"
        "- simulator/model/candidates/outcomes/holdout opened: `false / false / false / false / false`\n"
        "- AB/BA pilot/main order: `1/1` and `60/60`; latency descriptive only\n"
        "- post-divergence cross-arm tensors: state-conditioned and not compared\n"
        "- train source coverage complete/failed: `1054 / 821`; concentration risk disclosed\n",
        encoding="utf-8",
    )
    (output_dir / "HEADS.txt").write_text(
        f"CAMP_HEAD={camp_head}\nFIXED_DP_HEAD={dp_head}\n", encoding="ascii"
    )
    (output_dir / "COMMAND.txt").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (output_dir / "stdout.txt").write_text(
        json.dumps(
            {
                "status": result["status"],
                "check_count": result["check_count"],
                "failed_count": result["failed_count"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (output_dir / "run.exit").write_text("0\n" if not failed else "1\n", encoding="ascii")
    result["root_sha256"] = _seal(output_dir)
    if failed:
        raise ValueError(f"v24 paired static preflight failed: {failed}")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_static_preflight(
        config_path=args.config,
        dp_repo=args.dp_repo,
        camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
