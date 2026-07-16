#!/usr/bin/env python3
"""Independent result review for the single-open v24 holdout main execution.

This module deliberately does not import any paired producer, simulator runner,
or the production statistics module.  It consumes only complete-sealed evidence
and reconstructs the frozen schedule, receipt invariants, and statistics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
HOLDOUT_SEEDS = (24201, 24202, 24203, 24204, 24205)
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
SPEED_TOLERANCES = ("0.0", "0.05", "0.1", "0.2")
BOOTSTRAP_RESAMPLES = 5_000
BOOTSTRAP_SEED = 24_047
TIE_TOLERANCE = 1e-12
MINIMUM_FREE_BYTES = 10 * 1024**3
ARM_ORDER_DOMAIN = "camp-v24-paired-arm-order-v1"
HOLDOUT_STATE_SCHEMA = "camp_dp_v24_holdout_once_state_v1"
HEX = frozenset("0123456789abcdef")
LATENCY_STAGES = {
    "dp": {
        "default": "default_inference",
        "tracker": "tracker",
        "total": "total_planning",
    },
    "camp": {
        "default": "default_inference",
        "k8_candidate": "candidate_inference",
        "atom": "atom_materialization",
        "selector": "selector",
        "tracker": "tracker",
        "total": "total_planning",
    },
}
TRAIN_SOURCE_COVERAGE_DISCLOSURE = {
    "retained": 1875,
    "complete": 1054,
    "failed": 821,
    "failure_rate": 821 / 1875,
}
LEARNING_CURVE_STABILITY = {
    "levels_percent": [25, 50, 75, 100],
    "weights_l1_to_full": [
        0.3998769535788546,
        0.18971764213000833,
        0.20611942009995507,
        0.0,
    ],
    "effective_support_gt_1e_6": [3, 3, 3, 3],
    "candidate0_selection_rate": [
        0.20219094175157548,
        0.2786534178516361,
        0.25863020176544765,
        0.270222432001888,
    ],
    "selected_index_histogram_l1_to_full": [
        0.13606298050062507,
        0.019765760782601463,
        0.023184460472880697,
        0.0,
    ],
    "selected_index_argmax": [0, 0, 0, 0],
    "full_effective_support_indices": [7, 8, 13],
    "full_effective_support_names": [
        "lane_deviation",
        "clearance",
        "dp_prior_jerk_excess_cost",
    ],
    "full_effective_support_weights": [
        0.4178605234516141,
        0.5784894895043772,
        0.0036499870440052018,
    ],
    "distribution_concentration_is_automatic_failure": False,
    "risk_disclosure_required": True,
    "calibration_or_holdout_repair_authorized": False,
}
SECONDARY_DIRECTIONS = {
    "route_progress_m": "higher_is_better",
    "route_completion_rate": "higher_is_better",
    "mean_abs_jerk_mps3": "lower_is_better",
    "max_jerk_mps3": "lower_is_better",
    "mean_abs_lateral_acceleration_mps2": "lower_is_better",
    "max_abs_lateral_acceleration_mps2": "lower_is_better",
}
PRODUCER_PROVENANCE_FILES = (
    "scripts/integrations/evaluate_diffusion_planner_v24_pairs.py",
    "scripts/integrations/prepare_diffusion_planner_v24_paired_evaluation.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "camp_core/camp_core/evaluation/diffusion_planner_v24_statistics.py",
    "camp_core/camp_core/integrations/diffusion_planner_v21_native.py",
    "camp_core/camp_core/integrations/diffusion_planner_v22_native.py",
    "configs/integrations/diffusion_planner_v24_paired_evaluation.json",
)
EVIDENCE_GUARD_NAMES = (
    "artifact_sha_verified",
    "per_arm_candidate_immutability_verified",
    "per_arm_candidate0_default_identity_verified",
    "t0_cross_arm_input_and_candidate_identity_verified",
    "independent_review_passed",
    "split_zero_overlap_verified",
    "holdout_once_verified",
    "arm_order_balance_verified",
    "feature_identity_denylist_verified",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _require_sha256(value: Any, name: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return str(value)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _loads_json(value: str) -> Any:
    result = json.loads(
        value,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )
    _reject_nonfinite_json_numbers(result, "json")
    return result


def _reject_nonfinite_json_numbers(value: Any, name: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite JSON number is forbidden at {name}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_nonfinite_json_numbers(item, f"{name}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nonfinite_json_numbers(item, f"{name}[{index}]")


def _load_json(path: Path) -> Any:
    return _loads_json(Path(path).read_text(encoding="utf-8"))


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


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0.0):
        suffix = " finite and nonnegative" if nonnegative else " finite"
        raise ValueError(f"{name} must be{suffix}")
    return result


def _integer(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} is below its minimum")
    return int(value)


def verify_complete_seal(
    root: Path,
    expected_root_sha256: str,
    label: str,
    *,
    allowed_nested_seal_roots: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify root receipt, every manifest entry, and manifest completeness."""
    raw_root = Path(root)
    if raw_root.is_symlink():
        raise ValueError(f"{label} artifact root must not be a symlink")
    root = raw_root.resolve()
    expected_root_sha256 = _require_sha256(
        expected_root_sha256, f"{label} expected root"
    )
    if not root.is_dir():
        raise ValueError(f"{label} artifact directory is missing")
    sums = root / "SHA256SUMS"
    root_sums = root / "ROOT_SHA256SUMS"
    if not sums.is_file() or not root_sums.is_file():
        raise ValueError(f"{label} complete seal is missing")
    actual_root = _sha256_file(sums)
    if actual_root != expected_root_sha256:
        raise ValueError(f"{label} root SHA256 mismatch")
    if root_sums.read_text(encoding="ascii") != f"{actual_root}  SHA256SUMS\n":
        raise ValueError(f"{label} ROOT_SHA256SUMS mismatch")

    allowed_nested = {
        PurePosixPath(value).as_posix() for value in allowed_nested_seal_roots
    }
    if any(
        PurePosixPath(value).is_absolute()
        or ".." in PurePosixPath(value).parts
        or "\\" in value
        for value in allowed_nested
    ):
        raise ValueError(f"{label} allowed nested seal root is unsafe")

    declared: dict[str, str] = {}
    for line_number, line in enumerate(
        sums.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.count("  ") != 1 or line != line.strip():
            raise ValueError(f"{label} malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        _require_sha256(digest, f"{label} manifest digest")
        pure = PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or pure.as_posix() != relative
            or relative in declared
            or relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ):
            raise ValueError(f"{label} unsafe or duplicate manifest path")
        path = root.joinpath(*pure.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"{label} manifest file is missing or symlinked: {relative}")
        if _sha256_file(path) != digest:
            raise ValueError(f"{label} file SHA256 mismatch: {relative}")
        declared[relative] = digest

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{label} artifact contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            continue
        if (
            path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}
            and path.parent.relative_to(root).as_posix() in allowed_nested
        ):
            continue
        actual.add(relative)
    if set(declared) != actual:
        missing = sorted(actual - set(declared))[:5]
        stale = sorted(set(declared) - actual)[:5]
        raise ValueError(
            f"{label} seal is incomplete (unlisted={missing}, stale={stale})"
        )
    return {
        "label": label,
        "root": root.as_posix(),
        "root_sha256": actual_root,
        "file_count": len(declared),
        "manifest_paths": sorted(declared),
    }


def seal_artifact(root: Path) -> str:
    root = Path(root)
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha256 = _sha256_file(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha256}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha256


def _require_clean_completion(root: Path, label: str) -> None:
    run_exit = root / "run.exit"
    if not run_exit.is_file() or run_exit.read_text(encoding="ascii") != "0\n":
        raise ValueError(f"{label} run.exit is not clean")


def _artifact_declared_path(root: Path, declared: Any, name: str) -> Path:
    path = Path(str(declared)).resolve()
    root = Path(root).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"{name} declared path escapes its sealed artifact")
    if not path.is_file():
        raise ValueError(f"{name} declared file is missing")
    return path


def _git_text(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_bytes(repo: Path, revision_path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", revision_path],
        check=True,
        capture_output=True,
    ).stdout


def _assert_json_close(actual: Any, expected: Any, name: str) -> None:
    """Exact structural comparison with tight finite numeric tolerance."""
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping) or set(actual) != set(expected):
            raise ValueError(f"{name} mapping keys differ")
        for key in expected:
            _assert_json_close(actual[key], expected[key], f"{name}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{name} list shape differs")
        for index, (left, right) in enumerate(zip(actual, expected)):
            _assert_json_close(left, right, f"{name}[{index}]")
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if actual != expected or type(actual) is not type(expected):
            raise ValueError(f"{name} differs")
        return
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        left = _finite(actual, name)
        right = _finite(expected, name)
        if not math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"{name} numeric value differs")
        return
    if actual != expected:
        raise ValueError(f"{name} differs")


def _pair_key(run_config: Mapping[str, Any]) -> str:
    protocol = _mapping(run_config, "protocol")
    routes = run_config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("main run config must contain exactly one route")
    route = _mapping({"route": routes[0]}, "route")
    seed = _integer(_mapping(run_config, "seeds").get("scenario"), "scenario seed")
    return f"{protocol.get('evaluation_split')}/{route.get('name')}/seed_{seed}"


def _rank_sha256(pair_key: str) -> str:
    return _sha256_bytes(f"{ARM_ORDER_DOMAIN}\0{pair_key}".encode("utf-8"))


