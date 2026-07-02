#!/usr/bin/env python3
"""Preflight v14 default-off selector runtime shadow replay.

This is a static gate. It reads the materialized runtime artifact manifest,
runner source, public simulator assets, and v14 EOF/status boundary, then
writes a JSON/MD report and a guarded runbook. It does not execute replay,
generate candidates, train CAMP, modify Diffusion Planner, promote, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_shadow_replay_preflight_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_preflight_disabled"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_preflight_rejected"
)
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialized"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_preflight_only"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_execution_only"
)
GUARD_ENV_VAR = "DP_CAMP_V14_DEFAULT_OFF_SELECTOR_RUNTIME_SHADOW_REPLAY_EXECUTE"

DEFAULT_ASSETS_DIR = Path("/root/autodl-tmp/camp_dp_assets")
DEFAULT_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
DEFAULT_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
DEFAULT_DP_PYTHON = Path("/root/autodl-tmp/dp312_venv/bin/python")
REPLAY_SCRIPT = Path("scripts/integrations/run_diffusion_planner_camp_replay.py")
REWARD_CONFIG = Path("configs/integrations/dp_camp_reward_eval.json")
DP_REPLAY_CONFIG = Path("scenario_generation/configs/replay_default.json")

FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9
EXPECTED_LOG_COUNT = 32
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_RECORDS = EXPECTED_LOG_COUNT * EXPECTED_STEPS_PER_LOG
DEFAULT_STEPS = EXPECTED_STEPS_PER_LOG
DEFAULT_MAX_NPCS = 4
DEFAULT_SPAWN_PROBABILITY = 0.3
DEFAULT_SEEDS = (1, 2, 3, 4)
DEFAULT_TRAFFIC_LIGHT_MODES = ("on", "off")
FORMAL_SEEDS = {11, 12, 13}
RUNTIME_ENTRIES = ("atom_scales", "static_weights")

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

FORBIDDEN_COMMAND_SNIPPETS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
    "--camp_collect_closed_loop_outcomes",
)

BLOCKED_AUTHORIZATIONS = (
    "default_off_shadow_selector_runtime_execution_authorized",
    "runtime_artifact_manifest_materialization_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "training_authorized",
    "training_execution_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument("--replay_output_root", type=Path, required=True)
    parser.add_argument("--expected_runtime_manifest_sha256", default=None)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=DEFAULT_DP_REPO)
    parser.add_argument("--camp_repo", type=Path, default=DEFAULT_CAMP_REPO)
    parser.add_argument("--assets_dir", type=Path, default=DEFAULT_ASSETS_DIR)
    parser.add_argument("--dp_python", type=Path, default=DEFAULT_DP_PYTHON)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--num_candidates", type=int, default=EXPECTED_CANDIDATE_COUNT)
    parser.add_argument("--max_npcs", type=int, default=DEFAULT_MAX_NPCS)
    parser.add_argument("--spawn_probability", type=float, default=DEFAULT_SPAWN_PROBABILITY)
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument(
        "--traffic_light_modes",
        default=",".join(DEFAULT_TRAFFIC_LIGHT_MODES),
    )
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--expected_current_status", default=EXPECTED_CURRENT_STATUS)
    parser.add_argument(
        "--enable_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_manifest_json=args.runtime_manifest_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_json=args.output_json,
        output_md=args.output_md,
        output_runbook=args.output_runbook,
        replay_output_root=args.replay_output_root,
        expected_runtime_manifest_sha256=args.expected_runtime_manifest_sha256,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        assets_dir=args.assets_dir,
        dp_python=args.dp_python,
        steps=args.steps,
        num_candidates=args.num_candidates,
        max_npcs=args.max_npcs,
        spawn_probability=args.spawn_probability,
        seeds=_parse_ints(args.seeds),
        traffic_light_modes=_parse_strings(args.traffic_light_modes),
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        expected_current_status=args.expected_current_status,
        enabled=(
            args.enable_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_preflight
        ),
    )
    write_outputs(
        output_json=args.output_json,
        output_md=args.output_md,
        output_runbook=args.output_runbook,
        report=report,
    )
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_manifest_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_json: Path,
    output_md: Path,
    output_runbook: Path,
    replay_output_root: Path,
    expected_runtime_manifest_sha256: str | None = None,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: Path = DEFAULT_DP_REPO,
    camp_repo: Path = DEFAULT_CAMP_REPO,
    assets_dir: Path = DEFAULT_ASSETS_DIR,
    dp_python: Path = DEFAULT_DP_PYTHON,
    steps: int = DEFAULT_STEPS,
    num_candidates: int = EXPECTED_CANDIDATE_COUNT,
    max_npcs: int = DEFAULT_MAX_NPCS,
    spawn_probability: float = DEFAULT_SPAWN_PROBABILITY,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    traffic_light_modes: tuple[str, ...] = DEFAULT_TRAFFIC_LIGHT_MODES,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_current_status: str = EXPECTED_CURRENT_STATUS,
    enabled: bool = False,
) -> dict[str, Any]:
    runtime_manifest_json = runtime_manifest_json.resolve()
    v14_audit_md = v14_audit_md.resolve()
    current_status_md = current_status_md.resolve()
    output_json = output_json.resolve()
    output_md = output_md.resolve()
    output_runbook = output_runbook.resolve()
    replay_output_root = replay_output_root.resolve()
    dp_repo = dp_repo.resolve()
    camp_repo = camp_repo.resolve()
    assets_dir = assets_dir.resolve()
    dp_python = dp_python.resolve()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "static_preflight_only": True,
            "runtime_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "training_execution": False,
            "dp_modification_execution": False,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "runtime_manifest_json": str(runtime_manifest_json),
            "v14_audit_md": str(v14_audit_md),
            "current_status_md": str(current_status_md),
            "output_json": str(output_json),
            "output_md": str(output_md),
            "output_runbook": str(output_runbook),
        },
        "blocked_actions": _blocked_actions(),
        "runtime_manifest": {},
        "runtime_artifact_review": {},
        "shadow_replay_preflight": {},
        "checks": [],
        "final_decision": _decision(
            passed=False,
            failed=[],
            enabled=bool(enabled),
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }
    if not enabled:
        report["final_decision"]["status"] = DISABLED_STATUS
        return report

    manifest, manifest_error = _load_json(runtime_manifest_json)
    manifest_sha = _sha256(runtime_manifest_json) if runtime_manifest_json.is_file() else None
    artifacts = _dict(manifest.get("artifacts"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    atom_scales_path = Path(str(atom_entry.get("path", "")))
    static_weights_path = Path(str(weights_entry.get("path", "")))
    runner_path = camp_repo / REPLAY_SCRIPT
    runner_text = _read_text(runner_path)
    audit_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)

    atom_review = _review_atom_scales(atom_scales_path)
    weights_review = _review_static_weights(static_weights_path)
    planned_commands = _planned_commands(
        camp_repo=camp_repo,
        dp_repo=dp_repo,
        assets_dir=assets_dir,
        dp_python=dp_python,
        runtime_manifest_json=runtime_manifest_json,
        replay_output_root=replay_output_root,
        atom_scales_path=atom_scales_path,
        atom_scales_sha256=str(atom_entry.get("sha256", "")),
        static_weights_path=static_weights_path,
        static_weights_sha256=str(weights_entry.get("sha256", "")),
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=seeds,
        traffic_light_modes=traffic_light_modes,
    )
    command_text = "\n".join(" ".join(command) for command in planned_commands)
    checks = _build_checks(
        manifest=manifest,
        manifest_error=manifest_error,
        manifest_sha=manifest_sha,
        expected_runtime_manifest_sha256=expected_runtime_manifest_sha256,
        runtime_manifest_json=runtime_manifest_json,
        artifacts=artifacts,
        atom_entry=atom_entry,
        weights_entry=weights_entry,
        atom_scales_path=atom_scales_path,
        static_weights_path=static_weights_path,
        atom_review=atom_review,
        weights_review=weights_review,
        runner_path=runner_path,
        runner_text=runner_text,
        audit_text=audit_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        assets_dir=assets_dir,
        dp_python=dp_python,
        replay_output_root=replay_output_root,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        seeds=seeds,
        traffic_light_modes=traffic_light_modes,
        planned_commands=planned_commands,
        command_text=command_text,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
        expected_current_status=expected_current_status,
    )
    failed = sorted(check["name"] for check in checks if not check["passed"])
    passed = not failed
    report.update(
        {
            "runtime_manifest": manifest,
            "source_hashes": {
                "runtime_manifest_sha256": manifest_sha,
                "replay_runner_sha256": _sha256(runner_path)
                if runner_path.is_file()
                else None,
                "v14_audit_sha256": _sha256(v14_audit_md)
                if v14_audit_md.is_file()
                else None,
                "current_status_sha256": _sha256(current_status_md)
                if current_status_md.is_file()
                else None,
            },
            "runtime_artifact_review": {
                "atom_scales": atom_review,
                "static_weights": weights_review,
            },
            "shadow_replay_preflight": {
                "planned_command_count": len(planned_commands),
                "expected_steps_per_command": steps,
                "expected_records": len(planned_commands) * steps,
                "expected_log_count": len(planned_commands),
                "num_candidates": num_candidates,
                "camp_repo": str(camp_repo),
                "dp_repo": str(dp_repo),
                "assets_dir": str(assets_dir),
                "replay_output_root": str(replay_output_root),
                "runtime_manifest_json": str(runtime_manifest_json),
                "guard_env_var": GUARD_ENV_VAR,
                "planned_commands": planned_commands,
                "candidate_operation": "fixed DP candidate reranking only",
                "executed_output_policy": "dp_top1",
                "score_expression": SCORE_EXPRESSION,
                "runtime_manifest_sha256": manifest_sha,
            },
            "checks": checks,
            "final_decision": _decision(
                passed=passed,
                failed=failed,
                enabled=True,
                authorized_current_work=authorized_current_work,
                authorized_next_work=authorized_next_work,
            ),
        }
    )
    return report


def write_outputs(
    *,
    output_json: Path,
    output_md: Path,
    output_runbook: Path,
    report: dict[str, Any],
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_runbook.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_json, report)
    output_md.write_text(render_markdown(report), encoding="utf-8")
    output_runbook.write_text(render_runbook(report), encoding="utf-8")
    _write_sha256sums(
        output_json.parent / "SHA256SUMS",
        [output_json, output_md, output_runbook],
    )


def _planned_commands(
    *,
    camp_repo: Path,
    dp_repo: Path,
    assets_dir: Path,
    dp_python: Path,
    runtime_manifest_json: Path,
    replay_output_root: Path,
    atom_scales_path: Path,
    atom_scales_sha256: str,
    static_weights_path: Path,
    static_weights_sha256: str,
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
                    / "runtime_default_off_shadow_replay"
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
                        str(static_weights_path),
                        "--camp_atom_scales",
                        str(atom_scales_path),
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
                        atom_scales_sha256,
                        "--camp_shadow_expected_static_weights_sha256",
                        static_weights_sha256,
                    ]
                )
    return commands


def _build_checks(
    *,
    manifest: dict[str, Any],
    manifest_error: str | None,
    manifest_sha: str | None,
    expected_runtime_manifest_sha256: str | None,
    runtime_manifest_json: Path,
    artifacts: dict[str, Any],
    atom_entry: dict[str, Any],
    weights_entry: dict[str, Any],
    atom_scales_path: Path,
    static_weights_path: Path,
    atom_review: dict[str, Any],
    weights_review: dict[str, Any],
    runner_path: Path,
    runner_text: str,
    audit_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    dp_repo: Path,
    camp_repo: Path,
    assets_dir: Path,
    dp_python: Path,
    replay_output_root: Path,
    steps: int,
    num_candidates: int,
    max_npcs: int,
    spawn_probability: float,
    seeds: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    planned_commands: list[list[str]],
    command_text: str,
    authorized_current_work: str,
    authorized_next_work: str,
    expected_current_status: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(check: dict[str, Any]) -> None:
        checks.append(check)

    audit_status = _latest_value(audit_text, "current_v14_status")
    audit_next = _latest_value(audit_text, "next_work_target")
    status_doc_status = _latest_value(status_text, "current_v14_status")
    status_doc_next = _latest_value(status_text, "next_work_target")
    audit_preflight_authorized = _latest_value(
        audit_text,
        "default_off_shadow_selector_runtime_shadow_replay_preflight_authorized",
    )
    audit_runtime_authorized = _latest_value(
        audit_text,
        "default_off_shadow_selector_runtime_execution_authorized",
    )
    audit_safety_claim = _latest_value(
        audit_text,
        "safety_benefit_claim_authorized",
    )
    audit_camp_claim = _latest_value(
        audit_text,
        "camp_over_dp_top1_claim_authorized",
    )

    add(_check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"))
    add(_expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", audit_status, expected_current_status))
    add(_expect("audit_latest_next_work", audit_next, authorized_current_work))
    add(_expect("status_doc_latest_status", status_doc_status, expected_current_status))
    add(_expect("status_doc_latest_next_work", status_doc_next, authorized_current_work))
    add(_expect("audit_preflight_authorized", audit_preflight_authorized, "True"))
    add(_expect("audit_runtime_execution_not_yet_authorized", audit_runtime_authorized, "False"))
    add(_expect("audit_safety_claim_blocked", audit_safety_claim, "False"))
    add(_expect("audit_camp_over_dp_top1_claim_blocked", audit_camp_claim, "False"))

    add(_expect("runtime_manifest_readable", manifest_error, None))
    add(_check("runtime_manifest_sha256_valid", manifest_sha is not None and _is_sha256(manifest_sha), manifest_sha, "sha256"))
    if expected_runtime_manifest_sha256 is not None:
        add(_expect("runtime_manifest_expected_sha256", manifest_sha, expected_runtime_manifest_sha256))
    add(_expect("manifest_schema", manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION))
    add(_expect("manifest_role", manifest.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"))
    add(_expect("manifest_source_scope", manifest.get("source_scope"), SOURCE_SCOPE))
    add(_expect("manifest_default_off", manifest.get("default_off"), True))
    add(_expect("manifest_fail_closed", manifest.get("fail_closed"), True))
    add(_expect("manifest_selection_effect_false", manifest.get("selection_effect"), False))
    add(_expect("manifest_online_selector_change_false", manifest.get("online_selector_change"), False))
    add(_expect("manifest_selector_mode", manifest.get("selector_mode"), "static"))
    add(_expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("manifest_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"))
    add(_expect("manifest_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT))
    add(_expect("manifest_atom_count", manifest.get("atom_count"), EXPECTED_ATOM_COUNT))
    add(_expect("manifest_atom_schema", manifest.get("atom_schema_version"), ATOM_SCHEMA_VERSION))
    add(_expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD))
    add(_expect("manifest_current_dp_head", manifest.get("current_dp_head"), FIXED_DP_HEAD))
    add(_check("manifest_current_camp_head_is_sha", _is_git_sha(str(manifest.get("current_camp_head", ""))), manifest.get("current_camp_head"), "40-char git sha"))
    add(_expect("manifest_artifact_keys", sorted(artifacts), sorted(RUNTIME_ENTRIES)))

    authorizations = _dict(manifest.get("authorizations"))
    for name in BLOCKED_AUTHORIZATIONS:
        add(_expect(f"manifest_{name}_false", authorizations.get(name), False))
    add(_expect("manifest_training_executed_false", authorizations.get("training_executed"), False))

    for logical_name, entry, path in (
        ("atom_scales", atom_entry, atom_scales_path),
        ("static_weights", weights_entry, static_weights_path),
    ):
        expected_sha = entry.get("sha256")
        add(_expect(f"{logical_name}_logical_name", entry.get("logical_name"), logical_name))
        add(_expect(f"{logical_name}_required", entry.get("required"), True))
        add(_check(f"{logical_name}_sha256_valid", _is_sha256(expected_sha), expected_sha, "sha256"))
        add(_check(f"{logical_name}_path_exists", path.is_file(), str(path), "existing file"))
        if path.is_file() and _is_sha256(expected_sha):
            add(_expect(f"{logical_name}_sha256_matches", _sha256(path), expected_sha))

    add(_expect("atom_scales_loadable", atom_review.get("loadable"), True))
    add(_expect("atom_scales_length", atom_review.get("length"), EXPECTED_ATOM_COUNT))
    add(_expect("atom_scales_all_positive_finite", atom_review.get("all_positive_finite"), True))
    add(_expect("static_weights_loadable", weights_review.get("loadable"), True))
    add(_expect("static_weights_length", weights_review.get("length"), EXPECTED_ATOM_COUNT))
    add(_expect("static_weights_all_finite", weights_review.get("all_finite"), True))
    add(_expect("static_weights_nonnegative", weights_review.get("nonnegative"), True))
    add(_check("static_weights_simplex_sum", abs(float(weights_review.get("sum", math.nan)) - 1.0) <= 1e-6, weights_review.get("sum"), "1.0 +/- 1e-6"))

    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("assets_dir_exists", assets_dir.is_dir(), True))
    add(_expect("dp_python_exists", dp_python.is_file(), True))
    add(_expect("replay_script_exists", runner_path.is_file(), True))
    add(_expect("reward_config_exists", (camp_repo / REWARD_CONFIG).is_file(), True))
    add(_expect("dp_replay_config_exists", (dp_repo / DP_REPLAY_CONFIG).is_file(), True))
    add(_expect("replay_output_root_absent", replay_output_root.exists(), False))

    for asset in EXPECTED_PUBLIC_ASSETS:
        path = assets_dir / str(asset["relative_path"])
        add(_expect(f"asset_exists_{asset['name']}", path.is_file(), True))
        add(_expect(f"asset_sha256_{asset['name']}", _sha256(path) if path.is_file() else None, asset["sha256"]))

    add(_contains("runner_has_shadow_flag", runner_text, "--camp_default_off_shadow_selector"))
    add(_contains("runner_has_shadow_manifest_arg", runner_text, "--camp_shadow_artifact_manifest"))
    add(_contains("runner_has_expected_atom_scales_sha_arg", runner_text, "--camp_shadow_expected_atom_scales_sha256"))
    add(_contains("runner_has_expected_static_weights_sha_arg", runner_text, "--camp_shadow_expected_static_weights_sha256"))
    add(_contains("runner_loads_shadow_manifest", runner_text, "def _load_shadow_artifact_manifest"))
    add(_contains("runner_records_shadow_selected_index", runner_text, "shadow_selected_index"))
    add(_contains("runner_forces_dp_top1_policy", runner_text, '"executed_output_policy": "dp_top1"'))
    add(_contains("runner_rejects_incompatible_shadow_flags", runner_text, "cannot be combined"))

    add(_expect("steps_per_command", steps, EXPECTED_STEPS_PER_LOG))
    add(_expect("num_candidates_8", num_candidates, EXPECTED_CANDIDATE_COUNT))
    add(_expect("max_npcs_nonnegative", max_npcs >= 0, True))
    add(_expect("spawn_probability_valid", math.isfinite(spawn_probability) and 0.0 <= spawn_probability <= 1.0, True))
    add(_expect("formal_seeds_forbidden", bool(set(seeds) & FORMAL_SEEDS), False))
    add(_expect("traffic_light_modes_valid", set(traffic_light_modes) <= {"on", "off"}, True))
    add(_expect("planned_command_count", len(planned_commands), EXPECTED_LOG_COUNT))
    add(_expect("expected_records", len(planned_commands) * steps, EXPECTED_RECORDS))

    for command in planned_commands:
        add(_expect("command_uses_replay_script", str(camp_repo / REPLAY_SCRIPT) in command, True))
        add(_expect("command_uses_static_shadow_selector", _option_value(command, "--camp_selector_mode"), "static"))
        add(_expect("command_logs_candidate_tensor_provenance", "--camp_candidate_tensor_provenance_logging" in command, True))
        add(_expect("command_enables_default_off_shadow_selector", "--camp_default_off_shadow_selector" in command, True))
        add(_expect("command_has_shadow_artifact_manifest", _option_value(command, "--camp_shadow_artifact_manifest"), str(runtime_manifest_json)))
        add(_expect("command_static_weights_from_manifest", _option_value(command, "--camp_static_weights"), str(static_weights_path)))
        add(_expect("command_atom_scales_from_manifest", _option_value(command, "--camp_atom_scales"), str(atom_scales_path)))
        add(_expect("command_fallback_mode_top1", _option_value(command, "--camp_fallback_mode"), "top1"))
        add(_expect("command_feasibility_source_dp_reward", _option_value(command, "--camp_feasibility_source"), "dp_reward"))
        add(_expect("command_has_num_candidates_8", _option_value(command, "--num_candidates"), "8"))
        add(_expect("command_has_steps_100", _option_value(command, "--steps"), str(EXPECTED_STEPS_PER_LOG)))
    for snippet in FORBIDDEN_COMMAND_SNIPPETS:
        add(_expect(f"planned_commands_forbid_{_slug(snippet)}", snippet in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_11", "--seed 11" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_12", "--seed 12" in command_text, False))
    add(_expect("planned_commands_do_not_use_formal_seed_13", "--seed 13" in command_text, False))
    add(_expect("authorized_next_work_is_execution_only", authorized_next_work, AUTHORIZED_NEXT_WORK))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    enabled: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "enabled": enabled,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "shadow_replay_execution_authorized_next": bool(passed),
        "runtime_shadow_selector_execution_authorized_by_this_gate": False,
        "replay_execution_performed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "training_executed": False,
        "online_selector_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "executed_output_policy": "dp_top1",
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _blocked_actions() -> dict[str, bool]:
    return {
        "runtime_shadow_selector_execution_authorized_by_this_gate": False,
        "replay_execution_performed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "training_executed": False,
        "online_selector_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("shadow_replay_preflight"))
    failed = ",".join(str(item) for item in _list(decision.get("failed_checks")))
    lines = [
        "# V14 Default-Off Selector Runtime Shadow Replay Preflight",
        "",
        f"- Status: `{decision.get('status')}`",
        f"- Passed: `{decision.get('passed')}`",
        f"- Authorized next work: `{decision.get('authorized_next_work')}`",
        f"- Failure class: `{decision.get('failure_class')}`",
        f"- Failed checks: `{failed}`",
        f"- Planned commands: `{preflight.get('planned_command_count')}`",
        f"- Expected records: `{preflight.get('expected_records')}`",
        f"- Runtime manifest SHA256: `{preflight.get('runtime_manifest_sha256')}`",
        "",
        "This is a static preflight only. It creates a guarded runbook but does "
        "not execute replay, generate candidates, train CAMP, modify DP, "
        "promote, deploy, or authorize safety/CAMP-over-DP claims.",
        "",
        "CAMP remains a default-off shadow reranker over the fixed DP candidate "
        "tensor. The executed trajectory policy remains DP Top-1.",
    ]
    return "\n".join(lines) + "\n"


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
        "# Generated by the v14 default-off selector runtime shadow replay preflight.",
        "# Execute only after the v14 EOF authorizes runtime shadow replay execution.",
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
        lines.append(f"echo 'Running runtime default-off shadow replay command {index}/{len(commands)}'")
        lines.append(" ".join(_shell_quote(str(part)) for part in command))
        lines.append("")
    return "\n".join(lines)


def _review_atom_scales(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            raw = payload.get("scales")
        else:
            raw = payload
        values = np.asarray(raw, dtype=np.float64).reshape(-1)
        return {
            "loadable": True,
            "length": int(values.size),
            "all_positive_finite": bool(values.size and np.all(np.isfinite(values)) and np.all(values > 0.0)),
            "min": float(np.min(values)) if values.size else math.nan,
            "max": float(np.max(values)) if values.size else math.nan,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {
            "loadable": False,
            "error": type(exc).__name__,
            "length": 0,
            "all_positive_finite": False,
        }


def _review_static_weights(path: Path) -> dict[str, Any]:
    try:
        values = np.asarray(np.load(path), dtype=np.float64).reshape(-1)
        return {
            "loadable": True,
            "length": int(values.size),
            "sum": float(np.sum(values)) if values.size else math.nan,
            "min": float(np.min(values)) if values.size else math.nan,
            "max": float(np.max(values)) if values.size else math.nan,
            "all_finite": bool(values.size and np.all(np.isfinite(values))),
            "nonnegative": bool(values.size and np.all(values >= 0.0)),
        }
    except (OSError, ValueError, TypeError) as exc:
        return {
            "loadable": False,
            "error": type(exc).__name__,
            "length": 0,
            "sum": math.nan,
            "all_finite": False,
            "nonnegative": False,
        }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("manifest_" in check or "runtime_manifest" in check for check in failed):
        return "runtime_manifest_contract_failure"
    if any("asset_" in check or "repo_exists" in check for check in failed):
        return "public_simulator_asset_or_repo_contract_failure"
    if any("weights" in check or "scales" in check or "atom_" in check for check in failed):
        return "runtime_artifact_weight_or_atom_contract_failure"
    if any("formal_seed" in check or "forbid" in check or "command_" in check for check in failed):
        return "forbidden_shadow_replay_command_contract_failure"
    if any("replay_output_root" in check for check in failed):
        return "shadow_replay_preflight_output_not_fresh"
    return "runtime_shadow_replay_preflight_contract_failure"


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, "missing"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "unreadable"
    if not isinstance(loaded, dict):
        return {}, "not_object"
    return loaded, None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


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


def _option_value(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return command[index + 1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_stable(value), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(path: Path, files: list[Path]) -> None:
    lines = []
    for file_path in files:
        lines.append(f"{_sha256(file_path)}  {file_path.name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value.lower()
    )


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
