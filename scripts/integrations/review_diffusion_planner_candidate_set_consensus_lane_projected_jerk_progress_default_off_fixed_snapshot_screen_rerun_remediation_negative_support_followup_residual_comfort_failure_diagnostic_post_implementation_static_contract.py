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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DIAGNOSTICS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DIAGNOSTICS_READY_STATUS,
    REQUIRED_TABLES,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_post_implementation_static_contract_"
    "review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_post_implementation_static_contract_"
    "review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_failure_attribution_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_DIAGNOSTICS_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostics_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_SOURCE_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / (
        "analyze_diffusion_planner_candidate_set_consensus_lane_projected_"
        "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
        "negative_support_followup_residual_comfort_failure_diagnostics.py"
    )
)
DEFAULT_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / (
        "test_diffusion_planner_candidate_set_consensus_lane_projected_"
        "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
        "negative_support_followup_residual_comfort_failure_diagnostics.py"
    )
)

DIAGNOSTICS_JSON = "residual_comfort_failure_diagnostics.json"
DIAGNOSTICS_MD = "residual_comfort_failure_diagnostics.md"

REQUIRED_SOURCE_TOKENS = (
    "reward_recompute\": False",
    "tracker_recompute\": False",
    "candidate_reconstruction\": False",
    "does not import DP",
    "score_k(w)=a_k^T w",
    "simplex/CVaR/L2",
)
REQUIRED_TEST_NAMES = (
    "test_residual_comfort_failure_diagnostics_reads_existing_artifacts_only",
    "test_residual_comfort_failure_diagnostics_emits_required_tables",
    "test_residual_comfort_failure_diagnostics_rejects_missing_artifacts",
    "test_residual_comfort_failure_diagnostics_blocks_execution_flags",
    "test_residual_comfort_failure_diagnostics_preserves_math_boundary",
    "test_residual_comfort_failure_diagnostics_cli_writes_outputs",
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
            "Read-only post-implementation static review for residual comfort "
            "diagnostics."
        )
    )
    parser.add_argument(
        "--diagnostics_root",
        type=Path,
        default=Path(DEFAULT_DIAGNOSTICS_ROOT),
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--test_path", type=Path, default=DEFAULT_TEST_PATH)
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
        audit_path=args.audit_path,
        source_path=args.source_path,
        test_path=args.test_path,
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
    audit_path: Path,
    source_path: Path,
    test_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(diagnostics_root)
    audit_text = _read_text(audit_path)
    source_text = _read_text(source_path)
    test_text = _read_text(test_path)
    summary = _diagnostics_summary(artifact["payload"])
    source = _source_contract(source_path, source_text)
    tests = _test_contract(test_path, test_text)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_diagnostics_checks(summary),
        *_source_contract_checks(source),
        *_test_contract_checks(tests),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_post_"
                "implementation_static_review_v1"
            ),
            "label": label,
            "role": "read-only static review after residual comfort diagnostics",
            "read_only": True,
            "source_inspection_only": True,
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
                "This review reads only diagnostic artifacts, source text, test "
                "text, and audit authorization. It does not edit source code, "
                "create candidates, rerun the screen, run DP, run replay, use "
                "formal seeds, recompute rewards or tracker proxies, define "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, or claim a "
                "DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "diagnostics_artifact": _strip_payload(artifact),
        "diagnostics_summary": summary,
        "source_contract": source,
        "test_contract": tests,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["diagnostics_summary"]
    lines = [
        "# Residual Comfort Diagnostic Post-Implementation Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker: `{summary['primary_blocker_family']}`",
        f"- Hard/progress survivor rows: `{summary['hard_progress_survivor_rows']}`",
        f"- Comfort-admissible rows: `{summary['comfort_admissible_rows']}`",
        "",
        "## Tables",
        "",
    ]
    for name in summary["diagnostic_tables"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Source Contracts", ""])
    for name, passed in report["source_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Boundaries", ""])
    for item in (
        "failure attribution only may follow",
        "no candidate generation, screen rerun, replay, Full36, formal seeds, or training is authorized",
        "no atom promotion, online selector promotion, safety claim, CAMP-over-DP claim, or DP modification is authorized",
    ):
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / DIAGNOSTICS_JSON
    markdown_path = root / DIAGNOSTICS_MD
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


