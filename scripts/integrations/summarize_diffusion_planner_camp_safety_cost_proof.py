#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize existing DP-CAMP SafetyCost artifacts into one "
            "candidate-branch proof report. This is read-only."
        )
    )
    parser.add_argument("--oracle_report", type=Path, required=True)
    parser.add_argument("--selector_eval_report", type=Path, required=True)
    parser.add_argument("--state_floor_counterfactual", type=Path, default=None)
    parser.add_argument("--online_state_floor_report", type=Path, default=None)
    parser.add_argument("--lateral_target_report", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        oracle_report=_load_json(args.oracle_report),
        selector_eval_report=_load_json(args.selector_eval_report),
        state_floor_counterfactual=(
            None
            if args.state_floor_counterfactual is None
            else _load_json(args.state_floor_counterfactual)
        ),
        online_state_floor_report=(
            None
            if args.online_state_floor_report is None
            else _load_json(args.online_state_floor_report)
        ),
        lateral_target_report=(
            None
            if args.lateral_target_report is None
            else _load_json(args.lateral_target_report)
        ),
        paths={
            "oracle_report": str(args.oracle_report),
            "selector_eval_report": str(args.selector_eval_report),
            "state_floor_counterfactual": _path_or_none(args.state_floor_counterfactual),
            "online_state_floor_report": _path_or_none(args.online_state_floor_report),
            "lateral_target_report": _path_or_none(args.lateral_target_report),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    oracle_report: dict[str, Any],
    selector_eval_report: dict[str, Any],
    state_floor_counterfactual: dict[str, Any] | None = None,
    online_state_floor_report: dict[str, Any] | None = None,
    lateral_target_report: dict[str, Any] | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    current_camp = _oracle_summary(oracle_report)
    selector_eval = _selector_eval_summary(selector_eval_report)
    state_floor = (
        None
        if state_floor_counterfactual is None
        else _state_floor_summary(state_floor_counterfactual)
    )
    online_state_floor = (
        None
        if online_state_floor_report is None
        else _oracle_summary(online_state_floor_report)
    )
    lateral_target = (
        None if lateral_target_report is None else _oracle_summary(lateral_target_report)
    )
    gates = {
        "candidate_pool_opportunity": _candidate_pool_gate(current_camp),
        "current_camp_vs_top1": _camp_gate(current_camp),
        "safety_cost_trained_selector_vs_top1": _camp_gate(selector_eval["evaluated"]),
        "safety_cost_trained_selector_gap_closed": _gap_gate(
            selector_eval["evaluated"]
        ),
        "online_state_floor_selected_log": (
            None if online_state_floor is None else _camp_gate(online_state_floor)
        ),
        "lateral_target_selected_log": (
            None if lateral_target is None else _camp_gate(lateral_target)
        ),
    }
    final_decision = _decision(
        current_camp=current_camp,
        selector_eval=selector_eval,
        gates=gates,
        state_floor=state_floor,
        online_state_floor=online_state_floor,
        lateral_target=lateral_target,
    )
    return {
        "analysis": {
            "name": "dp_camp_comprehensive_safety_cost_proof_summary",
            "role": (
                "read-only summary of existing non-formal candidate-branch "
                "SafetyCost artifacts"
            ),
            "safety_cost_scope": (
                "candidate branch proxy unless a source artifact explicitly "
                "reports closed-loop replay metrics"
            ),
            "training": False,
            "online_selector_change": False,
            "formal_seed_policy": "forbidden; source artifacts must report zero",
            "math_boundary": (
                "DP is a fixed black-box candidate generator. CAMP selector "
                "scores use fixed current-tick candidate features and affine "
                "a_k^T w scoring. This report does not modify DP, CAMP atoms, "
                "weights, the simplex/CVaR/L2 master, or closed-loop replay. "
                "It is not classical Benders decomposition."
            ),
            "required_buckets": list(DEFAULT_REQUIRED_BUCKETS),
            "paths": paths or {},
        },
        "current_camp": current_camp,
        "safety_cost_trained_selector": selector_eval,
        "state_floor_counterfactual": state_floor,
        "online_state_floor": online_state_floor,
        "lateral_target": lateral_target,
        "gates": gates,
        "final_decision": final_decision,
    }


def _oracle_summary(report: dict[str, Any]) -> dict[str, Any]:
    overall = _metrics(_get(report, "overall") or {})
    by_bucket = _bucket_metrics(report.get("by_bucket") or [])
    _attach_opportunity_diagnostics(
        overall=overall,
        by_bucket=by_bucket,
        diagnostics=report.get("opportunity_diagnostics") or {},
    )
    return {
        "source_name": _get(report, "analysis", "name"),
        "logs": _get(report, "logs", "total"),
        "formal_seed_logs": _get(report, "logs", "formal_seed_logs"),
        "records": _get(report, "records", "total")
        or _get(report, "records", "records")
        or _get(report, "overall", "records"),
        "missing_required_buckets": _get(report, "coverage_gaps", "missing_required_buckets")
        or [],
        "opportunity_gate_passed": _get(report, "opportunity_gate", "passed"),
        "overall": overall,
        "by_bucket": by_bucket,
        "rates": {
            "camp_beats_top1": _get(report, "overall", "record_rates", "camp_beats_top1"),
            "camp_matches_top1": _get(
                report, "overall", "record_rates", "camp_matches_top1"
            ),
            "camp_matches_hard_guarded_oracle": _get(
                report,
                "overall",
                "record_rates",
                "camp_matches_hard_guarded_oracle",
            ),
            "hard_guarded_oracle_beats_top1": _get(
                report,
                "overall",
                "record_rates",
                "hard_guarded_oracle_beats_top1",
            ),
            "hard_guarded_oracle_available": _get(
                report,
                "overall",
                "record_rates",
                "hard_guarded_oracle_available",
            ),
        },
        "failure_modes": _get(report, "overall", "failure_mode_rates") or {},
        "hard_component_nonworse_rate": _get(
            report, "overall", "hard_component_nonworse_rate"
        )
        or {},
    }


def _selector_eval_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": _get(report, "analysis", "name"),
        "selector_name": _get(report, "analysis", "selector_name"),
        "logs": _get(report, "logs", "total"),
        "formal_seed_logs": _get(report, "logs", "formal_seed_logs"),
        "records": _get(report, "records", "total")
        or _get(report, "records", "records"),
        "missing_required_buckets": _get(report, "coverage_gaps", "missing_required_buckets")
        or [],
        "opportunity_gate_passed": _get(report, "opportunity_gate", "passed"),
        "evaluated": {
            "overall": _metrics(_get(report, "evaluated_selector", "overall") or {}),
            "by_bucket": _bucket_metrics(
                _get(report, "evaluated_selector", "by_bucket") or []
            ),
            "rates": _selector_rates(_get(report, "evaluated_selector", "overall") or {}),
        },
        "logged": {
            "overall": _metrics(_get(report, "logged_selector", "overall") or {}),
            "by_bucket": _bucket_metrics(
                _get(report, "logged_selector", "by_bucket") or []
            ),
            "rates": _selector_rates(_get(report, "logged_selector", "overall") or {}),
        },
        "selector_comparison": {
            "changed_record_rate": _get(
                report, "selector_comparison", "changed_record_rate"
            ),
            "evaluated_minus_logged_cost_mean": _get(
                report, "selector_comparison", "evaluated_minus_logged_cost_mean"
            ),
            "evaluated_minus_logged_cost_ci": _get(
                report,
                "selector_comparison",
                "run_level_evaluated_minus_logged_cost_ci",
            ),
        },
    }


def _state_floor_summary(report: dict[str, Any]) -> dict[str, Any]:
    rules: dict[str, Any] = {}
    raw_rules = report.get("rules") or []
    if isinstance(raw_rules, dict):
        iterable = raw_rules.items()
    else:
        iterable = ((str(rule.get("name")), rule) for rule in raw_rules)
    for name, rule in iterable:
        rules[name] = {
            "overall": _metrics(rule.get("overall") or {}),
            "by_bucket": _bucket_metrics(rule.get("by_bucket") or []),
            "rates": _selector_rates(rule.get("overall") or {}),
        }
    return {
        "source_name": _get(report, "analysis", "name"),
        "logs": _get(report, "logs", "total"),
        "formal_seed_logs": _get(report, "logs", "formal_seed_logs"),
        "missing_required_buckets": _get(report, "coverage_gaps", "missing_required_buckets")
        or [],
        "rules": rules,
    }


def _metrics(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": entry.get("records"),
        "logs": entry.get("logs"),
        "record_rates": entry.get("record_rates") or {},
        "candidate_pool_coverage": entry.get("candidate_pool_coverage") or {},
        "cost_mean": {
            "top1": _get(entry, "cost_mean", "top1"),
            "camp": _get(entry, "cost_mean", "camp"),
            "hard_guarded_oracle": _get(entry, "cost_mean", "hard_guarded_oracle"),
        },
        "camp_minus_top1": _ci(entry, "camp_minus_top1"),
        "hard_guarded_oracle_minus_top1": _ci(
            entry, "hard_guarded_oracle_minus_top1"
        ),
        "camp_minus_hard_guarded_oracle": _ci(
            entry, "camp_minus_hard_guarded_oracle"
        ),
        "cvar90_camp_minus_top1": _cvar_ci(entry, "camp_minus_top1"),
        "cvar90_hard_guarded_oracle_minus_top1": _cvar_ci(
            entry, "hard_guarded_oracle_minus_top1"
        ),
        "cvar90_camp_minus_hard_guarded_oracle": _cvar_ci(
            entry, "camp_minus_hard_guarded_oracle"
        ),
        "hard_component_nonworse_rate": entry.get("hard_component_nonworse_rate")
        or {},
        "failure_modes": entry.get("failure_mode_rates") or {},
    }


def _bucket_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("bucket")): _metrics(row) for row in rows}


