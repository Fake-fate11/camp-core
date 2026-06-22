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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_availability import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    READY_STATUS as SOURCE_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_existing_source_search_ready"
)
NO_SOURCE_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_existing_source_search_no_compatible_source"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_existing_source_search_rejected"
)
AUTHORIZED_NEXT_WORK_WITH_SOURCE = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "outcome_label_source_review_only"
)
AUTHORIZED_NEXT_WORK_NO_SOURCE = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "guarded_outcome_label_pass_consideration_plan_only"
)

LOG_NAME = "camp_selection_log.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only search for existing candidate_closed_loop_outcomes "
            "sources compatible with the candidate-set consensus safety-score "
            "evaluation. It does not generate labels, run replay, or modify DP."
        )
    )
    parser.add_argument("--availability_plan_json", type=Path, required=True)
    parser.add_argument("--search_root", type=Path, action="append", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        availability_plan=_load_json(args.availability_plan_json),
        search_roots=tuple(args.search_root),
        label=args.label,
        paths={"availability_plan_json": str(args.availability_plan_json)},
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
    availability_plan: dict[str, Any],
    search_roots: tuple[Path, ...],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(availability_plan)
    expected = _expected_scope(availability_plan)
    scan = _scan_roots(search_roots, expected)
    checks = [
        *_source_checks(source),
        *_scope_checks(expected),
        *_scan_checks(scan, expected),
    ]
    rejected = any(not check["passed"] for check in checks)
    full_sources = _full_compatible_sources(scan, expected)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_existing_source_search_v1"
            ),
            "label": label,
            "role": (
                "read-only scan for existing complete candidate outcome labels "
                "compatible with the fixed broader nonformal run scope"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "outcome_label_generation": False,
            "label_attachment": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(scan["formal_seed_log_count"]),
            "paths": paths or {},
            "math_boundary": (
                "This search reads only existing artifact files. It does not "
                "generate candidate_closed_loop_outcomes, does not attach "
                "labels, does not run replay or DP, and does not compute "
                "SafetyCost v1. A compatible source is only evidence for a "
                "later review gate; labels remain posterior offline labels and "
                "are forbidden for atom definition, lambda selection, online "
                "scoring, CAMP training, and any DP-side classical Benders "
                "claim."
            ),
        },
        "source_summary": source,
        "expected_scope": expected,
        "search_summary": scan,
        "compatible_source_sets": full_sources,
        "search_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(rejected, full_sources, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    scan = report["search_summary"]
    lines = [
        "# Candidate-Set Consensus Outcome-Label Existing Source Search",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Compatible source found: `{decision['compatible_source_found']}`",
        f"- Outcome-label generation authorized: `{decision['outcome_label_generation_authorized']}`",
        f"- Replay authorized: `{decision['new_replay_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Search Summary",
        "",
        f"- Search roots: `{scan['search_roots']}`",
        f"- Scanned logs: `{scan['scanned_log_count']}`",
        f"- Relevant logs: `{scan['relevant_log_count']}`",
        f"- Complete outcome logs: `{scan['complete_outcome_log_count']}`",
        f"- Formal seed logs: `{scan['formal_seed_log_count']}`",
        "",
        "## Compatible Source Sets",
        "",
        f"`{report['compatible_source_sets']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "If no compatible source exists, the next step is only a guarded "
        "outcome-label pass consideration plan. This search does not authorize "
        "label generation, replay, DP execution, CAMP training, atom promotion, "
        "online selector changes, formal seeds, or safety-benefit claims.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["search_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("outcome_label_availability_plan"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_ready": bool(decision.get("outcome_label_availability_plan_ready")),
        "existing_source_search_authorized": bool(
            decision.get("outcome_label_existing_source_search_authorized")
        ),
        "outcome_label_generation_authorized": bool(
            decision.get("outcome_label_generation_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "expected_logs": _optional_int(plan.get("expected_logs")),
        "expected_records": _optional_int(plan.get("expected_records")),
        "expected_candidates": _optional_int(plan.get("expected_candidates")),
        "route_seed_matrix": list(plan.get("route_seed_matrix") or []),
    }


def _expected_scope(report: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(report.get("outcome_label_availability_plan"))
    routes = [_dict(row) for row in plan.get("route_seed_matrix") or []]
    run_ids = [str(row.get("run_id")) for row in routes if row.get("run_id")]
    return {
        "expected_logs": _optional_int(plan.get("expected_logs")) or EXPECTED_LOGS,
        "expected_records": _optional_int(plan.get("expected_records")) or EXPECTED_RECORDS,
        "expected_candidates": (
            _optional_int(plan.get("expected_candidates")) or EXPECTED_CANDIDATES
        ),
        "run_ids": sorted(run_ids),
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "required_outcome_fields": list(REQUIRED_OUTCOME_FIELDS),
    }


def _scan_roots(search_roots: tuple[Path, ...], expected: dict[str, Any]) -> dict[str, Any]:
    paths: list[Path] = []
    root_errors = []
    for root in search_roots:
        if not root.exists():
            root_errors.append(f"{root}: missing")
            continue
        if root.is_file():
            if root.name == LOG_NAME:
                paths.append(root)
            continue
        paths.extend(sorted(root.rglob(LOG_NAME)))
    seen = set()
    unique_paths = []
    for path in paths:
        text = str(path)
        if text in seen:
            continue
        seen.add(text)
        unique_paths.append(path)
    relevant = []
    formal_paths = []
    for path in unique_paths:
        run_id = _run_id(path)
        if _contains_formal_seed(str(path)):
            formal_paths.append(str(path))
        if run_id not in expected["run_ids"]:
            continue
        relevant.append(_log_summary(path, expected))
    complete = [row for row in relevant if row["complete"]]
    by_run: dict[str, list[dict[str, Any]]] = {}
    for row in relevant:
        by_run.setdefault(row["run_id"], []).append(row)
    return {
        "search_roots": [str(root) for root in search_roots],
        "root_errors": root_errors,
        "scanned_log_count": len(unique_paths),
        "relevant_log_count": len(relevant),
        "complete_outcome_log_count": len(complete),
        "formal_seed_log_count": len(formal_paths),
        "formal_seed_log_paths": formal_paths,
        "relevant_logs": relevant,
        "complete_outcome_logs": complete,
        "by_run": {key: value for key, value in sorted(by_run.items())},
    }


def _log_summary(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    run_id = _run_id(path)
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
            "complete": False,
            "errors": [str(exc)],
        }
    if not isinstance(payload, list):
        return {
            "path": str(path),
            "run_id": run_id,
            "records": 0,
            "complete_outcome_records": 0,
            "candidate_count_compatible_records": 0,
            "complete": False,
            "errors": ["not_json_list"],
        }
    complete_records = 0
    candidate_count_records = 0
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            errors.append(f"record_{index}_not_dict")
            continue
        if _candidate_count(row) == expected["expected_candidates"]:
            candidate_count_records += 1
        else:
            errors.append(f"record_{index}_candidate_count_mismatch")
        outcomes = row.get("candidate_closed_loop_outcomes")
        if _outcomes_complete(
            outcomes,
            expected["expected_candidates"],
            expected["required_outcome_fields"],
        ):
            complete_records += 1
        else:
            errors.append(f"record_{index}_outcomes_incomplete")
    expected_records_per_log = expected["expected_records"] // expected["expected_logs"]
    return {
        "path": str(path),
        "run_id": run_id,
        "records": len(payload),
        "complete_outcome_records": complete_records,
        "candidate_count_compatible_records": candidate_count_records,
        "complete": (
            len(payload) == expected_records_per_log
            and complete_records == len(payload)
            and candidate_count_records == len(payload)
            and not _contains_formal_seed(str(path))
        ),
        "errors": sorted(set(errors))[:10],
    }


def _full_compatible_sources(
    scan: dict[str, Any],
    expected: dict[str, Any],
) -> list[dict[str, Any]]:
    complete_by_run: dict[str, list[dict[str, Any]]] = {}
    for row in scan["complete_outcome_logs"]:
        complete_by_run.setdefault(row["run_id"], []).append(row)
    missing = sorted(set(expected["run_ids"]) - set(complete_by_run))
    if missing:
        return []
    selected = [complete_by_run[run_id][0] for run_id in expected["run_ids"]]
    total_records = sum(row["records"] for row in selected)
    if total_records != expected["expected_records"]:
        return []
    return [
        {
            "source_type": "existing_complete_candidate_outcome_logs",
            "records": total_records,
            "logs": len(selected),
            "run_ids": expected["run_ids"],
            "paths": [row["path"] for row in selected],
        }
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorized_search",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_plan_ready", source["plan_ready"], True),
        _check_equal(
            "source_existing_source_search_authorized",
            source["existing_source_search_authorized"],
            True,
        ),
        _check_equal(
            "source_label_generation_not_authorized",
            source["outcome_label_generation_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _scope_checks(expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("expected_log_count", expected["expected_logs"], EXPECTED_LOGS),
        _check_equal("expected_record_count", expected["expected_records"], EXPECTED_RECORDS),
        _check_equal("expected_candidate_count", expected["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal("expected_run_id_count", len(expected["run_ids"]), EXPECTED_LOGS),
    ]


def _scan_checks(scan: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("search_roots_exist", scan["root_errors"], []),
        _check_equal("no_formal_seed_logs_in_search", scan["formal_seed_log_count"], 0),
        _check_equal(
            "relevant_run_ids_subset_expected",
            sorted(scan["by_run"]),
            sorted(set(scan["by_run"]) & set(expected["run_ids"])),
        ),
    ]


def _final_decision(
    rejected: bool,
    full_sources: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    compatible = bool(full_sources)
    if rejected:
        status = REJECT_STATUS
        passed = False
        next_work = None
    elif compatible:
        status = READY_STATUS
        passed = True
        next_work = AUTHORIZED_NEXT_WORK_WITH_SOURCE
    else:
        status = NO_SOURCE_STATUS
        passed = True
        next_work = AUTHORIZED_NEXT_WORK_NO_SOURCE
    return {
        "status": status,
        "passed": passed,
        "authorized_next_work": next_work,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "compatible_source_found": compatible,
        "compatible_source_review_authorized": compatible and not rejected,
        "guarded_outcome_label_pass_consideration_plan_authorized": (
            not compatible and not rejected
        ),
        "outcome_label_generation_authorized": False,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
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


def _run_id(path: Path) -> str:
    return path.parent.name


def _candidate_count(row: dict[str, Any]) -> int | None:
    direct = _optional_int(row.get("num_candidates"))
    if direct is not None:
        return direct
    payload = _dict(row.get("candidate_set_consensus_payload_logging"))
    return _optional_int(payload.get("candidate_count"))


def _outcomes_complete(
    outcomes: Any,
    expected_candidates: int,
    required_fields: list[str],
) -> bool:
    if not isinstance(outcomes, list) or len(outcomes) != expected_candidates:
        return False
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            return False
        if outcome.get("candidate_index", index) != index:
            return False
        if any(field not in outcome for field in required_fields):
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
