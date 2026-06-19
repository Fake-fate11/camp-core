#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


READY_STATUS = "prefix_lane_pruning_budget_support_present"
REJECT_STATUS = "prefix_lane_pruning_budget_support_insufficient"
SOURCE_CONFLICT_STATUS = "prefix_lane_pruning_budget_source_conflict"


@dataclass(frozen=True)
class PruningBudgetConfig:
    progress_loss_budgets_m: tuple[float, ...] = (2.0, 3.0, 4.0)
    min_snapshot_support_rate: float = 0.25
    max_candidate_fraction_for_pruning: float = 0.50


@dataclass(frozen=True)
class CandidateSubset:
    name: str
    description: str
    predicate: Callable[[dict[str, Any]], bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only pruning and stopping-progress budget audit over a fixed "
            "prefix-lane-projected route/topology screen. It consumes existing "
            "screen and absolute-lateral-guard JSON artifacts and does not run "
            "DP, generate new candidates, or affect selection."
        )
    )
    parser.add_argument("--screen_json", type=Path, required=True)
    parser.add_argument("--absolute_guard_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--progress_loss_budget_m", action="append", type=float)
    parser.add_argument("--min_snapshot_support_rate", type=float, default=0.25)
    parser.add_argument("--max_candidate_fraction_for_pruning", type=float, default=0.50)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PruningBudgetConfig(
        progress_loss_budgets_m=tuple(
            args.progress_loss_budget_m
            if args.progress_loss_budget_m is not None
            else (2.0, 3.0, 4.0)
        ),
        min_snapshot_support_rate=args.min_snapshot_support_rate,
        max_candidate_fraction_for_pruning=args.max_candidate_fraction_for_pruning,
    )
    report = analyze(
        screen_json=args.screen_json,
        absolute_guard_json=args.absolute_guard_json,
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
    absolute_guard_json: Path,
    label: str | None = None,
    config: PruningBudgetConfig = PruningBudgetConfig(),
) -> dict[str, Any]:
    screen = _load_json(screen_json)
    absolute = _load_json(absolute_guard_json)
    return build_report(
        screen=screen,
        absolute=absolute,
        label=label,
        paths={
            "screen_json": str(screen_json),
            "absolute_guard_json": str(absolute_guard_json),
        },
        config=config,
    )


