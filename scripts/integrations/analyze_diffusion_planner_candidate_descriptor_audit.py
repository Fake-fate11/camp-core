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

from scripts.integrations.analyze_diffusion_planner_candidate_support_quality import (  # noqa: E402
    EPS,
    GUARDS,
    PROTECTIVE_ATOMS,
    GuardConfig,
    _current_tick_guard_mask,
    _hard_nonworse,
    _oracle_choice,
    _outcome_float,
    _outcome_nonregressing_mask,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_atom_aware_screen import (  # noqa: E402
    _protective_margin,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (  # noqa: E402
    _is_dense_lane_change,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (  # noqa: E402
    _load_records,
)


DESCRIPTOR_FIELDS = (
    "candidate_index",
    "candidate_is_top1",
    "planned_progress_delta",
    "planned_progress_loss",
    "target_speed_delta",
    "target_speed_loss",
    "tracker_jerk_delta",
    "tracker_jerk_worse",
    "tracker_lateral_delta",
    "tracker_lateral_worse",
    "dp_prior_delta",
    "dp_prior_gain",
    "score_delta",
    "protective_margin",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only descriptor audit comparing clean posterior support "
            "against current-tick guarded safety-improving candidates that "
            "regress posterior comfort. Outcomes are labels only; reported "
            "separation descriptors are current-tick finite-candidate values."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
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
    guards: tuple[GuardConfig, ...] = GUARDS,
    protective_atoms: tuple[str, ...] = PROTECTIVE_ATOMS,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    dense_records = [record for record in records if _is_dense_lane_change(record)]
    rows = _candidate_rows(
        dense_records,
        guards=guards,
        protective_atoms=protective_atoms,
    )
    clean = [row for row in rows if row["group"] == "clean_outcome_support"]
    guarded_bad = [
        row for row in rows if row["group"].endswith("_comfort_regressing")
    ]
    return {
        "analysis": {
            "name": "dp_candidate_descriptor_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "posterior outcomes define audit groups only; descriptor "
                "separation uses current-tick finite-candidate values"
            ),
            "descriptor_fields": list(DESCRIPTOR_FIELDS),
            "protective_atoms": list(protective_atoms),
            "guards": [guard.__dict__ for guard in guards],
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Reported "
                "descriptors are fixed current-tick finite-candidate quantities: "
                "planned progress, target speed, tracker jerk/lateral proxies, "
                "DP-prior deviation, logged affine score, normalized atom "
                "contribution margins, and route context. Posterior outcomes "
                "are used only to label clean support and comfort-regressing "
                "guarded candidates. CAMP score remains affine a_k^T w and the "
                "simplex/CVaR/L2 robust master remains convex. This is not "
                "classical Benders decomposition because no DP-side "
                "master/subproblem, dual, or valid cuts are constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": {
            "total_records": len(records),
            "dense_lane_change_records": len(dense_records),
            "formal_seed_records": formal_seed_records,
            "candidate_rows": len(rows),
            "clean_outcome_support_rows": len(clean),
            "guarded_comfort_regressing_rows": len(guarded_bad),
        },
        "groups": _group_reports(rows),
        "separation": _separation_report(clean, guarded_bad),
        "final_decision": _decision(clean, guarded_bad),
    }


def _candidate_rows(
    records: list[dict[str, Any]],
    *,
    guards: tuple[GuardConfig, ...],
    protective_atoms: tuple[str, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        selected = int(record["selected"])
        clean_idx = _oracle_choice(record, _outcome_nonregressing_mask(record))
        if _safety_improves(record, clean_idx, selected):
            rows.append(
                _candidate_row(
                    record,
                    clean_idx,
                    selected,
                    group="clean_outcome_support",
                    source="oracle_outcome_nonregressing",
                    protective_atoms=protective_atoms,
                )
            )
        for guard in guards:
            guarded_idx = _oracle_choice(record, _current_tick_guard_mask(record, guard))
            if not _safety_improves(record, guarded_idx, selected):
                continue
            outcome_group = (
                f"{guard.name}_comfort_regressing"
                if _comfort_regresses(record, guarded_idx, selected)
                else f"{guard.name}_comfort_clean"
            )
            rows.append(
                _candidate_row(
                    record,
                    guarded_idx,
                    selected,
                    group=outcome_group,
                    source=f"oracle_guarded_{guard.name}",
                    protective_atoms=protective_atoms,
                )
            )
    return rows


def _candidate_row(
    record: dict[str, Any],
    candidate: int,
    selected: int,
    *,
    group: str,
    source: str,
    protective_atoms: tuple[str, ...],
) -> dict[str, Any]:
    descriptors = _descriptors(record, candidate, selected, protective_atoms)
    descriptors.update(_atom_contribution_margins(record, candidate, selected))
    descriptors.update(_atom_normalized_deltas(record, candidate, selected))
    chosen_outcome = record["outcomes"][candidate]
    selected_outcome = record["outcomes"][selected]
    return {
        "group": group,
        "source": source,
        "route": record["context"].get("route"),
        "npc_count": record["context"].get("npc_count"),
        "traffic_light": record["context"].get("traffic_light"),
        "selected": int(selected),
        "candidate": int(candidate),
        "descriptors": descriptors,
        "outcome": {
            "safety_delta": float(
                record["safety_cost"][candidate] - record["safety_cost"][selected]
            ),
            "progress_delta": float(
                record["outcome_progress"][candidate]
                - record["outcome_progress"][selected]
            ),
            "jerk_delta": float(
                _outcome_float(chosen_outcome, "mean_jerk_mps3")
                - _outcome_float(selected_outcome, "mean_jerk_mps3")
            ),
            "lateral_delta": float(
                _outcome_float(chosen_outcome, "mean_lateral_acceleration_mps2")
                - _outcome_float(selected_outcome, "mean_lateral_acceleration_mps2")
            ),
            "hard_nonworse": _hard_nonworse(chosen_outcome, selected_outcome),
        },
    }


def _descriptors(
    record: dict[str, Any],
    candidate: int,
    selected: int,
    protective_atoms: tuple[str, ...],
) -> dict[str, float]:
    planned = np.asarray(record["planned_progress"], dtype=np.float64)
    speed = np.asarray(record["target_speed"], dtype=np.float64)
    tracker_jerk = np.asarray(record["tracker_jerk"], dtype=np.float64)
    tracker_lateral = np.asarray(record["tracker_lateral"], dtype=np.float64)
    dp_prior = np.asarray(record["dp_prior_deviation"], dtype=np.float64)
    scores = np.asarray(record["scores"], dtype=np.float64)
    protective = _protective_margin(record, selected, candidate, protective_atoms)
    return {
        "candidate_index": float(candidate),
        "candidate_is_top1": float(candidate == 0),
        "planned_progress_delta": float(planned[candidate] - planned[selected]),
        "planned_progress_loss": max(float(planned[selected] - planned[candidate]), 0.0),
        "target_speed_delta": float(speed[candidate] - speed[selected]),
        "target_speed_loss": max(float(speed[selected] - speed[candidate]), 0.0),
        "tracker_jerk_delta": float(tracker_jerk[candidate] - tracker_jerk[selected]),
        "tracker_jerk_worse": max(float(tracker_jerk[candidate] - tracker_jerk[selected]), 0.0),
        "tracker_lateral_delta": float(tracker_lateral[candidate] - tracker_lateral[selected]),
        "tracker_lateral_worse": max(float(tracker_lateral[candidate] - tracker_lateral[selected]), 0.0),
        "dp_prior_delta": float(dp_prior[candidate] - dp_prior[selected]),
        "dp_prior_gain": float(dp_prior[selected] - dp_prior[candidate]),
        "score_delta": float(scores[candidate] - scores[selected]),
        "protective_margin": 0.0 if protective is None else float(protective),
    }


def _atom_contribution_margins(
    record: dict[str, Any],
    candidate: int,
    selected: int,
) -> dict[str, float]:
    if not record["score_schema_available"]:
        return {}
    contributions = np.asarray(record["score_contributions"], dtype=np.float64)
    names = list(record["score_atom_names"])
    margins = contributions[candidate] - contributions[selected]
    return {
        f"atom_margin:{name}": float(value)
        for name, value in zip(names, margins)
    }


def _atom_normalized_deltas(
    record: dict[str, Any],
    candidate: int,
    selected: int,
) -> dict[str, float]:
    if not record["score_schema_available"]:
        return {}
    normalized = np.asarray(record["score_normalized_atoms"], dtype=np.float64)
    names = list(record["score_atom_names"])
    deltas = normalized[candidate] - normalized[selected]
    return {
        f"atom_norm_delta:{name}": float(value)
        for name, value in zip(names, deltas)
    }


def _group_reports(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = sorted({row["group"] for row in rows})
    return {group: _group_report([row for row in rows if row["group"] == group]) for group in groups}


def _group_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "sources": sorted({str(row["source"]) for row in rows}),
        "outcome": {
            "safety_delta": _summary(row["outcome"]["safety_delta"] for row in rows),
            "progress_delta": _summary(row["outcome"]["progress_delta"] for row in rows),
            "jerk_delta": _summary(row["outcome"]["jerk_delta"] for row in rows),
            "lateral_delta": _summary(row["outcome"]["lateral_delta"] for row in rows),
            "hard_nonworse_rate": _rate(row["outcome"]["hard_nonworse"] for row in rows),
        },
        "descriptors": {
            field: _summary(row["descriptors"].get(field) for row in rows)
            for field in _descriptor_names(rows)
        },
    }


def _separation_report(
    clean: list[dict[str, Any]],
    guarded_bad: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = _descriptor_names([*clean, *guarded_bad])
    rows = []
    for field in fields:
        clean_values = _values(clean, field)
        bad_values = _values(guarded_bad, field)
        clean_mean = _mean(clean_values)
        bad_mean = _mean(bad_values)
        rows.append(
            {
                "descriptor": field,
                "clean_records": len(clean_values),
                "guarded_comfort_regressing_records": len(bad_values),
                "clean_mean": clean_mean,
                "guarded_comfort_regressing_mean": bad_mean,
                "clean_minus_guarded": (
                    None if clean_mean is None or bad_mean is None else clean_mean - bad_mean
                ),
                "standardized_abs_difference": _standardized_abs_difference(
                    clean_values,
                    bad_values,
                ),
            }
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            -float(row["standardized_abs_difference"] or 0.0),
            row["descriptor"],
        ),
    )
    return {
        "clean_records": len(clean),
        "guarded_comfort_regressing_records": len(guarded_bad),
        "top_descriptors": ranked[:24],
        "all_descriptors": ranked,
    }


def _decision(
    clean: list[dict[str, Any]],
    guarded_bad: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons = []
    if clean:
        reasons.append("clean_posterior_support_present")
    if guarded_bad:
        reasons.append("guarded_safety_support_comfort_regression_present")
    status = (
        "descriptor_audit_complete"
        if clean and guarded_bad
        else "descriptor_audit_inconclusive"
    )
    return {
        "status": status,
        "reasons": reasons,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "Inspect whether the ranked current-tick descriptors separate clean "
            "posterior support from comfort-regressing guarded support. If no "
            "predeclared no-leak descriptor can be turned into an offline proof "
            "that beats current CAMP without comfort regression, reject fixed-DP "
            "selector calibration and move to candidate/postprocess support."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP Candidate Descriptor Separation Audit",
        "",
        "This is a read-only offline diagnostic. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Online selector authorized: `{report['final_decision']['online_selector_authorized']}`",
        f"- Closed-loop smoke authorized: `{report['final_decision']['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "Reasons:",
    ]
    for reason in report["final_decision"]["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(["", "## Records", "", "| Metric | Value |", "| --- | ---: |"])
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Groups",
            "",
            "| Group | Records | Safety mean | Progress mean | Jerk mean | Lateral mean | Hard nonworse |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group, data in report["groups"].items():
        outcome = data["outcome"]
        lines.append(
            f"| `{group}` | {data['records']} | "
            f"{_fmt(outcome['safety_delta']['mean'])} | "
            f"{_fmt(outcome['progress_delta']['mean'])} | "
            f"{_fmt(outcome['jerk_delta']['mean'])} | "
            f"{_fmt(outcome['lateral_delta']['mean'])} | "
            f"{_fmt(outcome['hard_nonworse_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Top Current-Tick Descriptor Separators",
            "",
            "| Descriptor | Clean mean | Comfort-regressing guarded mean | Clean - guarded | Std abs diff |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["separation"]["top_descriptors"][:16]:
        lines.append(
            f"| `{row['descriptor']}` | "
            f"{_fmt(row['clean_mean'])} | "
            f"{_fmt(row['guarded_comfort_regressing_mean'])} | "
            f"{_fmt(row['clean_minus_guarded'])} | "
            f"{_fmt(row['standardized_abs_difference'])} |"
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


def _safety_improves(record: dict[str, Any], candidate: int, selected: int) -> bool:
    return bool(
        int(candidate) != int(selected)
        and float(record["safety_cost"][candidate] - record["safety_cost"][selected]) < -EPS
    )


def _comfort_regresses(record: dict[str, Any], candidate: int, selected: int) -> bool:
    chosen = record["outcomes"][int(candidate)]
    current = record["outcomes"][int(selected)]
    return bool(
        _outcome_float(chosen, "mean_jerk_mps3")
        > _outcome_float(current, "mean_jerk_mps3") + EPS
        or _outcome_float(chosen, "mean_lateral_acceleration_mps2")
        > _outcome_float(current, "mean_lateral_acceleration_mps2") + EPS
    )


def _descriptor_names(rows: list[dict[str, Any]]) -> list[str]:
    names = set(DESCRIPTOR_FIELDS)
    for row in rows:
        names.update(row["descriptors"].keys())
    return sorted(names)


def _values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values = []
    for row in rows:
        value = row["descriptors"].get(field)
        if value is None:
            continue
        result = float(value)
        if np.isfinite(result):
            values.append(result)
    return values


def _summary(values: Any) -> dict[str, Any]:
    arr = np.asarray(
        [value for value in values if value is not None],
        dtype=np.float64,
    ).reshape(-1)
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


def _rate(values: Any) -> float | None:
    rows = [bool(value) for value in values]
    if not rows:
        return None
    return float(np.mean(rows))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _standardized_abs_difference(
    left: list[float],
    right: list[float],
) -> float | None:
    if not left or not right:
        return None
    left_arr = np.asarray(left, dtype=np.float64)
    right_arr = np.asarray(right, dtype=np.float64)
    pooled = np.sqrt(0.5 * (np.var(left_arr) + np.var(right_arr)))
    return float(abs(np.mean(left_arr) - np.mean(right_arr)) / max(pooled, 1e-12))


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(result):
        return "n/a"
    return f"{result:.6f}"


if __name__ == "__main__":
    main()
