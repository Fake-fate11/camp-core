#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_lane_hard_violation_support_descriptor_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    REJECT_STATUS as SEPARABILITY_REJECT_STATUS,
    _candidate_rows,
    _descriptor_specs,
    _load_json,
    _path_seeds,
)


READY_STATUS = "lane_hard_violation_support_separability_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = (
    "lane_hard_violation_support_separability_bottleneck_source_not_ready"
)

SOURCE_PRIMARY_GAP = "lane_hard_violation_support_descriptors_do_not_separate_candidates"
SOURCE_NEXT_WORK = "diagnose_lane_hard_support_descriptor_bottleneck_before_retraining"
NEXT_WORK = "reject_lane_hard_standalone_or_design_joint_progress_lane_hard_screen"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only bottleneck diagnosis for a rejected lane/hard-violation "
            "support descriptor separability screen. It reuses existing matched "
            "nonformal logs and does not train CAMP, run DP, or change the "
            "online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
        separability_report=_load_json(args.separability_json),
        label=args.label,
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
    separability_report: dict[str, Any],
    label: str | None = None,
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
        separability_report=separability_report,
        label=label,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(separability_report)
    best = _best_screen(separability_report)
    rows, formal_seed_records = _rows_from_items(items)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    tradeoff = _screen_tradeoff(separability_report)
    screen_rows = _apply_screen(alternative_rows, best)
    grouped = _group_rows(screen_rows)
    diagnosis = _diagnosis(tradeoff, grouped, best)
    final = {
        "status": READY_STATUS if source["passed"] and best else SOURCE_BLOCKED_STATUS,
        "passed": bool(source["passed"] and best),
        "primary_gap": (
            diagnosis["primary_gap"] if source["passed"] and best else "source_not_ready"
        ),
        "authorized_next_work": (
            NEXT_WORK
            if source["passed"] and best
            else "fix_lane_hard_separability_source_before_bottleneck_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_lane_hard_violation_support_separability_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "math_boundary": (
                "The diagnosis reuses fixed current-tick lane/hard support "
                "descriptors and the rejected offline screen. Candidate "
                "outcomes explain offline error modes only; they are not "
                "runtime selector inputs. If these descriptors are later "
                "atomized, they remain fixed coefficients in an affine "
                "score_k(w)=a_k^T w for the simplex/CVaR/L2 convex master. "
                "No DP-side classical Benders master/subproblem, dual, or cut "
                "is introduced."
            ),
        },
        "source_separability_gate": source,
        "source_records": _source_records(separability_report),
        "best_screen": best,
        "screen_tradeoff": tradeoff,
        "screen_applications": _screen_applications(alternative_rows, tradeoff),
        "counts": _counts(grouped),
        "descriptor_overlap": _descriptor_overlap(alternative_rows),
        "diagnosis": diagnosis,
        "blocked_beneficial": _summary_for_rows(grouped["blocked_beneficial"], best),
        "allowed_harmful": _summary_for_rows(grouped["allowed_harmful"], best),
        "retained_beneficial": _summary_for_rows(grouped["retained_beneficial"], best),
        "blocked_harmful": _summary_for_rows(grouped["blocked_harmful"], best),
        "formal_seed_records": formal_seed_records,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _rows_from_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    specs = _descriptor_specs()
    for index, item in enumerate(items):
        record_rows, formal_seed = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            specs,
            min_value_gain=MIN_VALUE_GAIN,
            min_value_loss=MIN_VALUE_LOSS,
            progress_loss_budget_m=PROGRESS_LOSS_BUDGET_M,
        )
        rows.extend(record_rows)
        formal_seed_records += int(formal_seed)
    return rows, formal_seed_records


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    passed = (
        decision.get("passed") is False
        and status == SEPARABILITY_REJECT_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": decision.get("promising_screen_count"),
    }


def _source_records(report: dict[str, Any]) -> dict[str, Any]:
    records = report.get("records")
    if not isinstance(records, dict):
        return {}
    return {
        "total_records": records.get("total_records"),
        "candidate_rows": records.get("candidate_rows"),
        "alternative_rows": records.get("alternative_rows"),
        "formal_seed_records": records.get("formal_seed_records"),
        "class_counts": records.get("class_counts"),
    }


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    failure_gap = report.get("failure_gap")
    if isinstance(failure_gap, dict) and isinstance(failure_gap.get("best_screen"), dict):
        return failure_gap["best_screen"]
    ranked = report.get("ranked_screens")
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return ranked[0]
    return None


