#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    BLOCKED_ACTIONS,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    _load_json,
    _path_seeds,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_separability import (  # noqa: E402
    REJECT_STATUS as STRICT_LABEL_REJECT_STATUS,
    analyze_records as analyze_strict_label_records,
)


READY_STATUS = "revised_context_strict_label_sensitivity_promising"
DIAGNOSED_STATUS = "revised_context_strict_label_sensitivity_diagnosed"
SOURCE_BLOCKED_STATUS = "revised_context_strict_label_sensitivity_source_not_ready"

STRICT_SOURCE_PRIMARY_GAP = "strict_beneficial_support_insufficient"
STRICT_SOURCE_NEXT_WORK = "relax_or_redefine_strict_label_or_expand_nonformal_support"
NEXT_WORK_PROMISING = "offline_relaxed_strict_label_certificate_design_only"
NEXT_WORK_SUPPORT_FOUND = "diagnose_relaxed_strict_label_atom_bottleneck_before_replay"
NEXT_WORK_SUPPORT_LIMITED = (
    "record_candidate_set_support_limited_or_predeclare_broader_nonformal_support"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a predeclared threshold sensitivity over the strict offline "
            "safety-score label on existing revised-context matched logs. "
            "This does not train CAMP, run DP, or change the online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--strict_label_json", type=Path, required=True)
    parser.add_argument("--label_objective_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--progress_loss_budgets_m",
        default="0.05,0.10",
        help="Comma-separated strict-label progress loss budgets.",
    )
    parser.add_argument(
        "--safety_improvement_margins",
        default="0.00,0.025,0.05",
        help="Comma-separated lower-is-better safety penalty improvement margins.",
    )
    parser.add_argument(
        "--comfort_jerk_delta_budgets",
        default="0.0,0.5,1.0",
        help="Comma-separated allowed jerk deltas versus Top-1.",
    )
    parser.add_argument(
        "--comfort_lateral_delta_budgets",
        default="0.0,0.05,0.10",
        help="Comma-separated allowed lateral acceleration deltas versus Top-1.",
    )
    parser.add_argument("--harmful_safety_margin", type=float, default=0.05)
    parser.add_argument("--min_strict_beneficial_candidates", type=int, default=8)
    parser.add_argument("--min_harmful_candidates", type=int, default=8)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        strict_label_report=_load_json(args.strict_label_json),
        label_objective_audit_report=_load_json(args.label_objective_audit_json),
        label=args.label,
        progress_loss_budgets_m=_parse_float_list(args.progress_loss_budgets_m),
        safety_improvement_margins=_parse_float_list(args.safety_improvement_margins),
        comfort_jerk_delta_budgets=_parse_float_list(args.comfort_jerk_delta_budgets),
        comfort_lateral_delta_budgets=_parse_float_list(
            args.comfort_lateral_delta_budgets
        ),
        harmful_safety_margin=args.harmful_safety_margin,
        min_strict_beneficial_candidates=args.min_strict_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    strict_label_report: dict[str, Any],
    label_objective_audit_report: dict[str, Any],
    label: str | None = None,
    progress_loss_budgets_m: list[float] | None = None,
    safety_improvement_margins: list[float] | None = None,
    comfort_jerk_delta_budgets: list[float] | None = None,
    comfort_lateral_delta_budgets: list[float] | None = None,
    harmful_safety_margin: float = 0.05,
    min_strict_beneficial_candidates: int = 8,
    min_harmful_candidates: int = 8,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = _load_json(log_path)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(_path_seeds(log_path)),
                    },
                }
            )
    return analyze_records(
        items,
        strict_label_report=strict_label_report,
        label_objective_audit_report=label_objective_audit_report,
        label=label,
        progress_loss_budgets_m=progress_loss_budgets_m,
        safety_improvement_margins=safety_improvement_margins,
        comfort_jerk_delta_budgets=comfort_jerk_delta_budgets,
        comfort_lateral_delta_budgets=comfort_lateral_delta_budgets,
        harmful_safety_margin=harmful_safety_margin,
        min_strict_beneficial_candidates=min_strict_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    strict_label_report: dict[str, Any],
    label_objective_audit_report: dict[str, Any],
    label: str | None = None,
    progress_loss_budgets_m: list[float] | None = None,
    safety_improvement_margins: list[float] | None = None,
    comfort_jerk_delta_budgets: list[float] | None = None,
    comfort_lateral_delta_budgets: list[float] | None = None,
    harmful_safety_margin: float = 0.05,
    min_strict_beneficial_candidates: int = 8,
    min_harmful_candidates: int = 8,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    progress_loss_budgets_m = progress_loss_budgets_m or [0.05, 0.10]
    safety_improvement_margins = safety_improvement_margins or [0.0, 0.025, 0.05]
    comfort_jerk_delta_budgets = comfort_jerk_delta_budgets or [0.0, 0.5, 1.0]
    comfort_lateral_delta_budgets = comfort_lateral_delta_budgets or [0.0, 0.05, 0.10]

    source = _source_gate(strict_label_report)
    grid_results: list[dict[str, Any]] = []
    if source["passed"]:
        for progress_budget in progress_loss_budgets_m:
            for safety_margin in safety_improvement_margins:
                for jerk_budget in comfort_jerk_delta_budgets:
                    for lateral_budget in comfort_lateral_delta_budgets:
                        strict_report = analyze_strict_label_records(
                            items,
                            label_objective_audit_report=label_objective_audit_report,
                            label=label,
                            progress_loss_budget_m=float(progress_budget),
                            comfort_jerk_delta_budget=float(jerk_budget),
                            comfort_lateral_delta_budget=float(lateral_budget),
                            safety_improvement_margin=float(safety_margin),
                            harmful_safety_margin=float(harmful_safety_margin),
                            min_strict_beneficial_candidates=int(
                                min_strict_beneficial_candidates
                            ),
                            min_harmful_candidates=int(min_harmful_candidates),
                            fail_on_formal_seeds=fail_on_formal_seeds,
                        )
                        grid_results.append(
                            _compact_result(
                                strict_report,
                                progress_budget=float(progress_budget),
                                safety_margin=float(safety_margin),
                                jerk_budget=float(jerk_budget),
                                lateral_budget=float(lateral_budget),
                            )
                        )
    summary = _summarize_grid(
        grid_results,
        min_strict_beneficial_candidates=min_strict_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    final = _decision(source, summary)
    return {
        "analysis": {
            "name": "dp_camp_revised_context_strict_label_sensitivity_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_offline_sensitivity": True,
            "predeclared_grid": {
                "progress_loss_budgets_m": progress_loss_budgets_m,
                "safety_improvement_margins": safety_improvement_margins,
                "comfort_jerk_delta_budgets": comfort_jerk_delta_budgets,
                "comfort_lateral_delta_budgets": comfort_lateral_delta_budgets,
                "harmful_safety_margin": harmful_safety_margin,
            },
            "accept_criteria": {
                "min_strict_beneficial_candidates": min_strict_beneficial_candidates,
                "min_harmful_candidates": min_harmful_candidates,
                "promising": (
                    "a grid point must pass strict-label revised-atom "
                    "separability with support and screen criteria"
                ),
            },
            "math_boundary": (
                "This sensitivity changes only offline outcome-label thresholds "
                "for an already fixed DP candidate set. Revised atom values are "
                "read from current-tick default-off payloads and are never "
                "computed from outcomes. Any later CAMP use would still require "
                "fixed candidate coefficients in affine score_k(w)=a_k^T w for "
                "the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders decomposition, dual, or cut is introduced."
            ),
        },
        "source_strict_label_gate": source,
        "grid_summary": summary,
        "top_grid_results": _top_grid_results(grid_results),
        "all_grid_results": grid_results,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    passed = (
        decision.get("passed") is False
        and status == STRICT_LABEL_REJECT_STATUS
        and primary_gap == STRICT_SOURCE_PRIMARY_GAP
        and next_work == STRICT_SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
    }


def _compact_result(
    report: dict[str, Any],
    *,
    progress_budget: float,
    safety_margin: float,
    jerk_budget: float,
    lateral_budget: float,
) -> dict[str, Any]:
    decision = report["final_decision"]
    records = report["records"]
    class_counts = records.get("class_counts") or {}
    best = report["ranked_screens"][0] if report.get("ranked_screens") else None
    strict_label_summary = report.get("strict_label_summary") or {}
    beneficial_summary = strict_label_summary.get("beneficial") or {}
    harmful_summary = strict_label_summary.get("harmful") or {}
    return {
        "params": {
            "progress_loss_budget_m": progress_budget,
            "safety_improvement_margin": safety_margin,
            "comfort_jerk_delta_budget": jerk_budget,
            "comfort_lateral_delta_budget": lateral_budget,
        },
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "class_counts": {
            CLASS_BENEFICIAL: int(class_counts.get(CLASS_BENEFICIAL, 0)),
            CLASS_HARMFUL: int(class_counts.get(CLASS_HARMFUL, 0)),
            "neutral_alternative": int(class_counts.get("neutral_alternative", 0)),
        },
        "records_with_strict_beneficial": records.get("records_with_strict_beneficial"),
        "promising_screen_count": decision.get("promising_screen_count"),
        "best_screen": _screen_summary(best),
        "beneficial_summary": _trim_summary(beneficial_summary),
        "harmful_summary": _trim_summary(harmful_summary),
    }


def _summarize_grid(
    results: list[dict[str, Any]],
    *,
    min_strict_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in results if row["passed"]]
    support_sufficient = [
        row
        for row in results
        if row["class_counts"][CLASS_BENEFICIAL] >= int(min_strict_beneficial_candidates)
        and row["class_counts"][CLASS_HARMFUL] >= int(min_harmful_candidates)
    ]
    support_limited = [
        row
        for row in results
        if row["class_counts"][CLASS_BENEFICIAL] < int(min_strict_beneficial_candidates)
    ]
    best_by_support = max(
        results,
        key=lambda row: (
            row["class_counts"][CLASS_BENEFICIAL],
            row["class_counts"][CLASS_HARMFUL],
            _best_harmful_block_rate(row),
            _best_beneficial_retain_rate(row),
            -_best_allowed_harmful_rate(row),
        ),
        default=None,
    )
    best_by_screen = max(
        results,
        key=lambda row: (
            float(row["passed"]),
            _best_harmful_block_rate(row),
            _best_beneficial_retain_rate(row),
            -_best_allowed_harmful_rate(row),
            row["class_counts"][CLASS_BENEFICIAL],
        ),
        default=None,
    )
    return {
        "grid_count": len(results),
        "promising_count": len(promising),
        "support_sufficient_count": len(support_sufficient),
        "support_limited_count": len(support_limited),
        "min_strict_beneficial_candidates": min_strict_beneficial_candidates,
        "min_harmful_candidates": min_harmful_candidates,
        "max_strict_beneficial_candidates": (
            max((row["class_counts"][CLASS_BENEFICIAL] for row in results), default=0)
        ),
        "max_records_with_strict_beneficial": (
            max((row["records_with_strict_beneficial"] or 0 for row in results), default=0)
        ),
        "best_by_support": best_by_support,
        "best_by_screen": best_by_screen,
    }


def _decision(source: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        passed = False
        primary_gap = "strict_label_source_not_ready"
        next_work = "fix_strict_label_source_before_sensitivity"
    elif summary["promising_count"] > 0:
        status = READY_STATUS
        passed = True
        primary_gap = "no_gap_nearby_strict_label_screen_found"
        next_work = NEXT_WORK_PROMISING
    elif summary["support_sufficient_count"] > 0:
        status = DIAGNOSED_STATUS
        passed = True
        primary_gap = "support_exists_but_revised_atoms_do_not_separate_relaxed_strict_label"
        next_work = NEXT_WORK_SUPPORT_FOUND
    else:
        status = DIAGNOSED_STATUS
        passed = True
        primary_gap = "no_nearby_strict_label_has_sufficient_beneficial_support"
        next_work = NEXT_WORK_SUPPORT_LIMITED
    return {
        "status": status,
        "passed": passed,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _top_grid_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda row: (
            float(row["passed"]),
            row["class_counts"][CLASS_BENEFICIAL],
            _best_harmful_block_rate(row),
            _best_beneficial_retain_rate(row),
            -_best_allowed_harmful_rate(row),
        ),
        reverse=True,
    )
    return ranked[:10]


def _screen_summary(screen: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(screen, dict):
        return None
    return {
        "screen_name": screen.get("screen_name"),
        "descriptor_names": screen.get("descriptor_names"),
        "threshold": screen.get("threshold"),
        "harmful_block_rate": screen.get("harmful_block_rate"),
        "beneficial_retain_rate": screen.get("beneficial_retain_rate"),
        "allowed_harmful_rate": screen.get("allowed_harmful_rate"),
        "allowed_candidates": screen.get("allowed_candidates"),
        "promising_screen": screen.get("promising_screen"),
    }


def _trim_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": summary.get("count"),
        "progress_delta_mean_m": summary.get("progress_delta_mean_m"),
        "safety_penalty_delta_mean": summary.get("safety_penalty_delta_mean"),
        "jerk_delta_mean_mps3": summary.get("jerk_delta_mean_mps3"),
        "lateral_delta_mean_mps2": summary.get("lateral_delta_mean_mps2"),
    }


def _best_harmful_block_rate(row: dict[str, Any]) -> float:
    screen = row.get("best_screen") or {}
    return float(screen.get("harmful_block_rate") or 0.0)


def _best_beneficial_retain_rate(row: dict[str, Any]) -> float:
    screen = row.get("best_screen") or {}
    return float(screen.get("beneficial_retain_rate") or 0.0)


def _best_allowed_harmful_rate(row: dict[str, Any]) -> float:
    screen = row.get("best_screen") or {}
    value = screen.get("allowed_harmful_rate")
    return float(value) if value is not None else 1.0


def _parse_float_list(raw: str) -> list[float]:
    values = []
    for part in str(raw).split(","):
        text = part.strip()
        if not text:
            continue
        values.append(float(text))
    if not values:
        raise ValueError("At least one value is required.")
    return values


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Revised Context Strict Label Sensitivity",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Grid Summary",
        "",
        "```json",
        json.dumps(report["grid_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Top Grid Results",
        "",
        "```json",
        json.dumps(report["top_grid_results"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
