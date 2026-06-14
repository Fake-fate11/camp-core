from __future__ import annotations

import argparse
import os
import subprocess
import sys
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
COMPARE = ROOT / "scripts" / "integrations" / "compare_diffusion_planner_camp_replays.py"


def _parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("route must have the form NAME=/path/route.pkl")
    name, path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("route name must not be empty")
    return name, Path(path)


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_traffic_light_modes(value: str) -> list[str]:
    modes = [part.strip() for part in value.split(",") if part.strip()]
    invalid = [mode for mode in modes if mode not in {"on", "off"}]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"traffic light modes must be on/off, got {invalid}"
        )
    return modes


def _parse_variants(value: str) -> list[str]:
    variants = [part.strip() for part in value.split(",") if part.strip()]
    valid = {"top1", "uniform", "static", "theta"}
    invalid = [variant for variant in variants if variant not in valid]
    if invalid or not variants:
        raise argparse.ArgumentTypeError(
            f"variants must be a non-empty subset of {sorted(valid)}, got {variants}"
        )
    return variants


def _spawn_tag(value: float) -> str:
    return str(value).replace(".", "p")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the matched Diffusion-Planner benchmark matrix: original "
            "DP Top-1, uniform CAMP, static CAMP, and scene-conditioned Theta."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument(
        "--route",
        action="append",
        type=_parse_named_path,
        required=True,
        help="NAME=/path/to/route.pkl. Repeat for each route.",
    )
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, default=None)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument(
        "--advance_mode",
        choices=("perfect", "mpc", "teleport"),
        default="perfect",
        help="Closed-loop tracker. Formal DP+CAMP matrices default to perfect.",
    )
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seeds", type=_parse_int_list, required=True)
    parser.add_argument("--max_npcs", type=_parse_int_list, required=True)
    parser.add_argument("--spawn_probabilities", type=_parse_float_list, required=True)
    parser.add_argument(
        "--traffic_light_modes",
        type=_parse_traffic_light_modes,
        default=["on"],
        help="Comma-separated on/off modes. Seeds vary enabled-light phases.",
    )
    parser.add_argument(
        "--reward_config",
        type=Path,
        default=None,
        help="Full reward JSON used for in-memory lane/red-light plan metrics.",
    )
    parser.add_argument("--camp_atom_scales", type=Path, required=True)
    parser.add_argument("--camp_static_weights", type=Path, default=None)
    parser.add_argument("--camp_theta_checkpoint", type=Path, default=None)
    parser.add_argument("--camp_fallback_atom_scales", type=Path, default=None)
    parser.add_argument("--camp_fallback_static_weights", type=Path, default=None)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument(
        "--candidate_reference_blend_steps",
        type=int,
        default=None,
    )
    parser.add_argument("--camp_lane_corridor_buffer", type=float, default=1.0)
    parser.add_argument(
        "--camp_feasibility_source",
        choices=("context", "dp_reward"),
        default="dp_reward",
    )
    parser.add_argument(
        "--camp_fallback_mode",
        choices=("uniform", "learned"),
        default="uniform",
        help="Fallback policy for all-infeasible CAMP candidate sets.",
    )
    parser.add_argument("--camp_min_progress_ratio", type=float, default=0.8)
    parser.add_argument(
        "--camp_min_candidate0_progress_ratio",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--camp_min_candidate0_route_progress_ratio",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--camp_min_candidate0_step_reach_ratio",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--camp_candidate0_step_reach_preserve_feasible",
        action="store_true",
    )
    parser.add_argument(
        "--camp_lexicographic_progress_epsilon_m",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--camp_lexicographic_red_epsilon",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--camp_lexicographic_jerk_epsilon",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--camp_lexicographic_lateral_epsilon",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--camp_perfect_tracker_command_postselection",
        action="store_true",
    )
    parser.add_argument("--camp_underprogress_relaxation", action="store_true")
    parser.add_argument(
        "--camp_underprogress_progress_loss_budget_m",
        type=float,
        default=1.5,
    )
    parser.add_argument(
        "--camp_underprogress_h3_distance_loss_budget_m",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--camp_underprogress_lateral_limit_mps2",
        type=float,
        default=2.0,
    )
    parser.add_argument("--camp_reward_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_collect_closed_loop_outcomes", action="store_true")
    parser.add_argument("--camp_outcome_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_outcome_progress_weight", type=float, default=1.0)
    parser.add_argument("--camp_outcome_collision_penalty", type=float, default=100.0)
    parser.add_argument("--camp_outcome_near_miss_penalty", type=float, default=10.0)
    parser.add_argument("--camp_outcome_lane_penalty", type=float, default=20.0)
    parser.add_argument("--camp_outcome_red_light_penalty", type=float, default=30.0)
    parser.add_argument("--camp_outcome_jerk_penalty", type=float, default=0.25)
    parser.add_argument(
        "--camp_outcome_lateral_acceleration_penalty",
        type=float,
        default=1.0,
    )
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    parser.add_argument(
        "--variants",
        type=_parse_variants,
        default=["top1", "uniform", "static", "theta"],
        help="Comma-separated subset of top1,uniform,static,theta.",
    )
    parser.add_argument(
        "--skip_compare",
        action="store_true",
        help="Skip aggregate comparison, for example during uniform-only collection.",
    )
    parser.add_argument(
        "--render_png",
        action="store_true",
        help="Render per-step PNGs. By default REPLAY_NO_PNG=1 is set.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip runs that already contain camp_validation_summary.json.",
    )
    parser.add_argument("--dry_run", action="store_true")
    return parser.parse_args()


