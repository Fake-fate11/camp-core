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
    _descriptor_overlap,
    _group_rows,
    _rate,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_sensitivity import (  # noqa: E402
    DIAGNOSED_STATUS as SENSITIVITY_DIAGNOSED_STATUS,
    NEXT_WORK_SUPPORT_FOUND,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_separability import (  # noqa: E402
    _strict_candidate_rows,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    BLOCKED_ACTIONS,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    PAYLOAD_KEY,
    _descriptor_specs,
    _descriptor_values,
    _is_formal_seed,
    _load_json,
    _path_seeds,
    _record_candidate_count,
    _validate_payload,
)


READY_STATUS = "revised_context_relaxed_strict_label_atom_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = (
    "revised_context_relaxed_strict_label_atom_bottleneck_source_not_ready"
)

SOURCE_PRIMARY_GAP = (
    "support_exists_but_revised_atoms_do_not_separate_relaxed_strict_label"
)

NEXT_WORK_ATOM_SCHEMA = "predeclare_relaxed_strict_label_no_leak_atom_schema"
NEXT_WORK_SUPPORT_LIMITED = "record_relaxed_strict_label_candidate_support_limit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only bottleneck diagnosis for the best relaxed strict-label "
            "setting found by threshold sensitivity. It explains why revised "
            "atoms block strict-good candidates or allow harmful candidates."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--sensitivity_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--grid_choice",
        choices=("best_by_support", "best_by_screen"),
        default="best_by_support",
    )
    parser.add_argument("--min_beneficial_block_rate_for_atom_gap", type=float, default=0.50)
    parser.add_argument("--max_allowed_harmful_rate_target", type=float, default=0.10)
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
        sensitivity_report=_load_json(args.sensitivity_json),
        label=args.label,
        grid_choice=args.grid_choice,
        min_beneficial_block_rate_for_atom_gap=args.min_beneficial_block_rate_for_atom_gap,
        max_allowed_harmful_rate_target=args.max_allowed_harmful_rate_target,
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
    sensitivity_report: dict[str, Any],
    label: str | None = None,
    grid_choice: str = "best_by_support",
    min_beneficial_block_rate_for_atom_gap: float = 0.50,
    max_allowed_harmful_rate_target: float = 0.10,
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
        sensitivity_report=sensitivity_report,
        label=label,
        grid_choice=grid_choice,
        min_beneficial_block_rate_for_atom_gap=min_beneficial_block_rate_for_atom_gap,
        max_allowed_harmful_rate_target=max_allowed_harmful_rate_target,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    sensitivity_report: dict[str, Any],
    label: str | None = None,
    grid_choice: str = "best_by_support",
    min_beneficial_block_rate_for_atom_gap: float = 0.50,
    max_allowed_harmful_rate_target: float = 0.10,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(sensitivity_report)
    selected_grid = _selected_grid(sensitivity_report, grid_choice)
    params = _grid_params(selected_grid)
    raw_best_screen = selected_grid.get("best_screen") if isinstance(selected_grid, dict) else None
    best_screen = _restore_screen_coefficients(raw_best_screen)
    rows, formal_seed_records, missing_outcome_records, payload_candidate_rows = (
        _rows_from_items(items, params=params)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    screened = _apply_screen(alternative_rows, best_screen)
    grouped = _group_rows(screened)
    counts = _counts(grouped)
    diagnosis = _diagnosis(
        counts,
        grouped,
        min_beneficial_block_rate_for_atom_gap=min_beneficial_block_rate_for_atom_gap,
        max_allowed_harmful_rate_target=max_allowed_harmful_rate_target,
    )
    source_ready = bool(
        source["passed"]
        and selected_grid
        and best_screen
        and rows
        and not missing_outcome_records
    )
    final = {
        "status": READY_STATUS if source_ready else SOURCE_BLOCKED_STATUS,
        "passed": source_ready,
        "primary_gap": (
            diagnosis["primary_gap"]
            if source_ready
            else _blocked_primary_gap(source, selected_grid, best_screen, rows, missing_outcome_records)
        ),
        "authorized_next_work": (
            diagnosis["recommended_next_work"]
            if source_ready
            else "fix_relaxed_strict_label_bottleneck_source_before_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_revised_context_relaxed_strict_label_atom_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "grid_choice": grid_choice,
            "math_boundary": (
                "This diagnosis reuses a fixed relaxed strict-label setting "
                "from the offline sensitivity artifact and fixed current-tick "
                "revised atom coefficients. Closed-loop outcomes explain "
                "offline error modes only; they are not runtime selector inputs. "
                "Any later atom proposal must remain a fixed candidate "
                "coefficient in affine score_k(w)=a_k^T w for the "
                "simplex/CVaR/L2 convex CAMP master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is introduced."
            ),
        },
        "source_sensitivity_gate": source,
        "selected_grid": selected_grid,
        "records": {
            "total_records": len(items),
            "payload_candidate_rows": payload_candidate_rows,
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "missing_outcome_records": missing_outcome_records,
            "formal_seed_records": formal_seed_records,
        },
        "counts": counts,
        "descriptor_overlap": _descriptor_overlap(alternative_rows),
        "diagnosis": diagnosis,
        "blocked_beneficial": _summary_for_rows(
            grouped["blocked_beneficial"],
            best_screen,
        ),
        "retained_beneficial": _summary_for_rows(
            grouped["retained_beneficial"],
            best_screen,
        ),
        "allowed_harmful": _summary_for_rows(
            grouped["allowed_harmful"],
            best_screen,
        ),
        "blocked_harmful": _summary_for_rows(
            grouped["blocked_harmful"],
            best_screen,
        ),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _rows_from_items(
    items: list[dict[str, Any]],
    *,
    params: dict[str, float],
) -> tuple[list[dict[str, Any]], int, int, int]:
    specs = _descriptor_specs()
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_outcome_records = 0
    payload_candidate_rows = 0
    for index, item in enumerate(items):
        raw = item["raw"]
        context = item["context"]
        label = f"record {index}"
        payload = raw.get(PAYLOAD_KEY)
        outcomes = raw.get("candidate_closed_loop_outcomes")
        candidate_count = _record_candidate_count(raw, payload, outcomes, label)
        payload_candidate_rows += int(candidate_count)
        _validate_payload(payload, candidate_count, label)
        formal_seed_records += int(_is_formal_seed(raw, context))
        if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
            missing_outcome_records += 1
            continue
        feature_values = _descriptor_values(payload, specs, candidate_count, label)
        rows.extend(
            _strict_candidate_rows(
                raw,
                context,
                label,
                specs,
                feature_values=feature_values,
                progress_loss_budget_m=params["progress_loss_budget_m"],
                comfort_jerk_delta_budget=params["comfort_jerk_delta_budget"],
                comfort_lateral_delta_budget=params["comfort_lateral_delta_budget"],
                safety_improvement_margin=params["safety_improvement_margin"],
                harmful_safety_margin=params["harmful_safety_margin"],
            )
        )
    return rows, formal_seed_records, missing_outcome_records, payload_candidate_rows


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == SENSITIVITY_DIAGNOSED_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == NEXT_WORK_SUPPORT_FOUND
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
    }


def _selected_grid(report: dict[str, Any], grid_choice: str) -> dict[str, Any] | None:
    summary = report.get("grid_summary")
    if not isinstance(summary, dict):
        return None
    selected = summary.get(grid_choice)
    return selected if isinstance(selected, dict) else None


def _grid_params(selected_grid: dict[str, Any] | None) -> dict[str, float]:
    params = selected_grid.get("params") if isinstance(selected_grid, dict) else None
    if not isinstance(params, dict):
        return {
            "progress_loss_budget_m": 0.0,
            "safety_improvement_margin": 0.0,
            "comfort_jerk_delta_budget": 0.0,
            "comfort_lateral_delta_budget": 0.0,
            "harmful_safety_margin": 0.05,
        }
    return {
        "progress_loss_budget_m": float(params.get("progress_loss_budget_m", 0.0)),
        "safety_improvement_margin": float(params.get("safety_improvement_margin", 0.0)),
        "comfort_jerk_delta_budget": float(params.get("comfort_jerk_delta_budget", 0.0)),
        "comfort_lateral_delta_budget": float(params.get("comfort_lateral_delta_budget", 0.0)),
        "harmful_safety_margin": 0.05,
    }


def _restore_screen_coefficients(screen: Any) -> dict[str, Any] | None:
    if not isinstance(screen, dict):
        return None
    names = [str(name) for name in screen.get("descriptor_names") or []]
    if not names:
        return None
    coefficients = screen.get("coefficients")
    if not isinstance(coefficients, dict):
        coefficients = _coefficients_from_screen_name(str(screen.get("screen_name", "")), names)
    return {
        **screen,
        "descriptor_names": names,
        "coefficients": coefficients,
    }


def _coefficients_from_screen_name(
    screen_name: str,
    names: list[str],
) -> dict[str, float]:
    if not screen_name.startswith("affine_simplex:"):
        return {names[0]: 1.0} if len(names) == 1 else {name: 1.0 for name in names}
    coefficients: dict[str, float] = {}
    body = screen_name.split(":", 1)[1]
    for part in body.split("+"):
        if "*" not in part:
            continue
        raw_coeff, raw_name = part.split("*", 1)
        raw_name = raw_name.strip()
        if raw_name in names:
            coefficients[raw_name] = float(raw_coeff)
    missing = [name for name in names if name not in coefficients]
    if missing:
        fallback = 1.0 / float(len(names))
        for name in missing:
            coefficients[name] = fallback
    return coefficients


def _diagnosis(
    counts: dict[str, int],
    grouped: dict[str, list[dict[str, Any]]],
    *,
    min_beneficial_block_rate_for_atom_gap: float,
    max_allowed_harmful_rate_target: float,
) -> dict[str, Any]:
    beneficial_block_rate = _rate(
        counts["beneficial_blocked"],
        counts["beneficial_total"],
    )
    allowed_harmful_rate = _rate(
        counts["harmful_allowed"],
        counts["harmful_allowed"] + counts["beneficial_retained"],
    )
    atom_blocks_beneficial = beneficial_block_rate >= float(
        min_beneficial_block_rate_for_atom_gap
    )
    atom_allows_harmful = allowed_harmful_rate > float(max_allowed_harmful_rate_target)
    if atom_blocks_beneficial and atom_allows_harmful:
        primary = "relaxed_strict_label_atom_overlap_blocks_beneficial_and_allows_harmful"
        next_work = NEXT_WORK_ATOM_SCHEMA
    elif atom_blocks_beneficial:
        primary = "relaxed_strict_label_atoms_overblock_beneficial"
        next_work = NEXT_WORK_ATOM_SCHEMA
    elif atom_allows_harmful:
        primary = "relaxed_strict_label_atoms_allow_harmful"
        next_work = NEXT_WORK_ATOM_SCHEMA
    elif not grouped["blocked_beneficial"] and not grouped["allowed_harmful"]:
        primary = "selected_grid_screen_has_no_material_error_mode"
        next_work = NEXT_WORK_SUPPORT_LIMITED
    else:
        primary = "relaxed_strict_label_atom_bottleneck_mixed"
        next_work = NEXT_WORK_SUPPORT_LIMITED
    return {
        "primary_gap": primary,
        "beneficial_block_rate": beneficial_block_rate,
        "allowed_harmful_rate_among_allowed_nonneutral": allowed_harmful_rate,
        "atom_blocks_beneficial": atom_blocks_beneficial,
        "atom_allows_harmful": atom_allows_harmful,
        "current_revised_atom_family_recommended": False,
        "camp_retraining_recommended": False,
        "online_selector_recommended": False,
        "recommended_next_work": next_work,
    }


def _summary_for_rows(
    rows: list[dict[str, Any]],
    screen: dict[str, Any] | None,
) -> dict[str, Any]:
    names = [] if screen is None else [str(name) for name in screen.get("descriptor_names", [])]
    return {
        "count": len(rows),
        "outcome_summary": {
            "value_delta_mean": _mean([row["outcome_value_delta_vs_top1"] for row in rows]),
            "progress_delta_mean_m": _mean([row["progress_delta_vs_top1_m"] for row in rows]),
            "safety_penalty_delta_mean": _mean([row["safety_penalty_delta_vs_top1"] for row in rows]),
            "jerk_delta_mean_mps3": _mean([row["mean_jerk_delta_vs_top1_mps3"] for row in rows]),
            "lateral_delta_mean_mps2": _mean([row["mean_lateral_acceleration_delta_vs_top1_mps2"] for row in rows]),
            "hard_safety_worse_count": sum(int(row["hard_safety_worse_than_top1"]) for row in rows),
            "lane_worse_count": sum(int(row["lane_worse_than_top1"]) for row in rows),
            "red_light_worse_count": sum(int(row["red_light_worse_than_top1"]) for row in rows),
        },
        "screen_score_summary": _score_summary(rows),
        "descriptor_contribution_mean": {
            name: _mean([row["screen_contributions"].get(name, 0.0) for row in rows])
            for name in names
        },
        "dominant_contribution_counts": _dominant_contribution_counts(rows),
        "reason_counts": _reason_counts(rows),
        "top_examples": _examples(rows, names),
    }


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        reasons = []
        if not row["progress_compatible"]:
            reasons.append("progress_incompatible")
        if not row["jerk_compatible"]:
            reasons.append("jerk_incompatible")
        if not row["lateral_compatible"]:
            reasons.append("lateral_incompatible")
        if row["hard_safety_worse_than_top1"]:
            reasons.append("hard_safety_worse")
        if row["safety_penalty_delta_vs_top1"] >= 0.05:
            reasons.append("safety_penalty_worse")
        if row["class"] == CLASS_BENEFICIAL and not reasons:
            reasons.append("strict_good_blocked_by_atom_score")
        if not reasons:
            reasons.append("shape_overlap")
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _dominant_contribution_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        contributions = row.get("screen_contributions") or {}
        if not contributions:
            key = "none"
        else:
            key = max(contributions, key=lambda name: abs(float(contributions[name])))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _score_summary(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    values = [row.get("screen_score") for row in rows if row.get("screen_score") is not None]
    if not values:
        return {"min": None, "median": None, "max": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "max": float(np.max(array)),
    }


def _examples(rows: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -float(row.get("screen_score") or 0.0),
            str(row["context"].get("log_path", "")),
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
                "class": row["class"],
                "screen_score": row.get("screen_score"),
                "screen_allowed": row.get("screen_allowed"),
                "safety_penalty_delta_vs_top1": row["safety_penalty_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "jerk_delta_vs_top1_mps3": row["mean_jerk_delta_vs_top1_mps3"],
                "lateral_delta_vs_top1_mps2": row["mean_lateral_acceleration_delta_vs_top1_mps2"],
                "descriptor_values": {name: row["features"].get(name) for name in names},
            }
        )
    return examples


def _mean(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.mean(array))


def _blocked_primary_gap(
    source: dict[str, Any],
    selected_grid: dict[str, Any] | None,
    best_screen: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    missing_outcome_records: int,
) -> str:
    if not source.get("passed"):
        return "source_sensitivity_gate_not_ready"
    if not selected_grid:
        return "selected_sensitivity_grid_missing"
    if not best_screen:
        return "selected_sensitivity_grid_missing_best_screen"
    if missing_outcome_records:
        return "matched_outcomes_missing_for_relaxed_strict_label_bottleneck"
    if not rows:
        return "no_classified_rows_for_relaxed_strict_label_bottleneck"
    return "source_not_ready"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Relaxed Strict-Label Revised Atom Bottleneck",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Selected Grid",
        "",
        "```json",
        json.dumps(report["selected_grid"], indent=2, sort_keys=True),
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
