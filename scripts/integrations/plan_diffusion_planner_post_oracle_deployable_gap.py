#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ORACLE_ANALYSIS = "dp_camp_candidate_branch_safety_cost_v1_oracle"
SOURCE_INVENTORY_STATUS = "post_source_visibility_runtime_inventory_no_new_source_paused"
SOURCE_INVENTORY_NEXT_WORK = "keep_selector_route_paused_or_scenario_objective_redesign_only"

BLOCKED_STATUS = "post_oracle_deployable_gap_blocked_by_oracle"
GAP_CLOSED_STATUS = "post_oracle_deployable_gap_closed_candidate_branch"
GAP_OPEN_STATUS = "post_oracle_deployable_gap_current_selector_misses_oracle"

GAP_OPEN_NEXT_WORK = "selector_label_weight_design_preflight_only"
GAP_CLOSED_NEXT_WORK = "deployability_latency_preflight_design_only"

DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)

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
            "Read-only post-oracle deployability gap diagnosis. It consumes a "
            "SafetyCost candidate-branch oracle report and optionally the "
            "post-source-visibility runtime inventory."
        )
    )
    parser.add_argument("--oracle_json", type=Path, required=True)
    parser.add_argument("--source_inventory_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        oracle=_load_json(args.oracle_json),
        source_inventory=(
            None if args.source_inventory_json is None else _load_json(args.source_inventory_json)
        ),
        label=args.label,
        paths={
            "oracle_json": str(args.oracle_json),
            "source_inventory_json": _path_or_none(args.source_inventory_json),
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
    oracle: dict[str, Any],
    source_inventory: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    oracle_summary = _oracle_summary(oracle)
    source_summary = _source_summary(source_inventory)
    gap = _gap_summary(oracle)
    decision = _decision(oracle_summary, source_summary, gap)
    return {
        "analysis": {
            "name": "dp_camp_post_oracle_deployable_gap_v1",
            "label": label,
            "role": (
                "read-only diagnosis between offline hard-guarded SafetyCost "
                "oracle opportunity and a legal current-tick CAMP selector"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": (
                "closed-loop outcomes are consumed only as offline oracle "
                "labels; they are forbidden as runtime selector inputs"
            ),
            "paths": paths or {},
            "math_boundary": (
                "This gate creates no atom, trains no weight, changes no DP "
                "candidate, and runs no selector. A later deployable CAMP "
                "route must use fixed current-tick finite-candidate "
                "coefficients, with score_k(w)=a_k^T w and a convex "
                "simplex/CVaR/L2 master. This is not a DP-side classical "
                "Benders decomposition because no DP master/subproblem, dual, "
                "or valid cut is constructed."
            ),
        },
        "oracle_summary": oracle_summary,
        "source_inventory_summary": source_summary,
        "gap_summary": gap,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    oracle = report["oracle_summary"]
    source = report["source_inventory_summary"]
    gap = report["gap_summary"]
    lines = [
        "# Post-Oracle Deployability Gap",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Oracle Summary",
        "",
        f"- Logs: `{oracle['logs']}`",
        f"- Records: `{oracle['records']}`",
        f"- Formal seed logs: `{oracle['formal_seed_logs']}`",
        f"- Opportunity gate passed: `{oracle['opportunity_gate_passed']}`",
        f"- Missing required buckets: `{', '.join(oracle['missing_required_buckets']) or 'none'}`",
        "",
        "## Gap Summary",
        "",
        f"- CAMP minus Top-1 mean: `{gap['overall']['camp_minus_top1_mean']}`",
        f"- CAMP minus Top-1 CI high: `{gap['overall']['camp_minus_top1_ci_high']}`",
        f"- CAMP minus hard-guarded oracle mean: `{gap['overall']['camp_minus_hard_guarded_oracle_mean']}`",
        f"- CAMP minus hard-guarded oracle CI high: `{gap['overall']['camp_minus_hard_guarded_oracle_ci_high']}`",
        f"- Hard-guarded oracle available rate: `{gap['overall']['hard_guarded_oracle_available_rate']}`",
        f"- CAMP matches hard-guarded oracle rate: `{gap['overall']['camp_matches_hard_guarded_oracle_rate']}`",
        f"- Fallback all-infeasible rate: `{gap['overall']['fallback_all_infeasible_rate']}`",
        "",
        "## Bucket Gaps",
        "",
        "| Bucket | Records | CAMP-vs-Top1 CI high | CAMP-vs-Oracle CI high | Gap open |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in gap["by_bucket"]:
        lines.append(
            f"| `{row['bucket']}` | `{row['records']}` | "
            f"`{row['camp_minus_top1_ci_high']}` | "
            f"`{row['camp_minus_hard_guarded_oracle_ci_high']}` | "
            f"`{row['hard_guarded_oracle_gap_open']}` |"
        )
    lines.extend(
        [
            "",
            "## Failure Modes",
            "",
        ]
    )
    for name, value in gap["failure_mode_counts"].items():
        lines.append(f"- `{name}` = `{value}`")
    lines.extend(
        [
            "",
            "## Source Inventory",
            "",
            f"- Supplied: `{source['supplied']}`",
            f"- Status: `{source['status']}`",
            f"- No new runtime source: `{source['no_new_runtime_source']}`",
            "",
            "## Decision Reasons",
            "",
        ]
    )
    lines.extend(f"- `{reason}`" for reason in decision["reasons"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not authorize replay, CAMP retraining, online selector "
            "promotion, Full36, formal seeds, DP modification, or a classical "
            "Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _oracle_summary(report: dict[str, Any]) -> dict[str, Any]:
    formal_seed_logs = int(_get(report, "logs", "formal_seed_logs") or 0)
    missing = _string_list(_get(report, "coverage_gaps", "missing_required_buckets"))
    opportunity_gate_passed = bool(_get(report, "opportunity_gate", "passed"))
    by_bucket = _bucket_rows(report)
    required_failures = [
        row["bucket"]
        for row in by_bucket
        if row["bucket"] in DEFAULT_REQUIRED_BUCKETS
        and not _negative(row["hard_guarded_oracle_minus_top1_ci_high"])
    ]
    analysis_name = _get(report, "analysis", "name")
    passed = (
        analysis_name == ORACLE_ANALYSIS
        and opportunity_gate_passed
        and formal_seed_logs == 0
        and not missing
        and not required_failures
    )
    return {
        "analysis_name": analysis_name,
        "passed": passed,
        "opportunity_gate_passed": opportunity_gate_passed,
        "logs": _get(report, "logs", "total"),
        "records": _get(report, "records", "total"),
        "formal_seed_logs": formal_seed_logs,
        "missing_required_buckets": missing,
        "required_bucket_oracle_failures": required_failures,
    }


def _source_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {
            "supplied": False,
            "status": None,
            "passed": True,
            "no_new_runtime_source": None,
            "new_runtime_source_candidates": [],
        }
    final = _dict(report.get("final_decision"))
    new_candidates = _string_list(final.get("new_runtime_source_candidates"))
    return {
        "supplied": True,
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_INVENTORY_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == SOURCE_INVENTORY_NEXT_WORK
            and not new_candidates
        ),
        "no_new_runtime_source": not new_candidates,
        "new_runtime_source_candidates": new_candidates,
    }


def _gap_summary(report: dict[str, Any]) -> dict[str, Any]:
    overall_raw = _dict(report.get("overall"))
    by_bucket = _bucket_rows(report)
    gap_failures = [
        row["bucket"]
        for row in by_bucket
        if row["bucket"] in DEFAULT_REQUIRED_BUCKETS
        and row["hard_guarded_oracle_gap_open"]
    ]
    top1_failures = [
        row["bucket"]
        for row in by_bucket
        if row["bucket"] in DEFAULT_REQUIRED_BUCKETS
        and not _negative(row["camp_minus_top1_ci_high"])
    ]
    cvar_failures = [
        row["bucket"]
        for row in by_bucket
        if row["bucket"] in DEFAULT_REQUIRED_BUCKETS
        and not _nonpositive(row["cvar90_camp_minus_top1_ci_high"])
    ]
    failure_counts = {
        str(key): int(value)
        for key, value in _dict(
            _get(report, "opportunity_diagnostics", "failure_mode_counts")
            or overall_raw.get("failure_mode_counts")
        ).items()
    }
    failure_rates = {
        str(key): _number(value)
        for key, value in _dict(
            _get(report, "opportunity_diagnostics", "failure_mode_rates")
            or overall_raw.get("failure_mode_rates")
        ).items()
    }
    coverage = _dict(overall_raw.get("candidate_pool_coverage"))
    overall = _metric_row("overall", overall_raw)
    return {
        "overall": overall,
        "by_bucket": by_bucket,
        "hard_guarded_oracle_gap_bucket_failures": gap_failures,
        "camp_top1_bucket_failures": top1_failures,
        "camp_cvar90_bucket_failures": cvar_failures,
        "failure_mode_counts": failure_counts,
        "failure_mode_rates": failure_rates,
        "candidate_pool_coverage": coverage,
        "diagnostic_blockers": _diagnostic_blockers(
            overall=overall,
            gap_failures=gap_failures,
            top1_failures=top1_failures,
            cvar_failures=cvar_failures,
            failure_counts=failure_counts,
        ),
        "current_selector_gap_closed": (
            _nonpositive(overall["camp_minus_hard_guarded_oracle_ci_high"])
            and not gap_failures
        ),
    }


def _decision(
    oracle: dict[str, Any],
    source: dict[str, Any],
    gap: dict[str, Any],
) -> dict[str, Any]:
    if not oracle["passed"]:
        status = BLOCKED_STATUS
        passed = False
        authorized_next = None
        next_step = "Refresh or repair the SafetyCost candidate-branch oracle first."
        reasons = ["oracle_gate_not_ready"]
    elif not source["passed"]:
        status = "post_oracle_deployable_gap_blocked_by_source_inventory"
        passed = False
        authorized_next = None
        next_step = "Refresh or repair the post-source-visibility runtime inventory."
        reasons = ["source_inventory_not_ready"]
    elif gap["current_selector_gap_closed"]:
        status = GAP_CLOSED_STATUS
        passed = True
        authorized_next = GAP_CLOSED_NEXT_WORK
        next_step = (
            "Predeclare deployability, latency, fallback, and comfort gates before "
            "any tiny paired nonformal smoke."
        )
        reasons = ["current_selector_closes_hard_guarded_oracle_gap_candidate_branch"]
    else:
        status = GAP_OPEN_STATUS
        passed = True
        authorized_next = GAP_OPEN_NEXT_WORK
        next_step = (
            "Predeclare an outcome-free selector label/weight-design gate using "
            "the hard-guarded oracle only as offline supervision. Do not train or "
            "run closed-loop smoke yet."
        )
        reasons = [
            "fixed_candidate_pool_has_oracle_opportunity",
            "current_selector_does_not_close_hard_guarded_oracle_gap",
            *gap["diagnostic_blockers"],
        ]
        if source["supplied"] and source["no_new_runtime_source"]:
            reasons.append("no_new_runtime_source_available_from_latest_inventory")
    return {
        "status": status,
        "passed": passed,
        "authorized_next_work": authorized_next,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "training_execution_authorized": False,
        "oracle_passed": oracle["passed"],
        "source_inventory_passed": source["passed"],
        "current_selector_gap_closed": gap["current_selector_gap_closed"],
        "reasons": reasons,
        "next_step": next_step,
    }


def _diagnostic_blockers(
    *,
    overall: dict[str, Any],
    gap_failures: list[str],
    top1_failures: list[str],
    cvar_failures: list[str],
    failure_counts: dict[str, int],
) -> list[str]:
    blockers: list[str] = []
    if gap_failures:
        blockers.append("hard_guarded_oracle_gap_bucket_failures")
    if top1_failures:
        blockers.append("camp_top1_required_bucket_failures")
    if cvar_failures:
        blockers.append("camp_cvar90_required_bucket_failures")
    if int(failure_counts.get("fallback_all_infeasible", 0)) > 0:
        blockers.append("fallback_all_infeasible_records_present")
    if int(failure_counts.get("camp_not_hard_guarded_oracle_when_available", 0)) > 0:
        blockers.append("camp_misses_available_hard_guarded_oracle_records")
    if not _negative(overall["camp_minus_top1_ci_high"]):
        blockers.append("overall_camp_top1_ci_not_strictly_negative")
    if not _nonpositive(overall["cvar90_camp_minus_top1_ci_high"]):
        blockers.append("overall_camp_cvar90_not_nonpositive")
    return blockers


def _bucket_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for entry in report.get("by_bucket") or []:
        if isinstance(entry, dict):
            rows.append(_metric_row(str(entry.get("bucket") or "<unknown>"), entry))
    return rows


def _metric_row(bucket: str, entry: dict[str, Any]) -> dict[str, Any]:
    rates = _dict(entry.get("record_rates"))
    coverage = _dict(entry.get("candidate_pool_coverage"))
    return {
        "bucket": bucket,
        "records": entry.get("records"),
        "logs": entry.get("logs"),
        "camp_minus_top1_mean": _ci(entry, "camp_minus_top1", "mean"),
        "camp_minus_top1_ci_high": _ci(entry, "camp_minus_top1", "ci95_high"),
        "cvar90_camp_minus_top1_ci_high": _cvar(
            entry, "camp_minus_top1", "ci95_high"
        ),
        "hard_guarded_oracle_minus_top1_ci_high": _ci(
            entry, "hard_guarded_oracle_minus_top1", "ci95_high"
        ),
        "camp_minus_hard_guarded_oracle_mean": _ci(
            entry, "camp_minus_hard_guarded_oracle", "mean"
        ),
        "camp_minus_hard_guarded_oracle_ci_high": _ci(
            entry, "camp_minus_hard_guarded_oracle", "ci95_high"
        ),
        "hard_guarded_oracle_available_rate": _first_not_none(
            rates.get("hard_guarded_oracle_available"),
            coverage.get("hard_guarded_oracle_available_rate"),
        ),
        "hard_guarded_oracle_beats_top1_rate": rates.get(
            "hard_guarded_oracle_beats_top1"
        ),
        "camp_matches_hard_guarded_oracle_rate": rates.get(
            "camp_matches_hard_guarded_oracle"
        ),
        "fallback_all_infeasible_rate": _first_not_none(
            coverage.get("fallback_all_infeasible_rate"),
            _safe_rate(entry.get("fallback_all_infeasible_records"), entry.get("records")),
        ),
        "hard_guarded_oracle_gap_open": not _nonpositive(
            _ci(entry, "camp_minus_hard_guarded_oracle", "ci95_high")
        ),
    }


def _ci(entry: dict[str, Any], key: str, field: str) -> float | None:
    return _number(_get(entry, "run_level_delta_ci", key, field))


def _cvar(entry: dict[str, Any], key: str, field: str) -> float | None:
    return _number(_get(entry, "run_level_cvar90_delta", key, field))


def _safe_rate(numerator: Any, denominator: Any) -> float | None:
    numerator = _number(numerator)
    denominator = _number(denominator)
    if numerator is None or denominator is None or denominator == 0.0:
        return None
    return numerator / denominator


def _negative(value: Any) -> bool:
    value = _number(value)
    return value is not None and value < 0.0


def _nonpositive(value: Any) -> bool:
    value = _number(value)
    return value is not None and value <= 0.0


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _get(report: dict[str, Any], *path: str) -> Any:
    current: Any = report
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


if __name__ == "__main__":
    main()