def _validate_main_run_config(run_config: Mapping[str, Any]) -> None:
    if run_config.get("schema_version") != "camp_dp_v24_native_evaluation_run_v1":
        raise ValueError("main run-config schema mismatch")
    fixed_dp = _mapping(run_config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("main run-config fixed DP head mismatch")
    for field in ("checkpoint", "args_json"):
        asset = _mapping(fixed_dp, field)
        _require_sha256(asset.get("sha256"), f"fixed DP {field}")
        if not isinstance(asset.get("path"), str) or not asset["path"]:
            raise ValueError(f"fixed DP {field} path is missing")

    selector = _mapping(run_config, "selector")
    if (
        selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != "v22_source_valid"
        or selector.get("role") != "v24_primary_frozen_train_only"
    ):
        raise ValueError("main selector contract mismatch")
    for field in ("root_sha256", "model_sha256"):
        _require_sha256(selector.get(field), f"selector {field}")
    for field in ("atom_scales", "weights"):
        asset = _mapping(selector, field)
        _require_sha256(asset.get("sha256"), f"selector {field}")

    map_asset = _mapping(run_config, "map")
    for field in ("sha256", "logical_map_sha256", "corridor_group_sha256"):
        _require_sha256(map_asset.get(field), f"map {field}")
    if not isinstance(map_asset.get("map_family_id"), str) or not map_asset[
        "map_family_id"
    ]:
        raise ValueError("map family id is missing")
    route = _mapping({"route": run_config["routes"][0]}, "route")
    for field in ("name", "sha256"):
        _require_sha256(route.get(field), f"route {field}")

    seeds = _mapping(run_config, "seeds")
    scenario_seed = _integer(seeds.get("scenario"), "scenario seed", minimum=0)
    if seeds != {
        "scenario": scenario_seed,
        "candidate": scenario_seed,
        "bootstrap": scenario_seed,
        "formal_forbidden": [11, 12, 13],
    } or scenario_seed not in HOLDOUT_SEEDS:
        raise ValueError("main seed namespace mismatch")
    protocol = _mapping(run_config, "protocol")
    expected_flags = {
        "evaluation_mode": "main",
        "evaluation_split": "holdout",
        "evaluation_steps": 64,
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
    for field, expected in expected_flags.items():
        _assert_json_close(
            protocol.get(field), expected, f"main protocol field {field}"
        )
    if protocol.get("arm_order") not in (["dp", "camp"], ["camp", "dp"]):
        raise ValueError("main arm order is invalid")
    _require_sha256(protocol.get("arm_order_rank_sha256"), "arm-order rank")
    spawn = _mapping(run_config, "spawn_config")
    if spawn.get("seed") != scenario_seed or spawn.get("max_steps") != 64:
        raise ValueError("main spawn seed/steps mismatch")


def reconstruct_main_schedule(preflight_root: Path) -> dict[str, Any]:
    """Parse and independently reconstruct the exact frozen 120-pair schedule."""
    preflight_root = Path(preflight_root)
    lines = (preflight_root / "disabled_run_configs.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    if any(not line.strip() for line in lines):
        raise ValueError("disabled run-config JSONL contains a blank record")
    configs = [_loads_json(line) for line in lines]
    main = [
        item
        for item in configs
        if _mapping(item, "protocol").get("evaluation_mode") == "main"
    ]
    if len(configs) != 123 or len(main) != 120:
        raise ValueError("sealed preflight run-config population mismatch")
    for item in main:
        _validate_main_run_config(item)

    by_key: dict[str, Mapping[str, Any]] = {}
    route_seeds: dict[str, set[int]] = defaultdict(set)
    route_metadata: dict[str, dict[str, Any]] = {}
    families: set[str] = set()
    corridors: set[str] = set()
    for item in main:
        key = _pair_key(item)
        if key in by_key:
            raise ValueError("main pair keys are not unique")
        by_key[key] = item
        route = item["routes"][0]
        route_identity = str(route["name"])
        seed = int(item["seeds"]["scenario"])
        route_seeds[route_identity].add(seed)
        metadata = {
            "map_family_id": str(item["map"]["map_family_id"]),
            "logical_map_sha256": str(item["map"]["logical_map_sha256"]),
            "corridor_group_sha256": str(item["map"]["corridor_group_sha256"]),
            "source_map_path": str(item["map"]["path"]),
            "source_map_sha256": str(item["map"]["sha256"]),
            "route_asset_path": str(route["path"]),
            "route_asset_sha256": str(route["sha256"]),
        }
        prior = route_metadata.setdefault(route_identity, metadata)
        if prior != metadata:
            raise ValueError("one main route changes metadata across its five seeds")
        families.add(str(item["map"]["map_family_id"]))
        corridors.add(str(item["map"]["corridor_group_sha256"]))

    if len(route_seeds) != 24 or any(
        tuple(sorted(seeds)) != HOLDOUT_SEEDS for seeds in route_seeds.values()
    ):
        raise ValueError("main route x seed schedule mismatch")
    if len(families) != 1 or len(corridors) != 3:
        raise ValueError("main family/corridor population mismatch")

    ranked = sorted(by_key, key=_rank_sha256)
    expected_orders = {
        key: (["dp", "camp"] if index < 60 else ["camp", "dp"])
        for index, key in enumerate(ranked)
    }
    counts: Counter[str] = Counter()
    for key, item in by_key.items():
        protocol = item["protocol"]
        rank = _rank_sha256(key)
        if protocol.get("arm_order_rank_sha256") != rank:
            raise ValueError("main arm-order rank digest mismatch")
        if protocol.get("arm_order") != expected_orders[key]:
            raise ValueError("main deterministic balanced arm order mismatch")
        counts["dp_camp" if protocol["arm_order"] == ["dp", "camp"] else "camp_dp"] += 1
    if dict(counts) != {"dp_camp": 60, "camp_dp": 60}:
        raise ValueError("main AB/BA balance mismatch")

    receipts = _load_json(preflight_root / "run_config_receipts.json")
    receipt_by_key = {
        str(item["pair_key"]): item
        for item in receipts
        if item.get("mode") == "main"
    }
    if set(receipt_by_key) != set(by_key):
        raise ValueError("preflight run-config receipt population mismatch")
    for key, item in by_key.items():
        receipt = receipt_by_key[key]
        if (
            receipt.get("config_sha256") != _canonical_sha256(item)
            or receipt.get("execution_authorized") is not False
            or receipt.get("holdout_access_authorized") is not False
        ):
            raise ValueError("preflight run-config receipt mismatch")

    plan = _load_json(preflight_root / "evaluation_plan.json")
    if plan.get("schema") != "camp_dp_v24_native_paired_evaluation_plan_v1":
        raise ValueError("preflight evaluation plan schema mismatch")
    plan_without_hash = dict(plan)
    declared_plan_hash = plan_without_hash.pop("plan_sha256", None)
    if declared_plan_hash != _canonical_sha256(plan_without_hash):
        raise ValueError("preflight evaluation plan SHA256 mismatch")
    planned_rows = _mapping(plan, "schedules").get("main")
    if not isinstance(planned_rows, list) or len(planned_rows) != 120:
        raise ValueError("preflight public main schedule mismatch")
    public_by_key = {str(item.get("pair_key")): item for item in planned_rows}
    if set(public_by_key) != set(by_key):
        raise ValueError("public plan and disabled main schedule differ")
    for key, item in by_key.items():
        public = public_by_key[key]
        expected = {
            "mode": "main",
            "split": "holdout",
            "route_identity_sha256": item["routes"][0]["name"],
            "map_family_id": item["map"]["map_family_id"],
            "logical_map_sha256": item["map"]["logical_map_sha256"],
            "corridor_group_sha256": item["map"]["corridor_group_sha256"],
            "seed": item["seeds"]["scenario"],
            "max_steps": 64,
            "expected_arms": ["dp", "camp"],
            "included_in_denominator": True,
            "replacement_authorized": False,
            "arm_order": item["protocol"]["arm_order"],
            "arm_order_rank_sha256": item["protocol"]["arm_order_rank_sha256"],
        }
        for name, value in expected.items():
            _assert_json_close(
                public.get(name), value, f"public main schedule {name}"
            )

    return {
        "configs": main,
        "by_key": by_key,
        "route_metadata": route_metadata,
        "pair_keys": sorted(by_key),
        "receipt": {
            "pair_count": 120,
            "unique_pair_count": 120,
            "route_count": 24,
            "seed_count_per_route": 5,
            "seeds": list(HOLDOUT_SEEDS),
            "map_family_count": 1,
            "corridor_group_count": 3,
            "arm_order_counts": dict(counts),
            "arm_order_domain_separator": ARM_ORDER_DOMAIN,
            "deterministic_hash_rank_verified": True,
            "outcome_blind_preregistered_order_control_verified": True,
            "independent_reset_per_arm_verified": True,
            "latency_comparative_conclusion_authorized": False,
        },
        "plan": plan,
    }


def _orientation(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _on_segment(a: np.ndarray, b: np.ndarray, p: np.ndarray, eps: float) -> bool:
    return bool(
        min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps
    )


def _segments_intersect(a: Any, b: Any, c: Any, d: Any) -> bool:
    points = [np.asarray(value, dtype=np.float64) for value in (a, b, c, d)]
    if any(value.shape != (2,) or not np.isfinite(value).all() for value in points):
        raise ValueError("red-light segment points must be finite 2D points")
    first, second, third, fourth = points
    o1 = _orientation(first, second, third)
    o2 = _orientation(first, second, fourth)
    o3 = _orientation(third, fourth, first)
    o4 = _orientation(third, fourth, second)
    eps = 1e-12
    if (o1 > eps and o2 < -eps or o1 < -eps and o2 > eps) and (
        o3 > eps and o4 < -eps or o3 < -eps and o4 > eps
    ):
        return True
    return bool(
        (abs(o1) <= eps and _on_segment(first, second, third, eps))
        or (abs(o2) <= eps and _on_segment(first, second, fourth, eps))
        or (abs(o3) <= eps and _on_segment(third, fourth, first, eps))
        or (abs(o4) <= eps and _on_segment(third, fourth, second, eps))
    )


def _validate_safety_tick(value: Any, expected_index: int, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} safety tick is missing")
    if value.get("source_complete") is not True or value.get("tick_index") != expected_index:
        raise ValueError(f"{name} safety source/index mismatch")
    for field in (
        "speed_mps",
        "ego_heading_rad",
        "route_heading_rad",
        "route_progress_m",
        "min_obb_clearance_m",
    ):
        _finite(value.get(field), f"{name}.{field}", nonnegative=field in {"speed_mps", "route_progress_m"})
    if not isinstance(value.get("five_point_drivable_coverage"), bool):
        raise ValueError(f"{name} drivable coverage must be boolean")
    if not isinstance(value.get("red_light_at_interval_start"), bool):
        raise ValueError(f"{name} red-light source must be boolean")
    for field in ("position_xy", "front_center_prev_xy", "front_center_xy"):
        point = np.asarray(value.get(field), dtype=np.float64)
        if point.shape != (2,) or not np.isfinite(point).all():
            raise ValueError(f"{name}.{field} must be finite [2]")
    stop_lines = np.asarray(value.get("red_stop_lines"), dtype=np.float64)
    if stop_lines.size == 0:
        stop_lines = np.empty((0, 2, 2), dtype=np.float64)
    if stop_lines.ndim != 3 or stop_lines.shape[1:] != (2, 2) or not np.isfinite(stop_lines).all():
        raise ValueError(f"{name} red_stop_lines must be finite [N,2,2]")
    speed_limit = value.get("speed_limit_mps")
    if value["five_point_drivable_coverage"]:
        _finite(speed_limit, f"{name}.speed_limit_mps", nonnegative=True)
        if float(speed_limit) <= 0.0:
            raise ValueError(f"{name} speed limit must be positive")
    ttc = value.get("constant_velocity_circle_ttc_diagnostic_s")
    if ttc is not None:
        _finite(ttc, f"{name}.ttc", nonnegative=True)
    return value


def recompute_safety(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    records = [_validate_safety_tick(tick["safety"], index, "tick") for index, tick in enumerate(ticks)]
    if not records:
        raise ValueError("safety reconstruction requires ticks")
    clearances: list[float] = []
    collision: list[int] = []
    near: list[int] = []
    offroad: list[int] = []
    wrong_way: list[int] = []
    red: list[int] = []
    strict_speed: list[int] = []
    moving_onroad = 0
    evaluated_speed: list[tuple[int, float]] = []
    for record in records:
        index = int(record["tick_index"])
        clearance = float(record["min_obb_clearance_m"])
        clearances.append(clearance)
        if clearance <= 1e-6:
            collision.append(index)
        elif clearance <= 2.0:
            near.append(index)
        covered = bool(record["five_point_drivable_coverage"])
        if not covered:
            offroad.append(index)
        speed = float(record["speed_mps"])
        if covered and speed > 0.5:
            moving_onroad += 1
            error = math.atan2(
                math.sin(float(record["ego_heading_rad"]) - float(record["route_heading_rad"])),
                math.cos(float(record["ego_heading_rad"]) - float(record["route_heading_rad"])),
            )
            if math.cos(error) < 0.0:
                wrong_way.append(index)
        stop_lines = np.asarray(record["red_stop_lines"], dtype=np.float64)
        if stop_lines.size == 0:
            stop_lines = np.empty((0, 2, 2), dtype=np.float64)
        if bool(record["red_light_at_interval_start"]) and speed > 0.5 and any(
            _segments_intersect(
                record["front_center_prev_xy"],
                record["front_center_xy"],
                line[0],
                line[1],
            )
            for line in stop_lines
        ):
            red.append(index)
        if covered:
            excess = max(speed - float(record["speed_limit_mps"]), 0.0)
            evaluated_speed.append((index, excess))
            if excess > 1e-6:
                strict_speed.append(index)
    if moving_onroad == 0 or not evaluated_speed:
        raise ValueError("safety denominator is zero")
    count = len(records)

    def event(tolerance: float) -> dict[str, Any]:
        indices = [
            index
            for index, excess in evaluated_speed
            if excess > tolerance + 1e-6
        ]
        return {
            "tolerance_mps": float(tolerance),
            "event_count": len(indices),
            "event_rate": len(indices) / len(evaluated_speed),
            "event_ticks": indices,
        }

    sensitivity = {
        key: event(float(key)) for key in SPEED_TOLERANCES
    }
    excesses = [value for _index, value in evaluated_speed]
    positive = [index for index, value in evaluated_speed if value > 0.0]
    strict = event(0.0)
    strict["epsilon_mps"] = 1e-6
    speed_protocol = {
        "schema_version": "speed_protocol_v22",
        "dt_s": 0.1,
        "speed_limit_ticks": len(evaluated_speed),
        "strict": strict,
        "operational_tolerance_mps": 0.1,
        "operational": sensitivity["0.1"],
        "sensitivity": sensitivity,
        "continuous": {
            "maximum_excess_mps": max(excesses),
            "mean_excess_mps": sum(excesses) / len(excesses),
            "excess_duration_s": len(positive) * 0.1,
            "magnitude_duration_m": sum(excesses) * 0.1,
            "positive_excess_ticks": positive,
        },
    }
    components = {
        "collision_any": float(bool(collision)),
        "near_miss_noncollision_rate": len(near) / count,
        "offroad_rate": len(offroad) / count,
        "wrong_way_rate": len(wrong_way) / moving_onroad,
        "red_light_violation_any": float(bool(red)),
        "speed_limit_violation_rate": sensitivity["0.1"]["event_rate"],
    }
    cost = sum(SAFETY_WEIGHTS[name] * value for name, value in components.items())
    return {
        "schema_version": "safety_cost_native_v22",
        "safety_cost": cost,
        "components": components,
        "raw_counts": {
            "collision_ticks": len(collision),
            "near_miss_noncollision_ticks": len(near),
            "offroad_ticks": len(offroad),
            "wrong_way_ticks": len(wrong_way),
            "red_light_violation_intervals": len(red),
            "speed_limit_violation_ticks": sensitivity["0.1"]["event_count"],
            "strict_speed_limit_violation_ticks": len(strict_speed),
        },
        "denominators": {
            "clearance_ticks": count,
            "drivable_area_ticks": count,
            "moving_onroad_ticks": moving_onroad,
            "speed_limit_ticks": len(evaluated_speed),
        },
        "minimum_clearance_m": min(clearances),
        "maximum_speed_excess_mps": speed_protocol["continuous"]["maximum_excess_mps"],
        "event_ticks": {
            "collision": collision,
            "near_miss_noncollision": near,
            "offroad": offroad,
            "wrong_way": wrong_way,
            "red_light_violation": red,
            "speed_limit_violation": sensitivity["0.1"]["event_ticks"],
            "strict_speed_limit_violation": strict_speed,
        },
        "five_point_proxy_not_polygon_union": True,
        "speed_protocol": speed_protocol,
    }


def recompute_secondary(
    ticks: Sequence[Mapping[str, Any]],
    stored: Mapping[str, Any],
    native_result: Mapping[str, Any],
    *,
    expected_route_length_m: float,
) -> dict[str, Any]:
    records = [tick["safety"] for tick in ticks]
    positions = np.asarray([record["position_xy"] for record in records], dtype=np.float64)
    speeds = np.asarray([record["speed_mps"] for record in records], dtype=np.float64)
    headings = np.asarray([record["ego_heading_rad"] for record in records], dtype=np.float64)
    if positions.shape != (len(records), 2) or not np.isfinite(positions).all():
        raise ValueError("secondary position ticks are invalid")
    progress = _finite(stored.get("route_progress_m"), "route progress", nonnegative=True)
    stored_length = _finite(
        stored.get("route_length_m"), "stored route length", nonnegative=True
    )
    length = _finite(
        expected_route_length_m, "source-census route length", nonnegative=True
    )
    if length <= 0.0 or not math.isclose(
        stored_length, length, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("stored route length differs from source-census arc length")
    if not math.isclose(
        progress, float(records[-1]["route_progress_m"]), rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("secondary route progress/length mismatch")
    reason = stored.get("termination_reason")
    if not isinstance(reason, str) or not reason or native_result.get("reason") != reason:
        raise ValueError("secondary termination reason mismatch")
    acceleration = np.diff(speeds) / 0.1
    jerk = np.diff(acceleration) / 0.1
    yaw_rate = np.arctan2(np.sin(np.diff(headings)), np.cos(np.diff(headings))) / 0.1
    lateral = speeds[1:] * yaw_rate

    def mean_abs(values: np.ndarray) -> float:
        return float(np.mean(np.abs(values))) if values.size else 0.0

    def max_abs(values: np.ndarray) -> float:
        return float(np.max(np.abs(values))) if values.size else 0.0

    return {
        "dt_s": 0.1,
        "route_progress_m": progress,
        "route_length_m": length,
        "route_completion_rate": min(max(progress / length, 0.0), 1.0),
        "termination_reason": reason,
        "distance_traveled_m": float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()),
        "stopped_fraction": float(np.mean(speeds <= 0.5)),
        "mean_speed_mps": float(np.mean(speeds)),
        "max_speed_mps": float(np.max(speeds)),
        "mean_abs_acceleration_mps2": mean_abs(acceleration),
        "max_acceleration_mps2": max_abs(acceleration),
        "mean_abs_jerk_mps3": mean_abs(jerk),
        "max_jerk_mps3": max_abs(jerk),
        "mean_abs_yaw_rate_radps": mean_abs(yaw_rate),
        "max_abs_yaw_rate_radps": max_abs(yaw_rate),
        "mean_abs_lateral_acceleration_mps2": mean_abs(lateral),
        "max_abs_lateral_acceleration_mps2": max_abs(lateral),
    }


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "mean": None, "median": None, "p95": None, "p99": None, "max": None}
    if not np.isfinite(array).all() or np.any(array < 0.0):
        raise ValueError("latency distribution contains invalid values")
    return {
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p95": float(np.percentile(array, 95.0)),
        "p99": float(np.percentile(array, 99.0)),
        "max": float(array.max()),
    }


def _recompute_arm_latency(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = sorted({name for tick in ticks for name in _mapping(tick, "latency_ms")})
    return {
        name: _distribution(
            [float(tick["latency_ms"][name]) for tick in ticks if name in tick["latency_ms"]]
        )
        for name in names
    }


def validate_tick_receipt(
    tick: Mapping[str, Any], arm: str, expected_index: int
) -> dict[str, Any]:
    name = f"{arm}.tick_{expected_index}"
    if tick.get("tick_index") != expected_index:
        raise ValueError(f"{name} index mismatch")
    if "native_ranked_k8" in tick and tick.get("native_ranked_k8") is not False:
        raise ValueError(f"{name} native-ranked provenance drift")
    _require_sha256(tick.get("input_sha256"), f"{name} input")
    padding = _mapping(tick, "padding")
    observed = _integer(padding.get("observed_frames"), f"{name} observed frames", minimum=1)
    padded = _integer(padding.get("padded_frames"), f"{name} padded frames", minimum=0)
    if observed > 31 or padded != 31 - observed or padding.get("padding_policy") != "native_zero_left_pad_to_31_v1":
        raise ValueError(f"{name} causal padding mismatch")
    if _mapping(tick, "tracker").get("status") != "ok":
        raise ValueError(f"{name} tracker status mismatch")
    _validate_safety_tick(tick.get("safety"), expected_index, name)
    latency = _mapping(tick, "latency_ms")
    for stage in LATENCY_STAGES[arm].values():
        if stage not in latency:
            raise ValueError(f"{name} missing latency stage: {stage}")
    for stage, value in latency.items():
        _finite(value, f"{name} latency {stage}", nonnegative=True)

    hashes = (
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate_neighbor_sha256",
        "selected_trajectory_sha256",
        "global_rng_sha256_before",
        "global_rng_sha256_after",
        "default_output_sha256",
    )
    for field in hashes:
        _require_sha256(tick.get(field), f"{name} {field}")
    if tick["candidate_tensor_sha256_before"] != tick["candidate_tensor_sha256_after"]:
        raise ValueError(f"{name} candidate tensor mutation")
    if tick["global_rng_sha256_before"] != tick["global_rng_sha256_after"]:
        raise ValueError(f"{name} global RNG mutation")
    rows = tick.get("candidate_row_sha256")
    if not isinstance(rows, list) or len(rows) != 8 or any(not _is_sha256(value) for value in rows):
        raise ValueError(f"{name} candidate-row digest list mismatch")
    selected = _integer(tick.get("selected_index"), f"{name} selected index", minimum=0)
    if selected >= 8 or tick["selected_trajectory_sha256"] != rows[selected]:
        raise ValueError(f"{name} selected-row identity mismatch")
    identity = _mapping(tick, "default_candidate0_identity")
    if (
        identity.get("elementwise_equal") is not True
        or _finite(identity.get("max_abs_difference"), f"{name} default max diff") != 0.0
        or identity.get("native_ranked_k8") is not False
        or identity.get("default_output_sha256") != rows[0]
        or identity.get("candidate0_sha256") != rows[0]
        or tick.get("default_output_sha256") != rows[0]
        or tick.get("npc_operational_outputs_unchanged") is not True
    ):
        raise ValueError(f"{name} default/candidate0 or NPC identity mismatch")
    if (
        "post_divergence_cross_arm_tensor_identity_required" in tick
        and tick.get("post_divergence_cross_arm_tensor_identity_required") is not False
    ):
        raise ValueError(f"{name} post-divergence comparison contract mismatch")
    if "candidate_tensor" in tick or "atom_matrix" in tick:
        raise ValueError(f"{name} unexpectedly contains raw candidate/atom bytes")

    all_high = False
    if arm == "dp":
        if (
            selected != 0
            or tick.get("candidate0_operational_default") is not True
            or tick.get("selection_policy") != "candidate0_operational_default"
            or tick.get("score_contract") != "candidate0_operational_default"
            or tick.get("eligibility_mask_name") != "candidate0_operational_default"
        ):
            raise ValueError(f"{name} DP operational-default contract mismatch")
    else:
        if (
            tick.get("selection_policy") != "v22_source_valid"
            or tick.get("score_contract") != "score_k(w)=a_k^T w"
            or tick.get("eligibility_mask_name") != "source_valid_mask"
        ):
            raise ValueError(f"{name} CAMP selector contract mismatch")
        _require_sha256(tick.get("atom_matrix_sha256"), f"{name} atom matrix")
        masks: dict[str, list[bool]] = {}
        for field in ("source_valid_mask", "physical_feasible_mask", "source_complete_mask"):
            values = tick.get(field)
            if not isinstance(values, list) or len(values) != 8 or any(type(value) is not bool for value in values):
                raise ValueError(f"{name} {field} mismatch")
            masks[field] = values
        scores = tick.get("scores")
        if not isinstance(scores, list) or len(scores) != 8:
            raise ValueError(f"{name} score receipt mismatch")
        score_values = [_finite(value, f"{name} score") for value in scores]
        if not any(masks["source_valid_mask"]):
            raise ValueError(f"{name} has no source-valid candidate")
        expected = min(
            range(8),
            key=lambda index: score_values[index]
            if masks["source_valid_mask"][index]
            else math.inf,
        )
        if selected != expected or not masks["source_valid_mask"][selected]:
            raise ValueError(f"{name} CAMP source-valid affine argmin mismatch")
        all_high = all(masks["source_valid_mask"]) and not any(
            masks["physical_feasible_mask"]
        )
        if tick.get("all_k_high_risk") is not all_high:
            raise ValueError(f"{name} all-K-high-risk receipt mismatch")
    return {"selected_index": selected, "all_k_high_risk": all_high}


def _spawn_sha256(run_config: Mapping[str, Any]) -> str:
    payload = dict(_mapping(run_config, "spawn_config"))
    payload["max_steps"] = 64
    return _canonical_sha256(payload)


def validate_arm_receipt(
    receipt: Mapping[str, Any],
    arm: str,
    run_config: Mapping[str, Any],
    *,
    expected_route_length_m: float,
) -> dict[str, Any]:
    if receipt.get("schema_version") != "v21_native_arm_receipt_v1" or receipt.get("arm") != arm:
        raise ValueError(f"{arm} arm schema/identity mismatch")
    status = receipt.get("status")
    if status not in {"ok", "source_invalid", "failed"}:
        raise ValueError(f"{arm} arm status mismatch")
    if status != "ok":
        if not isinstance(receipt.get("failure_stage"), str) or not isinstance(receipt.get("reason"), str):
            raise ValueError(f"{arm} failed-arm accounting is incomplete")
        if receipt.get("claim_authorized") is not False:
            raise ValueError(f"{arm} failed arm cannot authorize a claim")
        return {"status": status, "ticks": [], "selected_indices": [], "all_k_tick_count": 0}

    route = run_config["routes"][0]
    fixed_dp = run_config["fixed_dp"]
    expected = {
        "route_name": route["name"],
        "route_sha256": route["sha256"],
        "logical_map_sha256": run_config["map"]["sha256"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": fixed_dp["checkpoint"]["sha256"],
        "args_sha256": fixed_dp["args_json"]["sha256"],
        "scenario_seed": run_config["seeds"]["scenario"],
        "spawn_config_sha256": _spawn_sha256(run_config),
        "claim_authorized": False,
    }
    for field, value in expected.items():
        _assert_json_close(receipt.get(field), value, f"{arm} arm base {field}")
    for field in ("route_sha256", "initial_state_sha256", "initial_input_sha256"):
        _require_sha256(receipt.get(field), f"{arm} {field}")
    initial_state = _sha256_bytes(
        ("v21_native_scene_context_v1\0" + str(receipt["initial_input_sha256"])).encode("ascii")
    )
    if receipt["initial_state_sha256"] != initial_state:
        raise ValueError(f"{arm} initial-state receipt mismatch")
    _finite(receipt.get("evaluation_wall_clock_s"), f"{arm} wall clock", nonnegative=True)
    ticks = receipt.get("ticks")
    if not isinstance(ticks, list) or len(ticks) != 64:
        raise ValueError(f"{arm} tick population mismatch")
    tick_results = [validate_tick_receipt(tick, arm, index) for index, tick in enumerate(ticks)]
    if ticks[0]["input_sha256"] != receipt["initial_input_sha256"]:
        raise ValueError(f"{arm} initial input mismatch")
    safety = recompute_safety(ticks)
    _assert_json_close(receipt.get("safety"), safety, f"{arm}.safety")
    native_result = _mapping(receipt, "native_result")
    secondary = recompute_secondary(
        ticks,
        _mapping(receipt, "secondary"),
        native_result,
        expected_route_length_m=expected_route_length_m,
    )
    _assert_json_close(receipt.get("secondary"), secondary, f"{arm}.secondary")
    latency = _recompute_arm_latency(ticks)
    _assert_json_close(receipt.get("latency"), latency, f"{arm}.latency")
    if arm == "camp":
        scale = _mapping(receipt, "selector_scale_contract")
        if (
            scale.get("effective_atom_schema_version") != "dp_camp_v10_14d"
            or scale.get("compatibility_policy") != "exact_atom_names_on_frozen_sha_v1"
        ):
            raise ValueError("CAMP selector-scale contract mismatch")
    return {
        "status": status,
        "ticks": ticks,
        "safety": safety,
        "secondary": secondary,
        "selected_indices": [item["selected_index"] for item in tick_results],
        "all_k_tick_count": sum(item["all_k_high_risk"] for item in tick_results),
    }


def _expected_failure_class(dp_status: str, camp_status: str) -> tuple[bool, bool, str | None]:
    source_invalid = "source_invalid" in {dp_status, camp_status}
    execution_failure = "failed" in {dp_status, camp_status}
    failure_class = "execution_failure" if execution_failure else "source_failure" if source_invalid else None
    return source_invalid, execution_failure, failure_class


def validate_paired_reset_and_t0(
    dp_arm: Mapping[str, Any], camp_arm: Mapping[str, Any], pair_key: str
) -> None:
    """Validate paired reset plus t=0 identity, without post-t=0 comparison."""
    for field in (
        "initial_state_sha256",
        "initial_input_sha256",
        "spawn_config_sha256",
        "scenario_seed",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
    ):
        if dp_arm.get(field) != camp_arm.get(field):
            raise ValueError(f"{pair_key} paired reset mismatch: {field}")
    dp_secondary = _mapping(dp_arm, "secondary")
    camp_secondary = _mapping(camp_arm, "secondary")
    _assert_json_close(
        camp_secondary.get("route_length_m"),
        dp_secondary.get("route_length_m"),
        f"{pair_key} paired route-length denominator",
    )
    dp_ticks = dp_arm.get("ticks")
    camp_ticks = camp_arm.get("ticks")
    if not isinstance(dp_ticks, list) or not isinstance(camp_ticks, list) or not dp_ticks or not camp_ticks:
        raise ValueError(f"{pair_key} successful arms require ticks")
    for field in (
        "input_sha256",
        "candidate_tensor_sha256_before",
        "candidate_row_sha256",
        "candidate_neighbor_sha256",
        "default_output_sha256",
    ):
        if dp_ticks[0].get(field) != camp_ticks[0].get(field):
            raise ValueError(f"{pair_key} t0 cross-arm mismatch: {field}")


def inspect_execution(
    execution_root: Path,
    schedule: Mapping[str, Any],
    route_sources: Mapping[str, Mapping[str, Any]],
    *,
    expected_execution_source_head: str,
    expected_preflight_root_sha256: str,
) -> dict[str, Any]:
    execution_root = Path(execution_root)
    summary = _load_json(execution_root / "summary.json")
    rows = _load_json(execution_root / "pair_rows.json")
    by_key = schedule["by_key"]
    if not isinstance(rows, list) or len(rows) != 120:
        raise ValueError("execution retained-row population mismatch")
    row_by_key = {str(row.get("pair_key")): row for row in rows}
    if len(row_by_key) != 120 or set(row_by_key) != set(by_key):
        raise ValueError("execution pair population differs from frozen schedule")

    recomputed_rows: list[dict[str, Any]] = []
    dp_tick_count = 0
    camp_tick_count = 0
    all_k_tick_count = 0
    for pair_key in schedule["pair_keys"]:
        run_config = by_key[pair_key]
        route_identity = str(run_config["routes"][0]["name"])
        if route_identity not in route_sources:
            raise ValueError(f"{pair_key} has no sealed source-route binding")
        expected_route_length_m = route_sources[route_identity][
            "source_arc_length_m"
        ]
        row = row_by_key[pair_key]
        pair_root = execution_root.joinpath(*PurePosixPath(pair_key).parts)
        pair_file = _load_json(pair_root / "pair.json")
        if pair_file != row:
            raise ValueError(f"{pair_key} pair.json differs from pair_rows.json")
        arms = {
            arm: _load_json(pair_root / f"{arm}.json") for arm in ("dp", "camp")
        }
        inspected = {
            arm: validate_arm_receipt(
                arms[arm],
                arm,
                run_config,
                expected_route_length_m=expected_route_length_m,
            )
            for arm in ("dp", "camp")
        }
        dp_status = str(inspected["dp"]["status"])
        camp_status = str(inspected["camp"]["status"])
        source_invalid, execution_failure, failure_class = _expected_failure_class(dp_status, camp_status)
        complete = dp_status == camp_status == "ok"
        expected_row = {
            "schema_version": "v22_retained_pair_row_v1",
            "pair_key": pair_key,
            "split": "holdout",
            "included_in_denominator": True,
            "paired_complete": complete,
            "failure_class": failure_class,
            "hard_invalid": source_invalid,
            "execution_failure": execution_failure,
            "dp_status": dp_status,
            "camp_status": camp_status,
            "dp_failure_stage": arms["dp"].get("failure_stage"),
            "camp_failure_stage": arms["camp"].get("failure_stage"),
            "dp_failure_reason": arms["dp"].get("reason"),
            "camp_failure_reason": arms["camp"].get("reason"),
            "route_retained": True,
            "replacement_used": False,
            "source_invalid": source_invalid,
            "route_identity_sha256": run_config["routes"][0]["name"],
            "map_family_id": run_config["map"]["map_family_id"],
            "corridor_group_sha256": run_config["map"]["corridor_group_sha256"],
            "logical_map_sha256": run_config["map"]["logical_map_sha256"],
            "seed": run_config["seeds"]["scenario"],
            "arm_order": run_config["protocol"]["arm_order"],
            "arm_order_rank_sha256": run_config["protocol"]["arm_order_rank_sha256"],
            "post_divergence_cross_arm_tensor_compared": False,
            "native_ranked_k8_provenance_claimed": False,
        }
        for field, value in expected_row.items():
            _assert_json_close(
                row.get(field), value, f"{pair_key} retained row {field}"
            )
        expected_guards = complete
        for field in (
            "per_arm_candidate_immutability_verified",
            "per_arm_candidate0_default_identity_verified",
            "t0_cross_arm_input_and_candidate_identity_verified",
        ):
            if row.get(field) is not expected_guards:
                raise ValueError(f"{pair_key} retained row guard mismatch: {field}")

        if complete:
            dp_ticks = inspected["dp"]["ticks"]
            camp_ticks = inspected["camp"]["ticks"]
            validate_paired_reset_and_t0(arms["dp"], arms["camp"], pair_key)
            # Cross-arm candidate tensors after t=0 are intentionally not compared.
            camp_all_high = inspected["camp"]["all_k_tick_count"] > 0
            if row.get("all_k_high_risk") is not camp_all_high:
                raise ValueError(f"{pair_key} all-K pair stratum mismatch")
            copied = {
                "dp_safety": inspected["dp"]["safety"],
                "camp_safety": inspected["camp"]["safety"],
                "dp_secondary": inspected["dp"]["secondary"],
                "camp_secondary": inspected["camp"]["secondary"],
                "dp_tick_latency_ms": [tick["latency_ms"] for tick in dp_ticks],
                "camp_tick_latency_ms": [tick["latency_ms"] for tick in camp_ticks],
                "camp_selected_indices": inspected["camp"]["selected_indices"],
            }
            for field, value in copied.items():
                _assert_json_close(row.get(field), value, f"{pair_key}.row.{field}")
            dp_tick_count += len(dp_ticks)
            camp_tick_count += len(camp_ticks)
            all_k_tick_count += inspected["camp"]["all_k_tick_count"]
        else:
            if any(
                field in row
                for field in (
                    "dp_safety",
                    "camp_safety",
                    "dp_secondary",
                    "camp_secondary",
                    "camp_selected_indices",
                )
            ):
                raise ValueError(f"{pair_key} failed pair contains complete-only fields")
        recomputed_rows.append(dict(row))

    complete_count = sum(row["paired_complete"] is True for row in recomputed_rows)
    source_count = sum(row["source_invalid"] is True for row in recomputed_rows)
    execution_count = sum(row["execution_failure"] is True for row in recomputed_rows)
    expected_summary = {
        "schema": "camp_dp_v24_native_paired_execution_summary_v1",
        "mode": "main",
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": complete_count,
        "source_invalid_pair_count": source_count,
        "execution_failure_pair_count": execution_count,
        "arm_order_counts": {"dp_camp": 60, "camp_dp": 60},
        "camp_head": expected_execution_source_head,
        "preflight_root_sha256": expected_preflight_root_sha256,
        "holdout_opened": True,
        "holdout_open_count": 1,
        "post_divergence_cross_arm_tensor_compared": False,
        "latency_comparison_authorized": False,
        "final_claim_authorized": False,
    }
    for field, value in expected_summary.items():
        _assert_json_close(summary.get(field), value, f"execution summary {field}")
    expected_status = "complete" if complete_count == 120 else "complete_with_retained_failures"
    if summary.get("status") != expected_status:
        raise ValueError("execution summary completion status mismatch")
    _finite(summary.get("wall_clock_s"), "execution wall clock", nonnegative=True)
    for field in ("free_bytes_before", "free_bytes_after"):
        if _integer(summary.get(field), field, minimum=0) <= MINIMUM_FREE_BYTES:
            raise ValueError("execution crossed the 10 GiB disk floor")

    return {
        "summary": summary,
        "rows": recomputed_rows,
        "complete_count": complete_count,
        "source_invalid_count": source_count,
        "execution_failure_count": execution_count,
        "dp_tick_count": dp_tick_count,
        "camp_tick_count": camp_tick_count,
        "all_k_high_risk_tick_count": all_k_tick_count,
    }


def _corridor_route_seed_ci(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    resamples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not rows or resamples <= 0:
        return None, None
    corridors = sorted({str(row["corridor_group_sha256"]) for row in rows})
    rng = np.random.default_rng(seed)
    means = np.empty(resamples, dtype=np.float64)
    by_corridor: dict[str, list[Mapping[str, Any]]] = {
        corridor: [row for row in rows if str(row["corridor_group_sha256"]) == corridor]
        for corridor in corridors
    }
    for sample_index in range(resamples):
        sampled: list[float] = []
        for corridor in rng.choice(corridors, size=len(corridors), replace=True):
            corridor_rows = by_corridor[str(corridor)]
            routes = sorted({str(row["route_identity_sha256"]) for row in corridor_rows})
            for route in rng.choice(routes, size=len(routes), replace=True):
                route_rows = [row for row in corridor_rows if str(row["route_identity_sha256"]) == str(route)]
                seeds = sorted({int(row["seed"]) for row in route_rows})
                for scenario_seed in rng.choice(seeds, size=len(seeds), replace=True):
                    matches = [row for row in route_rows if int(row["seed"]) == int(scenario_seed)]
                    if len(matches) != 1:
                        raise ValueError("bootstrap route/seed identity is not unique")
                    sampled.append(_finite(getter(matches[0]), "bootstrap value"))
        means[sample_index] = float(np.mean(sampled))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _paired_summary(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    resamples: int,
    seed: int,
    direction: str = "lower_is_better",
) -> dict[str, Any]:
    if direction not in {
        "lower_is_better",
        "higher_is_better",
        "descriptive_only",
    }:
        raise ValueError("paired-summary direction is invalid")
    values = np.asarray([_finite(getter(row), "paired value") for row in rows], dtype=np.float64)
    if values.size == 0:
        result = {
            "pair_count": 0,
            "mean": None,
            "median": None,
            "ci95_low": None,
            "ci95_high": None,
            "better_tie_worse": {"better": 0, "tie": 0, "worse": 0},
        }
        if direction != "lower_is_better":
            result["direction"] = direction
            result["descriptive_unclassified_count"] = 0
        return result
    if direction == "lower_is_better":
        labels = Counter(
            "better"
            if value < -TIE_TOLERANCE
            else "worse"
            if value > TIE_TOLERANCE
            else "tie"
            for value in values
        )
    elif direction == "higher_is_better":
        labels = Counter(
            "better"
            if value > TIE_TOLERANCE
            else "worse"
            if value < -TIE_TOLERANCE
            else "tie"
            for value in values
        )
    else:
        labels = Counter("tie" if abs(value) <= TIE_TOLERANCE else "unclassified" for value in values)
    low, high = _corridor_route_seed_ci(rows, getter, resamples=resamples, seed=seed)
    result = {
        "pair_count": int(values.size),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "ci95_low": low,
        "ci95_high": high,
        "better_tie_worse": {
            "better": labels["better"],
            "tie": labels["tie"],
            "worse": labels["worse"],
        },
    }
    if direction != "lower_is_better":
        result["direction"] = direction
        result["descriptive_unclassified_count"] = labels["unclassified"]
    return result


def _safety_delta(row: Mapping[str, Any]) -> float:
    return float(row["camp_safety"]["safety_cost"]) - float(row["dp_safety"]["safety_cost"])


def _component_delta(row: Mapping[str, Any], name: str) -> float:
    return float(row["camp_safety"]["components"][name]) - float(row["dp_safety"]["components"][name])


def _secondary_numeric_fields(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    common: set[str] | None = None
    for row in rows:
        dp = _mapping(row, "dp_secondary")
        camp = _mapping(row, "camp_secondary")
        numeric = {
            name
            for name in set(dp) & set(camp)
            if not isinstance(dp[name], bool)
            and not isinstance(camp[name], bool)
            and _is_finite_number(dp[name])
            and _is_finite_number(camp[name])
        }
        common = numeric if common is None else common & numeric
    return sorted(common or set())


def _is_finite_number(value: Any) -> bool:
    try:
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def aggregate_metrics(
    planned_pair_keys: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    *,
    evidence_guards: Mapping[str, bool],
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    planned = [str(value) for value in planned_pair_keys]
    observed = [str(row.get("pair_key")) for row in rows]
    if len(set(planned)) != len(planned) or len(set(observed)) != len(observed) or set(planned) != set(observed):
        raise ValueError("metric population differs from frozen denominator")
    if any(
        row.get("route_retained") is not True
        or row.get("included_in_denominator") is not True
        or row.get("replacement_used") is not False
        for row in rows
    ):
        raise ValueError("metric population violates retention/no-replacement")
    complete = [row for row in rows if row.get("paired_complete") is True]
    coverage = {
        "planned_pair_count": len(planned),
        "retained_pair_count": len(rows),
        "paired_complete_count": len(complete),
        "source_invalid_pair_count": sum(row.get("source_invalid") is True for row in rows),
        "execution_invalid_pair_count": sum(row.get("execution_failure") is True for row in rows),
        "retention_rate": len(rows) / (len(planned) or 1),
        "paired_complete_rate": len(complete) / (len(rows) or 1),
        "source_invalid_rate": sum(row.get("source_invalid") is True for row in rows) / (len(rows) or 1),
        "execution_invalid_rate": sum(row.get("execution_failure") is True for row in rows) / (len(rows) or 1),
    }
    overall = _paired_summary(
        complete, _safety_delta, resamples=bootstrap_resamples, seed=bootstrap_seed
    )
    all_high = [row for row in complete if row.get("all_k_high_risk") is True]
    components = {
        name: _paired_summary(
            complete,
            lambda row, component=name: _component_delta(row, component),
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
        )
        for name in SAFETY_WEIGHTS
    }
    speed: dict[str, Any] = {}
    for tolerance in SPEED_TOLERANCES:
        speed[tolerance] = _paired_summary(
            complete,
            lambda row, key=tolerance: float(row["camp_safety"]["speed_protocol"]["sensitivity"][key]["event_rate"])
            - float(row["dp_safety"]["speed_protocol"]["sensitivity"][key]["event_rate"]),
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
        )
    for field in (
        "maximum_excess_mps",
        "mean_excess_mps",
        "excess_duration_s",
        "magnitude_duration_m",
    ):
        speed[f"continuous_{field}_delta"] = _paired_summary(
            complete,
            lambda row, name=field: float(row["camp_safety"]["speed_protocol"]["continuous"][name])
            - float(row["dp_safety"]["speed_protocol"]["continuous"][name]),
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
        )
    secondary = {
        field: _paired_summary(
            complete,
            lambda row, name=field: float(row["camp_secondary"][name]) - float(row["dp_secondary"][name]),
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
            direction=SECONDARY_DIRECTIONS.get(field, "descriptive_only"),
        )
        for field in _secondary_numeric_fields(complete)
    }
    selected = [int(index) for row in complete for index in row.get("camp_selected_indices", [])]
    if any(index < 0 or index >= 8 for index in selected):
        raise ValueError("selected index outside fixed K=8")
    candidate_selection = {
        "camp_tick_count": len(selected),
        "camp_selected_index_histogram": {str(index): selected.count(index) for index in range(8)},
        "candidate0_selection_count": sum(index == 0 for index in selected),
        "non_candidate0_selection_count": sum(index != 0 for index in selected),
        "all_k_high_risk_pair_count": len(all_high),
        "all_k_high_risk_tick_count": sum(
            bool(tick.get("all_k_high_risk"))
            for row in complete
            for tick in row.get("camp_tick_receipts", [])
        ),
    }
    latency: dict[str, Any] = {}
    for arm, aliases in LATENCY_STAGES.items():
        tick_latencies = [tick for row in complete for tick in row.get(f"{arm}_tick_latency_ms", [])]
        latency[arm] = {}
        for public, source in aliases.items():
            if any(source not in tick for tick in tick_latencies):
                raise ValueError(f"missing {arm} latency stage: {source}")
            latency[arm][public] = _distribution([float(tick[source]) for tick in tick_latencies])

    regressions = {
        name: sum(_component_delta(row, name) > TIE_TOLERANCE for row in complete)
        for name in (
            "collision_any",
            "offroad_rate",
            "red_light_violation_any",
            "wrong_way_rate",
        )
    }
    guards = {name: bool(evidence_guards.get(name, False)) for name in EVIDENCE_GUARD_NAMES}
    btw = overall["better_tie_worse"]
    gates = {
        "retention_rate": coverage["retention_rate"] == 1.0,
        "paired_complete_rate": coverage["paired_complete_rate"] == 1.0,
        "source_invalid_rate": coverage["source_invalid_rate"] == 0.0,
        "execution_invalid_rate": coverage["execution_invalid_rate"] == 0.0,
        "safety_cost_mean_delta_below_zero": _strictly_negative(overall["mean"]),
        "clustered_ci95_upper_below_zero": _strictly_negative(overall["ci95_high"]),
        "better_exceeds_worse": btw["better"] > btw["worse"],
        "no_additional_collision_pairs": regressions["collision_any"] == 0,
        "no_additional_offroad_pairs": regressions["offroad_rate"] == 0,
        "no_additional_red_light_pairs": regressions["red_light_violation_any"] == 0,
        "no_additional_wrong_way_pairs": regressions["wrong_way_rate"] == 0,
        "evidence_guards": all(guards.values()),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "schema": "camp_dp_v24_holdout_main_independent_statistics_v1",
        "bootstrap_contract": {
            "primary_hierarchy": ["corridor_group_sha256", "route_identity_sha256", "seed"],
            "map_family_cluster_level_authorized": False,
            "resamples": bootstrap_resamples,
            "seed": bootstrap_seed,
        },
        "coverage": coverage,
        "failure_accounting": {
            "dp_status": dict(Counter(str(row.get("dp_status")) for row in rows)),
            "camp_status": dict(Counter(str(row.get("camp_status")) for row in rows)),
            "failure_class": dict(Counter(str(row.get("failure_class")) for row in rows)),
            "failed_pairs_dropped": False,
            "replacement_or_resampling_used": False,
        },
        "safety_cost_delta": overall,
        "strata": {
            "overall": overall,
            "all_k_high_risk": _paired_summary(
                all_high, _safety_delta, resamples=bootstrap_resamples, seed=bootstrap_seed
            ),
        },
        "components": components,
        "speed_sensitivity": speed,
        "secondary": secondary,
        "additional_event_pairs": regressions,
        "candidate_selection": candidate_selection,
        "latency": latency,
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
        "evidence_guards": guards,
        "claim_gate_result": {
            "decision": "limited_claim_gates_passed" if not failed else "honest_no_claim",
            "final_claim_authorized": False,
            "claim_scope": "frozen_held_out_map_family_and_three_corridor_groups_only",
            "map_family_level_ci": False,
            "unseen_map_generalization": False,
            "native_ranked_k8_superiority": False,
            "latency_comparative_conclusion": False,
            "gates": gates,
            "failed_gates": failed,
        },
    }


def _strictly_negative(value: Any) -> bool:
    return _is_finite_number(value) and float(value) < 0.0


def _compare_source_statistics(source: Mapping[str, Any], metrics: Mapping[str, Any]) -> None:
    expected = {
        "coverage": metrics["coverage"],
        "failure_accounting": metrics["failure_accounting"],
        "strata": metrics["strata"],
        "components": metrics["components"],
        "additional_event_pairs": metrics["additional_event_pairs"],
        "candidate_selection": {
            "tick_count": metrics["candidate_selection"]["camp_tick_count"],
            "candidate0_selection_count": metrics["candidate_selection"]["candidate0_selection_count"],
            "non_candidate0_selection_count": metrics["candidate_selection"]["non_candidate0_selection_count"],
            "all_k_high_risk_pair_count": metrics["candidate_selection"]["all_k_high_risk_pair_count"],
        },
        "latency": metrics["latency"],
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
    }
    speed_expected = {
        key: value
        for key, value in metrics["speed_sensitivity"].items()
        if key in SPEED_TOLERANCES or key in {
            "continuous_magnitude_duration_m_delta",
            "continuous_excess_duration_s_delta",
        }
    }
    expected["speed_sensitivity_event_rate_delta"] = speed_expected
    expected["secondary_mean_delta"] = {
        field: value["mean"] for field, value in metrics["secondary"].items()
    }
    for field, value in expected.items():
        _assert_json_close(source.get(field), value, f"producer_statistics.{field}")


def _build_route_source_bindings(
    census: Mapping[str, Any], split_manifest: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    if (
        census.get("schema")
        != "diffusion_planner_v24_outcome_blind_route_census_v1"
        or census.get("route_census_completed") is not True
        or census.get("outcome_accessed") is not False
        or census.get("holdout_opened") is not False
    ):
        raise ValueError("route-census source boundary mismatch")
    retained = census.get("retained_routes")
    if not isinstance(retained, list) or len(retained) != 401:
        raise ValueError("route-census retained population mismatch")
    by_identity: dict[str, dict[str, Any]] = {}
    by_record: dict[str, dict[str, Any]] = {}
    for raw in retained:
        route = _mapping({"route": raw}, "route")
        identity = _require_sha256(route.get("identity_sha256"), "route identity")
        record_key = route.get("record_key")
        if not isinstance(record_key, str) or not record_key:
            raise ValueError("route-census record key is missing")
        logical_map = _require_sha256(
            route.get("logical_map_sha256"), "route logical map"
        )
        source_geometry = _require_sha256(
            route.get("source_geometry_sha256"), "route source geometry"
        )
        if identity != _canonical_sha256(
            {
                "logical_map_sha256": logical_map,
                "source_geometry_sha256": source_geometry,
            }
        ):
            raise ValueError("route identity is not bound to source geometry")
        source_map_sha256 = _require_sha256(
            route.get("source_map_sha256"), "route source map"
        )
        source_map_path = route.get("source_map_path")
        family = route.get("map_family_id")
        if not isinstance(source_map_path, str) or not source_map_path:
            raise ValueError("route source-map path is missing")
        if not isinstance(family, str) or not family:
            raise ValueError("route map-family id is missing")
        route_spec = _mapping(route, "route_spec")
        lanelet_ids = route.get("lanelet_ids")
        if (
            route_spec.get("map_path") != source_map_path
            or route_spec.get("lanelet_ids") != lanelet_ids
            or not isinstance(lanelet_ids, list)
            or not lanelet_ids
            or any(isinstance(value, bool) or not isinstance(value, int) for value in lanelet_ids)
        ):
            raise ValueError("route spec differs from source route fields")
        route_spec_length = _finite(
            route_spec.get("route_length_m"), "route-spec geometry length", nonnegative=True
        )
        source_route_length = _finite(
            route.get("source_route_length_m"),
            "source geometry route length",
            nonnegative=True,
        )
        source_arc_length = _finite(
            route.get("source_arc_length_m"),
            "source builder-cache arc length",
            nonnegative=True,
        )
        if (
            route_spec_length <= 0.0
            or source_route_length <= 0.0
            or source_arc_length <= 0.0
            or not math.isclose(
                route_spec_length,
                source_route_length,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            or route.get("route_serialization_sha256")
            != _canonical_sha256(route_spec)
        ):
            raise ValueError("route-census source length/spec digest mismatch")
        binding = {
            "record_key": record_key,
            "identity_sha256": identity,
            "logical_map_sha256": logical_map,
            "map_family_id": family,
            "source_map_path": source_map_path,
            "source_map_sha256": source_map_sha256,
            "source_geometry_sha256": source_geometry,
            "route_serialization_sha256": str(route["route_serialization_sha256"]),
            "source_arc_length_m": source_arc_length,
            "source_route_length_m": source_route_length,
        }
        if identity in by_identity or record_key in by_record:
            raise ValueError("route-census identity/record key is not unique")
        by_identity[identity] = binding
        by_record[record_key] = binding

    records = split_manifest.get("records")
    if not isinstance(records, list) or len(records) != 401:
        raise ValueError("split manifest record population mismatch")
    holdout: dict[str, dict[str, Any]] = {}
    for raw in records:
        if raw.get("split") != "holdout":
            continue
        identity = _require_sha256(raw.get("identity_sha256"), "holdout identity")
        record_key = raw.get("record_key")
        corridor = _require_sha256(
            raw.get("corridor_group_sha256"), "holdout corridor"
        )
        if record_key not in by_record or identity not in by_identity:
            raise ValueError("holdout split route is absent from sealed route census")
        binding = by_identity[identity]
        if (
            binding is not by_record[record_key]
            or raw.get("map_family_id") != binding["map_family_id"]
            or raw.get("seeds") != list(HOLDOUT_SEEDS)
        ):
            raise ValueError("holdout split/census route binding mismatch")
        if identity in holdout:
            raise ValueError("holdout route identity is duplicated")
        holdout[identity] = {
            **binding,
            "corridor_group_sha256": corridor,
            "seeds": list(HOLDOUT_SEEDS),
        }
    if len(holdout) != 24:
        raise ValueError("holdout split/census route count mismatch")
    return holdout


def _verify_schedule_route_source_bindings(
    schedule: Mapping[str, Any], route_sources: Mapping[str, Mapping[str, Any]]
) -> None:
    metadata = schedule.get("route_metadata")
    if not isinstance(metadata, Mapping) or set(metadata) != set(route_sources):
        raise ValueError("main schedule differs from sealed holdout route identities")
    public_records: dict[str, str] = {}
    for row in _mapping(schedule["plan"], "schedules").get("main", []):
        identity = str(row.get("route_identity_sha256"))
        record_key = row.get("record_key")
        if not isinstance(record_key, str) or not record_key:
            raise ValueError("public main schedule record key is missing")
        prior = public_records.setdefault(identity, record_key)
        if prior != record_key:
            raise ValueError("one route changes public record key across seeds")
    if set(public_records) != set(route_sources):
        raise ValueError("public main schedule differs from sealed holdout routes")
    for identity, source in route_sources.items():
        item = metadata[identity]
        expected = {
            "map_family_id": source["map_family_id"],
            "logical_map_sha256": source["logical_map_sha256"],
            "corridor_group_sha256": source["corridor_group_sha256"],
            "source_map_path": source["source_map_path"],
            "source_map_sha256": source["source_map_sha256"],
        }
        for field, value in expected.items():
            _assert_json_close(item.get(field), value, f"schedule source route {field}")
        if public_records[identity] != source["record_key"]:
            raise ValueError("public schedule record key differs from split/census")


def _verify_frozen_metric_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    scalar_contract = {
        "candidate_k": 8,
        "selection_policy": "v22_source_valid",
        "score_contract": "score_k(w)=a_k^T w",
        "nonnegative_simplex": True,
        "safety_schema": "safety_cost_native_v22",
        "safety_component_weights": SAFETY_WEIGHTS,
        "primary_speed_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "route_retention": "all_preregistered_routes_and_failures_no_replacement",
    }
    for field, expected in scalar_contract.items():
        _assert_json_close(config.get(field), expected, f"frozen metric contract {field}")
    coverage = {
        "planned_pair_retention_rate_min": 1.0,
        "paired_complete_rate_min_for_claim": 1.0,
        "source_invalid_pair_rate_max_for_claim": 0.0,
        "execution_invalid_pair_rate_max_for_claim": 0.0,
        "failed_arm_receipts_retained": True,
        "failed_pairs_dropped": False,
        "replacement_or_resampling_authorized": False,
        "train_route_seed_source_coverage_disclosure": TRAIN_SOURCE_COVERAGE_DISCLOSURE,
    }
    _assert_json_close(
        config.get("coverage_execution_contract"), coverage, "coverage execution contract"
    )
    if (
        TRAIN_SOURCE_COVERAGE_DISCLOSURE["complete"]
        + TRAIN_SOURCE_COVERAGE_DISCLOSURE["failed"]
        != TRAIN_SOURCE_COVERAGE_DISCLOSURE["retained"]
    ):
        raise AssertionError("frozen train source disclosure is internally inconsistent")
    candidate = {
        "per_arm_candidate_tensor_immutability_required_every_tick": True,
        "per_arm_candidate0_default_byte_identity_required_every_tick": True,
        "selected_trajectory_must_be_exact_indexed_candidate": True,
        "dp_policy": "candidate0_operational_default_not_native_ranked_top1",
        "camp_policy": "frozen_14d_affine_simplex_rerank_over_own_state_fixed_dp_k8",
        "t0_cross_arm_input_and_candidate_hash_identity_required": True,
        "post_divergence_cross_arm_tensor_comparison": "expected_noncomparable_state_conditioned_fixed_dp_outputs",
        "post_divergence_cross_arm_tensor_identity_required": False,
        "policy_level_closed_loop_claim_preclosed": False,
        "native_ranked_k8_provenance_claim_authorized": False,
    }
    _assert_json_close(config.get("candidate_contract"), candidate, "candidate contract")
    claim = {
        "paired_retention_rate_required": 1.0,
        "paired_complete_rate_required": 1.0,
        "overall_mean_delta_strictly_below_zero": True,
        "cluster_ci95_upper_strictly_below_zero": True,
        "better_pairs_must_exceed_worse_pairs": True,
        "additional_collision_pairs_max": 0,
        "additional_offroad_pairs_max": 0,
        "additional_red_light_pairs_max": 0,
        "additional_wrong_way_pairs_max": 0,
        "per_arm_candidate_immutability_required": True,
        "per_arm_candidate0_default_identity_required": True,
        "t0_cross_arm_identity_required": True,
        "zero_overlap_required": True,
        "holdout_once_required": True,
    }
    _assert_json_close(config.get("claim_contract"), claim, "claim contract")
    statistics = {
        "primary_bootstrap_hierarchy": [
            "corridor_group_sha256",
            "route_identity_sha256",
            "seed",
        ],
        "map_family_cluster_level_authorized": False,
        "holdout_map_family_count": 1,
        "holdout_corridor_group_count": 3,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "tie_tolerance": TIE_TOLERANCE,
        "latency_quantiles": [0.5, 0.95, 0.99],
        "latency_stages": LATENCY_STAGES,
    }
    _assert_json_close(config.get("statistics"), statistics, "statistics contract")
    _assert_json_close(
        config.get("learning_curve_stability"),
        LEARNING_CURVE_STABILITY,
        "learning-curve stability disclosure",
    )
    return {
        "train_route_seed_source_coverage_disclosure": dict(
            TRAIN_SOURCE_COVERAGE_DISCLOSURE
        ),
        "learning_curve_stability": dict(LEARNING_CURVE_STABILITY),
        "distribution_concentration_risk_disclosed": True,
        "calibration_or_holdout_repair_authorized": False,
    }


def _verify_split_and_training(config: Mapping[str, Any]) -> dict[str, Any]:
    split = _mapping(config, "source_split")
    route = _mapping(config, "source_route_census")
    training = _mapping(config, "frozen_selector")
    roots = {
        "split": verify_complete_seal(Path(str(split["artifact"])), str(split["artifact_root_sha256"]), "split"),
        "split_review": verify_complete_seal(Path(str(split["independent_review_artifact"])), str(split["independent_review_root_sha256"]), "split_review"),
        "route_census": verify_complete_seal(Path(str(route["artifact"])), str(route["artifact_root_sha256"]), "route_census"),
        "route_census_review": verify_complete_seal(Path(str(route["independent_review_artifact"])), str(route["independent_review_root_sha256"]), "route_census_review"),
        "training": verify_complete_seal(Path(str(training["training_artifact"])), str(training["training_artifact_root_sha256"]), "training"),
        "training_review": verify_complete_seal(Path(str(training["independent_review_artifact"])), str(training["independent_review_root_sha256"]), "training_review"),
    }
    for name, receipt in roots.items():
        _require_clean_completion(Path(receipt["root"]), name)
    review_bindings = {
        "split_review": roots["split"]["root_sha256"],
        "route_census_review": roots["route_census"]["root_sha256"],
        "training_review": roots["training"]["root_sha256"],
    }
    for name, expected_source_root in review_bindings.items():
        review = _load_review_receipt(Path(roots[name]["root"]))
        if review.get("status") != "passed" or review.get("failed_count") != 0:
            raise ValueError(f"{name} did not pass")
        if expected_source_root not in _declared_root_sha256_values(review):
            raise ValueError(f"{name} is not bound to its config-pinned source root")

    split_path = _artifact_declared_path(Path(roots["split"]["root"]), split["manifest_path"], "split manifest")
    if _sha256_file(split_path) != split.get("file_sha256"):
        raise ValueError("split manifest file SHA mismatch")
    manifest = _load_json(split_path)
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != 401:
        raise ValueError("split manifest record population mismatch")
    expected_counts = {"train": 375, "calibration": 2, "holdout": 24}
    if dict(Counter(str(item.get("split")) for item in records)) != expected_counts:
        raise ValueError("split manifest counts mismatch")
    for field in (
        "record_key",
        "identity_sha256",
        "corridor_group_sha256",
        "map_family_id",
    ):
        sets = {
            split_name: {str(item[field]) for item in records if item.get("split") == split_name}
            for split_name in expected_counts
        }
        if sets["train"] & sets["calibration"] or sets["train"] & sets["holdout"] or sets["calibration"] & sets["holdout"]:
            raise ValueError(f"split zero-overlap failed for {field}")

    census_path = _artifact_declared_path(
        Path(roots["route_census"]["root"]), route["census_path"], "route census"
    )
    if _sha256_file(census_path) != route.get("file_sha256"):
        raise ValueError("route census file SHA mismatch")
    route_sources = _build_route_source_bindings(_load_json(census_path), manifest)

    training_root = Path(roots["training"]["root"])
    model_path = _artifact_declared_path(training_root, training["model_path"], "training model")
    weights_path = _artifact_declared_path(training_root, training["weights_f64le_path"], "training weights")
    if _sha256_file(model_path) != training.get("model_sha256") or _sha256_file(weights_path) != training.get("weights_f64le_sha256"):
        raise ValueError("training model/weights file SHA mismatch")
    model = _load_json(model_path)
    weights = np.fromfile(weights_path, dtype="<f8")
    stored = np.asarray(model.get("weights"), dtype=np.float64)
    if (
        model.get("atom_schema_version") != "dp_camp_v10_14d"
        or tuple(model.get("atom_names", ())) != EXPECTED_ATOM_NAMES
        or model.get("active_atom_mask") != [True] * 14
        or weights.shape != (14,)
        or stored.shape != (14,)
        or not np.array_equal(weights, stored)
        or not np.isfinite(weights).all()
        or np.any(weights < 0.0)
        or not math.isclose(float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12)
    ):
        raise ValueError("training frozen 14D simplex model mismatch")
    forbidden = ("map", "route", "split", "seed", "holdout", "outcome", "label", "_id", "id_")
    if any(any(token in name.lower() for token in forbidden) for name in EXPECTED_ATOM_NAMES):
        raise ValueError("feature identity denylist violation")
    return {
        "roots": roots,
        "split_zero_overlap_verified": True,
        "feature_identity_denylist_verified": True,
        "training_model_sha256": _sha256_file(model_path),
        "training_weights_sha256": _sha256_file(weights_path),
        "training_weights": weights.tolist(),
        "atom_names": list(EXPECTED_ATOM_NAMES),
        "holdout_route_sources": route_sources,
        "route_census_file_sha256": _sha256_file(census_path),
    }


def _load_review_receipt(root: Path) -> Mapping[str, Any]:
    candidates = [
        root / name for name in ("review_result.json", "review.json", "result.json")
        if (root / name).is_file()
    ]
    if len(candidates) != 1:
        raise ValueError("independent-review artifact has no unique review receipt")
    value = _load_json(candidates[0])
    if not isinstance(value, Mapping):
        raise ValueError("independent-review receipt must be a mapping")
    return value


def _declared_root_sha256_values(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if "root_sha256" in str(key) and _is_sha256(item):
                result.add(str(item))
            result.update(_declared_root_sha256_values(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_declared_root_sha256_values(item))
    return result


def _verify_runtime_selector(preflight_root: Path, schedule: Mapping[str, Any], training: Mapping[str, Any]) -> dict[str, Any]:
    first = schedule["configs"][0]["selector"]
    runtime_root = Path(str(first["root"])).resolve()
    preflight_root = Path(preflight_root).resolve()
    if runtime_root != preflight_root and preflight_root not in runtime_root.parents:
        raise ValueError("runtime selector escapes sealed preflight")
    receipt = verify_complete_seal(runtime_root, str(first["root_sha256"]), "runtime_selector")
    weights_path = _artifact_declared_path(runtime_root, first["weights"]["path"], "runtime weights")
    scales_path = _artifact_declared_path(runtime_root, first["atom_scales"]["path"], "runtime atom scales")
    if _sha256_file(weights_path) != first["weights"]["sha256"] or _sha256_file(scales_path) != first["atom_scales"]["sha256"]:
        raise ValueError("runtime selector asset SHA mismatch")
    weights = np.load(weights_path, allow_pickle=False)
    scales_payload = _load_json(scales_path)
    scales = np.asarray(scales_payload.get("scales"), dtype=np.float64)
    if (
        weights.shape != (14,)
        or not np.array_equal(weights, np.asarray(training["training_weights"], dtype=np.float64))
        or tuple(scales_payload.get("atom_names", ())) != EXPECTED_ATOM_NAMES
        or scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
    ):
        raise ValueError("runtime selector differs from frozen training assets")
    if any(item["selector"] != first for item in schedule["configs"]):
        raise ValueError("selector request differs across main schedule")
    return {
        "root": receipt,
        "weights_sha256": _sha256_file(weights_path),
        "atom_scales_sha256": _sha256_file(scales_path),
        "weights": weights.tolist(),
        "atom_scales": scales.tolist(),
    }


def _verify_request_assets(
    schedule: Mapping[str, Any], preflight_root: Path
) -> dict[str, Any]:
    configs = schedule["configs"]
    fixed_dp = configs[0]["fixed_dp"]
    if any(item["fixed_dp"] != fixed_dp for item in configs):
        raise ValueError("fixed DP request differs across main schedule")
    assets: dict[str, str] = {}
    for name in ("checkpoint", "args_json"):
        spec = _mapping(fixed_dp, name)
        path = Path(str(spec["path"]))
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"fixed DP {name} asset is missing or symlinked")
        actual = _sha256_file(path)
        if actual != spec.get("sha256"):
            raise ValueError(f"fixed DP {name} asset SHA mismatch")
        assets[f"fixed_dp_{name}"] = actual
    dp_repo = Path(str(fixed_dp["repo"])).resolve()
    native_sources = _mapping(fixed_dp, "native_source_sha256")
    for relative, expected in native_sources.items():
        pure = PurePosixPath(str(relative))
        if pure.is_absolute() or ".." in pure.parts or "\\" in str(relative):
            raise ValueError("fixed DP native source path is unsafe")
        path = dp_repo.joinpath(*pure.parts)
        if path.is_symlink() or not path.is_file() or _sha256_file(path) != expected:
            raise ValueError(f"fixed DP native source SHA mismatch: {relative}")
        assets[f"fixed_dp_source:{relative}"] = str(expected)

    preflight_root = Path(preflight_root).resolve()
    route_hashes: dict[str, str] = {}
    map_hashes: dict[str, str] = {}
    for item in configs:
        route = item["routes"][0]
        raw_route_path = Path(str(route["path"]))
        route_path = raw_route_path.resolve()
        if (
            raw_route_path.is_symlink()
            or not route_path.is_file()
            or preflight_root not in route_path.parents
            or _sha256_file(route_path) != route["sha256"]
        ):
            raise ValueError("route asset is not hash-bound inside sealed preflight")
        route_identity = str(route["name"])
        route_digest = str(route["sha256"])
        if route_identity in route_hashes and route_hashes[route_identity] != route_digest:
            raise ValueError("one route identity changes route-asset SHA across seeds")
        route_hashes[route_identity] = route_digest
        map_spec = item["map"]
        raw_map_path = Path(str(map_spec["path"]))
        map_path = raw_map_path.resolve()
        if raw_map_path.is_symlink() or not map_path.is_file() or _sha256_file(map_path) != map_spec["sha256"]:
            raise ValueError("source map asset SHA mismatch")
        map_hashes[str(map_path.resolve())] = str(map_spec["sha256"])
    if len(route_hashes) != 24:
        raise ValueError("request asset route population mismatch")
    return {
        "fixed_dp_assets": assets,
        "route_asset_count": len(route_hashes),
        "route_asset_sha256": route_hashes,
        "map_asset_count": len(map_hashes),
        "map_asset_sha256": map_hashes,
        "same_fixed_dp_request_all_pairs": True,
    }


def _verify_chain_receipts(
    *,
    preflight_root: Path,
    preflight_review_root: Path,
    pilot_review_root: Path,
    authorization_root: Path,
    authorization_review_root: Path,
    expected_preflight_root_sha256: str,
    expected_pilot_review_root_sha256: str,
    expected_authorization_root_sha256: str,
    expected_preflight_config_sha256: str,
    expected_preflight_camp_head: str,
    expected_pilot_review_camp_head: str,
    expected_pilot_execution_source_head: str,
) -> None:
    preflight = _load_json(preflight_root / "preflight_result.json")
    preflight_review = _load_json(preflight_review_root / "review_result.json")
    pilot_review = _load_json(pilot_review_root / "review_result.json")
    authorization = _load_json(authorization_root / "authorization_result.json")
    authorization_review = _load_json(authorization_review_root / "review_result.json")
    def require_all_checks(payload: Mapping[str, Any], label: str) -> None:
        checks = payload.get("checks")
        if (
            not isinstance(checks, Mapping)
            or not checks
            or any(value is not True for value in checks.values())
            or payload.get("check_count") != len(checks)
            or payload.get("failed_count") != 0
            or payload.get("failed_checks") != []
        ):
            raise ValueError(f"{label} checks are not complete and all true")

    require_all_checks(preflight, "preflight")
    require_all_checks(pilot_review, "calibration pilot-review")
    if (
        preflight.get("schema")
        != "camp_dp_v24_native_paired_evaluation_static_preflight_v1"
        or preflight.get("status") != "passed"
        or preflight.get("config_sha256") != expected_preflight_config_sha256
        or preflight.get("camp_head") != expected_preflight_camp_head
        or preflight.get("fixed_dp_head") != FIXED_DP_HEAD
        or preflight.get("planned_pair_counts", {}).get("main") != 120
        or preflight.get("holdout_opened") is not False
        or preflight.get("holdout_open_count") != 0
        or preflight.get("outcome_fields_consumed") != []
    ):
        raise ValueError("preflight receipt mismatch")
    if (
        preflight_review.get("status") != "passed"
        or preflight_review.get("failed_count") != 0
        or preflight_review.get("source_preflight_root_sha256") != expected_preflight_root_sha256
    ):
        raise ValueError("preflight-review receipt mismatch")
    if (
        pilot_review.get("schema")
        != "camp_dp_v24_paired_calibration_pilot_independent_review_v1"
        or pilot_review.get("status") != "passed"
        or pilot_review.get("failed_count") != 0
        or pilot_review.get("source_roots", {}).get("preflight", {}).get("root_sha256")
        != expected_preflight_root_sha256
        or pilot_review.get("execution_source_head")
        != expected_pilot_execution_source_head
        or pilot_review.get("camp_head") != expected_pilot_review_camp_head
        or pilot_review.get("fixed_dp_head") != FIXED_DP_HEAD
        or pilot_review.get("source_execution_reexecuted") is not False
        or pilot_review.get("holdout_opened") is not False
        or pilot_review.get("holdout_open_count") != 0
        or pilot_review.get("latency_comparison_authorized") is not False
        or pilot_review.get("main_execution_authorized") is not False
    ):
        raise ValueError("calibration pilot-review receipt mismatch")
    if (
        authorization.get("status") != "passed"
        or authorization.get("failed_count") != 0
        or authorization.get("main_pair_count") != 120
        or authorization.get("holdout_opened") is not False
        or authorization.get("holdout_open_count") != 0
        or authorization.get("main_execution_authorized") is not False
        or authorization.get("source_roots", {}).get("preflight", {}).get("root_sha256") != expected_preflight_root_sha256
        or authorization.get("source_roots", {}).get("pilot_review", {}).get("root_sha256") != expected_pilot_review_root_sha256
    ):
        raise ValueError("holdout authorization receipt mismatch")
    roots = authorization_review.get("source_roots", {})
    if (
        authorization_review.get("status") != "passed"
        or authorization_review.get("failed_count") != 0
        or roots.get("authorization", {}).get("root_sha256") != expected_authorization_root_sha256
        or roots.get("preflight", {}).get("root_sha256") != expected_preflight_root_sha256
        or roots.get("pilot_review", {}).get("root_sha256") != expected_pilot_review_root_sha256
        or authorization_review.get("holdout_opened") is not False
        or authorization_review.get("holdout_open_count") != 0
    ):
        raise ValueError("authorization-review receipt mismatch")


def _read_optional_named(root: Path, names: Sequence[str]) -> tuple[str, str] | None:
    for name in names:
        path = root / name
        if path.is_file():
            return name, path.read_text(encoding="utf-8").strip()
    return None


def _verify_launch(
    launch_root: Path,
    execution_root: Path,
    state_path: Path,
    *,
    execution_source_head: str,
    preflight_root: Path,
    preflight_sha: str,
    authorization_root: Path,
    authorization_sha: str,
) -> dict[str, Any]:
    _require_clean_completion(launch_root, "launch")
    output = _read_optional_named(launch_root, ("OUTPUT_PATH", "OUTPUT_PATH.txt"))
    state = _read_optional_named(launch_root, ("STATE_PATH", "STATE_PATH.txt"))
    if output is None or Path(output[1]).resolve() != Path(execution_root).resolve():
        raise ValueError("launch output-path binding mismatch")
    if state is None or Path(state[1]).resolve() != Path(state_path).resolve():
        raise ValueError("launch state-path binding mismatch")
    heads = _read_optional_named(launch_root, ("HEADS", "HEADS.txt"))
    command = _read_optional_named(launch_root, ("COMMAND", "COMMAND.txt"))
    if heads is None or execution_source_head not in heads[1] or FIXED_DP_HEAD not in heads[1]:
        raise ValueError("launch HEADS binding mismatch")
    if command is None:
        raise ValueError("launch COMMAND is missing")
    required_tokens = (
        "--mode main",
        "--execute-authorized",
        "--holdout-once-authorized",
        str(Path(preflight_root)),
        preflight_sha,
        str(Path(authorization_root)),
        authorization_sha,
        str(Path(execution_root)),
    )
    if any(token not in command[1] for token in required_tokens):
        raise ValueError("launch COMMAND binding mismatch")
    stderr = (launch_root / "stderr.txt").read_text(encoding="utf-8") if (launch_root / "stderr.txt").is_file() else ""
    if "Traceback (most recent call last)" in stderr:
        raise ValueError("launch stderr contains a traceback")
    return {
        "output_path_file": output[0],
        "state_path_file": state[0],
        "heads_file": heads[0],
        "command_file": command[0],
        "stderr_bytes": len(stderr.encode("utf-8")),
    }


def _verify_holdout_state(
    state_path: Path,
    *,
    execution_source_head: str,
    authorization_sha: str,
    preflight_sha: str,
    execution_root: Path,
) -> dict[str, Any]:
    state = _load_json(state_path)
    expected = {
        "schema": HOLDOUT_STATE_SCHEMA,
        "holdout_opened": True,
        "holdout_open_count": 1,
        "rerun_authorized": False,
        "camp_head": execution_source_head,
        "authorization_root_sha256": authorization_sha,
        "preflight_root_sha256": preflight_sha,
        "output_dir": str(Path(execution_root).resolve()),
    }
    _assert_json_close(state, expected, "holdout-once state")
    return state


def _verify_pinned_source_blobs(
    *,
    config_blob: bytes,
    live_config_blob: bytes,
    expected_config_sha256: str,
    evaluator_blob: bytes,
    expected_evaluator_sha256: str,
) -> dict[str, str]:
    if (
        config_blob != live_config_blob
        or _sha256_bytes(config_blob) != expected_config_sha256
    ):
        raise ValueError("live paired config differs from execution-source blob")
    if _sha256_bytes(evaluator_blob) != expected_evaluator_sha256:
        raise ValueError("execution-source evaluator SHA256 mismatch")
    return {
        "config_blob_sha256": _sha256_bytes(config_blob),
        "evaluator_blob_sha256": _sha256_bytes(evaluator_blob),
    }


def _verify_provenance(
    camp_repo: Path,
    schedule: Mapping[str, Any],
    *,
    execution_source_head: str,
    camp_head: str,
    config_path: Path,
    expected_config_sha256: str,
    expected_evaluator_sha256: str,
    prior_camp_heads: Mapping[str, str],
) -> dict[str, Any]:
    live_head = _git_text(camp_repo, "rev-parse", "HEAD")
    live_status = _git_text(camp_repo, "status", "--porcelain", "--untracked-files=no")
    if live_head != camp_head or live_status:
        raise ValueError("live CAMP HEAD or tracked state mismatch")
    if _git_text(camp_repo, "cat-file", "-t", execution_source_head) != "commit":
        raise ValueError("execution source head is not a commit")
    ancestor = subprocess.run(
        ["git", "-C", str(camp_repo), "merge-base", "--is-ancestor", execution_source_head, camp_head],
        check=False,
    ).returncode == 0
    if not ancestor:
        raise ValueError("execution source head is not an ancestor of live CAMP")
    prior_ancestry: dict[str, bool] = {}
    for label, head in prior_camp_heads.items():
        if _git_text(camp_repo, "cat-file", "-t", head) != "commit":
            raise ValueError(f"{label} is not a CAMP commit")
        is_ancestor = subprocess.run(
            ["git", "-C", str(camp_repo), "merge-base", "--is-ancestor", head, execution_source_head],
            check=False,
        ).returncode == 0
        if not is_ancestor:
            raise ValueError(f"{label} is not an ancestor of holdout execution source")
        prior_ancestry[label] = True
    blobs: dict[str, dict[str, str]] = {}
    for relative in PRODUCER_PROVENANCE_FILES:
        source = _git_bytes(camp_repo, f"{execution_source_head}:{relative}")
        live = _git_bytes(camp_repo, f"{camp_head}:{relative}")
        if source != live:
            raise ValueError(f"producer code drift after execution: {relative}")
        blobs[relative] = {
            "execution_source_sha256": _sha256_bytes(source),
            "live_sha256": _sha256_bytes(live),
        }
    relative_config = Path(config_path).resolve().relative_to(Path(camp_repo).resolve()).as_posix()
    config_blob = _git_bytes(camp_repo, f"{execution_source_head}:{relative_config}")
    evaluator_blob = _git_bytes(
        camp_repo,
        f"{execution_source_head}:scripts/integrations/evaluate_diffusion_planner_v24_pairs.py",
    )
    pinned_blobs = _verify_pinned_source_blobs(
        config_blob=config_blob,
        live_config_blob=Path(config_path).read_bytes(),
        expected_config_sha256=expected_config_sha256,
        evaluator_blob=evaluator_blob,
        expected_evaluator_sha256=expected_evaluator_sha256,
    )

    dp_repo = Path(str(schedule["configs"][0]["fixed_dp"]["repo"]))
    dp_head = _git_text(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_text(dp_repo, "status", "--porcelain", "--untracked-files=no")
    if dp_head != FIXED_DP_HEAD or dp_status:
        raise ValueError("fixed DP HEAD or tracked state drift")
    if any(item["fixed_dp"] != schedule["configs"][0]["fixed_dp"] for item in schedule["configs"]):
        raise ValueError("fixed DP request differs across main schedule")
    return {
        "live_camp_head": live_head,
        "execution_source_head": execution_source_head,
        "execution_source_is_ancestor": True,
        "prior_gate_heads_are_execution_source_ancestors": prior_ancestry,
        "live_camp_tracked_clean": True,
        "fixed_dp_head": dp_head,
        "fixed_dp_tracked_clean": True,
        "producer_blob_sha256": blobs,
        "config_blob_sha256": pinned_blobs["config_blob_sha256"],
        "expected_config_sha256": expected_config_sha256,
        "evaluator_blob_sha256": pinned_blobs["evaluator_blob_sha256"],
        "expected_evaluator_sha256": expected_evaluator_sha256,
    }


def review_holdout_main_result(
    *,
    config_path: Path,
    expected_config_sha256: str,
    expected_preflight_config_sha256: str,
    expected_evaluator_sha256: str,
    execution_root: Path,
    expected_execution_root_sha256: str,
    launch_root: Path,
    expected_launch_root_sha256: str,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    preflight_review_root: Path,
    expected_preflight_review_root_sha256: str,
    pilot_review_root: Path,
    expected_pilot_review_root_sha256: str,
    authorization_root: Path,
    expected_authorization_root_sha256: str,
    authorization_review_root: Path,
    expected_authorization_review_root_sha256: str,
    expected_preflight_camp_head: str,
    expected_pilot_review_camp_head: str,
    expected_pilot_execution_source_head: str,
    expected_execution_source_head: str,
    camp_head: str,
    output_dir: Path,
    enable_independent_review: bool,
    camp_repo: Path = ROOT,
) -> dict[str, Any]:
    if enable_independent_review is not True:
        raise ValueError("explicit --enable-independent-review is required")
    if Path(output_dir).exists():
        raise FileExistsError(output_dir)
    for name, value in (
        ("preflight CAMP head", expected_preflight_camp_head),
        ("pilot-review CAMP head", expected_pilot_review_camp_head),
        ("pilot execution source head", expected_pilot_execution_source_head),
        ("execution source head", expected_execution_source_head),
        ("CAMP head", camp_head),
    ):
        _require_sha256(value, name)
    expected_config_sha256 = _require_sha256(
        expected_config_sha256, "expected config SHA256"
    )
    expected_preflight_config_sha256 = _require_sha256(
        expected_preflight_config_sha256, "expected preflight config SHA256"
    )
    expected_evaluator_sha256 = _require_sha256(
        expected_evaluator_sha256, "expected evaluator SHA256"
    )
    if _sha256_file(Path(config_path)) != expected_config_sha256:
        raise ValueError("frozen paired config SHA256 mismatch")

    roots = {
        "execution": verify_complete_seal(execution_root, expected_execution_root_sha256, "execution"),
        "launch": verify_complete_seal(launch_root, expected_launch_root_sha256, "launch"),
        "preflight": verify_complete_seal(
            preflight_root,
            expected_preflight_root_sha256,
            "preflight",
            allowed_nested_seal_roots=("runtime_selector",),
        ),
        "preflight_review": verify_complete_seal(preflight_review_root, expected_preflight_review_root_sha256, "preflight_review"),
        "pilot_review": verify_complete_seal(pilot_review_root, expected_pilot_review_root_sha256, "pilot_review"),
        "authorization": verify_complete_seal(authorization_root, expected_authorization_root_sha256, "authorization"),
        "authorization_review": verify_complete_seal(authorization_review_root, expected_authorization_review_root_sha256, "authorization_review"),
    }
    for name in roots:
        _require_clean_completion(Path(roots[name]["root"]), name)
    _verify_chain_receipts(
        preflight_root=Path(preflight_root),
        preflight_review_root=Path(preflight_review_root),
        pilot_review_root=Path(pilot_review_root),
        authorization_root=Path(authorization_root),
        authorization_review_root=Path(authorization_review_root),
        expected_preflight_root_sha256=expected_preflight_root_sha256,
        expected_pilot_review_root_sha256=expected_pilot_review_root_sha256,
        expected_authorization_root_sha256=expected_authorization_root_sha256,
        expected_preflight_config_sha256=expected_preflight_config_sha256,
        expected_preflight_camp_head=expected_preflight_camp_head,
        expected_pilot_review_camp_head=expected_pilot_review_camp_head,
        expected_pilot_execution_source_head=expected_pilot_execution_source_head,
    )
    config = _load_json(config_path)
    if config.get("schema_version") != "camp_dp_v24_native_paired_evaluation_v1":
        raise ValueError("paired config schema mismatch")
    frozen_metric_contract = _verify_frozen_metric_contract(config)
    schedule = reconstruct_main_schedule(Path(preflight_root))
    upstream = _verify_split_and_training(config)
    _verify_schedule_route_source_bindings(
        schedule, upstream["holdout_route_sources"]
    )
    runtime_selector = _verify_runtime_selector(Path(preflight_root), schedule, upstream)
    request_assets = _verify_request_assets(schedule, Path(preflight_root))
    state_path = Path(str(_mapping(config, "holdout_once_contract")["state_path"]))
    state = _verify_holdout_state(
        state_path,
        execution_source_head=expected_execution_source_head,
        authorization_sha=expected_authorization_root_sha256,
        preflight_sha=expected_preflight_root_sha256,
        execution_root=Path(execution_root),
    )
    launch = _verify_launch(
        Path(launch_root),
        Path(execution_root),
        state_path,
        execution_source_head=expected_execution_source_head,
        preflight_root=Path(preflight_root),
        preflight_sha=expected_preflight_root_sha256,
        authorization_root=Path(authorization_root),
        authorization_sha=expected_authorization_root_sha256,
    )
    provenance = _verify_provenance(
        Path(camp_repo),
        schedule,
        execution_source_head=expected_execution_source_head,
        camp_head=camp_head,
        config_path=Path(config_path),
        expected_config_sha256=expected_config_sha256,
        expected_evaluator_sha256=expected_evaluator_sha256,
        prior_camp_heads={
            "preflight_camp_head": expected_preflight_camp_head,
            "pilot_review_camp_head": expected_pilot_review_camp_head,
            "pilot_execution_source_head": expected_pilot_execution_source_head,
        },
    )
    execution = inspect_execution(
        Path(execution_root),
        schedule,
        upstream["holdout_route_sources"],
        expected_execution_source_head=expected_execution_source_head,
        expected_preflight_root_sha256=expected_preflight_root_sha256,
    )
    # Preserve tick-level all-K counts for independent aggregate accounting.
    for row in execution["rows"]:
        if row.get("paired_complete") is True:
            pair_root = Path(execution_root).joinpath(*PurePosixPath(str(row["pair_key"])).parts)
            row["camp_tick_receipts"] = _load_json(pair_root / "camp.json")["ticks"]
    guards = {
        "artifact_sha_verified": True,
        "per_arm_candidate_immutability_verified": True,
        "per_arm_candidate0_default_identity_verified": True,
        "t0_cross_arm_input_and_candidate_identity_verified": True,
        # This reviewer cannot self-authorize its own yet-unsealed evidence root.
        # The separate claim-decision gate may set this guard only after rehashing
        # the complete-sealed reviewer artifact.
        "independent_review_passed": False,
        "split_zero_overlap_verified": upstream["split_zero_overlap_verified"],
        "holdout_once_verified": state["holdout_open_count"] == 1 and state["rerun_authorized"] is False,
        "arm_order_balance_verified": schedule["receipt"]["arm_order_counts"] == {"dp_camp": 60, "camp_dp": 60},
        "feature_identity_denylist_verified": upstream["feature_identity_denylist_verified"],
    }
    metrics = aggregate_metrics(
        schedule["pair_keys"],
        execution["rows"],
        evidence_guards=guards,
    )
    source_stats = execution["summary"].get("descriptive_statistics")
    if not isinstance(source_stats, Mapping):
        raise ValueError("execution summary is missing descriptive statistics")
    _compare_source_statistics(source_stats, metrics)

    raw_candidate_paths = [
        relative
        for relative in roots["execution"]["manifest_paths"]
        if "candidate_tensor" in relative.lower()
        and not relative.lower().endswith(".json")
    ]
    raw_atom_paths = [
        relative
        for relative in roots["execution"]["manifest_paths"]
        if "atom_matrix" in relative.lower()
        and not relative.lower().endswith(".json")
    ]
    if raw_candidate_paths or raw_atom_paths:
        raise ValueError("unexpected raw candidate/atom payload path in execution artifact")
    evidence_limitations = {
        "raw_candidate_tensor_bytes_present": False,
        "raw_atom_matrix_bytes_present": False,
        "affine_score_receipt_consistency_verified": True,
        "affine_scores_recomputed_from_raw_atoms": False,
        "candidate_hashes_recomputed_from_raw_tensor_bytes": False,
        "candidate_and_atom_hash_scope": "complete_sealed_receipt_consistency_only",
        "raw_byte_proof_claimed": False,
    }
    free_bytes = shutil.disk_usage(Path(output_dir).parent).free
    if free_bytes <= MINIMUM_FREE_BYTES:
        raise ValueError("independent review violates the 10 GiB disk floor")
    checks = {
        "all_source_complete_seals_verified": True,
        "execution_launch_chain_bound": True,
        "preflight_authorization_reviews_passed": True,
        "split_and_training_roots_verified": True,
        "split_census_schedule_exact_join_verified": True,
        "source_census_arc_length_denominators_verified": True,
        "frozen_train_coverage_and_learning_curve_risk_disclosed": True,
        "runtime_selector_matches_training": True,
        "fixed_request_and_assets_hash_bound": True,
        "main_schedule_24x5_120": True,
        "arm_order_hash_rank_balance_60_60": True,
        "outcome_blind_preregistered_arm_order_control_verified": True,
        "independent_reset_same_initial_state_and_exogenous_seed_verified": True,
        "one_family_three_corridors": True,
        "holdout_state_exact_open_once": True,
        "live_camp_and_fixed_dp_clean": True,
        "producer_code_provenance_unchanged": True,
        "all_pair_arm_tick_receipts_recomputed": True,
        "t0_cross_arm_identity_only": True,
        "post_divergence_cross_arm_tensors_not_compared": True,
        "safety_secondary_latency_recomputed": True,
        "producer_descriptive_statistics_consistent": True,
        "raw_byte_evidence_limit_disclosed": True,
        "latency_descriptive_only": True,
        "latency_comparative_conclusion_forbidden": True,
        "map_family_ci_and_unseen_claim_forbidden": True,
        "disk_floor": True,
    }
    result = {
        "schema": "camp_dp_v24_paired_holdout_main_once_execution_independent_review_v1",
        "status": "passed",
        "check_count": len(checks),
        "failed_count": 0,
        "failed_checks": [],
        "checks": checks,
        "source_roots": {**roots, **upstream["roots"], "runtime_selector": runtime_selector["root"]},
        "schedule": schedule["receipt"],
        "execution": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": execution["complete_count"],
            "source_invalid_pair_count": execution["source_invalid_count"],
            "execution_failure_pair_count": execution["execution_failure_count"],
            "dp_tick_count": execution["dp_tick_count"],
            "camp_tick_count": execution["camp_tick_count"],
            "all_k_high_risk_tick_count": execution["all_k_high_risk_tick_count"],
        },
        "holdout_state": state,
        "launch": launch,
        "provenance": provenance,
        "runtime_selector": {key: value for key, value in runtime_selector.items() if key != "root"},
        "request_assets": request_assets,
        "route_source_bindings": upstream["holdout_route_sources"],
        "frozen_metric_contract": frozen_metric_contract,
        "evidence_limitations": evidence_limitations,
        "claim_guard_handoff": {
            "independent_review_passed": False,
            "status": "pending_separate_claim_decision_rehash_of_sealed_reviewer_root",
            "reviewer_self_authorization_forbidden": True,
        },
        "metrics": metrics,
        "camp_head": camp_head,
        "execution_source_head": expected_execution_source_head,
        "preflight_camp_head": expected_preflight_camp_head,
        "preflight_config_sha256": expected_preflight_config_sha256,
        "pilot_review_camp_head": expected_pilot_review_camp_head,
        "pilot_execution_source_head": expected_pilot_execution_source_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_execution_reexecuted": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
        "holdout_open_count": 1,
        "latency_comparison_authorized": False,
        "map_family_level_ci_authorized": False,
        "unseen_map_generalization_authorized": False,
        "native_ranked_k8_claim_authorized": False,
        "final_claim_authorized": False,
        "free_bytes_after_review": free_bytes,
        "next_work_target": "v24_evidence_package_and_preregistered_claim_decision",
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True)
    _write_json(output_dir / "review_result.json", result)
    _write_json(output_dir / "recomputed_metrics.json", metrics)
    _write_json(output_dir / "schedule_receipt.json", schedule["receipt"])
    _write_json(output_dir / "provenance.json", provenance)
    decision = metrics["claim_gate_result"]["decision"]
    (output_dir / "summary.md").write_text(
        "# v24 holdout main-once independent result review\n\n"
        f"- status/checks/failed: `{result['status']} / {len(checks)} / 0`\n"
        f"- planned/retained/complete: `120 / 120 / {execution['complete_count']}`\n"
        f"- source-invalid/execution-invalid: `{execution['source_invalid_count']} / {execution['execution_failure_count']}`\n"
        "- train source coverage disclosure: `1875 retained / 1054 complete / 821 failed`\n"
        "- learning-curve concentration: active support `[7, 8, 13]`; risk disclosed, no calibration/holdout repair\n"
        "- route completion denominator: independently bound to sealed route-census `source_arc_length_m`\n"
        f"- preregistered claim-gate result: `{decision}`\n"
        "- CI hierarchy: `corridor -> route -> seed`; map-family CI is forbidden\n"
        "- latency: descriptive arm-only; no comparative conclusion\n"
        "- raw candidate/atom bytes: absent; sealed receipt consistency only\n"
        "- final claim authorization: `false` (separate claim-decision gate required)\n",
        encoding="utf-8",
    )
    (output_dir / "HEADS.txt").write_text(
        f"CAMP_HEAD={camp_head}\n"
        f"EXECUTION_SOURCE_HEAD={expected_execution_source_head}\n"
        f"PREFLIGHT_CAMP_HEAD={expected_preflight_camp_head}\n"
        f"PILOT_REVIEW_CAMP_HEAD={expected_pilot_review_camp_head}\n"
        f"PILOT_EXECUTION_SOURCE_HEAD={expected_pilot_execution_source_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output_dir / "COMMAND.txt").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output_dir / "stdout.txt").write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = seal_artifact(output_dir)
    verify_complete_seal(output_dir, root_sha256, "independent_review_output")
    result["root_sha256"] = root_sha256
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-preflight-config-sha256", required=True)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--expected-execution-root-sha256", required=True)
    parser.add_argument("--launch-root", type=Path, required=True)
    parser.add_argument("--expected-launch-root-sha256", required=True)
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--preflight-review-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-review-root-sha256", required=True)
    parser.add_argument("--pilot-review-root", type=Path, required=True)
    parser.add_argument("--expected-pilot-review-root-sha256", required=True)
    parser.add_argument("--authorization-root", type=Path, required=True)
    parser.add_argument("--expected-authorization-root-sha256", required=True)
    parser.add_argument("--authorization-review-root", type=Path, required=True)
    parser.add_argument("--expected-authorization-review-root-sha256", required=True)
    parser.add_argument("--expected-preflight-camp-head", required=True)
    parser.add_argument("--expected-pilot-review-camp-head", required=True)
    parser.add_argument("--expected-pilot-execution-source-head", required=True)
    parser.add_argument("--expected-execution-source-head", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-independent-review", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = review_holdout_main_result(
        config_path=args.config,
        expected_config_sha256=args.expected_config_sha256,
        expected_preflight_config_sha256=args.expected_preflight_config_sha256,
        expected_evaluator_sha256=args.expected_evaluator_sha256,
        execution_root=args.execution_root,
        expected_execution_root_sha256=args.expected_execution_root_sha256,
        launch_root=args.launch_root,
        expected_launch_root_sha256=args.expected_launch_root_sha256,
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        preflight_review_root=args.preflight_review_root,
        expected_preflight_review_root_sha256=args.expected_preflight_review_root_sha256,
        pilot_review_root=args.pilot_review_root,
        expected_pilot_review_root_sha256=args.expected_pilot_review_root_sha256,
        authorization_root=args.authorization_root,
        expected_authorization_root_sha256=args.expected_authorization_root_sha256,
        authorization_review_root=args.authorization_review_root,
        expected_authorization_review_root_sha256=args.expected_authorization_review_root_sha256,
        expected_preflight_camp_head=args.expected_preflight_camp_head,
        expected_pilot_review_camp_head=args.expected_pilot_review_camp_head,
        expected_pilot_execution_source_head=args.expected_pilot_execution_source_head,
        expected_execution_source_head=args.expected_execution_source_head,
        camp_head=args.camp_head,
        output_dir=args.output_dir,
        enable_independent_review=args.enable_independent_review,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
