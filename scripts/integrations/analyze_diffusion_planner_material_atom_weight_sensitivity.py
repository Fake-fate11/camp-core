#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
    ATOM_FAMILIES,
    DEFAULT_REQUIRED_BUCKETS,
    FORMAL_SEEDS,
    _log_context,
    _record_analysis,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_WEIGHTS,
    _load_scenario_bucket_manifest,
)


READY_AVAILABILITY_STATUS = "material_atom_schema_availability_ready_for_offline_weight_audit"
READY_STATUS = "material_atom_weight_sensitivity_ready_for_offline_selector_screen"
REJECT_STATUS = "material_atom_weight_sensitivity_rejected"
SOURCE_BLOCKED_STATUS = "material_atom_weight_sensitivity_source_not_ready"
FORMAL_SEED_STATUS = "material_atom_weight_sensitivity_formal_seed_conflict"

BOOL_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
OUTCOME_NUMERIC_FIELDS = (
    "progress_m",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
)
BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)
EPS = 1e-12


@dataclass(frozen=True)
class WeightVariant:
    name: str
    weights: tuple[float, float, float, float, float]
    rationale: str


PREDECLARED_VARIANTS: tuple[WeightVariant, ...] = (
    WeightVariant(
        name="uniform_material",
        weights=(0.20, 0.20, 0.20, 0.20, 0.20),
        rationale="balanced sensitivity baseline over all five material atoms",
    ),
    WeightVariant(
        name="traffic_rule_focus",
        weights=(0.25, 0.10, 0.10, 0.15, 0.40),
        rationale="prioritize traffic-rule exposure while retaining feasibility and Top-1 shape",
    ),
    WeightVariant(
        name="traffic_top1_guard",
        weights=(0.20, 0.10, 0.10, 0.35, 0.25),
        rationale="traffic safety with a stronger DP Top-1 shape guard",
    ),
    WeightVariant(
        name="support_comfort_guard",
        weights=(0.20, 0.25, 0.25, 0.20, 0.10),
        rationale="stress progress/support and comfort preservation",
    ),
    WeightVariant(
        name="hard_traffic_support",
        weights=(0.35, 0.20, 0.10, 0.10, 0.25),
        rationale="hard-feasibility first with traffic and support protection",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak material-atom weight sensitivity audit. It selects "
            "among fixed DP candidates using fixed current-tick material atoms "
            "and evaluates the choices with offline outcome labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--availability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--bootstrap_resamples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=12345)
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
        availability_report=_load_json(args.availability_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        scale_percentile=args.scale_percentile,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
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
    availability_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    scale_percentile: float = 95.0,
    bootstrap_resamples: int = 2000,
    seed: int = 12345,
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
            items.append(
                {
                    "raw": raw,
                    "context": {
                        **context,
                        "record_index": index,
                    },
                }
            )
    return analyze_records(
        items,
        availability_report=availability_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        scale_percentile=scale_percentile,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    availability_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    scale_percentile: float = 95.0,
    bootstrap_resamples: int = 2000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
    variants: tuple[WeightVariant, ...] = PREDECLARED_VARIANTS,
    progress_loss_budget_m: float = 0.05,
    hard_nonworse_threshold: float = 0.99,
    beneficial_preservation_threshold: float = 0.80,
    cvar_percentile: float = 90.0,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    if not 0.0 < scale_percentile < 100.0:
        raise ValueError("scale_percentile must be in (0, 100).")
    if not 0.0 <= cvar_percentile < 100.0:
        raise ValueError("cvar_percentile must be in [0, 100).")
    source = _source_gate(availability_report)
    records = [
        _load_record(item["raw"], item["context"], f"record {index}")
        for index, item in enumerate(items)
    ]
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    scales = _scales(records, scale_percentile)
    variant_reports = [
        _variant_report(
            variant,
            records,
            scales,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
            progress_loss_budget_m=progress_loss_budget_m,
            hard_nonworse_threshold=hard_nonworse_threshold,
            beneficial_preservation_threshold=beneficial_preservation_threshold,
            cvar_percentile=cvar_percentile,
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
            "name": "dp_camp_material_atom_weight_sensitivity_v1",
            "label": label,
            "role": (
                "offline no-leak fixed-candidate material-atom weight "
                "sensitivity audit"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_selection": False,
            "future_outcome_labels_used_for_evaluation": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "atom_families": list(ATOM_FAMILIES),
            "normalization": {
                "scale_percentile": float(scale_percentile),
                "scales": scales,
                "clip": 10.0,
            },
            "predeclared_variants": [
                {
                    "name": variant.name,
                    "weights": dict(zip(ATOM_FAMILIES, variant.weights)),
                    "rationale": variant.rationale,
                }
                for variant in variants
            ],
            "accept_criteria": {
                "safety_cost_delta_vs_current_ci95_high": "< 0",
                "safety_cost_delta_vs_current_cvar90": "<= 0",
                "hard_nonworse_vs_current": f">= {hard_nonworse_threshold}",
                "progress_delta_vs_current_ci95_low": f">= -{progress_loss_budget_m}",
                "beneficial_current_preserved_rate": (
                    f">= {beneficial_preservation_threshold}"
                ),
                "fallback_retained_rate": "== 1",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Material "
                "atoms are fixed current-tick finite-candidate coefficients. "
                "Every screened weight vector is a nonnegative simplex point, "
                "so score_k(w)=a_k^T w remains affine in w and the "
                "simplex/CVaR/L2 CAMP master remains convex over fixed atoms. "
                "Closed-loop outcomes are used only after selection for offline "
                "evaluation. This audit does not construct a DP-side "
                "master/subproblem, dual, or valid cut, and it does not claim "
                "classical Benders decomposition."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_availability_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "baseline_current_vs_top1": _baseline_vs_top1(records),
        "variants": variant_reports,
        "ranked_variants": _rank_variants(variant_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _load_record(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    analyzed = _record_analysis(raw, context, label)
    candidate_count = int(analyzed["candidate_count"])
    outcomes = _outcomes(
        raw.get("candidate_closed_loop_outcomes"),
        candidate_count,
        label,
    )
    feasible = _bool_vector(raw.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    material_atoms = np.column_stack(
        [
            analyzed["families"][family]["values"]
            for family in ATOM_FAMILIES
        ]
    ).astype(np.float64)
    if material_atoms.shape != (candidate_count, len(ATOM_FAMILIES)):
        raise ValueError(f"{label} material atom matrix has invalid shape.")
    if not np.all(np.isfinite(material_atoms)) or np.any(material_atoms < -1e-12):
        raise ValueError(f"{label} material atoms must be finite and nonnegative.")
    material_atoms = np.maximum(material_atoms, 0.0)
    safety_cost = np.asarray(
        [_candidate_safety_cost(outcome, raw, idx) for idx, outcome in enumerate(outcomes)],
        dtype=np.float64,
    )
    progress = np.asarray(
        [_nonnegative_outcome_float(outcome, "progress_m") for outcome in outcomes],
        dtype=np.float64,
    )
    return {
        "context": analyzed["context"],
        "candidate_count": candidate_count,
        "selected_index": int(analyzed["selected_index"]),
        "feasible": feasible,
        "material_atoms": material_atoms,
        "outcomes": outcomes,
        "safety_cost": safety_cost,
        "progress": progress,
    }


def _variant_report(
    variant: WeightVariant,
    records: list[dict[str, Any]],
    scales: dict[str, float],
    *,
    bootstrap_resamples: int,
    seed: int,
    progress_loss_budget_m: float,
    hard_nonworse_threshold: float,
    beneficial_preservation_threshold: float,
    cvar_percentile: float,
) -> dict[str, Any]:
    weights = _weights(variant)
    selected = np.asarray([record["selected_index"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    chosen = np.asarray(
        [_select(record, weights, scales) for record in records],
        dtype=np.int64,
    )
    safety = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    progress = np.asarray([record["progress"] for record in records], dtype=np.float64)
    current_safety = safety[np.arange(len(records)), selected]
    chosen_safety = safety[np.arange(len(records)), chosen]
    top1_safety = safety[:, 0]
    current_progress = progress[np.arange(len(records)), selected]
    chosen_progress = progress[np.arange(len(records)), chosen]
    fallback_mask = np.asarray([not record["feasible"].any() for record in records], dtype=bool)
    changed = chosen != selected
    harmful_current = (current_safety - top1_safety) > EPS
    beneficial_current = (top1_safety - current_safety) > EPS
    safety_delta = chosen_safety - current_safety
    progress_delta = chosen_progress - current_progress
    hard_nonworse = _hard_nonworse_rate(records, chosen, selected)
    beneficial_preserved = _conditional_rate(chosen == selected, beneficial_current)
    fallback_retained = _conditional_rate(chosen == selected, fallback_mask)
    safety_summary = _paired_summary(
        safety_delta,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    progress_summary = _paired_summary(
        progress_delta,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    passed = bool(
        safety_summary["ci95_high"] is not None
        and safety_summary["ci95_high"] < 0.0
        and _cvar_tail_mean(safety_delta, cvar_percentile) <= 0.0
        and hard_nonworse >= hard_nonworse_threshold
        and progress_summary["ci95_low"] is not None
        and progress_summary["ci95_low"] >= -float(progress_loss_budget_m)
        and beneficial_preserved >= beneficial_preservation_threshold
        and fallback_retained >= 1.0 - EPS
    )
    return {
        "name": variant.name,
        "rationale": variant.rationale,
        "weights": dict(zip(ATOM_FAMILIES, weights)),
        "simplex_sum": float(np.sum(weights)),
        "minimum_weight": float(np.min(weights)),
        "changed_records": int(np.sum(changed)),
        "changed_rate": float(np.mean(changed)),
        "nonfallback_changed_rate": _conditional_rate(changed, ~fallback_mask),
        "top1_selected_rate": float(np.mean(chosen == top1)),
        "fallback_retained_rate": fallback_retained,
        "harmful_current_records": int(np.sum(harmful_current)),
        "harmful_current_changed_rate": _conditional_rate(changed, harmful_current),
        "beneficial_current_records": int(np.sum(beneficial_current)),
        "beneficial_current_preserved_rate": beneficial_preserved,
        "hard_nonworse_vs_current": hard_nonworse,
        "safety_cost_delta_vs_current": safety_summary,
        "safety_cost_delta_vs_top1": _paired_summary(
            chosen_safety - top1_safety,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "safety_cost_delta_vs_current_cvar90": _cvar_tail_mean(
            safety_delta,
            cvar_percentile,
        ),
        "progress_delta_vs_current": progress_summary,
        "outcome_delta_vs_current": _outcome_delta_summary(records, chosen, selected),
        "by_bucket": _bucket_reports(records, chosen, selected),
        "passed_offline_weight_screen": passed,
    }


def _select(
    record: dict[str, Any],
    weights: np.ndarray,
    scales: dict[str, float],
) -> int:
    selected = int(record["selected_index"])
    feasible = np.asarray(record["feasible"], dtype=bool)
    if not feasible.any():
        return selected
    normalized = _normalized_atoms(record["material_atoms"], scales)
    scores = normalized @ weights
    masked = np.where(feasible, scores, np.inf)
    return int(np.argmin(masked))


def _normalized_atoms(
    atoms: np.ndarray,
    scales: dict[str, float],
) -> np.ndarray:
    scale = np.asarray([scales[family] for family in ATOM_FAMILIES], dtype=np.float64)
    return np.clip(np.asarray(atoms, dtype=np.float64) / scale.reshape(1, -1), 0.0, 10.0)


def _scales(records: list[dict[str, Any]], percentile: float) -> dict[str, float]:
    matrix = np.vstack([record["material_atoms"] for record in records])
    result: dict[str, float] = {}
    for idx, family in enumerate(ATOM_FAMILIES):
        values = matrix[:, idx]
        positive = values[np.isfinite(values) & (values > EPS)]
        result[family] = (
            max(float(np.percentile(positive, percentile)), 1e-6)
            if positive.size
            else 1.0
        )
    return result


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == READY_AVAILABILITY_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
        "missing_atom_families": decision.get("missing_atom_families", []),
        "missing_required_buckets": decision.get("missing_required_buckets", []),
        "failed_convexity_checks": decision.get("failed_convexity_checks", []),
    }


def _decision(
    source: dict[str, Any],
    variants: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    passing = [
        variant["name"]
        for variant in variants
        if variant["passed_offline_weight_screen"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not run weight sensitivity until the availability gate passes."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using this weight-sensitivity evidence."
    elif passing:
        status = READY_STATUS
        next_step = (
            "Design only an offline no-leak selector screen around the passing "
            "weight variants; replay, formal seeds, and retraining remain blocked."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "Reject these predeclared material-weight directions for promotion; "
            "redesign the offline weighting hypothesis or atom scaling before replay."
        )
    return {
        "status": status,
        "passing_variants": passing,
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


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "nonfallback": int(sum(record["feasible"].any() for record in records)),
        "fallback": int(sum(not record["feasible"].any() for record in records)),
        "formal_seed_records": int(formal_seed_records),
        "scenario_bucket_counts": _scenario_bucket_counts(records),
    }


def _baseline_vs_top1(records: list[dict[str, Any]]) -> dict[str, Any]:
    selected = np.asarray([record["selected_index"] for record in records], dtype=np.int64)
    safety = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    progress = np.asarray([record["progress"] for record in records], dtype=np.float64)
    current_safety = safety[np.arange(len(records)), selected]
    top1_safety = safety[:, 0]
    current_progress = progress[np.arange(len(records)), selected]
    top1_progress = progress[:, 0]
    return {
        "selected_non_top1_rate": float(np.mean(selected != 0)),
        "safety_cost_selected_minus_top1": _summary(current_safety - top1_safety),
        "progress_selected_minus_top1": _summary(current_progress - top1_progress),
    }


def _scenario_bucket_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for bucket in record["context"].get("scenario_buckets", ["overall"]):
            grouped.setdefault(bucket, []).append(record)
    return {
        bucket: {
            "records": len(bucket_records),
            "candidate_rows": int(
                sum(record["candidate_count"] for record in bucket_records)
            ),
        }
        for bucket, bucket_records in sorted(grouped.items())
    }


def _bucket_reports(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        for bucket in record["context"].get("scenario_buckets", ["overall"]):
            grouped.setdefault(bucket, []).append(index)
    rows = []
    safety = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    progress = np.asarray([record["progress"] for record in records], dtype=np.float64)
    for bucket, indices in sorted(grouped.items()):
        idx = np.asarray(indices, dtype=np.int64)
        rows.append(
            {
                "bucket": bucket,
                "records": int(idx.size),
                "changed_rate": float(np.mean(chosen[idx] != selected[idx])),
                "safety_cost_delta_vs_current": _summary(
                    safety[idx, chosen[idx]] - safety[idx, selected[idx]]
                ),
                "progress_delta_vs_current": _summary(
                    progress[idx, chosen[idx]] - progress[idx, selected[idx]]
                ),
            }
        )
    return rows


def _candidate_safety_cost(outcome: dict[str, Any], record: dict[str, Any], index: int) -> float:
    progress = np.asarray(
        [
            _nonnegative_outcome_float(item, "progress_m")
            for item in record["candidate_closed_loop_outcomes"]
        ],
        dtype=np.float64,
    )
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    branch_feasible = feasible if feasible.any() else np.ones_like(feasible, dtype=bool)
    progress_ref = (
        float(np.max(progress[branch_feasible]))
        if branch_feasible.any()
        else float(np.max(progress))
    )
    progress_denom = max(progress_ref, 1.0)
    planned_red = _planned_red_values(record, len(progress))
    components = {
        "collision": float(bool(outcome["collision"])),
        "near_miss": float(bool(outcome["near_miss"])),
        "lane_violation": float(bool(outcome["lane_violation"])),
        "realized_red_light": float(bool(outcome["red_light_violation"])),
        "planned_red_light": min(max(float(planned_red[index]), 0.0), 1.0),
        "mean_jerk": min(
            _nonnegative_outcome_float(outcome, "mean_jerk_mps3")
            / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
            SAFETY_COST_V1_CLIP,
        ),
        "mean_lateral_acceleration": min(
            _nonnegative_outcome_float(outcome, "mean_lateral_acceleration_mps2")
            / SAFETY_COST_V1_NORMALIZATION["mean_lateral_acceleration_mps2"],
            SAFETY_COST_V1_CLIP,
        ),
        "route_shortfall": min(
            max(
                (progress_ref - _nonnegative_outcome_float(outcome, "progress_m"))
                / progress_denom,
                0.0,
            ),
            1.0,
        ),
    }
    return float(
        sum(
            float(components[key]) * float(SAFETY_COST_V1_WEIGHTS[key])
            for key in components
        )
    )


def _outcome_delta_summary(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in OUTCOME_NUMERIC_FIELDS:
        result[field] = _summary(
            [
                _outcome_float(record["outcomes"][int(chosen_idx)], field)
                - _outcome_float(record["outcomes"][int(selected_idx)], field)
                for record, chosen_idx, selected_idx in zip(records, chosen, selected)
            ]
        )
    for field in BOOL_FIELDS:
        result[field] = _summary(
            [
                float(bool(record["outcomes"][int(chosen_idx)].get(field)))
                - float(bool(record["outcomes"][int(selected_idx)].get(field)))
                for record, chosen_idx, selected_idx in zip(records, chosen, selected)
            ]
        )
    return result


def _hard_nonworse_rate(records: list[dict[str, Any]], chosen: np.ndarray, reference: np.ndarray) -> float:
    rows = []
    for record, chosen_idx, reference_idx in zip(records, chosen, reference):
        chosen_outcome = record["outcomes"][int(chosen_idx)]
        reference_outcome = record["outcomes"][int(reference_idx)]
        rows.append(
            all(
                float(bool(chosen_outcome[field])) <= float(bool(reference_outcome[field]))
                for field in BOOL_FIELDS
            )
        )
    return float(np.mean(rows)) if rows else 0.0


def _planned_red_values(record: dict[str, Any], size: int) -> np.ndarray:
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
    ):
        values = record.get(key)
        if values is None:
            continue
        vector = np.asarray(values, dtype=np.float64).reshape(-1)
        if vector.shape != (size,):
            raise ValueError(f"{key} must have shape [{size}].")
        if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
            raise ValueError(f"{key} must contain finite nonnegative values.")
        return vector
    return np.zeros(size, dtype=np.float64)


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index", index) != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _bool_vector(value: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(value, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(item, (bool, np.bool_)) for item in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _nonnegative_outcome_float(outcome: dict[str, Any], field: str) -> float:
    value = float(outcome[field])
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Candidate outcome {field!r} must be finite and nonnegative.")
    return value


def _outcome_float(outcome: dict[str, Any], field: str) -> float:
    value = outcome.get(field)
    return 0.0 if value is None else float(value)


def _paired_summary(
    values: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    summary = _summary(arr)
    if arr.size == 0 or bootstrap_resamples <= 0:
        return {**summary, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(seed)
    means = np.empty(int(bootstrap_resamples), dtype=np.float64)
    for idx in range(int(bootstrap_resamples)):
        sample = arr[rng.integers(0, arr.size, size=arr.size)]
        means[idx] = float(np.mean(sample))
    return {
        **summary,
        "ci95_low": float(np.percentile(means, 2.5)),
        "ci95_high": float(np.percentile(means, 97.5)),
    }


def _cvar_tail_mean(values: np.ndarray, percentile: float) -> float:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return 0.0
    threshold = float(np.percentile(arr, percentile))
    tail = arr[arr >= threshold]
    return float(np.mean(tail)) if tail.size else threshold


def _conditional_rate(values: np.ndarray, mask: np.ndarray) -> float:
    mask = np.asarray(mask, dtype=bool).reshape(-1)
    if not mask.any():
        return 1.0
    return float(np.mean(np.asarray(values, dtype=bool).reshape(-1)[mask]))


def _summary(values: Any) -> dict[str, Any]:
    arr = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=np.float64).reshape(-1)
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


def _weights(variant: WeightVariant) -> np.ndarray:
    weights = np.asarray(variant.weights, dtype=np.float64).reshape(-1)
    if weights.shape != (len(ATOM_FAMILIES),):
        raise ValueError(f"{variant.name} must define {len(ATOM_FAMILIES)} weights.")
    if not np.all(np.isfinite(weights)) or np.any(weights < -EPS):
        raise ValueError(f"{variant.name} weights must be finite and nonnegative.")
    if abs(float(np.sum(weights)) - 1.0) > 1e-9:
        raise ValueError(f"{variant.name} weights must sum to one.")
    return np.maximum(weights, 0.0)


def _rank_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        safety = variant["safety_cost_delta_vs_current"]
        rows.append(
            {
                "name": variant["name"],
                "passed_offline_weight_screen": variant["passed_offline_weight_screen"],
                "safety_delta_mean": safety["mean"],
                "safety_delta_ci95_high": safety["ci95_high"],
                "safety_delta_cvar90": variant["safety_cost_delta_vs_current_cvar90"],
                "progress_delta_ci95_low": variant["progress_delta_vs_current"]["ci95_low"],
                "hard_nonworse_vs_current": variant["hard_nonworse_vs_current"],
                "changed_rate": variant["changed_rate"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed_offline_weight_screen"],
            float(row["safety_delta_ci95_high"] or 0.0),
            float(row["safety_delta_cvar90"] or 0.0),
            float(row["changed_rate"]),
        ),
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    records = report["records"]
    lines = [
        "# Material Atom Weight Sensitivity Audit",
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
        f"| `logs` | `{records['logs']}` |",
        f"| `total` | `{records['total']}` |",
        f"| `candidate_rows` | `{records['candidate_rows']}` |",
        f"| `nonfallback` | `{records['nonfallback']}` |",
        f"| `fallback` | `{records['fallback']}` |",
        f"| `formal_seed_records` | `{records['formal_seed_records']}` |",
        "",
        "## Ranked Variants",
        "",
        "| Variant | Pass | Safety Mean | Safety CI High | Safety CVaR90 | Progress CI Low | Hard Nonworse | Changed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_variants"]:
        lines.append(
            f"| `{row['name']}` | `{row['passed_offline_weight_screen']}` | "
            f"{_fmt(row['safety_delta_mean'])} | "
            f"{_fmt(row['safety_delta_ci95_high'])} | "
            f"{_fmt(row['safety_delta_cvar90'])} | "
            f"{_fmt(row['progress_delta_ci95_low'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} | "
            f"{_fmt(row['changed_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Variant Details",
            "",
            "| Variant | Changed | Top1 Rate | Fallback Retained | Beneficial Preserved | Harmful Changed |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for variant in report["variants"]:
        lines.append(
            f"| `{variant['name']}` | "
            f"{_fmt(variant['changed_rate'])} | "
            f"{_fmt(variant['top1_selected_rate'])} | "
            f"{_fmt(variant['fallback_retained_rate'])} | "
            f"{_fmt(variant['beneficial_current_preserved_rate'])} | "
            f"{_fmt(variant['harmful_current_changed_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "This is an offline fixed-candidate sensitivity audit only. It does "
            "not train weights, change online selection, run closed-loop replay, "
            "modify Diffusion Planner, or authorize formal seeds.",
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
