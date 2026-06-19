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
    _hard_component_nonworse_rates,
    _hard_nonworse_rate,
    _is_dense_lane_change,
    _load_records,
    _summary_with_cvar,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    BOOL_FIELDS,
    EPS,
    _fmt,
    _paired_summary,
    _summary,
)


DESCRIPTOR_FIELDS = (
    "dp_prior_gain",
    "score_penalty",
    "planned_progress_loss",
    "target_speed_loss",
    "jerk_worse",
    "lateral_worse",
    "current_score_minus_loose",
    "current_dp_prior_minus_loose",
    "current_planned_progress_minus_loose",
    "current_target_speed_minus_loose",
    "current_jerk_minus_loose",
    "current_lateral_minus_loose",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only attribution for dense lane-change records where current "
            "CAMP can be better than DP Top-1 and the loose non-Top1 support "
            "alternative. Outcomes are posterior labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
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
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
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
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    choices = [_choice(record, config) for record in records]
    rows = [_row(record, choice) for record, choice in zip(records, choices)]
    supported = [row for row in rows if row["supported_target"]]
    camp_advantage = [row for row in supported if row["camp_advantage_record"]]
    loose_hurts = [row for row in supported if row["loose_regresses_current_safety"]]
    loose_helps = [row for row in supported if row["loose_improves_current_safety"]]
    loose_neutral = [
        row
        for row in supported
        if not row["loose_regresses_current_safety"]
        and not row["loose_improves_current_safety"]
    ]
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    return {
        "analysis": {
            "name": "dense_lane_change_current_camp_advantage_attribution_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "outcomes are used only for posterior attribution labels; all "
                "reported descriptors are current-tick fixed candidate features"
            ),
            "loose_rule": config.__dict__,
            "descriptor_fields": list(DESCRIPTOR_FIELDS),
            "math_boundary": (
                "This attribution screen does not change DP, CAMP atoms, CAMP "
                "weights, or selector behavior. Runtime candidate descriptors "
                "remain fixed finite-candidate constants. If any descriptor is "
                "later atomized, the CAMP score must remain affine a_k^T w and "
                "the simplex/CVaR/L2 robust master remains convex. This is not "
                "classical Benders decomposition."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, rows),
        "supported_target": _group_report(
            supported,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "camp_advantage_records": _group_report(
            camp_advantage,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "loose_hurts_current": _group_report(
            loose_hurts,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "loose_helps_current": _group_report(
            loose_helps,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "loose_neutral_current": _group_report(
            loose_neutral,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "descriptor_separation": _descriptor_separation(loose_hurts, loose_helps),
        "final_decision": _decision(rows, supported, camp_advantage, loose_hurts),
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
    top1_progress = float(record["outcome_progress"][top1])
    descriptors = _descriptors(record, loose)
    return {
        "dense_lane_change": _is_dense_lane_change(record),
        "target_record": bool(choice["target_record"]),
        "supported_target": bool(choice["support"]),
        "changed": bool(choice["changed"]),
        "selected": selected,
        "loose": loose,
        "top1": top1,
        "safety_loose_minus_current": loose_cost - current_cost,
        "safety_current_minus_top1": current_cost - top1_cost,
        "safety_loose_minus_top1": loose_cost - top1_cost,
        "progress_loose_minus_current": loose_progress - current_progress,
        "progress_current_minus_top1": current_progress - top1_progress,
        "progress_loose_minus_top1": loose_progress - top1_progress,
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
        "loose_progress_regresses_current": bool(
            loose_progress < current_progress - EPS
        ),
        "hard_nonworse_vs_current": _hard_outcome_nonworse(record, loose, selected),
        "hard_nonworse_vs_top1": _hard_outcome_nonworse(record, loose, top1),
        "descriptors": descriptors,
    }


def _descriptors(record: dict[str, Any], loose: int) -> dict[str, float]:
    selected = int(record["selected"])
    return {
        "dp_prior_gain": float(
            record["dp_prior_deviation"][selected]
            - record["dp_prior_deviation"][loose]
        ),
        "score_penalty": max(
            float(record["scores"][loose] - record["scores"][selected]),
            0.0,
        ),
        "planned_progress_loss": max(
            float(record["planned_progress"][selected] - record["planned_progress"][loose]),
            0.0,
        ),
        "target_speed_loss": max(
            float(record["target_speed"][selected] - record["target_speed"][loose]),
            0.0,
        ),
        "jerk_worse": max(
            float(record["tracker_jerk"][loose] - record["tracker_jerk"][selected]),
            0.0,
        ),
        "lateral_worse": max(
            float(record["tracker_lateral"][loose] - record["tracker_lateral"][selected]),
            0.0,
        ),
        "current_score_minus_loose": float(
            record["scores"][selected] - record["scores"][loose]
        ),
        "current_dp_prior_minus_loose": float(
            record["dp_prior_deviation"][selected]
            - record["dp_prior_deviation"][loose]
        ),
        "current_planned_progress_minus_loose": float(
            record["planned_progress"][selected] - record["planned_progress"][loose]
        ),
        "current_target_speed_minus_loose": float(
            record["target_speed"][selected] - record["target_speed"][loose]
        ),
        "current_jerk_minus_loose": float(
            record["tracker_jerk"][selected] - record["tracker_jerk"][loose]
        ),
        "current_lateral_minus_loose": float(
            record["tracker_lateral"][selected] - record["tracker_lateral"][loose]
        ),
    }


def _group_report(
    rows: list[dict[str, Any]],
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "records": len(rows),
        "safety_loose_minus_current": _summary_with_cvar(
            _values(rows, "safety_loose_minus_current"),
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "safety_current_minus_top1": _summary_with_cvar(
            _values(rows, "safety_current_minus_top1"),
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_loose_minus_current": _paired_summary(
            _values(rows, "progress_loose_minus_current"),
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_current_minus_top1": _paired_summary(
            _values(rows, "progress_current_minus_top1"),
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "rates": {
            "camp_beats_top1": _rate(rows, "camp_beats_top1"),
            "camp_beats_loose": _rate(rows, "camp_beats_loose"),
            "camp_progress_ge_loose": _rate(rows, "camp_progress_ge_loose"),
            "loose_regresses_current_safety": _rate(
                rows,
                "loose_regresses_current_safety",
            ),
            "loose_progress_regresses_current": _rate(
                rows,
                "loose_progress_regresses_current",
            ),
            "hard_nonworse_vs_current": _rate(rows, "hard_nonworse_vs_current"),
            "hard_nonworse_vs_top1": _rate(rows, "hard_nonworse_vs_top1"),
        },
        "descriptors": {
            field: _summary(row["descriptors"][field] for row in rows)
            for field in DESCRIPTOR_FIELDS
        },
    }


def _record_summary(
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": int(
            sum(record["context"].get("formal_seed", False) for record in records)
        ),
        "dense_lane_change_records": int(sum(row["dense_lane_change"] for row in rows)),
        "target_records": int(sum(row["target_record"] for row in rows)),
        "supported_target_records": int(sum(row["supported_target"] for row in rows)),
        "camp_advantage_records": int(sum(row["camp_advantage_record"] for row in rows)),
        "loose_regresses_current_safety_records": int(
            sum(row["loose_regresses_current_safety"] and row["supported_target"] for row in rows)
        ),
        "loose_improves_current_safety_records": int(
            sum(row["loose_improves_current_safety"] and row["supported_target"] for row in rows)
        ),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _descriptor_separation(
    loose_hurts: list[dict[str, Any]],
    loose_helps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for field in DESCRIPTOR_FIELDS:
        hurts = _descriptor_mean(loose_hurts, field)
        helps = _descriptor_mean(loose_helps, field)
        rows.append(
            {
                "descriptor": field,
                "loose_hurts_mean": hurts,
                "loose_helps_mean": helps,
                "hurts_minus_helps": (
                    None if hurts is None or helps is None else float(hurts - helps)
                ),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            0.0
            if item["hurts_minus_helps"] is None
            else -abs(float(item["hurts_minus_helps"]))
        ),
    )


def _decision(
    rows: list[dict[str, Any]],
    supported: list[dict[str, Any]],
    camp_advantage: list[dict[str, Any]],
    loose_hurts: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons = []
    if camp_advantage:
        reasons.append("current_camp_advantage_records_exist")
    if loose_hurts:
        reasons.append("loose_rule_overrides_can_regress_current_camp")
    if len(loose_hurts) >= len(supported) / 2.0 if supported else False:
        reasons.append("loose_rule_hurts_at_least_half_supported_records")
    status = "current_camp_advantage_requires_preservation"
    return {
        "status": status,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "reasons": reasons,
        "next_step": (
            "Design any later finite selector to preserve current CAMP on "
            "records with posterior CAMP advantage before considering replay; "
            "first search for current-tick descriptors that separate "
            "loose-hurts from loose-helps records."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Current CAMP Advantage Attribution",
        "",
        "This is a read-only attribution screen. It does not train CAMP, change DP, run replay, or authorize online selection.",
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
        lines.append(f"| `{key}` | {_fmt_value(value)} |")
    lines.extend(
        [
            "",
            "## Outcome Groups",
            "",
            "| Group | Records | Loose-current Safety | Current-Top1 Safety | Loose-current Progress | CAMP beats Top1 | CAMP beats loose |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, key in (
        ("supported_target", "supported_target"),
        ("camp_advantage", "camp_advantage_records"),
        ("loose_hurts_current", "loose_hurts_current"),
        ("loose_helps_current", "loose_helps_current"),
        ("loose_neutral_current", "loose_neutral_current"),
    ):
        group = report[key]
        lines.append(
            f"| `{label}` | {group['records']} | "
            f"{_fmt_value(group['safety_loose_minus_current']['mean'])} | "
            f"{_fmt_value(group['safety_current_minus_top1']['mean'])} | "
            f"{_fmt_value(group['progress_loose_minus_current']['mean'])} | "
            f"{_fmt_value(group['rates']['camp_beats_top1'])} | "
            f"{_fmt_value(group['rates']['camp_beats_loose'])} |"
        )
    lines.extend(
        [
            "",
            "## Descriptor Separation",
            "",
            "| Descriptor | Loose hurts mean | Loose helps mean | Hurts - helps |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in report["descriptor_separation"]:
        lines.append(
            f"| `{row['descriptor']}` | "
            f"{_fmt_value(row['loose_hurts_mean'])} | "
            f"{_fmt_value(row['loose_helps_mean'])} | "
            f"{_fmt_value(row['hurts_minus_helps'])} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _values(rows: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in rows], dtype=np.float64)


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    return float(np.mean([bool(row[key]) for row in rows]))


def _descriptor_mean(rows: list[dict[str, Any]], field: str) -> float | None:
    if not rows:
        return None
    return float(np.mean([row["descriptors"][field] for row in rows]))


def _hard_outcome_nonworse(
    record: dict[str, Any],
    candidate: int,
    reference: int,
) -> bool:
    candidate_outcome = record["outcomes"][int(candidate)]
    reference_outcome = record["outcomes"][int(reference)]
    return all(
        float(bool(candidate_outcome[field])) <= float(bool(reference_outcome[field]))
        for field in BOOL_FIELDS
    )


def _fmt_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    try:
        return _fmt(value)
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    main()
