#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as EVALUATION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as EVALUATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_result_review_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "mixed_result_nonpromotion_diagnosis_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_EXECUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_shadow_atom_"
    "safety_score_evaluation_retry_execution_a28d089"
)

EXECUTION_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_execution.json"
)
EXECUTION_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "evaluation_retry_execution.md"
)
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

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
            "Result-review-only gate for a read-only candidate-set consensus "
            "shadow atom safety-score evaluation artifact. It classifies "
            "mixed SafetyCost v1 diagnostics and does not promote atoms, "
            "train CAMP, change online selection, run replay, or modify DP."
        )
    )
    parser.add_argument("--execution_root", type=Path, default=Path(DEFAULT_EXECUTION_ROOT))
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(execution_root=args.execution_root, label=args.label)
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
    execution_root: Path,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(execution_root)
    evaluation = _evaluation_summary(artifact.get("json_payload") or {})
    classification = _classify_result(evaluation)
    checks = [
        *_artifact_checks(artifact),
        *_evaluation_checks(evaluation),
        *_classification_checks(classification),
        *_boundary_checks(evaluation),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_"
                "safety_score_evaluation_result_review_v1"
            ),
            "label": label,
            "role": (
                "review-only classification of read-only SafetyCost v1 "
                "diagnostics after fixed shadow selection"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "label_attachment": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This review reads an offline evaluation artifact only. It "
                "does not recompute labels, define atoms, choose lambda, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, run DP, modify DP, or "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "execution_artifact": _strip_payload(artifact),
        "evaluation_summary": evaluation,
        "result_classification": classification,
        "review_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, classification),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["evaluation_summary"]
    classification = report["result_classification"]
    lines = [
        "# Candidate-Set Consensus Safety-Score Evaluation Result Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Result classification: `{classification['classification']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Artifact",
        "",
        f"- Root: `{report['execution_artifact']['root']}`",
        f"- SHA OK: `{report['execution_artifact']['sha256sums_ok']}`",
        f"- Exit code: `{report['execution_artifact']['exit_code']}`",
        f"- HEADS present: `{bool(report['execution_artifact']['heads_text'])}`",
        "",
        "## Summary",
        "",
        f"- Logs: `{summary['log_count']}`",
        f"- Records: `{summary['records']}`",
        f"- Valid records: `{summary['valid_records']}`",
        f"- Outcome-available records: `{summary['outcome_available_records']}`",
        f"- Formal seed logs: `{summary['formal_seed_log_count']}`",
        f"- Max changed records: `{summary['max_changed_records']}`",
        f"- Fallback-retained records: `{summary['fallback_retained_records']}`",
        "",
        "## Lambda Review",
        "",
        "| Lambda | Changed | Better | Same | Worse | Mean delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in classification["lambda_rows"]:
        lines.append(
            f"| `{row['lambda']}` | `{row['changed_records']}` | "
            f"`{row['changed_cost_better_records']}` | "
            f"`{row['changed_cost_same_records']}` | "
            f"`{row['changed_cost_worse_records']}` | "
            f"`{row['changed_safety_cost_delta_mean']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            classification["interpretation"],
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This review does not authorize safety benefit claims, atom "
            "promotion, CAMP retraining, online selector changes, formal "
            "seeds, Full36, replay, label attachment, or DP modification.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (EXECUTION_JSON, EXECUTION_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[EXECUTION_JSON].is_file():
        loaded = _load_json(files[EXECUTION_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
    exit_code = None
    if files[EXIT_CODE].is_file():
        exit_code = (files[EXIT_CODE].read_text(encoding="utf-8").strip() or None)
    heads = (
        files[HEADS].read_text(encoding="utf-8", errors="replace")
        if files[HEADS].is_file()
        else ""
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "exit_code": exit_code,
        "heads_text": heads,
        "json_payload": payload,
    }


def _evaluation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("evaluation_summary"))
    rows = [_dict(row) for row in summary.get("by_lambda") or []]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "evaluation_ready": bool(decision.get("safety_score_evaluation_ready")),
        "result_review_authorized": bool(
            decision.get("safety_score_evaluation_result_review_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "failed_checks": list(decision.get("failed_checks") or []),
        "log_count": _optional_int(summary.get("log_count")),
        "records": _optional_int(summary.get("records")),
        "valid_records": _optional_int(summary.get("valid_records")),
        "outcome_available_records": _optional_int(
            summary.get("outcome_available_records")
        ),
        "formal_seed_log_count": _optional_int(summary.get("formal_seed_log_count")),
        "fallback_retained_records": _optional_int(
            summary.get("fallback_retained_records")
        ),
        "record_error_counts": dict(summary.get("record_error_counts") or {}),
        "max_changed_records": _optional_int(summary.get("max_changed_records")),
        "by_lambda": rows,
        "by_run": _dict(summary.get("by_run")),
    }


def _classify_result(summary: dict[str, Any]) -> dict[str, Any]:
    rows = [_normalize_lambda_row(row) for row in summary["by_lambda"]]
    positive_rows = [row for row in rows if row["lambda"] is not None and row["lambda"] > 0.0]
    changed_positive_rows = [row for row in positive_rows if row["changed_records"] > 0]
    better_only_rows = [
        row
        for row in changed_positive_rows
        if row["changed_cost_better_records"] > 0
        and row["changed_cost_worse_records"] == 0
    ]
    worse_rows = [
        row for row in changed_positive_rows if row["changed_cost_worse_records"] > 0
    ]
    positive_mean_worse_rows = [
        row
        for row in changed_positive_rows
        if row["changed_safety_cost_delta_mean"] is not None
        and row["changed_safety_cost_delta_mean"] > 0.0
    ]
    zero_row = next((row for row in rows if row["lambda"] == 0.0), {})
    classification = "mixed_nonpromotion"
    if not changed_positive_rows:
        classification = "no_material_selection_change"
    elif not worse_rows and not positive_mean_worse_rows:
        classification = "directional_signal_only_not_promotable"
    return {
        "classification": classification,
        "lambda_rows": rows,
        "positive_changed_lambda_count": len(changed_positive_rows),
        "better_only_lambda_count": len(better_only_rows),
        "worse_lambda_count": len(worse_rows),
        "positive_mean_worse_lambda_count": len(positive_mean_worse_rows),
        "zero_lambda_changed_records": zero_row.get("changed_records"),
        "best_small_lambda": (
            min(
                better_only_rows,
                key=lambda row: abs(row["changed_safety_cost_delta_mean"] or 0.0),
            )
            if better_only_rows
            else None
        ),
        "max_changed_records": summary["max_changed_records"],
        "sample_too_small_for_promotion": True,
        "safety_benefit_evidence": False,
        "atom_promotion_recommended": False,
        "interpretation": (
            "The retry contains a real selection-change signal, but the "
            "diagnostic is mixed: some small positive lambdas improve changed "
            "SafetyCost v1 rows, while larger lambdas introduce worse changed "
            "rows or positive mean deltas. This supports only a non-promotion "
            "diagnosis gate, not a safety-benefit claim."
        ),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "artifact_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("artifact_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("artifact_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "artifact_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _evaluation_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("evaluation_status", summary["status"], EVALUATION_READY_STATUS),
        _check_equal("evaluation_passed", summary["passed"], True),
        _check_equal(
            "evaluation_authorizes_result_review",
            summary["authorized_next_work"],
            EVALUATION_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("evaluation_ready", summary["evaluation_ready"], True),
        _check_equal(
            "evaluation_result_review_authorized",
            summary["result_review_authorized"],
            True,
        ),
        _check_equal("evaluation_no_blocked_actions", summary["blocked_action_conflicts"], []),
        _check_equal("evaluation_failed_checks_empty", summary["failed_checks"], []),
        _check_equal("evaluation_log_count", summary["log_count"], EXPECTED_LOGS),
        _check_equal("evaluation_records", summary["records"], EXPECTED_RECORDS),
        _check_equal("evaluation_valid_records", summary["valid_records"], EXPECTED_RECORDS),
        _check_equal(
            "evaluation_outcomes_available",
            summary["outcome_available_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal("evaluation_no_formal_seed_logs", summary["formal_seed_log_count"], 0),
        _check_equal("evaluation_record_errors_empty", summary["record_error_counts"], {}),
        _check_equal("evaluation_max_changed_positive", (summary["max_changed_records"] or 0) > 0, True),
    ]


def _classification_checks(classification: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "classification_has_positive_changes",
            classification["positive_changed_lambda_count"] > 0,
            True,
        ),
        _check_equal(
            "classification_zero_lambda_preserves_selection",
            classification["zero_lambda_changed_records"],
            0,
        ),
        _check_equal(
            "classification_mixed_nonpromotion",
            classification["classification"],
            "mixed_nonpromotion",
        ),
        _check_equal(
            "classification_sample_too_small_for_promotion",
            classification["sample_too_small_for_promotion"],
            True,
        ),
        _check_equal(
            "classification_no_safety_benefit_claim",
            classification["safety_benefit_evidence"],
            False,
        ),
        _check_equal(
            "classification_no_atom_promotion",
            classification["atom_promotion_recommended"],
            False,
        ),
    ]


def _boundary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("boundary_safety_benefit_not_claimed", False, False),
        _check_equal("boundary_atom_promotion_not_authorized", False, False),
        _check_equal("boundary_camp_training_not_authorized", False, False),
        _check_equal("boundary_online_selector_not_authorized", False, False),
        _check_equal("boundary_dp_modification_not_authorized", False, False),
        _check_equal("boundary_no_blocked_actions_from_source", summary["blocked_action_conflicts"], []),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    classification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_result_review_ready": passed,
        "mixed_result_nonpromotion_diagnosis_plan_authorized": passed,
        "result_classification": classification["classification"],
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


def _sha256sum_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    root = path.parent
    details = []
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            ok = False
            details.append({"line": line, "ok": False, "reason": "malformed"})
            continue
        expected, name = parts
        item = root / name.strip()
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append(
            {
                "path": str(item),
                "expected": expected,
                "actual": actual,
                "ok": matched,
            }
        )
    return ok, details


def _normalize_lambda_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "lambda": _optional_float(row.get("lambda")),
        "changed_records": _int(row.get("changed_records")),
        "changed_cost_better_records": _int(row.get("changed_cost_better_records")),
        "changed_cost_same_records": _int(row.get("changed_cost_same_records")),
        "changed_cost_worse_records": _int(row.get("changed_cost_worse_records")),
        "changed_hard_worse_records": _int(row.get("changed_hard_worse_records")),
        "changed_safety_cost_delta_mean": _optional_float(
            row.get("changed_safety_cost_delta_mean")
        ),
    }


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


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


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
