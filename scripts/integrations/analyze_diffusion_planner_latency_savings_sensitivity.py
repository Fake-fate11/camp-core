#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

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


TOTAL_FIELD = "latency_ms_including_candidate_generation"
CLEARANCE_FIELD = "latency_ms_shadow_obstacle_clearance"
ATOM_FIELD = "latency_ms_camp_atom_computation"
CAMP_SELECTION_FIELD = "latency_ms_camp_selection"
REWARD_FIELD = "latency_ms_reward_scoring"
CANDIDATE_FIELD = "latency_ms_candidate_generation"


@dataclass(frozen=True)
class Scenario:
    name: str
    component: str | None
    camp_side_exact_equivalence_candidate: bool
    exact_equivalence_engineering_candidate: bool
    admissibility_note: str
    saving_fn: Callable[[dict[str, float]], float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Project which component-level latency savings would be sufficient "
            "to clear the DP-CAMP no-outcome Full36 latency gate. This is "
            "read-only and does not replay or change selector semantics."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--budget_ms", type=float, default=100.0)
    parser.add_argument("--max_examples", type=int, default=10)
    parser.add_argument(
        "--reference_old_clearance_p95_ms",
        type=float,
        required=True,
        help="Old smoke-test clearance p95 used as the scale baseline.",
    )
    parser.add_argument(
        "--reference_new_clearance_p95_ms",
        type=float,
        required=True,
        help="New vectorized smoke-test clearance p95 used for projection.",
    )
    parser.add_argument(
        "--reference_source",
        default=None,
        help="Human-readable path/SHA note for the smoke artifact source.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        budget_ms=args.budget_ms,
        max_examples=args.max_examples,
        reference_old_clearance_p95_ms=args.reference_old_clearance_p95_ms,
        reference_new_clearance_p95_ms=args.reference_new_clearance_p95_ms,
        reference_source=args.reference_source,
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
    paths: Sequence[Path],
    *,
    label: str | None = None,
    budget_ms: float = 100.0,
    max_examples: int = 10,
    reference_old_clearance_p95_ms: float,
    reference_new_clearance_p95_ms: float,
    reference_source: str | None = None,
) -> dict[str, Any]:
    if budget_ms <= 0.0:
        raise ValueError("budget_ms must be positive.")
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    if reference_old_clearance_p95_ms <= 0.0:
        raise ValueError("reference_old_clearance_p95_ms must be positive.")
    if reference_new_clearance_p95_ms < 0.0:
        raise ValueError("reference_new_clearance_p95_ms must be nonnegative.")

    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    roots = _directory_inputs(paths)
    rows = _load_rows(log_paths, roots)
    usable_rows = [
        row
        for row in rows
        if row["latencies"].get(TOTAL_FIELD) is not None
        and row["latencies"].get(CLEARANCE_FIELD) is not None
    ]
    if not usable_rows:
        raise ValueError(
            f"No records had finite {TOTAL_FIELD} and {CLEARANCE_FIELD} values."
        )

    scale_ratio = reference_new_clearance_p95_ms / reference_old_clearance_p95_ms
    projection_modes: dict[str, Callable[[float], float]] = {
        "constant_new_p95": lambda old: reference_new_clearance_p95_ms,
        "cap_at_new_p95": lambda old: min(old, reference_new_clearance_p95_ms),
        "scale_by_smoke_p95_ratio": lambda old: old * scale_ratio,
    }
    scenarios = _scenarios()
    return {
        "analysis": {
            "name": "dp_camp_latency_savings_sensitivity_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "projection_not_replay_measurement": True,
            "component_savings_are_hypothetical": True,
            "selector_semantics_changed": False,
            "budget_ms": float(budget_ms),
            "math_boundary": (
                "This audit projects runtime savings over existing current-tick "
                "latency logs. It does not change finite candidates, atom "
                "values, feasibility, affine CAMP scoring, optimization "
                "masters, Benders subproblems, duals, or cuts."
            ),
        },
        "reference": {
            "source": reference_source,
            "old_clearance_p95_ms": float(reference_old_clearance_p95_ms),
            "new_clearance_p95_ms": float(reference_new_clearance_p95_ms),
            "scale_ratio": float(scale_ratio),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(rows),
            "usable": len(usable_rows),
            "missing_total_latency": sum(
                row["latencies"].get(TOTAL_FIELD) is None for row in rows
            ),
            "missing_clearance_latency": sum(
                row["latencies"].get(CLEARANCE_FIELD) is None for row in rows
            ),
        },
        "projection_modes": {
            mode_name: _mode_report(
                usable_rows,
                projection_fn=projection_fn,
                scenarios=scenarios,
                budget_ms=budget_ms,
                max_examples=max_examples,
            )
            for mode_name, projection_fn in projection_modes.items()
        },
    }


def _scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            name="no_extra_saving",
            component=None,
            camp_side_exact_equivalence_candidate=True,
            exact_equivalence_engineering_candidate=True,
            admissibility_note="baseline projection after clearance replacement only",
            saving_fn=lambda _latencies: 0.0,
        ),
        Scenario(
            name="camp_atom_computation_25pct_saving",
            component=ATOM_FIELD,
            camp_side_exact_equivalence_candidate=True,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "CAMP-side optimization candidate only if atom values remain bitwise "
                "or numerically equivalent within the existing tolerance"
            ),
            saving_fn=lambda latencies: 0.25 * _latency(latencies, ATOM_FIELD),
        ),
        Scenario(
            name="camp_atom_computation_50pct_saving",
            component=ATOM_FIELD,
            camp_side_exact_equivalence_candidate=True,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "CAMP-side optimization candidate only if atom values remain bitwise "
                "or numerically equivalent within the existing tolerance"
            ),
            saving_fn=lambda latencies: 0.50 * _latency(latencies, ATOM_FIELD),
        ),
        Scenario(
            name="camp_atom_computation_zero_upper_bound",
            component=ATOM_FIELD,
            camp_side_exact_equivalence_candidate=True,
            exact_equivalence_engineering_candidate=False,
            admissibility_note=(
                "upper bound on CAMP-side atom-computation savings; not a promised "
                "implementation target"
            ),
            saving_fn=lambda latencies: _latency(latencies, ATOM_FIELD),
        ),
        Scenario(
            name="reward_scoring_10pct_saving",
            component=REWARD_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "reward/feasibility plumbing candidate only if reward outputs and "
                "feasibility masks remain exactly equivalent"
            ),
            saving_fn=lambda latencies: 0.10 * _latency(latencies, REWARD_FIELD),
        ),
        Scenario(
            name="reward_scoring_25pct_saving",
            component=REWARD_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "reward/feasibility plumbing candidate only if reward outputs and "
                "feasibility masks remain exactly equivalent"
            ),
            saving_fn=lambda latencies: 0.25 * _latency(latencies, REWARD_FIELD),
        ),
        Scenario(
            name="reward_scoring_50pct_saving",
            component=REWARD_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "reward/feasibility plumbing candidate only if reward outputs and "
                "feasibility masks remain exactly equivalent"
            ),
            saving_fn=lambda latencies: 0.50 * _latency(latencies, REWARD_FIELD),
        ),
        Scenario(
            name="camp_atom_50pct_plus_reward_10pct",
            component=f"{ATOM_FIELD}+{REWARD_FIELD}",
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "combined exact-equivalent engineering candidate; reward plumbing "
                "must not be described as a CAMP Benders subproblem"
            ),
            saving_fn=lambda latencies: (
                0.50 * _latency(latencies, ATOM_FIELD)
                + 0.10 * _latency(latencies, REWARD_FIELD)
            ),
        ),
        Scenario(
            name="camp_atom_50pct_plus_reward_25pct",
            component=f"{ATOM_FIELD}+{REWARD_FIELD}",
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "combined exact-equivalent engineering candidate; reward plumbing "
                "must not be described as a CAMP Benders subproblem"
            ),
            saving_fn=lambda latencies: (
                0.50 * _latency(latencies, ATOM_FIELD)
                + 0.25 * _latency(latencies, REWARD_FIELD)
            ),
        ),
        Scenario(
            name="camp_atom_50pct_plus_reward_50pct",
            component=f"{ATOM_FIELD}+{REWARD_FIELD}",
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=True,
            admissibility_note=(
                "combined exact-equivalent engineering candidate; reward plumbing "
                "must not be described as a CAMP Benders subproblem"
            ),
            saving_fn=lambda latencies: (
                0.50 * _latency(latencies, ATOM_FIELD)
                + 0.50 * _latency(latencies, REWARD_FIELD)
            ),
        ),
        Scenario(
            name="camp_selection_zero_upper_bound",
            component=CAMP_SELECTION_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=False,
            admissibility_note=(
                "broad diagnostic upper bound; removing all CAMP selection latency "
                "is not an implementation plan"
            ),
            saving_fn=lambda latencies: _latency(latencies, CAMP_SELECTION_FIELD),
        ),
        Scenario(
            name="reward_scoring_zero_engineering_upper_bound",
            component=REWARD_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=False,
            admissibility_note=(
                "reward scoring is instrumentation/plumbing here, not a CAMP "
                "Benders subproblem or cut source"
            ),
            saving_fn=lambda latencies: _latency(latencies, REWARD_FIELD),
        ),
        Scenario(
            name="candidate_generation_zero_inadmissible_upper_bound",
            component=CANDIDATE_FIELD,
            camp_side_exact_equivalence_candidate=False,
            exact_equivalence_engineering_candidate=False,
            admissibility_note=(
                "inadmissible under the current goal because DP is fixed as a "
                "black-box candidate generator"
            ),
            saving_fn=lambda latencies: _latency(latencies, CANDIDATE_FIELD),
        ),
    )


