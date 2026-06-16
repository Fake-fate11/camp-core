#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
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
)


TOL = 1e-12
SNAPSHOT_GLOB = "camp_microbenchmark_step_*.npz"


@dataclass(frozen=True)
class Requirement:
    name: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class StageSpec:
    name: str
    role: str
    requirements: tuple[Requirement, ...]


SELECTION_LOG_STAGES = (
    StageSpec(
        name="raw_splice_geometry_from_selection_log",
        role="construct the H10-preserving raw tail splice from logged candidates",
        requirements=(
            Requirement("candidate_raw_trajectory_prefix", ("candidate_raw_trajectory_prefix",)),
            Requirement("selected_index", ("selected_index",)),
            Requirement("feasible_mask", ("feasible_mask",)),
            Requirement(
                "short_horizon_red_cost",
                ("candidate_planned_red_light_cost", "dp_candidate_rewards"),
            ),
            Requirement(
                "full_horizon_red_cost",
                ("candidate_full_horizon_planned_red_light_cost",),
            ),
        ),
    ),
    StageSpec(
        name="camp_logged_score_audit_from_selection_log",
        role="audit the already logged CAMP affine score and deterministic selection",
        requirements=(
            Requirement("selected_index", ("selected_index",)),
            Requirement("feasible_mask", ("feasible_mask",)),
            Requirement("atoms", ("atoms",)),
            Requirement("normalized_atoms", ("normalized_atoms",)),
            Requirement("selection_scores", ("selection_scores",)),
            Requirement("selection_weights", ("selection_weights",)),
            Requirement("infeasibility_reasons", ("infeasibility_reasons",)),
        ),
    ),
    StageSpec(
        name="perfect_tracker_splice_recompute_from_selection_log",
        role="recompute PerfectTracker command and open-loop shadows for a transformed candidate",
        requirements=(
            Requirement("candidate_raw_trajectory_prefix", ("candidate_raw_trajectory_prefix",)),
            Requirement("perfect_tracker_command_inputs.dt", ("perfect_tracker_command_inputs.dt",)),
            Requirement(
                "perfect_tracker_command_inputs.current_speed_mps",
                ("perfect_tracker_command_inputs.current_speed_mps",),
            ),
            Requirement(
                "perfect_tracker_command_inputs.current_longitudinal_acceleration_mps2",
                (
                    "perfect_tracker_command_inputs.current_longitudinal_acceleration_mps2",
                ),
            ),
            Requirement(
                "perfect_tracker_open_loop_rollout_inputs.current_acceleration_ego_xy",
                (
                    "perfect_tracker_open_loop_rollout_inputs.current_acceleration_ego_xy",
                ),
            ),
            Requirement(
                "perfect_tracker_candidate_preprocessing",
                ("perfect_tracker_candidate_preprocessing",),
            ),
        ),
    ),
    StageSpec(
        name="red_stopping_margin_splice_recompute_from_selection_log",
        role="recompute the red-stopping-margin atom for a transformed candidate",
        requirements=(
            Requirement("candidate_raw_trajectory_prefix", ("candidate_raw_trajectory_prefix",)),
            Requirement("red_route_points", ("red_route_points",)),
        ),
    ),
    StageSpec(
        name="dp_reward_red_recompute_from_selection_log",
        role="recompute DP near-horizon reward and full-horizon red-light cost for a transformed candidate",
        requirements=(
            Requirement("candidate_raw_trajectory_prefix", ("candidate_raw_trajectory_prefix",)),
            Requirement("reward_input__lanes", ("reward_input__lanes",)),
            Requirement("reward_input__route_lanes", ("reward_input__route_lanes",)),
            Requirement("reward_input__line_strings", ("reward_input__line_strings",)),
            Requirement("reward_input__ego_shape", ("reward_input__ego_shape",)),
            Requirement(
                "reward_input__neighbor_agents_future",
                ("reward_input__neighbor_agents_future",),
            ),
            Requirement(
                "reward_input__neighbor_agents_past",
                ("reward_input__neighbor_agents_past",),
            ),
            Requirement("reward_input__goal_pose", ("reward_input__goal_pose",)),
        ),
    ),
)


