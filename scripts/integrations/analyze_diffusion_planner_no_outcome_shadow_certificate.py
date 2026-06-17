#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
    parse_selection_log_metadata,
)


TOL = 1e-12
ABSOLUTE_LATERAL_GUARD_MPS2 = 2.0


SCREENS: tuple[dict[str, Any], ...] = (
    {
        "name": "route_h10_score0",
        "description": (
            "route-progress nonworse, H10 lower-bound not more than 0.15 m "
            "ahead of candidate0, and original CAMP affine score nonworse"
        ),
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.15},
            {"field": "score_delta", "max": 0.0},
        ),
    },
    {
        "name": "route_h10_clearance_nonworse",
        "description": (
            "route_h10_score0 plus soft and near-miss clearance hinge costs "
            "nonworse than candidate0"
        ),
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.15},
            {"field": "score_delta", "max": 0.0},
            {"field": "soft_clearance_cost_delta", "max": 0.0},
            {"field": "near_miss_clearance_cost_delta", "max": 0.0},
        ),
    },
    {
        "name": "route_h10_clearance_zero",
        "description": (
            "route_h10_score0 plus absolute zero soft and near-miss clearance "
            "hinge costs"
        ),
        "filters": (
            {"field": "route_progress_loss", "max": 0.0},
            {"field": "h10_distance_loss", "min": -0.15},
            {"field": "score_delta", "max": 0.0},
            {"field": "soft_clearance_cost", "max": 0.0},
            {"field": "near_miss_clearance_cost", "max": 0.0},
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "No-outcome shadow audit for finite-candidate route/H10/clearance "
            "guards. This reads only current-tick candidate descriptors and "
            "rejects logs containing candidate closed-loop outcomes."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_examples", type=int, default=20)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
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
    label: str | None = None,
    max_examples: int = 20,
) -> dict[str, Any]:
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        context = _log_context(log_path)
        for record_index, raw_record in enumerate(payload):
            records.append(_load_record(raw_record, log_path, record_index, context))

    events = [_event(record, screen) for screen in SCREENS for record in records]
    by_screen = {
        screen["name"]: [event for event in events if event["screen"] == screen["name"]]
        for screen in SCREENS
    }
    return {
        "analysis": {
            "name": "dp_camp_no_outcome_shadow_certificate_v1",
            "label": label,
            "role": (
                "default-off offline readiness audit for finite-candidate "
                "route-progress, H10 lower-bound, and clearance hinge guards"
            ),
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
            "screens": [
                {
                    "name": screen["name"],
                    "description": screen["description"],
                    "filters": list(screen["filters"]),
                }
                for screen in SCREENS
            ],
            "math_boundary": (
                "All audited quantities are fixed current-tick constants over "
                "a finite DP candidate set: feasibility, affine CAMP scores, "
                "route-progress, H10 open-loop distance, and v2 clearance hinge "
                "costs. Candidate outcomes are forbidden by this audit. If "
                "later atomized as nonnegative costs, CAMP scoring remains "
                "affine in master weights and the simplex/CVaR/L2 master stays "
                "convex. This is not a classical Benders subproblem/cut audit."
            ),
        },
        "records": _record_summary(records, len(log_paths)),
        "descriptor_coverage": _descriptor_coverage(records),
        "latency_ms": _latency_summary(records),
        "screens": [_screen_report(name, rows, max_examples) for name, rows in by_screen.items()],
    }


def _log_context(log_path: Path) -> dict[str, Any]:
    metadata = parse_selection_log_metadata(log_path)
    validation = _read_json_if_exists(log_path.with_name("camp_validation_summary.json"))
    benchmark = validation.get("benchmark", {})
    if not isinstance(benchmark, dict):
        benchmark = {}
    route = benchmark.get("route")
    return {
        "log_path": str(log_path),
        "route": route,
        "route_name": Path(str(route)).stem if route is not None else metadata.route,
        "seed": benchmark.get("seed", metadata.seed),
        "max_npcs": benchmark.get("max_npcs", metadata.npc_count),
        "traffic_lights": benchmark.get(
            "traffic_lights",
            metadata.traffic_light == "on",
        ),
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_record(
    raw_record: dict[str, Any],
    log_path: Path,
    record_index: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    label = f"{log_path} record {record_index}"
    outcomes = raw_record.get("candidate_closed_loop_outcomes")
    if outcomes is not None:
        raise ValueError(
            f"{label} contains candidate_closed_loop_outcomes; this is a no-outcome audit."
        )
    candidate_count = int(raw_record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(raw_record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    atom_names = tuple(raw_record.get("atom_names") or ())
    atoms = _matrix(raw_record.get("atoms"), candidate_count, len(atom_names), f"{label} atoms")
    return {
        "context": context,
        "record_index": int(record_index),
        "selection_step": int(raw_record.get("selection_step", record_index)),
        "candidate_count": candidate_count,
        "selected_index": selected_index,
        "used_fallback": bool(raw_record.get("used_fallback", False)),
        "feasible": _bool_vector(
            raw_record.get("feasible_mask"),
            candidate_count,
            f"{label} feasible_mask",
        ),
        "scores": _score_vector(
            raw_record.get("selection_scores", raw_record.get("scores")),
            candidate_count,
            f"{label} selection_scores",
        ),
        "progress_shortfall": _atom_vector(
            atoms,
            atom_names,
            "progress_shortfall",
            label,
        ),
        "union_red": _vector(
            raw_record.get("candidate_horizon_union_planned_red_light_cost"),
            candidate_count,
            f"{label} candidate_horizon_union_planned_red_light_cost",
        ),
        "red_stopping": _vector(
            raw_record.get("candidate_red_stopping_margin_cost"),
            candidate_count,
            f"{label} candidate_red_stopping_margin_cost",
        ),
        "proxy_jerk": _vector(
            raw_record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
        "proxy_lateral": _vector(
            raw_record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "route_progress": _optional_vector(
            raw_record.get("candidate_route_progress"),
            candidate_count,
            f"{label} candidate_route_progress",
        ),
        "h10_distance": _h10_distance(raw_record, candidate_count, label),
        "clearance": _clearance(raw_record, candidate_count, label),
        "latencies": {
            "shadow_obstacle_clearance": raw_record.get(
                "latency_ms_shadow_obstacle_clearance"
            ),
            "shadow_perfect_tracker_open_loop": raw_record.get(
                "latency_ms_shadow_perfect_tracker_open_loop"
            ),
            "camp_selection": raw_record.get("latency_ms_camp_selection"),
            "including_candidate_generation": raw_record.get(
                "latency_ms_including_candidate_generation"
            ),
        },
    }


def _matrix(values: Any, rows: int, cols: int, label: str) -> np.ndarray:
    if cols <= 0:
        raise ValueError(f"{label} requires atom_names.")
    arr = np.asarray(values, dtype=np.float64)
    if arr.shape != (rows, cols) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must have shape {(rows, cols)} and finite values.")
    return arr


def _atom_vector(
    atoms: np.ndarray,
    atom_names: tuple[str, ...],
    name: str,
    label: str,
) -> np.ndarray:
    try:
        index = atom_names.index(name)
    except ValueError as exc:
        raise ValueError(f"{label} is missing atom {name!r}.") from exc
    return atoms[:, index].astype(np.float64)


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.shape != (size,) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must be a finite vector of length {size}.")
    return arr


def _optional_vector(values: Any, size: int, label: str) -> np.ndarray | None:
    if values is None:
        return None
    return _vector(values, size, label)


def _score_vector(values: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.shape != (size,):
        raise ValueError(f"{label} must be a vector of length {size}.")
    finite = np.isfinite(arr)
    arr = arr.astype(np.float64)
    arr[~finite] = np.inf
    return arr


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(values, dtype=bool)
    if arr.shape != (size,):
        raise ValueError(f"{label} must be a boolean vector of length {size}.")
    return arr


def _h10_distance(
    raw_record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> np.ndarray | None:
    rollout = raw_record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict):
        return None
    payload = rollout.get("10", rollout.get(10))
    if not isinstance(payload, dict):
        return None
    return _optional_vector(
        payload.get("distance_m"),
        candidate_count,
        f"{label} H10 distance_m",
    )


def _clearance(
    raw_record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any] | None:
    payload = raw_record.get("candidate_obstacle_clearance")
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != "candidate_current_tick_obstacle_clearance_v2":
        return None
    return {
        "schema_version": payload.get("schema_version"),
        "soft_cost": _vector(
            payload.get("soft_clearance_violation_cost"),
            candidate_count,
            f"{label} soft_clearance_violation_cost",
        ),
        "near_cost": _vector(
            payload.get("near_miss_violation_cost"),
            candidate_count,
            f"{label} near_miss_violation_cost",
        ),
        "min_lower_bound": _optional_vector(
            payload.get("min_obstacle_clearance_lower_bound_m"),
            candidate_count,
            f"{label} min_obstacle_clearance_lower_bound_m",
        ),
        "exact_pairs": _optional_vector(
            payload.get("exact_evaluated_pairs"),
            candidate_count,
            f"{label} exact_evaluated_pairs",
        ),
    }


def _event(record: dict[str, Any], screen: dict[str, Any]) -> dict[str, Any]:
    available, missing = _required_available(record, screen)
    if not record["feasible"].any():
        stage = "fallback_retain_logged"
        mask = np.zeros(record["candidate_count"], dtype=bool)
    elif not bool(record["feasible"][0]):
        stage = "candidate0_infeasible_retain_logged"
        mask = np.zeros(record["candidate_count"], dtype=bool)
    elif not available:
        stage = "descriptor_missing_retain_candidate0"
        mask = np.zeros(record["candidate_count"], dtype=bool)
    else:
        mask = _candidate_mask(record, screen)
        stage = "shadow_candidate" if mask.any() else "candidate0_retain_empty_mask"
    selected = _select_candidate(record, mask) if mask.any() else 0
    return {
        "screen": screen["name"],
        "context": record["context"],
        "selection_step": record["selection_step"],
        "record_index": record["record_index"],
        "stage": stage,
        "descriptor_available": bool(available),
        "missing_descriptors": missing,
        "candidate0_feasible": bool(record["feasible"].any() and record["feasible"][0]),
        "logged_selected": int(record["selected_index"]),
        "shadow_selected": int(selected),
        "shadow_changes_candidate0": bool(selected != 0),
        "shadow_differs_from_logged": bool(selected != int(record["selected_index"])),
        "admissible_candidates": int(mask.sum()),
        "selected_candidate": _candidate_payload(record, selected),
        "logged_candidate": _candidate_payload(record, int(record["selected_index"])),
    }


def _required_available(
    record: dict[str, Any],
    screen: dict[str, Any],
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for filter_spec in screen["filters"]:
        field = str(filter_spec["field"])
        if _feature_values(record, field) is None:
            missing.append(field)
    return not missing, missing


def _candidate_mask(record: dict[str, Any], screen: dict[str, Any]) -> np.ndarray:
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
    progress_delta = _feature_values(record, "progress_delta")
    if progress_delta is None:
        raise ValueError("progress_delta must be available.")
    mask &= progress_delta >= -2.0 - TOL
    mask &= progress_delta <= 0.05 + TOL
    for filter_spec in screen["filters"]:
        values = _feature_values(record, str(filter_spec["field"]))
        if values is None:
            return np.zeros(record["candidate_count"], dtype=bool)
        if "max" in filter_spec:
            mask &= values <= float(filter_spec["max"]) + TOL
        if "min" in filter_spec:
            mask &= values >= float(filter_spec["min"]) - TOL
    return mask


def _feature_values(record: dict[str, Any], field: str) -> np.ndarray | None:
    if field == "progress_delta":
        return record["progress_shortfall"] - record["progress_shortfall"][0]
    if field == "score_delta":
        return record["scores"] - record["scores"][0]
    if field == "route_progress_loss":
        route_progress = record["route_progress"]
        return None if route_progress is None else route_progress[0] - route_progress
    if field == "h10_distance_loss":
        h10 = record["h10_distance"]
        return None if h10 is None else h10[0] - h10
    clearance = record["clearance"]
    if field == "soft_clearance_cost":
        return None if clearance is None else clearance["soft_cost"]
    if field == "near_miss_clearance_cost":
        return None if clearance is None else clearance["near_cost"]
    if field == "soft_clearance_cost_delta":
        return None if clearance is None else clearance["soft_cost"] - clearance["soft_cost"][0]
    if field == "near_miss_clearance_cost_delta":
        return None if clearance is None else clearance["near_cost"] - clearance["near_cost"][0]
    raise ValueError(f"Unsupported feature field: {field}")


def _select_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return 0
    soft = _feature_values(record, "soft_clearance_cost")
    near = _feature_values(record, "near_miss_clearance_cost")
    h10_loss = _feature_values(record, "h10_distance_loss")
    progress_delta = _feature_values(record, "progress_delta")
    if soft is None:
        soft = np.zeros(record["candidate_count"], dtype=np.float64)
    if near is None:
        near = np.zeros(record["candidate_count"], dtype=np.float64)
    if h10_loss is None:
        h10_loss = np.zeros(record["candidate_count"], dtype=np.float64)
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
            soft[indices],
            near[indices],
            record["red_stopping"][indices],
            record["union_red"][indices],
        )
    )
    return int(indices[order[0]])


def _candidate_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    payload = {
        "candidate_index": int(index),
        "score_delta": _scalar_feature(record, "score_delta", index),
        "progress_delta": _scalar_feature(record, "progress_delta", index),
        "route_progress_loss": _scalar_feature(record, "route_progress_loss", index),
        "h10_distance_loss": _scalar_feature(record, "h10_distance_loss", index),
        "soft_clearance_cost": _scalar_feature(record, "soft_clearance_cost", index),
        "near_miss_clearance_cost": _scalar_feature(
            record,
            "near_miss_clearance_cost",
            index,
        ),
        "soft_clearance_cost_delta": _scalar_feature(
            record,
            "soft_clearance_cost_delta",
            index,
        ),
        "near_miss_clearance_cost_delta": _scalar_feature(
            record,
            "near_miss_clearance_cost_delta",
            index,
        ),
        "union_red_delta": float(record["union_red"][index] - record["union_red"][0]),
        "red_stopping_delta": float(
            record["red_stopping"][index] - record["red_stopping"][0]
        ),
        "proxy_jerk_delta": float(record["proxy_jerk"][index] - record["proxy_jerk"][0]),
        "proxy_lateral_delta": float(
            record["proxy_lateral"][index] - record["proxy_lateral"][0]
        ),
    }
    return payload


def _scalar_feature(record: dict[str, Any], field: str, index: int) -> float | None:
    values = _feature_values(record, field)
    return None if values is None else float(values[index])


def _record_summary(records: list[dict[str, Any]], logs: int) -> dict[str, Any]:
    return {
        "logs": int(logs),
        "total": len(records),
        "nonfallback": sum(int(record["feasible"].any()) for record in records),
        "fallback": sum(int(not record["feasible"].any()) for record in records),
        "candidate0_feasible": sum(
            int(record["feasible"].any() and bool(record["feasible"][0]))
            for record in records
        ),
        "logged_nonzero": sum(int(record["selected_index"] != 0) for record in records),
        "closed_loop_outcome_records": 0,
    }


def _descriptor_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_route_progress_records": sum(
            int(record["route_progress"] is not None) for record in records
        ),
        "h10_distance_records": sum(
            int(record["h10_distance"] is not None) for record in records
        ),
        "obstacle_clearance_v2_records": sum(
            int(record["clearance"] is not None) for record in records
        ),
        "all_required_records": sum(
            int(
                record["route_progress"] is not None
                and record["h10_distance"] is not None
                and record["clearance"] is not None
            )
            for record in records
        ),
    }


def _latency_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "shadow_obstacle_clearance",
        "shadow_perfect_tracker_open_loop",
        "camp_selection",
        "including_candidate_generation",
    )
    return {
        field: _summary(
            [
                float(record["latencies"][field])
                for record in records
                if record["latencies"].get(field) is not None
            ]
        )
        for field in fields
    }


def _screen_report(
    name: str,
    rows: list[dict[str, Any]],
    max_examples: int,
) -> dict[str, Any]:
    candidate0 = [row for row in rows if row["candidate0_feasible"]]
    available = [row for row in candidate0 if row["descriptor_available"]]
    changed = [row for row in available if row["shadow_changes_candidate0"]]
    different = [row for row in available if row["shadow_differs_from_logged"]]
    return {
        "name": name,
        "stage_counts": _counter(row["stage"] for row in rows),
        "records": {
            "candidate0_feasible": len(candidate0),
            "descriptor_available": len(available),
            "opportunity": sum(int(row["admissible_candidates"] > 0) for row in available),
            "shadow_changes_candidate0": len(changed),
            "shadow_differs_from_logged": len(different),
        },
        "selected_delta_summary": _candidate_collection_summary(changed),
        "logged_delta_summary": _candidate_collection_summary(
            [row for row in available if row["logged_selected"] != 0],
            key="logged_candidate",
        ),
        "missing_descriptor_counts": _counter(
            missing for row in candidate0 for missing in row["missing_descriptors"]
        ),
        "examples": {
            "shadow_change": _examples(changed, max_examples=max_examples),
            "descriptor_missing": _examples(
                [row for row in candidate0 if row["missing_descriptors"]],
                max_examples=max_examples,
            ),
        },
    }


def _candidate_collection_summary(
    rows: list[dict[str, Any]],
    *,
    key: str = "selected_candidate",
) -> dict[str, Any]:
    fields = (
        "score_delta",
        "progress_delta",
        "route_progress_loss",
        "h10_distance_loss",
        "soft_clearance_cost",
        "near_miss_clearance_cost",
        "soft_clearance_cost_delta",
        "near_miss_clearance_cost_delta",
        "proxy_jerk_delta",
        "proxy_lateral_delta",
    )
    return {
        field: _summary(
            [
                float(row[key][field])
                for row in rows
                if row[key].get(field) is not None
            ]
        )
        for field in fields
    }


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _examples(rows: list[dict[str, Any]], *, max_examples: int) -> list[dict[str, Any]]:
    examples = []
    for row in rows[:max_examples]:
        examples.append(
            {
                "context": row["context"],
                "selection_step": row["selection_step"],
                "record_index": row["record_index"],
                "stage": row["stage"],
                "logged_selected": row["logged_selected"],
                "shadow_selected": row["shadow_selected"],
                "admissible_candidates": row["admissible_candidates"],
                "selected_candidate": row["selected_candidate"],
                "logged_candidate": row["logged_candidate"],
                "missing_descriptors": row["missing_descriptors"],
            }
        )
    return examples


def _counter(values) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# No-Outcome Shadow Certificate Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Descriptor Coverage",
            "",
            "| Field | Records |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["descriptor_coverage"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Screens", ""])
    for screen in report["screens"]:
        records = screen["records"]
        lines.extend(
            [
                f"### `{screen['name']}`",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
            ]
        )
        for key, value in records.items():
            lines.append(f"| `{key}` | `{value}` |")
        lines.append("")
        lines.append("Stage counts:")
        lines.append("")
        lines.append("| Stage | Records |")
        lines.append("| --- | ---: |")
        for key, value in screen["stage_counts"].items():
            lines.append(f"| `{key}` | `{value}` |")
        lines.append("")
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            str(report["analysis"]["math_boundary"]),
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
