#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _aggregate_rows,
    _expand_scenario_bucket_rows,
    _paired_deltas,
    _safety_gate_assessments,
)


DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit explicit scenario bucket coverage for a DP-CAMP SafetyCost "
            "comparison JSON. This labels nothing by inference; it only reports "
            "what the comparison rows already carry."
        )
    )
    parser.add_argument("--comparison_json", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, required=True)
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Baseline variant. Defaults to comparison_json['baseline'].",
    )
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        default=None,
        help=(
            "Bucket required for development coverage. Repeat to override the "
            "default normal+critical bucket list."
        ),
    )
    parser.add_argument(
        "--fail_on_missing_required",
        action="store_true",
        help="Exit nonzero if any required bucket has zero run keys.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = _read_json(args.comparison_json)
    required_buckets = (
        tuple(args.required_bucket)
        if args.required_bucket is not None
        else DEFAULT_REQUIRED_BUCKETS
    )
    report = audit_comparison(
        comparison,
        baseline=args.baseline,
        required_buckets=required_buckets,
        comparison_path=args.comparison_json,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_markdown.write_text(render_markdown(report), encoding="utf-8")
    if args.fail_on_missing_required and report["coverage_gaps"][
        "missing_required_buckets"
    ]:
        missing = ", ".join(report["coverage_gaps"]["missing_required_buckets"])
        raise SystemExit(f"Missing required scenario bucket coverage: {missing}")


def audit_comparison(
    comparison: dict[str, Any],
    *,
    baseline: str | None = None,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
    comparison_path: Path | None = None,
) -> dict[str, Any]:
    rows = comparison.get("runs")
    if not isinstance(rows, list) or not rows:
        raise ValueError("comparison JSON must contain a nonempty runs list.")
    for row in rows:
        buckets = row.get("scenario_buckets")
        if buckets is not None:
            _validate_buckets(buckets)
    baseline = baseline or str(comparison.get("baseline") or rows[0]["variant"])
    _validate_buckets(list(required_buckets))

    expanded_rows = _expand_scenario_bucket_rows(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in expanded_rows:
        bucket = str(row.get("scenario_bucket", "overall"))
        if bucket not in SUPPORTED_SCENARIO_BUCKETS:
            raise ValueError(f"Unsupported scenario bucket in comparison: {bucket}")
        grouped[bucket].append(row)

    bucket_reports = []
    for bucket in _ordered_buckets(grouped):
        group = grouped[bucket]
        aggregates = _aggregate_rows(group, seed_prefix=f"scenario_bucket|{bucket}")
        deltas = _paired_deltas(
            group,
            baseline=baseline,
            seed_prefix=f"scenario_bucket|{bucket}|paired",
        )
        gates = _safety_gate_assessments(
            group,
            deltas,
            aggregates,
            baseline=baseline,
        )
        bucket_reports.append(
            {
                "bucket": bucket,
                **_bucket_pairing(group),
                "route_names": sorted(
                    {
                        str(row["route_name"])
                        for row in group
                        if row.get("route_name") is not None
                    }
                ),
                "aggregates": aggregates,
                "paired_deltas": deltas,
                "safety_gate_assessments": gates,
            }
        )

    bucket_by_name = {entry["bucket"]: entry for entry in bucket_reports}
    missing_required = [
        bucket
        for bucket in required_buckets
        if bucket_by_name.get(bucket, {}).get("n_run_keys", 0) == 0
    ]
    overall_only_run_keys = sorted(
        {
            str(row.get("run_key"))
            for row in rows
            if _is_overall_only(row.get("scenario_buckets"))
        }
    )
    return {
        "analysis": {
            "name": "dp_camp_scenario_bucket_coverage_v1",
            "comparison_path": None if comparison_path is None else str(comparison_path),
            "baseline": baseline,
            "explicit_labeling_only": True,
            "labels_are_not_inferred_from_metrics": True,
            "online_selector_change": False,
            "training": False,
        },
        "supported_buckets": sorted(SUPPORTED_SCENARIO_BUCKETS),
        "required_buckets": list(required_buckets),
        "total_rows": len(rows),
        "total_run_keys": len({str(row.get("run_key")) for row in rows}),
        "buckets": bucket_reports,
        "coverage_gaps": {
            "missing_required_buckets": missing_required,
            "overall_only_run_key_count": len(overall_only_run_keys),
            "overall_only_run_keys": overall_only_run_keys[:50],
            "overall_only_run_keys_truncated": len(overall_only_run_keys) > 50,
        },
        "next_step": (
            "add_or_verify_scenario_manifest_labels"
            if missing_required
            else "run_bucketed_safety_cost_gate"
        ),
    }


def _bucket_pairing(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_variant: dict[str, set[str]] = defaultdict(set)
    duplicates = []
    for row in rows:
        variant = str(row.get("variant"))
        run_key = str(row.get("run_key"))
        if run_key in by_variant[variant]:
            duplicates.append({"variant": variant, "run_key": run_key})
        by_variant[variant].add(run_key)
    if not by_variant:
        return {
            "n_rows": 0,
            "n_run_keys": 0,
            "variant_run_counts": {},
            "strictly_paired": False,
            "missing_run_keys": {},
            "duplicate_run_keys": [],
        }
    common = set.intersection(*(keys for keys in by_variant.values()))
    union = set.union(*(keys for keys in by_variant.values()))
    return {
        "n_rows": len(rows),
        "n_run_keys": len(union),
        "variant_run_counts": {
            variant: len(keys) for variant, keys in sorted(by_variant.items())
        },
        "strictly_paired": (
            not duplicates and all(keys == common for keys in by_variant.values())
        ),
        "missing_run_keys": {
            variant: sorted(union - keys) for variant, keys in sorted(by_variant.items())
        },
        "duplicate_run_keys": duplicates,
    }


def _ordered_buckets(
    grouped: dict[str, list[dict[str, Any]]],
) -> list[str]:
    order = ["overall", *DEFAULT_REQUIRED_BUCKETS]
    remaining = sorted(bucket for bucket in grouped if bucket not in order)
    return [bucket for bucket in order if bucket in grouped] + remaining


def _is_overall_only(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return True
    return set(str(bucket) for bucket in value) == {"overall"}


def _validate_buckets(buckets: list[Any]) -> None:
    invalid = [
        bucket
        for bucket in buckets
        if not isinstance(bucket, str) or bucket not in SUPPORTED_SCENARIO_BUCKETS
    ]
    if invalid:
        raise ValueError(
            "Unsupported scenario bucket(s): "
            f"{invalid}. Supported buckets: {sorted(SUPPORTED_SCENARIO_BUCKETS)}."
        )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Scenario Bucket Coverage Audit",
        "",
        "This audit reports explicit scenario labels already present in a "
        "SafetyCost comparison JSON. It does not infer critical buckets from "
        "route names, metrics, or outcomes.",
        "",
        f"Baseline: `{report['analysis']['baseline']}`",
        f"Next step: `{report['next_step']}`",
        "",
        "| Bucket | Run keys | Strict pairs | Variants | SafetyCost delta | "
        "Hard gate | Claim gate | Routes |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for bucket in report["buckets"]:
        delta_text, hard_gate_text, claim_text = _bucket_gate_summary(bucket)
        lines.append(
            f"| `{bucket['bucket']}` | "
            f"{bucket['n_run_keys']} | "
            f"{_yes_no(bucket['strictly_paired'])} | "
            f"{_variant_counts(bucket['variant_run_counts'])} | "
            f"{delta_text} | "
            f"{hard_gate_text} | "
            f"{claim_text} | "
            f"{_routes(bucket['route_names'])} |"
        )
    gaps = report["coverage_gaps"]["missing_required_buckets"]
    lines.extend(
        [
            "",
            "## Coverage Gaps",
            "",
            "- Missing required buckets: "
            + (", ".join(f"`{bucket}`" for bucket in gaps) if gaps else "none"),
            "- Overall-only run keys: "
            + str(report["coverage_gaps"]["overall_only_run_key_count"]),
            "",
        ]
    )
    return "\n".join(lines)


def _bucket_gate_summary(bucket: dict[str, Any]) -> tuple[str, str, str]:
    deltas = bucket.get("paired_deltas", [])
    gates = bucket.get("safety_gate_assessments", [])
    if not deltas:
        return "n/a", "n/a", "n/a"
    delta = deltas[0].get("safety_cost_v1")
    if isinstance(delta, dict) and delta.get("mean") is not None:
        delta_text = (
            f"{float(delta['mean']):+.6g} "
            f"[{float(delta['ci95_low']):+.3g}, "
            f"{float(delta['ci95_high']):+.3g}]"
        )
    else:
        delta_text = "n/a"
    if not gates:
        return delta_text, "n/a", "n/a"
    gate = gates[0]
    return (
        delta_text,
        _yes_no(bool(gate.get("hard_gate_passed"))),
        _yes_no(bool(gate.get("safety_cost_claim_passed"))),
    )


def _variant_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{variant}:{count}" for variant, count in sorted(counts.items()))


def _routes(routes: list[str]) -> str:
    if not routes:
        return "none"
    if len(routes) <= 4:
        return ", ".join(f"`{route}`" for route in routes)
    return ", ".join(f"`{route}`" for route in routes[:4]) + ", ..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    main()
