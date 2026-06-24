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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_implementation_plan import (  # noqa: E402
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK as IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_post_implementation_static_"
    "review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_post_implementation_static_"
    "review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_fixed_snapshot_screen_rerun_plan_only"
)
IMPLEMENTATION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_complete"
)
IMPLEMENTATION_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_only"
)
REQUIRED_AUDIT_AUTHORIZATION = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_post_implementation_static_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_IMPLEMENTATION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "implementation_bff8f8b"
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
            "default-off fixed-snapshot screen rerun remediation."
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
    summary = _implementation_summary(artifact["summary_payload"])
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
                "default_off_fixed_snapshot_screen_rerun_remediation_post_"
                "implementation_static_review_v1"
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
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Post-Implementation Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Contracts",
        "",
    ]
    for name, passed in source["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Test Contracts", ""])
    for name, passed in tests["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Boundaries", ""])
    for item in _blocked_boundaries():
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
                "fixed_snapshot_screen_rerun_plan_only` is authorized if all "
                "checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    summary_path = root / SUMMARY_JSON
    markdown_path = root / SUMMARY_MD
    sha_path = root / SHA256SUMS
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "summary_exists": summary_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "sha256sums_exists": sha_path.is_file(),
        "sha256sums_ok": _sha256sums_ok(root),
        "summary_sha256": _sha256(summary_path),
        "markdown_sha256": _sha256(markdown_path),
        "summary_payload": _read_json(summary_path),
        "markdown_text": _read_text(markdown_path),
    }


def _implementation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "passed": bool(payload.get("passed")),
        "allowed_files_modified": _list(payload.get("allowed_files_modified")),
        "planned_policy": payload.get("planned_policy"),
        "local_default_policy_preserved": bool(
            payload.get("local_default_policy_preserved")
        ),
        "file_sha256": _dict(payload.get("file_sha256")),
        "candidate_generation_execution": bool(
            payload.get("candidate_generation_execution")
        ),
        "fixed_snapshot_screen_rerun_execution": bool(
            payload.get("fixed_snapshot_screen_rerun_execution")
        ),
        "replay_execution": bool(payload.get("replay_execution")),
        "formal_seeds_used": bool(payload.get("formal_seeds_used")),
        "full36_used": bool(payload.get("full36_used")),
        "camp_retraining": bool(payload.get("camp_retraining")),
        "dp_modification": bool(payload.get("dp_modification")),
        "online_selector_promotion": bool(payload.get("online_selector_promotion")),
        "atom_promotion": bool(payload.get("atom_promotion")),
        "safety_benefit_claim": bool(payload.get("safety_benefit_claim")),
        "camp_over_dp_top1_claim": bool(payload.get("camp_over_dp_top1_claim")),
        "verification": _dict(payload.get("verification")),
    }


def _source_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        "default_policy_preserved": 'generator_policy: str = "lane_centerline_red_stop"' in text,
        "planned_policy_registered": PLANNED_POLICY in text,
        "planned_policy_branch_present": f'config.generator_policy == "{PLANNED_POLICY}"' in text,
        "close_red_partition_present": "close_red_current_tick_fallback" in text,
        "comfort_first_profile_present": "comfort_first_jerk_limited_lane_station" in text,
        "budget_cap_present": "max_remediation_candidates" in text,
        "current_tick_fail_closed_present": "_requires_current_tick_scalar_evidence" in text
        and PLANNED_POLICY in _function_body(text, "_requires_current_tick_scalar_evidence"),
        "finite_selected_fail_closed_present": "_requires_finite_selected_candidate_evidence" in text
        and PLANNED_POLICY in _function_body(text, "_requires_finite_selected_candidate_evidence"),
        "monotonic_lane_station_present": "_monotonic_lane_station_candidate" in text,
        "payload_only_diagnostics_present": "current_tick_features_only" in text,
        "dp_invocation_unchanged": "_load_runtime" in text and "Diffusion-Planner" not in _function_body(text, "build_route_topology_candidates"),
        "math_boundary_preserved": "affine a_k^T w" in text
        and "simplex/CVaR/L2 robust master remains convex" in text,
    }
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _sha256(path),
        "contracts": contracts,
    }


