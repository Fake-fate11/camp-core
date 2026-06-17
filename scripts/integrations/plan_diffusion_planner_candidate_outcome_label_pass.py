#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_benchmark_matrix.py"
FORMAL_SEEDS = {11, 12, 13}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a non-formal DP-CAMP candidate outcome-label replay pass "
            "from an existing paired comparison JSON. This emits commands and "
            "gates only; it does not run DP."
        )
    )
    parser.add_argument("--comparison_json", type=Path, required=True)
    parser.add_argument("--source_variant", type=str, required=True)
    parser.add_argument("--label_output_root", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, default=None)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--camp_atom_scales", type=Path, required=True)
    parser.add_argument("--camp_static_weights", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument("--camp_fallback_mode", default="uniform")
    parser.add_argument("--camp_feasibility_source", default="dp_reward")
    parser.add_argument("--camp_min_progress_ratio", type=float, default=0.8)
    parser.add_argument("--camp_reward_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_outcome_horizon_steps", type=int, default=30)
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = _read_json(args.comparison_json)
    report = build_plan(
        comparison,
        source_variant=args.source_variant,
        comparison_path=args.comparison_json,
        label_output_root=args.label_output_root,
        diffusion_repo=args.diffusion_repo,
        map_path=args.map_path,
        model_path=args.model_path,
        model_args=args.model_args,
        config=args.config,
        reward_config=args.reward_config,
        camp_atom_scales=args.camp_atom_scales,
        camp_static_weights=args.camp_static_weights,
        device=args.device,
        num_candidates=args.num_candidates,
        candidate_noise_scale=args.candidate_noise_scale,
        camp_fallback_mode=args.camp_fallback_mode,
        camp_feasibility_source=args.camp_feasibility_source,
        camp_min_progress_ratio=args.camp_min_progress_ratio,
        camp_reward_horizon_steps=args.camp_reward_horizon_steps,
        camp_outcome_horizon_steps=args.camp_outcome_horizon_steps,
        near_miss_threshold_m=args.near_miss_threshold_m,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))


def build_plan(
    comparison: dict[str, Any],
    *,
    source_variant: str,
    comparison_path: Path | None = None,
    label_output_root: Path,
    diffusion_repo: Path,
    map_path: str | None,
    model_path: Path,
    model_args: Path | None,
    config: Path,
    reward_config: Path,
    camp_atom_scales: Path,
    camp_static_weights: Path,
    device: str = "cuda",
    num_candidates: int = 8,
    candidate_noise_scale: float = 1.0,
    camp_fallback_mode: str = "uniform",
    camp_feasibility_source: str = "dp_reward",
    camp_min_progress_ratio: float = 0.8,
    camp_reward_horizon_steps: int = 30,
    camp_outcome_horizon_steps: int = 30,
    near_miss_threshold_m: float = 2.0,
) -> dict[str, Any]:
    rows = comparison.get("runs")
    if not isinstance(rows, list) or not rows:
        raise ValueError("comparison JSON must contain a nonempty runs list.")
    source_rows = [row for row in rows if row.get("variant") == source_variant]
    if not source_rows:
        raise ValueError(f"source variant {source_variant!r} is not present.")
    scenarios = _unique_scenarios(source_rows)
    _validate_scenarios(scenarios, source_variant)
    grid = _grid(scenarios)
    command = _matrix_command(
        grid,
        label_output_root=label_output_root,
        diffusion_repo=diffusion_repo,
        map_path=map_path,
        model_path=model_path,
        model_args=model_args,
        config=config,
        reward_config=reward_config,
        camp_atom_scales=camp_atom_scales,
        camp_static_weights=camp_static_weights,
        device=device,
        num_candidates=num_candidates,
        candidate_noise_scale=candidate_noise_scale,
        camp_fallback_mode=camp_fallback_mode,
        camp_feasibility_source=camp_feasibility_source,
        camp_min_progress_ratio=camp_min_progress_ratio,
        camp_reward_horizon_steps=camp_reward_horizon_steps,
        camp_outcome_horizon_steps=camp_outcome_horizon_steps,
        near_miss_threshold_m=near_miss_threshold_m,
    )
    return {
        "analysis": {
            "name": "dp_camp_candidate_outcome_label_pass_plan_v1",
            "comparison_json": None if comparison_path is None else str(comparison_path),
            "source_variant": source_variant,
            "training": False,
            "online_selector_change": False,
            "dp_modification": False,
            "formal_seeds": False,
            "runs_dp": False,
            "future_outcome_leakage": (
                "the planned pass collects candidate outcomes as offline labels "
                "only; labels must not be used by the online selector"
            ),
            "convexity_boundary": (
                "candidate outcomes are fixed labels after collection and are "
                "outside the finite-candidate Benders-style master"
            ),
        },
        "summary": {
            "source_variant": source_variant,
            "scenario_count": len(scenarios),
            "route_count": len(grid["routes"]),
            "seeds": grid["seeds"],
            "max_npcs": grid["max_npcs"],
            "spawn_probabilities": grid["spawn_probabilities"],
            "traffic_light_modes": grid["traffic_light_modes"],
            "steps": grid["steps"],
            "advance_mode": grid["advance_mode"],
            "num_candidates": int(num_candidates),
            "candidate_noise_scale": float(candidate_noise_scale),
            "outcome_horizon_steps": int(camp_outcome_horizon_steps),
        },
        "scenario_grid": grid,
        "command": {
            "argv": command,
            "shell": shlex.join(command),
        },
        "post_run_gates": [
            "run audit_diffusion_planner_candidate_availability_inputs.py and require candidate_availability_oracle_ready=true",
            "run audit_diffusion_planner_camp_dataset.py with closed_loop_outcome_policy=required and forbidden seeds 11/12/13",
            "run analyze_diffusion_planner_candidate_availability.py on the label-pass logs",
            "do not use label-pass latency as deployable latency because outcome collection is offline",
            "do not claim CAMP improvement without paired SafetyCost v1 hard-gate evidence",
        ],
        "decision": (
            "approved_plan_only; run this non-formal label pass only after "
            "asset paths are verified on AutoDL"
        ),
    }