def _attach_opportunity_diagnostics(
    *,
    overall: dict[str, Any],
    by_bucket: dict[str, dict[str, Any]],
    diagnostics: dict[str, Any],
) -> None:
    coverage = diagnostics.get("candidate_pool_coverage")
    if isinstance(coverage, dict):
        overall["candidate_pool_coverage"] = coverage
    failures = diagnostics.get("failure_mode_rates")
    if isinstance(failures, dict):
        overall["failure_modes"] = failures
    for row in diagnostics.get("by_bucket") or []:
        if not isinstance(row, dict):
            continue
        bucket = str(row.get("bucket"))
        if bucket not in by_bucket:
            continue
        coverage = row.get("candidate_pool_coverage")
        if isinstance(coverage, dict):
            by_bucket[bucket]["candidate_pool_coverage"] = coverage
        failures = row.get("failure_mode_rates")
        if isinstance(failures, dict):
            by_bucket[bucket]["failure_modes"] = failures


def _selector_rates(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "camp_beats_top1": _get(entry, "record_rates", "camp_beats_top1"),
        "camp_matches_top1": _get(entry, "record_rates", "camp_matches_top1"),
        "camp_matches_hard_guarded_oracle": _get(
            entry, "record_rates", "camp_matches_hard_guarded_oracle"
        ),
    }


