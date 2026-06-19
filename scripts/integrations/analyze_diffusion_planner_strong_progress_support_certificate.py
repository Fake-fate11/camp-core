#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
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
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (  # noqa: E402
    FORMAL_SEEDS,
    PREDECLARED_VARIANTS,
    WeightVariant,
    _load_record,
    _scales,
    _select,
    _weights,
)
from scripts.integrations.analyze_diffusion_planner_material_weight_failure_attribution import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_NON_SWITCH,
    REJECT_STATUS_ATTRIBUTION,
    _event,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "strong_progress_support_certificate_promising"
REJECT_STATUS = "strong_progress_support_certificate_rejected"
SOURCE_BLOCKED_STATUS = "strong_progress_support_certificate_source_not_rejected"
FORMAL_SEED_STATUS = "strong_progress_support_certificate_formal_seed_conflict"

PROGRESS_LOSS_BUDGET_M = 0.05
HARMFUL_BLOCK_RATE_TARGET = 0.75
BENEFICIAL_RETAIN_RATE_TARGET = 0.75
HARD_NONWORSE_RATE_TARGET = 0.99
ABSOLUTE_LATERAL_GUARD_MPS2 = 2.0
EPS = 1e-12

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class CertificateSpec:
    name: str
    progress_loss_budget_m: float
    first_step_loss_budget_m: float
    speed_loss_budget_mps: float
    jerk_worse_budget_mps3: float
    lateral_worse_budget_mps2: float
    yaw_worse_budget_rps: float
    absolute_lateral_guard_mps2: float
    rationale: str


