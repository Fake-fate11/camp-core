#!/usr/bin/env python3
"""Plan implementation for v13 non-overlap data remediation.

This is a plan-only gate. It consumes the completed non-overlap remediation
static contract review and defines a future implementation plan for enforcing
independent holdout data in static DP-reward result-readiness. It does not
edit implementation code, run replay, generate candidates, train CAMP, modify
Diffusion Planner, promote artifacts, deploy, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_rejected"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
MINIMUM_HOLDOUT_RECORDS = 3200
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
FUTURE_RESULT_READINESS_SCRIPT = (
    "scripts/integrations/"
    "review_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_result_readiness.py"
)
FUTURE_RESULT_READINESS_TEST = (
    "camp_core/tests/"
    "test_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_result_readiness.py"
)
FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST = (
    "camp_core/tests/"
    "test_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_nonoverlap_data_remediation_"
    "implementation_static_contract.py"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan for v13 static DP-reward "
            "non-overlap data remediation."
        )
    )
    parser.add_argument("--static_contract_review_json", type=Path, required=True)
    parser.add_argument("--result_readiness_py", type=Path, required=True)
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
        static_contract_review_json=args.static_contract_review_json,
        result_readiness_py=args.result_readiness_py,
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
    static_contract_review_json: Path,
    result_readiness_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    static_contract_review_json = static_contract_review_json.resolve()
    result_readiness_py = result_readiness_py.resolve()
    v13_audit_md = v13_audit_md.resolve()
    source_review = _load_json_dict(static_contract_review_json)
    result_readiness_text = _read_text(result_readiness_py)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_review)
    checks = _checks(
        static_contract_review_json=static_contract_review_json,
        result_readiness_py=result_readiness_py,
        v13_audit_md=v13_audit_md,
        result_readiness_text=result_readiness_text,
        audit_text=audit_text,
        source_review=source_review,
        source_summary=source_summary,
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
            "plan_only": True,
            "implementation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
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
            "static_contract_review_json": str(static_contract_review_json),
            "result_readiness_py": str(result_readiness_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "static_contract_review_json_sha256": _sha256(static_contract_review_json),
            "result_readiness_py_sha256": _sha256(result_readiness_py),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "implementation_plan": _implementation_plan(),
        "future_static_contract_review_requirements": _future_static_review_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_plan_ready": passed,
            "implementation_static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# V13 Static DP-Reward Non-Overlap Data Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized: `{decision['implementation_authorized_next']}`",
        f"- Training preflight authorized: `{decision['training_preflight_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        "",
        "## Future Implementation Scope",
        "",
        f"- Target script: `{plan['future_result_readiness_script']}`",
        f"- Target test: `{plan['future_result_readiness_test']}`",
        f"- Implementation performed by this gate: `{plan['implementation_performed_by_this_gate']}`",
        "",
        "## Required Future Changes",
        "",
    ]
    for item in plan["required_future_changes"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report["future_static_contract_review_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report["forbidden_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not edit result-readiness, build a split manifest, run replay, generate candidates, train CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    contract = _dict(source_review.get("contract_summary"))
    analysis = _dict(source_review.get("analysis"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized_next": decision.get(
            "implementation_plan_authorized_next"
        ),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        "training_preflight_authorized_next": decision.get("training_preflight_authorized_next"),
        "training_execution_authorized_next": decision.get("training_execution_authorized_next"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get(
            "fixed_dp_candidate_generation_authorized_next"
        ),
        "candidate_generation_by_camp_authorized": decision.get(
            "candidate_generation_by_camp_authorized"
        ),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get(
            "camp_over_dp_top1_claim_authorized"
        ),
        "split_manifest_required": contract.get("split_manifest_required"),
        "candidate_tensor_hash_registry_required": contract.get(
            "candidate_tensor_hash_registry_required"
        ),
        "path_signature_registry_required": contract.get("path_signature_registry_required"),
        "record_identity_hash_registry_required": contract.get(
            "record_identity_hash_registry_required"
        ),
        "train_eval_candidate_tensor_intersection_must_be_zero": contract.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "train_eval_path_signature_intersection_must_be_zero": contract.get(
            "train_eval_path_signature_intersection_must_be_zero"
        ),
        "result_readiness_must_compare_against_all_training_summary_selection_logs": contract.get(
            "result_readiness_must_compare_against_all_training_summary_selection_logs"
        ),
        "formal_seeds_11_12_13_excluded": contract.get("formal_seeds_11_12_13_excluded"),
        "new_nonoverlap_source_root_required": contract.get("new_nonoverlap_source_root_required"),
        "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden": contract.get(
            "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden"
        ),
        "reuse_of_training_summary_selection_logs_for_holdout_forbidden": contract.get(
            "reuse_of_training_summary_selection_logs_for_holdout_forbidden"
        ),
        "minimum_holdout_records": contract.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": contract.get("minimum_holdout_selection_logs"),
        "expected_candidate_count": contract.get("expected_candidate_count"),
        "expected_atom_count": contract.get("expected_atom_count"),
        "fixed_dp_candidate_generation_requires_later_explicit_preflight": contract.get(
            "fixed_dp_candidate_generation_requires_later_explicit_preflight"
        ),
        "candidate_operation": analysis.get("candidate_operation"),
        "score_expression": analysis.get("score_expression"),
    }


def _implementation_plan() -> dict[str, Any]:
    return {
        "status": "plan_ready_no_implementation",
        "implementation_performed_by_this_gate": False,
        "future_result_readiness_script": FUTURE_RESULT_READINESS_SCRIPT,
        "future_result_readiness_test": FUTURE_RESULT_READINESS_TEST,
        "future_implementation_static_contract_test": FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST,
        "future_cli_extensions": [
            "--split_manifest_json for explicit train/holdout split evidence",
            "--candidate_tensor_hash_registry_json for train/eval candidate tensor hashes",
            "--path_signature_registry_json for train/eval route/seed/npc/spawn/tl/static_shadow signatures",
            "--record_identity_hash_registry_json for same-signature step identity checks",
        ],
        "required_future_changes": [
            "load split_manifest_json as a structured JSON object",
            "require train and holdout selection-log roots to be disjoint",
            "require candidate_tensor_hash train/eval intersection count to be zero",
            "require path_signature train/eval intersection count to be zero",
            "require record_identity_hash train/eval intersection count to be zero",
            "compare evaluation hashes against every training_summary.selection_logs entry",
            "reject formal seeds 11/12/13 in both train and holdout manifests",
            "reject reuse of the diagnosed prior evaluation root for holdout",
            "reject reuse of training-summary selection logs for holdout",
            "preserve default-off shadow selector validation and fixed DP Top-1 execution",
            "preserve affine score contract score_k(w)=a_k^T w",
        ],
        "future_result_readiness_acceptance": {
            "minimum_holdout_records": MINIMUM_HOLDOUT_RECORDS,
            "minimum_holdout_selection_logs": MINIMUM_HOLDOUT_SELECTION_LOGS,
            "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
            "expected_atom_count": EXPECTED_ATOM_COUNT,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "not_authorized_by_this_plan": {
            "implementation": True,
            "training_preflight": True,
            "training_execution": True,
            "replay_execution": True,
            "fixed_dp_candidate_generation": True,
            "candidate_generation_by_camp": True,
            "dp_modification": True,
            "promotion": True,
            "deployment": True,
            "safety_claim": True,
            "camp_over_dp_top1_claim": True,
        },
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "confirm result-readiness CLI exposes split and registry inputs",
        "confirm split manifest parsing is structured JSON, not string parsing",
        "confirm train/eval candidate tensor hash intersection must be zero",
        "confirm train/eval path signature intersection must be zero",
        "confirm train/eval record identity hash intersection must be zero",
        "confirm all training_summary.selection_logs are compared",
        "confirm formal seeds 11/12/13 are rejected",
        "confirm default-off fixed-DP reranking boundary remains unchanged",
        "confirm no implementation, replay, candidate generation, training, DP modification, promotion, deployment, or safety claim is authorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "CAMP trajectory generation or mutation",
        "Diffusion Planner code/config/weight modification",
        "reference_blend, guidance, postprocess/postselection, or closed-loop online input",
        "formal seeds 11/12/13",
        "selector or atom promotion",
        "deployment or deployable checkpoint claim",
        "safety benefit or CAMP-over-DP-Top-1 claim",
    ]


def _checks(
    *,
    static_contract_review_json: Path,
    result_readiness_py: Path,
    v13_audit_md: Path,
    result_readiness_text: str,
    audit_text: str,
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check(
            "static_contract_review_json_exists",
            static_contract_review_json.is_file(),
            str(static_contract_review_json),
            "file exists",
        ),
        _check(
            "result_readiness_py_exists",
            result_readiness_py.is_file(),
            str(result_readiness_py),
            "file exists",
        ),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check(
            "current_gate_authorized_in_audit",
            f"next_work_target={authorized_current_work}" in audit_text,
            authorized_current_work,
            "present as next_work_target",
        ),
        _check(
            "current_status_static_review_complete",
            (
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_"
                "shadow_replay_evaluation_nonoverlap_data_remediation_static_contract_"
                "review_complete"
            )
            in audit_text,
            "static_contract_review_complete",
            "present in audit",
        ),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _expect_value(source_review, "schema_version", (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_static_contract_review_v1"
        )),
        _expect_summary(source_summary, "status", SOURCE_REVIEW_STATUS),
        _expect_summary(source_summary, "passed", True),
        _expect_summary(source_summary, "failed_checks", []),
        _expect_summary(source_summary, "authorized_next_work", authorized_current_work),
        _expect_summary(source_summary, "implementation_plan_authorized_next", True),
        _expect_summary(source_summary, "implementation_authorized_next", False),
        _expect_summary(source_summary, "training_preflight_authorized_next", False),
        _expect_summary(source_summary, "training_execution_authorized_next", False),
        _expect_summary(source_summary, "replay_execution_authorized_next", False),
        _expect_summary(source_summary, "fixed_dp_candidate_generation_authorized_next", False),
        _expect_summary(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "dp_modification_authorized", False),
        _expect_summary(source_summary, "selector_promotion_authorized", False),
        _expect_summary(source_summary, "atom_promotion_authorized", False),
        _expect_summary(source_summary, "deployment_authorized", False),
        _expect_summary(source_summary, "safety_benefit_claim_authorized", False),
        _expect_summary(source_summary, "camp_over_dp_top1_claim_authorized", False),
        _expect_summary(source_summary, "split_manifest_required", True),
        _expect_summary(source_summary, "candidate_tensor_hash_registry_required", True),
        _expect_summary(source_summary, "path_signature_registry_required", True),
        _expect_summary(source_summary, "record_identity_hash_registry_required", True),
        _expect_summary(source_summary, "train_eval_candidate_tensor_intersection_must_be_zero", True),
        _expect_summary(source_summary, "train_eval_path_signature_intersection_must_be_zero", True),
        _expect_summary(
            source_summary,
            "result_readiness_must_compare_against_all_training_summary_selection_logs",
            True,
        ),
        _expect_summary(source_summary, "formal_seeds_11_12_13_excluded", True),
        _expect_summary(source_summary, "new_nonoverlap_source_root_required", True),
        _expect_summary(source_summary, "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden", True),
        _expect_summary(source_summary, "reuse_of_training_summary_selection_logs_for_holdout_forbidden", True),
        _expect_summary(source_summary, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_summary(source_summary, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_summary(source_summary, "expected_candidate_count", EXPECTED_CANDIDATE_COUNT),
        _expect_summary(source_summary, "expected_atom_count", EXPECTED_ATOM_COUNT),
        _expect_summary(
            source_summary,
            "fixed_dp_candidate_generation_requires_later_explicit_preflight",
            True,
        ),
        _expect_summary(source_summary, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_summary(source_summary, "score_expression", SCORE_EXPRESSION),
        _contains("result_readiness_has_previous_training_summary_input", result_readiness_text, "previous_training_summary_json"),
        _contains("result_readiness_compares_candidate_tensor_hashes", result_readiness_text, "_compare_candidate_tensor_hashes"),
        _contains("result_readiness_has_max_overlap_rate", result_readiness_text, "max_previous_overlap_rate"),
        _contains("audit_keeps_implementation_disabled", audit_text, "implementation_authorized_by_current_boundary=False"),
        _contains("audit_keeps_training_preflight_disabled", audit_text, "static_dp_reward_training_preflight_authorized_by_current_boundary=False"),
        _contains("audit_keeps_replay_disabled", audit_text, "replay_execution_authorized_by_current_boundary=False"),
        _contains("audit_keeps_candidate_generation_disabled", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=False"),
        _contains("audit_keeps_dp_modification_disabled", audit_text, "dp_modification_authorized_by_current_boundary=False"),
    ]
    return checks


def _expect_summary(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, summary.get(key) == expected, summary.get(key), expected)


def _expect_value(payload: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, payload.get(key) == expected, payload.get(key), expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
