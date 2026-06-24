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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as ATTRIBUTION_READY_STATUS,
    SCREEN_REJECT_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


GATE_NAME = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_design_plan_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_failure_"
    "attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

ATTRIBUTION_JSON = "failure_attribution.json"
ATTRIBUTION_MD = "failure_attribution.md"

REQUIRED_FAILURE_MODES = (
    "red_stop_distance_window_zero_candidate_partition",
    "comfort_admissible_support_absent",
    "comfort_blockers_dominate_generated_rows",
    "latency_budget_exceeded",
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
    "safety_benefit_evidence",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only remediation design after the default-off product-code "
            "fixed-snapshot screen rerun failure attribution. This does not "
            "edit production code, generate candidates, rerun the screen, run "
            "replay, train CAMP, or modify DP."
        )
    )
    parser.add_argument(
        "--attribution_root",
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
        attribution_root=args.attribution_root,
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
    attribution_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(attribution_root)
    attribution = _attribution_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _remediation_design(attribution)
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_artifact_checks(artifact),
        *_audit_checks(audit_text),
        *_attribution_checks(attribution),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_design_v1"
            ),
            "gate": GATE_NAME,
            "label": label,
            "role": "plan-only remediation design after fixed-snapshot support rejection",
            "plan_only": True,
            "implementation_code_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This gate reads only the completed fixed-snapshot failure "
                "attribution and repo audit authorization, then writes a "
                "remediation design plan. It does not edit production code, "
                "generate candidates, rerun the screen, run replay, use "
                "formal seeds, define or promote runtime atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition. Any future atom must prove "
                "nonnegativity or use a legal hinge/signed-split form while "
                "preserving linear score structure."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "source_artifact": _strip_payload(artifact),
        "source_attribution": attribution,
        "remediation_design": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    attribution = report["source_attribution"]
    plan = report["remediation_design"]
    lines = [
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Static contract review authorized: "
            f"`{decision['static_contract_review_authorized']}`"
        ),
        "",
        "## Source Attribution",
        "",
        f"- Screen status: `{attribution['screen_status']}`",
        f"- Snapshots: `{attribution['snapshots']}`",
        f"- Generated candidate rows: `{attribution['generated_candidate_rows']}`",
        (
            "- Comfort-admissible lower-red rows: "
            f"`{attribution['comfort_admissible_lower_red_rows']}`"
        ),
        "",
        "## Failure Modes",
        "",
    ]
    for mode in attribution["primary_failure_modes"]:
        lines.append(f"- `{mode}`")
    lines.extend(["", "## Design Thesis", "", plan["design_thesis"], ""])
    lines.extend(["## Remediation Axes", ""])
    for item in plan["remediation_axes"]:
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
    return "\n".join(lines) + "\n"


