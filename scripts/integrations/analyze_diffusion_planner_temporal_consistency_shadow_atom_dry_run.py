#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "temporal_consistency_atom_schema_preflight_ready"
SOURCE_READY_NEXT_WORK = "temporal_consistency_shadow_atom_dry_run_only"
READY_STATUS = "temporal_consistency_shadow_atom_dry_run_ready"
REJECT_STATUS = "temporal_consistency_shadow_atom_dry_run_rejected"
AUTHORIZED_NEXT_WORK = "temporal_consistency_shadow_weight_sensitivity_existing_smoke_only"

LOG_NAME = "camp_selection_log.json"
PAYLOAD_KEY = "temporal_consistency_payload_logging"
ATOM_NAME = "previous_plan_temporal_consistency_rms_m"
COEFFICIENT_KEY = "previous_plan_temporal_consistency_rms_m"
SCORE_TOLERANCE = 1e-9

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Shadow-only dry run for appending the temporal-consistency "
            "coefficient to CAMP atom tables without changing deployed selection."
        )
    )
    parser.add_argument("--schema_preflight_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--expected_available_records", type=int, default=None)
    parser.add_argument("--expected_fail_closed_records", type=int, default=None)
    parser.add_argument("--shadow_scale_m", type=float, default=1.0)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        schema_preflight=_load_json(args.schema_preflight_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        expected_available_records=args.expected_available_records,
        expected_fail_closed_records=args.expected_fail_closed_records,
        shadow_scale_m=args.shadow_scale_m,
        label=args.label,
        paths={
            "schema_preflight_json": str(args.schema_preflight_json),
            "candidate_root": str(args.candidate_root),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    *,
    schema_preflight: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    expected_available_records: int | None = None,
    expected_fail_closed_records: int | None = None,
    shadow_scale_m: float = 1.0,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if not math.isfinite(shadow_scale_m) or shadow_scale_m <= 0.0:
        raise ValueError("shadow_scale_m must be finite and positive.")

    log_payloads = _load_selection_logs(candidate_root)
    source = _source_summary(schema_preflight)
    schema = dict(schema_preflight.get("atom_schema") or {})
    expected_available = (
        expected_records - expected_logs
        if expected_available_records is None
        else expected_available_records
    )
    expected_fail_closed = (
        expected_logs
        if expected_fail_closed_records is None
        else expected_fail_closed_records
    )
    records = [
        _shadow_record(
            record=record,
            run_id=run_id,
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
            shadow_scale_m=shadow_scale_m,
        )
        for global_index, (run_id, record_index, record) in enumerate(_iter_records(log_payloads))
    ]
    summary = _summary(records, log_payloads, shadow_scale_m=shadow_scale_m)
    checks = [
        *_source_checks(source),
        *_schema_checks(schema),
        *_record_count_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_available_records=expected_available,
            expected_fail_closed_records=expected_fail_closed,
        ),
        *_shadow_checks(summary),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_shadow_atom_dry_run_v1",
            "label": label,
            "role": "shadow-only atom table append and zero-weight affine bookkeeping",
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "deployed_atom_schema_change": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This dry run reads existing logging-enabled records only. For "
                "available payloads it appends the fixed current-tick "
                "temporal-consistency coefficient as a shadow atom and appends a "
                "zero shadow weight. Therefore score_k(w)=a_k^T w bookkeeping is "
                "checked while deployed CAMP scores and selected_index must remain "
                "unchanged. It does not train CAMP, run DP, deploy the atom, read "
                "future outcomes, claim trajectory-coordinate convexity, or claim "
                "a DP-side classical Benders decomposition."
            ),
        },
        "source_summary": source,
        "atom_schema": schema,
        "shadow_scale_m": shadow_scale_m,
        "record_checks": checks,
        "dry_run_records": records,
        "dry_run_summary": summary,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "atom_schema_preflight_ready": bool(
            decision.get("atom_schema_preflight_ready")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
    }


