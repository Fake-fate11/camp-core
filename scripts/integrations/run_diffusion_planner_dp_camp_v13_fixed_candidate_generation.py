#!/usr/bin/env python3
"""CAMP-owned guarded runner for fixed-DP candidate generation.

This runner is the CAMP-side replacement for the missing DP-repo
``tools/camp_fixed_candidate_generation.py`` entrypoint. It builds and, only
under an explicit future execution gate, can launch a fixed Diffusion Planner
candidate-generation command. The implementation gate that introduces this
file does not run Diffusion Planner, generate candidates, train CAMP, modify
DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_static_contract_review_v1"
)
SOURCE_PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_implementation_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_implementation_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_implementation_rejected"
)
DISABLED_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "runner_execution_disabled"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_implementation_static_"
    "contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_post_implementation_static_contract_review_only"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
FORBIDDEN_COMMAND_SNIPPETS = (
    "reference_blend",
    "guidance",
    "postprocess",
    "postselection",
    "splice",
    "repair",
    "rewrite",
    "closed_loop",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_preflight_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "data_preparation_authorized_next",
    "replay_execution_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, default=Path("/root/autodl-tmp/Diffusion-Planner"))
    parser.add_argument("--camp_repo", type=Path, default=Path("/root/autodl-tmp/camp_core"))
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--dp_command", nargs="+", required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        implementation_static_contract_review_json=args.implementation_static_contract_review_json,
        v13_audit_md=args.v13_audit_md,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        output_dir=args.output_dir,
        dp_command=args.dp_command,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        execute=args.execute,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if report["final_decision"]["passed"] and args.execute:
        result = execute_fixed_dp_command(report["runner_contract"]["planned_command"], args.dp_repo)
        report["runner_execution"] = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
        return result.returncode
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    implementation_static_contract_review_json: Path,
    v13_audit_md: Path,
    dp_repo: Path,
    camp_repo: Path,
    output_dir: Path,
    dp_command: Sequence[str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    execute: bool = False,
) -> dict[str, Any]:
    source_payload = _load_json_dict(implementation_static_contract_review_json)
    source_decision = _dict(source_payload.get("final_decision"))
    audit_text = _read_text(v13_audit_md)
    planned_command = _planned_command(
        dp_command=list(dp_command),
        output_dir=output_dir,
        required_dp_head=required_dp_head,
    )
    checks = _checks(
        implementation_static_contract_review_json=implementation_static_contract_review_json,
        v13_audit_md=v13_audit_md,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        output_dir=output_dir,
        source_payload=source_payload,
        source_decision=source_decision,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        planned_command=planned_command,
        execute=execute,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "implementation_only": True,
            "runner_default_off": True,
            "execute_requested": execute,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
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
        "source_static_review": {
            "path": str(implementation_static_contract_review_json.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "json_sha256": _sha256(implementation_static_contract_review_json),
        },
        "runner_contract": {
            "runner_script": RUNNER_SCRIPT,
            "guard_env_var": GUARD_ENV_VAR,
            "dp_repo": str(dp_repo),
            "camp_repo": str(camp_repo),
            "output_dir": str(output_dir),
            "planned_command": planned_command,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "dp_modification": False,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            execute=execute,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def execute_fixed_dp_command(command: Sequence[str], dp_repo: Path) -> subprocess.CompletedProcess[str]:
    if os.environ.get(GUARD_ENV_VAR) != "1":
        raise RuntimeError(f"set {GUARD_ENV_VAR}=1 only in an authorized execution gate")
    return subprocess.run(
        list(command),
        cwd=str(dp_repo),
        check=False,
        text=True,
        capture_output=True,
    )


def _planned_command(
    *,
    dp_command: list[str],
    output_dir: Path,
    required_dp_head: str,
) -> list[str]:
    return list(dp_command) + [
        "--output_dir",
        str(output_dir),
        "--fixed_dp_head",
        required_dp_head,
        "--candidate_operation",
        "fixed DP candidate reranking only",
        "--score_expression",
        SCORE_EXPRESSION,
        "--forbid_full36",
        "--forbid_formal_seeds",
        "11",
        "12",
        "13",
        "--write_zero_overlap_registries",
    ]


def _checks(
    *,
    implementation_static_contract_review_json: Path,
    v13_audit_md: Path,
    dp_repo: Path,
    camp_repo: Path,
    output_dir: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    planned_command: list[str],
    execute: bool,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    command_text = " ".join(planned_command).lower()
    checks: list[dict[str, Any]] = [
        _expect("implementation_static_contract_review_json_exists", implementation_static_contract_review_json.exists(), True),
        _expect("v13_audit_exists", v13_audit_md.exists(), True),
        _expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_decision.get("status"), SOURCE_PASS_STATUS),
        _expect("source_passed", source_decision.get("passed"), True),
        _expect("source_failed_checks_empty", source_decision.get("failed_checks"), []),
        _expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_authorizes_implementation", source_decision.get("entrypoint_contract_remediation_implementation_authorized_next"), True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("dp_repo_exists", dp_repo.is_dir(), True),
        _expect("camp_repo_exists", camp_repo.is_dir(), True),
        _expect("output_dir_not_written_by_implementation_gate", output_dir.exists(), False),
        _expect("runner_is_default_off_for_this_gate", execute, False),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_implementation", _latest_value(audit_text, "entrypoint_contract_remediation_implementation_authorized_next"), "True"),
        _expect("planned_command_has_output_dir", "--output_dir" in planned_command, True),
        _expect("planned_command_has_fixed_dp_head", FIXED_DP_HEAD in planned_command, True),
        _expect("planned_command_forbids_full36", "--forbid_full36" in planned_command, True),
        _expect("planned_command_forbids_formal_seeds", all(seed in planned_command for seed in ("11", "12", "13")), True),
        _expect("planned_command_writes_zero_overlap_registries", "--write_zero_overlap_registries" in planned_command, True),
        _expect("planned_command_candidate_operation_fixed", "fixed DP candidate reranking only" in planned_command, True),
        _expect("planned_command_score_affine", SCORE_EXPRESSION in planned_command, True),
    ]
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    for snippet in FORBIDDEN_COMMAND_SNIPPETS:
        checks.append(_expect(f"planned_command_forbids_{_slug(snippet)}", snippet in command_text, False))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    execute: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    status = READY_STATUS if passed else REJECT_STATUS
    return {
        "status": status,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "entrypoint_contract_remediation_implementation_complete": passed,
        "entrypoint_contract_remediation_post_implementation_static_contract_review_authorized_next": passed,
        "fixed_dp_candidate_generation_preflight_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
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
    decision = _dict(report["final_decision"])
    runner = _dict(report["runner_contract"])
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation CAMP Runner Implementation",
            "",
            f"- status: `{decision['status']}`",
            f"- passed: `{decision['passed']}`",
            f"- failed_checks: `{decision['failed_checks']}`",
            f"- authorized_next_work: `{decision['authorized_next_work']}`",
            f"- runner_script: `{runner['runner_script']}`",
            f"- guard_env_var: `{runner['guard_env_var']}`",
            f"- fixed_dp_generation_executed: `{decision['fixed_dp_candidate_generation_executed']}`",
            f"- candidate_generation_by_camp_authorized: `{decision['candidate_generation_by_camp_authorized']}`",
            f"- dp_modification_authorized: `{decision['dp_modification_authorized']}`",
            f"- training_preflight_authorized: `{decision['training_preflight_authorized_next']}`",
            "",
        ]
    )


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
