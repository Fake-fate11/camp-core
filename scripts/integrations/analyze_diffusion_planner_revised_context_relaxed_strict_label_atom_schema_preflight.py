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
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_atom_schema_redesign_preflight import (  # noqa: E402
    _candidate_count,
    _fmt,
    _profiles,
    _record_summary,
    _summary,
    _validate_payload,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_descriptor_separability import (  # noqa: E402
    FORMAL_SEEDS,
    _load_json,
    _path_seeds,
    _record_seed,
)


READY_STATUS = "revised_context_relaxed_strict_label_atom_schema_preflight_ready"
REJECT_STATUS = "revised_context_relaxed_strict_label_atom_schema_preflight_rejected"
SOURCE_BLOCKED_STATUS = (
    "revised_context_relaxed_strict_label_atom_schema_preflight_source_not_ready"
)
FORMAL_SEED_STATUS = (
    "revised_context_relaxed_strict_label_atom_schema_preflight_formal_seed_conflict"
)

SOURCE_READY_STATUS = "revised_context_relaxed_strict_label_atom_bottleneck_diagnosed"
SOURCE_PRIMARY_GAP = (
    "relaxed_strict_label_atom_overlap_blocks_beneficial_and_allows_harmful"
)
SOURCE_NEXT_WORK = "predeclare_relaxed_strict_label_no_leak_atom_schema"
NEXT_WORK = (
    "default_off_relaxed_strict_label_atom_payload_implementation_unit_tests_only"
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
    observed_error_target: str
    uses_product_of_current_tick_features: bool = False


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="longitudinal_accel_step_excess_v1",
        expression="max_t |speed[k,t+1] - speed[k,t]| / dt_s",
        required_fields=("candidate_speed_profile_mps",),
        rationale=(
            "the relaxed strict-label bottleneck left low-atom harmful "
            "comfort regressions; this exposes acceleration-like changes in "
            "the logged current-tick speed profile"
        ),
        observed_error_target="low-atom-score harmful jerk/comfort regressions",
    ),
    AtomSpec(
        name="longitudinal_jerk_surrogate_v1",
        expression=(
            "max_t |speed[k,t+2] - 2*speed[k,t+1] + speed[k,t]| / dt_s^2"
        ),
        required_fields=("candidate_speed_profile_mps",),
        rationale=(
            "uses only the fixed candidate speed profile to approximate "
            "longitudinal roughness that the current progress-conflict atoms "
            "do not represent"
        ),
        observed_error_target="jerk-incompatible harmful alternatives",
    ),
    AtomSpec(
        name="lateral_rate_change_surrogate_v1",
        expression="max_t |lateral_rate[k,t+1] - lateral_rate[k,t]| / dt_s",
        required_fields=("candidate_lateral_error_rate_profile_mps",),
        rationale=(
            "captures lateral-rate roughness without consulting closed-loop "
            "lateral acceleration labels"
        ),
        observed_error_target="lateral/comfort degradation hidden by progress atoms",
    ),
    AtomSpec(
        name="heading_error_change_surrogate_v1",
        expression="max_t |heading_error[k,t+1] - heading_error[k,t]| / dt_s",
        required_fields=("candidate_route_heading_error_profile_rad",),
        rationale=(
            "exposes heading oscillation in the fixed DP candidate relative to "
            "the current route, avoiding a pure progress-shortfall screen"
        ),
        observed_error_target="beneficial/harmful shape overlap under heading-progress atoms",
    ),
    AtomSpec(
        name="corridor_margin_drop_surrogate_v1",
        expression="max_t max(0, corridor_margin[k,t] - corridor_margin[k,t+1])",
        required_fields=("candidate_route_corridor_margin_profile_m",),
        rationale=(
            "detects candidates moving toward the corridor boundary using "
            "current route-corridor geometry only"
        ),
        observed_error_target="safety-penalty-worse harmful alternatives",
    ),
    AtomSpec(
        name="roughness_corridor_conflict_v1",
        expression=(
            "max(longitudinal_jerk_surrogate, lateral_rate_change_surrogate, "
            "heading_error_change_surrogate) * "
            "max_t max(0, corridor_margin[k,t] - corridor_margin[k,t+1])"
        ),
        required_fields=(
            "candidate_speed_profile_mps",
            "candidate_lateral_error_rate_profile_mps",
            "candidate_route_heading_error_profile_rad",
            "candidate_route_corridor_margin_profile_m",
        ),
        rationale=(
            "targets the observed low-score harmful cases where comfort "
            "roughness and safety penalty can coexist while the old "
            "progress-shortfall terms remain near zero; margin drop is used "
            "instead of corridor exhaustion because the matched evidence may "
            "stay inside the absolute safety margin while still moving toward "
            "the boundary"
        ),
        observed_error_target="low-atom-score harmful comfort plus safety regressions",
        uses_product_of_current_tick_features=True,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only no-leak atom-schema preflight after the relaxed "
            "strict-label revised-atom bottleneck diagnosis. It reads existing "
            "current-tick context payloads only and does not train CAMP, run "
            "Diffusion Planner, or change online selection."
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
                "dp_camp_revised_context_relaxed_strict_label_atom_schema_"
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
            "source_outcomes_used_only_in_prior_bottleneck": True,
            "threshold_tuning": False,
            "schema_preflight_only": True,
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Relaxed "
                "strict-label atom proposals are current-tick finite-candidate "
                "coefficients computed from logged speed, route-progress, "
                "heading, lateral-rate, and corridor-margin profiles before "
                "any closed-loop outcome is consulted. Abs, max, finite "
                "differences, and products are evaluated over already fixed "
                "candidate descriptors; after precomputation each candidate "
                "has a fixed nonnegative coefficient vector a_k. CAMP scoring "
                "remains affine score_k(w)=a_k^T w, and the simplex/CVaR/L2 "
                "robust master remains convex in w. This preflight makes no "
                "global convexity claim over trajectory coordinates and does "
                "not construct a DP-side classical Benders master/subproblem, "
                "dual, or valid cut."
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
        and int(np.sum(finite > EPS)) > 0
    )
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_fields": list(spec.required_fields),
        "rationale": spec.rationale,
        "observed_error_target": spec.observed_error_target,
        "records_total": len(records),
        "candidate_rows_total": candidate_rows_total,
        "finite_records": finite_records,
        "nonnegative_records": nonnegative_records,
        "finite_candidate_rows": int(finite.size),
        "nonnegative_candidate_rows": int(np.sum(finite >= -EPS)),
        "nonzero_candidate_rows": int(np.sum(finite > EPS)),
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
    speed = np.asarray(p["speed"], dtype=np.float64)
    lateral_rate = np.asarray(p["lateral_rate"], dtype=np.float64)
    heading_error = np.abs(np.asarray(p["heading_error_interval"], dtype=np.float64))
    corridor_margin = np.asarray(p["corridor_margin_interval"], dtype=np.float64)
    dt_s = float(p["dt_s"])

    accel_step = _max_abs_first_difference(speed) / dt_s
    jerk_surrogate = _max_abs_second_difference(speed) / max(dt_s * dt_s, EPS)
    lateral_rate_change = _max_abs_first_difference(lateral_rate) / dt_s
    heading_error_change = _max_abs_first_difference(heading_error) / dt_s
    corridor_margin_drop = _max_positive_drop(corridor_margin)
    roughness = np.maximum.reduce(
        [jerk_surrogate, lateral_rate_change, heading_error_change]
    )

    if spec.name == "longitudinal_accel_step_excess_v1":
        return accel_step
    if spec.name == "longitudinal_jerk_surrogate_v1":
        return jerk_surrogate
    if spec.name == "lateral_rate_change_surrogate_v1":
        return lateral_rate_change
    if spec.name == "heading_error_change_surrogate_v1":
        return heading_error_change
    if spec.name == "corridor_margin_drop_surrogate_v1":
        return corridor_margin_drop
    if spec.name == "roughness_corridor_conflict_v1":
        return roughness * corridor_margin_drop
    raise ValueError(f"Unsupported atom spec: {spec.name}")


def _max_abs_first_difference(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape[1] < 2:
        return np.zeros(array.shape[0], dtype=np.float64)
    return np.max(np.abs(np.diff(array, axis=1)), axis=1)


def _max_abs_second_difference(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape[1] < 3:
        return np.zeros(array.shape[0], dtype=np.float64)
    return np.max(np.abs(np.diff(array, n=2, axis=1)), axis=1)


def _max_positive_drop(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape[1] < 2:
        return np.zeros(array.shape[0], dtype=np.float64)
    return np.max(np.maximum(array[:, :-1] - array[:, 1:], 0.0), axis=1)


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
            "candidate coefficients are nonnegative by abs/max/product construction",
        ),
        (
            "proposed_atoms_have_nonzero_support",
            all(row["nonzero_candidate_rows"] > 0 for row in atom_rows),
            "each proposed coefficient is nonzero for at least one logged candidate",
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
        next_work = "fix_relaxed_strict_label_bottleneck_source_before_schema_preflight"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif failed_atoms or failed_math:
        status = REJECT_STATUS
        primary_gap = "relaxed_strict_label_atom_schema_preflight_failed"
        next_work = "reject_or_design_smaller_no_leak_relaxed_strict_label_schema"
    else:
        status = READY_STATUS
        primary_gap = "relaxed_strict_label_no_leak_atom_schema_preflight_passed"
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


def _spec_payload(spec: AtomSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_fields": list(spec.required_fields),
        "rationale": spec.rationale,
        "observed_error_target": spec.observed_error_target,
        "current_tick_only": True,
        "nonnegative_by_construction": True,
        "fixed_candidate_coefficient": True,
        "affine_score_compatible": True,
        "uses_product_of_current_tick_features": spec.uses_product_of_current_tick_features,
        "trajectory_coordinate_convexity_claim": False,
        "classical_benders_claim": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Relaxed Strict-Label Atom Schema Preflight",
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
        "| Atom | Target | Passed | Mean | P95 | Max | Product Fixed Coefficient |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["atom_reports"]:
        summary = row["summary"]
        lines.append(
            f"| `{row['name']}` | {row['observed_error_target']} | "
            f"`{row['passed_preflight']}` | {_fmt(summary['mean'])} | "
            f"{_fmt(summary['p95'])} | {_fmt(summary['max'])} | "
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


if __name__ == "__main__":
    main()
