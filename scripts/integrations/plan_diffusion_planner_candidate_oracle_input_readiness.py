#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "scenario_evidence_matrix_predeclared"
SOURCE_NEXT_WORK = "candidate_branch_oracle_input_readiness_gate"

READY_STATUS = "candidate_branch_oracle_input_readiness_ready"
INCOMPLETE_STATUS = "candidate_branch_oracle_input_readiness_incomplete"
SOURCE_BLOCKED_STATUS = "candidate_branch_oracle_input_readiness_source_blocked"
CONFLICT_STATUS = "candidate_branch_oracle_input_readiness_source_conflict"
AUTHORIZED_NEXT_WORK = "candidate_branch_safety_cost_oracle_audit_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Candidate-branch oracle input-readiness gate. It consumes a "
            "ProofProtocol v2 scenario evidence matrix gate and the read-only "
            "candidate availability input audit. It does not run DP."
        )
    )
    parser.add_argument("--scenario_evidence_matrix_gate_json", type=Path, required=True)
    parser.add_argument("--candidate_readiness_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        scenario_evidence_matrix_gate=_load_json(args.scenario_evidence_matrix_gate_json),
        candidate_readiness=_load_json(args.candidate_readiness_json),
        label=args.label,
        paths={
            "scenario_evidence_matrix_gate_json": str(
                args.scenario_evidence_matrix_gate_json
            ),
            "candidate_readiness_json": str(args.candidate_readiness_json),
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
    scenario_evidence_matrix_gate: dict[str, Any],
    candidate_readiness: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    matrix_source = _matrix_source(scenario_evidence_matrix_gate)
    readiness_source = _readiness_source(candidate_readiness, matrix_source)
    conflicts = _source_conflicts(scenario_evidence_matrix_gate, candidate_readiness)
    decision = _decision(matrix_source, readiness_source, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_candidate_oracle_input_readiness_gate_v1",
            "label": label,
            "role": (
                "read-only gate that verifies existing outcome-labeled fixed "
                "DP candidate logs are sufficient for the general SafetyCost "
                "candidate-branch oracle"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": (
                "candidate closed-loop outcomes are required only as offline "
                "oracle labels and are forbidden as runtime selector inputs"
            ),
            "paths": paths or {},
            "math_boundary": (
                "This readiness gate audits existing finite-candidate logs. "
                "Outcome labels are offline evidence only. Current-tick proxy "
                "fields are fixed candidate constants; any later CAMP score "
                "must remain affine score_k(w)=a_k^T w with a convex "
                "simplex/CVaR/L2 robust master. This gate does not construct a "
                "DP-side classical Benders master/subproblem, dual, or cut."
            ),
        },
        "scenario_evidence_matrix_source": matrix_source,
        "candidate_readiness_source": readiness_source,
        "source_authorization_conflicts": conflicts,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    matrix = report["scenario_evidence_matrix_source"]
    readiness = report["candidate_readiness_source"]
    lines = [
        "# Candidate Oracle Input Readiness",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Scenario Evidence Matrix Source",
        "",
        f"- Status: `{matrix['status']}`",
        f"- Planned logs: `{matrix['planned_run_count']}`",
        f"- Missing required buckets: `{', '.join(matrix['missing_required_buckets']) or 'none'}`",
        f"- Formal seeds: `{', '.join(str(seed) for seed in matrix['formal_seeds']) or 'none'}`",
        "",
        "## Candidate Readiness Source",
        "",
        f"- Logs: `{readiness['logs']}`",
        f"- Records: `{readiness['records']}`",
        f"- Nonfallback records: `{readiness['nonfallback_records']}`",
        f"- Fallback records: `{readiness['fallback_records']}`",
        f"- Outcome labels ready: `{readiness['outcome_labels_ready']}`",
        f"- Current-tick proxies ready: `{readiness['current_tick_proxy_inputs_ready']}`",
        f"- Log count matches plan: `{readiness['log_count_matches_plan']}`",
        f"- Missing example keys: `{', '.join(readiness['missing_example_keys']) or 'none'}`",
        "",
        "## Decision Reasons",
        "",
    ]
    lines.extend(f"- `{reason}`" for reason in decision["reasons"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run DP, train CAMP, promote an online selector, "
            "authorize Full36, or touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _matrix_source(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    matrix = _dict(report.get("matrix_source"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    missing = list(matrix.get("missing_required_buckets") or [])
    formal = list(matrix.get("formal_seeds") or [])
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and not missing
            and not formal
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "planned_run_count": _int_or_none(matrix.get("planned_run_count")),
        "missing_required_buckets": missing,
        "formal_seeds": formal,
        "blocked_action_conflicts": conflicts,
    }


def _readiness_source(
    report: dict[str, Any],
    matrix_source: dict[str, Any],
) -> dict[str, Any]:
    readiness = _dict(report.get("readiness"))
    records = _dict(report.get("records"))
    missing = _dict(report.get("missing_examples"))
    logs = _int_or_none(records.get("logs"))
    planned_logs = matrix_source.get("planned_run_count")
    log_count_matches_plan = (
        logs is not None
        and planned_logs is not None
        and int(logs) == int(planned_logs)
    )
    return {
        "analysis_name": _get(report, "analysis", "name"),
        "candidate_availability_oracle_ready": bool(
            readiness.get("candidate_availability_oracle_ready")
        ),
        "outcome_labels_ready": bool(readiness.get("outcome_labels_ready")),
        "current_tick_proxy_inputs_ready": bool(
            readiness.get("current_tick_proxy_inputs_ready")
        ),
        "readiness_next_step": readiness.get("next_step"),
        "logs": logs,
        "records": _int_or_none(records.get("records")),
        "nonfallback_records": _int_or_none(records.get("nonfallback_records")),
        "fallback_records": _int_or_none(records.get("fallback_records")),
        "planned_logs": planned_logs,
        "log_count_matches_plan": log_count_matches_plan,
        "missing_example_keys": sorted(str(key) for key in missing),
        "passed": (
            bool(readiness.get("candidate_availability_oracle_ready"))
            and bool(readiness.get("outcome_labels_ready"))
            and bool(readiness.get("current_tick_proxy_inputs_ready"))
            and log_count_matches_plan
            and not missing
        ),
    }


def _decision(
    matrix_source: dict[str, Any],
    readiness_source: dict[str, Any],
    conflicts: list[str],
) -> dict[str, Any]:
    if conflicts:
        status = CONFLICT_STATUS
        reasons = ["source_authorizes_blocked_action"]
        next_step = "Resolve authorization conflicts before oracle input readiness."
    elif not matrix_source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        reasons = ["scenario_evidence_matrix_gate_not_ready"]
        next_step = "Repair or rerun the scenario evidence matrix gate."
    elif not readiness_source["passed"]:
        status = INCOMPLETE_STATUS
        reasons = _readiness_failure_reasons(readiness_source)
        next_step = (
            "Repair candidate outcome labels or current-tick proxy inputs before "
            "running the SafetyCost candidate-branch oracle."
        )
    else:
        status = READY_STATUS
        reasons = [
            "all_planned_logs_present",
            "candidate_closed_loop_outcomes_complete",
            "current_tick_proxy_inputs_complete",
            "oracle_input_scope_matches_scenario_matrix",
        ]
        next_step = (
            "Run the SafetyCost candidate-branch oracle audit against this "
            "nonformal matrix before any selector training, replay promotion, "
            "or formal seeds."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if status == READY_STATUS else None,
        "recommended_first_action": (
            "candidate_branch_safety_cost_oracle_audit"
            if status == READY_STATUS
            else "repair_candidate_oracle_inputs"
        ),
        "reasons": reasons,
        "next_step": next_step,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _readiness_failure_reasons(source: dict[str, Any]) -> list[str]:
    reasons = []
    if not source["candidate_availability_oracle_ready"]:
        reasons.append("candidate_availability_oracle_not_ready")
    if not source["outcome_labels_ready"]:
        reasons.append("candidate_closed_loop_outcomes_incomplete")
    if not source["current_tick_proxy_inputs_ready"]:
        reasons.append("current_tick_proxy_inputs_incomplete")
    if not source["log_count_matches_plan"]:
        reasons.append("readiness_log_count_does_not_match_scenario_matrix_plan")
    if source["missing_example_keys"]:
        reasons.append("readiness_audit_has_missing_examples")
    return reasons or ["candidate_readiness_failed_unknown_condition"]


def _source_conflicts(*reports: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    for index, report in enumerate(reports):
        final = _dict(report.get("final_decision"))
        name = str(_get(report, "analysis", "name") or f"source_{index}")
        for key in BLOCKED_ACTIONS:
            if bool(final.get(key)):
                conflicts.append(f"{name}:{key}")
    return conflicts


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get(report: dict[str, Any], *path: str) -> Any:
    current: Any = report
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