def _mode_report(
    rows: Sequence[dict[str, Any]],
    *,
    projection_fn: Callable[[float], float],
    scenarios: Sequence[Scenario],
    budget_ms: float,
    max_examples: int,
) -> dict[str, Any]:
    projected_rows = [_project_row(row, projection_fn) for row in rows]
    baseline_runs = _run_summaries(
        projected_rows,
        adjusted_total_key="projected_total_ms",
        budget_ms=budget_ms,
    )
    baseline_over = sum(row["over_budget"] for row in baseline_runs)
    scenario_reports = {}
    for scenario in scenarios:
        scenario_rows = [
            _apply_scenario(row, scenario) for row in projected_rows
        ]
        run_summaries = _run_summaries(
            scenario_rows,
            adjusted_total_key="adjusted_total_ms",
            budget_ms=budget_ms,
        )
        over_budget = [row for row in run_summaries if row["over_budget"]]
        scenario_reports[scenario.name] = {
            "component": scenario.component,
            "camp_side_exact_equivalence_candidate": (
                scenario.camp_side_exact_equivalence_candidate
            ),
            "exact_equivalence_engineering_candidate": (
                scenario.exact_equivalence_engineering_candidate
            ),
            "admissibility_note": scenario.admissibility_note,
            "runs": len(run_summaries),
            "runs_over_budget": len(over_budget),
            "runs_over_budget_delta_vs_no_extra_saving": (
                len(over_budget) - baseline_over
            ),
            "budget_passing_rate": (
                float((len(run_summaries) - len(over_budget)) / len(run_summaries))
                if run_summaries
                else None
            ),
            "per_run_p95_ms": _summary(
                [row["p95_ms"] for row in run_summaries]
            ),
            "per_run_shortfall_ms": _summary(
                [row["shortfall_ms"] for row in over_budget]
            ),
            "mean_record_saving_ms": _summary(
                [row["scenario_saving_ms"] for row in scenario_rows]
            ),
            "over_budget_runs": over_budget[:max_examples],
        }
    return {
        "no_extra_saving_runs_over_budget": baseline_over,
        "no_extra_saving_per_run_p95_ms": _summary(
            [row["p95_ms"] for row in baseline_runs]
        ),
        "scenarios": scenario_reports,
    }


