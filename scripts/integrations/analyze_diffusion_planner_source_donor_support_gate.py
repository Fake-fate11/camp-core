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

from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (  # noqa: E402
    TOL,
    _load_runtime,
    _load_snapshot,
    _score_trajectories,
    _validate_snapshot,
    reward_hard_feasibility,
    reward_metric_vector,
    reward_progress_screen,
)
from scripts.integrations.analyze_diffusion_planner_world_frame_bridge_screen import (  # noqa: E402
    _selected_tracker_summary,
    _tracker_diagnostics,
    _tracker_metrics_for_budget,
)


READY_STATUS = "source_donor_support_present"
REJECT_STATUS = "source_donor_support_insufficient"


@dataclass(frozen=True)
class SourceDonorSupportConfig:
    min_progress_ratio: float = 0.8
    progress_loss_budgets_m: tuple[float, ...] = (0.5, 1.0, 1.5)
    smoothness_loss_budgets: tuple[float, ...] = (0.0, 0.5, 1.0)
    command_jerk_worse_budget_mps3: float = 0.0
    command_lateral_worse_budget_mps2: float = 0.0
    rollout_horizon: int = 3
    rollout_distance_loss_budget_m: float = 0.10
    rollout_jerk_worse_budget_mps3: float = 0.0
    rollout_lateral_worse_budget_mps2: float = 0.0
    min_snapshot_support_rate: float = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only source-donor support gate over fixed DP/CAMP "
            "microbenchmark snapshots. It checks whether the original DP "
            "candidate pool contains lower-red, DP-hard-feasible, "
            "progress/comfort-admissible donors before any transform."
        )
    )
    parser.add_argument("--bridge_screen_json", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--snapshot_dir", type=Path, default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_progress_ratio", type=float, default=0.8)
    parser.add_argument("--progress_loss_budget_m", action="append", type=float)
    parser.add_argument("--smoothness_loss_budget", action="append", type=float)
    parser.add_argument("--command_jerk_worse_budget_mps3", type=float, default=0.0)
    parser.add_argument("--command_lateral_worse_budget_mps2", type=float, default=0.0)
    parser.add_argument("--rollout_horizon", type=int, default=3)
    parser.add_argument("--rollout_distance_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--rollout_jerk_worse_budget_mps3", type=float, default=0.0)
    parser.add_argument("--rollout_lateral_worse_budget_mps2", type=float, default=0.0)
    parser.add_argument("--min_snapshot_support_rate", type=float, default=0.25)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SourceDonorSupportConfig(
        min_progress_ratio=args.min_progress_ratio,
        progress_loss_budgets_m=tuple(
            args.progress_loss_budget_m
            if args.progress_loss_budget_m is not None
            else (0.5, 1.0, 1.5)
        ),
        smoothness_loss_budgets=tuple(
            args.smoothness_loss_budget
            if args.smoothness_loss_budget is not None
            else (0.0, 0.5, 1.0)
        ),
        command_jerk_worse_budget_mps3=args.command_jerk_worse_budget_mps3,
        command_lateral_worse_budget_mps2=args.command_lateral_worse_budget_mps2,
        rollout_horizon=args.rollout_horizon,
        rollout_distance_loss_budget_m=args.rollout_distance_loss_budget_m,
        rollout_jerk_worse_budget_mps3=args.rollout_jerk_worse_budget_mps3,
        rollout_lateral_worse_budget_mps2=args.rollout_lateral_worse_budget_mps2,
        min_snapshot_support_rate=args.min_snapshot_support_rate,
    )
    report = analyze(
        bridge_screen_json=args.bridge_screen_json,
        diffusion_repo=args.diffusion_repo,
        reward_config_path=args.reward_config,
        snapshot_dir=args.snapshot_dir,
        device=args.device,
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
    bridge_screen_json: Path,
    diffusion_repo: Path,
    reward_config_path: Path,
    snapshot_dir: Path | None = None,
    device: str = "cuda",
    label: str | None = None,
    config: SourceDonorSupportConfig = SourceDonorSupportConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    screen = _load_json(bridge_screen_json)
    replay_module, reward_config, torch = _load_runtime(
        diffusion_repo,
        reward_config_path,
    )
    rows: list[dict[str, Any]] = []
    for screen_row in screen.get("rows", []):
        if not isinstance(screen_row, dict):
            continue
        snapshot_path = _resolve_snapshot_path(screen_row, snapshot_dir)
        arrays, metadata = _load_snapshot(snapshot_path)
        _validate_snapshot(arrays, metadata, snapshot_path)
        rows.extend(
            _candidate_rows_for_snapshot(
                snapshot_path=snapshot_path,
                arrays=arrays,
                metadata=metadata,
                replay_module=replay_module,
                reward_config=reward_config,
                torch=torch,
                device=device,
                config=config,
            )
        )
    return build_report_from_source_rows(
        rows,
        screen=screen,
        config=config,
        label=label,
        paths={
            "bridge_screen_json": str(bridge_screen_json),
            "snapshot_dir": None if snapshot_dir is None else str(snapshot_dir),
            "diffusion_repo": str(diffusion_repo),
            "reward_config": str(reward_config_path),
        },
    )


def build_report_from_source_rows(
    rows: list[dict[str, Any]],
    *,
    screen: dict[str, Any] | None = None,
    config: SourceDonorSupportConfig = SourceDonorSupportConfig(),
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lower = [row for row in rows if row["lower_union_red"]]
    hard = [row for row in lower if row["hard_feasible"]]
    progress = [row for row in lower if row["progress_feasible"]]
    comfort = [row for row in lower if row["comfort_admissible"]]
    by_snapshot = _by_snapshot(rows)
    support = _support_summary(by_snapshot, config)
    hard_reasons = Counter(
        reason for row in lower if not row["hard_feasible"] for reason in row["hard_reasons"]
    )
    failure_classes = Counter(
        klass for row in lower for klass in source_failure_classes(row)
    )
    decision = _decision(support)
    return {
        "analysis": {
            "name": "dp_camp_source_donor_support_gate_v1",
            "label": label,
            "role": (
                "read-only gate for whether the existing DP candidate pool "
                "contains lower-red lane-constrained source donors before any "
                "transform"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This gate uses fixed current-tick DP candidate diagnostics "
                "only. It does not modify DP, does not train CAMP, does not use "
                "future closed-loop outcomes, and does not construct a Benders "
                "master/subproblem, dual, or cuts. If used later, any donor "
                "support diagnostic must be atomized as fixed finite-candidate "
                "constants so CAMP scores remain affine a_k^T w."
            ),
            "paths": paths or {},
        },
        "config": asdict(config),
        "source_screen": {
            "status": _deep_get(screen or {}, ("final_decision", "status")),
            "support_gate": (screen or {}).get("support_gate", {}),
        },
        "records": {
            "candidate_rows": len(rows),
            "lower_union_red_rows": len(lower),
            "lower_union_red_hard_feasible_rows": len(hard),
            "lower_union_red_progress_feasible_rows": len(progress),
            "lower_union_red_comfort_admissible_rows": len(comfort),
        },
        "support_gate": support,
        "hard_reason_counts": dict(sorted(hard_reasons.items())),
        "failure_class_counts": dict(sorted(failure_classes.items())),
        "red_delta": _red_delta_summary(lower),
        "progress_comfort_delta": _progress_comfort_summary(lower),
        "by_snapshot": by_snapshot,
        "top_candidates": _top_candidates(lower),
        "final_decision": decision,
        "candidate_rows": rows,
    }


def source_failure_classes(row: dict[str, Any]) -> list[str]:
    if not row["lower_union_red"]:
        return ["not_lower_red"]
    classes: list[str] = []
    reasons = set(row["hard_reasons"])
    if "dp_lane_crossing" in reasons:
        classes.append("source_lane_invalid")
    if "dp_red_light" in reasons:
        classes.append("source_red_timing_invalid")
    for reason in sorted(reasons - {"dp_lane_crossing", "dp_red_light"}):
        classes.append(f"source_{reason}")
    if row["hard_feasible"] and not row["progress_feasible"]:
        classes.append("source_hard_feasible_but_underprogress")
    if row["progress_feasible"] and not row["comfort_admissible"]:
        classes.extend(_comfort_failure_classes(row))
    if row["comfort_admissible"]:
        classes.append("source_comfort_admissible_support")
    return classes or ["source_unclassified_lower_red_failure"]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    records = report["records"]
    support = report["support_gate"]
    lines = [
        "# Source Donor Support Gate",
        "",
        "This is a read-only fixed-snapshot gate. It does not run replay, train CAMP, or change DP.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Next step: {decision['next_step']}",
        f"- Online selector authorized: `{decision['online_selector_authorized']}`",
        f"- Full36 authorized: `{decision['full36_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Candidate rows | {records['candidate_rows']} |",
        f"| Lower-red source rows | {records['lower_union_red_rows']} |",
        f"| Lower-red hard-feasible rows | {records['lower_union_red_hard_feasible_rows']} |",
        f"| Lower-red progress-feasible rows | {records['lower_union_red_progress_feasible_rows']} |",
        f"| Lower-red comfort-admissible rows | {records['lower_union_red_comfort_admissible_rows']} |",
        "",
        "## Snapshot Support",
        "",
        f"- Required snapshot support rate: `{support['min_snapshot_support_rate']}`",
        f"- Hard-feasible support rate: `{support['hard_feasible_snapshot_support_rate']:.6f}`",
        f"- Comfort-admissible support rate: `{support['comfort_admissible_snapshot_support_rate']:.6f}`",
        "",
        "## Failure Classes",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    for key, value in report["failure_class_counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Hard Reasons",
            "",
            f"`{report['hard_reason_counts']}`",
            "",
            "## Deltas",
            "",
            f"- Red delta summary: `{report['red_delta']}`",
            f"- Progress/comfort summary: `{report['progress_comfort_delta']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _candidate_rows_for_snapshot(
    *,
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    replay_module: Any,
    reward_config: Any,
    torch: Any,
    device: str,
    config: SourceDonorSupportConfig,
) -> list[dict[str, Any]]:
    candidates = np.asarray(arrays["candidates"], dtype=np.float64)
    selected = int(metadata["selected_index"])
    scores = _score_trajectories(
        candidates,
        arrays=arrays,
        metadata=metadata,
        replay_module=replay_module,
        reward_config=reward_config,
        torch=torch,
        device=device,
    )
    tracker = _tracker_diagnostics(candidates, arrays=arrays, metadata=metadata)
    tracker_metrics = _tracker_metrics_for_budget(tracker, _tracker_config(config))
    selected_tracker = _selected_tracker_summary(tracker, selected, _tracker_config(config))
    hard_feasible, hard_reasons = reward_hard_feasibility(scores["reward_breakdowns"])
    progress_feasible, progress_reasons = reward_progress_screen(
        scores["reward_breakdowns"],
        hard_feasible,
        min_progress_ratio=config.min_progress_ratio,
    )
    progress = reward_metric_vector(scores["reward_breakdowns"], "progress")
    smoothness = reward_metric_vector(scores["reward_breakdowns"], "smoothness")
    selected_union = float(scores["union_red_cost"][selected])
    selected_progress = float(progress[selected])
    selected_smoothness = float(smoothness[selected])

    rows = []
    for candidate_index in range(candidates.shape[0]):
        if candidate_index == selected:
            continue
        lower = float(scores["union_red_cost"][candidate_index]) < selected_union - TOL
        progress_loss = float(selected_progress - progress[candidate_index])
        smoothness_loss = float(selected_smoothness - smoothness[candidate_index])
        tracker_delta = _tracker_delta(
            tracker_metrics,
            selected_tracker,
            candidate_index,
        )
        comfort_admissible = _comfort_admissible(
            progress_loss=progress_loss,
            smoothness_loss=smoothness_loss,
            tracker_delta=tracker_delta,
            lower_union_red=lower,
            hard_feasible=bool(hard_feasible[candidate_index]),
            progress_feasible=bool(progress_feasible[candidate_index]),
            config=config,
        )
        row = {
            "snapshot_path": str(snapshot_path),
            "selection_step": int(metadata["selection_step"]),
            "selected_index": selected,
            "candidate_index": int(candidate_index),
            "selected_union_red": selected_union,
            "candidate_union_red": float(scores["union_red_cost"][candidate_index]),
            "candidate_near_red": float(scores["near_red_cost"][candidate_index]),
            "candidate_full_red": float(scores["full_red_cost"][candidate_index]),
            "lower_union_red": lower,
            "hard_feasible": bool(hard_feasible[candidate_index]),
            "hard_reasons": list(hard_reasons[candidate_index]),
            "progress_feasible": bool(progress_feasible[candidate_index]),
            "progress_reasons": list(progress_reasons[candidate_index]),
            "progress_loss_m": progress_loss,
            "smoothness_loss": smoothness_loss,
            "tracker_delta": tracker_delta,
            "comfort_admissible": comfort_admissible,
        }
        row["failure_classes"] = source_failure_classes(row)
        rows.append(row)
    return rows


def _support_summary(
    by_snapshot: list[dict[str, Any]],
    config: SourceDonorSupportConfig,
) -> dict[str, Any]:
    denominator = max(1, len(by_snapshot))
    hard_snapshots = int(
        sum(row["lower_union_red_hard_feasible"] > 0 for row in by_snapshot)
    )
    comfort_snapshots = int(
        sum(row["lower_union_red_comfort_admissible"] > 0 for row in by_snapshot)
    )
    hard_rate = hard_snapshots / denominator
    comfort_rate = comfort_snapshots / denominator
    return {
        "snapshots": len(by_snapshot),
        "snapshots_with_lower_union_red_hard_feasible": hard_snapshots,
        "snapshots_with_lower_union_red_comfort_admissible": comfort_snapshots,
        "min_snapshot_support_rate": float(config.min_snapshot_support_rate),
        "hard_feasible_snapshot_support_rate": hard_rate,
        "comfort_admissible_snapshot_support_rate": comfort_rate,
        "hard_feasible_snapshot_support_pass": (
            hard_rate >= float(config.min_snapshot_support_rate)
        ),
        "comfort_admissible_snapshot_support_pass": (
            comfort_rate >= float(config.min_snapshot_support_rate)
        ),
    }


def _decision(support: dict[str, Any]) -> dict[str, Any]:
    passed = bool(
        support["hard_feasible_snapshot_support_pass"]
        and support["comfort_admissible_snapshot_support_pass"]
    )
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "next_step": (
            "Design a default-off offline selector screen over source donors; "
            "do not run replay yet."
            if passed
            else (
                "Reject lane-constrained donor search over the existing DP "
                "candidate pool; move to route/topology-aware candidate-generation "
                "support or reject transform-based support."
            )
        ),
    }


def _by_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["snapshot_path"], []).append(row)
    result = []
    for path, group in sorted(grouped.items()):
        lower = [row for row in group if row["lower_union_red"]]
        result.append(
            {
                "snapshot_path": path,
                "selection_step": int(group[0]["selection_step"]),
                "candidate_rows": len(group),
                "lower_union_red": len(lower),
                "lower_union_red_hard_feasible": int(
                    sum(row["hard_feasible"] for row in lower)
                ),
                "lower_union_red_progress_feasible": int(
                    sum(row["progress_feasible"] for row in lower)
                ),
                "lower_union_red_comfort_admissible": int(
                    sum(row["comfort_admissible"] for row in lower)
                ),
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


def _top_candidates(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            not row["comfort_admissible"],
            not row["hard_feasible"],
            row["candidate_union_red"],
            row["progress_loss_m"],
        ),
    )
    keys = (
        "snapshot_path",
        "selection_step",
        "candidate_index",
        "selected_union_red",
        "candidate_union_red",
        "hard_feasible",
        "hard_reasons",
        "progress_feasible",
        "progress_loss_m",
        "smoothness_loss",
        "tracker_delta",
        "comfort_admissible",
        "failure_classes",
    )
    return [{key: row[key] for key in keys} for row in sorted_rows[:limit]]


def _tracker_config(config: SourceDonorSupportConfig) -> Any:
    return SimpleNamespace(rollout_horizon=config.rollout_horizon)


def _tracker_delta(
    tracker: dict[str, np.ndarray],
    selected_tracker: dict[str, float],
    index: int,
) -> dict[str, float]:
    return {
        "command_jerk_worse_mps3": float(
            tracker["command_jerk_mps3"][index]
            - selected_tracker["command_jerk_mps3"]
        ),
        "command_lateral_worse_mps2": float(
            tracker["command_lateral_mps2"][index]
            - selected_tracker["command_lateral_mps2"]
        ),
        "rollout_distance_loss_m": float(
            selected_tracker["rollout_distance_m"]
            - tracker["rollout_distance_m"][index]
        ),
        "rollout_jerk_worse_mps3": float(
            tracker["rollout_jerk_mps3"][index]
            - selected_tracker["rollout_jerk_mps3"]
        ),
        "rollout_lateral_worse_mps2": float(
            tracker["rollout_lateral_mps2"][index]
            - selected_tracker["rollout_lateral_mps2"]
        ),
    }


def _comfort_admissible(
    *,
    progress_loss: float,
    smoothness_loss: float,
    tracker_delta: dict[str, float],
    lower_union_red: bool,
    hard_feasible: bool,
    progress_feasible: bool,
    config: SourceDonorSupportConfig,
) -> bool:
    if not lower_union_red or not hard_feasible or not progress_feasible:
        return False
    tracker_ok = (
        tracker_delta["command_jerk_worse_mps3"]
        <= config.command_jerk_worse_budget_mps3 + TOL
        and tracker_delta["command_lateral_worse_mps2"]
        <= config.command_lateral_worse_budget_mps2 + TOL
        and tracker_delta["rollout_distance_loss_m"]
        <= config.rollout_distance_loss_budget_m + TOL
        and tracker_delta["rollout_jerk_worse_mps3"]
        <= config.rollout_jerk_worse_budget_mps3 + TOL
        and tracker_delta["rollout_lateral_worse_mps2"]
        <= config.rollout_lateral_worse_budget_mps2 + TOL
    )
    if not tracker_ok:
        return False
    return any(
        progress_loss <= progress_budget + TOL
        and smoothness_loss <= smoothness_budget + TOL
        for progress_budget in config.progress_loss_budgets_m
        for smoothness_budget in config.smoothness_loss_budgets
    )


def _comfort_failure_classes(row: dict[str, Any]) -> list[str]:
    delta = row["tracker_delta"]
    classes: list[str] = []
    if row["progress_loss_m"] > 1.5 + TOL:
        classes.append("source_comfort_blocked_progress_loss")
    if row["smoothness_loss"] > 1.0 + TOL:
        classes.append("source_comfort_blocked_smoothness_loss")
    if delta["command_jerk_worse_mps3"] > TOL:
        classes.append("source_comfort_blocked_command_jerk")
    if delta["command_lateral_worse_mps2"] > TOL:
        classes.append("source_comfort_blocked_command_lateral")
    if delta["rollout_distance_loss_m"] > 0.10 + TOL:
        classes.append("source_comfort_blocked_rollout_distance")
    if delta["rollout_jerk_worse_mps3"] > TOL:
        classes.append("source_comfort_blocked_rollout_jerk")
    if delta["rollout_lateral_worse_mps2"] > TOL:
        classes.append("source_comfort_blocked_rollout_lateral")
    return classes or ["source_comfort_blocked_unknown_budget"]


def _red_delta_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_union_red": _summary(row["selected_union_red"] for row in rows),
        "candidate_union_red": _summary(row["candidate_union_red"] for row in rows),
        "selected_to_candidate_reduction": _summary(
            row["selected_union_red"] - row["candidate_union_red"] for row in rows
        ),
    }


def _progress_comfort_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "progress_loss_m": _summary(row["progress_loss_m"] for row in rows),
        "smoothness_loss": _summary(row["smoothness_loss"] for row in rows),
        "command_jerk_worse_mps3": _summary(
            row["tracker_delta"]["command_jerk_worse_mps3"] for row in rows
        ),
        "command_lateral_worse_mps2": _summary(
            row["tracker_delta"]["command_lateral_worse_mps2"] for row in rows
        ),
        "rollout_distance_loss_m": _summary(
            row["tracker_delta"]["rollout_distance_loss_m"] for row in rows
        ),
        "rollout_jerk_worse_mps3": _summary(
            row["tracker_delta"]["rollout_jerk_worse_mps3"] for row in rows
        ),
        "rollout_lateral_worse_mps2": _summary(
            row["tracker_delta"]["rollout_lateral_worse_mps2"] for row in rows
        ),
    }