def build_report(
    *,
    screen: dict[str, Any],
    absolute: dict[str, Any],
    label: str | None = None,
    paths: dict[str, Any] | None = None,
    config: PruningBudgetConfig = PruningBudgetConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    rows = _join_rows(screen, absolute)
    conflicts = _source_conflicts(screen, absolute)
    subsets = _candidate_subsets(rows)
    budget_rows = [
        _budget_report(subset, rows, budget, config)
        for subset in subsets
        for budget in config.progress_loss_budgets_m
    ]
    prune_rows = [_pruning_report(subset, rows, config) for subset in subsets]
    decision = _decision(conflicts, budget_rows, prune_rows, config)
    return {
        "analysis": {
            "name": "dp_camp_prefix_lane_pruning_budget_v1",
            "label": label,
            "role": (
                "read-only pruning and stopping-progress budget audit over "
                "fixed prefix-lane-projected route/topology candidates"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "recomputes_dp_reward_or_red_light": False,
            "recomputes_perfect_tracker_proxies": False,
            "math_boundary": (
                "All predicates use fixed current-tick finite-candidate rows "
                "from the source screen and absolute lateral guard audit. The "
                "audit does not generate trajectories, run DP, use closed-loop "
                "outcomes, modify CAMP weights, or construct a Benders "
                "master/subproblem, dual, or cuts."
            ),
            "paths": paths or {},
        },
        "config": {
            "progress_loss_budgets_m": list(config.progress_loss_budgets_m),
            "min_snapshot_support_rate": config.min_snapshot_support_rate,
            "max_candidate_fraction_for_pruning": (
                config.max_candidate_fraction_for_pruning
            ),
        },
        "source_summaries": {
            "screen": _screen_summary(screen),
            "absolute_guard": _absolute_summary(absolute),
        },
        "records": _record_summary(rows),
        "subset_pruning": prune_rows,
        "budget_sensitivity": budget_rows,
        "top_budget_rows": _top_budget_rows(budget_rows),
        "failure_class_counts": _failure_counts(rows),
        "final_decision": decision,
    }


def _join_rows(
    screen: dict[str, Any],
    absolute: dict[str, Any],
) -> list[dict[str, Any]]:
    absolute_by_key = {
        _row_key(row): row
        for row in absolute.get("rows", [])
        if isinstance(row, dict)
    }
    joined = []
    for source_row in screen.get("rows", []):
        if not isinstance(source_row, dict):
            continue
        for candidate in source_row.get("candidate_rows", []):
            if not isinstance(candidate, dict):
                continue
            key = _row_key(candidate)
            guard = absolute_by_key.get(key)
            if guard is None:
                raise ValueError(f"absolute guard row missing for {key}.")
            meta = candidate.get("candidate_meta", {})
            if not isinstance(meta, dict):
                raise ValueError("candidate_meta must be a dict.")
            joined.append(
                {
                    "snapshot_path": candidate["snapshot_path"],
                    "selection_step": int(candidate["selection_step"]),
                    "candidate_index": int(candidate["candidate_index"]),
                    "candidate_meta": meta,
                    "lower_union_red": bool(candidate.get("lower_union_red")),
                    "hard_feasible": bool(candidate.get("hard_feasible")),
                    "progress_feasible": bool(candidate.get("progress_feasible")),
                    "comfort_admissible": bool(candidate.get("comfort_admissible")),
                    "progress_loss_m": _float_or_none(
                        candidate.get("progress_loss_m")
                    ),
                    "smoothness_loss": _float_or_none(
                        candidate.get("smoothness_loss")
                    ),
                    "tracker_delta": candidate.get("tracker_delta", {}),
                    "failure_classes": list(candidate.get("failure_classes", [])),
                    "absolute_lateral_guard_pass": bool(
                        guard.get("absolute_lateral_guard_pass")
                    ),
                    "candidate_tracker": guard.get("candidate_tracker", {}),
                }
            )
    return joined


def _candidate_subsets(rows: list[dict[str, Any]]) -> list[CandidateSubset]:
    # Keep this list deliberately small and interpretable. These subsets reflect
    # the prior diagnostic direction: reduce the 54-candidate per-snapshot grid
    # before trying any new replay.
    return (
        CandidateSubset(
            "all_prefix_lane_projected",
            "all generated prefix-lane-projected candidates",
            lambda row: True,
        ),
        CandidateSubset(
            "prefix3_margin2_offsets1_0p5",
            "prefix 3, red margin 2m, offsets 1.0 or 0.5",
            lambda row: _meta(row, "prefix_steps") == 3
            and _meta(row, "red_stop_margin_m") == 2.0
            and _meta(row, "lateral_offset_scale") in {1.0, 0.5},
        ),
        CandidateSubset(
            "prefix3_margin2_offset1",
            "prefix 3, red margin 2m, offset 1.0 only",
            lambda row: _meta(row, "prefix_steps") == 3
            and _meta(row, "red_stop_margin_m") == 2.0
            and _meta(row, "lateral_offset_scale") == 1.0,
        ),
        CandidateSubset(
            "prefix3_margin2_offset0p5",
            "prefix 3, red margin 2m, offset 0.5 only",
            lambda row: _meta(row, "prefix_steps") == 3
            and _meta(row, "red_stop_margin_m") == 2.0
            and _meta(row, "lateral_offset_scale") == 0.5,
        ),
        CandidateSubset(
            "prefix3_all_margins_offsets1_0p5",
            "prefix 3, all margins, offsets 1.0 or 0.5",
            lambda row: _meta(row, "prefix_steps") == 3
            and _meta(row, "lateral_offset_scale") in {1.0, 0.5},
        ),
        CandidateSubset(
            "prefix3_or5_margin2_offsets1_0p5",
            "prefix 3 or 5, red margin 2m, offsets 1.0 or 0.5",
            lambda row: _meta(row, "prefix_steps") in {3, 5}
            and _meta(row, "red_stop_margin_m") == 2.0
            and _meta(row, "lateral_offset_scale") in {1.0, 0.5},
        ),
    )


def _pruning_report(
    subset: CandidateSubset,
    rows: list[dict[str, Any]],
    config: PruningBudgetConfig,
) -> dict[str, Any]:
    selected = [row for row in rows if subset.predicate(row)]
    baseline = [row for row in rows if _support_base(row)]
    support = [row for row in selected if _support_base(row)]
    baseline_snapshots = _snapshot_count(baseline)
    support_snapshots = _snapshot_count(support)
    candidate_fraction = _rate(len(selected), len(rows))
    return {
        "subset": subset.name,
        "description": subset.description,
        "candidate_rows": len(selected),
        "candidate_fraction": candidate_fraction,
        "support_rows": len(support),
        "support_snapshots": support_snapshots,
        "baseline_support_snapshots": baseline_snapshots,
        "support_snapshot_rate": _rate(support_snapshots, max(1, baseline_snapshots)),
        "absolute_support_rate_over_generated_snapshots": _rate(
            support_snapshots,
            max(1, _snapshot_count(rows)),
        ),
        "keeps_all_baseline_absolute_support": (
            baseline_snapshots > 0 and support_snapshots == baseline_snapshots
        ),
        "candidate_fraction_pass": (
            candidate_fraction <= config.max_candidate_fraction_for_pruning
        ),
    }


def _budget_report(
    subset: CandidateSubset,
    rows: list[dict[str, Any]],
    budget: float,
    config: PruningBudgetConfig,
) -> dict[str, Any]:
    selected = [row for row in rows if subset.predicate(row)]
    support = [row for row in selected if _budget_support(row, budget)]
    support_snapshots = _snapshot_count(support)
    generated_snapshots = max(1, _snapshot_count(rows))
    support_rate = _rate(support_snapshots, generated_snapshots)
    candidate_fraction = _rate(len(selected), len(rows))
    return {
        "subset": subset.name,
        "description": subset.description,
        "progress_loss_budget_m": float(budget),
        "candidate_rows": len(selected),
        "candidate_fraction": candidate_fraction,
        "budget_support_rows": len(support),
        "budget_support_snapshots": support_snapshots,
        "budget_support_snapshot_rate": support_rate,
        "support_pass": support_rate >= config.min_snapshot_support_rate,
        "candidate_fraction_pass": (
            candidate_fraction <= config.max_candidate_fraction_for_pruning
        ),
        "mean_progress_loss_m": _mean(
            row.get("progress_loss_m") for row in support
        ),
        "p95_abs_command_lateral_mps2": _percentile(
            _candidate_tracker_values(support, "command_lateral_mps2"),
            95.0,
        ),
        "p95_abs_rollout_lateral_mps2": _percentile(
            _candidate_tracker_values(support, "rollout_lateral_mps2"),
            95.0,
        ),
        "p95_abs_command_jerk_mps3": _percentile(
            _candidate_tracker_values(support, "command_jerk_mps3"),
            95.0,
        ),
        "p95_abs_rollout_jerk_mps3": _percentile(
            _candidate_tracker_values(support, "rollout_jerk_mps3"),
            95.0,
        ),
    }


def _decision(
    conflicts: list[str],
    budget_rows: list[dict[str, Any]],
    prune_rows: list[dict[str, Any]],
    config: PruningBudgetConfig,
) -> dict[str, Any]:
    if conflicts:
        status = SOURCE_CONFLICT_STATUS
        next_step = "Fix source artifact conflicts before interpreting pruning budgets."
    else:
        passing_budget = [
            row for row in budget_rows if row["support_pass"] and row["candidate_fraction_pass"]
        ]
        pruning = [
            row
            for row in prune_rows
            if row["keeps_all_baseline_absolute_support"]
            and row["candidate_fraction_pass"]
        ]
        if passing_budget or pruning:
            status = READY_STATUS
            next_step = (
                "Use the reported subset only as an offline design input. "
                "A progress-aware generator or no-leak selector screen is still "
                "required before replay."
            )
        else:
            status = REJECT_STATUS
            next_step = (
                "Pruning or stopping-progress budget sensitivity does not "
                "produce enough support; design a progress-aware stop target "
                "before additional replay."
            )
    return {
        "status": status,
        "offline_design_input_authorized": status == READY_STATUS,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "source_authorization_conflicts": conflicts,
        "min_snapshot_support_rate": config.min_snapshot_support_rate,
        "max_candidate_fraction_for_pruning": (
            config.max_candidate_fraction_for_pruning
        ),
        "next_step": next_step,
    }


def _source_conflicts(screen: dict[str, Any], absolute: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    screen_decision = screen.get("final_decision") or {}
    absolute_decision = absolute.get("final_decision") or {}
    if (screen.get("analysis") or {}).get("name") != (
        "dp_camp_route_topology_candidate_screen_v1"
    ):
        conflicts.append("screen:unexpected_analysis")
    if screen.get("config", {}).get("generator_policy") != (
        "prefix_lane_projected_red_stop"
    ):
        conflicts.append("screen:not_prefix_lane_projected")
    for key in (
        "closed_loop_smoke_authorized",
        "online_selector_authorized",
        "full36_authorized",
        "formal_seeds_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
    ):
        if screen_decision.get(key):
            conflicts.append(f"screen:{key}")
        if absolute_decision.get(key):
            conflicts.append(f"absolute_guard:{key}")
    return conflicts


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Prefix Lane Pruning/Budget Audit",
        "",
        "This is a read-only fixed-artifact diagnostic. It does not run replay, "
        "generate candidates, modify DP, or authorize online selection.",
        "",
        "## Decision",
        "",
        f"- Status: `{decision['status']}`",
        f"- Offline design input authorized: `{str(decision['offline_design_input_authorized']).lower()}`",
        f"- Closed-loop smoke authorized: `{str(decision['closed_loop_smoke_authorized']).lower()}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Records",
        "",
    ]
    for key, value in report["records"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Subset Pruning", ""])
    lines.append(
        "| Subset | Rows | Fraction | Support rows | Support snapshots | Keeps all baseline support |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for row in report["subset_pruning"]:
        lines.append(
            "| {subset} | {candidate_rows} | {candidate_fraction:.6f} | "
            "{support_rows} | {support_snapshots} | {keeps} |".format(
                subset=row["subset"],
                candidate_rows=row["candidate_rows"],
                candidate_fraction=row["candidate_fraction"],
                support_rows=row["support_rows"],
                support_snapshots=row["support_snapshots"],
                keeps=str(row["keeps_all_baseline_absolute_support"]).lower(),
            )
        )
    lines.extend(["", "## Budget Sensitivity", ""])
    lines.append(
        "| Subset | Budget m | Rows | Fraction | Support rows | Support snapshots | Rate | Pass |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in report["budget_sensitivity"]:
        lines.append(
            "| {subset} | {budget:.1f} | {candidate_rows} | {fraction:.6f} | "
            "{rows} | {snapshots} | {rate:.6f} | {passed} |".format(
                subset=row["subset"],
                budget=row["progress_loss_budget_m"],
                candidate_rows=row["candidate_rows"],
                fraction=row["candidate_fraction"],
                rows=row["budget_support_rows"],
                snapshots=row["budget_support_snapshots"],
                rate=row["budget_support_snapshot_rate"],
                passed=str(row["support_pass"]).lower(),
            )
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"]])
    return "\n".join(lines) + "\n"


def _record_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_rows": len(rows),
        "snapshots": _snapshot_count(rows),
        "lower_union_red_rows": sum(row["lower_union_red"] for row in rows),
        "hard_feasible_rows": sum(row["hard_feasible"] for row in rows),
        "absolute_lateral_guard_rows": sum(
            row["absolute_lateral_guard_pass"] for row in rows
        ),
        "base_support_rows": sum(_support_base(row) for row in rows),
        "base_support_snapshots": _snapshot_count(
            [row for row in rows if _support_base(row)]
        ),
    }


def _screen_summary(screen: dict[str, Any]) -> dict[str, Any]:
    decision = screen.get("final_decision") or {}
    records = screen.get("records") or {}
    support = screen.get("support_gate") or {}
    return {
        "analysis_name": (screen.get("analysis") or {}).get("name"),
        "status": decision.get("status"),
        "generator_policy": (screen.get("config") or {}).get("generator_policy"),
        "generated_candidate_rows": records.get("generated_candidate_rows"),
        "lower_union_red_hard_feasible_rows": records.get(
            "lower_union_red_hard_feasible_rows"
        ),
        "lower_union_red_progress_feasible_rows": records.get(
            "lower_union_red_progress_feasible_rows"
        ),
        "lower_union_red_comfort_admissible_rows": records.get(
            "lower_union_red_comfort_admissible_rows"
        ),
        "hard_feasible_snapshot_support_rate": support.get(
            "hard_feasible_snapshot_support_rate"
        ),
        "comfort_admissible_snapshot_support_rate": support.get(
            "comfort_admissible_snapshot_support_rate"
        ),
    }


def _absolute_summary(absolute: dict[str, Any]) -> dict[str, Any]:
    decision = absolute.get("final_decision") or {}
    records = absolute.get("records") or {}
    support = absolute.get("support_gate") or {}
    return {
        "analysis_name": (absolute.get("analysis") or {}).get("name"),
        "status": decision.get("status"),
        "absolute_lateral_guard_rows": records.get("absolute_lateral_guard_rows"),
        "absolute_lateral_guard_snapshot_support_rate": support.get(
            "absolute_lateral_guard_snapshot_support_rate"
        ),
    }


def _row_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("snapshot_path")), int(row.get("candidate_index", -1)))


def _support_base(row: dict[str, Any]) -> bool:
    return bool(
        row["lower_union_red"]
        and row["hard_feasible"]
        and row["progress_feasible"]
        and row["absolute_lateral_guard_pass"]
    )


def _budget_support(row: dict[str, Any], budget: float) -> bool:
    progress = row.get("progress_loss_m")
    return bool(
        _support_base(row)
        and progress is not None
        and float(progress) <= float(budget) + 1e-12
    )


def _meta(row: dict[str, Any], key: str) -> Any:
    value = row.get("candidate_meta", {}).get(key)
    if isinstance(value, float):
        return round(value, 9)
    return value


def _snapshot_count(rows: list[dict[str, Any]]) -> int:
    return len({str(row["snapshot_path"]) for row in rows})


def _rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _candidate_tracker_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get("candidate_tracker", {}).get(key)
        converted = _float_or_none(value)
        if converted is not None:
            values.append(converted)
    return values


def _mean(values: Any) -> float | None:
    finite = [float(value) for value in values if value is not None]
    return sum(finite) / len(finite) if finite else None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(float(value) for value in values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * float(percentile) / 100.0
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    fraction = position - low
    return sorted_values[low] * (1.0 - fraction) + sorted_values[high] * fraction


def _top_budget_rows(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            not row["support_pass"],
            -row["budget_support_snapshot_rate"],
            row["candidate_fraction"],
            row["progress_loss_budget_m"],
            row["subset"],
        ),
    )
    return sorted_rows[:limit]


def _failure_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(Counter(klass for row in rows for klass in row["failure_classes"]).items())
    )


def _validate_config(config: PruningBudgetConfig) -> None:
    if not 0.0 <= float(config.min_snapshot_support_rate) <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0,1].")
    if not 0.0 < float(config.max_candidate_fraction_for_pruning) <= 1.0:
        raise ValueError("max_candidate_fraction_for_pruning must be in (0,1].")
    for value in config.progress_loss_budgets_m:
        if not float(value) >= 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


if __name__ == "__main__":
    main()
