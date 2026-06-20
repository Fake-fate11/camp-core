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
from scripts.integrations.analyze_diffusion_planner_progress_support_descriptor_separability import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    REJECT_STATUS as SEPARABILITY_REJECT_STATUS,
    _candidate_rows,
    _descriptor_specs,
    _load_json,
)


READY_STATUS = "progress_support_separability_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "progress_support_separability_bottleneck_source_not_ready"

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
            "Read-only bottleneck diagnosis for a rejected progress-support "
            "descriptor separability screen. It applies the best rejected "
            "screen to existing matched logs and explains blocked beneficial "
            "and allowed harmful alternatives."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
                    },
                }
            )
    return analyze_records(
        items,
        separability_report=separability_report,
        label=label,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_gate(separability_report)
    best = _best_screen(separability_report)
    rows = _rows_from_items(items, separability_report)
    alternative_rows = [row for row in rows if row["class"] != "top1_reference"]
    screen_rows = _apply_screen(alternative_rows, best)
    grouped = _group_rows(screen_rows)
    diagnosis = _diagnosis(grouped, best)
    final = {
        "status": READY_STATUS if source["passed"] and best else SOURCE_BLOCKED_STATUS,
        "passed": bool(source["passed"] and best),
        "primary_gap": diagnosis["primary_gap"] if source["passed"] and best else "source_not_ready",
        "authorized_next_work": (
            "reject_or_design_new_progress_support_descriptor_family"
            if source["passed"] and best
            else "fix_progress_support_separability_source_before_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_progress_support_separability_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "math_boundary": (
                "The diagnosis reuses fixed current-tick progress-support "
                "descriptors and the rejected offline threshold screen. "
                "Candidate outcomes explain offline error modes only; they "
                "are not runtime selector features. No CAMP training, online "
                "selector, DP modification, or classical Benders cut is "
                "introduced."
            ),
        },
        "source_separability_gate": source,
        "best_screen": best,
        "counts": _counts(grouped),
        "diagnosis": diagnosis,
        "blocked_beneficial": _summary_for_rows(
            grouped["blocked_beneficial"],
            best,
        ),
        "allowed_harmful": _summary_for_rows(
            grouped["allowed_harmful"],
            best,
        ),
        "retained_beneficial": _summary_for_rows(
            grouped["retained_beneficial"],
            best,
        ),
        "blocked_harmful": _summary_for_rows(
            grouped["blocked_harmful"],
            best,
        ),
        "final_decision": final,
    }


def _rows_from_items(
    items: list[dict[str, Any]],
    separability_report: dict[str, Any],
) -> list[dict[str, Any]]:
    params = separability_report.get("analysis", {})
    label_definition = params.get("label_definition", {})
    del label_definition
    rows: list[dict[str, Any]] = []
    specs = _descriptor_specs()
    for index, item in enumerate(items):
        record_rows, _ = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            specs,
            min_value_gain=0.25,
            min_value_loss=0.25,
            progress_loss_budget_m=0.05,
        )
        rows.extend(record_rows)
    return rows


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    passed = (
        decision.get("passed") is False
        and status == SEPARABILITY_REJECT_STATUS
        and primary_gap == "progress_support_descriptors_do_not_separate_candidates"
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    failure_gap = report.get("failure_gap")
    if isinstance(failure_gap, dict) and isinstance(failure_gap.get("best_screen"), dict):
        return failure_gap["best_screen"]
    ranked = report.get("ranked_screens")
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return ranked[0]
    return None


def _apply_screen(rows: list[dict[str, Any]], screen: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not screen:
        return []
    names = tuple(str(name) for name in screen.get("descriptor_names", []))
    coefficients = {
        str(name): float(value)
        for name, value in screen.get("coefficients", {}).items()
    }
    threshold = float(screen.get("threshold", 0.0))
    if not names:
        return []
    result = []
    for row in rows:
        score = 0.0
        ok = True
        contributions = {}
        for name in names:
            value = row["features"].get(name)
            if value is None or not np.isfinite(float(value)):
                ok = False
                break
            coeff = coefficients.get(name, 0.0)
            contribution = coeff * float(value)
            contributions[name] = contribution
            score += contribution
        allowed = bool(ok and score <= threshold + 1e-12)
        result.append(
            {
                **row,
                "screen_score": score if ok else None,
                "screen_allowed": allowed,
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


def _diagnosis(
    grouped: dict[str, list[dict[str, Any]]],
    best: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = _counts(grouped)
    beneficial_retain_rate = _rate(counts["beneficial_retained"], counts["beneficial_total"])
    allowed_harmful_rate = _rate(counts["harmful_allowed"], counts["harmful_allowed"] + counts["beneficial_retained"])
    if beneficial_retain_rate < 0.75 and allowed_harmful_rate > 0.10:
        primary = "beneficial_retain_low_and_allowed_harmful_high"
    elif beneficial_retain_rate < 0.75:
        primary = "beneficial_retain_rate_insufficient"
    elif allowed_harmful_rate > 0.10:
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "best_screen_rejected_by_secondary_condition"
    return {
        "primary_gap": primary,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_harmful_rate_among_allowed_nonneutral": allowed_harmful_rate,
        "screen_name": None if best is None else best.get("screen_name"),
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
        "top_examples": _examples(rows, names),
    }


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
    for row in ranked[:5]:
        examples.append(
            {
                "log_path": row["context"].get("log_path"),
                "record_index": row["context"].get("record_index"),
                "candidate_index": row["candidate_index"],
                "screen_score": row["screen_score"],
                "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "hard_violation_delta_vs_top1": row["hard_violation_delta_vs_top1"],
                "descriptor_values": {
                    name: row["features"].get(name)
                    for name in names
                },
            }
        )
    return examples


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
        "# Progress-Support Separability Bottleneck Diagnosis",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
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
