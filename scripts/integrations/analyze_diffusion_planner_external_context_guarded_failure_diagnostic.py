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
from scripts.integrations.analyze_diffusion_planner_external_context_atom_outcome_counterfactual import (  # noqa: E402
    READY_STATUS as COUNTERFACTUAL_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_external_context_atom_schema_dry_run import (  # noqa: E402
    _atom_coefficients,
    _combined_scores,
)
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    _candidate_branch_components,
    _outcomes,
    _planned_red_values,
)


READY_STATUS = "external_context_guarded_failure_diagnostic_ready"
REJECT_STATUS = "external_context_guarded_failure_diagnostic_rejected"
LOG_NAME = "camp_selection_log.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only diagnostic for a failed progress-guarded external-context "
            "atom counterfactual. This consumes existing logs only."
        )
    )
    parser.add_argument("--counterfactual_json", type=Path, required=True)
    parser.add_argument("--atomization_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--record_index", type=int, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        counterfactual=_load_json(args.counterfactual_json),
        atomization=_load_json(args.atomization_json),
        candidate_root=args.candidate_root,
        record_index=args.record_index,
        label=args.label,
        paths={
            "counterfactual_json": str(args.counterfactual_json),
            "atomization_json": str(args.atomization_json),
            "candidate_root": str(args.candidate_root),
        },
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
    *,
    counterfactual: dict[str, Any],
    atomization: dict[str, Any],
    candidate_root: Path,
    record_index: int,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    records = _load_records(candidate_root)
    source = _source_summary(counterfactual)
    source_checks = _source_checks(source)
    record_checks = [
        {
            "name": "record_index_in_range",
            "passed": 0 <= record_index < len(records),
            "actual": record_index,
            "expected": f"0..{max(len(records) - 1, 0)}",
        },
        {
            "name": "counterfactual_row_available",
            "passed": _counterfactual_row(counterfactual, record_index) is not None,
            "actual": record_index,
            "expected": "row present",
        },
    ]
    selected_specs = [
        row for row in atomization.get("selected_atom_candidates") or []
        if isinstance(row, dict)
    ]
    if not (0 <= record_index < len(records)):
        record = None
        diagnostic = None
    else:
        record = records[record_index]
        diagnostic = _diagnostic_record(
            record=record,
            counterfactual_row=_counterfactual_row(counterfactual, record_index),
            selected_specs=selected_specs,
        )
    diagnostic_checks = _diagnostic_checks(diagnostic)
    passed = (
        all(check["passed"] for check in source_checks)
        and all(check["passed"] for check in record_checks)
        and all(check["passed"] for check in diagnostic_checks)
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_guarded_failure_diagnostic_v1",
            "label": label,
            "role": (
                "existing-log explanation of a failed progress-guarded "
                "external-context atom counterfactual"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_guard": False,
            "future_outcome_labels_used_for_evaluation": True,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This diagnostic reads fixed current-tick candidate descriptors "
                "and posterior outcome labels from existing logs. It does not "
                "change CAMP scores, train weights, run DP, deploy a selector, "
                "or construct a Benders cut. Any proposed guard remains only a "
                "finite-candidate diagnostic unless later proven as fixed "
                "affine coefficients or an explicitly named lexicographic guard."
            ),
        },
        "source_counterfactual": source,
        "source_checks": source_checks,
        "record_checks": record_checks,
        "diagnostic_checks": diagnostic_checks,
        "diagnostic": diagnostic,
        "final_decision": _final_decision(passed, diagnostic),
    }


def _source_summary(counterfactual: dict[str, Any]) -> dict[str, Any]:
    decision = counterfactual.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "promotion_authorized": bool(decision.get("promotion_authorized")),
        "guarded_tiny_counterfactual_noninferior": bool(
            decision.get("guarded_tiny_counterfactual_noninferior")
        ),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_counterfactual_ready", source["status"], COUNTERFACTUAL_READY_STATUS),
        _check_equal("source_counterfactual_passed", source["passed"], True),
        _check_equal("source_promotion_not_authorized", source["promotion_authorized"], False),
        _check_equal(
            "source_guarded_counterfactual_not_noninferior",
            source["guarded_tiny_counterfactual_noninferior"],
            False,
        ),
        _check_equal("source_new_replay_not_authorized", source["new_replay_authorized"], False),
        _check_equal("source_training_not_authorized", source["camp_retraining_authorized"], False),
        _check_equal("source_formal_not_authorized", source["formal_seeds_authorized"], False),
        _check_equal("source_dp_modification_not_authorized", source["dp_modification_authorized"], False),
    ]