def _validate_config(config: SourceDonorSupportConfig) -> None:
    if not 0.0 <= float(config.min_progress_ratio) <= 1.0:
        raise ValueError("min_progress_ratio must be in [0,1].")
    if not 0.0 <= float(config.min_snapshot_support_rate) <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0,1].")
    for value in config.progress_loss_budgets_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")
    for value in config.smoothness_loss_budgets:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("smoothness_loss_budgets must be nonnegative.")
    for name in (
        "command_jerk_worse_budget_mps3",
        "command_lateral_worse_budget_mps2",
        "rollout_distance_loss_budget_m",
        "rollout_jerk_worse_budget_mps3",
        "rollout_lateral_worse_budget_mps2",
    ):
        value = float(getattr(config, name))
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be nonnegative.")


def _resolve_snapshot_path(
    screen_row: dict[str, Any],
    snapshot_dir: Path | None,
) -> Path:
    path = Path(str(screen_row.get("snapshot_path", "")))
    if path.is_file():
        return path
    if snapshot_dir is None:
        raise FileNotFoundError(f"Missing snapshot path: {path}")
    step = int(screen_row["selection_step"])
    matches = sorted(Path(snapshot_dir).rglob(f"camp_microbenchmark_step_{step:04d}.npz"))
    if not matches:
        raise FileNotFoundError(f"No snapshot for step {step} under {snapshot_dir}")
    return matches[0]


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


def _deep_get(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
