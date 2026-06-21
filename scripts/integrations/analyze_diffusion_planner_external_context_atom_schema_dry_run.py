#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Callable


PREFLIGHT_READY_STATUS = "external_context_atomization_preflight_ready"
PREFLIGHT_NEXT_WORK = "external_context_atom_schema_dry_run_existing_smoke_only"
READY_STATUS = "external_context_atom_schema_dry_run_ready"
REJECT_STATUS = "external_context_atom_schema_dry_run_rejected"
AUTHORIZED_NEXT_WORK = "external_context_real_smoke_refresh_when_autodl_available"
LOG_NAME = "camp_selection_log.json"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Existing-smoke-only dry run for external-context atom schema effects. "
            "Reads logged payloads only; does not deploy atoms, run DP, or train CAMP."
        )
    )
    parser.add_argument("--atomization_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_records", type=int, default=3)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        atomization=_load_json(args.atomization_json),
        candidate_root=args.candidate_root,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        label=args.label,
        paths={
            "atomization_json": str(args.atomization_json),
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
    atomization: dict[str, Any],
    candidate_root: Path,
    expected_records: int = 3,
    expected_candidates: int = 8,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")

    records = _load_selection_records(candidate_root)
    source = _source_gate(atomization)
    source_checks = _source_checks(source)
    selected_specs = [
        row for row in atomization.get("selected_atom_candidates") or []
        if isinstance(row, dict)
    ]
    selected_atom_names = [str(row.get("name")) for row in selected_specs]
    record_checks = _record_checks(
        records,
        expected_records=expected_records,
        expected_candidates=expected_candidates,
    )
    dry_run_records = [
        _dry_run_record(index, record, selected_specs)
        for index, record in enumerate(records)
    ]
    dry_run_checks = _dry_run_checks(dry_run_records, selected_specs)
    summary = _summary(dry_run_records, selected_atom_names)
    passed = (
        all(check["passed"] for check in source_checks)
        and all(check["passed"] for check in record_checks)
        and all(check["passed"] for check in dry_run_checks)
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_atom_schema_dry_run_v1",
            "label": label,
            "role": (
                "existing-smoke-only dry run of external-context atom coefficients "
                "and ranking effects"
            ),
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
                "This dry run reads fixed current-tick finite-candidate payload "
                "fields selected by the atomization preflight and computes only "
                "offline candidate coefficients and rankings. It does not deploy "
                "the atom schema, train CAMP, run DP, or change the online "
                "selector. Scores are finite-candidate affine costs "
                "score_k(w)=a_k^T w with fixed coefficients, so the simplex/CVaR/L2 "
                "master remains convex over weights. No trajectory-coordinate "
                "convexity or classical Benders cut is claimed."
            ),
        },
        "source_atomization_gate": source,
        "source_checks": source_checks,
        "record_checks": record_checks,
        "selected_atom_candidate_names": selected_atom_names,
        "dry_run_records": dry_run_records,
        "dry_run_summary": summary,
        "dry_run_checks": dry_run_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, summary),
    }


def _source_gate(atomization: dict[str, Any]) -> dict[str, Any]:
    decision = atomization.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_atom_candidate_names": list(
            decision.get("selected_atom_candidate_names") or []
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], PREFLIGHT_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_dry_run",
            source["authorized_next_work"],
            PREFLIGHT_NEXT_WORK,
        ),
        _check_equal(
            "source_selected_atoms_nonempty",
            bool(source["selected_atom_candidate_names"]),
            True,
        ),
        _check_equal(
            "source_blocked_action_conflicts_empty",
            source["blocked_action_conflicts"],
            [],
        ),
    ]


