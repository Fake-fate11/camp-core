#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize why the CAMP-vs-DP-Top1 candidate-branch SafetyCost "
            "proof did or did not transfer to the deployable closed-loop path. "
            "This is read-only."
        )
    )
    parser.add_argument("--proof_report", type=Path, required=True)
    parser.add_argument("--deployable_failure_report", type=Path, required=True)
    parser.add_argument("--top1_fallback_report", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        proof_report=_load_json(args.proof_report),
        deployable_failure_report=_load_json(args.deployable_failure_report),
        top1_fallback_report=(
            None if args.top1_fallback_report is None else _load_json(args.top1_fallback_report)
        ),
        paths={
            "proof_report": str(args.proof_report),
            "deployable_failure_report": str(args.deployable_failure_report),
            "top1_fallback_report": _path_or_none(args.top1_fallback_report),
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
    proof_report: dict[str, Any],
    deployable_failure_report: dict[str, Any],
    top1_fallback_report: dict[str, Any] | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    proof = _proof_summary(proof_report)
    deployable = _deployable_summary(deployable_failure_report)
    top1_fallback = (
        None if top1_fallback_report is None else _deployable_summary(top1_fallback_report)
    )
    mechanism = _mechanism_summary(
        proof=proof,
        deployable=deployable,
        top1_fallback=top1_fallback,
    )
    decision = _decision(mechanism)
    return {
        "analysis": {
            "name": "dp_camp_proof_to_deployable_gap_summary",
            "role": (
                "read-only bridge from candidate-branch SafetyCost proof to "
                "deployable closed-loop failure diagnosis"
            ),
            "training": False,
            "online_selector_change": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "math_boundary": (
                "DP remains a fixed black-box candidate generator. This report "
                "only consolidates existing artifacts. CAMP candidate scores "
                "remain affine a_k^T w over fixed current-tick features, and "
                "the simplex/CVaR/L2 robust master is unchanged. DP-side "
                "postselection or fallback logic is finite-candidate logic, "
                "not classical Benders decomposition."
            ),
            "paths": paths or {},
        },
        "candidate_branch_proof": proof,
        "deployable_static_gap": deployable,
        "top1_fallback_targeted": top1_fallback,
        "mechanism": mechanism,
        "final_decision": decision,
    }


def _proof_summary(report: dict[str, Any]) -> dict[str, Any]:
    gates = report.get("gates") or {}
    selector = _get(report, "safety_cost_trained_selector", "evaluated") or {}
    current = report.get("current_camp") or {}
    return {
        "status": _get(report, "final_decision", "status"),
        "current_camp_complete_proof": _get(
            report, "final_decision", "current_camp_complete_proof"
        ),
        "safety_cost_trained_selector_candidate_branch_proof": _get(
            report,
            "final_decision",
            "safety_cost_trained_selector_candidate_branch_proof",
        ),
        "hard_guarded_oracle_gap_closed": _get(
            report, "final_decision", "hard_guarded_oracle_gap_closed"
        ),
        "candidate_pool_opportunity": _gate_summary(
            gates.get("candidate_pool_opportunity") or {}
        ),
        "current_camp_vs_top1": _gate_summary(gates.get("current_camp_vs_top1") or {}),
        "safety_cost_trained_selector_vs_top1": _gate_summary(
            gates.get("safety_cost_trained_selector_vs_top1") or {}
        ),
        "hard_guarded_oracle_gap": _gate_summary(
            gates.get("safety_cost_trained_selector_gap_closed") or {}
        ),
        "current_camp_metrics": _proof_metrics(current.get("overall") or {}),
        "safety_cost_trained_selector_metrics": _proof_metrics(
            selector.get("overall") or {}
        ),
        "selector_bucket_failures": _gate_summary(
            gates.get("safety_cost_trained_selector_vs_top1") or {}
        ).get("bucket_failures"),
        "current_bucket_failures": _gate_summary(
            gates.get("current_camp_vs_top1") or {}
        ).get("bucket_failures"),
    }


def _proof_metrics(entry: dict[str, Any]) -> dict[str, Any]:
    coverage = entry.get("candidate_pool_coverage") or {}
    rates = entry.get("record_rates") or {}
    return {
        "records": entry.get("records"),
        "logs": entry.get("logs"),
        "camp_minus_top1_ci_high": _ci_high(entry, "camp_minus_top1"),
        "camp_minus_top1_cvar90_ci_high": _ci_high(
            entry,
            "cvar90_camp_minus_top1",
        ),
        "hard_guarded_oracle_minus_top1_ci_high": _ci_high(
            entry,
            "hard_guarded_oracle_minus_top1",
        ),
        "gap_to_hard_guarded_oracle_ci_high": _ci_high(
            entry,
            "camp_minus_hard_guarded_oracle",
        ),
        "hard_guarded_oracle_available_rate": _first_not_none(
            coverage.get("hard_guarded_oracle_available_rate"),
            rates.get("hard_guarded_oracle_available"),
        ),
        "hard_guarded_oracle_beats_top1_rate": rates.get(
            "hard_guarded_oracle_beats_top1"
        ),
        "camp_hard_component_nonworse_min": _hard_nonworse_min(entry, "camp"),
    }


def _gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": gate.get("passed"),
        "overall_ci_high": gate.get("overall_ci_high"),
        "bucket_failures": gate.get("bucket_failures") or {},
    }


def _deployable_summary(report: dict[str, Any]) -> dict[str, Any]:
    if "overall" in report and "worst_runs" in report:
        return _deployable_failure_summary(report)
    if "rules" in report:
        return _top1_shadow_summary(report)
    return {
        "source_name": _get(report, "analysis", "name"),
        "recognized_schema": False,
    }


def _deployable_failure_summary(report: dict[str, Any]) -> dict[str, Any]:
    overall = report.get("overall") or {}
    gate = overall.get("gate") or {}
    worst_runs = [_compact_worst_run(row) for row in report.get("worst_runs") or []]
    lane_runs = [row for row in worst_runs if "lane_change" in str(row.get("route_name"))]
    benchmark_deltas = overall.get("benchmark_delta_means") or {}
    return {
        "source_name": _get(report, "analysis", "name"),
        "recognized_schema": True,
        "records": report.get("records") or {},
        "gate": {
            "hard_gate_passed": gate.get("hard_gate_passed"),
            "safety_cost_claim_passed": gate.get("safety_cost_claim_passed"),
            "claim_rule": gate.get("claim_rule"),
        },
        "mean_static_fallback_rate": overall.get("mean_static_fallback_rate"),
        "mean_static_candidate_feasible_rate": overall.get(
            "mean_static_candidate_feasible_rate"
        ),
        "mean_static_selected_non_top1_rate": overall.get(
            "mean_static_selected_non_top1_rate"
        ),
        "benchmark_delta_means": {
            "safety_cost_v1": benchmark_deltas.get("safety_cost_v1"),
            "route_completion_rate": benchmark_deltas.get("route_completion_rate"),
            "near_miss_rate": benchmark_deltas.get("near_miss_rate"),
            "lane_violation_rate": benchmark_deltas.get("lane_violation_rate"),
            "mean_jerk_magnitude_mps3": benchmark_deltas.get(
                "mean_jerk_magnitude_mps3"
            ),
        },
        "feature_deltas_selected_minus_top1": _feature_focus(
            overall.get("feature_deltas_selected_minus_top1") or {}
        ),
        "global_infeasibility_reasons": overall.get("global_infeasibility_reasons")
        or [],
        "worst_runs": worst_runs,
        "worst_lane_change_run": lane_runs[0] if lane_runs else None,
    }


def _top1_shadow_summary(report: dict[str, Any]) -> dict[str, Any]:
    rules = {str(rule.get("name")): rule for rule in report.get("rules") or []}
    top1_fallback = rules.get("top1_on_all_infeasible")
    baseline = rules.get("static_baseline")
    return {
        "source_name": _get(report, "analysis", "name"),
        "recognized_schema": True,
        "records": report.get("records") or {},
        "static_baseline": _shadow_rule_summary(baseline),
        "top1_on_all_infeasible": _shadow_rule_summary(top1_fallback),
    }


def _shadow_rule_summary(rule: dict[str, Any] | None) -> dict[str, Any] | None:
    if rule is None:
        return None
    overall = rule.get("overall") or {}
    return {
        "changed_from_static_rate": overall.get("changed_from_static_rate"),
        "top1_selected_rate": overall.get("top1_selected_rate"),
        "all_infeasible_top1_restored_rate": overall.get(
            "all_infeasible_top1_restored_rate"
        ),
        "dp_prior_deviation_trigger_rate": overall.get(
            "dp_prior_deviation_trigger_rate"
        ),
        "target_speed_trigger_rate": overall.get("target_speed_trigger_rate"),
        "worst_coverage": rule.get("worst_coverage") or [],
    }


def _feature_focus(features: dict[str, Any]) -> dict[str, Any]:
    names = (
        "route_progress",
        "target_speed",
        "dp_prior_deviation",
        "dp_prior_lateral_excess",
        "horizon_lateral_cost",
        "selection_score",
    )
    focused: dict[str, Any] = {}
    for name in names:
        entry = features.get(name)
        if not isinstance(entry, dict):
            continue
        focused[name] = {
            "changed_records": entry.get("changed_records"),
            "mean_of_run_mean_delta": entry.get("mean_of_run_mean_delta"),
            "mean_selected_better_or_equal_rate": entry.get(
                "mean_selected_better_or_equal_rate"
            ),
        }
    return focused


def _compact_worst_run(row: dict[str, Any]) -> dict[str, Any]:
    benchmark = row.get("benchmark") or {}
    delta = benchmark.get("delta_static_minus_top1") or {}
    static = benchmark.get("static") or {}
    selection = row.get("selection") or {}
    return {
        "route_name": row.get("route_name"),
        "max_npcs": row.get("max_npcs"),
        "traffic_lights": row.get("traffic_lights"),
        "safety_cost_delta": delta.get("safety_cost_v1"),
        "completion_delta": delta.get("route_completion_rate"),
        "near_miss_delta": delta.get("near_miss_rate"),
        "lane_delta": delta.get("lane_violation_rate"),
        "static_p95_latency_ms": static.get("p95_selection_latency_ms"),
        "fallback_rate": selection.get("fallback_rate"),
        "candidate_feasible_rate": selection.get("candidate_feasible_rate"),
        "selected_non_top1_rate": selection.get("selected_non_top1_rate"),
        "top_infeasibility_reasons": row.get("top_infeasibility_reasons") or [],
    }


def _mechanism_summary(
    *,
    proof: dict[str, Any],
    deployable: dict[str, Any],
    top1_fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate_support_exists = bool(
        proof["candidate_pool_opportunity"].get("passed")
    )
    candidate_branch_selector_passes = bool(
        proof.get("safety_cost_trained_selector_candidate_branch_proof")
    )
    deployable_gate_passes = bool(
        deployable.get("gate", {}).get("hard_gate_passed")
        and deployable.get("gate", {}).get("safety_cost_claim_passed")
    )
    worst_lane = deployable.get("worst_lane_change_run") or {}
    fallback_rate = _as_float(worst_lane.get("fallback_rate"))
    feasible_rate = _as_float(worst_lane.get("candidate_feasible_rate"))
    latency = _as_float(worst_lane.get("static_p95_latency_ms"))
    completion_delta = _as_float(worst_lane.get("completion_delta"))
    safety_delta = _as_float(worst_lane.get("safety_cost_delta"))
    lane_delta = _as_float(worst_lane.get("lane_delta"))
    blockers: list[str] = []
    if safety_delta is not None and safety_delta > 0.0:
        blockers.append("dense_lane_change_safety_cost_regression")
    if lane_delta is not None and lane_delta > 0.0:
        blockers.append("dense_lane_change_lane_regression")
    if fallback_rate is not None and fallback_rate >= 0.3:
        blockers.append("high_all_infeasible_fallback")
    if feasible_rate is not None and feasible_rate <= 0.6:
        blockers.append("low_candidate_feasible_rate")
    if completion_delta is not None and completion_delta < 0.0:
        blockers.append("completion_loss")
    if latency is not None and latency >= 100.0:
        blockers.append("per_run_latency_above_100ms")
    top1_fallback_effect = _top1_fallback_effect(deployable, top1_fallback)
    if top1_fallback_effect.get("remaining_safety_delta", 0.0) > 0.0:
        blockers.append("top1_fallback_insufficient")
    return {
        "candidate_support_exists": candidate_support_exists,
        "candidate_branch_selector_passes": candidate_branch_selector_passes,
        "deployable_gate_passes": deployable_gate_passes,
        "root_cause_class": (
            "score_schema_feasibility_fallback_deployability_gap"
            if candidate_support_exists and candidate_branch_selector_passes and not deployable_gate_passes
            else "proof_or_support_incomplete"
        ),
        "primary_blockers": blockers,
        "worst_dense_lane_change": worst_lane or None,
        "top1_fallback_effect": top1_fallback_effect,
        "interpretation": _interpretation(
            candidate_support_exists=candidate_support_exists,
            candidate_branch_selector_passes=candidate_branch_selector_passes,
            deployable_gate_passes=deployable_gate_passes,
            blockers=blockers,
        ),
    }


def _top1_fallback_effect(
    deployable: dict[str, Any],
    top1_fallback: dict[str, Any] | None,
) -> dict[str, Any]:
    if top1_fallback is None or "worst_lane_change_run" not in top1_fallback:
        return {
            "available": False,
            "interpretation": "no targeted top1 fallback closed-loop report supplied",
        }
    before = deployable.get("worst_lane_change_run") or {}
    after = top1_fallback.get("worst_lane_change_run") or {}
    before_safety = _as_float(before.get("safety_cost_delta"))
    after_safety = _as_float(after.get("safety_cost_delta"))
    before_lane = _as_float(before.get("lane_delta"))
    after_lane = _as_float(after.get("lane_delta"))
    before_latency = _as_float(before.get("static_p95_latency_ms"))
    after_latency = _as_float(after.get("static_p95_latency_ms"))
    return {
        "available": True,
        "baseline_lane_change_safety_delta": before_safety,
        "top1_fallback_lane_change_safety_delta": after_safety,
        "safety_delta_reduction": _subtract(after_safety, before_safety),
        "baseline_lane_delta": before_lane,
        "top1_fallback_lane_delta": after_lane,
        "lane_delta_reduction": _subtract(after_lane, before_lane),
        "top1_fallback_latency_ms": after_latency,
        "remaining_safety_delta": after_safety,
        "interpretation": (
            "top1 fallback reduces the dense lane-change SafetyCost gap but "
            "still leaves a positive safety/lane/latency blocker"
        ),
    }


def _interpretation(
    *,
    candidate_support_exists: bool,
    candidate_branch_selector_passes: bool,
    deployable_gate_passes: bool,
    blockers: list[str],
) -> list[str]:
    lines: list[str] = []
    if candidate_support_exists:
        lines.append(
            "DP Top-1 is not always SafetyCost-optimal: the fixed candidate pools "
            "contain hard-guarded opportunity in the required non-formal buckets."
        )
    else:
        lines.append(
            "The candidate-pool opportunity proof is incomplete, so a training or "
            "selector claim would be premature."
        )
    if candidate_branch_selector_passes:
        lines.append(
            "The SafetyCost-trained CAMP selector passes the candidate-branch "
            "proof gate versus DP Top-1, so CAMP's affine finite-candidate "
            "framework is not the blocker by itself."
        )
    if not deployable_gate_passes:
        lines.append(
            "The deployable closed-loop path fails despite the candidate-branch "
            "proof; the issue is the transfer through outcome-free scoring, "
            "feasibility/fallback, postprocess, tracker state, and latency."
        )
    if blockers:
        lines.append("Primary blockers: " + ", ".join(blockers) + ".")
    lines.append(
        "This is not evidence for immediate retraining. The next step must first "
        "state a legal current-tick finite-candidate hypothesis that targets the "
        "observed deployable gap."
    )
    return lines


def _decision(mechanism: dict[str, Any]) -> dict[str, Any]:
    passes = bool(mechanism.get("deployable_gate_passes"))
    return {
        "status": "deployable_gap_diagnosed" if not passes else "deployable_gate_passed",
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "Predeclare and offline-screen a current-tick finite-candidate "
            "hypothesis focused on dense lane-change feasible ticks: "
            "DP-prior/completion preservation, feasible-candidate fallback, or "
            "schema calibration. Do not train or run Full36 until that screen "
            "passes and the math boundary is written down."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    proof = report["candidate_branch_proof"]
    deployable = report["deployable_static_gap"]
    top1_fallback = report.get("top1_fallback_targeted")
    mechanism = report["mechanism"]
    decision = report["final_decision"]
    lines = [
        "# CAMP Proof-to-Deployable Gap Summary",
        "",
        "This report consolidates existing artifacts only. It does not run DP, "
        "train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Candidate support exists: `{mechanism['candidate_support_exists']}`",
        f"- Candidate-branch selector proof passes: `{mechanism['candidate_branch_selector_passes']}`",
        f"- Deployable closed-loop gate passes: `{mechanism['deployable_gate_passes']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        f"- Full36 authorized: `{decision['full36_authorized']}`",
        "",
        "## Candidate-Branch Proof",
        "",
        "| Gate | Passed | CI high | Bucket failures |",
        "| --- | --- | ---: | --- |",
        _gate_row("candidate_pool_opportunity", proof["candidate_pool_opportunity"]),
        _gate_row("current_camp_vs_top1", proof["current_camp_vs_top1"]),
        _gate_row(
            "safety_cost_trained_selector_vs_top1",
            proof["safety_cost_trained_selector_vs_top1"],
        ),
        _gate_row("hard_guarded_oracle_gap", proof["hard_guarded_oracle_gap"]),
        "",
        "### Key Proof Metrics",
        "",
        "| Metric | Current logged CAMP | SafetyCost-trained selector |",
        "| --- | ---: | ---: |",
    ]
    current_metrics = proof["current_camp_metrics"]
    selector_metrics = proof["safety_cost_trained_selector_metrics"]
    for key in (
        "camp_minus_top1_ci_high",
        "camp_minus_top1_cvar90_ci_high",
        "hard_guarded_oracle_available_rate",
        "hard_guarded_oracle_beats_top1_rate",
        "camp_hard_component_nonworse_min",
        "gap_to_hard_guarded_oracle_ci_high",
    ):
        lines.append(
            f"| `{key}` | {_fmt(current_metrics.get(key))} | {_fmt(selector_metrics.get(key))} |"
        )
    lines.extend(
        [
            "",
            "## Deployable Closed-Loop Gap",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| hard gate passed | `{_fmt(deployable.get('gate', {}).get('hard_gate_passed'))}` |",
            f"| SafetyCost claim passed | `{_fmt(deployable.get('gate', {}).get('safety_cost_claim_passed'))}` |",
            f"| mean static fallback rate | {_fmt(deployable.get('mean_static_fallback_rate'))} |",
            f"| mean static candidate feasible rate | {_fmt(deployable.get('mean_static_candidate_feasible_rate'))} |",
            f"| mean static selected non-Top1 rate | {_fmt(deployable.get('mean_static_selected_non_top1_rate'))} |",
        ]
    )
    for key, value in (deployable.get("benchmark_delta_means") or {}).items():
        lines.append(f"| `{key}` delta mean | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "### Worst Dense Lane-Change Row",
            "",
            _worst_run_table(deployable.get("worst_lane_change_run")),
            "",
        ]
    )
    if top1_fallback is not None:
        lines.extend(
            [
                "## Top-1 Fallback Targeted Evidence",
                "",
                _worst_run_table(top1_fallback.get("worst_lane_change_run")),
                "",
                "| Effect | Value |",
                "| --- | ---: |",
            ]
        )
        for key, value in mechanism["top1_fallback_effect"].items():
            if key in {"available", "interpretation"}:
                continue
            lines.append(f"| `{key}` | {_fmt(value)} |")
        lines.append("")
    lines.extend(
        [
            "## Mechanism",
            "",
        ]
    )
    for item in mechanism["interpretation"]:
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
    for key, value in (report["analysis"].get("paths") or {}).items():
        lines.append(f"| `{key}` | `{value or 'none'}` |")
    lines.append("")
    return "\n".join(lines)


def _gate_row(name: str, gate: dict[str, Any]) -> str:
    failures = gate.get("bucket_failures") or {}
    failure_text = "none"
    if failures:
        failure_text = ", ".join(
            f"{bucket}={_fmt(value)}" for bucket, value in failures.items()
        )
    return (
        f"| `{name}` | `{gate.get('passed')}` | "
        f"{_fmt(gate.get('overall_ci_high'))} | {failure_text} |"
    )


def _worst_run_table(row: dict[str, Any] | None) -> str:
    if not row:
        return "No lane-change row was available."
    lines = [
        "| Field | Value |",
        "| --- | ---: |",
        f"| route | `{row.get('route_name')}` |",
        f"| NPCs | {_fmt(row.get('max_npcs'))} |",
        f"| traffic lights | `{row.get('traffic_lights')}` |",
        f"| SafetyCost delta | {_fmt(row.get('safety_cost_delta'))} |",
        f"| completion delta | {_fmt(row.get('completion_delta'))} |",
        f"| near-miss delta | {_fmt(row.get('near_miss_delta'))} |",
        f"| lane delta | {_fmt(row.get('lane_delta'))} |",
        f"| p95 latency ms | {_fmt(row.get('static_p95_latency_ms'))} |",
        f"| fallback rate | {_fmt(row.get('fallback_rate'))} |",
        f"| candidate feasible rate | {_fmt(row.get('candidate_feasible_rate'))} |",
    ]
    return "\n".join(lines)


def _ci_high(entry: dict[str, Any], key: str) -> float | None:
    value = _get(entry, key, "ci95_high")
    return None if value is None else float(value)


def _hard_nonworse_min(entry: dict[str, Any], candidate: str) -> float | None:
    rates = entry.get("hard_component_nonworse_rate") or {}
    values = [
        rates.get(f"{candidate}_{name}_vs_top1")
        for name in ("collision", "near_miss", "lane", "realized_red_light")
    ]
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return min(numeric)


def _subtract(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left - right)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
