#!/usr/bin/env python3
"""Implementation-plan gate for v13 fresh evaluation split evaluation.

This gate consumes the completed evaluation plan artifact and defines the
future evaluator implementation contract. It does not implement or execute the
evaluator, run Diffusion Planner, generate candidates, replay, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_evaluation_plan_v1"
SOURCE_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_plan_ready"
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_implementation_static_"
    "contract_review_only"
)
FUTURE_EVALUATOR_SCRIPT = (
    "scripts/integrations/evaluate_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split.py"
)
FUTURE_EVALUATOR_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_evaluator.py"
)
SOURCE_FALSE_FLAGS = (
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "fresh_evaluation_split_evaluation_executed",
    "fixed_dp_candidate_generation_executed",
    "replay_executed",
    "training_executed",
    "dp_modification_executed",
)
AUDIT_FALSE_FLAGS = (
    "fresh_evaluation_split_evaluation_execution_authorized_next",
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
    parser = argparse.ArgumentParser(
        description="Plan-only implementation plan for v13 fresh split evaluation."
    )
    parser.add_argument("--evaluation_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evaluation_plan_artifact_dir=args.evaluation_plan_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evaluation_plan_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = evaluation_plan_artifact_dir.resolve()
    v13_audit_md = v13_audit_md.resolve()
    artifact_paths = _artifact_paths(artifact_dir)
    artifact_texts = {
        name: _read_text(path) for name, path in artifact_paths.items() if path.is_file()
    }
    source = _load_json_dict(artifact_paths["fresh_evaluation_split_evaluation_plan.json"])
    audit_text = _read_text(v13_audit_md)
    implementation_plan = _implementation_plan(source)
    checks = _checks(
        artifact_dir=artifact_dir,
        v13_audit_md=v13_audit_md,
        artifact_paths=artifact_paths,
        artifact_texts=artifact_texts,
        source=source,
        audit_text=audit_text,
        implementation_plan=implementation_plan,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "implementation_plan_only": True,
            "implementation_execution": False,
            "evaluation_execution": False,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
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
            "evaluation_plan_artifact_dir": str(artifact_dir),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "evaluation_plan_json_sha256": _sha256(
                artifact_paths["fresh_evaluation_split_evaluation_plan.json"]
            ),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": _source_summary(source, artifact_texts),
        "implementation_plan": implementation_plan,
        "static_contract_review_requirements": _static_contract_review_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "implementation_plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Evaluation Implementation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Implementation execution by this gate: `{plan['implementation_execution_by_this_gate']}`",
            f"- Evaluation execution by this gate: `{plan['evaluation_execution_by_this_gate']}`",
            f"- Future evaluator script: `{plan['future_evaluator']['script']}`",
            f"- Score expression: `{plan['math_boundary']['score_expression']}`",
            "",
            "This implementation-plan gate does not implement or execute the "
            "evaluator, generate candidates, replay, train CAMP, modify DP, "
            "promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _implementation_plan(source: dict[str, Any]) -> dict[str, Any]:
    source_plan = _dict(source.get("fresh_evaluation_split_evaluation_plan"))
    source_requirements = _dict(source_plan.get("source_requirements"))
    return {
        "objective": (
            "define a future read-only evaluator implementation that computes "
            "shadow CAMP selected indices over the fresh zero-overlap fixed-DP "
            "candidate tensors without changing executed DP Top-1 trajectories"
        ),
        "implementation_execution_by_this_gate": False,
        "evaluation_execution_by_this_gate": False,
        "future_evaluator": {
            "script": FUTURE_EVALUATOR_SCRIPT,
            "test": FUTURE_EVALUATOR_TEST,
            "input_contract": {
                "fresh_evaluation_split_member_source_manifest": True,
                "fresh_evaluation_split_nonoverlap_report": True,
                "fixed_dp_candidate_tensor_references": True,
                "approved_atom_feature_schema": True,
                "default_off_shadow_selector_runtime_manifest": True,
            },
            "output_contract": {
                "report_json": "fresh_evaluation_split_evaluation_report.json",
                "report_md": "fresh_evaluation_split_evaluation_report.md",
                "sha256sums": "SHA256SUMS.artifact",
                "shadow_selected_index_only": True,
                "executed_trajectory_change": False,
            },
        },
        "source_invariants": {
            "selected_member_count": source_requirements.get("selected_member_count"),
            "all_required_intersections_zero": source_requirements.get(
                "all_required_intersections_zero"
            ),
            "rejected_overlap_artifact_must_not_be_holdout": source_requirements.get(
                "rejected_overlap_artifact_must_not_be_holdout"
            ),
            "split_root_zero_alone_is_insufficient": source_requirements.get(
                "split_root_zero_alone_is_insufficient"
            ),
        },
        "future_fail_closed_checks": [
            "DP HEAD must equal the fixed TiERIV Diffusion Planner commit",
            "all four zero-overlap intersections must remain zero",
            "candidate tensors must already exist as fixed DP outputs",
            "formal seeds 11/12/13 and Full36 must be absent",
            "CAMP must only score fixed candidate rows with affine atom scores",
            "online selector and executed trajectory must remain unchanged",
            "evaluation output must not become training input in this gate",
        ],
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_only": True,
            "nonnegative_simplex_weights_only": True,
            "simplex_cvar_l2_master_remains_convex": True,
        },
    }


def _static_contract_review_requirements() -> dict[str, Any]:
    return {
        "must_review_future_evaluator_before_implementation": True,
        "must_pin_read_only_inputs": True,
        "must_pin_zero_overlap_revalidation": True,
        "must_pin_default_off_shadow_index_only_behavior": True,
        "must_pin_no_training_no_replay_no_candidate_generation": True,
        "must_pin_affine_score_and_nonnegative_simplex_contract": True,
    }


def _forbidden_paths() -> dict[str, bool]:
    return {
        "implement_evaluator_in_this_gate": True,
        "execute_evaluation_in_this_gate": True,
        "run_diffusion_planner": True,
        "generate_fixed_dp_candidates": True,
        "generate_candidates_by_camp": True,
        "generate_or_modify_trajectories_by_camp": True,
        "reference_blend": True,
        "guidance": True,
        "postprocess_or_postselection": True,
        "use_closed_loop_outcomes": True,
        "train_camp": True,
        "modify_dp": True,
        "change_online_selector": True,
        "promote_or_deploy": True,
        "claim_safety_or_camp_over_dp_top1": True,
    }


def _checks(
    *,
    artifact_dir: Path,
    v13_audit_md: Path,
    artifact_paths: dict[str, Path],
    artifact_texts: dict[str, str],
    source: dict[str, Any],
    audit_text: str,
    implementation_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    heads = _key_values(artifact_texts.get("HEADS", ""))
    decision = _dict(source.get("final_decision"))
    source_plan = _dict(source.get("fresh_evaluation_split_evaluation_plan"))
    source_requirements = _dict(source_plan.get("source_requirements"))
    math_boundary = _dict(source_plan.get("math_boundary"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("evaluation_plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
    ]
    for name, path in artifact_paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    checks.extend(
        [
            _expect("artifact_run_exit_zero", artifact_texts.get("run.exit", "").strip(), "0"),
            _expect("artifact_sha256_check_exit_zero", artifact_texts.get("SHA256SUMS_artifact.check.exit", "").strip(), "0"),
            _expect("artifact_dp_head_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
            _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
            _expect("source_status", decision.get("status"), SOURCE_STATUS),
            _expect("source_passed", decision.get("passed"), True),
            _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
            _expect("source_authorizes_current_gate", decision.get("authorized_next_work"), authorized_current_work),
            _expect(
                "source_implementation_plan_authorized",
                decision.get("fresh_evaluation_split_evaluation_implementation_plan_authorized_next"),
                True,
            ),
            _expect("source_selected_member_count", source_requirements.get("selected_member_count"), 32),
            _expect("source_all_intersections_zero", source_requirements.get("all_required_intersections_zero"), True),
            _expect("source_rejected_overlap_not_holdout", source_requirements.get("rejected_overlap_artifact_must_not_be_holdout"), True),
            _expect("source_split_root_zero_insufficient", source_requirements.get("split_root_zero_alone_is_insufficient"), True),
            _expect("source_candidate_operation", math_boundary.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("source_score_affine", math_boundary.get("score_expression"), SCORE_EXPRESSION),
            _expect("implementation_plan_no_implementation", implementation_plan.get("implementation_execution_by_this_gate"), False),
            _expect("implementation_plan_no_evaluation", implementation_plan.get("evaluation_execution_by_this_gate"), False),
            _expect("implementation_plan_shadow_index_only", implementation_plan["future_evaluator"]["output_contract"].get("shadow_selected_index_only"), True),
            _expect("implementation_plan_no_executed_change", implementation_plan["future_evaluator"]["output_contract"].get("executed_trajectory_change"), False),
            _expect("implementation_plan_score_affine", implementation_plan["math_boundary"].get("score_expression"), SCORE_EXPRESSION),
        ]
    )
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_implementation_plan",
            _latest_value(text, "fresh_evaluation_split_evaluation_implementation_plan_authorized_next"),
            "True",
        ),
        _expect(
            "audit_keeps_evaluation_execution_blocked",
            _latest_value(text, "fresh_evaluation_split_evaluation_execution_authorized_next"),
            "False",
        ),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(text, flag), "False"))
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
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "fresh_evaluation_split_evaluation_implementation_plan_ready": passed,
        "fresh_evaluation_split_evaluation_implementation_static_contract_review_authorized_next": passed,
        "fresh_evaluation_split_evaluation_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fresh_evaluation_split_evaluation_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "HEADS": root / "HEADS",
        "COMMAND": root / "COMMAND",
        "run.exit": root / "run.exit",
        "stdout.txt": root / "stdout.txt",
        "stderr.txt": root / "stderr.txt",
        "fresh_evaluation_split_evaluation_plan.json": root / "fresh_evaluation_split_evaluation_plan.json",
        "fresh_evaluation_split_evaluation_plan.md": root / "fresh_evaluation_split_evaluation_plan.md",
        "SHA256SUMS.artifact": root / "SHA256SUMS.artifact",
        "SHA256SUMS_artifact.check.exit": root / "SHA256SUMS_artifact.check.exit",
        "SHA256SUMS_artifact.check.stdout": root / "SHA256SUMS_artifact.check.stdout",
        "SHA256SUMS_artifact.check.stderr": root / "SHA256SUMS_artifact.check.stderr",
    }


def _source_summary(source: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    heads = _key_values(texts.get("HEADS", ""))
    decision = _dict(source.get("final_decision"))
    source_plan = _dict(source.get("fresh_evaluation_split_evaluation_plan"))
    requirements = _dict(source_plan.get("source_requirements"))
    return {
        "camp_head": heads.get("camp_head"),
        "camp_origin_main": heads.get("camp_origin_main"),
        "dp_head": heads.get("dp_head"),
        "exit": texts.get("run.exit", "").strip(),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_member_count": requirements.get("selected_member_count"),
        "all_required_intersections_zero": requirements.get("all_required_intersections_zero"),
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _key_values(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", maxsplit=1)
            values[key.strip()] = value.strip()
    return values


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