def _available_screens(report: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[tuple[str, float]] = set()
    screens: list[dict[str, Any]] = []
    for key in ("ranked_screens", "single_descriptor_screens", "affine_screens"):
        rows = report.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            marker = (str(row.get("screen_name")), float(row.get("threshold", 0.0)))
            if marker in seen:
                continue
            seen.add(marker)
            screens.append(row)
    return screens


def _screen_tradeoff(report: dict[str, Any]) -> dict[str, Any]:
    screens = _available_screens(report)
    strict = [
        screen
        for screen in screens
        if float(screen.get("harmful_block_rate", 0.0)) >= 0.75
        and float(screen.get("allowed_harmful_rate", 1.0)) <= ALLOWED_HARMFUL_RATE_TARGET
    ]
    high_retain = [
        screen
        for screen in screens
        if float(screen.get("beneficial_retain_rate", 0.0)) >= BENEFICIAL_RETAIN_RATE_TARGET
    ]
    strict_best = max(
        strict,
        key=lambda row: (
            float(row.get("beneficial_retain_rate", 0.0)),
            float(row.get("harmful_block_rate", 0.0)),
            -float(row.get("allowed_harmful_rate", 1.0)),
        ),
        default=None,
    )
    high_retain_best = min(
        high_retain,
        key=lambda row: (
            float(row.get("allowed_harmful_rate", 1.0)),
            -float(row.get("harmful_block_rate", 0.0)),
            -float(row.get("beneficial_retain_rate", 0.0)),
        ),
        default=None,
    )
    return {
        "strict_safe_screen_count": len(strict),
        "best_strict_safe_screen": _screen_summary(strict_best),
        "high_retain_screen_count": len(high_retain),
        "best_high_retain_screen": _screen_summary(high_retain_best),
    }


def _screen_summary(screen: dict[str, Any] | None) -> dict[str, Any] | None:
    if screen is None:
        return None
    return {
        "screen_name": screen.get("screen_name"),
        "descriptor_names": screen.get("descriptor_names"),
        "coefficients": screen.get("coefficients"),
        "threshold": screen.get("threshold"),
        "harmful_block_rate": screen.get("harmful_block_rate"),
        "beneficial_retain_rate": screen.get("beneficial_retain_rate"),
        "allowed_harmful_rate": screen.get("allowed_harmful_rate"),
        "allowed_candidates": screen.get("allowed_candidates"),
    }


def _apply_screen(rows: list[dict[str, Any]], screen: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not screen:
        return []
    names = tuple(str(name) for name in screen.get("descriptor_names", []))
    coefficients = {
        str(name): float(value)
        for name, value in (screen.get("coefficients") or {}).items()
    }
    threshold = float(screen.get("threshold", 0.0))
    result = []
    for row in rows:
        ok = bool(names)
        score = 0.0
        contributions: dict[str, float] = {}
        for name in names:
            value = row["features"].get(name)
            if value is None or not np.isfinite(float(value)):
                ok = False
                break
            coeff = coefficients.get(name, 0.0)
            contribution = coeff * float(value)
            contributions[name] = contribution
            score += contribution
        result.append(
            {
                **row,
                "screen_score": score if ok else None,
                "screen_allowed": bool(ok and score <= threshold + 1e-12),
                "screen_contributions": contributions,
            }
        )
    return result


def _group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "blocked_beneficial": [
            row
            for row in rows
            if row["class"] == CLASS_BENEFICIAL and not row["screen_allowed"]
        ],
        "retained_beneficial": [
            row
            for row in rows
            if row["class"] == CLASS_BENEFICIAL and row["screen_allowed"]
        ],
        "allowed_harmful": [
            row
            for row in rows
            if row["class"] == CLASS_HARMFUL and row["screen_allowed"]
        ],
        "blocked_harmful": [
            row
            for row in rows
            if row["class"] == CLASS_HARMFUL and not row["screen_allowed"]
        ],
        "neutral": [row for row in rows if row["class"] == CLASS_NEUTRAL],
    }


def _counts(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    beneficial_total = len(grouped["blocked_beneficial"]) + len(grouped["retained_beneficial"])
    harmful_total = len(grouped["allowed_harmful"]) + len(grouped["blocked_harmful"])
    return {
        "beneficial_total": beneficial_total,
        "beneficial_blocked": len(grouped["blocked_beneficial"]),
        "beneficial_retained": len(grouped["retained_beneficial"]),
        "harmful_total": harmful_total,
        "harmful_allowed": len(grouped["allowed_harmful"]),
        "harmful_blocked": len(grouped["blocked_harmful"]),
        "neutral_total": len(grouped["neutral"]),
    }


def _screen_applications(
    rows: list[dict[str, Any]],
    tradeoff: dict[str, Any],
) -> dict[str, Any]:
    applications = {}
    for key in ("best_strict_safe_screen", "best_high_retain_screen"):
        screen = tradeoff.get(key)
        if not isinstance(screen, dict):
            applications[key] = None
            continue
        grouped = _group_rows(_apply_screen(rows, screen))
        applications[key] = {
            "counts": _counts(grouped),
            "blocked_beneficial": _summary_for_rows(
                grouped["blocked_beneficial"],
                screen,
            ),
            "allowed_harmful": _summary_for_rows(
                grouped["allowed_harmful"],
                screen,
            ),
        }
    return applications


def _diagnosis(
    tradeoff: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    best: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = _counts(grouped)
    beneficial_retain_rate = _rate(counts["beneficial_retained"], counts["beneficial_total"])
    allowed_harmful_rate = _rate(
        counts["harmful_allowed"],
        counts["harmful_allowed"] + counts["beneficial_retained"],
    )
    strict_best = tradeoff["best_strict_safe_screen"] or {}
    high_retain_best = tradeoff["best_high_retain_screen"] or {}
    strict_overblocks = (
        bool(strict_best)
        and float(strict_best.get("beneficial_retain_rate", 0.0))
        < BENEFICIAL_RETAIN_RATE_TARGET
    )
    high_retain_allows_harmful = (
        bool(high_retain_best)
        and float(high_retain_best.get("allowed_harmful_rate", 1.0))
        > ALLOWED_HARMFUL_RATE_TARGET
    )
    if strict_overblocks and high_retain_allows_harmful:
        primary = "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
    elif strict_overblocks:
        primary = "strict_screens_overblock_beneficial"
    elif high_retain_allows_harmful:
        primary = "high_retain_screens_allow_harmful"
    else:
        primary = "lane_hard_descriptor_overlap_requires_new_joint_or_state_descriptor"
    return {
        "primary_gap": primary,
        "best_screen_name": None if best is None else best.get("screen_name"),
        "best_screen_beneficial_retain_rate": beneficial_retain_rate,
        "best_screen_allowed_harmful_rate_among_allowed_nonneutral": allowed_harmful_rate,
        "strict_safe_screen_count": tradeoff["strict_safe_screen_count"],
        "high_retain_screen_count": tradeoff["high_retain_screen_count"],
        "standalone_lane_hard_route_recommended": False,
        "joint_progress_lane_hard_design_only_recommended": True,
        "camp_retraining_recommended": False,
    }


def _descriptor_overlap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    beneficial = [row for row in rows if row["class"] == CLASS_BENEFICIAL]
    harmful = [row for row in rows if row["class"] == CLASS_HARMFUL]
    descriptors = sorted(
        {
            name
            for row in rows
            for name, value in row["features"].items()
            if np.isfinite(float(value))
        }
    )
    summaries = []
    for name in descriptors:
        b = _values(beneficial, name)
        h = _values(harmful, name)
        if b.size == 0 or h.size == 0:
            continue
        bq = _quantiles(b)
        hq = _quantiles(h)
        harmful_below_beneficial_p75 = _rate(
            int(np.sum(h <= bq["p75"] + 1e-12)),
            h.size,
        )
        beneficial_above_harmful_p25 = _rate(
            int(np.sum(b >= hq["p25"] - 1e-12)),
            b.size,
        )
        overlap_low = max(bq["min"], hq["min"])
        overlap_high = min(bq["max"], hq["max"])
        summaries.append(
            {
                "descriptor": name,
                "beneficial": bq,
                "harmful": hq,
                "intervals_overlap": bool(overlap_low <= overlap_high + 1e-12),
                "harmful_below_beneficial_p75_rate": harmful_below_beneficial_p75,
                "beneficial_above_harmful_p25_rate": beneficial_above_harmful_p25,
                "overlap_pressure": float(
                    0.5
                    * (
                        harmful_below_beneficial_p75
                        + beneficial_above_harmful_p25
                    )
                ),
            }
        )
    ranked = sorted(
        summaries,
        key=lambda row: (
            -float(row["overlap_pressure"]),
            str(row["descriptor"]),
        ),
    )
    return {
        "beneficial_count": len(beneficial),
        "harmful_count": len(harmful),
        "top_overlap_descriptors": ranked[:10],
    }


def _summary_for_rows(
    rows: list[dict[str, Any]],
    best: dict[str, Any] | None,
) -> dict[str, Any]:
    names = [] if best is None else [str(name) for name in best.get("descriptor_names", [])]
    return {
        "count": len(rows),
        "outcome_summary": {
            "value_delta_mean": _mean([row["outcome_value_delta_vs_top1"] for row in rows]),
            "progress_delta_mean_m": _mean([row["progress_delta_vs_top1_m"] for row in rows]),
            "hard_violation_delta_mean": _mean([row["hard_violation_delta_vs_top1"] for row in rows]),
            "red_light_worse_count": sum(int(row["red_light_worse_than_top1"]) for row in rows),
            "lane_worse_count": sum(int(row["lane_worse_than_top1"]) for row in rows),
            "collision_worse_count": sum(int(row["collision_worse_than_top1"]) for row in rows),
            "near_miss_worse_count": sum(int(row["near_miss_worse_than_top1"]) for row in rows),
        },
        "screen_score_summary": _score_summary(rows),
        "descriptor_contribution_mean": {
            name: _mean([row["screen_contributions"].get(name, 0.0) for row in rows])
            for name in names
        },
        "reason_counts": _reason_counts(rows),
        "top_examples": _examples(rows, names),
    }


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason in _reasons(row):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    if row["progress_delta_vs_top1_m"] < -PROGRESS_LOSS_BUDGET_M:
        reasons.append("progress_loss")
    if row["outcome_value_delta_vs_top1"] <= -MIN_VALUE_LOSS:
        reasons.append("outcome_value_loss")
    if row["hard_violation_delta_vs_top1"] > 0:
        reasons.append("hard_violation_worse")
    if row["red_light_worse_than_top1"]:
        reasons.append("red_light_worse")
    if row["lane_worse_than_top1"]:
        reasons.append("lane_worse")
    if row["collision_worse_than_top1"]:
        reasons.append("collision_worse")
    if row["near_miss_worse_than_top1"]:
        reasons.append("near_miss_worse")
    if not reasons:
        reasons.append("beneficial_or_neutral_shape_overlap")
    return reasons


def _score_summary(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    scores = [row["screen_score"] for row in rows if row["screen_score"] is not None]
    if not scores:
        return {"min": None, "median": None, "max": None}
    array = np.asarray(scores, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "max": float(np.max(array)),
    }


def _examples(rows: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -float(row["screen_score"] or 0.0),
            row["context"].get("log_path", ""),
            int(row["context"].get("record_index", 0)),
            int(row["candidate_index"]),
        ),
    )
    examples = []
    for row in ranked[:8]:
        examples.append(
            {
                "log_path": row["context"].get("log_path"),
                "record_index": row["context"].get("record_index"),
                "candidate_index": row["candidate_index"],
                "screen_score": row["screen_score"],
                "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "hard_violation_delta_vs_top1": row["hard_violation_delta_vs_top1"],
                "reasons": _reasons(row),
                "descriptor_values": {name: row["features"].get(name) for name in names},
            }
        )
    return examples


def _values(rows: list[dict[str, Any]], name: str) -> np.ndarray:
    values = [
        float(row["features"][name])
        for row in rows
        if name in row["features"] and np.isfinite(float(row["features"][name]))
    ]
    return np.asarray(values, dtype=np.float64)


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "p75": float(np.percentile(values, 75)),
        "max": float(np.max(values)),
    }


def _mean(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.mean(array))


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Lane/Hard Support Separability Bottleneck Diagnosis",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Screen Tradeoff",
        "",
        "```json",
        json.dumps(report["screen_tradeoff"], indent=2, sort_keys=True),
        "```",
        "",
        "## Screen Applications",
        "",
        "```json",
        json.dumps(report["screen_applications"], indent=2, sort_keys=True),
        "```",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Diagnosis",
        "",
        "```json",
        json.dumps(report["diagnosis"], indent=2, sort_keys=True),
        "```",
        "",
        "## Descriptor Overlap",
        "",
        "```json",
        json.dumps(report["descriptor_overlap"], indent=2, sort_keys=True),
        "```",
        "",
        "## Blocked Beneficial",
        "",
        "```json",
        json.dumps(report["blocked_beneficial"], indent=2, sort_keys=True),
        "```",
        "",
        "## Allowed Harmful",
        "",
        "```json",
        json.dumps(report["allowed_harmful"], indent=2, sort_keys=True),
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
