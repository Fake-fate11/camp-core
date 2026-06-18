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
    parse_selection_log_metadata,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_WEIGHTS,
)


ALPHAS = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4)
BOOL_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for a DP-prior-deviation CAMP atom candidate. "
            "The audit appends a virtual normalized atom to logged finite "
            "candidate scores and evaluates it with existing outcome labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--alpha", type=float, action="append", default=[])
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
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
        label=args.label,
        scale_percentile=args.scale_percentile,
        alphas=tuple(args.alpha) if args.alpha else ALPHAS,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
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
    scale_percentile: float = 95.0,
    alphas: tuple[float, ...] = ALPHAS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
) -> dict[str, Any]:
    if not 0.0 < scale_percentile < 100.0:
        raise ValueError("scale_percentile must be in (0, 100).")
    if not alphas:
        raise ValueError("At least one alpha is required.")
    for alpha in alphas:
        if not 0.0 <= float(alpha) < 1.0:
            raise ValueError("Every alpha must be in [0, 1).")
    records = _load_records(paths)
    if not records:
        raise ValueError("No outcome-labeled records with DP-prior deviation were found.")
    scale = _robust_positive_scale(
        np.concatenate([record["dp_prior_deviation"] for record in records]),
        scale_percentile,
    )
    alpha_reports = [
        _alpha_report(
            records,
            float(alpha),
            scale=scale,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        for alpha in alphas
    ]
    return {
        "analysis": {
            "name": "dp_prior_deviation_atom_candidate_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes evaluate the virtual atom only; the atom "
                "itself is a fixed current-tick candidate diagnostic"
            ),
            "candidate_atom": {
                "name": "dp_prior_deviation_cost",
                "definition": (
                    "mean_t ||xy_candidate(t) - xy_DPTop1(t)||_2^2 over the "
                    "logged DP candidate horizon"
                ),
                "nonnegative": True,
                "candidate0_value": 0.0,
                "scale_percentile": float(scale_percentile),
                "scale": float(scale),
            },
            "virtual_score": (
                "score_alpha(k) = (1-alpha) * logged_selection_score(k) + "
                "alpha * clip(dp_prior_deviation_cost(k) / scale)"
            ),
            "math_boundary": (
                "For a fixed DP candidate set, dp_prior_deviation_cost is a "
                "fixed nonnegative coefficient. Appending it to the CAMP atom "
                "vector preserves affine scores a_k^T w and the simplex/CVaR/L2 "
                "convex master. This audit does not construct a Benders "
                "subproblem, dual, or cut, and it does not claim global "
                "convexity over DP trajectory generation."
            ),
            "alphas": [float(alpha) for alpha in alphas],
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
        },
        "records": _record_summary(records),
        "selected_vs_top1": _selected_vs_top1(records),
        "alphas": alpha_reports,
        "ranked_candidates": _rank(alpha_reports),
    }


