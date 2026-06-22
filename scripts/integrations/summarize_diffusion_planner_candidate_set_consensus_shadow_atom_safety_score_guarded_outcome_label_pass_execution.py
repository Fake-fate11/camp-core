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

from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    REQUIRED_OUTCOME_FIELDS,
)
from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as AUTHORIZED_EXECUTION_NEXT_WORK,
    READY_STATUS as AUTHORIZATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_execution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_execution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review_only"
)
LOG_NAME = "camp_selection_log.json"
SUCCESS_MARKER = (
    "candidate_set_consensus_guarded_outcome_label_pass_candidate_complete"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only execution summary for the guarded nonformal outcome-label "
            "pass. It validates produced candidate_closed_loop_outcomes logs "
            "but does not attach labels, retry SafetyCost evaluation, train CAMP, "
            "or modify DP."
        )
    )
    parser.add_argument("--authorization_json", type=Path, required=True)
    parser.add_argument("--label_root", type=Path, required=True)
    parser.add_argument("--runbook_log", type=Path, required=True)
    parser.add_argument("--exit_code_path", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        authorization=_load_json(args.authorization_json),
        label_root=args.label_root,
        runbook_log=args.runbook_log,
        exit_code_path=args.exit_code_path,
        label=args.label,
        paths={
            "authorization_json": str(args.authorization_json),
            "label_root": str(args.label_root),
            "runbook_log": str(args.runbook_log),
            "exit_code_path": str(args.exit_code_path),
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
    authorization: dict[str, Any],
    label_root: Path,
    runbook_log: Path,
    exit_code_path: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    auth = _authorization_summary(authorization)
    execution = _execution_summary(runbook_log, exit_code_path)
    logs = _label_log_summary(label_root, auth["route_run_ids"])
    checks = [
        *_authorization_checks(auth),
        *_execution_checks(execution),
        *_label_log_checks(logs, auth),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "guarded_outcome_label_pass_execution_summary_v1"
            ),
            "label": label,
            "role": (
                "read-only summary of generated posterior candidate outcome "
                "labels for the six nonformal guarded label-pass runs"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "label_attachment": False,
            "safety_score_evaluation_retry": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(logs["formal_seed_log_count"]),
            "paths": paths or {},
            "math_boundary": (
                "This summary validates generated posterior "
                "candidate_closed_loop_outcomes only. It does not attach labels "
                "to prior artifacts, compute SafetyCost v1, retry the "
                "safety-score evaluation, train CAMP, promote an atom, change "
                "online selection, or modify DP. The labels remain offline "
                "evidence and are forbidden for atom definition, lambda "
                "selection, online scoring, CAMP training, and any DP-side "
                "classical Benders claim. The affine score form "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 master are unchanged."
            ),
        },
        "authorization_summary": auth,
        "execution_summary": execution,
        "label_log_summary": logs,
        "execution_checks": checks,
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    logs = report["label_log_summary"]
    execution = report["execution_summary"]
    lines = [
        "# Candidate-Set Consensus Guarded Outcome-Label Pass Execution Summary",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Outcome-label pass executed: `{decision['outcome_label_pass_executed']}`",
        f"- Label attachment authorized: `{decision['label_attachment_authorized']}`",
        f"- Safety-score retry authorized: `{decision['safety_score_evaluation_retry_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Execution",
        "",
        f"- Exit code: `{execution['exit_code']}`",
        f"- Success marker present: `{execution['success_marker_present']}`",
        "",
        "## Label Logs",
        "",
        f"- Label root: `{logs['label_root']}`",
        f"- Log count: `{logs['log_count']}`",
        f"- Records: `{logs['records']}`",
        f"- Complete outcome records: `{logs['complete_outcome_records']}`",
        f"- Candidate-count compatible records: `{logs['candidate_count_compatible_records']}`",
        f"- Formal seed logs: `{logs['formal_seed_log_count']}`",
        f"- Run IDs: `{logs['run_ids']}`",
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
    for check in report["execution_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _authorization_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("plan_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "execution_authorized": bool(
            decision.get("outcome_label_pass_execution_authorized")
        ),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "label_attachment_authorized": bool(decision.get("label_attachment_authorized")),
        "safety_score_retry_authorized": bool(
            decision.get("safety_score_evaluation_retry_authorized")
        ),
        "blocked_action_conflicts": [
            key
            for key in (
                "atom_promotion_authorized",
                "full36_authorized",
                "online_selector_authorized",
                "camp_retraining_authorized",
                "training_execution_authorized",
                "dp_modification_authorized",
                "classic_benders_claim_authorized",
            )
            if bool(decision.get(key))
        ],
        "expected_logs": _optional_int(plan.get("expected_logs")) or EXPECTED_LOGS,
        "expected_records": _optional_int(plan.get("expected_records")) or EXPECTED_RECORDS,
        "expected_candidates": (
            _optional_int(plan.get("expected_candidates")) or EXPECTED_CANDIDATES
        ),
        "route_run_ids": sorted(str(run_id) for run_id in plan.get("route_run_ids") or []),
    }


def _execution_summary(runbook_log: Path, exit_code_path: Path) -> dict[str, Any]:
    log_text = runbook_log.read_text(encoding="utf-8", errors="replace") if runbook_log.is_file() else ""
    exit_text = exit_code_path.read_text(encoding="utf-8", errors="replace").strip() if exit_code_path.is_file() else None
    return {
        "runbook_log": str(runbook_log),
        "runbook_log_exists": runbook_log.is_file(),
        "exit_code_path": str(exit_code_path),
        "exit_code_path_exists": exit_code_path.is_file(),
        "exit_code": _optional_int(exit_text),
        "success_marker_present": SUCCESS_MARKER in log_text,
        "log_tail": "\n".join(log_text.splitlines()[-40:]),
    }


def _label_log_summary(label_root: Path, expected_run_ids: list[str]) -> dict[str, Any]:
    paths = sorted(path for path in label_root.glob(f"*/{LOG_NAME}") if path.is_file())
    rows = [_log_summary(path) for path in paths]
    return {
        "label_root": str(label_root),
        "label_root_exists": label_root.is_dir(),
        "log_count": len(rows),
        "records": sum(row["records"] for row in rows),
        "complete_outcome_records": sum(row["complete_outcome_records"] for row in rows),
        "candidate_count_compatible_records": sum(
            row["candidate_count_compatible_records"] for row in rows
        ),
        "formal_seed_log_count": sum(1 for row in rows if row["formal_seed"]),
        "run_ids": sorted(row["run_id"] for row in rows),
        "expected_run_ids": expected_run_ids,
        "errors": sorted({error for row in rows for error in row["errors"]})[:20],
        "logs": rows,
    }


def _log_summary(path: Path) -> dict[str, Any]:
    run_id = path.parent.name
    errors = []
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "path": str(path),
            "run_id": run_id,
            "records": 0,
            "complete_outcome_records": 0,
            "candidate_count_compatible_records": 0,
            "formal_seed": _contains_formal_seed(str(path)),
            "errors": [str(exc)],
        }
    if not isinstance(payload, list):
        return {
            "path": str(path),
            "run_id": run_id,
            "records": 0,
            "complete_outcome_records": 0,
            "candidate_count_compatible_records": 0,
            "formal_seed": _contains_formal_seed(str(path)),
            "errors": ["not_json_list"],
        }
    complete_records = 0
    candidate_count_records = 0
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            errors.append(f"{run_id}:record_{index}_not_dict")
            continue
        if _candidate_count(row) == EXPECTED_CANDIDATES:
            candidate_count_records += 1
        else:
            errors.append(f"{run_id}:record_{index}_candidate_count_mismatch")
        if _outcomes_complete(row.get("candidate_closed_loop_outcomes")):
            complete_records += 1
        else:
            errors.append(f"{run_id}:record_{index}_outcomes_incomplete")
    return {
        "path": str(path),
        "run_id": run_id,
        "records": len(payload),
        "complete_outcome_records": complete_records,
        "candidate_count_compatible_records": candidate_count_records,
        "formal_seed": _contains_formal_seed(str(path)),
        "errors": sorted(set(errors))[:10],
    }


def _authorization_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("authorization_status", summary["status"], AUTHORIZATION_READY_STATUS),
        _check_equal("authorization_passed", summary["passed"], True),
        _check_equal(
            "authorization_next_work",
            summary["authorized_next_work"],
            AUTHORIZED_EXECUTION_NEXT_WORK,
        ),
        _check_equal("authorization_execution_authorized", summary["execution_authorized"], True),
        _check_equal("authorization_formal_seeds_not_authorized", summary["formal_seeds_authorized"], False),
        _check_equal("authorization_label_attachment_not_authorized", summary["label_attachment_authorized"], False),
        _check_equal("authorization_safety_retry_not_authorized", summary["safety_score_retry_authorized"], False),
        _check_equal("authorization_no_blocked_actions", summary["blocked_action_conflicts"], []),
    ]


def _execution_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("runbook_log_exists", summary["runbook_log_exists"], True),
        _check_equal("exit_code_path_exists", summary["exit_code_path_exists"], True),
        _check_equal("runbook_exit_code_zero", summary["exit_code"], 0),
        _check_equal("runbook_success_marker_present", summary["success_marker_present"], True),
    ]


