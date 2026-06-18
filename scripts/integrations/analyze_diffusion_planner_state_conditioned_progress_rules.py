#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_dp_prior_completion_joint_audit import (  # noqa: E402
    _choice_metrics,
    _load_records,
    _record_indices,
    _records_by_bucket,
)


DEFAULT_TARGET_BUCKETS = ("normal", "red_light_turn", "sharp_turn")
PROGRESS_THRESHOLDS = (0.0025, 0.005, 0.01, 0.02)
JERK_TOLERANCES = (0.0, 0.05, 0.1)
LATERAL_TOLERANCES = (0.0, 0.05, 0.1)
SCORE_MARGINS = (0.05, 0.1, float("inf"))


@dataclass(frozen=True)
class Rule:
    progress_gain_threshold: float
    jerk_tolerance: float
    lateral_tolerance: float
    score_margin: float

    @property
    def name(self) -> str:
        return (
            f"progress_ge_{_tag(self.progress_gain_threshold)}"
            f"_jerk_le_{_tag(self.jerk_tolerance)}"
            f"_lat_le_{_tag(self.lateral_tolerance)}"
            f"_score_le_{_tag(self.score_margin)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only state/bucket-conditioned material-progress rule audit. "
            "Rules use current-tick planned progress, tracker jerk/lateral "
            "proxies, and logged CAMP scores only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--target_bucket", action="append", default=None)
    parser.add_argument("--progress_gain_threshold", type=float, action="append", default=[])
    parser.add_argument("--jerk_tolerance", type=float, action="append", default=[])
    parser.add_argument("--lateral_tolerance", type=float, action="append", default=[])
    parser.add_argument("--score_margin", type=float, action="append", default=[])
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--min_progress_delta_ci_low", type=float, default=-0.001)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        label=args.label,
        target_buckets=tuple(args.target_bucket or DEFAULT_TARGET_BUCKETS),
        progress_gain_thresholds=tuple(
            args.progress_gain_threshold or PROGRESS_THRESHOLDS
        ),
        jerk_tolerances=tuple(args.jerk_tolerance or JERK_TOLERANCES),
        lateral_tolerances=tuple(args.lateral_tolerance or LATERAL_TOLERANCES),
        score_margins=tuple(args.score_margin or SCORE_MARGINS),
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        min_progress_delta_ci_low=args.min_progress_delta_ci_low,
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
    label: str | None = None,
    target_buckets: tuple[str, ...] = DEFAULT_TARGET_BUCKETS,
    progress_gain_thresholds: tuple[float, ...] = PROGRESS_THRESHOLDS,
    jerk_tolerances: tuple[float, ...] = JERK_TOLERANCES,
    lateral_tolerances: tuple[float, ...] = LATERAL_TOLERANCES,
    score_margins: tuple[float, ...] = SCORE_MARGINS,
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    min_progress_delta_ci_low: float = -0.001,
) -> dict[str, Any]:
    records = _load_records(paths)
    if not records:
        raise ValueError("No outcome-labeled records were found.")
    for value in (
        *progress_gain_thresholds,
        *jerk_tolerances,
        *lateral_tolerances,
        *score_margins,
    ):
        if value < 0.0:
            raise ValueError("Rule thresholds must be nonnegative.")
    rules = [
        Rule(
            progress_gain_threshold=float(progress),
            jerk_tolerance=float(jerk),
            lateral_tolerance=float(lateral),
            score_margin=float(score),
        )
        for progress, jerk, lateral, score in product(
            progress_gain_thresholds,
            jerk_tolerances,
            lateral_tolerances,
            score_margins,
        )
    ]
    rule_reports = [
        _rule_report(
            records,
            rule,
            target_buckets=target_buckets,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
            min_progress_delta_ci_low=min_progress_delta_ci_low,
        )
        for rule in rules
    ]
    ranked = _rank(rule_reports)
    return {
        "analysis": {
            "name": "dp_camp_state_conditioned_material_progress_rule_audit_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "target_buckets": list(target_buckets),
            "future_outcome_leakage": False,
            "selection_inputs": [
                "selection_scores",
                "candidate_route_progress",
                "candidate_perfect_tracker_jerk_magnitude_mps3 or fallback jerk proxy",
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2 or fallback lateral proxy",
                "scenario bucket metadata",
            ],
            "math_boundary": (
                "Each rule is a finite-candidate selector over fixed "
                "current-tick DP candidates. If promoted as CAMP atoms, the "
                "progress, jerk, lateral, and score-margin quantities remain "
                "fixed coefficients, preserving affine scoring and the "
                "simplex/CVaR/L2 convex master. This audit is not classical "
                "Benders decomposition."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "min_progress_delta_ci_low": float(min_progress_delta_ci_low),
        },
        "records": {
            "logs": len({record["context"]["log_path"] for record in records}),
            "total": len(records),
            "candidate_count_values": sorted(
                {record["candidate_count"] for record in records}
            ),
            "bucket_record_counts": {
                bucket: len(bucket_records)
                for bucket, bucket_records in _records_by_bucket(records).items()
            },
        },
        "ranked_candidates": ranked,
        "rules": rule_reports,
        "decision": _decision(ranked),
    }


def _rule_report(
    records: list[dict[str, Any]],
    rule: Rule,
    *,
    target_buckets: tuple[str, ...],
    bootstrap_resamples: int,
    seed: int,
    min_progress_delta_ci_low: float,
) -> dict[str, Any]:
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    chosen = np.asarray(
        [_select(record, rule, target_buckets=target_buckets) for record in records],
        dtype=np.int64,
    )
    overall = _choice_metrics(
        records,
        chosen,
        selected,
        top1,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    by_bucket = {}
    for bucket, bucket_records in _records_by_bucket(records).items():
        if bucket not in target_buckets:
            continue
        indices = _record_indices(records, bucket)
        by_bucket[bucket] = _choice_metrics(
            bucket_records,
            chosen[indices],
            selected[indices],
            top1[indices],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
    bucket_failures = _bucket_failures(
        by_bucket,
        target_buckets=target_buckets,
        min_progress_delta_ci_low=min_progress_delta_ci_low,
    )
    return {
        "name": rule.name,
        "rule": {
            "progress_gain_threshold": rule.progress_gain_threshold,
            "jerk_tolerance": rule.jerk_tolerance,
            "lateral_tolerance": rule.lateral_tolerance,
            "score_margin": None if np.isinf(rule.score_margin) else rule.score_margin,
        },
        "passed_target_screen": bool(
            _passes(overall, min_progress_delta_ci_low) and not bucket_failures
        ),
        "bucket_failures": bucket_failures,
        "overall": overall,
        "by_bucket": by_bucket,
    }


def _select(
    record: dict[str, Any],
    rule: Rule,
    *,
    target_buckets: tuple[str, ...],
) -> int:
    if not set(record["buckets"]).intersection(target_buckets):
        return int(record["selected"])
    selected = int(record["selected"])
    selected_score = float(record["scores"][selected])
    rows = []
    for idx in range(int(record["candidate_count"])):
        progress_gain = float(record["planned_progress"][idx] - record["planned_progress"][selected])
        if progress_gain < rule.progress_gain_threshold:
            continue
        jerk_delta = float(record["tracker_jerk"][idx] - record["tracker_jerk"][selected])
        lateral_delta = float(record["tracker_lateral"][idx] - record["tracker_lateral"][selected])
        if jerk_delta > rule.jerk_tolerance or lateral_delta > rule.lateral_tolerance:
            continue
        score = float(record["scores"][idx])
        score_delta = _score_delta(score, selected_score)
        if score_delta > rule.score_margin:
            continue
        rows.append(
            {
                "idx": idx,
                "progress_gain": progress_gain,
                "jerk_delta": jerk_delta,
                "lateral_delta": lateral_delta,
                "score": score,
            }
        )
    if not rows:
        return selected
    rows.sort(
        key=lambda row: (
            -row["progress_gain"],
            max(row["jerk_delta"], 0.0),
            max(row["lateral_delta"], 0.0),
            row["score"],
            row["idx"],
        )
    )
    return int(rows[0]["idx"])


def _score_delta(score: float, selected_score: float) -> float:
    if np.isneginf(score):
        return -np.inf
    if np.isposinf(score):
        return np.inf
    if np.isposinf(selected_score):
        return 0.0
    return float(score - selected_score)


def _bucket_failures(
    by_bucket: dict[str, dict[str, Any]],
    *,
    target_buckets: tuple[str, ...],
    min_progress_delta_ci_low: float,
) -> dict[str, dict[str, Any]]:
    failures = {}
    for bucket in target_buckets:
        metrics = by_bucket.get(bucket)
        if metrics is None:
            failures[bucket] = {"reason": "missing_bucket"}
        elif not _passes(metrics, min_progress_delta_ci_low):
            failures[bucket] = {
                "safety_ci_high": metrics["safety_cost_delta_vs_current"][
                    "ci95_high"
                ],
                "progress_ci_low": metrics["progress_delta_vs_current"][
                    "ci95_low"
                ],
                "hard_nonworse": metrics["hard_nonworse_vs_current"],
                "beneficial_preserved": metrics["beneficial_current_preserved_rate"],
                "changed": metrics["changed_from_current_rate"],
            }
    return failures


def _passes(metrics: dict[str, Any], min_progress_delta_ci_low: float) -> bool:
    safety_high = metrics["safety_cost_delta_vs_current"]["ci95_high"]
    progress_low = metrics["progress_delta_vs_current"]["ci95_low"]
    return bool(
        safety_high is not None
        and safety_high < 0.0
        and progress_low is not None
        and progress_low >= min_progress_delta_ci_low
        and metrics["hard_nonworse_vs_current"] >= 0.99
        and metrics["beneficial_current_preserved_rate"] >= 0.8
    )


def _rank(rule_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for report in rule_reports:
        overall = report["overall"]
        safety = overall["safety_cost_delta_vs_current"]
        progress = overall["progress_delta_vs_current"]
        rows.append(
            {
                "name": report["name"],
                **report["rule"],
                "passed_target_screen": report["passed_target_screen"],
                "bucket_failure_count": len(report["bucket_failures"]),
                "safety_delta_mean": safety["mean"],
                "safety_delta_ci95_high": safety["ci95_high"],
                "progress_delta_ci95_low": progress["ci95_low"],
                "changed_from_current_rate": overall["changed_from_current_rate"],
                "beneficial_current_preserved_rate": overall[
                    "beneficial_current_preserved_rate"
                ],
                "hard_nonworse_vs_current": overall["hard_nonworse_vs_current"],
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            not row["passed_target_screen"],
            int(row["bucket_failure_count"]),
            float(row["safety_delta_ci95_high"] or 0.0),
            -float(row["changed_from_current_rate"]),
        ),
    )


def _decision(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [row for row in ranked if row["passed_target_screen"]]
    return {
        "status": (
            "targeted_offline_screen_passed"
            if passing
            else "targeted_offline_screen_failed"
        ),
        "passing_rules": len(passing),
        "online_selector_change_authorized": False,
        "training_authorized": False,
        "formal_seeds_authorized": False,
        "next_step": (
            "if a rule passes, inspect it for latency and closed-loop risk "
            "before any default-off smoke; otherwise reject this rule family"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# State-Conditioned Material Progress Rule Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['decision']['status']}`",
        f"- Passing rules: `{report['decision']['passing_rules']}`",
        f"- Online selector change authorized: `{report['decision']['online_selector_change_authorized']}`",
        f"- Training authorized: `{report['decision']['training_authorized']}`",
        f"- Formal seeds authorized: `{report['decision']['formal_seeds_authorized']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Ranked Rules",
        "",
        "| Rule | Pass | Bucket failures | Safety mean | Safety CI high | Progress CI low | Changed | Beneficial preserved | Hard nonworse |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_candidates"][:20]:
        lines.append(
            f"| `{row['name']}` | `{row['passed_target_screen']}` | "
            f"{row['bucket_failure_count']} | {_fmt(row['safety_delta_mean'])} | "
            f"{_fmt(row['safety_delta_ci95_high'])} | "
            f"{_fmt(row['progress_delta_ci95_low'])} | "
            f"{_fmt(row['changed_from_current_rate'])} | "
            f"{_fmt(row['beneficial_current_preserved_rate'])} | "
            f"{_fmt(row['hard_nonworse_vs_current'])} |"
        )
    best = _find_rule(report["rules"], report["ranked_candidates"][0]["name"])
    lines.extend(
        [
            "",
            "## Best Rule Bucket Metrics",
            "",
            f"Best rule: `{best['name']}`",
            "",
            "| Bucket | Records | Safety mean | Safety CI high | Progress CI low | Changed | Beneficial preserved | Hard nonworse |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for bucket, metrics in best["by_bucket"].items():
        safety = metrics["safety_cost_delta_vs_current"]
        progress = metrics["progress_delta_vs_current"]
        lines.append(
            f"| `{bucket}` | {metrics['records']} | {_fmt(safety['mean'])} | "
            f"{_fmt(safety['ci95_high'])} | {_fmt(progress['ci95_low'])} | "
            f"{_fmt(metrics['changed_from_current_rate'])} | "
            f"{_fmt(metrics['beneficial_current_preserved_rate'])} | "
            f"{_fmt(metrics['hard_nonworse_vs_current'])} |"
        )
    if best["bucket_failures"]:
        lines.extend(["", "## Best Rule Failures", ""])
        for bucket, failure in best["bucket_failures"].items():
            lines.append(f"- `{bucket}`: `{failure}`")
    lines.extend(["", f"Next step: {report['decision']['next_step']}", ""])
    return "\n".join(lines)


def _find_rule(rules: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for rule in rules:
        if rule["name"] == name:
            return rule
    raise KeyError(name)


def _tag(value: float) -> str:
    if np.isinf(value):
        return "inf"
    return f"{float(value):g}".replace(".", "p").replace("-", "m")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(result):
        return "n/a"
    return f"`{result:.6g}`"


if __name__ == "__main__":
    main()