def _test_contract(path: Path, text: str) -> dict[str, Any]:
    required_tests = (
        "test_route_topology_generator_builds_comfort_first_remediation_policy",
        "test_route_topology_comfort_first_remediation_candidate_budget_cap",
        "test_route_topology_comfort_first_requires_current_tick_scalars",
        "test_route_topology_report_rejects_invalid_remediation_candidate_cap",
    )
    contracts = {
        "required_tests_present": all(name in text for name in required_tests),
        "default_off_pinned": "lane_centerline_red_stop" in text
        and "comfort_first_lane_projected_red_stop" in text,
        "close_red_partition_pinned": "close_red_current_tick_fallback" in text,
        "budget_cap_pinned": "candidate_budget_cap" in text
        and "max_remediation_candidates" in text,
        "current_tick_fail_closed_pinned": "current_tick_scalar_invalid" in text,
        "no_fixed_snapshot_execution_in_tests": "snapshot_dir" not in text
        and "formal_seeds_used" not in text,
    }
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _sha256(path),
        "contracts": contracts,
        "required_tests": list(required_tests),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("implementation_artifact_root_exists", artifact["exists"]),
        _check("implementation_summary_exists", artifact["summary_exists"]),
        _check("implementation_markdown_exists", artifact["markdown_exists"]),
        _check("implementation_sha256sums_exists", artifact["sha256sums_exists"]),
        _check("implementation_sha256sums_ok", artifact["sha256sums_ok"]),
        _check("implementation_summary_parseable", bool(artifact["summary_payload"])),
        _check("implementation_markdown_records_verification", "Verification" in artifact["markdown_text"]),
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
        _check("audit_exists", bool(audit_text)),
        _check("audit_authorizes_post_implementation_review", REQUIRED_AUDIT_AUTHORIZATION in audit_text),
        _check(
            "audit_records_implementation_complete",
            IMPLEMENTATION_READY_STATUS in audit_text
            or IMPLEMENTATION_GATE in audit_text,
        ),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _summary_checks(
    summary: dict[str, Any],
    source: dict[str, Any],
    tests: dict[str, Any],
) -> list[dict[str, Any]]:
    source_hash = source["sha256"]
    test_hash = tests["sha256"]
    return [
        _check("summary_status_complete", summary["status"] == IMPLEMENTATION_READY_STATUS),
        _check("summary_passed", summary["passed"] is True),
        _check("summary_allowed_files_exact", tuple(summary["allowed_files_modified"]) == ALLOWED_NEXT_FILES),
        _check("summary_planned_policy", summary["planned_policy"] == PLANNED_POLICY),
        _check("summary_default_policy_preserved", summary["local_default_policy_preserved"] is True),
        _check("summary_source_hash_matches", summary["file_sha256"].get(ALLOWED_NEXT_FILES[0]) == source_hash),
        _check("summary_test_hash_matches", summary["file_sha256"].get(ALLOWED_NEXT_FILES[1]) == test_hash),
        _check("summary_py_compile_passed", summary["verification"].get("py_compile") == "passed"),
        _check("summary_route_pytest_passed", summary["verification"].get("route_pytest") == "23 passed"),
        _check("summary_related_pytest_passed", summary["verification"].get("related_pytest") == "41 passed"),
        *_blocked_summary_checks(summary),
    ]


def _blocked_summary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("summary_no_candidate_generation_execution", summary["candidate_generation_execution"] is False),
        _check("summary_no_screen_rerun", summary["fixed_snapshot_screen_rerun_execution"] is False),
        _check("summary_no_replay", summary["replay_execution"] is False),
        _check("summary_no_formal_seeds", summary["formal_seeds_used"] is False),
        _check("summary_no_training", summary["camp_retraining"] is False),
        _check("summary_no_dp_modification", summary["dp_modification"] is False),
        _check("summary_no_promotion", summary["online_selector_promotion"] is False and summary["atom_promotion"] is False),
        _check("summary_no_claims", summary["safety_benefit_claim"] is False and summary["camp_over_dp_top1_claim"] is False),
    ]


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("source_exists", source["exists"]),
        *[
            _check(f"source_contract_{name}", passed)
            for name, passed in source["contracts"].items()
        ],
    ]


def _test_contract_checks(tests: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("tests_exist", tests["exists"]),
        *[
            _check(f"test_contract_{name}", passed)
            for name, passed in tests["contracts"].items()
        ],
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    text = "\n".join(_blocked_boundaries())
    return [
        _check("boundary_blocks_candidate_generation", "candidate generation execution is not authorized" in text),
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


def _blocked_boundaries() -> list[str]:
    return [
        "static review only; implementation edits are not authorized",
        "candidate generation execution is not authorized",
        "fixed-snapshot screen rerun is not authorized",
        "replay, Full36, closed-loop smoke, and formal seeds 11/12/13 remain frozen",
        "CAMP retraining and training execution are not authorized",
        "atom promotion and online selector promotion are not authorized",
        "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
        "DP weights, DP code, DP configs, and DP invocation must remain fixed",
    ]


def _function_body(text: str, name: str) -> str:
    marker = f"def {name}"
    start = text.find(marker)
    if start < 0:
        return ""
    next_def = text.find("\ndef ", start + len(marker))
    return text[start:] if next_def < 0 else text[start:next_def]


def _sha256sums_ok(root: Path) -> bool:
    sha_path = root / SHA256SUMS
    if not sha_path.is_file():
        return False
    for raw_line in sha_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split(None, 1)
        if len(parts) != 2:
            return False
        expected, name = parts
        candidate = root / name.strip()
        if not candidate.is_file():
            return False
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
            return False
    return True


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"summary_payload", "markdown_text"}
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
