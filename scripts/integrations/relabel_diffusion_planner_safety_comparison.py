#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    BOOTSTRAP_RESAMPLES,
    FORMAL_SEEDS,
    SAFETY_COST_V1_ALPHA,
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_COMPLETION_TOLERANCE,
    SAFETY_COST_V1_LATENCY_BUDGET_MS,
    SAFETY_COST_V1_LATENCY_MARGIN_MS,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_NO_WORSE_METRICS,
    SAFETY_COST_V1_WEIGHTS,
    _aggregate_markdown_table,
    _aggregate_rows,
    _all_pairwise_deltas,
    _apply_safety_cost_v1,
    _load_scenario_bucket_manifest,
    _markdown_table,
    _paired_deltas,
    _paired_markdown_table,
    _pairing_audit,
    _safety_gate_assessments,
    _safety_gate_markdown_table,
    _scenario_buckets,
    _stratified_statistics,
    require_strict_pairing,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reapply an explicit scenario bucket manifest to an existing "
            "DP-CAMP SafetyCost comparison JSON and recompute aggregate gates."
        )
    )
    parser.add_argument("--input_json", type=Path, required=True)
    parser.add_argument("--scenario_bucket_manifest", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, default=None)
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Baseline variant. Defaults to input_json['baseline'] or first row.",
    )
    parser.add_argument(
        "--require_strict_pairing",
        action="store_true",
        help="Exit nonzero unless all variants share identical run keys.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_payload = _read_json(args.input_json)
    manifest = _load_scenario_bucket_manifest(args.scenario_bucket_manifest)
    result = relabel_comparison(
        input_payload,
        manifest,
        baseline=args.baseline,
        input_path=args.input_json,
        manifest_path=args.scenario_bucket_manifest,
    )
    if args.require_strict_pairing:
        require_strict_pairing(result["pairing_audit"])

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_markdown is not None:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(render_markdown(result), encoding="utf-8")

    print(
        json.dumps(
                {
                    "input_json": str(args.input_json),
                    "scenario_bucket_manifest": str(args.scenario_bucket_manifest),
                    "output_json": str(args.output_json),
                    "n_rows": len(result["runs"]),
                    "n_run_keys": result["pairing_audit"]["union_run_count"],
                    "strictly_paired": result["pairing_audit"]["strictly_paired"],
                    "baseline": result["baseline"],
                },
            indent=2,
            sort_keys=True,
        )
    )


def relabel_comparison(
    comparison: dict[str, Any],
    scenario_bucket_manifest: dict[str, Any],
    *,
    baseline: str | None = None,
    input_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    source_rows = comparison.get("runs")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("input comparison JSON must contain a nonempty runs list.")

    rows: list[dict[str, Any]] = []
    for source_row in source_rows:
        if not isinstance(source_row, dict):
            raise ValueError("every comparison run row must be a JSON object.")
        row = dict(source_row)
        _apply_safety_cost_v1(row)
        row["scenario_buckets"] = _scenario_buckets(row, scenario_bucket_manifest)
        rows.append(row)

    baseline = baseline or comparison.get("baseline") or rows[0].get("variant")
    if not baseline:
        raise ValueError("baseline is required when rows do not include a variant.")
    baseline = str(baseline)

    aggregates = _aggregate_rows(rows)
    paired_deltas = _paired_deltas(rows, baseline=baseline)
    all_pairwise_deltas = _all_pairwise_deltas(rows)
    safety_gate_assessments = _safety_gate_assessments(
        rows,
        paired_deltas,
        aggregates,
        baseline=baseline,
    )
    stratified_aggregates, stratified_pairwise_deltas = _stratified_statistics(rows)
    pairing_audit = _pairing_audit(rows)
    result = {
        "comparison_type": "diffusion_planner_camp_replay_variants",
        "relabel_analysis": {
            "name": "dp_camp_safety_comparison_relabel_v1",
            "input_json": None if input_path is None else str(input_path),
            "scenario_bucket_manifest": (
                None if manifest_path is None else str(manifest_path)
            ),
            "explicit_labeling_only": True,
            "labels_are_not_inferred_from_metrics": True,
            "online_selector_change": False,
            "training": False,
        },
        "runs": rows,
        "aggregates": aggregates,
        "paired_deltas": paired_deltas,
        "all_pairwise_deltas": all_pairwise_deltas,
        "safety_cost_v1": {
            "weights": SAFETY_COST_V1_WEIGHTS,
            "normalization": SAFETY_COST_V1_NORMALIZATION,
            "clip": SAFETY_COST_V1_CLIP,
            "tail_alpha": SAFETY_COST_V1_ALPHA,
            "lower_is_better": True,
            "hard_gate": {
                "no_worse_metrics": list(SAFETY_COST_V1_NO_WORSE_METRICS),
                "completion_tolerance": SAFETY_COST_V1_COMPLETION_TOLERANCE,
                "latency_budget_ms": SAFETY_COST_V1_LATENCY_BUDGET_MS,
                "latency_margin_ms": SAFETY_COST_V1_LATENCY_MARGIN_MS,
                "formal_seeds": sorted(FORMAL_SEEDS),
                "requires_finite_candidate_contract": True,
            },
        },
        "safety_gate_assessments": safety_gate_assessments,
        "stratified_aggregates": stratified_aggregates,
        "stratified_pairwise_deltas": stratified_pairwise_deltas,
        "pairing_audit": pairing_audit,
        "baseline": baseline,
        "ci_method": "deterministic bootstrap percentile",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "caveat": (
            "This file reapplies explicit scenario buckets to an existing "
            "comparison JSON. It does not rerun DP, CAMP selection, replay, or "
            "training."
        ),
    }
    return result


def render_markdown(report: dict[str, Any]) -> str:
    return (
        "## Relabel Analysis\n\n"
        + "```json\n"
        + json.dumps(report["relabel_analysis"], indent=2, sort_keys=True)
        + "\n```\n"
        + "\n## Runs\n\n"
        + _markdown_table(report["runs"])
        + "\n## Aggregates\n\n"
        + _aggregate_markdown_table(report["aggregates"])
        + "\n## All Pairwise Deltas (variant - baseline)\n\n"
        + _paired_markdown_table(report["all_pairwise_deltas"])
        + "\n## SafetyCost v1 Hard Gate\n\n"
        + _safety_gate_markdown_table(report["safety_gate_assessments"])
        + "\n## Pairing Audit\n\n"
        + "```json\n"
        + json.dumps(report["pairing_audit"], indent=2, sort_keys=True)
        + "\n```\n"
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
