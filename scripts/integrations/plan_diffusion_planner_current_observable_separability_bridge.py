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

from scripts.integrations.analyze_diffusion_planner_affine_allowed_harmful_residual import (
    READY_STATUS as AFFINE_RESIDUAL_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_constrained_affine_upper_bound import (
    REJECT_STATUS as AFFINE_REJECT_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (
    FEATURE_SPECS,
    REJECT_STATUS as OBSERVABLE_REJECT_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_observable_state_payload_coverage import (
    READY_STATUS as COVERAGE_READY_STATUS,
)


DUPLICATE_REJECT_STATUS = "current_observable_separability_bridge_duplicate_rejected"
MATERIALLY_NEW_READY_STATUS = (
    "current_observable_separability_bridge_materially_new_route_ready"
)
EVIDENCE_MISSING_STATUS = "current_observable_separability_bridge_evidence_missing"
SOURCE_NOT_READY_STATUS = "current_observable_separability_bridge_source_not_ready"

MATCHED_CONTRACT_READY_STATUS = "matched_observable_outcome_contract_passed"
MATCHED_CONTRACT_NEXT_WORK = "offline_observable_descriptor_separability_screen_only"
OBSERVABLE_FAILURE_GAP = (
    "observable_descriptors_do_not_separate_beneficial_and_harmful_candidates"
)
AFFINE_FAILURE_GAP = "allowed_harmful_rate_too_high"

NEXT_AFTER_DUPLICATE_REJECT = "proof_objective_or_new_descriptor_family_design_only"
NEXT_AFTER_NEW_ROUTE = "predeclare_offline_no_leak_observable_descriptor_separability_screen_only"
NEXT_AFTER_MISSING = "locate_or_generate_matched_observable_route_evidence_before_rerun"
NEXT_AFTER_SOURCE_NOT_READY = "repair_current_observable_payload_coverage_before_bridge"

BLOCKED_ACTIONS = (
    "closed_loop_replay_authorized",
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
            "Read-only bridge gate that checks whether the current observable "
            "payload coverage route is materially new or is already closed by "
            "older matched observable separability evidence."
        )
    )
    parser.add_argument("--current_payload_coverage_json", type=Path, required=True)
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--observable_separability_json", type=Path, required=True)
    parser.add_argument("--constrained_affine_json", type=Path, required=True)
    parser.add_argument("--affine_residual_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        current_payload_coverage=_load_json(args.current_payload_coverage_json),
        matched_contract=_load_json(args.matched_contract_json),
        observable_separability=_load_json(args.observable_separability_json),
        constrained_affine=_load_json(args.constrained_affine_json),
        affine_residual=(
            _load_json(args.affine_residual_json)
            if args.affine_residual_json is not None
            else None
        ),
        label=args.label,
        paths={
            "current_payload_coverage_json": str(args.current_payload_coverage_json),
            "matched_contract_json": str(args.matched_contract_json),
            "observable_separability_json": str(args.observable_separability_json),
            "constrained_affine_json": str(args.constrained_affine_json),
            "affine_residual_json": (
                str(args.affine_residual_json)
                if args.affine_residual_json is not None
                else None
            ),
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


def build_report(
    *,
    current_payload_coverage: dict[str, Any],
    matched_contract: dict[str, Any],
    observable_separability: dict[str, Any],
    constrained_affine: dict[str, Any],
    affine_residual: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    source_checks = [
        *_current_coverage_checks(current_payload_coverage),
        *_old_evidence_checks(
            matched_contract=matched_contract,
            observable_separability=observable_separability,
            constrained_affine=constrained_affine,
            affine_residual=affine_residual,
        ),
    ]
    current_ready = all(
        check["passed"]
        for check in source_checks
        if str(check["group"]) == "current_payload_coverage"
    )
    old_evidence_ready = all(
        check["passed"]
        for check in source_checks
        if str(check["group"]) != "current_payload_coverage"
    )
    equivalence = _equivalence_report(
        current_payload_coverage=current_payload_coverage,
        observable_separability=observable_separability,
        matched_contract=matched_contract,
    )
    decision = _decision(
        current_ready=current_ready,
        old_evidence_ready=old_evidence_ready,
        materially_new=bool(equivalence["materially_new_route"]),
    )
    return {
        "analysis": {
            "name": "dp_camp_current_observable_separability_bridge_v1",
            "label": label,
            "role": (
                "closure gate for deciding whether current observable-state "
                "coverage authorizes a new separability route or duplicates an "
                "already rejected matched observable descriptor family"
            ),
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "future_outcome_labels_used_for_online_features": False,
            "future_outcome_labels_used_for_bridge_evidence": True,
            "paths": paths or {},
            "math_boundary": (
                "This bridge consumes existing JSON artifacts only. Current "
                "payload descriptors are finite current-tick candidate data. "
                "Older outcome labels are used only to close or justify an "
                "offline separability route, never as online features. If a "
                "future atom is designed from these descriptors, it must enter "
                "as a fixed coefficient a_k so score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 robust master remains convex. "
                "No DP-side classical Benders master/subproblem, dual, or cut "
                "is constructed."
            ),
        },
        "source_checks": source_checks,
        "equivalence": equivalence,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _current_coverage_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(report.get("final_decision"))
    counts = _dict(report.get("counts"))
    context = _dict(report.get("context"))
    material_fields = _string_list(report.get("material_candidate_fields"))
    return [
        _check(
            "current_coverage_ready_status",
            "current_payload_coverage",
            decision.get("status"),
            COVERAGE_READY_STATUS,
        ),
        _check(
            "current_coverage_validation_passed",
            "current_payload_coverage",
            decision.get("validation_passed"),
            True,
        ),
        _check(
            "current_coverage_materiality_gate_passed",
            "current_payload_coverage",
            decision.get("materiality_gate_passed"),
            True,
        ),
        _check_min(
            "current_coverage_records",
            "current_payload_coverage",
            counts.get("records", decision.get("records_total")),
            12,
        ),
        _check_min(
            "current_coverage_candidate_rows",
            "current_payload_coverage",
            counts.get("candidate_rows"),
            1,
        ),
        _check_min(
            "current_coverage_red_context_records",
            "current_payload_coverage",
            context.get("red_context_records"),
            1,
        ),
        _check_min(
            "current_coverage_material_candidate_fields",
            "current_payload_coverage",
            len(material_fields),
            4,
        ),
        _check(
            "current_coverage_authorized_next",
            "current_payload_coverage",
            decision.get("authorized_next_work"),
            "offline_no_leak_observable_descriptor_separability_design_only",
        ),
    ]


def _old_evidence_checks(
    *,
    matched_contract: dict[str, Any],
    observable_separability: dict[str, Any],
    constrained_affine: dict[str, Any],
    affine_residual: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    contract_decision = _dict(matched_contract.get("final_decision"))
    observable_decision = _dict(observable_separability.get("final_decision"))
    observable_failure = _dict(observable_separability.get("failure_gap"))
    affine_decision = _dict(constrained_affine.get("final_decision"))
    affine_failure = _dict(constrained_affine.get("failure_gap"))
    observable_records = _dict(observable_separability.get("records"))
    checks = [
        _check(
            "matched_contract_passed",
            "old_matched_evidence",
            contract_decision.get("status"),
            MATCHED_CONTRACT_READY_STATUS,
        ),
        _check(
            "matched_contract_authorized_separability",
            "old_matched_evidence",
            contract_decision.get("authorized_next_work"),
            MATCHED_CONTRACT_NEXT_WORK,
        ),
        _check(
            "observable_separability_rejected",
            "old_observable_separability",
            observable_decision.get("status"),
            OBSERVABLE_REJECT_STATUS,
        ),
        _check(
            "observable_separability_not_passed",
            "old_observable_separability",
            bool(observable_decision.get("passed")),
            False,
        ),
        _check(
            "observable_separability_primary_gap",
            "old_observable_separability",
            observable_decision.get("primary_gap") or observable_failure.get("primary_gap"),
            OBSERVABLE_FAILURE_GAP,
        ),
        _check(
            "observable_separability_no_promising_screen",
            "old_observable_separability",
            int(observable_decision.get("promising_screen_count", 0)),
            0,
        ),
        _check(
            "observable_separability_no_formal_seeds",
            "old_observable_separability",
            int(observable_records.get("formal_seed_records", 0)),
            0,
        ),
        _check(
            "constrained_affine_rejected",
            "old_constrained_affine",
            affine_decision.get("status"),
            AFFINE_REJECT_STATUS,
        ),
        _check(
            "constrained_affine_not_passed",
            "old_constrained_affine",
            bool(affine_decision.get("passed")),
            False,
        ),
        _check(
            "constrained_affine_failure_gap",
            "old_constrained_affine",
            affine_failure.get("primary_gap"),
            AFFINE_FAILURE_GAP,
        ),
    ]
    if affine_residual is not None:
        residual_decision = _dict(affine_residual.get("final_decision"))
        residual_records = _dict(affine_residual.get("records"))
        checks.extend(
            [
                _check(
                    "affine_residual_diagnosed",
                    "old_affine_residual",
                    residual_decision.get("status"),
                    AFFINE_RESIDUAL_READY_STATUS,
                ),
                _check(
                    "affine_residual_no_formal_seeds",
                    "old_affine_residual",
                    int(residual_records.get("formal_seed_records", 0)),
                    0,
                ),
            ]
        )
    return checks


def _equivalence_report(
    *,
    current_payload_coverage: dict[str, Any],
    observable_separability: dict[str, Any],
    matched_contract: dict[str, Any],
) -> dict[str, Any]:
    current_counts = _dict(current_payload_coverage.get("counts"))
    current_decision = _dict(current_payload_coverage.get("final_decision"))
    current_fields = set(_string_list(current_payload_coverage.get("material_candidate_fields")))
    old_fields = _old_observable_source_fields(observable_separability)
    old_records = _dict(observable_separability.get("records"))
    contract_counts = _dict(matched_contract.get("counts"))

    current_record_count = _int_or_none(
        current_counts.get("records", current_decision.get("records_total"))
    )
    current_candidate_rows = _int_or_none(current_counts.get("candidate_rows"))
    old_record_count = _int_or_none(old_records.get("total_records"))
    old_candidate_rows = _int_or_none(old_records.get("candidate_rows"))
    contract_record_count = _int_or_none(
        contract_counts.get("records", contract_counts.get("matched_records"))
    )
    contract_candidate_rows = _int_or_none(
        contract_counts.get("candidate_rows", contract_counts.get("matched_candidate_rows"))
    )

    uncovered_fields = sorted(current_fields - old_fields)
    same_record_count = (
        current_record_count is not None
        and old_record_count is not None
        and current_record_count == old_record_count
    )
    same_candidate_rows = (
        current_candidate_rows is not None
        and old_candidate_rows is not None
        and current_candidate_rows == old_candidate_rows
    )
    matched_contract_same_scope = (
        contract_record_count is None
        or current_record_count is None
        or contract_record_count == current_record_count
    ) and (
        contract_candidate_rows is None
        or current_candidate_rows is None
        or contract_candidate_rows == current_candidate_rows
    )
    materially_new = bool(
        uncovered_fields
        or (
            current_record_count is not None
            and old_record_count is not None
            and current_record_count > old_record_count
        )
        or (
            current_candidate_rows is not None
            and old_candidate_rows is not None
            and current_candidate_rows > old_candidate_rows
        )
    )
    return {
        "current_records": current_record_count,
        "current_candidate_rows": current_candidate_rows,
        "old_observable_records": old_record_count,
        "old_observable_candidate_rows": old_candidate_rows,
        "matched_contract_records": contract_record_count,
        "matched_contract_candidate_rows": contract_candidate_rows,
        "same_record_count_as_old_observable": same_record_count,
        "same_candidate_rows_as_old_observable": same_candidate_rows,
        "matched_contract_same_scope_if_reported": matched_contract_same_scope,
        "current_material_fields": sorted(current_fields),
        "old_observable_source_fields": sorted(old_fields),
        "current_material_fields_covered_by_old_observable_family": not uncovered_fields,
        "uncovered_current_material_fields": uncovered_fields,
        "materially_new_route": materially_new,
        "duplicate_route_evidence": (
            not materially_new
            and same_record_count
            and same_candidate_rows
            and matched_contract_same_scope
        ),
    }


def _decision(
    *,
    current_ready: bool,
    old_evidence_ready: bool,
    materially_new: bool,
) -> dict[str, Any]:
    if not current_ready:
        status = SOURCE_NOT_READY_STATUS
        primary_gap = "current_payload_coverage_not_ready"
        authorized_next_work = NEXT_AFTER_SOURCE_NOT_READY
        closure_gate_passed = False
    elif not old_evidence_ready:
        status = EVIDENCE_MISSING_STATUS
        primary_gap = "old_matched_observable_evidence_incomplete"
        authorized_next_work = NEXT_AFTER_MISSING
        closure_gate_passed = False
    elif materially_new:
        status = MATERIALLY_NEW_READY_STATUS
        primary_gap = "current_observable_route_materially_new"
        authorized_next_work = NEXT_AFTER_NEW_ROUTE
        closure_gate_passed = True
    else:
        status = DUPLICATE_REJECT_STATUS
        primary_gap = "current_observable_route_duplicates_rejected_old_family"
        authorized_next_work = NEXT_AFTER_DUPLICATE_REJECT
        closure_gate_passed = True
    return {
        "status": status,
        "closure_gate_passed": closure_gate_passed,
        "passed": closure_gate_passed,
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        "selection_effect": False,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    equivalence = report["equivalence"]
    lines = [
        "# Current Observable Separability Bridge",
        "",
        f"- Status: `{decision['status']}`",
        f"- Closure gate passed: `{decision['closure_gate_passed']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Equivalence",
        "",
        f"- Current records: `{equivalence['current_records']}`",
        f"- Current candidate rows: `{equivalence['current_candidate_rows']}`",
        f"- Old observable records: `{equivalence['old_observable_records']}`",
        f"- Old observable candidate rows: `{equivalence['old_observable_candidate_rows']}`",
        f"- Materially new route: `{equivalence['materially_new_route']}`",
        f"- Duplicate route evidence: `{equivalence['duplicate_route_evidence']}`",
        f"- Uncovered current material fields: `{equivalence['uncovered_current_material_fields']}`",
        "",
        "## Source Checks",
        "",
        "| Group | Check | Passed | Actual | Expected |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['group']}` | `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('actual')}` | `{check.get('expected')}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run DP, train CAMP, promote an online selector, "
            "authorize Full36, or touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _old_observable_source_fields(report: dict[str, Any]) -> set[str]:
    specs = _dict(report.get("analysis")).get("feature_specs")
    fields = {
        str(spec.get("source_field"))
        for spec in specs
        if isinstance(spec, dict) and spec.get("source_field")
    } if isinstance(specs, list) else set()
    if fields:
        return fields
    return {spec.source_field for spec in FEATURE_SPECS}


def _check(name: str, group: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "group": group,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_min(name: str, group: str, actual: Any, minimum: int) -> dict[str, Any]:
    value = _int_or_none(actual)
    return {
        "name": name,
        "group": group,
        "passed": value is not None and value >= int(minimum),
        "actual": value,
        "expected": f">={int(minimum)}",
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
