#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_atom_aware_screen import (  # noqa: E402
    PROTECTIVE_ATOMS,
    _protective_margin,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (  # noqa: E402
    LooseRuleConfig,
    _choice,
    _is_dense_lane_change,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (  # noqa: E402
    _load_records,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    BOOL_FIELDS,
)


EPS = 1e-12
OUTCOME_PROGRESS_LOSS_BUDGET = 0.05


@dataclass(frozen=True)
class GuardConfig:
    name: str
    progress_loss_budget: float
    target_speed_loss_budget: float
    jerk_worse_budget: float
    lateral_worse_budget: float


GUARDS: tuple[GuardConfig, ...] = (
    GuardConfig(
        name="strict_progress005_speed010_comfort_nonworse",
        progress_loss_budget=0.05,
        target_speed_loss_budget=0.10,
        jerk_worse_budget=0.0,
        lateral_worse_budget=0.0,
    ),
    GuardConfig(
        name="loose_progress010_speed020_comfort005",
        progress_loss_budget=0.10,
        target_speed_loss_budget=0.20,
        jerk_worse_budget=0.05,
        lateral_worse_budget=0.05,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DP candidate-support quality diagnostic. It compares "
            "posterior oracle choices with current-tick no-leak reachability "
            "guards to decide whether selector calibration or candidate support "
            "is the limiting factor."
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
    loose_config: LooseRuleConfig = LooseRuleConfig(),
    guards: tuple[GuardConfig, ...] = GUARDS,
    protective_atoms: tuple[str, ...] = PROTECTIVE_ATOMS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    choices = [_choice(record, loose_config) for record in records]
    selection_sets = _selection_sets(
        records,
        choices,
        guards=guards,
        protective_atoms=protective_atoms,
    )
    slices = _slice_reports(
        records,
        selection_sets,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    return {
        "analysis": {
            "name": "dp_candidate_support_quality_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "oracle choices use posterior outcomes only to measure support "
                "quality; no-leak guarded oracle masks use current-tick finite "
                "candidate descriptors only"
            ),
            "loose_rule": loose_config.__dict__,
            "protective_atoms": list(protective_atoms),
            "outcome_progress_loss_budget": OUTCOME_PROGRESS_LOSS_BUDGET,
            "guards": [asdict(guard) for guard in guards],
            "strategies": _strategy_definitions(guards),
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Runtime "
                "descriptors in guarded masks are fixed current-tick "
                "finite-candidate quantities: feasibility, planned progress, "
                "target speed, tracker jerk/lateral proxies, normalized atoms, "
                "logged weights, and logged scores. Posterior outcomes are used "
                "only for oracle support evaluation. CAMP score remains affine "
                "a_k^T w and the simplex/CVaR/L2 robust master remains convex. "
                "This is not classical Benders decomposition because no DP-side "
                "master/subproblem, dual, or valid cuts are constructed."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, formal_seed_records),
        "slices": slices,
        "support_diagnosis": _support_diagnosis(slices),
        "final_decision": _decision(slices),
    }


def _selection_sets(
    records: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    *,
    guards: tuple[GuardConfig, ...],
    protective_atoms: tuple[str, ...],
) -> dict[str, np.ndarray]:
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    result: dict[str, np.ndarray] = {
        "current_camp": selected.copy(),
        "dp_top1": np.zeros(len(records), dtype=np.int64),
        "loose_supported": np.asarray(
            [int(choice["chosen"]) for choice in choices],
            dtype=np.int64,
        ),
        "atom_aware_preserve0": np.asarray(
            [
                _atom_aware_choice(record, choice, protective_atoms)
                for record, choice in zip(records, choices)
            ],
            dtype=np.int64,
        ),
        "oracle_all_candidates": np.asarray(
            [_oracle_choice(record, _branch_mask(record)) for record in records],
            dtype=np.int64,
        ),
        "oracle_outcome_nonregressing": np.asarray(
            [_oracle_choice(record, _outcome_nonregressing_mask(record)) for record in records],
            dtype=np.int64,
        ),
    }
    for guard in guards:
        result[f"oracle_guarded_{guard.name}"] = np.asarray(
            [_oracle_choice(record, _current_tick_guard_mask(record, guard)) for record in records],
            dtype=np.int64,
        )
    return result


def _atom_aware_choice(
    record: dict[str, Any],
    choice: dict[str, Any],
    protective_atoms: tuple[str, ...],
) -> int:
    selected = int(record["selected"])
    if not choice["support"]:
        return selected
    loose = int(choice["chosen"])
    margin = _protective_margin(record, selected, loose, protective_atoms)
    if margin is None or float(margin) > EPS:
        return selected
    return loose


def _branch_mask(record: dict[str, Any]) -> np.ndarray:
    feasible = np.asarray(record["feasible"], dtype=bool).reshape(-1)
    if feasible.any():
        return feasible.copy()
    return np.ones(int(record["candidate_count"]), dtype=bool)


def _outcome_nonregressing_mask(record: dict[str, Any]) -> np.ndarray:
    selected = int(record["selected"])
    mask = _branch_mask(record)
    selected_outcome = record["outcomes"][selected]
    selected_progress = float(record["outcome_progress"][selected])
    selected_jerk = _outcome_float(selected_outcome, "mean_jerk_mps3")
    selected_lateral = _outcome_float(
        selected_outcome,
        "mean_lateral_acceleration_mps2",
    )
    for idx, outcome in enumerate(record["outcomes"]):
        if not mask[idx]:
            continue
        progress_ok = (
            float(record["outcome_progress"][idx])
            >= selected_progress - OUTCOME_PROGRESS_LOSS_BUDGET - EPS
        )
        jerk_ok = _outcome_float(outcome, "mean_jerk_mps3") <= selected_jerk + EPS
        lateral_ok = (
            _outcome_float(outcome, "mean_lateral_acceleration_mps2")
            <= selected_lateral + EPS
        )
        hard_ok = _hard_nonworse(outcome, selected_outcome)
        mask[idx] = bool(progress_ok and jerk_ok and lateral_ok and hard_ok)
    mask[selected] = True
    return mask


def _current_tick_guard_mask(
    record: dict[str, Any],
    guard: GuardConfig,
) -> np.ndarray:
    selected = int(record["selected"])
    mask = _branch_mask(record)
    progress = np.asarray(record["planned_progress"], dtype=np.float64)
    speed = np.asarray(record["target_speed"], dtype=np.float64)
    jerk = np.asarray(record["tracker_jerk"], dtype=np.float64)
    lateral = np.asarray(record["tracker_lateral"], dtype=np.float64)
    progress_loss = np.maximum(progress[selected] - progress, 0.0)
    speed_loss = np.maximum(speed[selected] - speed, 0.0)
    jerk_worse = np.maximum(jerk - jerk[selected], 0.0)
    lateral_worse = np.maximum(lateral - lateral[selected], 0.0)
    mask &= progress_loss <= guard.progress_loss_budget + EPS
    mask &= speed_loss <= guard.target_speed_loss_budget + EPS
    mask &= jerk_worse <= guard.jerk_worse_budget + EPS
    mask &= lateral_worse <= guard.lateral_worse_budget + EPS
    mask[selected] = True
    return mask


def _oracle_choice(record: dict[str, Any], mask: np.ndarray) -> int:
    selected = int(record["selected"])
    valid = np.flatnonzero(np.asarray(mask, dtype=bool).reshape(-1))
    if valid.size == 0:
        return selected
    costs = np.asarray(record["safety_cost"], dtype=np.float64)
    progress = np.asarray(record["outcome_progress"], dtype=np.float64)
    return int(
        sorted(
            valid.tolist(),
            key=lambda idx: (
                float(costs[idx]),
                -float(progress[idx]),
                idx != selected,
                idx,
            ),
        )[0]
    )


def _slice_reports(
    records: list[dict[str, Any]],
    selection_sets: dict[str, np.ndarray],
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    dense_mask = np.asarray([_is_dense_lane_change(record) for record in records], dtype=bool)
    normal_mask = ~dense_mask
    return {
        "all": _strategy_reports(
            records,
            np.ones(len(records), dtype=bool),
            selection_sets,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "dense_lane_change": _strategy_reports(
            records,
            dense_mask,
            selection_sets,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "normal": _strategy_reports(
            records,
            normal_mask,
            selection_sets,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
    }


def _strategy_reports(
    records: list[dict[str, Any]],
    mask: np.ndarray,
    selection_sets: dict[str, np.ndarray],
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    subset = _subset(records, mask)
    selected = np.asarray([record["selected"] for record in subset], dtype=np.int64)
    reports = {}
    for name, choices in selection_sets.items():
        reports[name] = _metrics(
            subset,
            np.asarray(choices, dtype=np.int64)[mask],
            selected,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
    return {
        "records": len(subset),
        "strategies": reports,
    }


def _metrics(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    if not records:
        empty = _empty_summary()
        return {
            "records": 0,
            "changed_rate": None,
            "improvement_rate": None,
            "regression_rate": None,
            "progress_regression_rate": None,
            "safety_cost_delta_vs_current": empty,
            "progress_delta_vs_current": empty,
            "mean_jerk_delta_vs_current": empty,
            "mean_lateral_delta_vs_current": empty,
            "hard_nonworse_vs_current": None,
        }
    safety = []
    progress = []
    jerk = []
    lateral = []
    hard = []
    for record, chosen_idx, selected_idx in zip(records, chosen, selected):
        c_idx = int(chosen_idx)
        s_idx = int(selected_idx)
        chosen_outcome = record["outcomes"][c_idx]
        selected_outcome = record["outcomes"][s_idx]
        safety.append(float(record["safety_cost"][c_idx] - record["safety_cost"][s_idx]))
        progress.append(
            float(record["outcome_progress"][c_idx] - record["outcome_progress"][s_idx])
        )
        jerk.append(
            _outcome_float(chosen_outcome, "mean_jerk_mps3")
            - _outcome_float(selected_outcome, "mean_jerk_mps3")
        )
        lateral.append(
            _outcome_float(chosen_outcome, "mean_lateral_acceleration_mps2")
            - _outcome_float(selected_outcome, "mean_lateral_acceleration_mps2")
        )
        hard.append(_hard_nonworse(chosen_outcome, selected_outcome))
    safety_arr = np.asarray(safety, dtype=np.float64)
    progress_arr = np.asarray(progress, dtype=np.float64)
    return {
        "records": len(records),
        "changed_rate": float(np.mean(chosen != selected)),
        "improvement_rate": float(np.mean(safety_arr < -EPS)),
        "regression_rate": float(np.mean(safety_arr > EPS)),
        "progress_regression_rate": float(np.mean(progress_arr < -EPS)),
        "safety_cost_delta_vs_current": _paired_summary(
            safety,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "mean_jerk_delta_vs_current": _paired_summary(
            jerk,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "mean_lateral_delta_vs_current": _paired_summary(
            lateral,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": float(np.mean(hard)),
    }


def _support_diagnosis(slices: dict[str, Any]) -> dict[str, Any]:
    diagnosis = {}
    for slice_name, report in slices.items():
        strategies = report["strategies"]
        diagnosis[slice_name] = {
            "oracle_all_improvement_rate": strategies["oracle_all_candidates"][
                "improvement_rate"
            ],
            "oracle_outcome_nonregressing_improvement_rate": strategies[
                "oracle_outcome_nonregressing"
            ]["improvement_rate"],
            "strict_guarded_improvement_rate": strategies[
                "oracle_guarded_strict_progress005_speed010_comfort_nonworse"
            ]["improvement_rate"],
            "loose_guarded_improvement_rate": strategies[
                "oracle_guarded_loose_progress010_speed020_comfort005"
            ]["improvement_rate"],
            "oracle_all_safety_ci95_high": strategies["oracle_all_candidates"][
                "safety_cost_delta_vs_current"
            ]["ci95_high"],
            "oracle_outcome_nonregressing_safety_ci95_high": strategies[
                "oracle_outcome_nonregressing"
            ]["safety_cost_delta_vs_current"]["ci95_high"],
            "strict_guarded_safety_ci95_high": strategies[
                "oracle_guarded_strict_progress005_speed010_comfort_nonworse"
            ]["safety_cost_delta_vs_current"]["ci95_high"],
            "loose_guarded_safety_ci95_high": strategies[
                "oracle_guarded_loose_progress010_speed020_comfort005"
            ]["safety_cost_delta_vs_current"]["ci95_high"],
        }
    return diagnosis


def _decision(slices: dict[str, Any]) -> dict[str, Any]:
    dense = slices["dense_lane_change"]["strategies"]
    outcome_support = dense["oracle_outcome_nonregressing"]
    strict = dense["oracle_guarded_strict_progress005_speed010_comfort_nonworse"]
    loose = dense["oracle_guarded_loose_progress010_speed020_comfort005"]
    reasons = []
    outcome_pass = _support_pass(outcome_support)
    strict_pass = _support_pass(strict)
    loose_pass = _support_pass(loose)
    if not outcome_pass:
        status = "candidate_pool_outcome_support_insufficient"
        reasons.append("outcome_nonregressing_oracle_not_proven_vs_current")
    elif strict_pass or loose_pass:
        status = "no_leak_guarded_candidate_support_present"
        if strict_pass:
            reasons.append("strict_current_tick_guarded_oracle_passed")
        if loose_pass:
            reasons.append("loose_current_tick_guarded_oracle_passed")
    else:
        status = "no_leak_guarded_candidate_support_insufficient"
        reasons.append("outcome_support_exists_but_current_tick_guards_fail")
    return {
        "status": status,
        "reasons": reasons,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "If no-leak guarded support is present, design a descriptor-only "
            "offline selector approximation against current CAMP. If only "
            "posterior outcome support exists, reject selector calibration and "
            "diagnose candidate/postprocess support. If outcome support is "
            "insufficient, reject the current fixed-DP candidate pool for this "
            "failure mode."
        ),
    }


def _support_pass(metrics: dict[str, Any]) -> bool:
    safety = metrics["safety_cost_delta_vs_current"]
    progress = metrics["progress_delta_vs_current"]
    jerk = metrics["mean_jerk_delta_vs_current"]
    lateral = metrics["mean_lateral_delta_vs_current"]
    return bool(
        safety["ci95_high"] is not None
        and safety["ci95_high"] < 0.0
        and progress["ci95_low"] is not None
        and progress["ci95_low"] >= -OUTCOME_PROGRESS_LOSS_BUDGET
        and jerk["ci95_high"] is not None
        and jerk["ci95_high"] <= 0.0
        and lateral["ci95_high"] is not None
        and lateral["ci95_high"] <= 0.0
        and metrics["hard_nonworse_vs_current"] is not None
        and metrics["hard_nonworse_vs_current"] >= 0.99
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP Candidate Support Quality Diagnostic",
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
            "## Strategy Comparison",
            "",
            "| Slice | Strategy | Changed | Improve | Regress | Safety CI high | Progress CI low | Jerk CI high | Lateral CI high | Hard nonworse |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    strategy_order = (
        "dp_top1",
        "loose_supported",
        "atom_aware_preserve0",
        "oracle_all_candidates",
        "oracle_outcome_nonregressing",
        "oracle_guarded_strict_progress005_speed010_comfort_nonworse",
        "oracle_guarded_loose_progress010_speed020_comfort005",
    )
    for slice_name in ("dense_lane_change", "normal"):
        strategies = report["slices"][slice_name]["strategies"]
        for strategy in strategy_order:
            row = strategies[strategy]
            lines.append(
                f"| `{slice_name}` | `{strategy}` | "
                f"{_fmt(row['changed_rate'])} | "
                f"{_fmt(row['improvement_rate'])} | "
                f"{_fmt(row['regression_rate'])} | "
                f"{_fmt(row['safety_cost_delta_vs_current']['ci95_high'])} | "
                f"{_fmt(row['progress_delta_vs_current']['ci95_low'])} | "
                f"{_fmt(row['mean_jerk_delta_vs_current']['ci95_high'])} | "
                f"{_fmt(row['mean_lateral_delta_vs_current']['ci95_high'])} | "
                f"{_fmt(row['hard_nonworse_vs_current'])} |"
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


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    dense = [_is_dense_lane_change(record) for record in records]
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": formal_seed_records,
        "dense_lane_change_records": int(sum(dense)),
        "normal_records": int(len(records) - sum(dense)),
        "schema_records": int(sum(record["score_schema_available"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _strategy_definitions(guards: tuple[GuardConfig, ...]) -> dict[str, str]:
    result = {
        "current_camp": "logged CAMP selection",
        "dp_top1": "candidate0 from the frozen DP candidate set",
        "loose_supported": "predeclared loose non-Top1 support rule, otherwise current CAMP",
        "atom_aware_preserve0": (
            "loose-supported candidate only when protective contribution margin "
            "over dp_prior_jerk_excess_cost + jerk_early is nonpositive"
        ),
        "oracle_all_candidates": "posterior minimum SafetyCost over branch candidates",
        "oracle_outcome_nonregressing": (
            "posterior minimum SafetyCost among branch candidates that are "
            "posterior nonworse for progress, jerk, lateral, and hard outcomes"
        ),
    }
    for guard in guards:
        result[f"oracle_guarded_{guard.name}"] = (
            "posterior minimum SafetyCost within a current-tick no-leak guard: "
            f"progress loss <= {guard.progress_loss_budget}, target-speed loss "
            f"<= {guard.target_speed_loss_budget}, jerk worse <= "
            f"{guard.jerk_worse_budget}, lateral worse <= {guard.lateral_worse_budget}"
        )
    return result


def _paired_summary(
    values: Any,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    arr = np.asarray(list(values), dtype=np.float64).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return _empty_summary()
    result = {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }
    if bootstrap_resamples <= 0:
        return {**result, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(seed)
    means = np.empty(int(bootstrap_resamples), dtype=np.float64)
    for idx in range(int(bootstrap_resamples)):
        sample = finite[rng.integers(0, finite.size, size=finite.size)]
        means[idx] = float(np.mean(sample))
    return {
        **result,
        "ci95_low": float(np.percentile(means, 2.5)),
        "ci95_high": float(np.percentile(means, 97.5)),
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "mean": None,
        "min": None,
        "p50": None,
        "p95": None,
        "max": None,
        "ci95_low": None,
        "ci95_high": None,
    }


def _hard_nonworse(candidate: dict[str, Any], reference: dict[str, Any]) -> bool:
    return all(
        float(bool(candidate[field])) <= float(bool(reference[field]))
        for field in BOOL_FIELDS
    )


def _outcome_float(outcome: dict[str, Any], field: str) -> float:
    value = float(outcome[field])
    if not np.isfinite(value):
        raise ValueError(f"Outcome field {field!r} must be finite.")
    return value


def _subset(items: list[Any], mask: np.ndarray) -> list[Any]:
    return [item for item, keep in zip(items, mask) if bool(keep)]


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
