#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
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


TARGET_REASONS = frozenset(
    (
        "budget_admissible_lower_red_candidate",
        "no_budget_admissible_lower_red_candidate",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit default-off splice-shadow pilot records. This is a read-only "
            "selection-log analysis; it does not recompute DP reward and has no "
            "selection effect."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze([*args.root, *args.selection_log], label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(paths: list[Path], *, label: str | None = None) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    rows: list[dict[str, Any]] = []
    missing_shadow_records = 0
    total_records = 0
    selection_effect_values: set[bool] = set()
    online_selector_values: set[bool] = set()
    for log_path in log_paths:
        metadata = parse_selection_log_metadata(log_path)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            total_records += 1
            shadow = record.get("splice_shadow_rule")
            if shadow is None:
                missing_shadow_records += 1
                continue
            selection_effect_values.add(bool(shadow.get("selection_effect")))
            online_selector_values.add(bool(shadow.get("online_selector_change")))
            reason = str(shadow.get("reason"))
            if reason in TARGET_REASONS:
                rows.append(
                    _row_from_record(
                        record=record,
                        shadow=shadow,
                        metadata=asdict(metadata),
                        record_index=record_index,
                        log_path=log_path,
                    )
                )

    reason_counts = Counter(row["reason"] for row in rows)
    class_counts = Counter(row["no_budget_class"] for row in rows if row["kind"] == "no_budget")
    changed_rows = [row for row in rows if row["kind"] == "changed"]
    no_budget_rows = [row for row in rows if row["kind"] == "no_budget"]
    return {
        "analysis": {
            "name": "dp_camp_splice_shadow_pilot_audit_v1",
            "label": label,
            "role": (
                "read-only audit of default-off fixed-candidate splice-shadow "
                "selection-log records"
            ),
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "mathematical_boundary": (
                "The audit consumes fixed finite per-tick constants already "
                "logged by the shadow path. It is not Benders, does not add a "
                "dual subproblem or cuts, and does not claim trajectory-space "
                "convexity."
            ),
            "limitation": (
                "Existing logs store transformed-candidate aggregate counts and "
                "the chosen changed candidate, but not full per-donor transformed "
                "reward arrays. No-budget records can be split by aggregate "
                "hard-feasible/lower-red counts, but not attributed to exact "
                "per-donor progress or smoothness blockers without recomputation "
                "or richer future logging."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "missing_splice_shadow": missing_shadow_records,
            "target_records": len(rows),
            "changed": len(changed_rows),
            "no_budget": len(no_budget_rows),
            "selection_effect_values": sorted(selection_effect_values),
            "online_selector_change_values": sorted(online_selector_values),
            "reason_counts": dict(sorted(reason_counts.items())),
            "no_budget_class_counts": dict(sorted(class_counts.items())),
        },
        "safety_opportunity": {
            "changed": _changed_summary(changed_rows),
            "no_budget": _no_budget_summary(no_budget_rows),
        },
        "latency": _latency_summary(rows),
        "by_run": _by_run(rows),
        "top_latency_records": sorted(
            rows,
            key=lambda row: row["latency_ms_splice_shadow_rule"] or -1.0,
            reverse=True,
        )[:10],
        "target_rows": rows,
    }


def _row_from_record(
    *,
    record: dict[str, Any],
    shadow: dict[str, Any],
    metadata: dict[str, Any],
    record_index: int,
    log_path: Path,
) -> dict[str, Any]:
    label = f"{log_path} record {record_index}"
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(record.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    union_red = _vector(
        record.get("candidate_horizon_union_planned_red_light_cost"),
        candidate_count,
        f"{label} candidate_horizon_union_planned_red_light_cost",
        nonnegative=True,
    )
    full_red = _optional_vector(
        record.get("candidate_full_horizon_planned_red_light_cost"),
        candidate_count,
        f"{label} candidate_full_horizon_planned_red_light_cost",
        nonnegative=True,
    )
    near_red = _optional_reward_metric(record, selected, "red_light", negate=True)
    progress = _optional_reward_metric(record, selected, "progress")
    smoothness = _optional_reward_metric(record, selected, "smoothness")
    feasible = _optional_bool_vector(
        record.get("feasible_mask"),
        candidate_count,
        f"{label} feasible_mask",
    )
    baseline_union_red = float(union_red[selected])
    chosen_union_red = _optional_float(shadow.get("chosen_union_red"))
    kind = (
        "changed"
        if str(shadow.get("reason")) == "budget_admissible_lower_red_candidate"
        else "no_budget"
    )
    row = {
        "log_path": str(log_path),
        "metadata": metadata,
        "record_index": int(record_index),
        "selection_step": int(record.get("selection_step", record_index)),
        "kind": kind,
        "reason": str(shadow.get("reason")),
        "selected_index": selected,
        "baseline_union_red": baseline_union_red,
        "baseline_full_red": (
            float(full_red[selected]) if full_red is not None else None
        ),
        "baseline_near_red": near_red,
        "baseline_progress": progress,
        "baseline_smoothness": smoothness,
        "selected_is_feasible": (
            bool(feasible[selected]) if feasible is not None else None
        ),
        "fallback_record": bool(feasible is not None and not feasible.any()),
        "donor_count": int(shadow.get("donor_count", 0)),
        "transform_count": int(shadow.get("transform_count", 0)),
        "hard_feasible_count": int(shadow.get("hard_feasible_count", 0)),
        "lower_union_red_count": int(shadow.get("lower_union_red_count", 0)),
        "lower_union_red_hard_feasible_count": int(
            shadow.get("lower_union_red_hard_feasible_count", 0)
        ),
        "admissible_count": int(shadow.get("admissible_count", 0)),
        "chosen_donor_index": shadow.get("chosen_donor_index"),
        "chosen_union_red": chosen_union_red,
        "chosen_progress_loss_m": _optional_float(
            shadow.get("chosen_progress_loss_m")
        ),
        "chosen_smoothness_loss": _optional_float(
            shadow.get("chosen_smoothness_loss")
        ),
        "union_red_reduction": (
            baseline_union_red - chosen_union_red
            if chosen_union_red is not None
            else None
        ),
        "budget": dict(shadow.get("budget") or {}),
        "no_budget_class": (
            _no_budget_class(shadow) if kind == "no_budget" else None
        ),
        "latency_ms_splice_shadow_rule": _optional_float(
            record.get("latency_ms_splice_shadow_rule")
        ),
        "latency_ms_splice_shadow_internal": _optional_float(
            shadow.get("latency_ms")
        ),
        "latency_ms_splice_shadow_full_red": _optional_float(
            shadow.get("full_red_latency_ms")
        ),
        "latency_ms_selection": _optional_float(record.get("latency_ms_selection")),
        "latency_ms_including_candidate_generation": _optional_float(
            record.get("latency_ms_including_candidate_generation")
        ),
    }
    if row["kind"] == "changed" and row["union_red_reduction"] is not None:
        row["changed_to_zero_union_red"] = bool(abs(row["chosen_union_red"]) <= 1e-12)
    else:
        row["changed_to_zero_union_red"] = None
    return row


def _no_budget_class(shadow: dict[str, Any]) -> str:
    transform_count = int(shadow.get("transform_count", 0))
    if transform_count <= 0:
        return "no_transformed_candidates"
    hard_feasible = int(shadow.get("hard_feasible_count", 0))
    lower_red = int(shadow.get("lower_union_red_count", 0))
    lower_red_hard = int(shadow.get("lower_union_red_hard_feasible_count", 0))
    admissible = int(shadow.get("admissible_count", 0))
    if hard_feasible <= 0:
        return "no_hard_feasible_transformed_candidates"
    if lower_red <= 0:
        return "splice_removed_lower_red_advantage"
    if lower_red_hard <= 0:
        return "lower_red_transforms_not_hard_feasible"
    if admissible <= 0:
        return "lower_red_hard_feasible_but_budget_empty"
    return "unexpected_nonempty_admissible_no_change"


def _changed_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "zero_union_red_records": sum(
            int(bool(row["changed_to_zero_union_red"])) for row in rows
        ),
        "baseline_union_red": _summary(
            row["baseline_union_red"] for row in rows
        ),
        "chosen_union_red": _summary(
            row["chosen_union_red"] for row in rows
        ),
        "union_red_reduction": _summary(
            row["union_red_reduction"] for row in rows
        ),
        "progress_loss_m": _summary(
            row["chosen_progress_loss_m"] for row in rows
        ),
        "smoothness_loss": _summary(
            row["chosen_smoothness_loss"] for row in rows
        ),
    }


def _no_budget_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "baseline_union_red": _summary(
            row["baseline_union_red"] for row in rows
        ),
        "donor_count": _summary(row["donor_count"] for row in rows),
        "transform_count": _summary(row["transform_count"] for row in rows),
        "hard_feasible_count": _summary(
            row["hard_feasible_count"] for row in rows
        ),
        "lower_union_red_count": _summary(
            row["lower_union_red_count"] for row in rows
        ),
        "lower_union_red_hard_feasible_count": _summary(
            row["lower_union_red_hard_feasible_count"] for row in rows
        ),
    }


def _latency_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "all_target_records": _summary(
            row["latency_ms_splice_shadow_rule"] for row in rows
        ),
        "changed_records": _summary(
            row["latency_ms_splice_shadow_rule"]
            for row in rows
            if row["kind"] == "changed"
        ),
        "no_budget_records": _summary(
            row["latency_ms_splice_shadow_rule"]
            for row in rows
            if row["kind"] == "no_budget"
        ),
        "internal_full_red_component": _summary(
            row["latency_ms_splice_shadow_full_red"] for row in rows
        ),
    }


def _by_run(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        meta = row["metadata"]
        key = (
            f"{meta['route']}/seed_{meta['seed']}/npc_{meta['npc_count']}/"
            f"{meta['spawn']}/tl_{meta['traffic_light']}/{meta['mode']}"
        )
        grouped.setdefault(key, []).append(row)
    report = []
    for key, group in sorted(grouped.items()):
        report.append(
            {
                "run": key,
                "records": len(group),
                "changed": sum(int(row["kind"] == "changed") for row in group),
                "no_budget": sum(int(row["kind"] == "no_budget") for row in group),
                "steps": [row["selection_step"] for row in group],
                "no_budget_class_counts": dict(
                    sorted(
                        Counter(
                            row["no_budget_class"]
                            for row in group
                            if row["kind"] == "no_budget"
                        ).items()
                    )
                ),
                "union_red_reduction": _summary(
                    row["union_red_reduction"] for row in group
                ),
                "latency_ms_splice_shadow_rule": _summary(
                    row["latency_ms_splice_shadow_rule"] for row in group
                ),
            }
        )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    changed = report["safety_opportunity"]["changed"]
    no_budget = report["safety_opportunity"]["no_budget"]
    latency = report["latency"]
    lines = [
        "# Diffusion Planner Splice-Shadow Pilot Audit",
        "",
        f"Label: `{report['analysis']['label']}`",
        "",
        "## Scope",
        "",
        report["analysis"]["role"] + ".",
        "",
        report["analysis"]["limitation"],
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Logs | {records['logs']} |",
        f"| Total records | {records['total']} |",
        f"| Missing splice-shadow records | {records['missing_splice_shadow']} |",
        f"| Target records | {records['target_records']} |",
        f"| Changed records | {records['changed']} |",
        f"| No-budget records | {records['no_budget']} |",
        f"| Reason counts | `{records['reason_counts']}` |",
        f"| No-budget class counts | `{records['no_budget_class_counts']}` |",
        "",
        "## Safety Opportunity",
        "",
        "| Metric | Changed | No-budget |",
        "| --- | ---: | ---: |",
        f"| Records | {changed['records']} | {no_budget['records']} |",
        f"| Baseline union-red mean | {_fmt(changed['baseline_union_red']['mean'])} | {_fmt(no_budget['baseline_union_red']['mean'])} |",
        f"| Changed chosen union-red mean | {_fmt(changed['chosen_union_red']['mean'])} | n/a |",
        f"| Union-red reduction mean | {_fmt(changed['union_red_reduction']['mean'])} | n/a |",
        f"| Progress loss max | {_fmt(changed['progress_loss_m']['max'])} | n/a |",
        f"| Smoothness loss max | {_fmt(changed['smoothness_loss']['max'])} | n/a |",
        f"| Zero-union changed records | {changed['zero_union_red_records']} | n/a |",
        "",
        "## Latency",
        "",
        "| Metric | Mean | P95 | Max |",
        "| --- | ---: | ---: | ---: |",
        _summary_row("All target records", latency["all_target_records"]),
        _summary_row("Changed records", latency["changed_records"]),
        _summary_row("No-budget records", latency["no_budget_records"]),
        _summary_row("Internal full-red component", latency["internal_full_red_component"]),
        "",
        "## By Run",
        "",
        "| Run | Changed | No-budget | Steps | No-budget classes |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in report["by_run"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{row['run']}`",
                    str(row["changed"]),
                    str(row["no_budget"]),
                    "`" + ", ".join(str(step) for step in row["steps"]) + "`",
                    "`" + str(row["no_budget_class_counts"]) + "`",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Decision Boundary",
            "",
            report["analysis"]["mathematical_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p95'])} | "
        f"{_fmt(values['max'])} |"
    )


def _summary(values: Any) -> dict[str, float | int | None]:
    finite = [
        float(value)
        for value in values
        if value is not None and np.isfinite(float(value))
    ]
    if not finite:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "p50": None,
            "p95": None,
            "max": None,
        }
    arr = np.asarray(finite, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "max": float(np.max(arr)),
    }


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"


def _vector(
    value: Any,
    size: int,
    label: str,
    *,
    nonnegative: bool = False,
) -> np.ndarray:
    if value is None:
        raise ValueError(f"{label} is required.")
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.size != size:
        raise ValueError(f"{label} expected {size} values, got {arr.size}.")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must be finite.")
    if nonnegative and np.any(arr < -1e-12):
        raise ValueError(f"{label} must be nonnegative.")
    return arr


def _optional_vector(
    value: Any,
    size: int,
    label: str,
    *,
    nonnegative: bool = False,
) -> np.ndarray | None:
    if value is None:
        return None
    return _vector(value, size, label, nonnegative=nonnegative)


def _optional_bool_vector(value: Any, size: int, label: str) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=bool).reshape(-1)
    if arr.size != size:
        raise ValueError(f"{label} expected {size} values, got {arr.size}.")
    return arr


def _optional_reward_metric(
    record: dict[str, Any],
    selected: int,
    key: str,
    *,
    negate: bool = False,
) -> float | None:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or selected >= len(rewards):
        return None
    reward = rewards[selected]
    if not isinstance(reward, dict) or reward.get(key) is None:
        return None
    value = float(reward[key])
    if not np.isfinite(value):
        return None
    return -value if negate else value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


if __name__ == "__main__":
    main()
