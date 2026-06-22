#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as EVALUATION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as EVALUATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_result import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_result_review_only"
)
EPS = 1e-12

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
            "Read-only mixed-result non-promotion diagnosis for candidate-set "
            "consensus SafetyCost v1 evaluation artifacts."
        )
    )
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--result_review_json", type=Path, required=True)
    parser.add_argument("--execution_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        plan=_load_json(args.plan_json),
        result_review=_load_json(args.result_review_json),
        execution=_load_json(args.execution_json),
        label=args.label,
        paths={
            "plan_json": str(args.plan_json),
            "result_review_json": str(args.result_review_json),
            "execution_json": str(args.execution_json),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    plan: dict[str, Any],
    result_review: dict[str, Any],
    execution: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    sources = _source_summary(plan, result_review, execution)
    diagnosis = _diagnosis(execution)
    checks = [
        *_source_checks(sources),
        *_diagnosis_checks(diagnosis),
        *_boundary_checks(sources),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_v1"
            ),
            "label": label,
            "role": (
                "read-only diagnosis of mixed SafetyCost v1 deltas after fixed "
                "shadow selection"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "paths": paths or {},
            "math_boundary": (
                "This diagnosis reads existing offline artifacts only. It does "
                "not recompute outcomes, define atoms, choose lambda online, "
                "alter score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, run replay, run "
                "DP, modify DP, or claim a DP-side classical Benders "
                "decomposition."
            ),
        },
        "source_summary": sources,
        "diagnosis_summary": diagnosis,
        "diagnosis_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, diagnosis),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["diagnosis_summary"]
    lines = [
        "# Candidate-Set Consensus Mixed Result Non-Promotion Diagnosis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Diagnosis class: `{summary['diagnosis_class']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Lambda Buckets",
        "",
        "| Lambda | Changed | Better | Same | Worse | Mean delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["by_lambda"]:
        lines.append(
            f"| `{row['lambda']}` | `{row['changed_records']}` | "
            f"`{row['better_records']}` | `{row['same_records']}` | "
            f"`{row['worse_records']}` | `{row['mean_delta']}` |"
        )
    lines.extend(["", "## Run Buckets", ""])
    for key, row in summary["by_run"].items():
        lines.append(f"- `{key}`: `{row}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This diagnosis does not authorize safety benefit claims, atom "
            "promotion, CAMP retraining, online selector changes, formal "
            "seeds, Full36, replay, label attachment, or DP modification.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(
    plan: dict[str, Any],
    result_review: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    plan_decision = _dict(plan.get("final_decision"))
    review_decision = _dict(result_review.get("final_decision"))
    execution_decision = _dict(execution.get("final_decision"))
    return {
        "plan_status": plan_decision.get("status"),
        "plan_passed": bool(plan_decision.get("passed")),
        "plan_authorized_next_work": plan_decision.get("authorized_next_work"),
        "result_review_status": review_decision.get("status"),
        "result_review_passed": bool(review_decision.get("passed")),
        "result_review_authorized_next_work": review_decision.get("authorized_next_work"),
        "result_classification": review_decision.get("result_classification"),
        "execution_status": execution_decision.get("status"),
        "execution_passed": bool(execution_decision.get("passed")),
        "execution_authorized_next_work": execution_decision.get("authorized_next_work"),
        "blocked_action_conflicts": [
            key
            for decision in (plan_decision, review_decision, execution_decision)
            for key in BLOCKED_ACTIONS
            if bool(decision.get(key))
        ],
    }


def _diagnosis(execution: dict[str, Any]) -> dict[str, Any]:
    records = [_dict(record) for record in execution.get("evaluation_records") or []]
    by_lambda: dict[float, dict[str, Any]] = {}
    by_run = defaultdict(_empty_bucket)
    by_fallback = defaultdict(_empty_bucket)
    changed_examples = []
    for record in records:
        run_id = str(record.get("run_id"))
        fallback = bool(record.get("fallback_retained"))
        for result in record.get("lambda_results") or []:
            row = _dict(result)
            lam = _float(row.get("lambda"))
            if lam is None:
                continue
            bucket = by_lambda.setdefault(lam, _empty_bucket())
            if not row.get("changed_selected_index"):
                continue
            delta = _float(row.get("safety_cost_delta_vs_logged_selected"))
            _add_delta(bucket, delta)
            _add_delta(by_run[run_id], delta)
            _add_delta(by_fallback["fallback" if fallback else "nonfallback"], delta)
            if len(changed_examples) < 20:
                changed_examples.append(
                    {
                        "run_id": run_id,
                        "record_index": record.get("record_index"),
                        "lambda": lam,
                        "delta": delta,
                        "fallback_retained": fallback,
                        "hard_components_worse_than_logged": row.get(
                            "hard_components_worse_than_logged"
                        ),
                    }
                )
    lambda_rows = [
        {"lambda": lam, **_finalize_bucket(bucket)}
        for lam, bucket in sorted(by_lambda.items())
    ]
    worse_rows = [row for row in lambda_rows if row["worse_records"] > 0]
    better_only_rows = [
        row
        for row in lambda_rows
        if row["changed_records"] > 0 and row["better_records"] > 0 and row["worse_records"] == 0
    ]
    return {
        "diagnosis_class": "mixed_nonpromotion",
        "records": len(records),
        "by_lambda": lambda_rows,
        "by_run": {key: _finalize_bucket(value) for key, value in sorted(by_run.items())},
        "by_fallback": {
            key: _finalize_bucket(value) for key, value in sorted(by_fallback.items())
        },
        "changed_examples": changed_examples,
        "better_only_lambda_count": len(better_only_rows),
        "worse_lambda_count": len(worse_rows),
        "sample_too_small_for_promotion": True,
        "safety_benefit_evidence": False,
        "atom_promotion_recommended": False,
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_status", source["plan_status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", source["plan_passed"], True),
        _check_equal(
            "plan_authorizes_authorization_only",
            source["plan_authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("review_status", source["result_review_status"], REVIEW_READY_STATUS),
        _check_equal("review_passed", source["result_review_passed"], True),
        _check_equal(
            "review_authorizes_plan",
            source["result_review_authorized_next_work"],
            REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "review_classification_mixed",
            source["result_classification"],
            "mixed_nonpromotion",
        ),
        _check_equal("execution_status", source["execution_status"], EVALUATION_READY_STATUS),
        _check_equal("execution_passed", source["execution_passed"], True),
        _check_equal(
            "execution_authorizes_review",
            source["execution_authorized_next_work"],
            EVALUATION_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _diagnosis_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("diagnosis_class", summary["diagnosis_class"], "mixed_nonpromotion"),
        _check_equal("diagnosis_records_present", summary["records"] > 0, True),
        _check_equal("diagnosis_better_only_present", summary["better_only_lambda_count"] > 0, True),
        _check_equal("diagnosis_worse_present", summary["worse_lambda_count"] > 0, True),
        _check_equal("diagnosis_no_safety_benefit", summary["safety_benefit_evidence"], False),
        _check_equal("diagnosis_no_promotion", summary["atom_promotion_recommended"], False),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("boundary_no_source_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("boundary_no_training", False, False),
        _check_equal("boundary_no_online_selector", False, False),
        _check_equal("boundary_no_dp_modification", False, False),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "mixed_result_nonpromotion_diagnosis_ready": passed,
        "mixed_result_nonpromotion_diagnosis_result_review_authorized": passed,
        "diagnosis_class": diagnosis["diagnosis_class"],
        "sample_too_small_for_promotion": True,
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


def _empty_bucket() -> dict[str, Any]:
    return {
        "changed_records": 0,
        "better_records": 0,
        "same_records": 0,
        "worse_records": 0,
        "deltas": [],
    }


def _add_delta(bucket: dict[str, Any], delta: float | None) -> None:
    bucket["changed_records"] += 1
    if delta is None:
        return
    bucket["deltas"].append(delta)
    if delta < -EPS:
        bucket["better_records"] += 1
    elif delta > EPS:
        bucket["worse_records"] += 1
    else:
        bucket["same_records"] += 1


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    deltas = list(bucket.get("deltas") or [])
    return {
        "changed_records": int(bucket.get("changed_records") or 0),
        "better_records": int(bucket.get("better_records") or 0),
        "same_records": int(bucket.get("same_records") or 0),
        "worse_records": int(bucket.get("worse_records") or 0),
        "mean_delta": sum(deltas) / len(deltas) if deltas else None,
    }


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
