#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
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
    WorldFrameBridgeConfig,
    _selected_tracker_summary,
    _tracker_diagnostics,
    _tracker_metrics_for_budget,
    build_world_frame_bridge_candidates,
)


STATUS_REJECTED = "world_frame_bridge_failure_attribution_reject_transform_route"
STATUS_INCONCLUSIVE = "world_frame_bridge_failure_attribution_inconclusive"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only per-candidate attribution for failed world-frame "
            "donor-tail bridge screens. It recomputes fixed-snapshot DP reward, "
            "SG-off diagnostics, and PerfectTracker proxy blockers. It does "
            "not run replay or change selection."
        )
    )
    parser.add_argument("--bridge_screen_json", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--snapshot_dir", type=Path, default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        bridge_screen_json=args.bridge_screen_json,
        diffusion_repo=args.diffusion_repo,
        reward_config_path=args.reward_config,
        snapshot_dir=args.snapshot_dir,
        device=args.device,
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
    *,
    bridge_screen_json: Path,
    diffusion_repo: Path,
    reward_config_path: Path,
    snapshot_dir: Path | None = None,
    device: str = "cuda",
    label: str | None = None,
) -> dict[str, Any]:
    screen = _load_json(bridge_screen_json)
    config = _config_from_screen(screen)
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
                screen_row=screen_row,
                arrays=arrays,
                metadata=metadata,
                replay_module=replay_module,
                reward_config=reward_config,
                torch=torch,
                device=device,
                config=config,
            )
        )
    return build_report_from_candidate_rows(
        rows,
        screen=screen,
        label=label,
        paths={
            "bridge_screen_json": str(bridge_screen_json),
            "snapshot_dir": None if snapshot_dir is None else str(snapshot_dir),
            "diffusion_repo": str(diffusion_repo),
            "reward_config": str(reward_config_path),
        },
    )


