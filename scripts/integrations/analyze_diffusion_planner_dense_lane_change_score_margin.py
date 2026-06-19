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
    _is_dense_lane_change,
    _load_records,
    _metrics,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    _fmt,
    _summary,
)


DEFAULT_THRESHOLDS = (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only score-margin sensitivity screen for dense lane-change "
            "loose non-Top1 support. Candidate outcomes are posterior labels "
            "only; runtime predicates use current-tick finite-candidate fields."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--threshold", type=float, action="append", default=[])
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--min_changed_supported_rate", type=float, default=0.05)
    parser.add_argument("--min_progress_delta_ci_low", type=float, default=-0.05)
    parser.add_argument("--min_hard_nonworse_rate", type=float, default=0.99)
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
        thresholds=tuple(args.threshold) if args.threshold else DEFAULT_THRESHOLDS,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        min_changed_supported_rate=args.min_changed_supported_rate,
        min_progress_delta_ci_low=args.min_progress_delta_ci_low,
        min_hard_nonworse_rate=args.min_hard_nonworse_rate,
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
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    min_changed_supported_rate: float = 0.05,
    min_progress_delta_ci_low: float = -0.05,
    min_hard_nonworse_rate: float = 0.99,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("At least one record is required.")
    _validate_thresholds(thresholds)
    if not 0.0 <= min_changed_supported_rate <= 1.0:
        raise ValueError("min_changed_supported_rate must be in [0, 1].")
    if not 0.0 <= min_hard_nonworse_rate <= 1.0:
        raise ValueError("min_hard_nonworse_rate must be in [0, 1].")
    choices = [_choice(record, config) for record in records]
    if fail_on_formal_seeds and any(
        record["context"].get("formal_seed", False) for record in records
    ):
        raise ValueError("Formal seed records are forbidden.")
    grid = [
        _threshold_report(
            records,
            choices,
            float(threshold),
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
            min_changed_supported_rate=min_changed_supported_rate,
            min_progress_delta_ci_low=min_progress_delta_ci_low,
            min_hard_nonworse_rate=min_hard_nonworse_rate,
        )
        for threshold in thresholds
    ]
    return {
        "analysis": {
            "name": "dense_lane_change_score_margin_preservation_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "candidate outcomes are used only after deterministic "
                "score-margin-threshold selection for posterior SafetyCost "
                "evaluation"
            ),
            "rule": {
                "base": "non_top1_progress010_speed020_comfort005",
                "score_margin_filter": (
                    "allow loose support only when score_penalty <= threshold"
                ),
                "loose_config": config.__dict__,
            },
            "thresholds": [float(value) for value in thresholds],
            "gate": {
                "min_changed_supported_rate": float(min_changed_supported_rate),
                "min_progress_delta_ci_low": float(min_progress_delta_ci_low),
                "min_hard_nonworse_rate": float(min_hard_nonworse_rate),
            },
            "math_boundary": (
                "The score-margin filter is a deterministic finite-candidate "
                "selector over fixed current-tick constants: logged CAMP "
                "selection score, DP-prior deviation, planned progress, target "
                "speed, and comfort proxies. It does not alter DP, CAMP atoms, "
                "CAMP weights, or the affine score a_k^T w. It is not "
                "classical Benders decomposition."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, choices),
        "grid": grid,
        "ranked_thresholds": _rank(grid),
        "final_decision": _decision(grid),
    }


def _threshold_report(
    records: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    threshold: float,
    *,
    bootstrap_resamples: int,
    seed: int,
    min_changed_supported_rate: float,
    min_progress_delta_ci_low: float,
    min_hard_nonworse_rate: float,
) -> dict[str, Any]:
    chosen = np.asarray(
        [
            _chosen_for_threshold(record, choice, threshold)
            for record, choice in zip(records, choices)
        ],
        dtype=np.int64,
    )
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    dense_mask = np.asarray([_is_dense_lane_change(record) for record in records], dtype=bool)
    supported_mask = np.asarray([choice["support"] for choice in choices], dtype=bool)
    changed_mask = chosen != selected
    dense_records = _subset(records, dense_mask)
    dense_metrics = _metrics(
        dense_records,
        chosen[dense_mask],
        selected[dense_mask],
        top1[dense_mask],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    supported_records = _subset(records, supported_mask)
    supported_metrics = _metrics(
        supported_records,
        chosen[supported_mask],
        selected[supported_mask],
        top1[supported_mask],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    changed_supported = np.logical_and(changed_mask, supported_mask)
    changed_supported_records = _subset(records, changed_supported)
    changed_supported_metrics = _metrics(
        changed_supported_records,
        chosen[changed_supported],
        selected[changed_supported],
        top1[changed_supported],
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    changed_supported_rate = (
        None
        if int(np.sum(supported_mask)) == 0
        else float(np.mean(changed_mask[supported_mask]))
    )
    gate = _gate(
        dense_metrics,
        supported_metrics,
        changed_supported_rate=changed_supported_rate,
        min_changed_supported_rate=min_changed_supported_rate,
        min_progress_delta_ci_low=min_progress_delta_ci_low,
        min_hard_nonworse_rate=min_hard_nonworse_rate,
    )
    return {
        "threshold": float(threshold),
        "gate": gate,
        "changed_records": int(np.sum(changed_mask)),
        "supported_records": int(np.sum(supported_mask)),
        "changed_supported_records": int(np.sum(changed_supported)),
        "changed_supported_rate": changed_supported_rate,
        "changed_top1_rate": (
            None
            if int(np.sum(changed_mask)) == 0
            else float(np.mean(chosen[changed_mask] == 0))
        ),
        "score_penalty_changed": _summary(
            _score_penalty(choice)
            for choice, changed in zip(choices, changed_mask)
            if changed
        ),
        "dense_lane_change": dense_metrics,
        "supported_target": supported_metrics,
        "changed_supported": changed_supported_metrics,
    }


def _chosen_for_threshold(
    record: dict[str, Any],
    choice: dict[str, Any],
    threshold: float,
) -> int:
    selected = int(record["selected"])
    if not choice["support"]:
        return selected
    penalty = _score_penalty(choice)
    return int(choice["chosen"]) if penalty <= threshold + 1e-12 else selected


def _score_penalty(choice: dict[str, Any]) -> float:
    candidate = choice.get("candidate")
    if not candidate:
        return float("inf")
    return float(candidate["score_penalty"])


def _gate(
    dense_metrics: dict[str, Any],
    supported_metrics: dict[str, Any],
    *,
    changed_supported_rate: float | None,
    min_changed_supported_rate: float,
    min_progress_delta_ci_low: float,
    min_hard_nonworse_rate: float,
) -> dict[str, Any]:
    reasons: list[str] = []
    if changed_supported_rate is None or changed_supported_rate < min_changed_supported_rate:
        reasons.append("insufficient_nontrivial_coverage")
    dense_current = dense_metrics["safety_cost_delta_vs_current"]
    dense_top1 = dense_metrics["safety_cost_delta_vs_top1"]
    supported_current = supported_metrics["safety_cost_delta_vs_current"]
    if dense_current["ci95_high"] is None or dense_current["ci95_high"] >= 0.0:
        reasons.append("dense_safety_vs_current_not_proven")
    if dense_top1["ci95_high"] is None or dense_top1["ci95_high"] >= 0.0:
        reasons.append("dense_safety_vs_top1_not_proven")
    if (
        supported_current["ci95_high"] is None
        or supported_current["ci95_high"] >= 0.0
    ):
        reasons.append("supported_safety_vs_current_not_proven")
    progress = dense_metrics["progress_delta_vs_current"]
    if (
        progress["ci95_low"] is None
        or progress["ci95_low"] < min_progress_delta_ci_low
    ):
        reasons.append("dense_progress_regression")
    if (
        dense_metrics["hard_nonworse_vs_current"] is None
        or dense_metrics["hard_nonworse_vs_current"] < min_hard_nonworse_rate
    ):
        reasons.append("hard_components_worse_vs_current")
    if (
        dense_metrics["hard_nonworse_vs_top1"] is None
        or dense_metrics["hard_nonworse_vs_top1"] < min_hard_nonworse_rate
    ):
        reasons.append("hard_components_worse_vs_top1")
    return {
        "passed": not reasons,
        "reasons": reasons,
    }


def _record_summary(
    records: list[dict[str, Any]],
    choices: list[dict[str, Any]],
) -> dict[str, Any]:
    supported = [choice for choice in choices if choice["support"]]
    target = [choice for choice in choices if choice["target_record"]]
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": int(
            sum(record["context"].get("formal_seed", False) for record in records)
        ),
        "dense_lane_change_records": int(sum(_is_dense_lane_change(record) for record in records)),
        "target_records": len(target),
        "supported_target_records": len(supported),
        "supported_score_penalty": _summary(_score_penalty(choice) for choice in supported),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _rank(grid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in grid:
        dense = item["dense_lane_change"]
        supported = item["supported_target"]
        rows.append(
            {
                "threshold": item["threshold"],
                "passed": item["gate"]["passed"],
                "failure_count": len(item["gate"]["reasons"]),
                "changed_supported_rate": item["changed_supported_rate"],
                "dense_safety_ci_high": dense["safety_cost_delta_vs_current"]["ci95_high"],
                "supported_safety_ci_high": supported["safety_cost_delta_vs_current"]["ci95_high"],
                "dense_top1_ci_high": dense["safety_cost_delta_vs_top1"]["ci95_high"],
                "dense_progress_ci_low": dense["progress_delta_vs_current"]["ci95_low"],
                "hard_nonworse_vs_current": dense["hard_nonworse_vs_current"],
                "changed_supported_records": item["changed_supported_records"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed"],
            row["failure_count"],
            float(row["dense_safety_ci_high"] or 0.0),
            -float(row["changed_supported_rate"] or 0.0),
        ),
    )


def _decision(grid: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [item for item in grid if item["gate"]["passed"]]
    return {
        "status": (
            "score_margin_screen_passed"
            if passing
            else "score_margin_screen_rejected"
        ),
        "passing_thresholds": [item["threshold"] for item in passing],
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": bool(passing),
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "If a threshold passes, implement a default-off selector with "
            "metadata/fail-closed tests before any small non-formal smoke. If "
            "none pass, reject the score-margin preservation route."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Score-Margin Preservation Screen",
        "",
        "This is a read-only threshold screen. It does not train CAMP, change DP, run replay, or authorize online promotion.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Passing thresholds: `{report['final_decision']['passing_thresholds']}`",
        f"- Closed-loop smoke authorized: `{report['final_decision']['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        if isinstance(value, dict):
            lines.append(f"| `{key}.mean` | {_fmt_value(value.get('mean'))} |")
        else:
            lines.append(f"| `{key}` | {_fmt_value(value)} |")
    lines.extend(
        [
            "",
            "## Ranked Thresholds",
            "",
            "| Threshold | Pass | Failures | Changed supported | Dense safety CI high | Supported safety CI high | Dense Top1 CI high | Progress CI low |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_thresholds"]:
        lines.append(
            f"| {_fmt_value(row['threshold'])} | `{row['passed']}` | "
            f"{row['failure_count']} | "
            f"{_fmt_value(row['changed_supported_rate'])} | "
            f"{_fmt_value(row['dense_safety_ci_high'])} | "
            f"{_fmt_value(row['supported_safety_ci_high'])} | "
            f"{_fmt_value(row['dense_top1_ci_high'])} | "
            f"{_fmt_value(row['dense_progress_ci_low'])} |"
        )
    lines.extend(
        [
            "",
            "## Threshold Details",
            "",
        ]
    )
    for item in report["grid"]:
        gate = item["gate"]
        dense = item["dense_lane_change"]
        supported = item["supported_target"]
        lines.extend(
            [
                f"### Threshold `{_fmt_value(item['threshold'])}`",
                "",
                f"- passed: `{gate['passed']}`",
                f"- reasons: `{gate['reasons']}`",
                f"- changed supported records: `{item['changed_supported_records']}`",
                f"- changed supported rate: `{_fmt_value(item['changed_supported_rate'])}`",
                f"- dense safety vs current mean/CI high: `{_fmt_value(dense['safety_cost_delta_vs_current']['mean'])}` / `{_fmt_value(dense['safety_cost_delta_vs_current']['ci95_high'])}`",
                f"- supported safety vs current mean/CI high: `{_fmt_value(supported['safety_cost_delta_vs_current']['mean'])}` / `{_fmt_value(supported['safety_cost_delta_vs_current']['ci95_high'])}`",
                f"- dense progress vs current mean/CI low: `{_fmt_value(dense['progress_delta_vs_current']['mean'])}` / `{_fmt_value(dense['progress_delta_vs_current']['ci95_low'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _subset(records: list[dict[str, Any]], mask: np.ndarray) -> list[dict[str, Any]]:
    return [record for record, keep in zip(records, mask) if bool(keep)]


def _validate_thresholds(thresholds: tuple[float, ...]) -> None:
    if not thresholds:
        raise ValueError("At least one threshold is required.")
    for value in thresholds:
        numeric = float(value)
        if not np.isfinite(numeric) or numeric < 0.0:
            raise ValueError("Every threshold must be finite and nonnegative.")


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