def _load_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in iter_selection_log_paths(paths):
        metadata = parse_selection_log_metadata(log_path)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_index, raw in enumerate(payload):
            try:
                record = _load_record(raw, f"{log_path} record {record_index}")
            except ValueError as exc:
                if "candidate_closed_loop_outcomes" in str(exc):
                    continue
                raise
            record["context"] = {
                "log_path": str(log_path),
                "record_index": int(record_index),
                "route": metadata.route,
                "seed": metadata.seed,
                "npc_count": metadata.npc_count,
                "traffic_light": metadata.traffic_light,
                "mode": metadata.mode,
            }
            records.append(record)
    return records


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} requires complete candidate_closed_loop_outcomes.")
    dp_prior = _vector(
        raw.get("candidate_dp_prior_deviation_cost"),
        candidate_count,
        f"{label} candidate_dp_prior_deviation_cost",
    )
    if abs(float(dp_prior[0])) > 1e-9:
        raise ValueError(f"{label} DP-prior deviation atom must be zero for candidate0.")
    scores = _vector(
        raw.get("selection_scores"),
        candidate_count,
        f"{label} selection_scores",
        allow_positive_infinity=True,
    )
    feasible = np.asarray(raw.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        raise ValueError(f"{label} feasible_mask must have shape [{candidate_count}].")
    costs = np.asarray(
        [_candidate_safety_cost(outcome, raw, idx) for idx, outcome in enumerate(outcomes)],
        dtype=np.float64,
    )
    progress = np.asarray(
        [_nonnegative_float(outcome, "progress_m") for outcome in outcomes],
        dtype=np.float64,
    )
    return {
        "selected": selected,
        "candidate_count": candidate_count,
        "feasible": feasible,
        "scores": scores,
        "dp_prior_deviation": dp_prior,
        "safety_cost": costs,
        "progress": progress,
        "outcomes": outcomes,
    }


def _candidate_safety_cost(outcome: dict[str, Any], record: dict[str, Any], index: int) -> float:
    progress = np.asarray(
        [
            _nonnegative_float(item, "progress_m")
            for item in record["candidate_closed_loop_outcomes"]
        ],
        dtype=np.float64,
    )
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    branch_feasible = feasible if feasible.any() else np.ones_like(feasible, dtype=bool)
    progress_ref = float(np.max(progress[branch_feasible])) if branch_feasible.any() else float(np.max(progress))
    progress_denom = max(progress_ref, 1.0)
    planned_red = _planned_red_values(record, len(progress))
    components = {
        "collision": float(bool(outcome["collision"])),
        "near_miss": float(bool(outcome["near_miss"])),
        "lane_violation": float(bool(outcome["lane_violation"])),
        "realized_red_light": float(bool(outcome["red_light_violation"])),
        "planned_red_light": min(max(float(planned_red[index]), 0.0), 1.0),
        "mean_jerk": min(
            _nonnegative_float(outcome, "mean_jerk_mps3")
            / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
            SAFETY_COST_V1_CLIP,
        ),
        "mean_lateral_acceleration": min(
            _nonnegative_float(outcome, "mean_lateral_acceleration_mps2")
            / SAFETY_COST_V1_NORMALIZATION["mean_lateral_acceleration_mps2"],
            SAFETY_COST_V1_CLIP,
        ),
        "route_shortfall": min(
            max((progress_ref - _nonnegative_float(outcome, "progress_m")) / progress_denom, 0.0),
            1.0,
        ),
    }
    return float(
        sum(
            float(components[key]) * float(SAFETY_COST_V1_WEIGHTS[key])
            for key in components
        )
    )


def _alpha_report(
    records: list[dict[str, Any]],
    alpha: float,
    *,
    scale: float,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    chosen = np.asarray(
        [_select_with_alpha(record, alpha, scale) for record in records],
        dtype=np.int64,
    )
    costs = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    progress = np.asarray([record["progress"] for record in records], dtype=np.float64)
    current_cost = costs[np.arange(len(records)), selected]
    top1_cost = costs[:, 0]
    chosen_cost = costs[np.arange(len(records)), chosen]
    current_progress = progress[np.arange(len(records)), selected]
    chosen_progress = progress[np.arange(len(records)), chosen]
    top1_progress = progress[:, 0]
    harmful_current = (current_cost - top1_cost) > EPS
    beneficial_current = (top1_cost - current_cost) > EPS
    return {
        "alpha": float(alpha),
        "changed_from_current_rate": float(np.mean(chosen != selected)),
        "top1_selected_rate": float(np.mean(chosen == top1)),
        "harmful_current_records": int(np.sum(harmful_current)),
        "harmful_current_changed_rate": _conditional_rate(chosen != selected, harmful_current),
        "beneficial_current_records": int(np.sum(beneficial_current)),
        "beneficial_current_preserved_rate": _conditional_rate(chosen == selected, beneficial_current),
        "safety_cost_delta_vs_current": _paired_summary(
            chosen_cost - current_cost,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "safety_cost_delta_vs_top1": _paired_summary(
            chosen_cost - top1_cost,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            chosen_progress - current_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_top1": _paired_summary(
            chosen_progress - top1_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": _hard_nonworse_rate(records, chosen, selected),
        "hard_nonworse_vs_top1": _hard_nonworse_rate(records, chosen, top1),
        "dp_prior_deviation_selected": _summary(
            [record["dp_prior_deviation"][idx] for record, idx in zip(records, chosen)]
        ),
    }


def _select_with_alpha(record: dict[str, Any], alpha: float, scale: float) -> int:
    if float(alpha) == 0.0:
        return int(record["selected"])
    scores = np.asarray(record["scores"], dtype=np.float64)
    prior = np.clip(record["dp_prior_deviation"] / float(scale), 0.0, 10.0)
    mixed = (1.0 - float(alpha)) * scores + float(alpha) * prior
    return int(np.argmin(mixed))


def _record_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_counts = sorted({record["candidate_count"] for record in records})
    return {
        "logs": len({record["context"]["log_path"] for record in records}),
        "total": len(records),
        "candidates": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": candidate_counts,
        "selected_non_top1_rate": float(
            np.mean([record["selected"] != 0 for record in records])
        ),
    }


def _selected_vs_top1(records: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = []
    prior_deltas = []
    harmful_with_prior = 0
    beneficial_with_prior = 0
    for record in records:
        selected = int(record["selected"])
        cost_delta = float(record["safety_cost"][selected] - record["safety_cost"][0])
        prior_delta = float(record["dp_prior_deviation"][selected] - record["dp_prior_deviation"][0])
        deltas.append(cost_delta)
        prior_deltas.append(prior_delta)
        harmful_with_prior += int(cost_delta > EPS and prior_delta > EPS)
        beneficial_with_prior += int(cost_delta < -EPS and prior_delta > EPS)
    return {
        "safety_cost_selected_minus_top1": _summary(deltas),
        "dp_prior_selected_minus_top1": _summary(prior_deltas),
        "harmful_selected_with_positive_prior_delta": harmful_with_prior,
        "beneficial_selected_with_positive_prior_delta": beneficial_with_prior,
    }


def _rank(alpha_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in alpha_reports:
        safety = report["safety_cost_delta_vs_current"]
        rows.append(
            {
                "alpha": report["alpha"],
                "passed_atom_screen": bool(
                    safety["ci95_high"] is not None
                    and safety["ci95_high"] < 0.0
                    and report["hard_nonworse_vs_current"] >= 0.99
                    and report["beneficial_current_preserved_rate"] >= 0.8
                ),
                "safety_delta_mean": safety["mean"],
                "safety_delta_ci95_high": safety["ci95_high"],
                "changed_from_current_rate": report["changed_from_current_rate"],
                "top1_selected_rate": report["top1_selected_rate"],
                "beneficial_current_preserved_rate": report["beneficial_current_preserved_rate"],
                "hard_nonworse_vs_current": report["hard_nonworse_vs_current"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed_atom_screen"],
            float(row["safety_delta_ci95_high"] or 0.0),
            float(row["changed_from_current_rate"]),
        ),
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-Prior Deviation Atom Candidate Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Candidate Atom",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    atom = report["analysis"]["candidate_atom"]
    for key in ("name", "definition", "nonnegative", "candidate0_value", "scale"):
        lines.append(f"| `{key}` | `{atom[key]}` |")
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Selected vs Top-1",
            "",
            "| Metric | Mean | CI/Extra |",
            "| --- | ---: | ---: |",
        ]
    )
    selected = report["selected_vs_top1"]
    lines.append(
        "| `safety_cost_selected_minus_top1` | "
        f"{_fmt(selected['safety_cost_selected_minus_top1']['mean'])} | "
        f"p95 {_fmt(selected['safety_cost_selected_minus_top1']['p95'])} |"
    )
    lines.append(
        "| `dp_prior_selected_minus_top1` | "
        f"{_fmt(selected['dp_prior_selected_minus_top1']['mean'])} | "
        f"p95 {_fmt(selected['dp_prior_selected_minus_top1']['p95'])} |"
    )
    lines.append(
        "| `harmful_selected_with_positive_prior_delta` | "
        f"`{selected['harmful_selected_with_positive_prior_delta']}` | |"
    )
    lines.append(
        "| `beneficial_selected_with_positive_prior_delta` | "
        f"`{selected['beneficial_selected_with_positive_prior_delta']}` | |"
    )
    lines.extend(
        [
            "",
            "## Ranked Alpha Candidates",
            "",
            "| Alpha | Pass | Safety Mean | Safety CI High | Changed | Top1 Rate | Beneficial Preserved | Hard Nonworse |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_candidates"]:
        lines.append(
            "| "
            f"{_fmt(row['alpha'])} | `{row['passed_atom_screen']}` | "
            f"{_fmt(row['safety_delta_mean'])} | "
            f"{_fmt(row['safety_delta_ci95_high'])} | "
            f"{_fmt(row['changed_from_current_rate'])} | "
            f"{_fmt(row['top1_selected_rate'])} | "
            f"{_fmt(row['beneficial_current_preserved_rate'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} |"
        )
    lines.extend(
        [
            "",
            "## Alpha Details",
            "",
            "| Alpha | Safety vs Current | Safety CI | Progress vs Current | Hard Nonworse | Harmful Changed | Beneficial Preserved |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["alphas"]:
        safety = row["safety_cost_delta_vs_current"]
        progress = row["progress_delta_vs_current"]
        lines.append(
            "| "
            f"{_fmt(row['alpha'])} | "
            f"{_fmt(safety['mean'])} | "
            f"[{_fmt(safety['ci95_low'])}, {_fmt(safety['ci95_high'])}] | "
            f"{_fmt(progress['mean'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} | "
            f"{_fmt(row['harmful_current_changed_rate'])} | "
            f"{_fmt(row['beneficial_current_preserved_rate'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def _paired_summary(
    values: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    summary = _summary(arr)
    if arr.size == 0 or bootstrap_resamples <= 0:
        return {**summary, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(seed)
    means = np.empty(int(bootstrap_resamples), dtype=np.float64)
    for idx in range(int(bootstrap_resamples)):
        sample = arr[rng.integers(0, arr.size, size=arr.size)]
        means[idx] = float(np.mean(sample))
    return {
        **summary,
        "ci95_low": float(np.percentile(means, 2.5)),
        "ci95_high": float(np.percentile(means, 97.5)),
    }


def _hard_nonworse_rate(records: list[dict[str, Any]], chosen: np.ndarray, reference: np.ndarray) -> float:
    rows = []
    for record, chosen_idx, reference_idx in zip(records, chosen, reference):
        chosen_outcome = record["outcomes"][int(chosen_idx)]
        reference_outcome = record["outcomes"][int(reference_idx)]
        rows.append(
            all(
                float(bool(chosen_outcome[field])) <= float(bool(reference_outcome[field]))
                for field in BOOL_FIELDS
            )
        )
    return float(np.mean(rows)) if rows else 0.0


def _planned_red_values(record: dict[str, Any], size: int) -> np.ndarray:
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
    ):
        values = record.get(key)
        if values is None:
            continue
        vector = np.asarray(values, dtype=np.float64).reshape(-1)
        if vector.shape != (size,):
            raise ValueError(f"{key} must have shape [{size}].")
        if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
            raise ValueError(f"{key} must contain finite nonnegative values.")
        return vector
    return np.zeros(size, dtype=np.float64)


def _nonnegative_float(outcome: dict[str, Any], field: str) -> float:
    value = float(outcome[field])
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Candidate outcome {field!r} must be finite and nonnegative.")
    return value


def _vector(
    value: Any,
    size: int,
    label: str,
    *,
    allow_positive_infinity: bool = False,
) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}], got {arr.shape}.")
    if allow_positive_infinity:
        valid = np.isfinite(arr) | np.isposinf(arr)
    else:
        valid = np.isfinite(arr)
    if not np.all(valid):
        raise ValueError(f"{label} must contain finite values.")
    return arr


def _robust_positive_scale(values: np.ndarray, percentile: float) -> float:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    positive = arr[np.isfinite(arr) & (arr > 1e-12)]
    if positive.size == 0:
        return 1.0
    return max(float(np.percentile(positive, percentile)), 1e-6)


def _conditional_rate(values: np.ndarray, mask: np.ndarray) -> float:
    mask = np.asarray(mask, dtype=bool).reshape(-1)
    if not mask.any():
        return 1.0
    return float(np.mean(np.asarray(values, dtype=bool).reshape(-1)[mask]))


def _summary(values: Any) -> dict[str, Any]:
    arr = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=np.float64).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"n": 0, "mean": None, "min": None, "p50": None, "p95": None, "max": None}
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not np.isfinite(result):
        return "n/a"
    return f"`{result:.6g}`"


if __name__ == "__main__":
    main()
