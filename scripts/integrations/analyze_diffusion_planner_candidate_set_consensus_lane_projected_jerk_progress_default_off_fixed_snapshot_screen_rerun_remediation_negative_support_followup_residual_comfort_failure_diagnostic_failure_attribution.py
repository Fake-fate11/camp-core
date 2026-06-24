#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (  # noqa: E402
    READY_STATUS as DIAGNOSTICS_READY_STATUS,
    REQUIRED_TABLES,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_post_implementation_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as POST_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as POST_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_failure_attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_failure_attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_design_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DIAGNOSTICS_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostics_bff8f8b"
)
DEFAULT_POST_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_post_"
    "implementation_static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

DIAGNOSTICS_JSON = "residual_comfort_failure_diagnostics.json"
POST_REVIEW_JSON = "post_implementation_static_review.json"

COMFORT_PREFIX = "route_topology_comfort_blocked_"

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
            "Read-only attribution over residual comfort-failure diagnostic "
            "tables."
        )
    )
    parser.add_argument(
        "--diagnostics_root",
        type=Path,
        default=Path(DEFAULT_DIAGNOSTICS_ROOT),
    )
    parser.add_argument(
        "--post_review_root",
        type=Path,
        default=Path(DEFAULT_POST_REVIEW_ROOT),
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
        diagnostics_root=args.diagnostics_root,
        post_review_root=args.post_review_root,
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
    diagnostics_root: Path,
    post_review_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    diagnostics_artifact = _artifact_summary(diagnostics_root, DIAGNOSTICS_JSON)
    post_review_artifact = _artifact_summary(post_review_root, POST_REVIEW_JSON)
    audit_text = _read_text(audit_path)
    diagnostics = _diagnostics_summary(diagnostics_artifact["payload"])
    post_review = _post_review_summary(post_review_artifact["payload"])
    attribution = _failure_attribution(diagnostics_artifact["payload"])
    checks = [
        *_artifact_checks("diagnostics", diagnostics_artifact),
        *_artifact_checks("post_review", post_review_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_post_review_checks(post_review),
        *_diagnostics_checks(diagnostics),
        *_attribution_checks(attribution),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_failure_"
                "attribution_v1"
            ),
            "label": label,
            "role": "read-only attribution over residual comfort diagnostic tables",
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
                "This attribution reads only diagnostic and post-review "
                "artifacts plus audit text. It does not edit code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, recompute rewards or tracker proxies, define runtime "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, mutate "
                "the convex simplex/CVaR/L2 master, train CAMP, change online "
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
        "source_artifacts": {
            "diagnostics": _strip_payload(diagnostics_artifact),
            "post_review": _strip_payload(post_review_artifact),
        },
        "source_summary": {
            "diagnostics": diagnostics,
            "post_review": post_review,
        },
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Residual Comfort Diagnostic Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker: `{attribution['primary_blocker_family']}`",
        f"- Residual family: `{attribution['residual_failure_family']}`",
        "",
        "## Comfort Blocker Ranking",
        "",
    ]
    for item in attribution["comfort_blocker_ranking"]:
        lines.append(f"- `{item['name']}`: `{item['count']}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            attribution["interpretation"],
            "",
            "## Boundaries",
            "",
            "- remediation design planning only may follow",
            "- no candidate generation, screen rerun, replay, Full36, formal seeds, or training is authorized",
            "- no atom promotion, online selector promotion, safety claim, CAMP-over-DP claim, or DP modification is authorized",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path, filename: str) -> dict[str, Any]:
    path = root / filename
    return {
        "root": str(root),
        "path": str(path),
        "root_exists": root.is_dir(),
        "json_exists": path.is_file(),
        "json_sha256": _sha256(path),
        "payload": _read_json(path),
    }


def _diagnostics_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    tables = _dict(payload.get("diagnostic_tables"))
    boundary = _dict(tables.get("diagnostic_decision_boundary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "tables": sorted(tables.keys()),
        "primary_blocker_family": boundary.get("primary_blocker_family"),
        "hard_progress_survivor_rows": _int(boundary.get("hard_progress_survivor_rows")),
        "comfort_admissible_rows": _int(boundary.get("comfort_admissible_rows")),
        "hard_support_positive": bool(boundary.get("hard_support_positive")),
        "comfort_support_positive": bool(boundary.get("comfort_support_positive")),
        "positive_support_evidence": bool(boundary.get("positive_support_evidence")),
        "replay_evidence_ready": bool(boundary.get("replay_evidence_ready")),
        "training_ready": bool(boundary.get("training_ready")),
    }


def _post_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failure_attribution_authorized": bool(
            decision.get("diagnostic_failure_attribution_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _failure_attribution(payload: dict[str, Any]) -> dict[str, Any]:
    tables = _dict(payload.get("diagnostic_tables"))
    boundary = _dict(tables.get("diagnostic_decision_boundary"))
    counts = Counter()
    counts.update(_dict(_dict(tables.get("hard_progress_survivor_distribution")).get("comfort_blocker_counts")))
    for row in _list(tables.get("comfort_blocker_by_snapshot")):
        if isinstance(row, dict):
            counts.update(_dict(row.get("comfort_blocker_counts")))
    ranking = [
        {"name": name, "count": int(count)}
        for name, count in counts.most_common()
        if name.startswith(COMFORT_PREFIX) and int(count) > 0
    ]
    top = ranking[0]["name"] if ranking else None
    residual_family = _residual_family(top)
    return {
        "primary_blocker_family": boundary.get("primary_blocker_family"),
        "residual_failure_family": residual_family,
        "hard_progress_survivor_rows": _int(boundary.get("hard_progress_survivor_rows")),
        "comfort_admissible_rows": _int(boundary.get("comfort_admissible_rows")),
        "comfort_blocker_ranking": ranking,
        "top_comfort_blocker": top,
        "remediation_design_needed": True,
        "replay_evidence_ready": False,
        "training_ready": False,
        "interpretation": (
            "Hard/progress support is present, but the surviving rows remain "
            "comfort-inadmissible. The dominant residual family should be "
            "addressed by a remediation design plan before any replay or "
            "training can be considered."
        ),
    }


def _residual_family(top: Optional[str]) -> str:
    if top is None:
        return "comfort_support_zero_without_ranked_blocker"
    if "jerk" in top:
        return "jerk_dominated_comfort_gap_after_hard_progress_survival"
    if "lateral" in top:
        return "lateral_dominated_comfort_gap_after_hard_progress_survival"
    if "progress" in top:
        return "progress_retention_comfort_gap_after_hard_survival"
    return "mixed_comfort_gap_after_hard_progress_survival"


def _artifact_checks(name: str, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_root_exists", artifact["root_exists"]),
        _check(f"{name}_json_exists", artifact["json_exists"]),
        _check(f"{name}_json_parseable", bool(artifact["payload"])),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_post_review_complete", POST_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_failure_attribution", POST_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _post_review_checks(post_review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("post_review_status_complete", post_review["status"] == POST_REVIEW_READY_STATUS),
        _check("post_review_passed", post_review["passed"] is True),
        _check("post_review_failed_checks_empty", not post_review["failed_checks"]),
        _check("post_review_authorizes_this_gate", post_review["authorized_next_work"] == POST_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("post_review_failure_attribution_authorized", post_review["failure_attribution_authorized"] is True),
        _check("post_review_no_blocked_actions", not post_review["blocked_action_conflicts"]),
    ]


def _diagnostics_checks(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    tables = set(diagnostics["tables"])
    return [
        _check("diagnostics_status_complete", diagnostics["status"] == DIAGNOSTICS_READY_STATUS),
        _check("diagnostics_passed", diagnostics["passed"] is True),
        _check("diagnostics_failed_checks_empty", not diagnostics["failed_checks"]),
        *[_check(f"diagnostics_table_{name}", name in tables) for name in REQUIRED_TABLES],
        _check("diagnostics_primary_blocker", diagnostics["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("diagnostics_hard_progress_survivors_positive", diagnostics["hard_progress_survivor_rows"] > 0),
        _check("diagnostics_comfort_zero", diagnostics["comfort_admissible_rows"] == 0),
        _check("diagnostics_hard_positive", diagnostics["hard_support_positive"] is True),
        _check("diagnostics_comfort_absent", diagnostics["comfort_support_positive"] is False),
        _check("diagnostics_no_positive_support", diagnostics["positive_support_evidence"] is False),
        _check("diagnostics_replay_not_ready", diagnostics["replay_evidence_ready"] is False),
        _check("diagnostics_training_not_ready", diagnostics["training_ready"] is False),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("attribution_primary_blocker", attribution["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("attribution_survivors_positive", attribution["hard_progress_survivor_rows"] > 0),
        _check("attribution_comfort_zero", attribution["comfort_admissible_rows"] == 0),
        _check("attribution_has_ranked_blockers", bool(attribution["comfort_blocker_ranking"])),
        _check("attribution_selects_residual_family", attribution["residual_failure_family"].endswith("_after_hard_progress_survival")),
        _check("attribution_remediation_design_needed", attribution["remediation_design_needed"] is True),
        _check("attribution_replay_not_ready", attribution["replay_evidence_ready"] is False),
        _check("attribution_training_not_ready", attribution["training_ready"] is False),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_remediation_design_plan", decision["remediation_design_plan_authorized"] is True),
        _check("boundary_blocks_implementation", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "residual_comfort_failure_attribution_complete": passed,
        "remediation_design_plan_authorized": passed,
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
    return {key: value for key, value in artifact.items() if key != "payload"}


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
