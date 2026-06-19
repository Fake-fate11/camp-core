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

from scripts.integrations.analyze_diffusion_planner_candidate_descriptor_audit import (  # noqa: E402
    _descriptors,
)
from scripts.integrations.analyze_diffusion_planner_candidate_support_quality import (  # noqa: E402
    EPS,
    PROTECTIVE_ATOMS,
    _metrics,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (  # noqa: E402
    _is_dense_lane_change,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (  # noqa: E402
    _load_records,
)


COMFORT_ATOMS = (
    "rms_acceleration",
    "jerk_full",
    "planned_lateral_acceleration_cost",
)
DP_PRIOR_ATOMS = ("dp_prior_jerk_excess_cost",)
RED_ATOMS = ("planned_red_light_cost", "red_stopping_margin_cost")
PROGRESS_LOSS_GATE = -0.05
HARD_NONWORSE_GATE = 0.99


@dataclass(frozen=True)
class DescriptorScreenConfig:
    name: str
    progress_loss_budget: float
    target_speed_loss_budget: float
    max_comfort_atom_norm_delta: float
    max_dp_prior_atom_norm_delta: float | None
    max_protective_margin: float | None
    max_score_delta: float | None


SCREENS: tuple[DescriptorScreenConfig, ...] = (
    DescriptorScreenConfig(
        name="strict_comfort_atom_guard",
        progress_loss_budget=0.05,
        target_speed_loss_budget=0.10,
        max_comfort_atom_norm_delta=0.0,
        max_dp_prior_atom_norm_delta=0.0,
        max_protective_margin=0.0,
        max_score_delta=0.25,
    ),
    DescriptorScreenConfig(
        name="balanced_comfort_atom_guard",
        progress_loss_budget=0.10,
        target_speed_loss_budget=0.20,
        max_comfort_atom_norm_delta=0.0,
        max_dp_prior_atom_norm_delta=0.0,
        max_protective_margin=0.0,
        max_score_delta=0.50,
    ),
    DescriptorScreenConfig(
        name="score_tight_comfort_atom_guard",
        progress_loss_budget=0.10,
        target_speed_loss_budget=0.20,
        max_comfort_atom_norm_delta=0.0,
        max_dp_prior_atom_norm_delta=None,
        max_protective_margin=None,
        max_score_delta=0.05,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only descriptor-only offline selector screen. Runtime "
            "selection predicates use current-tick fixed finite-candidate "
            "descriptors only; posterior candidate outcomes are used only "
            "after deterministic selection for evaluation."
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
    screens: tuple[DescriptorScreenConfig, ...] = SCREENS,
    comfort_atoms: tuple[str, ...] = COMFORT_ATOMS,
    dp_prior_atoms: tuple[str, ...] = DP_PRIOR_ATOMS,
    red_atoms: tuple[str, ...] = RED_ATOMS,
    protective_atoms: tuple[str, ...] = PROTECTIVE_ATOMS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    if not screens:
        raise ValueError("At least one descriptor screen is required.")
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    screen_reports = [
        _screen_report(
            records,
            screen,
            comfort_atoms=comfort_atoms,
            dp_prior_atoms=dp_prior_atoms,
            red_atoms=red_atoms,
            protective_atoms=protective_atoms,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        for screen in screens
    ]
    return {
        "analysis": {
            "name": "dp_descriptor_only_offline_selector_screen_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "deterministic selection uses only current-tick finite-candidate "
                "descriptors; posterior outcomes are used only after selection "
                "for offline evaluation"
            ),
            "rule_definition": (
                "For each record, fail closed to logged current CAMP when the "
                "candidate set has no feasible branch, required score-schema "
                "atoms are missing, or no non-selected candidate passes the "
                "predeclared progress, speed, comfort-atom, DP-prior, red-atom, "
                "protective-margin, and score-delta guards. Otherwise select "
                "deterministically by comfort atom sum, protective margin, "
                "DP-prior atom sum, progress loss, speed loss, score delta, "
                "and candidate index."
            ),
            "comfort_atoms": list(comfort_atoms),
            "dp_prior_atoms": list(dp_prior_atoms),
            "red_atoms": list(red_atoms),
            "protective_atoms": list(protective_atoms),
            "screens": [asdict(screen) for screen in screens],
            "gate": {
                "safety_cost_ci95_high_lt": 0.0,
                "progress_delta_ci95_low_ge": PROGRESS_LOSS_GATE,
                "jerk_delta_ci95_high_le": 0.0,
                "lateral_delta_ci95_high_le": 0.0,
                "hard_nonworse_rate_ge": HARD_NONWORSE_GATE,
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Selector "
                "inputs are fixed current-tick finite-candidate quantities: "
                "feasibility, planned progress, target speed, logged affine "
                "CAMP score, normalized atom deltas, atom contribution margins, "
                "and protective margins. Posterior outcomes are evaluation "
                "labels only. CAMP scoring remains affine a_k^T w and the "
                "simplex/CVaR/L2 robust master remains convex. This is not "
                "classical Benders decomposition because no DP-side "
                "master/subproblem, dual, or valid cuts are constructed."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, formal_seed_records),
        "screens": screen_reports,
        "ranked_screens": _rank_screens(screen_reports),
        "final_decision": _decision(screen_reports),
    }


def _screen_report(
    records: list[dict[str, Any]],
    screen: DescriptorScreenConfig,
    *,
    comfort_atoms: tuple[str, ...],
    dp_prior_atoms: tuple[str, ...],
    red_atoms: tuple[str, ...],
    protective_atoms: tuple[str, ...],
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    rows = [
        _select_record(
            record,
            screen,
            comfort_atoms=comfort_atoms,
            dp_prior_atoms=dp_prior_atoms,
            red_atoms=red_atoms,
            protective_atoms=protective_atoms,
        )
        for record in records
    ]
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    chosen = np.asarray([row["chosen"] for row in rows], dtype=np.int64)
    all_mask = np.ones(len(records), dtype=bool)
    dense_mask = np.asarray([_is_dense_lane_change(record) for record in records], dtype=bool)
    normal_mask = ~dense_mask
    report = {
        "name": screen.name,
        "config": asdict(screen),
        "records": _screen_record_summary(records, rows),
        "slices": {
            "all": _slice_metrics(
                records,
                all_mask,
                chosen,
                selected,
                bootstrap_resamples=bootstrap_resamples,
                seed=seed,
            ),
            "dense_lane_change": _slice_metrics(
                records,
                dense_mask,
                chosen,
                selected,
                bootstrap_resamples=bootstrap_resamples,
                seed=seed,
            ),
            "normal": _slice_metrics(
                records,
                normal_mask,
                chosen,
                selected,
                bootstrap_resamples=bootstrap_resamples,
                seed=seed,
            ),
        },
        "stage_counts": _stage_counts(rows),
    }
    report["gate"] = _screen_gate(report)
    return report


def _select_record(
    record: dict[str, Any],
    screen: DescriptorScreenConfig,
    *,
    comfort_atoms: tuple[str, ...],
    dp_prior_atoms: tuple[str, ...],
    red_atoms: tuple[str, ...],
    protective_atoms: tuple[str, ...],
) -> dict[str, Any]:
    selected = int(record["selected"])
    feasible = np.asarray(record["feasible"], dtype=bool).reshape(-1)
    if not feasible.any():
        return _retained(selected, "fallback_no_feasible_candidates")
    if not record["score_schema_available"]:
        return _retained(selected, "missing_score_schema")

    candidates: list[dict[str, Any]] = []
    for candidate in range(int(record["candidate_count"])):
        if candidate == selected or not bool(feasible[candidate]):
            continue
        diagnostics = _candidate_diagnostics(
            record,
            candidate,
            selected,
            comfort_atoms=comfort_atoms,
            dp_prior_atoms=dp_prior_atoms,
            red_atoms=red_atoms,
            protective_atoms=protective_atoms,
        )
        if diagnostics is None:
            continue
        reject_reason = _reject_reason(diagnostics, screen)
        if reject_reason is not None:
            continue
        candidates.append({"candidate": candidate, **diagnostics})
    if not candidates:
        return _retained(selected, "empty_admissible_set")
    chosen = min(candidates, key=_candidate_sort_key)
    return {
        "chosen": int(chosen["candidate"]),
        "changed": True,
        "stage": "descriptor_candidate",
        "diagnostics": _json_diagnostics(chosen),
    }


def _retained(selected: int, stage: str) -> dict[str, Any]:
    return {
        "chosen": int(selected),
        "changed": False,
        "stage": stage,
        "diagnostics": {},
    }


def _candidate_diagnostics(
    record: dict[str, Any],
    candidate: int,
    selected: int,
    *,
    comfort_atoms: tuple[str, ...],
    dp_prior_atoms: tuple[str, ...],
    red_atoms: tuple[str, ...],
    protective_atoms: tuple[str, ...],
) -> dict[str, float] | None:
    descriptors = _descriptors(record, candidate, selected, protective_atoms)
    required_names = [
        *(f"atom_norm_delta:{name}" for name in comfort_atoms),
        *(f"atom_norm_delta:{name}" for name in dp_prior_atoms),
        *(f"atom_margin:{name}" for name in red_atoms),
    ]
    atom_values = _atom_values(record, candidate, selected, required_names)
    if atom_values is None:
        return None
    comfort_values = [
        atom_values[f"atom_norm_delta:{name}"] for name in comfort_atoms
    ]
    dp_prior_values = [
        atom_values[f"atom_norm_delta:{name}"] for name in dp_prior_atoms
    ]
    red_values = [atom_values[f"atom_margin:{name}"] for name in red_atoms]
    return {
        "progress_loss": float(descriptors["planned_progress_loss"]),
        "target_speed_loss": float(descriptors["target_speed_loss"]),
        "score_delta": float(descriptors["score_delta"]),
        "protective_margin": float(descriptors["protective_margin"]),
        "comfort_atom_norm_max": float(max(comfort_values)),
        "comfort_atom_norm_sum": float(sum(comfort_values)),
        "dp_prior_atom_norm_max": float(max(dp_prior_values)),
        "dp_prior_atom_norm_sum": float(sum(dp_prior_values)),
        "red_atom_margin_max": float(max(red_values)),
        "red_atom_margin_sum": float(sum(red_values)),
    }


def _atom_values(
    record: dict[str, Any],
    candidate: int,
    selected: int,
    names: list[str],
) -> dict[str, float] | None:
    atom_names = list(record["score_atom_names"])
    normalized = np.asarray(record["score_normalized_atoms"], dtype=np.float64)
    contributions = np.asarray(record["score_contributions"], dtype=np.float64)
    result: dict[str, float] = {}
    for full_name in names:
        prefix, atom_name = full_name.split(":", 1)
        if atom_name not in atom_names:
            return None
        atom_index = atom_names.index(atom_name)
        if prefix == "atom_norm_delta":
            value = normalized[candidate, atom_index] - normalized[selected, atom_index]
        elif prefix == "atom_margin":
            value = contributions[candidate, atom_index] - contributions[selected, atom_index]
        else:
            raise ValueError(f"Unsupported atom value prefix: {prefix}")
        if not np.isfinite(value):
            return None
        result[full_name] = float(value)
    return result


def _reject_reason(
    diagnostics: dict[str, float],
    screen: DescriptorScreenConfig,
) -> str | None:
    if diagnostics["progress_loss"] > screen.progress_loss_budget + EPS:
        return "progress_loss"
    if diagnostics["target_speed_loss"] > screen.target_speed_loss_budget + EPS:
        return "target_speed_loss"
    if diagnostics["comfort_atom_norm_max"] > screen.max_comfort_atom_norm_delta + EPS:
        return "comfort_atom_norm_delta"
    if (
        screen.max_dp_prior_atom_norm_delta is not None
        and diagnostics["dp_prior_atom_norm_max"]
        > screen.max_dp_prior_atom_norm_delta + EPS
    ):
        return "dp_prior_atom_norm_delta"
    if diagnostics["red_atom_margin_max"] > EPS:
        return "red_atom_margin"
    if (
        screen.max_protective_margin is not None
        and diagnostics["protective_margin"] > screen.max_protective_margin + EPS
    ):
        return "protective_margin"
    if (
        screen.max_score_delta is not None
        and diagnostics["score_delta"] > screen.max_score_delta + EPS
    ):
        return "score_delta"
    return None


def _candidate_sort_key(row: dict[str, Any]) -> tuple[float, ...]:
    return (
        float(row["comfort_atom_norm_sum"]),
        float(row["protective_margin"]),
        float(row["dp_prior_atom_norm_sum"]),
        float(row["progress_loss"]),
        float(row["target_speed_loss"]),
        float(row["score_delta"]),
        float(row["candidate"]),
    )


def _json_diagnostics(row: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(row[key])
        for key in (
            "progress_loss",
            "target_speed_loss",
            "score_delta",
            "protective_margin",
            "comfort_atom_norm_max",
            "comfort_atom_norm_sum",
            "dp_prior_atom_norm_max",
            "dp_prior_atom_norm_sum",
            "red_atom_margin_max",
            "red_atom_margin_sum",
        )
    }


def _slice_metrics(
    records: list[dict[str, Any]],
    mask: np.ndarray,
    chosen: np.ndarray,
    selected: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    subset = _subset(records, mask)
    return _metrics(
        subset,
        chosen[mask],
        selected[mask],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )


def _screen_gate(report: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    dense = report["slices"]["dense_lane_change"]
    all_records = report["slices"]["all"]
    if dense["records"] == 0:
        failures.append("no_dense_lane_change_records")
    if dense["changed_rate"] is None or dense["changed_rate"] <= 0.0:
        failures.append("dense_no_changes")
    for slice_name, metrics in (
        ("dense", dense),
        ("all", all_records),
    ):
        if not _ci_lt(metrics["safety_cost_delta_vs_current"], 0.0, "ci95_high"):
            failures.append(f"{slice_name}_safety_not_proven")
        if not _ci_ge(
            metrics["progress_delta_vs_current"],
            PROGRESS_LOSS_GATE,
            "ci95_low",
        ):
            failures.append(f"{slice_name}_progress_regression")
        if not _ci_le(metrics["mean_jerk_delta_vs_current"], 0.0, "ci95_high"):
            failures.append(f"{slice_name}_jerk_regression")
        if not _ci_le(metrics["mean_lateral_delta_vs_current"], 0.0, "ci95_high"):
            failures.append(f"{slice_name}_lateral_regression")
        hard = metrics["hard_nonworse_vs_current"]
        if hard is None or float(hard) < HARD_NONWORSE_GATE:
            failures.append(f"{slice_name}_hard_regression")
    return {
        "pass": not failures,
        "failures": failures,
    }


def _ci_lt(summary: dict[str, Any], threshold: float, key: str) -> bool:
    value = summary.get(key)
    return bool(value is not None and float(value) < threshold)


def _ci_le(summary: dict[str, Any], threshold: float, key: str) -> bool:
    value = summary.get(key)
    return bool(value is not None and float(value) <= threshold)


def _ci_ge(summary: dict[str, Any], threshold: float, key: str) -> bool:
    value = summary.get(key)
    return bool(value is not None and float(value) >= threshold)


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    dense = [_is_dense_lane_change(record) for record in records]
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": formal_seed_records,
        "dense_lane_change_records": int(sum(dense)),
        "normal_records": int(len(records) - sum(dense)),
        "schema_records": int(sum(record["score_schema_available"] for record in records)),
        "fallback_records": int(
            sum(not np.asarray(record["feasible"], dtype=bool).any() for record in records)
        ),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _screen_record_summary(
    records: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    changed = [row for row in rows if row["changed"]]
    dense_changed = [
        row for record, row in zip(records, rows) if row["changed"] and _is_dense_lane_change(record)
    ]
    return {
        "total": len(records),
        "changed": len(changed),
        "dense_changed": len(dense_changed),
        "fail_closed": len(records) - len(changed),
    }


def _stage_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        stage = str(row["stage"])
        result[stage] = result.get(stage, 0) + 1
    return dict(sorted(result.items()))


def _rank_screens(screen_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in screen_reports:
        dense = report["slices"]["dense_lane_change"]
        safety = dense["safety_cost_delta_vs_current"]
        rows.append(
            {
                "name": report["name"],
                "pass": report["gate"]["pass"],
                "dense_changed_rate": dense["changed_rate"],
                "dense_safety_ci95_high": safety["ci95_high"],
                "dense_safety_mean": safety["mean"],
                "failures": report["gate"]["failures"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not bool(row["pass"]),
            float("inf")
            if row["dense_safety_ci95_high"] is None
            else float(row["dense_safety_ci95_high"]),
            -float(row["dense_changed_rate"] or 0.0),
            row["name"],
        ),
    )


def _decision(screen_reports: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [report["name"] for report in screen_reports if report["gate"]["pass"]]
    if passing:
        status = "descriptor_only_offline_screen_passed"
        reasons = [f"{name}_passed_predeclared_gate" for name in passing]
        next_step = (
            "Inspect the passing offline screen, confirm latency impact is "
            "negligible, then consider a default-off non-formal paired smoke. "
            "Do not use formal seeds or promote online until that smoke passes."
        )
    else:
        status = "descriptor_only_offline_screen_rejected"
        reasons = sorted(
            {
                reason
                for report in screen_reports
                for reason in report["gate"]["failures"]
            }
        )
        next_step = (
            "Reject this fixed-DP descriptor-only selector route unless a new "
            "current-tick descriptor is justified. Move to candidate/postprocess "
            "support analysis while keeping DP frozen."
        )
    return {
        "status": status,
        "reasons": reasons,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": bool(passing),
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def _subset(records: list[dict[str, Any]], mask: np.ndarray) -> list[dict[str, Any]]:
    return [record for record, keep in zip(records, mask) if bool(keep)]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP Descriptor-Only Offline Selector Screen",
        "",
        "This is a read-only offline screen. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
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
            "## Screen Results",
            "",
            "| Screen | Pass | Changed | Dense changed | Dense safety CI high | Dense progress CI low | Dense jerk CI high | Dense lateral CI high | Dense hard nonworse | Failures |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for screen in report["screens"]:
        dense = screen["slices"]["dense_lane_change"]
        lines.append(
            f"| `{screen['name']}` | `{str(screen['gate']['pass']).lower()}` | "
            f"{screen['records']['changed']} | "
            f"{screen['records']['dense_changed']} | "
            f"{_fmt(dense['safety_cost_delta_vs_current']['ci95_high'])} | "
            f"{_fmt(dense['progress_delta_vs_current']['ci95_low'])} | "
            f"{_fmt(dense['mean_jerk_delta_vs_current']['ci95_high'])} | "
            f"{_fmt(dense['mean_lateral_delta_vs_current']['ci95_high'])} | "
            f"{_fmt(dense['hard_nonworse_vs_current'])} | "
            f"`{', '.join(screen['gate']['failures']) or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Stage Counts",
            "",
            "| Screen | Stage counts |",
            "| --- | --- |",
        ]
    )
    for screen in report["screens"]:
        stages = ", ".join(
            f"{key}: {value}" for key, value in screen["stage_counts"].items()
        )
        lines.append(f"| `{screen['name']}` | `{stages}` |")
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


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt(item) for item in value)
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(result):
        return "n/a"
    return f"{result:.6f}"


if __name__ == "__main__":
    main()
