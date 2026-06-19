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
    atom_names_for_dimension,
    iter_selection_log_paths,
    parse_selection_log_metadata,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (  # noqa: E402
    FORMAL_SEEDS,
    LooseRuleConfig,
    _choice,
    _is_dense_lane_change,
    _load_record as _load_outcome_record,
)


EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only score-schema calibration diagnostic for dense lane-change "
            "records. It explains current CAMP score contributions on supported "
            "non-Top1 alternatives; candidate outcomes are posterior labels only."
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


def _load_records(
    paths: list[Path],
    *,
    fail_on_formal_seeds: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in iter_selection_log_paths(paths):
        metadata = parse_selection_log_metadata(log_path)
        formal_seed = metadata.seed in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
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
                "formal_seed": formal_seed,
                "npc_count": metadata.npc_count,
                "traffic_light": metadata.traffic_light,
                "mode": metadata.mode,
            }
            records.append(record)
    return records


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    record = _load_outcome_record(raw, label)
    record.update(_score_schema_fields(raw, int(record["candidate_count"]), label))
    return record


def _score_schema_fields(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any]:
    normalized = _optional_matrix(
        raw,
        candidate_count,
        label,
        ("selection_normalized_atoms", "normalized_atoms"),
    )
    weights = _optional_vector(raw, label, ("selection_weights", "weights"))
    if normalized is None or weights is None:
        return {
            "score_schema_available": False,
            "score_schema_reason": "missing_normalized_atoms_or_weights",
            "score_atom_names": [],
            "score_normalized_atoms": None,
            "score_weights": None,
            "score_contributions": None,
            "score_reconstructed": None,
            "score_reconstruction_abs_errors": np.asarray([], dtype=np.float64),
        }
    if normalized.shape[1] != weights.shape[0]:
        raise ValueError(
            f"{label} normalized atom dimension {normalized.shape[1]} does not "
            f"match weights dimension {weights.shape[0]}."
        )
    names = _atom_names(raw, normalized.shape[1], label)
    scores = np.asarray(raw.get("selection_scores"), dtype=np.float64).reshape(-1)
    if scores.shape != (candidate_count,):
        raise ValueError(f"{label} selection_scores must have shape [{candidate_count}].")
    reconstructed = normalized @ weights
    finite_score = np.isfinite(scores)
    errors = np.abs(reconstructed[finite_score] - scores[finite_score])
    return {
        "score_schema_available": True,
        "score_schema_reason": "available",
        "score_atom_names": names,
        "score_normalized_atoms": normalized,
        "score_weights": weights,
        "score_contributions": normalized * weights.reshape(1, -1),
        "score_reconstructed": reconstructed,
        "score_reconstruction_abs_errors": errors,
    }