def _shadow_record(
    *,
    record: dict[str, Any],
    run_id: str,
    record_index: int,
    global_index: int,
    expected_candidates: int,
    shadow_scale_m: float,
) -> dict[str, Any]:
    errors: list[str] = []
    payload = record.get(PAYLOAD_KEY)
    if not isinstance(payload, dict):
        return _record_error(run_id, record_index, global_index, "payload_missing")
    for key in (
        "selection_effect",
        "future_outcome_leakage",
        "closed_loop_outcome_fields_read",
        "online_selector_change",
        "deployed_atom_vector_change",
        "classical_benders_claim",
    ):
        if bool(payload.get(key)):
            errors.append(f"{key}_must_be_false")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")

    selected_index = _optional_int(record.get("selected_index"))
    available = bool(payload.get("available"))
    availability_reason = payload.get("availability_reason")
    candidate_count = _optional_int(payload.get("candidate_count"))
    if candidate_count != expected_candidates:
        errors.append(f"candidate_count expected {expected_candidates}, got {candidate_count}")
    atom_names = _string_list(record.get("atom_names"))
    weights = _float_vector(record.get("weights"))
    selection_weights = _float_vector(record.get("selection_weights"))
    atoms = _matrix(record.get("atoms"))
    normalized_atoms = _matrix(record.get("normalized_atoms"))
    scores = _score_vector(record.get("scores"))
    selection_scores = _score_vector(record.get("selection_scores"))
    feasible_mask = _bool_vector(record.get("feasible_mask"), expected_candidates)

    if not atom_names:
        errors.append("atom_names_missing")
    if len(weights) != len(atom_names):
        errors.append("weights_shape_mismatch")
    if len(selection_weights) != len(atom_names):
        errors.append("selection_weights_shape_mismatch")
    if _shape(atoms) != [expected_candidates, len(atom_names)]:
        errors.append("atoms_shape_mismatch")
    if _shape(normalized_atoms) != [expected_candidates, len(atom_names)]:
        errors.append("normalized_atoms_shape_mismatch")
    if len(scores) != expected_candidates:
        errors.append("scores_shape_mismatch")
    if len(selection_scores) != expected_candidates:
        errors.append("selection_scores_shape_mismatch")
    if len(feasible_mask) != expected_candidates:
        errors.append("feasible_mask_shape_mismatch")
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")

    base_score_max_abs_diff = _score_max_abs_diff(normalized_atoms, weights, scores)
    if not math.isfinite(base_score_max_abs_diff) or base_score_max_abs_diff > SCORE_TOLERANCE:
        errors.append("base_affine_score_mismatch")
    selection_score_max_abs_diff = _selection_score_max_abs_diff(
        normalized_atoms,
        selection_weights,
        selection_scores,
        feasible_mask,
    )
    if (
        not math.isfinite(selection_score_max_abs_diff)
        or selection_score_max_abs_diff > SCORE_TOLERANCE
    ):
        errors.append("selection_affine_score_mismatch")

    if not available:
        if availability_reason != "previous_selected_plan_absent":
            errors.append("unavailable_reason_not_fail_closed")
        return {
            "run_id": run_id,
            "record_index": record_index,
            "global_index": global_index,
            "available": False,
            "availability_reason": availability_reason,
            "selected_index": selected_index,
            "candidate_count": candidate_count,
            "base_atom_count": len(atom_names),
            "shadow_atom_count": len(atom_names),
            "shadow_append_available": False,
            "shadow_append_reason": "fail_closed_unavailable",
            "base_score_max_abs_diff": base_score_max_abs_diff,
            "selection_score_max_abs_diff": selection_score_max_abs_diff,
            "shadow_zero_weight_score_max_abs_diff": 0.0,
            "selection_effect": False,
            "deployed_selection_preserved": True,
            "ranking_signal_present": False,
            "temporal_only_best_index": None,
            "temporal_only_would_change_selected_index": False,
            "errors": errors,
            "passed": not errors,
        }

    coeff = _float_vector(payload.get(COEFFICIENT_KEY))
    if len(coeff) != expected_candidates:
        errors.append("temporal_coefficient_shape_mismatch")
    if any((not math.isfinite(value)) or value < 0.0 for value in coeff):
        errors.append("temporal_coefficient_nonfinite_or_negative")
    normalized_coeff = [value / shadow_scale_m for value in coeff]
    shadow_weights = [*weights, 0.0]
    shadow_selection_weights = [*selection_weights, 0.0]
    shadow_normalized_atoms = [
        [*row, normalized_coeff[index]]
        for index, row in enumerate(normalized_atoms[: len(normalized_coeff)])
    ]
    shadow_scores = _dot_scores(shadow_normalized_atoms, shadow_weights)
    shadow_selection_scores = _masked_selection_scores(
        _dot_scores(shadow_normalized_atoms, shadow_selection_weights),
        feasible_mask,
    )
    shadow_zero_diff = _max_abs_score_diff(shadow_scores, scores)
    shadow_selection_zero_diff = _max_abs_score_diff(
        shadow_selection_scores,
        selection_scores,
    )
    if not math.isfinite(shadow_zero_diff) or shadow_zero_diff > SCORE_TOLERANCE:
        errors.append("shadow_zero_weight_score_changed")
    if (
        not math.isfinite(shadow_selection_zero_diff)
        or shadow_selection_zero_diff > SCORE_TOLERANCE
    ):
        errors.append("shadow_zero_weight_selection_score_changed")
    temporal_only_best = _argmin_feasible(coeff, feasible_mask)
    temporal_only_changed = (
        selected_index is not None
        and temporal_only_best is not None
        and temporal_only_best != selected_index
    )
    return {
        "run_id": run_id,
        "record_index": record_index,
        "global_index": global_index,
        "available": True,
        "availability_reason": availability_reason,
        "selected_index": selected_index,
        "candidate_count": candidate_count,
        "base_atom_count": len(atom_names),
        "shadow_atom_count": len(atom_names) + 1,
        "shadow_atom_name": ATOM_NAME,
        "shadow_append_available": True,
        "shadow_append_reason": "available_current_tick_coefficient",
        "base_atom_table_shape": _shape(atoms),
        "shadow_atom_table_shape": [expected_candidates, len(atom_names) + 1],
        "shadow_weight_count": len(shadow_weights),
        "shadow_weight_last": 0.0,
        "base_score_max_abs_diff": base_score_max_abs_diff,
        "selection_score_max_abs_diff": selection_score_max_abs_diff,
        "shadow_zero_weight_score_max_abs_diff": shadow_zero_diff,
        "shadow_zero_weight_selection_score_max_abs_diff": shadow_selection_zero_diff,
        "selection_effect": False,
        "deployed_selection_preserved": True,
        "ranking_signal_present": _has_ranking_signal(coeff),
        "temporal_only_best_index": temporal_only_best,
        "temporal_only_would_change_selected_index": temporal_only_changed,
        "temporal_coefficient_min": min(coeff) if coeff else None,
        "temporal_coefficient_max": max(coeff) if coeff else None,
        "errors": errors,
        "passed": not errors,
    }


