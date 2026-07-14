#!/usr/bin/env python3
"""Thin retained-pair evaluator over the shared v21 native arm runner."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    aggregate_paired_safety,
    paired_safety_delta,
)
from camp_core.integrations.diffusion_planner_v22_native import (  # noqa: E402
    retained_pair_row,
)
from camp_core.integrations.diffusion_planner_v22_split import (  # noqa: E402
    validate_split_manifest,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    NATIVE_SOURCE_SHA256,
    SPAWN_CONFIG_FIELDS,
    V22_SOURCE_VALID_SELECTION,
    build_native_arm_runner,
    canonical_spawn_config_sha256,
    validate_native_arm_receipt,
    validate_v22_evaluation_run_config,
    verify_config_assets,
)


FORMAL_SEEDS = frozenset({11, 12, 13})
MODES = frozenset({"capability", "pilot", "main"})


def build_pair_schedule(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    _validate_evaluation_config(config)
    validate_split_manifest(manifest)
    if manifest.get("source_only") is not True or manifest.get(
        "outcome_fields_consumed"
    ) != []:
        raise ValueError("evaluation split must remain source-only and outcome-blind")
    if manifest.get("split_freeze_sha256") != _mapping(
        config, "source_split"
    ).get("split_freeze_sha256"):
        raise ValueError("split freeze SHA mismatch")
    if mode not in MODES:
        raise ValueError("unknown evaluation mode")
    if mode == "main" and config.get("main_execution_authorized") is not True:
        raise ValueError("main execution is not authorized")
    if mode == "main" and config.get("holdout_opened") is not False:
        raise ValueError("main holdout was already opened")
    if mode == "pilot" and config.get("pilot_execution_authorized") is not True:
        raise ValueError("pilot execution is not authorized")

    mode_config = _mapping(_mapping(config, "modes"), mode)
    split = str(mode_config["split"])
    split_payload = _mapping(_mapping(manifest, "splits"), split)
    routes = sorted(
        list(split_payload.get("routes", [])),
        key=lambda item: str(item["identity_sha256"]),
    )
    seeds = sorted(int(value) for value in split_payload.get("seed_namespace", []))
    route_count = int(mode_config["route_count"])
    seed_count = int(mode_config["seed_count"])
    if mode in {"pilot", "main"} and (
        len(routes) != route_count or len(seeds) != seed_count
    ):
        raise ValueError(f"{mode} route or seed count differs from preregistration")
    if len(routes) < route_count or len(seeds) < seed_count:
        raise ValueError(f"{mode} route or seed capacity is incomplete")
    selected_routes = routes[:route_count]
    selected_seeds = seeds[:seed_count]
    if set(selected_seeds).intersection(FORMAL_SEEDS):
        raise ValueError("formal seed is forbidden")
    return [
        {
            "schema_version": "v22_planned_pair_v1",
            "pair_key": f"{split}/{route['identity_sha256']}/seed_{seed}",
            "receipt_key": (
                f"{split}/{route['identity_sha256']}/seed_{seed}/pair.json"
            ),
            "split": split,
            "route_identity_sha256": str(route["identity_sha256"]),
            "group_sha256": str(route["group_sha256"]),
            "logical_map_sha256": str(route["logical_map_sha256"]),
            "seed": seed,
            "route": dict(route),
            "source_stratum": dict(route.get("source_stratum", {})),
            "expected_arms": ["dp", "camp"],
            "included_in_denominator": True,
        }
        for route in selected_routes
        for seed in selected_seeds
    ]


def build_evaluation_run_config(
    config: Mapping[str, Any],
    base_config: Mapping[str, Any],
    planned: Mapping[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    mode_config = _mapping(_mapping(config, "modes"), mode)
    route = _mapping(planned, "route")
    route_asset = _mapping(route, "route_asset")
    logical_map_sha256 = str(planned["logical_map_sha256"])
    maps = {
        str(item["sha256"]): item
        for item in config.get("maps", [])
        if isinstance(item, Mapping)
    }
    if logical_map_sha256 not in maps:
        raise ValueError("planned route logical map is absent from frozen maps")
    map_asset = maps[logical_map_sha256]
    if _mapping(route, "route_spec").get("map_path") != map_asset.get("path"):
        raise ValueError("planned route map path differs from frozen logical map")
    seed = int(planned["seed"])
    steps = int(mode_config["max_steps"])
    frozen = _mapping(config, "frozen_selector")
    result = deepcopy(dict(base_config))
    result["schema_version"] = "camp_dp_v22_native_evaluation_run_v1"
    result["selector"] = {
        "root": str(frozen["artifact"]),
        "root_sha256": str(frozen["artifact_root_sha256"]),
        "model_sha256": str(frozen["model_sha256"]),
        "atom_scales": dict(_mapping(frozen, "atom_scales")),
        "weights": dict(_mapping(frozen, "weights")),
        "score_contract": "score_k(w)=a_k^T w",
        "nonnegative_simplex": True,
        "candidate_k": 8,
        "selection_policy": V22_SOURCE_VALID_SELECTION,
        "role": "v22_primary_frozen",
    }
    result["map"] = dict(map_asset)
    result["routes"] = [
        {
            "name": str(planned["route_identity_sha256"]),
            "path": str(route_asset["path"]),
            "sha256": str(route_asset["sha256"]),
        }
    ]
    result["seeds"] = {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [11, 12, 13],
    }
    result["spawn_config"]["seed"] = seed
    result["spawn_config"]["max_steps"] = steps
    result["protocol"] = {
        "evaluation_mode": mode,
        "evaluation_split": str(mode_config["split"]),
        "evaluation_steps": steps,
        "arm_order": ["dp", "camp"],
        "safety_schema": "safety_cost_native_v22",
        "route_retention": "all_preregistered_routes_and_failures",
        "training_authorized": False,
        "holdout_access_authorized": mode == "main",
        "formal_seeds_authorized": False,
        "claim_authorized": False,
    }
    validate_v22_evaluation_run_config(result)
    return result


def validate_successful_pair(
    dp_arm: Mapping[str, Any],
    camp_arm: Mapping[str, Any],
    planned: Mapping[str, Any],
    run_config: Mapping[str, Any],
) -> None:
    steps = int(_mapping(run_config, "protocol")["evaluation_steps"])
    validate_native_arm_receipt(
        dp_arm, "dp", expected_ticks=steps, expected_safety_schema="safety_cost_native_v22"
    )
    validate_native_arm_receipt(
        camp_arm,
        "camp",
        expected_ticks=steps,
        expected_selection_policy=V22_SOURCE_VALID_SELECTION,
        expected_safety_schema="safety_cost_native_v22",
    )
    route = _mapping(planned, "route")
    expected = {
        "route_name": planned["route_identity_sha256"],
        "route_sha256": _mapping(route, "route_asset")["sha256"],
        "logical_map_sha256": planned["logical_map_sha256"],
        "fixed_dp_head": run_config["fixed_dp"]["head"],
        "checkpoint_sha256": run_config["fixed_dp"]["checkpoint"]["sha256"],
        "args_sha256": run_config["fixed_dp"]["args_json"]["sha256"],
        "scenario_seed": planned["seed"],
        "spawn_config_sha256": canonical_spawn_config_sha256(run_config, steps),
    }
    for name, value in expected.items():
        if dp_arm.get(name) != value or camp_arm.get(name) != value:
            raise ValueError(f"paired {name} mismatch")
    for name in ("initial_state_sha256", "initial_input_sha256"):
        if dp_arm.get(name) != camp_arm.get(name):
            raise ValueError(f"paired {name} mismatch")


def execute_paired_evaluation(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    base_config: Mapping[str, Any],
    freeze_manifest: Mapping[str, Any],
    *,
    mode: str,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_freeze_manifest(config, freeze_manifest)
    schedule = build_pair_schedule(config, manifest, mode=mode)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    rows = []
    pair_started = time.perf_counter()
    for planned in schedule:
        run_config = build_evaluation_run_config(
            config, base_config, planned, mode=mode
        )
        native_route = run_config["routes"][0]
        pair_root = output / planned["receipt_key"].removesuffix("/pair.json")
        arms: dict[str, dict[str, Any]] = {}
        for arm in ("dp", "camp"):
            arm_started = time.perf_counter()
            try:
                receipt = dict(
                    run_arm(
                        route=native_route,
                        arm=arm,
                        config=run_config,
                        output_dir=pair_root / "native_runs" / arm,
                        max_steps=int(run_config["protocol"]["evaluation_steps"]),
                    )
                )
            except Exception as exc:
                receipt = _failure_arm(planned, arm, exc)
            receipt["evaluation_wall_clock_s"] = time.perf_counter() - arm_started
            arms[arm] = receipt
            _write_json(pair_root / f"{arm}.json", receipt)
            for tick in receipt.get("ticks", []):
                _write_json(
                    pair_root / arm / f"tick_{int(tick['tick_index']):04d}.json",
                    tick,
                )
        if arms["dp"]["status"] == arms["camp"]["status"] == "ok":
            validate_successful_pair(arms["dp"], arms["camp"], planned, run_config)
        arms["camp"]["all_k_high_risk"] = any(
            bool(tick.get("all_k_high_risk")) for tick in arms["camp"].get("ticks", [])
        )
        row = retained_pair_row(
            pair_key=str(planned["pair_key"]),
            split=str(planned["split"]),
            dp_arm=arms["dp"],
            camp_arm=arms["camp"],
        )
        row.update(
            {
                "receipt_key": planned["receipt_key"],
                "route_identity_sha256": planned["route_identity_sha256"],
                "group_sha256": planned["group_sha256"],
                "logical_map_sha256": planned["logical_map_sha256"],
                "seed": planned["seed"],
                "source_stratum": planned["source_stratum"],
                "arm_order": ["dp", "camp"],
                "route_retained": True,
            }
        )
        if row["paired_complete"]:
            dp_safety = arms["dp"]["safety"]
            camp_safety = arms["camp"]["safety"]
            row.update(
                {
                    "dp_safety": dp_safety,
                    "camp_safety": camp_safety,
                    "paired_delta": paired_safety_delta(
                        dp_safety["safety_cost"], camp_safety["safety_cost"]
                    ),
                    "component_delta": {
                        name: float(camp_safety["components"][name])
                        - float(dp_safety["components"][name])
                        for name in dp_safety["components"]
                    },
                    "dp_secondary": arms["dp"]["secondary"],
                    "camp_secondary": arms["camp"]["secondary"],
                    "dp_latency": arms["dp"]["latency"],
                    "camp_latency": arms["camp"]["latency"],
                }
            )
        _write_json(pair_root / "pair.json", row)
        rows.append(row)

    complete = [row for row in rows if row["paired_complete"]]
    summary: dict[str, Any] = {
        "schema_version": "camp_dp_v22_paired_evaluation_summary_v1",
        "status": "complete_with_retained_failures" if len(complete) < len(rows) else "complete",
        "mode": mode,
        "execution_split": _mapping(_mapping(config, "modes"), mode)["split"],
        "planned_pair_count": len(schedule),
        "retained_pair_count": len(rows),
        "paired_complete_count": len(complete),
        "hard_invalid_pair_count": sum(bool(row["hard_invalid"]) for row in rows),
        "execution_failure_pair_count": sum(bool(row["execution_failure"]) for row in rows),
        "all_k_high_risk_pair_count": sum(bool(row["all_k_high_risk"]) for row in rows),
        "route_coverage": len(rows) / len(schedule),
        "paired_complete_rate": len(complete) / len(rows),
        "hard_invalid_rate": sum(bool(row["hard_invalid"]) for row in rows) / len(rows),
        "wall_clock_s": time.perf_counter() - pair_started,
        "primary_speed_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "final_claim_authorized": False,
        "holdout_opened": mode == "main",
    }
    if complete:
        summary["aggregate_complete_pairs"] = aggregate_paired_safety(
            [row["paired_delta"] for row in complete]
        )
    _write_json(output / "pair_rows.json", rows)
    _write_json(output / "summary.json", summary)
    (output / "summary.md").write_text(
        "# v22 native paired evaluation\n\n"
        f"- mode: `{mode}`\n"
        f"- planned / retained / complete: `{len(schedule)} / {len(rows)} / {len(complete)}`\n"
        "- final claim authorized: `false`\n",
        encoding="utf-8",
    )
    (output / "run.exit").write_text("0\n", encoding="ascii")
    _write_json(output / "evaluation_config.json", config)
    _write_json(output / "planned_pairs.json", schedule)
    _write_heads_and_command(output, mode)
    _seal_output(output)
    return summary


def run_static_preflight(config_path: Path) -> dict[str, Any]:
    config_bytes = Path(config_path).read_bytes()
    config = json.loads(config_bytes)
    _validate_evaluation_config(config)
    source = _mapping(config, "source_split")
    source_artifact = _verify_artifact_root(
        source["artifact"], source["artifact_root_sha256"], "source split"
    )
    manifest_path = Path(str(source["manifest_path"]))
    if (
        not manifest_path.resolve().is_relative_to(source_artifact.resolve())
        or _file_sha256(manifest_path) != source["manifest_sha256"]
    ):
        raise ValueError("source split manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_split_manifest(manifest)

    base_entry = _mapping(config, "base_native_config")
    base_path = Path(str(base_entry["path"]))
    if _file_sha256(base_path) != base_entry["sha256"]:
        raise ValueError("base native config SHA mismatch")
    base_config = json.loads(base_path.read_text(encoding="utf-8"))

    frozen = _mapping(config, "frozen_selector")
    freeze_artifact = _verify_artifact_root(
        frozen["artifact"], frozen["artifact_root_sha256"], "frozen selector"
    )
    _verify_artifact_root(
        frozen["independent_review_artifact"],
        frozen["independent_review_root_sha256"],
        "frozen selector independent review",
    )
    freeze_path = Path(str(frozen["manifest_path"]))
    if (
        not freeze_path.resolve().is_relative_to(freeze_artifact.resolve())
        or _file_sha256(freeze_path) != frozen["manifest_sha256"]
    ):
        raise ValueError("frozen selector manifest SHA mismatch")
    freeze_manifest = json.loads(freeze_path.read_text(encoding="utf-8"))
    _validate_freeze_manifest(config, freeze_manifest)
    for name in ("weights", "atom_scales"):
        asset = _mapping(frozen, name)
        if _file_sha256(Path(str(asset["path"]))) != asset["sha256"]:
            raise ValueError(f"frozen selector {name} SHA mismatch")

    maps = {
        str(item["sha256"]): item
        for item in config.get("maps", [])
        if isinstance(item, Mapping)
    }
    if len(maps) != 2:
        raise ValueError("evaluation must freeze exactly two logical maps")
    for item in maps.values():
        if _file_sha256(Path(str(item["path"]))) != item["sha256"]:
            raise ValueError("logical map SHA mismatch")
    splits = _mapping(manifest, "splits")
    route_counts = {}
    seed_counts = {}
    for split in ("train", "calibration", "holdout"):
        payload = _mapping(splits, split)
        routes = list(payload.get("routes", []))
        seeds = list(payload.get("seed_namespace", []))
        route_counts[split] = len(routes)
        seed_counts[split] = len(seeds)
        for route in routes:
            if str(route["logical_map_sha256"]) not in maps:
                raise ValueError("split route references an unfrozen logical map")
            asset = _mapping(route, "route_asset")
            if _file_sha256(Path(str(asset["path"]))) != asset["sha256"]:
                raise ValueError("split route asset SHA mismatch")

    capability = build_pair_schedule(config, manifest, mode="capability")
    pilot = build_pair_schedule(config, manifest, mode="pilot")
    main_config = deepcopy(dict(config))
    main_config["main_execution_authorized"] = True
    main = build_pair_schedule(main_config, manifest, mode="main")
    planned = {
        "capability": capability,
        "pilot": pilot,
        "main": main,
    }
    run_configs = {
        mode: [
            build_evaluation_run_config(config, base_config, item, mode=mode)
            for item in schedule
        ]
        for mode, schedule in planned.items()
    }
    verified_assets = {}
    seen_maps = set()
    for mode in ("capability", "pilot", "main"):
        for run_config in run_configs[mode]:
            map_sha = run_config["map"]["sha256"]
            if map_sha not in seen_maps:
                verified_assets.update(verify_config_assets(run_config))
                seen_maps.add(map_sha)
    return {
        "schema_version": "camp_dp_v22_paired_evaluation_preflight_v1",
        "status": "passed",
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "split_manifest_sha256": source["manifest_sha256"],
        "split_freeze_sha256": source["split_freeze_sha256"],
        "frozen_selector_root_sha256": frozen["artifact_root_sha256"],
        "frozen_selector_review_root_sha256": frozen[
            "independent_review_root_sha256"
        ],
        "route_counts": route_counts,
        "seed_counts": seed_counts,
        "planned_pair_counts": {
            mode: len(schedule) for mode, schedule in planned.items()
        },
        "validated_run_config_count": sum(
            len(values) for values in run_configs.values()
        ),
        "verified_asset_count": len(verified_assets),
        "shared_runner_factory": build_native_arm_runner.__name__,
        "primary_speed_tolerance_mps": 0.1,
        "speed_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "model_loaded": False,
        "runner_built": False,
        "simulator_executed": False,
        "pilot_executed": False,
        "holdout_opened": False,
        "holdout_outcomes_read": False,
        "claim_authorized": False,
        "main_execution_authorized": False,
        "next_work_target": "v22_native_paired_capability_execution_only",
    }


def execute_from_config(
    config_path: Path,
    output_dir: Path,
    *,
    mode: str,
    device: str,
) -> dict[str, Any]:
    run_static_preflight(config_path)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    source = _mapping(config, "source_split")
    manifest = json.loads(
        Path(str(source["manifest_path"])).read_text(encoding="utf-8")
    )
    base = _mapping(config, "base_native_config")
    base_config = json.loads(
        Path(str(base["path"])).read_text(encoding="utf-8")
    )
    frozen = _mapping(config, "frozen_selector")
    freeze_manifest = json.loads(
        Path(str(frozen["manifest_path"])).read_text(encoding="utf-8")
    )
    schedule = build_pair_schedule(config, manifest, mode=mode)
    first_config = build_evaluation_run_config(
        config, base_config, schedule[0], mode=mode
    )
    run_arm = build_native_arm_runner(first_config, device=device)
    return execute_paired_evaluation(
        config,
        manifest,
        base_config,
        freeze_manifest,
        mode=mode,
        output_dir=output_dir,
        run_arm=run_arm,
    )


def _validate_evaluation_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v22_native_evaluation_v1":
        raise ValueError("evaluation config schema mismatch")
    if set(_mapping(config, "modes")) != MODES:
        raise ValueError("evaluation modes must be capability/pilot/main")
    if (
        config.get("arm_order") != ["dp", "camp"]
        or config.get("candidate_k") != 8
        or config.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or config.get("score_contract") != "score_k(w)=a_k^T w"
        or config.get("nonnegative_simplex") is not True
        or config.get("safety_schema") != "safety_cost_native_v22"
        or float(config.get("primary_speed_tolerance_mps", -1.0)) != 0.1
        or config.get("speed_sensitivity_tolerances_mps") != [0.0, 0.05, 0.1, 0.2]
        or config.get("route_retention")
        != "all_preregistered_routes_and_failures"
        or config.get("claim_contract")
        != {
            "overall_mean_delta_strictly_below_zero": True,
            "cluster_ci95_upper_strictly_below_zero": True,
            "better_pairs_must_exceed_worse_pairs": True,
            "additional_collision_pairs_max": 0,
            "additional_red_light_pairs_max": 0,
            "offroad_wrong_way_mean_delta_max": 0.0,
            "offroad_wrong_way_ci95_upper_max": 0.005,
        }
        or config.get("formal_seeds_authorized") is not False
        or config.get("full36_authorized") is not False
        or config.get("claim_authorized") is not False
    ):
        raise ValueError("evaluation scientific contract mismatch")


def _validate_freeze_manifest(
    config: Mapping[str, Any], freeze_manifest: Mapping[str, Any]
) -> None:
    frozen = _mapping(config, "frozen_selector")
    selected = _mapping(freeze_manifest, "selected_model")
    runtime = _mapping(freeze_manifest, "runtime_assets")
    if (
        freeze_manifest.get("status") != "complete"
        or freeze_manifest.get("primary_model_frozen") is not True
        or freeze_manifest.get("model_retrained") is not False
        or freeze_manifest.get("solver_invoked") is not False
        or freeze_manifest.get("holdout_executed") is not False
        or freeze_manifest.get("claim_authorized") is not False
        or selected.get("model_sha256") != frozen.get("model_sha256")
        or _mapping(runtime, "weights").get("sha256")
        != _mapping(frozen, "weights").get("sha256")
        or _mapping(runtime, "atom_scales").get("sha256")
        != _mapping(frozen, "atom_scales").get("sha256")
        or selected.get("score_contract") != "score_k(w)=a_k^T w"
        or float(freeze_manifest.get("primary_operational_tolerance_mps", -1.0))
        != 0.1
    ):
        raise ValueError("frozen selector receipt mismatch")


def _failure_arm(
    planned: Mapping[str, Any], arm: str, exc: Exception
) -> dict[str, Any]:
    reason = str(exc)
    source_invalid = any(
        marker in reason.lower()
        for marker in (
            "source is incomplete",
            "source invalid",
            "nan",
            "inf",
            "shape",
            "time grid",
            "candidate hash",
            "candidate bytes",
        )
    )
    return {
        "schema_version": "v22_failed_arm_receipt_v1",
        "status": "source_invalid" if source_invalid else "failed",
        "arm": arm,
        "route_name": planned["route_identity_sha256"],
        "failure_stage": "source_validation" if source_invalid else "native_arm_execution",
        "reason": reason,
        "ticks": [],
        "claim_authorized": False,
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(value))


def _write_heads_and_command(output: Path, mode: str) -> None:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (output / "HEADS").write_text(
        f"camp_head={head}\nfixed_dp_head={FIXED_DP_HEAD}\n", encoding="ascii"
    )
    (output / "COMMAND").write_text(
        f"mode={mode}\nshared_runner=build_native_arm_runner\n", encoding="utf-8"
    )
    (output / "stdout").write_text("paired evaluation complete\n", encoding="utf-8")
    (output / "stderr").write_text("", encoding="utf-8")


def _seal_output(output: Path) -> str:
    entries = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            relative = path.relative_to(output).as_posix()
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    sums = "".join(entries).encode("ascii")
    (output / "SHA256SUMS").write_bytes(sums)
    root = hashlib.sha256(sums).hexdigest()
    (output / "ROOT_SHA256SUMS").write_text(f"{root}  SHA256SUMS\n", encoding="ascii")
    return root


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact_root_sha256(path: Path) -> str:
    sums = Path(path) / "SHA256SUMS"
    if not sums.is_file():
        raise ValueError("artifact SHA256SUMS is missing")
    return hashlib.sha256(sums.read_bytes()).hexdigest()


def _verify_artifact_root(path_value: Any, expected: Any, label: str) -> Path:
    path = Path(str(path_value))
    if not isinstance(expected, str) or _artifact_root_sha256(path) != expected:
        raise ValueError(f"{label} artifact root SHA mismatch")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", dest="mode", action="store_const", const="preflight")
    modes.add_argument("--capability", dest="mode", action="store_const", const="capability")
    modes.add_argument("--pilot", dest="mode", action="store_const", const="pilot")
    modes.add_argument("--main", dest="mode", action="store_const", const="main")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args(argv)
    if args.mode != "preflight" and args.output is None:
        parser.error("--output is required for execution")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "preflight":
        result = run_static_preflight(args.config)
    else:
        result = execute_from_config(
            args.config, args.output, mode=args.mode, device=args.device
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