def _diagnostic_record(
    *,
    record: dict[str, Any],
    counterfactual_row: dict[str, Any] | None,
    selected_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    if counterfactual_row is None:
        return {"passed": False, "reason": "counterfactual_row_missing"}
    payload = record.get("external_context_payload_logging")
    if not isinstance(payload, dict):
        return {"passed": False, "reason": "payload_missing"}
    candidate_count = int(payload.get("candidate_count", record.get("num_candidates", 0)))
    selected = int(counterfactual_row["selected_index"])
    atom_best = int(counterfactual_row["atom_best_index"])
    guarded = int(counterfactual_row["guarded_atom_best_index"])
    top1 = 0
    comparison_indices = _unique_indices([top1, selected, atom_best, guarded])
    atom_scores = {
        str(spec.get("name")): _atom_coefficients(spec, payload, candidate_count)
        for spec in selected_specs
    }
    combined_atom_score = _combined_scores(atom_scores, candidate_count)
    outcomes = _outcomes(
        record.get("candidate_closed_loop_outcomes"),
        candidate_count,
        "candidate_closed_loop_outcomes",
    )
    planned_red, planned_red_source = _planned_red_values(record, candidate_count)
    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, default=True)
    components = _candidate_branch_components(outcomes, planned_red, feasible)
    candidate_rows = [
        _candidate_row(
            index,
            record=record,
            atom_scores=atom_scores,
            combined_atom_score=combined_atom_score,
            components=components,
            planned_red=planned_red,
            roles=_roles(index, top1=top1, selected=selected, atom_best=atom_best, guarded=guarded),
        )
        for index in comparison_indices
    ]
    selected_row = next(row for row in candidate_rows if row["index"] == selected)
    guarded_row = next(row for row in candidate_rows if row["index"] == guarded)
    deltas = _pair_deltas(guarded_row, selected_row)
    explainers = _fixed_descriptor_explainers(
        guarded_row=guarded_row,
        selected_row=selected_row,
    )
    return {
        "passed": True,
        "record_index": int(counterfactual_row["record_index"]),
        "selected_index": selected,
        "atom_best_index": atom_best,
        "guarded_atom_best_index": guarded,
        "planned_red_source": planned_red_source,
        "candidate_rows": candidate_rows,
        "guarded_minus_selected": deltas,
        "fixed_descriptor_explainers": explainers,
        "diagnosis": _diagnosis(deltas, explainers, guarded, selected),
    }


def _candidate_row(
    index: int,
    *,
    record: dict[str, Any],
    atom_scores: dict[str, list[float]],
    combined_atom_score: list[float],
    components: list[dict[str, Any]],
    planned_red: np.ndarray,
    roles: list[str],
) -> dict[str, Any]:
    outcome = record["candidate_closed_loop_outcomes"][index]
    row = {
        "index": index,
        "roles": roles,
        "feasible": bool(_bool_vector(record.get("feasible_mask"), len(components), default=True)[index]),
        "camp_score": _vector_value(record, "scores", index),
        "camp_selection_score": _vector_value(record, "selection_scores", index),
        "route_progress": _vector_value(record, "candidate_route_progress", index),
        "planned_red": float(planned_red[index]),
        "combined_external_context_atom_score": float(combined_atom_score[index]),
        "safety_cost_v1": float(components[index]["cost"]),
        "safety_cost_weighted_components": components[index]["weighted_components"],
        "outcome": {
            "progress_m": float(outcome["progress_m"]),
            "collision": bool(outcome["collision"]),
            "near_miss": bool(outcome["near_miss"]),
            "lane_violation": bool(outcome["lane_violation"]),
            "red_light_violation": bool(outcome["red_light_violation"]),
            "mean_jerk_mps3": float(outcome["mean_jerk_mps3"]),
            "mean_lateral_acceleration_mps2": float(outcome["mean_lateral_acceleration_mps2"]),
        },
        "dp_reward": _dp_reward_row(record, index),
        "perfect_tracker_rollout": _rollout_row(record, index),
        "external_context_atoms": {
            name: float(values[index]) for name, values in atom_scores.items()
        },
    }
    return row


