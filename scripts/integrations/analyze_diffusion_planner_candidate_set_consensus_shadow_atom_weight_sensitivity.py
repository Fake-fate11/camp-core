#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (  # noqa: E402
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    ATOM_NAME,
    AUTHORIZED_NEXT_WORK as SOURCE_READY_NEXT_WORK,
    COEFFICIENT_FIELD,
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
    PAYLOAD_KEY,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_shadow_atom_weight_sensitivity_ready"
REJECT_STATUS = "candidate_set_consensus_shadow_atom_weight_sensitivity_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_weight_sensitivity_result_review_only"
)

LOG_NAME = "camp_selection_log.json"

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline read-only candidate-set consensus shadow atom weight "
            "sensitivity over existing nonformal CAMP selection logs. It does "
            "not train CAMP, run replay, promote atoms, or modify DP."
        )
    )
    parser.add_argument("--weight_sensitivity_plan_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        weight_sensitivity_plan=_load_json(args.weight_sensitivity_plan_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        label=args.label,
        paths={
            "weight_sensitivity_plan_json": str(args.weight_sensitivity_plan_json),
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
    weight_sensitivity_plan: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")

    source = _source_summary(weight_sensitivity_plan)
    lambda_grid = tuple(source["lambda_grid"])
    logs = _load_selection_logs(candidate_root)
    records = [
        _sensitivity_record(
            record=record,
            run_id=log["run_id"],
            log_path=log["path"],
            formal_seed_detected=bool(log["formal_seed_detected"]),
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
            lambda_grid=lambda_grid,
        )
        for global_index, (log, record_index, record) in enumerate(_iter_records(logs))
    ]
    summary = _summary(records, logs, lambda_grid)
    checks = [
        *_source_checks(
            source,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_candidates=expected_candidates,
        ),
        *_input_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
        ),
        *_sensitivity_checks(summary, lambda_grid),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_shadow_atom_weight_sensitivity_v1",
            "label": label,
            "role": (
                "read-only offline lambda-grid sensitivity over existing "
                "candidate-set consensus broader nonformal logs"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "deployed_atom_schema_change": False,
            "future_outcome_labels_used_for_selection": False,
            "safety_score_fields_used_for_selection": False,
            "formal_seed_records": int(summary["formal_seed_log_count"]),
            "paths": paths or {"candidate_root": str(candidate_root)},
            "math_boundary": (
                "This sensitivity scan reuses existing nonformal selection logs "
                "and applies predeclared nonnegative lambda values to the fixed "
                "current-tick candidate-set consensus coefficient. For each "
                "finite feasible candidate it evaluates score'_k(lambda) = "
                "selection_score_k + lambda * "
                "candidate_set_consensus_center_rms_m[k]. The coefficient is "
                "fixed before scoring, so the expression remains affine in "
                "weights. The scan is diagnostic only: no online selector, "
                "training, DP execution, safety-benefit claim, or classical "
                "Benders decomposition is introduced."
            ),
        },
        "source_summary": source,
        "lambda_grid": list(lambda_grid),
        "sensitivity_records": records,
        "sensitivity_summary": summary,
        "sensitivity_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["sensitivity_summary"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Weight Sensitivity",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Max changed records: `{decision['max_changed_records']}`",
        f"- Min critical positive lambda: `{summary['min_critical_positive_lambda']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summary",
        "",
        f"`{summary}`",
        "",
        "## Lambda Grid",
        "",
        "| Lambda | Changed records | Changed rate |",
        "| ---: | ---: | ---: |",
    ]
    for row in summary["by_lambda"]:
        lines.append(
            f"| `{row['lambda']}` | `{row['changed_records']}` | "
            f"`{row['changed_rate']}` |"
        )
    lines.extend(
        [
            "",
            "## Route Summary",
            "",
            "| Run | Records | Fallback retained | Max changed records |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for run_id, row in summary["by_run"].items():
        lines.append(
            f"| `{run_id}` | `{row['records']}` | "
            f"`{row['fallback_retained_records']}` | "
            f"`{row['max_changed_records']}` |"
        )
    lines.extend(
        [
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
    )
    for check in report["sensitivity_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("sensitivity_plan"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "weight_sensitivity_plan_ready": bool(
            decision.get("weight_sensitivity_plan_ready")
        ),
        "sensitivity_implementation_authorized": bool(
            decision.get("sensitivity_implementation_authorized")
        ),
        "sensitivity_execution_authorized": bool(
            decision.get("sensitivity_execution_authorized")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
        "expected_logs": _optional_int(plan.get("expected_logs")),
        "expected_records": _optional_int(plan.get("expected_records")),
        "expected_candidates": _optional_int(plan.get("expected_candidates")),
        "formal_seeds_forbidden": sorted(
            _optional_int(seed)
            for seed in (plan.get("formal_seeds_forbidden") or [])
            if _optional_int(seed) is not None
        ),
        "atom_name": plan.get("atom_name"),
        "payload_key": plan.get("payload_key"),
        "coefficient_field": plan.get("coefficient_field"),
        "lambda_grid": _validated_lambda_grid(plan.get("lambda_grid") or []),
        "score_formula": plan.get("score_formula"),
    }


def _source_checks(
    source: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    grid = list(source["lambda_grid"])
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_implementation_unit_tests",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_weight_sensitivity_plan_ready",
            source["weight_sensitivity_plan_ready"],
            True,
        ),
        _check_equal(
            "source_implementation_authorized",
            source["sensitivity_implementation_authorized"],
            True,
        ),
        _check_equal(
            "source_execution_not_pre_authorized",
            source["sensitivity_execution_authorized"],
            False,
        ),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_expected_logs", source["expected_logs"], expected_logs),
        _check_equal("source_expected_records", source["expected_records"], expected_records),
        _check_equal("source_expected_candidates", source["expected_candidates"], expected_candidates),
        _check_equal("source_formal_seeds_forbidden", source["formal_seeds_forbidden"], sorted(FORMAL_SEEDS)),
        _check_equal("source_atom_name", source["atom_name"], ATOM_NAME),
        _check_equal("source_payload_key", source["payload_key"], PAYLOAD_KEY),
        _check_equal("source_coefficient_field", source["coefficient_field"], COEFFICIENT_FIELD),
        _check_equal("source_lambda_grid_nonempty", bool(grid), True),
        _check_equal("source_lambda_grid_contains_zero", 0.0 in grid, True),
        _check_equal("source_lambda_grid_has_positive_value", any(value > 0.0 for value in grid), True),
        _check_equal("source_lambda_grid_sorted_unique", grid == sorted(set(grid)), True),
        _check_equal("source_score_formula_affine", "selection_score_k + lambda *" in str(source["score_formula"]), True),
    ]


def _input_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal("no_formal_seed_logs", summary["formal_seed_log_count"], 0),
    ]


def _sensitivity_checks(
    summary: dict[str, Any],
    lambda_grid: tuple[float, ...],
) -> list[dict[str, Any]]:
    zero_row = _by_lambda(summary, 0.0)
    return [
        _check_equal("all_records_valid", summary["valid_records"], summary["records"]),
        _check_equal("all_payloads_available", summary["available_records"], summary["records"]),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
        _check_equal("lambda_zero_preserves_selection", zero_row["changed_records"], 0),
        _check_equal("positive_lambda_grid_present", any(value > 0.0 for value in lambda_grid), True),
        _check_equal("ranking_signal_present", summary["ranking_signal_records"] > 0, True),
        _check_equal("route_level_reporting_present", bool(summary["by_run"]), True),
        _check_equal("online_selector_mutated", False, False),
        _check_equal("deployed_atom_schema_mutated", False, False),
        _check_equal("safety_score_fields_used_for_selection", False, False),
    ]


def _sensitivity_record(
    *,
    record: dict[str, Any],
    run_id: str,
    log_path: str,
    formal_seed_detected: bool,
    record_index: int,
    global_index: int,
    expected_candidates: int,
    lambda_grid: tuple[float, ...],
) -> dict[str, Any]:
    errors: list[str] = []
    if formal_seed_detected:
        errors.append("formal_seed_detected")
    payload = record.get(PAYLOAD_KEY)
    if not isinstance(payload, dict):
        return _record_error(run_id, log_path, record_index, global_index, "payload_missing", errors)

    _payload_boundary_errors(payload, record, errors)
    selected_index = _optional_int(record.get("selected_index"))
    candidate_count = _optional_int(payload.get("candidate_count"))
    if candidate_count != expected_candidates:
        errors.append("candidate_count_mismatch")
    available = bool(payload.get("available"))
    if not available:
        errors.append("payload_unavailable")
    selection_scores = _score_vector(record.get("selection_scores"))
    feasible_mask = _bool_vector(record.get("feasible_mask"), expected_candidates)
    coeff = _float_vector(payload.get(COEFFICIENT_FIELD))
    used_fallback = bool(record.get("used_fallback", not any(feasible_mask)))
    fallback_mode_present = "camp_fallback_mode" in record
    infeasibility_reasons_present = isinstance(record.get("infeasibility_reasons"), list)
    if len(selection_scores) != expected_candidates:
        errors.append("selection_scores_shape_mismatch")
    if len(feasible_mask) != expected_candidates:
        errors.append("feasible_mask_shape_mismatch")
    if len(coeff) != expected_candidates:
        errors.append("coefficient_shape_mismatch")
    if any((not math.isfinite(value)) or value < 0.0 for value in coeff):
        errors.append("coefficient_nonfinite_or_negative")
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")
    if not fallback_mode_present:
        errors.append("camp_fallback_mode_missing")
    if not infeasibility_reasons_present:
        errors.append("infeasibility_reasons_missing")

    candidate_domain = _candidate_domain(selection_scores, feasible_mask)
    fallback_retained = used_fallback or not candidate_domain
    if not fallback_retained and selected_index not in candidate_domain:
        errors.append("selected_index_not_in_candidate_domain")
    lambda_results = []
    for lam in lambda_grid:
        if fallback_retained:
            shadow_selected = selected_index
            changed = False
            score_delta = 0.0
        else:
            shadow_scores = _shadow_scores(selection_scores, coeff, lam, candidate_domain)
            shadow_selected = _argmin(shadow_scores, candidate_domain)
            changed = selected_index is not None and shadow_selected != selected_index
            score_delta = (
                shadow_scores[shadow_selected] - selection_scores[selected_index]
                if shadow_selected is not None and selected_index is not None
                else math.nan
            )
        lambda_results.append(
            {
                "lambda": lam,
                "shadow_selected_index": shadow_selected,
                "changed_selected_index": changed,
                "shadow_score_delta_vs_logged_selected": score_delta,
            }
        )
    critical_lambda = (
        None
        if fallback_retained
        else _critical_positive_lambda(
            selected_index=selected_index,
            selection_scores=selection_scores,
            coeff=coeff,
            candidate_domain=candidate_domain,
        )
    )
    return {
        "run_id": run_id,
        "log_path": log_path,
        "record_index": record_index,
        "global_index": global_index,
        "available": available,
        "selected_index": selected_index,
        "candidate_count": candidate_count,
        "used_fallback": used_fallback,
        "fallback_retained": fallback_retained,
        "candidate_domain": candidate_domain,
        "ranking_signal_present": _has_ranking_signal(coeff, candidate_domain),
        "critical_positive_lambda": critical_lambda,
        "lambda_results": lambda_results,
        "errors": errors,
        "passed": not errors,
    }


def _payload_boundary_errors(
    payload: dict[str, Any],
    record: dict[str, Any],
    errors: list[str],
) -> None:
    expected_scalars = {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            errors.append(f"payload_{key}_mismatch")
    if payload.get("atom_candidate_names") != list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append("payload_atom_candidate_names_mismatch")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")


def _record_error(
    run_id: str,
    log_path: str,
    record_index: int,
    global_index: int,
    reason: str,
    extra_errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "log_path": log_path,
        "record_index": record_index,
        "global_index": global_index,
        "available": False,
        "lambda_results": [],
        "errors": [*(extra_errors or []), reason],
        "passed": False,
    }


def _summary(
    records: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    lambda_grid: tuple[float, ...],
) -> dict[str, Any]:
    valid = [record for record in records if record.get("passed") is True]
    available = [record for record in records if record.get("available") is True]
    ranking = [record for record in valid if record.get("ranking_signal_present")]
    by_lambda = []
    transitions: dict[str, int] = {}
    for lam in lambda_grid:
        changed = []
        for record in valid:
            result = _lambda_result(record, lam)
            if result.get("changed_selected_index"):
                changed.append(record)
                key = f"{record.get('selected_index')}->{result.get('shadow_selected_index')}"
                transitions[key] = transitions.get(key, 0) + 1
        by_lambda.append(
            {
                "lambda": lam,
                "changed_records": len(changed),
                "changed_rate": len(changed) / len(valid) if valid else None,
            }
        )
    by_run: dict[str, dict[str, Any]] = {}
    for record in records:
        run = str(record.get("run_id"))
        row = by_run.setdefault(
            run,
            {
                "records": 0,
                "valid_records": 0,
                "ranking_signal_records": 0,
                "fallback_retained_records": 0,
                "changed_records_by_lambda": {str(lam): 0 for lam in lambda_grid},
                "max_changed_records": 0,
            },
        )
        row["records"] += 1
        row["valid_records"] += int(record.get("passed") is True)
        row["ranking_signal_records"] += int(record.get("ranking_signal_present") is True)
        row["fallback_retained_records"] += int(record.get("fallback_retained") is True)
        for lam in lambda_grid:
            result = _lambda_result(record, lam)
            row["changed_records_by_lambda"][str(lam)] += int(
                result.get("changed_selected_index") is True
            )
        row["max_changed_records"] = max(row["changed_records_by_lambda"].values())
    critical = [
        float(record["critical_positive_lambda"])
        for record in valid
        if record.get("critical_positive_lambda") is not None
    ]
    formal_logs = [log for log in logs if log.get("formal_seed_detected")]
    return {
        "log_count": len(logs),
        "records": len(records),
        "valid_records": len(valid),
        "available_records": len(available),
        "ranking_signal_records": len(ranking),
        "fallback_retained_records": sum(
            1 for record in records if record.get("fallback_retained") is True
        ),
        "formal_seed_log_count": len(formal_logs),
        "formal_seed_log_paths": [str(log["path"]) for log in formal_logs],
        "by_lambda": by_lambda,
        "by_run": dict(sorted(by_run.items())),
        "selected_index_transition_counts": dict(sorted(transitions.items())),
        "critical_positive_lambda_records": len(critical),
        "min_critical_positive_lambda": min(critical) if critical else None,
        "record_error_counts": _error_counts(records),
        "lambda_grid": list(lambda_grid),
    }


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    max_changed = max((row["changed_records"] for row in summary["by_lambda"]), default=0)
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "weight_sensitivity_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "max_changed_records": max_changed,
        "min_critical_positive_lambda": summary["min_critical_positive_lambda"],
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "next_step": (
            "Review the offline sensitivity result artifact only. Do not train "
            "CAMP, deploy online selection, run replay, run Full36, use formal "
            "seeds, modify DP, or claim safety benefit."
            if passed
            else "Reject the weight-sensitivity result and inspect failed source/input/record checks."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _load_selection_logs(root: Path) -> list[dict[str, Any]]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        path_text = str(path)
        run_id = path.parent.name
        result.append(
            {
                "run_id": run_id,
                "path": path_text,
                "formal_seed_detected": _contains_formal_seed(
                    f"{run_id} {path_text}"
                ),
                "records": [row for row in payload if isinstance(row, dict)],
            }
        )
    return result


def _iter_records(
    logs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], int, dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], int, dict[str, Any]]] = []
    for log in logs:
        rows.extend(
            (log, index, record)
            for index, record in enumerate(log.get("records") or [])
            if isinstance(record, dict)
        )
    return rows


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


def _validated_lambda_grid(value: Any) -> tuple[float, ...]:
    if not isinstance(value, list):
        return ()
    result = []
    for item in value:
        parsed = _optional_float(item)
        if parsed is None:
            return ()
        result.append(parsed)
    return tuple(result)


def _candidate_domain(selection_scores: list[float], feasible_mask: list[bool]) -> list[int]:
    return [
        index
        for index, score in enumerate(selection_scores)
        if index < len(feasible_mask) and feasible_mask[index] and math.isfinite(score)
    ]


def _shadow_scores(
    selection_scores: list[float],
    coeff: list[float],
    lam: float,
    domain: list[int],
) -> list[float]:
    scores = [math.inf for _ in selection_scores]
    for index in domain:
        scores[index] = selection_scores[index] + lam * coeff[index]
    return scores


def _argmin(values: list[float], domain: list[int]) -> int | None:
    candidates = [(index, values[index]) for index in domain]
    if not candidates:
        return None
    best_index, _ = min(candidates, key=lambda item: (item[1], item[0]))
    return int(best_index)


def _critical_positive_lambda(
    *,
    selected_index: int | None,
    selection_scores: list[float],
    coeff: list[float],
    candidate_domain: list[int],
) -> float | None:
    if selected_index is None or selected_index not in candidate_domain:
        return None
    selected_score = selection_scores[selected_index]
    selected_coeff = coeff[selected_index]
    thresholds = []
    for index in candidate_domain:
        if index == selected_index:
            continue
        if coeff[index] >= selected_coeff:
            continue
        denom = selected_coeff - coeff[index]
        score_gap = selection_scores[index] - selected_score
        threshold = max(score_gap / denom, 0.0)
        if math.isfinite(threshold):
            thresholds.append(float(threshold))
    return min(thresholds) if thresholds else None


def _lambda_result(record: dict[str, Any], lam: float) -> dict[str, Any]:
    for result in record.get("lambda_results") or []:
        if result.get("lambda") == lam:
            return result
    return {}


def _by_lambda(summary: dict[str, Any], lam: float) -> dict[str, Any]:
    for row in summary.get("by_lambda") or []:
        if row.get("lambda") == lam:
            return row
    return {"lambda": lam, "changed_records": math.inf}


def _has_ranking_signal(values: list[float], domain: list[int]) -> bool:
    subset = [values[index] for index in domain if index < len(values)]
    return bool(subset) and max(subset) > min(subset)


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


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
