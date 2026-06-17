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
    _optional_vector,
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
ABSOLUTE_LATERAL_GUARD_MPS2 = 2.0

RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "baseline_shortfall_any_p005",
        "description": (
            "previous any-comfort progress_shortfall<=0.05 rule; included as "
            "the predeclared reference"
        ),
        "tiers": (
            {
                "name": "base",
                "progress_delta_min": None,
                "progress_delta_max": 0.05,
                "h10_distance_loss_max": None,
                "score_delta_max": None,
            },
        ),
    },
    {
        "name": "banded_shortfall_m010_p005",
        "description": (
            "reject candidates whose progress_shortfall is too negative "
            "relative to candidate0; this targets the observed hard-gate "
            "false-positive mode"
        ),
        "tiers": (
            {
                "name": "banded_base",
                "progress_delta_min": -0.10,
                "progress_delta_max": 0.05,
                "h10_distance_loss_max": None,
                "score_delta_max": None,
            },
        ),
    },
    {
        "name": "banded_shortfall_m020_p005",
        "description": "less conservative lower band for the same false-positive guard",
        "tiers": (
            {
                "name": "banded_base",
                "progress_delta_min": -0.20,
                "progress_delta_max": 0.05,
                "h10_distance_loss_max": None,
                "score_delta_max": None,
            },
        ),
    },
    {
        "name": "tiered_banded_m010_escape_p010_h10_p005_score0",
        "description": (
            "first apply the -0.10..0.05 band; only if empty, allow a "
            "score-nonworse H10-supported escape with progress_delta<=0.10"
        ),
        "tiers": (
            {
                "name": "banded_base",
                "progress_delta_min": -0.10,
                "progress_delta_max": 0.05,
                "h10_distance_loss_max": None,
                "score_delta_max": None,
            },
            {
                "name": "escape",
                "progress_delta_min": -0.10,
                "progress_delta_max": 0.10,
                "h10_distance_loss_max": 0.05,
                "score_delta_max": 0.0,
            },
        ),
    },
    {
        "name": "tiered_banded_m020_escape_p010_h10_p005_score0",
        "description": (
            "same tiered escape with a wider -0.20 lower band; included to "
            "quantify coverage versus hard-gate risk"
        ),
        "tiers": (
            {
                "name": "banded_base",
                "progress_delta_min": -0.20,
                "progress_delta_max": 0.05,
                "h10_distance_loss_max": None,
                "score_delta_max": None,
            },
            {
                "name": "escape",
                "progress_delta_min": -0.20,
                "progress_delta_max": 0.10,
                "h10_distance_loss_max": 0.05,
                "score_delta_max": 0.0,
            },
        ),
    },
    {
        "name": "intersect_shortfall_p010_h10_p005_score0",
        "description": (
            "non-tiered contrast: a single expanded candidate set guarded by "
            "H10 distance loss and score nonworse"
        ),
        "tiers": (
            {
                "name": "intersect",
                "progress_delta_min": None,
                "progress_delta_max": 0.10,
                "h10_distance_loss_max": 0.05,
                "score_delta_max": 0.0,
            },
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline composite guard audit for fixed DP candidates. Outcome "
            "labels are posterior evaluation only and never online inputs."
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

    rule_reports = [_rule_report(records, rule, max_examples=max_examples) for rule in RULES]
    return {
        "analysis": {
            "name": "dp_camp_composite_guard_audit_v1",
            "label": label,
            "role": (
                "offline composite current-tick guard audit before any online "
                "Top-1-preserving selector"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are posterior labels only",
            "classical_benders_claim": False,
            "outcome_progress_budget_m": OUTCOME_PROGRESS_BUDGET_M,
            "absolute_lateral_guard_mps2": ABSOLUTE_LATERAL_GUARD_MPS2,
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "rules": [
                {
                    "name": str(rule["name"]),
                    "description": str(rule["description"]),
                    "tiers": list(rule["tiers"]),
                }
                for rule in RULES
            ],
            "selection_contract": (
                "If candidate0 is feasible, select candidate0 unless the first "
                "nonempty deterministic tier admits a nonzero candidate. If "
                "candidate0 is infeasible or all candidates are infeasible, no "
                "Top-1 override is audited. The online analogue would fail "
                "closed to candidate0/baseline on missing descriptors."
            ),
            "math_boundary": (
                "All rule inputs are fixed finite current-tick candidate "
                "constants: feasibility, progress_shortfall delta, H10 open-loop "
                "distance delta when present, red proxies, proxy jerk/lateral, "
                "selection score, and deterministic candidate index. Outcome "
                "labels evaluate posterior safety only and are not online inputs "
                "or Benders cut sources. If these diagnostics are atomized, they "
                "must be scaled as fixed nonnegative atoms so CAMP scores remain "
                "affine in the master variable."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
            "candidate0_feasible": sum(
                int(record["feasible"].any() and bool(record["feasible"][0]))
                for record in records
            ),
        },
        "rules": rule_reports,
    }


def _rule_report(
    records: list[dict[str, Any]],
    rule: dict[str, Any],
    *,
    max_examples: int,
) -> dict[str, Any]:
    events = [
        _event(record, rule)
        for record in records
        if record["feasible"].any() and bool(record["feasible"][0])
    ]
    by_bucket = _bucket_report(events)
    false_events = [event for event in events if event["false_override"]]
    hidden_events = [event for event in events if event["hidden_outcome"]]
    regressions = [event for event in events if event["safety_regression"]]
    return {
        "name": str(rule["name"]),
        "description": str(rule["description"]),
        "tiers": list(rule["tiers"]),
        "overall": _summary(events),
        "by_bucket": by_bucket,
        "tier_counts": _counter(event["selected_tier"] for event in events),
        "false_tier_counts": _counter(event["selected_tier"] for event in false_events),
        "safety_regression_tier_counts": _counter(
            event["selected_tier"] for event in regressions
        ),
        "false_reason_counts": _counter(
            reason for event in false_events for reason in event["false_reasons"]
        ),
        "hidden_blocker_counts": _counter(
            blocker for event in hidden_events for blocker in event["hidden_blockers"]
        ),
        "examples": {
            "false_override": _examples(false_events, max_examples=max_examples),
            "safety_regression": _examples(regressions, max_examples=max_examples),
            "hidden_outcome": _examples(hidden_events, max_examples=max_examples),
        },
    }


def _event(record: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    selected = 0
    selected_tier = "top1"
    selected_mask = np.zeros(int(record["candidate_count"]), dtype=bool)
    tier_availability: dict[str, bool] = {}
    tier_sizes: dict[str, int] = {}
    for tier in rule["tiers"]:
        mask, available = _tier_mask(record, tier)
        tier_name = str(tier["name"])
        tier_availability[tier_name] = available
        tier_sizes[tier_name] = int(mask.sum()) if available else 0
        if available and mask.any():
            selected = _select_candidate(record, mask)
            selected_tier = tier_name
            selected_mask = mask
            break

    outcome_mask = _outcome_mask_vs_candidate0(record, OUTCOME_PROGRESS_BUDGET_M)
    override = selected != 0
    candidate_delta = _candidate_label_delta(record, selected)
    strict_safety_improving = bool(
        override
        and candidate_delta["candidate_label_safety_delta"] < -TOL
        and all(candidate_delta["bool_delta"][field] <= 0 for field in BOOL_OUTCOMES)
    )
    safety_regression = bool(
        override and candidate_delta["candidate_label_safety_delta"] > TOL
    )
    false_override = bool(override and not outcome_mask[selected])
    hidden_outcome = bool((not override) and outcome_mask.any())
    best_hidden = _best_outcome_candidate(record, outcome_mask) if hidden_outcome else None
    return {
        "context": record["context"],
        "selection_step": int(record["selection_step"]),
        "record_index": int(record["record_index"]),
        "selected": int(selected),
        "selected_tier": selected_tier,
        "override": override,
        "true_override": bool(override and outcome_mask[selected]),
        "false_override": false_override,
        "hidden_outcome": hidden_outcome,
        "strict_safety_improving": strict_safety_improving,
        "safety_regression": safety_regression,
        "certificate_size": int(selected_mask.sum()),
        "outcome_oracle_size": int(outcome_mask.sum()),
        "tier_availability": tier_availability,
        "tier_sizes": tier_sizes,
        "selected_candidate": _candidate_payload(record, selected),
        "false_reasons": (
            _outcome_oracle_failure_reasons(
                record,
                selected,
                OUTCOME_PROGRESS_BUDGET_M,
            )
            if false_override
            else []
        ),
        "best_hidden_candidate": (
            _candidate_payload(record, best_hidden) if best_hidden is not None else None
        ),
        "hidden_blockers": (
            _rule_blockers(record, best_hidden, rule)
            if best_hidden is not None
            else []
        ),
    }


def _tier_mask(
    record: dict[str, Any],
    tier: dict[str, Any],
) -> tuple[np.ndarray, bool]:
    mask = record["feasible"].copy()
    mask[0] = False
    progress_delta = record["progress_shortfall"] - record["progress_shortfall"][0]
    progress_delta_min = tier.get("progress_delta_min")
    if progress_delta_min is not None:
        mask &= progress_delta >= float(progress_delta_min) - TOL
    progress_delta_max = tier.get("progress_delta_max")
    if progress_delta_max is not None:
        mask &= progress_delta <= float(progress_delta_max) + TOL

    h10_loss_max = tier.get("h10_distance_loss_max")
    h10_loss = None
    if h10_loss_max is not None:
        h10_values = _descriptor_vector(record, "rollout_h10_distance_m")
        if h10_values is None:
            return np.zeros(int(record["candidate_count"]), dtype=bool), False
        h10_loss = h10_values[0] - h10_values
        mask &= h10_loss <= float(h10_loss_max) + TOL

    score_delta_max = tier.get("score_delta_max")
    if score_delta_max is not None:
        mask &= record["scores"] - record["scores"][0] <= float(score_delta_max) + TOL

    mask &= record["union_red"] <= record["union_red"][0] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][0] + TOL
    mask &= record["proxy_jerk"] <= record["proxy_jerk"][0] + TOL
    mask &= record["proxy_lateral"] <= record["proxy_lateral"][0] + TOL
    mask &= record["proxy_lateral"] <= ABSOLUTE_LATERAL_GUARD_MPS2 + TOL
    mask &= (
        (record["proxy_jerk"] < record["proxy_jerk"][0] - TOL)
        | (record["proxy_lateral"] < record["proxy_lateral"][0] - TOL)
    )
    if h10_loss is not None:
        _optional_vector(h10_loss, int(record["candidate_count"]), "h10_loss")
    return mask, True


def _descriptor_vector(record: dict[str, Any], field: str) -> np.ndarray | None:
    value = record["descriptors"].get(field)
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64)


def _select_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return 0
    h10_values = _descriptor_vector(record, "rollout_h10_distance_m")
    if h10_values is None:
        h10_loss = np.zeros(int(record["candidate_count"]), dtype=np.float64)
    else:
        h10_loss = h10_values[0] - h10_values
    progress_delta = record["progress_shortfall"] - record["progress_shortfall"][0]
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


def _rule_blockers(
    record: dict[str, Any],
    candidate: int,
    rule: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for tier in rule["tiers"]:
        tier_name = str(tier["name"])
        tier_blockers = _tier_blockers(record, candidate, tier)
        if not tier_blockers:
            blockers.append(f"{tier_name}:passes_but_not_selected")
        else:
            blockers.extend(f"{tier_name}:{blocker}" for blocker in tier_blockers)
    return blockers


def _tier_blockers(
    record: dict[str, Any],
    candidate: int,
    tier: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not bool(record["feasible"][candidate]):
        blockers.append("not_base_feasible")
    progress_delta = float(
        record["progress_shortfall"][candidate] - record["progress_shortfall"][0]
    )
    progress_delta_min = tier.get("progress_delta_min")
    if progress_delta_min is not None and progress_delta < float(progress_delta_min) - TOL:
        blockers.append("progress_delta_below_lower_band")
    progress_delta_max = tier.get("progress_delta_max")
    if progress_delta_max is not None and progress_delta > float(progress_delta_max) + TOL:
        blockers.append("progress_delta_exceeds_budget")
    h10_loss_max = tier.get("h10_distance_loss_max")
    if h10_loss_max is not None:
        h10_values = _descriptor_vector(record, "rollout_h10_distance_m")
        if h10_values is None:
            blockers.append("h10_distance_missing")
        else:
            h10_loss = float(h10_values[0] - h10_values[candidate])
            if h10_loss > float(h10_loss_max) + TOL:
                blockers.append("h10_distance_loss_exceeds_budget")
    score_delta_max = tier.get("score_delta_max")
    if (
        score_delta_max is not None
        and record["scores"][candidate] - record["scores"][0]
        > float(score_delta_max) + TOL
    ):
        blockers.append("selection_score_worse")
    if record["union_red"][candidate] > record["union_red"][0] + TOL:
        blockers.append("union_red_worse")
    if record["red_stopping"][candidate] > record["red_stopping"][0] + TOL:
        blockers.append("red_stopping_worse")
    if record["proxy_jerk"][candidate] > record["proxy_jerk"][0] + TOL:
        blockers.append("proxy_jerk_worse")
    if record["proxy_lateral"][candidate] > record["proxy_lateral"][0] + TOL:
        blockers.append("proxy_lateral_worse")
    if record["proxy_lateral"][candidate] > ABSOLUTE_LATERAL_GUARD_MPS2 + TOL:
        blockers.append("absolute_lateral_guard_exceeded")
    if not (
        record["proxy_jerk"][candidate] < record["proxy_jerk"][0] - TOL
        or record["proxy_lateral"][candidate] < record["proxy_lateral"][0] - TOL
    ):
        blockers.append("no_strict_proxy_comfort_gain")
    return blockers


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
    indices_arr = np.asarray(indices, dtype=np.int64)
    order = np.lexsort((indices_arr, progress_loss, cost))
    return int(indices[order[0]])


def _candidate_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "candidate_index": int(index),
        "candidate_label_delta": _candidate_label_delta(record, index),
        "proxy_delta": _proxy_delta(record, index),
        "progress_delta": float(
            record["progress_shortfall"][index] - record["progress_shortfall"][0]
        ),
        "h10_distance_loss_m": _candidate_h10_loss(record, index),
    }


def _candidate_h10_loss(record: dict[str, Any], index: int) -> float | None:
    h10_values = _descriptor_vector(record, "rollout_h10_distance_m")
    if h10_values is None:
        return None
    return float(h10_values[0] - h10_values[index])


def _summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    overrides = [event for event in events if event["override"]]
    true_overrides = [event for event in overrides if event["true_override"]]
    false_overrides = [event for event in overrides if event["false_override"]]
    hidden = [event for event in events if event["hidden_outcome"]]
    strict_safety = [event for event in overrides if event["strict_safety_improving"]]
    regressions = [event for event in overrides if event["safety_regression"]]
    override_deltas = [
        event["selected_candidate"]["candidate_label_delta"] for event in overrides
    ]
    return {
        "candidate0_feasible_records": len(events),
        "override_records": len(overrides),
        "override_rate": len(overrides) / max(len(events), 1),
        "true_override_records": len(true_overrides),
        "true_override_rate_among_overrides": len(true_overrides)
        / max(len(overrides), 1),
        "false_override_records": len(false_overrides),
        "false_override_rate_among_overrides": len(false_overrides)
        / max(len(overrides), 1),
        "hidden_outcome_records": len(hidden),
        "hidden_outcome_rate": len(hidden) / max(len(events), 1),
        "strict_safety_improving_records": len(strict_safety),
        "strict_safety_improving_rate_among_overrides": len(strict_safety)
        / max(len(overrides), 1),
        "safety_regression_records": len(regressions),
        "safety_regression_rate_among_overrides": len(regressions)
        / max(len(overrides), 1),
        "candidate_label_safety_delta_overrides": _stats(
            [
                delta["candidate_label_safety_delta"]
                for delta in override_deltas
            ]
        ),
        "progress_loss_overrides": _stats(
            [delta["progress_loss_m"] for delta in override_deltas]
        ),
        "hard_gate_bool_worse_records": {
            field: sum(
                int(delta["bool_delta"][field] > 0)
                for delta in override_deltas
            )
            for field in BOOL_OUTCOMES
        },
    }


def _bucket_report(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        buckets = event["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(event)
    return [
        {"bucket": bucket, **_summary(grouped[bucket])}
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


def _examples(
    events: list[dict[str, Any]],
    *,
    max_examples: int,
) -> list[dict[str, Any]]:
    if max_examples <= 0:
        return []
    rows = sorted(events, key=_example_sort_key, reverse=True)
    examples = []
    for event in rows[:max_examples]:
        context = event["context"]
        examples.append(
            {
                "route_name": context["route_name"],
                "scenario_buckets": context["scenario_buckets"],
                "seed": context["seed"],
                "max_npcs": context["max_npcs"],
                "traffic_lights": context["traffic_lights"],
                "selection_step": event["selection_step"],
                "selected": event["selected"],
                "selected_tier": event["selected_tier"],
                "certificate_size": event["certificate_size"],
                "outcome_oracle_size": event["outcome_oracle_size"],
                "selected_candidate": event["selected_candidate"],
                "false_reasons": event["false_reasons"],
                "best_hidden_candidate": event["best_hidden_candidate"],
                "hidden_blockers": event["hidden_blockers"],
                "run_key": context["run_key"],
                "log_path": context["log_path"],
            }
        )
    return examples


def _example_sort_key(event: dict[str, Any]) -> tuple[float, int]:
    candidate = event["selected_candidate"]
    cost = candidate["candidate_label_delta"]["candidate_label_safety_delta"]
    return (float(cost), int(event["selection_step"]))


def _counter(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Composite Guard Audit",
        "",
        "This is an offline audit of deterministic finite-candidate composite "
        "guards. Outcome labels are posterior evaluation only.",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Rule Results",
        "",
        "| Rule | Override | True | False | Hidden | Safety<0 | Safety>0 | "
        "Mean safety | CVaR90 safety | Bool hard-gate worse |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["rules"]:
        overall = row["overall"]
        safety = overall["candidate_label_safety_delta_overrides"]
        bool_worse = overall["hard_gate_bool_worse_records"]
        bool_summary = ", ".join(
            f"{field}:{count}" for field, count in bool_worse.items() if count
        )
        lines.append(
            f"| `{row['name']}` | "
            f"{overall['override_records']} | "
            f"{overall['true_override_records']} | "
            f"{overall['false_override_records']} | "
            f"{overall['hidden_outcome_records']} | "
            f"{overall['strict_safety_improving_records']} | "
            f"{overall['safety_regression_records']} | "
            f"{_fmt(safety['mean'])} | {_fmt(safety['cvar90'])} | "
            f"{bool_summary or 'none'} |"
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