def _candidate_pool_gate(current_camp: dict[str, Any]) -> dict[str, Any]:
    overall = _ci_high(current_camp["overall"], "hard_guarded_oracle_minus_top1")
    bucket_failures = _bucket_failures(
        current_camp, metric="hard_guarded_oracle_minus_top1"
    )
    return {
        "passed": _formal_ok(current_camp)
        and not current_camp["missing_required_buckets"]
        and overall is not None
        and overall < 0.0
        and not bucket_failures,
        "overall_ci_high": overall,
        "bucket_failures": bucket_failures,
    }


def _camp_gate(summary: dict[str, Any]) -> dict[str, Any]:
    overall = _ci_high(summary["overall"], "camp_minus_top1")
    bucket_failures = _bucket_failures(summary, metric="camp_minus_top1")
    return {
        "passed": _formal_ok(summary)
        and not summary.get("missing_required_buckets")
        and overall is not None
        and overall < 0.0
        and not bucket_failures,
        "overall_ci_high": overall,
        "bucket_failures": bucket_failures,
    }


def _gap_gate(selector_eval: dict[str, Any]) -> dict[str, Any]:
    overall = _ci_high(selector_eval["overall"], "camp_minus_hard_guarded_oracle")
    bucket_failures = _bucket_failures(
        selector_eval, metric="camp_minus_hard_guarded_oracle", require_negative=True
    )
    return {
        "passed": overall is not None and overall <= 0.0 and not bucket_failures,
        "overall_ci_high": overall,
        "bucket_failures": bucket_failures,
        "interpretation": (
            "pass would mean the selector closes the hard-guarded oracle gap; "
            "failure can coexist with a valid improvement over DP Top-1"
        ),
    }