def build_report_from_candidate_rows(
    rows: list[dict[str, Any]],
    *,
    screen: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lower_red = [row for row in rows if row["lower_union_red"]]
    hard_failed = [row for row in lower_red if not row["transformed_hard_feasible"]]
    hard_supported = [row for row in lower_red if row["transformed_hard_feasible"]]
    comfort_failed = [
        row
        for row in hard_supported
        if not row["comfort_admissible"]
    ]
    class_counts = Counter(
        failure_class
        for row in lower_red
        for failure_class in row["failure_classes"]
    )
    hard_reason_counts = Counter(
        reason
        for row in hard_failed
        for reason in row["transformed_hard_reasons"]
    )
    source_reason_counts = Counter(
        reason
        for row in lower_red
        for reason in row["source_donor_hard_reasons"]
    )
    sg_counts = Counter(
        reason
        for row in lower_red
        for reason in row["sg_effect_classes"]
    )
    support = _screen_support(screen)
    decision = _decision(class_counts, lower_red_count=len(lower_red), support=support)
    return {
        "analysis": {
            "name": "dp_camp_world_frame_bridge_failure_attribution_v1",
            "label": label,
            "role": (
                "read-only fixed-snapshot attribution for why lower-red "
                "world-frame bridge candidates remain hard-infeasible or "
                "comfort-blocked"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This attribution recomputes deterministic diagnostics over "
                "fixed current-tick snapshot candidates. It does not modify DP, "
                "does not train CAMP, does not use closed-loop future outcomes, "
                "and does not construct a Benders master/subproblem, dual, or "
                "cuts. Any future CAMP atomization would still require fixed "
                "finite candidate constants so scores remain affine a_k^T w."
            ),
            "paths": paths or {},
        },
        "source_screen": {
            "status": _deep_get(screen or {}, ("final_decision", "status")),
            "support_gate": support,
        },
        "records": {
            "candidate_rows": len(rows),
            "lower_union_red_rows": len(lower_red),
            "lower_union_red_hard_failed_rows": len(hard_failed),
            "lower_union_red_hard_supported_rows": len(hard_supported),
            "lower_union_red_comfort_failed_rows": len(comfort_failed),
            "lower_union_red_comfort_admissible_rows": int(
                sum(row["comfort_admissible"] for row in lower_red)
            ),
        },
        "failure_class_counts": dict(sorted(class_counts.items())),
        "transformed_hard_reason_counts": dict(sorted(hard_reason_counts.items())),
        "source_donor_hard_reason_counts": dict(sorted(source_reason_counts.items())),
        "sg_effect_counts": dict(sorted(sg_counts.items())),
        "comfort_blocker_counts": _comfort_blocker_counts(comfort_failed),
        "red_delta": _red_delta_summary(lower_red),
        "progress_comfort_delta": _progress_comfort_summary(lower_red),
        "by_snapshot": _by_snapshot(rows),
        "top_examples": _top_examples(lower_red),
        "final_decision": decision,
        "candidate_rows": rows,
    }


def _candidate_rows_for_snapshot(
    *,
    snapshot_path: Path,
    screen_row: dict[str, Any],
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    replay_module: Any,
    reward_config: Any,
    torch: Any,
    device: str,
    config: WorldFrameBridgeConfig,
) -> list[dict[str, Any]]:
    candidates = np.asarray(arrays["candidates"], dtype=np.float64)
    selected = int(metadata["selected_index"])
    donor_indices = np.asarray(screen_row.get("donor_indices", []), dtype=np.int64)
    transformed_candidates = build_world_frame_bridge_candidates(
        candidates,
        selected_index=selected,
        donor_indices=donor_indices,
        preserve_steps=config.preserve_steps,
        bridge_steps=config.bridge_steps,
        heading_mode=config.heading_mode,
    )
    if transformed_candidates.size == 0:
        return []

    baseline_scores = _score_trajectories(
        candidates,
        arrays=arrays,
        metadata=metadata,
        replay_module=replay_module,
        reward_config=reward_config,
        torch=torch,
        device=device,
    )
    transformed_scores = _score_trajectories(
        transformed_candidates,
        arrays=arrays,
        metadata=metadata,
        replay_module=replay_module,
        reward_config=reward_config,
        torch=torch,
        device=device,
    )
    no_sg_metadata = dict(metadata)
    no_sg_metadata["sg_smooth_enabled"] = False
    transformed_no_sg_scores = _score_trajectories(
        transformed_candidates,
        arrays=arrays,
        metadata=no_sg_metadata,
        replay_module=replay_module,
        reward_config=reward_config,
        torch=torch,
        device=device,
    )
    baseline_tracker = _tracker_diagnostics(candidates, arrays=arrays, metadata=metadata)
    transformed_tracker = _tracker_diagnostics(
        transformed_candidates,
        arrays=arrays,
        metadata=metadata,
    )
    tracker_metrics = _tracker_metrics_for_budget(transformed_tracker, config)
    selected_tracker = _selected_tracker_summary(baseline_tracker, selected, config)

    baseline_hard, baseline_reasons = reward_hard_feasibility(
        baseline_scores["reward_breakdowns"]
    )
    transformed_hard, transformed_reasons = reward_hard_feasibility(
        transformed_scores["reward_breakdowns"]
    )
    no_sg_hard, no_sg_reasons = reward_hard_feasibility(
        transformed_no_sg_scores["reward_breakdowns"]
    )
    progress_feasible, progress_reasons = reward_progress_screen(
        transformed_scores["reward_breakdowns"],
        transformed_hard,
        min_progress_ratio=config.min_progress_ratio,
    )
    progress = reward_metric_vector(transformed_scores["reward_breakdowns"], "progress")
    smoothness = reward_metric_vector(
        transformed_scores["reward_breakdowns"],
        "smoothness",
    )
    selected_progress = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "progress")[
            selected
        ]
    )
    selected_smoothness = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "smoothness")[
            selected
        ]
    )
    selected_union = float(baseline_scores["union_red_cost"][selected])
    rows: list[dict[str, Any]] = []
    donor_list = [int(index) for index in donor_indices.tolist() if int(index) != selected]
    for transformed_index, donor_index in enumerate(donor_list):
        progress_loss = float(selected_progress - progress[transformed_index])
        smoothness_loss = float(selected_smoothness - smoothness[transformed_index])
        tracker_delta = _tracker_delta(
            tracker_metrics,
            selected_tracker,
            transformed_index,
        )
        lower_union = (
            float(transformed_scores["union_red_cost"][transformed_index])
            < selected_union - TOL
        )
        comfort_admissible = _comfort_admissible(
            progress_loss=progress_loss,
            smoothness_loss=smoothness_loss,
            tracker_delta=tracker_delta,
            hard_feasible=bool(transformed_hard[transformed_index]),
            lower_union_red=lower_union,
            config=config,
        )
        row = {
            "snapshot_path": str(snapshot_path),
            "selection_step": int(metadata["selection_step"]),
            "selected_index": selected,
            "donor_index": donor_index,
            "transformed_index": int(transformed_index),
            "selected_union_red": selected_union,
            "source_donor_union_red": float(
                baseline_scores["union_red_cost"][donor_index]
            ),
            "transformed_union_red": float(
                transformed_scores["union_red_cost"][transformed_index]
            ),
            "transformed_near_red": float(
                transformed_scores["near_red_cost"][transformed_index]
            ),
            "transformed_full_red": float(
                transformed_scores["full_red_cost"][transformed_index]
            ),
            "transformed_no_sg_union_red": float(
                transformed_no_sg_scores["union_red_cost"][transformed_index]
            ),
            "lower_union_red": lower_union,
            "source_donor_hard_feasible": bool(baseline_hard[donor_index]),
            "source_donor_hard_reasons": list(baseline_reasons[donor_index]),
            "transformed_hard_feasible": bool(transformed_hard[transformed_index]),
            "transformed_hard_reasons": list(
                transformed_reasons[transformed_index]
            ),
            "transformed_no_sg_hard_feasible": bool(no_sg_hard[transformed_index]),
            "transformed_no_sg_hard_reasons": list(
                no_sg_reasons[transformed_index]
            ),
            "progress_feasible": bool(progress_feasible[transformed_index]),
            "progress_reasons": list(progress_reasons[transformed_index]),
            "progress_loss_m": progress_loss,
            "smoothness_loss": smoothness_loss,
            "tracker_delta": tracker_delta,
            "comfort_admissible": comfort_admissible,
        }
        row["failure_classes"] = candidate_failure_classes(row)
        row["sg_effect_classes"] = sg_effect_classes(row)
        rows.append(row)
    return rows


