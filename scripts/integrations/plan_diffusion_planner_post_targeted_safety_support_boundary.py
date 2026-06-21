#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TARGETED_SAFETY_STATUS = "alternative_safety_source_materiality_ready"
TARGETED_SAFETY_NEXT_WORK = "targeted_safety_support_scenario_or_source_design_only"
TEMPORAL_SAFETY_STATUS = "temporal_consistency_shadow_safety_proxy_ready"
TEMPORAL_SAFETY_NEXT_WORK = (
    "reject_temporal_consistency_as_safety_source_or_predeclare_alternative_no_leak_atom_only"
)
LEDGER_STATUS = "post_pause_source_family_ledger_ready"
STRICT_SOURCE_CLOSURE_STATUS = "targeted_source_discovery_route_closed"

READY_STATUS = "post_targeted_safety_support_boundary_ready"
BLOCKED_STATUS = "post_targeted_safety_support_boundary_blocked"
AUTHORIZED_NEXT_WORK = (
    "new_current_tick_source_visibility_predeclaration_or_keep_selector_route_paused_only"
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)

CLOSED_SOURCE_LABELS = (
    "red_clearance_gap_to_best_current_tick",
    "temporal_consistency",
    "external_context",
    "route_speed",
    "signal_right_of_way",
    "turn_logit",
    "dp_prior_deviation",
    "top1_retention",
    "progress_lane_hard",
    "observable_interaction",
    "route_topology",
    "mode_seeking",
    "source_donor",
    "raw_prefix",
    "postprocess_tracker_descriptor_family",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only boundary gate after targeted safety support discovery. "
            "It consumes existing artifacts only and decides whether the current "
            "fixed-DP CAMP selector route must remain paused until a genuinely "
            "new current-tick source is predeclared."
        )
    )
    parser.add_argument("--targeted_safety_materiality_json", type=Path, required=True)
    parser.add_argument("--temporal_safety_proxy_json", type=Path, required=True)
    parser.add_argument("--source_family_ledger_json", type=Path, required=True)
    parser.add_argument("--strict_source_closure_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        targeted_safety_materiality=_load_json(args.targeted_safety_materiality_json),
        temporal_safety_proxy=_load_json(args.temporal_safety_proxy_json),
        source_family_ledger=_load_json(args.source_family_ledger_json),
        strict_source_closure=(
            None
            if args.strict_source_closure_json is None
            else _load_json(args.strict_source_closure_json)
        ),
        label=args.label,
        paths={
            "targeted_safety_materiality_json": str(
                args.targeted_safety_materiality_json
            ),
            "temporal_safety_proxy_json": str(args.temporal_safety_proxy_json),
            "source_family_ledger_json": str(args.source_family_ledger_json),
            "strict_source_closure_json": (
                None
                if args.strict_source_closure_json is None
                else str(args.strict_source_closure_json)
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    targeted_safety_materiality: dict[str, Any],
    temporal_safety_proxy: dict[str, Any],
    source_family_ledger: dict[str, Any],
    strict_source_closure: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    targeted = _targeted_safety_summary(targeted_safety_materiality)
    temporal = _temporal_safety_summary(temporal_safety_proxy)
    ledger = _ledger_summary(source_family_ledger)
    strict = (
        None
        if strict_source_closure is None
        else _strict_source_closure_summary(strict_source_closure)
    )
    checks = [
        *_targeted_safety_checks(targeted),
        *_temporal_safety_checks(temporal),
        *_ledger_checks(ledger),
        *([] if strict is None else _strict_source_checks(strict)),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_post_targeted_safety_support_boundary_v1",
            "label": label,
            "role": (
                "read-only boundary after temporal, external-context, and "
                "targeted safety-support routes failed to produce deployable "
                "no-leak selector evidence"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "selection_effect": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate creates no atom, runs no selector, trains no weights, "
                "and reads no future outcome label as a runtime feature. Any "
                "future CAMP-on-DP source must be a current-tick fixed finite "
                "candidate coefficient a_k, nonnegative, hinged, or signed-split, "
                "so score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. No DP-side classical Benders "
                "decomposition is claimed because no DP master/subproblem, "
                "dual, or valid cut is constructed."
            ),
        },
        "targeted_safety_summary": targeted,
        "temporal_safety_summary": temporal,
        "source_family_ledger_summary": ledger,
        "strict_source_closure_summary": strict,
        "boundary_checks": checks,
        "closed_source_labels": _closed_source_labels(ledger),
        "next_source_visibility_contract": _next_source_visibility_contract(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def _targeted_safety_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    materiality = _dict(report.get("materiality_summary"))
    by_source = [
        row for row in materiality.get("by_source") or [] if isinstance(row, dict)
    ]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "has_material_safety_source": bool(final.get("has_material_safety_source")),
        "has_actionable_existing_safety_source": bool(
            final.get("has_actionable_existing_safety_source")
        ),
        "actionable_existing_safety_sources": _string_list(
            final.get("actionable_existing_safety_sources")
        ),
        "material_but_current_selection_already_best": _string_list(
            final.get("material_but_current_selection_already_best")
        ),
        "records": _int_or_none(materiality.get("records")),
        "available_records": _int_or_none(materiality.get("available_records")),
        "valid_available_records": _int_or_none(
            materiality.get("valid_available_records")
        ),
        "by_source": by_source,
        "blocked_action_conflicts": _blocked_action_conflicts(final),
    }


def _temporal_safety_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "safety_proxy_evidence": bool(final.get("safety_proxy_evidence")),
        "safety_benefit_evidence": bool(final.get("safety_benefit_evidence")),
        "max_changed_records": _int_or_none(final.get("max_changed_records")),
        "blocked_action_conflicts": _blocked_action_conflicts(final),
    }


def _ledger_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    ledger = _dict(report.get("source_family_ledger"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "support_source_ready": bool(final.get("support_source_ready")),
        "current_selector_route_rejected": bool(
            final.get("current_camp_dp_selector_route_rejected")
        ),
        "closed_source_family_labels": _string_list(
            ledger.get("closed_source_family_labels")
        ),
        "closed_source_family_labels_count": _int_or_none(
            final.get("closed_source_family_labels_count")
        ),
        "blocked_action_conflicts": _blocked_action_conflicts(final),
    }


def _strict_source_closure_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "source_discovery_closed": bool(final.get("source_discovery_closed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "blocked_action_conflicts": _blocked_action_conflicts(final),
    }


def _targeted_safety_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("targeted_safety_status", summary["status"], TARGETED_SAFETY_STATUS),
        _check_equal("targeted_safety_passed", summary["passed"], True),
        _check_equal(
            "targeted_safety_authorizes_only_support_design",
            summary["authorized_next_work"],
            TARGETED_SAFETY_NEXT_WORK,
        ),
        _check_equal(
            "targeted_safety_no_actionable_existing_source",
            summary["has_actionable_existing_safety_source"],
            False,
        ),
        _check_empty(
            "targeted_safety_actionable_sources_empty",
            summary["actionable_existing_safety_sources"],
        ),
        _check_equal(
            "targeted_safety_has_material_source",
            summary["has_material_safety_source"],
            True,
        ),
        _check_nonempty(
            "targeted_safety_material_already_best_nonempty",
            summary["material_but_current_selection_already_best"],
        ),
        _check_empty(
            "targeted_safety_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _temporal_safety_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("temporal_safety_status", summary["status"], TEMPORAL_SAFETY_STATUS),
        _check_equal("temporal_safety_passed", summary["passed"], True),
        _check_equal(
            "temporal_safety_authorizes_only_reject_or_alternative_source",
            summary["authorized_next_work"],
            TEMPORAL_SAFETY_NEXT_WORK,
        ),
        _check_equal("temporal_safety_proxy_evidence_false", summary["safety_proxy_evidence"], False),
        _check_equal("temporal_safety_benefit_evidence_false", summary["safety_benefit_evidence"], False),
        _check_empty(
            "temporal_safety_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _ledger_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_ledger_status", summary["status"], LEDGER_STATUS),
        _check_equal("source_ledger_passed", summary["passed"], True),
        _check_equal("source_ledger_support_source_ready_false", summary["support_source_ready"], False),
        _check_equal(
            "source_ledger_current_route_rejected",
            summary["current_selector_route_rejected"],
            True,
        ),
        _check_empty(
            "source_ledger_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _strict_source_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "strict_source_closure_status",
            summary["status"],
            STRICT_SOURCE_CLOSURE_STATUS,
        ),
        _check_equal("strict_source_closure_passed", summary["passed"], True),
        _check_equal(
            "strict_source_discovery_closed",
            summary["source_discovery_closed"],
            True,
        ),
        _check_empty(
            "strict_source_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _closed_source_labels(ledger: dict[str, Any]) -> list[str]:
    labels = set(CLOSED_SOURCE_LABELS)
    labels.update(ledger.get("closed_source_family_labels") or [])
    return sorted(labels)


def _next_source_visibility_contract() -> dict[str, Any]:
    return {
        "allowed_next_work": AUTHORIZED_NEXT_WORK,
        "runtime_source_required_properties": [
            "current_tick_available_before_selection",
            "candidate_level_or_deterministically_joinable_to_candidates",
            "finite_or_fail_closed_for_every_candidate",
            "deterministic",
            "not_future_outcome_or_safetycost_label",
            "not_equivalent_to_closed_source_labels",
            "does_not_require_dp_modification_or_retraining",
            "does_not_require_replay_or_training_to_compute_runtime_value",
            "default_off_latency_accounted",
            "atomizable_as_nonnegative_hinge_or_signed_split_coefficient",
            "affine_score_preserved",
        ],
        "pre_replay_evidence_required": [
            "source_visibility_predeclaration",
            "non_equivalence_argument_against_closed_labels",
            "existing_log_materiality_or_explicit_reason_existing_logs_cannot_contain_source",
            "existing_log_noninferiority_if_source_changes_selection",
        ],
        "explicitly_forbidden_shortcuts": [
            "repeat_red_or_clearance_only_materiality",
            "repeat_temporal_consistency_shadow_weight_search",
            "reopen_external_context_signal_or_route_speed_without_new_non_equivalence",
            "use_DP_top1_rank_or_future_outcome_as_runtime_feature",
            "train_CAMP_weights_before_source_gate",
            "promote_online_selector_before_nonformal_paired_evidence",
            "run_Full36_or_formal_seeds",
            "modify_or_retrain_DP",
            "call_finite_candidate_selector_classical_Benders",
        ],
    }


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "selector_route_paused": passed,
        "support_source_ready": False,
        "current_camp_dp_selector_route_rejected": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": failed,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post Targeted Safety Support Boundary",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        f"- Support source ready: `{decision['support_source_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Evidence Summary",
        "",
        _summary_line("Targeted safety", report["targeted_safety_summary"]),
        _summary_line("Temporal safety", report["temporal_safety_summary"]),
        _summary_line("Source ledger", report["source_family_ledger_summary"]),
    ]
    if report["strict_source_closure_summary"] is not None:
        lines.append(
            _summary_line("Strict source closure", report["strict_source_closure_summary"])
        )
    lines.extend(
        [
            "",
            "## Closed Source Labels",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in report["closed_source_labels"])
    lines.extend(
        [
            "",
            "## Next Source Visibility Contract",
            "",
            "Required runtime source properties:",
        ]
    )
    contract = report["next_source_visibility_contract"]
    lines.extend(f"- `{item}`" for item in contract["runtime_source_required_properties"])
    lines.extend(["", "Forbidden shortcuts:"])
    lines.extend(f"- `{item}`" for item in contract["explicitly_forbidden_shortcuts"])
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


def _summary_line(label: str, summary: dict[str, Any]) -> str:
    return (
        f"- {label}: status=`{summary.get('status')}`, "
        f"passed=`{summary.get('passed')}`, "
        f"next=`{summary.get('authorized_next_work')}`"
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON at {path}")
    return payload


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _blocked_action_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_empty(name: str, values: list[Any]) -> dict[str, Any]:
    return {"name": name, "passed": len(values) == 0, "actual": values, "expected": []}


def _check_nonempty(name: str, values: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(values) > 0,
        "actual": values,
        "expected": "nonempty",
    }


if __name__ == "__main__":
    main()