SNAPSHOT_STAGES = (
    StageSpec(
        name="perfect_tracker_splice_recompute_from_snapshot",
        role="recompute SG-aware PerfectTracker command and open-loop shadows from snapshot tensors",
        requirements=(
            Requirement("candidates", ("candidates",)),
            Requirement("metadata.current_speed_mps", ("metadata.current_speed_mps",)),
            Requirement(
                "metadata.current_longitudinal_acceleration_mps2",
                ("metadata.current_longitudinal_acceleration_mps2",),
            ),
            Requirement("current_acceleration_ego_xy", ("current_acceleration_ego_xy",)),
            Requirement("metadata.sg_smooth_enabled", ("metadata.sg_smooth_enabled",)),
            Requirement("metadata.sg_filter_window", ("metadata.sg_filter_window",)),
            Requirement("metadata.sg_filter_order", ("metadata.sg_filter_order",)),
        ),
    ),
    StageSpec(
        name="red_stopping_margin_splice_recompute_from_snapshot",
        role="recompute red-stopping-margin atom from snapshot tensors",
        requirements=(
            Requirement("candidates", ("candidates",)),
            Requirement("red_route_points", ("red_route_points",)),
        ),
    ),
    StageSpec(
        name="dp_reward_red_recompute_from_snapshot",
        role="recompute DP near-horizon reward and full-horizon red-light cost from snapshot tensors",
        requirements=(
            Requirement("candidates", ("candidates",)),
            Requirement("metadata.reward_horizon_steps", ("metadata.reward_horizon_steps",)),
            Requirement("metadata.sg_smooth_enabled", ("metadata.sg_smooth_enabled",)),
            Requirement("metadata.sg_filter_window", ("metadata.sg_filter_window",)),
            Requirement("metadata.sg_filter_order", ("metadata.sg_filter_order",)),
            Requirement("reward_input__lanes", ("reward_input__lanes",)),
            Requirement("reward_input__route_lanes", ("reward_input__route_lanes",)),
            Requirement("reward_input__line_strings", ("reward_input__line_strings",)),
            Requirement("reward_input__ego_shape", ("reward_input__ego_shape",)),
            Requirement(
                "reward_input__neighbor_agents_future",
                ("reward_input__neighbor_agents_future",),
            ),
            Requirement(
                "reward_input__neighbor_agents_past",
                ("reward_input__neighbor_agents_past",),
            ),
            Requirement("reward_input__goal_pose", ("reward_input__goal_pose",)),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed readiness audit for recomputing a stop-aware raw-H80 "
            "splice through SG/postprocess, PerfectTracker shadows, and DP "
            "reward/red-light feasibility. The audit inspects artifacts only; "
            "it does not change selection behavior or recompute scores."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--snapshot_root", type=Path, action="append", default=[])
    parser.add_argument("--snapshot", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        snapshot_paths=[*args.snapshot_root, *args.snapshot],
        label=args.label,
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
    snapshot_paths: list[Path] | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    selection_logs = iter_selection_log_paths(paths) if paths else []
    snapshots = iter_snapshot_paths(snapshot_paths or paths)

    records: list[dict[str, Any]] = []
    for log_path in selection_logs:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            if not isinstance(record, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            records.append(
                {
                    "log_path": str(log_path),
                    "record_index": record_index,
                    "record": record,
                    "target": _is_selected_h30_safe_full_red(record),
                }
            )

    snapshot_items = [_snapshot_item(path) for path in snapshots]
    selection_stage_summary = _summarize_items(records, SELECTION_LOG_STAGES)
    snapshot_stage_summary = _summarize_items(snapshot_items, SNAPSHOT_STAGES)

    target_count = sum(1 for item in records if bool(item["target"]))
    can_recompute_from_selection_logs = (
        target_count > 0
        and selection_stage_summary[
            "red_stopping_margin_splice_recompute_from_selection_log"
        ]["target_ready_count"]
        == target_count
        and selection_stage_summary[
            "dp_reward_red_recompute_from_selection_log"
        ]["target_ready_count"]
        == target_count
    )
    can_recompute_from_snapshots = (
        bool(snapshot_items)
        and snapshot_stage_summary[
            "red_stopping_margin_splice_recompute_from_snapshot"
        ]["ready_count"]
        == len(snapshot_items)
        and snapshot_stage_summary["dp_reward_red_recompute_from_snapshot"][
            "ready_count"
        ]
        == len(snapshot_items)
    )

    return {
        "analysis": {
            "name": "dp_camp_splice_recompute_readiness_v1",
            "role": (
                "fail-closed artifact readiness audit for stop-aware splice "
                "recompute before any selector, replay, or formal-seed claim"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "recomputes_dp_reward_or_red_light": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "This audit inspects fixed current-tick artifact fields only. "
                "It defines a finite-candidate recomputation logging contract; "
                "it is not Benders and makes no trajectory-coordinate convexity "
                "claim. If transformed-candidate diagnostics are later atomized "
                "as fixed per-candidate constants, the CAMP score remains affine "
                "in w and the existing simplex/CVaR/L2 master remains convex."
            ),
        },
        "selection_logs": {
            "logs": len(selection_logs),
            "records": len(records),
            "selected_h30_safe_full_red_records": target_count,
            "stages": selection_stage_summary,
        },
        "snapshots": {
            "files": len(snapshot_items),
            "stages": snapshot_stage_summary,
        },
        "gate": {
            "can_recompute_splice_red_feasibility_from_selection_logs": (
                can_recompute_from_selection_logs
            ),
            "can_recompute_splice_red_feasibility_from_snapshots": (
                can_recompute_from_snapshots
            ),
            "decision": _gate_decision(
                can_recompute_from_selection_logs,
                can_recompute_from_snapshots,
                target_count,
                len(snapshot_items),
            ),
        },
    }


def iter_snapshot_paths(paths: list[Path]) -> list[Path]:
    snapshots: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            if path.suffix != ".npz":
                continue
            snapshots.append(path)
        elif path.is_dir():
            snapshots.extend(sorted(path.rglob(SNAPSHOT_GLOB)))
        elif paths:
            raise FileNotFoundError(path)
    return sorted(dict.fromkeys(snapshots))


def _snapshot_item(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as payload:
        keys = set(payload.files)
        metadata: dict[str, Any] = {}
        if "metadata_json" in keys:
            metadata = json.loads(str(payload["metadata_json"].item()))
    return {
        "path": str(path),
        "record_index": None,
        "record": {"metadata": metadata, **{key: True for key in sorted(keys)}},
        "target": True,
    }


def _summarize_items(
    items: list[dict[str, Any]],
    stages: tuple[StageSpec, ...],
) -> dict[str, Any]:
    return {
        stage.name: _summarize_stage(items, stage)
        for stage in stages
    }


def _summarize_stage(items: list[dict[str, Any]], stage: StageSpec) -> dict[str, Any]:
    missing = Counter()
    target_missing = Counter()
    ready_count = 0
    target_ready_count = 0
    target_count = 0
    examples = []

    for item in items:
        record = item["record"]
        missing_names = _missing_requirements(record, stage.requirements)
        ready = not missing_names
        is_target = bool(item["target"])
        ready_count += int(ready)
        if is_target:
            target_count += 1
            target_ready_count += int(ready)
        for name in missing_names:
            missing[name] += 1
            if is_target:
                target_missing[name] += 1
        if missing_names and len(examples) < 5:
            examples.append(
                {
                    "path": item.get("log_path") or item.get("path"),
                    "record_index": item.get("record_index"),
                    "missing": missing_names,
                }
            )

    total = len(items)
    return {
        "role": stage.role,
        "required": [
            {
                "name": requirement.name,
                "alternatives": list(requirement.alternatives),
            }
            for requirement in stage.requirements
        ],
        "ready_count": ready_count,
        "total": total,
        "ready_rate": ready_count / total if total else 0.0,
        "target_ready_count": target_ready_count,
        "target_total": target_count,
        "target_ready_rate": target_ready_count / target_count if target_count else 0.0,
        "missing_counts": dict(sorted(missing.items())),
        "target_missing_counts": dict(sorted(target_missing.items())),
        "examples": examples,
    }


def _missing_requirements(
    record: dict[str, Any],
    requirements: tuple[Requirement, ...],
) -> list[str]:
    missing = []
    for requirement in requirements:
        if not any(_has_path(record, path) for path in requirement.alternatives):
            missing.append(requirement.name)
    return missing


def _has_path(record: dict[str, Any], dotted: str) -> bool:
    current: Any = record
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return _is_present(current)


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value)
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _is_selected_h30_safe_full_red(record: dict[str, Any]) -> bool:
    count = _candidate_count(record)
    selected = record.get("selected_index")
    if count <= 0 or not isinstance(selected, int) or not 0 <= selected < count:
        return False
    short = _short_red(record, count)
    full = _vector(record.get("candidate_full_horizon_planned_red_light_cost"), count)
    if short is None or full is None:
        return False
    return bool(short[selected] <= TOL and full[selected] > TOL)


def _candidate_count(record: dict[str, Any]) -> int:
    count = record.get("num_candidates")
    if isinstance(count, int) and count > 0:
        return count
    for field in (
        "feasible_mask",
        "candidate_raw_trajectory_prefix",
        "candidate_full_horizon_planned_red_light_cost",
    ):
        value = record.get(field)
        if isinstance(value, list) and value:
            return len(value)
    return 0


def _short_red(record: dict[str, Any], count: int) -> np.ndarray | None:
    planned = _vector(record.get("candidate_planned_red_light_cost"), count)
    if planned is not None:
        return planned
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != count:
        return None
    try:
        values = np.asarray(
            [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
            dtype=np.float64,
        )
    except (TypeError, ValueError, AttributeError):
        return None
    if not np.all(np.isfinite(values)):
        return None
    return values


def _vector(value: Any, count: int) -> np.ndarray | None:
    if value is None:
        return None
    try:
        arr = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if arr.shape != (count,) or not np.all(np.isfinite(arr)):
        return None
    return arr


def _gate_decision(
    selection_logs_ready: bool,
    snapshots_ready: bool,
    target_count: int,
    snapshot_count: int,
) -> str:
    if selection_logs_ready:
        return (
            "Selection logs unexpectedly contain enough tensor context for full "
            "splice red/feasibility recompute; verify implementation before replay."
        )
    if snapshots_ready:
        return (
            "Snapshot artifacts contain the required tensor context. The next "
            "step can implement the actual transformed-candidate recompute gate."
        )
    if target_count == 0:
        return (
            "No selected h30-safe/full-red target records were found. Re-run the "
            "readiness audit on the raw-H80 miss artifact."
        )
    if snapshot_count == 0:
        return (
            "Fail-closed: selection logs do not contain full DP reward/red-light "
            "tensor context. Re-run a default-off snapshot capture before claiming "
            "splice feasibility."
        )
    return (
        "Fail-closed: snapshots exist but are missing required reward/red-light "
        "or PerfectTracker tensor fields. Extend snapshot logging or audit the "
        "snapshot producer before recomputing transformed candidates."
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stop-Aware Splice Recompute Readiness Audit",
        "",
        "This is a fail-closed artifact audit. It does not recompute DP rewards, red-light costs, CAMP scores, or closed-loop outcomes.",
        "",
        "## Inputs",
        "",
        f"- Selection logs: `{report['selection_logs']['logs']}`",
        f"- Selection records: `{report['selection_logs']['records']}`",
        f"- Selected h30-safe/full-red target records: `{report['selection_logs']['selected_h30_safe_full_red_records']}`",
        f"- Snapshot files: `{report['snapshots']['files']}`",
        "",
        "## Selection Log Stages",
        "",
        "| Stage | Ready | Target ready | Top missing target fields |",
        "| --- | ---: | ---: | --- |",
    ]
    for stage_name, stage in report["selection_logs"]["stages"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    stage_name,
                    _count(stage["ready_count"], stage["total"]),
                    _count(stage["target_ready_count"], stage["target_total"]),
                    _top_missing(stage["target_missing_counts"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Snapshot Stages",
            "",
            "| Stage | Ready | Top missing fields |",
            "| --- | ---: | --- |",
        ]
    )
    for stage_name, stage in report["snapshots"]["stages"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    stage_name,
                    _count(stage["ready_count"], stage["total"]),
                    _top_missing(stage["missing_counts"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- Selection-log full recompute ready: `{report['gate']['can_recompute_splice_red_feasibility_from_selection_logs']}`",
            f"- Snapshot full recompute ready: `{report['gate']['can_recompute_splice_red_feasibility_from_snapshots']}`",
            f"- Decision: {report['gate']['decision']}",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["convexity_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _count(count: int, total: int) -> str:
    return f"{count}/{total}"


def _top_missing(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(
        f"{name} ({count})"
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[
            :3
        ]
    )


if __name__ == "__main__":
    main()
