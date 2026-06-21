#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_observable_interaction_payload_attribution import (  # noqa: E402
    READY_STATUS as PAYLOAD_ATTRIBUTION_READY_STATUS,
)


PAYLOAD_KEY = "observable_state_logging"
FORMAL_SEEDS = frozenset({11, 12, 13})
READY_STATUS = "red_alignment_semantics_microaudit_completed"
SOURCE_BLOCKED_STATUS = "red_alignment_semantics_source_not_ready"
CURRENT_SUPPORT_STATUS = "red_alignment_current_semantics_support_present"
UNDERDETERMINED_STATUS = "red_alignment_sign_semantics_underdetermined"
REJECT_STATUS = "red_alignment_current_payload_rejected"
NEXT_WORK_UNDERDETERMINED = (
    "predeclare_red_route_point_vector_logging_plan_or_reject_red_descriptor"
)
NEXT_WORK_REJECT = "reject_current_red_alignment_descriptor_for_existing_payloads"
NEXT_WORK_SOURCE = "fix_payload_attribution_source_before_red_alignment_microaudit"
BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "offline_separability_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only red alignment semantics microaudit. It checks whether "
            "existing observable-state payloads can distinguish current-sign "
            "support, reverse-sign support, sparse step support, and missing "
            "geometry needed to prove the sign convention."
        )
    )
    parser.add_argument("--payload_attribution_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--max_examples", type=int, default=12)
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
        payload_attribution_report=_read_json(args.payload_attribution_json),
        label=args.label,
        red_distance_budget_m=args.red_distance_budget_m,
        max_examples=args.max_examples,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_finite_json(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(_markdown(report), encoding="utf-8")


def analyze(
    paths: list[Path],
    *,
    payload_attribution_report: dict[str, Any],
    label: str | None,
    red_distance_budget_m: float,
    max_examples: int,
) -> dict[str, Any]:
    source_gate = _source_gate(payload_attribution_report)
    log_paths = iter_selection_log_paths(paths)
    counts = {
        "input_log_paths": len(log_paths),
        "excluded_formal_seed_logs": 0,
        "scanned_logs": 0,
        "records": 0,
        "candidate_payload_records": 0,
        "baseline_disabled_records": 0,
        "payload_candidates": 0,
        "red_relation_candidate_count": 0,
        "within_budget_candidate_count": 0,
        "current_mean_supported_candidate_count": 0,
        "reverse_mean_supported_candidate_count": 0,
        "current_distance_gated_positive_step_candidate_count": 0,
        "reverse_distance_gated_positive_step_candidate_count": 0,
        "current_positive_step_candidate_count": 0,
        "reverse_positive_step_candidate_count": 0,
        "records_with_red_relation": 0,
        "records_within_budget": 0,
        "records_with_current_mean_support": 0,
        "records_with_reverse_mean_support": 0,
        "records_with_current_distance_gated_positive_step": 0,
        "records_with_reverse_distance_gated_positive_step": 0,
        "records_with_logged_red_geometry": 0,
    }
    metrics = {
        "min_red_distance_m": math.inf,
        "max_current_mean_alignment": -math.inf,
        "max_current_step_alignment": -math.inf,
        "max_reverse_mean_alignment": -math.inf,
        "max_reverse_step_alignment": -math.inf,
        "max_current_distance_gated_step_alignment": -math.inf,
        "max_reverse_distance_gated_step_alignment": -math.inf,
        "min_current_mean_alignment_within_budget": math.inf,
        "max_current_mean_alignment_within_budget": -math.inf,
        "min_reverse_mean_alignment_within_budget": math.inf,
        "max_reverse_mean_alignment_within_budget": -math.inf,
    }
    reason_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    log_summaries: list[dict[str, Any]] = []
    geometry_fields = Counter()

    if not source_gate["passed"]:
        final_status = SOURCE_BLOCKED_STATUS
        passed = False
        next_work = NEXT_WORK_SOURCE
    else:
        for log_path in log_paths:
            path_seeds = sorted(_path_seeds(log_path))
            if any(seed in FORMAL_SEEDS for seed in path_seeds):
                counts["excluded_formal_seed_logs"] += 1
                continue
            counts["scanned_logs"] += 1
            rows = _read_selection_rows(log_path)
            log_summary = {
                "log_path": str(log_path),
                "records": len(rows),
                "candidate_payload_records": 0,
                "candidate_reason_counts": Counter(),
            }
            for record_index, record in enumerate(rows):
                counts["records"] += 1
                payload = record.get(PAYLOAD_KEY)
                if payload is None:
                    counts["baseline_disabled_records"] += 1
                    continue
                if not isinstance(payload, dict):
                    continue
                counts["candidate_payload_records"] += 1
                log_summary["candidate_payload_records"] += 1
                record_has_geometry = _record_has_logged_red_geometry(record, payload)
                if record_has_geometry:
                    counts["records_with_logged_red_geometry"] += 1
                    geometry_fields.update(_logged_red_geometry_fields(record, payload))
                contexts = _candidate_contexts(
                    payload,
                    log_path=log_path,
                    record_index=record_index,
                    red_distance_budget_m=red_distance_budget_m,
                    record_has_geometry=record_has_geometry,
                )
                _update_counts_and_metrics(
                    counts,
                    metrics,
                    contexts,
                    red_distance_budget_m=red_distance_budget_m,
                )
                for item in contexts:
                    reason_counts[item["reason"]] += 1
                    log_summary["candidate_reason_counts"][item["reason"]] += 1
                    if item["reason"] != "red_route_points_or_relation_absent":
                        examples.append(item)
            log_summary["candidate_reason_counts"] = dict(
                sorted(log_summary["candidate_reason_counts"].items())
            )
            log_summaries.append(log_summary)
        final_status, passed, next_work = _final_decision(counts)

    final_decision = {
        "status": final_status,
        "passed": passed,
        "primary_gap": _primary_gap(final_status, counts),
        "authorized_next_work": next_work,
    }
    return {
        "analysis": {
            "name": "dp_camp_red_alignment_semantics_microaudit_v1",
            "label": label,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "training": False,
            "diffusion_planner_modification": False,
            "formal_seed_policy": "exclude_path_seed_11_12_13",
            "math_boundary": (
                "This microaudit reads only existing current-tick observable "
                "payloads. Current-sign and reverse-sign alignment counts are "
                "diagnostics over fixed logged coefficients; they introduce no "
                "selector, atom, threshold, outcome label, trajectory-space "
                "convexity claim, or Benders cut."
            ),
        },
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "source_gate": source_gate,
        "budgets": {"red_distance_budget_m": float(red_distance_budget_m)},
        "counts": counts,
        "metrics": metrics,
        "reason_counts": dict(sorted(reason_counts.items())),
        "geometry_fields": dict(sorted(geometry_fields.items())),
        "top_examples": _rank_examples(examples)[: max(0, int(max_examples))],
        "log_summaries": log_summaries,
        "final_decision": final_decision,
    }


def _candidate_contexts(
    payload: dict[str, Any],
    *,
    log_path: Path,
    record_index: int,
    red_distance_budget_m: float,
    record_has_geometry: bool,
) -> list[dict[str, Any]]:
    candidate_count = int(payload.get("candidate_count") or 0)
    distances = _candidate_matrix(payload.get("candidate_red_stopline_distance_m"))
    alignments = _candidate_matrix(payload.get("candidate_red_heading_alignment"))
    red_route_point_count = int(payload.get("red_route_point_count") or 0)
    contexts: list[dict[str, Any]] = []
    for candidate_index in range(candidate_count):
        distance_values = distances[candidate_index] if candidate_index < len(distances) else []
        alignment_values = (
            alignments[candidate_index] if candidate_index < len(alignments) else []
        )
        paired = [
            (distance, alignment)
            for distance, alignment in zip(distance_values, alignment_values)
            if distance is not None and alignment is not None
        ]
        if red_route_point_count <= 0 or not paired:
            item = {
                "log_path": str(log_path),
                "record_index": record_index,
                "candidate_index": candidate_index,
                "red_route_point_count": red_route_point_count,
                "reason": "red_route_points_or_relation_absent",
            }
            contexts.append(item)
            continue
        finite_distances = [distance for distance, _ in paired]
        finite_alignments = [alignment for _, alignment in paired]
        gated_alignments = [
            alignment
            for distance, alignment in paired
            if distance <= float(red_distance_budget_m)
        ]
        current_mean = sum(finite_alignments) / len(finite_alignments)
        reverse_mean = -current_mean
        current_step_max = max(finite_alignments)
        reverse_step_max = max(-value for value in finite_alignments)
        current_gated_max = max(gated_alignments) if gated_alignments else None
        reverse_gated_max = (
            max(-value for value in gated_alignments) if gated_alignments else None
        )
        min_distance = min(finite_distances)
        item = {
            "log_path": str(log_path),
            "record_index": record_index,
            "candidate_index": candidate_index,
            "red_route_point_count": red_route_point_count,
            "min_red_distance_m": min_distance,
            "current_mean_alignment": current_mean,
            "current_step_max_alignment": current_step_max,
            "reverse_mean_alignment": reverse_mean,
            "reverse_step_max_alignment": reverse_step_max,
            "current_distance_gated_step_max_alignment": current_gated_max,
            "reverse_distance_gated_step_max_alignment": reverse_gated_max,
            "distance_gated_step_count": len(gated_alignments),
            "record_has_logged_red_geometry": record_has_geometry,
        }
        item["reason"] = _reason(item, red_distance_budget_m=red_distance_budget_m)
        contexts.append(item)
    return contexts


def _reason(item: dict[str, Any], *, red_distance_budget_m: float) -> str:
    distance = item.get("min_red_distance_m")
    if distance is None:
        return "red_route_points_or_relation_absent"
    if float(distance) > float(red_distance_budget_m):
        if float(item["current_step_max_alignment"]) > 0.0:
            return "current_positive_step_but_distance_outside_budget"
        if float(item["reverse_step_max_alignment"]) > 0.0:
            return "reverse_positive_step_but_distance_outside_budget"
        return "distance_outside_budget"
    if float(item["current_mean_alignment"]) > 0.0:
        return "current_mean_supported"
    if float(item["reverse_mean_alignment"]) > 0.0:
        if not bool(item.get("record_has_logged_red_geometry")):
            return "reverse_mean_supported_but_geometry_unlogged"
        return "reverse_mean_supported_with_geometry_logged"
    if (
        item["current_distance_gated_step_max_alignment"] is not None
        and float(item["current_distance_gated_step_max_alignment"]) > 0.0
    ):
        return "current_sparse_step_supported_mean_nonpositive"
    if (
        item["reverse_distance_gated_step_max_alignment"] is not None
        and float(item["reverse_distance_gated_step_max_alignment"]) > 0.0
    ):
        return "reverse_sparse_step_supported_mean_nonpositive"
    return "no_current_or_reverse_alignment_support"


def _update_counts_and_metrics(
    counts: dict[str, int],
    metrics: dict[str, float],
    contexts: list[dict[str, Any]],
    *,
    red_distance_budget_m: float,
) -> None:
    record_flags = {
        "red_relation": False,
        "within_budget": False,
        "current_mean": False,
        "reverse_mean": False,
        "current_gated_step": False,
        "reverse_gated_step": False,
    }
    for item in contexts:
        counts["payload_candidates"] += 1
        if "min_red_distance_m" not in item:
            continue
        counts["red_relation_candidate_count"] += 1
        record_flags["red_relation"] = True
        distance = float(item["min_red_distance_m"])
        current_mean = float(item["current_mean_alignment"])
        reverse_mean = float(item["reverse_mean_alignment"])
        current_step = float(item["current_step_max_alignment"])
        reverse_step = float(item["reverse_step_max_alignment"])
        metrics["min_red_distance_m"] = min(metrics["min_red_distance_m"], distance)
        metrics["max_current_mean_alignment"] = max(
            metrics["max_current_mean_alignment"], current_mean
        )
        metrics["max_reverse_mean_alignment"] = max(
            metrics["max_reverse_mean_alignment"], reverse_mean
        )
        metrics["max_current_step_alignment"] = max(
            metrics["max_current_step_alignment"], current_step
        )
        metrics["max_reverse_step_alignment"] = max(
            metrics["max_reverse_step_alignment"], reverse_step
        )
        if current_step > 0.0:
            counts["current_positive_step_candidate_count"] += 1
        if reverse_step > 0.0:
            counts["reverse_positive_step_candidate_count"] += 1
        if item["current_distance_gated_step_max_alignment"] is not None:
            current_gated = float(item["current_distance_gated_step_max_alignment"])
            metrics["max_current_distance_gated_step_alignment"] = max(
                metrics["max_current_distance_gated_step_alignment"],
                current_gated,
            )
            if current_gated > 0.0:
                counts["current_distance_gated_positive_step_candidate_count"] += 1
                record_flags["current_gated_step"] = True
        if item["reverse_distance_gated_step_max_alignment"] is not None:
            reverse_gated = float(item["reverse_distance_gated_step_max_alignment"])
            metrics["max_reverse_distance_gated_step_alignment"] = max(
                metrics["max_reverse_distance_gated_step_alignment"],
                reverse_gated,
            )
            if reverse_gated > 0.0:
                counts["reverse_distance_gated_positive_step_candidate_count"] += 1
                record_flags["reverse_gated_step"] = True
        within_budget = distance <= float(red_distance_budget_m)
        if within_budget:
            counts["within_budget_candidate_count"] += 1
            record_flags["within_budget"] = True
            metrics["min_current_mean_alignment_within_budget"] = min(
                metrics["min_current_mean_alignment_within_budget"], current_mean
            )
            metrics["max_current_mean_alignment_within_budget"] = max(
                metrics["max_current_mean_alignment_within_budget"], current_mean
            )
            metrics["min_reverse_mean_alignment_within_budget"] = min(
                metrics["min_reverse_mean_alignment_within_budget"], reverse_mean
            )
            metrics["max_reverse_mean_alignment_within_budget"] = max(
                metrics["max_reverse_mean_alignment_within_budget"], reverse_mean
            )
        if within_budget and current_mean > 0.0:
            counts["current_mean_supported_candidate_count"] += 1
            record_flags["current_mean"] = True
        if within_budget and reverse_mean > 0.0:
            counts["reverse_mean_supported_candidate_count"] += 1
            record_flags["reverse_mean"] = True
    if record_flags["red_relation"]:
        counts["records_with_red_relation"] += 1
    if record_flags["within_budget"]:
        counts["records_within_budget"] += 1
    if record_flags["current_mean"]:
        counts["records_with_current_mean_support"] += 1
    if record_flags["reverse_mean"]:
        counts["records_with_reverse_mean_support"] += 1
    if record_flags["current_gated_step"]:
        counts["records_with_current_distance_gated_positive_step"] += 1
    if record_flags["reverse_gated_step"]:
        counts["records_with_reverse_distance_gated_positive_step"] += 1


def _final_decision(counts: dict[str, int]) -> tuple[str, bool, str]:
    if counts["current_mean_supported_candidate_count"] > 0:
        return (
            CURRENT_SUPPORT_STATUS,
            True,
            "run_offline_separability_screen_only_after_predeclared_gate",
        )
    if counts["reverse_mean_supported_candidate_count"] > 0:
        return UNDERDETERMINED_STATUS, True, NEXT_WORK_UNDERDETERMINED
    return REJECT_STATUS, True, NEXT_WORK_REJECT


def _primary_gap(final_status: str, counts: dict[str, int]) -> str:
    if final_status == SOURCE_BLOCKED_STATUS:
        return "payload_attribution_source_not_ready"
    if final_status == CURRENT_SUPPORT_STATUS:
        return "current_alignment_semantics_have_support"
    if final_status == UNDERDETERMINED_STATUS:
        return "reverse_sign_would_create_support_but_red_geometry_is_unlogged"
    if counts["within_budget_candidate_count"] == 0:
        return "no_red_candidates_within_distance_budget"
    return "no_current_or_reverse_red_alignment_support"


def _source_gate(payload_attribution_report: dict[str, Any]) -> dict[str, Any]:
    final = (
        payload_attribution_report.get("final_decision")
        if isinstance(payload_attribution_report, dict)
        else None
    )
    final = final if isinstance(final, dict) else {}
    return {
        "payload_attribution_status": final.get("status"),
        "payload_attribution_passed": final.get("passed"),
        "passed": (
            final.get("status") == PAYLOAD_ATTRIBUTION_READY_STATUS
            and final.get("passed") is True
        ),
    }


def _candidate_matrix(raw: Any) -> list[list[float | None]]:
    if raw is None or not isinstance(raw, list):
        return []
    matrix: list[list[float | None]] = []
    for row in raw:
        if isinstance(row, list):
            matrix.append([_as_finite_float(value) for value in row])
        else:
            matrix.append([_as_finite_float(row)])
    return matrix


def _record_has_logged_red_geometry(record: dict[str, Any], payload: dict[str, Any]) -> bool:
    return bool(_logged_red_geometry_fields(record, payload))


def _logged_red_geometry_fields(
    record: dict[str, Any], payload: dict[str, Any]
) -> list[str]:
    fields: list[str] = []
    for key in ("red_route_points", "red_route_point_vectors", "route_centerline_ego"):
        if key in record or key in payload:
            fields.append(key)
    evaluation = record.get("evaluation_state")
    if isinstance(evaluation, dict) and evaluation.get("red_route_points") is not None:
        fields.append("evaluation_state.red_route_points")
    return fields


def _read_selection_rows(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return [row for row in data["records"] if isinstance(row, dict)]
    raise ValueError(f"Unsupported selection log format: {path}")


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _path_seeds(path: Path) -> set[int]:
    seeds: set[int] = set()
    for part in Path(path).parts:
        match = re.fullmatch(r"seed_?(\d+)", part)
        if match:
            seeds.add(int(match.group(1)))
    return seeds


def _as_finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _rank_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        examples,
        key=lambda item: (
            item.get("min_red_distance_m") is None,
            (
                float("inf")
                if item.get("min_red_distance_m") is None
                else float(item["min_red_distance_m"])
            ),
            -float(item.get("reverse_mean_alignment") or 0.0),
            str(item.get("reason")),
        ),
    )


def _markdown(report: dict[str, Any]) -> str:
    final = report["final_decision"]
    counts = report["counts"]
    metrics = _finite_json(report["metrics"])
    lines = [
        "# Red Alignment Semantics Microaudit",
        "",
        f"- status: `{final['status']}`",
        f"- passed: `{final['passed']}`",
        f"- primary gap: `{final['primary_gap']}`",
        f"- authorized next work: `{final['authorized_next_work']}`",
        "",
        "## Counts",
        "",
    ]
    for key in (
        "scanned_logs",
        "records",
        "candidate_payload_records",
        "payload_candidates",
        "red_relation_candidate_count",
        "within_budget_candidate_count",
        "current_mean_supported_candidate_count",
        "reverse_mean_supported_candidate_count",
        "current_distance_gated_positive_step_candidate_count",
        "reverse_distance_gated_positive_step_candidate_count",
        "records_with_logged_red_geometry",
    ):
        lines.append(f"- {key}: `{counts[key]}`")
    lines.extend(["", "## Reasons", ""])
    for key, value in report["reason_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Metrics", ""])
    for key, value in metrics.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_json(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
