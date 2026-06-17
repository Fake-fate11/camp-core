#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Project the engineering latency effect of replacing old obstacle "
            "clearance shadow diagnostics with the vectorized implementation. "
            "This is a read-only projection over existing logs, not a replay."
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
        if row["total_latency_ms"] is not None
        and row["old_clearance_latency_ms"] is not None
    ]
    if not usable_rows:
        raise ValueError(
            f"No records had finite {TOTAL_FIELD} and {CLEARANCE_FIELD} values."
        )

    scale_ratio = (
        reference_new_clearance_p95_ms / reference_old_clearance_p95_ms
    )
    modes = {
        "constant_new_p95": lambda old: reference_new_clearance_p95_ms,
        "cap_at_new_p95": lambda old: min(old, reference_new_clearance_p95_ms),
        "scale_by_smoke_p95_ratio": lambda old: old * scale_ratio,
    }
    mode_reports = {
        mode: _mode_report(
            usable_rows,
            budget_ms=budget_ms,
            max_examples=max_examples,
            replacement_fn=replacement_fn,
        )
        for mode, replacement_fn in modes.items()
    }
    report = {
        "analysis": {
            "name": "dp_camp_clearance_latency_projection_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "projection_not_replay_measurement": True,
            "selector_semantics_changed": False,
            "total_latency_field": TOTAL_FIELD,
            "clearance_latency_field": CLEARANCE_FIELD,
            "budget_ms": float(budget_ms),
            "math_boundary": (
                "This projection is a read-only engineering diagnostic over "
                "existing current-tick latency logs. It does not define CAMP "
                "atoms, selector constraints, Benders subproblems, duals, or "
                "cuts, and it must not be cited as replay-measured latency."
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
                row["total_latency_ms"] is None for row in rows
            ),
            "missing_clearance_latency": sum(
                row["old_clearance_latency_ms"] is None for row in rows
            ),
        },
        "baseline": _baseline_report(
            usable_rows,
            budget_ms=budget_ms,
            max_examples=max_examples,
        ),
        "projection_modes": mode_reports,
    }
    return report


def _directory_inputs(paths: Sequence[Path]) -> list[Path]:
    roots = [Path(path).resolve() for path in paths if Path(path).is_dir()]
    return sorted(roots, key=lambda path: len(path.parts), reverse=True)


def _load_rows(
    log_paths: Sequence[Path],
    roots: Sequence[Path],
) -> list[dict[str, Any]]:
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
                    "total_latency_ms": _finite(record.get(TOTAL_FIELD)),
                    "old_clearance_latency_ms": _finite(record.get(CLEARANCE_FIELD)),
                }
            )
    return rows


def _run_key(log_path: Path, roots: Sequence[Path]) -> str:
    resolved = Path(log_path).resolve()
    for root in roots:
        try:
            return str(resolved.parent.relative_to(root))
        except ValueError:
            continue
    return str(resolved.parent)


def _baseline_report(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
    max_examples: int,
) -> dict[str, Any]:
    totals = [float(row["total_latency_ms"]) for row in rows]
    clearances = [float(row["old_clearance_latency_ms"]) for row in rows]
    per_run = _per_run_summary(rows, budget_ms=budget_ms)
    return {
        "total_latency_ms": _summary(totals),
        "clearance_latency_ms": _summary(clearances),
        "per_run_total_p95_ms": _summary(
            [row["baseline_total_p95_ms"] for row in per_run]
        ),
        "runs_over_budget": sum(
            row["baseline_total_p95_ms"] > budget_ms for row in per_run
        ),
        "runs": len(per_run),
        "worst_runs": per_run[:max_examples],
    }


def _mode_report(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
    max_examples: int,
    replacement_fn: Any,
) -> dict[str, Any]:
    projected_rows = []
    for row in rows:
        total = float(row["total_latency_ms"])
        old_clearance = float(row["old_clearance_latency_ms"])
        projected_clearance = float(replacement_fn(old_clearance))
        projected_total = max(total - old_clearance + projected_clearance, 0.0)
        projected_rows.append(
            {
                **row,
                "projected_clearance_latency_ms": projected_clearance,
                "projected_total_latency_ms": projected_total,
            }
        )
    per_run = _per_run_summary(projected_rows, budget_ms=budget_ms)
    over_budget = [
        row for row in per_run if row["projected_total_p95_ms"] > budget_ms
    ]
    return {
        "total_latency_ms": _summary(
            [row["projected_total_latency_ms"] for row in projected_rows]
        ),
        "projected_clearance_latency_ms": _summary(
            [row["projected_clearance_latency_ms"] for row in projected_rows]
        ),
        "per_run_total_p95_ms": _summary(
            [row["projected_total_p95_ms"] for row in per_run]
        ),
        "runs": len(per_run),
        "runs_over_budget": len(over_budget),
        "runs_over_budget_delta": len(over_budget)
        - sum(row["baseline_total_p95_ms"] > budget_ms for row in per_run),
        "budget_passing_rate": (
            float((len(per_run) - len(over_budget)) / len(per_run))
            if per_run
            else None
        ),
        "worst_runs": per_run[:max_examples],
        "over_budget_runs": over_budget[:max_examples],
    }


