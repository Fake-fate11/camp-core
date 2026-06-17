#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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
from scripts.integrations.analyze_diffusion_planner_hidden_outcome_gap import (  # noqa: E402
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_candidate_availability import (  # noqa: E402
    PROGRESS_BUDGETS_M,
    _load_record as _load_availability_record,
    _outcome_joint_comfort_mask,
    _outcome_pareto_mask,
    _proxy_joint_comfort_mask,
    _proxy_pareto_mask,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
)


TOL = 1e-12
ROLLOUT_HORIZONS = ("3", "5", "10")
DESCRIPTORS = (
    "progress_shortfall_atom",
    "route_progress",
    "step_reach",
    "tracker_first_step_reach",
    "tracker_target_speed",
    "rollout_h3_distance",
    "rollout_h5_distance",
    "rollout_h10_distance",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DP-CAMP progress certificate design audit. It compares "
            "fixed current-tick progress descriptors against hidden "
            "outcome-joint candidate opportunities."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--progress_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override default budgets 0, 0.05, 0.10, 0.25.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(
    paths: list[Path],
    *,
    label: str | None = None,
    scenario_bucket_manifest: Path | None = None,
    progress_budgets_m: tuple[float, ...] = PROGRESS_BUDGETS_M,
) -> dict[str, Any]:
    budgets = tuple(_canonical_budget(value) for value in progress_budgets_m)
    if len(set(budgets)) != len(budgets):
        raise ValueError("Progress budgets must be unique.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, record in enumerate(payload):
            loaded = _load_record(record, f"{log_path} record {index}")
            loaded["scenario_buckets"] = context["scenario_buckets"]
            records.append(loaded)

    return {
        "analysis": {
            "name": "dp_camp_progress_certificate_design_v1",
            "role": (
                "offline progress-certificate design audit before any online "
                "finite-candidate selector"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "explicit_bucket_labels_only": True,
            "progress_budgets_m": list(budgets),
            "descriptors": list(DESCRIPTORS),
            "certificate_rule": (
                "candidate remains inside the fixed finite candidate set, is "
                "base-feasible, has union-red and red-stopping costs no worse "
                "than the selected candidate, and has descriptor loss within "
                "the declared budget"
            ),
            "proxy_comfort_rule": (
                "strictly lower current-tick proxy jerk and proxy lateral "
                "costs than the selected candidate"
            ),
            "math_boundary": (
                "Every descriptor is a fixed current-tick finite-candidate "
                "constant. If a descriptor is later atomized with fixed scales, "
                "CAMP scoring remains affine in w and the simplex/CVaR/L2 "
                "master remains convex. This audit is not Benders and does not "
                "claim trajectory-coordinate convexity."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
            "scenario_bucket_counts": _scenario_bucket_counts(records),
            "descriptor_available_records": {
                name: sum(int(record["descriptors"].get(name) is not None) for record in records)
                for name in DESCRIPTORS
            },
        },
        "budgets": [
            _budget_report(records, budget)
            for budget in budgets
        ],
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    loaded = _load_availability_record(record, label)
    candidate_count = int(record.get("num_candidates", 0))
    descriptors: dict[str, np.ndarray | None] = {
        "progress_shortfall_atom": loaded["progress_shortfall"],
        "route_progress": _optional_vector(
            record.get("candidate_route_progress"),
            candidate_count,
            f"{label} candidate_route_progress",
        ),
        "step_reach": _required_vector(
            record.get("candidate_step_reach"),
            candidate_count,
            f"{label} candidate_step_reach",
        ),
        "tracker_first_step_reach": _required_vector(
            record.get("candidate_perfect_tracker_first_step_reach_m"),
            candidate_count,
            f"{label} candidate_perfect_tracker_first_step_reach_m",
        ),
        "tracker_target_speed": _required_vector(
            record.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
        ),
    }
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    for horizon in ROLLOUT_HORIZONS:
        key = f"rollout_h{horizon}_distance"
        if not isinstance(rollout, dict) or horizon not in rollout:
            descriptors[key] = None
            continue
        payload = rollout[horizon]
        descriptors[key] = (
            _required_vector(
                payload.get("distance_m") if isinstance(payload, dict) else None,
                candidate_count,
                f"{label} rollout H{horizon} distance_m",
            )
        )
    loaded["descriptors"] = descriptors
    return loaded


def _budget_report(records: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    report = _budget_report_flat(records, budget)
    report["by_bucket"] = [
        {
            "bucket": bucket_name,
            **_budget_report_flat(bucket_records, budget),
        }
        for bucket_name, bucket_records in _records_by_bucket(records).items()
    ]
    return report


def _budget_report_flat(records: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    nonfallback = [record for record in records if record["feasible"].any()]
    outcome_joint_by_record = [
        _outcome_joint_mask(record, budget)
        for record in nonfallback
    ]
    current_proxy_joint_records = sum(
        int((_proxy_joint_mask(record, budget)).any())
        for record in nonfallback
    )
    outcome_joint_records = sum(int(mask.any()) for mask in outcome_joint_by_record)
    rows = []
    for descriptor in DESCRIPTORS:
        rows.append(
            _descriptor_report(
                nonfallback,
                outcome_joint_by_record,
                descriptor,
                budget,
            )
        )
    return {
        "progress_budget_m": float(budget),
        "nonfallback_records": len(nonfallback),
        "outcome_joint_records": int(outcome_joint_records),
        "outcome_joint_rate": outcome_joint_records / max(len(nonfallback), 1),
        "current_proxy_joint_records": int(current_proxy_joint_records),
        "current_proxy_joint_rate": current_proxy_joint_records / max(len(nonfallback), 1),
        "descriptors": rows,
    }


def _records_by_bucket(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        buckets = record.get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(record)
    return {bucket: grouped[bucket] for bucket in _ordered_buckets(grouped)}


def _scenario_bucket_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for bucket, bucket_records in _records_by_bucket(records).items():
        counts[bucket] = {
            "records": len(bucket_records),
            "nonfallback": sum(int(record["feasible"].any()) for record in bucket_records),
            "fallback": sum(int(not record["feasible"].any()) for record in bucket_records),
        }
    return counts


def _ordered_buckets(grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    order = [
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    return [bucket for bucket in order if bucket in grouped] + sorted(
        bucket for bucket in grouped if bucket not in order
    )


def _descriptor_report(
    records: list[dict[str, Any]],
    outcome_joint_masks: list[np.ndarray],
    descriptor: str,
    budget: float,
) -> dict[str, Any]:
    available_records = 0
    outcome_joint_records = 0
    hidden_records = 0
    certificate_records = 0
    certificate_outcome_joint_records = 0
    certificate_hidden_records = 0
    certificate_proxy_comfort_records = 0
    certificate_proxy_comfort_outcome_joint_records = 0
    certificate_proxy_comfort_hidden_records = 0
    hidden_losses: list[float] = []
    covered_hidden_losses: list[float] = []
    proxy_comfort_covered_hidden_losses: list[float] = []

    for record, outcome_joint in zip(records, outcome_joint_masks, strict=True):
        values = record["descriptors"].get(descriptor)
        if values is None:
            continue
        available_records += 1
        current_proxy_joint = _proxy_joint_mask(record, budget)
        has_outcome_joint = bool(outcome_joint.any())
        is_hidden = has_outcome_joint and not bool(current_proxy_joint.any())
        outcome_joint_records += int(has_outcome_joint)
        hidden_records += int(is_hidden)
        certificate = _certificate_mask(record, values, descriptor, budget)
        proxy_comfort_certificate = certificate & _proxy_joint_comfort_mask(record)
        has_certificate = bool(certificate.any())
        has_certificate_outcome = bool((certificate & outcome_joint).any())
        has_certificate_proxy_comfort = bool(proxy_comfort_certificate.any())
        has_proxy_comfort_outcome = bool((proxy_comfort_certificate & outcome_joint).any())
        certificate_records += int(has_certificate)
        certificate_outcome_joint_records += int(has_certificate_outcome)
        certificate_hidden_records += int(is_hidden and has_certificate_outcome)
        certificate_proxy_comfort_records += int(has_certificate_proxy_comfort)
        certificate_proxy_comfort_outcome_joint_records += int(has_proxy_comfort_outcome)
        certificate_proxy_comfort_hidden_records += int(
            is_hidden and has_proxy_comfort_outcome
        )
        if is_hidden:
            min_hidden_loss = _min_loss(record, values, descriptor, outcome_joint)
            hidden_losses.append(min_hidden_loss)
            if has_certificate_outcome:
                covered_hidden_losses.append(
                    _min_loss(record, values, descriptor, certificate & outcome_joint)
                )
            if has_proxy_comfort_outcome:
                proxy_comfort_covered_hidden_losses.append(
                    _min_loss(
                        record,
                        values,
                        descriptor,
                        proxy_comfort_certificate & outcome_joint,
                    )
                )
    denom = max(available_records, 1)
    outcome_denom = max(outcome_joint_records, 1)
    hidden_denom = max(hidden_records, 1)
    proxy_records = certificate_proxy_comfort_records
    proxy_denom = max(proxy_records, 1)
    return {
        "descriptor": descriptor,
        "available_records": int(available_records),
        "outcome_joint_records": int(outcome_joint_records),
        "hidden_joint_records": int(hidden_records),
        "certificate_records": int(certificate_records),
        "certificate_rate": certificate_records / denom,
        "certificate_outcome_joint_records": int(certificate_outcome_joint_records),
        "certificate_outcome_joint_capture_rate": (
            certificate_outcome_joint_records / outcome_denom
        ),
        "certificate_hidden_joint_records": int(certificate_hidden_records),
        "certificate_hidden_joint_capture_rate": certificate_hidden_records / hidden_denom,
        "certificate_proxy_comfort_records": int(certificate_proxy_comfort_records),
        "certificate_proxy_comfort_rate": certificate_proxy_comfort_records / denom,
        "certificate_proxy_comfort_outcome_joint_records": int(
            certificate_proxy_comfort_outcome_joint_records
        ),
        "certificate_proxy_comfort_outcome_joint_rate": (
            certificate_proxy_comfort_outcome_joint_records / proxy_denom
        ),
        "certificate_proxy_comfort_hidden_joint_records": int(
            certificate_proxy_comfort_hidden_records
        ),
        "certificate_proxy_comfort_hidden_capture_rate": (
            certificate_proxy_comfort_hidden_records / hidden_denom
        ),
        "hidden_loss_summary": _summary(hidden_losses),
        "covered_hidden_loss_summary": _summary(covered_hidden_losses),
        "proxy_comfort_covered_hidden_loss_summary": _summary(
            proxy_comfort_covered_hidden_losses
        ),
    }


def _outcome_joint_mask(record: dict[str, Any], budget: float) -> np.ndarray:
    return _outcome_pareto_mask(record, budget) & _outcome_joint_comfort_mask(record)


def _proxy_joint_mask(record: dict[str, Any], budget: float) -> np.ndarray:
    return _proxy_pareto_mask(record, budget) & _proxy_joint_comfort_mask(record)


def _certificate_mask(
    record: dict[str, Any],
    values: np.ndarray,
    descriptor: str,
    budget: float,
) -> np.ndarray:
    selected = int(record["selected_index"])
    mask = record["feasible"].copy()
    mask[selected] = False
    mask &= record["union_red"] <= record["union_red"][selected] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][selected] + TOL
    loss = _descriptor_loss(values, selected, descriptor)
    mask &= loss <= budget + TOL
    return mask


def _descriptor_loss(values: np.ndarray, selected: int, descriptor: str) -> np.ndarray:
    if descriptor == "progress_shortfall_atom":
        return np.maximum(0.0, values - values[selected])
    return np.maximum(0.0, values[selected] - values)


def _min_loss(
    record: dict[str, Any],
    values: np.ndarray,
    descriptor: str,
    mask: np.ndarray,
) -> float:
    selected = int(record["selected_index"])
    losses = _descriptor_loss(values, selected, descriptor)
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        raise ValueError("Cannot summarize an empty candidate mask.")
    return float(np.min(losses[indices]))


def _required_vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return vector


def _optional_vector(values: Any, size: int, label: str) -> np.ndarray | None:
    if values is None:
        return None
    try:
        return _required_vector(values, size, label)
    except ValueError:
        return None


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p90": None, "p95": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "p50": float(np.percentile(array, 50.0)),
        "p90": float(np.percentile(array, 90.0)),
        "p95": float(np.percentile(array, 95.0)),
    }


def _canonical_budget(value: float) -> float:
    budget = round(float(value), 8)
    if budget < -TOL:
        raise ValueError("Progress budgets must be nonnegative.")
    return budget


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP CAMP Progress Certificate Design Audit",
        "",
        "This is a read-only design audit. Candidate outcomes are offline labels; "
        "all certificate descriptors are fixed current-tick finite-candidate fields.",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records: {records['fallback']}",
        "",
    ]
    for budget in report["budgets"]:
        lines.extend(
            [
                f"## Progress Budget {budget['progress_budget_m']:.2f} m",
                "",
                f"- Outcome-joint records: {budget['outcome_joint_records']} "
                f"({budget['outcome_joint_rate']:.6f})",
                f"- Current proxy-joint records: {budget['current_proxy_joint_records']} "
                f"({budget['current_proxy_joint_rate']:.6f})",
                "",
                "| Descriptor | Available | Certificate | Outcome capture | "
                "Hidden capture | Proxy-comfort capture | Proxy-comfort precision |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in budget["descriptors"]:
            lines.append(
                f"| `{row['descriptor']}` | {row['available_records']} | "
                f"{row['certificate_records']} ({row['certificate_rate']:.6f}) | "
                f"{row['certificate_outcome_joint_records']} "
                f"({row['certificate_outcome_joint_capture_rate']:.6f}) | "
                f"{row['certificate_hidden_joint_records']} "
                f"({row['certificate_hidden_joint_capture_rate']:.6f}) | "
                f"{row['certificate_proxy_comfort_hidden_joint_records']} "
                f"({row['certificate_proxy_comfort_hidden_capture_rate']:.6f}) | "
                f"{row['certificate_proxy_comfort_outcome_joint_rate']:.6f} |"
            )
        lines.append("")
        lines.extend(
            [
                "### Scenario Bucket Descriptor Capture",
                "",
                "| Bucket | Descriptor | Nonfallback | Hidden capture | "
                "Proxy-comfort hidden capture | Proxy-comfort precision |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for bucket in budget.get("by_bucket", []):
            for row in bucket["descriptors"]:
                lines.append(
                    f"| `{bucket['bucket']}` | `{row['descriptor']}` | "
                    f"{bucket['nonfallback_records']} | "
                    f"{row['certificate_hidden_joint_records']} "
                    f"({row['certificate_hidden_joint_capture_rate']:.6f}) | "
                    f"{row['certificate_proxy_comfort_hidden_joint_records']} "
                    f"({row['certificate_proxy_comfort_hidden_capture_rate']:.6f}) | "
                    f"{row['certificate_proxy_comfort_outcome_joint_rate']:.6f} |"
                )
        lines.append("")
    lines.extend(["## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    budgets = (
        tuple(args.progress_budget_m)
        if args.progress_budget_m
        else PROGRESS_BUDGETS_M
    )
    report = analyze(
        paths,
        label=args.label,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        progress_budgets_m=budgets,
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


if __name__ == "__main__":
    main()
