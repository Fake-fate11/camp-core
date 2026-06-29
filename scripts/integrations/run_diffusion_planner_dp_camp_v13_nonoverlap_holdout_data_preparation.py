#!/usr/bin/env python3
"""Execute v13 non-overlap holdout data preparation.

This runner consumes the manifest-only holdout request artifact and materializes
fixed-DP default-off shadow-selector selection logs plus non-overlap registries.
It does not train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP Top-1 claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs,
)


SCHEMA_VERSION = "dp_camp_v13_nonoverlap_holdout_data_preparation_v1"
READY_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_complete"
REJECT_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_rejected"
DISABLED_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_disabled"
REQUEST_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_candidate_request_manifest_v1"
)
EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_expected_artifact_manifest_v1"
)
EXCLUSION_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_exclusion_registry_manifest_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_static_dp_reward_training_preflight_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
FORMAL_SEEDS = {11, 12, 13}
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_LOG_COUNT = 128
EXPECTED_RECORDS = 12800
FORBIDDEN_COMMAND_FLAGS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
    "--camp_collect_closed_loop_outcomes",
)
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize fixed-DP non-overlap holdout selection logs and "
            "registries for v13 default-off shadow-selector training data."
        )
    )
    parser.add_argument("--holdout_candidate_request_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_holdout_artifact_manifest_json", type=Path, required=True)
    parser.add_argument("--nonoverlap_exclusion_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--route", action="append", required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--base_output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--python_executable", default="python")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=EXPECTED_STEPS_PER_LOG)
    parser.add_argument("--num_candidates", type=int, default=EXPECTED_CANDIDATE_COUNT)
    parser.add_argument("--max_npcs_values", default="0,4")
    parser.add_argument("--traffic_light_modes", default="on,off")
    parser.add_argument("--spawn_probability", type=float, default=0.3)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--enable_v13_nonoverlap_holdout_data_preparation",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    common = dict(
        holdout_candidate_request_manifest_json=args.holdout_candidate_request_manifest_json,
        expected_holdout_artifact_manifest_json=args.expected_holdout_artifact_manifest_json,
        nonoverlap_exclusion_registry_manifest_json=(
            args.nonoverlap_exclusion_registry_manifest_json
        ),
        runtime_manifest_json=args.runtime_manifest_json,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        diffusion_repo=args.diffusion_repo,
        route_specs=tuple(args.route),
        model_path=args.model_path,
        model_args=args.model_args,
        config=args.config,
        reward_config=args.reward_config,
        base_output_dir=args.base_output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        python_executable=args.python_executable,
        device=args.device,
        steps=args.steps,
        num_candidates=args.num_candidates,
        max_npcs_values=_parse_ints(args.max_npcs_values),
        traffic_light_modes=_parse_strings(args.traffic_light_modes),
        spawn_probability=args.spawn_probability,
        enabled=bool(args.enable_v13_nonoverlap_holdout_data_preparation),
    )
    report = build_report(**common, execute=False)
    _write_report_artifacts(report, args.output_json, args.output_md, args.output_runbook)
    if args.execute and report["final_decision"]["passed"]:
        report = build_report(**common, execute=True)
        _write_report_artifacts(report, args.output_json, args.output_md, args.output_runbook)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    holdout_candidate_request_manifest_json: Path,
    expected_holdout_artifact_manifest_json: Path,
    nonoverlap_exclusion_registry_manifest_json: Path,
    runtime_manifest_json: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
    diffusion_repo: Path,
    route_specs: tuple[str, ...],
    model_path: Path,
    model_args: Path,
    config: Path,
    reward_config: Path,
    base_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    python_executable: str = "python",
    device: str = "cuda",
    steps: int = EXPECTED_STEPS_PER_LOG,
    num_candidates: int = EXPECTED_CANDIDATE_COUNT,
    max_npcs_values: tuple[int, ...] = (0, 4),
    traffic_light_modes: tuple[str, ...] = ("on", "off"),
    spawn_probability: float = 0.3,
    execute: bool = False,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "execute": bool(execute),
            "data_preparation_execution": bool(execute),
            "fixed_dp_candidate_generation_executed": False,
            "training_execution": False,
            "shadow_replay_evaluation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "holdout_candidate_request_manifest_json": str(holdout_candidate_request_manifest_json),
            "expected_holdout_artifact_manifest_json": str(expected_holdout_artifact_manifest_json),
            "nonoverlap_exclusion_registry_manifest_json": str(nonoverlap_exclusion_registry_manifest_json),
            "runtime_manifest_json": str(runtime_manifest_json),
            "replay_runner_py": str(replay_runner_py),
            "v13_audit_md": str(v13_audit_md),
            "base_output_dir": str(base_output_dir),
        },
        "source_hashes": {},
        "planned_commands": [],
        "execution": {},
        "selection_log_summary": {},
        "registry_summary": {},
        "training_data_contract": {},
        "checks": [],
        "final_decision": _decision(False, [], enabled=False, execute=execute),
    }
    if not enabled:
        report["final_decision"]["status"] = DISABLED_STATUS
        return report

    request_manifest, request_error = _load_json(
        holdout_candidate_request_manifest_json,
        "request_manifest",
    )
    expected_manifest, expected_error = _load_json(
        expected_holdout_artifact_manifest_json,
        "expected_artifact_manifest",
    )
    exclusion_manifest, exclusion_error = _load_json(
        nonoverlap_exclusion_registry_manifest_json,
        "exclusion_manifest",
    )
    runtime_manifest, runtime_error = _load_json(runtime_manifest_json, "runtime_manifest")
    audit_text = _read_text(v13_audit_md)
    runner_text = _read_text(replay_runner_py)
    routes, route_errors = _parse_routes(route_specs)
    requests = _list(request_manifest.get("route_seed_requests"))
    commands = _planned_commands(
        requests=requests,
        routes=routes,
        replay_runner_py=replay_runner_py,
        diffusion_repo=diffusion_repo,
        model_path=model_path,
        model_args=model_args,
        config=config,
        reward_config=reward_config,
        runtime_manifest_json=runtime_manifest_json,
        base_output_dir=base_output_dir,
        python_executable=python_executable,
        device=device,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        spawn_probability=spawn_probability,
    )

    report["source_hashes"] = _source_hashes(
        holdout_candidate_request_manifest_json,
        expected_holdout_artifact_manifest_json,
        nonoverlap_exclusion_registry_manifest_json,
        runtime_manifest_json,
        replay_runner_py,
        v13_audit_md,
        model_args,
        reward_config,
    )
    report["planned_commands"] = commands
    checks = _checks(
        request_manifest=request_manifest,
        request_error=request_error,
        expected_manifest=expected_manifest,
        expected_error=expected_error,
        exclusion_manifest=exclusion_manifest,
        exclusion_error=exclusion_error,
        runtime_manifest=runtime_manifest,
        runtime_error=runtime_error,
        audit_text=audit_text,
        runner_text=runner_text,
        routes=routes,
        route_errors=route_errors,
        requests=requests,
        commands=commands,
        diffusion_repo=diffusion_repo,
        model_path=model_path,
        model_args=model_args,
        config=config,
        reward_config=reward_config,
        base_output_dir=base_output_dir,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        steps=steps,
        num_candidates=num_candidates,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        spawn_probability=spawn_probability,
        execute=execute,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    if execute and not failed:
        execution = _execute_commands(commands, base_output_dir=base_output_dir)
        report["execution"] = execution
        if execution["failed_commands"]:
            failed.append("all_replay_commands_exit_zero")
        log_summary, registry_summary, registry_failures = _materialize_registries(
            commands=commands,
            base_output_dir=base_output_dir,
            expected_log_count=EXPECTED_LOG_COUNT,
            expected_steps_per_log=steps,
            expected_records=EXPECTED_RECORDS,
            expected_num_candidates=num_candidates,
        )
        report["selection_log_summary"] = log_summary
        report["registry_summary"] = registry_summary
        failed.extend(registry_failures)
        logs = [Path(entry["selection_log"]) for entry in log_summary.get("logs", [])]
        if logs:
            contract = validate_logs(logs)
            report["training_data_contract"] = {
                "passed": bool(contract.get("passed")),
                "records": int(contract.get("records", 0)),
                "failed_records": int(len(contract.get("failed_records", []))),
                "future_training_input_contract_satisfied": bool(
                    contract.get("future_training_input_contract_satisfied")
                ),
            }
            if not contract.get("passed"):
                failed.append("training_data_contract_passed")
        else:
            report["training_data_contract"] = {
                "passed": False,
                "records": 0,
                "failed_records": 0,
                "future_training_input_contract_satisfied": False,
            }
            failed.append("selection_logs_present")
        if not failed:
            report["analysis"]["fixed_dp_candidate_generation_executed"] = True
    else:
        report["selection_log_summary"] = {
            "expected_log_count": EXPECTED_LOG_COUNT,
            "expected_records": EXPECTED_RECORDS,
            "planned_log_count": len(commands),
            "data_preparation_executed": False,
        }
    report["checks"] = checks + _checks_from_failures(failed, {check["name"] for check in checks})
    passed = not failed
    report["final_decision"] = _decision(passed, failed, enabled=True, execute=execute)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("selection_log_summary", {})
    registry = report.get("registry_summary", {})
    contract = report.get("training_data_contract", {})
    lines = [
        "# V13 Non-Overlap Holdout Data Preparation",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Execute: `{decision['execute']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Selection logs: `{summary.get('log_count')}`",
        f"- Records: `{summary.get('record_count')}`",
        f"- Candidate tensor hashes: `{registry.get('candidate_tensor_hash_count')}`",
        f"- Training data contract passed: `{contract.get('passed')}`",
        "",
        "CAMP remains a default-off fixed-DP candidate reranker. Executed "
        "trajectory records must stay DP Top-1; only shadow selected indices "
        "are logged. No training, DP modification, promotion, deployment, "
        "safety claim, or CAMP-over-DP Top-1 claim is made by this gate.",
        "",
    ]
    return "\n".join(lines)


def render_runbook(report: dict[str, Any]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated v13 non-overlap holdout data-preparation runbook.",
        "# Executes fixed DP candidate generation through the default-off shadow selector.",
    ]
    for index, entry in enumerate(report.get("planned_commands", []), start=1):
        lines.extend(
            [
                "",
                (
                    f"# command {index}: request={entry['request_id']} "
                    f"route={entry['route_name']} seed={entry['seed']} "
                    f"npc={entry['max_npcs']} tl={entry['traffic_lights']}"
                ),
                _shell_join(entry["command"]),
            ]
        )
    return "\n".join(lines) + "\n"


def _planned_commands(
    *,
    requests: list[Any],
    routes: list[dict[str, str]],
    replay_runner_py: Path,
    diffusion_repo: Path,
    model_path: Path,
    model_args: Path,
    config: Path,
    reward_config: Path,
    runtime_manifest_json: Path,
    base_output_dir: Path,
    python_executable: str,
    device: str,
    steps: int,
    num_candidates: int,
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    spawn_probability: float,
) -> list[dict[str, Any]]:
    if not routes:
        return []
    commands: list[dict[str, Any]] = []
    spawn_dir = "spawn_" + f"{spawn_probability:g}".replace(".", "p")
    for index, request in enumerate(requests):
        if not isinstance(request, dict):
            continue
        route = routes[index % len(routes)]
        seed = int(request.get("seed"))
        max_npcs = max_npcs_values[(index // len(routes)) % len(max_npcs_values)]
        traffic_lights = traffic_light_modes[
            (index // (len(routes) * len(max_npcs_values))) % len(traffic_light_modes)
        ]
        tl_dir = "tl_on" if traffic_lights == "on" else "tl_off"
        request_id = str(request.get("request_id", f"request_{index:03d}"))
        output_dir = (
            base_output_dir
            / "selection_logs"
            / request_id
            / route["name"]
            / f"seed_{seed}"
            / f"npc_{max_npcs}"
            / spawn_dir
            / tl_dir
            / "static_shadow"
        )
        command = [
            python_executable,
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
            "--camp_default_off_shadow_selector",
            "--camp_shadow_artifact_manifest",
            str(runtime_manifest_json),
            "--num_candidates",
            str(num_candidates),
        ]
        commands.append(
            {
                "index": index,
                "request_id": request_id,
                "source_route_id": request.get("route_id"),
                "scenario_tag": request.get("scenario_tag"),
                "route_name": route["name"],
                "route_path": route["path"],
                "seed": seed,
                "max_npcs": max_npcs,
                "traffic_lights": traffic_lights,
                "spawn_probability": spawn_probability,
                "output_dir": str(output_dir),
                "selection_log": str(output_dir / "camp_selection_log.json"),
                "command": command,
            }
        )
    return commands


def _checks(
    *,
    request_manifest: dict[str, Any],
    request_error: str | None,
    expected_manifest: dict[str, Any],
    expected_error: str | None,
    exclusion_manifest: dict[str, Any],
    exclusion_error: str | None,
    runtime_manifest: dict[str, Any],
    runtime_error: str | None,
    audit_text: str,
    runner_text: str,
    routes: list[dict[str, str]],
    route_errors: list[str],
    requests: list[Any],
    commands: list[dict[str, Any]],
    diffusion_repo: Path,
    model_path: Path,
    model_args: Path,
    config: Path,
    reward_config: Path,
    base_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    steps: int,
    num_candidates: int,
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    spawn_probability: float,
    execute: bool,
) -> list[dict[str, Any]]:
    seeds = [request.get("seed") for request in requests if isinstance(request, dict)]
    command_lists = [entry["command"] for entry in commands]
    expected_outputs = set(_list(expected_manifest.get("required_outputs")))
    artifacts = _dict(runtime_manifest.get("artifacts"))
    checks = [
        _check("request_manifest_readable", request_error is None, request_error, None),
        _check("expected_manifest_readable", expected_error is None, expected_error, None),
        _check("exclusion_manifest_readable", exclusion_error is None, exclusion_error, None),
        _check("runtime_manifest_readable", runtime_error is None, runtime_error, None),
        _expect("current_camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("request_manifest_schema", request_manifest.get("schema_version"), REQUEST_MANIFEST_SCHEMA_VERSION),
        _expect("expected_manifest_schema", expected_manifest.get("schema_version"), EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION),
        _expect("exclusion_manifest_schema", exclusion_manifest.get("schema_version"), EXCLUSION_MANIFEST_SCHEMA_VERSION),
        _expect("request_manifest_target_log_count", request_manifest.get("target_holdout_selection_logs"), EXPECTED_LOG_COUNT),
        _expect("request_manifest_target_records", request_manifest.get("target_holdout_records"), EXPECTED_RECORDS),
        _expect("request_manifest_steps_per_log", request_manifest.get("expected_steps_per_log"), EXPECTED_STEPS_PER_LOG),
        _expect("request_manifest_candidate_count", request_manifest.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("request_manifest_atom_count", request_manifest.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
        _expect("request_manifest_score_expression", request_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("request_manifest_nonnegative_simplex", request_manifest.get("formal_seeds_11_12_13_excluded"), True),
        _check("request_count", len(requests) == EXPECTED_LOG_COUNT, len(requests), EXPECTED_LOG_COUNT),
        _check("request_ids_unique", _request_ids_unique(requests), "unique" if _request_ids_unique(requests) else "duplicate", "unique"),
        _check("formal_seeds_excluded", not (set(seeds) & FORMAL_SEEDS), sorted(set(seeds) & FORMAL_SEEDS), []),
        _expect("expected_manifest_log_count", expected_manifest.get("expected_selection_log_count"), EXPECTED_LOG_COUNT),
        _expect("expected_manifest_records", expected_manifest.get("expected_records"), EXPECTED_RECORDS),
        _check("expected_manifest_required_outputs", {"selection_logs", "candidate_tensor_hash_registry.json", "path_signature_registry.json", "record_identity_hash_registry.json", "SHA256SUMS"} <= expected_outputs, sorted(expected_outputs), "required outputs present"),
        _expect("exclusion_candidate_tensor_zero_intersection", exclusion_manifest.get("train_eval_candidate_tensor_intersection_must_be_zero"), True),
        _expect("exclusion_path_signature_zero_intersection", exclusion_manifest.get("train_eval_path_signature_intersection_must_be_zero"), True),
        _expect("exclusion_record_identity_zero_intersection", exclusion_manifest.get("train_eval_record_identity_intersection_must_be_zero"), True),
        _expect("runtime_manifest_schema", runtime_manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("runtime_manifest_default_off", runtime_manifest.get("default_off"), True),
        _expect("runtime_manifest_selection_effect", runtime_manifest.get("selection_effect"), False),
        _expect("runtime_manifest_executed_output_policy", runtime_manifest.get("executed_output_policy"), "dp_top1"),
        _expect("runtime_manifest_candidate_operation", runtime_manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("runtime_manifest_score_expression", runtime_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("runtime_manifest_dp_head_fixed", runtime_manifest.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("runtime_manifest_required_dp_head_fixed", runtime_manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _check("runtime_manifest_artifacts_present", set(artifacts) >= {"atom_scales", "static_weights"}, sorted(artifacts), "atom_scales/static_weights"),
        _check("routes_parse", not route_errors, route_errors, []),
        _check("route_count_positive", len(routes) > 0, len(routes), "> 0"),
        _check("all_route_paths_exist", all(Path(route["path"]).is_file() for route in routes), [route["path"] for route in routes], "all exist"),
        _check("diffusion_repo_exists", diffusion_repo.is_dir(), str(diffusion_repo), "directory exists"),
        _check("model_path_exists", model_path.is_file(), str(model_path), "file exists"),
        _check("model_args_exists", model_args.is_file(), str(model_args), "file exists"),
        _check("config_exists", config.is_file(), str(config), "file exists"),
        _check("reward_config_exists", reward_config.is_file(), str(reward_config), "file exists"),
        _check("steps_expected", steps == EXPECTED_STEPS_PER_LOG, steps, EXPECTED_STEPS_PER_LOG),
        _check("num_candidates_expected", num_candidates == EXPECTED_CANDIDATE_COUNT, num_candidates, EXPECTED_CANDIDATE_COUNT),
        _check("max_npcs_values_valid", bool(max_npcs_values) and all(value >= 0 for value in max_npcs_values), list(max_npcs_values), "nonempty and nonnegative"),
        _check("traffic_light_modes_valid", bool(traffic_light_modes) and set(traffic_light_modes) <= {"on", "off"}, list(traffic_light_modes), "on/off"),
        _check("spawn_probability_valid", math.isfinite(spawn_probability) and 0.0 <= spawn_probability <= 1.0, spawn_probability, "[0, 1]"),
        _check("planned_command_count", len(commands) == EXPECTED_LOG_COUNT, len(commands), EXPECTED_LOG_COUNT),
        _check("planned_output_paths_unique", len({entry["output_dir"] for entry in commands}) == len(commands), len({entry["output_dir"] for entry in commands}), len(commands)),
        _check("base_output_absent_before_execution", (not execute) or not base_output_dir.exists(), str(base_output_dir), "absent before execution"),
        _contains("audit_authorizes_current_gate", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_authorizes_data_preparation", audit_text, "data_preparation_authorized_by_current_boundary=True"),
        _contains("audit_authorizes_fixed_dp_generation", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=True"),
        _contains("audit_blocks_training", audit_text, "training_execution_authorized_by_current_boundary=False"),
        _contains("audit_blocks_replay_evaluation", audit_text, "replay_execution_authorized_by_current_boundary=False"),
        _contains("audit_blocks_camp_candidate_generation", audit_text, "candidate_generation_by_camp_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _contains("runner_has_default_off_shadow_selector", runner_text, "--camp_default_off_shadow_selector"),
        _contains("runner_forces_dp_top1", runner_text, '"executed_output_policy": "dp_top1"'),
        _contains("runner_records_shadow_selected_index", runner_text, "shadow_selected_index"),
    ]
    checks.extend(_command_checks(command_lists))
    checks.extend(_artifact_file_checks("atom_scales", _dict(artifacts.get("atom_scales"))))
    checks.extend(_artifact_file_checks("static_weights", _dict(artifacts.get("static_weights"))))
    return checks


def _command_checks(commands: list[list[str]]) -> list[dict[str, Any]]:
    joined = "\n".join(" ".join(command) for command in commands)
    return [
        _check("commands_use_shadow_selector", all("--camp_default_off_shadow_selector" in command for command in commands), joined, "all"),
        _check("commands_use_shadow_manifest", all("--camp_shadow_artifact_manifest" in command for command in commands), joined, "all"),
        _check("commands_selector_mode_static", all(_argument_value(command, "--camp_selector_mode") == "static" for command in commands), joined, "static"),
        _check("commands_fallback_mode_learned", all(_argument_value(command, "--camp_fallback_mode") == "learned" for command in commands), joined, "learned"),
        _check("commands_feasibility_source_dp_reward", all(_argument_value(command, "--camp_feasibility_source") == "dp_reward" for command in commands), joined, "dp_reward"),
        _check("commands_num_candidates_8", all(_argument_value(command, "--num_candidates") == str(EXPECTED_CANDIDATE_COUNT) for command in commands), joined, "8"),
        _check("commands_have_reward_config", all("--reward_config" in command for command in commands), joined, "all"),
        _check("commands_have_model_args", all("--model_args" in command for command in commands), joined, "all"),
        _check("commands_no_forbidden_flags", all(all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS) for command in commands), joined, "no forbidden flags"),
    ]


def _execute_commands(
    commands: list[dict[str, Any]],
    *,
    base_output_dir: Path,
) -> dict[str, Any]:
    execution_dir = base_output_dir / "execution_logs"
    execution_dir.mkdir(parents=True, exist_ok=True)
    failed_commands: list[dict[str, Any]] = []
    completed = 0
    for index, entry in enumerate(commands, start=1):
        command_id = f"command_{index:03d}_{entry['request_id']}"
        stdout_path = execution_dir / f"{command_id}.stdout.log"
        stderr_path = execution_dir / f"{command_id}.stderr.log"
        output_dir = Path(entry["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            result = subprocess.run(
                [str(part) for part in entry["command"]],
                cwd=str(ROOT),
                stdout=stdout_handle,
                stderr=stderr_handle,
                check=False,
            )
        completed += 1
        if result.returncode != 0:
            failed_commands.append(
                {
                    "request_id": entry["request_id"],
                    "returncode": int(result.returncode),
                    "stdout": str(stdout_path),
                    "stderr": str(stderr_path),
                    "command": entry["command"],
                }
            )
            break
    return {
        "commands_completed": completed,
        "commands_planned": len(commands),
        "failed_commands": failed_commands,
        "execution_log_dir": str(execution_dir),
    }


def _materialize_registries(
    *,
    commands: list[dict[str, Any]],
    base_output_dir: Path,
    expected_log_count: int,
    expected_steps_per_log: int,
    expected_records: int,
    expected_num_candidates: int,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    failures: list[str] = []
    command_by_log = {Path(entry["selection_log"]).resolve(): entry for entry in commands}
    logs = sorted(base_output_dir.rglob("camp_selection_log.json"))
    log_entries: list[dict[str, Any]] = []
    tensor_registry: list[dict[str, Any]] = []
    path_registry: list[dict[str, Any]] = []
    identity_registry: list[dict[str, Any]] = []
    record_count = 0
    executed_index_violations = 0
    default_off_missing = 0
    atom_schema_violations = 0
    forbidden_runtime_flags = 0
    for log_path in logs:
        records = _read_json_list(log_path)
        command_entry = command_by_log.get(log_path.resolve(), {})
        log_entries.append(
            {
                "selection_log": str(log_path),
                "relative_path": str(log_path.relative_to(base_output_dir)),
                "records": len(records),
                "sha256": _sha256(log_path),
                "request_id": command_entry.get("request_id"),
                "route_name": command_entry.get("route_name"),
                "seed": command_entry.get("seed"),
            }
        )
        if len(records) != expected_steps_per_log:
            failures.append(f"log_steps:{log_path}")
        path_signature_payload = {
            "request_id": command_entry.get("request_id"),
            "source_route_id": command_entry.get("source_route_id"),
            "route_name": command_entry.get("route_name"),
            "route_path": command_entry.get("route_path"),
            "seed": command_entry.get("seed"),
            "max_npcs": command_entry.get("max_npcs"),
            "traffic_lights": command_entry.get("traffic_lights"),
            "spawn_probability": command_entry.get("spawn_probability"),
        }
        path_signature_hash = _stable_hash(path_signature_payload)
        path_registry.append(
            {
                "path_signature_hash": path_signature_hash,
                **path_signature_payload,
                "selection_log": str(log_path),
            }
        )
        for record_index, record in enumerate(records):
            record_count += 1
            if record.get("selected_index") != 0 or record.get("executed_index") != 0:
                executed_index_violations += 1
            selector = _dict(record.get("default_off_shadow_selector"))
            if not selector:
                default_off_missing += 1
            if record.get("atom_schema_version") != ATOM_SCHEMA_VERSION:
                atom_schema_violations += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                forbidden_runtime_flags += 1
            generation = _dict(record.get("candidate_generation_contract"))
            if generation.get("reference_blend_steps") is not None:
                forbidden_runtime_flags += 1
            if generation.get("guidance_enabled") not in (False, None):
                forbidden_runtime_flags += 1
            tensor_hash = _candidate_tensor_hash(record)
            if tensor_hash is None:
                failures.append(f"candidate_tensor_hash_missing:{log_path}:{record_index}")
                continue
            shadow_selected_index = _as_int(record.get("shadow_selected_index"))
            tensor_registry.append(
                {
                    "candidate_tensor_hash": tensor_hash,
                    "selection_log": str(log_path),
                    "record_index": record_index,
                    "request_id": command_entry.get("request_id"),
                    "selection_step": record.get("selection_step"),
                    "selected_index": record.get("selected_index"),
                    "executed_index": record.get("executed_index"),
                    "shadow_selected_index": shadow_selected_index,
                    "num_candidates": record.get("num_candidates"),
                }
            )
            identity_payload = {
                "path_signature_hash": path_signature_hash,
                "record_index": record_index,
                "selection_step": record.get("selection_step"),
                "candidate_tensor_hash": tensor_hash,
            }
            identity_registry.append(
                {
                    "record_identity_hash": _stable_hash(identity_payload),
                    **identity_payload,
                    "selection_log": str(log_path),
                }
            )
            if record.get("num_candidates") != expected_num_candidates:
                failures.append(f"num_candidates:{log_path}:{record_index}")
    if len(logs) != expected_log_count:
        failures.append("selection_log_count")
    if record_count != expected_records:
        failures.append("record_count")
    if executed_index_violations:
        failures.append("executed_index_dp_top1")
    if default_off_missing:
        failures.append("default_off_payload_present")
    if atom_schema_violations:
        failures.append("atom_schema")
    if forbidden_runtime_flags:
        failures.append("forbidden_runtime_flags_disabled")

    _write_json(base_output_dir / "candidate_tensor_hash_registry.json", {"entries": tensor_registry})
    _write_json(base_output_dir / "path_signature_registry.json", {"entries": path_registry})
    _write_json(base_output_dir / "record_identity_hash_registry.json", {"entries": identity_registry})
    (base_output_dir / "selection_logs.txt").write_text(
        "\n".join(entry["selection_log"] for entry in log_entries) + "\n",
        encoding="utf-8",
    )
    return (
        {
            "log_count": len(logs),
            "record_count": record_count,
            "expected_log_count": expected_log_count,
            "expected_records": expected_records,
            "logs": log_entries,
            "executed_index_violations": executed_index_violations,
            "default_off_missing": default_off_missing,
            "atom_schema_violations": atom_schema_violations,
            "forbidden_runtime_flags": forbidden_runtime_flags,
        },
        {
            "candidate_tensor_hash_count": len(tensor_registry),
            "unique_candidate_tensor_hash_count": len(
                {entry["candidate_tensor_hash"] for entry in tensor_registry}
            ),
            "path_signature_count": len(path_registry),
            "record_identity_hash_count": len(identity_registry),
            "unique_record_identity_hash_count": len(
                {entry["record_identity_hash"] for entry in identity_registry}
            ),
            "candidate_tensor_hash_registry": str(base_output_dir / "candidate_tensor_hash_registry.json"),
            "path_signature_registry": str(base_output_dir / "path_signature_registry.json"),
            "record_identity_hash_registry": str(base_output_dir / "record_identity_hash_registry.json"),
        },
        sorted(set(failures)),
    )


def _write_report_artifacts(
    report: dict[str, Any],
    output_json: Path,
    output_md: Path,
    output_runbook: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_runbook.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    output_runbook.write_text(render_runbook(report), encoding="utf-8")
    _write_sha256sums(output_json.parent)


def _write_sha256sums(root: Path) -> None:
    files = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS"
    ]
    lines = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decision(
    passed: bool,
    failed: list[str],
    *,
    enabled: bool,
    execute: bool,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "enabled": bool(enabled),
        "execute": bool(execute),
        "passed": bool(passed),
        "failed_checks": sorted(set(failed)),
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed and execute else None,
        "training_preflight_authorized_next": bool(passed and execute),
        "data_preparation_executed": bool(passed and execute),
        "fixed_dp_candidate_generation_executed": bool(passed and execute),
        "training_executed": False,
        "replay_evaluation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _source_hashes(*paths: Path) -> dict[str, str | None]:
    return {
        path.name: _sha256(path) if path.is_file() else None
        for path in paths
    }


def _artifact_file_checks(name: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(str(entry.get("path", "")))
    expected_sha = entry.get("sha256")
    checks = [
        _expect(f"{name}_logical_name", entry.get("logical_name"), name),
        _expect(f"{name}_required", entry.get("required"), True),
        _check(f"{name}_path_exists", path.is_file(), str(path), "file exists"),
        _check(f"{name}_sha256_valid", _is_sha256(expected_sha), expected_sha, "sha256"),
    ]
    if path.is_file() and _is_sha256(expected_sha):
        checks.append(_expect(f"{name}_sha256_matches", _sha256(path), expected_sha))
    return checks


def _checks_from_failures(
    failed: list[str],
    existing_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    existing_names = existing_names or set()
    checks = []
    for name in sorted(set(failed)):
        if name not in existing_names:
            checks.append(_check(name, False, name, "pass"))
    return checks


def _candidate_tensor_hash(record: dict[str, Any]) -> str | None:
    selector = _dict(record.get("default_off_shadow_selector"))
    tensor_hash = _dict(selector.get("candidate_tensor_hash"))
    value = tensor_hash.get("sha256")
    if _is_sha256(value):
        return str(value).lower()
    provenance = _dict(record.get("camp_candidate_tensor_provenance"))
    for key in ("pre_camp_scoring_tensor", "candidate_tensor_hash"):
        nested = _dict(provenance.get(key))
        value = nested.get("sha256")
        if _is_sha256(value):
            return str(value).lower()
    return None


def _request_ids_unique(requests: list[Any]) -> bool:
    ids = [request.get("request_id") for request in requests if isinstance(request, dict)]
    return len(ids) == len(set(ids)) == len(requests)


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
            errors.append(f"route_empty:{spec}")
            continue
        if name in seen:
            errors.append(f"route_duplicate:{name}")
            continue
        seen.add(name)
        routes.append({"name": name, "path": path})
    return routes, errors


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _argument_value(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return command[index + 1]


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


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(_stable(payload), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in value)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
