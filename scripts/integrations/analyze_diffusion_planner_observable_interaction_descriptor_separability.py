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
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    BLOCKED_ACTIONS as BASE_BLOCKED_ACTIONS,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    FEATURE_SPECS as BASE_OBSERVABLE_FEATURE_SPECS,
    FORMAL_SEEDS,
    HARMFUL_BLOCK_RATE_TARGET,
    MIN_BENEFICIAL_CANDIDATES,
    MIN_HARMFUL_CANDIDATES,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    _candidate_rows as _base_candidate_rows,
    _class_counts,
    _decision as _base_decision,
    _failure_gap,
    _feature_coverage,
    _feature_report,
    _load_json,
    _pair_reports,
    _path_seeds,
    _payload_scalar_vector,
    _ranked_screens,
    _record_seed,
    _source_gate,
)
from scripts.integrations.plan_diffusion_planner_observable_interaction_descriptor_preflight import (  # noqa: E402
    DESCRIPTOR_SPECS,
    NEXT_WORK as PREFLIGHT_NEXT_WORK,
    READY_STATUS as PREFLIGHT_READY_STATUS,
    InteractionDescriptorSpec,
)


READY_STATUS = "observable_interaction_descriptor_separability_ready_for_certificate_design"
REJECT_STATUS = "observable_interaction_descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = "observable_interaction_descriptor_separability_source_not_ready"
FORMAL_SEED_STATUS = "observable_interaction_descriptor_separability_formal_seed_conflict"
NEXT_WORK_CERTIFICATE = "offline_observable_interaction_certificate_design_only"
NEXT_WORK_BOTTLENECK = (
    "diagnose_observable_interaction_descriptor_bottleneck_before_new_replay"
)
BLOCKED_ACTIONS = tuple(
    dict.fromkeys(
        (
            *BASE_BLOCKED_ACTIONS,
            "new_replay_authorized",
            "closed_loop_smoke_authorized",
            "classic_benders_claim_authorized",
        )
    )
)


