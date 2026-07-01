#!/usr/bin/env python3
"""Static contract review for v13 fixed-DP candidate generation planning.

This read-only gate verifies the fixed-DP candidate generation plan before any
implementation planning. It does not run Diffusion Planner, generate
candidates, prepare data, replay, train CAMP, modify DP, promote, deploy, or
make safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_static_contract_review_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_static_contract_review_passed"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_static_contract_review_rejected"
PLAN_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_plan_v1"
PLAN_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_plan_ready"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_implementation_plan_only"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
REQUIRED_PLAN_TERMS = (
    "fixed Diffusion Planner candidate tensor only",
    "Diffusion-Planner at fixed commit",
    "target_min_candidate_members",
    "hundreds_to_thousands",
    "formal seeds 11/12/13",
    "Full36",
    "default_off_shadow_selector log with selected_index=0",
    "executed_index=0",
    "shadow_selected_index recorded without execution effect",
    SCORE_EXPRESSION,
)
FALSE_DECISION_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
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
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--plan_script_py", type=Path, required=True)
    parser.add_argument("--plan_test_py", type=Path, required=True)
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
        plan_json=args.plan_json,
        plan_artifact_dir=args.plan_artifact_dir,
        plan_script_py=args.plan_script_py,
        plan_test_py=args.plan_test_py,
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
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script_py: Path,
    plan_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_payload = _load_json_dict(plan_json)
    decision = _dict(plan_payload.get("final_decision"))
    plan = _dict(plan_payload.get("fixed_dp_candidate_generation_plan"))
    script_text = _read_text(plan_script_py)
    test_text = _read_text(plan_test_py)
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        plan_json=plan_json,
        plan_artifact_dir=plan_artifact_dir,
        plan_script_py=plan_script_py,
        plan_test_py=plan_test_py,
        v13_audit_md=v13_audit_md,
        plan_payload=plan_payload,
        decision=decision,
        plan=plan,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
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
            "static_contract_review_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_execution": False,
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
        "source_plan": {
            "path": str(plan_json.resolve()),
            "artifact_dir": str(plan_artifact_dir.resolve()),
            "json_sha256": _sha256(plan_json),
            "schema_version": plan_payload.get("schema_version"),
            "status": decision.get("status"),
            "target_min_candidate_members": plan.get("target_min_candidate_members"),
            "target_candidates_per_member": plan.get("target_candidates_per_member"),
            "zero_overlap_required_against_training_registries": plan.get("zero_overlap_required_against_training_registries"),
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _checks(
    *,
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script_py: Path,
    plan_test_py: Path,
    v13_audit_md: Path,
    plan_payload: dict[str, Any],
    decision: dict[str, Any],
    plan: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("plan_json_exists", plan_json.is_file(), str(plan_json), "file exists"),
        _check("plan_artifact_dir_exists", plan_artifact_dir.is_dir(), str(plan_artifact_dir), "directory exists"),
        _check("plan_script_exists", plan_script_py.is_file(), str(plan_script_py), "file exists"),
        _check("plan_test_exists", plan_test_py.is_file(), str(plan_test_py), "file exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("plan_schema", plan_payload.get("schema_version"), PLAN_SCHEMA_VERSION),
        _expect("plan_status", decision.get("status"), PLAN_STATUS),
        _expect("plan_passed", decision.get("passed"), True),
        _expect("plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("plan_authorized_next", decision.get("authorized_next_work"), authorized_current_work),
        _expect("plan_static_review_authorized", decision.get("fixed_dp_candidate_generation_static_contract_review_authorized_next"), True),
        _expect("plan_generation_execution_not_authorized", decision.get("fixed_dp_candidate_generation_execution_authorized_next"), False),
        _check("plan_target_members_at_least_1000", _as_int(plan.get("target_min_candidate_members")) is not None and _as_int(plan.get("target_min_candidate_members")) >= 1000, plan.get("target_min_candidate_members"), ">= 1000"),
        _expect("plan_candidates_per_member", plan.get("target_candidates_per_member"), 8),
        _expect("plan_required_dp_head", plan.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("plan_execution_not_authorized_by_gate", plan.get("execution_authorized_by_this_gate"), False),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_static_review_authorized", _latest_value(audit_text, "fixed_dp_candidate_generation_static_contract_review_authorized_next"), "True"),
    ]
    checks.extend(
        _expect(f"plan_forbids_{flag}", decision.get(flag), False)
        for flag in FALSE_DECISION_FLAGS
    )
    checks.extend(
        _expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False")
        for flag in AUDIT_FALSE_FLAGS
    )
    checks.extend(
        _check(f"script_contains_{_slug(term)}", term in script_text, term if term in script_text else "missing", term)
        for term in REQUIRED_PLAN_TERMS
    )
    checks.extend(
        _check(f"test_contains_{term}", term in test_text, term if term in test_text else "missing", term)
        for term in (
            "test_fixed_dp_candidate_generation_plan_authorizes_static_review_only",
            "test_fixed_dp_candidate_generation_plan_rejects_wrong_audit_target",
            "test_fixed_dp_candidate_generation_plan_rejects_small_target",
            "test_fixed_dp_candidate_generation_plan_rejects_camp_generation_auth",
        )
    )
    required_zero = set(plan.get("zero_overlap_required_against_training_registries") or [])
    checks.extend(
        _check(f"plan_requires_zero_overlap_{key}", key in required_zero, sorted(required_zero), key)
        for key in ZERO_OVERLAP_KEYS
    )
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
        "fixed_dp_candidate_generation_static_contract_review_passed": passed,
        "fixed_dp_candidate_generation_implementation_plan_authorized_next": passed,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_plan"]
    lines = [
        "# Fixed-DP Candidate Generation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Target minimum candidate members: `{source['target_min_candidate_members']}`",
        f"- Fixed-DP generation execution authorized next: `{decision['fixed_dp_candidate_generation_execution_authorized_next']}`",
        f"- CAMP candidate generation authorized: `{decision['candidate_generation_by_camp_authorized']}`",
        f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        "",
        "This review is static-only; it authorizes implementation planning, not candidate generation execution.",
        "",
    ]
    return "\n".join(lines)


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


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


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
    if isinstance(value, set):
        return sorted(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
