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
EPS = 1e-9
BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize the ProofProtocol v2 gap between a saved CAMP selector, "
            "logged CAMP, DP Top-1, and the hard-guarded SafetyCost oracle. "
            "This is read-only."
        )
    )
    parser.add_argument("--oracle_report", type=Path, required=True)
    parser.add_argument("--selector_eval_report", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        oracle_report=_load_json(args.oracle_report),
        selector_eval_report=_load_json(args.selector_eval_report),
        label=args.label,
        paths={
            "oracle_report": str(args.oracle_report),
            "selector_eval_report": str(args.selector_eval_report),
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
    oracle_report: dict[str, Any],
    selector_eval_report: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    oracle = _oracle_source(oracle_report)
    evaluated = _selector_source(selector_eval_report, "evaluated_selector")
    logged = _selector_source(selector_eval_report, "logged_selector")
    comparison = _selector_comparison(selector_eval_report)
    decision = _decision(oracle, evaluated, logged, comparison)
    return {
        "analysis": {
            "name": "dp_camp_selector_oracle_gap_v1",
            "label": label,
            "role": (
                "read-only ProofProtocol v2 selector-vs-oracle gap summary over "
                "fixed DP candidate outcome logs"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": (
                "candidate outcomes are read only as offline labels; selector "
                "scores are fixed current-tick finite-candidate atom coefficients"
            ),
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box finite-candidate generator. "
                "CAMP selector scoring remains affine score_k(w)=a_k^T w over "
                "fixed candidate coefficients, and the simplex/CVaR/L2 master "
                "remains convex. This summary does not construct a DP-side "
                "classical Benders master/subproblem, dual, or valid cut."
            ),
        },
        "required_buckets": list(DEFAULT_REQUIRED_BUCKETS),
        "oracle": oracle,
        "evaluated_selector": evaluated,
        "logged_selector": logged,
        "selector_comparison": comparison,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _oracle_source(report: dict[str, Any]) -> dict[str, Any]:
    formal_seed_logs = int(_get(report, "logs", "formal_seed_logs") or 0)
    missing = list(_get(report, "coverage_gaps", "missing_required_buckets") or [])
    overall = _metric_summary(report.get("overall") or {})
    by_bucket = _bucket_summaries(report.get("by_bucket") or [])
    bucket_failures = _failures(
        by_bucket,
        field="hard_guarded_oracle_minus_top1_ci_high",
        require_negative=True,
    )
    passed = (
        bool(_get(report, "opportunity_gate", "passed"))
        and formal_seed_logs == 0
        and not missing
        and overall["hard_guarded_oracle_minus_top1_ci_high"] is not None
        and overall["hard_guarded_oracle_minus_top1_ci_high"] < 0.0
        and not bucket_failures
    )
    return {
        "passed": passed,
        "opportunity_gate_passed": bool(_get(report, "opportunity_gate", "passed")),
        "formal_seed_logs": formal_seed_logs,
        "records": _get(report, "records", "total"),
        "logs": _get(report, "logs", "total"),
        "missing_required_buckets": missing,
        "overall": overall,
        "by_bucket": by_bucket,
        "bucket_failures": bucket_failures,
    }


def _selector_source(report: dict[str, Any], key: str) -> dict[str, Any]:
    source = report.get(key) or {}
    formal_seed_logs = int(_get(report, "logs", "formal_seed_logs") or 0)
    missing = list(_get(report, "coverage_gaps", "missing_required_buckets") or [])
    overall = _metric_summary(source.get("overall") or {})
    by_bucket = _bucket_summaries(source.get("by_bucket") or [])
    top1_failures = _failures(
        by_bucket,
        field="camp_minus_top1_ci_high",
        require_negative=True,
    )
    cvar_failures = _failures(
        by_bucket,
        field="cvar90_camp_minus_top1_ci_high",
        require_nonpositive=True,
    )
    gap_failures = _failures(
        by_bucket,
        field="camp_minus_hard_guarded_oracle_ci_high",
        require_nonpositive=True,
    )
    top1_passed = (
        formal_seed_logs == 0
        and not missing
        and _negative(overall["camp_minus_top1_ci_high"])
        and not top1_failures
    )
    cvar_passed = (
        overall["cvar90_camp_minus_top1_ci_high"] is not None
        and overall["cvar90_camp_minus_top1_ci_high"] <= 0.0
        and not cvar_failures
    )
    gap_closed = (
        overall["camp_minus_hard_guarded_oracle_ci_high"] is not None
        and overall["camp_minus_hard_guarded_oracle_ci_high"] <= 0.0
        and not gap_failures
    )
    return {
        "name": key,
        "passed_proof_protocol_v2": top1_passed and cvar_passed,
        "top1_mean_gate_passed": top1_passed,
        "cvar90_gate_passed": cvar_passed,
        "hard_guarded_oracle_gap_closed": gap_closed,
        "formal_seed_logs": formal_seed_logs,
        "records": _get(report, "records", "total"),
        "logs": _get(report, "logs", "total"),
        "missing_required_buckets": missing,
        "overall": overall,
        "by_bucket": by_bucket,
        "top1_bucket_failures": top1_failures,
        "cvar90_bucket_failures": cvar_failures,
        "gap_bucket_failures": gap_failures,
    }


def _selector_comparison(report: dict[str, Any]) -> dict[str, Any]:
    raw = report.get("selector_comparison") or {}
    changed_rate = _number(raw.get("changed_record_rate"))
    mean_delta = _number(raw.get("evaluated_minus_logged_cost_mean"))
    ci_high = _number(
        _get(raw, "run_level_evaluated_minus_logged_cost_ci", "ci95_high")
    )
    return {
        "selector_name": _get(report, "analysis", "selector_name"),
        "changed_record_rate": changed_rate,
        "evaluated_minus_logged_cost_mean": mean_delta,
        "evaluated_minus_logged_cost_ci_high": ci_high,
        "evaluated_same_as_logged": (
            changed_rate is not None
            and changed_rate <= EPS
            and (mean_delta is None or abs(mean_delta) <= EPS)
        ),
    }


def _decision(
    oracle: dict[str, Any],
    evaluated: dict[str, Any],
    logged: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    if not oracle["passed"]:
        status = "selector_oracle_gap_blocked_by_oracle"
        reasons = ["candidate_pool_opportunity_incomplete"]
        next_step = "Refresh or repair the hard-guarded oracle opportunity audit."
        authorized_next = "candidate_pool_opportunity_repair"
    elif evaluated["hard_guarded_oracle_gap_closed"]:
        status = "selector_oracle_gap_closed_candidate_branch"
        reasons = ["evaluated_selector_closes_hard_guarded_oracle_gap"]
        next_step = (
            "Predeclare deployability and latency gates before any tiny paired "
            "closed-loop smoke; this candidate-branch result is not online proof."
        )
        authorized_next = "deployability_latency_preflight_design_only"
    elif evaluated["passed_proof_protocol_v2"]:
        status = "selector_beats_top1_but_oracle_gap_open"
        reasons = ["evaluated_selector_passes_top1_but_oracle_gap_remains"]
        next_step = (
            "Diagnose which current-tick atom or weight design would close the "
            "oracle gap without outcome leakage before any closed-loop smoke."
        )
        authorized_next = "outcome_free_selector_gap_diagnosis_design_only"
    elif comparison["evaluated_same_as_logged"]:
        status = "current_selector_gap_open"
        reasons = [
            "evaluated_selector_matches_logged_selector",
            "current_selector_fails_required_bucket_or_tail_gate",
            "hard_guarded_oracle_gap_remains_open",
        ]
        next_step = (
            "Predeclare an outcome-free selector label/weight-design gate using "
            "the hard-guarded oracle only as offline supervision. Do not train "
            "or run closed-loop smoke yet."
        )
        authorized_next = "selector_label_weight_design_preflight"
    else:
        status = "evaluated_selector_gap_open"
        reasons = [
            "evaluated_selector_changes_logged_choice",
            "evaluated_selector_fails_required_bucket_or_tail_gate",
            "hard_guarded_oracle_gap_remains_open",
        ]
        next_step = (
            "Diagnose evaluated-selector failure modes by bucket and component "
            "before any training, smoke, or larger non-formal run."
        )
        authorized_next = "selector_failure_mode_diagnosis"
    return {
        "status": status,
        "passed": status == "selector_oracle_gap_closed_candidate_branch",
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
        "oracle_passed": oracle["passed"],
        "evaluated_passed_proof_protocol_v2": evaluated["passed_proof_protocol_v2"],
        "logged_passed_proof_protocol_v2": logged["passed_proof_protocol_v2"],
        "evaluated_gap_closed": evaluated["hard_guarded_oracle_gap_closed"],
        "evaluated_same_as_logged": comparison["evaluated_same_as_logged"],
        "reasons": reasons,
        "next_step": next_step,
    }


def _metric_summary(entry: dict[str, Any]) -> dict[str, Any]:
    rates = entry.get("record_rates") or {}
    return {
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
        "camp_minus_hard_guarded_oracle_ci_high": _ci(
            entry, "camp_minus_hard_guarded_oracle", "ci95_high"
        ),
        "camp_beats_top1_rate": rates.get("camp_beats_top1"),
        "camp_matches_hard_guarded_oracle_rate": rates.get(
            "camp_matches_hard_guarded_oracle"
        ),
        "hard_guarded_oracle_beats_top1_rate": rates.get(
            "hard_guarded_oracle_beats_top1"
        ),
    }


def _bucket_summaries(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("bucket")): _metric_summary(row)
        for row in rows
        if isinstance(row, dict)
    }


def _failures(
    by_bucket: dict[str, dict[str, Any]],
    *,
    field: str,
    require_negative: bool = False,
    require_nonpositive: bool = False,
) -> dict[str, float | None]:
    failures: dict[str, float | None] = {}
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        value = by_bucket.get(bucket, {}).get(field)
        if value is None:
            failures[bucket] = None
        elif require_negative and float(value) >= 0.0:
            failures[bucket] = float(value)
        elif require_nonpositive and float(value) > 0.0:
            failures[bucket] = float(value)
    return failures


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    evaluated = report["evaluated_selector"]
    logged = report["logged_selector"]
    lines = [
        "# DP-CAMP Selector Oracle Gap Summary",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Overall Gates",
        "",
        "| Source | ProofProtocol v2 | Gap closed | CAMP-Top1 CI high | CVaR90 CI high | Gap CI high |",
        "| --- | --- | --- | ---: | ---: | ---: |",
        _selector_row("evaluated", evaluated),
        _selector_row("logged", logged),
        "",
        "## Selector Comparison",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Selector name | `{report['selector_comparison']['selector_name']}` |",
        f"| Changed record rate | {_fmt(report['selector_comparison']['changed_record_rate'])} |",
        f"| Evaluated minus logged mean cost | {_fmt(report['selector_comparison']['evaluated_minus_logged_cost_mean'])} |",
        f"| Evaluated same as logged | `{report['selector_comparison']['evaluated_same_as_logged']}` |",
        "",
        "## Required-Bucket Failures",
        "",
        "### Evaluated Selector",
        "",
        _failure_table(evaluated),
        "",
        "### Logged Selector",
        "",
        _failure_table(logged),
        "",
        "## Bucket Snapshot",
        "",
        "| Bucket | Eval CAMP-Top1 CI high | Eval CVaR90 CI high | Eval gap CI high | Logged CAMP-Top1 CI high | Logged gap CI high |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        ev = evaluated["by_bucket"].get(bucket, {})
        lo = logged["by_bucket"].get(bucket, {})
        lines.append(
            f"| `{bucket}` | "
            f"{_fmt(ev.get('camp_minus_top1_ci_high'))} | "
            f"{_fmt(ev.get('cvar90_camp_minus_top1_ci_high'))} | "
            f"{_fmt(ev.get('camp_minus_hard_guarded_oracle_ci_high'))} | "
            f"{_fmt(lo.get('camp_minus_top1_ci_high'))} | "
            f"{_fmt(lo.get('camp_minus_hard_guarded_oracle_ci_high'))} |"
        )
    lines.extend(["", "## Decision Reasons", ""])
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(["", "## Blocked Actions", ""])
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision.get(action, False)}`")
    lines.extend(
        [
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
        lines.append(f"| `{name}` | `{path}` |")
    lines.append("")
    return "\n".join(lines)


def _selector_row(name: str, source: dict[str, Any]) -> str:
    overall = source["overall"]
    return (
        f"| `{name}` | `{source['passed_proof_protocol_v2']}` | "
        f"`{source['hard_guarded_oracle_gap_closed']}` | "
        f"{_fmt(overall['camp_minus_top1_ci_high'])} | "
        f"{_fmt(overall['cvar90_camp_minus_top1_ci_high'])} | "
        f"{_fmt(overall['camp_minus_hard_guarded_oracle_ci_high'])} |"
    )


def _failure_table(source: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Gate | Buckets |",
            "| --- | --- |",
            f"| Top-1 mean CI | {_failure_text(source['top1_bucket_failures'])} |",
            f"| CVaR90 CI | {_failure_text(source['cvar90_bucket_failures'])} |",
            f"| Oracle gap CI | {_failure_text(source['gap_bucket_failures'])} |",
        ]
    )


def _failure_text(values: dict[str, float | None]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{bucket}`={_fmt(value)}" for bucket, value in values.items())


def _negative(value: float | None) -> bool:
    return value is not None and value < 0.0


def _ci(entry: dict[str, Any], name: str, field: str) -> float | None:
    return _number(_get(entry, "run_level_delta_ci", name, field))


def _cvar(entry: dict[str, Any], name: str, field: str) -> float | None:
    return _number(_get(entry, "run_level_cvar90_delta", name, field))


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