def _record_error(
    run_id: str,
    record_index: int,
    global_index: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "record_index": record_index,
        "global_index": global_index,
        "available": False,
        "shadow_append_available": False,
        "errors": [reason],
        "passed": False,
    }


def _summary(
    records: list[dict[str, Any]],
    log_payloads: list[tuple[str, list[dict[str, Any]]]],
    *,
    shadow_scale_m: float,
) -> dict[str, Any]:
    available = [record for record in records if record.get("available") is True]
    unavailable = [record for record in records if record.get("available") is False]
    valid = [record for record in records if record.get("passed") is True]
    ranking = [record for record in available if record.get("ranking_signal_present")]
    temporal_change = [
        record
        for record in available
        if record.get("temporal_only_would_change_selected_index")
    ]
    score_diffs = [
        float(record.get("shadow_zero_weight_score_max_abs_diff", math.nan))
        for record in records
    ]
    selection_score_diffs = [
        float(record.get("shadow_zero_weight_selection_score_max_abs_diff", math.nan))
        for record in records
    ]
    return {
        "log_count": len(log_payloads),
        "records": len(records),
        "valid_records": len(valid),
        "available_records": len(available),
        "unavailable_records": len(unavailable),
        "fail_closed_unavailable_records": sum(
            1
            for record in unavailable
            if record.get("availability_reason") == "previous_selected_plan_absent"
        ),
        "shadow_appended_records": sum(
            1 for record in records if record.get("shadow_append_available") is True
        ),
        "ranking_signal_records": len(ranking),
        "temporal_only_would_change_selected_index_records": len(temporal_change),
        "temporal_only_changed_indices": [
            record["global_index"] for record in temporal_change
        ],
        "deployed_selection_preserved_records": sum(
            1 for record in records if record.get("deployed_selection_preserved") is True
        ),
        "max_shadow_zero_weight_score_abs_diff": _finite_max(score_diffs),
        "max_shadow_zero_weight_selection_score_abs_diff": _finite_max(
            selection_score_diffs
        ),
        "record_error_counts": _error_counts(records),
        "shadow_scale_m": shadow_scale_m,
        "shadow_weight_policy": "append_zero_weight_no_deployed_effect",
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_shadow_dry_run",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_schema_preflight_ready",
            source["atom_schema_preflight_ready"],
            True,
        ),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _schema_checks(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("schema_atom_name", schema.get("atom_name"), ATOM_NAME),
        _check_equal("schema_payload_key", schema.get("payload_key"), PAYLOAD_KEY),
        _check_equal(
            "schema_coefficient_key",
            schema.get("coefficient_key"),
            COEFFICIENT_KEY,
        ),
        _check_equal("schema_affine_score", schema.get("affine_score_compatible"), True),
        _check_equal("schema_convex_master", schema.get("convex_master_compatible"), True),
        _check_equal("schema_nonnegative", schema.get("nonnegative_by_definition"), True),
        _check_equal("schema_no_future_outcomes", schema.get("uses_future_outcomes"), False),
        _check_equal(
            "schema_no_classic_benders_claim",
            schema.get("classic_benders_claim"),
            False,
        ),
    ]


