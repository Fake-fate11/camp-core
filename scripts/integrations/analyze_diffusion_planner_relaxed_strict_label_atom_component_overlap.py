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
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_separability_bottleneck import (  # noqa: E402
    _apply_screen,
    _counts,
    _group_rows,
    _rate,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_bottleneck import (  # noqa: E402
    NEXT_WORK_NEW_ATOM as SOURCE_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
    _rows_from_items,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_separability import (  # noqa: E402
    BLOCKED_ACTIONS,
    _descriptor_specs,
    _load_json,
    _path_seeds,
)


READY_STATUS = "relaxed_strict_label_atom_component_overlap_diagnosed"
SOURCE_BLOCKED_STATUS = "relaxed_strict_label_atom_component_overlap_source_not_ready"

SOURCE_PRIMARY_GAP = "relaxed_strict_atom_threshold_tradeoff_overblocks_or_leaks_harmful"
NEXT_WORK_REDESIGN = "predeclare_component_level_no_leak_atom_redesign"
NEXT_WORK_LIMITATION = "record_relaxed_strict_atom_observability_limit"

DEFAULT_TARGET_RETAIN_RATE = 0.10
DEFAULT_MIN_GOOD_RETAIN_RATE = 0.50
DEFAULT_HARMFUL_BLOCK_RATE_TARGET = 0.95
DEFAULT_ALLOWED_HARMFUL_RATE_TARGET = 0.10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare blocked beneficial alternatives against harmful "
            "alternatives newly admitted by relaxing the rejected relaxed "
            "strict atom screen. This is offline-only and uses closed-loop "
            "outcomes only for labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--target_retain_rate", type=float, default=DEFAULT_TARGET_RETAIN_RATE)
    parser.add_argument(
        "--min_good_retain_rate",
        type=float,
        default=DEFAULT_MIN_GOOD_RETAIN_RATE,
    )
    parser.add_argument(
        "--harmful_block_rate_target",
        type=float,
        default=DEFAULT_HARMFUL_BLOCK_RATE_TARGET,
    )
    parser.add_argument(
        "--allowed_harmful_rate_target",
        type=float,
        default=DEFAULT_ALLOWED_HARMFUL_RATE_TARGET,
    )
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
        bottleneck_report=_load_json(args.bottleneck_json),
        label=args.label,
        target_retain_rate=args.target_retain_rate,
        min_good_retain_rate=args.min_good_retain_rate,
        harmful_block_rate_target=args.harmful_block_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
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
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    target_retain_rate: float = DEFAULT_TARGET_RETAIN_RATE,
    min_good_retain_rate: float = DEFAULT_MIN_GOOD_RETAIN_RATE,
    harmful_block_rate_target: float = DEFAULT_HARMFUL_BLOCK_RATE_TARGET,
    allowed_harmful_rate_target: float = DEFAULT_ALLOWED_HARMFUL_RATE_TARGET,
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
        bottleneck_report=bottleneck_report,
        label=label,
        target_retain_rate=target_retain_rate,
        min_good_retain_rate=min_good_retain_rate,
        harmful_block_rate_target=harmful_block_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    target_retain_rate: float = DEFAULT_TARGET_RETAIN_RATE,
    min_good_retain_rate: float = DEFAULT_MIN_GOOD_RETAIN_RATE,
    harmful_block_rate_target: float = DEFAULT_HARMFUL_BLOCK_RATE_TARGET,
    allowed_harmful_rate_target: float = DEFAULT_ALLOWED_HARMFUL_RATE_TARGET,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(bottleneck_report)
    params = _selected_label_params(bottleneck_report)
    best_screen = _best_screen(bottleneck_report)
    rows, payload_rows, formal_seed_records, missing_outcome_records = _rows_from_items(
        items,
        params=params,
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != "top1"]
    screened = _apply_screen(alternative_rows, best_screen)
    grouped = _group_rows(screened)
    blocked_beneficial = grouped["blocked_beneficial"]
    leaked_harmful, relaxation = _newly_admitted_harmful(
        screened,
        target_retain_rate=target_retain_rate,
    )
    component_screens = _component_screens(
        blocked_beneficial,
        leaked_harmful,
        min_good_retain_rate=min_good_retain_rate,
        harmful_block_rate_target=harmful_block_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )
    best_component = component_screens[0] if component_screens else None
    diagnosis = _diagnosis(best_component, blocked_beneficial, leaked_harmful)
    source_ready = bool(
        source["passed"]
        and best_screen
        and rows
        and not missing_outcome_records
        and blocked_beneficial
        and leaked_harmful
    )
    final = {
        "status": READY_STATUS if source_ready else SOURCE_BLOCKED_STATUS,
        "passed": source_ready,
        "primary_gap": (
            diagnosis["primary_gap"]
            if source_ready
            else _blocked_primary_gap(
                source,
                best_screen,
                rows,
                missing_outcome_records,
                blocked_beneficial,
                leaked_harmful,
            )
        ),
        "authorized_next_work": (
            diagnosis["recommended_next_work"]
            if source_ready
            else "fix_component_overlap_source_before_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_relaxed_strict_label_atom_component_overlap_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "target_retain_rate_for_leakage": float(target_retain_rate),
            "accept_criteria": {
                "min_good_retain_rate": float(min_good_retain_rate),
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "allowed_harmful_rate": f"<= {allowed_harmful_rate_target}",
            },
            "math_boundary": (
                "This diagnostic compares fixed current-tick relaxed strict "
                "atom coefficients for blocked beneficial candidates and "
                "harmful candidates newly admitted by an offline threshold "
                "relaxation. Closed-loop outcomes define only the offline "
                "groups. Each component value is a nonnegative fixed "
                "finite-candidate coefficient a_k, so any later CAMP score "
                "would remain affine score_k(w)=a_k^T w and compatible with "
                "the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_bottleneck_gate": source,
        "best_screen": best_screen,
        "relaxation": relaxation,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(payload_rows),
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "missing_outcome_records": missing_outcome_records,
            "formal_seed_records": formal_seed_records,
        },
        "screen_counts": _counts(grouped),
        "group_counts": {
            "blocked_beneficial": len(blocked_beneficial),
            "newly_admitted_harmful": len(leaked_harmful),
        },
        "component_screens": component_screens,
        "best_component_screen": best_component,
        "group_summaries": {
            "blocked_beneficial": _summary_for_rows(blocked_beneficial),
            "newly_admitted_harmful": _summary_for_rows(leaked_harmful),
        },
        "diagnosis": diagnosis,
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
    blocked_actions = report.get("blocked_actions")
    blocked_clear = True
    if isinstance(blocked_actions, dict):
        blocked_clear = not any(bool(blocked_actions.get(key)) for key in BLOCKED_ACTIONS)
    passed = (
        bool(decision.get("passed"))
        and status == SOURCE_READY_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == SOURCE_NEXT_WORK
        and blocked_clear
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "blocked_actions_clear": blocked_clear,
    }


def _selected_label_params(report: dict[str, Any]) -> dict[str, float]:
    analysis = report.get("analysis") if isinstance(report, dict) else None
    params = analysis.get("selected_label_params") if isinstance(analysis, dict) else None
    if not isinstance(params, dict):
        raise ValueError("bottleneck report missing analysis.selected_label_params")
    required = (
        "progress_loss_budget_m",
        "comfort_jerk_delta_budget",
        "comfort_lateral_delta_budget",
        "safety_improvement_margin",
        "harmful_safety_margin",
    )
    missing = [key for key in required if key not in params]
    if missing:
        raise ValueError(f"bottleneck report label params missing {missing}")
    return {key: float(params[key]) for key in required}


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(report.get("best_screen"), dict):
        return report["best_screen"]
    failure_gap = report.get("source_failure_gap")
    if isinstance(failure_gap, dict) and isinstance(failure_gap.get("best_screen"), dict):
        return failure_gap["best_screen"]
    return None


def _newly_admitted_harmful(
    rows: list[dict[str, Any]],
    *,
    target_retain_rate: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    beneficial_scores = sorted(
        float(row["screen_score"])
        for row in rows
        if row["class"] == "beneficial_alternative" and row["screen_score"] is not None
    )
    if not beneficial_scores:
        return [], {"target_retain_rate": float(target_retain_rate), "threshold": None}
    count = max(1, int(np.ceil(float(target_retain_rate) * len(beneficial_scores))))
    threshold = beneficial_scores[min(count, len(beneficial_scores)) - 1]
    leaked = [
        row
        for row in rows
        if row["class"] == "harmful_alternative"
        and not row["screen_allowed"]
        and row["screen_score"] is not None
        and float(row["screen_score"]) <= threshold + 1e-12
    ]
    retained = [
        row
        for row in rows
        if row["class"] == "beneficial_alternative"
        and row["screen_score"] is not None
        and float(row["screen_score"]) <= threshold + 1e-12
    ]
    harmful_total = sum(int(row["class"] == "harmful_alternative") for row in rows)
    beneficial_total = sum(int(row["class"] == "beneficial_alternative") for row in rows)
    return leaked, {
        "target_retain_rate": float(target_retain_rate),
        "threshold": float(threshold),
        "beneficial_total": beneficial_total,
        "beneficial_retained_at_threshold": len(retained),
        "beneficial_retain_rate": _rate(len(retained), beneficial_total),
        "newly_admitted_harmful": len(leaked),
        "harmful_total": harmful_total,
        "harmful_block_rate_at_threshold": _rate(harmful_total - len(leaked), harmful_total),
    }


def _component_screens(
    good_rows: list[dict[str, Any]],
    bad_rows: list[dict[str, Any]],
    *,
    min_good_retain_rate: float,
    harmful_block_rate_target: float,
    allowed_harmful_rate_target: float,
) -> list[dict[str, Any]]:
    descriptors = [spec.name for spec in _descriptor_specs()]
    screens = []
    for name in descriptors:
        good_values = _values(good_rows, name)
        bad_values = _values(bad_rows, name)
        if good_values.size == 0 or bad_values.size == 0:
            continue
        best = _best_component_threshold(
            name,
            good_values,
            bad_values,
            min_good_retain_rate=min_good_retain_rate,
            harmful_block_rate_target=harmful_block_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
        )
        screens.append(best)
    return sorted(screens, key=_component_sort_key, reverse=True)


def _best_component_threshold(
    name: str,
    good_values: np.ndarray,
    bad_values: np.ndarray,
    *,
    min_good_retain_rate: float,
    harmful_block_rate_target: float,
    allowed_harmful_rate_target: float,
) -> dict[str, Any]:
    candidates = sorted({float(value) for value in np.concatenate([good_values, bad_values])})
    rows = []
    for threshold in candidates:
        good_allowed = int(np.sum(good_values <= threshold + 1e-12))
        bad_allowed = int(np.sum(bad_values <= threshold + 1e-12))
        good_total = int(good_values.size)
        bad_total = int(bad_values.size)
        allowed_total = good_allowed + bad_allowed
        good_retain_rate = _rate(good_allowed, good_total)
        harmful_block_rate = _rate(bad_total - bad_allowed, bad_total)
        allowed_harmful_rate = _rate(bad_allowed, allowed_total)
        promising = (
            good_retain_rate >= float(min_good_retain_rate)
            and harmful_block_rate >= float(harmful_block_rate_target)
            and allowed_harmful_rate <= float(allowed_harmful_rate_target)
        )
        rows.append(
            {
                "descriptor": name,
                "threshold": float(threshold),
                "good_retain_rate": good_retain_rate,
                "harmful_block_rate": harmful_block_rate,
                "allowed_harmful_rate": allowed_harmful_rate,
                "good_allowed": good_allowed,
                "harmful_allowed": bad_allowed,
                "promising_component_separator": promising,
            }
        )
    best = max(rows, key=_component_sort_key)
    best.update(
        {
            "good": _quantiles(good_values),
            "newly_admitted_harmful": _quantiles(bad_values),
            "lower_is_better_auc_good_vs_harmful": _auc_lower_is_better(
                good_values,
                bad_values,
            ),
            "intervals_overlap": bool(
                max(float(np.min(good_values)), float(np.min(bad_values)))
                <= min(float(np.max(good_values)), float(np.max(bad_values))) + 1e-12
            ),
            "harmful_below_good_p75_rate": _rate(
                int(np.sum(bad_values <= np.percentile(good_values, 75) + 1e-12)),
                int(bad_values.size),
            ),
            "good_above_harmful_p25_rate": _rate(
                int(np.sum(good_values >= np.percentile(bad_values, 25) - 1e-12)),
                int(good_values.size),
            ),
        }
    )
    return best


def _component_sort_key(row: dict[str, Any]) -> tuple[float, float, float, float, float, str]:
    return (
        float(row.get("promising_component_separator", False)),
        float(row.get("harmful_block_rate", 0.0)),
        float(row.get("good_retain_rate", 0.0)),
        -float(row.get("allowed_harmful_rate", 1.0)),
        float(row.get("lower_is_better_auc_good_vs_harmful") or 0.0),
        str(row.get("descriptor", "")),
    )


def _diagnosis(
    best_component: dict[str, Any] | None,
    blocked_beneficial: list[dict[str, Any]],
    leaked_harmful: list[dict[str, Any]],
) -> dict[str, Any]:
    found_separator = bool(
        best_component and best_component.get("promising_component_separator")
    )
    if found_separator:
        primary = "component_atom_separates_blocked_beneficial_from_leaked_harmful"
        next_work = NEXT_WORK_REDESIGN
    else:
        primary = "component_atoms_do_not_separate_blocked_beneficial_from_leaked_harmful"
        next_work = NEXT_WORK_LIMITATION
    return {
        "primary_gap": primary,
        "blocked_beneficial_count": len(blocked_beneficial),
        "newly_admitted_harmful_count": len(leaked_harmful),
        "best_component_descriptor": (
            None if best_component is None else best_component.get("descriptor")
        ),
        "promising_component_separator_found": found_separator,
        "new_atom_schema_recommended": found_separator,
        "camp_retraining_recommended": False,
        "online_selector_recommended": False,
        "recommended_next_work": next_work,
    }


def _summary_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "outcome_summary": {
            "value_delta_mean": _mean([row["outcome_value_delta_vs_top1"] for row in rows]),
            "progress_delta_mean_m": _mean([row["progress_delta_vs_top1_m"] for row in rows]),
            "safety_penalty_delta_mean": _mean(
                [row["safety_penalty_delta_vs_top1"] for row in rows]
            ),
            "jerk_delta_mean_mps3": _mean(
                [row["mean_jerk_delta_vs_top1_mps3"] for row in rows]
            ),
            "lateral_delta_mean_mps2": _mean(
                [row["mean_lateral_acceleration_delta_vs_top1_mps2"] for row in rows]
            ),
            "hard_safety_worse_count": sum(int(row["hard_safety_worse_than_top1"]) for row in rows),
            "red_light_worse_count": sum(int(row["red_light_worse_than_top1"]) for row in rows),
            "lane_worse_count": sum(int(row["lane_worse_than_top1"]) for row in rows),
            "collision_worse_count": sum(int(row["collision_worse_than_top1"]) for row in rows),
            "near_miss_worse_count": sum(int(row["near_miss_worse_than_top1"]) for row in rows),
        },
    }


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


def _auc_lower_is_better(good_values: np.ndarray, bad_values: np.ndarray) -> float | None:
    if good_values.size == 0 or bad_values.size == 0:
        return None
    wins = 0.0
    total = 0
    for good in good_values:
        for bad in bad_values:
            total += 1
            if good < bad:
                wins += 1.0
            elif good == bad:
                wins += 0.5
    return wins / total if total else None


def _mean(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.mean(array))


def _blocked_primary_gap(
    source: dict[str, Any],
    best_screen: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    missing_outcome_records: int,
    blocked_beneficial: list[dict[str, Any]],
    leaked_harmful: list[dict[str, Any]],
) -> str:
    if not source.get("passed"):
        return "source_bottleneck_gate_not_ready"
    if not best_screen:
        return "source_bottleneck_best_screen_missing"
    if missing_outcome_records:
        return "matched_outcomes_missing_for_component_overlap"
    if not rows:
        return "no_classified_rows_for_component_overlap"
    if not blocked_beneficial:
        return "no_blocked_beneficial_for_component_overlap"
    if not leaked_harmful:
        return "no_newly_admitted_harmful_for_component_overlap"
    return "source_not_ready"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Relaxed Strict-Label Atom Component Overlap",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_bottleneck_gate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Relaxation",
        "",
        "```json",
        json.dumps(report["relaxation"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Component Screen",
        "",
        "```json",
        json.dumps(report["best_component_screen"], indent=2, sort_keys=True),
        "```",
        "",
        "## Component Screens",
        "",
        "| Rank | Descriptor | Promising | Good Retain | Harmful Block | Allowed Harmful | AUC |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for index, row in enumerate(report["component_screens"][:10], start=1):
        auc = row.get("lower_is_better_auc_good_vs_harmful")
        lines.append(
            f"| {index} | `{row['descriptor']}` | "
            f"`{row['promising_component_separator']}` | "
            f"{row['good_retain_rate']:.3f} | "
            f"{row['harmful_block_rate']:.3f} | "
            f"{row['allowed_harmful_rate']:.3f} | "
            f"{0.0 if auc is None else float(auc):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Group Summaries",
            "",
            "```json",
            json.dumps(report["group_summaries"], indent=2, sort_keys=True),
            "```",
            "",
            "## Diagnosis",
            "",
            "```json",
            json.dumps(report["diagnosis"], indent=2, sort_keys=True),
            "```",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
