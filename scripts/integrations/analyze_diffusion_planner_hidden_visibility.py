#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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
from scripts.integrations.analyze_diffusion_planner_progress_proxy_guard import (  # noqa: E402
    _load_descriptors,
    _stats,
)
from scripts.integrations.analyze_diffusion_planner_top1_preservation import (  # noqa: E402
    BOOL_OUTCOMES,
    TOL,
    _load_record,
    _log_context,
    _outcome_mask_vs_candidate0,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_counterfactual import (  # noqa: E402
    _candidate_label_delta,
    _proxy_delta,
)
from scripts.integrations.analyze_diffusion_planner_top1_preserving_failure_attribution import (  # noqa: E402
    _outcome_oracle_failure_reasons,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


OUTCOME_PROGRESS_BUDGET_M = 0.05
BASE_PROGRESS_DELTA_MIN = -0.10
BASE_PROGRESS_DELTA_MAX = 0.05
ABSOLUTE_LATERAL_GUARD_MPS2 = 2.0

SCREEN_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "escape_p010_score0",
        "description": "score-nonworse escape inside progress_delta [-0.10, 0.10]",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": ({"field": "score_delta", "max": 0.0},),
    },
    {
        "name": "escape_p010_h10_p005_score0",
        "description": "score-nonworse escape additionally guarded by H10 loss <= 0.05 m",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": (
            {"field": "h10_distance_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_p010_h5_p005_score0",
        "description": "score-nonworse escape guarded by H5 loss <= 0.05 m",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": (
            {"field": "h5_distance_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_p010_step_p005_score0",
        "description": "score-nonworse escape guarded by step-reach loss <= 0.05 m",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": (
            {"field": "step_reach_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_p010_target_speed_p005_score0",
        "description": "score-nonworse escape guarded by target-speed loss <= 0.05 m/s",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": (
            {"field": "target_speed_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_p010_route_p005_score0",
        "description": "score-nonworse escape guarded by route-progress loss <= 0.05 m",
        "progress_delta_min": -0.10,
        "progress_delta_max": 0.10,
        "filters": (
            {"field": "route_progress_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_p005_score0",
        "description": (
            "route-progress lower-band recovery: allow progress_delta down to "
            "-2.0 m only when route-progress is nonworse than candidate0 and "
            "the CAMP score is nonworse"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_p005_h10_p005_score0",
        "description": (
            "same route-progress lower-band recovery with an additional "
            "H10 open-loop distance loss <= 0.05 m guard"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_h10_min_m005_score0",
        "description": (
            "route-progress lower-band sensitivity with H10 distance loss "
            ">= -0.05 m and CAMP score nonworse"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_h10_min_m010_score0",
        "description": (
            "route-progress lower-band sensitivity with H10 distance loss "
            ">= -0.10 m and CAMP score nonworse"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.10},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_h10_min_m015_score0",
        "description": (
            "route-progress lower-band sensitivity with H10 distance loss "
            ">= -0.15 m and CAMP score nonworse"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.15},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_route_nonworse_lower_m200_h10_min_m020_score0",
        "description": (
            "route-progress lower-band sensitivity with H10 distance loss "
            ">= -0.20 m and CAMP score nonworse"
        ),
        "progress_delta_min": -2.00,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.20},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "escape_lower_m020_p005_score0",
        "description": "lower-band recovery contrast: progress_delta [-0.20, 0.05] and score nonworse",
        "progress_delta_min": -0.20,
        "progress_delta_max": 0.05,
        "filters": ({"field": "score_delta", "max": 0.0},),
    },
    {
        "name": "escape_lower_m020_p005_h10_p005_score0",
        "description": "lower-band recovery contrast additionally guarded by H10 loss <= 0.05 m",
        "progress_delta_min": -0.20,
        "progress_delta_max": 0.05,
        "filters": (
            {"field": "h10_distance_loss", "max": 0.05},
            {"field": "score_delta", "max": 0.0},
        ),
    },
)

FEATURE_FIELDS: tuple[str, ...] = (
    "progress_delta",
    "score_delta",
    "h3_distance_loss",
    "h5_distance_loss",
    "h10_distance_loss",
    "step_reach_loss",
    "tracker_first_step_reach_loss",
    "target_speed_loss",
    "route_progress_loss",
    "proxy_lateral_delta",
    "proxy_jerk_delta",
    "union_red_delta",
    "red_stopping_delta",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline hidden-candidate visibility audit for the protected "
            "banded_shortfall_m010_p005 rule. Outcomes are posterior labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_examples", type=int, default=20)
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
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        max_examples=args.max_examples,
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


def analyze(
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    max_examples: int = 20,
) -> dict[str, Any]:
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            record = _load_record(raw_record, f"{log_path} record {record_index}")
            record["descriptors"] = _load_descriptors(
                raw_record,
                int(record["candidate_count"]),
                f"{log_path} record {record_index}",
            )
            record["context"] = context
            record["selection_step"] = int(raw_record.get("selection_step", record_index))
            record["record_index"] = int(record_index)
            records.append(record)

    candidate0_records = [
        record
        for record in records
        if record["feasible"].any() and bool(record["feasible"][0])
    ]
    hidden_rows = _hidden_rows(candidate0_records)
    risky_rows = _risky_common_rows(candidate0_records)
    screen_reports = [
        _screen_report(candidate0_records, spec, max_examples=max_examples)
        for spec in SCREEN_SPECS
    ]
    return {
        "analysis": {
            "name": "dp_camp_hidden_visibility_audit_v1",
            "label": label,
            "role": (
                "offline visibility audit for hidden oracle candidates under "
                "the protected banded_shortfall_m010_p005 rule"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "classical_benders_claim": False,
            "base_rule": {
                "name": "banded_shortfall_m010_p005",
                "progress_delta_min": BASE_PROGRESS_DELTA_MIN,
                "progress_delta_max": BASE_PROGRESS_DELTA_MAX,
                "absolute_lateral_guard_mps2": ABSOLUTE_LATERAL_GUARD_MPS2,
            },
            "outcome_progress_budget_m": OUTCOME_PROGRESS_BUDGET_M,
            "screen_specs": list(SCREEN_SPECS),
            "feature_fields": list(FEATURE_FIELDS),
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "math_boundary": (
                "All visibility features are fixed current-tick finite-candidate "
                "diagnostics already logged with the candidate set. Outcome "
                "labels identify hidden/recovered/false cases only and are not "
                "online selector inputs or cut sources. If any feature is later "
                "atomized, use fixed nonnegative transforms such as hinge losses "
                "or bounded-window violations so the CAMP score remains affine "
                "in master variables."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
            "candidate0_feasible": len(candidate0_records),
        },
        "base_rule": _base_rule_report(candidate0_records, hidden_rows, risky_rows),
        "feature_distributions": _feature_distribution_report(hidden_rows, risky_rows),
        "screens": screen_reports,
    }


def _hidden_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        base_mask = _base_mask(record)
        outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
        if base_mask.any() or not outcome_mask.any():
            continue
        best = _best_outcome_candidate(record, outcome_mask)
        rows.append(
            {
                "record": record,
                "candidate": best,
                "candidate_payload": _candidate_payload(record, best),
                "blockers": _base_blockers(record, best),
            }
        )
    return rows


def _risky_common_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        base_mask = _base_mask(record)
        if base_mask.any():
            continue
        common_mask = _common_mask(record)
        outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
        for candidate in np.flatnonzero(common_mask & ~outcome_mask):
            rows.append(
                {
                    "record": record,
                    "candidate": int(candidate),
                    "candidate_payload": _candidate_payload(record, int(candidate)),
                    "failure_reasons": _outcome_oracle_failure_reasons(
                        record,
                        int(candidate),
                        OUTCOME_PROGRESS_BUDGET_M,
                    ),
                }
            )
    return rows


def _base_rule_report(
    records: list[dict[str, Any]],
    hidden_rows: list[dict[str, Any]],
    risky_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    events = [_base_event(record) for record in records]
    overrides = [event for event in events if event["override"]]
    false_overrides = [event for event in overrides if event["false_override"]]
    true_overrides = [event for event in overrides if event["true_override"]]
    return {
        "candidate0_feasible_records": len(records),
        "override_records": len(overrides),
        "true_override_records": len(true_overrides),
        "false_override_records": len(false_overrides),
        "hidden_outcome_records": len(hidden_rows),
        "risky_common_candidates_in_hidden_contexts": len(risky_rows),
        "hidden_blocker_counts": _counter(
            blocker for row in hidden_rows for blocker in row["blockers"]
        ),
        "false_reason_counts": _counter(
            reason for event in false_overrides for reason in event["false_reasons"]
        ),
        "hard_gate_bool_worse_records": _bool_worse_summary(overrides),
        "candidate_label_safety_delta_overrides": _stats(
            [
                event["candidate_payload"]["candidate_label_delta"][
                    "candidate_label_safety_delta"
                ]
                for event in overrides
            ]
        ),
    }


def _base_event(record: dict[str, Any]) -> dict[str, Any]:
    mask = _base_mask(record)
    selected = _select_candidate(record, mask) if mask.any() else 0
    outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
    false_override = bool(selected != 0 and not outcome_mask[selected])
    return {
        "record": record,
        "selected": selected,
        "override": selected != 0,
        "true_override": bool(selected != 0 and outcome_mask[selected]),
        "false_override": false_override,
        "candidate_payload": _candidate_payload(record, selected),
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                selected,
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if false_override
            else []
        ),
    }


def _screen_report(
    records: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    max_examples: int,
) -> dict[str, Any]:
    events = [_screen_event(record, spec) for record in records]
    hidden_contexts = [event for event in events if event["base_hidden_outcome"]]
    escape_overrides = [event for event in events if event["escape_override"]]
    true_recoveries = [event for event in events if event["true_recovery"]]
    false_escapes = [event for event in events if event["false_escape"]]
    hidden_remaining = [event for event in events if event["hidden_remaining"]]
    return {
        "name": str(spec["name"]),
        "description": str(spec["description"]),
        "progress_delta_min": spec["progress_delta_min"],
        "progress_delta_max": spec["progress_delta_max"],
        "filters": list(spec["filters"]),
        "summary": {
            "candidate0_feasible_records": len(events),
            "base_hidden_context_records": len(hidden_contexts),
            "escape_override_records": len(escape_overrides),
            "true_recovery_records": len(true_recoveries),
            "false_escape_records": len(false_escapes),
            "hidden_remaining_records": len(hidden_remaining),
            "true_recovery_rate_among_hidden": len(true_recoveries)
            / max(len(hidden_contexts), 1),
            "false_escape_rate_among_escape_overrides": len(false_escapes)
            / max(len(escape_overrides), 1),
            "descriptor_missing_records": sum(
                int(event["descriptor_missing"]) for event in hidden_contexts
            ),
            "candidate_label_safety_delta_escape": _stats(
                [
                    event["selected_candidate"]["candidate_label_delta"][
                        "candidate_label_safety_delta"
                    ]
                    for event in escape_overrides
                ]
            ),
            "hard_gate_bool_worse_records": _bool_worse_summary(escape_overrides),
        },
        "by_bucket": _screen_bucket_report(hidden_contexts),
        "false_reason_counts": _counter(
            reason for event in false_escapes for reason in event["false_reasons"]
        ),
        "examples": {
            "true_recovery": _event_examples(true_recoveries, max_examples=max_examples),
            "false_escape": _event_examples(false_escapes, max_examples=max_examples),
            "hidden_remaining": _event_examples(hidden_remaining, max_examples=max_examples),
        },
    }


def _screen_event(record: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    base_mask = _base_mask(record)
    outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
    base_hidden = bool((not base_mask.any()) and outcome_mask.any())
    if base_mask.any():
        selected = _select_candidate(record, base_mask)
        descriptor_missing = False
        escape_mask = np.zeros(int(record["candidate_count"]), dtype=bool)
    else:
        escape_mask, descriptor_missing = _screen_mask(record, spec)
        selected = _select_candidate(record, escape_mask) if escape_mask.any() else 0
    escape_override = bool(base_hidden and selected != 0)
    false_escape = bool(escape_override and not outcome_mask[selected])
    best_hidden = _best_outcome_candidate(record, outcome_mask) if base_hidden else None
    return {
        "record": record,
        "selected": selected,
        "base_hidden_outcome": base_hidden,
        "escape_override": escape_override,
        "true_recovery": bool(escape_override and outcome_mask[selected]),
        "false_escape": false_escape,
        "hidden_remaining": bool(base_hidden and selected == 0),
        "descriptor_missing": descriptor_missing,
        "certificate_size": int(escape_mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "selected_candidate": _candidate_payload(record, selected),
        "best_hidden_candidate": (
            _candidate_payload(record, best_hidden) if best_hidden is not None else None
        ),
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                selected,
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if false_escape
            else []
        ),
    }


def _base_mask(record: dict[str, Any]) -> np.ndarray:
    progress_delta = _feature_values(record, "progress_delta")
    if progress_delta is None:
        raise ValueError("progress_delta must be available.")
    mask = _common_mask(record)
    mask &= progress_delta >= BASE_PROGRESS_DELTA_MIN - TOL
    mask &= progress_delta <= BASE_PROGRESS_DELTA_MAX + TOL
    return mask


def _screen_mask(
    record: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[np.ndarray, bool]:
    progress_delta = _feature_values(record, "progress_delta")
    if progress_delta is None:
        raise ValueError("progress_delta must be available.")
    mask = _common_mask(record)
    mask &= progress_delta >= float(spec["progress_delta_min"]) - TOL
    mask &= progress_delta <= float(spec["progress_delta_max"]) + TOL
    descriptor_missing = False
    for filter_spec in spec["filters"]:
        values = _feature_values(record, str(filter_spec["field"]))
        if values is None:
            descriptor_missing = True
            return np.zeros(int(record["candidate_count"]), dtype=bool), True
        if "max" in filter_spec:
            mask &= values <= float(filter_spec["max"]) + TOL
        if "min" in filter_spec:
            mask &= values >= float(filter_spec["min"]) - TOL
    return mask, descriptor_missing


def _common_mask(record: dict[str, Any]) -> np.ndarray:
    mask = record["feasible"].copy()
    mask[0] = False
    mask &= record["union_red"] <= record["union_red"][0] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][0] + TOL
    mask &= record["proxy_jerk"] <= record["proxy_jerk"][0] + TOL
    mask &= record["proxy_lateral"] <= record["proxy_lateral"][0] + TOL
    mask &= record["proxy_lateral"] <= ABSOLUTE_LATERAL_GUARD_MPS2 + TOL
    mask &= (
        (record["proxy_jerk"] < record["proxy_jerk"][0] - TOL)
        | (record["proxy_lateral"] < record["proxy_lateral"][0] - TOL)
    )
    return mask


def _feature_values(record: dict[str, Any], field: str) -> np.ndarray | None:
    if field == "progress_delta":
        return record["progress_shortfall"] - record["progress_shortfall"][0]
    if field == "score_delta":
        return record["scores"] - record["scores"][0]
    if field == "proxy_lateral_delta":
        return record["proxy_lateral"] - record["proxy_lateral"][0]
    if field == "proxy_jerk_delta":
        return record["proxy_jerk"] - record["proxy_jerk"][0]
    if field == "union_red_delta":
        return record["union_red"] - record["union_red"][0]
    if field == "red_stopping_delta":
        return record["red_stopping"] - record["red_stopping"][0]
    descriptor_field = {
        "h3_distance_loss": "rollout_h3_distance_m",
        "h5_distance_loss": "rollout_h5_distance_m",
        "h10_distance_loss": "rollout_h10_distance_m",
        "step_reach_loss": "candidate_step_reach",
        "tracker_first_step_reach_loss": "candidate_perfect_tracker_first_step_reach_m",
        "target_speed_loss": "candidate_perfect_tracker_target_speed_mps",
        "route_progress_loss": "candidate_route_progress",
    }.get(field)
    if descriptor_field is None:
        raise ValueError(f"Unsupported feature field: {field}")
    values = record["descriptors"].get(descriptor_field)
    if values is None:
        return None
    arr = np.asarray(values, dtype=np.float64)
    return arr[0] - arr


def _select_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return 0
    h10_loss = _feature_values(record, "h10_distance_loss")
    if h10_loss is None:
        h10_loss = np.zeros(int(record["candidate_count"]), dtype=np.float64)
    progress_delta = _feature_values(record, "progress_delta")
    if progress_delta is None:
        raise ValueError("progress_delta must be available.")
    order = np.lexsort(
        (
            indices,
            record["scores"][indices],
            h10_loss[indices],
            progress_delta[indices],
            record["proxy_jerk"][indices],
            record["proxy_lateral"][indices],
            record["red_stopping"][indices],
            record["union_red"][indices],
        )
    )
    return int(indices[order[0]])


def _base_blockers(record: dict[str, Any], candidate: int) -> list[str]:
    blockers: list[str] = []
    progress_delta = _feature_values(record, "progress_delta")
    if progress_delta is None:
        raise ValueError("progress_delta must be available.")
    if progress_delta[candidate] < BASE_PROGRESS_DELTA_MIN - TOL:
        blockers.append("progress_delta_below_lower_band")
    if progress_delta[candidate] > BASE_PROGRESS_DELTA_MAX + TOL:
        blockers.append("progress_delta_exceeds_budget")
    if record["union_red"][candidate] > record["union_red"][0] + TOL:
        blockers.append("union_red_worse")
    if record["red_stopping"][candidate] > record["red_stopping"][0] + TOL:
        blockers.append("red_stopping_worse")
    if record["proxy_jerk"][candidate] > record["proxy_jerk"][0] + TOL:
        blockers.append("proxy_jerk_worse")
    if record["proxy_lateral"][candidate] > record["proxy_lateral"][0] + TOL:
        blockers.append("proxy_lateral_worse")
    if not (
        record["proxy_jerk"][candidate] < record["proxy_jerk"][0] - TOL
        or record["proxy_lateral"][candidate] < record["proxy_lateral"][0] - TOL
    ):
        blockers.append("no_strict_proxy_comfort_gain")
    return blockers or ["passes_base_but_not_selected"]


def _best_outcome_candidate(record: dict[str, Any], outcome_mask: np.ndarray) -> int:
    indices = np.flatnonzero(outcome_mask)
    if indices.size == 0:
        raise ValueError("best outcome candidate requested for empty mask.")
    cost = np.asarray(
        [
            _candidate_label_delta(record, int(index))["candidate_label_safety_delta"]
            for index in indices
        ],
        dtype=np.float64,
    )
    progress_loss = np.asarray(
        [
            _candidate_label_delta(record, int(index))["progress_loss_m"]
            for index in indices
        ],
        dtype=np.float64,
    )
    order = np.lexsort((indices, progress_loss, cost))
    return int(indices[order[0]])


def _candidate_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    payload = {
        "candidate_index": int(index),
        "candidate_label_delta": _candidate_label_delta(record, index),
        "proxy_delta": _proxy_delta(record, index),
    }
    for field in FEATURE_FIELDS:
        values = _feature_values(record, field)
        payload[field] = None if values is None else float(values[index])
    return payload


def _feature_distribution_report(
    hidden_rows: list[dict[str, Any]],
    risky_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        field: {
            "hidden_best_oracle": _feature_stats(hidden_rows, field),
            "risky_common_candidates": _feature_stats(risky_rows, field),
        }
        for field in FEATURE_FIELDS
    }


def _feature_stats(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = []
    missing = 0
    for row in rows:
        feature_values = _feature_values(row["record"], field)
        if feature_values is None:
            missing += 1
            continue
        values.append(float(feature_values[int(row["candidate"])]))
    if not values:
        return {
            "n": 0,
            "missing": missing,
            "min": None,
            "p10": None,
            "p50": None,
            "p90": None,
            "max": None,
        }
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "missing": missing,
        "min": float(np.min(arr)),
        "p10": float(np.percentile(arr, 10.0)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "max": float(np.max(arr)),
    }


def _screen_bucket_report(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets = event["record"]["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(event)
    return [
        {
            "bucket": bucket,
            "base_hidden_context_records": len(grouped[bucket]),
            "escape_override_records": sum(
                int(event["escape_override"]) for event in grouped[bucket]
            ),
            "true_recovery_records": sum(
                int(event["true_recovery"]) for event in grouped[bucket]
            ),
            "false_escape_records": sum(
                int(event["false_escape"]) for event in grouped[bucket]
            ),
            "hidden_remaining_records": sum(
                int(event["hidden_remaining"]) for event in grouped[bucket]
            ),
        }
        for bucket in _ordered_buckets(grouped)
    ]


def _ordered_buckets(grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    order = [
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    return [bucket for bucket in order if bucket in grouped] + sorted(
        bucket for bucket in grouped if bucket not in order
    )


def _bool_worse_summary(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(
            int(
                _event_candidate_payload(event)["candidate_label_delta"]["bool_delta"][
                    field
                ]
                > 0
            )
            for event in events
        )
        for field in BOOL_OUTCOMES
    }


def _event_candidate_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("selected_candidate", event.get("candidate_payload"))
    if not isinstance(payload, dict):
        raise ValueError("Event is missing a selected candidate payload.")
    return payload


def _event_examples(
    events: list[dict[str, Any]],
    *,
    max_examples: int,
) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    rows = sorted(events, key=_event_cost_sort_key, reverse=True)
    examples = []
    for event in rows[:max_examples]:
        context = event["record"]["context"]
        examples.append(
            {
                "route_name": context["route_name"],
                "scenario_buckets": context["scenario_buckets"],
                "seed": context["seed"],
                "max_npcs": context["max_npcs"],
                "traffic_lights": context["traffic_lights"],
                "selection_step": event["record"]["selection_step"],
                "selected": event["selected"],
                "certificate_size": event["certificate_size"],
                "outcome_oracle_size": event["outcome_oracle_size"],
                "selected_candidate": event["selected_candidate"],
                "best_hidden_candidate": event["best_hidden_candidate"],
                "false_reasons": event["false_reasons"],
                "run_key": context["run_key"],
                "log_path": context["log_path"],
            }
        )
    return examples


def _event_cost_sort_key(event: dict[str, Any]) -> tuple[float, int]:
    candidate = event["selected_candidate"]
    cost = candidate["candidate_label_delta"]["candidate_label_safety_delta"]
    return (float(cost), int(event["record"]["selection_step"]))


def _counter(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Hidden Visibility Audit",
        "",
        "This is an offline audit. It starts from the protected "
        "`banded_shortfall_m010_p005` rule and evaluates shadow-only escape "
        "screens on records where that protected rule keeps candidate0 despite "
        "an outcome-label oracle candidate.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Base Rule",
        "",
        "```json",
        json.dumps(report["base_rule"], indent=2, sort_keys=True),
        "```",
        "",
        "## Escape Screens",
        "",
        "| Screen | Escape | True Recovery | False Escape | Hidden Remaining | "
        "Mean escape safety | Bool hard-gate worse | Missing descriptors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in report["screens"]:
        summary = row["summary"]
        safety = summary["candidate_label_safety_delta_escape"]
        bool_worse = summary["hard_gate_bool_worse_records"]
        bool_summary = ", ".join(
            f"{field}:{count}" for field, count in bool_worse.items() if count
        )
        lines.append(
            f"| `{row['name']}` | "
            f"{summary['escape_override_records']} | "
            f"{summary['true_recovery_records']} | "
            f"{summary['false_escape_records']} | "
            f"{summary['hidden_remaining_records']} | "
            f"{_fmt(safety['mean'])} | "
            f"{bool_summary or 'none'} | "
            f"{summary['descriptor_missing_records']} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
