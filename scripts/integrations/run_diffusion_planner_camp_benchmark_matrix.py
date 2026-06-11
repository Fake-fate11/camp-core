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
    parser.add_argument("--camp_static_weights", type=Path, required=True)
    parser.add_argument("--camp_theta_checkpoint", type=Path, required=True)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
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
            ]
        )
    if variant == "static":
        cmd.extend(["--camp_static_weights", str(args.camp_static_weights)])
    elif variant == "theta":
        cmd.extend(["--camp_checkpoint", str(args.camp_theta_checkpoint)])
    return cmd


def main() -> None:
    args = parse_args()
    variants = ("top1", "uniform", "static", "theta")
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