def _project_row(
    row: dict[str, Any],
    projection_fn: Callable[[float], float],
) -> dict[str, Any]:
    latencies = dict(row["latencies"])
    total = _latency(latencies, TOTAL_FIELD)
    old_clearance = _latency(latencies, CLEARANCE_FIELD)
    projected_clearance = float(projection_fn(old_clearance))
    projected_total = max(total - old_clearance + projected_clearance, 0.0)
    return {
        **row,
        "latencies": latencies,
        "projected_clearance_ms": projected_clearance,
        "projected_total_ms": projected_total,
    }


def _apply_scenario(
    row: dict[str, Any],
    scenario: Scenario,
) -> dict[str, Any]:
    saving = max(float(scenario.saving_fn(row["latencies"])), 0.0)
    adjusted_total = max(float(row["projected_total_ms"]) - saving, 0.0)
    return {
        **row,
        "scenario_saving_ms": saving,
        "adjusted_total_ms": adjusted_total,
    }


def _run_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    adjusted_total_key: str,
    budget_ms: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_key"], []).append(row)
    result = []
    for run_key, run_rows in grouped.items():
        values = [float(row[adjusted_total_key]) for row in run_rows]
        p95 = _percentile(values, 95.0)
        result.append(
            {
                "run_key": run_key,
                "records": len(run_rows),
                "p95_ms": float(p95),
                "shortfall_ms": float(max(p95 - budget_ms, 0.0)),
                "over_budget": bool(p95 > budget_ms),
            }
        )
    return sorted(
        result,
        key=lambda row: (row["p95_ms"], row["run_key"]),
        reverse=True,
    )


