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
    _available_screens,
    _counts,
    _descriptor_overlap,
    _group_rows,
    _rate,
    _screen_applications,
    _screen_summary,
    _summary_for_rows,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_TOP1,
    HARMFUL_BLOCK_RATE_TARGET,
    PAYLOAD_KEY,
    REJECT_STATUS as REVISED_SEPARABILITY_REJECT_STATUS,
    _candidate_rows,
    _class_counts,
    _descriptor_specs,
    _descriptor_values,
    _is_formal_seed,
    _load_json,
    _path_seeds,
    _record_candidate_count,
    _validate_payload,
)


READY_STATUS = "revised_context_atom_separability_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = (
    "revised_context_atom_separability_bottleneck_source_not_ready"
)

SOURCE_PRIMARY_GAP = "revised_context_atoms_do_not_separate_candidates"
SOURCE_NEXT_WORK = "diagnose_revised_context_atom_bottleneck_before_retraining"
NEXT_WORK = "revise_atom_label_or_objective_before_retraining"

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
            "Read-only bottleneck diagnosis for a rejected revised "
            "progress+lane/hard context atom separability screen. It reuses "
            "matched nonformal logs and does not train CAMP, run DP, promote "
            "an online selector, or claim a DP-side classical Benders cut."
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
    rows, formal_seed_records, missing_outcome_records, payload_candidate_rows = (
        _rows_from_items(items)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    tradeoff = _screen_tradeoff(separability_report)
    screen_rows = _apply_screen(alternative_rows, best)
    grouped = _group_rows(screen_rows)
    diagnosis = _diagnosis(tradeoff, grouped, best)
    source_ready = bool(source["passed"] and best and rows and not missing_outcome_records)
    final = {
        "status": READY_STATUS if source_ready else SOURCE_BLOCKED_STATUS,
        "passed": source_ready,
        "primary_gap": (
            diagnosis["primary_gap"]
            if source_ready
            else _blocked_primary_gap(source, best, rows, missing_outcome_records)
        ),
        "authorized_next_work": (
            NEXT_WORK
            if source_ready
            else "fix_revised_atom_bottleneck_source_before_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_revised_context_atom_separability_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "predeclared_hypothesis": (
                "The rejected revised atom family is bottlenecked by atom/label "
                "overlap: strict low-risk thresholds overblock beneficial "
                "alternatives, while high-retain thresholds would allow harmful "
                "alternatives. This must be diagnosed before any CAMP retraining."
            ),
            "math_boundary": (
                "The diagnosis reuses fixed current-tick revised atom "
                "coefficients emitted in the default-off payload. Candidate "
                "closed-loop outcomes explain offline error modes only; they "
                "are not runtime selector inputs and are not used to form atom "
                "values. Revised atoms remain finite candidate coefficients in "
                "an affine score_k(w)=a_k^T w, preserving compatibility with "
                "the simplex/CVaR/L2 convex CAMP master if later accepted. No "
                "DP-side classical Benders master/subproblem, dual, or cut is "
                "introduced here."
            ),
        },
        "source_separability_gate": source,
        "source_records": _source_records(separability_report),
        "best_screen": best,
        "screen_tradeoff": tradeoff,
        "screen_applications": _screen_applications(alternative_rows, tradeoff),
        "records": {
            "total_records": len(items),
            "payload_candidate_rows": payload_candidate_rows,
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "missing_outcome_records": missing_outcome_records,
            "formal_seed_records": formal_seed_records,
            "class_counts": _class_counts(alternative_rows),
        },
        "counts": _counts(grouped),
        "descriptor_overlap": _descriptor_overlap(alternative_rows),
        "diagnosis": diagnosis,
        "blocked_beneficial": _summary_for_rows(grouped["blocked_beneficial"], best),
        "allowed_harmful": _summary_for_rows(grouped["allowed_harmful"], best),
        "retained_beneficial": _summary_for_rows(grouped["retained_beneficial"], best),
        "blocked_harmful": _summary_for_rows(grouped["blocked_harmful"], best),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _rows_from_items(
    items: list[dict[str, Any]],
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
            _candidate_rows(
                raw,
                context,
                label,
                specs,
                feature_values=feature_values,
                min_value_gain=0.25,
                min_value_loss=0.25,
                progress_loss_budget_m=0.05,
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
        decision.get("passed") is False
        and status == REVISED_SEPARABILITY_REJECT_STATUS
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
        "outcome_records": records.get("outcome_records"),
        "missing_outcome_records": records.get("missing_outcome_records"),
        "candidate_rows": records.get("candidate_rows"),
        "classified_candidate_rows": records.get("classified_candidate_rows"),
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


def _screen_tradeoff(report: dict[str, Any]) -> dict[str, Any]:
    screens = _available_screens(report)
    strict = [
        screen
        for screen in screens
        if float(screen.get("harmful_block_rate", 0.0)) >= HARMFUL_BLOCK_RATE_TARGET
        and float(screen.get("allowed_harmful_rate", 1.0))
        <= ALLOWED_HARMFUL_RATE_TARGET
    ]
    high_retain = [
        screen
        for screen in screens
        if float(screen.get("beneficial_retain_rate", 0.0))
        >= BENEFICIAL_RETAIN_RATE_TARGET
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


def _diagnosis(
    tradeoff: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    best: dict[str, Any] | None,
) -> dict[str, Any]:
    counts = _counts(grouped)
    beneficial_retain_rate = _rate(
        counts["beneficial_retained"],
        counts["beneficial_total"],
    )
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
        primary = "strict_atom_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
        likely = "atom_label_overlap_or_objective_mismatch"
    elif strict_overblocks:
        primary = "strict_atom_screens_overblock_beneficial"
        likely = "atom_family_too_conservative_for_beneficial_alternatives"
    elif high_retain_allows_harmful:
        primary = "high_retain_atom_screens_allow_harmful"
        likely = "atom_family_too_weak_for_harmful_alternatives"
    elif counts["beneficial_total"] == 0 or counts["harmful_total"] == 0:
        primary = "matched_dataset_class_support_insufficient"
        likely = "scenario_support_bottleneck"
    else:
        primary = "revised_atom_overlap_requires_atom_or_label_revision"
        likely = "descriptor_overlap_or_label_definition_mismatch"
    return {
        "primary_gap": primary,
        "likely_bottleneck": likely,
        "best_screen_name": None if best is None else best.get("screen_name"),
        "best_screen_beneficial_retain_rate_on_logs": beneficial_retain_rate,
        "best_screen_allowed_harmful_rate_among_allowed_nonneutral": (
            allowed_harmful_rate
        ),
        "strict_safe_screen_count": tradeoff["strict_safe_screen_count"],
        "high_retain_screen_count": tradeoff["high_retain_screen_count"],
        "current_revised_atom_family_recommended_for_certificate": False,
        "camp_retraining_recommended": False,
        "stale_camp_weight_bottleneck_supported": False,
        "next_evidence_needed": (
            "diagnose whether the bottleneck comes from atom definitions, "
            "offline label/objective mismatch, scenario support, or DP "
            "candidate-set structure before considering CAMP retraining"
        ),
    }


def _blocked_primary_gap(
    source: dict[str, Any],
    best: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    missing_outcome_records: int,
) -> str:
    if not source.get("passed"):
        return "source_separability_gate_not_rejected_for_revised_atom_bottleneck"
    if best is None:
        return "source_separability_report_missing_best_screen"
    if missing_outcome_records:
        return "matched_outcomes_missing_for_revised_atom_bottleneck_diagnosis"
    if not rows:
        return "no_classified_candidate_rows_for_revised_atom_bottleneck_diagnosis"
    return "source_not_ready"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Revised Context Atom Separability Bottleneck Diagnosis",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_separability_gate"], indent=2, sort_keys=True),
        "```",
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
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
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