def _pair_deltas(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "safety_cost_v1": candidate["safety_cost_v1"] - baseline["safety_cost_v1"],
        "route_progress": _delta(candidate["route_progress"], baseline["route_progress"]),
        "outcome_progress_m": candidate["outcome"]["progress_m"] - baseline["outcome"]["progress_m"],
        "planned_red": candidate["planned_red"] - baseline["planned_red"],
        "camp_score": _delta(candidate["camp_score"], baseline["camp_score"]),
        "camp_selection_score": _delta(
            candidate["camp_selection_score"],
            baseline["camp_selection_score"],
        ),
        "combined_external_context_atom_score": (
            candidate["combined_external_context_atom_score"]
            - baseline["combined_external_context_atom_score"]
        ),
        "dp_reward_total": _nested_delta(candidate, baseline, ("dp_reward", "total")),
        "dp_reward_progress": _nested_delta(candidate, baseline, ("dp_reward", "progress")),
        "dp_reward_red_light": _nested_delta(candidate, baseline, ("dp_reward", "red_light")),
        "h3_distance_m": _nested_delta(
            candidate,
            baseline,
            ("perfect_tracker_rollout", "3", "distance_m"),
        ),
        "h3_mean_vector_jerk_mps3": _nested_delta(
            candidate,
            baseline,
            ("perfect_tracker_rollout", "3", "mean_vector_jerk_mps3"),
        ),
        "h3_mean_lateral_acceleration_mps2": _nested_delta(
            candidate,
            baseline,
            ("perfect_tracker_rollout", "3", "mean_lateral_acceleration_mps2"),
        ),
    }


