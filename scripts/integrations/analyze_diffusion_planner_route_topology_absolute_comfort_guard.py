#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (  # noqa: E402
    REJECT_STATUS as ROUTE_TOPOLOGY_REJECT_STATUS,
    RouteTopologyCandidateConfig,
    build_route_topology_candidates,
)
from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (  # noqa: E402
    _load_snapshot,
    _validate_snapshot,
)
from scripts.integrations.analyze_diffusion_planner_world_frame_bridge_screen import (  # noqa: E402
    _selected_tracker_summary,
    _tracker_diagnostics,
    _tracker_metrics_for_budget,
)


READY_STATUS = "route_topology_absolute_lateral_guard_support_present"
REJECT_STATUS = "route_topology_absolute_lateral_guard_support_insufficient"
SOURCE_CONFLICT_STATUS = "route_topology_absolute_lateral_guard_source_conflict"


@dataclass(frozen=True)
class AbsoluteComfortGuardConfig:
    max_command_lateral_mps2: float
    max_rollout_lateral_mps2: float
    rollout_horizon: int = 3
    min_snapshot_support_rate: float = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only absolute lateral guard audit for route/topology generated "
            "candidates. It consumes an existing fixed-snapshot candidate screen, "
            "recomputes PerfectTracker absolute lateral metrics, and does not "
            "run DP reward or replay."
        )
    )
    parser.add_argument("--screen_json", type=Path, required=True)
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_command_lateral_mps2", type=float, default=None)
    parser.add_argument("--max_rollout_lateral_mps2", type=float, default=None)
    parser.add_argument("--rollout_horizon", type=int, default=3)
    parser.add_argument("--min_snapshot_support_rate", type=float, default=0.25)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reward_config = _load_json(args.reward_config)
    max_lat = _max_lateral_from_reward_config(reward_config)
    config = AbsoluteComfortGuardConfig(
        max_command_lateral_mps2=(
            float(args.max_command_lateral_mps2)
            if args.max_command_lateral_mps2 is not None
            else max_lat
        ),
        max_rollout_lateral_mps2=(
            float(args.max_rollout_lateral_mps2)
            if args.max_rollout_lateral_mps2 is not None
            else max_lat
        ),
        rollout_horizon=args.rollout_horizon,
        min_snapshot_support_rate=args.min_snapshot_support_rate,
    )
    report = analyze(
        screen_json=args.screen_json,
        snapshot_dir=args.snapshot_dir,
        reward_config_path=args.reward_config,
        label=args.label,
        config=config,
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
    *,
    screen_json: Path,
    snapshot_dir: Path,
    reward_config_path: Path,
    label: str | None = None,
    config: AbsoluteComfortGuardConfig | None = None,
) -> dict[str, Any]:
    screen = _load_json(screen_json)
    reward_config = _load_json(reward_config_path)
    active_config = config or AbsoluteComfortGuardConfig(
        max_command_lateral_mps2=_max_lateral_from_reward_config(reward_config),
        max_rollout_lateral_mps2=_max_lateral_from_reward_config(reward_config),
    )
    _validate_config(active_config)
    rows = _recompute_rows(
        screen=screen,
        snapshot_dir=snapshot_dir,
        config=active_config,
    )
    return build_report_from_rows(
        rows,
        screen=screen,
        label=label,
        config=active_config,
        paths={
            "screen_json": str(screen_json),
            "snapshot_dir": str(snapshot_dir),
            "reward_config": str(reward_config_path),
        },
    )


