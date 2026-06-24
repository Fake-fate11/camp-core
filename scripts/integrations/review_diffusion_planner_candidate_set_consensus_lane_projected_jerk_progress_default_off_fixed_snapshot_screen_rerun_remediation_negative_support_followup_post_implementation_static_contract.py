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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (  # noqa: E402
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK as IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
    REQUIRED_TESTS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "post_implementation_static_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "post_implementation_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "fixed_snapshot_screen_rerun_plan_only"
)
IMPLEMENTATION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_complete"
)
IMPLEMENTATION_AUDIT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_only"
)
REQUIRED_AUDIT_AUTHORIZATION = IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_IMPLEMENTATION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_implementation_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_SOURCE_PATH = ROOT / ALLOWED_NEXT_FILES[0]
DEFAULT_TEST_PATH = ROOT / ALLOWED_NEXT_FILES[1]

SUMMARY_JSON = "implementation_summary.json"
SUMMARY_MD = "implementation_summary.md"
SHA256SUMS = "SHA256SUMS"

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
            "Read-only post-implementation static contract review for the "
            "negative-support follow-up implementation."
        )
    )
    parser.add_argument(
        "--implementation_root",
        type=Path,
        default=Path(DEFAULT_IMPLEMENTATION_ROOT),
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
        implementation_root=args.implementation_root,
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
    implementation_root: Path,
    audit_path: Path,
    source_path: Path,
    test_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(implementation_root)
    summary = _implementation_summary(artifact["payload"])
    source = _source_contract(source_path, _read_text(source_path))
    tests = _test_contract(test_path, _read_text(test_path))
    audit_text = _read_text(audit_path)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_summary_checks(summary, source, tests),
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
                "support_followup_post_implementation_static_review_v1"
            ),
            "label": label,
            "role": "read-only static review after scoped implementation",
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
                "This review reads only implementation artifacts, source text, "
                "test text, and audit authorization. It does not edit source "
                "code, create fixed-snapshot candidates, rerun the screen, run "
                "DP, run replay, recompute outcomes, define runtime atoms, "
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
        "implementation_artifact": _strip_payload(artifact),
        "implementation_summary": summary,
        "source_contract": source,
        "test_contract": tests,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_contract"]
    tests = report["test_contract"]
    lines = [
        "# Negative-Support Follow-Up Post-Implementation Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Contracts",
        "",
    ]
    for name, passed in source["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Test Contracts", ""])
    for name, passed in tests["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- fixed-snapshot screen rerun planning only may follow",
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
    payload_path = root / SUMMARY_JSON
    markdown_path = root / SUMMARY_MD
    sha_path = root / SHA256SUMS
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "sha256sums_exists": sha_path.is_file(),
        "sha256sums_ok": _sha256sums_ok(sha_path),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _implementation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "passed": bool(payload.get("passed")),
        "planned_policy": payload.get("planned_policy"),
        "allowed_files_modified": _list(payload.get("allowed_files_modified")),
        "file_sha256": _dict(payload.get("file_sha256")),
        "verification": _dict(payload.get("verification")),
        "implementation_summary": _dict(payload.get("implementation_summary")),
        "blocked_action_conflicts": [
            key for key, value in _dict(payload.get("blocked_actions")).items() if bool(value)
        ],
    }


def _source_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        "planned_policy_registered": PLANNED_POLICY in text,
        "default_policy_preserved": 'generator_policy: str = "lane_centerline_red_stop"' in text,
        "planned_policy_branch_present": f'== "{PLANNED_POLICY}"' in text,
        "fail_closed_partition_present": "fail_closed_partition" in text,
        "current_tick_fail_closed_present": "_add_negative_support_fail_closed_partition" in text,
        "hard_floor_metadata_present": "hard_feasibility_floor_current_tick" in text,
        "comfort_after_hard_progress_present": "comfort_after_hard_progress" in text,
        "budget_cap_present": "max_remediation_candidates" in text,
        "current_tick_requirements_include_policy": (
            "_requires_current_tick_scalar_evidence" in text and PLANNED_POLICY in text
        ),
        "finite_selected_requirements_include_policy": (
            "_requires_finite_selected_candidate_evidence" in text
            and PLANNED_POLICY in text
        ),
        "math_boundary_preserved": (
            "score_k(w)=a_k^T w" not in text
            and "Diffusion-Planner" not in text
        ),
    }
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "contracts": contracts,
    }


