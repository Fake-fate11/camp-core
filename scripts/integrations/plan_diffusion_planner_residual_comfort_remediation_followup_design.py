#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
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

_ATTRIBUTION_MODULE = (
    "scripts.integrations.analyze_diffusion_planner_residual_comfort_"
    "remediation_guarded_rerun_failure_attribution"
)
_MATERIALITY_MODULE = (
    "scripts.integrations.plan_diffusion_planner_candidate_set_consensus_"
    "broader_nonformal_materiality"
)
_attribution = importlib.import_module(_ATTRIBUTION_MODULE)
_materiality = importlib.import_module(_MATERIALITY_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_plan_"
    "rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_static_"
    "contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

ATTRIBUTION_JSON = "failure_attribution.json"
ATTRIBUTION_MD = "failure_attribution.md"
EXPECTED_DP_HEAD = _materiality.EXPECTED_DP_HEAD
FORMAL_SEEDS = _materiality.FORMAL_SEEDS
FAILURE_ATTRIBUTION_READY_STATUS = _attribution.READY_STATUS
FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK = _attribution.AUTHORIZED_NEXT_WORK
PRIMARY_BLOCKER_FAMILY = "comfort_support_zero_after_hard_support_pass"
TOP_COMMAND_JERK_BLOCKER = "route_topology_comfort_blocked_command_jerk"
TOP_ROLLOUT_LATERAL_BLOCKER = "route_topology_comfort_blocked_rollout_lateral"
RESIDUAL_FAMILY = (
    "command_jerk_rollout_lateral_zero_comfort_gap_after_hard_progress_survival"
)

BLOCKED_ACTIONS = (
    "implementation_code_edit_authorized",
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
            "Plan-only follow-up design after residual comfort remediation "
            "guarded screen failure attribution."
        )
    )
    parser.add_argument(
        "--failure_attribution_root",
        type=Path,
        default=Path(DEFAULT_ATTRIBUTION_ROOT),
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
    source = _attribution_summary(artifact["payload"])
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
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_design_plan_v1"
            ),
            "label": label,
            "role": "plan-only follow-up design from negative support attribution",
            "plan_only": True,
            "implementation_code_edit": False,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan reads only the completed attribution artifact and "
                "audit authorization. It does not edit implementation code, "
                "create candidates, rerun the screen, run DP, run replay, use "
                "formal seeds, define runtime atoms, choose lambda online, "
                "alter score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, modify DP "
                "weights or code, or claim a DP-side classical Benders "
                "decomposition. Any later atom or descriptor proposal must "
                "prove nonnegativity or legal hinge/signed-split form and "
                "remain affine over the fixed finite candidate set."
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
        "followup_design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["failure_attribution_summary"]
    plan = report["followup_design_plan"]
    lines = [
        "# Residual Comfort Remediation Follow-Up Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Residual family: `{plan['target_failure']['residual_family']}`",
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Comfort support gap: `{source['comfort_support_gap']}`",
        "",
        "## Design Position",
        "",
        plan["design_position"],
        "",
        "## Tracks",
        "",
    ]
    for item in plan["tracks"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Evidence: `{item['evidence']}`")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Static Review Requirements", ""])
    for item in plan["static_review_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in plan["rejected_non_fixes"]:
        lines.append(f"- `{item['name']}`: {item['reason']}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / ATTRIBUTION_JSON
    md_path = root / ATTRIBUTION_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": json_path.is_file(),
        "markdown_exists": md_path.is_file(),
        "json_sha256": _sha256(json_path),
        "markdown_sha256": _sha256(md_path),
        "payload": _read_json(json_path),
        "markdown_text": _read_text(md_path),
    }


def _attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    ranking = _list(attribution.get("comfort_blocker_ranking"))
    top_names = [
        str(item.get("name"))
        for item in ranking
        if isinstance(item, dict) and item.get("name")
    ]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "hard_support_positive": bool(attribution.get("hard_support_positive")),
        "comfort_support_positive": bool(attribution.get("comfort_support_positive")),
        "positive_support_evidence": bool(
            attribution.get("positive_support_evidence")
        ),
        "replay_evidence_ready": bool(attribution.get("replay_evidence_ready")),
        "training_ready": bool(attribution.get("training_ready")),
        "comfort_support_gap": float(attribution.get("comfort_support_gap") or 0.0),
        "candidate_coverage_rate": float(
            attribution.get("candidate_coverage_rate") or 0.0
        ),
        "comfort_blocker_ranking": ranking,
        "top_comfort_blockers": top_names[:5],
        "residual_family": RESIDUAL_FAMILY,
    }


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "residual_comfort_remediation_followup_design_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_failure": {
            "primary_blocker_family": source["primary_blocker_family"],
            "residual_family": RESIDUAL_FAMILY,
            "comfort_support_gap": source["comfort_support_gap"],
            "top_comfort_blockers": source["top_comfort_blockers"],
            "candidate_coverage_rate": source["candidate_coverage_rate"],
        },
        "design_position": (
            "Do not train CAMP, do not rerun the screen, and do not edit the "
            "production screen implementation in this gate. The evidence says "
            "hard/progress support exists, but comfort support is exactly zero "
            "with command jerk and rollout lateral as the strongest blockers. "
            "The next admissible work is a static contract review of a "
            "default-off follow-up design that separates descriptor "
            "separability from any future candidate-construction intervention."
        ),
        "tracks": [
            {
                "name": "comfort_gap_blocker_partition",
                "purpose": (
                    "Partition the existing hard/progress survivors by command "
                    "jerk, rollout lateral, command lateral, rollout jerk, and "
                    "progress-loss blocker families before any future execution "
                    "gate is proposed."
                ),
                "evidence": ",".join(source["top_comfort_blockers"]),
                "contract": (
                    "read-only current-tick finite candidate features; no "
                    "candidate, score, selected-index, fallback, online "
                    "selector, or deployed atom-schema mutation"
                ),
            },
            {
                "name": "command_jerk_rollout_lateral_descriptor_family",
                "purpose": (
                    "Specify candidate-local descriptor families that could "
                    "separate high-jerk or high-lateral-rollout survivors from "
                    "future admissible support without using outcome labels."
                ),
                "evidence": RESIDUAL_FAMILY,
                "contract": (
                    "descriptors must be nonnegative or legal hinge/signed-"
                    "split terms and preserve score_k(w)=a_k^T w"
                ),
            },
            {
                "name": "support_intervention_static_boundary",
                "purpose": (
                    "Define what a later default-off candidate support "
                    "intervention would need to prove before it could rerun a "
                    "fixed-snapshot screen."
                ),
                "evidence": "positive_support_evidence=False",
                "contract": (
                    "plan-only boundary; no candidate generation, screen "
                    "rerun, replay, formal seeds, Full36, training, or DP edit"
                ),
            },
            {
                "name": "positive_support_before_training_gate",
                "purpose": (
                    "Keep training blocked until a fixed-snapshot or nonformal "
                    "rerun shows positive support with no leakage and no "
                    "candidate-construction contract defect."
                ),
                "evidence": "training_ready=False and replay_evidence_ready=False",
                "contract": (
                    "training_execution_authorized remains False; no atom "
                    "promotion, online selector promotion, safety claim, or "
                    "CAMP-over-DP-Top-1 claim"
                ),
            },
            {
                "name": "dp_fixed_black_box_boundary",
                "purpose": (
                    "Keep TiERIV Diffusion Planner as the fixed black-box "
                    "candidate trajectory source."
                ),
                "evidence": EXPECTED_DP_HEAD,
                "contract": (
                    "no DP code, weight, config, invocation, reward-recompute, "
                    "tracker-recompute, tuning, or classical Benders claim"
                ),
            },
        ],
        "static_review_requirements": [
            "prove the follow-up design is default-off and plan-only",
            "prove all proposed features are finite, current-tick, and candidate-local",
            "prove diagnostic payloads cannot alter candidates, scores, selected index, fallback, online selector, or deployed atom schema",
            "prove any descriptor is nonnegative or a legal hinge/signed-split term",
            "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
            "prove candidate generation, screen rerun, replay, Full36, and formal seeds remain unauthorized",
            "prove CAMP retraining remains unauthorized until positive support and a separate training contract exist",
            "prove DP remains fixed at the pinned commit",
            "prove no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is introduced",
        ],
        "rejected_non_fixes": [
            {
                "name": "train_on_negative_support",
                "reason": (
                    "zero comfort-admissible support cannot justify CAMP "
                    "training or replay"
                ),
            },
            {
                "name": "rerun_without_static_contract",
                "reason": (
                    "another screen rerun without a reviewed design would "
                    "only repeat the current zero-comfort failure mode"
                ),
            },
            {
                "name": "relax_comfort_acceptance",
                "reason": (
                    "weakening the comfort contract would erase the blocker "
                    "instead of creating legal CAMP-side evidence"
                ),
            },
            {
                "name": "selector_or_atom_promotion",
                "reason": (
                    "online selection and atom promotion cannot create missing "
                    "candidate support and are not authorized"
                ),
            },
            {
                "name": "dp_side_change",
                "reason": (
                    "DP must remain a fixed black-box generator at the pinned "
                    "commit"
                ),
            },
        ],
        "acceptance_criteria": [
            "failure attribution is complete and authorizes only this design-plan gate",
            "the plan explains the command-jerk and rollout-lateral zero-comfort blocker",
            "the plan separates descriptor separability from future candidate support intervention",
            "the plan blocks training, replay, rerun-until-positive, selector workarounds, promotion, and DP-side fixes",
            "the next gate is static contract review only and cannot edit implementation code",
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized in this gate",
            "production implementation edits are not authorized",
            "candidate generation and screen rerun are not authorized",
            "replay and closed-loop smoke are not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", artifact["exists"]),
        _check("failure_attribution_json_exists", artifact["json_exists"]),
        _check("failure_attribution_markdown_exists", artifact["markdown_exists"]),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "failure_attribution_markdown_records_title",
            "Residual Comfort Remediation Screen Failure Attribution"
            in artifact["markdown_text"],
        ),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check(
            "audit_records_failure_attribution_complete",
            FAILURE_ATTRIBUTION_READY_STATUS in audit_text,
        ),
        _check(
            "audit_authorizes_followup_design",
            FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check(
            "audit_records_command_jerk_blocker",
            TOP_COMMAND_JERK_BLOCKER in audit_text,
        ),
        _check(
            "audit_records_rollout_lateral_blocker",
            TOP_ROLLOUT_LATERAL_BLOCKER in audit_text,
        ),
        _check(
            "audit_blocks_candidate_generation",
            "candidate_generation_execution_authorized=False" in audit_text,
        ),
        _check(
            "audit_blocks_screen_rerun",
            "fixed_snapshot_screen_rerun_authorized=False" in audit_text,
        ),
        _check(
            "audit_blocks_training",
            "training_execution_authorized=False" in audit_text,
        ),
        _check(
            "audit_blocks_dp_modification",
            "dp_modification_authorized=False" in audit_text,
        ),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = set(source["top_comfort_blockers"])
    return [
        _check("failure_attribution_status_complete", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("failure_attribution_passed", source["passed"] is True),
        _check("failure_attribution_failed_checks_empty", not source["failed_checks"]),
        _check(
            "failure_attribution_authorizes_this_plan",
            source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
        ),
        _check("failure_attribution_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("failure_attribution_primary_blocker", source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY),
        _check("failure_attribution_hard_support_positive", source["hard_support_positive"] is True),
        _check("failure_attribution_comfort_support_absent", source["comfort_support_positive"] is False),
        _check("failure_attribution_positive_support_absent", source["positive_support_evidence"] is False),
        _check("failure_attribution_replay_not_ready", source["replay_evidence_ready"] is False),
        _check("failure_attribution_training_not_ready", source["training_ready"] is False),
        _check("failure_attribution_comfort_gap_positive", source["comfort_support_gap"] > 0),
        _check("failure_attribution_candidate_coverage_positive", source["candidate_coverage_rate"] > 0),
        _check("failure_attribution_command_jerk_blocker", TOP_COMMAND_JERK_BLOCKER in blockers),
        _check("failure_attribution_rollout_lateral_blocker", TOP_ROLLOUT_LATERAL_BLOCKER in blockers),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    tracks = {item["name"] for item in plan["tracks"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}
    return [
        _check("plan_selection_type", plan["selection_type"] == "residual_comfort_remediation_followup_design_plan_only"),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_target_residual_family", plan["target_failure"]["residual_family"] == RESIDUAL_FAMILY),
        _check("plan_has_blocker_partition", "comfort_gap_blocker_partition" in tracks),
        _check("plan_has_descriptor_family", "command_jerk_rollout_lateral_descriptor_family" in tracks),
        _check("plan_has_support_boundary", "support_intervention_static_boundary" in tracks),
        _check("plan_has_positive_support_gate", "positive_support_before_training_gate" in tracks),
        _check("plan_has_dp_boundary", "dp_fixed_black_box_boundary" in tracks),
        _check("plan_rejects_negative_training", "train_on_negative_support" in rejected),
        _check("plan_rejects_unreviewed_rerun", "rerun_without_static_contract" in rejected),
        _check("plan_rejects_comfort_relaxation", "relax_comfort_acceptance" in rejected),
        _check("plan_rejects_promotion", "selector_or_atom_promotion" in rejected),
        _check("plan_rejects_dp_change", "dp_side_change" in rejected),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate", "finite candidate" in text),
        _check("plan_mentions_candidate_local", "candidate-local" in text),
        _check("plan_mentions_no_mutation", "no candidate, score" in text),
        _check("plan_mentions_nonnegative_or_hinge", "nonnegative" in text and "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_static_review", decision["static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_safety_claim", decision["safety_benefit_claim_authorized"] is False),
        _check("boundary_blocks_camp_over_dp", decision["camp_over_dp_top1_claim_authorized"] is False),
        _check("boundary_blocks_benders", decision["classic_benders_claim_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "followup_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
        "followup_design_static_contract_review_authorized": passed,
        "implementation_code_edit_authorized": False,
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
