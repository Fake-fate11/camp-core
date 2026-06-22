#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_result import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as RESULT_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as RESULT_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_authorization_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_RESULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_result_review_0a87b7b"
)
DEFAULT_RESULT_REVIEW_JSON = (
    f"{DEFAULT_RESULT_REVIEW_ROOT}/"
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_result_review.json"
)
DEFAULT_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_retry_execution_a28d089"
)

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for mixed-result non-promotion diagnosis after the "
            "candidate-set consensus safety-score result review. It does not "
            "execute diagnosis, run replay, train CAMP, promote atoms, change "
            "online selection, use formal seeds, or modify DP."
        )
    )
    parser.add_argument(
        "--result_review_json",
        type=Path,
        default=Path(DEFAULT_RESULT_REVIEW_JSON),
    )
    parser.add_argument("--execution_root", default=DEFAULT_EXECUTION_ROOT)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        result_review=_load_json(args.result_review_json),
        result_review_json=str(args.result_review_json),
        execution_root=args.execution_root,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    result_review: dict[str, Any],
    result_review_json: str = DEFAULT_RESULT_REVIEW_JSON,
    execution_root: str = DEFAULT_EXECUTION_ROOT,
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_summary(result_review)
    plan = _diagnosis_plan(
        source=source,
        result_review_json=result_review_json,
        execution_root=execution_root,
    )
    checks = [
        *_source_checks(source),
        *_plan_scope_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only follow-up for mixed SafetyCost v1 diagnostics and "
                "sample-size limits"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "The planned diagnosis may read only existing offline result "
                "review and evaluation artifacts. It must not recompute "
                "outcomes, define atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, run replay, run DP, "
                "modify DP, or claim a DP-side classical Benders decomposition."
            ),
        },
        "source_summary": source,
        "diagnosis_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["diagnosis_plan"]
    lines = [
        "# Candidate-Set Consensus Mixed Result Non-Promotion Diagnosis Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Diagnosis execution authorized: `{decision['mixed_result_nonpromotion_diagnosis_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Review",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source classification: `{source['result_classification']}`",
        f"- Positive changed lambdas: `{source['positive_changed_lambda_count']}`",
        f"- Worse lambdas: `{source['worse_lambda_count']}`",
        f"- Sample too small for promotion: `{source['sample_too_small_for_promotion']}`",
        "",
        "## Planned Scope",
        "",
        f"- Result review JSON: `{plan['result_review_json']}`",
        f"- Execution root: `{plan['execution_root']}`",
        f"- Read-only artifact inputs: `{plan['read_only_artifact_inputs']}`",
        f"- Executes diagnosis now: `{plan['executes_diagnosis_now']}`",
        "",
        "## Planned Diagnostics",
        "",
    ]
    for item in plan["diagnostic_questions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Accept Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Reject Criteria", ""])
    for item in plan["reject_criteria"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize safety benefit claims, atom "
            "promotion, CAMP retraining, online selector changes, formal "
            "seeds, Full36, replay, label attachment, or DP modification.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    classification = _dict(report.get("result_classification"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "result_review_ready": bool(
            decision.get("safety_score_evaluation_result_review_ready")
        ),
        "diagnosis_plan_authorized": bool(
            decision.get("mixed_result_nonpromotion_diagnosis_plan_authorized")
        ),
        "result_classification": decision.get("result_classification"),
        "sample_too_small_for_promotion": bool(
            decision.get("sample_too_small_for_promotion")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "positive_changed_lambda_count": _int(
            classification.get("positive_changed_lambda_count")
        ),
        "better_only_lambda_count": _int(classification.get("better_only_lambda_count")),
        "worse_lambda_count": _int(classification.get("worse_lambda_count")),
        "positive_mean_worse_lambda_count": _int(
            classification.get("positive_mean_worse_lambda_count")
        ),
        "zero_lambda_changed_records": _int(
            classification.get("zero_lambda_changed_records")
        ),
        "max_changed_records": _int(classification.get("max_changed_records")),
    }