def _load_rows(
    log_paths: Sequence[Path],
    roots: Sequence[Path],
) -> list[dict[str, Any]]:
    fields = (
        TOTAL_FIELD,
        CLEARANCE_FIELD,
        ATOM_FIELD,
        CAMP_SELECTION_FIELD,
        REWARD_FIELD,
        CANDIDATE_FIELD,
    )
    rows: list[dict[str, Any]] = []
    for log_path in log_paths:
        records = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        run_key = _run_key(log_path, roots)
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            rows.append(
                {
                    "log_path": str(log_path),
                    "run_key": run_key,
                    "record_index": int(record_index),
                    "selection_step": record.get("selection_step", record_index),
                    "latencies": {
                        field: _finite(record.get(field)) for field in fields
                    },
                }
            )
    return rows


def _directory_inputs(paths: Sequence[Path]) -> list[Path]:
    roots = [Path(path).resolve() for path in paths if Path(path).is_dir()]
    return sorted(roots, key=lambda path: len(path.parts), reverse=True)


def _run_key(log_path: Path, roots: Sequence[Path]) -> str:
    resolved = Path(log_path).resolve()
    for root in roots:
        try:
            return str(resolved.parent.relative_to(root))
        except ValueError:
            continue
    return str(resolved.parent)


def _latency(latencies: dict[str, float | None], field: str) -> float:
    value = latencies.get(field)
    return 0.0 if value is None else float(value)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


def _summary(values: Sequence[float]) -> dict[str, Any]:
    finite_values = [
        float(value)
        for value in values
        if not isinstance(value, bool) and np.isfinite(float(value))
    ]
    if not finite_values:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    arr = np.asarray(finite_values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Latency Savings Sensitivity",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "> Projection only: component savings are hypothetical and do not "
        "change selector semantics.",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Projection Modes", ""])
    for mode_name, mode in report["projection_modes"].items():
        lines.extend(
            [
                f"### `{mode_name}`",
                "",
                "| Scenario | CAMP-Side Exact Candidate | Exact Engineering Candidate | Runs Over Budget | P95 of Run P95 | Shortfall Max | Mean Record Saving | Note |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for scenario_name, scenario in mode["scenarios"].items():
            lines.append(
                "| "
                f"`{scenario_name}` | "
                f"`{scenario['camp_side_exact_equivalence_candidate']}` | "
                f"`{scenario['exact_equivalence_engineering_candidate']}` | "
                f"`{scenario['runs_over_budget']} / {scenario['runs']}` | "
                f"{_fmt(scenario['per_run_p95_ms']['p95'])} | "
                f"{_fmt(scenario['per_run_shortfall_ms']['max'])} | "
                f"{_fmt(scenario['mean_record_saving_ms']['mean'])} | "
                f"{scenario['admissibility_note']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    return f"`{float(value):.6f}`"


if __name__ == "__main__":
    main()
