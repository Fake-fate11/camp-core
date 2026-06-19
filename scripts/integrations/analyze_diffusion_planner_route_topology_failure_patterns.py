#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only route-topology screen failure-pattern audit. It explains "
            "whether lower-red candidate rows are blocked by hard feasibility, "
            "progress, or comfort before any replay or online selector is "
            "considered."
        )
    )
    parser.add_argument("--screen_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_snapshot_support_rate", type=float, default=0.25)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    screen = json.loads(args.screen_json.read_text(encoding="utf-8"))
    report = build_report(
        screen,
        source_screen_json=str(args.screen_json),
        label=args.label,
        min_snapshot_support_rate=args.min_snapshot_support_rate,
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


def build_report(
    screen: dict[str, Any],
    *,
    source_screen_json: str | None = None,
    label: str | None = None,
    min_snapshot_support_rate: float = 0.25,
) -> dict[str, Any]:
    if not 0.0 <= min_snapshot_support_rate <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0, 1].")
    rows = _lower_red_rows(screen)
    snapshot_ids = sorted({row["snapshot_id"] for row in rows})
    support = _support_summary(rows, snapshot_ids)
    failures = _failure_summary(rows)
    metadata = _metadata_summary(rows)
    decision = _decision(
        support,
        failures,
        min_snapshot_support_rate=min_snapshot_support_rate,
    )
    return {
        "analysis": {
            "name": "dp_route_topology_failure_patterns_v1",
            "label": label,
            "source_screen_json": source_screen_json,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "future_outcome_leakage": False,
        },
        "source_screen": {
            "generator_policy": (screen.get("config") or {}).get("generator_policy"),
            "final_status": (screen.get("final_decision") or {}).get("status"),
            "records": screen.get("records"),
            "support_gate": screen.get("support_gate"),
        },
        "records": {
            "parent_rows": len(screen.get("rows") or []),
            "lower_red_candidate_rows": len(rows),
            "lower_red_snapshots": len(snapshot_ids),
        },
        "support": support,
        "failures": failures,
        "metadata_breakdown": metadata,
        "top_failure_snapshots": _top_failure_snapshots(screen, limit=10),
        "final_decision": decision,
        "math_boundary": {
            "finite_candidate_diagnostic": True,
            "current_tick_quantities_only": True,
            "dp_modified": False,
            "camp_weights_changed": False,
            "classical_benders_claim": False,
            "affine_score_preserved_if_atomized": True,
        },
    }


