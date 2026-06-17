#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


LOWER_BETTER = "lower"
HIGHER_BETTER = "higher"
TOL = 1e-12
BENCHMARK_KEY_FIELDS = (
    "route",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
)
RUN_DELTA_FIELDS = (
    "safety_cost_v1",
    "route_completion_rate",
    "near_miss_rate",
    "planned_red_light_violation_rate",
    "mean_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "p95_selection_latency_ms",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute the rejected traffic-light hybrid postselection smoke "
            "using current-tick finite-candidate diagnostics only."
        )
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--baseline_root",
        type=Path,
        default=None,
        help=(
            "Optional no-hybrid static baseline root. Used only for paired "
            "closed-loop run deltas; selection attribution still comes from "
            "the hybrid log itself."
        ),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        args.root,
        baseline_root=args.baseline_root,
        label=args.label,
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
    root: Path,
    *,
    baseline_root: Path | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    baseline_root = baseline_root.resolve() if baseline_root is not None else None
    static_logs = sorted(root.glob("**/static/camp_selection_log.json"))
    if not static_logs:
        raise ValueError(f"No static CAMP selection logs found under {root}.")

    baseline_runs = _index_static_summaries(baseline_root) if baseline_root else {}
    reason_counts: dict[str, int] = {}
    change_type_counts: dict[str, int] = {}
    run_reports: list[dict[str, Any]] = []
    changed_events: list[dict[str, Any]] = []
    deltas_vs_baseline: dict[str, list[float]] = {}
    deltas_vs_candidate0: dict[str, list[float]] = {}

    total_records = 0
    changed_records = 0
    selected_nonzero_records = 0
    paired_baseline_runs = 0
    missing_baseline_runs: list[str] = []

    for log_path in static_logs:
        run_dir = log_path.parent
        summary = _read_json(run_dir / "camp_validation_summary.json")
        key = _benchmark_key(summary)
        baseline_summary = baseline_runs.get(key)
        if baseline_root is not None:
            if baseline_summary is None:
                missing_baseline_runs.append(str(run_dir.relative_to(root)))
            else:
                paired_baseline_runs += 1

        records = _read_json(log_path)
        if not isinstance(records, list) or not records:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")

        run_changed: list[int] = []
        run_reason_counts: dict[str, int] = {}
        run_selected_nonzero = 0
        for record_index, record in enumerate(records):
            total_records += 1
            _reject_candidate_outcomes(record, log_path, record_index)
            selected = _int_index(record.get("selected_index"), "selected_index")
            run_selected_nonzero += int(selected != 0)
            selected_nonzero_records += int(selected != 0)
            hybrid = record.get("traffic_light_hybrid_postselection") or {}
            reason = str(hybrid.get("reason"))
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            run_reason_counts[reason] = run_reason_counts.get(reason, 0) + 1
            if not bool(hybrid.get("changed")):
                continue

            changed_records += 1
            run_changed.append(record_index)
            before = _int_index(
                record.get(
                    "camp_selected_index_before_traffic_light_hybrid_postselection"
                ),
                "camp_selected_index_before_traffic_light_hybrid_postselection",
            )
            change_type = _change_type(before, selected)
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
            features = _feature_vectors(record)
            baseline_deltas = _candidate_deltas(features, selected, before)
            candidate0_deltas = _candidate_deltas(features, selected, 0)
            _extend_deltas(deltas_vs_baseline, baseline_deltas)
            _extend_deltas(deltas_vs_candidate0, candidate0_deltas)
            changed_events.append(
                _event_row(
                    root=root,
                    log_path=log_path,
                    record_index=record_index,
                    before=before,
                    selected=selected,
                    change_type=change_type,
                    hybrid=hybrid,
                    baseline_deltas=baseline_deltas,
                    candidate0_deltas=candidate0_deltas,
                )
            )

        run_reports.append(
            _run_report(
                root=root,
                run_dir=run_dir,
                summary=summary,
                baseline_summary=baseline_summary,
                records=len(records),
                changed_steps=run_changed,
                selected_nonzero=run_selected_nonzero,
                reason_counts=run_reason_counts,
            )
        )

    return {
        "analysis": {
            "name": "dp_camp_traffic_light_hybrid_failure_attribution_v1",
            "label": label,
            "role": (
                "read-only attribution of the rejected traffic-light hybrid "
                "postselection smoke"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
            "convexity_boundary": (
                "All audited quantities are fixed current-tick finite-candidate "
                "diagnostics. If promoted to CAMP atoms with fixed nonnegative "
                "scaling, scores remain affine in the CAMP master variable. "
                "This report does not make DP, tracker, simulator, or trajectory "
                "coordinates part of a Benders subproblem."
            ),
        },
        "inputs": {
            "root": str(root),
            "baseline_root": str(baseline_root) if baseline_root else None,
        },
        "records": {
            "runs": len(static_logs),
            "total": total_records,
            "changed": changed_records,
            "selected_nonzero": selected_nonzero_records,
            "selected_nonzero_rate": (
                selected_nonzero_records / total_records if total_records else 0.0
            ),
        },
        "traffic_light_hybrid_reasons": reason_counts,
        "change_types": change_type_counts,
        "pairing": {
            "baseline_root_provided": baseline_root is not None,
            "paired_baseline_runs": paired_baseline_runs,
            "missing_baseline_runs": missing_baseline_runs,
        },
        "feature_deltas_vs_original_camp": _feature_delta_report(
            deltas_vs_baseline
        ),
        "feature_deltas_vs_candidate0": _feature_delta_report(
            deltas_vs_candidate0
        ),
        "run_reports": run_reports,
        "changed_events": changed_events,
    }


def _feature_vectors(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    specs: dict[str, tuple[str, Callable[[dict[str, Any]], list[float] | None]]] = {
        "camp_score": (LOWER_BETTER, lambda row: _vector(row, "selection_scores")),
        "dp_total": (HIGHER_BETTER, lambda row: _reward_vector(row, "total")),
        "dp_progress": (HIGHER_BETTER, lambda row: _reward_vector(row, "progress")),
        "dp_smoothness": (
            HIGHER_BETTER,
            lambda row: _reward_vector(row, "smoothness"),
        ),
        "union_red": (
            LOWER_BETTER,
            lambda row: _vector(row, "candidate_horizon_union_planned_red_light_cost"),
        ),
        "red_stopping": (
            LOWER_BETTER,
            lambda row: _vector(row, "candidate_red_stopping_margin_cost"),
        ),
        "raw_jerk": (
            LOWER_BETTER,
            lambda row: _vector(row, "candidate_dp_prior_jerk_excess_cost"),
        ),
        "raw_lateral": (
            LOWER_BETTER,
            lambda row: _vector(row, "candidate_horizon_lateral_acceleration_cost"),
        ),
        "target_speed": (
            HIGHER_BETTER,
            lambda row: _vector(row, "candidate_perfect_tracker_target_speed_mps"),
        ),
        "first_step_reach": (
            HIGHER_BETTER,
            lambda row: _vector(row, "candidate_step_reach"),
        ),
        "h3_distance": (
            HIGHER_BETTER,
            lambda row: _rollout_vector(row, 3, "distance_m"),
        ),
        "h10_distance": (
            HIGHER_BETTER,
            lambda row: _rollout_vector(row, 10, "distance_m"),
        ),
    }
    features: dict[str, dict[str, Any]] = {}
    for name, (direction, getter) in specs.items():
        values = getter(record)
        if values is not None:
            features[name] = {"direction": direction, "values": values}
    return features


def _candidate_deltas(
    features: dict[str, dict[str, Any]],
    selected: int,
    reference: int,
) -> dict[str, dict[str, Any]]:
    deltas: dict[str, dict[str, Any]] = {}
    for name, payload in features.items():
        values = payload["values"]
        if selected >= len(values) or reference >= len(values):
            continue
        delta = float(values[selected]) - float(values[reference])
        direction = str(payload["direction"])
        if direction == LOWER_BETTER:
            attractive = delta < -TOL
            worse = delta > TOL
        else:
            attractive = delta > TOL
            worse = delta < -TOL
        deltas[name] = {
            "delta": delta,
            "direction": direction,
            "attractive": attractive,
            "worse": worse,
        }
    return deltas


def _event_row(
    *,
    root: Path,
    log_path: Path,
    record_index: int,
    before: int,
    selected: int,
    change_type: str,
    hybrid: dict[str, Any],
    baseline_deltas: dict[str, dict[str, Any]],
    candidate0_deltas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run": str(log_path.parent.relative_to(root)),
        "selection_step": record_index,
        "before_hybrid_index": before,
        "selected_index": selected,
        "change_type": change_type,
        "admissible_candidates": int(hybrid.get("admissible_candidates", 0)),
        "admissible_indices": hybrid.get("admissible_indices", []),
        "hybrid_rule_delta": hybrid.get("delta", {}),
        "hybrid_rule_losses": hybrid.get("losses", {}),
        "attractive_vs_original_camp": _attractive_features(baseline_deltas),
        "worse_vs_candidate0": _worse_features(candidate0_deltas),
        "deltas_vs_original_camp": baseline_deltas,
        "deltas_vs_candidate0": candidate0_deltas,
    }


def _run_report(
    *,
    root: Path,
    run_dir: Path,
    summary: dict[str, Any],
    baseline_summary: dict[str, Any] | None,
    records: int,
    changed_steps: list[int],
    selected_nonzero: int,
    reason_counts: dict[str, int],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "run": str(run_dir.relative_to(root)),
        "records": records,
        "changed_records": len(changed_steps),
        "changed_steps": changed_steps,
        "selected_nonzero": selected_nonzero,
        "selected_nonzero_rate": selected_nonzero / records if records else 0.0,
        "reason_counts": reason_counts,
        "summary": _selected_summary_fields(summary),
    }
    if baseline_summary is not None:
        report["baseline_delta"] = _summary_deltas(summary, baseline_summary)
    return report


def _summary_deltas(
    summary: dict[str, Any],
    baseline_summary: dict[str, Any],
) -> dict[str, float | None]:
    enriched = _summary_with_safety_cost(summary)
    baseline = _summary_with_safety_cost(baseline_summary)
    return {
        field: _optional_float(enriched.get(field), baseline.get(field))
        for field in RUN_DELTA_FIELDS
    }


def _selected_summary_fields(summary: dict[str, Any]) -> dict[str, Any]:
    enriched = _summary_with_safety_cost(summary)
    return {field: enriched.get(field) for field in RUN_DELTA_FIELDS}


def _summary_with_safety_cost(summary: dict[str, Any]) -> dict[str, Any]:
    out = dict(summary)
    out["safety_cost_v1"] = _safety_cost_v1(summary)
    return out


def _safety_cost_v1(summary: dict[str, Any]) -> float | None:
    required = (
        "obb_collision_rate",
        "near_miss_rate",
        "lane_violation_rate",
        "red_light_violation_rate",
        "planned_red_light_violation_rate",
        "mean_jerk_magnitude_mps3",
        "mean_lateral_acceleration_mps2",
        "route_completion_rate",
    )
    values = [_as_float(summary.get(field)) for field in required]
    if any(value is None for value in values):
        return None
    collision, near, lane, red, planned_red, jerk, lateral, completion = values
    assert collision is not None
    assert near is not None
    assert lane is not None
    assert red is not None
    assert planned_red is not None
    assert jerk is not None
    assert lateral is not None
    assert completion is not None
    return (
        100.0 * _clip(collision, 0.0, 1.0)
        + 10.0 * _clip(near, 0.0, 1.0)
        + 20.0 * _clip(lane, 0.0, 1.0)
        + 30.0 * _clip(red, 0.0, 1.0)
        + 15.0 * _clip(planned_red, 0.0, 1.0)
        + _clip(jerk / 10.0, 0.0, 10.0)
        + 2.0 * _clip(lateral / 2.0, 0.0, 10.0)
        + 2.0 * _clip(1.0 - completion, 0.0, 1.0)
    )


def _feature_delta_report(
    deltas_by_feature: dict[str, list[float]],
) -> dict[str, dict[str, Any]]:
    return {
        name: _numeric_summary(values)
        for name, values in sorted(deltas_by_feature.items())
    }


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "negative": int(np.sum(arr < -TOL)),
        "positive": int(np.sum(arr > TOL)),
        "zero": int(np.sum(np.abs(arr) <= TOL)),
    }


def _extend_deltas(
    target: dict[str, list[float]],
    deltas: dict[str, dict[str, Any]],
) -> None:
    for name, payload in deltas.items():
        target.setdefault(name, []).append(float(payload["delta"]))


def _attractive_features(deltas: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(name for name, payload in deltas.items() if payload["attractive"])


def _worse_features(deltas: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(name for name, payload in deltas.items() if payload["worse"])


def _index_static_summaries(root: Path | None) -> dict[tuple[Any, ...], dict[str, Any]]:
    if root is None:
        return {}
    summaries = sorted(root.glob("**/static/camp_validation_summary.json"))
    if not summaries:
        raise ValueError(f"No static summaries found under {root}.")
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for path in summaries:
        summary = _read_json(path)
        key = _benchmark_key(summary)
        if key in indexed:
            raise ValueError(f"Duplicate baseline benchmark key under {root}: {key}")
        indexed[key] = summary
    return indexed


def _benchmark_key(summary: dict[str, Any]) -> tuple[Any, ...]:
    benchmark = summary.get("benchmark")
    if not isinstance(benchmark, dict):
        raise ValueError("camp_validation_summary.json is missing benchmark metadata.")
    route = benchmark.get("route")
    route_key = Path(str(route)).stem if route is not None else None
    values: list[Any] = [route_key]
    for field in BENCHMARK_KEY_FIELDS[1:]:
        value = benchmark.get(field)
        if isinstance(value, float):
            value = round(value, 9)
        values.append(value)
    return tuple(values)


def _change_type(before: int, selected: int) -> str:
    if before != 0 and selected == 0:
        return "to_candidate0"
    if before == 0 and selected != 0:
        return "away_from_candidate0"
    if before != selected:
        return "nonzero_to_nonzero"
    return "unchanged"


def _vector(record: dict[str, Any], field: str) -> list[float] | None:
    values = record.get(field)
    if not isinstance(values, list):
        return None
    return [float(value) for value in values]


def _reward_vector(record: dict[str, Any], key: str) -> list[float] | None:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list):
        return None
    values: list[float] = []
    for reward in rewards:
        if not isinstance(reward, dict) or key not in reward:
            return None
        values.append(float(reward[key]))
    return values


def _rollout_vector(record: dict[str, Any], horizon: int, key: str) -> list[float] | None:
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict):
        return None
    payload = rollout.get(str(horizon), rollout.get(horizon))
    if not isinstance(payload, dict):
        return None
    values = payload.get(key)
    if not isinstance(values, list):
        return None
    return [float(value) for value in values]


def _reject_candidate_outcomes(
    record: dict[str, Any],
    log_path: Path,
    record_index: int,
) -> None:
    outcomes = record.get("candidate_closed_loop_outcomes")
    if outcomes is not None:
        raise ValueError(
            f"{log_path} record {record_index} contains candidate closed-loop "
            "outcomes; this attribution must remain outcome-free."
        )


def _int_index(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer index.")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return int(value)


def _optional_float(value: Any, baseline: Any) -> float | None:
    left = _as_float(value)
    right = _as_float(baseline)
    if left is None or right is None:
        return None
    return left - right


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _clip(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Traffic-Light Hybrid Failure Attribution")
    lines.append("")
    records = report["records"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Root: `{report['inputs']['root']}`")
    if report["inputs"].get("baseline_root"):
        lines.append(f"- Baseline root: `{report['inputs']['baseline_root']}`")
    lines.append(f"- Runs: `{records['runs']}`")
    lines.append(f"- Records: `{records['total']}`")
    lines.append(f"- Hybrid-changed records: `{records['changed']}`")
    lines.append(
        f"- Selected nonzero records after hybrid: "
        f"`{records['selected_nonzero']}` "
        f"(`{records['selected_nonzero_rate']:.6f}`)"
    )
    lines.append("")
    lines.append("## Reasons")
    lines.append("")
    lines.append("| Reason | Count |")
    lines.append("| --- | ---: |")
    for reason, count in sorted(
        report["traffic_light_hybrid_reasons"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"| `{reason}` | {count} |")
    lines.append("")
    lines.append("## Change Types")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("| --- | ---: |")
    for change_type, count in sorted(report["change_types"].items()):
        lines.append(f"| `{change_type}` | {count} |")
    lines.append("")
    lines.extend(_feature_table("Vs Original CAMP", report["feature_deltas_vs_original_camp"]))
    lines.extend(_feature_table("Vs Candidate0", report["feature_deltas_vs_candidate0"]))
    lines.append("## Runs With Changes")
    lines.append("")
    lines.append(
        "| Run | Changed | SafetyCost Delta vs Baseline | Near-Miss Delta | "
        "Planned-Red Delta | Jerk Delta |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    changed_runs = [
        run for run in report["run_reports"] if run["changed_records"] > 0
    ]
    for run in sorted(changed_runs, key=lambda item: (-item["changed_records"], item["run"])):
        delta = run.get("baseline_delta", {})
        lines.append(
            f"| `{run['run']}` | {run['changed_records']} | "
            f"{_fmt(delta.get('safety_cost_v1'))} | "
            f"{_fmt(delta.get('near_miss_rate'))} | "
            f"{_fmt(delta.get('planned_red_light_violation_rate'))} | "
            f"{_fmt(delta.get('mean_jerk_magnitude_mps3'))} |"
        )
    lines.append("")
    lines.append("## Changed Events")
    lines.append("")
    lines.append(
        "| Run | Step | Before | After | Type | Attractive vs CAMP | Worse vs C0 |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | --- | --- |")
    for event in report["changed_events"][:40]:
        lines.append(
            f"| `{event['run']}` | {event['selection_step']} | "
            f"{event['before_hybrid_index']} | {event['selected_index']} | "
            f"`{event['change_type']}` | "
            f"`{', '.join(event['attractive_vs_original_camp'])}` | "
            f"`{', '.join(event['worse_vs_candidate0'])}` |"
        )
    lines.append("")
    lines.append("## Mathematical Boundary")
    lines.append("")
    lines.append(report["analysis"]["convexity_boundary"])
    lines.append("")
    return "\n".join(lines)


def _feature_table(title: str, payload: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"## Feature Deltas {title}", ""]
    lines.append("| Feature | n | mean | min | max | negative | positive | zero |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name, stats in payload.items():
        lines.append(
            f"| `{name}` | {stats.get('n', 0)} | "
            f"{_fmt(stats.get('mean'))} | {_fmt(stats.get('min'))} | "
            f"{_fmt(stats.get('max'))} | {stats.get('negative', 0)} | "
            f"{stats.get('positive', 0)} | {stats.get('zero', 0)} |"
        )
    lines.append("")
    return lines


if __name__ == "__main__":
    main()
