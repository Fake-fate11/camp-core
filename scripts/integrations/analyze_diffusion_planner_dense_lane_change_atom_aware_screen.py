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

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (  # noqa: E402
    LooseRuleConfig,
    _choice,
    _is_dense_lane_change,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (  # noqa: E402
    _load_records,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    BOOL_FIELDS,
)


EPS = 1e-12
PROTECTIVE_ATOMS = ("dp_prior_jerk_excess_cost", "jerk_early")
DEFAULT_THRESHOLDS = (0.0, 0.005, 0.01, 0.02, 0.03, 0.05)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only atom-aware offline screen for dense lane-change supported "
            "alternatives. The runtime rule preserves current CAMP whenever the "
            "predeclared protective atom contribution margin is above threshold; "
            "candidate outcomes are posterior evaluation labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--threshold", type=float, action="append", default=[])
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--min_changed_supported_rate", type=float, default=0.05)
    parser.add_argument("--min_progress_delta_ci_low", type=float, default=-0.05)
    parser.add_argument("--max_jerk_delta_ci_high", type=float, default=0.0)
    parser.add_argument("--max_lateral_delta_ci_high", type=float, default=0.0)
    parser.add_argument("--min_hard_nonworse_rate", type=float, default=0.99)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    records = _load_records(paths, fail_on_formal_seeds=args.fail_on_formal_seeds)
    report = analyze_records(
        records,
        label=args.label,
        thresholds=tuple(args.threshold) if args.threshold else DEFAULT_THRESHOLDS,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        min_changed_supported_rate=args.min_changed_supported_rate,
        min_progress_delta_ci_low=args.min_progress_delta_ci_low,
        max_jerk_delta_ci_high=args.max_jerk_delta_ci_high,
        max_lateral_delta_ci_high=args.max_lateral_delta_ci_high,
        min_hard_nonworse_rate=args.min_hard_nonworse_rate,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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


def analyze_records(
    records: list[dict[str, Any]],
    *,
    label: str | None = None,
    config: LooseRuleConfig = LooseRuleConfig(),
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
    protective_atoms: tuple[str, ...] = PROTECTIVE_ATOMS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    min_changed_supported_rate: float = 0.05,
    min_progress_delta_ci_low: float = -0.05,
    max_jerk_delta_ci_high: float = 0.0,
    max_lateral_delta_ci_high: float = 0.0,
    min_hard_nonworse_rate: float = 0.99,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    _validate_thresholds(thresholds)
    if not protective_atoms:
        raise ValueError("At least one protective atom is required.")
    for name, value in (
        ("min_changed_supported_rate", min_changed_supported_rate),
        ("min_hard_nonworse_rate", min_hard_nonworse_rate),
    ):
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be in [0, 1].")
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    choices = [_choice(record, config) for record in records]
    rows = [
        _row(record, choice, protective_atoms=protective_atoms)
        for record, choice in zip(records, choices)
    ]
    threshold_reports = [
        _threshold_report(
            records,
            rows,
            threshold,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
            min_changed_supported_rate=min_changed_supported_rate,
            min_progress_delta_ci_low=min_progress_delta_ci_low,
            max_jerk_delta_ci_high=max_jerk_delta_ci_high,
            max_lateral_delta_ci_high=max_lateral_delta_ci_high,
            min_hard_nonworse_rate=min_hard_nonworse_rate,
        )
        for threshold in thresholds
    ]
    return {
        "analysis": {
            "name": "dense_lane_change_atom_aware_no_leak_screen_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "candidate outcomes are used only after deterministic "
                "atom-aware selection for posterior SafetyCost/progress/comfort "
                "evaluation; runtime predicates use current-tick candidate "
                "features, normalized atoms, logged weights, and score margins"
            ),
            "loose_rule": config.__dict__,
            "protective_atoms": list(protective_atoms),
            "thresholds": [float(value) for value in thresholds],
            "gate": {
                "min_changed_supported_rate": float(min_changed_supported_rate),
                "min_progress_delta_ci_low": float(min_progress_delta_ci_low),
                "max_jerk_delta_ci_high": float(max_jerk_delta_ci_high),
                "max_lateral_delta_ci_high": float(max_lateral_delta_ci_high),
                "min_hard_nonworse_rate": float(min_hard_nonworse_rate),
            },
            "rule_definition": (
                "For each dense lane-change loose-supported target record, "
                "compute the loose-minus-current contribution margin over the "
                "predeclared protective atoms. Preserve current CAMP when this "
                "margin is greater than threshold; otherwise take the loose "
                "supported non-Top1 candidate. All other records preserve "
                "current CAMP."
            ),
            "math_boundary": (
                "This is a deterministic finite-candidate offline screen over "
                "fixed current-tick constants. It does not alter DP, CAMP atoms, "
                "CAMP weights, or the affine score a_k^T w. If promoted later, "
                "the runtime score remains affine and the simplex/CVaR/L2 "
                "robust master remains convex. This is not classical Benders "
                "decomposition because no DP-side master/subproblem, dual, or "
                "valid cuts are constructed."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, rows, formal_seed_records),
        "threshold_grid": threshold_reports,
        "ranked_thresholds": _rank_thresholds(threshold_reports),
        "final_decision": _decision(threshold_reports),
    }


def _row(
    record: dict[str, Any],
    choice: dict[str, Any],
    *,
    protective_atoms: tuple[str, ...],
) -> dict[str, Any]:
    selected = int(record["selected"])
    loose = int(choice["chosen"])
    protective_margin = _protective_margin(record, selected, loose, protective_atoms)
    return {
        "dense_lane_change": _is_dense_lane_change(record),
        "target_record": bool(choice["target_record"]),
        "supported_target": bool(choice["support"]),
        "selected": selected,
        "loose": loose,
        "all_infeasible": not bool(np.asarray(record["feasible"], dtype=bool).any()),
        "schema_available": bool(record["score_schema_available"]),
        "protective_margin": protective_margin,
        "protective_margin_available": protective_margin is not None,
    }


def _threshold_report(
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    threshold: float,
    *,
    bootstrap_resamples: int,
    seed: int,
    min_changed_supported_rate: float,
    min_progress_delta_ci_low: float,
    max_jerk_delta_ci_high: float,
    max_lateral_delta_ci_high: float,
    min_hard_nonworse_rate: float,
) -> dict[str, Any]:
    selected = np.asarray([row["selected"] for row in rows], dtype=np.int64)
    chosen = np.asarray(
        [_chosen_for_threshold(row, threshold) for row in rows],
        dtype=np.int64,
    )
    dense_mask = np.asarray([row["dense_lane_change"] for row in rows], dtype=bool)
    supported_mask = np.asarray([row["supported_target"] for row in rows], dtype=bool)
    changed_mask = chosen != selected
    dense_metrics = _metrics(
        _subset(records, dense_mask),
        chosen[dense_mask],
        selected[dense_mask],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    supported_metrics = _metrics(
        _subset(records, supported_mask),
        chosen[supported_mask],
        selected[supported_mask],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    changed_supported_rate = _rate(
        int(np.logical_and(changed_mask, supported_mask).sum()),
        int(supported_mask.sum()),
    )
    fallback_changed = int(
        sum(row["all_infeasible"] and bool(changed) for row, changed in zip(rows, changed_mask))
    )
    failures = _gate_failures(
        changed_supported_rate=changed_supported_rate,
        fallback_changed_records=fallback_changed,
        schema_missing_records=int(sum(not row["schema_available"] for row in rows)),
        dense_metrics=dense_metrics,
        supported_metrics=supported_metrics,
        min_changed_supported_rate=min_changed_supported_rate,
        min_progress_delta_ci_low=min_progress_delta_ci_low,
        max_jerk_delta_ci_high=max_jerk_delta_ci_high,
        max_lateral_delta_ci_high=max_lateral_delta_ci_high,
        min_hard_nonworse_rate=min_hard_nonworse_rate,
    )
    return {
        "threshold": float(threshold),
        "passed": not failures,
        "failures": failures,
        "changed_records": int(changed_mask.sum()),
        "changed_rate": _rate(int(changed_mask.sum()), len(rows)),
        "changed_supported_records": int(np.logical_and(changed_mask, supported_mask).sum()),
        "changed_supported_rate": changed_supported_rate,
        "fallback_changed_records": fallback_changed,
        "preserved_by_positive_protective_margin": int(
            sum(
                row["supported_target"]
                and row["protective_margin"] is not None
                and float(row["protective_margin"]) > threshold + EPS
                for row in rows
            )
        ),
        "missing_protective_margin_records": int(
            sum(row["supported_target"] and row["protective_margin"] is None for row in rows)
        ),
        "dense_lane_change": dense_metrics,
        "supported_target": supported_metrics,
    }


def _chosen_for_threshold(row: dict[str, Any], threshold: float) -> int:
    if not row["supported_target"]:
        return int(row["selected"])
    margin = row["protective_margin"]
    if margin is None:
        return int(row["selected"])
    if float(margin) > threshold + EPS:
        return int(row["selected"])
    return int(row["loose"])


def _protective_margin(
    record: dict[str, Any],
    selected: int,
    candidate: int,
    protective_atoms: tuple[str, ...],
) -> float | None:
    if not record["score_schema_available"]:
        return None
    names = list(record["score_atom_names"])
    missing = [atom for atom in protective_atoms if atom not in names]
    if missing:
        return None
    contributions = np.asarray(record["score_contributions"], dtype=np.float64)
    indices = [names.index(atom) for atom in protective_atoms]
    margin = contributions[int(candidate), indices] - contributions[int(selected), indices]
    return float(np.sum(margin))


def _metrics(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    if not records:
        empty = _empty_summary()
        return {
            "records": 0,
            "safety_cost_delta_vs_current": empty,
            "progress_delta_vs_current": empty,
            "mean_jerk_delta_vs_current": empty,
            "mean_lateral_delta_vs_current": empty,
            "hard_nonworse_vs_current": None,
            "hard_component_nonworse_vs_current": {},
        }
    safety = []
    progress = []
    jerk = []
    lateral = []
    hard_rows = []
    component_rows = {field: [] for field in BOOL_FIELDS}
    for record, chosen_idx, selected_idx in zip(records, chosen, selected):
        c_idx = int(chosen_idx)
        s_idx = int(selected_idx)
        chosen_outcome = record["outcomes"][c_idx]
        selected_outcome = record["outcomes"][s_idx]
        safety.append(float(record["safety_cost"][c_idx] - record["safety_cost"][s_idx]))
        progress.append(
            float(record["outcome_progress"][c_idx] - record["outcome_progress"][s_idx])
        )
        jerk.append(_outcome_float(chosen_outcome, "mean_jerk_mps3") - _outcome_float(selected_outcome, "mean_jerk_mps3"))
        lateral.append(
            _outcome_float(chosen_outcome, "mean_lateral_acceleration_mps2")
            - _outcome_float(selected_outcome, "mean_lateral_acceleration_mps2")
        )
        component_nonworse = []
        for field in BOOL_FIELDS:
            nonworse = float(bool(chosen_outcome[field])) <= float(bool(selected_outcome[field]))
            component_rows[field].append(nonworse)
            component_nonworse.append(nonworse)
        hard_rows.append(all(component_nonworse))
    return {
        "records": len(records),
        "safety_cost_delta_vs_current": _paired_summary(
            safety,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "mean_jerk_delta_vs_current": _paired_summary(
            jerk,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "mean_lateral_delta_vs_current": _paired_summary(
            lateral,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": float(np.mean(hard_rows)),
        "hard_component_nonworse_vs_current": {
            field: float(np.mean(values)) for field, values in component_rows.items()
        },
    }


def _gate_failures(
    *,
    changed_supported_rate: float | None,
    fallback_changed_records: int,
    schema_missing_records: int,
    dense_metrics: dict[str, Any],
    supported_metrics: dict[str, Any],
    min_changed_supported_rate: float,
    min_progress_delta_ci_low: float,
    max_jerk_delta_ci_high: float,
    max_lateral_delta_ci_high: float,
    min_hard_nonworse_rate: float,
) -> list[str]:
    failures = []
    if schema_missing_records:
        failures.append("score_schema_missing")
    if changed_supported_rate is None or changed_supported_rate < min_changed_supported_rate:
        failures.append("insufficient_changed_supported_rate")
    if fallback_changed_records:
        failures.append("fallback_branch_changed")
    for prefix, metrics in (
        ("dense", dense_metrics),
        ("supported", supported_metrics),
    ):
        safety = metrics["safety_cost_delta_vs_current"]
        if safety["ci95_high"] is None or safety["ci95_high"] >= 0.0:
            failures.append(f"{prefix}_safety_vs_current_not_proven")
        progress = metrics["progress_delta_vs_current"]
        if progress["ci95_low"] is None or progress["ci95_low"] < min_progress_delta_ci_low:
            failures.append(f"{prefix}_progress_regression")
        jerk = metrics["mean_jerk_delta_vs_current"]
        if jerk["ci95_high"] is None or jerk["ci95_high"] > max_jerk_delta_ci_high:
            failures.append(f"{prefix}_jerk_regression")
        lateral = metrics["mean_lateral_delta_vs_current"]
        if (
            lateral["ci95_high"] is None
            or lateral["ci95_high"] > max_lateral_delta_ci_high
        ):
            failures.append(f"{prefix}_lateral_regression")
        hard_rate = metrics["hard_nonworse_vs_current"]
        if hard_rate is None or hard_rate < min_hard_nonworse_rate:
            failures.append(f"{prefix}_hard_components_worse")
    return failures


def _record_summary(
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    formal_seed_records: int,
) -> dict[str, Any]:
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": formal_seed_records,
        "dense_lane_change_records": int(sum(row["dense_lane_change"] for row in rows)),
        "target_records": int(sum(row["target_record"] for row in rows)),
        "supported_target_records": int(sum(row["supported_target"] for row in rows)),
        "schema_records": int(sum(row["schema_available"] for row in rows)),
        "missing_schema_records": int(sum(not row["schema_available"] for row in rows)),
        "protective_margin_available_records": int(
            sum(row["protective_margin_available"] for row in rows)
        ),
        "supported_positive_protective_margin_records": int(
            sum(
                row["supported_target"]
                and row["protective_margin"] is not None
                and float(row["protective_margin"]) > EPS
                for row in rows
            )
        ),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _rank_thresholds(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in reports:
        dense_safety = report["dense_lane_change"]["safety_cost_delta_vs_current"]
        supported_safety = report["supported_target"]["safety_cost_delta_vs_current"]
        rows.append(
            {
                "threshold": report["threshold"],
                "passed": report["passed"],
                "failures": len(report["failures"]),
                "changed_supported_rate": report["changed_supported_rate"],
                "dense_safety_ci95_high": dense_safety["ci95_high"],
                "supported_safety_ci95_high": supported_safety["ci95_high"],
                "dense_progress_ci95_low": report["dense_lane_change"]["progress_delta_vs_current"]["ci95_low"],
                "dense_jerk_ci95_high": report["dense_lane_change"]["mean_jerk_delta_vs_current"]["ci95_high"],
                "dense_lateral_ci95_high": report["dense_lane_change"]["mean_lateral_delta_vs_current"]["ci95_high"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed"],
            row["failures"],
            _sort_value(row["dense_safety_ci95_high"]),
            -_sort_value(row["changed_supported_rate"]),
            row["threshold"],
        ),
    )


def _decision(threshold_reports: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [report for report in threshold_reports if report["passed"]]
    status = (
        "atom_aware_offline_screen_passed"
        if passing
        else "atom_aware_offline_screen_rejected"
    )
    return {
        "status": status,
        "passing_thresholds": [report["threshold"] for report in passing],
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": bool(passing),
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "If a threshold passes, consider a small paired non-formal smoke "
            "only after implementing a default-off selector with fail-closed "
            "metadata. If all thresholds fail, reject this atom-aware finite "
            "filter route and return to schema/candidate support."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Atom-Aware No-Leak Screen",
        "",
        "This is a read-only offline screen. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Closed-loop smoke authorized: `{report['final_decision']['closed_loop_smoke_authorized']}`",
        f"- Online selector authorized: `{report['final_decision']['online_selector_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "## Rule",
        "",
        f"- Protective atoms: `{', '.join(report['analysis']['protective_atoms'])}`",
        f"- Thresholds: `{', '.join(_fmt(value) for value in report['analysis']['thresholds'])}`",
        f"- Definition: {report['analysis']['rule_definition']}",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Threshold Grid",
            "",
            "| Threshold | Pass | Failures | Changed supported | Dense safety CI high | Supported safety CI high | Dense progress CI low | Dense jerk CI high | Dense lateral CI high |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_thresholds"]:
        lines.append(
            f"| `{_fmt(row['threshold'])}` | "
            f"`{str(row['passed']).lower()}` | "
            f"`{row['failures']}` | "
            f"{_fmt(row['changed_supported_rate'])} | "
            f"{_fmt(row['dense_safety_ci95_high'])} | "
            f"{_fmt(row['supported_safety_ci95_high'])} | "
            f"{_fmt(row['dense_progress_ci95_low'])} | "
            f"{_fmt(row['dense_jerk_ci95_high'])} | "
            f"{_fmt(row['dense_lateral_ci95_high'])} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {report['final_decision']['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def _paired_summary(
    values: Any,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    arr = np.asarray(list(values), dtype=np.float64).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return _empty_summary()
    result = {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }
    if bootstrap_resamples <= 0:
        return {**result, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(seed)
    means = np.empty(int(bootstrap_resamples), dtype=np.float64)
    for idx in range(int(bootstrap_resamples)):
        sample = finite[rng.integers(0, finite.size, size=finite.size)]
        means[idx] = float(np.mean(sample))
    return {
        **result,
        "ci95_low": float(np.percentile(means, 2.5)),
        "ci95_high": float(np.percentile(means, 97.5)),
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "mean": None,
        "min": None,
        "p50": None,
        "p95": None,
        "max": None,
        "ci95_low": None,
        "ci95_high": None,
    }


def _outcome_float(outcome: dict[str, Any], field: str) -> float:
    value = float(outcome[field])
    if not np.isfinite(value):
        raise ValueError(f"Outcome field {field!r} must be finite.")
    return value


def _subset(items: list[Any], mask: np.ndarray) -> list[Any]:
    return [item for item, keep in zip(items, mask) if bool(keep)]


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _validate_thresholds(thresholds: tuple[float, ...]) -> None:
    if not thresholds:
        raise ValueError("At least one threshold is required.")
    for threshold in thresholds:
        value = float(threshold)
        if not np.isfinite(value) or value < 0.0:
            raise ValueError("threshold values must be finite and nonnegative.")


def _sort_value(value: Any) -> float:
    if value is None:
        return float("inf")
    return float(value)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "n/a"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(result):
        return "n/a"
    return f"{result:.6f}"


if __name__ == "__main__":
    main()