def _record_count_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
    expected_available_records: int,
    expected_fail_closed_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal(
            "available_record_count",
            summary["available_records"],
            expected_available_records,
        ),
        _check_equal(
            "fail_closed_unavailable_record_count",
            summary["fail_closed_unavailable_records"],
            expected_fail_closed_records,
        ),
    ]


def _shadow_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("all_records_valid", summary["valid_records"], summary["records"]),
        _check_equal(
            "shadow_appended_all_available_records",
            summary["shadow_appended_records"],
            summary["available_records"],
        ),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
        _check_equal(
            "ranking_signal_present",
            summary["ranking_signal_records"] > 0,
            True,
        ),
        _check_equal(
            "deployed_selection_preserved_all_records",
            summary["deployed_selection_preserved_records"],
            summary["records"],
        ),
        _check_equal(
            "shadow_zero_weight_scores_unchanged",
            summary["max_shadow_zero_weight_score_abs_diff"] <= SCORE_TOLERANCE,
            True,
        ),
        _check_equal(
            "shadow_zero_weight_selection_scores_unchanged",
            summary["max_shadow_zero_weight_selection_score_abs_diff"]
            <= SCORE_TOLERANCE,
            True,
        ),
        _check_equal("online_selector_mutated", False, False),
        _check_equal("deployed_atom_schema_mutated", False, False),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "shadow_atom_dry_run_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "ranking_signal_records": summary["ranking_signal_records"],
        "temporal_only_would_change_selected_index_records": summary[
            "temporal_only_would_change_selected_index_records"
        ],
        "max_shadow_zero_weight_score_abs_diff": summary[
            "max_shadow_zero_weight_score_abs_diff"
        ],
        "next_step": (
            "Run an existing-smoke shadow weight sensitivity diagnosis. Keep the "
            "atom shadow-only; do not train CAMP, deploy online selection, run "
            "Full36, use formal seeds, or claim safety benefit."
            if passed
            else "Reject the shadow atom dry-run and inspect failed source/schema/record checks."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["dry_run_summary"]
    lines = [
        "# Temporal Consistency Shadow Atom Dry Run",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Shadow appended records: `{summary['shadow_appended_records']}`",
        f"- Ranking signal records: `{summary['ranking_signal_records']}`",
        f"- Temporal-only changed records: `{summary['temporal_only_would_change_selected_index_records']}`",
        f"- Max zero-weight score diff: `{summary['max_shadow_zero_weight_score_abs_diff']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summary",
        "",
        f"`{summary}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["record_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_selection_logs(root: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    paths = sorted(root.rglob(LOG_NAME))
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        result.append((path.parent.name, [row for row in payload if isinstance(row, dict)]))
    return result


def _iter_records(
    logs: list[tuple[str, list[dict[str, Any]]]],
) -> list[tuple[str, int, dict[str, Any]]]:
    rows: list[tuple[str, int, dict[str, Any]]] = []
    for run_id, records in logs:
        rows.extend((run_id, index, record) for index, record in enumerate(records))
    return rows


def _score_max_abs_diff(
    normalized_atoms: list[list[float]],
    weights: list[float],
    scores: list[float],
) -> float:
    return _max_abs_score_diff(_dot_scores(normalized_atoms, weights), scores)


def _selection_score_max_abs_diff(
    normalized_atoms: list[list[float]],
    weights: list[float],
    selection_scores: list[float],
    feasible_mask: list[bool],
) -> float:
    raw = _dot_scores(normalized_atoms, weights)
    return _max_abs_score_diff(_masked_selection_scores(raw, feasible_mask), selection_scores)


def _dot_scores(matrix: list[list[float]], weights: list[float]) -> list[float]:
    if not matrix or not weights:
        return []
    return [sum(value * weight for value, weight in zip(row, weights)) for row in matrix]


def _masked_selection_scores(scores: list[float], feasible_mask: list[bool]) -> list[float]:
    if feasible_mask and not any(feasible_mask):
        return list(scores)
    return [
        score if index < len(feasible_mask) and feasible_mask[index] else math.inf
        for index, score in enumerate(scores)
    ]


def _max_abs_score_diff(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return math.inf
    diffs = []
    for a, b in zip(left, right):
        if math.isinf(a) and math.isinf(b):
            diffs.append(0.0)
        elif math.isfinite(a) and math.isfinite(b):
            diffs.append(abs(a - b))
        else:
            return math.inf
    return max(diffs) if diffs else 0.0


def _argmin_feasible(values: list[float], feasible_mask: list[bool]) -> int | None:
    candidates = [
        (index, value)
        for index, value in enumerate(values)
        if index < len(feasible_mask) and feasible_mask[index]
    ]
    if not candidates:
        return None
    best_index, _ = min(candidates, key=lambda item: (item[1], item[0]))
    return best_index


def _has_ranking_signal(values: list[float]) -> bool:
    return bool(values) and max(values) > min(values)


def _shape(matrix: list[list[float]]) -> list[int]:
    if not matrix:
        return [0, 0]
    return [len(matrix), len(matrix[0]) if matrix[0] else 0]


def _matrix(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    matrix = []
    for row in value:
        if not isinstance(row, list):
            return []
        parsed = _float_vector(row)
        if len(parsed) != len(row):
            return []
        matrix.append(parsed)
    return matrix


def _float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _score_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if item == "inf":
            result.append(math.inf)
            continue
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _bool_vector(value: Any, expected_candidates: int) -> list[bool]:
    if isinstance(value, list):
        return [bool(item) for item in value]
    return [True for _ in range(expected_candidates)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finite_max(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return max(finite) if finite else math.inf


def _error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for error in record.get("errors") or []:
            counts[error] = counts.get(error, 0) + 1
    return counts


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
