#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


READY_STATUS = "dp_native_candidate_reranking_design_plan_ready"
REJECT_STATUS = "dp_native_candidate_reranking_design_plan_rejected"
AUTHORIZED_NEXT_WORK = "dp_native_candidate_reranking_fixed_artifact_evidence_audit_only"

DEFAULT_FAILURE_ATTRIBUTION_JSON = (
    ROOT
    / "analysis_bundles"
    / "v4_fixed_screen_failure_attribution_3584269"
    / "guarded_material_v4_fixed_snapshot_screen_failure_attribution.json"
)
DEFAULT_AUDIT_MD = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MATERIALIZED_REJECTION_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_"
    "comfort_failure_diagnostic_remediation_followup_materially_different_generator_"
    "guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_"
    "fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_snapshot_"
    "screen_rerun_failure_attribution_remediation_design_plan_only"
)

PROHIBITED_EVIDENCE_FAMILIES = (
    "new_candidate_generation",
    "trajectory_rewrite",
    "trajectory_materialization",
    "splice_transform",
    "lane_projection_mutation",
    "red_light_rewrite",
    "candidate_tensor_append",
    "candidate_tensor_coordinate_mutation",
)

BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "trajectory_rewrite_authorized",
    "candidate_tensor_mutation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "offline_selector_screen_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "atom_promotion_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)