def _label_log_checks(logs: dict[str, Any], auth: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("label_root_exists", logs["label_root_exists"], True),
        _check_equal("label_log_count", logs["log_count"], auth["expected_logs"]),
        _check_equal("label_record_count", logs["records"], auth["expected_records"]),
        _check_equal(
            "label_candidate_count_compatible_records",
            logs["candidate_count_compatible_records"],
            auth["expected_records"],
        ),
        _check_equal(
            "label_complete_outcome_records",
            logs["complete_outcome_records"],
            auth["expected_records"],
        ),
        _check_equal("label_no_formal_seed_logs", logs["formal_seed_log_count"], 0),
        _check_equal("label_run_ids_match_authorization", logs["run_ids"], auth["route_run_ids"]),
        _check_equal("label_errors_empty", logs["errors"], []),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "outcome_label_pass_executed": passed,
        "outcome_label_source_review_authorized": passed,
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


def _candidate_count(row: dict[str, Any]) -> int | None:
    direct = _optional_int(row.get("num_candidates"))
    if direct is not None:
        return direct
    payload = row.get("candidate_set_consensus_payload_logging")
    if isinstance(payload, dict):
        return _optional_int(payload.get("candidate_count"))
    return None


def _outcomes_complete(outcomes: Any) -> bool:
    if not isinstance(outcomes, list) or len(outcomes) != EXPECTED_CANDIDATES:
        return False
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            return False
        if _optional_int(outcome.get("candidate_index")) != index:
            return False
        if not set(REQUIRED_OUTCOME_FIELDS).issubset(outcome):
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
