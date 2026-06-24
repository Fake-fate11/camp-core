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
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DESIGN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_design_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

DESIGN_JSON = "design_plan.json"
DESIGN_MD = "design_plan.md"

REQUIRED_COMPONENTS = (
    "coverage_first_fail_closed_partition",
    "hard_feasibility_support_floor",
    "comfort_feasibility_after_hard_progress",
    "nonformal_screen_only_readiness",
)
REQUIRED_STATIC_CONTRACTS = (
    "negative_support_evidence_is_consumed_without_safety_claim",
    "followup_components_are_default_off_and_current_tick_only",
    "coverage_component_addresses_fail_closed_snapshots",
    "comfort_component_addresses_hard_progress_feasible_regressions",
    "hard_feasibility_component_addresses_red_lane_road_kinematic_counts",
    "no_execution_or_training_authorization_leaks",
    "affine_score_and_convex_master_boundary_preserved",
)
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
            "Static contract review for the negative-support follow-up design."
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
    contracts = _contract_review(source, artifact["payload"])
    audit_text = _read_text(audit_path)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_contract_checks(contracts),
        *_boundary_checks(artifact["payload"]),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_static_contract_review_v1"
            ),
            "label": label,
            "role": "read-only static contract review of follow-up design",
            "read_only": True,
            "implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This review reads only the accepted design plan and audit. It "
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
        "design_artifact": _strip_payload(artifact),
        "design_summary": source,
        "static_contract_review": contracts,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Negative-Support Follow-Up Static Contract Review",
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
            "- no production implementation edit is authorized",
            "- no candidate generation, replay, Full36, formal seeds, or training is authorized",
            "- no atom promotion, online selector promotion, safety claim, or DP modification is authorized",
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
    plan = _dict(payload.get("design_plan"))
    analysis = _dict(payload.get("analysis"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": bool(
            decision.get("static_contract_review_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "components": [
            item.get("name") for item in _list(plan.get("components")) if isinstance(item, dict)
        ],
        "required_static_contracts": _list(plan.get("required_static_contracts")),
        "forbidden_actions": _list(plan.get("forbidden_actions")),
        "math_boundary": str(analysis.get("math_boundary") or ""),
    }


def _contract_review(source: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    components = set(source["components"])
    contracts = set(source["required_static_contracts"])
    forbidden = "\n".join(str(item) for item in source["forbidden_actions"])
    math_boundary = source["math_boundary"]
    contract_items = [
        _contract(
            "negative_support_evidence_is_consumed_without_safety_claim",
            "negative_support_evidence_is_consumed_without_safety_claim" in contracts
            and "safety-benefit" in forbidden,
        ),
        _contract(
            "followup_components_are_default_off_and_current_tick_only",
            "followup_components_are_default_off_and_current_tick_only" in contracts
            and "current-tick" in json.dumps(payload, sort_keys=True),
        ),
        _contract(
            "coverage_component_addresses_fail_closed_snapshots",
            "coverage_first_fail_closed_partition" in components
            and "fail_closed" in json.dumps(payload, sort_keys=True),
        ),
        _contract(
            "comfort_component_addresses_hard_progress_feasible_regressions",
            "comfort_feasibility_after_hard_progress" in components
            and "hard-progress-feasible" in json.dumps(payload, sort_keys=True),
        ),
        _contract(
            "hard_feasibility_component_addresses_red_lane_road_kinematic_counts",
            "hard_feasibility_support_floor" in components
            and "dp_red_light" in json.dumps(payload, sort_keys=True)
            and "dp_lane_crossing" in json.dumps(payload, sort_keys=True),
        ),
        _contract(
            "no_execution_or_training_authorization_leaks",
            "no_execution_or_training_authorization_leaks" in contracts
            and "candidate generation" in forbidden
            and "CAMP retraining" in forbidden,
        ),
        _contract(
            "affine_score_and_convex_master_boundary_preserved",
            "affine_score_and_convex_master_boundary_preserved" in contracts
            and "score_k(w)=a_k^T w" in math_boundary
            and "simplex/CVaR/L2" in math_boundary,
        ),
    ]
    return {
        "all_contracts_pass": all(item["status"] == "pass" for item in contract_items),
        "contracts": contract_items,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_root_exists", artifact["exists"]),
        _check("design_json_exists", artifact["json_exists"]),
        _check("design_markdown_exists", artifact["markdown_exists"]),
        _check("design_json_parseable", bool(artifact["payload"])),
        _check("design_markdown_records_next_gate", "## Next Gate" in artifact["markdown_text"]),
        _check("design_markdown_records_boundaries", "## Boundaries" in artifact["markdown_text"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_authorizes_static_review", DESIGN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_required_contracts", "Required static contracts" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_status_ready", source["status"] == DESIGN_READY_STATUS),
        _check("design_passed", source["passed"] is True),
        _check("design_failed_checks_empty", not source["failed_checks"]),
        _check("design_authorizes_this_review", source["authorized_next_work"] == DESIGN_AUTHORIZED_NEXT_WORK),
        _check("design_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check("design_no_blocked_actions", not source["blocked_action_conflicts"]),
        *[
            _check(f"design_component_{name}", name in set(source["components"]))
            for name in REQUIRED_COMPONENTS
        ],
        *[
            _check(f"design_contract_{name}", name in set(source["required_static_contracts"]))
            for name in REQUIRED_STATIC_CONTRACTS
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


def _boundary_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    return [
        _check("boundary_no_production_edit", not decision.get("production_implementation_edit_authorized")),
        _check("boundary_no_execution", not decision.get("candidate_generation_execution_authorized")),
        _check("boundary_no_training", not decision.get("training_execution_authorized")),
        _check("boundary_no_dp_modification", not decision.get("dp_modification_authorized")),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_plan_authorized": passed,
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
        "evidence": "contract present and boundary text matches" if passed else "missing or inconsistent",
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
