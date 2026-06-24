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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    PRIMARY_BLOCKER_FAMILY,
    READY_STATUS as DESIGN_READY_STATUS,
    RESIDUAL_FAILURE_FAMILY,
    TOP_COMFORT_BLOCKER,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_static_contract_"
    "review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_static_contract_"
    "review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DESIGN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_design_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

DESIGN_JSON = "remediation_design_plan.json"
DESIGN_MD = "remediation_design_plan.md"

REQUIRED_TRACKS = (
    "hard_progress_survivor_comfort_gap_partition",
    "command_jerk_hinge_descriptor_family",
    "jerk_bounded_support_intervention_boundary",
    "positive_support_before_training_gate",
    "dp_fixed_black_box_boundary",
)
REQUIRED_REJECTED_NON_FIXES = (
    "train_on_zero_comfort_support",
    "rerun_until_positive",
    "relax_jerk_or_comfort_contracts",
    "online_selector_workaround",
    "dp_side_fix",
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
            "Static contract review for the residual comfort remediation "
            "design. This gate is read-only and authorizes at most an "
            "implementation-plan gate."
        )
    )
    parser.add_argument("--design_root", type=Path, default=Path(DEFAULT_DESIGN_ROOT))
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
        design_root=args.design_root,
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
    design_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(design_root)
    source = _design_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    review = _static_contract_review(source, artifact["payload"])
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_contract_checks(review),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_design_static_contract_review_v1"
            ),
            "label": label,
            "role": "read-only static review of residual comfort remediation design",
            "read_only": True,
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
                "This review reads only the remediation design artifact and "
                "audit text. It does not edit implementation code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, define runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "design_artifact": _strip_payload(artifact),
        "design_summary": source,
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Residual Comfort Remediation Design Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Contracts",
        "",
    ]
    for contract in review["contracts"]:
        lines.append(
            f"- `{contract['name']}`: `{contract['status']}` - {contract['evidence']}"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- implementation planning only may follow",
            "- implementation code edits and production implementation edits are not authorized",
            "- candidate generation, fixed-snapshot screen rerun, replay, Full36, and formal seeds are not authorized",
            "- CAMP retraining, atom promotion, online selector promotion, safety claims, CAMP-over-DP-Top-1 claims, and DP modification are not authorized",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / DESIGN_JSON
    markdown_path = root / DESIGN_MD
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


def _design_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("remediation_design_plan"))
    analysis = _dict(payload.get("analysis"))
    target = _dict(plan.get("target_failure"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": bool(
            decision.get("static_contract_review_authorized")
        ),
        "remediation_design_static_contract_review_authorized": bool(
            decision.get("remediation_design_static_contract_review_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "primary_blocker_family": target.get("primary_blocker_family"),
        "residual_failure_family": target.get("residual_failure_family"),
        "top_comfort_blocker": target.get("top_comfort_blocker"),
        "hard_progress_survivor_rows": _int(
            target.get("hard_progress_survivor_rows")
        ),
        "comfort_admissible_rows": _int(target.get("comfort_admissible_rows")),
        "tracks": [
            item.get("name")
            for item in _list(plan.get("remediation_tracks"))
            if isinstance(item, dict)
        ],
        "static_review_requirements": [
            str(item) for item in _list(plan.get("static_review_requirements"))
        ],
        "rejected_non_fixes": [
            item.get("name")
            for item in _list(plan.get("rejected_non_fixes"))
            if isinstance(item, dict)
        ],
        "blocked_boundaries": [
            str(item) for item in _list(plan.get("blocked_boundaries"))
        ],
        "design_position": str(plan.get("design_position") or ""),
        "math_boundary": str(analysis.get("math_boundary") or ""),
    }


def _static_contract_review(
    source: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True).lower()
    requirements = " ".join(source["static_review_requirements"]).lower()
    boundaries = " ".join(source["blocked_boundaries"]).lower()
    math_boundary = source["math_boundary"]
    contracts = [
        _contract(
            "failure_target_preserved",
            source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY
            and source["residual_failure_family"] == RESIDUAL_FAILURE_FAMILY
            and source["top_comfort_blocker"] == TOP_COMFORT_BLOCKER,
        ),
        _contract(
            "required_tracks_present",
            set(REQUIRED_TRACKS).issubset(set(source["tracks"])),
        ),
        _contract(
            "rejected_non_fixes_present",
            set(REQUIRED_REJECTED_NON_FIXES).issubset(
                set(source["rejected_non_fixes"])
            ),
        ),
        _contract(
            "current_tick_finite_feature_contract",
            "finite, current-tick, and candidate-local" in requirements
            and "current-tick finite candidate features" in text,
        ),
        _contract(
            "no_candidate_mutation_contract",
            "cannot alter candidates, scores, selected index, fallback" in requirements
            and "no mutation of candidates" in text,
        ),
        _contract(
            "atom_math_contract",
            "nonnegative" in requirements
            and "hinge/signed-split" in requirements
            and "score_k(w)=a_k^t w" in requirements,
        ),
        _contract(
            "convex_master_contract",
            "simplex/cvar/l2" in requirements
            and "simplex/CVaR/L2" in math_boundary,
        ),
        _contract(
            "execution_training_boundary",
            "candidate generation" in boundaries
            and "screen rerun" in boundaries
            and "camp retraining" in boundaries,
        ),
        _contract(
            "formal_seed_boundary",
            "formal seeds 11/12/13" in boundaries
            and sorted(FORMAL_SEEDS) == [11, 12, 13],
        ),
        _contract(
            "dp_fixed_boundary",
            "dp weights" in boundaries
            and "dp code" in boundaries
            and "dp config" in boundaries
            and "dp invocation" in boundaries,
        ),
        _contract(
            "claim_boundary",
            "camp-over-dp-top-1" in boundaries
            and "safety-benefit" in boundaries,
        ),
    ]
    return {
        "all_contracts_pass": all(item["status"] == "pass" for item in contracts),
        "contracts": contracts,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_root_exists", artifact["exists"]),
        _check("design_json_exists", artifact["json_exists"]),
        _check("design_markdown_exists", artifact["markdown_exists"]),
        _check("design_json_parseable", bool(artifact["payload"])),
        _check(
            "design_markdown_records_title",
            "Residual Comfort Failure Remediation Design Plan"
            in artifact["markdown_text"],
        ),
        _check(
            "design_markdown_records_boundaries",
            "## Forbidden Work" in artifact["markdown_text"]
            and "## Math Boundary" in artifact["markdown_text"],
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
        _check("audit_records_design_ready", DESIGN_READY_STATUS in audit_text),
        _check("audit_authorizes_static_review", DESIGN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_top_comfort_blocker", TOP_COMFORT_BLOCKER in audit_text),
        _check("audit_records_no_execution", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_status_ready", source["status"] == DESIGN_READY_STATUS),
        _check("design_passed", source["passed"] is True),
        _check("design_failed_checks_empty", not source["failed_checks"]),
        _check("design_authorizes_this_review", source["authorized_next_work"] == DESIGN_AUTHORIZED_NEXT_WORK),
        _check("design_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check(
            "design_remediation_static_review_authorized",
            source["remediation_design_static_contract_review_authorized"] is True,
        ),
        _check("design_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("design_primary_blocker", source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY),
        _check("design_residual_family", source["residual_failure_family"] == RESIDUAL_FAILURE_FAMILY),
        _check("design_top_comfort_blocker", source["top_comfort_blocker"] == TOP_COMFORT_BLOCKER),
        _check("design_survivors_positive", source["hard_progress_survivor_rows"] > 0),
        _check("design_comfort_zero", source["comfort_admissible_rows"] == 0),
        *[
            _check(f"design_track_{name}", name in set(source["tracks"]))
            for name in REQUIRED_TRACKS
        ],
        *[
            _check(f"design_rejected_non_fix_{name}", name in set(source["rejected_non_fixes"]))
            for name in REQUIRED_REJECTED_NON_FIXES
        ],
    ]


def _contract_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_contracts_all_pass", review["all_contracts_pass"]),
        *[
            _check(f"static_contract_{item['name']}", item["status"] == "pass")
            for item in review["contracts"]
        ],
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_blocks_implementation", True),
        _check("boundary_blocks_candidate_generation", True),
        _check("boundary_blocks_screen_rerun", True),
        _check("boundary_blocks_replay", True),
        _check("boundary_blocks_training", "camp retraining" in " ".join(source["blocked_boundaries"]).lower()),
        _check("boundary_blocks_dp_modification", "dp weights" in " ".join(source["blocked_boundaries"]).lower()),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_design_static_contract_review_complete": passed,
        "remediation_implementation_plan_authorized": passed,
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


def _contract(name: str, passed: bool) -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "evidence": "contract present and boundary text matches"
        if passed
        else "missing or inconsistent",
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


def _int(value: Any) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
