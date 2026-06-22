#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.summarize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass_execution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as EXECUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as EXECUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_consideration_plan_only"
)
LOG_NAME = "camp_selection_log.json"
COMPATIBILITY_FIELDS = (
    "num_candidates",
    "selected_index",
    "scores",
    "selection_scores",
    "weights",
    "selection_weights",
    "atoms",
    "normalized_atoms",
    "candidate_first_reference_xy",
    "candidate_route_progress",
    "candidate_step_reach",
    "candidate_horizon_union_planned_red_light_cost",
    "feasible_mask",
    "infeasibility_reasons",
    "candidate_set_consensus_payload_logging",
)
PAYLOAD_COMPATIBILITY_KEYS = (
    "candidate_count",
    "candidate_set_consensus_center_rms_m",
    "candidate_set_consensus_center_rms_rank",
    "default_off",
    "closed_loop_outcome_fields_read",
    "future_outcome_leakage",
    "classical_benders_claim",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Review generated outcome-label logs against the fixed broader "
            "nonformal candidate logs. This verifies candidate ordering and "
            "posterior-label isolation, but does not attach labels or retry "
            "SafetyCost evaluation."
        )
    )
    parser.add_argument("--execution_summary_json", type=Path, required=True)
    parser.add_argument("--label_root", type=Path, required=True)
    parser.add_argument("--broader_candidate_root", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        execution_summary=_load_json(args.execution_summary_json),
        label_root=args.label_root,
        broader_candidate_root=args.broader_candidate_root,
        label=args.label,
        paths={
            "execution_summary_json": str(args.execution_summary_json),
            "label_root": str(args.label_root),
            "broader_candidate_root": str(args.broader_candidate_root),
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


def build_report(
    *,
    execution_summary: dict[str, Any],
    label_root: Path,
    broader_candidate_root: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    execution = _execution_summary(execution_summary)
    review = _source_review(label_root, broader_candidate_root, execution["run_ids"])
    checks = [
        *_execution_checks(execution),
        *_review_checks(review, execution),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_source_review_v1"
            ),
            "label": label,
            "role": (
                "review generated posterior outcome labels as a compatible "
                "source for the fixed broader nonformal candidate ordering"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "label_attachment": False,
            "safety_score_evaluation_retry": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(review["formal_seed_log_count"]),
            "paths": paths or {},
            "math_boundary": (
                "This source review compares candidate ordering fields and "
                "posterior-label isolation only. It does not attach labels, "
                "compute SafetyCost v1, retry the safety-score evaluation, "
                "train CAMP, promote an atom, change online selection, or "
                "modify DP. Labels remain offline evidence only and are "
                "forbidden for atom definition, lambda selection, online "
                "scoring, CAMP training, and any DP-side classical Benders "
                "claim. The affine score form score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 master are unchanged."
            ),
        },
        "execution_summary": execution,
        "source_review": review,
        "source_review_checks": checks,
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["source_review"]
    lines = [
        "# Candidate-Set Consensus Outcome-Label Source Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Label attachment authorized: `{decision['label_attachment_authorized']}`",
        f"- Safety-score retry authorized: `{decision['safety_score_evaluation_retry_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Compatibility",
        "",
        f"- Run count: `{review['run_count']}`",
        f"- Records compared: `{review['records_compared']}`",
        f"- Compatibility mismatches: `{review['compatibility_mismatch_count']}`",
        f"- Label complete outcome records: `{review['label_complete_outcome_records']}`",
        f"- Broader outcome records present: `{review['broader_outcome_records_present']}`",
        f"- Payload no-leak records: `{review['payload_no_leak_records']}`",
        f"- Formal seed logs: `{review['formal_seed_log_count']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["source_review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _execution_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    logs = _dict(report.get("label_log_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "source_review_authorized": bool(
            decision.get("outcome_label_source_review_authorized")
        ),
        "label_attachment_authorized": bool(decision.get("label_attachment_authorized")),
        "safety_score_retry_authorized": bool(
            decision.get("safety_score_evaluation_retry_authorized")
        ),
        "run_ids": sorted(str(run_id) for run_id in logs.get("run_ids") or []),
        "log_count": _optional_int(logs.get("log_count")) or 0,
        "records": _optional_int(logs.get("records")) or 0,
        "complete_outcome_records": (
            _optional_int(logs.get("complete_outcome_records")) or 0
        ),
    }


def _source_review(
    label_root: Path,
    broader_candidate_root: Path,
    run_ids: list[str],
) -> dict[str, Any]:
    rows = []
    mismatch_count = 0
    label_records = 0
    broader_records = 0
    complete_outcome_records = 0
    broader_outcome_records = 0
    payload_no_leak_records = 0
    formal_seed_log_count = 0
    errors = []
    for run_id in run_ids:
        label_path = label_root / run_id / LOG_NAME
        broader_path = broader_candidate_root / run_id / LOG_NAME
        pair = _compare_run(label_path, broader_path)
        rows.append(pair)
        mismatch_count += pair["compatibility_mismatch_count"]
        label_records += pair["label_records"]
        broader_records += pair["broader_records"]
        complete_outcome_records += pair["label_complete_outcome_records"]
        broader_outcome_records += pair["broader_outcome_records_present"]
        payload_no_leak_records += pair["payload_no_leak_records"]
        formal_seed_log_count += int(pair["formal_seed"])
        errors.extend(pair["errors"])
    return {
        "label_root": str(label_root),
        "broader_candidate_root": str(broader_candidate_root),
        "run_count": len(rows),
        "run_ids": run_ids,
        "label_records": label_records,
        "broader_records": broader_records,
        "records_compared": sum(row["records_compared"] for row in rows),
        "compatibility_mismatch_count": mismatch_count,
        "label_complete_outcome_records": complete_outcome_records,
        "broader_outcome_records_present": broader_outcome_records,
        "payload_no_leak_records": payload_no_leak_records,
        "formal_seed_log_count": formal_seed_log_count,
        "errors": sorted(set(errors))[:20],
        "runs": rows,
    }


def _compare_run(label_path: Path, broader_path: Path) -> dict[str, Any]:
    run_id = label_path.parent.name
    errors = []
    label_rows = _read_rows(label_path, errors, "label")
    broader_rows = _read_rows(broader_path, errors, "broader")
    records_compared = min(len(label_rows), len(broader_rows))
    mismatches = []
    label_complete = 0
    broader_outcomes = 0
    payload_no_leak = 0
    for index in range(records_compared):
        label_row = label_rows[index]
        broader_row = broader_rows[index]
        for field in COMPATIBILITY_FIELDS:
            if _compat_value(label_row, field) != _compat_value(broader_row, field):
                mismatches.append({"record": index, "field": field})
                break
        if _complete_outcomes(label_row.get("candidate_closed_loop_outcomes")):
            label_complete += 1
        if broader_row.get("candidate_closed_loop_outcomes") is not None:
            broader_outcomes += 1
        payload = _dict(label_row.get("candidate_set_consensus_payload_logging"))
        if (
            payload.get("closed_loop_outcome_fields_read") is False
            and payload.get("future_outcome_leakage") is False
            and payload.get("classical_benders_claim") is False
        ):
            payload_no_leak += 1
    return {
        "run_id": run_id,
        "label_path": str(label_path),
        "broader_path": str(broader_path),
        "label_records": len(label_rows),
        "broader_records": len(broader_rows),
        "records_compared": records_compared,
        "compatibility_mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:10],
        "label_complete_outcome_records": label_complete,
        "broader_outcome_records_present": broader_outcomes,
        "payload_no_leak_records": payload_no_leak,
        "formal_seed": _contains_formal_seed(f"{run_id} {label_path} {broader_path}"),
        "errors": errors,
    }


def _read_rows(path: Path, errors: list[str], label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        errors.append(f"{label}:missing:{path}")
        return []
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}:invalid_json:{path}:{exc}")
        return []
    if not isinstance(payload, list):
        errors.append(f"{label}:not_json_list:{path}")
        return []
    return [row for row in payload if isinstance(row, dict)]


def _compat_value(row: dict[str, Any], field: str) -> Any:
    value = row.get(field)
    if field == "candidate_set_consensus_payload_logging":
        payload = _dict(value)
        return {key: payload.get(key) for key in PAYLOAD_COMPATIBILITY_KEYS}
    return value


def _execution_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("execution_status", summary["status"], EXECUTION_READY_STATUS),
        _check_equal("execution_passed", summary["passed"], True),
        _check_equal(
            "execution_authorizes_source_review",
            summary["authorized_next_work"],
            EXECUTION_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("execution_source_review_authorized", summary["source_review_authorized"], True),
        _check_equal("execution_label_attachment_not_authorized", summary["label_attachment_authorized"], False),
        _check_equal("execution_safety_retry_not_authorized", summary["safety_score_retry_authorized"], False),
        _check_equal("execution_log_count", summary["log_count"], EXPECTED_LOGS),
        _check_equal("execution_records", summary["records"], EXPECTED_RECORDS),
        _check_equal("execution_complete_outcomes", summary["complete_outcome_records"], EXPECTED_RECORDS),
    ]


def _review_checks(review: dict[str, Any], execution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("review_run_count", review["run_count"], EXPECTED_LOGS),
        _check_equal("review_run_ids_match_execution", review["run_ids"], execution["run_ids"]),
        _check_equal("review_label_records", review["label_records"], EXPECTED_RECORDS),
        _check_equal("review_broader_records", review["broader_records"], EXPECTED_RECORDS),
        _check_equal("review_records_compared", review["records_compared"], EXPECTED_RECORDS),
        _check_equal("review_compatibility_mismatches_zero", review["compatibility_mismatch_count"], 0),
        _check_equal("review_label_complete_outcomes", review["label_complete_outcome_records"], EXPECTED_RECORDS),
        _check_equal("review_broader_outcomes_absent", review["broader_outcome_records_present"], 0),
        _check_equal("review_payload_no_leak_all_records", review["payload_no_leak_records"], EXPECTED_RECORDS),
        _check_equal("review_no_formal_seed_logs", review["formal_seed_log_count"], 0),
        _check_equal("review_errors_empty", review["errors"], []),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "outcome_label_source_review_ready": passed,
        "safety_score_evaluation_retry_plan_authorized": passed,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
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


def _complete_outcomes(outcomes: Any) -> bool:
    if not isinstance(outcomes, list) or len(outcomes) != EXPECTED_CANDIDATES:
        return False
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            return False
        if _optional_int(outcome.get("candidate_index")) != index:
            return False
    return True


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
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