def analyze_records(
    records: list[dict[str, Any]],
    *,
    label: str | None = None,
    config: LooseRuleConfig = LooseRuleConfig(),
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    choices = [_choice(record, config) for record in records]
    rows = [_row(record, choice) for record, choice in zip(records, choices)]
    supported = [row for row in rows if row["supported_target"]]
    camp_advantage = [row for row in supported if row["camp_advantage_record"]]
    loose_hurts = [row for row in supported if row["loose_regresses_current_safety"]]
    loose_helps = [row for row in supported if row["loose_improves_current_safety"]]
    return {
        "analysis": {
            "name": "dense_lane_change_score_schema_calibration_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "candidate outcomes are used only for posterior grouping; "
                "score schema descriptors are current-tick finite-candidate "
                "atoms, normalized atoms, logged weights, and logged scores"
            ),
            "loose_rule": config.__dict__,
            "math_boundary": (
                "This diagnostic does not change DP, CAMP atoms, CAMP weights, "
                "or selector behavior. It explains the logged affine score "
                "a_k^T w using fixed current-tick finite-candidate quantities. "
                "The simplex/CVaR/L2 robust master remains convex. This is not "
                "classical Benders decomposition because no DP-side "
                "master/subproblem, dual, or valid cuts are constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, rows, formal_seed_records),
        "score_schema": _score_schema_summary(records, rows),
        "groups": {
            "supported_target": _group_report(supported),
            "camp_advantage": _group_report(camp_advantage),
            "loose_hurts_current": _group_report(loose_hurts),
            "loose_helps_current": _group_report(loose_helps),
        },
        "atom_contribution_separation": _atom_contribution_separation(
            supported,
            camp_advantage,
            loose_hurts,
            loose_helps,
        ),
        "final_decision": _decision(records, supported, camp_advantage, loose_hurts),
    }


def _row(record: dict[str, Any], choice: dict[str, Any]) -> dict[str, Any]:
    selected = int(record["selected"])
    loose = int(choice["chosen"])
    top1 = 0
    current_cost = float(record["safety_cost"][selected])
    loose_cost = float(record["safety_cost"][loose])
    top1_cost = float(record["safety_cost"][top1])
    current_progress = float(record["outcome_progress"][selected])
    loose_progress = float(record["outcome_progress"][loose])
    schema = _score_schema_row(record, selected, loose)
    return {
        "dense_lane_change": _is_dense_lane_change(record),
        "target_record": bool(choice["target_record"]),
        "supported_target": bool(choice["support"]),
        "selected": selected,
        "loose": loose,
        "top1": top1,
        "score_schema_available": bool(record["score_schema_available"]),
        "score_penalty": max(float(record["scores"][loose] - record["scores"][selected]), 0.0),
        "score_delta_loose_minus_current": float(
            record["scores"][loose] - record["scores"][selected]
        ),
        "safety_loose_minus_current": loose_cost - current_cost,
        "safety_current_minus_top1": current_cost - top1_cost,
        "progress_loose_minus_current": loose_progress - current_progress,
        "camp_beats_top1": current_cost < top1_cost - EPS,
        "camp_beats_loose": current_cost < loose_cost - EPS,
        "camp_progress_ge_loose": current_progress >= loose_progress - EPS,
        "camp_advantage_record": bool(
            choice["support"]
            and current_cost < top1_cost - EPS
            and current_cost < loose_cost - EPS
            and current_progress >= loose_progress - EPS
        ),
        "loose_regresses_current_safety": bool(loose_cost > current_cost + EPS),
        "loose_improves_current_safety": bool(loose_cost < current_cost - EPS),
        **schema,
    }


def _score_schema_row(
    record: dict[str, Any],
    selected: int,
    loose: int,
) -> dict[str, Any]:
    if not record["score_schema_available"]:
        return {
            "contribution_margin_total": None,
            "score_delta_reconstruction_abs_error": None,
            "atom_contribution_margins": {},
            "atom_normalized_deltas": {},
        }
    contributions = np.asarray(record["score_contributions"], dtype=np.float64)
    normalized = np.asarray(record["score_normalized_atoms"], dtype=np.float64)
    margins = contributions[loose] - contributions[selected]
    normalized_deltas = normalized[loose] - normalized[selected]
    score_delta = float(record["scores"][loose] - record["scores"][selected])
    contribution_total = float(np.sum(margins))
    names = list(record["score_atom_names"])
    return {
        "contribution_margin_total": contribution_total,
        "score_delta_reconstruction_abs_error": abs(contribution_total - score_delta),
        "atom_contribution_margins": {
            name: float(value) for name, value in zip(names, margins)
        },
        "atom_normalized_deltas": {
            name: float(value) for name, value in zip(names, normalized_deltas)
        },
    }


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
        "camp_advantage_records": int(sum(row["camp_advantage_record"] for row in rows)),
        "loose_regresses_current_safety_records": int(
            sum(row["supported_target"] and row["loose_regresses_current_safety"] for row in rows)
        ),
        "loose_improves_current_safety_records": int(
            sum(row["supported_target"] and row["loose_improves_current_safety"] for row in rows)
        ),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _score_schema_summary(
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    reconstruction_errors = np.concatenate(
        [
            np.asarray(record["score_reconstruction_abs_errors"], dtype=np.float64)
            for record in records
            if record["score_schema_available"]
        ]
        or [np.asarray([], dtype=np.float64)]
    )
    delta_errors = [
        row["score_delta_reconstruction_abs_error"]
        for row in rows
        if row["score_delta_reconstruction_abs_error"] is not None
    ]
    return {
        "records_with_schema": int(
            sum(record["score_schema_available"] for record in records)
        ),
        "records_missing_schema": int(
            sum(not record["score_schema_available"] for record in records)
        ),
        "atom_dimensions": sorted(
            {
                len(record["score_atom_names"])
                for record in records
                if record["score_schema_available"]
            }
        ),
        "score_reconstruction_abs_error": _summary(reconstruction_errors),
        "selected_loose_delta_reconstruction_abs_error": _summary(delta_errors),
    }


def _group_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_rows = [row for row in rows if row["score_schema_available"]]
    return {
        "records": len(rows),
        "schema_records": len(schema_rows),
        "safety_loose_minus_current": _summary(
            row["safety_loose_minus_current"] for row in rows
        ),
        "safety_current_minus_top1": _summary(
            row["safety_current_minus_top1"] for row in rows
        ),
        "progress_loose_minus_current": _summary(
            row["progress_loose_minus_current"] for row in rows
        ),
        "score_penalty": _summary(row["score_penalty"] for row in rows),
        "score_delta_loose_minus_current": _summary(
            row["score_delta_loose_minus_current"] for row in rows
        ),
        "contribution_margin_total": _summary(
            row["contribution_margin_total"] for row in schema_rows
        ),
        "score_delta_reconstruction_abs_error": _summary(
            row["score_delta_reconstruction_abs_error"] for row in schema_rows
        ),
        "rates": {
            "camp_beats_top1": _rate(row["camp_beats_top1"] for row in rows),
            "camp_beats_loose": _rate(row["camp_beats_loose"] for row in rows),
            "camp_progress_ge_loose": _rate(
                row["camp_progress_ge_loose"] for row in rows
            ),
        },
    }


def _atom_contribution_separation(
    supported: list[dict[str, Any]],
    camp_advantage: list[dict[str, Any]],
    loose_hurts: list[dict[str, Any]],
    loose_helps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    atom_names = sorted(
        {
            atom
            for row in supported
            for atom in row["atom_contribution_margins"].keys()
        }
    )
    rows = []
    for atom in atom_names:
        supported_values = _atom_values(supported, atom)
        advantage_values = _atom_values(camp_advantage, atom)
        hurts_values = _atom_values(loose_hurts, atom)
        helps_values = _atom_values(loose_helps, atom)
        hurts_mean = _mean_or_none(hurts_values)
        helps_mean = _mean_or_none(helps_values)
        rows.append(
            {
                "atom": atom,
                "supported_records": len(supported_values),
                "camp_advantage_records": len(advantage_values),
                "loose_hurts_records": len(hurts_values),
                "loose_helps_records": len(helps_values),
                "supported_mean_contribution_margin": _mean_or_none(supported_values),
                "camp_advantage_mean_contribution_margin": _mean_or_none(
                    advantage_values
                ),
                "loose_hurts_mean_contribution_margin": hurts_mean,
                "loose_helps_mean_contribution_margin": helps_mean,
                "hurts_minus_helps_contribution_margin": (
                    None
                    if hurts_mean is None or helps_mean is None
                    else float(hurts_mean - helps_mean)
                ),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            0.0
            if item["hurts_minus_helps_contribution_margin"] is None
            else -abs(float(item["hurts_minus_helps_contribution_margin"])),
            item["atom"],
        ),
    )


def _decision(
    records: list[dict[str, Any]],
    supported: list[dict[str, Any]],
    camp_advantage: list[dict[str, Any]],
    loose_hurts: list[dict[str, Any]],
) -> dict[str, Any]:
    schema_records = sum(record["score_schema_available"] for record in records)
    reasons = []
    if schema_records:
        reasons.append("affine_score_schema_available")
    else:
        reasons.append("affine_score_schema_missing")
    if camp_advantage:
        reasons.append("current_camp_advantage_records_exist")
    if loose_hurts:
        reasons.append("loose_rule_can_regress_current_camp")
    status = (
        "score_schema_calibration_diagnostic_complete"
        if schema_records and supported
        else "score_schema_calibration_inconclusive"
    )
    return {
        "status": status,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "reasons": reasons,
        "next_step": (
            "Use the contribution evidence to decide whether existing atoms "
            "already protect current CAMP advantage. Any future selector or "
            "schema change must first pass an offline no-leak proof target "
            "against current CAMP before replay."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Score Schema Calibration Diagnostic",
        "",
        "This report is read-only. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Online selector authorized: `{report['final_decision']['online_selector_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "Reasons:",
    ]
    for reason in report["final_decision"]["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(["", "## Records", "", "| Metric | Value |", "| --- | ---: |"])
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    schema = report["score_schema"]
    lines.extend(
        [
            "",
            "## Score Reconstruction",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| `records_with_schema` | {_fmt(schema['records_with_schema'])} |",
            f"| `records_missing_schema` | {_fmt(schema['records_missing_schema'])} |",
            f"| `atom_dimensions` | {_fmt(schema['atom_dimensions'])} |",
            f"| `mean_abs_score_error` | {_fmt(schema['score_reconstruction_abs_error']['mean'])} |",
            f"| `max_abs_score_error` | {_fmt(schema['score_reconstruction_abs_error']['max'])} |",
            f"| `mean_abs_selected_loose_delta_error` | {_fmt(schema['selected_loose_delta_reconstruction_abs_error']['mean'])} |",
        ]
    )
    lines.extend(
        [
            "",
            "## Outcome Groups",
            "",
            "| Group | Records | Schema records | Loose-current Safety | Current-Top1 Safety | Loose-current Progress | Score penalty | Contribution margin |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label in (
        "supported_target",
        "camp_advantage",
        "loose_hurts_current",
        "loose_helps_current",
    ):
        group = report["groups"][label]
        lines.append(
            f"| `{label}` | {group['records']} | {group['schema_records']} | "
            f"{_fmt(group['safety_loose_minus_current']['mean'])} | "
            f"{_fmt(group['safety_current_minus_top1']['mean'])} | "
            f"{_fmt(group['progress_loose_minus_current']['mean'])} | "
            f"{_fmt(group['score_penalty']['mean'])} | "
            f"{_fmt(group['contribution_margin_total']['mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Atom Contribution Separation",
            "",
            "Positive contribution margin means the logged affine CAMP score penalizes the loose alternative more than the current selection.",
            "",
            "| Atom | Supported mean | CAMP advantage mean | Loose hurts mean | Loose helps mean | Hurts - helps |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["atom_contribution_separation"][:16]:
        lines.append(
            f"| `{row['atom']}` | "
            f"{_fmt(row['supported_mean_contribution_margin'])} | "
            f"{_fmt(row['camp_advantage_mean_contribution_margin'])} | "
            f"{_fmt(row['loose_hurts_mean_contribution_margin'])} | "
            f"{_fmt(row['loose_helps_mean_contribution_margin'])} | "
            f"{_fmt(row['hurts_minus_helps_contribution_margin'])} |"
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


def _optional_matrix(
    raw: dict[str, Any],
    rows: int,
    label: str,
    keys: tuple[str, ...],
) -> np.ndarray | None:
    for key in keys:
        if raw.get(key) is None:
            continue
        arr = np.asarray(raw.get(key), dtype=np.float64)
        if arr.ndim != 2 or arr.shape[0] != rows:
            raise ValueError(f"{label} {key} must have shape [{rows}, D].")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{label} {key} must contain finite values.")
        return arr
    return None


def _optional_vector(
    raw: dict[str, Any],
    label: str,
    keys: tuple[str, ...],
) -> np.ndarray | None:
    for key in keys:
        if raw.get(key) is None:
            continue
        arr = np.asarray(raw.get(key), dtype=np.float64).reshape(-1)
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{label} {key} must contain finite values.")
        return arr
    return None


def _atom_names(raw: dict[str, Any], dimension: int, label: str) -> list[str]:
    names = raw.get("atom_names")
    if names is None:
        return list(atom_names_for_dimension(dimension))
    if not isinstance(names, list) or len(names) != dimension:
        raise ValueError(f"{label} atom_names must have length {dimension}.")
    return [str(name) for name in names]


def _atom_values(rows: list[dict[str, Any]], atom: str) -> list[float]:
    return [
        float(row["atom_contribution_margins"][atom])
        for row in rows
        if atom in row["atom_contribution_margins"]
    ]


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


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


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