def _diagnostics_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    tables = _dict(payload.get("diagnostic_tables"))
    boundary = _dict(tables.get("diagnostic_decision_boundary"))
    source = _dict(payload.get("source_summary"))
    screen = _dict(source.get("screen"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "post_review_authorized": bool(
            decision.get("post_implementation_static_contract_review_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "read_only": bool(analysis.get("read_only")),
        "production_implementation_edit": bool(
            analysis.get("production_implementation_edit")
        ),
        "candidate_generation_execution": bool(
            analysis.get("candidate_generation_execution")
        ),
        "fixed_snapshot_screen_rerun_execution": bool(
            analysis.get("fixed_snapshot_screen_rerun_execution")
        ),
        "diffusion_planner_execution": bool(analysis.get("diffusion_planner_execution")),
        "diffusion_planner_modification": bool(
            analysis.get("diffusion_planner_modification")
        ),
        "reward_recompute": bool(analysis.get("reward_recompute")),
        "tracker_recompute": bool(analysis.get("tracker_recompute")),
        "candidate_reconstruction": bool(analysis.get("candidate_reconstruction")),
        "training": bool(analysis.get("training")),
        "diagnostic_tables": sorted(tables.keys()),
        "primary_blocker_family": boundary.get("primary_blocker_family"),
        "hard_progress_survivor_rows": _int(boundary.get("hard_progress_survivor_rows")),
        "comfort_admissible_rows": _int(boundary.get("comfort_admissible_rows")),
        "hard_support_positive": bool(boundary.get("hard_support_positive")),
        "comfort_support_positive": bool(boundary.get("comfort_support_positive")),
        "positive_support_evidence": bool(boundary.get("positive_support_evidence")),
        "replay_evidence_ready": bool(boundary.get("replay_evidence_ready")),
        "training_ready": bool(boundary.get("training_ready")),
        "generated_candidate_rows": _int(boundary.get("generated_candidate_rows")),
        "screen_generated_candidate_rows": _int(screen.get("generated_candidate_rows")),
    }


def _source_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        f"source_token_{index}": token in text
        for index, token in enumerate(REQUIRED_SOURCE_TOKENS)
    }
    contracts.update(
        {
            "source_path_is_python": path.suffix == ".py",
            "source_imports_static_review_authorization": (
                "STATIC_REVIEW_AUTHORIZED_NEXT_WORK" in text
            ),
            "source_defines_required_tables": "REQUIRED_TABLES" in text,
            "source_blocks_actions": "BLOCKED_ACTIONS" in text,
        }
    )
    return {"path": str(path), "exists": path.is_file(), "contracts": contracts}


def _test_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        name: name in text
        for name in REQUIRED_TEST_NAMES
    }
    return {"path": str(path), "exists": path.is_file(), "contracts": contracts}


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("diagnostics_root_exists", artifact["exists"]),
        _check("diagnostics_json_exists", artifact["json_exists"]),
        _check("diagnostics_markdown_exists", artifact["markdown_exists"]),
        _check("diagnostics_json_parseable", bool(artifact["payload"])),
        _check(
            "diagnostics_markdown_records_title",
            "Residual Comfort Failure Diagnostics" in artifact["markdown_text"],
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_diagnostics_complete", DIAGNOSTICS_READY_STATUS in audit_text),
        _check("audit_authorizes_post_review", DIAGNOSTICS_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _diagnostics_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    tables = set(summary["diagnostic_tables"])
    return [
        _check("diagnostics_status_complete", summary["status"] == DIAGNOSTICS_READY_STATUS),
        _check("diagnostics_passed", summary["passed"] is True),
        _check("diagnostics_failed_checks_empty", not summary["failed_checks"]),
        _check("diagnostics_authorizes_this_review", summary["authorized_next_work"] == DIAGNOSTICS_AUTHORIZED_NEXT_WORK),
        _check("diagnostics_post_review_authorized", summary["post_review_authorized"] is True),
        _check("diagnostics_no_blocked_actions", not summary["blocked_action_conflicts"]),
        _check("diagnostics_read_only", summary["read_only"] is True),
        _check("diagnostics_no_production_edit", summary["production_implementation_edit"] is False),
        _check("diagnostics_no_candidate_generation", summary["candidate_generation_execution"] is False),
        _check("diagnostics_no_screen_rerun", summary["fixed_snapshot_screen_rerun_execution"] is False),
        _check("diagnostics_no_dp_execution", summary["diffusion_planner_execution"] is False),
        _check("diagnostics_no_dp_modification", summary["diffusion_planner_modification"] is False),
        _check("diagnostics_no_reward_recompute", summary["reward_recompute"] is False),
        _check("diagnostics_no_tracker_recompute", summary["tracker_recompute"] is False),
        _check("diagnostics_no_candidate_reconstruction", summary["candidate_reconstruction"] is False),
        _check("diagnostics_no_training", summary["training"] is False),
        *[_check(f"diagnostics_table_{name}", name in tables) for name in REQUIRED_TABLES],
        _check("diagnostics_primary_blocker", summary["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("diagnostics_hard_progress_survivors_positive", summary["hard_progress_survivor_rows"] > 0),
        _check("diagnostics_comfort_admissible_zero", summary["comfort_admissible_rows"] == 0),
        _check("diagnostics_hard_positive", summary["hard_support_positive"] is True),
        _check("diagnostics_comfort_absent", summary["comfort_support_positive"] is False),
        _check("diagnostics_no_positive_support", summary["positive_support_evidence"] is False),
        _check("diagnostics_replay_not_ready", summary["replay_evidence_ready"] is False),
        _check("diagnostics_training_not_ready", summary["training_ready"] is False),
        _check("diagnostics_generated_rows_consistent", summary["generated_candidate_rows"] == summary["screen_generated_candidate_rows"]),
    ]


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("source_exists", source["exists"]),
        *[
            _check(f"source_contract_{name}", bool(passed))
            for name, passed in source["contracts"].items()
        ],
    ]


def _test_contract_checks(tests: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("test_exists", tests["exists"]),
        *[
            _check(f"test_contract_{name}", bool(passed))
            for name, passed in tests["contracts"].items()
        ],
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_failure_attribution", decision["diagnostic_failure_attribution_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
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
        "diagnostic_post_implementation_static_review_complete": passed,
        "diagnostic_failure_attribution_authorized": passed,
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


def _int(value: Any) -> int:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