@dataclass(frozen=True)
class _ScreenSpec:
    name: str
    source_field: str
    direction_hint: str
    rationale: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen for predeclared observable "
            "interaction descriptors. It reads existing matched observable "
            "logs only; no replay, training, or online selection is changed."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--clearance_budget_m", type=float, default=2.0)
    parser.add_argument("--lateral_error_budget_m", type=float, default=0.5)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument(
        "--harmful_block_rate_target",
        type=float,
        default=HARMFUL_BLOCK_RATE_TARGET,
    )
    parser.add_argument(
        "--beneficial_retain_rate_target",
        type=float,
        default=BENEFICIAL_RETAIN_RATE_TARGET,
    )
    parser.add_argument(
        "--allowed_harmful_rate_target",
        type=float,
        default=ALLOWED_HARMFUL_RATE_TARGET,
    )
    parser.add_argument(
        "--min_beneficial_candidates",
        type=int,
        default=MIN_BENEFICIAL_CANDIDATES,
    )
    parser.add_argument(
        "--min_harmful_candidates",
        type=int,
        default=MIN_HARMFUL_CANDIDATES,
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
        preflight_report=_load_json(args.preflight_json),
        matched_contract_report=_load_json(args.matched_contract_json),
        label=args.label,
        red_distance_budget_m=args.red_distance_budget_m,
        clearance_budget_m=args.clearance_budget_m,
        lateral_error_budget_m=args.lateral_error_budget_m,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
        min_beneficial_candidates=args.min_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
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
    preflight_report: dict[str, Any],
    matched_contract_report: dict[str, Any],
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    lateral_error_budget_m: float = 0.5,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = json.loads(log_path.read_text(encoding="utf-8-sig"))
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
        preflight_report=preflight_report,
        matched_contract_report=matched_contract_report,
        label=label,
        red_distance_budget_m=red_distance_budget_m,
        clearance_budget_m=clearance_budget_m,
        lateral_error_budget_m=lateral_error_budget_m,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    preflight_report: dict[str, Any],
    matched_contract_report: dict[str, Any],
    label: str | None = None,
    descriptor_specs: tuple[InteractionDescriptorSpec, ...] = DESCRIPTOR_SPECS,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    lateral_error_budget_m: float = 0.5,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    preflight = _preflight_gate(preflight_report)
    contract = _source_gate(matched_contract_report)
    source_ready = bool(preflight["passed"] and contract["passed"])
    source = {"passed": source_ready, "preflight": preflight, "contract": contract}
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, record_formal = _interaction_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            descriptor_specs=descriptor_specs,
            red_distance_budget_m=red_distance_budget_m,
            clearance_budget_m=clearance_budget_m,
            lateral_error_budget_m=lateral_error_budget_m,
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        formal_seed_records += int(record_formal)
        rows.extend(record_rows)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if int(row["candidate_index"]) != 0]
    class_counts = _class_counts(alternative_rows)
    screen_specs = tuple(
        _ScreenSpec(
            name=spec.name,
            source_field="observable_interaction",
            direction_hint="allow_low",
            rationale=spec.rationale,
        )
        for spec in descriptor_specs
    )
    feature_reports = [
        _feature_report(
            spec,
            alternative_rows,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
        for spec in screen_specs
    ]
    pair_reports = _pair_reports(
        feature_reports,
        alternative_rows,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    base_decision = _base_decision(
        {"passed": source_ready},
        feature_reports,
        pair_reports,
        formal_seed_records=formal_seed_records,
        class_counts=class_counts,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    decision = _interaction_decision(base_decision, preflight, contract)
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_descriptor_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_thresholds": True,
            "future_outcome_labels_used_for_evaluation": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "descriptor_names": [spec.name for spec in descriptor_specs],
            "budgets": {
                "red_distance_budget_m": float(red_distance_budget_m),
                "clearance_budget_m": float(clearance_budget_m),
                "lateral_error_budget_m": float(lateral_error_budget_m),
            },
            "label_definition": {
                "beneficial": (
                    "candidate k>0 is feasible, improves outcome value over "
                    "candidate0 by min_value_gain, preserves progress within "
                    "progress_loss_budget_m, and is hard-safety-nonworse"
                ),
                "harmful": (
                    "candidate k>0 is infeasible, hard-safety-worse, loses "
                    "more than min_value_loss in outcome value, or exceeds the "
                    "progress loss budget"
                ),
                "neutral": "all other k>0 candidates",
                "outcome_value_direction": "higher_is_better",
            },
            "math_boundary": (
                "Observable interaction descriptors are fixed current-tick "
                "finite-candidate coefficients computed before candidate "
                "closed-loop outcomes. Outcome labels define only offline "
                "beneficial/harmful classes and threshold-screen diagnostics. "
                "If any descriptor is later atomized, it is a fixed coefficient "
                "a_k, so CAMP score_k(w)=a_k^T w remains affine and the "
                "simplex/CVaR/L2 robust master remains convex. Products and "
                "hinges are feature computations over fixed payloads, not a "
                "trajectory-space convexity claim. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_gates": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "feature_coverage": _feature_coverage(alternative_rows, screen_specs),
        "feature_reports": feature_reports,
        "pair_reports": pair_reports,
        "ranked_screens": _ranked_screens(feature_reports, pair_reports),
        "failure_gap": _failure_gap(feature_reports, pair_reports, class_counts),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _interaction_candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    *,
    descriptor_specs: tuple[InteractionDescriptorSpec, ...],
    red_distance_budget_m: float,
    clearance_budget_m: float,
    lateral_error_budget_m: float,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool]:
    rows, formal_seed = _base_candidate_rows(
        raw,
        context,
        label,
        BASE_OBSERVABLE_FEATURE_SPECS,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
    )
    values = _interaction_values(
        raw["observable_state_logging"],
        candidate_count=len(rows),
        descriptor_specs=descriptor_specs,
        label=label,
        red_distance_budget_m=red_distance_budget_m,
        clearance_budget_m=clearance_budget_m,
        lateral_error_budget_m=lateral_error_budget_m,
    )
    for row in rows:
        candidate_index = int(row["candidate_index"])
        row["features"] = {
            name: float(vector[candidate_index])
            for name, vector in values.items()
            if np.isfinite(vector[candidate_index])
        }
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True
    return rows, formal_seed


def _interaction_values(
    payload: dict[str, Any],
    *,
    candidate_count: int,
    descriptor_specs: tuple[InteractionDescriptorSpec, ...],
    label: str,
    red_distance_budget_m: float,
    clearance_budget_m: float,
    lateral_error_budget_m: float,
) -> dict[str, np.ndarray]:
    projection = _payload_vector(
        payload,
        "candidate_route_projection_s_m",
        candidate_count,
        label,
    )
    lateral = np.abs(
        _payload_vector(payload, "candidate_route_lateral_error_m", candidate_count, label)
    )
    heading = np.abs(
        _payload_vector(
            payload,
            "candidate_route_heading_change_rad",
            candidate_count,
            label,
        )
    )
    clearance = _nan_to(
        _payload_vector(
            payload,
            "candidate_min_obstacle_clearance_lower_bound_m",
            candidate_count,
            label,
        ),
        np.inf,
    )
    red_distance = _nan_to(
        _payload_vector(
            payload,
            "candidate_red_stopline_distance_m",
            candidate_count,
            label,
            none_value=np.inf,
        ),
        np.inf,
    )
    red_alignment = _nan_to(
        _payload_vector(
            payload,
            "candidate_red_heading_alignment",
            candidate_count,
            label,
            none_value=0.0,
        ),
        0.0,
    )

    red_risk = np.maximum(red_alignment, 0.0) * np.maximum(
        float(red_distance_budget_m) - red_distance,
        0.0,
    )
    clearance_deficit = np.maximum(float(clearance_budget_m) - clearance, 0.0)
    route_progress_gain = np.maximum(projection - float(projection[0]), 0.0)
    route_progress_loss = np.maximum(float(projection[0]) - projection, 0.0)
    lateral_worse = np.maximum(lateral - float(lateral[0]), 0.0)
    lateral_excess = np.maximum(lateral - float(lateral_error_budget_m), 0.0)
    clearance_top1 = float(clearance[0])
    if np.isfinite(clearance_top1):
        clearance_gain = np.maximum(clearance - clearance_top1, 0.0)
    else:
        clearance_gain = np.zeros_like(clearance, dtype=np.float64)
    red_gain = np.maximum(float(red_risk[0]) - red_risk, 0.0)
    safety_gain = clearance_gain + red_gain
    raw_values = {
        "red_aligned_stopline_proximity_hinge_v1": red_risk,
        "clearance_progress_tradeoff_hinge_v1": (
            clearance_deficit * route_progress_gain
        ),
        "turn_lateral_clearance_context_hinge_v1": (
            heading * lateral_excess * clearance_deficit
        ),
        "top1_deviation_without_current_safety_gain_v1": np.maximum(
            lateral_worse + route_progress_loss - safety_gain,
            0.0,
        ),
    }
    return {
        spec.name: np.asarray(raw_values[spec.name], dtype=np.float64)
        for spec in descriptor_specs
    }


def _payload_vector(
    payload: dict[str, Any],
    field: str,
    candidate_count: int,
    label: str,
    *,
    none_value: float | None = None,
) -> np.ndarray:
    value = payload.get(field)
    if value is None and none_value is not None:
        return np.full(candidate_count, float(none_value), dtype=np.float64)
    vector = _payload_scalar_vector(value, candidate_count, f"{label} {field}", field)
    if vector is None:
        return np.full(candidate_count, np.nan, dtype=np.float64)
    return vector


def _nan_to(values: np.ndarray, replacement: float) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64).copy()
    result[~np.isfinite(result)] = float(replacement)
    return result


def _preflight_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    passed = bool(
        decision.get("passed")
        and decision.get("status") == PREFLIGHT_READY_STATUS
        and decision.get("authorized_next_work") == PREFLIGHT_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _interaction_decision(
    base_decision: dict[str, Any],
    preflight: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    if not preflight["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "interaction_preflight_not_ready"
        next_work = "fix_interaction_preflight_before_separability"
    elif not contract["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "matched_contract_gate_not_passed"
        next_work = "fix_matched_observable_outcome_contract_before_separability"
    elif base_decision["status"].endswith("_formal_seed_conflict"):
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif base_decision["passed"]:
        status = READY_STATUS
        primary_gap = "no_gap_promising_observable_interaction_screen_found"
        next_work = NEXT_WORK_CERTIFICATE
    else:
        status = REJECT_STATUS
        primary_gap = base_decision["primary_gap"].replace(
            "observable_descriptors",
            "observable_interaction_descriptors",
        )
        next_work = NEXT_WORK_BOTTLENECK
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": int(base_decision.get("promising_screen_count", 0)),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gap = report["failure_gap"]
    lines = [
        "# Observable Interaction Descriptor Separability",
        "",
        "This read-only audit tests whether current-tick observable interaction "
        "descriptors can separate offline beneficial alternatives from harmful "
        "alternatives relative to DP Top-1.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Screen",
        "",
        "```json",
        json.dumps(gap.get("best_screen"), indent=2, sort_keys=True),
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