def candidate_failure_classes(row: dict[str, Any]) -> list[str]:
    classes: list[str] = []
    if not row["lower_union_red"]:
        return ["not_lower_red"]
    source = set(row["source_donor_hard_reasons"])
    transformed = set(row["transformed_hard_reasons"])
    if "dp_lane_crossing" in transformed:
        if "dp_lane_crossing" in source:
            classes.append("source_donor_lane_invalid")
        else:
            classes.append("bridge_or_sg_introduced_lane_invalid")
    if "dp_red_light" in transformed:
        if "dp_red_light" in source:
            classes.append("source_donor_red_timing_invalid")
        else:
            classes.append("bridge_or_sg_introduced_red_invalid")
    for reason in sorted(transformed - {"dp_lane_crossing", "dp_red_light"}):
        classes.append(f"transformed_{reason}")
    if row["transformed_hard_feasible"] and not row["progress_feasible"]:
        classes.append("hard_feasible_but_underprogress")
    if row["transformed_hard_feasible"] and row["progress_feasible"] and not row[
        "comfort_admissible"
    ]:
        classes.extend(_comfort_failure_classes(row))
    if not classes and row["comfort_admissible"]:
        classes.append("admissible_support")
    elif not classes:
        classes.append("unclassified_lower_red_failure")
    return classes


def sg_effect_classes(row: dict[str, Any]) -> list[str]:
    if not row["lower_union_red"]:
        return []
    sg = set(row["transformed_hard_reasons"])
    no_sg = set(row["transformed_no_sg_hard_reasons"])
    introduced = sg - no_sg
    removed = no_sg - sg
    classes = [f"sg_introduced_{reason}" for reason in sorted(introduced)]
    classes.extend(f"sg_removed_{reason}" for reason in sorted(removed))
    if row["transformed_no_sg_hard_feasible"] and not row["transformed_hard_feasible"]:
        classes.append("sg_changed_hard_feasible_to_infeasible")
    return classes


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    decision = report["final_decision"]
    lines = [
        "# World-Frame Bridge Failure Attribution",
        "",
        "This is a read-only fixed-snapshot attribution. It is not replay, not training, and not an online selector.",
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
        f"| Lower-red rows | {records['lower_union_red_rows']} |",
        f"| Lower-red hard-failed rows | {records['lower_union_red_hard_failed_rows']} |",
        f"| Lower-red hard-supported rows | {records['lower_union_red_hard_supported_rows']} |",
        f"| Lower-red comfort-admissible rows | {records['lower_union_red_comfort_admissible_rows']} |",
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
            f"- Transformed hard reasons: `{report['transformed_hard_reason_counts']}`",
            f"- Source donor hard reasons: `{report['source_donor_hard_reason_counts']}`",
            f"- SG effect classes: `{report['sg_effect_counts']}`",
            f"- Comfort blocker counts: `{report['comfort_blocker_counts']}`",
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


def _config_from_screen(screen: dict[str, Any]) -> WorldFrameBridgeConfig:
    raw = screen.get("config") or {}
    return WorldFrameBridgeConfig(
        preserve_steps=int(raw.get("preserve_steps", 1)),
        bridge_steps=int(raw.get("bridge_steps", 10)),
        donor_pool=str(raw.get("donor_pool", "lower_logged_union_red")),
        heading_mode=str(raw.get("heading_mode", "world_donor_tail")),
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
        shadow_rule_enabled=bool(raw.get("shadow_rule_enabled", False)),
        shadow_progress_loss_budget_m=float(
            raw.get("shadow_progress_loss_budget_m", 1.0)
        ),
        shadow_smoothness_loss_budget=float(
            raw.get("shadow_smoothness_loss_budget", 0.5)
        ),
    )


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
    hard_feasible: bool,
    lower_union_red: bool,
    config: WorldFrameBridgeConfig,
) -> bool:
    if not hard_feasible or not lower_union_red:
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
        classes.append("comfort_blocked_progress_loss")
    if row["smoothness_loss"] > 1.0 + TOL:
        classes.append("comfort_blocked_smoothness_loss")
    if delta["command_jerk_worse_mps3"] > TOL:
        classes.append("comfort_blocked_command_jerk")
    if delta["command_lateral_worse_mps2"] > TOL:
        classes.append("comfort_blocked_command_lateral")
    if delta["rollout_distance_loss_m"] > 0.10 + TOL:
        classes.append("comfort_blocked_rollout_distance")
    if delta["rollout_jerk_worse_mps3"] > TOL:
        classes.append("comfort_blocked_rollout_jerk")
    if delta["rollout_lateral_worse_mps2"] > TOL:
        classes.append("comfort_blocked_rollout_lateral")
    return classes or ["comfort_blocked_unknown_budget"]