def _unique_scenarios(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        scenario = {
            "route_name": str(row.get("route_name") or Path(str(row["route"])).stem),
            "route": str(row.get("route")),
            "seed": int(row.get("seed")),
            "steps": int(row.get("steps")),
            "max_npcs": int(row.get("max_npcs")),
            "spawn_probability": float(row.get("spawn_probability")),
            "traffic_lights": bool(row.get("traffic_lights")),
            "advance_mode": str(row.get("advance_mode")),
        }
        key = tuple(scenario[field] for field in scenario)
        previous = by_key.get(key)
        if previous is not None and previous != scenario:
            raise ValueError(f"Conflicting scenario rows for {key}.")
        by_key[key] = scenario
    return [by_key[key] for key in sorted(by_key)]


def _validate_scenarios(scenarios: list[dict[str, Any]], source_variant: str) -> None:
    if not scenarios:
        raise ValueError(f"{source_variant} has no scenarios.")
    formal = sorted({row["seed"] for row in scenarios if row["seed"] in FORMAL_SEEDS})
    if formal:
        raise ValueError(f"formal seeds are forbidden in label-pass plans: {formal}.")
    if len({row["steps"] for row in scenarios}) != 1:
        raise ValueError("label-pass planner requires one shared step count.")
    if len({row["advance_mode"] for row in scenarios}) != 1:
        raise ValueError("label-pass planner requires one shared advance_mode.")
    if any(row["advance_mode"] != "perfect" for row in scenarios):
        raise ValueError("candidate outcome label pass requires perfect tracking.")


def _grid(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    routes: dict[str, str] = {}
    for row in scenarios:
        existing = routes.get(row["route_name"])
        if existing is not None and existing != row["route"]:
            raise ValueError(f"Route name {row['route_name']} maps to multiple paths.")
        routes[row["route_name"]] = row["route"]
    return {
        "routes": dict(sorted(routes.items())),
        "seeds": sorted({int(row["seed"]) for row in scenarios}),
        "max_npcs": sorted({int(row["max_npcs"]) for row in scenarios}),
        "spawn_probabilities": sorted({float(row["spawn_probability"]) for row in scenarios}),
        "traffic_light_modes": sorted(
            {"on" if row["traffic_lights"] else "off" for row in scenarios}
        ),
        "steps": int(scenarios[0]["steps"]),
        "advance_mode": str(scenarios[0]["advance_mode"]),
    }


def _matrix_command(
    grid: dict[str, Any],
    *,
    label_output_root: Path,
    diffusion_repo: Path,
    map_path: str | None,
    model_path: Path,
    model_args: Path | None,
    config: Path,
    reward_config: Path,
    camp_atom_scales: Path,
    camp_static_weights: Path,
    device: str,
    num_candidates: int,
    candidate_noise_scale: float,
    camp_fallback_mode: str,
    camp_feasibility_source: str,
    camp_min_progress_ratio: float,
    camp_reward_horizon_steps: int,
    camp_outcome_horizon_steps: int,
    near_miss_threshold_m: float,
) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--diffusion_repo",
        str(diffusion_repo),
        "--model_path",
        str(model_path),
        "--config",
        str(config),
        "--output_root",
        str(label_output_root),
        "--device",
        str(device),
        "--advance_mode",
        str(grid["advance_mode"]),
        "--steps",
        str(grid["steps"]),
        "--seeds",
        _csv(grid["seeds"]),
        "--max_npcs",
        _csv(grid["max_npcs"]),
        "--spawn_probabilities",
        _csv(grid["spawn_probabilities"]),
        "--traffic_light_modes",
        ",".join(grid["traffic_light_modes"]),
        "--reward_config",
        str(reward_config),
        "--camp_atom_scales",
        str(camp_atom_scales),
        "--camp_static_weights",
        str(camp_static_weights),
        "--num_candidates",
        str(num_candidates),
        "--candidate_noise_scale",
        str(candidate_noise_scale),
        "--camp_feasibility_source",
        str(camp_feasibility_source),
        "--camp_fallback_mode",
        str(camp_fallback_mode),
        "--camp_min_progress_ratio",
        str(camp_min_progress_ratio),
        "--camp_reward_horizon_steps",
        str(camp_reward_horizon_steps),
        "--camp_collect_closed_loop_outcomes",
        "--camp_outcome_horizon_steps",
        str(camp_outcome_horizon_steps),
        "--near_miss_threshold_m",
        str(near_miss_threshold_m),
        "--variants",
        "static",
        "--skip_compare",
    ]
    if map_path is not None:
        command.extend(["--map_path", str(map_path)])
    if model_args is not None:
        command.extend(["--model_args", str(model_args)])
    for route_name, route_path in grid["routes"].items():
        command.extend(["--route", f"{route_name}={route_path}"])
    return command


def _csv(values: list[Any]) -> str:
    return ",".join(str(value) for value in values)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Candidate Outcome Label Pass Plan",
        "",
        "This is a command plan only. It does not run DP and does not authorize "
        "formal seeds or online use of candidate outcome labels.",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(report["summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Command",
        "",
        "```bash",
        report["command"]["shell"],
        "```",
        "",
        "## Post-Run Gates",
        "",
    ]
    lines.extend(f"- {gate}" for gate in report["post_run_gates"])
    lines.extend(["", f"Decision: `{report['decision']}`", ""])
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
