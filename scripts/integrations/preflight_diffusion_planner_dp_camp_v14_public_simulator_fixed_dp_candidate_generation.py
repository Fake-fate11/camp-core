#!/usr/bin/env python3
"""V14 public-simulator fixed-DP candidate generation preflight.

This gate checks public simulator assets and emits a guarded runbook for a
future fixed Diffusion Planner candidate-generation execution. It does not run
Diffusion Planner, generate candidates, train CAMP, modify DP, promote,
deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
from pathlib import Path
from typing import Any, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = "dp_camp_v14_public_simulator_fixed_dp_candidate_generation_preflight_v1"
READY_STATUS = "public_simulator_fixed_dp_candidate_generation_preflight_ready"
REJECT_STATUS = "public_simulator_fixed_dp_candidate_generation_preflight_rejected"
CURRENT_V14_STATUS = "public_simulator_fixed_dp_candidate_source_available_preflight_required"
AUTHORIZED_CURRENT_WORK = "public_simulator_fixed_dp_candidate_generation_preflight"
AUTHORIZED_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_execution"
ZERO_OVERLAP_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation"
GUARD_ENV_VAR = "DP_CAMP_V14_PUBLIC_SIMULATOR_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
DEFAULT_ASSETS_DIR = Path("/root/autodl-tmp/camp_dp_assets")
DEFAULT_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
DEFAULT_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
DEFAULT_DP_PYTHON = Path("/root/autodl-tmp/dp312_venv/bin/python")
DEFAULT_NUSCENES_ROOT = Path("/autodl-pub/data/nuScenes")
REPLAY_SCRIPT = Path("scripts/integrations/run_diffusion_planner_camp_replay.py")
REWARD_CONFIG = Path("configs/integrations/dp_camp_reward_eval.json")
DP_REPLAY_CONFIG = Path("scenario_generation/configs/replay_default.json")
STATIC_WEIGHTS_REL = Path("camp_dp_static_calibration_v2/offline_weights_dp_static.npy")
ATOM_SCALES_REL = Path("camp_dp_static_calibration_v2/atom_scales_dp_static.json")
EXPECTED_STATIC_WEIGHTS_SHA256 = (
    "b8b29335eb9d2bc068376bc17fe5c89425eaf179fd6a0ac1b56138ce85de8041"
)
EXPECTED_ATOM_SCALES_SHA256 = (
    "434836eb901460dce7c65b736e55647185c474e7a4b0a15c882096819e53a7fd"
)
DEFAULT_STEPS = 100
DEFAULT_NUM_CANDIDATES = 8
DEFAULT_MAX_NPCS = 4
DEFAULT_SPAWN_PROBABILITY = 0.3
DEFAULT_SEEDS = (1, 2, 3, 4)
DEFAULT_TRAFFIC_LIGHT_MODES = ("on", "off")
FORMAL_SEEDS = {11, 12, 13}
FORBIDDEN_SNIPPETS = (
    "reference_blend",
    "guidance",
    "postprocess",
    "postselection",
    "splice",
    "repair",
    "rewrite",
    "closed_loop",
    "camp_collect_closed_loop_outcomes",
    "full36",
)
EXPECTED_PUBLIC_ASSETS = (
    {
        "name": "diffusion_planner_pth",
        "relative_path": "diffusion_planner.pth",
        "sha256": "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75",
    },
    {
        "name": "diffusion_planner_param_json",
        "relative_path": "diffusion_planner.param.json",
        "sha256": "ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268",
    },
    {
        "name": "sample_map_no_ros",
        "relative_path": "sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm",
        "sha256": "a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036",
    },
    {
        "name": "sample_tl_route",
        "relative_path": "sample_map_tl_route_59_to_86.pkl",
        "sha256": "dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4",
    },
    {
        "name": "sample_normal_route",
        "relative_path": "sample_map_route_2_to_104.pkl",
        "sha256": "489980fd79458695db68b30e91d4fcfc3efb80aca9e82ee9858a94cf2822ae35",
    },
    {
        "name": "nishishinjuku_no_ros",
        "relative_path": "nishishinjuku_no_ros.osm",
        "sha256": "bf1ff35bfb7562b6ab15e62b1ac55770bb84352b00af5204c3601bd47f079b81",
    },
    {
        "name": "nishishinjuku_release_route",
        "relative_path": "nishishinjuku_release_auto_route.pkl",
        "sha256": "fef5f2be64fb9d043d4cdf46672d28cf8d3445d67bb6b2c6c1bb7570621e4337",
    },
    {
        "name": "nishishinjuku_lane_change_route",
        "relative_path": "nishishinjuku_lane_change_route_7_via_8_to_1.pkl",
        "sha256": "4d03a3f99f3d39d51e53389064c83f2a942921b7ddea437c9ed3730ae0fd033b",
    },
)
ROUTE_SPECS = (
    {
        "name": "sample_normal",
        "route_relative_path": "sample_map_route_2_to_104.pkl",
        "map_relative_path": "sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm",
    },
    {
        "name": "sample_tl",
        "route_relative_path": "sample_map_tl_route_59_to_86.pkl",
        "map_relative_path": "sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm",
    },
    {
        "name": "nishi_release",
        "route_relative_path": "nishishinjuku_release_auto_route.pkl",
        "map_relative_path": "nishishinjuku_no_ros.osm",
    },
    {
        "name": "nishi_lane_change",
        "route_relative_path": "nishishinjuku_lane_change_route_7_via_8_to_1.pkl",
        "map_relative_path": "nishishinjuku_no_ros.osm",
    },
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument("--candidate_output_root", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=DEFAULT_DP_REPO)
    parser.add_argument("--camp_repo", type=Path, default=DEFAULT_CAMP_REPO)
    parser.add_argument("--assets_dir", type=Path, default=DEFAULT_ASSETS_DIR)
    parser.add_argument("--dp_python", type=Path, default=DEFAULT_DP_PYTHON)
    parser.add_argument("--public_nuscenes_root", type=Path, default=DEFAULT_NUSCENES_ROOT)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--num_candidates", type=int, default=DEFAULT_NUM_CANDIDATES)
    parser.add_argument("--max_npcs", type=int, default=DEFAULT_MAX_NPCS)
    parser.add_argument("--spawn_probability", type=float, default=DEFAULT_SPAWN_PROBABILITY)
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument(
        "--traffic_light_modes",
        default=",".join(DEFAULT_TRAFFIC_LIGHT_MODES),
    )
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        candidate_output_root=args.candidate_output_root,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        assets_dir=args.assets_dir,
        dp_python=args.dp_python,
        public_nuscenes_root=args.public_nuscenes_root,
        steps=args.steps,
        num_candidates=args.num_candidates,
        max_npcs=args.max_npcs,
        spawn_probability=args.spawn_probability,
        seeds=_parse_ints(args.seeds),
        traffic_light_modes=_parse_strings(args.traffic_light_modes),
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_runbook.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    args.output_runbook.write_text(render_runbook(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    v14_audit_md: Path,
    current_status_md: Path,
    candidate_output_root: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: Path = DEFAULT_DP_REPO,
    camp_repo: Path = DEFAULT_CAMP_REPO,
    assets_dir: Path = DEFAULT_ASSETS_DIR,
    dp_python: Path = DEFAULT_DP_PYTHON,
    public_nuscenes_root: Path = DEFAULT_NUSCENES_ROOT,
    steps: int = DEFAULT_STEPS,
    num_candidates: int = DEFAULT_NUM_CANDIDATES,
    max_npcs: int = DEFAULT_MAX_NPCS,
    spawn_probability: float = DEFAULT_SPAWN_PROBABILITY,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    traffic_light_modes: Sequence[str] = DEFAULT_TRAFFIC_LIGHT_MODES,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_public_assets: Sequence[dict[str, str]] = EXPECTED_PUBLIC_ASSETS,
    expected_static_weights_sha256: str = EXPECTED_STATIC_WEIGHTS_SHA256,
    expected_atom_scales_sha256: str = EXPECTED_ATOM_SCALES_SHA256,
) -> dict[str, Any]:
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    candidate_output_root = candidate_output_root.resolve()
    planned_commands = _planned_commands(
        camp_repo=camp_repo,
        dp_repo=dp_repo,
        assets_dir=assets_dir,
        dp_python=dp_python,
        candidate_output_root=candidate_output_root,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=tuple(seeds),
        traffic_light_modes=tuple(traffic_light_modes),
    )
    checks = _checks(
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        assets_dir=assets_dir,
        dp_python=dp_python,
        public_nuscenes_root=public_nuscenes_root,
        candidate_output_root=candidate_output_root,
        planned_commands=planned_commands,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=tuple(seeds),
        traffic_light_modes=tuple(traffic_light_modes),
        authorized_current_work=authorized_current_work,
        expected_public_assets=expected_public_assets,
        expected_static_weights_sha256=expected_static_weights_sha256,
        expected_atom_scales_sha256=expected_atom_scales_sha256,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "public_simulator_fixed_dp_candidate_generation_preflight_only": True,
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "public_simulator_preflight": {
            "candidate_output_root": str(candidate_output_root),
            "candidate_output_root_exists": candidate_output_root.exists(),
            "camp_repo": str(camp_repo),
            "dp_repo": str(dp_repo),
            "assets_dir": str(assets_dir),
            "dp_python": str(dp_python),
            "public_nuscenes_root": str(public_nuscenes_root),
            "route_count": len(ROUTE_SPECS),
            "routes": [
                {
                    "name": route["name"],
                    "route_path": str(assets_dir / route["route_relative_path"]),
                    "map_path": str(assets_dir / route["map_relative_path"]),
                }
                for route in ROUTE_SPECS
            ],
            "seeds": list(seeds),
            "traffic_light_modes": list(traffic_light_modes),
            "steps_per_command": steps,
            "num_candidates": num_candidates,
            "max_npcs": max_npcs,
            "spawn_probability": spawn_probability,
            "planned_command_count": len(planned_commands),
            "expected_records": len(planned_commands) * steps,
            "guard_env_var": GUARD_ENV_VAR,
            "executed_output_policy": "dp_top1",
            "default_off_shadow_selector": True,
            "candidate_tensor_provenance_logging": True,
            "required_zero_overlap_keys": [
                "candidate_tensor_hash",
                "path_signature",
                "record_identity",
                "split_manifest_root",
            ],
            "static_weights": str(assets_dir / STATIC_WEIGHTS_REL),
            "atom_scales": str(assets_dir / ATOM_SCALES_REL),
            "planned_commands": planned_commands,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _planned_commands(
    *,
    camp_repo: Path,
    dp_repo: Path,
    assets_dir: Path,
    dp_python: Path,
    candidate_output_root: Path,
    steps: int,
    num_candidates: int,
    max_npcs: int,
    spawn_probability: float,
    seeds: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
) -> list[list[str]]:
    commands: list[list[str]] = []
    for route in ROUTE_SPECS:
        for seed in seeds:
            for traffic_lights in traffic_light_modes:
                output_dir = (
                    candidate_output_root
                    / route["name"]
                    / f"seed_{seed}"
                    / f"tl_{traffic_lights}"
                    / "fixed_dp_top1_execution"
                )
                commands.append(
                    [
                        str(dp_python),
                        str(camp_repo / REPLAY_SCRIPT),
                        "--diffusion_repo",
                        str(dp_repo),
                        "--map_path",
                        str(assets_dir / route["map_relative_path"]),
                        "--route",
                        str(assets_dir / route["route_relative_path"]),
                        "--model_path",
                        str(assets_dir / "diffusion_planner.pth"),
                        "--model_args",
                        str(assets_dir / "diffusion_planner.param.json"),
                        "--config",
                        str(dp_repo / DP_REPLAY_CONFIG),
                        "--reward_config",
                        str(camp_repo / REWARD_CONFIG),
                        "--output_dir",
                        str(output_dir),
                        "--device",
                        "cuda",
                        "--advance_mode",
                        "perfect",
                        "--steps",
                        str(steps),
                        "--seed",
                        str(seed),
                        "--max_npcs",
                        str(max_npcs),
                        "--spawn_probability",
                        f"{spawn_probability:g}",
                        "--traffic_lights",
                        traffic_lights,
                        "--camp_selector_mode",
                        "static",
                        "--camp_static_weights",
                        str(assets_dir / STATIC_WEIGHTS_REL),
                        "--camp_atom_scales",
                        str(assets_dir / ATOM_SCALES_REL),
                        "--camp_fallback_mode",
                        "top1",
                        "--camp_feasibility_source",
                        "dp_reward",
                        "--camp_min_progress_ratio",
                        "0.8",
                        "--num_candidates",
                        str(num_candidates),
                        "--camp_candidate_tensor_provenance_logging",
                        "--camp_default_off_shadow_selector",
                        "--camp_shadow_expected_atom_scales_sha256",
                        EXPECTED_ATOM_SCALES_SHA256,
                        "--camp_shadow_expected_static_weights_sha256",
                        EXPECTED_STATIC_WEIGHTS_SHA256,
                    ]
                )
    return commands


def _checks(
    *,
    v14_audit_md: Path,
    current_status_md: Path,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    dp_repo: Path,
    camp_repo: Path,
    assets_dir: Path,
    dp_python: Path,
    public_nuscenes_root: Path,
    candidate_output_root: Path,
    planned_commands: list[list[str]],
    steps: int,
    num_candidates: int,
    max_npcs: int,
    spawn_probability: float,
    seeds: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    authorized_current_work: str,
    expected_public_assets: Sequence[dict[str, str]],
    expected_static_weights_sha256: str,
    expected_atom_scales_sha256: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    command_text = "\n".join(" ".join(command).lower() for command in planned_commands)

    add(_expect("v14_audit_exists", v14_audit_md.is_file(), True))
    add(_expect("current_status_exists", current_status_md.is_file(), True))
    add(_expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), CURRENT_V14_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_public_nuscenes_available", _latest_value(v14_text, "public_nuscenes_archives_available"), "True"))
    add(
        _expect(
            "audit_nuscenes_not_marked_missing",
            _latest_value(v14_text, "v14_public_simulator_source_reclassification_nuscenes_marked_missing"),
            "False",
        )
    )
    add(_expect("status_doc_points_to_v14", "docs/diffusion_planner_v14_iteration_audit.md" in status_text, True))
    add(_expect("status_doc_current_status", CURRENT_V14_STATUS in status_text, True))
    add(_expect("status_doc_next_work", authorized_current_work in status_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("assets_dir_exists", assets_dir.is_dir(), True))
    add(_expect("public_nuscenes_root_exists", public_nuscenes_root.is_dir(), True))
    add(_expect("dp_python_exists", dp_python.is_file(), True))
    add(_expect("replay_script_exists", (camp_repo / REPLAY_SCRIPT).is_file(), True))
    add(_expect("reward_config_exists", (camp_repo / REWARD_CONFIG).is_file(), True))
    add(_expect("dp_replay_config_exists", (dp_repo / DP_REPLAY_CONFIG).is_file(), True))
    add(_expect("candidate_output_root_absent", candidate_output_root.exists(), False))
    add(_expect("steps_per_command", steps, DEFAULT_STEPS))
    add(_expect("num_candidates", num_candidates, DEFAULT_NUM_CANDIDATES))
    add(_expect("max_npcs_nonnegative", max_npcs >= 0, True))
    add(_expect("spawn_probability_valid", math.isfinite(spawn_probability) and 0.0 <= spawn_probability <= 1.0, True))
    add(_expect("formal_seeds_forbidden", bool(set(seeds) & FORMAL_SEEDS), False))
    add(_expect("traffic_light_modes_valid", set(traffic_light_modes) <= {"on", "off"}, True))
    add(_expect("planned_command_count", len(planned_commands), 32))
    add(_expect("expected_records_at_least_3200", len(planned_commands) * steps >= 3200, True))

    for asset in expected_public_assets:
        path = assets_dir / asset["relative_path"]
        add(_expect(f"asset_exists_{asset['name']}", path.is_file(), True))
        add(_expect(f"asset_sha256_{asset['name']}", _sha256(path) if path.is_file() else None, asset["sha256"]))

    static_weights = assets_dir / STATIC_WEIGHTS_REL
    atom_scales = assets_dir / ATOM_SCALES_REL
    add(_expect("static_weights_exists", static_weights.is_file(), True))
    add(_expect("atom_scales_exists", atom_scales.is_file(), True))
    add(_expect("static_weights_sha256", _sha256(static_weights) if static_weights.is_file() else None, expected_static_weights_sha256))
    add(_expect("atom_scales_sha256", _sha256(atom_scales) if atom_scales.is_file() else None, expected_atom_scales_sha256))

    for command in planned_commands:
        add(_expect("command_uses_replay_script", str(camp_repo / REPLAY_SCRIPT) in command, True))
        add(_expect("command_uses_static_shadow_selector", "--camp_selector_mode" in command and "static" in command, True))
        add(_expect("command_logs_candidate_tensor_provenance", "--camp_candidate_tensor_provenance_logging" in command, True))
        add(_expect("command_enables_default_off_shadow_selector", "--camp_default_off_shadow_selector" in command, True))
        add(_expect("command_has_static_weights", "--camp_static_weights" in command, True))
        add(_expect("command_has_atom_scales", "--camp_atom_scales" in command, True))
        add(_expect("command_has_num_candidates_8", _option_value(command, "--num_candidates"), "8"))
        add(_expect("command_has_steps_100", _option_value(command, "--steps"), "100"))
    for snippet in FORBIDDEN_SNIPPETS:
        add(_expect(f"planned_commands_forbid_{_slug(snippet)}", snippet in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_11", "--seed 11" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_12", "--seed 12" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_13", "--seed 13" in command_text, False))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "recommended_next_work": None if passed else "public_simulator_fixed_dp_candidate_generation_preflight_remediation",
        "public_simulator_fixed_dp_candidate_generation_preflight_passed": passed,
        "public_simulator_fixed_dp_candidate_generation_execution_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": passed,
        "fixed_dp_candidate_generation_execution_authorized_next": passed,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("public_simulator_preflight"))
    return "\n".join(
        [
            "# V14 Public Simulator Fixed-DP Candidate Generation Preflight",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{decision.get('failed_checks')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Planned command count: `{preflight.get('planned_command_count')}`",
            f"- Expected records: `{preflight.get('expected_records')}`",
            f"- Candidate output root: `{preflight.get('candidate_output_root')}`",
            f"- Guard env var: `{preflight.get('guard_env_var')}`",
            f"- Executed output policy: `{preflight.get('executed_output_policy')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- CAMP generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized: `{decision.get('training_preflight_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Safety benefit claim authorized: `{decision.get('safety_benefit_claim_authorized')}`",
            "",
        ]
    )


def render_runbook(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("public_simulator_preflight"))
    heads = _dict(report.get("heads"))
    commands = [_list(command) for command in _list(preflight.get("planned_commands"))]
    failed = ",".join(str(item) for item in _list(decision.get("failed_checks")))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by the v14 public simulator fixed-DP candidate generation preflight.",
        "# Execute only after this preflight is audited and the v14 EOF authorizes execution.",
        f"if [ \"{decision.get('passed')}\" != \"True\" ]; then",
        f"  echo 'Refusing to run: preflight did not pass ({failed})' >&2",
        "  exit 39",
        "fi",
        f"if [ \"${{{GUARD_ENV_VAR}:-}}\" != \"1\" ]; then",
        f"  echo 'Refusing to run: set {GUARD_ENV_VAR}=1 in an authorized execution gate' >&2",
        "  exit 40",
        "fi",
        "source /etc/network_turbo >/dev/null 2>&1 || true",
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('camp_repo')))} rev-parse HEAD)\" != {_shell_quote(str(heads.get('current_camp_head')))} ]; then",
        "  echo 'CAMP HEAD mismatch' >&2",
        "  exit 41",
        "fi",
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('dp_repo')))} rev-parse HEAD)\" != {_shell_quote(FIXED_DP_HEAD)} ]; then",
        "  echo 'DP HEAD mismatch' >&2",
        "  exit 42",
        "fi",
        f"if [ -e {_shell_quote(str(preflight.get('candidate_output_root')))} ]; then",
        "  echo 'Candidate output root already exists' >&2",
        "  exit 43",
        "fi",
        f"export PYTHONPATH={_shell_quote(str(preflight.get('camp_repo')))}:{_shell_quote(str(Path(str(preflight.get('camp_repo'))) / 'camp_core'))}:{_shell_quote(str(preflight.get('dp_repo')))}:{_shell_quote(str(Path(str(preflight.get('dp_repo'))) / 'diffusion_planner'))}:${{PYTHONPATH:-}}",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        lines.append(f"echo 'Running fixed-DP public simulator command {index}/{len(commands)}'")
        lines.append(" ".join(_shell_quote(str(part)) for part in command))
        lines.append("")
    return "\n".join(lines)


def _parse_ints(value: str) -> tuple[int, ...]:
    parsed = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not parsed:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return parsed


def _parse_strings(value: str) -> tuple[str, ...]:
    parsed = tuple(part.strip() for part in value.split(",") if part.strip())
    if not parsed:
        raise argparse.ArgumentTypeError("at least one value is required")
    return parsed


def _failure_class(failed: list[str]) -> str:
    if any("asset_" in check or check in {"static_weights_exists", "atom_scales_exists"} for check in failed):
        return "missing_or_mismatched_public_simulator_asset"
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("dp_head" in check for check in failed):
        return "fixed_dp_head_mismatch"
    if any("candidate_output_root" in check for check in failed):
        return "candidate_output_root_not_fresh"
    return "public_simulator_fixed_dp_candidate_generation_preflight_contract_failure"


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": actual == expected}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _latest_value(text: str, key: str) -> str | None:
    pattern = f"{key}="
    matches = [line.split("=", 1)[1].strip() for line in text.splitlines() if line.startswith(pattern)]
    return matches[-1] if matches else None


def _option_value(command: Sequence[str], option: str) -> str | None:
    parts = [str(part) for part in command]
    if option not in parts:
        return None
    index = parts.index(option)
    return parts[index + 1] if index + 1 < len(parts) else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")[:80]


def _shell_quote(value: str) -> str:
    return shlex.quote(value)


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
