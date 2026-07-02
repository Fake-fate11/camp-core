#!/usr/bin/env python3
"""V14 trained default-off shadow replay/evaluation preflight.

This gate emits a guarded runtime manifest and runbook for evaluating the
already-trained CAMP static weights as a default-off shadow selector over fixed
Diffusion Planner candidate tensors. It does not run replay, generate
candidates, train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_rejected"
)
GUARD_ENV_VAR = "DP_CAMP_V14_TRAINED_DEFAULT_OFF_SHADOW_REPLAY_EVALUATION_EXECUTE"

DEFAULT_ASSETS_DIR = Path("/root/autodl-tmp/camp_dp_assets")
DEFAULT_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
DEFAULT_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
DEFAULT_DP_PYTHON = Path("/root/autodl-tmp/dp312_venv/bin/python")
DEFAULT_NUSCENES_ROOT = Path("/autodl-pub/data/nuScenes")
REPLAY_SCRIPT = Path("scripts/integrations/run_diffusion_planner_camp_replay.py")
REWARD_CONFIG = Path("configs/integrations/dp_camp_reward_eval.json")
DP_REPLAY_CONFIG = Path("scenario_generation/configs/replay_default.json")

EXPECTED_TRAINING_TYPE = "diffusion_planner_static_candidate_preference"
EXPECTED_LABEL_SOURCE = "dp_reward"
EXPECTED_REWARD_KEY = "quality_without_progress"
EXPECTED_REWARD_PROGRESS_WEIGHT = 2.0
EXPECTED_CONTRACT_RECORDS = 3200
EXPECTED_RECORDS_USED = 2914
EXPECTED_DROPPED_RECORDS = 286
EXPECTED_NUM_CANDIDATES = 8
EXPECTED_NUM_ATOMS = 9
EXPECTED_LOG_COUNT = 32
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_RECORDS = EXPECTED_LOG_COUNT * EXPECTED_STEPS_PER_LOG
EXPECTED_OUTPUT_FILES = (
    "atom_scales_dp_static.json",
    "offline_weights_dp_static.npy",
    "training_summary.json",
)
DEFAULT_STEPS = 100
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
    parser.add_argument("--training_execution_artifact_dir", type=Path, required=True)
    parser.add_argument(
        "--training_artifact_static_contract_review_artifact_dir",
        type=Path,
        required=True,
    )
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument("--output_runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--replay_output_root", type=Path, required=True)
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
    parser.add_argument("--num_candidates", type=int, default=EXPECTED_NUM_CANDIDATES)
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
        training_execution_artifact_dir=args.training_execution_artifact_dir,
        training_artifact_static_contract_review_artifact_dir=(
            args.training_artifact_static_contract_review_artifact_dir
        ),
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_json=args.output_json,
        output_md=args.output_md,
        output_runbook=args.output_runbook,
        output_runtime_manifest_json=args.output_runtime_manifest_json,
        replay_output_root=args.replay_output_root,
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
    write_outputs(
        output_json=args.output_json,
        output_md=args.output_md,
        output_runbook=args.output_runbook,
        output_runtime_manifest_json=args.output_runtime_manifest_json,
        report=report,
    )
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    training_execution_artifact_dir: Path,
    training_artifact_static_contract_review_artifact_dir: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_json: Path,
    output_md: Path,
    output_runbook: Path,
    output_runtime_manifest_json: Path,
    replay_output_root: Path,
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
    num_candidates: int = EXPECTED_NUM_CANDIDATES,
    max_npcs: int = DEFAULT_MAX_NPCS,
    spawn_probability: float = DEFAULT_SPAWN_PROBABILITY,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    traffic_light_modes: tuple[str, ...] = DEFAULT_TRAFFIC_LIGHT_MODES,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    training_dir = training_execution_artifact_dir.resolve()
    review_dir = training_artifact_static_contract_review_artifact_dir.resolve()
    weights_path = training_dir / "offline_weights_dp_static.npy"
    scales_path = training_dir / "atom_scales_dp_static.json"
    summary_path = training_dir / "training_summary.json"
    review_report_path = review_dir / "training_artifact_static_contract_report.json"

    summary = _read_json_dict(summary_path)
    scales_payload = _read_json_dict(scales_path)
    weights = _read_weights(weights_path)
    training_heads = _parse_key_values(_read_text(training_dir / "HEADS"))
    review_heads = _parse_key_values(_read_text(review_dir / "HEADS"))
    training_sha256s = _read_sha256sums(training_dir / "SHA256SUMS")
    review_sha256s = _read_sha256sums(review_dir / "SHA256SUMS")
    review_report = _read_json_dict(review_report_path)
    output_files = _read_lines(training_dir / "planned_output_files.txt")
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    artifact_review = _artifact_summary(
        summary=summary,
        scales_payload=scales_payload,
        weights=weights,
        output_files=output_files,
    )
    runtime_manifest = _runtime_manifest(
        training_dir=training_dir,
        review_dir=review_dir,
        summary=summary,
        scales_payload=scales_payload,
        weights_path=weights_path,
        scales_path=scales_path,
        summary_path=summary_path,
        review_report_path=review_report_path,
        training_sha256s=training_sha256s,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    planned_commands = _planned_commands(
        camp_repo=camp_repo.resolve(),
        dp_repo=dp_repo.resolve(),
        assets_dir=assets_dir.resolve(),
        dp_python=dp_python.resolve(),
        training_dir=training_dir,
        runtime_manifest_json=output_runtime_manifest_json.resolve(),
        replay_output_root=replay_output_root.resolve(),
        weights_sha256=runtime_manifest["artifacts"]["static_weights"]["sha256"],
        scales_sha256=runtime_manifest["artifacts"]["atom_scales"]["sha256"],
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=seeds,
        traffic_light_modes=traffic_light_modes,
    )
    checks = _checks(
        training_dir=training_dir,
        review_dir=review_dir,
        summary_path=summary_path,
        scales_path=scales_path,
        weights_path=weights_path,
        review_report_path=review_report_path,
        training_heads=training_heads,
        review_heads=review_heads,
        training_sha256s=training_sha256s,
        review_sha256s=review_sha256s,
        summary=summary,
        scales_payload=scales_payload,
        artifact_review=artifact_review,
        review_report=review_report,
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        dp_repo=dp_repo.resolve(),
        camp_repo=camp_repo.resolve(),
        assets_dir=assets_dir.resolve(),
        dp_python=dp_python.resolve(),
        public_nuscenes_root=public_nuscenes_root.resolve(),
        replay_output_root=replay_output_root.resolve(),
        output_runtime_manifest_json=output_runtime_manifest_json.resolve(),
        planned_commands=planned_commands,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=seeds,
        traffic_light_modes=traffic_light_modes,
        authorized_current_work=authorized_current_work,
        expected_public_assets=EXPECTED_PUBLIC_ASSETS,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "preflight_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "training_artifact_source_review_passed": bool(
                _dict(review_report.get("final_decision")).get("passed")
            ),
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "inputs": {
            "training_execution_artifact_dir": str(training_dir),
            "training_artifact_static_contract_review_artifact_dir": str(review_dir),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_json": str(output_json.resolve()),
            "output_md": str(output_md.resolve()),
            "output_runbook": str(output_runbook.resolve()),
            "output_runtime_manifest_json": str(output_runtime_manifest_json.resolve()),
            "replay_output_root": str(replay_output_root.resolve()),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_artifact_camp_head": training_heads.get("CAMP_HEAD"),
            "training_artifact_camp_origin_main": training_heads.get("CAMP_ORIGIN_MAIN"),
            "training_artifact_dp_head": training_heads.get("DP_HEAD"),
            "review_artifact_camp_head": review_heads.get("CAMP_HEAD"),
            "review_artifact_camp_origin_main": review_heads.get("CAMP_ORIGIN_MAIN"),
            "review_artifact_dp_head": review_heads.get("DP_HEAD"),
        },
        "artifact_hashes": {
            "training": training_sha256s,
            "review": review_sha256s,
        },
        "training_summary": summary,
        "artifact_review": artifact_review,
        "source_review_report": review_report,
        "runtime_manifest": runtime_manifest,
        "shadow_replay_preflight": {
            "planned_command_count": len(planned_commands),
            "expected_steps_per_command": steps,
            "expected_records": len(planned_commands) * steps,
            "expected_log_count": len(planned_commands),
            "num_candidates": num_candidates,
            "camp_repo": str(camp_repo.resolve()),
            "dp_repo": str(dp_repo.resolve()),
            "replay_output_root": str(replay_output_root.resolve()),
            "runtime_manifest_json": str(output_runtime_manifest_json.resolve()),
            "guard_env_var": GUARD_ENV_VAR,
            "planned_commands": planned_commands,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def write_outputs(
    *,
    output_json: Path,
    output_md: Path,
    output_runbook: Path,
    output_runtime_manifest_json: Path,
    report: dict[str, Any],
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_runbook.parent.mkdir(parents=True, exist_ok=True)
    output_runtime_manifest_json.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_json, report)
    output_md.write_text(render_markdown(report), encoding="utf-8")
    output_runbook.write_text(render_runbook(report), encoding="utf-8")
    _write_json(output_runtime_manifest_json, report["runtime_manifest"])
    _write_sha256sums(
        output_json.parent / "SHA256SUMS",
        [output_json, output_md, output_runbook, output_runtime_manifest_json],
    )


def _planned_commands(
    *,
    camp_repo: Path,
    dp_repo: Path,
    assets_dir: Path,
    dp_python: Path,
    training_dir: Path,
    runtime_manifest_json: Path,
    replay_output_root: Path,
    weights_sha256: str,
    scales_sha256: str,
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
                    replay_output_root
                    / route["name"]
                    / f"seed_{seed}"
                    / f"tl_{traffic_lights}"
                    / "trained_default_off_shadow_replay"
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
                        str(training_dir / "offline_weights_dp_static.npy"),
                        "--camp_atom_scales",
                        str(training_dir / "atom_scales_dp_static.json"),
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
                        "--camp_shadow_artifact_manifest",
                        str(runtime_manifest_json),
                        "--camp_shadow_expected_atom_scales_sha256",
                        scales_sha256,
                        "--camp_shadow_expected_static_weights_sha256",
                        weights_sha256,
                    ]
                )
    return commands


def _runtime_manifest(
    *,
    training_dir: Path,
    review_dir: Path,
    summary: dict[str, Any],
    scales_payload: dict[str, Any],
    weights_path: Path,
    scales_path: Path,
    summary_path: Path,
    review_report_path: Path,
    training_sha256s: dict[str, str],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    weights_sha = training_sha256s.get(weights_path.name) or (
        _sha256(weights_path) if weights_path.is_file() else None
    )
    scales_sha = training_sha256s.get(scales_path.name) or (
        _sha256(scales_path) if scales_path.is_file() else None
    )
    summary_sha = training_sha256s.get(summary_path.name) or (
        _sha256(summary_path) if summary_path.is_file() else None
    )
    review_sha = _sha256(review_report_path) if review_report_path.is_file() else None
    return {
        "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "source_preflight_schema_version": SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "score_expression": SCORE_EXPRESSION,
        "required_candidate_count": EXPECTED_NUM_CANDIDATES,
        "selector_mode": "static",
        "training_execution_artifact_dir": str(training_dir),
        "training_artifact_static_contract_review_artifact_dir": str(review_dir),
        "current_camp_head": current_camp_head,
        "current_dp_head": current_dp_head,
        "training_summary": {
            "training_type": summary.get("training_type"),
            "label_source": summary.get("label_source"),
            "reward_key": summary.get("reward_key"),
            "num_records": summary.get("num_records"),
            "dropped_records_without_feasible_candidate": summary.get(
                "dropped_records_without_feasible_candidate"
            ),
            "num_candidates": summary.get("num_candidates"),
            "num_atoms": summary.get("num_atoms"),
            "atom_schema_version": summary.get("atom_schema_version"),
            "atom_names": summary.get("atom_names"),
        },
        "artifacts": {
            "static_weights": {
                "path": str(weights_path),
                "sha256": weights_sha,
            },
            "atom_scales": {
                "path": str(scales_path),
                "sha256": scales_sha,
                "atom_schema_version": scales_payload.get("atom_schema_version"),
                "atom_names": scales_payload.get("atom_names"),
            },
            "training_summary": {
                "path": str(summary_path),
                "sha256": summary_sha,
            },
            "training_artifact_static_contract_review_report": {
                "path": str(review_report_path),
                "sha256": review_sha,
            },
        },
        "boundaries": {
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "reference_blend_authorized": False,
            "guidance_authorized": False,
            "postprocess_or_postselection_authorized": False,
            "closed_loop_outcome_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
    }


def _checks(
    *,
    training_dir: Path,
    review_dir: Path,
    summary_path: Path,
    scales_path: Path,
    weights_path: Path,
    review_report_path: Path,
    training_heads: dict[str, str],
    review_heads: dict[str, str],
    training_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
    summary: dict[str, Any],
    scales_payload: dict[str, Any],
    artifact_review: dict[str, Any],
    review_report: dict[str, Any],
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
    replay_output_root: Path,
    output_runtime_manifest_json: Path,
    planned_commands: list[list[str]],
    steps: int,
    num_candidates: int,
    max_npcs: int,
    spawn_probability: float,
    seeds: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    authorized_current_work: str,
    expected_public_assets: Sequence[dict[str, str]],
) -> list[dict[str, Any]]:
    expected_atom_schema, expected_atom_names = atom_schema_for_dimension(
        EXPECTED_NUM_ATOMS
    )
    review_decision = _dict(review_report.get("final_decision"))
    contract = _dict(summary.get("dp_native_training_data_contract"))
    command_text = "\n".join(" ".join(command).lower() for command in planned_commands)
    checks: list[dict[str, Any]] = []
    add = checks.append

    add(_expect("v14_audit_exists", v14_audit_md.is_file(), True))
    add(_expect("current_status_exists", current_status_md.is_file(), True))
    add(_expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work))
    add(_expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True))
    add(_expect("status_doc_next_work", authorized_current_work in status_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))

    add(_expect("training_artifact_dir_exists", training_dir.is_dir(), True))
    add(_expect("training_summary_exists", summary_path.is_file(), True))
    add(_expect("atom_scales_exists", scales_path.is_file(), True))
    add(_expect("offline_weights_exists", weights_path.is_file(), True))
    add(_expect("training_heads_exists", (training_dir / "HEADS").is_file(), True))
    add(_expect("training_sha256sums_exists", (training_dir / "SHA256SUMS").is_file(), True))
    add(_expect("training_exit_code", _read_text(training_dir / "exit.code").strip(), "0"))
    add(_expect("training_artifact_dp_head_fixed", training_heads.get("DP_HEAD"), FIXED_DP_HEAD))
    add(_expect("training_artifact_camp_head_matches_origin", training_heads.get("CAMP_HEAD"), training_heads.get("CAMP_ORIGIN_MAIN")))

    add(_expect("review_artifact_dir_exists", review_dir.is_dir(), True))
    add(_expect("review_report_exists", review_report_path.is_file(), True))
    add(_expect("review_heads_exists", (review_dir / "HEADS").is_file(), True))
    add(_expect("review_sha256sums_exists", (review_dir / "SHA256SUMS").is_file(), True))
    add(_expect("review_exit_code", _read_text(review_dir / "exit.code").strip(), "0"))
    add(_expect("review_artifact_dp_head_fixed", review_heads.get("DP_HEAD"), FIXED_DP_HEAD))
    add(_expect("source_review_passed", review_decision.get("passed"), True))
    add(_expect("source_review_status", review_decision.get("status"), EXPECTED_CURRENT_STATUS))
    add(_expect("source_review_authorized_next", review_decision.get("authorized_next_work"), authorized_current_work))

    add(_expect("training_type", summary.get("training_type"), EXPECTED_TRAINING_TYPE))
    add(_expect("label_source", summary.get("label_source"), EXPECTED_LABEL_SOURCE))
    add(_expect("reward_key", summary.get("reward_key"), EXPECTED_REWARD_KEY))
    add(_expect("reward_progress_weight", _safe_float(summary.get("reward_progress_weight")), EXPECTED_REWARD_PROGRESS_WEIGHT))
    add(_expect("num_records", summary.get("num_records"), EXPECTED_RECORDS_USED))
    add(_expect("dropped_records_without_feasible_candidate", summary.get("dropped_records_without_feasible_candidate"), EXPECTED_DROPPED_RECORDS))
    add(_expect("contract_records", contract.get("records"), EXPECTED_CONTRACT_RECORDS))
    add(_expect("contract_failed_records_zero", len(contract.get("failed_records", [])), 0))
    add(_expect("contract_future_training_input", contract.get("future_training_input_contract_satisfied"), True))
    add(_expect("num_candidates", summary.get("num_candidates"), EXPECTED_NUM_CANDIDATES))
    add(_expect("num_atoms", summary.get("num_atoms"), EXPECTED_NUM_ATOMS))
    add(_expect("atom_schema_version", summary.get("atom_schema_version"), expected_atom_schema))
    add(_expect("atom_names", tuple(summary.get("atom_names") or ()), tuple(expected_atom_names)))
    add(_expect("closed_loop_outcome_key_absent", summary.get("outcome_key"), None))
    add(_expect("outcome_weights_path_absent", summary.get("outcome_weights_path"), None))
    add(_expect("outcome_weights_absent", summary.get("outcome_weights"), None))
    add(_expect("weights_length", artifact_review["weights_length"], EXPECTED_NUM_ATOMS))
    add(_expect("weights_all_finite", artifact_review["weights_all_finite"], True))
    add(_expect("weights_nonnegative", artifact_review["weights_nonnegative"], True))
    add(_check("weights_sum_one", abs(artifact_review["weights_sum"] - 1.0) <= 1e-9, artifact_review["weights_sum"], "1.0 +/- 1e-9"))
    add(_expect("weights_file_matches_summary", artifact_review["weights_file_matches_summary"], True))
    add(_expect("scales_schema", scales_payload.get("atom_schema_version"), expected_atom_schema))
    add(_expect("scales_names", tuple(scales_payload.get("atom_names") or ()), tuple(expected_atom_names)))
    add(_expect("scales_length", artifact_review["scales_length"], EXPECTED_NUM_ATOMS))
    add(_expect("scales_all_positive_finite", artifact_review["scales_all_positive_finite"], True))
    add(_expect("training_output_files", tuple(artifact_review["output_files"]), EXPECTED_OUTPUT_FILES))
    add(_expect("training_summary_sha256_matches", training_sha256s.get(summary_path.name), _sha256(summary_path) if summary_path.is_file() else None))
    add(_expect("atom_scales_sha256_matches", training_sha256s.get(scales_path.name), _sha256(scales_path) if scales_path.is_file() else None))
    add(_expect("offline_weights_sha256_matches", training_sha256s.get(weights_path.name), _sha256(weights_path) if weights_path.is_file() else None))
    add(_expect("review_report_sha256_matches", review_sha256s.get(review_report_path.name), _sha256(review_report_path) if review_report_path.is_file() else None))

    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("assets_dir_exists", assets_dir.is_dir(), True))
    add(_expect("public_nuscenes_root_exists", public_nuscenes_root.is_dir(), True))
    add(_expect("dp_python_exists", dp_python.is_file(), True))
    add(_expect("replay_script_exists", (camp_repo / REPLAY_SCRIPT).is_file(), True))
    add(_expect("reward_config_exists", (camp_repo / REWARD_CONFIG).is_file(), True))
    add(_expect("dp_replay_config_exists", (dp_repo / DP_REPLAY_CONFIG).is_file(), True))
    add(_expect("replay_output_root_absent", replay_output_root.exists(), False))
    add(_expect("runtime_manifest_json_absent_before_preflight", output_runtime_manifest_json.exists(), False))
    add(_expect("steps_per_command", steps, EXPECTED_STEPS_PER_LOG))
    add(_expect("num_candidates_8", num_candidates, EXPECTED_NUM_CANDIDATES))
    add(_expect("max_npcs_nonnegative", max_npcs >= 0, True))
    add(_expect("spawn_probability_valid", math.isfinite(spawn_probability) and 0.0 <= spawn_probability <= 1.0, True))
    add(_expect("formal_seeds_forbidden", bool(set(seeds) & FORMAL_SEEDS), False))
    add(_expect("traffic_light_modes_valid", set(traffic_light_modes) <= {"on", "off"}, True))
    add(_expect("planned_command_count", len(planned_commands), EXPECTED_LOG_COUNT))
    add(_expect("expected_records", len(planned_commands) * steps, EXPECTED_RECORDS))

    for asset in expected_public_assets:
        path = assets_dir / asset["relative_path"]
        add(_expect(f"asset_exists_{asset['name']}", path.is_file(), True))
        add(_expect(f"asset_sha256_{asset['name']}", _sha256(path) if path.is_file() else None, asset["sha256"]))

    for command in planned_commands:
        add(_expect("command_uses_replay_script", str(camp_repo / REPLAY_SCRIPT) in command, True))
        add(_expect("command_uses_static_shadow_selector", _option_value(command, "--camp_selector_mode"), "static"))
        add(_expect("command_logs_candidate_tensor_provenance", "--camp_candidate_tensor_provenance_logging" in command, True))
        add(_expect("command_enables_default_off_shadow_selector", "--camp_default_off_shadow_selector" in command, True))
        add(_expect("command_has_shadow_artifact_manifest", _option_value(command, "--camp_shadow_artifact_manifest"), str(output_runtime_manifest_json)))
        add(_expect("command_static_weights_from_training_artifact", _option_value(command, "--camp_static_weights"), str(weights_path)))
        add(_expect("command_atom_scales_from_training_artifact", _option_value(command, "--camp_atom_scales"), str(scales_path)))
        add(_expect("command_has_num_candidates_8", _option_value(command, "--num_candidates"), "8"))
        add(_expect("command_has_steps_100", _option_value(command, "--steps"), str(EXPECTED_STEPS_PER_LOG)))
    for snippet in FORBIDDEN_SNIPPETS:
        add(_expect(f"planned_commands_forbid_{_slug(snippet)}", snippet in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_11", "--seed 11" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_12", "--seed 12" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_13", "--seed 13" in command_text, False))
    return checks


def _artifact_summary(
    *,
    summary: dict[str, Any],
    scales_payload: dict[str, Any],
    weights: np.ndarray,
    output_files: list[str],
) -> dict[str, Any]:
    summary_weights = np.asarray(summary.get("trained_weights") or [], dtype=np.float64)
    scales = np.asarray(scales_payload.get("scales") or [], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    return {
        "output_files": output_files,
        "weights_length": int(weights.size),
        "weights_sum": float(np.sum(weights)) if weights.size else math.nan,
        "weights_min": float(np.min(weights)) if weights.size else math.nan,
        "weights_max": float(np.max(weights)) if weights.size else math.nan,
        "weights_all_finite": bool(weights.size and np.all(np.isfinite(weights))),
        "weights_nonnegative": bool(weights.size and np.all(weights >= 0.0)),
        "weights_file_matches_summary": bool(
            weights.shape == summary_weights.shape
            and weights.size
            and np.allclose(weights, summary_weights, rtol=0.0, atol=1e-12)
        ),
        "scales_length": int(scales.size),
        "scales_all_positive_finite": bool(
            scales.size and np.all(np.isfinite(scales)) and np.all(scales > 0.0)
        ),
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "trained_default_off_shadow_replay_evaluation_preflight_complete": bool(passed),
        "trained_default_off_shadow_replay_evaluation_execution_authorized_next": bool(passed),
        "training_artifact_static_contract_review_source_required": True,
        "preflight_only": True,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
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
        "executed_output_policy": "dp_top1",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("shadow_replay_preflight"))
    review = _dict(report.get("artifact_review"))
    runtime = _dict(report.get("runtime_manifest"))
    return "\n".join(
        [
            "# V14 Trained Default-Off Shadow Replay/Evaluation Preflight",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{decision.get('failed_checks')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Planned command count: `{preflight.get('planned_command_count')}`",
            f"- Expected records: `{preflight.get('expected_records')}`",
            f"- Replay output root: `{preflight.get('replay_output_root')}`",
            f"- Runtime manifest: `{preflight.get('runtime_manifest_json')}`",
            f"- Guard env var: `{preflight.get('guard_env_var')}`",
            f"- Weights sum: `{review.get('weights_sum')}`",
            f"- Runtime schema: `{runtime.get('schema_version')}`",
            f"- Executed output policy: `{decision.get('executed_output_policy')}`",
            f"- Replay executed: `{decision.get('replay_executed')}`",
            f"- CAMP generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Safety benefit claim authorized: `{decision.get('safety_benefit_claim_authorized')}`",
            "",
            "This is a preflight only. It writes a fail-closed shadow-selector "
            "manifest and guarded runbook but does not run replay, change the "
            "executed DP Top-1 trajectory, promote, deploy, or claim safety benefit.",
            "",
        ]
    )


def render_runbook(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("shadow_replay_preflight"))
    heads = _dict(report.get("heads"))
    commands = [_list(command) for command in _list(preflight.get("planned_commands"))]
    failed = ",".join(str(item) for item in _list(decision.get("failed_checks")))
    runtime_manifest = str(preflight.get("runtime_manifest_json"))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by the v14 trained default-off shadow replay/evaluation preflight.",
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
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('camp_repo', DEFAULT_CAMP_REPO)))} rev-parse HEAD)\" != {_shell_quote(str(heads.get('current_camp_head')))} ]; then",
        "  echo 'CAMP HEAD mismatch' >&2",
        "  exit 41",
        "fi",
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('dp_repo', DEFAULT_DP_REPO)))} rev-parse HEAD)\" != {_shell_quote(FIXED_DP_HEAD)} ]; then",
        "  echo 'DP HEAD mismatch' >&2",
        "  exit 42",
        "fi",
        f"if [ ! -f {_shell_quote(runtime_manifest)} ]; then",
        "  echo 'Runtime manifest missing' >&2",
        "  exit 43",
        "fi",
        f"if [ -e {_shell_quote(str(preflight.get('replay_output_root')))} ]; then",
        "  echo 'Replay output root already exists' >&2",
        "  exit 44",
        "fi",
        f"export PYTHONPATH={_shell_quote(str(preflight.get('camp_repo', DEFAULT_CAMP_REPO)))}:{_shell_quote(str(Path(str(preflight.get('camp_repo', DEFAULT_CAMP_REPO))) / 'camp_core'))}:{_shell_quote(str(preflight.get('dp_repo', DEFAULT_DP_REPO)))}:{_shell_quote(str(Path(str(preflight.get('dp_repo', DEFAULT_DP_REPO))) / 'diffusion_planner'))}:${{PYTHONPATH:-}}",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        lines.append(f"echo 'Running trained default-off shadow replay command {index}/{len(commands)}'")
        lines.append(" ".join(_shell_quote(str(part)) for part in command))
        lines.append("")
    return "\n".join(lines)


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("review" in check for check in failed):
        return "training_artifact_static_contract_review_missing_or_failed"
    if any("asset_" in check or "repo_exists" in check for check in failed):
        return "public_simulator_asset_or_repo_contract_failure"
    if any("weights" in check or "scales" in check or "atom_" in check for check in failed):
        return "training_artifact_weight_or_atom_contract_failure"
    if any("label" in check or "outcome" in check or "reward" in check for check in failed):
        return "training_label_contract_failure"
    if any("replay_output_root" in check or "runtime_manifest" in check for check in failed):
        return "shadow_replay_preflight_output_not_fresh"
    if any("formal_seed" in check or "forbid" in check for check in failed):
        return "forbidden_shadow_replay_command_contract_failure"
    return "trained_default_off_shadow_replay_evaluation_preflight_contract_failure"


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


def _read_weights(path: Path) -> np.ndarray:
    if not path.is_file():
        return np.asarray([], dtype=np.float64)
    return np.asarray(np.load(path), dtype=np.float64).reshape(-1)


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_lines(path: Path) -> list[str]:
    text = _read_text(path)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _read_sha256sums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            entries[Path(parts[-1]).name] = parts[0].lower()
    return entries


def _parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    found: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            found = stripped[len(prefix) :]
    return found


def _option_value(command: list[str], option: str) -> str | None:
    try:
        index = command.index(option)
    except ValueError:
        return None
    next_index = index + 1
    if next_index >= len(command):
        return None
    return command[next_index]


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(path: Path, files: Sequence[Path]) -> None:
    lines = [f"{_sha256(file)}  {file.name}" for file in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": actual == expected}


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": bool(passed)}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _shell_quote(value: str) -> str:
    return shlex.quote(value)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
