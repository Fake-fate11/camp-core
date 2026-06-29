#!/usr/bin/env python3
"""Preflight shadow replay/evaluation for a trained v13 static DP-reward artifact.

This is a planning/materialization gate only. It validates an existing static
training artifact, writes a default-off runtime manifest for those fixed
weights/scales, and builds a replay runbook. It does not execute replay,
generate candidates, train CAMP, modify Diffusion Planner, promote artifacts,
deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402


SCHEMA_VERSION = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_preflight_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
DISABLED_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_preflight_disabled"
)
READY_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_preflight_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_static_dp_reward_training_artifact_"
    "shadow_replay_evaluation_execution_only"
)
AUTHORIZED_PREFLIGHT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_static_dp_reward_training_artifact_"
    "shadow_replay_evaluation_preflight_only"
)
LATEST_ALLOWED_STATUS = (
    "current_source_large_default_off_shadow_selector_broader_nonformal_"
    "shadow_replay_batch_static_dp_reward_training_execution_passed"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FORMAL_SEEDS = (11, 12, 13)
FORBIDDEN_COMMAND_FLAGS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
    "--camp_collect_closed_loop_outcomes",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static preflight for evaluating a trained v13 static DP-reward "
            "CAMP artifact in default-off shadow replay."
        )
    )
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--static_weights_npy", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--route", action="append", required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--base_replay_output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--seeds", default="301,302")
    parser.add_argument("--formal_seeds", default="11,12,13")
    parser.add_argument("--max_npcs_values", default="0,4")
    parser.add_argument("--spawn_probability", type=float, default=0.3)
    parser.add_argument("--traffic_light_modes", default="on,off")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--num_candidates", type=int, default=EXPECTED_CANDIDATE_COUNT)
    parser.add_argument("--expected_training_contract_records", type=int, default=3200)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--python_executable", default="python")
    parser.add_argument("--pythonpath", default=None)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_PREFLIGHT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--latest_allowed_status", default=LATEST_ALLOWED_STATUS)
    parser.add_argument("--output_runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_static_dp_reward_training_artifact_shadow_replay_evaluation_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        training_summary_json=args.training_summary_json,
        atom_scales_json=args.atom_scales_json,
        static_weights_npy=args.static_weights_npy,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        diffusion_repo=args.diffusion_repo,
        route_specs=tuple(args.route),
        model_path=args.model_path,
        model_args=args.model_args,
        config=args.config,
        reward_config=args.reward_config,
        base_replay_output_dir=args.base_replay_output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        seeds=_parse_ints(args.seeds),
        formal_seeds=_parse_ints(args.formal_seeds),
        max_npcs_values=_parse_ints(args.max_npcs_values),
        spawn_probability=args.spawn_probability,
        traffic_light_modes=_parse_strings(args.traffic_light_modes),
        steps=args.steps,
        num_candidates=args.num_candidates,
        expected_training_contract_records=args.expected_training_contract_records,
        device=args.device,
        python_executable=args.python_executable,
        pythonpath=args.pythonpath,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        latest_allowed_status=args.latest_allowed_status,
        output_runtime_manifest_json=args.output_runtime_manifest_json,
        enabled=bool(
            args.enable_v13_static_dp_reward_training_artifact_shadow_replay_evaluation_preflight
        ),
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
    training_summary_json: Path,
    atom_scales_json: Path,
    static_weights_npy: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
    diffusion_repo: Path,
    route_specs: tuple[str, ...],
    model_path: Path,
    model_args: Path,
    config: Path,
    reward_config: Path,
    base_replay_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    output_runtime_manifest_json: Path,
    required_dp_head: str = FIXED_DP_HEAD,
    seeds: tuple[int, ...] = (301, 302),
    formal_seeds: tuple[int, ...] = FORMAL_SEEDS,
    max_npcs_values: tuple[int, ...] = (0, 4),
    spawn_probability: float = 0.3,
    traffic_light_modes: tuple[str, ...] = ("on", "off"),
    steps: int = 100,
    num_candidates: int = EXPECTED_CANDIDATE_COUNT,
    expected_training_contract_records: int = 3200,
    device: str = "cuda",
    python_executable: str = "python",
    pythonpath: str | None = None,
    authorized_current_work: str = AUTHORIZED_PREFLIGHT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    latest_allowed_status: str = LATEST_ALLOWED_STATUS,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "static_preflight_only": True,
            "runtime_manifest_materialized_by_this_gate": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "training_execution": False,
            "dp_modification_execution": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work,
            "latest_allowed_status": latest_allowed_status,
        },
        "source_hashes": {},
        "runtime_manifest": {},
        "planned_commands": [],
        "review_checks": [],
        "final_decision": _decision(
            False,
            [],
            enabled=False,
            authorized_next_work=authorized_next_work,
        ),
    }
    if not enabled:
        report["final_decision"]["status"] = DISABLED_STATUS
        return report

    routes, route_errors = _parse_routes(route_specs)
    training_summary = _load_json(training_summary_json)
    atom_scales = _load_json(atom_scales_json)
    weights = _load_weights(static_weights_npy)
    audit_text = _read_text(v13_audit_md)
    runner_text = _read_text(replay_runner_py)
    runtime_manifest = _runtime_manifest(
        training_summary_json=training_summary_json,
        atom_scales_json=atom_scales_json,
        static_weights_npy=static_weights_npy,
        training_summary=training_summary,
        atom_scales=atom_scales,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    commands = _planned_commands(
        replay_runner_py=replay_runner_py,
        diffusion_repo=diffusion_repo,
        routes=routes,
        model_path=model_path,
        model_args=model_args,
        config=config,
        reward_config=reward_config,
        base_replay_output_dir=base_replay_output_dir,
        device=device,
        python_executable=python_executable,
        pythonpath=pythonpath,
        steps=steps,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        spawn_probability=spawn_probability,
        traffic_light_modes=traffic_light_modes,
        num_candidates=num_candidates,
        atom_scales_path=atom_scales_json,
        static_weights_path=static_weights_npy,
        runtime_manifest_json=output_runtime_manifest_json,
    )
    output_dirs = [entry["output_dir"] for entry in commands]

    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("training_summary_exists", training_summary_json.is_file(), str(training_summary_json), "file exists"),
        _check("atom_scales_exists", atom_scales_json.is_file(), str(atom_scales_json), "file exists"),
        _check("static_weights_exists", static_weights_npy.is_file(), str(static_weights_npy), "file exists"),
        _check("replay_runner_exists", replay_runner_py.is_file(), str(replay_runner_py), "file exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("runtime_manifest_output_absent", not output_runtime_manifest_json.exists(), str(output_runtime_manifest_json), "absent before preflight"),
        _check("runtime_manifest_output_is_json", str(output_runtime_manifest_json).endswith(".json"), str(output_runtime_manifest_json), "*.json"),
        _check("routes_parse", not route_errors, route_errors, []),
        _check("route_count", len(routes) >= 2, len(routes), ">= 2"),
        _check("seeds_nonempty", bool(seeds), list(seeds), "nonempty"),
        _check("seeds_exclude_formal", not set(seeds) & set(formal_seeds), list(seeds), f"exclude {formal_seeds}"),
        _check("max_npcs_values_nonempty", bool(max_npcs_values), list(max_npcs_values), "nonempty"),
        _check("max_npcs_values_nonnegative", all(value >= 0 for value in max_npcs_values), list(max_npcs_values), "all >= 0"),
        _check("traffic_light_modes_valid", set(traffic_light_modes) <= {"on", "off"}, list(traffic_light_modes), "on/off only"),
        _check("steps_positive", steps > 0, steps, "> 0"),
        _expect("num_candidates", num_candidates, EXPECTED_CANDIDATE_COUNT),
        _check("spawn_probability_in_unit_interval", 0.0 <= spawn_probability <= 1.0, spawn_probability, "[0, 1]"),
        _check("diffusion_repo_exists", diffusion_repo.is_dir(), str(diffusion_repo), "directory exists"),
        _check("model_path_exists", model_path.is_file(), str(model_path), "file exists"),
        _check("model_args_exists", model_args.is_file(), str(model_args), "file exists"),
        _check("config_exists", config.is_file(), str(config), "file exists"),
        _check("reward_config_exists", reward_config.is_file(), str(reward_config), "file exists"),
        _check("base_output_absent", not base_replay_output_dir.exists(), str(base_replay_output_dir), "absent before replay"),
        _check("command_count_positive", len(commands) > 0, len(commands), "> 0"),
        _check("command_count", len(commands) == len(routes) * len(seeds) * len(max_npcs_values) * len(traffic_light_modes), len(commands), "cartesian product"),
        _check("output_paths_unique", len(set(output_dirs)) == len(output_dirs), len(set(output_dirs)), len(output_dirs)),
        _check("all_planned_outputs_absent", all(not Path(path).exists() for path in output_dirs), output_dirs, "all absent before replay"),
    ]
    for path in (training_summary_json, atom_scales_json, static_weights_npy, replay_runner_py, v13_audit_md, model_args, reward_config):
        if path.is_file():
            report["source_hashes"][path.name] = _sha256(path)
    for route in routes:
        checks.append(_check(f"route_path_exists:{route['name']}", Path(route["path"]).is_file(), route["path"], "file exists"))
    checks.extend(
        _training_checks(
            training_summary,
            expected_contract_records=expected_training_contract_records,
        )
    )
    checks.extend(_atom_scale_checks(atom_scales))
    checks.extend(_weight_checks(weights))
    checks.extend(_runtime_manifest_checks(runtime_manifest, atom_scales_json, static_weights_npy))
    checks.extend(_runner_checks(runner_text))
    checks.extend(
        _audit_checks(
            audit_text,
            authorized_current_work=authorized_current_work,
            latest_allowed_status=latest_allowed_status,
        )
    )
    checks.extend(_batch_command_checks([entry["command"] for entry in commands]))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    if passed:
        output_runtime_manifest_json.parent.mkdir(parents=True, exist_ok=True)
        output_runtime_manifest_json.write_text(
            json.dumps(_stable(runtime_manifest), indent=2) + "\n",
            encoding="utf-8",
        )
        report["source_hashes"]["runtime_manifest_sha256"] = _sha256(output_runtime_manifest_json)
        report["analysis"]["runtime_manifest_materialized_by_this_gate"] = True
    report["runtime_manifest"] = runtime_manifest if passed else {}
    report["planned_commands"] = commands
    report["review_checks"] = checks
    report["preflight"] = {
        "routes": routes,
        "route_names": sorted(route["name"] for route in routes),
        "seeds": list(seeds),
        "formal_seeds": list(formal_seeds),
        "formal_seeds_excluded": not set(seeds) & set(formal_seeds),
        "max_npcs_values": list(max_npcs_values),
        "spawn_probability": spawn_probability,
        "traffic_light_modes": list(traffic_light_modes),
        "steps": steps,
        "num_candidates": num_candidates,
        "command_count": len(commands),
        "expected_records": len(commands) * steps,
        "base_replay_output_dir": str(base_replay_output_dir),
        "runtime_manifest_json": str(output_runtime_manifest_json),
        "static_weights": str(static_weights_npy),
        "atom_scales": str(atom_scales_json),
        "python_executable": python_executable,
        "pythonpath": pythonpath,
    }
    report["final_decision"] = _decision(
        passed,
        failed,
        enabled=True,
        authorized_next_work=authorized_next_work,
    )
    return report


def _runtime_manifest(
    *,
    training_summary_json: Path,
    atom_scales_json: Path,
    static_weights_npy: Path,
    training_summary: dict[str, Any],
    atom_scales: dict[str, Any],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    artifacts = {
        "atom_scales": {
            "logical_name": "atom_scales",
            "path": str(atom_scales_json),
            "sha256": _sha256(atom_scales_json) if atom_scales_json.is_file() else None,
            "required": True,
        },
        "static_weights": {
            "logical_name": "static_weights",
            "path": str(static_weights_npy),
            "sha256": _sha256(static_weights_npy) if static_weights_npy.is_file() else None,
            "required": True,
        },
    }
    return {
        "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "label": "v13_current_source_large_static_dp_reward_training_artifact",
        "default_off": True,
        "selection_effect": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "atom_count": EXPECTED_ATOM_COUNT,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": list(atom_schema_for_dimension(EXPECTED_ATOM_COUNT)[1]),
        "score_expression": SCORE_EXPRESSION,
        "required_dp_head": FIXED_DP_HEAD,
        "current_dp_head": current_dp_head,
        "current_camp_head": current_camp_head,
        "training_summary": {
            "path": str(training_summary_json),
            "sha256": _sha256(training_summary_json) if training_summary_json.is_file() else None,
            "label_source": training_summary.get("label_source"),
            "reward_key": training_summary.get("reward_key"),
            "reward_progress_weight": training_summary.get("reward_progress_weight"),
            "num_records": training_summary.get("num_records"),
            "dropped_records_without_feasible_candidate": training_summary.get("dropped_records_without_feasible_candidate"),
        },
        "artifacts": artifacts,
        "sha256": {
            "atom_scales": artifacts["atom_scales"]["sha256"],
            "static_weights": artifacts["static_weights"]["sha256"],
            str(atom_scales_json): artifacts["atom_scales"]["sha256"],
            str(static_weights_npy): artifacts["static_weights"]["sha256"],
        },
        "authorizations": _blocked_actions(training_executed=True),
    }


def _planned_commands(
    *,
    replay_runner_py: Path,
    diffusion_repo: Path,
    routes: list[dict[str, str]],
    model_path: Path,
    model_args: Path,
    config: Path,
    reward_config: Path,
    base_replay_output_dir: Path,
    device: str,
    python_executable: str,
    pythonpath: str | None,
    steps: int,
    seeds: tuple[int, ...],
    max_npcs_values: tuple[int, ...],
    spawn_probability: float,
    traffic_light_modes: tuple[str, ...],
    num_candidates: int,
    atom_scales_path: Path,
    static_weights_path: Path,
    runtime_manifest_json: Path,
) -> list[dict[str, Any]]:
    planned = []
    for route, seed, max_npcs, traffic_lights in itertools.product(
        routes,
        seeds,
        max_npcs_values,
        traffic_light_modes,
    ):
        tl_dir = "tl_on" if traffic_lights == "on" else "tl_off"
        output_dir = (
            base_replay_output_dir
            / route["name"]
            / f"seed_{seed}"
            / f"npc_{max_npcs}"
            / "spawn_0p3"
            / tl_dir
            / "static_shadow"
        )
        command = []
        if pythonpath:
            command.extend(["env", f"PYTHONPATH={pythonpath}"])
        command.extend(
            [
                python_executable,
                str(replay_runner_py),
            ]
        )
        command.extend([
            "--diffusion_repo",
            str(diffusion_repo),
            "--route",
            route["path"],
            "--model_path",
            str(model_path),
            "--model_args",
            str(model_args),
            "--config",
            str(config),
            "--reward_config",
            str(reward_config),
            "--output_dir",
            str(output_dir),
            "--device",
            device,
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
            "--camp_fallback_mode",
            "learned",
            "--camp_feasibility_source",
            "dp_reward",
            "--camp_atom_scales",
            str(atom_scales_path),
            "--camp_static_weights",
            str(static_weights_path),
            "--camp_default_off_shadow_selector",
            "--camp_shadow_artifact_manifest",
            str(runtime_manifest_json),
            "--num_candidates",
            str(num_candidates),
        ])
        planned.append(
            {
                "route_name": route["name"],
                "route_path": route["path"],
                "seed": seed,
                "max_npcs": max_npcs,
                "traffic_lights": traffic_lights,
                "output_dir": str(output_dir),
                "command": command,
            }
        )
    return planned


def _training_checks(
    summary: dict[str, Any],
    *,
    expected_contract_records: int,
) -> list[dict[str, Any]]:
    contract = summary.get("dp_native_training_data_contract")
    if not isinstance(contract, dict):
        contract = {}
    return [
        _expect("training_label_source", summary.get("label_source"), "dp_reward"),
        _expect("training_reward_key", summary.get("reward_key"), "quality_without_progress"),
        _expect("training_reward_progress_weight", summary.get("reward_progress_weight"), 2.0),
        _expect("training_num_candidates", summary.get("num_candidates"), EXPECTED_CANDIDATE_COUNT),
        _expect("training_num_atoms", summary.get("num_atoms"), EXPECTED_ATOM_COUNT),
        _expect("training_atom_schema", summary.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _check("training_records_positive", int(summary.get("num_records", 0)) > 0, summary.get("num_records"), "> 0"),
        _expect("training_contract_passed", contract.get("passed"), True),
        _expect("training_contract_records", contract.get("records"), expected_contract_records),
        _expect("training_no_closed_loop_label", summary.get("label_source") != "closed_loop_outcome", True),
        _expect("training_no_safety_cost_label", summary.get("label_source") != "safety_cost_v1_hard_guarded", True),
    ]


def _atom_scale_checks(scales: dict[str, Any]) -> list[dict[str, Any]]:
    values = _float_array(scales.get("scales"))
    expected_names = list(atom_schema_for_dimension(EXPECTED_ATOM_COUNT)[1])
    return [
        _expect("scales_atom_schema", scales.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("scales_atom_names", scales.get("atom_names"), expected_names),
        _expect("scales_shape", list(values.shape), [EXPECTED_ATOM_COUNT]),
        _check("scales_finite", bool(values.size and np.all(np.isfinite(values))), values.tolist() if values.size else [], "all finite"),
        _check("scales_positive", bool(values.size and np.all(values > 0.0)), values.tolist() if values.size else [], "all > 0"),
    ]


def _weight_checks(weights: np.ndarray) -> list[dict[str, Any]]:
    return [
        _expect("weights_shape", list(weights.shape), [EXPECTED_ATOM_COUNT]),
        _check("weights_finite", bool(weights.size and np.all(np.isfinite(weights))), weights.tolist() if weights.size else [], "all finite"),
        _check("weights_nonnegative", bool(weights.size and np.all(weights >= -1e-12)), weights.tolist() if weights.size else [], "all >= 0"),
        _check("weights_simplex_sum_1", bool(weights.size and abs(float(np.sum(weights)) - 1.0) <= 1e-9), float(np.sum(weights)) if weights.size else None, "sum == 1"),
    ]


def _runtime_manifest_checks(
    manifest: dict[str, Any],
    atom_scales_json: Path,
    static_weights_npy: Path,
) -> list[dict[str, Any]]:
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    atom = artifacts.get("atom_scales") if isinstance(artifacts.get("atom_scales"), dict) else {}
    weights = artifacts.get("static_weights") if isinstance(artifacts.get("static_weights"), dict) else {}
    return [
        _expect("manifest_schema", manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("manifest_default_off", manifest.get("default_off"), True),
        _expect("manifest_selection_effect", manifest.get("selection_effect"), False),
        _expect("manifest_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("manifest_executed_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("manifest_required_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("manifest_atom_count", manifest.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("manifest_atom_schema", manifest.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_atom_path", atom.get("path"), str(atom_scales_json)),
        _expect("manifest_weights_path", weights.get("path"), str(static_weights_npy)),
        _check("manifest_atom_sha", _is_sha256(atom.get("sha256")), atom.get("sha256"), "sha256"),
        _check("manifest_weights_sha", _is_sha256(weights.get("sha256")), weights.get("sha256"), "sha256"),
    ]


def _runner_checks(source: str) -> list[dict[str, Any]]:
    return [
        _contains("runner_has_shadow_flag", source, 'parser.add_argument(\n        "--camp_default_off_shadow_selector"'),
        _contains("runner_has_shadow_manifest_arg", source, 'parser.add_argument(\n        "--camp_shadow_artifact_manifest"'),
        _contains("runner_loads_artifact_manifest", source, "def _load_shadow_artifact_manifest"),
        _contains("runner_shadow_forces_dp_top1", source, '"executed_output_policy": "dp_top1"'),
        _contains("runner_records_shadow_selected_index", source, "shadow_selected_index"),
    ]


def _audit_checks(
    text: str,
    *,
    authorized_current_work: str,
    latest_allowed_status: str,
) -> list[dict[str, Any]]:
    runtime_execution = _latest_audit_value(text, "runtime_shadow_selector_execution_authorized")
    runtime_check_required = authorized_current_work == AUTHORIZED_PREFLIGHT_WORK
    return [
        _expect("audit_latest_scope_allows_preflight", _latest_audit_value(text, "next_work_target"), authorized_current_work),
        _expect("audit_latest_status_allows_preflight", _latest_audit_value(text, "current_v13_status"), latest_allowed_status),
        _check(
            "audit_latest_runtime_execution_blocked",
            (not runtime_check_required) or runtime_execution == "False",
            runtime_execution,
            "False" if runtime_check_required else "not required for parameterized gate",
        ),
        _expect("audit_latest_replay_execution_blocked", _latest_audit_value(text, "replay_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_latest_candidate_generation_blocked", _latest_audit_value(text, "fixed_dp_candidate_generation_authorized_by_current_boundary"), "False"),
    ]


def _batch_command_checks(commands: list[list[str]]) -> list[dict[str, Any]]:
    joined = "\n".join(" ".join(command) for command in commands)
    return [
        _check("all_commands_use_shadow_selector", all("--camp_default_off_shadow_selector" in command for command in commands), joined, "shadow flag in all"),
        _check("all_commands_use_shadow_manifest", all("--camp_shadow_artifact_manifest" in command for command in commands), joined, "manifest flag in all"),
        _check("all_commands_selector_mode_static", all(_argument_value(command, "--camp_selector_mode") == "static" for command in commands), joined, "static"),
        _check("all_commands_fallback_mode_learned", all(_argument_value(command, "--camp_fallback_mode") == "learned" for command in commands), joined, "learned"),
        _check("all_commands_feasibility_source_dp_reward", all(_argument_value(command, "--camp_feasibility_source") == "dp_reward" for command in commands), joined, "dp_reward"),
        _check("all_commands_have_reward_config", all("--reward_config" in command for command in commands), joined, "reward config"),
        _check("all_commands_have_model_args", all("--model_args" in command for command in commands), joined, "model args"),
        _check("all_commands_num_candidates_8", all(_argument_value(command, "--num_candidates") == str(EXPECTED_CANDIDATE_COUNT) for command in commands), joined, "8"),
        _check("all_commands_no_forbidden_flags", all(all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS) for command in commands), joined, "no forbidden flags"),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report.get("preflight", {})
    lines = [
        "# V13 Static DP-Reward Artifact Shadow Replay Evaluation Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{','.join(decision['failed_checks'])}`",
        f"- Runtime manifest written: `{decision['runtime_manifest_written']}`",
        f"- Command count: `{preflight.get('command_count')}`",
        f"- Expected records: `{preflight.get('expected_records')}`",
        "",
        "This is a static preflight only. It does not execute replay, generate "
        "candidates, train CAMP, modify DP, promote, deploy, or authorize "
        "safety/CAMP-over-DP claims.",
        "",
    ]
    return "\n".join(lines)


def render_runbook(report: dict[str, Any]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated preflight runbook. Do not execute unless the audit EOF authorizes shadow replay/evaluation execution.",
    ]
    for index, entry in enumerate(report.get("planned_commands", []), start=1):
        lines.extend(
            [
                "",
                f"# command {index}: {entry['route_name']} seed={entry['seed']} npc={entry['max_npcs']} tl={entry['traffic_lights']}",
                _shell_join(entry["command"]),
            ]
        )
    return "\n".join(lines) + "\n"


def _decision(
    passed: bool,
    failed_checks: list[str],
    *,
    enabled: bool,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "enabled": bool(enabled),
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": authorized_next_work if passed else None,
        "runtime_manifest_written": bool(passed),
        "shadow_replay_evaluation_execution_authorized_next": bool(passed),
        "runtime_shadow_selector_execution_authorized_by_this_gate": False,
        "replay_execution_performed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "training_executed": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _blocked_actions(*, training_executed: bool) -> dict[str, bool]:
    return {
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "training_executed": bool(training_executed),
    }


def _parse_routes(specs: tuple[str, ...]) -> tuple[list[dict[str, str]], list[str]]:
    routes: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for spec in specs:
        if "=" not in spec:
            errors.append(f"route_missing_equals:{spec}")
            continue
        name, path = (part.strip() for part in spec.split("=", 1))
        if not name or not path:
            errors.append(f"route_empty_name_or_path:{spec}")
            continue
        if name in seen:
            errors.append(f"route_duplicate:{name}")
            continue
        seen.add(name)
        routes.append({"name": name, "path": path})
    return routes, errors


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _load_weights(path: Path) -> np.ndarray:
    if not path.is_file():
        return np.asarray([], dtype=np.float64)
    return np.asarray(np.load(path), dtype=np.float64)


def _float_array(value: Any) -> np.ndarray:
    try:
        return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return np.asarray([], dtype=np.float64)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _latest_audit_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def _argument_value(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    value_index = index + 1
    if value_index >= len(command):
        return None
    return command[value_index]


def _shell_join(command: list[str]) -> str:
    def quote(arg: str) -> str:
        if not arg:
            return "''"
        safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/.:=+"
        if all(ch in safe for ch in arg):
            return arg
        return "'" + arg.replace("'", "'\\''") + "'"

    return " ".join(quote(str(arg)) for arg in command)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if isinstance(value, np.generic):
        return value.item()
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value.lower()
    )


if __name__ == "__main__":
    raise SystemExit(main())