def _comfort_blocker_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        klass
        for row in rows
        for klass in _comfort_failure_classes(row)
    )
    return dict(sorted(counts.items()))


def _red_delta_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_union_red": _summary(row["selected_union_red"] for row in rows),
        "source_donor_union_red": _summary(row["source_donor_union_red"] for row in rows),
        "transformed_union_red": _summary(row["transformed_union_red"] for row in rows),
        "transformed_no_sg_union_red": _summary(
            row["transformed_no_sg_union_red"] for row in rows
        ),
        "selected_to_transformed_reduction": _summary(
            row["selected_union_red"] - row["transformed_union_red"] for row in rows
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


def _by_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["snapshot_path"], []).append(row)
    report = []
    for path, group in sorted(grouped.items()):
        lower = [row for row in group if row["lower_union_red"]]
        report.append(
            {
                "snapshot_path": path,
                "selection_step": group[0]["selection_step"],
                "candidates": len(group),
                "lower_union_red": len(lower),
                "lower_union_red_hard_feasible": int(
                    sum(row["transformed_hard_feasible"] for row in lower)
                ),
                "comfort_admissible": int(
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
    return report


def _top_examples(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            row["comfort_admissible"],
            row["transformed_hard_feasible"],
            row["transformed_union_red"],
            row["progress_loss_m"],
        ),
    )
    keys = (
        "snapshot_path",
        "selection_step",
        "donor_index",
        "selected_union_red",
        "source_donor_union_red",
        "transformed_union_red",
        "transformed_hard_reasons",
        "source_donor_hard_reasons",
        "failure_classes",
        "sg_effect_classes",
        "progress_loss_m",
        "smoothness_loss",
        "tracker_delta",
        "comfort_admissible",
    )
    return [{key: row[key] for key in keys} for row in sorted_rows[:limit]]


def _decision(
    class_counts: Counter[str],
    *,
    lower_red_count: int,
    support: dict[str, Any],
) -> dict[str, Any]:
    source_invalid = (
        class_counts.get("source_donor_lane_invalid", 0)
        + class_counts.get("source_donor_red_timing_invalid", 0)
    )
    introduced_invalid = (
        class_counts.get("bridge_or_sg_introduced_lane_invalid", 0)
        + class_counts.get("bridge_or_sg_introduced_red_invalid", 0)
    )
    if lower_red_count <= 0:
        status = STATUS_INCONCLUSIVE
        next_step = "No lower-red transformed candidates were available to attribute."
    elif source_invalid >= max(1, introduced_invalid):
        status = STATUS_REJECTED
        next_step = (
            "Reject minor transform tuning; inspect lane-constrained donor "
            "search or route/topology-aware candidate-generation support."
        )
    else:
        status = STATUS_REJECTED
        next_step = (
            "Reject the current bridge and inspect transform geometry, SG, or "
            "postprocess changes before any replay."
        )
    return {
        "status": status,
        "source_invalid_count": int(source_invalid),
        "introduced_invalid_count": int(introduced_invalid),
        "source_screen_support": support,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "next_step": next_step,
    }


def _screen_support(screen: dict[str, Any] | None) -> dict[str, Any]:
    support = (screen or {}).get("support_gate") or {}
    return {
        "status": _deep_get(screen or {}, ("final_decision", "status")),
        "hard_feasible_snapshot_support_rate": support.get(
            "hard_feasible_snapshot_support_rate"
        ),
        "comfort_admissible_snapshot_support_rate": support.get(
            "comfort_admissible_snapshot_support_rate"
        ),
        "min_snapshot_support_rate": support.get("min_snapshot_support_rate"),
    }


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
