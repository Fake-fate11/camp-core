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
    "remediation_followup_guarded_rerun_failure_attribution"
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
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

ATTRIBUTION_JSON = "failure_attribution.json"
ATTRIBUTION_MD = "failure_attribution.md"
EXPECTED_DP_HEAD = _attribution.EXPECTED_DP_HEAD
FORMAL_SEEDS = _materiality.FORMAL_SEEDS
FAILURE_ATTRIBUTION_READY_STATUS = _attribution.READY_STATUS
FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK = _attribution.AUTHORIZED_NEXT_WORK

PRIMARY_BLOCKER_FAMILY = "comfort_support_zero_after_hard_support_pass"
RESIDUAL_FAMILY = (
    "zero_comfort_support_after_hard_progress_survival_requires_new_generator"
)
TOP_COMFORT_BLOCKERS = (
    "route_topology_comfort_blocked_command_jerk",
    "route_topology_comfort_blocked_rollout_jerk",
    "route_topology_comfort_blocked_command_lateral",
    "route_topology_comfort_blocked_progress_loss",
    "route_topology_comfort_blocked_rollout_lateral",
)
HARD_CONTEXT_BLOCKERS = ("dp_kinematic", "dp_lane_crossing", "dp_road_border")

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
            "Plan-only materially different generator design after follow-up "
            "residual comfort failure attribution."
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
                "remediation_followup_materially_different_generator_"
                "design_plan_v1"
            ),
            "label": label,
            "role": "plan-only materially different current-tick generator design",
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
                "This plan reads only the completed failure-attribution "
                "artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun the screen, "
                "run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T "
                "w, mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or "
                "claim a DP-side classical Benders decomposition. Any later "
                "descriptor or atom must prove definition, nonnegative or "
                "legal hinge/signed-split form, candidate-local availability, "
                "and affine score contribution over the fixed finite "
                "current-tick candidate set."
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
        "materially_different_generator_design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["failure_attribution_summary"]
    plan = report["materially_different_generator_design_plan"]
    lines = [
        "# Residual Comfort Follow-Up Materially Different Generator Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Static contract review authorized: "
            f"`{decision['static_contract_review_authorized']}`"
        ),
        f"- Residual family: `{plan['target_failure']['residual_family']}`",
        f"- Primary blocker: `{source['primary_blocker_family']}`",
        f"- Comfort support gap: `{source['comfort_support_gap']}`",
        "",
        "## Design Position",
        "",
        plan["design_position"],
        "",
        "## Material Difference",
        "",
    ]
    for item in plan["material_difference_claims"]:
        lines.append(f"- `{item['name']}`: {item['claim']}")
    lines.extend(["", "## Generator Tracks", ""])
    for item in plan["generator_tracks"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Evidence target: `{item['evidence_target']}`")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Descriptor And Atom Contract", ""])
    for item in plan["descriptor_atom_contract"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in plan["rejected_non_fixes"]:
        lines.append(f"- `{item['name']}`: {item['reason']}")
    lines.extend(["", "## Static Review Requirements", ""])
    for item in plan["static_review_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": (
            "residual_comfort_remediation_followup_materially_different_"
            "generator_design_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_failure": {
            "residual_family": RESIDUAL_FAMILY,
            "primary_blocker_family": source["primary_blocker_family"],
            "comfort_support_gap": source["comfort_support_gap"],
            "top_comfort_blockers": source["top_comfort_blockers"],
            "hard_context_blockers": source["hard_context_blockers"],
        },
        "design_position": (
            "The next admissible move is not another comfort-budget relaxation "
            "and not a replay or training attempt. The guarded rerun already "
            "showed hard/progress survival, but zero comfort support. A "
            "materially different generator must change the finite "
            "current-tick candidate construction so that support candidates "
            "are lane-station consistent, jerk-limited, red-stop aware, and "
            "lateral-continuity preserving before the existing hard/progress/"
            "comfort gates evaluate them. The default behavior, candidate0, "
            "online selector, deployed atoms, DP weights, DP code, DP config, "
            "and DP invocation all remain fixed."
        ),
        "material_difference_claims": [
            {
                "name": "construction_not_budget_relaxation",
                "claim": (
                    "The family changes candidate geometry and kinematics "
                    "upstream of the gates instead of accepting the same "
                    "failed rows with wider comfort thresholds."
                ),
            },
            {
                "name": "finite_current_tick_features_only",
                "claim": (
                    "The family may use only current-tick route, lane, ego, "
                    "traffic-light, and finite candidate features; it may not "
                    "use future outcomes, replay labels, or formal-seed data."
                ),
            },
            {
                "name": "candidate0_preserving_default_off_append",
                "claim": (
                    "Any later implementation must preserve candidate0 and "
                    "default behavior, and may only append bounded support "
                    "candidates behind an explicit default-off profile."
                ),
            },
            {
                "name": "score_affine_contract_preserved",
                "claim": (
                    "Any later descriptor or atom must be candidate-local and "
                    "enter only as an affine component of score_k(w)=a_k^T w, "
                    "leaving the simplex/CVaR/L2 master convex."
                ),
            },
        ],
        "generator_tracks": [
            {
                "name": "lane_station_jerk_limited_stop_synthesis",
                "purpose": (
                    "Synthesize support trajectories in lane-station space "
                    "from current ego speed, stop-line geometry, and red-light "
                    "state with bounded jerk and bounded command acceleration."
                ),
                "evidence_target": (
                    "reduce command jerk and rollout jerk blockers while "
                    "retaining progress-feasible rows"
                ),
                "contract": (
                    "deterministic, finite, current-tick only, no DP change, "
                    "no future labels, no selector mutation"
                ),
            },
            {
                "name": "lateral_heading_continuity_projection",
                "purpose": (
                    "Project each support trajectory onto the current route "
                    "corridor with bounded lateral acceleration, bounded "
                    "heading error, endpoint continuity, and road-border "
                    "screening before comfort evaluation."
                ),
                "evidence_target": (
                    "reduce command lateral, rollout lateral, lane invalid, "
                    "and road-border blockers"
                ),
                "contract": (
                    "uses current lane geometry and candidate-local rollout "
                    "features only; never edits DP output or online selection"
                ),
            },
            {
                "name": "red_timing_progress_guard",
                "purpose": (
                    "Build stop or creep support profiles that respect the "
                    "current red-light timing window while preserving a "
                    "bounded progress floor relative to candidate0."
                ),
                "evidence_target": (
                    "reduce red timing invalid and progress loss blockers "
                    "without relaxing progress acceptance"
                ),
                "contract": (
                    "all thresholds must be static-contract reviewed before "
                    "implementation; no replay execution is authorized"
                ),
            },
            {
                "name": "hard_progress_comfort_gate_passthrough",
                "purpose": (
                    "Keep the existing hard, progress, and comfort filters as "
                    "read-only gates for evidence; the generator must earn "
                    "support under those gates rather than weaken them."
                ),
                "evidence_target": (
                    "positive comfort-admissible snapshot support in a later "
                    "fixed-snapshot screen before any training discussion"
                ),
                "contract": (
                    "no candidate, score, selected-index, fallback, online "
                    "selector, or deployed atom schema mutation is authorized "
                    "in this design gate"
                ),
            },
        ],
        "descriptor_atom_contract": [
            {
                "name": "command_jerk_hinge",
                "contract": (
                    "nonnegative hinge descriptor max(0, command_jerk_delta - "
                    "budget), defined from current candidate commands only"
                ),
            },
            {
                "name": "rollout_jerk_hinge",
                "contract": (
                    "nonnegative hinge descriptor max(0, rollout_jerk_delta - "
                    "budget), candidate-local and finite at the current tick"
                ),
            },
            {
                "name": "lateral_error_signed_split",
                "contract": (
                    "signed lateral or heading errors must be represented as "
                    "two nonnegative hinge/signed-split channels before any "
                    "future atom proposal"
                ),
            },
            {
                "name": "progress_retention_hinge",
                "contract": (
                    "nonnegative progress-loss hinge, never an outcome label, "
                    "and affine if later included in a_k"
                ),
            },
            {
                "name": "lane_projection_residual_hinge",
                "contract": (
                    "nonnegative lane-projection residual hinge over current "
                    "route geometry; no future map or replay leakage"
                ),
            },
        ],
        "static_review_requirements": [
            "prove each proposed generator input is available at the current tick",
            "prove finite candidate count and deterministic candidate ordering",
            "prove candidate0 and default behavior preservation",
            "prove no mutation of DP weights, DP code, DP config, or DP invocation",
            "prove no candidate, score, selected-index, fallback, online selector, or deployed atom schema mutation in the design gate",
            "prove all descriptor values are nonnegative or legal hinge/signed-split channels",
            "prove any future scoring use preserves score_k(w)=a_k^T w and convex simplex/CVaR/L2 optimization",
            "prove formal seeds 11/12/13 remain frozen and unused",
            "prove no safety-benefit or CAMP-over-DP-Top-1 claim is made",
            "prove no DP-side classical Benders claim is made",
        ],
        "rejected_non_fixes": [
            {
                "name": "comfort_budget_relaxation",
                "reason": (
                    "The previous support profile already left comfort "
                    "support at zero; wider acceptance would not prove a "
                    "materially different generator."
                ),
            },
            {
                "name": "rerun_unchanged_generator",
                "reason": (
                    "The fixed-snapshot rerun is already negative and no new "
                    "screen execution is authorized in this gate."
                ),
            },
            {
                "name": "train_on_negative_support",
                "reason": (
                    "positive_support_evidence=False, replay_evidence_ready="
                    "False, and training_ready=False"
                ),
            },
            {
                "name": "selector_or_atom_promotion",
                "reason": (
                    "No online selector, deployed atom schema, or promotion "
                    "change is authorized before positive offline support."
                ),
            },
            {
                "name": "dp_side_change",
                "reason": (
                    "DP must remain a fixed black-box trajectory generator at "
                    f"{EXPECTED_DP_HEAD}."
                ),
            },
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized",
            "production implementation edits are not authorized",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "closed-loop replay is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "CAMP retraining and training execution are not authorized",
            "online selector promotion and atom promotion are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


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
    blocked = _dict(payload.get("blocked_actions"))
    comfort_rank = _list(attribution.get("comfort_blocker_ranking"))
    hard_rank = _list(attribution.get("hard_blocker_ranking"))
    comfort_names = tuple(
        item.get("name")
        for item in comfort_rank
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )
    hard_names = tuple(
        item.get("name")
        for item in hard_rank
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "hard_support_positive": _coalesce_bool(
            attribution.get("hard_support_positive"),
            decision.get("hard_support_positive"),
        ),
        "comfort_support_positive": _coalesce_bool(
            attribution.get("comfort_support_positive"),
            decision.get("comfort_support_positive"),
        ),
        "positive_support_evidence": _coalesce_bool(
            attribution.get("positive_support_evidence"),
            decision.get("positive_support_evidence"),
        ),
        "replay_evidence_ready": _coalesce_bool(
            attribution.get("replay_evidence_ready"),
            decision.get("replay_evidence_ready"),
        ),
        "training_ready": _coalesce_bool(
            attribution.get("training_ready"),
            decision.get("training_ready"),
        ),
        "materially_different_generator_design_plan_authorized": decision.get(
            "materially_different_generator_design_plan_authorized"
        ),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "comfort_support_gap": attribution.get("comfort_support_gap"),
        "candidate_coverage_rate": attribution.get("candidate_coverage_rate"),
        "top_comfort_blockers": comfort_names,
        "hard_context_blockers": hard_names,
        "blocked_action_conflicts": sorted(
            key
            for source in (decision, blocked)
            for key in BLOCKED_ACTIONS
            if source.get(key) is True
        ),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", artifact["exists"]),
        _check("failure_attribution_json_exists", artifact["json_exists"]),
        _check("failure_attribution_markdown_exists", artifact["markdown_exists"]),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "failure_attribution_markdown_records_title",
            "Failure Attribution" in artifact["markdown_text"],
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
            "audit_authorizes_materially_different_design",
            FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check("audit_records_primary_blocker", PRIMARY_BLOCKER_FAMILY in audit_text),
        _check("audit_records_comfort_gap", "comfort_support_gap=0.25" in audit_text),
        _check(
            "audit_records_zero_comfort_support",
            "comfort_support_positive=False" in audit_text,
        ),
        _check(
            "audit_records_no_positive_support",
            "positive_support_evidence=False" in audit_text,
        ),
        _check("audit_records_training_not_ready", "training_ready=False" in audit_text),
        _check(
            "audit_records_replay_not_ready",
            "replay_evidence_ready=False" in audit_text,
        ),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    comfort_blockers = set(source["top_comfort_blockers"])
    hard_blockers = set(source["hard_context_blockers"])
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
        _check(
            "failure_attribution_material_design_authorized",
            source["materially_different_generator_design_plan_authorized"] is True,
        ),
        _check(
            "failure_attribution_comfort_gap_positive",
            isinstance(source["comfort_support_gap"], (int, float))
            and source["comfort_support_gap"] > 0,
        ),
        _check(
            "failure_attribution_candidate_coverage_positive",
            isinstance(source["candidate_coverage_rate"], (int, float))
            and source["candidate_coverage_rate"] > 0,
        ),
        *[
            _check(f"failure_attribution_has_{name}", name in comfort_blockers)
            for name in TOP_COMFORT_BLOCKERS
        ],
        *[
            _check(f"failure_attribution_context_has_{name}", name in hard_blockers)
            for name in HARD_CONTEXT_BLOCKERS
        ],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    tracks = {item["name"] for item in plan["generator_tracks"]}
    descriptors = {item["name"] for item in plan["descriptor_atom_contract"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}
    return [
        _check(
            "plan_selection_type",
            plan["selection_type"]
            == "residual_comfort_remediation_followup_materially_different_generator_design_plan_only",
        ),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_target_residual_family", plan["target_failure"]["residual_family"] == RESIDUAL_FAMILY),
        _check("plan_has_jerk_stop_synthesis", "lane_station_jerk_limited_stop_synthesis" in tracks),
        _check("plan_has_lateral_projection", "lateral_heading_continuity_projection" in tracks),
        _check("plan_has_red_timing_guard", "red_timing_progress_guard" in tracks),
        _check("plan_has_gate_passthrough", "hard_progress_comfort_gate_passthrough" in tracks),
        _check("plan_has_command_jerk_descriptor", "command_jerk_hinge" in descriptors),
        _check("plan_has_rollout_jerk_descriptor", "rollout_jerk_hinge" in descriptors),
        _check("plan_has_lateral_signed_split", "lateral_error_signed_split" in descriptors),
        _check("plan_has_progress_descriptor", "progress_retention_hinge" in descriptors),
        _check("plan_has_lane_projection_descriptor", "lane_projection_residual_hinge" in descriptors),
        _check("plan_rejects_comfort_relaxation", "comfort_budget_relaxation" in rejected),
        _check("plan_rejects_unchanged_rerun", "rerun_unchanged_generator" in rejected),
        _check("plan_rejects_negative_training", "train_on_negative_support" in rejected),
        _check("plan_rejects_promotion", "selector_or_atom_promotion" in rejected),
        _check("plan_rejects_dp_change", "dp_side_change" in rejected),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate", "finite current-tick candidate" in text),
        _check("plan_mentions_candidate_local", "candidate-local" in text),
        _check("plan_mentions_not_budget_relaxation", "not another comfort-budget relaxation" in text),
        _check("plan_mentions_no_mutation", "no candidate, score, selected-index" in text),
        _check("plan_mentions_nonnegative_or_hinge", "nonnegative" in text and "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seed_freeze", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_mentions_camp_over_dp_blocked", "camp-over-dp-top-1" in text),
        _check("plan_mentions_benders_blocked", "classical benders" in text),
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
        "materially_different_generator_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
        "materially_different_generator_static_contract_review_authorized": passed,
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


def _coalesce_bool(*values: Any) -> Optional[bool]:
    for value in values:
        if isinstance(value, bool):
            return value
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
