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
    CLASS_TOP1,
    FORMAL_SEEDS,
    _class_counts,
    _load_json,
    _path_seeds,
)
from scripts.integrations.analyze_diffusion_planner_turn_logit_matched_outcome_atom_separability import (  # noqa: E402
    REJECT_STATUS as SEPARABILITY_REJECT_STATUS,
    _candidate_rows,
    _descriptor_specs,
)


READY_STATUS = "turn_logit_atom_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "turn_logit_atom_bottleneck_source_not_rejected"
FORMAL_SEED_STATUS = "turn_logit_atom_bottleneck_formal_seed_conflict"

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
            "Read-only bottleneck diagnostic for a rejected turn-logit atom "
            "separability screen. This explains why direct atomization is not "
            "ready; it does not run replay or train CAMP."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--margin_shortfall_budget", type=float, default=0.25)
    parser.add_argument("--min_value_gain", type=float, default=0.25)
    parser.add_argument("--min_value_loss", type=float, default=0.25)
    parser.add_argument("--progress_loss_budget_m", type=float, default=0.05)
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
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        margin_shortfall_budget=args.margin_shortfall_budget,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
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
    expected_logs: int | None = None,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    margin_shortfall_budget: float = 0.25,
    min_value_gain: float = 0.25,
    min_value_loss: float = 0.25,
    progress_loss_budget_m: float = 0.05,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    if expected_logs is not None and len(log_paths) != int(expected_logs):
        raise ValueError(f"log_count={len(log_paths)} expected={expected_logs}.")
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    descriptor_specs = _descriptor_specs()
    for log_path in log_paths:
        payload = _load_json(log_path)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        if expected_records is not None and len(payload) != int(expected_records):
            raise ValueError(
                f"{log_path} record_count={len(payload)} expected={expected_records}."
            )
        for record_index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            record_rows, formal_seed = _candidate_rows(
                raw,
                {
                    "log_path": str(log_path),
                    "record_index": record_index,
                    "path_seeds": sorted(_path_seeds(log_path)),
                },
                f"{log_path} record {record_index}",
                descriptor_specs,
                expected_candidates=expected_candidates,
                margin_shortfall_budget=margin_shortfall_budget,
                min_value_gain=min_value_gain,
                min_value_loss=min_value_loss,
                progress_loss_budget_m=progress_loss_budget_m,
            )
            rows.extend(record_rows)
            formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternatives = [row for row in rows if row["class"] != CLASS_TOP1]
    class_counts = _class_counts(alternatives)
    feature_summaries = {
        spec.name: _feature_summary(alternatives, spec.name) for spec in descriptor_specs
    }
    best_screen = (separability_report.get("failure_gap") or {}).get("best_screen")
    if not isinstance(best_screen, dict):
        ranked = separability_report.get("ranked_screens") or []
        best_screen = ranked[0] if ranked and isinstance(ranked[0], dict) else None
    source = _source_gate(separability_report)
    decision = _decision(
        source,
        formal_seed_records=formal_seed_records,
        class_counts=class_counts,
        best_screen=best_screen,
        feature_summaries=feature_summaries,
    )
    return {
        "analysis": {
            "name": "dp_camp_turn_logit_atom_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_features": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "math_boundary": (
                "This diagnostic reads existing matched nonformal logs and a "
                "rejected separability artifact. Turn-logit feature values are "
                "current-tick candidate coefficients; closed-loop outcomes are "
                "used only to explain offline beneficial/harmful class overlap. "
                "No online selector, CAMP retraining, DP modification, or "
                "classical Benders decomposition is authorized."
            ),
        },
        "source_gate": source,
        "records": {
            "total_records": len(rows) // int(expected_candidates),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternatives),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "feature_summaries": feature_summaries,
        "best_screen": best_screen,
        "bottleneck_summary": _bottleneck_summary(best_screen, feature_summaries),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _feature_summary(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    by_class = {}
    for cls in (CLASS_BENEFICIAL, CLASS_HARMFUL, CLASS_NEUTRAL):
        values = np.asarray(
            [
                float(row["features"][name])
                for row in rows
                if row["class"] == cls and name in row["features"]
            ],
            dtype=np.float64,
        )
        values = values[np.isfinite(values)]
        by_class[cls] = _stats(values)
    beneficial = np.asarray(
        [
            float(row["features"][name])
            for row in rows
            if row["class"] == CLASS_BENEFICIAL and name in row["features"]
        ],
        dtype=np.float64,
    )
    harmful = np.asarray(
        [
            float(row["features"][name])
            for row in rows
            if row["class"] == CLASS_HARMFUL and name in row["features"]
        ],
        dtype=np.float64,
    )
    beneficial = beneficial[np.isfinite(beneficial)]
    harmful = harmful[np.isfinite(harmful)]
    return {
        "by_class": by_class,
        "beneficial_lower_than_harmful_median": (
            _median(beneficial) is not None
            and _median(harmful) is not None
            and _median(beneficial) < _median(harmful)
        ),
        "beneficial_harmful_median_gap": (
            None
            if _median(beneficial) is None or _median(harmful) is None
            else _median(harmful) - _median(beneficial)
        ),
        "beneficial_harmful_iqr_overlap": _iqr_overlap(beneficial, harmful),
    }


def _stats(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
        }
    return {
        "count": int(values.size),
        "min": float(np.min(values)),
        "p10": float(np.percentile(values, 10)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.percentile(values, 50)),
        "p75": float(np.percentile(values, 75)),
        "p90": float(np.percentile(values, 90)),
        "max": float(np.max(values)),
    }


def _median(values: np.ndarray) -> float | None:
    if values.size == 0:
        return None
    return float(np.percentile(values, 50))


def _iqr_overlap(left: np.ndarray, right: np.ndarray) -> bool | None:
    if left.size == 0 or right.size == 0:
        return None
    left_low = float(np.percentile(left, 25))
    left_high = float(np.percentile(left, 75))
    right_low = float(np.percentile(right, 25))
    right_high = float(np.percentile(right, 75))
    return max(left_low, right_low) <= min(left_high, right_high)


def _source_gate(separability_report: dict[str, Any]) -> dict[str, Any]:
    decision = separability_report.get("final_decision")
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    return {
        "passed": decision.get("status") == SEPARABILITY_REJECT_STATUS
        and decision.get("passed") is False,
        "status": decision.get("status"),
        "passed_value": decision.get("passed"),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _decision(
    source: dict[str, Any],
    *,
    formal_seed_records: int,
    class_counts: dict[str, int],
    best_screen: dict[str, Any] | None,
    feature_summaries: dict[str, Any],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary = "separability_source_not_rejected"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary = "formal_seed_conflict"
    elif not best_screen:
        status = READY_STATUS
        primary = "no_finite_turn_logit_screen"
    elif int(best_screen.get("beneficial_count", 0)) <= 0:
        status = READY_STATUS
        primary = "beneficial_candidate_support_absent"
    elif float(best_screen.get("beneficial_retain_rate", 0.0)) <= 0.0:
        status = READY_STATUS
        primary = "best_screen_blocks_all_beneficial_candidates"
    elif all(
        summary["beneficial_harmful_iqr_overlap"] is True
        for summary in feature_summaries.values()
    ):
        status = READY_STATUS
        primary = "beneficial_harmful_feature_distributions_overlap"
    else:
        status = READY_STATUS
        primary = "turn_logit_screen_metrics_below_acceptance_threshold"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_bottleneck": primary,
        "class_counts": class_counts,
        "authorized_next_work": (
            "design_non_turn_logit_or_interaction_atoms_before_retraining"
            if status == READY_STATUS
            else None
        ),
        "CAMP_retraining_authorized": False,
        "online_selector_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "DP_modification_authorized": False,
    }


def _bottleneck_summary(
    best_screen: dict[str, Any] | None,
    feature_summaries: dict[str, Any],
) -> dict[str, Any]:
    return {
        "best_screen_name": None if not best_screen else best_screen.get("screen_name"),
        "best_screen_beneficial_retain_rate": (
            None if not best_screen else best_screen.get("beneficial_retain_rate")
        ),
        "best_screen_harmful_block_rate": (
            None if not best_screen else best_screen.get("harmful_block_rate")
        ),
        "best_screen_allowed_harmful_rate": (
            None if not best_screen else best_screen.get("allowed_harmful_rate")
        ),
        "features_with_beneficial_lower_median": sorted(
            name
            for name, summary in feature_summaries.items()
            if summary["beneficial_lower_than_harmful_median"] is True
        ),
        "features_with_beneficial_harmful_iqr_overlap": sorted(
            name
            for name, summary in feature_summaries.items()
            if summary["beneficial_harmful_iqr_overlap"] is True
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Turn-Logit Atom Bottleneck Diagnostic",
        "",
        "This is a read-only diagnostic over existing matched nonformal logs.",
        "",
        f"- status: `{decision['status']}`",
        f"- primary bottleneck: `{decision['primary_bottleneck']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Bottleneck Summary",
        "",
        "```json",
        json.dumps(report["bottleneck_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Feature Summaries",
        "",
        "```json",
        json.dumps(report["feature_summaries"], indent=2, sort_keys=True),
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
