#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_FAILURE_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_guarded_"
    "fixed_snapshot_screen_rerun_failure_attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

FAILURE_JSON = "failure_attribution.json"
FAILURE_MD = "failure_attribution.md"

REQUIRED_AUDIT_AUTHORIZATION = FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK

BLOCKED_ACTIONS = (
    "production_implementation_edit_authorized",
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only follow-up design after negative guarded remediation "
            "fixed-snapshot support evidence."
        )
    )
    parser.add_argument(
        "--failure_attribution_root",
        type=Path,
        default=Path(DEFAULT_FAILURE_ATTRIBUTION_ROOT),
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        failure_attribution_root=args.failure_attribution_root,
        audit_path=args.audit_path,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
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
    failure_attribution_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(failure_attribution_root)
    source = _failure_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _design_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_design_plan_v1"
            ),
            "label": label,
            "role": "plan-only follow-up design after negative support evidence",
            "plan_only": True,
            "implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan designs a future default-off follow-up only. It "
                "does not edit production code, create candidates, rerun a "
                "screen, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T "
                "w, mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or claim "
                "a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "failure_attribution_artifact": _strip_payload(artifact),
        "failure_attribution_summary": source,
        "design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["failure_attribution_summary"]
    plan = report["design_plan"]
    lines = [
        "# Negative-Support Follow-Up Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Positive support evidence: `{source['positive_support_evidence']}`",
        f"- Training ready: `{source['training_ready']}`",
        "",
        "## Plan Components",
        "",
    ]
    for component in plan["components"]:
        lines.append(f"### {component['name']}")
        lines.append("")
        lines.append(component["purpose"])
        lines.append("")
        lines.append(f"- Evidence driver: `{component['evidence_driver']}`")
        lines.append(f"- Contract: `{component['contract']}`")
        lines.append("")
    lines.extend(
        [
            "## Next Gate",
            "",
            f"`{plan['authorized_next_work']}`",
            "",
            "## Boundaries",
            "",
        ]
    )
    for item in plan["forbidden_actions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / FAILURE_JSON
    markdown_path = root / FAILURE_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _failure_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    source = _dict(payload.get("source_summary"))
    attribution = _dict(payload.get("read_only_attribution"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "positive_support_evidence": bool(decision.get("positive_support_evidence")),
        "training_ready": bool(decision.get("training_ready")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "screen_status": source.get("status"),
        "snapshots": int(source.get("snapshots") or 0),
        "snapshots_with_generated_candidates": int(
            source.get("snapshots_with_generated_candidates") or 0
        ),
        "generated_candidate_rows": int(source.get("generated_candidate_rows") or 0),
        "hard_support_rate": float(source.get("hard_support_rate") or 0.0),
        "comfort_support_rate": float(source.get("comfort_support_rate") or 0.0),
        "comfort_admissible_rows": int(source.get("comfort_admissible_rows") or 0),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "construction_status_ranking": _list(
            attribution.get("construction_status_ranking")
        ),
        "comfort_blocker_ranking": _list(attribution.get("comfort_blocker_ranking")),
        "hard_blocker_ranking": _list(attribution.get("hard_blocker_ranking")),
    }


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "negative_support_followup_design_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "design_position": (
            "Do not continue to replay or training. Treat the guarded "
            "remediation result as negative evidence and design the next "
            "candidate-support intervention around coverage, hard feasibility, "
            "and comfort feasibility before any additional execution gate."
        ),
        "required_static_contracts": [
            "negative_support_evidence_is_consumed_without_safety_claim",
            "followup_components_are_default_off_and_current_tick_only",
            "coverage_component_addresses_fail_closed_snapshots",
            "comfort_component_addresses_hard_progress_feasible_regressions",
            "hard_feasibility_component_addresses_red_lane_road_kinematic_counts",
            "no_execution_or_training_authorization_leaks",
            "affine_score_and_convex_master_boundary_preserved",
        ],
        "components": [
            {
                "name": "coverage_first_fail_closed_partition",
                "purpose": (
                    "Partition the 30 fail-closed snapshots before proposing "
                    "another generator change, so the next implementation does "
                    "not only improve the 27 ready snapshots."
                ),
                "evidence_driver": "construction_status.fail_closed=30, ready=27",
                "contract": (
                    "The follow-up must define current-tick finite evidence for "
                    "every construction partition and fail closed without "
                    "mutating candidates, scores, selected index, fallback, "
                    "online selector, or deployed atom schema."
                ),
            },
            {
                "name": "hard_feasibility_support_floor",
                "purpose": (
                    "Raise hard-feasible snapshot support above the fixed "
                    "nonformal threshold before replay or training can be "
                    "considered."
                ),
                "evidence_driver": (
                    "hard_support_rate=0.148148 below 0.25; dp_red_light=275, "
                    "dp_lane_crossing=253, dp_road_border=242, dp_kinematic=241"
                ),
                "contract": (
                    "Any proposed candidate-family change must remain an "
                    "opt-in current-tick transform over fixed DP candidates and "
                    "must not change DP code, weights, configs, or invocation."
                ),
            },
            {
                "name": "comfort_feasibility_after_hard_progress",
                "purpose": (
                    "Address the systematic comfort blockers that remain even "
                    "when candidates are hard-feasible and progress-feasible."
                ),
                "evidence_driver": (
                    "comfort_support_rate=0.0; command_lateral and progress "
                    "blockers each occur in 37 hard-progress-feasible rows"
                ),
                "contract": (
                    "The design must constrain lateral and progress changes as "
                    "finite current-tick candidate features or diagnostics; any "
                    "future atomization must be nonnegative or hinge/signed-"
                    "split legal and preserve score_k(w)=a_k^T w."
                ),
            },
            {
                "name": "nonformal_screen_only_readiness",
                "purpose": (
                    "Define the evidence required before another guarded "
                    "nonformal fixed-snapshot screen rerun can be planned."
                ),
                "evidence_driver": "positive_support_evidence=False and training_ready=False",
                "contract": (
                    "The next execution gate, if ever planned, remains "
                    "nonformal seed-2 fixed-snapshot only; formal seeds 11/12/13, "
                    "Full36, replay, promotion, and training remain frozen."
                ),
            },
        ],
        "forbidden_actions": [
            "production implementation edits are not authorized in this design gate",
            "candidate generation and fixed-snapshot screen execution are not authorized",
            "replay, Full36, closed-loop smoke, and formal seeds 11/12/13 remain frozen",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
            "DP weights, DP code, DP configs, and DP invocation must remain fixed",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", artifact["exists"]),
        _check("failure_attribution_json_exists", artifact["json_exists"]),
        _check("failure_attribution_markdown_exists", artifact["markdown_exists"]),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "failure_attribution_markdown_records_boundaries",
            "## Boundaries" in artifact["markdown_text"],
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_authorizes_design_plan", REQUIRED_AUDIT_AUTHORIZATION in audit_text),
        _check(
            "audit_records_negative_support",
            "with negative support evidence" in audit_text
            and "hard_support_below_threshold_and_comfort_support_zero" in audit_text,
        ),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_status_complete", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("failure_attribution_passed", source["passed"] is True),
        _check("failure_attribution_failed_checks_empty", not source["failed_checks"]),
        _check(
            "failure_attribution_authorizes_this_plan",
            source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
        ),
        _check("failure_attribution_no_positive_support", source["positive_support_evidence"] is False),
        _check("failure_attribution_training_not_ready", source["training_ready"] is False),
        _check("failure_attribution_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("failure_attribution_primary_blocker_expected", source["primary_blocker_family"] == "hard_support_below_threshold_and_comfort_support_zero"),
        _check("failure_attribution_coverage_gap_present", source["snapshots_with_generated_candidates"] < source["snapshots"]),
        _check("failure_attribution_zero_comfort_rows", source["comfort_admissible_rows"] == 0),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    component_names = {component["name"] for component in plan["components"]}
    contracts = set(plan["required_static_contracts"])
    forbidden_text = "\n".join(plan["forbidden_actions"])
    return [
        _check("plan_selects_next_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_has_coverage_component", "coverage_first_fail_closed_partition" in component_names),
        _check("plan_has_hard_feasibility_component", "hard_feasibility_support_floor" in component_names),
        _check("plan_has_comfort_component", "comfort_feasibility_after_hard_progress" in component_names),
        _check("plan_has_nonformal_screen_readiness", "nonformal_screen_only_readiness" in component_names),
        _check("plan_contracts_cover_execution_leaks", "no_execution_or_training_authorization_leaks" in contracts),
        _check("plan_contracts_cover_math_boundary", "affine_score_and_convex_master_boundary_preserved" in contracts),
        _check("plan_forbids_production_edits", "production implementation edits are not authorized" in forbidden_text),
        _check("plan_forbids_training", "CAMP retraining" in forbidden_text),
        _check("plan_forbids_dp_modification", "DP weights" in forbidden_text),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    return [
        _check("boundary_no_execution_authorized", True),
        _check("boundary_no_training_authorized", True),
        _check("boundary_no_formal_seeds_authorized", True),
        _check("boundary_no_dp_modification_authorized", True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_plan_ready": False,
        "static_contract_review_authorized": passed,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown_text"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
