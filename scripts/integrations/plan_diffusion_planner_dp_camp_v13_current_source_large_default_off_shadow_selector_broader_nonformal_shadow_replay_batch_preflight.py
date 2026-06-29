#!/usr/bin/env python3
"""Preflight a broader v13 current-source-large CAMP shadow replay batch.

This tool is deliberately static. It validates fixed artifacts, builds a
runbook of replay commands, and writes JSON/Markdown reports. It does not
execute replay, generate candidates, train CAMP, modify Diffusion Planner,
promote selectors/atoms, deploy, or make safety claims.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_preflight_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_preflight_disabled"
)
READY_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_preflight_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_execution_only"
)
AUTHORIZED_PREFLIGHT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "broader_nonformal_shadow_replay_batch_preflight_only"
)
AUTHORIZED_RESULT_REVIEW_PREFLIGHT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_and_broader_nonformal_preflight_only"
)
ALLOWED_PREFLIGHT_WORK = (
    AUTHORIZED_PREFLIGHT_WORK,
    AUTHORIZED_RESULT_REVIEW_PREFLIGHT_WORK,
)
LATEST_ALLOWED_STATUS = (
    "current_source_large_default_off_shadow_selector_runtime_shadow_replay_smoke_execution_passed"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
FORMAL_SEEDS = (11, 12, 13)
FORBIDDEN_COMMAND_FLAGS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static preflight for a broader current-source-large default-off "
            "CAMP shadow replay batch. Writes reports only."
        )
    )
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--runtime_shadow_replay_execution_artifact_dir", type=Path)
    parser.add_argument("--runtime_shadow_replay_output_dir", type=Path)
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
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report(
        runtime_manifest_json=args.runtime_manifest_json,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        runtime_shadow_replay_execution_artifact_dir=(
            args.runtime_shadow_replay_execution_artifact_dir
        ),
        runtime_shadow_replay_output_dir=args.runtime_shadow_replay_output_dir,
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
        device=args.device,
        enabled=bool(
            args.enable_v13_current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_runbook.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    args.output_runbook.write_text(_runbook(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_manifest_json: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
    runtime_shadow_replay_execution_artifact_dir: Path | None = None,
    runtime_shadow_replay_output_dir: Path | None = None,
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
    required_dp_head: str = FIXED_DP_HEAD,
    seeds: tuple[int, ...] = (301, 302),
    formal_seeds: tuple[int, ...] = FORMAL_SEEDS,
    max_npcs_values: tuple[int, ...] = (0, 4),
    spawn_probability: float = 0.3,
    traffic_light_modes: tuple[str, ...] = ("on", "off"),
    steps: int = 100,
    num_candidates: int = EXPECTED_CANDIDATE_COUNT,
    device: str = "cuda",
    enabled: bool,
) -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "static_preflight_only": True,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "training_execution": False,
            "dp_modification_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "blocked_actions": _blocked_actions(),
        "planned_commands": [],
        "review_checks": [],
    }
    if not enabled:
        base["final_decision"] = _decision(False, [], enabled=False)
        base["final_decision"]["status"] = DISABLED_STATUS
        return base

    routes, route_errors = _parse_routes(route_specs)
    manifest, manifest_error = _load_json(runtime_manifest_json, "runtime_manifest")
    runner_text = _read_text(replay_runner_py)
    audit_text = _read_text(v13_audit_md)
    latest_next_work = _latest_audit_value(audit_text, "next_work_target")
    smoke_result_review_required = (
        latest_next_work == AUTHORIZED_RESULT_REVIEW_PREFLIGHT_WORK
    )
    smoke_static_audit_path = (
        runtime_shadow_replay_execution_artifact_dir / "execution_static_audit.json"
        if runtime_shadow_replay_execution_artifact_dir is not None
        else None
    )
    smoke_static_audit, smoke_static_audit_error = (
        _load_json(smoke_static_audit_path, "runtime_shadow_replay_execution_static_audit")
        if smoke_static_audit_path is not None
        else ({}, "runtime_shadow_replay_execution_static_audit_missing")
    )
    artifacts = _dict(manifest.get("artifacts"))
    atom_scales = _dict(artifacts.get("atom_scales"))
    static_weights = _dict(artifacts.get("static_weights"))
    atom_scales_path = Path(str(atom_scales.get("path", "")))
    static_weights_path = Path(str(static_weights.get("path", "")))
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
        steps=steps,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        spawn_probability=spawn_probability,
        traffic_light_modes=traffic_light_modes,
        num_candidates=num_candidates,
        atom_scales_path=atom_scales_path,
        static_weights_path=static_weights_path,
        runtime_manifest_json=runtime_manifest_json,
    )
    output_dirs = [entry["output_dir"] for entry in commands]
    command_lists = [entry["command"] for entry in commands]

    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
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
        _check("runtime_manifest_readable", manifest_error is None, manifest_error, None),
        _expect("manifest_schema", manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("manifest_default_off", manifest.get("default_off"), True),
        _expect("manifest_selection_effect", manifest.get("selection_effect"), False),
        _expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("manifest_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("manifest_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("manifest_required_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("manifest_current_dp_head", manifest.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_artifact_keys", sorted(artifacts.keys()), ["atom_scales", "static_weights"]),
        _check("command_count", len(commands) == len(routes) * len(seeds) * len(max_npcs_values) * len(traffic_light_modes), len(commands), "cartesian product"),
        _check("command_count_positive", len(commands) > 0, len(commands), "> 0"),
        _check("output_paths_unique", len(set(output_dirs)) == len(output_dirs), len(set(output_dirs)), len(output_dirs)),
        _check("all_planned_outputs_absent", all(not Path(path).exists() for path in output_dirs), output_dirs, "all absent before replay"),
    ]
    checks.extend(
        _smoke_result_review_checks(
            required=smoke_result_review_required,
            execution_artifact_dir=runtime_shadow_replay_execution_artifact_dir,
            replay_output_dir=runtime_shadow_replay_output_dir,
            static_audit_path=smoke_static_audit_path,
            static_audit=smoke_static_audit,
            static_audit_error=smoke_static_audit_error,
        )
    )
    for route in routes:
        checks.append(_check(f"route_path_exists:{route['name']}", Path(route["path"]).is_file(), route["path"], "file exists"))
    checks.extend(_artifact_checks("atom_scales", atom_scales))
    checks.extend(_artifact_checks("static_weights", static_weights))
    checks.extend(_runner_checks(runner_text))
    checks.extend(_audit_checks(audit_text))
    checks.extend(_batch_command_checks(command_lists))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    base.update(
        {
            "source_hashes": {
                "runtime_manifest_sha256": _sha256(runtime_manifest_json) if runtime_manifest_json.is_file() else None,
                "replay_runner_sha256": _sha256(replay_runner_py) if replay_runner_py.is_file() else None,
                "v13_audit_sha256": _sha256(v13_audit_md) if v13_audit_md.is_file() else None,
                "model_args_sha256": _sha256(model_args) if model_args.is_file() else None,
                "reward_config_sha256": _sha256(reward_config) if reward_config.is_file() else None,
            },
            "preflight": {
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
                "base_replay_output_dir": str(base_replay_output_dir),
                "command_count": len(commands),
                "expected_records": len(commands) * steps,
                "expected_shadow_records": len(commands) * steps,
                "runtime_manifest": str(runtime_manifest_json),
                "manifest_sha256": _sha256(runtime_manifest_json) if runtime_manifest_json.is_file() else None,
                "atom_scales_path": str(atom_scales_path),
                "atom_scales_sha256": atom_scales.get("sha256"),
                "static_weights_path": str(static_weights_path),
                "static_weights_sha256": static_weights.get("sha256"),
                "all_planned_outputs_absent": all(not Path(path).exists() for path in output_dirs),
                "output_paths_unique": len(set(output_dirs)) == len(output_dirs),
            },
            "runtime_shadow_replay_result_review": _smoke_result_review_summary(
                required=smoke_result_review_required,
                execution_artifact_dir=runtime_shadow_replay_execution_artifact_dir,
                replay_output_dir=runtime_shadow_replay_output_dir,
                static_audit_path=smoke_static_audit_path,
                static_audit=smoke_static_audit,
            ),
            "planned_commands": commands,
            "review_checks": checks,
            "final_decision": _decision(passed, failed, enabled=True),
        }
    )
    return base


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
    planned: list[dict[str, Any]] = []
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
        command = [
            "python",
            str(replay_runner_py),
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
        ]
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


def _artifact_checks(name: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    path_text = entry.get("path")
    expected_sha = entry.get("sha256")
    path = Path(str(path_text or ""))
    checks = [
        _expect(f"{name}_logical_name", entry.get("logical_name"), name),
        _expect(f"{name}_required", entry.get("required"), True),
        _check(f"{name}_sha256_valid", _is_sha256(expected_sha), expected_sha, "sha256"),
        _check(f"{name}_path_exists", path.is_file(), str(path), "file exists"),
    ]
    if path.is_file() and _is_sha256(expected_sha):
        checks.append(_expect(f"{name}_sha256_matches", _sha256(path), expected_sha))
    return checks


def _runner_checks(source: str) -> list[dict[str, Any]]:
    return [
        _contains("runner_has_shadow_flag", source, 'parser.add_argument(\n        "--camp_default_off_shadow_selector"'),
        _contains("runner_has_shadow_manifest_arg", source, 'parser.add_argument(\n        "--camp_shadow_artifact_manifest"'),
        _contains("runner_loads_artifact_manifest", source, "def _load_shadow_artifact_manifest"),
        _contains("runner_expected_sha_lookup", source, "def _manifest_expected_sha256"),
        _contains("runner_shadow_forces_dp_top1", source, '"executed_output_policy": "dp_top1"'),
        _contains("runner_records_shadow_selected_index", source, "shadow_selected_index"),
        _contains("runner_rejects_incompatible_shadow_flags", source, "--camp_default_off_shadow_selector cannot be combined"),
    ]


def _smoke_result_review_checks(
    *,
    required: bool,
    execution_artifact_dir: Path | None,
    replay_output_dir: Path | None,
    static_audit_path: Path | None,
    static_audit: dict[str, Any],
    static_audit_error: str | None,
) -> list[dict[str, Any]]:
    if not required:
        return []
    audit_checks = _dict(static_audit.get("checks"))
    expected_counts = {"0": 100}
    checks = [
        _check(
            "runtime_shadow_replay_result_review_execution_artifact_dir_provided",
            execution_artifact_dir is not None,
            str(execution_artifact_dir) if execution_artifact_dir is not None else None,
            "provided",
        ),
        _check(
            "runtime_shadow_replay_result_review_output_dir_provided",
            replay_output_dir is not None,
            str(replay_output_dir) if replay_output_dir is not None else None,
            "provided",
        ),
        _check(
            "runtime_shadow_replay_result_review_execution_artifact_dir_exists",
            execution_artifact_dir is not None and execution_artifact_dir.is_dir(),
            str(execution_artifact_dir) if execution_artifact_dir is not None else None,
            "directory exists",
        ),
        _check(
            "runtime_shadow_replay_result_review_output_dir_exists",
            replay_output_dir is not None and replay_output_dir.is_dir(),
            str(replay_output_dir) if replay_output_dir is not None else None,
            "directory exists",
        ),
        _check(
            "runtime_shadow_replay_result_review_static_audit_readable",
            static_audit_error is None,
            static_audit_error,
            None,
        ),
        _expect("runtime_shadow_replay_result_review_static_audit_passed", static_audit.get("passed"), True),
        _expect("runtime_shadow_replay_result_review_static_audit_failed_checks", static_audit.get("failed_checks"), []),
        _expect(
            "runtime_shadow_replay_result_review_authorized_next_work",
            static_audit.get("authorized_next_work"),
            AUTHORIZED_RESULT_REVIEW_PREFLIGHT_WORK,
        ),
        _expect("runtime_shadow_replay_result_review_selection_log_count", static_audit.get("selection_log_count"), 100),
        _expect("runtime_shadow_replay_result_review_metric_log_count", static_audit.get("metric_log_count"), 100),
        _expect("runtime_shadow_replay_result_review_evaluation_state_log_count", static_audit.get("evaluation_state_log_count"), 100),
        _expect("runtime_shadow_replay_result_review_trajectory_log_count", static_audit.get("trajectory_log_count"), 100),
        _expect("runtime_shadow_replay_result_review_selected_indices_dp_top1", static_audit.get("selected_index_counts"), expected_counts),
        _expect("runtime_shadow_replay_result_review_executed_indices_dp_top1", static_audit.get("executed_index_counts"), expected_counts),
        _check(
            "runtime_shadow_replay_result_review_nonzero_shadow_selection_positive",
            int(static_audit.get("nonzero_shadow_selection_count") or 0) > 0,
            static_audit.get("shadow_selected_index_counts"),
            "nonzero shadow selections",
        ),
        _expect("runtime_shadow_replay_result_review_candidate_generation_by_fixed_dp_executed", static_audit.get("candidate_generation_by_fixed_dp_executed"), True),
        _expect("runtime_shadow_replay_result_review_candidate_generation_by_camp_executed", static_audit.get("candidate_generation_by_camp_executed"), False),
        _expect("runtime_shadow_replay_result_review_training_executed", static_audit.get("training_executed"), False),
        _expect("runtime_shadow_replay_result_review_dp_modified", static_audit.get("dp_modified"), False),
        _expect("runtime_shadow_replay_result_review_formal_seeds_not_executed", static_audit.get("formal_seeds_11_12_13_executed"), False),
        _expect("runtime_shadow_replay_result_review_selector_promotion_blocked", static_audit.get("selector_promotion_authorized"), False),
        _expect("runtime_shadow_replay_result_review_atom_promotion_blocked", static_audit.get("atom_promotion_authorized"), False),
        _expect("runtime_shadow_replay_result_review_safety_claim_blocked", static_audit.get("safety_benefit_claim_authorized"), False),
        _expect("runtime_shadow_replay_result_review_camp_over_dp_claim_blocked", static_audit.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("runtime_shadow_replay_result_review_check_execution_exit_zero", audit_checks.get("execution_exit_zero"), True),
        _expect("runtime_shadow_replay_result_review_check_missing_shadow_payload_zero", audit_checks.get("missing_shadow_payload_zero"), True),
        _expect("runtime_shadow_replay_result_review_check_failed_shadow_records_zero", audit_checks.get("failed_shadow_records_zero"), True),
        _expect("runtime_shadow_replay_result_review_check_reference_blend_disabled", audit_checks.get("reference_blend_disabled_all_records"), True),
        _expect("runtime_shadow_replay_result_review_check_guidance_disabled", audit_checks.get("guidance_disabled_all_records"), True),
        _expect("runtime_shadow_replay_result_review_check_postprocess_disabled", audit_checks.get("postselection_relaxation_splice_disabled"), True),
    ]
    if replay_output_dir is not None:
        checks.append(
            _expect(
                "runtime_shadow_replay_result_review_replay_output_dir_matches",
                static_audit.get("replay_output_dir"),
                str(replay_output_dir),
            )
        )
        checks.append(
            _check(
                "runtime_shadow_replay_result_review_selection_log_exists",
                (replay_output_dir / "camp_selection_log.json").is_file(),
                str(replay_output_dir / "camp_selection_log.json"),
                "file exists",
            )
        )
    if static_audit_path is not None:
        checks.append(
            _check(
                "runtime_shadow_replay_result_review_static_audit_exists",
                static_audit_path.is_file(),
                str(static_audit_path),
                "file exists",
            )
        )
    return checks


def _smoke_result_review_summary(
    *,
    required: bool,
    execution_artifact_dir: Path | None,
    replay_output_dir: Path | None,
    static_audit_path: Path | None,
    static_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "required_by_current_audit_scope": required,
        "execution_artifact_dir": str(execution_artifact_dir) if execution_artifact_dir is not None else None,
        "replay_output_dir": str(replay_output_dir) if replay_output_dir is not None else None,
        "static_audit_json": str(static_audit_path) if static_audit_path is not None else None,
        "static_audit_json_sha256": (
            _sha256(static_audit_path)
            if static_audit_path is not None and static_audit_path.is_file()
            else None
        ),
        "passed": static_audit.get("passed"),
        "failed_checks": static_audit.get("failed_checks"),
        "selection_log_count": static_audit.get("selection_log_count"),
        "metric_log_count": static_audit.get("metric_log_count"),
        "evaluation_state_log_count": static_audit.get("evaluation_state_log_count"),
        "trajectory_log_count": static_audit.get("trajectory_log_count"),
        "selected_index_counts": static_audit.get("selected_index_counts"),
        "executed_index_counts": static_audit.get("executed_index_counts"),
        "shadow_selected_index_counts": static_audit.get("shadow_selected_index_counts"),
        "nonzero_shadow_selection_count": static_audit.get("nonzero_shadow_selection_count"),
        "authorized_next_work": static_audit.get("authorized_next_work"),
    }


def _audit_checks(text: str) -> list[dict[str, Any]]:
    latest_next_work = _latest_audit_value(text, "next_work_target")
    latest_status = _latest_audit_value(text, "current_v13_status")
    latest_runtime_shadow = _latest_audit_value(text, "runtime_shadow_selector_execution_authorized")
    latest_replay = _latest_audit_value(text, "replay_execution_authorized_by_current_boundary")
    latest_training = _latest_audit_value(text, "training_execution_authorized_by_current_boundary")
    return [
        _check(
            "audit_latest_scope_allows_batch_preflight",
            latest_next_work in ALLOWED_PREFLIGHT_WORK,
            latest_next_work,
            list(ALLOWED_PREFLIGHT_WORK),
        ),
        _expect("audit_latest_status_allows_batch_preflight", latest_status, LATEST_ALLOWED_STATUS),
        _expect("audit_latest_runtime_execution_blocked", latest_runtime_shadow, "False"),
        _expect("audit_latest_replay_execution_blocked", latest_replay, "False"),
        _expect("audit_latest_training_blocked", latest_training, "False"),
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
        _check("all_commands_no_guidance_or_reference_blend", all(all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS[:3]) for command in commands), joined, "no guidance/blend flags"),
        _check("all_commands_no_postselection_relaxation_or_splice", all(all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS[3:]) for command in commands), joined, "no postselection/relaxation/splice flags"),
    ]


def _decision(passed: bool, failed_checks: list[str], *, enabled: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "enabled": enabled,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "batch_execution_authorized_next": bool(passed),
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


def _blocked_actions() -> dict[str, bool]:
    return {
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


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report.get("preflight", {})
    lines = [
        "# V13 Current-Source Large Broader Shadow Replay Batch Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{','.join(decision['failed_checks'])}`",
        f"- Command count: `{preflight.get('command_count')}`",
        f"- Expected records: `{preflight.get('expected_records')}`",
        "",
        "This is a static preflight only. It does not execute replay, generate "
        "candidates, train CAMP, modify DP, promote, deploy, or authorize "
        "safety/CAMP-over-DP claims.",
    ]
    return "\n".join(lines) + "\n"


def _runbook(report: dict[str, Any]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated preflight runbook. Do not execute unless the audit EOF authorizes batch execution.",
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


def _shell_join(command: list[str]) -> str:
    def quote(arg: str) -> str:
        if not arg:
            return "''"
        safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-/.:=+"
        if all(ch in safe for ch in arg):
            return arg
        return "'" + arg.replace("'", "'\\''") + "'"

    return " ".join(quote(str(arg)) for arg in command)


def _load_json(path: Path, name: str) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, f"{name}_missing"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, f"{name}_unreadable"
    if not isinstance(loaded, dict):
        return {}, f"{name}_not_object"
    return loaded, None


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
    if not isinstance(value, str):
        return False
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