AUDIT_EVIDENCE_PATTERNS = {
    "materialized_generator_rejected": (
        "Reject this guarded material v4 route/topology candidate construction family"
    ),
    "dp_fixed_tail": f"DP remained fixed at `{EXPECTED_DP_HEAD}`",
    "selector_equivalence_exact": (
        "selector_equivalence.exact_field_mismatches=0 for selected_index"
    ),
    "selector_equivalence_numeric": (
        "selector_equivalence.numeric_field_mismatches=0 for scores"
    ),
    "candidate_tensor_available": "The fixed candidate tensor exists before",
    "candidate_tensor_dp_native_boundary": (
        "already generated DP candidate tensor before selection"
    ),
    "fixed_dp_candidate_pool_opportunity": (
        "fixed DP candidate pool contains hard-guarded lower-SafetyCost alternatives"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate that redirects post-materialized-generator CAMP/DP "
            "work back to DP-native candidate reranking."
        )
    )
    parser.add_argument(
        "--failure_attribution_json",
        type=Path,
        default=DEFAULT_FAILURE_ATTRIBUTION_JSON,
    )
    parser.add_argument("--audit_md", type=Path, default=DEFAULT_AUDIT_MD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        failure_attribution=_load_json(args.failure_attribution_json),
        audit_text=args.audit_md.read_text(encoding="utf-8"),
        failure_attribution_json=str(args.failure_attribution_json),
        audit_md=str(args.audit_md),
        label=args.label,
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
    failure_attribution: dict[str, Any],
    audit_text: str,
    failure_attribution_json: str = str(DEFAULT_FAILURE_ATTRIBUTION_JSON),
    audit_md: str = str(DEFAULT_AUDIT_MD),
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_summary(failure_attribution)
    evidence = _audit_evidence_summary(audit_text)
    plan = _design_plan(
        failure_attribution_json=failure_attribution_json,
        audit_md=audit_md,
        source=source,
        evidence=evidence,
    )
    checks = [
        *_source_checks(source),
        *_evidence_checks(evidence),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_native_candidate_reranking_design_plan_v1",
            "label": label,
            "role": (
                "plan-only correction that excludes CAMP-side trajectory "
                "generation as positive evidence and restores DP-native "
                "candidate reranking as the main integration path"
            ),
            "plan_only": True,
            "read_only": True,
            "candidate_generation_execution": False,
            "trajectory_rewrite": False,
            "candidate_tensor_mutation": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This design gate reads only the completed materialized-generator "
                "failure attribution and audit evidence. It does not create or "
                "rewrite trajectories, append candidates, rerun screens, run DP, "
                "run replay, use formal seeds, train CAMP, define or promote "
                "atoms, choose lambda online, change online selection, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "modify DP weights/code/config, claim safety benefit, or claim "
                "CAMP over DP Top-1."
            ),
        },
        "source_summary": source,
        "existing_evidence_anchors": evidence,
        "design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    evidence = report["existing_evidence_anchors"]
    plan = report["design_plan"]
    lines = [
        "# DP-Native Candidate Reranking Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Candidate generation authorized: `{decision['candidate_generation_execution_authorized']}`",
        f"- Trajectory rewrite authorized: `{decision['trajectory_rewrite_authorized']}`",
        f"- Candidate tensor mutation authorized: `{decision['candidate_tensor_mutation_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP over DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Rejection",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source passed: `{source['passed']}`",
        f"- Generated rows: `{source['generated_candidate_rows']}`",
        f"- Materialized rows: `{source['materialized_rows']}`",
        f"- Hard-feasible rows: `{source['hard_feasible_rows']}`",
        f"- Comfort-admissible rows: `{source['comfort_admissible_rows']}`",
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        "",
        "## Existing DP-Native Evidence Anchors",
        "",
    ]
    for name, anchor in evidence["anchors"].items():
        lines.append(
            f"- `{name}`: present=`{anchor['present']}`, line=`{anchor['line']}`"
        )
    lines.extend(
        [
            "",
            "## DP-Native Reranking Scope",
            "",
            f"- Route: `{plan['route']}`",
            f"- Source failure attribution JSON: `{plan['failure_attribution_json']}`",
            f"- Audit markdown: `{plan['audit_md']}`",
            "",
            "## Success Criteria",
            "",
        ]
    )
    for item in plan["success_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Failure Criteria", ""])
    for item in plan["failure_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Prohibited Evidence Families", ""])
    for item in plan["prohibited_evidence_families"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            f"`{AUTHORIZED_NEXT_WORK}`",
            "",
            "The next gate may only audit fixed DP-native candidate artifacts. It may not "
            "generate candidates, rewrite trajectories, run replay, use formal seeds, "
            "train CAMP, promote atoms, change online selection, modify DP, or make "
            "safety/CAMP-over-DP claims.",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    source = _dict(report.get("source_summary"))
    attribution = _dict(report.get("read_only_attribution"))
    materialization = _dict(report.get("materialization_summary"))
    blocked_actions = _dict(report.get("blocked_actions"))
    head_audit = _dict(report.get("head_audit"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "remediation_design_plan_authorized": bool(
            decision.get("remediation_design_plan_authorized")
        ),
        "dp_head": head_audit.get("dp_head"),
        "expected_dp_head": head_audit.get("expected_dp_head", EXPECTED_DP_HEAD),
        "source_status": source.get("status"),
        "snapshots": _optional_int(source.get("snapshots")),
        "snapshots_with_generated_candidates": _optional_int(
            source.get("snapshots_with_generated_candidates")
        ),
        "generated_candidate_rows": _optional_int(source.get("generated_candidate_rows")),
        "lower_union_red_rows": _optional_int(source.get("lower_union_red_rows")),
        "hard_feasible_rows": _optional_int(source.get("hard_feasible_rows")),
        "comfort_admissible_rows": _optional_int(
            source.get("comfort_admissible_rows")
        ),
        "hard_support_rate": _optional_float(source.get("hard_support_rate")),
        "comfort_support_rate": _optional_float(source.get("comfort_support_rate")),
        "materialized_rows": _optional_int(materialization.get("materialized_rows")),
        "report_only_rows": _optional_int(materialization.get("report_only_rows")),
        "uses_outcome_labels_rows": _optional_int(
            materialization.get("uses_outcome_labels_rows")
        ),
        "score_mutation_rows": _optional_int(materialization.get("score_mutation_rows")),
        "selector_mutation_rows": _optional_int(
            materialization.get("selector_mutation_rows")
        ),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "secondary_blocker_family": attribution.get("secondary_blocker_family"),
        "training_ready": bool(attribution.get("training_ready")),
        "replay_evidence_ready": bool(attribution.get("replay_evidence_ready")),
        "positive_support_evidence": bool(attribution.get("positive_support_evidence")),
        "blocked_action_conflicts": [
            key for key, value in blocked_actions.items() if bool(value)
        ],
    }


def _audit_evidence_summary(audit_text: str) -> dict[str, Any]:
    anchors = {
        name: _find_anchor(audit_text, pattern)
        for name, pattern in AUDIT_EVIDENCE_PATTERNS.items()
    }
    return {
        "audit_line_count": len(audit_text.splitlines()),
        "anchors": anchors,
        "all_required_present": all(anchor["present"] for anchor in anchors.values()),
    }


def _design_plan(
    *,
    failure_attribution_json: str,
    audit_md: str,
    source: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "route": "dp_native_candidate_reranking_only",
        "failure_attribution_json": failure_attribution_json,
        "audit_md": audit_md,
        "source_materialized_generator_rejected": (
            source["passed"]
            and source["hard_feasible_rows"] == 0
            and source["comfort_admissible_rows"] == 0
            and source["generated_candidate_rows"] == source["materialized_rows"]
        ),
        "uses_existing_dp_native_evidence_only": evidence["all_required_present"],
        "next_gate": AUTHORIZED_NEXT_WORK,
        "success_criteria": [
            "selected output is an index k from the original DP candidate tensor: 0 <= k < candidate_count",
            "candidate tensor shape, hash, and candidate_count are unchanged before and after CAMP evaluation",
            "no candidate row is added and no trajectory coordinate, heading, speed, or postprocess output is mutated",
            "CAMP reads only DP-native current/logged candidate features, atoms, scores, selection_scores, feasible_mask, and infeasibility_reasons",
            "selected_index mutation is false and selector-equivalence fields remain exact for selected_index, feasible_mask, scores, selection_scores, atoms, and normalized_atoms when the gate is diagnostic-only",
            "DP code, config, weights, and HEAD remain fixed at the expected commit",
            "any later benefit claim must be based only on DP-native candidate re-selection, not CAMP-side generated or rewritten trajectories",
        ],
        "failure_criteria": [
            "any generated_candidate_rows or materialized rows are counted as positive CAMP reranking evidence",
            "selected output is not traceable to an original DP candidate index",
            "candidate_count changes, candidate tensor hash changes, or any candidate coordinates are rewritten",
            "selector-equivalence or mutation checks are missing, indirect, or nonzero for diagnostic logging gates",
            "DP HEAD, DP config, or DP weights differ from the fixed expected commit",
            "the gate requests replay, Full36, formal seeds, CAMP retraining, atom promotion, online selector promotion, or a safety benefit claim",
        ],
        "prohibited_evidence_families": list(PROHIBITED_EVIDENCE_FAMILIES),
        "required_next_artifact_fields": [
            "HEADS",
            "SHA256SUMS",
            "EXIT_CODE",
            "log",
            "source_dp_candidate_artifact_paths",
            "candidate_tensor_shape_and_hash",
            "candidate_count_before_after",
            "selected_index_source_and_output_range_check",
            "scores_selection_scores_atoms_feasible_mask_infeasibility_reasons_presence",
            "mutation_checks",
            "blocked_action_flags",
        ],
        "boundary_flags": {
            "plan_only": True,
            "read_only": True,
            "candidate_generation_execution": False,
            "trajectory_rewrite": False,
            "candidate_tensor_mutation": False,
            "replay": False,
            "formal_seeds": False,
            "full36": False,
            "training": False,
            "atom_promotion": False,
            "online_selector_promotion": False,
            "dp_modification": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("source_passed", source["passed"]),
        _check("source_status_complete", str(source["status"]).endswith("_complete")),
        _check(
            "source_authorizes_design_plan",
            bool(source["remediation_design_plan_authorized"]),
        ),
        _check(
            "source_next_work_matches_materialized_rejection",
            source["authorized_next_work"] == MATERIALIZED_REJECTION_NEXT_WORK,
        ),
        _check("dp_head_fixed", source["dp_head"] == EXPECTED_DP_HEAD),
        _check("generated_rows_positive", source["generated_candidate_rows"] == 73),
        _check("materialized_rows_positive", source["materialized_rows"] == 73),
        _check("generated_equals_materialized", source["generated_candidate_rows"] == source["materialized_rows"]),
        _check("hard_support_zero", source["hard_feasible_rows"] == 0),
        _check("comfort_support_zero", source["comfort_admissible_rows"] == 0),
        _check(
            "primary_blocker_is_materialized_hard_failure",
            source["primary_blocker_family"]
            == "route_topology_hard_constraint_failure_after_v4_materialization",
        ),
        _check("training_not_ready", not source["training_ready"]),
        _check("replay_not_ready", not source["replay_evidence_ready"]),
        _check("no_positive_support_evidence", not source["positive_support_evidence"]),
        _check("source_no_blocked_authorizations", not source["blocked_action_conflicts"]),
        _check("source_no_outcome_labels", source["uses_outcome_labels_rows"] == 0),
        _check("source_no_score_mutation", source["score_mutation_rows"] == 0),
        _check("source_no_selector_mutation", source["selector_mutation_rows"] == 0),
    ]


def _evidence_checks(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for name, anchor in evidence["anchors"].items():
        checks.append(_check(f"audit_anchor_{name}", bool(anchor["present"])))
    checks.append(_check("audit_required_anchors_present", evidence["all_required_present"]))
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    required_success_phrases = (
        "original DP candidate tensor",
        "candidate_count are unchanged",
        "no candidate row is added",
        "feasible_mask",
        "selected_index mutation is false",
        "DP code, config, weights",
        "DP-native candidate re-selection",
    )
    success_text = "\n".join(plan["success_criteria"])
    return [
        _check("plan_route_dp_native", plan["route"] == "dp_native_candidate_reranking_only"),
        _check(
            "plan_source_materialized_generator_rejected",
            plan["source_materialized_generator_rejected"],
        ),
        _check("plan_uses_existing_dp_native_evidence", plan["uses_existing_dp_native_evidence_only"]),
        _check("plan_next_gate", plan["next_gate"] == AUTHORIZED_NEXT_WORK),
        *[
            _check(f"success_criterion_contains_{idx}", phrase in success_text)
            for idx, phrase in enumerate(required_success_phrases)
        ],
        *[
            _check(
                f"prohibits_{family}",
                family in plan["prohibited_evidence_families"],
            )
            for family in PROHIBITED_EVIDENCE_FAMILIES
        ],
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    flags = plan["boundary_flags"]
    false_flags = [
        "candidate_generation_execution",
        "trajectory_rewrite",
        "candidate_tensor_mutation",
        "replay",
        "formal_seeds",
        "full36",
        "training",
        "atom_promotion",
        "online_selector_promotion",
        "dp_modification",
        "safety_benefit_claim",
        "camp_over_dp_top1_claim",
    ]
    return [
        _check("boundary_plan_only", flags["plan_only"]),
        _check("boundary_read_only", flags["read_only"]),
        *[_check(f"boundary_no_{name}", not flags[name]) for name in false_flags],
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    blocked = {key: False for key in BLOCKED_ACTIONS}
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "dp_native_reranking_design_plan_ready": passed,
        "fixed_artifact_evidence_audit_authorized": passed,
        **blocked,
    }


def _find_anchor(text: str, pattern: str) -> dict[str, Any]:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return {"present": True, "line": line_number, "pattern": pattern}
    return {"present": False, "line": None, "pattern": pattern}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