def _test_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        "required_tests_present": all(name in text for name in REQUIRED_TESTS),
        "default_policy_pinned": (
            "test_route_topology_negative_support_followup_preserves_default_policy"
            in text
        ),
        "fail_closed_partition_pinned": (
            "test_route_topology_negative_support_followup_partitions_fail_closed_snapshots"
            in text
        ),
        "nonfinite_current_tick_pinned": (
            "test_route_topology_negative_support_followup_rejects_nonfinite_current_tick_inputs"
            in text
        ),
        "budget_cap_pinned": (
            "test_route_topology_negative_support_followup_candidate_budget_cap"
            in text
        ),
        "no_fixed_snapshot_execution_in_tests": "snapshot_dir" not in text,
        "no_formal_seed_use_in_tests": "formal_seeds_used" not in text,
    }
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "contracts": contracts,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("implementation_root_exists", artifact["exists"]),
        _check("implementation_json_exists", artifact["json_exists"]),
        _check("implementation_markdown_exists", artifact["markdown_exists"]),
        _check("implementation_sha256sums_exists", artifact["sha256sums_exists"]),
        _check("implementation_sha256sums_ok", artifact["sha256sums_ok"]),
        _check("implementation_json_parseable", bool(artifact["payload"])),
        _check("implementation_markdown_records_status", "Implementation Summary" in artifact["markdown_text"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_authorizes_post_implementation_review", REQUIRED_AUDIT_AUTHORIZATION in audit_text),
        _check("audit_records_implementation_gate_complete", IMPLEMENTATION_AUDIT_STATUS in audit_text),
    ]


def _summary_checks(
    summary: dict[str, Any],
    source: dict[str, Any],
    tests: dict[str, Any],
) -> list[dict[str, Any]]:
    file_sha = summary["file_sha256"]
    verification = summary["verification"]
    impl = summary["implementation_summary"]
    return [
        _check("implementation_status_complete", summary["status"] == IMPLEMENTATION_READY_STATUS),
        _check("implementation_passed", summary["passed"] is True),
        _check("implementation_policy_matches_plan", summary["planned_policy"] == PLANNED_POLICY),
        _check("implementation_allowed_files_match", tuple(summary["allowed_files_modified"]) == ALLOWED_NEXT_FILES),
        _check("implementation_source_hash_matches", file_sha.get(ALLOWED_NEXT_FILES[0]) == source["sha256"]),
        _check("implementation_test_hash_matches", file_sha.get(ALLOWED_NEXT_FILES[1]) == tests["sha256"]),
        _check("implementation_route_pytest_passed", "passed" in str(verification.get("route_pytest"))),
        _check("implementation_related_pytest_passed", "passed" in str(verification.get("related_pytest"))),
        _check("implementation_default_policy_preserved", impl.get("default_policy_preserved") is True),
        _check("implementation_new_policy_opt_in", impl.get("new_policy_opt_in") is True),
        _check("implementation_no_blocked_actions", not summary["blocked_action_conflicts"]),
    ]


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"source_contract_{name}", passed)
        for name, passed in source["contracts"].items()
    ]


def _test_contract_checks(tests: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"test_contract_{name}", passed)
        for name, passed in tests["contracts"].items()
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    return [
        _check("boundary_blocks_execution", True),
        _check("boundary_blocks_formal_seeds", True),
        _check("boundary_blocks_training", True),
        _check("boundary_blocks_dp_modification", True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "fixed_snapshot_screen_rerun_plan_authorized": passed,
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


def _sha256sums_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            return False
        expected, name = parts[0], parts[-1]
        target = Path(name)
        if not target.is_absolute():
            target = path.parent / target
        if not target.is_file() or _sha256(target) != expected:
            return False
    return True


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