def _lower_red_rows(screen: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parent in screen.get("rows") or []:
        snapshot_path = str(parent.get("snapshot_path") or "")
        selection_step = parent.get("selection_step")
        snapshot_id = _snapshot_id(snapshot_path, selection_step)
        for candidate in parent.get("candidate_rows") or []:
            if not candidate.get("lower_union_red"):
                continue
            row = dict(candidate)
            row["snapshot_id"] = snapshot_id
            row["parent_selected_union_red"] = parent.get("selected_union_red")
            rows.append(row)
    return rows


def _snapshot_id(snapshot_path: str, selection_step: Any) -> str:
    if selection_step is not None:
        return f"step:{selection_step}"
    if snapshot_path:
        return f"path:{snapshot_path}"
    return "unknown"


def _support_summary(
    rows: list[dict[str, Any]],
    snapshot_ids: list[str],
) -> dict[str, Any]:
    snapshot_count = len(snapshot_ids)
    hard_snapshots = _snapshots_where(rows, "hard_feasible")
    progress_snapshots = _snapshots_where(rows, "progress_feasible")
    comfort_snapshots = _snapshots_where(rows, "comfort_admissible")
    hard_progress_snapshots = {
        row["snapshot_id"]
        for row in rows
        if row.get("hard_feasible") and row.get("progress_feasible")
    }
    hard_progress_not_comfort_snapshots = {
        row["snapshot_id"]
        for row in rows
        if row.get("hard_feasible")
        and row.get("progress_feasible")
        and not row.get("comfort_admissible")
    }
    return {
        "snapshots": snapshot_count,
        "hard_feasible_rows": _count_true(rows, "hard_feasible"),
        "hard_feasible_snapshots": len(hard_snapshots),
        "hard_feasible_snapshot_rate": _rate(len(hard_snapshots), snapshot_count),
        "progress_feasible_rows": _count_true(rows, "progress_feasible"),
        "progress_feasible_snapshots": len(progress_snapshots),
        "progress_feasible_snapshot_rate": _rate(
            len(progress_snapshots), snapshot_count
        ),
        "comfort_admissible_rows": _count_true(rows, "comfort_admissible"),
        "comfort_admissible_snapshots": len(comfort_snapshots),
        "comfort_admissible_snapshot_rate": _rate(
            len(comfort_snapshots), snapshot_count
        ),
        "hard_and_progress_snapshots": len(hard_progress_snapshots),
        "hard_progress_not_comfort_snapshots": len(
            hard_progress_not_comfort_snapshots
        ),
    }


def _failure_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hard_reason_rows: Counter[str] = Counter()
    hard_reason_snapshots: dict[str, set[str]] = defaultdict(set)
    failure_class_rows: Counter[str] = Counter()
    failure_class_snapshots: dict[str, set[str]] = defaultdict(set)
    status_grid: Counter[str] = Counter()
    for row in rows:
        snapshot_id = row["snapshot_id"]
        for reason in row.get("hard_reasons") or []:
            hard_reason_rows[str(reason)] += 1
            hard_reason_snapshots[str(reason)].add(snapshot_id)
        for klass in row.get("failure_classes") or []:
            failure_class_rows[str(klass)] += 1
            failure_class_snapshots[str(klass)].add(snapshot_id)
        status_grid[_status_key(row)] += 1
    return {
        "hard_reason_row_counts": dict(sorted(hard_reason_rows.items())),
        "hard_reason_snapshot_counts": {
            key: len(value)
            for key, value in sorted(hard_reason_snapshots.items())
        },
        "failure_class_row_counts": dict(sorted(failure_class_rows.items())),
        "failure_class_snapshot_counts": {
            key: len(value)
            for key, value in sorted(failure_class_snapshots.items())
        },
        "status_grid_counts": dict(sorted(status_grid.items())),
    }


def _metadata_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        meta = row.get("candidate_meta") or {}
        backup = _fmt_meta(meta.get("backup_stop_offset_m"))
        offset = _fmt_meta(meta.get("lateral_offset_scale"))
        groups[f"backup={backup}|offset={offset}"].append(row)
    return {
        key: _group_summary(value)
        for key, value in sorted(groups.items())
    }


def _group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    red_reductions = [
        _as_float(row.get("selected_union_red"), 0.0)
        - _as_float(row.get("candidate_union_red"), 0.0)
        for row in rows
    ]
    return {
        "rows": len(rows),
        "hard_feasible_rows": _count_true(rows, "hard_feasible"),
        "progress_feasible_rows": _count_true(rows, "progress_feasible"),
        "comfort_admissible_rows": _count_true(rows, "comfort_admissible"),
        "mean_progress_loss_m": _mean(row.get("progress_loss_m") for row in rows),
        "max_progress_loss_m": _max(row.get("progress_loss_m") for row in rows),
        "mean_smoothness_loss": _mean(row.get("smoothness_loss") for row in rows),
        "mean_union_red_reduction": _mean(red_reductions),
    }


def _top_failure_snapshots(
    screen: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rows = list(screen.get("by_snapshot") or [])
    rows.sort(
        key=lambda item: (
            int(item.get("lower_union_red_hard_feasible") or 0),
            int(item.get("lower_union_red_progress_feasible") or 0),
            int(item.get("lower_union_red_comfort_admissible") or 0),
            -int(item.get("lower_union_red") or 0),
        )
    )
    return rows[:limit]


def _decision(
    support: dict[str, Any],
    failures: dict[str, Any],
    *,
    min_snapshot_support_rate: float,
) -> dict[str, Any]:
    hard_rate = float(support["hard_feasible_snapshot_rate"])
    progress_rate = float(support["progress_feasible_snapshot_rate"])
    comfort_rate = float(support["comfort_admissible_snapshot_rate"])
    hard_reasons = failures.get("hard_reason_snapshot_counts") or {}
    if hard_rate < min_snapshot_support_rate:
        status = "route_topology_failure_patterns_hard_support_insufficient"
        next_step = (
            "Reject more tuning of this stop-target family; design a materially "
            "different lane-valid generator before replay."
        )
    elif progress_rate < min_snapshot_support_rate:
        status = "route_topology_failure_patterns_progress_limited"
        next_step = (
            "Keep the generator offline and redesign progress preservation before "
            "any selector or replay."
        )
    elif comfort_rate < min_snapshot_support_rate:
        status = "route_topology_failure_patterns_comfort_limited"
        next_step = (
            "Keep the generator offline and redesign comfort/bridge behavior before "
            "any selector or replay."
        )
    else:
        status = "route_topology_failure_patterns_support_present"
        next_step = (
            "Use this as diagnostic input for a no-leak offline selector screen; "
            "do not promote online without a separate gate."
        )
    return {
        "status": status,
        "min_snapshot_support_rate": float(min_snapshot_support_rate),
        "dominant_hard_reasons": _top_items(hard_reasons, limit=5),
        "next_step": next_step,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    analysis = report["analysis"]
    source = report["source_screen"]
    records = report["records"]
    support = report["support"]
    failures = report["failures"]
    decision = report["final_decision"]
    lines = [
        "# Route-Topology Failure-Pattern Audit",
        "",
        f"- Label: `{analysis.get('label')}`",
        f"- Source screen: `{analysis.get('source_screen_json')}`",
        f"- Generator policy: `{source.get('generator_policy')}`",
        f"- Source status: `{source.get('final_status')}`",
        f"- Decision: `{decision['status']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Records",
        "",
        f"- Parent rows: `{records['parent_rows']}`",
        f"- Lower-red candidate rows: `{records['lower_red_candidate_rows']}`",
        f"- Lower-red snapshots: `{records['lower_red_snapshots']}`",
        "",
        "## Support",
        "",
        "| Gate | Rows | Snapshots | Snapshot rate |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| hard feasible | `{support['hard_feasible_rows']}` | "
            f"`{support['hard_feasible_snapshots']}` | "
            f"`{support['hard_feasible_snapshot_rate']:.6f}` |"
        ),
        (
            f"| progress feasible | `{support['progress_feasible_rows']}` | "
            f"`{support['progress_feasible_snapshots']}` | "
            f"`{support['progress_feasible_snapshot_rate']:.6f}` |"
        ),
        (
            f"| comfort admissible | `{support['comfort_admissible_rows']}` | "
            f"`{support['comfort_admissible_snapshots']}` | "
            f"`{support['comfort_admissible_snapshot_rate']:.6f}` |"
        ),
        "",
        "## Hard Reasons",
        "",
        "| Reason | Candidate rows | Snapshots |",
        "| --- | ---: | ---: |",
    ]
    hard_rows = failures.get("hard_reason_row_counts") or {}
    hard_snaps = failures.get("hard_reason_snapshot_counts") or {}
    for reason, count in sorted(hard_rows.items()):
        lines.append(f"| `{reason}` | `{count}` | `{hard_snaps.get(reason, 0)}` |")
    if not hard_rows:
        lines.append("| none | `0` | `0` |")
    lines.extend(
        [
            "",
            "## Status Grid",
            "",
            "| Status | Rows |",
            "| --- | ---: |",
        ]
    )
    for key, count in (failures.get("status_grid_counts") or {}).items():
        lines.append(f"| `{key}` | `{count}` |")
    lines.extend(
        [
            "",
            "## Metadata Breakdown",
            "",
            "| Group | Rows | Hard | Progress | Comfort | Mean progress loss | Mean red reduction |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for key, item in report["metadata_breakdown"].items():
        lines.append(
            f"| `{key}` | `{item['rows']}` | `{item['hard_feasible_rows']}` | "
            f"`{item['progress_feasible_rows']}` | "
            f"`{item['comfort_admissible_rows']}` | "
            f"`{_fmt_float(item['mean_progress_loss_m'])}` | "
            f"`{_fmt_float(item['mean_union_red_reduction'])}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            "This is a read-only finite-candidate diagnostic. It uses fixed "
            "current-tick screen rows and predeclared support thresholds. It does "
            "not modify DP, change CAMP weights, use closed-loop future outcomes "
            "for runtime selection, or claim classical Benders decomposition. If "
            "any diagnostic is later atomized, it must remain fixed per candidate "
            "so the CAMP score stays affine in `w` and the simplex/CVaR/L2 master "
            "remains convex.",
            "",
        ]
    )
    return "\n".join(lines)


def _snapshots_where(rows: list[dict[str, Any]], key: str) -> set[str]:
    return {row["snapshot_id"] for row in rows if row.get(key)}


def _count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key))


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else float(numerator) / float(denominator)


def _status_key(row: dict[str, Any]) -> str:
    hard = "hard" if row.get("hard_feasible") else "not_hard"
    progress = "progress" if row.get("progress_feasible") else "not_progress"
    comfort = "comfort" if row.get("comfort_admissible") else "not_comfort"
    return f"{hard}|{progress}|{comfort}"


def _fmt_meta(value: Any) -> str:
    if value is None:
        return "none"
    try:
        return f"{float(value):.3g}"
    except (TypeError, ValueError):
        return str(value)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: Any) -> float | None:
    vals = [_as_float(value, float("nan")) for value in values]
    finite = [value for value in vals if value == value]
    if not finite:
        return None
    return float(fmean(finite))


def _max(values: Any) -> float | None:
    vals = [_as_float(value, float("nan")) for value in values]
    finite = [value for value in vals if value == value]
    if not finite:
        return None
    return float(max(finite))


def _top_items(counts: dict[str, int], *, limit: int) -> list[dict[str, Any]]:
    return [
        {"name": key, "count": int(value)}
        for key, value in sorted(
            counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:limit]
    ]


def _fmt_float(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"


if __name__ == "__main__":
    main()
