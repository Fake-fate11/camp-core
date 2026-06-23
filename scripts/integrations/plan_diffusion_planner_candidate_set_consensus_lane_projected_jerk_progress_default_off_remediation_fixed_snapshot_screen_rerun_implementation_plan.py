#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    DEFAULT_DEVELOPMENT_ROOT,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_implementation_only"
)
SOURCE_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_implementation_plan_only"
)

DEFAULT_TEST_ARTIFACT_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "unit_tests_036433c_r1"
)
SUMMARY_JSON = "fixed_snapshot_screen_rerun_unit_tests_summary.json"
SUMMARY_MD = "fixed_snapshot_screen_rerun_unit_tests_summary.md"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
PY_COMPILE_ERR = "PY_COMPILE.err"
PY_COMPILE_EXIT = "PY_COMPILE_EXIT"
PYTEST_UNIT_ERR = "PYTEST_UNIT.err"
PYTEST_UNIT_EXIT = "PYTEST_UNIT_EXIT"
PYTEST_RELATED_ERR = "PYTEST_RELATED.err"
PYTEST_RELATED_EXIT = "PYTEST_RELATED_EXIT"

ALLOWED_NEXT_FILES = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
    "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
)

BLOCKED_SCOPE_KEYS = (
    "production_code_modified",
    "screen_rerun_executed",
    "candidate_generation_executed",
    "replay_executed",
    "formal_seeds_used",
    "full36_used",
    "camp_retraining",
    "online_selector_promotion",
    "atom_promotion",
    "dp_modification",
    "safety_benefit_claim",
    "camp_over_dp_top1_claim",
    "classic_benders_claim",
)

BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "fixed_snapshot_screen_rerun_execution_authorized",
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
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation gate for the default-off fixed-snapshot "
            "screen rerun remediation."
        )
    )
    parser.add_argument(
        "--test_artifact_root",
        type=Path,
        default=Path(DEFAULT_TEST_ARTIFACT_ROOT),
    )
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
        test_artifact_root=args.test_artifact_root,
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
    test_artifact_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(test_artifact_root)
    summary = _summary_source(artifact["summary_payload"])
    plan = _implementation_plan()
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_summary_checks(summary),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "implementation_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only implementation contract after synthetic/static "
                "unit tests pinned fixed-snapshot rerun remediation boundaries"
            ),
            "plan_only": True,
            "implementation_code_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This plan reads only unit-test artifact evidence and existing "
                "source contracts. It does not edit product code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, recompute outcomes, define runtime atoms, choose "
                "lambda online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, claim safety benefit, claim CAMP "
                "is better than DP Top-1, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "unit_test_artifact": artifact,
        "source_summary": summary,
        "implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    artifact = report["unit_test_artifact"]
    summary = report["source_summary"]
    plan = report["implementation_plan"]
    lines = [
        "# Fixed-Snapshot Screen Rerun Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Unit Tests",
        "",
        f"- Root: `{artifact['root']}`",
        f"- Unit-test status: `{summary['status']}`",
        f"- Unit-test next work: `{summary['authorized_next_work']}`",
        f"- Required files present: `{artifact['required_files_present']}`",
        f"- SHA256SUMS ok: `{artifact['sha256sums_ok']}`",
        "",
        "## Allowed Next Files",
        "",
    ]
    for path in plan["allowed_next_files"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Planned Components", ""])
    for item in plan["components"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - purpose: {item['purpose']}")
        lines.append(f"  - required behavior: `{item['required_behavior']}`")
        lines.append(f"  - forbidden behavior: {item['forbidden_behavior']}")
    lines.extend(["", "## Verification Plan", ""])
    for item in plan["verification_plan"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- current gate is plan-only; product code edits are not authorized now",
            "- next gate may edit only the allowed CAMP product/test files",
            "- implementation must remain default-off and opt-in",
            "- candidate generation execution is not authorized by this plan",
            "- fixed-snapshot screen rerun is not authorized by this plan",
            "- replay, Full36, formal seeds, and closed-loop smoke are not authorized",
            "- atom promotion, CAMP retraining, and online selector changes are not authorized",
            "- DP weights and DP code must remain fixed",
            "- no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is authorized",
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "implementation_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan() -> dict[str, Any]:
    return {
        "selection_type": "fixed_snapshot_screen_rerun_implementation_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "allowed_next_files": list(ALLOWED_NEXT_FILES),
        "implementation_code_edit_authorized_current_gate": False,
        "implementation_code_edit_authorized_next_gate": True,
        "components": [
            {
                "name": "policy_default_off_boundary",
                "purpose": (
                    "keep the existing online-inert default path unchanged "
                    "while allowing only an explicit offline opt-in remediation"
                ),
                "required_behavior": [
                    "RouteTopologyCandidateConfig() remains lane_centerline_red_stop",
                    "any remediation is reachable only through explicit config or generator_policy",
                    "candidate0 and original DP candidate tensors are not mutated in place",
                ],
                "forbidden_behavior": (
                    "no default-on policy, no online selector wiring, no DP "
                    "candidate or DP code mutation"
                ),
            },
            {
                "name": "current_tick_finite_candidate_contract",
                "purpose": (
                    "constrain implementation inputs to finite current-tick "
                    "candidate features"
                ),
                "required_behavior": [
                    "use only current candidate tensor, lane centerline, red-route points, speed, dt, and config",
                    "fail closed when geometry or finite scalar evidence is missing",
                    "do not read outcome labels, future replay state, or online selector state",
                ],
                "forbidden_behavior": (
                    "no future label leakage, no replay-derived construction, "
                    "no online lambda choice"
                ),
            },
            {
                "name": "comfort_progress_guard_contract",
                "purpose": (
                    "preserve pinned relative comfort/progress budget semantics "
                    "while adding only bounded implementation scaffolding"
                ),
                "required_behavior": [
                    "respect progress_loss_budgets_m and smoothness_loss_budgets",
                    "respect command and rollout jerk/lateral budgets",
                    "return zero generated support when progress retention or comfort guards fail",
                ],
                "forbidden_behavior": (
                    "no budget relaxation, no rerun-until-pass behavior, no "
                    "promotion of failed support"
                ),
            },
            {
                "name": "hard_blocker_latency_contract",
                "purpose": (
                    "preserve hard-reason reporting and latency diagnostics "
                    "through the implementation"
                ),
                "required_behavior": [
                    "hard_reason_counts and route_failure_classes keep DP hard families separate",
                    "candidate_build and total latency summaries remain present",
                    "diagnostic metadata is finite and JSON scalar clean",
                ],
                "forbidden_behavior": (
                    "no DP hard-label renaming, no latency field removal, no "
                    "nonfinite diagnostics"
                ),
            },
            {
                "name": "math_boundary_preservation",
                "purpose": (
                    "keep CAMP's finite-candidate affine scoring and convex "
                    "master assumptions unchanged"
                ),
                "required_behavior": [
                    "no new runtime atom is introduced",
                    "score_k(w)=a_k^T w remains the scoring contract",
                    "simplex/CVaR/L2 master convexity assumptions are untouched",
                ],
                "forbidden_behavior": (
                    "no online lambda choice, no atom promotion, no classical "
                    "Benders claim"
                ),
            },
        ],
        "verification_plan": [
            "py_compile the allowed analyzer and focused tests after implementation",
            "run route-topology candidate screen tests and fixed-snapshot rerun unit tests",
            "run related lane-projected jerk/progress remediation tests without screen rerun",
            "record HEADS, SHA256SUMS, exit codes, stdout/stderr logs, and diff checks",
            "replicate the same checks on AutoDL before audit acceptance",
        ],
        "accept_criteria": [
            "implementation plan is complete and plan-only",
            "next gate files are limited to the predeclared CAMP analyzer and focused tests",
            "default-off/no-leak/current-tick contracts remain explicit",
            "candidate generation, fixed-snapshot screen rerun, replay, Full36, and formal seeds remain unauthorized",
            "CAMP retraining, atom promotion, online selector changes, safety claims, and DP modification remain unauthorized",
            "DP weights and DP code remain fixed",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        SUMMARY_JSON,
        SUMMARY_MD,
        HEADS,
        SHA256SUMS,
        PY_COMPILE_ERR,
        PY_COMPILE_EXIT,
        PYTEST_UNIT_ERR,
        PYTEST_UNIT_EXIT,
        PYTEST_RELATED_ERR,
        PYTEST_RELATED_EXIT,
    )
    files = {name: (root / name).is_file() for name in required}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    summary_payload = _load_json_if_present(root / SUMMARY_JSON)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "summary_payload": summary_payload,
        "py_compile_exit": _read_text(root / PY_COMPILE_EXIT).strip() or None,
        "pytest_unit_exit": _read_text(root / PYTEST_UNIT_EXIT).strip() or None,
        "pytest_related_exit": _read_text(root / PYTEST_RELATED_EXIT).strip() or None,
        "py_compile_err_bytes": _file_size(root / PY_COMPILE_ERR),
        "pytest_unit_err_bytes": _file_size(root / PYTEST_UNIT_ERR),
        "pytest_related_err_bytes": _file_size(root / PYTEST_RELATED_ERR),
    }


def _summary_source(payload: dict[str, Any]) -> dict[str, Any]:
    scope = _dict(payload.get("scope"))
    heads = _dict(payload.get("heads"))
    return {
        "status": payload.get("status"),
        "passed": bool(payload.get("passed")),
        "authorized_next_work": payload.get("authorized_next_work"),
        "selected_next_work": payload.get("selected_next_work"),
        "failed_checks": _list(payload.get("failed_checks")),
        "tests_pinned": _list(payload.get("tests_pinned")),
        "scope": {key: bool(scope.get(key)) for key in ("tests_only", *BLOCKED_SCOPE_KEYS)},
        "heads": {
            "camp_head": heads.get("camp_head"),
            "camp_origin_main": heads.get("camp_origin_main"),
            "dp_head": heads.get("dp_head"),
            "expected_dp_head": heads.get("expected_dp_head"),
        },
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("unit_test_artifact_exists", artifact["exists"], True),
        _check_equal("unit_test_required_files_present", artifact["required_files_present"], True),
        _check_equal("unit_test_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("unit_test_py_compile_exit_zero", artifact["py_compile_exit"], "0"),
        _check_equal("unit_test_pytest_unit_exit_zero", artifact["pytest_unit_exit"], "0"),
        _check_equal("unit_test_pytest_related_exit_zero", artifact["pytest_related_exit"], "0"),
        _check_equal("unit_test_py_compile_err_empty", artifact["py_compile_err_bytes"], 0),
        _check_equal("unit_test_pytest_unit_err_empty", artifact["pytest_unit_err_bytes"], 0),
        _check_equal("unit_test_pytest_related_err_empty", artifact["pytest_related_err_bytes"], 0),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _summary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    scope = summary["scope"]
    blocked = [key for key in BLOCKED_SCOPE_KEYS if scope.get(key)]
    return [
        _check_equal("unit_test_status_ready", summary["status"], SOURCE_READY_STATUS),
        _check_equal("unit_tests_passed", summary["passed"], True),
        _check_equal(
            "unit_tests_authorize_implementation_plan",
            summary["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("unit_test_failed_checks_clear", summary["failed_checks"], []),
        _check_equal("unit_test_scope_tests_only", scope.get("tests_only"), True),
        _check_equal("unit_test_blocked_scope_clear", blocked, []),
        _check_equal("unit_test_pins_expected_groups", len(summary["tests_pinned"]) >= 6, True),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "fixed_snapshot_screen_rerun_implementation_plan_only",
        ),
        _check_equal("plan_allowed_files", plan["allowed_next_files"], list(ALLOWED_NEXT_FILES)),
        _check_equal("plan_has_five_components", len(plan["components"]), 5),
        _check_equal("plan_mentions_default_off", "default" in text and "opt-in" in text, True),
        _check_equal("plan_mentions_current_tick", "current-tick" in text or "current tick" in text, True),
        _check_equal("plan_mentions_fail_closed", "fail closed" in text or "fail-closed" in text, True),
        _check_equal("plan_mentions_latency", "latency" in text, True),
        _check_equal("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("plan_mentions_convex_master", "simplex/cvar/l2" in text, True),
        _check_equal("plan_blocks_replay", "replay" in text and "unauthorized" in text, True),
        _check_equal("plan_blocks_dp_modification", "dp weights and dp code remain fixed" in text, True),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal(
            "boundary_current_gate_blocks_implementation_edits",
            decision["implementation_code_edit_authorized"],
            False,
        ),
        _check_equal(
            "boundary_next_gate_scoped_implementation",
            decision["next_gate_implementation_code_edit_authorized"],
            True,
        ),
        _check_equal(
            "boundary_blocks_candidate_generation",
            decision["candidate_generation_execution_authorized"],
            False,
        ),
        _check_equal(
            "boundary_blocks_screen_rerun",
            decision["fixed_snapshot_screen_rerun_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal("boundary_blocks_camp_over_dp_top1_claim", decision["camp_over_dp_top1_claim_authorized"], False),
        _check_equal("boundary_blocks_benders", decision["classic_benders_claim_authorized"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "implementation_plan_ready": passed,
        "implementation_only_gate_authorized": passed,
        "next_gate_implementation_code_edit_authorized": passed,
        "next_gate_allowed_files": list(ALLOWED_NEXT_FILES) if passed else [],
        "implementation_code_edit_authorized": False,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
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
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _sha256sum_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    root = path.parent
    details = []
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            ok = False
            details.append({"line": line, "ok": False, "reason": "malformed"})
            continue
        expected, name = parts
        item = Path(name.strip())
        if not item.is_absolute():
            item = root / item
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append({"path": str(item), "expected": expected, "actual": actual, "ok": matched})
    return ok, details


def _load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


if __name__ == "__main__":
    main()