def _diagnosis_plan(
    *,
    source: dict[str, Any],
    result_review_json: str,
    execution_root: str,
) -> dict[str, Any]:
    return {
        "result_review_json": result_review_json,
        "execution_root": execution_root,
        "read_only_artifact_inputs": [
            result_review_json,
            f"{execution_root}/candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.json",
            f"{execution_root}/SHA256SUMS",
            f"{execution_root}/HEADS.txt",
        ],
        "executes_diagnosis_now": False,
        "requires_new_replay": False,
        "requires_label_attachment": False,
        "requires_camp_training": False,
        "requires_atom_promotion": False,
        "requires_online_selector_change": False,
        "requires_dp_modification": False,
        "diagnostic_questions": [
            "Separate better-only small-lambda rows from worse large-lambda rows.",
            "Summarize changed records by run, route bucket, fallback-retained status, and lambda.",
            "Report SafetyCost v1 component deltas for changed rows without redefining the atom.",
            "Identify whether worse rows are concentrated in nishishinjuku, traffic-light, turn, or normal buckets.",
            "Record sample-size and nonformal-only limits as promotion blockers.",
        ],
        "accept_criteria": [
            "source result review is mixed_nonpromotion and passed",
            "zero lambda preserves logged selection",
            "positive lambdas include both better-only and worse rows",
            "diagnosis remains read-only over existing artifacts",
            "output explicitly keeps safety_benefit_evidence and atom_promotion_authorized false",
        ],
        "reject_criteria": [
            "source result review is not ready or not mixed_nonpromotion",
            "any formal seed, new replay, label attachment, CAMP training, online selector change, atom promotion, or DP modification is required",
            "diagnosis would use posterior labels to define atoms, choose lambda online, or alter scoring",
        ],
        "expected_source": {
            "classification": source["result_classification"],
            "positive_changed_lambda_count": source["positive_changed_lambda_count"],
            "better_only_lambda_count": source["better_only_lambda_count"],
            "worse_lambda_count": source["worse_lambda_count"],
            "max_changed_records": source["max_changed_records"],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], RESULT_REVIEW_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_diagnosis_plan",
            source["authorized_next_work"],
            RESULT_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_result_review_ready", source["result_review_ready"], True),
        _check_equal(
            "source_diagnosis_plan_authorized",
            source["diagnosis_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_classification_mixed_nonpromotion",
            source["result_classification"],
            "mixed_nonpromotion",
        ),
        _check_equal(
            "source_sample_too_small_for_promotion",
            source["sample_too_small_for_promotion"],
            True,
        ),
        _check_equal("source_no_safety_benefit", source["safety_benefit_evidence"], False),
        _check_equal(
            "source_no_atom_promotion",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal(
            "source_positive_changed_lambdas_present",
            source["positive_changed_lambda_count"] > 0,
            True,
        ),
        _check_equal(
            "source_better_only_lambdas_present",
            source["better_only_lambda_count"] > 0,
            True,
        ),
        _check_equal("source_worse_lambdas_present", source["worse_lambda_count"] > 0, True),
        _check_equal("source_zero_lambda_no_change", source["zero_lambda_changed_records"], 0),
        _check_equal("source_max_changed_positive", source["max_changed_records"] > 0, True),
    ]


def _plan_scope_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_executes_nothing_now", plan["executes_diagnosis_now"], False),
        _check_equal("plan_no_new_replay", plan["requires_new_replay"], False),
        _check_equal("plan_no_label_attachment", plan["requires_label_attachment"], False),
        _check_equal("plan_no_camp_training", plan["requires_camp_training"], False),
        _check_equal("plan_no_atom_promotion", plan["requires_atom_promotion"], False),
        _check_equal(
            "plan_no_online_selector_change",
            plan["requires_online_selector_change"],
            False,
        ),
        _check_equal("plan_no_dp_modification", plan["requires_dp_modification"], False),
        _check_equal("plan_has_diagnostic_questions", bool(plan["diagnostic_questions"]), True),
        _check_equal("plan_has_accept_criteria", bool(plan["accept_criteria"]), True),
        _check_equal("plan_has_reject_criteria", bool(plan["reject_criteria"]), True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["accept_criteria"] + plan["reject_criteria"]).lower()
    return [
        _check_equal("criteria_blocks_formal_seed", "formal seed" in text, True),
        _check_equal("criteria_blocks_training", "training" in text, True),
        _check_equal("criteria_blocks_online", "online" in text, True),
        _check_equal("criteria_blocks_dp_modification", "dp modification" in text, True),
        _check_equal("criteria_blocks_promotion", "promotion" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "mixed_result_nonpromotion_diagnosis_plan_ready": passed,
        "mixed_result_nonpromotion_diagnosis_authorization_gate_authorized": passed,
        "mixed_result_nonpromotion_diagnosis_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
