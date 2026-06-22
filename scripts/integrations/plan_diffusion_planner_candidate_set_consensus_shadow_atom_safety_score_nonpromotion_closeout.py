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

from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_mixed_result_nonpromotion_diagnosis_result_review_8b3f146"
)
DEFAULT_REVIEW_JSON = (
    f"{DEFAULT_REVIEW_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_mixed_result_nonpromotion_diagnosis_result_review.json"
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
            "Plan-only closeout for the candidate-set consensus safety-score "
            "shadow atom evidence chain. It records non-promotion blockers and "
            "keeps the feature default-off."
        )
    )
    parser.add_argument("--result_review_json", type=Path, default=Path(DEFAULT_REVIEW_JSON))
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        result_review=_load_json(args.result_review_json),
        result_review_json=str(args.result_review_json),
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
    result_review_json: str = DEFAULT_REVIEW_JSON,
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_summary(result_review)
    plan = _closeout_plan(source=source, result_review_json=result_review_json)
    checks = [
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only closeout that records promotion blockers and keeps "
                "candidate-set consensus safety-score shadow atom default-off"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This closeout plan reads only the result-review artifact. It "
                "does not recompute outcomes, define new atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "run replay, run DP, modify DP, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "source_summary": source,
        "closeout_plan": plan,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["closeout_plan"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Non-Promotion Closeout Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closeout execution authorized: `{decision['nonpromotion_closeout_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Source status: `{source['status']}`",
        f"- Closeout classification: `{source['closeout_classification']}`",
        f"- Source authorizes closeout plan: `{source['nonpromotion_closeout_plan_authorized']}`",
        "",
        "## Closeout Scope",
        "",
        f"- Result review JSON: `{plan['result_review_json']}`",
        f"- Decision: `{plan['closeout_decision']}`",
        f"- Default-off retained: `{plan['default_off_retained']}`",
        f"- Executes closeout now: `{plan['executes_closeout_now']}`",
        "",
        "## Promotion Blockers",
        "",
    ]
    for item in plan["promotion_blockers"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Records", ""])
    for item in plan["required_closeout_records"]:
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
    review = _dict(report.get("result_review"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "result_review_ready": bool(
            decision.get("mixed_result_nonpromotion_diagnosis_result_review_ready")
        ),
        "nonpromotion_closeout_plan_authorized": bool(
            decision.get("nonpromotion_closeout_plan_authorized")
        ),
        "closeout_classification": review.get("closeout_classification"),
        "review_authorizes_closeout_plan": bool(review.get("authorizes_closeout_plan")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
    }


def _closeout_plan(source: dict[str, Any], result_review_json: str) -> dict[str, Any]:
    return {
        "result_review_json": result_review_json,
        "closeout_decision": "do_not_promote_shadow_atom_keep_default_off",
        "default_off_retained": True,
        "executes_closeout_now": False,
        "requires_new_replay": False,
        "requires_label_attachment": False,
        "requires_camp_training": False,
        "requires_atom_promotion": False,
        "requires_online_selector_change": False,
        "requires_dp_modification": False,
        "promotion_blockers": [
            "safety_benefit_evidence remains false",
            "diagnosis classified the result as mixed non-promotion",
            "worse changed rows remain present",
            "nonfallback mean SafetyCost v1 delta remains positive",
            "sample remains six nonformal logs and is too small for promotion",
            "formal seeds 11/12/13 remain frozen and unused",
        ],
        "required_closeout_records": [
            "artifact roots and SHA256SUMS for plan, evaluation, result review, diagnosis, and diagnosis result review",
            "explicit statement that candidate-set consensus safety-score atom remains shadow-only/default-off",
            "explicit statement that no CAMP retraining, online selector promotion, Full36, formal seeds, replay, or DP modification is authorized",
            "next admissible work, if any, must start from a fresh plan-only gate",
        ],
        "source_contract": {
            "status": source["status"],
            "classification": source["closeout_classification"],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], REVIEW_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_closeout_plan",
            source["authorized_next_work"],
            REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_result_review_ready", source["result_review_ready"], True),
        _check_equal(
            "source_closeout_plan_authorized",
            source["nonpromotion_closeout_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_closeout_classification",
            source["closeout_classification"],
            "confirmed_mixed_nonpromotion_closeout_needed",
        ),
        _check_equal("source_review_authorizes_closeout", source["review_authorizes_closeout_plan"], True),
        _check_equal("source_no_safety_benefit", source["safety_benefit_evidence"], False),
        _check_equal("source_no_atom_promotion", source["atom_promotion_authorized"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_decision_nonpromotion", plan["closeout_decision"], "do_not_promote_shadow_atom_keep_default_off"),
        _check_equal("plan_default_off_retained", plan["default_off_retained"], True),
        _check_equal("plan_executes_nothing_now", plan["executes_closeout_now"], False),
        _check_equal("plan_no_new_replay", plan["requires_new_replay"], False),
        _check_equal("plan_no_label_attachment", plan["requires_label_attachment"], False),
        _check_equal("plan_no_camp_training", plan["requires_camp_training"], False),
        _check_equal("plan_no_atom_promotion", plan["requires_atom_promotion"], False),
        _check_equal("plan_no_online_selector", plan["requires_online_selector_change"], False),
        _check_equal("plan_no_dp_modification", plan["requires_dp_modification"], False),
        _check_equal("plan_has_promotion_blockers", bool(plan["promotion_blockers"]), True),
        _check_equal("plan_has_required_records", bool(plan["required_closeout_records"]), True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["promotion_blockers"] + plan["required_closeout_records"]).lower()
    return [
        _check_equal("boundary_mentions_no_safety_benefit", "safety_benefit_evidence" in text, True),
        _check_equal("boundary_mentions_default_off", "default-off" in text or "default_off" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text, True),
        _check_equal("boundary_blocks_online", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp modification" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "nonpromotion_closeout_plan_ready": passed,
        "nonpromotion_closeout_authorization_gate_authorized": passed,
        "nonpromotion_closeout_authorized": False,
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
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