def _record_checks(
    records: list[dict[str, Any]],
    *,
    expected_records: int,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    checks = [_check_equal("record_count", len(records), expected_records)]
    payload_records = 0
    for index, record in enumerate(records):
        payload = record.get("external_context_payload_logging")
        present = isinstance(payload, dict)
        checks.append(_check_equal(f"record_{index}_payload_present", present, True))
        if not present:
            continue
        payload_records += 1
        checks.extend(
            [
                _check_equal(
                    f"record_{index}_candidate_count",
                    int(payload.get("candidate_count", -1)),
                    expected_candidates,
                ),
                _check_equal(
                    f"record_{index}_payload_valid",
                    (payload.get("finite_checks") or {}).get("payload_valid"),
                    True,
                ),
                _check_equal(
                    f"record_{index}_selection_effect",
                    payload.get("selection_effect"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_future_outcome_leakage",
                    payload.get("future_outcome_leakage"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcome_fields_read",
                    payload.get("closed_loop_outcome_fields_read"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcomes_absent",
                    record.get("candidate_closed_loop_outcomes"),
                    None,
                ),
            ]
        )
    checks.append(_check_equal("payload_record_count", payload_records, expected_records))
    return checks


def _dry_run_record(
    index: int,
    record: dict[str, Any],
    selected_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = record.get("external_context_payload_logging")
    if not isinstance(payload, dict):
        return {
            "record_index": index,
            "passed": False,
            "reason": "payload_missing",
        }
    selected_index = _optional_int(record.get("selected_index"))
    candidate_count = int(payload.get("candidate_count", 0))
    atom_scores: dict[str, list[float]] = {}
    atom_errors: dict[str, str] = {}
    for spec in selected_specs:
        name = str(spec.get("name"))
        try:
            atom_scores[name] = _atom_coefficients(spec, payload, candidate_count)
        except ValueError as exc:
            atom_errors[name] = str(exc)

    combined = _combined_scores(atom_scores, candidate_count)
    atom_best_index = _argmin_with_lowest_index_tie_break(combined)
    top1_preserved = (
        selected_index is not None
        and atom_best_index is not None
        and selected_index == atom_best_index
    )
    return {
        "record_index": index,
        "passed": not atom_errors and atom_best_index is not None,
        "selected_index": selected_index,
        "candidate_count": candidate_count,
        "atom_scores": atom_scores,
        "atom_errors": atom_errors,
        "combined_atom_score": combined,
        "atom_best_index": atom_best_index,
        "top1_preserved_by_atom_score": top1_preserved,
        "would_change_selected_index": (
            selected_index is not None
            and atom_best_index is not None
            and selected_index != atom_best_index
        ),
        "ranking_signal_present": _has_ranking_signal(combined),
        "deterministic_tie_break": "lowest_index_min_score",
        "future_outcome_labels_used": False,
    }


def _atom_coefficients(
    spec: dict[str, Any],
    payload: dict[str, Any],
    candidate_count: int,
) -> list[float]:
    name = str(spec.get("name"))
    source_field = str(spec.get("source_field"))
    raw_values = _field_values(payload, source_field, candidate_count)
    rules: dict[str, Callable[[float], float]] = {
        "route_speed_limit_excess_integral_v1": lambda value: value,
        "route_speed_limit_missing_context_v1": lambda value: max(1.0 - value, 0.0),
        "right_of_way_blocked_indicator_v1": lambda value: value,
        "signal_phase_margin_violation_hinge_v1": lambda value: max(-value, 0.0),
        "signal_arrival_time_reaches_control_v1": lambda value: (
            1.0 if math.isfinite(value) else 0.0
        ),
    }
    if name not in rules:
        raise ValueError(f"unsupported atom candidate {name!r}")
    coefficients = [float(rules[name](value)) for value in raw_values]
    if not all(math.isfinite(value) and value >= 0.0 for value in coefficients):
        raise ValueError(f"atom {name!r} produced non-finite or negative coefficients")
    return coefficients


def _field_values(
    payload: dict[str, Any],
    source_field: str,
    candidate_count: int,
) -> list[float]:
    values = payload.get(source_field)
    if not isinstance(values, list):
        raise ValueError(f"field {source_field!r} is missing or not a list")
    if len(values) != candidate_count:
        raise ValueError(
            f"field {source_field!r} has {len(values)} values, expected {candidate_count}"
        )
    parsed = [float(value) for value in values]
    if not all(math.isfinite(value) for value in parsed):
        raise ValueError(f"field {source_field!r} contains non-finite values")
    return parsed


def _combined_scores(
    atom_scores: dict[str, list[float]],
    candidate_count: int,
) -> list[float]:
    if not atom_scores:
        return []
    combined = [0.0 for _ in range(candidate_count)]
    for scores in atom_scores.values():
        for index, value in enumerate(scores):
            combined[index] += float(value)
    return combined


def _dry_run_checks(
    records: list[dict[str, Any]],
    selected_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _check_equal("selected_atom_specs_nonempty", bool(selected_specs), True),
        _check_equal(
            "all_records_have_valid_atom_scores",
            all(bool(record.get("passed")) for record in records),
            True,
        ),
        _check_equal(
            "all_record_scores_nonnegative_finite",
            all(_scores_nonnegative_finite(record) for record in records),
            True,
        ),
        _check_equal(
            "no_future_outcome_labels_used",
            all(record.get("future_outcome_labels_used") is False for record in records),
            True,
        ),
        _check_equal("online_selector_mutated", False, False),
        _check_equal("deployed_atom_schema_mutated", False, False),
    ]


def _scores_nonnegative_finite(record: dict[str, Any]) -> bool:
    for scores in (record.get("atom_scores") or {}).values():
        if not all(math.isfinite(float(value)) and float(value) >= 0.0 for value in scores):
            return False
    combined = record.get("combined_atom_score") or []
    return all(math.isfinite(float(value)) and float(value) >= 0.0 for value in combined)


def _summary(
    records: list[dict[str, Any]],
    selected_atom_names: list[str],
) -> dict[str, Any]:
    valid = [record for record in records if record.get("passed")]
    changed = [record for record in valid if record.get("would_change_selected_index")]
    preserved = [record for record in valid if record.get("top1_preserved_by_atom_score")]
    signal = [record for record in valid if record.get("ranking_signal_present")]
    total = len(valid)
    return {
        "records": len(records),
        "valid_records": total,
        "selected_atom_candidate_names": selected_atom_names,
        "ranking_signal_records": len(signal),
        "top1_preserved_records": len(preserved),
        "top1_preservation_rate": (len(preserved) / total if total else None),
        "would_change_selected_index_records": len(changed),
        "would_change_selected_index_rate": (len(changed) / total if total else None),
        "changed_record_indices": [record["record_index"] for record in changed],
    }


def _final_decision(passed: bool, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closed_loop_replay_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "selected_atom_candidate_names": summary["selected_atom_candidate_names"],
        "top1_preservation_rate": summary["top1_preservation_rate"],
        "ranking_signal_records": summary["ranking_signal_records"],
        "next_step": (
            "Refresh the evidence on real AutoDL external-context smoke when SSH is "
            "available; do not train, deploy, or enter Full36 from this synthetic dry run."
            if passed
            else "Reject atom-schema dry-run promotion and inspect the failing source, record, or score checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["dry_run_summary"]
    lines = [
        "# External Context Atom Schema Dry Run",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        f"- Selected atom candidates: `{decision['selected_atom_candidate_names']}`",
        f"- Ranking signal records: `{summary['ranking_signal_records']}`",
        f"- Top-1 preservation rate: `{summary['top1_preservation_rate']}`",
        "",
        "## Source Gate",
        "",
    ]
    for key, value in report["source_atomization_gate"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Record Effects", ""])
    for record in report["dry_run_records"]:
        lines.append(
            f"- record `{record['record_index']}`: selected=`{record.get('selected_index')}`, "
            f"atom_best=`{record.get('atom_best_index')}`, "
            f"changed=`{record.get('would_change_selected_index')}`"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_selection_records(candidate_root: Path) -> list[dict[str, Any]]:
    log_paths = sorted(candidate_root.rglob(LOG_NAME))
    if not log_paths:
        return []
    records: list[dict[str, Any]] = []
    for path in log_paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        records.extend(row for row in payload if isinstance(row, dict))
    return records


def _has_ranking_signal(scores: list[float]) -> bool:
    return bool(scores) and max(scores) > min(scores)


def _argmin_with_lowest_index_tie_break(values: list[float]) -> int | None:
    if not values:
        return None
    best_index = 0
    best_value = float(values[0])
    for index, value in enumerate(values[1:], start=1):
        value = float(value)
        if value < best_value:
            best_index = index
            best_value = value
    return best_index


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
