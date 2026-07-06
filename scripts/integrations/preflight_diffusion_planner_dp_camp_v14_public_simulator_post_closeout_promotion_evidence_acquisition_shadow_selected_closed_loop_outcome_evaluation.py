#!/usr/bin/env python3
"""Preflight shadow-selected closed-loop outcome evaluation.

This gate derives a future offline replay runbook from the audited
default-off shadow-selector runbook. It does not execute replay, modify
Diffusion Planner, train CAMP, generate candidates outside the fixed DP
candidate tensor runner, promote, deploy, enable an online selector, or make a
SafetyCost/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_FAILURE_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_failed_user_decision_required"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_execution_only"
)
AUTHORIZED_PREFLIGHT_EOF_PAIRS = {
    (SOURCE_FAILURE_STATUS, AUTHORIZED_CURRENT_WORK),
    (READY_STATUS, AUTHORIZED_NEXT_WORK),
}
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "shadow_selected_closed_loop_outcome_evaluation_preflight_v1"
)
PREFLIGHT_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_preflight.md"
)
RUNBOOK_NAME = "run_shadow_selected_closed_loop_outcome_evaluation.sh"

FORMAL_SEEDS = {11, 12, 13}
FULL36_MARKERS = ("full36", "full_36", "formal36")
REMOVE_FLAGS = {
    "--camp_default_off_shadow_selector": 0,
    "--camp_shadow_artifact_manifest": 1,
    "--camp_shadow_expected_atom_scales_sha256": 1,
    "--camp_shadow_expected_static_weights_sha256": 1,
}
FORBIDDEN_GENERATED_FLAGS = {
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_default_off_shadow_selector",
    "--camp_collect_closed_loop_outcomes",
    "--camp_splice_shadow_rule",
    "--camp_perfect_tracker_command_postselection",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
}
BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "training_authorized",
    "candidate_generation_by_camp_authorized",
    "dp_modification_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_runtime_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_runtime_runbook", type=Path, required=True)
    parser.add_argument("--source_runtime_execution_root", type=Path, required=True)
    parser.add_argument("--paired_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--paired_execution_json", type=Path, required=True)
    parser.add_argument("--materialization_failure_artifact_dir", type=Path, required=True)
    parser.add_argument("--materialization_failure_json", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--shadow_selected_output_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_command_count", type=int, default=32)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_shadow_selected_closed_loop_outcome_evaluation_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_runtime_execution_artifact_dir=args.source_runtime_execution_artifact_dir,
        source_runtime_runbook=args.source_runtime_runbook,
        source_runtime_execution_root=args.source_runtime_execution_root,
        paired_execution_artifact_dir=args.paired_execution_artifact_dir,
        paired_execution_json=args.paired_execution_json,
        materialization_failure_artifact_dir=args.materialization_failure_artifact_dir,
        materialization_failure_json=args.materialization_failure_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        shadow_selected_output_root=args.shadow_selected_output_root,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_command_count=args.expected_command_count,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_shadow_selected_closed_loop_outcome_evaluation_preflight
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_runtime_execution_artifact_dir: Path,
    source_runtime_runbook: Path,
    source_runtime_execution_root: Path,
    paired_execution_artifact_dir: Path,
    paired_execution_json: Path,
    materialization_failure_artifact_dir: Path,
    materialization_failure_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    shadow_selected_output_root: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_command_count: int = 32,
    enabled: bool = False,
) -> dict[str, Any]:
    source_runtime_execution_artifact_dir = source_runtime_execution_artifact_dir.resolve()
    source_runtime_runbook = source_runtime_runbook.resolve()
    source_runtime_execution_root = source_runtime_execution_root.resolve()
    paired_execution_artifact_dir = paired_execution_artifact_dir.resolve()
    paired_execution_json = paired_execution_json.resolve()
    materialization_failure_artifact_dir = materialization_failure_artifact_dir.resolve()
    materialization_failure_json = materialization_failure_json.resolve()
    shadow_selected_output_root = shadow_selected_output_root.resolve()
    output_dir = output_dir.resolve()

    source_heads = _parse_key_values(_read_text(source_runtime_execution_artifact_dir / "HEADS"))
    paired_execution = _read_json_dict(paired_execution_json)
    materialization_failure = _read_json_dict(materialization_failure_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source_runbook_text = _read_text(source_runtime_runbook)
    source_commands = _extract_python_commands(source_runbook_text)
    generated_commands = [
        _transform_command(
            command,
            source_runtime_execution_root=source_runtime_execution_root,
            shadow_selected_output_root=shadow_selected_output_root,
        )
        for command in source_commands
    ]
    generated_runbook = _render_runbook(
        commands=generated_commands,
        shadow_selected_output_root=shadow_selected_output_root,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    inventory = _command_inventory(source_commands, generated_commands, shadow_selected_output_root)
    checks = _checks(
        enabled=enabled,
        source_runtime_execution_artifact_dir=source_runtime_execution_artifact_dir,
        source_runtime_runbook=source_runtime_runbook,
        source_runtime_execution_root=source_runtime_execution_root,
        paired_execution_artifact_dir=paired_execution_artifact_dir,
        paired_execution_json=paired_execution_json,
        materialization_failure_artifact_dir=materialization_failure_artifact_dir,
        materialization_failure_json=materialization_failure_json,
        source_heads=source_heads,
        paired_execution=paired_execution,
        materialization_failure=materialization_failure,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_command_count=expected_command_count,
        source_commands=source_commands,
        generated_commands=generated_commands,
        inventory=inventory,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "preflight_only": True,
            "runbook_materialization_only": True,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation_by_camp": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "online_selector_change": False,
            "safety_or_camp_over_dp_claim": False,
            "closed_loop_outcomes_training_or_online_input": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_runtime_execution_artifact_dir": str(source_runtime_execution_artifact_dir),
            "source_runtime_runbook": str(source_runtime_runbook),
            "source_runtime_execution_root": str(source_runtime_execution_root),
            "paired_execution_artifact_dir": str(paired_execution_artifact_dir),
            "paired_execution_json": str(paired_execution_json),
            "materialization_failure_artifact_dir": str(materialization_failure_artifact_dir),
            "materialization_failure_json": str(materialization_failure_json),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "shadow_selected_output_root": str(shadow_selected_output_root),
            "output_dir": str(output_dir),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_runtime_camp_head": source_heads.get("CAMP_HEAD"),
            "source_runtime_dp_head": source_heads.get("DP_HEAD"),
        },
        "source_artifacts": {
            "source_runtime_runbook_sha256": _sha256(source_runtime_runbook),
            "source_runtime_artifact_sha256s_sha256": _optional_sha256(
                source_runtime_execution_artifact_dir / "SHA256SUMS"
            ),
            "paired_execution_json_sha256": _sha256(paired_execution_json),
            "paired_execution_artifact_sha256s_sha256": _optional_sha256(
                paired_execution_artifact_dir / "SHA256SUMS"
            ),
            "materialization_failure_json_sha256": _sha256(materialization_failure_json),
            "materialization_failure_artifact_sha256s_sha256": _optional_sha256(
                materialization_failure_artifact_dir / "SHA256SUMS"
            ),
        },
        "runbook_plan": {
            "command_count": len(generated_commands),
            "source_command_count": len(source_commands),
            "shadow_selected_output_root": str(shadow_selected_output_root),
            "runbook_name": RUNBOOK_NAME,
            "execute_env_guard": "DP_CAMP_V14_SHADOW_SELECTED_OUTCOME_EVALUATION_EXECUTE=1",
            "generated_runbook_sha256": hashlib.sha256(generated_runbook.encode("utf-8")).hexdigest(),
            "inventory": inventory,
            "boundary_note": (
                "Future execution is offline evaluation only: it executes the CAMP static "
                "selector over fixed DP candidates to obtain shadow-selected run-level "
                "summaries, then later materialization must pair them against DP Top-1."
            ),
        },
        "generated_runbook": generated_runbook,
        "preflight_checks": checks,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": _decision(passed=passed, checks=checks, inventory=inventory),
    }


def _checks(
    *,
    enabled: bool,
    source_runtime_execution_artifact_dir: Path,
    source_runtime_runbook: Path,
    source_runtime_execution_root: Path,
    paired_execution_artifact_dir: Path,
    paired_execution_json: Path,
    materialization_failure_artifact_dir: Path,
    materialization_failure_json: Path,
    source_heads: dict[str, str],
    paired_execution: dict[str, Any],
    materialization_failure: dict[str, Any],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_command_count: int,
    source_commands: list[list[str]],
    generated_commands: list[list[str]],
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    paired_decision = _dict(paired_execution.get("final_decision"))
    materialization_decision = _dict(materialization_failure.get("final_decision"))
    return [
        _expect("preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("source_runtime_execution_artifact_dir_exists", source_runtime_execution_artifact_dir.is_dir(), str(source_runtime_execution_artifact_dir), "directory"),
        _check("source_runtime_runbook_exists", source_runtime_runbook.is_file(), str(source_runtime_runbook), "file"),
        _check("source_runtime_execution_root_exists", source_runtime_execution_root.is_dir(), str(source_runtime_execution_root), "directory"),
        _check("paired_execution_artifact_dir_exists", paired_execution_artifact_dir.is_dir(), str(paired_execution_artifact_dir), "directory"),
        _check("paired_execution_json_exists", paired_execution_json.is_file(), str(paired_execution_json), "file"),
        _check("materialization_failure_artifact_dir_exists", materialization_failure_artifact_dir.is_dir(), str(materialization_failure_artifact_dir), "directory"),
        _check("materialization_failure_json_exists", materialization_failure_json.is_file(), str(materialization_failure_json), "file"),
        _expect("source_runtime_dp_head_fixed", source_heads.get("DP_HEAD"), required_dp_head),
        _check(
            "audit_latest_eof_authorizes_preflight_or_refresh",
            (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target"))
            in AUTHORIZED_PREFLIGHT_EOF_PAIRS,
            f"{_latest_value(v14_text, 'current_v14_status')} / {_latest_value(v14_text, 'next_work_target')}",
            "authorized preflight or refresh EOF pair",
        ),
        _check(
            "status_latest_eof_authorizes_preflight_or_refresh",
            (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target"))
            in AUTHORIZED_PREFLIGHT_EOF_PAIRS,
            f"{_latest_value(status_text, 'current_v14_status')} / {_latest_value(status_text, 'next_work_target')}",
            "authorized preflight or refresh EOF pair",
        ),
        _expect("paired_execution_passed", paired_decision.get("passed"), True),
        _expect("paired_execution_actual_safetycost_unavailable", paired_decision.get("actual_safetycost_v1_available"), False),
        _expect("materialization_failure_rejected", materialization_decision.get("passed"), False),
        _expect("materialization_failure_class", materialization_decision.get("failure_class"), "actual_safetycost_outcome_source_missing"),
        _expect("source_command_count", len(source_commands), expected_command_count),
        _expect("generated_command_count", len(generated_commands), expected_command_count),
        _expect("source_default_off_command_count", inventory["source_default_off_command_count"], expected_command_count),
        _expect("generated_default_off_command_count", inventory["generated_default_off_command_count"], 0),
        _expect("generated_shadow_artifact_flag_count", inventory["generated_shadow_artifact_flag_count"], 0),
        _expect("generated_forbidden_flag_count", inventory["generated_forbidden_flag_count"], 0),
        _expect("generated_formal_seed_count", inventory["generated_formal_seed_count"], 0),
        _expect("generated_full36_path_count", inventory["generated_full36_path_count"], 0),
        _expect("generated_static_selector_count", inventory["generated_static_selector_count"], expected_command_count),
        _expect("generated_top1_fallback_count", inventory["generated_top1_fallback_count"], expected_command_count),
        _expect("generated_dp_reward_feasibility_count", inventory["generated_dp_reward_feasibility_count"], expected_command_count),
        _expect("generated_num_candidates_8_count", inventory["generated_num_candidates_8_count"], expected_command_count),
        _expect("generated_provenance_logging_count", inventory["generated_provenance_logging_count"], expected_command_count),
        _expect("generated_output_root_count", inventory["generated_output_root_count"], expected_command_count),
        _expect("generated_unique_output_dirs", inventory["generated_unique_output_dirs"], expected_command_count),
        _expect("generated_output_root_preexists", inventory["generated_output_root_exists"], False),
    ]


def _extract_python_commands(runbook_text: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for line in runbook_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "run_diffusion_planner_camp_replay.py" not in stripped:
            continue
        commands.append(shlex.split(stripped))
    return commands


def _transform_command(
    command: list[str],
    *,
    source_runtime_execution_root: Path,
    shadow_selected_output_root: Path,
) -> list[str]:
    transformed: list[str] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token in REMOVE_FLAGS:
            index += 1 + REMOVE_FLAGS[token]
            continue
        transformed.append(token)
        index += 1
    if "--output_dir" not in transformed:
        raise ValueError("source replay command is missing --output_dir")
    output_index = transformed.index("--output_dir") + 1
    source_output = Path(transformed[output_index])
    try:
        relative = source_output.relative_to(source_runtime_execution_root)
    except ValueError as exc:
        raise ValueError(f"source output dir {source_output} is outside source root {source_runtime_execution_root}") from exc
    parts = list(relative.parts)
    if parts and parts[-1] == "runtime_default_off_shadow_replay":
        parts[-1] = "runtime_shadow_selected_closed_loop_evaluation"
    else:
        parts.append("runtime_shadow_selected_closed_loop_evaluation")
    transformed[output_index] = str(shadow_selected_output_root.joinpath(*parts))
    return transformed


def _render_runbook(
    *,
    commands: list[list[str]],
    shadow_selected_output_root: Path,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str,
) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by the v14 shadow-selected closed-loop outcome evaluation preflight.",
        "# This runbook is offline evaluation only; it must not be used as deployment.",
        'if [ "${DP_CAMP_V14_SHADOW_SELECTED_OUTCOME_EVALUATION_EXECUTE:-}" != "1" ]; then',
        "  echo 'Refusing to run: set DP_CAMP_V14_SHADOW_SELECTED_OUTCOME_EVALUATION_EXECUTE=1 in an authorized execution gate' >&2",
        "  exit 40",
        "fi",
        "source /etc/network_turbo >/dev/null 2>&1 || true",
        f"CAMP_PREFLIGHT_HEAD='{current_camp_head}'",
        "CAMP_CURRENT_HEAD=\"$(git -C '/root/autodl-tmp/camp_core' rev-parse HEAD)\"",
        'if [ "$CAMP_CURRENT_HEAD" != "$CAMP_PREFLIGHT_HEAD" ]; then',
        "  if ! git -C '/root/autodl-tmp/camp_core' merge-base --is-ancestor \"$CAMP_PREFLIGHT_HEAD\" \"$CAMP_CURRENT_HEAD\"; then",
        "    echo 'CAMP HEAD mismatch' >&2",
        "    exit 41",
        "  fi",
        "  CAMP_RUNTIME_CHANGED_PATHS=\"$(git -C '/root/autodl-tmp/camp_core' diff --name-only \"$CAMP_PREFLIGHT_HEAD\" \"$CAMP_CURRENT_HEAD\" -- | grep -Ev '^(docs/|camp_core/tests/|README\\.md$)' || true)\"",
        '  if [ -n "$CAMP_RUNTIME_CHANGED_PATHS" ]; then',
        "    echo 'CAMP runtime paths changed since preflight head' >&2",
        "    printf '%s\\n' \"$CAMP_RUNTIME_CHANGED_PATHS\" >&2",
        "    exit 41",
        "  fi",
        "fi",
        f"if [ \"$(git -C '/root/autodl-tmp/Diffusion-Planner' rev-parse HEAD)\" != '{required_dp_head}' ]; then",
        "  echo 'DP HEAD mismatch' >&2",
        "  exit 42",
        "fi",
        f"if [ '{current_dp_head}' != '{required_dp_head}' ]; then",
        "  echo 'preflight DP HEAD mismatch' >&2",
        "  exit 43",
        "fi",
        f"if [ -e {shlex.quote(str(shadow_selected_output_root))} ]; then",
        "  echo 'Shadow-selected output root already exists' >&2",
        "  exit 44",
        "fi",
        "export PYTHONPATH='/root/autodl-tmp/camp_core':'/root/autodl-tmp/camp_core/camp_core':'/root/autodl-tmp/Diffusion-Planner':'/root/autodl-tmp/Diffusion-Planner/diffusion_planner':${PYTHONPATH:-}",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        lines.append(f"echo 'Running shadow-selected closed-loop outcome evaluation command {index}/{len(commands)}'")
        lines.append(" ".join(shlex.quote(part) for part in command))
        lines.append("")
    return "\n".join(lines)


def _command_inventory(
    source_commands: list[list[str]],
    generated_commands: list[list[str]],
    shadow_selected_output_root: Path,
) -> dict[str, Any]:
    generated_output_dirs = [_value_after(command, "--output_dir") for command in generated_commands]
    generated_seeds = [_int_or_none(_value_after(command, "--seed")) for command in generated_commands]
    generated_joined = [" ".join(command) for command in generated_commands]
    return {
        "source_command_count": len(source_commands),
        "generated_command_count": len(generated_commands),
        "source_default_off_command_count": sum("--camp_default_off_shadow_selector" in command for command in source_commands),
        "generated_default_off_command_count": sum("--camp_default_off_shadow_selector" in command for command in generated_commands),
        "generated_shadow_artifact_flag_count": sum(
            any(flag in command for flag in REMOVE_FLAGS if flag != "--camp_default_off_shadow_selector")
            for command in generated_commands
        ),
        "generated_forbidden_flag_count": sum(
            any(_forbidden_flag_present(command, flag) for flag in FORBIDDEN_GENERATED_FLAGS)
            for command in generated_commands
        ),
        "generated_formal_seed_count": sum(seed in FORMAL_SEEDS for seed in generated_seeds),
        "generated_full36_path_count": sum(
            any(marker in joined.lower() for marker in FULL36_MARKERS) for joined in generated_joined
        ),
        "generated_static_selector_count": sum(_value_after(command, "--camp_selector_mode") == "static" for command in generated_commands),
        "generated_top1_fallback_count": sum(_value_after(command, "--camp_fallback_mode") == "top1" for command in generated_commands),
        "generated_dp_reward_feasibility_count": sum(_value_after(command, "--camp_feasibility_source") == "dp_reward" for command in generated_commands),
        "generated_num_candidates_8_count": sum(_value_after(command, "--num_candidates") == "8" for command in generated_commands),
        "generated_provenance_logging_count": sum("--camp_candidate_tensor_provenance_logging" in command for command in generated_commands),
        "generated_output_root_count": sum(
            bool(path and Path(path).is_relative_to(shadow_selected_output_root)) for path in generated_output_dirs
        ),
        "generated_unique_output_dirs": len(set(generated_output_dirs)),
        "generated_output_root_exists": shadow_selected_output_root.exists(),
        "generated_output_dir_examples": generated_output_dirs[:5],
    }


def _forbidden_flag_present(command: list[str], flag: str) -> bool:
    if flag not in command:
        return False
    if flag in {"--camp_traffic_light_hybrid_postselection"}:
        value = _value_after(command, flag)
        return value is not None and value != "off"
    return True


def _decision(*, passed: bool, checks: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "preflight_enabled" in failed:
        failure_class = "explicit_shadow_selected_closed_loop_outcome_evaluation_preflight_authorization_missing"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith(("audit_", "status_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("source_" in name or "paired_" in name or "materialization_" in name for name in failed):
        failure_class = "source_artifact_contract_failure"
    elif any("generated_" in name for name in failed):
        failure_class = "shadow_selected_runbook_contract_failure"
    else:
        failure_class = "shadow_selected_closed_loop_outcome_evaluation_preflight_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
        "shadow_selected_closed_loop_outcome_evaluation_preflight_passed": bool(passed),
        "shadow_selected_closed_loop_outcome_evaluation_execution_authorized": bool(passed),
        "shadow_selected_closed_loop_outcome_evaluation_executed_by_this_gate": False,
        "planned_shadow_selected_run_count": inventory["generated_command_count"],
        "planned_shadow_selected_output_root_exists": inventory["generated_output_root_exists"],
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "safetycost_v1_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    runbook_path = output_dir / RUNBOOK_NAME
    report_for_json = dict(report)
    report_for_json["generated_runbook"] = RUNBOOK_NAME
    json_path.write_text(json.dumps(_stable(report_for_json), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    runbook_path.write_text(report["generated_runbook"] + "\n", encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path, runbook_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["runbook_plan"]
    inventory = plan["inventory"]
    lines = [
        "# v14 Shadow-Selected Closed-Loop Outcome Evaluation Preflight",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Planned Execution",
        "",
        f"- Command count: `{plan['command_count']}`",
        f"- Shadow-selected output root: `{plan['shadow_selected_output_root']}`",
        f"- Runbook: `{plan['runbook_name']}`",
        f"- Execute env guard: `{plan['execute_env_guard']}`",
        f"- Generated runbook SHA256: `{plan['generated_runbook_sha256']}`",
        "",
        "## Boundary Checks",
        "",
        f"- Generated default-off commands: `{inventory['generated_default_off_command_count']}`",
        f"- Generated forbidden flag count: `{inventory['generated_forbidden_flag_count']}`",
        f"- Generated formal seed count: `{inventory['generated_formal_seed_count']}`",
        f"- Generated Full36 path count: `{inventory['generated_full36_path_count']}`",
        f"- Generated static selector count: `{inventory['generated_static_selector_count']}`",
        f"- Generated Top-1 fallback count: `{inventory['generated_top1_fallback_count']}`",
        "",
        "## Boundary",
        "",
        "- This gate only materializes a future offline evaluation runbook.",
        "- It does not execute replay, train CAMP, modify DP, promote, deploy, activate an online selector, or make a claim.",
        "- Future execution must remain offline evidence acquisition and must later be paired against DP Top-1 run-level summaries.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any = None, expected: Any = True) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual if actual is not None else bool(passed),
        "expected": expected,
    }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(_read_text(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_key_values(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    value = None
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line.split("=", 1)[1].strip()
    return value


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _optional_sha256(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _value_after(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(command):
        return None
    return command[index + 1]


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
