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
from scripts.integrations.analyze_diffusion_planner_first_step_graft_potential import (  # noqa: E402
    TOL,
    _fmt,
    _mean_third_difference_norm,
    _summary,
)
from scripts.integrations.analyze_diffusion_planner_outcome_free_bounded_selector import (  # noqa: E402
    BOOL_OUTCOMES,
    OUTCOME_DELTA_FIELDS,
    SCREENS,
    _admissible_mask,
    _choose,
    _load_record,
    _outcome_number,
    _result_row,
)


DEFAULT_SCREENS = (
    "balanced_lateral_jerk_nondegrading",
    "relaxed_lateral_jerk_nondegrading",
)
GUARD_SETS = (
    {
        "name": "prefix_tracker_jerk_nonworse",
        "features": (
            "prefix_jerk_proxy",
            "tracker_command_jerk_mps3",
        ),
    },
    {
        "name": "prefix_rollout_h3_jerk_nonworse",
        "features": (
            "prefix_jerk_proxy",
            "rollout_h3_mean_vector_jerk_mps3",
        ),
    },
    {
        "name": "tracker_rollout_h3_jerk_nonworse",
        "features": (
            "tracker_command_jerk_mps3",
            "rollout_h3_mean_vector_jerk_mps3",
        ),
    },
    {
        "name": "h3_distance_tracker_jerk_nonworse",
        "features": (
            "rollout_h3_distance_m",
            "tracker_command_jerk_mps3",
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "For changed records where an outcome-free selector picked a "
            "posterior joint-comfort failure, audit whether another admissible "
            "candidate existed that passed current-tick jerk guards and was "
            "posterior joint-comfort successful."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--screen", action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        screen_names=tuple(args.screen) or DEFAULT_SCREENS,
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
    screen_names: tuple[str, ...] = DEFAULT_SCREENS,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    screens = _selected_screens(screen_names)
    rows_by_screen = {screen["name"]: [] for screen in screens}
    totals = {
        "logs": len(log_paths),
        "total": 0,
        "nonfallback": 0,
        "fallback": 0,
    }
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            totals["total"] += 1
            label_text = f"{log_path} record {record_index}"
            record = _load_record(raw_record, label_text)
            fallback = not record["feasible"].any()
            totals["fallback"] += int(fallback)
            totals["nonfallback"] += int(not fallback)
            if fallback:
                continue
            features = _current_tick_feature_values(
                raw_record,
                int(raw_record["num_candidates"]),
                label_text,
            )
            for screen in screens:
                admissible = _admissible_mask(record, screen)
                if not admissible.any():
                    continue
                chosen = _choose(record, admissible)
                result = _result_row(record, chosen, opportunity=True, fallback=False)
                if not result["changed"] or bool(result["posterior_joint_comfort_improvement"]):
                    continue
                rows_by_screen[screen["name"]].append(
                    _failure_row(
                        record,
                        chosen,
                        admissible,
                        features,
                        log_path=log_path,
                        record_index=record_index,
                    )
                )
    return {
        "analysis": {
            "name": "dp_camp_outcome_free_alternative_candidates_v1",
            "role": (
                "offline tie-break-vs-candidate-generation attribution for "
                "outcome-free finite-candidate selector failures"
            ),
            "label": label,
            "screens": [screen["name"] for screen in screens],
            "guard_sets": [
                {"name": guard["name"], "features": list(guard["features"])}
                for guard in GUARD_SETS
            ],
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "outcomes classify posterior successful alternatives only; "
                "selection and guard predicates use current-tick finite "
                "candidate diagnostics"
            ),
            "convexity_boundary": (
                "All guard quantities are fixed finite-candidate constants at "
                "the current tick. If later atomized as candidate costs, CAMP "
                "scoring remains affine in w. This audit is not Benders and "
                "does not claim trajectory-coordinate convexity."
            ),
        },
        "records": totals,
        "screens": [_screen_report(name, rows) for name, rows in rows_by_screen.items()],
    }


def _selected_screens(screen_names: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    by_name = {screen["name"]: screen for screen in SCREENS}
    missing = [name for name in screen_names if name not in by_name]
    if missing:
        raise ValueError(f"Unknown screen(s): {', '.join(missing)}")
    return tuple(by_name[name] for name in screen_names)


def _current_tick_feature_values(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    features: dict[str, np.ndarray] = {}
    _add_vector(
        features,
        "tracker_command_jerk_mps3",
        record.get("candidate_perfect_tracker_jerk_magnitude_mps3"),
        candidate_count,
        f"{label} candidate_perfect_tracker_jerk_magnitude_mps3",
    )
    prefix = np.asarray(
        record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        dtype=np.float64,
    )
    if prefix.ndim == 3 and prefix.shape[0] == candidate_count and prefix.shape[2] >= 2:
        prefix_xy = prefix[:, :, :2]
        if np.all(np.isfinite(prefix_xy)):
            features["prefix_jerk_proxy"] = np.asarray(
                [_mean_third_difference_norm(prefix_xy[idx]) for idx in range(candidate_count)],
                dtype=np.float64,
            )
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if isinstance(rollout, dict):
        h3 = rollout.get("3", rollout.get(3))
        if isinstance(h3, dict):
            _add_vector(
                features,
                "rollout_h3_mean_vector_jerk_mps3",
                h3.get("mean_vector_jerk_mps3"),
                candidate_count,
                f"{label} H3 mean_vector_jerk_mps3",
            )
            _add_vector(
                features,
                "rollout_h3_distance_m",
                h3.get("distance_m"),
                candidate_count,
                f"{label} H3 distance_m",
            )
    return features


def _add_vector(
    features: dict[str, np.ndarray],
    key: str,
    values: Any,
    size: int,
    label: str,
) -> None:
    if values is None:
        return
    features[key] = _vector(values, size, label)


def _failure_row(
    record: dict[str, Any],
    chosen: int,
    admissible: np.ndarray,
    features: dict[str, np.ndarray],
    *,
    log_path: Path,
    record_index: int,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    posterior_success = _posterior_success_mask(record)
    admissible_indices = np.flatnonzero(admissible)
    success_indices = np.flatnonzero(admissible & posterior_success)
    chosen_rank = _rank_in_current_selector(record, admissible_indices, chosen)
    success_rank = (
        min(_rank_in_current_selector(record, admissible_indices, int(idx)) for idx in success_indices)
        if success_indices.size
        else None
    )
    guard_reports = [
        _guard_set_report(
            guard,
            record,
            admissible,
            posterior_success,
            features,
            selected=selected,
            admissible_indices=admissible_indices,
        )
        for guard in GUARD_SETS
    ]
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selected_index": selected,
        "chosen_index": int(chosen),
        "admissible_count": int(admissible.sum()),
        "admissible_success_count": int(success_indices.size),
        "chosen_rank": int(chosen_rank),
        "best_success_rank": None if success_rank is None else int(success_rank),
        "chosen_outcome_delta": _outcome_delta(record, chosen),
        "best_success_outcome_delta": (
            None
            if success_indices.size == 0
            else _outcome_delta(record, _best_success_candidate(record, success_indices))
        ),
        "guard_sets": guard_reports,
    }


def _posterior_success_mask(record: dict[str, Any]) -> np.ndarray:
    selected = int(record["selected_index"])
    count = record["feasible"].size
    mask = record["feasible"].copy()
    mask[selected] = False
    for field in BOOL_OUTCOMES:
        selected_value = bool(record["outcomes"][selected].get(field))
        mask &= np.asarray(
            [
                float(bool(record["outcomes"][idx].get(field))) <= float(selected_value)
                for idx in range(count)
            ],
            dtype=bool,
        )
    jerk = np.asarray(
        [_outcome_number(record, idx, "mean_jerk_mps3") for idx in range(count)],
        dtype=np.float64,
    )
    lateral = np.asarray(
        [
            _outcome_number(record, idx, "mean_lateral_acceleration_mps2")
            for idx in range(count)
        ],
        dtype=np.float64,
    )
    return mask & (jerk < jerk[selected] - TOL) & (lateral < lateral[selected] - TOL)


def _guard_set_report(
    guard: dict[str, Any],
    record: dict[str, Any],
    admissible: np.ndarray,
    posterior_success: np.ndarray,
    features: dict[str, np.ndarray],
    *,
    selected: int,
    admissible_indices: np.ndarray,
) -> dict[str, Any]:
    required = tuple(str(feature) for feature in guard["features"])
    guard_mask = admissible.copy()
    missing = [feature for feature in required if feature not in features]
    if missing:
        guard_mask &= False
    else:
        for feature in required:
            values = features[feature]
            if feature.endswith("distance_m"):
                guard_mask &= values >= values[selected] - TOL
            else:
                guard_mask &= values <= values[selected] + TOL
    guarded_indices = np.flatnonzero(guard_mask)
    guarded_success_indices = np.flatnonzero(guard_mask & posterior_success)
    best_guarded_success = (
        None
        if guarded_success_indices.size == 0
        else _best_success_candidate(record, guarded_success_indices)
    )
    best_rank = (
        None
        if best_guarded_success is None
        else _rank_in_current_selector(record, admissible_indices, int(best_guarded_success))
    )
    return {
        "name": str(guard["name"]),
        "missing_features": missing,
        "guarded_admissible_count": int(guarded_indices.size),
        "guarded_success_count": int(guarded_success_indices.size),
        "has_guarded_success": bool(guarded_success_indices.size),
        "best_guarded_success_index": (
            None if best_guarded_success is None else int(best_guarded_success)
        ),
        "best_guarded_success_rank": None if best_rank is None else int(best_rank),
        "best_guarded_success_outcome_delta": (
            None if best_guarded_success is None else _outcome_delta(record, best_guarded_success)
        ),
    }


def _rank_in_current_selector(record: dict[str, Any], indices: np.ndarray, candidate: int) -> int:
    order = _selector_order(record, indices)
    positions = np.flatnonzero(order == int(candidate))
    if positions.size != 1:
        raise ValueError("Candidate is not present exactly once in selector order.")
    return int(positions[0])


def _selector_order(record: dict[str, Any], indices: np.ndarray) -> np.ndarray:
    selected = record["selected_index"]
    progress_loss = np.maximum(0.0, record["progress_proxy"][selected] - record["progress_proxy"])
    target_loss = np.maximum(0.0, record["target_speed"][selected] - record["target_speed"])
    h10_loss = np.maximum(0.0, record["h10_displacement"][selected] - record["h10_displacement"])
    order = np.lexsort(
        (
            indices,
            record["selection_scores"][indices],
            h10_loss[indices],
            target_loss[indices],
            progress_loss[indices],
            record["raw_jerk"][indices],
            record["raw_lateral"][indices],
        )
    )
    return indices[order]


def _best_success_candidate(record: dict[str, Any], indices: np.ndarray) -> int:
    progress = np.asarray(
        [_outcome_number(record, int(idx), "progress_m") for idx in indices],
        dtype=np.float64,
    )
    jerk = np.asarray(
        [_outcome_number(record, int(idx), "mean_jerk_mps3") for idx in indices],
        dtype=np.float64,
    )
    lateral = np.asarray(
        [
            _outcome_number(record, int(idx), "mean_lateral_acceleration_mps2")
            for idx in indices
        ],
        dtype=np.float64,
    )
    order = np.lexsort((indices, lateral, jerk, -progress))
    return int(indices[order[0]])


def _outcome_delta(record: dict[str, Any], candidate: int) -> dict[str, float]:
    selected = int(record["selected_index"])
    return {
        field: _outcome_number(record, int(candidate), field)
        - _outcome_number(record, selected, field)
        for field in OUTCOME_DELTA_FIELDS
    }


def _screen_report(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "failure_records": len(rows),
        "with_any_admissible_posterior_success": sum(
            int(row["admissible_success_count"] > 0) for row in rows
        ),
        "guard_sets": [_guard_summary(str(guard["name"]), rows) for guard in GUARD_SETS],
        "candidate_counts": {
            "admissible": _summary([float(row["admissible_count"]) for row in rows]),
            "admissible_success": _summary(
                [float(row["admissible_success_count"]) for row in rows]
            ),
        },
        "rank_summary": {
            "chosen_rank": _summary([float(row["chosen_rank"]) for row in rows]),
            "best_success_rank": _summary(
                [
                    float(row["best_success_rank"])
                    for row in rows
                    if row["best_success_rank"] is not None
                ]
            ),
        },
        "chosen_outcome_delta_summary": _delta_summary(
            [row["chosen_outcome_delta"] for row in rows]
        ),
        "best_success_outcome_delta_summary": _delta_summary(
            [
                row["best_success_outcome_delta"]
                for row in rows
                if row["best_success_outcome_delta"] is not None
            ]
        ),
        "examples": _examples(rows),
    }


def _guard_summary(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    guard_rows = [guard for row in rows for guard in row["guard_sets"] if guard["name"] == name]
    with_guarded_success = [
        guard for guard in guard_rows if bool(guard["has_guarded_success"])
    ]
    return {
        "name": name,
        "failure_records": len(rows),
        "with_guarded_success": len(with_guarded_success),
        "guarded_success_rate": len(with_guarded_success) / max(len(rows), 1),
        "guarded_admissible_count": _summary(
            [float(guard["guarded_admissible_count"]) for guard in guard_rows]
        ),
        "guarded_success_count": _summary(
            [float(guard["guarded_success_count"]) for guard in guard_rows]
        ),
        "best_guarded_success_rank": _summary(
            [
                float(guard["best_guarded_success_rank"])
                for guard in guard_rows
                if guard["best_guarded_success_rank"] is not None
            ]
        ),
        "best_guarded_success_outcome_delta_summary": _delta_summary(
            [
                guard["best_guarded_success_outcome_delta"]
                for guard in guard_rows
                if guard["best_guarded_success_outcome_delta"] is not None
            ]
        ),
    }


def _delta_summary(rows: list[dict[str, float] | None]) -> dict[str, dict[str, float | int | None]]:
    clean = [row for row in rows if row is not None]
    return {
        field: _summary([float(row[field]) for row in clean])
        for field in OUTCOME_DELTA_FIELDS
    }


def _examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            -int(row["admissible_success_count"] > 0),
            -max(
                int(guard["has_guarded_success"]) for guard in row["guard_sets"]
            ),
            float(row["chosen_outcome_delta"]["mean_jerk_mps3"]),
        ),
    )
    return ordered[:10]


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    return array


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Outcome-Free Alternative Candidate Audit",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        "",
        "This audit inspects changed records where the stored outcome-free "
        "screen selected a posterior joint-comfort failure. It asks whether "
        "another admissible candidate existed, and whether that candidate also "
        "passed predeclared current-tick jerk guards.",
        "",
    ]
    for screen in report["screens"]:
        lines.extend(
            [
                f"## `{screen['name']}`",
                "",
                f"- Failure records: {screen['failure_records']}",
                f"- With any admissible posterior-success candidate: "
                f"{screen['with_any_admissible_posterior_success']}",
                "",
                "### Guarded Alternatives",
                "",
                "| Guard set | With guarded success | Rate | Guarded success count mean | Best guarded rank mean | Best guarded progress mean | Best guarded jerk mean | Best guarded lateral mean |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for guard in screen["guard_sets"]:
            delta = guard["best_guarded_success_outcome_delta_summary"]
            lines.append(
                f"| `{guard['name']}` | {guard['with_guarded_success']} | "
                f"{guard['guarded_success_rate']:.6f} | "
                f"{_fmt(guard['guarded_success_count']['mean'])} | "
                f"{_fmt(guard['best_guarded_success_rank']['mean'])} | "
                f"{_fmt(delta['progress_m']['mean'])} | "
                f"{_fmt(delta['mean_jerk_mps3']['mean'])} | "
                f"{_fmt(delta['mean_lateral_acceleration_mps2']['mean'])} |"
            )
        lines.extend(
            [
                "",
                "### Rank And Candidate Counts",
                "",
                "| Quantity | Mean | P50 | P90 | P95 |",
                "| --- | ---: | ---: | ---: | ---: |",
                _summary_row("Admissible candidates", screen["candidate_counts"]["admissible"]),
                _summary_row(
                    "Admissible posterior-success candidates",
                    screen["candidate_counts"]["admissible_success"],
                ),
                _summary_row("Chosen rank", screen["rank_summary"]["chosen_rank"]),
                _summary_row("Best posterior-success rank", screen["rank_summary"]["best_success_rank"]),
                "",
            ]
        )
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
