#!/usr/bin/env python3
"""Collect fixed-DP non-overlap remediation logs for v13 readiness rejection.

This gate is intentionally narrow: it materializes a replacement evaluation
log set after a result-readiness rejection caused by overlap with the previous
training/evaluation artifacts. It does not train CAMP, modify Diffusion
Planner, promote artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
ENV_CAMP_REPO = Path(os.environ["CAMP_REPO"]).resolve() if os.environ.get("CAMP_REPO") else None
extra_roots = (
    (ENV_CAMP_REPO, ENV_CAMP_REPO / "camp_core") if ENV_CAMP_REPO is not None else ()
)
for path in (ROOT, PACKAGE_ROOT, *extra_roots):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness import (  # noqa: E402
    _candidate_tensor_hash,
    _default_off_shadow_selector_valid,
    _record_has_finite_reward,
)
from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs,
)


SCHEMA_VERSION = (
    "dp_camp_v13_result_readiness_rejected_nonoverlap_remediation_collection_v1"
)
READINESS_SCHEMA_VERSION = (
    "dp_camp_v13_result_readiness_rejected_nonoverlap_remediation_readiness_v1"
)
GATE = (
    "dp_camp_v13_result_readiness_rejected_nonoverlap_remediation_fixed_dp_"
    "candidate_log_collection_plan_and_execution_user_authorized"
)
NEXT_GATE = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
    "eval_plus_prior_nonoverlap_remediation_static_dp_reward_training_preflight_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
FORMAL_SEEDS = {11, 12, 13}
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)
FORBIDDEN_FLAGS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
    "--camp_collect_closed_loop_outcomes",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact_dir", type=Path, required=True)
    parser.add_argument("--camp_repo", type=Path, default=ROOT)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--python_executable", type=Path, required=True)
    parser.add_argument("--runtime_manifest_template_json", type=Path, required=True)
    parser.add_argument("--previous_training_output_dir", type=Path, required=True)
    parser.add_argument("--previous_training_summary_json", type=Path, required=True)
    parser.add_argument("--rejected_eval_output_dir", type=Path, required=True)
    parser.add_argument("--assets_dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seeds", default="1300,1301")
    parser.add_argument("--max_npcs_values", default="0,4")
    parser.add_argument("--traffic_light_modes", default="on,off")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--spawn_probability", type=float, default=0.3)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    seeds = _parse_ints(args.seeds)
    max_npcs_values = _parse_ints(args.max_npcs_values)
    traffic_light_modes = _parse_strings(args.traffic_light_modes)
    report = run_collection(
        artifact_dir=args.artifact_dir,
        camp_repo=args.camp_repo,
        diffusion_repo=args.diffusion_repo,
        python_executable=args.python_executable,
        runtime_manifest_template_json=args.runtime_manifest_template_json,
        previous_training_output_dir=args.previous_training_output_dir,
        previous_training_summary_json=args.previous_training_summary_json,
        rejected_eval_output_dir=args.rejected_eval_output_dir,
        assets_dir=args.assets_dir,
        device=args.device,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        steps=args.steps,
        num_candidates=args.num_candidates,
        spawn_probability=args.spawn_probability,
        execute=bool(args.execute),
    )
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def run_collection(
    *,
    artifact_dir: Path,
    camp_repo: Path,
    diffusion_repo: Path,
    python_executable: Path,
    runtime_manifest_template_json: Path,
    previous_training_output_dir: Path,
    previous_training_summary_json: Path,
    rejected_eval_output_dir: Path,
    assets_dir: Path,
    device: str,
    seeds: tuple[int, ...],
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    steps: int,
    num_candidates: int,
    spawn_probability: float,
    execute: bool,
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    camp_repo = camp_repo.resolve()
    diffusion_repo = diffusion_repo.resolve()
    python_executable = python_executable.resolve()
    previous_training_output_dir = previous_training_output_dir.resolve()
    previous_training_summary_json = previous_training_summary_json.resolve()
    rejected_eval_output_dir = rejected_eval_output_dir.resolve()
    runtime_manifest_template_json = runtime_manifest_template_json.resolve()
    assets_dir = assets_dir.resolve()

    artifact_dir.mkdir(parents=True, exist_ok=True)
    progress_path = artifact_dir / "progress.jsonl"
    _append_progress(progress_path, "driver_start", artifact=str(artifact_dir))
    heads = _write_heads(
        artifact_dir=artifact_dir,
        camp_repo=camp_repo,
        diffusion_repo=diffusion_repo,
    )
    runtime_manifest_json = _write_runtime_manifest(
        artifact_dir=artifact_dir,
        template_path=runtime_manifest_template_json,
        heads=heads,
    )
    routes = _default_routes(assets_dir)
    commands = _planned_commands(
        artifact_dir=artifact_dir,
        camp_repo=camp_repo,
        diffusion_repo=diffusion_repo,
        python_executable=python_executable,
        runtime_manifest_json=runtime_manifest_json,
        previous_training_output_dir=previous_training_output_dir,
        assets_dir=assets_dir,
        routes=routes,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        steps=steps,
        num_candidates=num_candidates,
        spawn_probability=spawn_probability,
        device=device,
    )
    _write_scope_plan(
        artifact_dir=artifact_dir,
        routes=routes,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        steps=steps,
        num_candidates=num_candidates,
        spawn_probability=spawn_probability,
        previous_training_output_dir=previous_training_output_dir,
        rejected_eval_output_dir=rejected_eval_output_dir,
    )
    _write_json(artifact_dir / "commands.json", commands)
    _write_runbook(artifact_dir / "run_nonoverlap_remediation.sh", commands)

    failures = _preflight_failures(
        heads=heads,
        routes=routes,
        commands=commands,
        diffusion_repo=diffusion_repo,
        python_executable=python_executable,
        runtime_manifest_json=runtime_manifest_json,
        previous_training_output_dir=previous_training_output_dir,
        previous_training_summary_json=previous_training_summary_json,
        rejected_eval_output_dir=rejected_eval_output_dir,
        assets_dir=assets_dir,
        seeds=seeds,
        max_npcs_values=max_npcs_values,
        traffic_light_modes=traffic_light_modes,
        steps=steps,
        num_candidates=num_candidates,
        spawn_probability=spawn_probability,
    )
    _write_json(
        artifact_dir / "preflight_checks.json",
        {"schema_version": SCHEMA_VERSION, "passed": not failures, "failed_checks": failures},
    )
    if failures:
        report = _base_report(
            artifact_dir=artifact_dir,
            heads=heads,
            execute=execute,
            status="preflight_rejected",
            passed=False,
            failed_checks=failures,
        )
        _write_report(artifact_dir, report, exit_code=2)
        return report
    if not execute:
        report = _base_report(
            artifact_dir=artifact_dir,
            heads=heads,
            execute=False,
            status="preflight_passed_not_executed",
            passed=True,
            failed_checks=[],
        )
        _write_report(artifact_dir, report, exit_code=0)
        return report

    execution = _execute_commands(
        commands,
        camp_repo=camp_repo,
        diffusion_repo=diffusion_repo,
        artifact_dir=artifact_dir,
        progress_path=progress_path,
    )
    _write_json(artifact_dir / "execution_summary.json", execution)
    if execution["failed_commands"]:
        report = _base_report(
            artifact_dir=artifact_dir,
            heads=heads,
            execute=True,
            status="collection_failed",
            passed=False,
            failed_checks=["command_execution_failed"],
        )
        report["execution"] = execution
        _write_report(artifact_dir, report, exit_code=3)
        return report

    evaluation_output_dir = artifact_dir / "planned_shadow_replay_evaluation"
    selection_logs = sorted(evaluation_output_dir.rglob("camp_selection_log.json"))
    clean_contract = validate_logs(selection_logs)
    _write_json(artifact_dir / "clean_contract_validation.json", clean_contract)
    (artifact_dir / "clean_contract_validation.md").write_text(
        _render_clean_contract_markdown(clean_contract),
        encoding="utf-8",
    )
    record_summary = _summarize_records(selection_logs, evaluation_output_dir)
    nonoverlap = _materialize_registries(
        artifact_dir=artifact_dir,
        evaluation_output_dir=evaluation_output_dir,
        previous_training_output_dir=previous_training_output_dir,
        previous_training_summary_json=previous_training_summary_json,
        rejected_eval_output_dir=rejected_eval_output_dir,
        selection_logs=selection_logs,
    )
    failed_checks = _readiness_failures(
        selection_logs=selection_logs,
        clean_contract=clean_contract,
        record_summary=record_summary,
        nonoverlap=nonoverlap,
    )
    passed = not failed_checks
    report = {
        "schema_version": READINESS_SCHEMA_VERSION,
        "gate": GATE,
        "artifact": str(artifact_dir),
        "runtime_manifest_json": str(runtime_manifest_json),
        "heads": heads,
        "execution": execution,
        "selection_log_count": len(selection_logs),
        "selection_logs": [str(path) for path in selection_logs],
        "clean_contract": {
            "passed": bool(clean_contract.get("passed")),
            "records": int(clean_contract.get("records", 0)),
            "failed_records": int(len(clean_contract.get("failed_records", []))),
            "future_training_input_contract_satisfied": bool(
                clean_contract.get("future_training_input_contract_satisfied")
            ),
        },
        "record_summary": record_summary,
        "nonoverlap": nonoverlap,
        "final_decision": _decision(
            status=(
                "nonoverlap_remediation_readiness_passed"
                if passed
                else "nonoverlap_remediation_readiness_rejected"
            ),
            passed=passed,
            failed_checks=failed_checks,
            authorized_next_work=NEXT_GATE if passed else None,
        ),
    }
    _write_report(artifact_dir, report, exit_code=0 if passed else 1)
    _append_progress(progress_path, "driver_done", passed=passed, failed_checks=failed_checks)
    return report


def _parse_ints(value: str) -> tuple[int, ...]:
    parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not parsed:
        raise ValueError("At least one integer value is required.")
    return parsed


def _parse_strings(value: str) -> tuple[str, ...]:
    parsed = tuple(item.strip() for item in value.split(",") if item.strip())
    if not parsed:
        raise ValueError("At least one string value is required.")
    return parsed


def _default_routes(assets_dir: Path) -> list[dict[str, str]]:
    return [
        {
            "name": "sample_normal",
            "path": str(assets_dir / "sample_map_route_2_to_104.pkl"),
        },
        {
            "name": "sample_tl",
            "path": str(assets_dir / "sample_map_tl_route_59_to_86.pkl"),
        },
        {
            "name": "nishi_release",
            "path": str(assets_dir / "nishishinjuku_release_auto_route.pkl"),
        },
        {
            "name": "nishi_lane_change",
            "path": str(assets_dir / "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"),
        },
    ]


def _planned_commands(
    *,
    artifact_dir: Path,
    camp_repo: Path,
    diffusion_repo: Path,
    python_executable: Path,
    runtime_manifest_json: Path,
    previous_training_output_dir: Path,
    assets_dir: Path,
    routes: list[dict[str, str]],
    seeds: tuple[int, ...],
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    steps: int,
    num_candidates: int,
    spawn_probability: float,
    device: str,
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    output_root = artifact_dir / "planned_shadow_replay_evaluation"
    spawn_dir = "spawn_" + f"{spawn_probability:g}".replace(".", "p")
    index = 0
    for route in routes:
        for seed in seeds:
            for max_npcs in max_npcs_values:
                for traffic_lights in traffic_light_modes:
                    index += 1
                    tl_dir = "tl_on" if traffic_lights == "on" else "tl_off"
                    output_dir = (
                        output_root
                        / route["name"]
                        / f"seed_{seed}"
                        / f"npc_{max_npcs}"
                        / spawn_dir
                        / tl_dir
                        / "static_shadow"
                    )
                    command = [
                        str(python_executable),
                        "scripts/integrations/run_diffusion_planner_camp_replay.py",
                        "--diffusion_repo",
                        str(diffusion_repo),
                        "--route",
                        route["path"],
                        "--model_path",
                        str(assets_dir / "diffusion_planner.pth"),
                        "--model_args",
                        str(assets_dir / "diffusion_planner.param.json"),
                        "--config",
                        str(diffusion_repo / "scenario_generation/configs/replay_default.json"),
                        "--reward_config",
                        "configs/integrations/dp_camp_reward_eval.json",
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
                        str(previous_training_output_dir / "atom_scales_dp_static.json"),
                        "--camp_static_weights",
                        str(previous_training_output_dir / "offline_weights_dp_static.npy"),
                        "--camp_default_off_shadow_selector",
                        "--camp_candidate_tensor_provenance_logging",
                        "--camp_shadow_artifact_manifest",
                        str(runtime_manifest_json),
                        "--num_candidates",
                        str(num_candidates),
                    ]
                    commands.append(
                        {
                            "index": index,
                            "request_id": f"nonoverlap_remediation_{index:03d}",
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


def _write_scope_plan(
    *,
    artifact_dir: Path,
    routes: list[dict[str, str]],
    seeds: tuple[int, ...],
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    steps: int,
    num_candidates: int,
    spawn_probability: float,
    previous_training_output_dir: Path,
    rejected_eval_output_dir: Path,
) -> None:
    _write_json(
        artifact_dir / "scope_plan.json",
        {
            "schema_version": "dp_camp_v13_nonoverlap_remediation_scope_plan_v1",
            "gate": GATE,
            "routes": routes,
            "seeds": list(seeds),
            "max_npcs_values": list(max_npcs_values),
            "traffic_light_modes": list(traffic_light_modes),
            "steps": steps,
            "num_candidates": num_candidates,
            "noise_strategy": "iid",
            "spawn_probability": spawn_probability,
            "camp_candidate_tensor_provenance_logging_required": True,
            "default_off_shadow_selector_required": True,
            "forbidden_flags": list(FORBIDDEN_FLAGS),
            "previous_training_output_dir": str(previous_training_output_dir),
            "rejected_eval_output_dir": str(rejected_eval_output_dir),
            "authorized_next_if_passed": NEXT_GATE,
        },
    )


def _preflight_failures(
    *,
    heads: dict[str, str],
    routes: list[dict[str, str]],
    commands: list[dict[str, Any]],
    diffusion_repo: Path,
    python_executable: Path,
    runtime_manifest_json: Path,
    previous_training_output_dir: Path,
    previous_training_summary_json: Path,
    rejected_eval_output_dir: Path,
    assets_dir: Path,
    seeds: tuple[int, ...],
    max_npcs_values: tuple[int, ...],
    traffic_light_modes: tuple[str, ...],
    steps: int,
    num_candidates: int,
    spawn_probability: float,
) -> list[str]:
    failures: list[str] = []
    if heads["camp_head"] != heads["camp_origin_main"]:
        failures.append("camp_head_origin_mismatch")
    if heads["dp_head"] != FIXED_DP_HEAD:
        failures.append("dp_head_not_fixed")
    if set(seeds).intersection(FORMAL_SEEDS):
        failures.append("formal_seed_requested")
    if steps != 100:
        failures.append("steps_not_100")
    if num_candidates != 8:
        failures.append("num_candidates_not_8")
    if not math.isfinite(spawn_probability) or not 0.0 <= spawn_probability <= 1.0:
        failures.append("spawn_probability_invalid")
    if not max_npcs_values or any(value < 0 for value in max_npcs_values):
        failures.append("max_npcs_values_invalid")
    if not traffic_light_modes or set(traffic_light_modes) - {"on", "off"}:
        failures.append("traffic_light_modes_invalid")
    if len(commands) != 32:
        failures.append("planned_command_count_not_32")
    command_text = "\n".join(" ".join(entry["command"]) for entry in commands)
    for flag in FORBIDDEN_FLAGS:
        if flag in command_text:
            failures.append(f"forbidden_flag_present:{flag}")
    if any("--camp_candidate_tensor_provenance_logging" not in entry["command"] for entry in commands):
        failures.append("provenance_flag_missing")
    if any("--camp_default_off_shadow_selector" not in entry["command"] for entry in commands):
        failures.append("default_off_shadow_selector_flag_missing")
    if any("--camp_shadow_artifact_manifest" not in entry["command"] for entry in commands):
        failures.append("shadow_manifest_flag_missing")
    required_files = [
        python_executable,
        runtime_manifest_json,
        previous_training_summary_json,
        previous_training_output_dir / "atom_scales_dp_static.json",
        previous_training_output_dir / "offline_weights_dp_static.npy",
        assets_dir / "diffusion_planner.pth",
        assets_dir / "diffusion_planner.param.json",
        diffusion_repo / "scenario_generation/configs/replay_default.json",
    ] + [Path(route["path"]) for route in routes]
    for path in required_files:
        if not path.exists():
            failures.append(f"required_file_missing:{path}")
    for path in (diffusion_repo, previous_training_output_dir, rejected_eval_output_dir):
        if not path.is_dir():
            failures.append(f"required_dir_missing:{path}")
    return sorted(set(failures))


def _execute_commands(
    commands: list[dict[str, Any]],
    *,
    camp_repo: Path,
    diffusion_repo: Path,
    artifact_dir: Path,
    progress_path: Path,
) -> dict[str, Any]:
    log_dir = artifact_dir / "execution_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{diffusion_repo}:{diffusion_repo / 'diffusion_planner'}"
    failed_commands: list[dict[str, Any]] = []
    completed = 0
    for entry in commands:
        _append_progress(
            progress_path,
            "command_start",
            index=entry["index"],
            route=entry["route_name"],
            seed=entry["seed"],
            npc=entry["max_npcs"],
            traffic_lights=entry["traffic_lights"],
        )
        stdout_path = log_dir / f"command_{entry['index']:03d}.stdout.log"
        stderr_path = log_dir / f"command_{entry['index']:03d}.stderr.log"
        exit_path = log_dir / f"command_{entry['index']:03d}.exit"
        Path(entry["output_dir"]).mkdir(parents=True, exist_ok=True)
        started = time.time()
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            result = subprocess.run(
                [str(part) for part in entry["command"]],
                cwd=str(camp_repo),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                check=False,
            )
        completed += 1
        exit_path.write_text(f"{int(result.returncode)}\n", encoding="utf-8")
        _append_progress(
            progress_path,
            "command_done",
            index=entry["index"],
            returncode=int(result.returncode),
            elapsed_s=round(time.time() - started, 3),
        )
        if result.returncode != 0:
            failed_commands.append(
                {
                    "index": entry["index"],
                    "returncode": int(result.returncode),
                    "stdout": str(stdout_path),
                    "stderr": str(stderr_path),
                    "command": entry["command"],
                }
            )
            break
    return {
        "commands_planned": len(commands),
        "commands_completed": completed,
        "failed_commands": failed_commands,
        "execution_log_dir": str(log_dir),
    }


def _summarize_records(
    selection_logs: list[Path],
    evaluation_output_dir: Path,
) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    counters: dict[str, Counter[str]] = {
        "route_records": Counter(),
        "seed_records": Counter(),
        "route_tl_records": Counter(),
        "candidate_count_values": Counter(),
        "atom_schema_versions": Counter(),
        "atom_count_values": Counter(),
        "selected_index_counts": Counter(),
        "executed_index_counts": Counter(),
        "shadow_selected_index_counts": Counter(),
        "feasible_count_distribution": Counter(),
    }
    for log_path in selection_logs:
        metadata = _metadata_from_log_path(log_path, evaluation_output_dir)
        for record in _read_json_list(log_path):
            totals["records_total"] += 1
            counters["route_records"][str(metadata["route"])] += 1
            counters["seed_records"][str(metadata["seed"])] += 1
            counters["route_tl_records"][
                f"{metadata['route']}|tl_{metadata['traffic_lights']}"
            ] += 1
            if metadata["seed"] in FORMAL_SEEDS:
                totals["formal_seed_records"] += 1
            candidate_count = int(record.get("num_candidates", 0) or 0)
            counters["candidate_count_values"][str(candidate_count)] += 1
            atoms = record.get("atoms")
            atom_count = (
                len(atoms[0])
                if isinstance(atoms, list)
                and atoms
                and isinstance(atoms[0], list)
                else 0
            )
            counters["atom_count_values"][str(atom_count)] += 1
            counters["atom_schema_versions"][str(record.get("atom_schema_version"))] += 1
            counters["selected_index_counts"][str(record.get("selected_index"))] += 1
            counters["executed_index_counts"][str(record.get("executed_index"))] += 1
            counters["shadow_selected_index_counts"][
                str(record.get("shadow_selected_index"))
            ] += 1
            feasible = record.get("feasible_mask")
            feasible_values = feasible if isinstance(feasible, list) else []
            feasible_count = sum(1 for value in feasible_values if bool(value))
            counters["feasible_count_distribution"][str(feasible_count)] += 1
            if feasible_count == 0:
                totals["all_infeasible_records"] += 1
            if feasible_count > 0:
                totals["usable_feasible_records"] += 1
            if feasible_count > 1:
                totals["multi_feasible_records"] += 1
            if _record_has_finite_reward(
                record,
                candidate_count=candidate_count,
                reward_key="quality_without_progress",
                reward_progress_weight=2.0,
            ):
                totals["finite_reward_records"] += 1
            if record.get("candidate_closed_loop_outcomes") is not None:
                totals["closed_loop_outcome_records"] += 1
            generation = _dict(record.get("candidate_generation_contract"))
            if (
                generation.get("reference_blend_steps") is not None
                or record.get("candidate_reference_blend_steps") is not None
            ):
                totals["reference_blend_enabled_records"] += 1
            if bool(generation.get("guidance_enabled")):
                totals["guidance_enabled_records"] += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                totals["postselection_records"] += 1
            provenance = _dict(record.get("camp_candidate_tensor_provenance"))
            if provenance:
                totals["camp_candidate_tensor_provenance_records"] += 1
            if bool(provenance.get("candidate_generation_effect")):
                totals["camp_candidate_generation_effect_records"] += 1
            if bool(provenance.get("dp_modification_authorized")) or bool(
                generation.get("changes_diffusion_planner_weights")
            ):
                totals["dp_modification_records"] += 1
            if _default_off_shadow_selector_valid(record, candidate_count=candidate_count):
                totals["default_off_shadow_selector_valid_records"] += 1
            if record.get("shadow_selected_index") != 0:
                totals["shadow_differs_from_dp_top1_records"] += 1
    summary: dict[str, Any] = {key: int(value) for key, value in totals.items()}
    for key, counter in counters.items():
        summary[key] = dict(sorted(counter.items()))
    return summary


def _materialize_registries(
    *,
    artifact_dir: Path,
    evaluation_output_dir: Path,
    previous_training_output_dir: Path,
    previous_training_summary_json: Path,
    rejected_eval_output_dir: Path,
    selection_logs: list[Path],
) -> dict[str, Any]:
    previous_logs = _training_summary_logs(previous_training_summary_json)
    rejected_logs = sorted(rejected_eval_output_dir.rglob("camp_selection_log.json"))
    prior_logs = previous_logs + rejected_logs
    prior_hashes = _candidate_hashes_from_logs(prior_logs)
    eval_hashes = _candidate_hashes_from_logs(selection_logs)
    prior_hash_set = set(prior_hashes)
    eval_hash_set = set(eval_hashes)

    training_path_signatures = [
        _path_signature(log_path, previous_training_output_dir)
        for log_path in previous_logs
    ] + [
        _path_signature(log_path, rejected_eval_output_dir)
        for log_path in rejected_logs
    ]
    eval_path_signatures = [
        _path_signature(log_path, evaluation_output_dir) for log_path in selection_logs
    ]
    training_record_identities = _record_identity_hashes(
        previous_logs,
        previous_training_output_dir,
    ) + _record_identity_hashes(rejected_logs, rejected_eval_output_dir)
    eval_record_identities = _record_identity_hashes(selection_logs, evaluation_output_dir)

    split_manifest = {
        "schema_version": "dp_camp_v13_nonoverlap_remediation_split_manifest_v1",
        "training": {
            "selection_log_roots": [str(path.parent) for path in prior_logs],
            "seeds": sorted(
                {
                    seed
                    for seed in (
                        _metadata_from_log_path(path, previous_training_output_dir).get("seed")
                        for path in previous_logs
                    )
                    if seed is not None
                }
                | {
                    seed
                    for seed in (
                        _metadata_from_log_path(path, rejected_eval_output_dir).get("seed")
                        for path in rejected_logs
                    )
                    if seed is not None
                }
            ),
            "sources": [str(previous_training_output_dir), str(rejected_eval_output_dir)],
        },
        "holdout": {
            "selection_log_roots": [str(path.parent) for path in selection_logs],
            "seeds": sorted(
                {
                    seed
                    for seed in (
                        _metadata_from_log_path(path, evaluation_output_dir).get("seed")
                        for path in selection_logs
                    )
                    if seed is not None
                }
            ),
            "source": str(evaluation_output_dir),
        },
    }
    candidate_registry = {
        "schema_version": "dp_camp_v13_nonoverlap_remediation_candidate_tensor_hash_registry_v1",
        "training": {"values": prior_hashes, "source_log_count": len(prior_logs)},
        "evaluation": {"values": eval_hashes, "source_log_count": len(selection_logs)},
    }
    path_registry = {
        "schema_version": "dp_camp_v13_nonoverlap_remediation_path_signature_registry_v1",
        "training": {"signatures": training_path_signatures},
        "evaluation": {"signatures": eval_path_signatures},
    }
    record_identity_registry = {
        "schema_version": "dp_camp_v13_nonoverlap_remediation_record_identity_hash_registry_v1",
        "training": {"record_identities": training_record_identities},
        "evaluation": {"record_identities": eval_record_identities},
    }
    _write_json(artifact_dir / "split_manifest.json", split_manifest)
    _write_json(artifact_dir / "candidate_tensor_hash_registry.json", candidate_registry)
    _write_json(artifact_dir / "path_signature_registry.json", path_registry)
    _write_json(artifact_dir / "record_identity_hash_registry.json", record_identity_registry)

    eval_hash_overlap_count = sum(1 for value in eval_hashes if value in prior_hash_set)
    training_roots = set(split_manifest["training"]["selection_log_roots"])
    holdout_roots = set(split_manifest["holdout"]["selection_log_roots"])
    summary = {
        "previous_training_log_count": len(previous_logs),
        "rejected_eval_log_count": len(rejected_logs),
        "evaluation_log_count": len(selection_logs),
        "previous_plus_rejected_record_count": len(training_record_identities),
        "evaluation_record_count": len(eval_record_identities),
        "candidate_hash_training_value_count": len(prior_hashes),
        "candidate_hash_training_unique_value_count": len(prior_hash_set),
        "candidate_hash_evaluation_value_count": len(eval_hashes),
        "candidate_hash_evaluation_unique_value_count": len(eval_hash_set),
        "eval_hashes_in_previous_count": eval_hash_overlap_count,
        "eval_hashes_in_previous_rate": (
            float(eval_hash_overlap_count / len(eval_hashes)) if eval_hashes else None
        ),
        "candidate_hash_intersection_count": len(prior_hash_set.intersection(eval_hash_set)),
        "path_signature_intersection_count": len(
            set(training_path_signatures).intersection(eval_path_signatures)
        ),
        "record_identity_intersection_count": len(
            set(training_record_identities).intersection(eval_record_identities)
        ),
        "split_manifest_training_root_count": len(training_roots),
        "split_manifest_holdout_root_count": len(holdout_roots),
        "split_manifest_root_intersection_count": len(training_roots.intersection(holdout_roots)),
    }
    _write_json(artifact_dir / "support_registry_summary.json", summary)
    return summary


def _readiness_failures(
    *,
    selection_logs: list[Path],
    clean_contract: dict[str, Any],
    record_summary: dict[str, Any],
    nonoverlap: dict[str, Any],
) -> list[str]:
    failures: list[str] = []

    def expect(name: str, observed: Any, expected: Any) -> None:
        if observed != expected:
            failures.append(f"{name}:expected={expected}:observed={observed}")

    expect("selection_log_count", len(selection_logs), 32)
    expect("records_total", record_summary.get("records_total", 0), 3200)
    expect("clean_contract_passed", clean_contract.get("passed"), True)
    expect("clean_contract_records", clean_contract.get("records"), 3200)
    expect(
        "future_training_input_contract_satisfied",
        clean_contract.get("future_training_input_contract_satisfied"),
        True,
    )
    expect("candidate_count_values", record_summary.get("candidate_count_values"), {"8": 3200})
    expect(
        "atom_schema_versions",
        record_summary.get("atom_schema_versions"),
        {ATOM_SCHEMA_VERSION: 3200},
    )
    expect("atom_count_values", record_summary.get("atom_count_values"), {"14": 3200})
    expect("formal_seed_records", record_summary.get("formal_seed_records", 0), 0)
    expect("closed_loop_outcome_records", record_summary.get("closed_loop_outcome_records", 0), 0)
    expect(
        "reference_blend_enabled_records",
        record_summary.get("reference_blend_enabled_records", 0),
        0,
    )
    expect("guidance_enabled_records", record_summary.get("guidance_enabled_records", 0), 0)
    expect("postselection_records", record_summary.get("postselection_records", 0), 0)
    expect(
        "camp_candidate_generation_effect_records",
        record_summary.get("camp_candidate_generation_effect_records", 0),
        0,
    )
    expect("dp_modification_records", record_summary.get("dp_modification_records", 0), 0)
    expect(
        "default_off_shadow_selector_valid_records",
        record_summary.get("default_off_shadow_selector_valid_records", 0),
        3200,
    )
    expect(
        "camp_candidate_tensor_provenance_records",
        record_summary.get("camp_candidate_tensor_provenance_records", 0),
        3200,
    )
    expect("selected_index_counts", record_summary.get("selected_index_counts"), {"0": 3200})
    expect("executed_index_counts", record_summary.get("executed_index_counts"), {"0": 3200})
    if len(record_summary.get("route_records", {})) < 4:
        failures.append("routes_at_least_4")
    if len(record_summary.get("seed_records", {})) < 2:
        failures.append("seeds_at_least_2")
    if len(record_summary.get("route_tl_records", {})) < 8:
        failures.append("route_tl_buckets_at_least_8")
    if record_summary.get("usable_feasible_records", 0) < 100:
        failures.append("usable_feasible_records_at_least_100")
    if record_summary.get("multi_feasible_records", 0) < 100:
        failures.append("multi_feasible_records_at_least_100")
    expect("finite_reward_records", record_summary.get("finite_reward_records", 0), 3200)
    expect("eval_hashes_in_previous_count", nonoverlap["eval_hashes_in_previous_count"], 0)
    expect("candidate_hash_intersection_count", nonoverlap["candidate_hash_intersection_count"], 0)
    expect("path_signature_intersection_count", nonoverlap["path_signature_intersection_count"], 0)
    expect("record_identity_intersection_count", nonoverlap["record_identity_intersection_count"], 0)
    expect(
        "split_manifest_root_intersection_count",
        nonoverlap["split_manifest_root_intersection_count"],
        0,
    )
    return sorted(failures)


def _write_heads(
    *,
    artifact_dir: Path,
    camp_repo: Path,
    diffusion_repo: Path,
) -> dict[str, str]:
    heads = {
        "camp_head": _git(["rev-parse", "HEAD"], camp_repo),
        "camp_origin_main": _git(["rev-parse", "origin/main"], camp_repo),
        "camp_status_head": _git(["status", "--short", "--branch"], camp_repo).splitlines()[0],
        "dp_head": _git(["rev-parse", "HEAD"], diffusion_repo),
        "dp_status_head": _git(["status", "--short", "--branch"], diffusion_repo).splitlines()[0],
        "required_dp_head": FIXED_DP_HEAD,
    }
    (artifact_dir / "HEADS.txt").write_text(
        "\n".join(f"{key}={value}" for key, value in heads.items()) + "\n",
        encoding="utf-8",
    )
    return heads


def _write_runtime_manifest(
    *,
    artifact_dir: Path,
    template_path: Path,
    heads: dict[str, str],
) -> Path:
    payload = _read_json_dict(template_path)
    payload["schema_version"] = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
    payload["gate"] = GATE
    payload["current_camp_head"] = heads["camp_head"]
    payload["current_camp_origin_main"] = heads["camp_origin_main"]
    payload["current_dp_head"] = heads["dp_head"]
    payload["required_dp_head"] = FIXED_DP_HEAD
    payload["default_off"] = True
    payload["selection_effect"] = False
    payload["executed_output_policy"] = "dp_top1"
    payload["candidate_operation"] = "fixed DP candidate reranking only"
    payload["score_expression"] = SCORE_EXPRESSION
    payload["training_execution_authorized"] = False
    payload["dp_modification_authorized"] = False
    payload["safety_benefit_claim_authorized"] = False
    payload["camp_over_dp_top1_claim_authorized"] = False
    runtime_dir = artifact_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output = runtime_dir / "dp_camp_v13_nonoverlap_remediation_static_shadow_manifest_runtime.json"
    _write_json(output, payload)
    return output


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=str(cwd), text=True).strip()


def _candidate_hashes_from_logs(log_paths: list[Path]) -> list[str]:
    hashes: list[str] = []
    for log_path in log_paths:
        if not log_path.is_file():
            continue
        for record in _read_json_list(log_path):
            value = _candidate_tensor_hash(record)
            if value:
                hashes.append(value)
    return hashes


def _record_identity_hashes(log_paths: list[Path], root: Path) -> list[str]:
    identities: list[str] = []
    for log_path in log_paths:
        if not log_path.is_file():
            continue
        path_signature_hash = _path_signature(log_path, root)
        for index, record in enumerate(_read_json_list(log_path)):
            identities.append(
                _stable_hash(
                    {
                        "path_signature_hash": path_signature_hash,
                        "record_index": index,
                        "selection_step": record.get("selection_step"),
                        "candidate_tensor_hash": _candidate_tensor_hash(record),
                    }
                )
            )
    return identities


def _path_signature(log_path: Path, root: Path) -> str:
    return _stable_hash(_metadata_from_log_path(log_path, root))


def _metadata_from_log_path(log_path: Path, root: Path) -> dict[str, Any]:
    try:
        parts = log_path.relative_to(root).parts
    except ValueError:
        parts = log_path.parts
    route = parts[0] if parts else "unknown"
    seed: int | None = None
    max_npcs: int | None = None
    traffic_lights: str | None = None
    spawn_probability: float | None = None
    for part in parts:
        if part.startswith("seed_"):
            try:
                seed = int(part.split("_", 1)[1])
            except ValueError:
                seed = None
        elif part.startswith("npc_"):
            try:
                max_npcs = int(part.split("_", 1)[1])
            except ValueError:
                max_npcs = None
        elif part.startswith("spawn_"):
            try:
                spawn_probability = float(part.split("_", 1)[1].replace("p", "."))
            except ValueError:
                spawn_probability = None
        elif part in {"tl_on", "tl_off"}:
            traffic_lights = part.split("_", 1)[1]
    return {
        "route": route,
        "seed": seed,
        "max_npcs": max_npcs,
        "traffic_lights": traffic_lights,
        "spawn_probability": spawn_probability,
    }


def _training_summary_logs(path: Path) -> list[Path]:
    payload = _read_json_dict(path)
    logs = payload.get("selection_logs")
    if not isinstance(logs, list):
        return []
    return [Path(value) for value in logs if isinstance(value, str)]


def _base_report(
    *,
    artifact_dir: Path,
    heads: dict[str, str],
    execute: bool,
    status: str,
    passed: bool,
    failed_checks: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "gate": GATE,
        "artifact": str(artifact_dir),
        "execute": execute,
        "heads": heads,
        "final_decision": _decision(
            status=status,
            passed=passed,
            failed_checks=failed_checks,
            authorized_next_work=NEXT_GATE if passed and execute else None,
        ),
    }


def _decision(
    *,
    status: str,
    passed: bool,
    failed_checks: list[str],
    authorized_next_work: str | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": authorized_next_work,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _write_report(artifact_dir: Path, report: dict[str, Any], *, exit_code: int) -> None:
    _write_json(artifact_dir / "nonoverlap_readiness.json", report)
    (artifact_dir / "nonoverlap_readiness.md").write_text(
        _render_readiness_markdown(report),
        encoding="utf-8",
    )
    (artifact_dir / "nonoverlap_readiness.exit").write_text(
        f"{exit_code}\n",
        encoding="utf-8",
    )
    _write_sha256sums(artifact_dir)


def _render_readiness_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    record_summary = report.get("record_summary", {})
    nonoverlap = report.get("nonoverlap", {})
    clean = report.get("clean_contract", {})
    lines = [
        "# V13 Result Readiness Rejected Non-Overlap Remediation",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision.get('authorized_next_work')}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Selection logs: `{report.get('selection_log_count')}`",
        f"- Records: `{record_summary.get('records_total')}`",
        f"- Clean contract passed: `{clean.get('passed')}`",
        f"- Candidate hash intersection: `{nonoverlap.get('candidate_hash_intersection_count')}`",
        f"- Path signature intersection: `{nonoverlap.get('path_signature_intersection_count')}`",
        f"- Record identity intersection: `{nonoverlap.get('record_identity_intersection_count')}`",
        f"- Provenance records: `{record_summary.get('camp_candidate_tensor_provenance_records')}`",
        "",
        "This gate only collects fixed-DP, DP-native candidate logs under a "
        "default-off shadow selector. Executed output remains DP Top-1; CAMP "
        "only shadow-reranks fixed DP candidate tensors. No training, DP "
        "modification, selector/atom promotion, deployment, safety claim, or "
        "CAMP-over-DP Top-1 claim is made.",
        "",
    ]
    return "\n".join(lines)


def _render_clean_contract_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Clean Contract Validation",
            "",
            f"- Passed: `{report.get('passed')}`",
            f"- Records: `{report.get('records')}`",
            f"- Failed records: `{len(report.get('failed_records', []))}`",
            "",
        ]
    )


def _write_runbook(path: Path, commands: list[dict[str, Any]]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "cd /root/autodl-tmp/camp_core",
        (
            "export PYTHONPATH=/root/autodl-tmp/Diffusion-Planner:"
            "/root/autodl-tmp/Diffusion-Planner/diffusion_planner"
        ),
    ]
    for entry in commands:
        lines.extend(
            [
                "",
                (
                    f"# command {entry['index']:03d}: route={entry['route_name']} "
                    f"seed={entry['seed']} npc={entry['max_npcs']} "
                    f"tl={entry['traffic_lights']}"
                ),
                " ".join(shlex.quote(str(part)) for part in entry["command"]),
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_progress(path: Path, event: str, **payload: Any) -> None:
    row = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event,
        **payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_stable(row), sort_keys=True) + "\n")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(_stable(payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return str(value)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256sums(root: Path) -> None:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
