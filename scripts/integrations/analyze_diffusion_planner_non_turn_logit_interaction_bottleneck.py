#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
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

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (  # noqa: E402
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_outcome_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    REJECT_STATUS as SEPARABILITY_REJECT_STATUS,
)


PAYLOAD_KEY = "non_turn_logit_interaction_payload_logging"
FORMAL_SEEDS = frozenset({11, 12, 13})

READY_STATUS = "non_turn_logit_interaction_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "non_turn_logit_interaction_bottleneck_source_not_rejected"
FORMAL_SEED_STATUS = "non_turn_logit_interaction_bottleneck_formal_seed_conflict"
SOURCE_PRIMARY_GAP = "comfort_progress_interaction_does_not_separate_candidates"
SOURCE_NEXT_WORK = "diagnose_non_turn_logit_interaction_bottleneck_before_retraining"
NEXT_WORK = "reject_non_turn_interaction_or_return_to_progress_lane_hard_context"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "schema_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only bottleneck diagnosis for a rejected non-turn-logit "
            "interaction outcome-separability screen. It reuses existing "
            "matched logs and does not run DP, train CAMP, or change the "
            "online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
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
        separability_report=_read_json(args.separability_json),
        label=args.label,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
    expected_logs: int | None = None,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = _discover_logs(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    if expected_logs is not None and len(log_paths) != int(expected_logs):
        raise ValueError(f"log_count={len(log_paths)} expected={expected_logs}.")

    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for log_path in log_paths:
        payload = _read_json(log_path)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        if expected_records is not None and len(payload) != int(expected_records):
            raise ValueError(
                f"{log_path} record_count={len(payload)} expected={expected_records}."
            )
        path_seeds = _path_seeds(log_path)
        for record_index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            record_seed = _record_seed(raw)
            formal_seed_records += int(
                bool(path_seeds & FORMAL_SEEDS) or record_seed in FORMAL_SEEDS
            )
            rows.extend(
                _candidate_rows(
                    raw,
                    {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(path_seeds),
                        "record_seed": record_seed,
                    },
                    f"{log_path} record {record_index}",
                    expected_candidates=expected_candidates,
                    min_value_gain=min_value_gain,
                    min_value_loss=min_value_loss,
                    progress_loss_budget_m=progress_loss_budget_m,
                )
            )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    source = _source_gate(separability_report)
    alternatives = [row for row in rows if row["class"] != CLASS_TOP1]
    best_screen = _best_screen(separability_report)
    positive_screens = _positive_atom_screens(separability_report)
    best_positive = positive_screens[0] if positive_screens else None
    diagnosis = _diagnosis(alternatives, best_screen, best_positive)
    final = _decision(
        source,
        formal_seed_records=formal_seed_records,
        diagnosis=diagnosis,
    )
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_features": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "math_boundary": (
                "This diagnostic reads existing matched nonformal logs and a "
                "rejected separability artifact. The non-turn interaction "
                "payload is a current-tick fixed finite-candidate descriptor; "
                "closed-loop outcomes are used only to explain offline "
                "beneficial/harmful class overlap. No new atom is promoted, "
                "CAMP score_k(w)=a_k^T w and the simplex/CVaR/L2 master are "
                "unchanged, and no DP-side classical Benders decomposition is "
                "claimed."
            ),
        },
        "source_gate": source,
        "records": {
            "logs": len(log_paths),
            "total_records": _safe_record_count(rows, expected_candidates),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternatives),
            "formal_seed_records": formal_seed_records,
            "class_counts": _class_counts(alternatives),
        },
        "best_screen": best_screen,
        "best_positive_atom_screen": best_positive,
        "feature_summaries": _feature_summaries(alternatives),
        "diagnosis": diagnosis,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    *,
    expected_candidates: int,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> list[dict[str, Any]]:
    payload = raw.get(PAYLOAD_KEY)
    outcomes = raw.get("candidate_closed_loop_outcomes")
    _validate_payload(payload, expected_candidates, label)
    if not isinstance(outcomes, list) or len(outcomes) != int(expected_candidates):
        raise ValueError(f"{label} must contain complete candidate outcomes.")
    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    features = {
        field: np.asarray(payload[field], dtype=np.float64)
        for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES
    }
    rows = []
    for candidate_index, raw_outcome in enumerate(outcomes):
        outcome = _outcome(raw_outcome, f"{label} outcome {candidate_index}")
        value_delta = outcome["value"] - top1["value"]
        progress_delta = outcome["progress_m"] - top1["progress_m"]
        hard_worse = outcome["hard_violation_count"] > top1["hard_violation_count"]
        beneficial = (
            candidate_index != 0
            and outcome["feasible"]
            and value_delta >= float(min_value_gain)
            and progress_delta >= -float(progress_loss_budget_m)
            and not hard_worse
        )
        harmful = (
            candidate_index != 0
            and (
                not outcome["feasible"]
                or hard_worse
                or value_delta <= -float(min_value_loss)
                or progress_delta < -float(progress_loss_budget_m)
            )
        )
        if candidate_index == 0:
            cls = CLASS_TOP1
        elif beneficial:
            cls = CLASS_BENEFICIAL
        elif harmful:
            cls = CLASS_HARMFUL
        else:
            cls = CLASS_NEUTRAL
        feature_values = {
            name: float(values[candidate_index])
            for name, values in features.items()
            if np.isfinite(values[candidate_index])
        }
        flags = {
            "infeasible": not outcome["feasible"],
            "progress_loss": progress_delta < -float(progress_loss_budget_m),
            "outcome_value_loss": value_delta <= -float(min_value_loss),
            "hard_violation_worse": hard_worse,
            "collision_worse": outcome["collision"] and not top1["collision"],
            "near_miss_worse": outcome["near_miss"] and not top1["near_miss"],
            "lane_worse": outcome["lane_violation"] and not top1["lane_violation"],
            "red_light_worse": (
                outcome["red_light_violation"] and not top1["red_light_violation"]
            ),
        }
        rows.append(
            {
                "context": context,
                "candidate_index": candidate_index,
                "class": cls,
                "outcome_value_delta_vs_top1": value_delta,
                "progress_delta_vs_top1_m": progress_delta,
                "hard_violation_delta_vs_top1": (
                    outcome["hard_violation_count"] - top1["hard_violation_count"]
                ),
                "flags": flags,
                "features": feature_values,
                "interaction_zero": (
                    abs(feature_values.get("comfort_progress_interaction_cost", 0.0))
                    <= 1e-12
                ),
                "progress_deficit_zero": (
                    abs(feature_values.get("route_progress_deficit_vs_top1_m", 0.0))
                    <= 1e-12
                ),
                "jerk_excess_zero": (
                    abs(feature_values.get("dp_prior_jerk_excess_cost", 0.0))
                    <= 1e-12
                ),
            }
        )
    return rows