CERTIFICATE_SPECS: tuple[CertificateSpec, ...] = (
    CertificateSpec(
        name="strict_support_zero_comfort",
        progress_loss_budget_m=0.0,
        first_step_loss_budget_m=0.0,
        speed_loss_budget_mps=0.0,
        jerk_worse_budget_mps3=0.0,
        lateral_worse_budget_mps2=0.0,
        yaw_worse_budget_rps=0.0,
        absolute_lateral_guard_mps2=ABSOLUTE_LATERAL_GUARD_MPS2,
        rationale="fail closed on any current-tick progress, speed, or comfort regression",
    ),
    CertificateSpec(
        name="tiny_support_nonworse_comfort",
        progress_loss_budget_m=0.01,
        first_step_loss_budget_m=0.02,
        speed_loss_budget_mps=0.05,
        jerk_worse_budget_mps3=0.0,
        lateral_worse_budget_mps2=0.0,
        yaw_worse_budget_rps=0.0,
        absolute_lateral_guard_mps2=ABSOLUTE_LATERAL_GUARD_MPS2,
        rationale="allow tiny support loss but require nonworse tracker comfort",
    ),
    CertificateSpec(
        name="small_support_small_comfort",
        progress_loss_budget_m=0.05,
        first_step_loss_budget_m=0.05,
        speed_loss_budget_mps=0.10,
        jerk_worse_budget_mps3=0.10,
        lateral_worse_budget_mps2=0.05,
        yaw_worse_budget_rps=0.05,
        absolute_lateral_guard_mps2=ABSOLUTE_LATERAL_GUARD_MPS2,
        rationale="match the existing 0.05m progress-loss evaluation budget with small comfort slack",
    ),
    CertificateSpec(
        name="medium_support_small_comfort",
        progress_loss_budget_m=0.10,
        first_step_loss_budget_m=0.10,
        speed_loss_budget_mps=0.25,
        jerk_worse_budget_mps3=0.10,
        lateral_worse_budget_mps2=0.05,
        yaw_worse_budget_rps=0.05,
        absolute_lateral_guard_mps2=ABSOLUTE_LATERAL_GUARD_MPS2,
        rationale="test whether progress support rather than comfort slack is the bottleneck",
    ),
    CertificateSpec(
        name="medium_support_relaxed_comfort",
        progress_loss_budget_m=0.10,
        first_step_loss_budget_m=0.10,
        speed_loss_budget_mps=0.25,
        jerk_worse_budget_mps3=0.25,
        lateral_worse_budget_mps2=0.10,
        yaw_worse_budget_rps=0.10,
        absolute_lateral_guard_mps2=ABSOLUTE_LATERAL_GUARD_MPS2,
        rationale="separate support preservation from modest tracker comfort relaxations",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak strong progress/support certificate audit for "
            "previously rejected DP-CAMP material-weight switches."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--failure_attribution_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
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
        failure_attribution_report=_load_json(args.failure_attribution_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        scale_percentile=args.scale_percentile,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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
    failure_attribution_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            items.append({"raw": raw, "context": {**context, "record_index": index}})
    return analyze_records(
        items,
        failure_attribution_report=failure_attribution_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        scale_percentile=scale_percentile,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    failure_attribution_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
    variants: tuple[WeightVariant, ...] = PREDECLARED_VARIANTS,
    certificate_specs: tuple[CertificateSpec, ...] = CERTIFICATE_SPECS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    hard_nonworse_rate_target: float = HARD_NONWORSE_RATE_TARGET,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(failure_attribution_report)
    records: list[dict[str, Any]] = []
    descriptor_records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        records.append(_load_record(item["raw"], item["context"], f"record {index}"))
        descriptor_records.append(
            _descriptor_record(item["raw"], item["context"], f"record {index}")
        )
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    scales = _scales(records, scale_percentile)
    variant_reports = [
        _variant_report(
            variant,
            records,
            descriptor_records,
            scales,
            certificate_specs=certificate_specs,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for variant in variants
    ]
    decision = _decision(
        source,
        variant_reports,
        formal_seed_records=formal_seed_records,
    )
    return {
        "analysis": {
            "name": "dp_camp_strong_progress_support_certificate_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_certificate": False,
            "future_outcome_labels_used_for_selection": False,
            "future_outcome_labels_used_for_evaluation": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "certificate_specs": [_spec_payload(spec) for spec in certificate_specs],
            "accept_criteria": {
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_safety_delta_mean": "<= 0",
                "allowed_progress_delta_mean": f">= -{progress_loss_budget_m}",
                "final_hard_nonworse_rate": f">= {hard_nonworse_rate_target}",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Certificate "
                "descriptors are fixed current-tick finite-candidate quantities: "
                "progress/reach, tracker speed, tracker jerk/lateral/yaw, and "
                "DP-prior deviation diagnostics. They are evaluated after a fixed "
                "affine CAMP material score proposes a switch, but before any "
                "closed-loop outcome label is consulted. Closed-loop outcomes are "
                "used only to classify harmful or beneficial switches offline. "
                "CAMP scores remain affine a_k^T w over fixed atoms and the "
                "simplex/CVaR/L2 master convexity boundary is unchanged. No "
                "DP-side classical Benders decomposition, dual, or valid cut is "
                "claimed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_failure_attribution_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "descriptor_coverage": _descriptor_coverage(descriptor_records),
        "variants": variant_reports,
        "ranked_certificates": _rank_certificates(variant_reports),
        "failure_gap": _failure_gap(variant_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _variant_report(
    variant: WeightVariant,
    records: list[dict[str, Any]],
    descriptor_records: list[dict[str, Any]],
    scales: dict[str, float],
    *,
    certificate_specs: tuple[CertificateSpec, ...],
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
) -> dict[str, Any]:
    weights = _weights(variant)
    events = [
        {
            **_event(
                record,
                _select(record, weights, scales),
                weights,
                scales,
                progress_loss_budget_m=progress_loss_budget_m,
            ),
            "record_index": index,
        }
        for index, record in enumerate(records)
    ]
    rows = [
        _certificate_row(
            events,
            descriptor_records,
            spec,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            progress_loss_budget_m=progress_loss_budget_m,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for spec in certificate_specs
    ]
    return {
        "name": variant.name,
        "weights": dict(zip(_atom_families_from_event(events), weights)),
        "classification_counts": _class_counts(events),
        "top1_shape_harmful_switches": _top1_shape_harmful_count(events),
        "certificate_rows": rows,
        "best_certificate": _best_certificate(rows),
        "block_reason_summary": _block_reason_summary(rows),
        "scenario_bucket_breakdown": _bucket_breakdown(events, rows),
    }


def _certificate_row(
    events: list[dict[str, Any]],
    descriptor_records: list[dict[str, Any]],
    spec: CertificateSpec,
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    progress_loss_budget_m: float,
    hard_nonworse_rate_target: float,
) -> dict[str, Any]:
    changed = [event for event in events if event["changed"]]
    harmful = [event for event in changed if event["class"] == CLASS_HARMFUL]
    beneficial = [event for event in changed if event["class"] == CLASS_BENEFICIAL]
    allowed: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    block_reasons: Counter[str] = Counter()
    harmful_block_reasons: Counter[str] = Counter()
    beneficial_block_reasons: Counter[str] = Counter()
    final_events: list[dict[str, Any]] = []

    for event in events:
        if not event["changed"]:
            final_events.append({**event, "certificate_allowed": False, "final_switch": False})
            continue
        descriptor = descriptor_records[int(event["record_index"])]
        allowed_switch, reasons = _certificate_allows(
            descriptor,
            int(event["chosen"]),
            spec,
        )
        payload = {
            **event,
            "certificate_allowed": allowed_switch,
            "certificate_block_reasons": reasons,
            "descriptor_delta": _descriptor_delta_payload(
                descriptor,
                int(event["chosen"]),
            ),
            "final_switch": allowed_switch,
        }
        if allowed_switch:
            allowed.append(payload)
            final_events.append(payload)
        else:
            blocked.append(payload)
            block_reasons.update(reasons)
            if event["class"] == CLASS_HARMFUL:
                harmful_block_reasons.update(reasons)
            if event["class"] == CLASS_BENEFICIAL:
                beneficial_block_reasons.update(reasons)
            final_events.append(
                {
                    **payload,
                    "safety_delta": 0.0,
                    "progress_delta": 0.0,
                    "hard_worse": False,
                }
            )

    allowed_harmful = [event for event in allowed if event["class"] == CLASS_HARMFUL]
    allowed_beneficial = [event for event in allowed if event["class"] == CLASS_BENEFICIAL]
    blocked_harmful = [event for event in blocked if event["class"] == CLASS_HARMFUL]
    harmful_block_rate = len(blocked_harmful) / max(len(harmful), 1)
    beneficial_retain_rate = len(allowed_beneficial) / max(len(beneficial), 1)
    final_hard_nonworse_rate = _hard_nonworse_rate(final_events)
    allowed_safety_mean = _mean([event["safety_delta"] for event in allowed])
    allowed_progress_mean = _mean([event["progress_delta"] for event in allowed])
    promising = bool(
        harmful
        and beneficial
        and harmful_block_rate >= harmful_block_rate_target
        and beneficial_retain_rate >= beneficial_retain_rate_target
        and (allowed_safety_mean is not None and allowed_safety_mean <= 0.0)
        and (
            allowed_progress_mean is not None
            and allowed_progress_mean >= -float(progress_loss_budget_m)
        )
        and final_hard_nonworse_rate >= hard_nonworse_rate_target
    )
    return {
        "certificate": _spec_payload(spec),
        "changed_switches": len(changed),
        "allowed_switches": len(allowed),
        "blocked_switches": len(blocked),
        "harmful_switches": len(harmful),
        "beneficial_switches": len(beneficial),
        "allowed_harmful_switches": len(allowed_harmful),
        "allowed_beneficial_switches": len(allowed_beneficial),
        "blocked_harmful_switches": len(blocked_harmful),
        "harmful_block_rate": harmful_block_rate,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_safety_delta_mean": allowed_safety_mean,
        "allowed_progress_delta_mean": allowed_progress_mean,
        "final_safety_delta_mean": _mean([event["safety_delta"] for event in final_events]),
        "final_progress_delta_mean": _mean([event["progress_delta"] for event in final_events]),
        "final_hard_nonworse_rate": final_hard_nonworse_rate,
        "promising_strong_progress_support_certificate": promising,
        "block_reason_counts": dict(sorted(block_reasons.items())),
        "harmful_block_reason_counts": dict(sorted(harmful_block_reasons.items())),
        "beneficial_block_reason_counts": dict(sorted(beneficial_block_reasons.items())),
        "allowed_descriptor_delta_summary": _descriptor_delta_summary(allowed),
        "blocked_descriptor_delta_summary": _descriptor_delta_summary(blocked),
    }


def _certificate_allows(
    descriptor: dict[str, Any],
    candidate: int,
    spec: CertificateSpec,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    checks = (
        ("progress_loss_m", spec.progress_loss_budget_m),
        ("first_step_loss_m", spec.first_step_loss_budget_m),
        ("speed_loss_mps", spec.speed_loss_budget_mps),
        ("jerk_worse_mps3", spec.jerk_worse_budget_mps3),
        ("lateral_worse_mps2", spec.lateral_worse_budget_mps2),
        ("yaw_worse_rps", spec.yaw_worse_budget_rps),
    )
    for key, budget in checks:
        values = descriptor["values"].get(key)
        if values is None:
            reasons.append(f"missing_{key}")
            continue
        value = float(values[candidate])
        if value > float(budget) + EPS:
            reasons.append(f"{key}_exceeds_budget")

    lateral_abs = descriptor["values"].get("absolute_lateral_mps2")
    if lateral_abs is None:
        reasons.append("missing_absolute_lateral_mps2")
    elif float(lateral_abs[candidate]) > spec.absolute_lateral_guard_mps2 + EPS:
        reasons.append("absolute_lateral_guard_exceeded")

    return not reasons, reasons or ["allowed"]


def _descriptor_record(raw: dict[str, Any], context: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")

    progress = _first_present_vector(
        raw,
        candidate_count,
        label,
        ("candidate_route_progress", "candidate_step_reach"),
        nonnegative=False,
    )
    first_step = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_first_step_reach_m",),
        higher_is_better=True,
    )
    target_speed = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_target_speed_mps",),
        higher_is_better=True,
    )
    tail_speed = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_tail_average_speed_mps",),
        higher_is_better=True,
    )
    jerk = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_jerk_magnitude_mps3",),
        higher_is_better=False,
    )
    lateral = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",),
        higher_is_better=False,
    )
    yaw = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_yaw_rate_magnitude_rps",),
        higher_is_better=False,
    )
    dp_prior = _optional_loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_dp_prior_deviation_cost",),
        higher_is_better=False,
    )

    values: dict[str, np.ndarray | None] = {
        "progress_loss_m": (
            None if progress is None else np.maximum(float(progress[selected]) - progress, 0.0)
        ),
        "first_step_loss_m": first_step,
        "speed_loss_mps": _component_max_optional([target_speed, tail_speed]),
        "jerk_worse_mps3": jerk,
        "lateral_worse_mps2": lateral,
        "yaw_worse_rps": yaw,
        "top1_shape_improvement": dp_prior,
        "absolute_lateral_mps2": _optional_vector(
            raw,
            candidate_count,
            label,
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
            nonnegative=True,
        ),
    }
    return {
        "context": context,
        "candidate_count": candidate_count,
        "selected_index": selected,
        "values": values,
    }


def _first_present_vector(
    raw: dict[str, Any],
    size: int,
    label: str,
    keys: tuple[str, ...],
    *,
    nonnegative: bool,
) -> np.ndarray | None:
    for key in keys:
        values = _optional_vector(raw, size, label, key, nonnegative=nonnegative)
        if values is not None:
            return values
    return None


def _optional_loss_vector(
    raw: dict[str, Any],
    size: int,
    selected: int,
    label: str,
    keys: tuple[str, ...],
    *,
    higher_is_better: bool,
) -> np.ndarray | None:
    values = _first_present_vector(raw, size, label, keys, nonnegative=True)
    if values is None:
        return None
    selected_value = float(values[selected])
    if higher_is_better:
        return np.maximum(selected_value - values, 0.0)
    return np.maximum(values - selected_value, 0.0)


def _optional_vector(
    raw: dict[str, Any],
    size: int,
    label: str,
    key: str,
    *,
    nonnegative: bool,
) -> np.ndarray | None:
    if key not in raw or raw.get(key) is None:
        return None
    values = np.asarray(raw[key], dtype=np.float64).reshape(-1)
    if values.shape != (size,):
        raise ValueError(f"{label} {key} must have shape [{size}].")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} {key} must contain finite values.")
    if nonnegative and np.any(values < -EPS):
        raise ValueError(f"{label} {key} must be nonnegative.")
    return values


def _component_max_optional(vectors: list[np.ndarray | None]) -> np.ndarray | None:
    present = [vector for vector in vectors if vector is not None]
    if not present:
        return None
    return np.max(np.vstack(present), axis=0)


def _descriptor_delta_payload(
    descriptor: dict[str, Any],
    candidate: int,
) -> dict[str, float | None]:
    return {
        key: None if values is None else float(values[candidate])
        for key, values in descriptor["values"].items()
    }


def _descriptor_delta_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "progress_loss_m",
        "first_step_loss_m",
        "speed_loss_mps",
        "jerk_worse_mps3",
        "lateral_worse_mps2",
        "yaw_worse_rps",
        "top1_shape_improvement",
        "absolute_lateral_mps2",
    )
    return {
        key: _summary(
            [
                event["descriptor_delta"][key]
                for event in events
                if event.get("descriptor_delta", {}).get(key) is not None
            ]
        )
        for key in keys
    }


def _descriptor_coverage(descriptor_records: list[dict[str, Any]]) -> dict[str, Any]:
    if not descriptor_records:
        return {}
    total = len(descriptor_records)
    candidate_rows = int(sum(row["candidate_count"] for row in descriptor_records))
    keys = sorted(descriptor_records[0]["values"])
    result: dict[str, Any] = {}
    for key in keys:
        records_available = sum(int(row["values"].get(key) is not None) for row in descriptor_records)
        rows_available = sum(
            int(row["candidate_count"])
            for row in descriptor_records
            if row["values"].get(key) is not None
        )
        result[key] = {
            "records_available": int(records_available),
            "records_total": total,
            "candidate_rows_available": int(rows_available),
            "candidate_rows_total": candidate_rows,
        }
    return result


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == REJECT_STATUS_ATTRIBUTION,
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
        "promising_certificates": decision.get("promising_certificates", []),
    }


def _decision(
    source: dict[str, Any],
    variants: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    promising = [
        row
        for row in _rank_certificates(variants)
        if row["promising_strong_progress_support_certificate"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not test a stronger certificate unless the source attribution gate was rejected."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using this certificate evidence."
    elif promising:
        status = READY_STATUS
        next_step = (
            "Design only the next offline no-leak selector screen around the "
            "promising certificate rows; replay, formal seeds, online promotion, "
            "and retraining remain blocked."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "Reject the predeclared strong progress/support certificates. Use "
            "the failure_gap section to decide whether the next gate should "
            "address progress proxy weakness, Top-1 shape calibration, comfort "
            "envelope insufficiency, traffic/support interaction, or candidate-set support."
        )
    return {
        "status": status,
        "promising_certificates": promising,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_no_leak_selector_screen_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _rank_certificates(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in variants:
        for row in variant["certificate_rows"]:
            rows.append(
                {
                    "variant": variant["name"],
                    "certificate_name": row["certificate"]["name"],
                    **{
                        key: value
                        for key, value in row.items()
                        if key != "certificate"
                    },
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            not row["promising_strong_progress_support_certificate"],
            -float(row["harmful_block_rate"]),
            -float(row["beneficial_retain_rate"]),
            float(row["allowed_safety_delta_mean"] or 0.0),
            -float(row["final_hard_nonworse_rate"]),
        ),
    )


def _best_certificate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            not row["promising_strong_progress_support_certificate"],
            -float(row["harmful_block_rate"]),
            -float(row["beneficial_retain_rate"]),
            float(row["allowed_safety_delta_mean"] or 0.0),
            -float(row["final_hard_nonworse_rate"]),
        ),
    )[0]


def _failure_gap(variants: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = _rank_certificates(variants)
    if not ranked:
        return {
            "primary_gap": "no_certificate_rows",
            "best_certificate": None,
        }
    best = ranked[0]
    if best["promising_strong_progress_support_certificate"]:
        primary = "no_gap_promising_certificate_found"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "certificate_too_permissive_for_harmful_top1_switches"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "certificate_blocks_beneficial_opportunities"
    elif (best["allowed_safety_delta_mean"] is None) or best["allowed_safety_delta_mean"] > 0.0:
        primary = "allowed_switches_remain_safety_negative"
    elif (
        best["allowed_progress_delta_mean"] is None
        or best["allowed_progress_delta_mean"] < -PROGRESS_LOSS_BUDGET_M
    ):
        primary = "allowed_switches_remain_progress_negative"
    elif best["final_hard_nonworse_rate"] < HARD_NONWORSE_RATE_TARGET:
        primary = "allowed_switches_violate_hard_nonworse_budget"
    else:
        primary = "unclassified_acceptance_gap"
    return {
        "primary_gap": primary,
        "best_certificate": {
            "variant": best["variant"],
            "certificate_name": best["certificate_name"],
            "harmful_block_rate": best["harmful_block_rate"],
            "beneficial_retain_rate": best["beneficial_retain_rate"],
            "allowed_safety_delta_mean": best["allowed_safety_delta_mean"],
            "allowed_progress_delta_mean": best["allowed_progress_delta_mean"],
            "final_hard_nonworse_rate": best["final_hard_nonworse_rate"],
            "harmful_block_reason_counts": best["harmful_block_reason_counts"],
            "beneficial_block_reason_counts": best["beneficial_block_reason_counts"],
        },
    }


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _class_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        CLASS_HARMFUL: sum(int(event["class"] == CLASS_HARMFUL) for event in events),
        CLASS_BENEFICIAL: sum(int(event["class"] == CLASS_BENEFICIAL) for event in events),
        CLASS_NEUTRAL: sum(int(event["class"] == CLASS_NEUTRAL) for event in events),
        CLASS_NON_SWITCH: sum(int(event["class"] == CLASS_NON_SWITCH) for event in events),
    }


def _top1_shape_harmful_count(events: list[dict[str, Any]]) -> int:
    return sum(
        int(
            event["class"] == CLASS_HARMFUL
            and event.get("dominant_driver") == "top1_shape_deviation"
        )
        for event in events
    )


def _block_reason_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "certificate_name": row["certificate"]["name"],
            "harmful_block_reason_counts": row["harmful_block_reason_counts"],
            "beneficial_block_reason_counts": row["beneficial_block_reason_counts"],
        }
        for row in rows
    ]


def _bucket_breakdown(
    events: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    best = _best_certificate(rows)
    if best is None:
        return []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for bucket in event["context"].get("scenario_buckets", ["overall"]):
            grouped.setdefault(bucket, []).append(event)
    result = []
    for bucket, bucket_events in sorted(grouped.items()):
        counts = _class_counts(bucket_events)
        result.append(
            {
                "bucket": bucket,
                "events": len(bucket_events),
                "classification_counts": counts,
                "harmful_rate": counts[CLASS_HARMFUL] / max(len(bucket_events), 1),
                "beneficial_rate": counts[CLASS_BENEFICIAL] / max(len(bucket_events), 1),
            }
        )
    return result


def _hard_nonworse_rate(events: list[dict[str, Any]]) -> float:
    if not events:
        return 1.0
    return float(np.mean([not bool(event.get("hard_worse")) for event in events]))


def _atom_families_from_event(events: list[dict[str, Any]]) -> tuple[str, ...]:
    if events:
        return tuple(events[0]["raw_atom_delta"])
    return (
        "hard_feasibility_deficit",
        "support_preservation_deficit",
        "comfort_envelope_excess",
        "top1_shape_deviation",
        "traffic_rule_exposure",
    )


def _spec_payload(spec: CertificateSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "progress_loss_budget_m": spec.progress_loss_budget_m,
        "first_step_loss_budget_m": spec.first_step_loss_budget_m,
        "speed_loss_budget_mps": spec.speed_loss_budget_mps,
        "jerk_worse_budget_mps3": spec.jerk_worse_budget_mps3,
        "lateral_worse_budget_mps2": spec.lateral_worse_budget_mps2,
        "yaw_worse_budget_rps": spec.yaw_worse_budget_rps,
        "absolute_lateral_guard_mps2": spec.absolute_lateral_guard_mps2,
        "rationale": spec.rationale,
    }


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def _summary(values: list[float | None]) -> dict[str, Any]:
    arr = np.asarray([value for value in values if value is not None], dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"n": 0, "mean": None, "min": None, "p50": None, "p95": None, "max": None}
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Strong Progress/Support Certificate Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `logs` | `{report['records']['logs']}` |",
        f"| `total` | `{report['records']['total']}` |",
        f"| `candidate_rows` | `{report['records']['candidate_rows']}` |",
        f"| `formal_seed_records` | `{report['records']['formal_seed_records']}` |",
        "",
        "## Ranked Certificates",
        "",
        "| Variant | Certificate | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean | Final Hard Nonworse |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_certificates"][:20]:
        lines.append(
            f"| `{row['variant']}` | `{row['certificate_name']}` | "
            f"`{row['promising_strong_progress_support_certificate']}` | "
            f"{_fmt(row['harmful_block_rate'])} | "
            f"{_fmt(row['beneficial_retain_rate'])} | "
            f"{_fmt(row['allowed_safety_delta_mean'])} | "
            f"{_fmt(row['allowed_progress_delta_mean'])} | "
            f"{_fmt(row['final_hard_nonworse_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Failure Gap",
            "",
            f"- Primary gap: `{report['failure_gap']['primary_gap']}`",
            "",
            "This is an offline certificate audit only. It does not train weights, "
            "change online selection, run replay, modify DP, or authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "`n/a`"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "`n/a`"
    if not np.isfinite(result):
        return "`n/a`"
    return f"`{result:.6g}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
