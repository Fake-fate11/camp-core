#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_atom_design_review import (
    ATOM_NAME,
    AUTHORIZED_NEXT_WORK as SOURCE_NEXT_WORK,
    COEFFICIENT_FIELD,
    PAYLOAD_KEY,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_shadow_atom_dry_run_plan_ready"
REJECT_STATUS = "candidate_set_consensus_shadow_atom_dry_run_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_dry_run_implementation_unit_tests_only"
)

EXPECTED_LOGS = 6
EXPECTED_RECORDS = 60
EXPECTED_CANDIDATES = 8
FORMAL_SEEDS = frozenset({11, 12, 13})

DEFAULT_REPLAY_ROOT = (
    "/root/autodl-tmp/camp_dp_candidate_set_consensus_broader_nonformal_materiality"
)
DEFAULT_CANDIDATE_ROOT = f"{DEFAULT_REPLAY_ROOT}/logging_enabled"
DEFAULT_AUDIT_ROOT = f"{DEFAULT_REPLAY_ROOT}/audit"

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
            "Plan-only gate for a future candidate-set consensus shadow atom "
            "dry run. It predeclares zero-weight append checks over existing "
            "nonformal replay logs but does not execute the dry run."
        )
    )
    parser.add_argument("--atom_design_review_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--candidate_root", default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--audit_root", default=DEFAULT_AUDIT_ROOT)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        atom_design_review=_load_json(args.atom_design_review_json),
        label=args.label,
        candidate_root=args.candidate_root,
        audit_root=args.audit_root,
        paths={"atom_design_review_json": str(args.atom_design_review_json)},
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
    atom_design_review: dict[str, Any],
    label: str | None = None,
    candidate_root: str = DEFAULT_CANDIDATE_ROOT,
    audit_root: str = DEFAULT_AUDIT_ROOT,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(atom_design_review)
    dry_run = _dry_run_plan(candidate_root=candidate_root, audit_root=audit_root)
    checks = [
        *_source_checks(source),
        *_dry_run_scope_checks(dry_run),
        *_zero_weight_append_checks(dry_run),
        *_boundary_checks(dry_run),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_shadow_atom_dry_run_plan_v1",
            "label": label,
            "role": (
                "plan-only shadow atom dry-run design after candidate-set "
                "consensus atom design review; no dry-run execution"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "The planned dry run may read existing logging-enabled "
                "nonformal selection logs and append the fixed candidate-set "
                "consensus coefficient as a shadow atom with zero weight only. "
                "Because the added weight is zero, selector-visible affine "
                "scores must remain exactly unchanged: score_k(w)=a_k^T w "
                "before append equals the shadow score after append. This "
                "does not promote the atom, mutate runtime selection, train "
                "CAMP, rerun DP, or claim DP-side classical Benders cuts. The "
                "simplex/CVaR/L2 master remains convex because any later "
                "nonzero weight review would still optimize only over fixed "
                "coefficients."
            ),
        },
        "source_summary": source,
        "dry_run_plan": dry_run,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["dry_run_plan"]
    source = report["source_summary"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Dry-Run Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Dry-run implementation authorized: `{decision['dry_run_implementation_authorized']}`",
        f"- Dry-run execution authorized: `{decision['dry_run_execution_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source authorized next work: `{source['authorized_next_work']}`",
        f"- Atom name: `{source['atom_name']}`",
        f"- Payload key: `{source['payload_key']}`",
        f"- Coefficient field: `{source['coefficient_field']}`",
        "",
        "## Planned Scope",
        "",
        f"- Candidate root: `{plan['candidate_root']}`",
        f"- Audit root: `{plan['audit_root']}`",
        f"- Expected logs: `{plan['expected_logs']}`",
        f"- Expected records: `{plan['expected_records']}`",
        f"- Expected candidates: `{plan['expected_candidates']}`",
        f"- Formal seeds forbidden: `{plan['formal_seeds_forbidden']}`",
        "",
        "## Required Checks",
        "",
    ]
    for item in plan["required_dry_run_checks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not authorize dry-run execution, replay, atom "
            "promotion, CAMP training, Full36, formal seeds, online selector "
            "changes, DP modification, or a DP-side classical Benders claim.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    atom = _dict(report.get("proposed_atom_design"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "atom_design_review_ready": bool(decision.get("atom_design_review_ready")),
        "shadow_atom_dry_run_plan_authorized": bool(
            decision.get("shadow_atom_dry_run_plan_authorized")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
        "atom_name": atom.get("atom_name"),
        "payload_key": atom.get("payload_key"),
        "coefficient_field": atom.get("coefficient_field"),
        "nonnegative_by_definition": bool(atom.get("nonnegative_by_definition")),
        "hinge_required": bool(atom.get("hinge_required")),
        "signed_split_required": bool(atom.get("signed_split_required")),
        "affine_score_compatible": bool(atom.get("affine_score_compatible")),
        "convex_master_compatible": bool(atom.get("convex_master_compatible")),
        "classic_benders_claim": bool(atom.get("classic_benders_claim")),
    }


def _dry_run_plan(*, candidate_root: str, audit_root: str) -> dict[str, Any]:
    return {
        "plan_only": True,
        "candidate_root": candidate_root,
        "audit_root": audit_root,
        "expected_logs": EXPECTED_LOGS,
        "expected_records": EXPECTED_RECORDS,
        "expected_candidates": EXPECTED_CANDIDATES,
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "atom_name": ATOM_NAME,
        "payload_key": PAYLOAD_KEY,
        "coefficient_field": COEFFICIENT_FIELD,
        "shadow_append_policy": {
            "append_to": ["atoms", "normalized_atoms", "atom_names"],
            "weight_append_value": 0.0,
            "selection_weight_append_value": 0.0,
            "score_delta_tolerance": 0.0,
            "selected_index_delta_tolerance": 0,
            "write_runtime_logs": False,
        },
        "required_dry_run_checks": [
            "read existing logging_enabled camp_selection_log.json files only",
            "require exactly 6 logs, 60 records, and 8 candidates per valid record",
            "reject any run id or artifact path containing formal seed 11, 12, or 13",
            "require payload candidate_set_consensus_payload_logging.available=true before append",
            "require coefficient field candidate_set_consensus_center_rms_m length equals candidate_count",
            "require coefficient values are finite and nonnegative",
            "append candidate_set_consensus_center_rms_cost_v1 as a shadow atom with zero weight",
            "prove scores and selection_scores are exactly unchanged after zero-weight append",
            "prove selected_index, feasible_mask, fallback mode, and infeasibility reasons are unchanged",
            "keep closed-loop outcomes and safety-score summaries out of the coefficient",
            "write dry-run JSON/markdown/SHA/HEADS artifacts before any later execution gate",
            "do not change deployed atom schema, CAMP weights, online selector, DP code, or DP weights",
        ],
        "commands_if_later_implemented": {
            "implementation_target": (
                "scripts/integrations/analyze_diffusion_planner_candidate_set_"
                "consensus_shadow_atom_dry_run.py"
            ),
            "test_target": (
                "camp_core/tests/test_diffusion_planner_candidate_set_consensus_"
                "shadow_atom_dry_run.py"
            ),
            "cli_shape": [
                "python",
                "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run.py",
                "--atom_design_review_json",
                "<atom_design_review.json>",
                "--candidate_root",
                candidate_root,
                "--expected_logs",
                str(EXPECTED_LOGS),
                "--expected_records",
                str(EXPECTED_RECORDS),
                "--expected_candidates",
                str(EXPECTED_CANDIDATES),
                "--output_json",
                f"{audit_root}/candidate_set_consensus_shadow_atom_dry_run.json",
                "--output_md",
                f"{audit_root}/candidate_set_consensus_shadow_atom_dry_run.md",
            ],
        },
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal("source_authorizes_this_plan", source["authorized_next_work"], SOURCE_NEXT_WORK),
        _check_equal("source_atom_design_review_ready", source["atom_design_review_ready"], True),
        _check_equal(
            "source_shadow_atom_dry_run_plan_authorized",
            source["shadow_atom_dry_run_plan_authorized"],
            True,
        ),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_atom_name", source["atom_name"], ATOM_NAME),
        _check_equal("source_payload_key", source["payload_key"], PAYLOAD_KEY),
        _check_equal("source_coefficient_field", source["coefficient_field"], COEFFICIENT_FIELD),
        _check_equal("source_nonnegative", source["nonnegative_by_definition"], True),
        _check_equal("source_hinge_not_required", source["hinge_required"], False),
        _check_equal("source_signed_split_not_required", source["signed_split_required"], False),
        _check_equal("source_affine_score_compatible", source["affine_score_compatible"], True),
        _check_equal("source_convex_master_compatible", source["convex_master_compatible"], True),
        _check_equal("source_classic_benders_claim_false", source["classic_benders_claim"], False),
    ]


def _dry_run_scope_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_only", plan["plan_only"], True),
        _check_equal("expected_logs", plan["expected_logs"], EXPECTED_LOGS),
        _check_equal("expected_records", plan["expected_records"], EXPECTED_RECORDS),
        _check_equal("expected_candidates", plan["expected_candidates"], EXPECTED_CANDIDATES),
        _check_equal(
            "formal_seeds_forbidden",
            sorted(plan["formal_seeds_forbidden"]),
            sorted(FORMAL_SEEDS),
        ),
        _check_equal("candidate_root_is_logging_enabled", plan["candidate_root"].endswith("/logging_enabled"), True),
        _check_equal("audit_root_declared", bool(plan["audit_root"]), True),
    ]


def _zero_weight_append_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    policy = _dict(plan.get("shadow_append_policy"))
    required_text = " ".join(plan.get("required_dry_run_checks") or []).lower()
    return [
        _check_equal("append_to_atoms_declared", "atoms" in policy.get("append_to", []), True),
        _check_equal("append_to_normalized_atoms_declared", "normalized_atoms" in policy.get("append_to", []), True),
        _check_equal("zero_weight_append", policy.get("weight_append_value"), 0.0),
        _check_equal("zero_selection_weight_append", policy.get("selection_weight_append_value"), 0.0),
        _check_equal("score_delta_exact_zero", policy.get("score_delta_tolerance"), 0.0),
        _check_equal("selected_index_delta_exact_zero", policy.get("selected_index_delta_tolerance"), 0),
        _check_equal("runtime_logs_not_written", policy.get("write_runtime_logs"), False),
        _check_equal("requires_shape_check", "length equals candidate_count" in required_text, True),
        _check_equal("requires_nonnegative_check", "finite and nonnegative" in required_text, True),
        _check_equal("requires_selector_invariance", "selected_index" in required_text and "unchanged" in required_text, True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    required_text = " ".join(plan.get("required_dry_run_checks") or []).lower()
    return [
        _check_equal("blocks_formal_seeds", "formal seed" in required_text, True),
        _check_equal("blocks_closed_loop_outcomes", "closed-loop outcomes" in required_text, True),
        _check_equal("blocks_online_selector_change", "online selector" in required_text, True),
        _check_equal("blocks_dp_change", "dp code" in required_text and "dp weights" in required_text, True),
        _check_equal("requires_sha_heads_artifact", "sha/heads" in required_text, True),
        _check_equal(
            "implementation_target_predeclared",
            plan["commands_if_later_implemented"]["implementation_target"].endswith(
                "candidate_set_consensus_shadow_atom_dry_run.py"
            ),
            True,
        ),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "shadow_atom_dry_run_plan_ready": passed,
        "dry_run_implementation_authorized": passed,
        "dry_run_execution_authorized": False,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