def build_report_from_rows(
    rows: list[dict[str, Any]],
    *,
    screen: dict[str, Any],
    label: str | None = None,
    config: AbsoluteComfortGuardConfig,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_config(config)
    source = _source_summary(screen)
    conflicts = _source_conflicts(screen)
    lower = [row for row in rows if row["lower_union_red"]]
    target = [
        row
        for row in lower
        if row["hard_feasible"] and row["progress_feasible"]
    ]
    absolute = [row for row in target if row["absolute_lateral_guard_pass"]]
    by_snapshot = _by_snapshot(rows)
    support = _support_summary(by_snapshot, config)
    decision = _decision(source=source, conflicts=conflicts, support=support)
    return {
        "analysis": {
            "name": "dp_camp_route_topology_absolute_lateral_guard_v1",
            "label": label,
            "role": (
                "read-only audit of whether strict relative comfort budgets "
                "reject route/topology candidates that pass a documented "
                "absolute lateral acceleration guard"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "dp_reward_recompute": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "jerk_guard_policy": (
                "reported_only; no documented absolute jerk guard is used"
            ),
            "math_boundary": (
                "This audit recomputes deterministic PerfectTracker metrics "
                "from fixed current-tick snapshots and an existing fixed "
                "candidate screen. It does not modify DP, train CAMP, use "
                "future closed-loop outcomes, or construct a Benders "
                "master/subproblem, dual, or cuts. If this diagnostic is later "
                "atomized, it is a fixed finite-candidate constant and CAMP "
                "scores remain affine a_k^T w."
            ),
            "paths": paths or {},
        },
        "config": asdict(config),
        "source_screen": source,
        "records": {
            "candidate_rows": len(rows),
            "lower_union_red_rows": len(lower),
            "lower_union_red_hard_progress_rows": len(target),
            "absolute_lateral_guard_rows": len(absolute),
        },
        "support_gate": support,
        "absolute_metric_summary": _absolute_metric_summary(lower),
        "failure_class_counts": dict(sorted(_failure_classes(lower).items())),
        "top_absolute_guard_candidates": _top_candidates(absolute),
        "by_snapshot": by_snapshot,
        "source_authorization_conflicts": conflicts,
        "final_decision": decision,
        "rows": rows,
    }


def _recompute_rows(
    *,
    screen: dict[str, Any],
    snapshot_dir: Path,
    config: AbsoluteComfortGuardConfig,
) -> list[dict[str, Any]]:
    candidate_config = _candidate_config_from_screen(screen)
    result: list[dict[str, Any]] = []
    for screen_row in screen.get("rows", []):
        if not isinstance(screen_row, dict):
            continue
        screen_candidates = [
            row for row in screen_row.get("candidate_rows", []) if isinstance(row, dict)
        ]
        snapshot_path = _resolve_snapshot_path(screen_row, snapshot_dir)
        arrays, metadata = _load_snapshot(snapshot_path)
        _validate_snapshot(arrays, metadata, snapshot_path)
        candidates = np.asarray(arrays["candidates"], dtype=np.float64)
        selected = int(metadata["selected_index"])
        generated, generated_meta = build_route_topology_candidates(
            candidates,
            lane_centerline=np.asarray(arrays["lane_centerline"], dtype=np.float64),
            red_route_points=np.asarray(arrays["red_route_points"], dtype=np.float64),
            selected_index=selected,
            current_speed_mps=float(metadata.get("current_speed_mps", 0.0)),
            dt=float(metadata.get("dt", 0.1)),
            config=candidate_config,
        )
        if len(screen_candidates) != len(generated_meta):
            raise ValueError(
                f"{snapshot_path} generated {len(generated_meta)} candidates but "
                f"screen has {len(screen_candidates)} rows."
            )
        baseline_tracker = _tracker_diagnostics(
            candidates,
            arrays=arrays,
            metadata=metadata,
        )
        generated_tracker = _tracker_diagnostics(
            generated,
            arrays=arrays,
            metadata=metadata,
        )
        tracker_config = SimpleNamespace(rollout_horizon=config.rollout_horizon)
        selected_metrics = _selected_tracker_summary(
            baseline_tracker,
            selected,
            tracker_config,
        )
        generated_metrics = _tracker_metrics_for_budget(
            generated_tracker,
            tracker_config,
        )
        for idx, row in enumerate(screen_candidates):
            _assert_meta_compatible(row.get("candidate_meta", {}), generated_meta[idx])
            candidate_metrics = {
                "command_jerk_mps3": float(
                    generated_metrics["command_jerk_mps3"][idx]
                ),
                "command_lateral_mps2": float(
                    generated_metrics["command_lateral_mps2"][idx]
                ),
                "rollout_distance_m": float(
                    generated_metrics["rollout_distance_m"][idx]
                ),
                "rollout_jerk_mps3": float(
                    generated_metrics["rollout_jerk_mps3"][idx]
                ),
                "rollout_lateral_mps2": float(
                    generated_metrics["rollout_lateral_mps2"][idx]
                ),
            }
            absolute_pass = bool(
                row.get("lower_union_red")
                and row.get("hard_feasible")
                and row.get("progress_feasible")
                and candidate_metrics["command_lateral_mps2"]
                <= config.max_command_lateral_mps2
                and candidate_metrics["rollout_lateral_mps2"]
                <= config.max_rollout_lateral_mps2
            )
            result.append(
                {
                    "snapshot_path": str(snapshot_path),
                    "selection_step": int(metadata["selection_step"]),
                    "candidate_index": int(row.get("candidate_index", idx)),
                    "candidate_meta": row.get("candidate_meta", {}),
                    "lower_union_red": bool(row.get("lower_union_red")),
                    "hard_feasible": bool(row.get("hard_feasible")),
                    "hard_reasons": list(row.get("hard_reasons", [])),
                    "progress_feasible": bool(row.get("progress_feasible")),
                    "progress_loss_m": _float_or_none(row.get("progress_loss_m")),
                    "smoothness_loss": _float_or_none(row.get("smoothness_loss")),
                    "relative_comfort_admissible": bool(
                        row.get("comfort_admissible")
                    ),
                    "selected_tracker": selected_metrics,
                    "candidate_tracker": candidate_metrics,
                    "absolute_lateral_guard_pass": absolute_pass,
                    "failure_classes": _row_failure_classes(
                        row,
                        candidate_metrics,
                        config,
                    ),
                }
            )
    return result


def _candidate_config_from_screen(screen: dict[str, Any]) -> RouteTopologyCandidateConfig:
    raw = screen.get("config") or {}
    return RouteTopologyCandidateConfig(
        generator_policy=str(raw.get("generator_policy", "lane_centerline_red_stop")),
        red_stop_margins_m=tuple(
            float(value) for value in raw.get("red_stop_margins_m", (2.0, 4.0, 6.0))
        ),
        backup_stop_offsets_m=tuple(
            float(value) for value in raw.get("backup_stop_offsets_m", (0.0, 1.0))
        ),
        prefix_steps=tuple(int(value) for value in raw.get("prefix_steps", (3, 5, 10))),
        bridge_steps=tuple(int(value) for value in raw.get("bridge_steps", (10,))),
        min_stop_distance_m=float(raw.get("min_stop_distance_m", 2.0)),
        max_deceleration_mps2=float(raw.get("max_deceleration_mps2", 3.0)),
        default_speed_mps=float(raw.get("default_speed_mps", 4.0)),
        min_progress_ratio=float(raw.get("min_progress_ratio", 0.8)),
        progress_loss_budgets_m=tuple(
            float(value) for value in raw.get("progress_loss_budgets_m", (0.5, 1.0, 1.5))
        ),
        smoothness_loss_budgets=tuple(
            float(value) for value in raw.get("smoothness_loss_budgets", (0.0, 0.5, 1.0))
        ),
        command_jerk_worse_budget_mps3=float(
            raw.get("command_jerk_worse_budget_mps3", 0.0)
        ),
        command_lateral_worse_budget_mps2=float(
            raw.get("command_lateral_worse_budget_mps2", 0.0)
        ),
        rollout_horizon=int(raw.get("rollout_horizon", 3)),
        rollout_distance_loss_budget_m=float(
            raw.get("rollout_distance_loss_budget_m", 0.10)
        ),
        rollout_jerk_worse_budget_mps3=float(
            raw.get("rollout_jerk_worse_budget_mps3", 0.0)
        ),
        rollout_lateral_worse_budget_mps2=float(
            raw.get("rollout_lateral_worse_budget_mps2", 0.0)
        ),
        min_snapshot_support_rate=float(raw.get("min_snapshot_support_rate", 0.25)),
    )


def _source_summary(screen: dict[str, Any]) -> dict[str, Any]:
    decision = screen.get("final_decision") or {}
    support = screen.get("support_gate") or {}
    return {
        "analysis_name": (screen.get("analysis") or {}).get("name"),
        "status": decision.get("status"),
        "offline_selector_screen_authorized": bool(
            decision.get("offline_selector_screen_authorized")
        ),
        "closed_loop_smoke_authorized": bool(
            decision.get("closed_loop_smoke_authorized")
        ),
        "online_selector_authorized": bool(decision.get("online_selector_authorized")),
        "full36_authorized": bool(decision.get("full36_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
        "hard_feasible_snapshot_support_rate": support.get(
            "hard_feasible_snapshot_support_rate"
        ),
        "comfort_admissible_snapshot_support_rate": support.get(
            "comfort_admissible_snapshot_support_rate"
        ),
    }


def _source_conflicts(screen: dict[str, Any]) -> list[str]:
    source = _source_summary(screen)
    conflicts = []
    if source["status"] != ROUTE_TOPOLOGY_REJECT_STATUS:
        conflicts.append("source_screen:not_rejected")
    for key in (
        "offline_selector_screen_authorized",
        "closed_loop_smoke_authorized",
        "online_selector_authorized",
        "full36_authorized",
        "formal_seeds_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
    ):
        if source[key]:
            conflicts.append(f"source_screen:{key}")
    return conflicts


def _support_summary(
    by_snapshot: list[dict[str, Any]],
    config: AbsoluteComfortGuardConfig,
) -> dict[str, Any]:
    denominator = max(1, len(by_snapshot))
    supported = int(sum(row["absolute_lateral_guard_support"] > 0 for row in by_snapshot))
    rate = supported / denominator
    return {
        "snapshots": len(by_snapshot),
        "snapshots_with_absolute_lateral_guard_support": supported,
        "absolute_lateral_guard_snapshot_support_rate": rate,
        "min_snapshot_support_rate": float(config.min_snapshot_support_rate),
        "absolute_lateral_guard_snapshot_support_pass": (
            rate >= float(config.min_snapshot_support_rate)
        ),
    }


def _decision(
    *,
    source: dict[str, Any],
    conflicts: list[str],
    support: dict[str, Any],
) -> dict[str, Any]:
    if conflicts:
        status = SOURCE_CONFLICT_STATUS
        next_step = "Fix or rerun the source route/topology screen before this audit."
    elif support["absolute_lateral_guard_snapshot_support_pass"]:
        status = READY_STATUS
        next_step = (
            "Relative nonworse comfort is too strict for this slice under the "
            "documented absolute lateral guard. Next gate must still address "
            "jerk/progress with a documented guard or remain offline."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "The rejected screen is not rescued by the documented absolute "
            "lateral guard; move to a materially different lane-valid generator."
        )
    return {
        "status": status,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "source_authorization_conflicts": conflicts,
        "next_step": next_step,
    }


def _by_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["snapshot_path"], []).append(row)
    result = []
    for path, group in sorted(grouped.items()):
        lower = [row for row in group if row["lower_union_red"]]
        target = [
            row for row in lower if row["hard_feasible"] and row["progress_feasible"]
        ]
        absolute = [row for row in target if row["absolute_lateral_guard_pass"]]
        result.append(
            {
                "snapshot_path": path,
                "selection_step": int(group[0]["selection_step"]),
                "candidate_rows": len(group),
                "lower_union_red": len(lower),
                "lower_union_red_hard_progress": len(target),
                "absolute_lateral_guard_support": len(absolute),
                "failure_class_counts": dict(
                    sorted(
                        Counter(
                            klass
                            for row in lower
                            for klass in row["failure_classes"]
                        ).items()
                    )
                ),
            }
        )
    return result


def _row_failure_classes(
    row: dict[str, Any],
    candidate_metrics: dict[str, float],
    config: AbsoluteComfortGuardConfig,
) -> list[str]:
    if not bool(row.get("lower_union_red")):
        return ["not_lower_red"]
    classes: list[str] = []
    if not bool(row.get("hard_feasible")):
        classes.extend(f"hard_{reason}" for reason in row.get("hard_reasons", []))
    if bool(row.get("hard_feasible")) and not bool(row.get("progress_feasible")):
        classes.append("underprogress")
    if (
        candidate_metrics["command_lateral_mps2"]
        > config.max_command_lateral_mps2
    ):
        classes.append("absolute_command_lateral_guard_failed")
    if (
        candidate_metrics["rollout_lateral_mps2"]
        > config.max_rollout_lateral_mps2
    ):
        classes.append("absolute_rollout_lateral_guard_failed")
    if not classes:
        classes.append("absolute_lateral_guard_support")
    return classes


def _failure_classes(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(klass for row in rows for klass in row["failure_classes"])


def _absolute_metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_command_lateral_mps2": _summary(
            row["candidate_tracker"]["command_lateral_mps2"] for row in rows
        ),
        "candidate_rollout_lateral_mps2": _summary(
            row["candidate_tracker"]["rollout_lateral_mps2"] for row in rows
        ),
        "candidate_command_jerk_mps3": _summary(
            row["candidate_tracker"]["command_jerk_mps3"] for row in rows
        ),
        "candidate_rollout_jerk_mps3": _summary(
            row["candidate_tracker"]["rollout_jerk_mps3"] for row in rows
        ),
        "progress_loss_m": _summary(row["progress_loss_m"] for row in rows),
        "smoothness_loss": _summary(row["smoothness_loss"] for row in rows),
    }


def _top_candidates(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    keys = (
        "snapshot_path",
        "selection_step",
        "candidate_index",
        "candidate_meta",
        "progress_loss_m",
        "smoothness_loss",
        "selected_tracker",
        "candidate_tracker",
        "absolute_lateral_guard_pass",
        "failure_classes",
    )
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            row["candidate_tracker"]["rollout_lateral_mps2"],
            row["candidate_tracker"]["command_lateral_mps2"],
            row["progress_loss_m"] or 0.0,
        ),
    )
    return [{key: row[key] for key in keys} for row in sorted_rows[:limit]]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    support = report["support_gate"]
    records = report["records"]
    lines = [
        "# Route/Topology Absolute Lateral Guard Audit",
        "",
        "This report is read-only. It does not run DP reward, replay, train CAMP, change DP, or promote an online selector.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Next step: {decision['next_step']}",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in records.items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Support",
            "",
            f"- Required snapshot support rate: `{support['min_snapshot_support_rate']}`",
            f"- Absolute lateral support rate: `{support['absolute_lateral_guard_snapshot_support_rate']:.6f}`",
            "",
            "## Failure Classes",
            "",
            "| Class | Count |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["failure_class_counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Absolute Metrics",
            "",
            f"`{report['absolute_metric_summary']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_snapshot_path(screen_row: dict[str, Any], snapshot_dir: Path) -> Path:
    path = Path(str(screen_row.get("snapshot_path", "")))
    if path.is_file():
        return path
    step = int(screen_row["selection_step"])
    matches = sorted(Path(snapshot_dir).rglob(f"camp_microbenchmark_step_{step:04d}.npz"))
    if not matches:
        raise FileNotFoundError(f"No snapshot for step {step} under {snapshot_dir}")
    return matches[0]


def _assert_meta_compatible(left: Any, right: dict[str, Any]) -> None:
    if not isinstance(left, dict):
        raise ValueError("candidate_meta must be a dict.")
    for key in (
        "variant",
        "prefix_steps",
        "bridge_steps",
        "red_stop_margin_m",
        "backup_stop_offset_m",
    ):
        if key not in left and key not in right:
            continue
        if key not in left or key not in right:
            raise ValueError(f"candidate metadata missing {key}.")
        if isinstance(right[key], float):
            if abs(float(left[key]) - float(right[key])) > 1e-9:
                raise ValueError(f"candidate metadata mismatch for {key}.")
        elif left[key] != right[key]:
            raise ValueError(f"candidate metadata mismatch for {key}.")


def _max_lateral_from_reward_config(config: dict[str, Any]) -> float:
    value = config.get("max_lat_accel")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("reward_config must define finite max_lat_accel.") from None
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError("reward_config max_lat_accel must be positive.")
    return result


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
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
    }


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, float):
        return f"`{value:.6f}`"
    return f"`{value}`"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _validate_config(config: AbsoluteComfortGuardConfig) -> None:
    for name in ("max_command_lateral_mps2", "max_rollout_lateral_mps2"):
        value = float(getattr(config, name))
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be positive.")
    if int(config.rollout_horizon) <= 0:
        raise ValueError("rollout_horizon must be positive.")
    if not 0.0 <= float(config.min_snapshot_support_rate) <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0,1].")


if __name__ == "__main__":
    main()