def _remediation_design(attribution: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "default_off_fixed_snapshot_screen_rerun_remediation_design_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "source_failure_modes": list(attribution["primary_failure_modes"]),
        "design_thesis": (
            "The failed candidate construction should not be rescued by "
            "relaxing comfort gates, changing DP, or training CAMP. The next "
            "admissible path is a default-off, deterministic, current-tick "
            "candidate-support remediation that targets coverage, comfort, "
            "and latency before any future fixed-snapshot rerun is planned."
        ),
        "remediation_axes": [
            {
                "name": "red_stop_distance_window_coverage_partition",
                "covers_failure_mode": "red_stop_distance_window_zero_candidate_partition",
                "contract": (
                    "replace the hard zero-candidate partition with a bounded "
                    "current-tick red-stop support partition that records why "
                    "each snapshot is eligible or ineligible without using "
                    "future outcomes"
                ),
            },
            {
                "name": "comfort_first_longitudinal_retiming",
                "covers_failure_mode": "comfort_admissible_support_absent",
                "contract": (
                    "design jerk-limited stop-support trajectory candidates "
                    "from current ego state, lane station, red-stop geometry, "
                    "and DP candidate features before existing hard/progress/"
                    "comfort checks evaluate them"
                ),
            },
            {
                "name": "comfort_blocker_split_diagnostics",
                "covers_failure_mode": "comfort_blockers_dominate_generated_rows",
                "contract": (
                    "separate command jerk, rollout jerk, lateral rollout, "
                    "command lateral, and progress-loss blockers so future "
                    "implementation tests can pin each rejection path"
                ),
            },
            {
                "name": "latency_bounded_candidate_budget",
                "covers_failure_mode": "latency_budget_exceeded",
                "contract": (
                    "cap the number of additional candidates and require a "
                    "deterministic bailout path that preserves candidate-0 "
                    "and selector behavior when disabled"
                ),
            },
        ],
        "default_off_contract": {
            "enabled_by_default": False,
            "candidate0_preserved": True,
            "selection_effect_when_disabled": False,
            "future_outcome_leakage_allowed": False,
            "dp_code_or_weight_change_allowed": False,
            "formal_seed_use_allowed": False,
            "training_allowed": False,
        },
        "rejected_non_fixes": [
            {
                "name": "comfort_gate_relaxation",
                "reason": "would weaken the existing admissibility contract instead of constructing admissible support",
            },
            {
                "name": "dp_side_fix",
                "reason": "DP is fixed black-box trajectory generation at the pinned commit",
            },
            {
                "name": "training_or_online_selector_tuning",
                "reason": "the present evidence is support insufficiency, not learnable selector superiority",
            },
            {
                "name": "replay_or_formal_seed_expansion",
                "reason": "the gate is still pre-replay and formal seeds 11/12/13 remain frozen",
            },
        ],
        "static_review_requirements": [
            "prove the plan remains default-off and selection-neutral before implementation",
            "prove all proposed inputs are finite current-tick candidate, lane, route, and traffic-light features",
            "prove candidate-0 and deployed DP Top-1 behavior are unchanged when disabled",
            "prove no DP code, weights, configs, or invocation contract are modified",
            "prove no replay, Full36, formal seed, training, atom promotion, safety claim, or CAMP-over-DP-Top-1 claim is authorized",
            "prove any future atom proposal is nonnegative or legally hinge/signed-split while preserving score_k(w)=a_k^T w and convex simplex/CVaR/L2 master structure",
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "replay, Full36, and formal seeds 11/12/13 remain frozen",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
            "DP weights, DP code, DP configs, and DP invocation must remain fixed",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / ATTRIBUTION_JSON
    markdown_path = root / ATTRIBUTION_MD
    payload = _read_json(payload_path)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": payload,
        "markdown_text": _read_text(markdown_path),
    }


def _attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    source = _dict(payload.get("source_summary"))
    attribution = _dict(payload.get("read_only_attribution"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "screen_status": source.get("status"),
        "snapshots": _int(source.get("snapshots")),
        "generated_candidate_rows": _int(source.get("generated_candidate_rows")),
        "comfort_admissible_lower_red_rows": _int(
            source.get("lower_union_red_comfort_admissible_rows")
        ),
        "primary_failure_modes": _list(attribution.get("primary_failure_modes")),
        "zero_candidate_reasons": _dict(attribution.get("zero_candidate_reasons")),
        "comfort_blocker_counts": _dict(attribution.get("comfort_blocker_counts")),
        "recommended_design_focus": _list(attribution.get("recommended_design_focus")),
    }


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_equals_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("attribution_root_exists", artifact["exists"]),
        _check("attribution_json_exists", artifact["json_exists"]),
        _check("attribution_markdown_exists", artifact["markdown_exists"]),
        _check("attribution_json_parseable", bool(artifact["payload"])),
        _check("attribution_markdown_records_boundaries", "Boundaries" in artifact["markdown_text"]),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_exists", bool(audit_text)),
        _check("audit_authorizes_this_design_gate", GATE_NAME in audit_text),
        _check("audit_records_prior_attribution_complete", ATTRIBUTION_READY_STATUS in audit_text),
        _check("audit_does_not_authorize_training", "training_execution_authorized=False" in audit_text),
        _check("audit_does_not_authorize_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    modes = set(str(mode) for mode in attribution["primary_failure_modes"])
    return [
        _check("attribution_status_ready", attribution["status"] == ATTRIBUTION_READY_STATUS),
        _check("attribution_passed", attribution["passed"] is True),
        _check("attribution_failed_checks_empty", not attribution["failed_checks"]),
        _check(
            "attribution_authorizes_this_design_gate",
            attribution["authorized_next_work"] == ATTRIBUTION_AUTHORIZED_NEXT_WORK == GATE_NAME,
        ),
        _check("attribution_no_blocked_actions", not attribution["blocked_action_conflicts"]),
        _check("attribution_screen_rejected", attribution["screen_status"] == SCREEN_REJECT_STATUS),
        _check("attribution_expected_snapshot_count", attribution["snapshots"] == 57),
        _check("attribution_generated_rows_positive", attribution["generated_candidate_rows"] > 0),
        _check(
            "attribution_no_comfort_admissible_lower_red_rows",
            attribution["comfort_admissible_lower_red_rows"] == 0,
        ),
        *[
            _check(f"attribution_failure_mode_{mode}", mode in modes)
            for mode in REQUIRED_FAILURE_MODES
        ],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    axes = {item["name"]: item for item in plan["remediation_axes"]}
    covered_modes = {
        item["covers_failure_mode"] for item in plan["remediation_axes"]
    }
    return [
        _check("plan_selected_next_work", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check(
            "plan_selection_type_plan_only",
            plan["selection_type"].endswith("_design_plan_only"),
        ),
        _check("plan_covers_all_failure_modes", set(REQUIRED_FAILURE_MODES) <= covered_modes),
        _check("plan_has_red_stop_axis", "red_stop_distance_window_coverage_partition" in axes),
        _check("plan_has_comfort_axis", "comfort_first_longitudinal_retiming" in axes),
        _check("plan_has_latency_axis", "latency_bounded_candidate_budget" in axes),
        _check(
            "plan_default_off",
            plan["default_off_contract"]["enabled_by_default"] is False,
        ),
        _check(
            "plan_preserves_candidate0",
            plan["default_off_contract"]["candidate0_preserved"] is True,
        ),
        _check(
            "plan_blocks_dp_change",
            plan["default_off_contract"]["dp_code_or_weight_change_allowed"] is False,
        ),
        _check(
            "plan_blocks_training",
            plan["default_off_contract"]["training_allowed"] is False,
        ),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = "\n".join(plan["blocked_boundaries"])
    return [
        _check("boundary_blocks_implementation", "implementation edits are not authorized" in text),
        _check("boundary_blocks_screen_rerun", "fixed-snapshot screen rerun is not authorized" in text),
        _check("boundary_blocks_formal_seeds", "formal seeds 11/12/13 remain frozen" in text),
        _check("boundary_blocks_training", "CAMP retraining" in text),
        _check("boundary_blocks_dp_modification", "DP weights" in text),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
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


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown_text"}
    }


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
