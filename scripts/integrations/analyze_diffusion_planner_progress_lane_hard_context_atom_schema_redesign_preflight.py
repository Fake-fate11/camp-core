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
from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (  # noqa: E402
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_descriptor_separability import (  # noqa: E402
    FORMAL_SEEDS,
    _load_json,
    _matrix_any_width,
    _path_seeds,
    _record_seed,
)


READY_STATUS = (
    "progress_lane_hard_context_atom_schema_redesign_preflight_ready"
)
REJECT_STATUS = (
    "progress_lane_hard_context_atom_schema_redesign_preflight_rejected"
)
SOURCE_BLOCKED_STATUS = (
    "progress_lane_hard_context_atom_schema_redesign_preflight_source_not_ready"
)
FORMAL_SEED_STATUS = (
    "progress_lane_hard_context_atom_schema_redesign_preflight_formal_seed_conflict"
)

SOURCE_READY_STATUS = "progress_lane_hard_context_separability_bottleneck_diagnosed"
SOURCE_PRIMARY_GAP = (
    "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
)
SOURCE_NEXT_WORK = "predeclare_revised_context_atom_schema_or_reject_context_route"
NEXT_WORK = (
    "default_off_revised_progress_lane_hard_context_atom_payload_implementation_unit_tests_only"
)

EPS = 1e-12

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class AtomSpec:
    name: str
    expression: str
    required_fields: tuple[str, ...]
    rationale: str
    uses_product_of_current_tick_features: bool = False


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="route_progress_shortfall_vs_candidate_best_v1",
        expression=(
            "max(0, max_j sum_t dp_progress_delta[j,t] - "
            "sum_t dp_progress_delta[k,t])"
        ),
        required_fields=("candidate_route_progress_delta_profile_m",),
        rationale=(
            "the bottleneck showed harmful allowed candidates were often "
            "progress/value losses; this atom exposes current-tick route "
            "progress shortfall without outcome labels"
        ),
    ),
    AtomSpec(
        name="route_progress_efficiency_shortfall_v1",
        expression=(
            "max(0, dt * sum_t max(speed[k,t],0) - "
            "sum_t max(dp_progress_delta[k,t],0))"
        ),
        required_fields=(
            "candidate_speed_profile_mps",
            "candidate_route_progress_delta_profile_m",
        ),
        rationale=(
            "distinguishes motion that consumes speed budget without producing "
            "route progress, a likely driver of progress-loss harmful switches"
        ),
    ),
    AtomSpec(
        name="heading_progress_conflict_v1",
        expression=(
            "max_t abs(heading_error[k,t]) * "
            "max(0, max_j dp_progress_delta[j,t] - dp_progress_delta[k,t])"
        ),
        required_fields=(
            "candidate_route_heading_error_profile_rad",
            "candidate_route_progress_delta_profile_m",
        ),
        rationale=(
            "penalizes candidates that are both misaligned with the route and "
            "behind the best current candidate's route-progress profile"
        ),
        uses_product_of_current_tick_features=True,
    ),
    AtomSpec(
        name="lateral_rate_progress_conflict_v1",
        expression=(
            "max_t abs(lateral_error_rate[k,t]) * "
            "max(0, max_j dp_progress_delta[j,t] - dp_progress_delta[k,t])"
        ),
        required_fields=(
            "candidate_lateral_error_rate_profile_mps",
            "candidate_route_progress_delta_profile_m",
        ),
        rationale=(
            "targets lane-drift dynamics specifically when they coincide with "
            "route-progress loss rather than treating lateral rate alone as a "
            "global reject signal"
        ),
        uses_product_of_current_tick_features=True,
    ),
    AtomSpec(
        name="corridor_progress_conflict_v1",
        expression=(
            "max_t max(0, corridor_safety_margin - corridor_margin[k,t]) * "
            "max(0, max_j dp_progress_delta[j,t] - dp_progress_delta[k,t])"
        ),
        required_fields=(
            "candidate_route_corridor_margin_profile_m",
            "candidate_route_progress_delta_profile_m",
        ),
        rationale=(
            "keeps corridor margin exhaustion available only when it couples "
            "to route-progress loss; the previous standalone descriptor was "
            "nonseparating on the matched context evidence"
        ),
        uses_product_of_current_tick_features=True,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for a revised DP-CAMP progress+lane/hard "
            "context atom schema after bottleneck diagnosis. It reads existing "
            "nonformal logs only; it does not run DP, train CAMP, or change the "
            "online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--bottleneck_json", type=Path, required=True)
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
        bottleneck_report=_load_json(args.bottleneck_json),
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
    bottleneck_report: dict[str, Any],
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
        bottleneck_report=bottleneck_report,
        label=label,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(bottleneck_report)
    records: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record, formal_seed = _record(item["raw"], item["context"], f"record {index}")
        records.append(record)
        formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    atom_rows = [_atom_report(spec, records) for spec in atom_specs]
    math_checks = _math_checks(atom_rows)
    decision = _decision(
        source,
        atom_rows,
        math_checks,
        formal_seed_records=formal_seed_records,
    )
    return {
        "analysis": {
            "name": (
                "dp_camp_progress_lane_hard_context_atom_schema_redesign_"
                "preflight_v1"
            ),
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_evaluation": False,
            "threshold_tuning": False,
            "schema_preflight_only": True,
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Revised "
                "progress+lane/hard context atoms are current-tick "
                "finite-candidate coefficients computed from DP candidate "
                "geometry, route progress, speed, heading, lateral-rate, and "
                "corridor-margin profiles before any closed-loop outcome is "
                "consulted. Products and max operators are evaluated over "
                "already fixed candidate descriptors; after precomputation "
                "each candidate has a fixed coefficient vector a_k. CAMP "
                "scoring remains affine score_k(w)=a_k^T w, and the "
                "simplex/CVaR/L2 robust master remains convex in w. This "
                "preflight makes no global convexity claim over trajectory "
                "coordinates and does not construct a DP-side classical "
                "Benders master/subproblem, dual, or valid cut."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_bottleneck_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "proposed_atom_schema": [_spec_payload(spec) for spec in atom_specs],
        "atom_reports": atom_rows,
        "math_checks": math_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _record(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
) -> tuple[dict[str, Any], bool]:
    payload = raw.get("progress_lane_hard_context_logging")
    candidate_count = _candidate_count(raw, payload, label)
    _validate_payload(payload, candidate_count, label)
    formal_seed = bool(set(context.get("path_seeds") or ()) & FORMAL_SEEDS)
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True
    return {
        "context": context,
        "candidate_count": candidate_count,
        "payload": payload,
        "profiles": _profiles(payload, candidate_count, label),
    }, formal_seed


def _candidate_count(raw: dict[str, Any], payload: Any, label: str) -> int:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing progress_lane_hard_context_logging payload.")
    payload_count = payload.get("candidate_count")
    raw_count = raw.get("num_candidates")
    try:
        count = int(payload_count)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} context candidate_count must be an integer.") from exc
    if count <= 0:
        raise ValueError(f"{label} context candidate_count must be positive.")
    if raw_count is not None and int(raw_count) != count:
        raise ValueError(f"{label} raw num_candidates and payload candidate_count differ.")
    return count


def _validate_payload(payload: Any, candidate_count: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing progress_lane_hard_context_logging payload.")
    expected = {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(
                f"{label} progress_lane_hard_context_logging "
                f"{field}={payload.get(field)!r}."
            )
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} context payload embeds outcome labels.")
    if payload.get("candidate_count") != candidate_count:
        raise ValueError(f"{label} context candidate_count mismatch.")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        raise ValueError(f"{label} context finite checks missing.")
    for field in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES:
        if finite_checks.get(field) is not True:
            raise ValueError(f"{label} context finite check failed {field}.")


def _profiles(
    payload: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any]:
    lateral_rate = _matrix_any_width(
        payload.get("candidate_lateral_error_rate_profile_mps"),
        candidate_count,
        f"{label} candidate_lateral_error_rate_profile_mps",
    )
    speed = _matrix_any_width(
        payload.get("candidate_speed_profile_mps"),
        candidate_count,
        f"{label} candidate_speed_profile_mps",
    )
    progress_delta = _matrix_any_width(
        payload.get("candidate_route_progress_delta_profile_m"),
        candidate_count,
        f"{label} candidate_route_progress_delta_profile_m",
    )
    corridor_margin = _matrix_any_width(
        payload.get("candidate_route_corridor_margin_profile_m"),
        candidate_count,
        f"{label} candidate_route_corridor_margin_profile_m",
    )
    heading_error = _matrix_any_width(
        payload.get("candidate_route_heading_error_profile_rad"),
        candidate_count,
        f"{label} candidate_route_heading_error_profile_rad",
    )
    if lateral_rate.shape != speed.shape or lateral_rate.shape != progress_delta.shape:
        raise ValueError(f"{label} context interval profile shapes do not match.")
    interval_count = progress_delta.shape[1]
    if corridor_margin.shape[1] < interval_count:
        raise ValueError(f"{label} corridor margin horizon is shorter than intervals.")
    if heading_error.shape[1] < interval_count:
        raise ValueError(f"{label} heading horizon is shorter than intervals.")
    return {
        "dt_s": _finite_positive_dt(payload, label),
        "corridor_safety_margin_m": _finite_nonnegative_budget(
            payload,
            "corridor_safety_margin_m",
            label,
        ),
        "lateral_rate": lateral_rate,
        "speed": speed,
        "progress_delta": progress_delta,
        "corridor_margin_interval": corridor_margin[:, :interval_count],
        "heading_error_interval": heading_error[:, :interval_count],
    }


def _finite_positive_dt(payload: dict[str, Any], label: str) -> float:
    horizons = payload.get("horizons")
    if not isinstance(horizons, dict):
        raise ValueError(f"{label} context horizons missing.")
    try:
        value = float(horizons["dt_s"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} context dt_s must be finite positive.") from exc
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} context dt_s must be finite positive.")
    return value


def _finite_nonnegative_budget(
    payload: dict[str, Any],
    field: str,
    label: str,
) -> float:
    budgets = payload.get("budgets")
    if not isinstance(budgets, dict):
        raise ValueError(f"{label} context budgets missing.")
    try:
        value = float(budgets[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} context budget {field} must be finite.") from exc
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{label} context budget {field} must be finite nonnegative.")
    return value


def _atom_report(spec: AtomSpec, records: list[dict[str, Any]]) -> dict[str, Any]:
    values_by_record: list[np.ndarray] = []
    finite_records = 0
    nonnegative_records = 0
    for record in records:
        values = _atom_values(spec, record)
        values_by_record.append(values)
        finite_records += int(np.all(np.isfinite(values)))
        nonnegative_records += int(np.all(values >= -EPS))

    candidate_rows_total = int(sum(record["candidate_count"] for record in records))
    concatenated = np.concatenate(values_by_record) if values_by_record else np.asarray([])
    finite = concatenated[np.isfinite(concatenated)]
    passed = bool(
        finite_records == len(records)
        and nonnegative_records == len(records)
        and concatenated.size == candidate_rows_total
    )
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_fields": list(spec.required_fields),
        "rationale": spec.rationale,
        "records_total": len(records),
        "candidate_rows_total": candidate_rows_total,
        "finite_records": finite_records,
        "nonnegative_records": nonnegative_records,
        "finite_candidate_rows": int(finite.size),
        "nonnegative_candidate_rows": int(np.sum(finite >= -EPS)),
        "summary": _summary(finite),
        "no_leak": True,
        "current_tick_only": True,
        "fixed_before_weight_optimization": True,
        "affine_score_compatible": True,
        "convex_master_compatible": True,
        "fixed_coefficient_affine_only": True,
        "uses_product_of_current_tick_features": spec.uses_product_of_current_tick_features,
        "trajectory_coordinate_convexity_claim": False,
        "classical_benders_claim": False,
        "passed_preflight": passed,
    }


def _atom_values(spec: AtomSpec, record: dict[str, Any]) -> np.ndarray:
    p = record["profiles"]
    progress_delta = np.asarray(p["progress_delta"], dtype=np.float64)
    speed = np.asarray(p["speed"], dtype=np.float64)
    lateral_rate = np.asarray(p["lateral_rate"], dtype=np.float64)
    heading_error = np.abs(np.asarray(p["heading_error_interval"], dtype=np.float64))
    corridor_margin = np.asarray(p["corridor_margin_interval"], dtype=np.float64)
    dt_s = float(p["dt_s"])
    safety_margin = float(p["corridor_safety_margin_m"])

    total_progress = np.sum(progress_delta, axis=1)
    total_progress_ref = float(np.max(total_progress))
    route_progress_shortfall = np.maximum(total_progress_ref - total_progress, 0.0)

    nonnegative_route_progress = np.sum(np.maximum(progress_delta, 0.0), axis=1)
    speed_integral = np.sum(np.maximum(speed, 0.0), axis=1) * dt_s
    route_progress_efficiency_shortfall = np.maximum(
        speed_integral - nonnegative_route_progress,
        0.0,
    )

    interval_progress_ref = np.max(progress_delta, axis=0, keepdims=True)
    interval_progress_shortfall = np.maximum(
        interval_progress_ref - progress_delta,
        0.0,
    )
    corridor_exhaustion = np.maximum(safety_margin - corridor_margin, 0.0)

    if spec.name == "route_progress_shortfall_vs_candidate_best_v1":
        return route_progress_shortfall
    if spec.name == "route_progress_efficiency_shortfall_v1":
        return route_progress_efficiency_shortfall
    if spec.name == "heading_progress_conflict_v1":
        return np.max(heading_error * interval_progress_shortfall, axis=1)
    if spec.name == "lateral_rate_progress_conflict_v1":
        return np.max(np.abs(lateral_rate) * interval_progress_shortfall, axis=1)
    if spec.name == "corridor_progress_conflict_v1":
        return np.max(corridor_exhaustion * interval_progress_shortfall, axis=1)
    raise ValueError(f"Unsupported atom spec: {spec.name}")


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    blocked_actions = report.get("blocked_actions")
    blocked_clear = True
    if isinstance(blocked_actions, dict):
        blocked_clear = not any(bool(blocked_actions.get(key)) for key in BLOCKED_ACTIONS)
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
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


def _math_checks(atom_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        (
            "all_atoms_no_leak",
            all(row["no_leak"] for row in atom_rows),
            "atom values are computed from current-tick payload fields only",
        ),
        (
            "all_atoms_current_tick_only",
            all(row["current_tick_only"] for row in atom_rows),
            "no simulator future state or closed-loop outcome field is required",
        ),
        (
            "all_atoms_nonnegative",
            all(row["nonnegative_candidate_rows"] == row["candidate_rows_total"] for row in atom_rows),
            "candidate coefficients are nonnegative by max/product construction",
        ),
        (
            "affine_score_preserved",
            all(row["affine_score_compatible"] for row in atom_rows),
            "score_k(w)=a_k^T w over fixed precomputed atom coefficients",
        ),
        (
            "simplex_cvar_l2_master_convex",
            all(row["convex_master_compatible"] for row in atom_rows),
            "the robust master remains convex in w once atom values are fixed",
        ),
        (
            "product_atoms_are_fixed_coefficients_only",
            all(
                row["fixed_coefficient_affine_only"]
                for row in atom_rows
                if row["uses_product_of_current_tick_features"]
            ),
            "products are not optimized over trajectory variables in this gate",
        ),
        (
            "no_trajectory_coordinate_convexity_claim",
            not any(row["trajectory_coordinate_convexity_claim"] for row in atom_rows),
            "no global convexity over DP trajectory coordinates is claimed",
        ),
        (
            "no_classical_benders_claim",
            not any(row["classical_benders_claim"] for row in atom_rows),
            "no DP-side master/subproblem, dual, or valid cut is constructed",
        ),
    ]
    return [
        {"name": name, "passed": bool(passed), "evidence": evidence}
        for name, passed, evidence in checks
    ]


def _decision(
    source: dict[str, Any],
    atom_rows: list[dict[str, Any]],
    math_checks: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    failed_atoms = [
        row["name"]
        for row in atom_rows
        if not row["passed_preflight"]
    ]
    failed_math = [
        check["name"]
        for check in math_checks
        if not check["passed"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "source_bottleneck_gate_not_ready"
        next_work = "fix_context_bottleneck_source_before_schema_redesign"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif failed_atoms or failed_math:
        status = REJECT_STATUS
        primary_gap = "revised_context_atom_schema_preflight_failed"
        next_work = "reject_context_route_or_design_smaller_current_tick_schema"
    else:
        status = READY_STATUS
        primary_gap = "revised_context_atom_schema_preflight_passed"
        next_work = NEXT_WORK
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "failed_atoms": failed_atoms,
        "failed_math_checks": failed_math,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total_records": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _spec_payload(spec: AtomSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_fields": list(spec.required_fields),
        "rationale": spec.rationale,
        "current_tick_only": True,
        "nonnegative_by_construction": True,
        "fixed_candidate_coefficient": True,
        "affine_score_compatible": True,
        "uses_product_of_current_tick_features": spec.uses_product_of_current_tick_features,
        "trajectory_coordinate_convexity_claim": False,
        "classical_benders_claim": False,
    }


def _summary(values: np.ndarray) -> dict[str, Any]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
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
        "# Progress + Lane/Hard Context Atom Schema Redesign Preflight",
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
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Proposed Atom Schema",
        "",
        "```json",
        json.dumps(report["proposed_atom_schema"], indent=2, sort_keys=True),
        "```",
        "",
        "## Atom Reports",
        "",
        "| Atom | Passed | Mean | P95 | Max | Product Fixed Coefficient |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["atom_reports"]:
        summary = row["summary"]
        lines.append(
            f"| `{row['name']}` | `{row['passed_preflight']}` | "
            f"{_fmt(summary['mean'])} | {_fmt(summary['p95'])} | "
            f"{_fmt(summary['max'])} | "
            f"`{row['uses_product_of_current_tick_features'] and row['fixed_coefficient_affine_only']}` |"
        )
    lines.extend(
        [
            "",
            "## Math Checks",
            "",
            "```json",
            json.dumps(report["math_checks"], indent=2, sort_keys=True),
            "```",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6g}"


if __name__ == "__main__":
    main()
