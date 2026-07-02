#!/usr/bin/env python3
"""Execute the v14 public-simulator fixed-DP candidate generation gate.

This wrapper consumes a previously passed v14 preflight JSON, rechecks the
current v14 EOF execution authorization, and runs the preflight-approved
Diffusion Planner replay commands under an explicit guard. It does not train
CAMP, modify DP, promote, deploy, or change executed trajectory semantics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CURRENT_STATUS = "public_simulator_fixed_dp_candidate_generation_preflight_ready"
AUTHORIZED_CURRENT_WORK = "public_simulator_fixed_dp_candidate_generation_execution"
AUTHORIZED_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation"
PREFLIGHT_READY_STATUS = "public_simulator_fixed_dp_candidate_generation_preflight_ready"
EXECUTION_PASSED_STATUS = "public_simulator_fixed_dp_candidate_generation_execution_passed"
EXECUTION_FAILED_STATUS = "public_simulator_fixed_dp_candidate_generation_execution_failed"
GUARD_ENV_VAR = "DP_CAMP_V14_PUBLIC_SIMULATOR_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
EXPECTED_COMMAND_COUNT = 32
EXPECTED_STEPS_PER_COMMAND = 100
EXPECTED_RECORDS = 3200
EXPECTED_NUM_CANDIDATES = 8
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
REPLAY_SCRIPT_NAME = "run_diffusion_planner_camp_replay.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.execution_artifact_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(
        preflight_json=args.preflight_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        execution_artifact_dir=args.execution_artifact_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    if report["pre_execution_decision"]["passed"]:
        execution = execute_commands(report, args.execution_artifact_dir)
        report["execution"] = execution
        report["final_decision"] = _final_decision(
            pre_execution_passed=True,
            execution=execution,
            authorized_next_work=args.authorized_next_work,
        )
    else:
        report["execution"] = None
        report["final_decision"] = _final_decision(
            pre_execution_passed=False,
            execution=None,
            authorized_next_work=args.authorized_next_work,
        )
    _write_outputs(args.execution_artifact_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    preflight_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    execution_artifact_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    preflight = _read_json(preflight_json)
    commands = _planned_commands(preflight)
    preflight_section = _dict(preflight.get("public_simulator_preflight"))
    candidate_output_root = Path(str(preflight_section.get("candidate_output_root", ""))).resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks = _checks(
        preflight_json=preflight_json,
        preflight=preflight,
        commands=commands,
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        v14_text=v14_text,
        status_text=status_text,
        execution_artifact_dir=execution_artifact_dir,
        candidate_output_root=candidate_output_root,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    pre_passed = not failed
    return {
        "schema_version": "dp_camp_v14_public_simulator_fixed_dp_candidate_generation_execution_v1",
        "analysis": {
            "fixed_dp_candidate_generation_execution_gate": True,
            "candidate_generation_source": "fixed Diffusion Planner replay commands from passed v14 preflight",
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "executed_output_policy": "dp_top1",
            "default_off_shadow_selector": True,
            "candidate_tensor_provenance_logging": True,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "preflight_json": str(preflight_json),
            "preflight_json_sha256": _sha256(preflight_json) if preflight_json.is_file() else None,
            "v14_audit_md": str(v14_audit_md),
            "current_status_md": str(current_status_md),
            "execution_artifact_dir": str(execution_artifact_dir),
            "candidate_output_root": str(candidate_output_root),
            "candidate_output_root_exists_before": candidate_output_root.exists(),
            "guard_env_var": GUARD_ENV_VAR,
            "guard_env_value": os.environ.get(GUARD_ENV_VAR),
            "planned_command_count": len(commands),
            "expected_steps_per_command": EXPECTED_STEPS_PER_COMMAND,
            "expected_records": EXPECTED_RECORDS,
        },
        "preflight_final_decision": _dict(preflight.get("final_decision")),
        "preflight_public_simulator": preflight_section,
        "checks": checks,
        "pre_execution_decision": {
            "passed": pre_passed,
            "status": "public_simulator_fixed_dp_candidate_generation_execution_prechecks_passed"
            if pre_passed
            else "public_simulator_fixed_dp_candidate_generation_execution_prechecks_failed",
            "failed_checks": failed,
            "failure_class": None if pre_passed else _failure_class(failed),
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if pre_passed else None,
        },
        "commands": commands,
    }


def execute_commands(report: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    commands = [_list(command) for command in _list(report.get("commands"))]
    preflight = _dict(report.get("preflight_public_simulator"))
    camp_repo = Path(str(preflight.get("camp_repo")))
    dp_repo = Path(str(preflight.get("dp_repo")))
    candidate_output_root = Path(str(report["inputs"]["candidate_output_root"]))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(
        [
            str(camp_repo),
            str(camp_repo / "camp_core"),
            str(dp_repo),
            str(dp_repo / "diffusion_planner"),
            env.get("PYTHONPATH", ""),
        ]
    )
    command_results: list[dict[str, Any]] = []
    started_at = time.time()
    for index, command in enumerate(commands, start=1):
        stdout_path = artifact_dir / f"command_{index:02d}.stdout.log"
        stderr_path = artifact_dir / f"command_{index:02d}.stderr.log"
        command_path = artifact_dir / f"command_{index:02d}.json"
        command_path.write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
        with stdout_path.open("w", encoding="utf-8") as stdout_fh, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_fh:
            proc = subprocess.run(command, stdout=stdout_fh, stderr=stderr_fh, env=env)
        result = {
            "index": index,
            "exit_code": proc.returncode,
            "output_dir": _option_value(command, "--output_dir"),
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "command_json": str(command_path),
        }
        command_results.append(result)
        if proc.returncode != 0:
            break
    duration_s = time.time() - started_at
    all_succeeded = len(command_results) == len(commands) and all(
        result["exit_code"] == 0 for result in command_results
    )
    summaries = _summarize_outputs(candidate_output_root)
    return {
        "status": EXECUTION_PASSED_STATUS if all_succeeded else EXECUTION_FAILED_STATUS,
        "passed": all_succeeded,
        "command_count": len(commands),
        "commands_started": len(command_results),
        "commands_succeeded": sum(1 for result in command_results if result["exit_code"] == 0),
        "first_failed_command": next(
            (result for result in command_results if result["exit_code"] != 0),
            None,
        ),
        "duration_s": duration_s,
        "candidate_output_root": str(candidate_output_root),
        "candidate_output_root_exists_after": candidate_output_root.exists(),
        "command_results": command_results,
        "output_summary": summaries,
    }


def _checks(
    *,
    preflight_json: Path,
    preflight: dict[str, Any],
    commands: list[list[str]],
    v14_audit_md: Path,
    current_status_md: Path,
    v14_text: str,
    status_text: str,
    execution_artifact_dir: Path,
    candidate_output_root: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    pre_decision = _dict(preflight.get("final_decision"))
    preflight_section = _dict(preflight.get("public_simulator_preflight"))
    command_text = "\n".join(" ".join(command).lower() for command in commands)

    add(_expect("guard_env_set", os.environ.get(GUARD_ENV_VAR), "1"))
    add(_expect("preflight_json_exists", preflight_json.is_file(), True))
    add(_expect("v14_audit_exists", v14_audit_md.is_file(), True))
    add(_expect("current_status_exists", current_status_md.is_file(), True))
    add(_expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work))
    add(_expect("status_doc_points_to_v14", "docs/diffusion_planner_v14_iteration_audit.md" in status_text, True))
    add(_expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True))
    add(_expect("status_doc_next_work", authorized_current_work in status_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("preflight_passed", pre_decision.get("passed"), True))
    add(_expect("preflight_status_ready", pre_decision.get("status"), PREFLIGHT_READY_STATUS))
    add(_expect("preflight_authorized_next_is_execution", pre_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("preflight_fixed_dp_generation_executed_false", pre_decision.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("preflight_default_off_shadow_selector", preflight_section.get("default_off_shadow_selector"), True))
    add(_expect("preflight_candidate_tensor_provenance_logging", preflight_section.get("candidate_tensor_provenance_logging"), True))
    add(_expect("preflight_executed_output_policy", preflight_section.get("executed_output_policy"), "dp_top1"))
    add(_expect("candidate_output_root_absent_before", candidate_output_root.exists(), False))
    add(_expect("execution_artifact_dir_exists", execution_artifact_dir.is_dir(), True))
    add(_expect("planned_command_count", len(commands), EXPECTED_COMMAND_COUNT))
    add(_expect("preflight_expected_records", preflight_section.get("expected_records"), EXPECTED_RECORDS))
    add(_expect("preflight_steps_per_command", preflight_section.get("steps_per_command"), EXPECTED_STEPS_PER_COMMAND))
    add(_expect("preflight_num_candidates", preflight_section.get("num_candidates"), EXPECTED_NUM_CANDIDATES))
    add(_expect("formal_seeds_forbidden", any(_option_value(command, "--seed") in {"11", "12", "13"} for command in commands), False))
    for command in commands:
        add(_expect("command_uses_replay_script", any(REPLAY_SCRIPT_NAME in part for part in command), True))
        add(_expect("command_uses_static_shadow_selector", "--camp_selector_mode" in command and "static" in command, True))
        add(_expect("command_logs_candidate_tensor_provenance", "--camp_candidate_tensor_provenance_logging" in command, True))
        add(_expect("command_enables_default_off_shadow_selector", "--camp_default_off_shadow_selector" in command, True))
        add(_expect("command_has_num_candidates_8", _option_value(command, "--num_candidates"), "8"))
        add(_expect("command_has_steps_100", _option_value(command, "--steps"), "100"))
        add(_expect("command_has_output_dir", bool(_option_value(command, "--output_dir")), True))
    for snippet in FORBIDDEN_SNIPPETS:
        add(_expect(f"planned_commands_forbid_{_slug(snippet)}", snippet in command_text, False))
    return checks


def _final_decision(
    *,
    pre_execution_passed: bool,
    execution: dict[str, Any] | None,
    authorized_next_work: str,
) -> dict[str, Any]:
    execution_passed = bool(execution and execution.get("passed"))
    return {
        "status": EXECUTION_PASSED_STATUS if execution_passed else EXECUTION_FAILED_STATUS,
        "passed": pre_execution_passed and execution_passed,
        "failure_class": None if execution_passed else "fixed_dp_candidate_generation_execution_failed",
        "authorized_next_work": authorized_next_work if execution_passed else None,
        "recommended_next_work": authorized_next_work
        if execution_passed
        else "public_simulator_fixed_dp_candidate_generation_execution_remediation",
        "fixed_dp_candidate_generation_executed": execution_passed,
        "fixed_dp_candidate_generation_execution_passed": execution_passed,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "zero_overlap_validation_authorized_next": execution_passed,
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
        "candidate_operation": "fixed DP candidate generation for later CAMP reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _summarize_outputs(candidate_output_root: Path) -> dict[str, Any]:
    validation_files = sorted(candidate_output_root.rglob("camp_validation_summary.json")) if candidate_output_root.exists() else []
    replay_files = sorted(candidate_output_root.rglob("camp_replay_summary.json")) if candidate_output_root.exists() else []
    default_off_logs = 0
    provenance_logs = 0
    for path in validation_files:
        payload = _read_json(path)
        if payload.get("camp_default_off_shadow_selector") is not None:
            default_off_logs += 1
        if payload.get("camp_candidate_tensor_provenance") is not None:
            provenance_logs += 1
    return {
        "validation_summary_count": len(validation_files),
        "replay_summary_count": len(replay_files),
        "default_off_shadow_selector_summary_count": default_off_logs,
        "candidate_tensor_provenance_summary_count": provenance_logs,
    }


def _write_outputs(artifact_dir: Path, report: dict[str, Any]) -> None:
    report_path = artifact_dir / "execution_report.json"
    report_path.write_text(json.dumps(_stable(_without_commands(report)), indent=2) + "\n", encoding="utf-8")
    (artifact_dir / "execution_report.md").write_text(_render_markdown(report), encoding="utf-8")
    sha_paths = [path for path in artifact_dir.iterdir() if path.is_file() and path.name != "SHA256SUMS"]
    lines = [f"{_sha256(path)}  {path.name}" for path in sorted(sha_paths)]
    (artifact_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    execution = _dict(report.get("execution"))
    output = _dict(execution.get("output_summary"))
    return "\n".join(
        [
            "# V14 Public Simulator Fixed-DP Candidate Generation Execution",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Commands started: `{execution.get('commands_started')}`",
            f"- Commands succeeded: `{execution.get('commands_succeeded')}`",
            f"- Candidate output root: `{execution.get('candidate_output_root')}`",
            f"- Validation summaries: `{output.get('validation_summary_count')}`",
            f"- Replay summaries: `{output.get('replay_summary_count')}`",
            f"- Default-off shadow summaries: `{output.get('default_off_shadow_selector_summary_count')}`",
            f"- Candidate tensor provenance summaries: `{output.get('candidate_tensor_provenance_summary_count')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- CAMP generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training execution authorized: `{decision.get('training_execution_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Safety benefit claim authorized: `{decision.get('safety_benefit_claim_authorized')}`",
            "",
        ]
    )


def _without_commands(report: dict[str, Any]) -> dict[str, Any]:
    copy = dict(report)
    copy.pop("commands", None)
    return copy


def _failure_class(failed: list[str]) -> str:
    if "guard_env_set" in failed:
        return "execution_guard_not_set"
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("dp_head" in check for check in failed):
        return "fixed_dp_head_mismatch"
    if any("candidate_output_root" in check for check in failed):
        return "candidate_output_root_not_fresh"
    return "fixed_dp_candidate_generation_execution_precheck_failure"


def _planned_commands(preflight: dict[str, Any]) -> list[list[str]]:
    return [
        [str(part) for part in _list(command)]
        for command in _list(_dict(preflight.get("public_simulator_preflight")).get("planned_commands"))
    ]


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": actual == expected}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