def _append_common(cmd: list[str], args: argparse.Namespace, route: Path) -> None:
    cmd.extend(
        [
            "--diffusion_repo",
            str(args.diffusion_repo),
            "--route",
            str(route),
            "--model_path",
            str(args.model_path),
            "--config",
            str(args.config),
            "--device",
            args.device,
            "--advance_mode",
            args.advance_mode,
            "--near_miss_threshold_m",
            str(args.near_miss_threshold_m),
        ]
    )
    if args.map_path is not None:
        cmd.extend(["--map_path", args.map_path])
    if args.model_args is not None:
        cmd.extend(["--model_args", str(args.model_args)])
    if args.steps is not None:
        cmd.extend(["--steps", str(args.steps)])
    if args.reward_config is not None:
        cmd.extend(["--reward_config", str(args.reward_config)])


def _variant_command(
    *,
    variant: str,
    output_dir: Path,
    route: Path,
    seed: int,
    max_npcs: int,
    spawn_probability: float,
    traffic_lights: str,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [sys.executable, str(RUNNER)]
    _append_common(cmd, args, route)
    cmd.extend(
        [
            "--output_dir",
            str(output_dir),
            "--seed",
            str(seed),
            "--max_npcs",
            str(max_npcs),
            "--spawn_probability",
            str(spawn_probability),
            "--traffic_lights",
            traffic_lights,
            "--camp_selector_mode",
            "linear" if variant == "theta" else variant,
        ]
    )
    if variant != "top1":
        cmd.extend(
            [
                "--camp_atom_scales",
                str(args.camp_atom_scales),
                "--num_candidates",
                str(args.num_candidates),
                "--candidate_noise_scale",
                str(args.candidate_noise_scale),
                "--camp_lane_corridor_buffer",
                str(args.camp_lane_corridor_buffer),
                "--camp_feasibility_source",
                args.camp_feasibility_source,
                "--camp_fallback_mode",
                args.camp_fallback_mode,
                "--camp_min_progress_ratio",
                str(args.camp_min_progress_ratio),
                "--camp_reward_horizon_steps",
                str(args.camp_reward_horizon_steps),
            ]
        )
        if args.candidate_reference_blend_steps is not None:
            cmd.extend(
                [
                    "--candidate_reference_blend_steps",
                    str(args.candidate_reference_blend_steps),
                ]
            )
        if args.camp_min_candidate0_progress_ratio is not None:
            cmd.extend(
                [
                    "--camp_min_candidate0_progress_ratio",
                    str(args.camp_min_candidate0_progress_ratio),
                ]
            )
        if args.camp_min_candidate0_route_progress_ratio is not None:
            cmd.extend(
                [
                    "--camp_min_candidate0_route_progress_ratio",
                    str(args.camp_min_candidate0_route_progress_ratio),
                ]
            )
        if args.camp_min_candidate0_step_reach_ratio is not None:
            cmd.extend(
                [
                    "--camp_min_candidate0_step_reach_ratio",
                    str(args.camp_min_candidate0_step_reach_ratio),
                ]
            )
            if args.camp_candidate0_step_reach_preserve_feasible:
                cmd.append("--camp_candidate0_step_reach_preserve_feasible")
        if args.camp_lexicographic_progress_epsilon_m is not None:
            cmd.extend(
                [
                    "--camp_lexicographic_progress_epsilon_m",
                    str(args.camp_lexicographic_progress_epsilon_m),
                    "--camp_lexicographic_red_epsilon",
                    str(args.camp_lexicographic_red_epsilon),
                    "--camp_lexicographic_jerk_epsilon",
                    str(args.camp_lexicographic_jerk_epsilon),
                    "--camp_lexicographic_lateral_epsilon",
                    str(args.camp_lexicographic_lateral_epsilon),
                ]
            )
        if args.camp_perfect_tracker_command_postselection:
            cmd.append("--camp_perfect_tracker_command_postselection")
        if args.camp_underprogress_relaxation:
            cmd.append("--camp_underprogress_relaxation")
            cmd.extend(
                [
                    "--camp_underprogress_progress_loss_budget_m",
                    str(args.camp_underprogress_progress_loss_budget_m),
                    "--camp_underprogress_h3_distance_loss_budget_m",
                    str(args.camp_underprogress_h3_distance_loss_budget_m),
                    "--camp_underprogress_lateral_limit_mps2",
                    str(args.camp_underprogress_lateral_limit_mps2),
                ]
            )
        if args.camp_collect_closed_loop_outcomes:
            cmd.append("--camp_collect_closed_loop_outcomes")
            cmd.extend(
                [
                    "--camp_outcome_horizon_steps",
                    str(args.camp_outcome_horizon_steps),
                    "--camp_outcome_progress_weight",
                    str(args.camp_outcome_progress_weight),
                    "--camp_outcome_collision_penalty",
                    str(args.camp_outcome_collision_penalty),
                    "--camp_outcome_near_miss_penalty",
                    str(args.camp_outcome_near_miss_penalty),
                    "--camp_outcome_lane_penalty",
                    str(args.camp_outcome_lane_penalty),
                    "--camp_outcome_red_light_penalty",
                    str(args.camp_outcome_red_light_penalty),
                    "--camp_outcome_jerk_penalty",
                    str(args.camp_outcome_jerk_penalty),
                    "--camp_outcome_lateral_acceleration_penalty",
                    str(args.camp_outcome_lateral_acceleration_penalty),
                ]
            )
        fallback_scales = getattr(args, "camp_fallback_atom_scales", None)
        fallback_weights = getattr(args, "camp_fallback_static_weights", None)
        if fallback_scales is not None:
            cmd.extend(
                ["--camp_fallback_atom_scales", str(fallback_scales)]
            )
        if fallback_weights is not None:
            cmd.extend(
                ["--camp_fallback_static_weights", str(fallback_weights)]
            )
    if variant == "static":
        cmd.extend(["--camp_static_weights", str(args.camp_static_weights)])
    elif variant == "theta":
        cmd.extend(["--camp_checkpoint", str(args.camp_theta_checkpoint)])
    return cmd


def main() -> None:
    args = parse_args()
    if args.camp_feasibility_source == "dp_reward" and args.reward_config is None:
        raise ValueError(
            "--camp_feasibility_source dp_reward requires --reward_config."
        )
    variants = tuple(args.variants)
    if "static" in variants and args.camp_static_weights is None:
        raise ValueError("The static variant requires --camp_static_weights.")
    if "theta" in variants and args.camp_theta_checkpoint is None:
        raise ValueError("The theta variant requires --camp_theta_checkpoint.")
    runs: list[tuple[str, Path]] = []
    env = os.environ.copy()
    if not args.render_png:
        env["REPLAY_NO_PNG"] = "1"

    for (
        (route_name, route_path),
        seed,
        max_npcs,
        spawn_probability,
        traffic_lights,
    ) in product(
        args.route,
        args.seeds,
        args.max_npcs,
        args.spawn_probabilities,
        args.traffic_light_modes,
    ):
        scenario_dir = (
            args.output_root
            / route_name
            / f"seed_{seed}"
            / f"npc_{max_npcs}"
            / f"spawn_{_spawn_tag(spawn_probability)}"
            / f"tl_{traffic_lights}"
        )
        for variant in variants:
            output_dir = scenario_dir / variant
            cmd = _variant_command(
                variant=variant,
                output_dir=output_dir,
                route=route_path,
                seed=seed,
                max_npcs=max_npcs,
                spawn_probability=spawn_probability,
                traffic_lights=traffic_lights,
                args=args,
            )
            print(" ".join(cmd), flush=True)
            completed = (output_dir / "camp_validation_summary.json").is_file()
            if args.resume and completed:
                print(f"SKIP completed {output_dir}", flush=True)
            elif not args.dry_run:
                subprocess.run(cmd, check=True, env=env)
            runs.append((variant, output_dir))

    if args.skip_compare:
        return
    if "top1" not in variants or len(variants) < 2:
        raise ValueError(
            "Comparison requires top1 plus at least one CAMP variant; "
            "otherwise pass --skip_compare."
        )

    compare_cmd = [sys.executable, str(COMPARE), "--baseline", "top1"]
    for variant, output_dir in runs:
        compare_cmd.extend(["--variant", f"{variant}={output_dir}"])
    compare_cmd.extend(
        [
            "--output_json",
            str(args.output_root / "benchmark_comparison.json"),
            "--output_markdown",
            str(args.output_root / "benchmark_comparison.md"),
        ]
    )
    print(" ".join(compare_cmd), flush=True)
    if not args.dry_run:
        subprocess.run(compare_cmd, check=True)


if __name__ == "__main__":
    main()