def _per_run_summary(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_key"], []).append(row)
    result: list[dict[str, Any]] = []
    for run_key, run_rows in grouped.items():
        baseline_values = [float(row["total_latency_ms"]) for row in run_rows]
        projected_values = [
            row.get("projected_total_latency_ms") for row in run_rows
        ]
        baseline_p95 = _percentile(baseline_values, 95.0)
        projected_finite = [
            float(value) for value in projected_values if value is not None
        ]
        projected_p95 = (
            _percentile(projected_finite, 95.0)
            if projected_finite
            else baseline_p95
        )
        result.append(
            {
                "run_key": run_key,
                "records": len(run_rows),
                "baseline_total_p95_ms": float(baseline_p95),
                "projected_total_p95_ms": float(projected_p95),
                "p95_delta_ms": float(projected_p95 - baseline_p95),
                "baseline_over_budget": bool(baseline_p95 > budget_ms),
                "projected_over_budget": bool(projected_p95 > budget_ms),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            row["projected_total_p95_ms"],
            row["baseline_total_p95_ms"],
            row["run_key"],
        ),
        reverse=True,
    )


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


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Clearance Latency Projection",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "> Projection only: this is not replay-measured latency and does not "
        "change selector semantics.",
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
            "## Reference",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| `source` | `{report['reference'].get('source')}` |",
            f"| `old_clearance_p95_ms` | {_fmt(report['reference']['old_clearance_p95_ms'])} |",
            f"| `new_clearance_p95_ms` | {_fmt(report['reference']['new_clearance_p95_ms'])} |",
            f"| `scale_ratio` | {_fmt(report['reference']['scale_ratio'])} |",
            "",
            "## Baseline",
            "",
            "| Metric | Mean | P50 | P95 | Max | N |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            _summary_row(
                "total_latency_ms", report["baseline"]["total_latency_ms"]
            ),
            _summary_row(
                "clearance_latency_ms",
                report["baseline"]["clearance_latency_ms"],
            ),
            _summary_row(
                "per_run_total_p95_ms",
                report["baseline"]["per_run_total_p95_ms"],
            ),
            "",
            f"Runs over budget: `{report['baseline']['runs_over_budget']}` / "
            f"`{report['baseline']['runs']}`",
            "",
            "## Projection Modes",
            "",
        ]
    )
    for mode, mode_report in report["projection_modes"].items():
        lines.extend(
            [
                f"### `{mode}`",
                "",
                "| Metric | Mean | P50 | P95 | Max | N |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                _summary_row(
                    "total_latency_ms", mode_report["total_latency_ms"]
                ),
                _summary_row(
                    "projected_clearance_latency_ms",
                    mode_report["projected_clearance_latency_ms"],
                ),
                _summary_row(
                    "per_run_total_p95_ms",
                    mode_report["per_run_total_p95_ms"],
                ),
                "",
                f"Runs over budget: `{mode_report['runs_over_budget']}` / "
                f"`{mode_report['runs']}` "
                f"(delta `{mode_report['runs_over_budget_delta']}`)",
                "",
                "| Worst Run | Baseline P95 | Projected P95 | Delta |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for row in mode_report["worst_runs"]:
            lines.append(
                "| "
                f"`{row['run_key']}` | {_fmt(row['baseline_total_p95_ms'])} | "
                f"{_fmt(row['projected_total_p95_ms'])} | "
                f"{_fmt(row['p95_delta_ms'])} |"
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


def _summary_row(field: str, summary: dict[str, Any]) -> str:
    return (
        f"| `{field}` | {_fmt(summary['mean'])} | {_fmt(summary['p50'])} | "
        f"{_fmt(summary['p95'])} | {_fmt(summary['max'])} | {summary['n']} |"
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    return f"`{float(value):.6f}`"


if __name__ == "__main__":
    main()