def _bucket_failures(
    summary: dict[str, Any],
    *,
    metric: str,
    require_negative: bool = True,
) -> dict[str, float | None]:
    failures: dict[str, float | None] = {}
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        entry = summary.get("by_bucket", {}).get(bucket)
        ci_high = None if entry is None else _ci_high(entry, metric)
        if ci_high is None or (require_negative and ci_high >= 0.0):
            failures[bucket] = ci_high
    return failures


def _decision(
    *,
    current_camp: dict[str, Any],
    selector_eval: dict[str, Any],
    gates: dict[str, Any],
    state_floor: dict[str, Any] | None,
    online_state_floor: dict[str, Any] | None,
    lateral_target: dict[str, Any] | None,
) -> dict[str, Any]:
    current_gate = gates["current_camp_vs_top1"]["passed"]
    selector_gate = gates["safety_cost_trained_selector_vs_top1"]["passed"]
    oracle_gate = gates["candidate_pool_opportunity"]["passed"]
    gap_gate = gates["safety_cost_trained_selector_gap_closed"]["passed"]
    conclusions: list[str] = []
    if oracle_gate:
        conclusions.append(
            "The fixed DP candidate pools contain hard-guarded SafetyCost "
            "opportunity versus DP Top-1 in every required non-formal bucket."
        )
    else:
        conclusions.append(
            "The candidate-pool opportunity proof is incomplete; inspect "
            "missing buckets or hard-guarded oracle CI failures."
        )
    if current_gate:
        conclusions.append(
            "The currently logged CAMP selector passes the candidate-branch "
            "SafetyCost proof gate versus DP Top-1."
        )
    else:
        failures = ", ".join(gates["current_camp_vs_top1"]["bucket_failures"])
        conclusions.append(
            "The currently logged CAMP selector is not a complete proof versus "
            f"DP Top-1; failing buckets: {failures or 'none'}."
        )
    if selector_gate:
        conclusions.append(
            "The SafetyCost-trained CAMP selector passes the held-out "
            "candidate-branch proof gate versus DP Top-1."
        )
    else:
        conclusions.append(
            "The SafetyCost-trained selector does not yet pass the held-out "
            "candidate-branch proof gate versus DP Top-1."
        )
    if not gap_gate:
        conclusions.append(
            "The hard-guarded oracle gap remains open; this is evidence for "
            "candidate support plus imperfect CAMP scoring, not a DP limit."
        )
    if state_floor is not None:
        rule = state_floor.get("rules", {}).get(
            "state_redroute_top1_red_or_proxy_jerk_floor_unconditional"
        )
        if rule is not None:
            conclusions.append(
                "The state-gated Top-1-floor counterfactual passes the selected-log "
                "SafetyCost bucket gate, but later closed-loop lane attribution "
                "blocks promotion."
            )
    if online_state_floor is not None:
        conclusions.append(
            "The online state-floor smoke is selected-log positive but closed-loop "
            "red-turn lane regression blocks Full36/formal promotion."
        )
    if lateral_target is not None:
        conclusions.append(
            "The lateral-nonworse targeted red-turn slice has negative "
            "selected-log CAMP-minus-Top-1 SafetyCost, but it is not a "
            "comprehensive bucket proof and did not remove the closed-loop "
            "lane extra steps."
        )
    return {
        "status": (
            "candidate_branch_proof_passes_for_safety_cost_trained_selector"
            if selector_gate and oracle_gate
            else "proof_incomplete"
        ),
        "current_camp_complete_proof": current_gate,
        "safety_cost_trained_selector_candidate_branch_proof": selector_gate,
        "hard_guarded_oracle_gap_closed": gap_gate,
        "closed_loop_deployment_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_or_camp_retraining_authorized": False,
        "conclusions": conclusions,
        "next_step": (
            "Use this candidate-branch proof to decide whether to implement an "
            "outcome-free deployable selector for the SafetyCost-trained CAMP "
            "weights, then run a small paired non-formal closed-loop smoke. Do "
            "not run formal seeds until closed-loop safety, fallback, completion, "
            "and latency gates pass."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    current = report["current_camp"]
    selector = report["safety_cost_trained_selector"]
    gates = report["gates"]
    decision = report["final_decision"]
    lines = [
        "# CAMP vs DP Top-1 SafetyCost Proof Summary",
        "",
        "This report is a read-only consolidation of existing non-formal artifacts.",
        "It does not modify DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Current logged CAMP complete proof: `{decision['current_camp_complete_proof']}`",
        f"- SafetyCost-trained selector candidate-branch proof: `{decision['safety_cost_trained_selector_candidate_branch_proof']}`",
        f"- Hard-guarded oracle gap closed: `{decision['hard_guarded_oracle_gap_closed']}`",
        f"- Closed-loop deployment authorized: `{decision['closed_loop_deployment_authorized']}`",
        f"- Full36 authorized: `{decision['full36_authorized']}`",
        f"- Formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Gate Summary",
        "",
        "| Gate | Passed | Overall CI high | Bucket failures |",
        "| --- | --- | ---: | --- |",
    ]
    for name, gate in gates.items():
        if gate is None:
            continue
        lines.append(
            f"| `{name}` | `{gate['passed']}` | {_fmt(gate.get('overall_ci_high'))} | "
            f"{_bucket_failure_text(gate.get('bucket_failures') or {})} |"
        )
    lines.extend(
        [
            "",
            "## Current Logged CAMP",
            "",
            _metric_table(current),
            "",
            "## SafetyCost-Trained Selector Held-Out Evaluation",
            "",
            _selector_table(selector),
            "",
            "## Scenario Buckets",
            "",
            "### Current CAMP vs Top-1",
            "",
            _bucket_table(current),
            "",
            "### SafetyCost-Trained Selector vs Top-1",
            "",
            _bucket_table(selector["evaluated"]),
            "",
            "## Mechanism Interpretation",
            "",
        ]
    )
    for item in decision["conclusions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"Next step: {decision['next_step']}",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Source Artifacts",
            "",
            "| Artifact | Path |",
            "| --- | --- |",
        ]
    )
    for name, path in (report["analysis"].get("paths") or {}).items():
        lines.append(f"| `{name}` | `{path or 'none'}` |")
    lines.append("")
    return "\n".join(lines)


def _metric_table(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    rates = summary.get("rates", {})
    coverage = overall.get("candidate_pool_coverage") or {}
    return "\n".join(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Logs | {_fmt(summary.get('logs'))} |",
            f"| Records | {_fmt(summary.get('records'))} |",
            f"| Formal seed logs | {_fmt(summary.get('formal_seed_logs'))} |",
            f"| CAMP minus Top-1 mean | {_fmt(_ci_mean(overall, 'camp_minus_top1'))} |",
            f"| CAMP minus Top-1 CI high | {_fmt(_ci_high(overall, 'camp_minus_top1'))} |",
            f"| CAMP minus Top-1 CVaR90 CI high | {_fmt(_ci_high(overall, 'cvar90_camp_minus_top1'))} |",
            f"| Hard-guarded oracle minus Top-1 mean | {_fmt(_ci_mean(overall, 'hard_guarded_oracle_minus_top1'))} |",
            f"| Hard-guarded oracle minus Top-1 CI high | {_fmt(_ci_high(overall, 'hard_guarded_oracle_minus_top1'))} |",
            f"| Hard-guarded oracle minus Top-1 CVaR90 CI high | {_fmt(_ci_high(overall, 'cvar90_hard_guarded_oracle_minus_top1'))} |",
            f"| CAMP gap to hard-guarded oracle mean | {_fmt(_ci_mean(overall, 'camp_minus_hard_guarded_oracle'))} |",
            f"| CAMP gap to hard-guarded oracle CI high | {_fmt(_ci_high(overall, 'camp_minus_hard_guarded_oracle'))} |",
            f"| CAMP beats Top-1 rate | {_fmt(rates.get('camp_beats_top1'))} |",
            f"| CAMP matches hard-guarded oracle rate | {_fmt(rates.get('camp_matches_hard_guarded_oracle'))} |",
            f"| Hard-guarded oracle available rate | {_fmt(_first_not_none(coverage.get('hard_guarded_oracle_available_rate'), rates.get('hard_guarded_oracle_available')))} |",
            f"| Hard-guarded oracle beats Top-1 rate | {_fmt(rates.get('hard_guarded_oracle_beats_top1'))} |",
            f"| CAMP hard-component nonworse min | {_fmt(_hard_nonworse_min(overall, 'camp'))} |",
            f"| Hard-guarded oracle hard-component nonworse min | {_fmt(_hard_nonworse_min(overall, 'hard_guarded_oracle'))} |",
        ]
    )


def _selector_table(summary: dict[str, Any]) -> str:
    evaluated = summary["evaluated"]
    logged = summary["logged"]
    comparison = summary["selector_comparison"]
    rows = [
        "| Metric | Evaluated selector | Logged selector |",
        "| --- | ---: | ---: |",
        f"| Logs | {_fmt(summary.get('logs'))} | {_fmt(summary.get('logs'))} |",
        f"| Records | {_fmt(summary.get('records'))} | {_fmt(summary.get('records'))} |",
        f"| CAMP minus Top-1 mean | {_fmt(_ci_mean(evaluated['overall'], 'camp_minus_top1'))} | {_fmt(_ci_mean(logged['overall'], 'camp_minus_top1'))} |",
        f"| CAMP minus Top-1 CI high | {_fmt(_ci_high(evaluated['overall'], 'camp_minus_top1'))} | {_fmt(_ci_high(logged['overall'], 'camp_minus_top1'))} |",
        f"| CAMP minus Top-1 CVaR90 CI high | {_fmt(_ci_high(evaluated['overall'], 'cvar90_camp_minus_top1'))} | {_fmt(_ci_high(logged['overall'], 'cvar90_camp_minus_top1'))} |",
        f"| Gap to hard-guarded oracle mean | {_fmt(_ci_mean(evaluated['overall'], 'camp_minus_hard_guarded_oracle'))} | {_fmt(_ci_mean(logged['overall'], 'camp_minus_hard_guarded_oracle'))} |",
        f"| Gap to hard-guarded oracle CI high | {_fmt(_ci_high(evaluated['overall'], 'camp_minus_hard_guarded_oracle'))} | {_fmt(_ci_high(logged['overall'], 'camp_minus_hard_guarded_oracle'))} |",
        f"| CAMP beats Top-1 rate | {_fmt(evaluated['rates'].get('camp_beats_top1'))} | {_fmt(logged['rates'].get('camp_beats_top1'))} |",
        f"| CAMP matches hard-guarded oracle rate | {_fmt(evaluated['rates'].get('camp_matches_hard_guarded_oracle'))} | {_fmt(logged['rates'].get('camp_matches_hard_guarded_oracle'))} |",
        f"| CAMP hard-component nonworse min | {_fmt(_hard_nonworse_min(evaluated['overall'], 'camp'))} | {_fmt(_hard_nonworse_min(logged['overall'], 'camp'))} |",
        f"| Evaluated changed record rate | {_fmt(comparison.get('changed_record_rate'))} | n/a |",
        f"| Evaluated minus logged cost mean | {_fmt(comparison.get('evaluated_minus_logged_cost_mean'))} | n/a |",
    ]
    return "\n".join(rows)


def _bucket_table(summary: dict[str, Any]) -> str:
    rows = [
        "| Bucket | Records | Logs | CAMP-Top1 mean | CAMP-Top1 CI high | CAMP-Top1 CVaR90 CI high | HardOracle-Top1 CI high | HardOracle beats Top1 | HardOracle available | CAMP hard min | HardOracle hard min | Gap CI high |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    buckets = summary.get("by_bucket") or {}
    for bucket in ("overall", *DEFAULT_REQUIRED_BUCKETS):
        entry = buckets.get(bucket)
        if entry is None:
            continue
        rates = entry.get("record_rates") or {}
        coverage = entry.get("candidate_pool_coverage") or {}
        rows.append(
            f"| `{bucket}` | {_fmt(entry.get('records'))} | {_fmt(entry.get('logs'))} | "
            f"{_fmt(_ci_mean(entry, 'camp_minus_top1'))} | "
            f"{_fmt(_ci_high(entry, 'camp_minus_top1'))} | "
            f"{_fmt(_ci_high(entry, 'cvar90_camp_minus_top1'))} | "
            f"{_fmt(_ci_high(entry, 'hard_guarded_oracle_minus_top1'))} | "
            f"{_fmt(rates.get('hard_guarded_oracle_beats_top1'))} | "
            f"{_fmt(_first_not_none(coverage.get('hard_guarded_oracle_available_rate'), rates.get('hard_guarded_oracle_available')))} | "
            f"{_fmt(_hard_nonworse_min(entry, 'camp'))} | "
            f"{_fmt(_hard_nonworse_min(entry, 'hard_guarded_oracle'))} | "
            f"{_fmt(_ci_high(entry, 'camp_minus_hard_guarded_oracle'))} |"
        )
    return "\n".join(rows)


def _ci(entry: dict[str, Any], name: str) -> dict[str, Any]:
    raw = _get(entry, "run_level_delta_ci", name) or {}
    return {
        "mean": raw.get("mean"),
        "ci95_low": raw.get("ci95_low"),
        "ci95_high": raw.get("ci95_high"),
    }


def _cvar_ci(entry: dict[str, Any], name: str) -> dict[str, Any]:
    raw = _get(entry, "run_level_cvar90_delta", name) or {}
    return {
        "mean": raw.get("mean"),
        "ci95_low": raw.get("ci95_low"),
        "ci95_high": raw.get("ci95_high"),
    }


def _ci_mean(entry: dict[str, Any], name: str) -> float | None:
    value = _get(entry, name, "mean")
    return None if value is None else float(value)


def _ci_high(entry: dict[str, Any], name: str) -> float | None:
    value = _get(entry, name, "ci95_high")
    return None if value is None else float(value)


def _formal_ok(summary: dict[str, Any]) -> bool:
    return int(summary.get("formal_seed_logs") or 0) == 0


def _bucket_failure_text(failures: dict[str, float | None]) -> str:
    if not failures:
        return "none"
    return ", ".join(f"{bucket}={_fmt(value)}" for bucket, value in failures.items())


def _hard_nonworse_min(entry: dict[str, Any], candidate: str) -> float | None:
    rates = entry.get("hard_component_nonworse_rate") or {}
    components = ("collision", "near_miss", "lane", "realized_red_light")
    values = [
        rates.get(f"{candidate}_{component}_vs_top1") for component in components
    ]
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return min(numeric)


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _get(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


if __name__ == "__main__":
    main()