def _validate_payload(payload: Any, expected_candidates: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing {PAYLOAD_KEY} payload.")
    expected = {
        "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
        "available": True,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"{label} interaction payload {field}={payload.get(field)!r}.")
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} interaction payload embeds outcome labels.")
    if payload.get("candidate_count") != int(expected_candidates):
        raise ValueError(f"{label} interaction payload candidate_count mismatch.")
    for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES:
        array = np.asarray(payload.get(field), dtype=np.float64)
        if array.shape != (int(expected_candidates),):
            raise ValueError(f"{label} {field} shape={list(array.shape)}.")
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{label} {field} contains nonfinite values.")
        if np.any(array < -1e-12):
            raise ValueError(f"{label} {field} contains negative values.")


def _outcome(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    value = _float(raw.get("value"))
    progress = _float(raw.get("progress_m"))
    if value is None or progress is None:
        raise ValueError(f"{label} missing finite value/progress_m.")
    flags = {
        "collision": bool(raw.get("collision")),
        "near_miss": bool(raw.get("near_miss")),
        "lane_violation": bool(raw.get("lane_violation")),
        "red_light_violation": bool(raw.get("red_light_violation")),
    }
    return {
        "value": value,
        "progress_m": progress,
        "feasible": bool(raw.get("feasible")),
        "hard_violation_count": sum(int(value) for value in flags.values()),
        **flags,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision")
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    passed = (
        decision.get("status") == SEPARABILITY_REJECT_STATUS
        and decision.get("passed") is False
        and decision.get("primary_gap") == SOURCE_PRIMARY_GAP
        and decision.get("authorized_next_work") == SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": decision.get("status"),
        "passed_value": decision.get("passed"),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promising_screen_count": decision.get("promising_screen_count"),
    }


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    ranked = report.get("ranked_screens")
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return ranked[0]
    return None


def _positive_atom_screens(report: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = report.get("ranked_screens")
    if not isinstance(ranked, list):
        return []
    screens = [
        screen
        for screen in ranked
        if isinstance(screen, dict)
        and screen.get("descriptor") == "comfort_progress_interaction_cost"
        and bool(screen.get("atom_candidate_eligible")) is True
        and float(screen.get("threshold", 0.0)) > 1e-12
    ]
    return sorted(
        screens,
        key=lambda item: (
            -float(item.get("beneficial_retain_rate", 0.0)),
            float(item.get("allowed_harmful_rate", 1.0)),
            -float(item.get("harmful_block_rate", 0.0)),
        ),
    )


def _diagnosis(
    rows: list[dict[str, Any]],
    best_screen: dict[str, Any] | None,
    best_positive: dict[str, Any] | None,
) -> dict[str, Any]:
    harmful = [row for row in rows if row["class"] == CLASS_HARMFUL]
    beneficial = [row for row in rows if row["class"] == CLASS_BENEFICIAL]
    neutral = [row for row in rows if row["class"] == CLASS_NEUTRAL]
    positive_threshold = (
        None if best_positive is None else float(best_positive.get("threshold", 0.0))
    )
    allowed_harmful = (
        []
        if positive_threshold is None
        else [
            row
            for row in harmful
            if row["features"].get("comfort_progress_interaction_cost", 0.0)
            < positive_threshold
        ]
    )
    blocked_beneficial_at_zero = [
        row
        for row in beneficial
        if row["features"].get("comfort_progress_interaction_cost", 0.0) >= 0.0
    ]
    zero_interaction_harmful = [row for row in harmful if row["interaction_zero"]]
    zero_progress_harmful = [row for row in harmful if row["progress_deficit_zero"]]
    zero_jerk_harmful = [row for row in harmful if row["jerk_excess_zero"]]
    reasons = _reason_counts(harmful)
    if len(blocked_beneficial_at_zero) == len(beneficial) and beneficial:
        primary = "zero_threshold_blocks_all_beneficial"
    elif zero_interaction_harmful:
        primary = "harmful_candidates_have_zero_interaction"
    elif allowed_harmful:
        primary = "positive_threshold_retains_harmful_candidates"
    else:
        primary = "interaction_support_or_label_definition_insufficient"
    return {
        "primary_bottleneck": primary,
        "recommended_route": (
            "reject_non_turn_interaction_atom_and_return_to_progress_lane_hard_context"
        ),
        "camp_retraining_recommended": False,
        "schema_promotion_recommended": False,
        "best_screen": _screen_summary(best_screen),
        "best_positive_atom_screen": _screen_summary(best_positive),
        "counts": {
            "beneficial": len(beneficial),
            "harmful": len(harmful),
            "neutral": len(neutral),
            "blocked_beneficial_at_zero": len(blocked_beneficial_at_zero),
            "allowed_harmful_at_best_positive": len(allowed_harmful),
            "zero_interaction_harmful": len(zero_interaction_harmful),
            "zero_progress_deficit_harmful": len(zero_progress_harmful),
            "zero_jerk_excess_harmful": len(zero_jerk_harmful),
        },
        "harmful_reason_counts": reasons,
        "harmful_zero_breakdown": {
            "interaction_zero_by_reason": _reason_counts(zero_interaction_harmful),
            "progress_deficit_zero_by_reason": _reason_counts(zero_progress_harmful),
            "jerk_excess_zero_by_reason": _reason_counts(zero_jerk_harmful),
        },
        "beneficial_summary": _row_summary(beneficial),
        "harmful_summary": _row_summary(harmful),
        "allowed_harmful_at_best_positive": _examples(allowed_harmful),
        "blocked_beneficial_at_zero": _examples(blocked_beneficial_at_zero),
        "feature_overlap": _feature_overlap(beneficial, harmful),
    }


def _decision(
    source: dict[str, Any],
    *,
    formal_seed_records: int,
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_work = "fix_non_turn_logit_separability_source_before_bottleneck"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_work = None
    else:
        status = READY_STATUS
        next_work = NEXT_WORK
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_bottleneck": diagnosis["primary_bottleneck"],
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _row_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "value_delta": _stats([row["outcome_value_delta_vs_top1"] for row in rows]),
        "progress_delta_m": _stats([row["progress_delta_vs_top1_m"] for row in rows]),
        "route_progress_deficit_vs_top1_m": _stats(
            [
                row["features"].get("route_progress_deficit_vs_top1_m")
                for row in rows
            ]
        ),
        "dp_prior_jerk_excess_cost": _stats(
            [row["features"].get("dp_prior_jerk_excess_cost") for row in rows]
        ),
        "comfort_progress_interaction_cost": _stats(
            [
                row["features"].get("comfort_progress_interaction_cost")
                for row in rows
            ]
        ),
    }


def _feature_summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = {}
    for name in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES:
        summaries[name] = {
            "beneficial": _stats(
                [
                    row["features"].get(name)
                    for row in rows
                    if row["class"] == CLASS_BENEFICIAL
                ]
            ),
            "harmful": _stats(
                [
                    row["features"].get(name)
                    for row in rows
                    if row["class"] == CLASS_HARMFUL
                ]
            ),
            "neutral": _stats(
                [
                    row["features"].get(name)
                    for row in rows
                    if row["class"] == CLASS_NEUTRAL
                ]
            ),
        }
    return summaries


def _feature_overlap(
    beneficial: list[dict[str, Any]],
    harmful: list[dict[str, Any]],
) -> dict[str, Any]:
    overlap = {}
    for name in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES:
        b = _finite_values([row["features"].get(name) for row in beneficial])
        h = _finite_values([row["features"].get(name) for row in harmful])
        if b.size == 0 or h.size == 0:
            overlap[name] = {"available": False}
            continue
        bq = _quantiles(b)
        hq = _quantiles(h)
        overlap[name] = {
            "available": True,
            "beneficial": bq,
            "harmful": hq,
            "iqr_overlap": max(bq["p25"], hq["p25"]) <= min(bq["p75"], hq["p75"]),
            "harmful_at_or_below_beneficial_p75_rate": _rate(
                int(np.sum(h <= bq["p75"] + 1e-12)),
                h.size,
            ),
            "beneficial_at_or_above_harmful_p25_rate": _rate(
                int(np.sum(b >= hq["p25"] - 1e-12)),
                b.size,
            ),
        }
    return overlap


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason in _reasons(row):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _reasons(row: dict[str, Any]) -> list[str]:
    reasons = [name for name, value in row["flags"].items() if value]
    return reasons or ["beneficial_or_neutral"]


def _examples(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            row["features"].get("comfort_progress_interaction_cost", 0.0),
            row["context"].get("record_index", 0),
            row["candidate_index"],
        ),
    )
    examples = []
    for row in ranked[:limit]:
        examples.append(
            {
                "log_path": row["context"].get("log_path"),
                "record_index": row["context"].get("record_index"),
                "candidate_index": row["candidate_index"],
                "class": row["class"],
                "reasons": _reasons(row),
                "value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "features": row["features"],
            }
        )
    return examples


def _class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        CLASS_BENEFICIAL: 0,
        CLASS_HARMFUL: 0,
        CLASS_NEUTRAL: 0,
    }
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return counts


def _screen_summary(screen: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(screen, dict):
        return None
    return {
        "screen_name": screen.get("screen_name"),
        "descriptor": screen.get("descriptor"),
        "threshold": screen.get("threshold"),
        "harmful_block_rate": screen.get("harmful_block_rate"),
        "beneficial_retain_rate": screen.get("beneficial_retain_rate"),
        "allowed_harmful_rate": screen.get("allowed_harmful_rate"),
        "blocked_count": screen.get("blocked_count"),
        "allowed_count": screen.get("allowed_count"),
    }


def _stats(values: list[Any]) -> dict[str, Any]:
    array = _finite_values(values)
    if array.size == 0:
        return {"count": 0, "min": None, "median": None, "max": None}
    return {
        "count": int(array.size),
        "min": float(np.min(array)),
        "p25": float(np.percentile(array, 25)),
        "median": float(np.median(array)),
        "p75": float(np.percentile(array, 75)),
        "max": float(np.max(array)),
    }


def _finite_values(values: list[Any]) -> np.ndarray:
    finite = []
    for value in values:
        number = _float(value)
        if number is not None:
            finite.append(number)
    return np.asarray(finite, dtype=np.float64)


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "p75": float(np.percentile(values, 75)),
        "max": float(np.max(values)),
    }


def _discover_logs(paths: list[Path]) -> list[Path]:
    logs = []
    for path in paths:
        if path.is_file():
            logs.append(path)
        elif path.is_dir():
            logs.extend(sorted(path.rglob("camp_selection_log.json")))
    return sorted(dict.fromkeys(logs))


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        value = record.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            value = metadata.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _safe_record_count(rows: list[dict[str, Any]], expected_candidates: int) -> int:
    if expected_candidates <= 0:
        return 0
    return len(rows) // int(expected_candidates)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Non-Turn-Logit Interaction Bottleneck Diagnosis",
        "",
        "This is a read-only diagnostic over existing matched nonformal logs.",
        "",
        f"- status: `{decision['status']}`",
        f"- primary bottleneck: `{decision['primary_bottleneck']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Diagnosis",
        "",
        "```json",
        json.dumps(report["diagnosis"], indent=2, sort_keys=True),
        "```",
        "",
        "## Feature Summaries",
        "",
        "```json",
        json.dumps(report["feature_summaries"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
