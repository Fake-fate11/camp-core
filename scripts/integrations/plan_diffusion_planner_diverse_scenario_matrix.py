#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from itertools import product
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_benchmark_matrix.py"
FORMAL_SEEDS = {11, 12, 13}
SUPPORTED_BUCKETS = {
    "overall",
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
}
DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)
ROUTE_WIDE_BUCKETS = {"sharp_turn", "lane_change_or_merge"}
TRAFFIC_LIGHT_BUCKETS = {"traffic_light", "red_light_turn"}
CONFIG_DERIVED_BUCKETS = {"normal", "npc_interaction", "dense_scene"}


def _parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("route must have the form NAME=/path/route.pkl")
    name, raw_path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("route name must not be empty")
    return name, Path(raw_path)


def _parse_route_buckets(value: str) -> tuple[str, list[str]]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "route_bucket must have the form NAME=bucket[,bucket]"
        )
    name, raw_buckets = value.split("=", 1)
    buckets = [bucket.strip() for bucket in raw_buckets.split(",") if bucket.strip()]
    invalid = sorted(set(buckets) - (SUPPORTED_BUCKETS - {"overall"}))
    if invalid:
        raise argparse.ArgumentTypeError(f"unsupported bucket(s): {invalid}")
    return name.strip(), buckets


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_traffic_light_modes(value: str) -> list[str]:
    modes = [part.strip() for part in value.split(",") if part.strip()]
    invalid = sorted(set(modes) - {"on", "off"})
    if invalid:
        raise argparse.ArgumentTypeError(f"traffic light modes must be on/off: {invalid}")
    return modes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a non-formal diverse DP-CAMP outcome-label matrix and its "
            "explicit scenario bucket manifest. This emits commands and gates "
            "only; it does not run DP."
        )
    )
    parser.add_argument("--oracle_json", type=Path, default=None)
    parser.add_argument("--route", action="append", type=_parse_named_path, required=True)
    parser.add_argument(
        "--route_bucket",
        action="append",
        type=_parse_route_buckets,
        default=[],
        help=(
            "Explicit label evidence for a route, NAME=bucket[,bucket]. "
            "traffic_light/red_light_turn/normal/npc/dense buckets are emitted "
            "as configuration filters rather than metric-derived labels."
        ),
    )
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_manifest", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, default=None)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--camp_atom_scales", type=Path, required=True)
    parser.add_argument("--camp_static_weights", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seeds", type=_parse_int_list, required=True)
    parser.add_argument("--max_npcs", type=_parse_int_list, required=True)
    parser.add_argument("--spawn_probabilities", type=_parse_float_list, required=True)
    parser.add_argument("--traffic_light_modes", type=_parse_traffic_light_modes, required=True)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument("--candidate_reference_blend_steps", type=int, default=5)
    parser.add_argument("--camp_min_progress_ratio", type=float, default=0.8)
    parser.add_argument("--camp_reward_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_outcome_horizon_steps", type=int, default=30)
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    parser.add_argument("--npc_interaction_min_npcs", type=int, default=8)
    parser.add_argument("--npc_interaction_min_spawn", type=float, default=0.5)
    parser.add_argument("--dense_scene_min_npcs", type=int, default=8)
    parser.add_argument("--dense_scene_min_spawn", type=float, default=0.6)
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_BUCKETS - {"overall"}),
        default=None,
    )
    parser.add_argument("--require_route_files", action="store_true")
    parser.add_argument("--fail_on_blocker", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_plan(
        oracle_json=_read_json_if_exists(args.oracle_json),
        routes=dict(args.route),
        route_buckets=_route_bucket_map(args.route_bucket),
        output_root=args.output_root,
        output_manifest=args.output_manifest,
        diffusion_repo=args.diffusion_repo,
        map_path=args.map_path,
        model_path=args.model_path,
        model_args=args.model_args,
        config=args.config,
        reward_config=args.reward_config,
        camp_atom_scales=args.camp_atom_scales,
        camp_static_weights=args.camp_static_weights,
        device=args.device,
        steps=args.steps,
        seeds=args.seeds,
        max_npcs=args.max_npcs,
        spawn_probabilities=args.spawn_probabilities,
        traffic_light_modes=args.traffic_light_modes,
        num_candidates=args.num_candidates,
        candidate_noise_scale=args.candidate_noise_scale,
        candidate_reference_blend_steps=args.candidate_reference_blend_steps,
        camp_min_progress_ratio=args.camp_min_progress_ratio,
        camp_reward_horizon_steps=args.camp_reward_horizon_steps,
        camp_outcome_horizon_steps=args.camp_outcome_horizon_steps,
        near_miss_threshold_m=args.near_miss_threshold_m,
        npc_interaction_min_npcs=args.npc_interaction_min_npcs,
        npc_interaction_min_spawn=args.npc_interaction_min_spawn,
        dense_scene_min_npcs=args.dense_scene_min_npcs,
        dense_scene_min_spawn=args.dense_scene_min_spawn,
        required_buckets=(
            tuple(args.required_bucket)
            if args.required_bucket is not None
            else _required_buckets_from_oracle(args.oracle_json)
        ),
        require_route_files=args.require_route_files,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    args.output_manifest.write_text(
        json.dumps(report["scenario_bucket_manifest"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    if args.fail_on_blocker and report["blockers"]:
        raise SystemExit("; ".join(report["blockers"]))


def build_plan(
    *,
    oracle_json: dict[str, Any] | None,
    routes: dict[str, Path],
    route_buckets: dict[str, list[str]],
    output_root: Path,
    output_manifest: Path,
    diffusion_repo: Path,
    map_path: str | None,
    model_path: Path,
    model_args: Path | None,
    config: Path,
    reward_config: Path,
    camp_atom_scales: Path,
    camp_static_weights: Path,
    device: str,
    steps: int,
    seeds: list[int],
    max_npcs: list[int],
    spawn_probabilities: list[float],
    traffic_light_modes: list[str],
    num_candidates: int = 8,
    candidate_noise_scale: float = 1.0,
    candidate_reference_blend_steps: int = 5,
    camp_min_progress_ratio: float = 0.8,
    camp_reward_horizon_steps: int = 30,
    camp_outcome_horizon_steps: int = 30,
    near_miss_threshold_m: float = 2.0,
    npc_interaction_min_npcs: int = 8,
    npc_interaction_min_spawn: float = 0.5,
    dense_scene_min_npcs: int = 8,
    dense_scene_min_spawn: float = 0.6,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
    require_route_files: bool = False,
) -> dict[str, Any]:
    _validate_inputs(
        routes=routes,
        route_buckets=route_buckets,
        seeds=seeds,
        max_npcs=max_npcs,
        spawn_probabilities=spawn_probabilities,
        traffic_light_modes=traffic_light_modes,
        required_buckets=required_buckets,
    )
    manifest = _scenario_manifest(
        routes=routes,
        route_buckets=route_buckets,
        max_npcs=max_npcs,
        spawn_probabilities=spawn_probabilities,
        npc_interaction_min_npcs=npc_interaction_min_npcs,
        npc_interaction_min_spawn=npc_interaction_min_spawn,
        dense_scene_min_npcs=dense_scene_min_npcs,
        dense_scene_min_spawn=dense_scene_min_spawn,
    )
    scenario_rows = _planned_rows(
        routes=routes,
        seeds=seeds,
        max_npcs=max_npcs,
        spawn_probabilities=spawn_probabilities,
        traffic_light_modes=traffic_light_modes,
        steps=steps,
        manifest=manifest,
    )
    bucket_counts = _bucket_counts(scenario_rows)
    missing = [bucket for bucket in required_buckets if bucket_counts.get(bucket, 0) == 0]
    blockers = []
    if missing:
        blockers.append(
            "missing required planned scenario buckets: " + ", ".join(missing)
        )
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    if formal:
        blockers.append(f"formal seeds are forbidden: {formal}")
    if require_route_files:
        missing_routes = sorted(
            f"{name}={path}" for name, path in routes.items() if not path.is_file()
        )
        if missing_routes:
            blockers.append("missing route files: " + ", ".join(missing_routes))
    command = _matrix_command(
        routes=routes,
        output_root=output_root,
        output_manifest=output_manifest,
        diffusion_repo=diffusion_repo,
        map_path=map_path,
        model_path=model_path,
        model_args=model_args,
        config=config,
        reward_config=reward_config,
        camp_atom_scales=camp_atom_scales,
        camp_static_weights=camp_static_weights,
        device=device,
        steps=steps,
        seeds=seeds,
        max_npcs=max_npcs,
        spawn_probabilities=spawn_probabilities,
        traffic_light_modes=traffic_light_modes,
        num_candidates=num_candidates,
        candidate_noise_scale=candidate_noise_scale,
        candidate_reference_blend_steps=candidate_reference_blend_steps,
        camp_min_progress_ratio=camp_min_progress_ratio,
        camp_reward_horizon_steps=camp_reward_horizon_steps,
        camp_outcome_horizon_steps=camp_outcome_horizon_steps,
        near_miss_threshold_m=near_miss_threshold_m,
    )
    return {
        "analysis": {
            "name": "dp_camp_diverse_nonformal_matrix_plan_v1",
            "role": "predeclared plan for non-formal scenario coverage expansion",
            "runs_dp": False,
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "formal_seeds": False,
            "explicit_labeling_only": True,
            "labels_are_not_inferred_from_metrics": True,
            "oracle_gate_source": _oracle_gate_summary(oracle_json),
            "math_boundary": (
                "Scenario labels and outcome collection are evaluation metadata "
                "only. They do not change DP, CAMP atoms, affine scores, or the "
                "simplex/CVaR/L2 master."
            ),
        },
        "summary": {
            "route_count": len(routes),
            "planned_run_count": len(scenario_rows),
            "seeds": sorted(seeds),
            "max_npcs": sorted(max_npcs),
            "spawn_probabilities": sorted(spawn_probabilities),
            "traffic_light_modes": sorted(traffic_light_modes),
            "steps": int(steps),
            "num_candidates": int(num_candidates),
            "candidate_noise_scale": float(candidate_noise_scale),
            "candidate_reference_blend_steps": int(candidate_reference_blend_steps),
            "outcome_horizon_steps": int(camp_outcome_horizon_steps),
            "bucket_counts": bucket_counts,
            "required_buckets": list(required_buckets),
            "missing_required_buckets": missing,
            "blocker_count": len(blockers),
        },
        "routes": {
            name: {
                "path": str(path),
                "declared_buckets": route_buckets.get(name, []),
            }
            for name, path in sorted(routes.items())
        },
        "scenario_bucket_manifest": manifest,
        "planned_rows_preview": scenario_rows[:20],
        "planned_rows_truncated": len(scenario_rows) > 20,
        "command": {
            "argv": command,
            "shell": shlex.join(command),
        },
        "post_run_gates": [
            "audit_diffusion_planner_camp_dataset.py with forbidden seeds 11/12/13",
            "audit_diffusion_planner_candidate_availability_inputs.py with --fail_on_not_ready",
            "analyze_diffusion_planner_safety_cost_oracle.py with --fail_on_formal_seeds",
            "do not use outcome-label collection latency as deployable latency",
            "do not train CAMP unless hard-guarded oracle opportunity passes required buckets",
        ],
        "blockers": blockers,
        "decision": (
            "approved_nonformal_plan_only" if not blockers else "blocked_plan_only"
        ),
    }


def _scenario_manifest(
    *,
    routes: dict[str, Path],
    route_buckets: dict[str, list[str]],
    max_npcs: list[int],
    spawn_probabilities: list[float],
    npc_interaction_min_npcs: int,
    npc_interaction_min_spawn: float,
    dense_scene_min_npcs: int,
    dense_scene_min_spawn: float,
) -> dict[str, Any]:
    manifest_routes: dict[str, list[str]] = {}
    filters: list[dict[str, Any]] = []
    npc_values = [value for value in sorted(max_npcs) if value >= npc_interaction_min_npcs]
    npc_spawns = [
        value for value in sorted(spawn_probabilities) if value >= npc_interaction_min_spawn
    ]
    dense_values = [value for value in sorted(max_npcs) if value >= dense_scene_min_npcs]
    dense_spawns = [
        value for value in sorted(spawn_probabilities) if value >= dense_scene_min_spawn
    ]
    for route_name in sorted(routes):
        buckets = route_buckets.get(route_name, [])
        wide = sorted(bucket for bucket in buckets if bucket in ROUTE_WIDE_BUCKETS)
        if wide:
            manifest_routes[route_name] = wide
        tl_buckets = [bucket for bucket in buckets if bucket in TRAFFIC_LIGHT_BUCKETS]
        if tl_buckets:
            filters.append(
                {
                    "name": f"{route_name}_traffic_light_on",
                    "match": {"route_name": route_name, "traffic_lights": True},
                    "buckets": tl_buckets,
                }
            )
        if "normal" in buckets:
            filters.append(
                {
                    "name": f"{route_name}_normal_no_tl_no_npc",
                    "match": {
                        "route_name": route_name,
                        "traffic_lights": False,
                        "max_npcs": 0,
                    },
                    "buckets": ["normal"],
                }
            )
        if ("npc_interaction" in buckets or "dense_scene" in buckets) and npc_values and npc_spawns:
            filter_buckets = []
            if "npc_interaction" in buckets:
                filter_buckets.append("npc_interaction")
            if "dense_scene" in buckets and dense_values and dense_spawns:
                filter_buckets.append("dense_scene")
            if filter_buckets:
                match: dict[str, Any] = {
                    "route_name": route_name,
                    "max_npcs": dense_values if "dense_scene" in filter_buckets else npc_values,
                    "spawn_probability": (
                        dense_spawns if "dense_scene" in filter_buckets else npc_spawns
                    ),
                }
                filters.append(
                    {
                        "name": f"{route_name}_npc_stress",
                        "match": match,
                        "buckets": filter_buckets,
                    }
                )
    return {
        "metadata": {
            "schema_version": "dp_camp_scenario_buckets_v1",
            "purpose": (
                "Generated predeclared non-formal scenario labels for a "
                "DP-CAMP diverse candidate-branch oracle matrix."
            ),
            "development_only": True,
            "labeling_rule": (
                "Labels come only from route declarations and run configuration "
                "fields. Do not infer labels from SafetyCost, collisions, red "
                "lights, completion, jerk, latency, or other replay outcomes."
            ),
        },
        "supported_buckets": sorted(SUPPORTED_BUCKETS),
        "routes": manifest_routes,
        "run_keys": {},
        "filters": filters,
        "default_buckets": [],
    }


def _planned_rows(
    *,
    routes: dict[str, Path],
    seeds: list[int],
    max_npcs: list[int],
    spawn_probabilities: list[float],
    traffic_light_modes: list[str],
    steps: int,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for route_name, seed, npc, spawn, tl in product(
        sorted(routes),
        sorted(seeds),
        sorted(max_npcs),
        sorted(spawn_probabilities),
        sorted(traffic_light_modes),
    ):
        row = {
            "route_name": route_name,
            "route": str(routes[route_name]),
            "seed": int(seed),
            "steps": int(steps),
            "max_npcs": int(npc),
            "spawn_probability": float(spawn),
            "traffic_lights": tl == "on",
            "advance_mode": "perfect",
        }
        row["scenario_buckets"] = _scenario_buckets(row, manifest)
        rows.append(row)
    return rows


def _scenario_buckets(row: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    buckets = ["overall"]
    route_name = str(row["route_name"])
    for bucket in manifest.get("routes", {}).get(route_name, []):
        if bucket not in buckets:
            buckets.append(bucket)
    for entry in manifest.get("filters", []):
        if _filter_matches(row, entry.get("match", {})):
            for bucket in entry.get("buckets", []):
                if bucket not in buckets:
                    buckets.append(bucket)
    return buckets


def _filter_matches(row: dict[str, Any], match: dict[str, Any]) -> bool:
    return all(_matches(row.get(field), expected) for field, expected in match.items())


def _matches(actual: Any, expected: Any) -> bool:
    values = expected if isinstance(expected, list) else [expected]
    return any(_scalar_matches(actual, value) for value in values)


def _scalar_matches(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= 1e-9
    return str(actual) == str(expected)


def _bucket_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {bucket: 0 for bucket in sorted(SUPPORTED_BUCKETS)}
    for row in rows:
        for bucket in row["scenario_buckets"]:
            counts[bucket] = counts.get(bucket, 0) + 1
    return {bucket: counts[bucket] for bucket in sorted(counts) if counts[bucket]}


def _matrix_command(
    *,
    routes: dict[str, Path],
    output_root: Path,
    output_manifest: Path,
    diffusion_repo: Path,
    map_path: str | None,
    model_path: Path,
    model_args: Path | None,
    config: Path,
    reward_config: Path,
    camp_atom_scales: Path,
    camp_static_weights: Path,
    device: str,
    steps: int,
    seeds: list[int],
    max_npcs: list[int],
    spawn_probabilities: list[float],
    traffic_light_modes: list[str],
    num_candidates: int,
    candidate_noise_scale: float,
    candidate_reference_blend_steps: int,
    camp_min_progress_ratio: float,
    camp_reward_horizon_steps: int,
    camp_outcome_horizon_steps: int,
    near_miss_threshold_m: float,
) -> list[str]:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--diffusion_repo",
        str(diffusion_repo),
        "--model_path",
        str(model_path),
        "--config",
        str(config),
        "--output_root",
        str(output_root),
        "--device",
        device,
        "--steps",
        str(steps),
        "--seeds",
        ",".join(str(value) for value in sorted(seeds)),
        "--max_npcs",
        ",".join(str(value) for value in sorted(max_npcs)),
        "--spawn_probabilities",
        ",".join(_fmt_float(value) for value in sorted(spawn_probabilities)),
        "--traffic_light_modes",
        ",".join(sorted(traffic_light_modes)),
        "--reward_config",
        str(reward_config),
        "--camp_atom_scales",
        str(camp_atom_scales),
        "--camp_static_weights",
        str(camp_static_weights),
        "--num_candidates",
        str(num_candidates),
        "--candidate_noise_scale",
        _fmt_float(candidate_noise_scale),
        "--candidate_reference_blend_steps",
        str(candidate_reference_blend_steps),
        "--camp_feasibility_source",
        "dp_reward",
        "--camp_min_progress_ratio",
        _fmt_float(camp_min_progress_ratio),
        "--camp_reward_horizon_steps",
        str(camp_reward_horizon_steps),
        "--camp_collect_closed_loop_outcomes",
        "--camp_outcome_horizon_steps",
        str(camp_outcome_horizon_steps),
        "--near_miss_threshold_m",
        _fmt_float(near_miss_threshold_m),
        "--variants",
        "static",
        "--skip_compare",
        "--scenario_bucket_manifest",
        str(output_manifest),
    ]
    if map_path is not None:
        cmd.extend(["--map_path", map_path])
    if model_args is not None:
        cmd.extend(["--model_args", str(model_args)])
    for name, path in sorted(routes.items()):
        cmd.extend(["--route", f"{name}={path}"])
    return cmd


def _validate_inputs(
    *,
    routes: dict[str, Path],
    route_buckets: dict[str, list[str]],
    seeds: list[int],
    max_npcs: list[int],
    spawn_probabilities: list[float],
    traffic_light_modes: list[str],
    required_buckets: tuple[str, ...],
) -> None:
    if not routes:
        raise ValueError("At least one route is required.")
    unknown_routes = sorted(set(route_buckets) - set(routes))
    if unknown_routes:
        raise ValueError(f"route_bucket references unknown route(s): {unknown_routes}")
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    if formal:
        raise ValueError(f"formal seeds are forbidden: {formal}")
    if not max_npcs or any(value < 0 for value in max_npcs):
        raise ValueError("max_npcs must contain nonnegative integers.")
    if not spawn_probabilities or any(value < 0.0 for value in spawn_probabilities):
        raise ValueError("spawn_probabilities must contain nonnegative floats.")
    if sorted(set(traffic_light_modes) - {"on", "off"}):
        raise ValueError("traffic_light_modes must contain only on/off.")
    invalid = sorted(set(required_buckets) - (SUPPORTED_BUCKETS - {"overall"}))
    if invalid:
        raise ValueError(f"unsupported required bucket(s): {invalid}")


def _route_bucket_map(items: list[tuple[str, list[str]]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, buckets in items:
        if not name:
            raise ValueError("route_bucket route name must not be empty.")
        existing = result.setdefault(name, [])
        for bucket in buckets:
            if bucket not in existing:
                existing.append(bucket)
    return result


def _required_buckets_from_oracle(path: Path | None) -> tuple[str, ...]:
    payload = _read_json_if_exists(path)
    if payload:
        required = payload.get("coverage_gaps", {}).get("required_buckets")
        if isinstance(required, list) and required:
            return tuple(str(bucket) for bucket in required)
    return DEFAULT_REQUIRED_BUCKETS


def _oracle_gate_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    gate = payload.get("opportunity_gate", {})
    coverage = payload.get("coverage_gaps", {})
    return {
        "passed": gate.get("passed"),
        "missing_required_buckets": coverage.get("missing_required_buckets"),
        "overall_ci_high": (
            payload.get("overall", {})
            .get("run_level_delta_ci", {})
            .get("hard_guarded_oracle_minus_top1", {})
            .get("ci95_high")
        ),
    }


def _read_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# DP-CAMP Diverse Non-Formal Matrix Plan",
        "",
        "This is a plan-only artifact. It does not run DP, train CAMP, alter the "
        "online selector, or modify Diffusion Planner.",
        "",
        f"- Planned runs: `{summary['planned_run_count']}`",
        f"- Routes: `{summary['route_count']}`",
        f"- Required buckets: `{', '.join(summary['required_buckets'])}`",
        f"- Missing required buckets: `{', '.join(summary['missing_required_buckets']) or 'none'}`",
        f"- Decision: `{report['decision']}`",
        "",
        "## Bucket Counts",
        "",
        "| Bucket | Planned rows |",
        "| --- | ---: |",
    ]
    for bucket, count in summary["bucket_counts"].items():
        lines.append(f"| `{bucket}` | {count} |")
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    if report["blockers"]:
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Command",
            "",
            "```bash",
            report["command"]["shell"],
            "```",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def _fmt_float(value: float) -> str:
    text = f"{float(value):.12g}"
    return "0" if text == "-0" else text


if __name__ == "__main__":
    main()
