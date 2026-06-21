#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
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
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    EPS,
    FORMAL_SEEDS,
    _candidate_branch_components,
    _outcome_float,
    _outcomes,
    _planned_red_values,
)


READY_STATUS = "external_context_alternative_atom_search_ready"
REJECT_STATUS = "external_context_alternative_atom_search_rejected"
AUTHORIZED_NEXT_WORK = "external_context_alternative_atom_design_preflight_only"
LOG_NAME = "camp_selection_log.json"
HARD_OUTCOME_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class AtomSpec:
    name: str
    source_field: str
    coefficient_rule: str
    nonnegative_proof: str


ATOM_SPECS = (
    AtomSpec(
        name="signal_arrival_urgency_hinge_v1",
        source_field="candidate_first_signal_arrival_time_s",
        coefficient_rule=(
            "a_k=max(T-candidate_first_signal_arrival_time_s[k],0)/T for finite "
            "arrival time, else 0; T is the logged support horizon"
        ),
        nonnegative_proof="hinge divided by positive horizon is nonnegative",
    ),
    AtomSpec(
        name="right_of_way_blocked_indicator_v1",
        source_field="candidate_right_of_way_blocked_indicator",
        coefficient_rule="a_k=candidate_right_of_way_blocked_indicator[k]",
        nonnegative_proof="payload finite checks require binary values in {0,1}",
    ),
    AtomSpec(
        name="route_speed_limit_excess_integral_v1",
        source_field="candidate_speed_limit_excess_integral_mps",
        coefficient_rule=(
            "a_k=sum_t max(speed_k,t - limit_k,t, 0) * dt from the logged payload"
        ),
        nonnegative_proof="sum of nonnegative speed-limit excess hinges",
    ),
    AtomSpec(
        name="route_speed_limit_unavailable_fraction_v1",
        source_field="candidate_speed_limit_available_fraction",
        coefficient_rule="a_k=max(1-candidate_speed_limit_available_fraction[k],0)",
        nonnegative_proof="payload finite checks constrain available fraction to [0,1]",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only existing-log search for external-context atom candidates. "
            "Selection scores use only current-tick payload fields; candidate "
            "closed-loop outcomes are posterior labels used only for audit."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--progress_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--max_combo_size", type=int, default=2)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        progress_loss_budget_m=args.progress_loss_budget_m,
        max_combo_size=args.max_combo_size,
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    paths: list[Path],
    *,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    progress_loss_budget_m: float = 0.10,
    max_combo_size: int = 2,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        payload = _load_json(log_path)
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            records.append({**raw, "_log_path": str(log_path), "_record_index": index})
    return analyze_records(
        records,
        expected_records=expected_records,
        expected_candidates=expected_candidates,
        progress_loss_budget_m=progress_loss_budget_m,
        max_combo_size=max_combo_size,
        label=label,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    records: list[dict[str, Any]],
    *,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    progress_loss_budget_m: float = 0.10,
    max_combo_size: int = 2,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if progress_loss_budget_m < 0.0:
        raise ValueError("progress_loss_budget_m must be nonnegative.")
    if max_combo_size <= 0:
        raise ValueError("max_combo_size must be positive.")

    formal_seed_records = sum(int(int(record.get("seed", -1)) in FORMAL_SEEDS) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    combos = _atom_combos(atom_specs, max_combo_size=max_combo_size)
    record_checks = _record_checks(
        records,
        expected_records=expected_records,
        expected_candidates=expected_candidates,
    )
    candidate_reports = [
        _candidate_report(
            combo,
            records,
            expected_candidates=expected_candidates,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        for combo in combos
    ]
    decision = _decision(candidate_reports, record_checks, formal_seed_records)
    return {
        "analysis": {
            "name": "dp_camp_external_context_alternative_atom_search_v1",
            "label": label,
            "role": (
                "read-only existing-log search for external-context atom "
                "candidates after the signal-arrival path regressed or no-oped"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_selection": False,
            "future_outcome_labels_used_for_evaluation": True,
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
            "expected_records": expected_records,
            "expected_candidates": int(expected_candidates),
            "progress_loss_budget_m": float(progress_loss_budget_m),
            "max_combo_size": int(max_combo_size),
            "atom_specs": [_spec_json(spec) for spec in atom_specs],
            "selection_rule": (
                "For each atom or atom pair, compute fixed nonnegative current-tick "
                "coefficients from external_context_payload_logging, sum them, "
                "and choose the lowest-score feasible candidate only if route "
                "progress, planned-red, red-stopping, and absolute lateral guards "
                "are satisfied. Ties preserve the logged selected index."
            ),
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The searched "
                "atoms are fixed current-tick finite-candidate coefficients, each "
                "nonnegative by binary, hinge, or payload finite-check definition. "
                "Atom-combo scores are fixed sums of coefficients, so any later "
                "CAMP score remains score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "master remains convex over fixed atoms. Closed-loop outcomes are "
                "posterior labels only. This is a finite-candidate audit, not a "
                "classical Benders decomposition."
            ),
        },
        "records": {
            "total": len(records),
            "formal_seed_records": int(formal_seed_records),
            "candidate_count_values": sorted(
                {int(record.get("num_candidates", 0)) for record in records}
            ),
        },
        "record_checks": record_checks,
        "candidate_reports": candidate_reports,
        "ranked_candidates": _rank_candidates(candidate_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _atom_combos(
    atom_specs: tuple[AtomSpec, ...],
    *,
    max_combo_size: int,
) -> list[tuple[AtomSpec, ...]]:
    combos: list[tuple[AtomSpec, ...]] = []
    limit = min(max_combo_size, len(atom_specs))
    for size in range(1, limit + 1):
        combos.extend(tuple(combo) for combo in itertools.combinations(atom_specs, size))
    return combos


def _record_checks(
    records: list[dict[str, Any]],
    *,
    expected_records: int | None,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if expected_records is not None:
        checks.append(_check_equal("record_count", len(records), expected_records))
    for index, record in enumerate(records):
        label = f"record_{index}"
        payload = record.get("external_context_payload_logging")
        checks.extend(
            [
                _check_equal(
                    f"{label}_candidate_count",
                    int(record.get("num_candidates", 0)),
                    expected_candidates,
                ),
                _check_equal(f"{label}_payload_present", isinstance(payload, dict), True),
                _check_equal(
                    f"{label}_outcomes_present",
                    isinstance(record.get("candidate_closed_loop_outcomes"), list),
                    True,
                ),
            ]
        )
        if isinstance(payload, dict):
            checks.extend(
                [
                    _check_equal(
                        f"{label}_payload_candidate_count",
                        int(payload.get("candidate_count", 0)),
                        expected_candidates,
                    ),
                    _check_equal(f"{label}_selection_effect", payload.get("selection_effect"), False),
                    _check_equal(
                        f"{label}_future_outcome_leakage",
                        payload.get("future_outcome_leakage"),
                        False,
                    ),
                    _check_equal(
                        f"{label}_closed_loop_outcome_fields_read",
                        payload.get("closed_loop_outcome_fields_read"),
                        False,
                    ),
                ]
            )
    return checks


def _candidate_report(
    combo: tuple[AtomSpec, ...],
    records: list[dict[str, Any]],
    *,
    expected_candidates: int,
    progress_loss_budget_m: float,
) -> dict[str, Any]:
    rows = [
        _record_effect(
            combo,
            record,
            record_index=index,
            expected_candidates=expected_candidates,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        for index, record in enumerate(records)
    ]
    valid = [row for row in rows if row["valid"]]
    changed = [row for row in valid if row["changed"]]
    changed_all_gate = [
        row
        for row in changed
        if row["relations"]["safety_cost_noninferior"]
        and row["relations"]["hard_nonworse"]
        and row["relations"]["posterior_progress_within_budget"]
    ]
    return {
        "name": "+".join(spec.name for spec in combo),
        "source_fields": [spec.source_field for spec in combo],
        "coefficient_rules": [spec.coefficient_rule for spec in combo],
        "nonnegative_proofs": [spec.nonnegative_proof for spec in combo],
        "records": len(rows),
        "valid_records": len(valid),
        "ranking_signal_records": sum(int(row["ranking_signal"]) for row in valid),
        "changed_records": len(changed),
        "changed_safety_cost_better_records": sum(
            int(row["relations"]["safety_cost_better"]) for row in changed
        ),
        "changed_safety_cost_noninferior_records": sum(
            int(row["relations"]["safety_cost_noninferior"]) for row in changed
        ),
        "changed_hard_nonworse_records": sum(
            int(row["relations"]["hard_nonworse"]) for row in changed
        ),
        "changed_posterior_progress_within_budget_records": sum(
            int(row["relations"]["posterior_progress_within_budget"]) for row in changed
        ),
        "changed_all_gate_records": len(changed_all_gate),
        "changed_safety_cost_delta_mean": _mean(
            [row["deltas"]["safety_cost_delta"] for row in changed]
        ),
        "record_effects": rows,
        "gate_passed": bool(changed and len(changed_all_gate) == len(changed)),
    }


def _record_effect(
    combo: tuple[AtomSpec, ...],
    record: dict[str, Any],
    *,
    record_index: int,
    expected_candidates: int,
    progress_loss_budget_m: float,
) -> dict[str, Any]:
    label = f"record {record_index}"
    try:
        candidate_count = int(record.get("num_candidates", 0))
        if candidate_count != expected_candidates:
            raise ValueError("candidate_count_mismatch")
        selected = int(record.get("selected_index"))
        payload = record.get("external_context_payload_logging")
        if not isinstance(payload, dict):
            raise ValueError("payload_missing")
        scores = _combo_scores(combo, payload, candidate_count)
        feasible = _feasible(record, candidate_count)
        route_progress = _vector(record.get("candidate_route_progress"), candidate_count)
        planned_red, _ = _planned_red_values(record, candidate_count)
        red_stopping = _optional_vector(
            record.get("candidate_red_stopping_margin_cost"),
            candidate_count,
            default=np.zeros(candidate_count, dtype=np.float64),
        )
        lateral = _optional_vector(
            record.get("candidate_perfect_tracker_lateral_acceleration_magnitude_mps2"),
            candidate_count,
            default=np.zeros(candidate_count, dtype=np.float64),
        )
        chosen = _selected_preserving_argmin(
            scores,
            selected,
            feasible=feasible,
            route_progress=route_progress,
            planned_red=planned_red,
            red_stopping=red_stopping,
            lateral=lateral,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        outcomes = _outcomes(
            record.get("candidate_closed_loop_outcomes"),
            candidate_count,
            label,
        )
        components = _candidate_branch_components(outcomes, planned_red, feasible)
        selected_cost = float(components[selected]["cost"])
        chosen_cost = float(components[chosen]["cost"])
        selected_progress = _outcome_float(outcomes[selected], "progress_m")
        chosen_progress = _outcome_float(outcomes[chosen], "progress_m")
    except Exception as exc:  # noqa: BLE001 - reports become audit rows.
        return {
            "record_index": record_index,
            "valid": False,
            "reason": str(exc),
        }
    changed = chosen != selected
    return {
        "record_index": record_index,
        "valid": True,
        "selected_index": int(selected),
        "chosen_index": int(chosen),
        "changed": bool(changed),
        "ranking_signal": bool(float(np.max(scores) - np.min(scores)) > EPS),
        "score_selected": float(scores[selected]),
        "score_chosen": float(scores[chosen]),
        "deltas": {
            "safety_cost_delta": chosen_cost - selected_cost,
            "posterior_progress_delta_m": chosen_progress - selected_progress,
            "route_progress_delta_m": float(route_progress[chosen] - route_progress[selected]),
            "planned_red_delta": float(planned_red[chosen] - planned_red[selected]),
            "red_stopping_delta": float(red_stopping[chosen] - red_stopping[selected]),
            "lateral_delta_mps2": float(lateral[chosen] - lateral[selected]),
        },
        "relations": {
            "safety_cost_better": bool(chosen_cost < selected_cost - EPS),
            "safety_cost_noninferior": bool(chosen_cost <= selected_cost + EPS),
            "hard_nonworse": _hard_nonworse(outcomes[chosen], outcomes[selected]),
            "posterior_progress_within_budget": bool(
                chosen_progress + progress_loss_budget_m >= selected_progress
            ),
        },
        "component_costs": {
            "selected": components[selected],
            "chosen": components[chosen],
        },
    }


def _combo_scores(
    combo: tuple[AtomSpec, ...],
    payload: dict[str, Any],
    candidate_count: int,
) -> np.ndarray:
    values = [
        _atom_values(spec, payload, candidate_count)
        for spec in combo
    ]
    return np.sum(np.vstack(values), axis=0)


def _atom_values(
    spec: AtomSpec,
    payload: dict[str, Any],
    candidate_count: int,
) -> np.ndarray:
    values = payload.get(spec.source_field)
    horizon = _support_horizon_s(payload)
    if spec.name == "signal_arrival_urgency_hinge_v1":
        if values is None:
            return np.zeros(candidate_count, dtype=np.float64)
        parsed = np.asarray(
            [np.nan if value is None else float(value) for value in values],
            dtype=np.float64,
        )
        if parsed.shape != (candidate_count,):
            raise ValueError(f"{spec.source_field}_shape_mismatch")
        result = np.zeros(candidate_count, dtype=np.float64)
        finite = np.isfinite(parsed)
        result[finite] = np.maximum(horizon - parsed[finite], 0.0) / horizon
        return result
    if spec.name == "route_speed_limit_unavailable_fraction_v1":
        parsed = _vector(values, candidate_count)
        return np.maximum(1.0 - parsed, 0.0)
    return _vector(values, candidate_count)


def _support_horizon_s(payload: dict[str, Any]) -> float:
    horizons = payload.get("horizons")
    if not isinstance(horizons, dict):
        return 1.0
    steps = float(horizons.get("support_steps", 1.0))
    dt = float(horizons.get("dt_s", 1.0))
    return max(steps * dt, EPS)


def _selected_preserving_argmin(
    scores: np.ndarray,
    selected: int,
    *,
    feasible: np.ndarray,
    route_progress: np.ndarray,
    planned_red: np.ndarray,
    red_stopping: np.ndarray,
    lateral: np.ndarray,
    progress_loss_budget_m: float,
) -> int:
    if selected < 0 or selected >= scores.shape[0]:
        raise ValueError("selected_index_out_of_range")
    eligible = (
        feasible
        & (route_progress + progress_loss_budget_m >= route_progress[selected])
        & (planned_red <= planned_red[selected] + EPS)
        & (red_stopping <= red_stopping[selected] + EPS)
        & (lateral <= 2.0 + EPS)
    )
    if not eligible.any():
        return int(selected)
    best_score = float(np.min(scores[eligible]))
    if bool(eligible[selected]) and float(scores[selected]) <= best_score + EPS:
        return int(selected)
    indices = np.flatnonzero(eligible)
    best = min(indices, key=lambda index: (float(scores[index]), int(index)))
    return int(best)


def _feasible(record: dict[str, Any], candidate_count: int) -> np.ndarray:
    values = record.get("feasible_mask")
    if values is None:
        return np.ones(candidate_count, dtype=bool)
    array = np.asarray(values, dtype=bool).reshape(-1)
    if array.shape != (candidate_count,):
        raise ValueError("feasible_mask_shape_mismatch")
    if not array.any():
        return np.ones(candidate_count, dtype=bool)
    return array


def _optional_vector(
    values: Any,
    candidate_count: int,
    *,
    default: np.ndarray,
) -> np.ndarray:
    if values is None:
        return default.astype(np.float64)
    return _vector(values, candidate_count)


def _vector(values: Any, candidate_count: int) -> np.ndarray:
    if not isinstance(values, list) or len(values) != candidate_count:
        raise ValueError("candidate_vector_shape_mismatch")
    parsed = np.asarray(
        [np.nan if value is None else float(value) for value in values],
        dtype=np.float64,
    )
    if parsed.shape != (candidate_count,) or not np.all(np.isfinite(parsed)):
        raise ValueError("candidate_vector_nonfinite")
    return parsed


def _hard_nonworse(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return all(
        float(bool(candidate[field])) <= float(bool(baseline[field]))
        for field in HARD_OUTCOME_FIELDS
    )


def _decision(
    candidate_reports: list[dict[str, Any]],
    record_checks: list[dict[str, Any]],
    formal_seed_records: int,
) -> dict[str, Any]:
    passing = [
        report["name"] for report in candidate_reports
        if report["gate_passed"]
    ]
    record_checks_passed = all(check["passed"] for check in record_checks)
    passed = bool(record_checks_passed and not formal_seed_records and passing)
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "primary_gap": (
            "alternative_external_context_atom_certificate_found"
            if passed
            else "no_alternative_external_context_atom_certificate_found"
        ),
        "passing_candidates": passing,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": (
            "Predeclare a design-only atom schema for the passing candidates; "
            "do not deploy, train, or run Full36."
            if passed
            else (
                "Reject additional external-context atomization from the current "
                "existing logs and return to materiality discovery or a new "
                "predeclared logging-only evidence plan."
            )
        ),
    }


def _rank_candidates(candidate_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "name": report["name"],
            "gate_passed": report["gate_passed"],
            "changed_records": report["changed_records"],
            "changed_all_gate_records": report["changed_all_gate_records"],
            "changed_safety_cost_delta_mean": report["changed_safety_cost_delta_mean"],
            "ranking_signal_records": report["ranking_signal_records"],
        }
        for report in candidate_reports
    ]
    return sorted(
        rows,
        key=lambda row: (
            not bool(row["gate_passed"]),
            -int(row["changed_all_gate_records"]),
            float("inf")
            if row["changed_safety_cost_delta_mean"] is None
            else float(row["changed_safety_cost_delta_mean"]),
            -int(row["ranking_signal_records"]),
            row["name"],
        ),
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Alternative Atom Search",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Passing candidates: `{decision['passing_candidates']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Ranked Candidates",
        "",
        "| Candidate | Gate | Changed | Changed all-gate | Mean changed SafetyCost delta | Ranking signal records |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_candidates"]:
        lines.append(
            f"| `{row['name']}` | `{row['gate_passed']}` | "
            f"`{row['changed_records']}` | `{row['changed_all_gate_records']}` | "
            f"`{row['changed_safety_cost_delta_mean']}` | "
            f"`{row['ranking_signal_records']}` |"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _spec_json(spec: AtomSpec) -> dict[str, str]:
    return {
        "name": spec.name,
        "source_field": spec.source_field,
        "coefficient_rule": spec.coefficient_rule,
        "nonnegative_proof": spec.nonnegative_proof,
    }


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