def _fixed_descriptor_explainers(
    *,
    guarded_row: dict[str, Any],
    selected_row: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = [
        ("camp_score_lower_is_better", guarded_row["camp_score"], selected_row["camp_score"], "lower"),
        (
            "camp_selection_score_lower_is_better",
            guarded_row["camp_selection_score"],
            selected_row["camp_selection_score"],
            "lower",
        ),
        ("planned_red_lower_is_better", guarded_row["planned_red"], selected_row["planned_red"], "lower"),
        (
            "h3_mean_vector_jerk_lower_is_better",
            _nested_get(guarded_row, ("perfect_tracker_rollout", "3", "mean_vector_jerk_mps3")),
            _nested_get(selected_row, ("perfect_tracker_rollout", "3", "mean_vector_jerk_mps3")),
            "lower",
        ),
        (
            "h3_mean_lateral_lower_is_better",
            _nested_get(guarded_row, ("perfect_tracker_rollout", "3", "mean_lateral_acceleration_mps2")),
            _nested_get(selected_row, ("perfect_tracker_rollout", "3", "mean_lateral_acceleration_mps2")),
            "lower",
        ),
        ("route_progress_higher_is_better", guarded_row["route_progress"], selected_row["route_progress"], "higher"),
        ("dp_reward_total_higher_is_better", _nested_get(guarded_row, ("dp_reward", "total")), _nested_get(selected_row, ("dp_reward", "total")), "higher"),
    ]
    explainers = []
    for name, guarded, selected, direction in candidates:
        if guarded is None or selected is None:
            continue
        guarded_value = float(guarded)
        selected_value = float(selected)
        selected_prefers = (
            selected_value < guarded_value if direction == "lower" else selected_value > guarded_value
        )
        explainers.append(
            {
                "name": name,
                "selected_prefers_logged_candidate": bool(selected_prefers),
                "selected_value": selected_value,
                "guarded_value": guarded_value,
                "delta_guarded_minus_selected": guarded_value - selected_value,
            }
        )
    return explainers


def _diagnosis(
    deltas: dict[str, Any],
    explainers: list[dict[str, Any]],
    guarded: int,
    selected: int,
) -> dict[str, Any]:
    safety_worse = float(deltas["safety_cost_v1"]) > 0.0
    current_tick_explainers = [
        item["name"] for item in explainers if item["selected_prefers_logged_candidate"]
    ]
    return {
        "status": (
            "guarded_switch_worsens_safety_cost"
            if safety_worse and guarded != selected
            else "guarded_switch_not_worse_or_no_switch"
        ),
        "guarded_switch_worsens_safety_cost": bool(safety_worse and guarded != selected),
        "fixed_descriptor_explainer_names": current_tick_explainers,
        "interpretation": (
            "At least one fixed current-tick descriptor favors the logged selected "
            "candidate over the guarded atom-best candidate."
            if current_tick_explainers
            else "No inspected fixed current-tick descriptor favors the logged selected candidate."
        ),
    }


def _diagnostic_checks(diagnostic: dict[str, Any] | None) -> list[dict[str, Any]]:
    if diagnostic is None:
        return [_check_equal("diagnostic_present", False, True)]
    return [
        _check_equal("diagnostic_present", True, True),
        _check_equal("diagnostic_passed", diagnostic.get("passed"), True),
        _check_equal(
            "diagnostic_identifies_guarded_failure_or_no_switch",
            diagnostic.get("diagnosis", {}).get("status") in {
                "guarded_switch_worsens_safety_cost",
                "guarded_switch_not_worse_or_no_switch",
            },
            True,
        ),
    ]


def _final_decision(passed: bool, diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    diagnosis = {} if diagnostic is None else diagnostic.get("diagnosis", {})
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": None,
        "closed_loop_replay_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "guarded_failure_status": diagnosis.get("status"),
        "fixed_descriptor_explainer_names": diagnosis.get("fixed_descriptor_explainer_names", []),
        "next_step": (
            "Use the diagnostic to decide whether a strictly stronger fixed "
            "current-tick guard is plausible; do not run broader experiments or "
            "deploy from this existing-log artifact."
            if passed
            else "Reject this diagnostic and inspect failed source or record checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    diagnostic = report.get("diagnostic") or {}
    diagnosis = diagnostic.get("diagnosis") or {}
    lines = [
        "# External Context Guarded Failure Diagnostic",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Guarded failure status: `{decision['guarded_failure_status']}`",
        f"- Fixed descriptor explainers: `{decision['fixed_descriptor_explainer_names']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        "",
        "## Diagnosis",
        "",
        diagnosis.get("interpretation", "No diagnostic available."),
        "",
    ]
    if diagnostic.get("passed"):
        lines.extend(
            [
                "## Guarded Minus Selected",
                "",
                "```json",
                json.dumps(diagnostic["guarded_minus_selected"], indent=2, sort_keys=True),
                "```",
                "",
                "## Candidate Rows",
                "",
            ]
        )
        for row in diagnostic["candidate_rows"]:
            lines.append(
                f"- candidate `{row['index']}` roles=`{row['roles']}` "
                f"safety_cost=`{row['safety_cost_v1']}` "
                f"route_progress=`{row['route_progress']}` "
                f"atom_score=`{row['combined_external_context_atom_score']}`"
            )
        lines.extend(["", "## Fixed Descriptor Explainers", ""])
        for item in diagnostic["fixed_descriptor_explainers"]:
            lines.append(
                f"- `{item['name']}`: selected_prefers="
                f"`{item['selected_prefers_logged_candidate']}`, "
                f"selected=`{item['selected_value']}`, guarded=`{item['guarded_value']}`"
            )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_records(root: Path) -> list[dict[str, Any]]:
    paths = iter_selection_log_paths([root])
    if not paths:
        raise FileNotFoundError(f"No {LOG_NAME} found under {root}")
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        records.extend(row for row in payload if isinstance(row, dict))
    return records


def _counterfactual_row(counterfactual: dict[str, Any], record_index: int) -> dict[str, Any] | None:
    for row in counterfactual.get("counterfactual_rows") or []:
        if isinstance(row, dict) and int(row.get("record_index", -1)) == record_index:
            return row
    return None


def _dp_reward_row(record: dict[str, Any], index: int) -> dict[str, Any] | None:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or index >= len(rewards) or not isinstance(rewards[index], dict):
        return None
    return {
        key: value
        for key, value in rewards[index].items()
        if isinstance(value, (int, float, bool)) or value is None
    }


def _rollout_row(record: dict[str, Any], index: int) -> dict[str, Any]:
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict):
        return {}
    result: dict[str, Any] = {}
    for horizon, metrics in rollout.items():
        if not isinstance(metrics, dict):
            continue
        result[str(horizon)] = {
            name: _metric_at(values, index)
            for name, values in metrics.items()
            if isinstance(values, list)
        }
    return result


def _metric_at(values: list[Any], index: int) -> float | None:
    if index >= len(values) or values[index] is None:
        return None
    return float(values[index])


def _vector_value(record: dict[str, Any], key: str, index: int) -> float | None:
    values = record.get(key)
    if not isinstance(values, list) or index >= len(values) or values[index] is None:
        return None
    return float(values[index])


def _bool_vector(values: Any, size: int, *, default: bool) -> np.ndarray:
    if not isinstance(values, list):
        return np.full(size, default, dtype=bool)
    array = np.asarray(values, dtype=bool).reshape(-1)
    if array.shape != (size,):
        return np.full(size, default, dtype=bool)
    return array


def _roles(index: int, *, top1: int, selected: int, atom_best: int, guarded: int) -> list[str]:
    roles = []
    if index == top1:
        roles.append("top1")
    if index == selected:
        roles.append("selected")
    if index == atom_best:
        roles.append("atom_best")
    if index == guarded:
        roles.append("guarded_atom_best")
    return roles


def _unique_indices(values: list[int]) -> list[int]:
    return sorted(set(int(value) for value in values))


def _delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return float(candidate) - float(baseline)


def _nested_delta(candidate: dict[str, Any], baseline: dict[str, Any], path: tuple[str, ...]) -> float | None:
    return _delta(_nested_get(candidate, path), _nested_get(baseline, path))


def _nested_get(row: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = row
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
