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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
    REQUIRED_FAILURE_MODES,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DESIGN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "design_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

DESIGN_JSON = "remediation_design_plan.json"
DESIGN_MD = "remediation_design_plan.md"

REQUIRED_REMEDIATION_AXES = (
    "red_stop_distance_window_coverage_partition",
    "comfort_first_longitudinal_retiming",
    "comfort_blocker_split_diagnostics",
    "latency_bounded_candidate_budget",
)

REQUIRED_REJECTED_NON_FIXES = (
    "comfort_gate_relaxation",
    "dp_side_fix",
    "training_or_online_selector_tuning",
    "replay_or_formal_seed_expansion",
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
            "Read-only static contract review for the default-off "
            "fixed-snapshot screen rerun remediation design plan. This "
            "authorizes only a later implementation-plan gate."
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
    design = _design_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    review = _static_contract_review(design, artifact["markdown_text"])
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_artifact_checks(artifact),
        *_audit_checks(audit_text),
        *_design_authorization_checks(design),
        *_review_checks(review),
        *_boundary_checks(review),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_static_"
                "contract_review_v1"
            ),
            "label": label,
            "role": "read-only static contract review before remediation implementation plan",
            "read_only": True,
            "source_inspection_only": True,
            "implementation_code_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This review reads only the remediation design-plan artifact "
                "and audit authorization. It does not edit source code, "
                "implement a generator, create candidates, rerun the screen, "
                "run DP, run replay, recompute outcomes, define runtime atoms, "
                "choose lambda online, alter score_k(w)=a_k^T w, mutate the "
                "convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, modify DP weights or code, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "design_artifact": _strip_payload(artifact),
        "design_summary": design,
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Static Contracts",
        "",
    ]
    for item in review["contracts"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - status: `{item['status']}`")
        lines.append(f"  - evidence: `{item['evidence']}`")
        lines.append(f"  - allowed next step: {item['allowed_next_step']}")
    lines.extend(["", "## Rejection Rules", ""])
    for item in review["rejection_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in review["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_fixed_snapshot_screen_rerun_remediation_"
                "implementation_plan_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _static_contract_review(
    design: dict[str, Any],
    markdown_text: str,
) -> dict[str, Any]:
    axes = set(design["remediation_axis_names"])
    rejected = set(design["rejected_non_fix_names"])
    requirements_text = "\n".join(design["static_review_requirements"])
    boundary_text = "\n".join(design["blocked_boundaries"])
    contracts = [
        _contract(
            "source_failure_mode_coverage_contract",
            set(REQUIRED_FAILURE_MODES) <= set(design["source_failure_modes"])
            and set(REQUIRED_REMEDIATION_AXES) <= axes,
            "all four attributed failure modes are covered by named remediation axes",
        ),
        _contract(
            "default_off_selection_neutral_contract",
            design["default_off_contract"].get("enabled_by_default") is False
            and design["default_off_contract"].get("candidate0_preserved") is True
            and design["default_off_contract"].get("selection_effect_when_disabled") is False,
            "default-off plan preserves candidate-0 and disabled selector behavior",
        ),
        _contract(
            "current_tick_feature_contract",
            "finite current-tick" in requirements_text
            and "future outcomes" in markdown_text,
            "inputs are constrained to finite current-tick features with no future outcomes",
        ),
        _contract(
            "dp_black_box_fixed_contract",
            design["default_off_contract"].get("dp_code_or_weight_change_allowed") is False
            and "DP code" in requirements_text
            and "DP weights" in boundary_text,
            "DP code, weights, configs, and invocation remain fixed",
        ),
        _contract(
            "rejected_non_fix_contract",
            set(REQUIRED_REJECTED_NON_FIXES) <= rejected,
            "non-fixes reject comfort relaxation, DP changes, training, selector tuning, replay, and formal seed expansion",
        ),
        _contract(
            "math_boundary_contract",
            "hinge/signed-split" in requirements_text
            and "score_k(w)=a_k^T w" in requirements_text
            and "simplex/CVaR/L2" in requirements_text,
            "future atom constraints preserve linear scores and convex master structure",
        ),
        _contract(
            "execution_block_contract",
            "implementation edits are not authorized" in boundary_text
            and "candidate generation execution is not authorized" in boundary_text
            and "fixed-snapshot screen rerun is not authorized" in boundary_text
            and "formal seeds 11/12/13 remain frozen" in boundary_text
            and "CAMP retraining" in boundary_text,
            "implementation, candidate generation, rerun, formal seeds, and training remain blocked",
        ),
    ]
    return {
        "contracts": contracts,
        "all_contracts_pass": all(item["status"] == "pass" for item in contracts),
        "rejection_rules": [
            "reject if design no longer covers all four attributed failure modes",
            "reject if default-off or candidate-0 preservation is weakened",
            "reject if any future information or non-current-tick feature is required",
            "reject if DP code, weights, configs, or invocation may change",
            "reject if implementation, candidate generation, screen rerun, replay, formal seeds, training, promotion, safety claims, or CAMP-over-DP-Top-1 claims become authorized",
            "reject if future atom math cannot preserve nonnegativity or legal hinge/signed-split score linearity",
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
    payload_path = root / DESIGN_JSON
    markdown_path = root / DESIGN_MD
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


def _design_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    design = _dict(payload.get("remediation_design"))
    default_off = _dict(design.get("default_off_contract"))
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
        "source_failure_modes": _list(design.get("source_failure_modes")),
        "remediation_axis_names": [
            str(item.get("name")) for item in _list(design.get("remediation_axes"))
        ],
        "rejected_non_fix_names": [
            str(item.get("name")) for item in _list(design.get("rejected_non_fixes"))
        ],
        "static_review_requirements": [
            str(item) for item in _list(design.get("static_review_requirements"))
        ],
        "blocked_boundaries": [
            str(item) for item in _list(design.get("blocked_boundaries"))
        ],
        "default_off_contract": default_off,
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
        _check("design_root_exists", artifact["exists"]),
        _check("design_json_exists", artifact["json_exists"]),
        _check("design_markdown_exists", artifact["markdown_exists"]),
        _check("design_json_parseable", bool(artifact["payload"])),
        _check("design_markdown_records_static_contracts", "Static Review Requirements" in artifact["markdown_text"]),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_exists", bool(audit_text)),
        _check("audit_authorizes_static_contract_review", DESIGN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_design_ready", DESIGN_READY_STATUS in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _design_authorization_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_status_ready", design["status"] == DESIGN_READY_STATUS),
        _check("design_passed", design["passed"] is True),
        _check("design_failed_checks_empty", not design["failed_checks"]),
        _check(
            "design_authorizes_this_review",
            design["authorized_next_work"] == DESIGN_AUTHORIZED_NEXT_WORK,
        ),
        _check(
            "design_static_review_authorized",
            design["static_contract_review_authorized"] is True,
        ),
        _check("design_no_blocked_actions", not design["blocked_action_conflicts"]),
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *[
            _check(f"contract_{item['name']}_present", item["status"] == "pass")
            for item in review["contracts"]
        ],
        _check("review_all_contracts_pass", review["all_contracts_pass"]),
    ]


def _boundary_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    text = "\n".join(review["blocked_boundaries"])
    return [
        _check("boundary_blocks_implementation", "implementation edits are not authorized" in text),
        _check("boundary_blocks_candidate_generation", "candidate generation execution is not authorized" in text),
        _check("boundary_blocks_screen_rerun", "fixed-snapshot screen rerun is not authorized" in text),
        _check("boundary_blocks_formal_seeds", "formal seeds 11/12/13 remain frozen" in text),
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
        "implementation_plan_authorized": passed,
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


def _contract(
    name: str,
    passed: bool,
    evidence: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "allowed_next_step": "implementation-plan gate only; no production edit",
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


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
