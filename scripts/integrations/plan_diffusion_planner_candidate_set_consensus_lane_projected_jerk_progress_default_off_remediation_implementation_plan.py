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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (  # noqa: E402
    EXIT_CODE,
    HEADS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_implementation_only"
)
DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_TEST_ARTIFACT_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_unit_tests_9b96e96"
)

PY_COMPILE_LOG = "PY_COMPILE.log"
PY_COMPILE_ERR = "PY_COMPILE.err"
PYTEST_LOG = "PYTEST.log"
PYTEST_ERR = "PYTEST.err"

ALLOWED_NEXT_FILES = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
    "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
)

BLOCKED_ACTIONS = (
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
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for the default-off lane-projected jerk/progress "
            "remediation implementation."
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
    plan = _implementation_plan()
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_implementation_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only implementation contract after synthetic/static "
                "unit tests pinned the default-off remediation boundaries"
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
            "math_boundary": (
                "This plan reads only repo-local test/artifact evidence and "
                "source contracts. It does not edit implementation code, "
                "create candidates, rerun the screen, run DP, run replay, "
                "recompute outcomes, define runtime atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online "
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
        "unit_test_artifact": artifact,
        "implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    artifact = report["unit_test_artifact"]
    lines = [
        "# Lane-Projected Jerk/Progress Default-Off Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Unit-Test Artifact",
        "",
        f"- Root: `{artifact['root']}`",
        f"- Required files present: `{artifact['required_files_present']}`",
        f"- Py compile exit ok: `{artifact['py_compile_exit_ok']}`",
        f"- Pytest exit ok: `{artifact['pytest_exit_ok']}`",
        "",
        "## Allowed Next Files",
        "",
    ]
    for path in plan["allowed_next_files"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Planned Implementation Components", ""])
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
            "- current gate is plan-only; implementation code edits are not authorized now",
            "- next gate may edit only the two allowed CAMP route-topology files",
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
                "default_off_remediation_implementation_only` is authorized if "
                "all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan() -> dict[str, Any]:
    return {
        "selection_type": "default_off_remediation_implementation_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "allowed_next_files": list(ALLOWED_NEXT_FILES),
        "implementation_code_edit_authorized_next_gate": True,
        "production_implementation_edit_authorized_current_gate": False,
        "components": [
            {
                "name": "policy_default_off_boundary",
                "purpose": (
                    "keep the existing online-inert default policy unchanged "
                    "while allowing the later implementation gate to add an "
                    "explicit offline opt-in remediation path"
                ),
                "required_behavior": [
                    "RouteTopologyCandidateConfig() remains lane_centerline_red_stop",
                    "remediation is reachable only through an explicit generator_policy",
                    "candidate0 and original DP candidate ordering remain preserved",
                ],
                "forbidden_behavior": (
                    "no default-on behavior, no online selector wiring, no DP "
                    "candidate mutation"
                ),
            },
            {
                "name": "current_tick_input_contract",
                "purpose": (
                    "constrain any later candidate construction to information "
                    "available at the current tick"
                ),
                "required_behavior": [
                    "use only current candidate tensor, lane centerline, red-route points, speed, dt, and config",
                    "do not read future outcome labels or replay results for construction",
                    "fail closed when geometry or finite scalar evidence is missing",
                ],
                "forbidden_behavior": (
                    "no future label leakage, no matched outcome labels, no "
                    "closed-loop feedback"
                ),
            },
            {
                "name": "progress_comfort_fallback_boundary",
                "purpose": (
                    "predeclare fail-closed behavior for comfort/progress "
                    "support without relaxing the pinned budgets"
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
                "name": "hard_feasibility_and_latency_contract",
                "purpose": (
                    "preserve hard-label reporting and existing latency fields "
                    "while adding only reportable construction evidence"
                ),
                "required_behavior": [
                    "route_failure_classes continues to report DP hard reason families",
                    "candidate_build and total latency summaries remain present",
                    "diagnostic evidence is finite and JSON scalar clean",
                ],
                "forbidden_behavior": (
                    "no DP hard label renaming, no latency field removal, no "
                    "nonfinite or array-valued diagnostics"
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
            "py_compile only the allowed implementation file and focused route-topology tests",
            "run focused route-topology tests after any later implementation-only gate",
            "run the already-pinned default-off remediation unit tests with the focused route-topology tests",
            "record HEADS, artifact paths, SHA256 hashes, and stderr byte counts",
            "replicate the same narrow checks on AutoDL before any later audit acceptance",
        ],
        "accept_criteria": [
            "implementation plan is complete and plan-only",
            "next gate files are limited to the route-topology analyzer and focused tests",
            "default-off/no-leak/current-tick contracts remain explicit",
            "candidate generation, fixed-snapshot screen rerun, replay, Full36, and formal seeds remain unauthorized",
            "CAMP retraining, atom promotion, online selector changes, safety claims, and DP modification remain unauthorized",
            "DP weights and DP code must remain fixed",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (PY_COMPILE_LOG, PY_COMPILE_ERR, PYTEST_LOG, PYTEST_ERR, EXIT_CODE, HEADS)
    files = {name: (root / name).is_file() for name in required}
    exit_text = _read_text(root / EXIT_CODE)
    py_compile_err_bytes = _file_size(root / PY_COMPILE_ERR)
    pytest_err_bytes = _file_size(root / PYTEST_ERR)
    pytest_text = _read_text(root / PYTEST_LOG)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "exit_code_text": exit_text,
        "py_compile_exit_ok": "PY_COMPILE_EXIT=0" in exit_text,
        "pytest_exit_ok": "PYTEST_EXIT=0" in exit_text,
        "py_compile_err_bytes": py_compile_err_bytes,
        "pytest_err_bytes": pytest_err_bytes,
        "pytest_passed_text_present": "passed" in pytest_text.lower(),
        "hashes": {
            name: _sha256(root / name)
            for name in required
            if (root / name).is_file()
        },
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("unit_test_artifact_exists", artifact["exists"], True),
        _check_equal(
            "unit_test_artifact_required_files_present",
            artifact["required_files_present"],
            True,
        ),
        _check_equal("unit_test_py_compile_exit_ok", artifact["py_compile_exit_ok"], True),
        _check_equal("unit_test_pytest_exit_ok", artifact["pytest_exit_ok"], True),
        _check_equal("unit_test_py_compile_err_empty", artifact["py_compile_err_bytes"], 0),
        _check_equal("unit_test_pytest_err_empty", artifact["pytest_err_bytes"], 0),
        _check_equal(
            "unit_test_pytest_passed_text_present",
            artifact["pytest_passed_text_present"],
            True,
        ),
    ]


def _head_checks(
    camp_head: str, camp_origin_main: str, dp_head: str
) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "default_off_remediation_implementation_plan_only",
        ),
        _check_equal("plan_allowed_file_count", len(plan["allowed_next_files"]), 2),
        _check_equal("plan_allowed_files", plan["allowed_next_files"], list(ALLOWED_NEXT_FILES)),
        _check_equal("plan_has_five_components", len(plan["components"]), 5),
        _check_equal("plan_mentions_default_off", "default" in text and "opt-in" in text, True),
        _check_equal("plan_mentions_current_tick", "current tick" in text, True),
        _check_equal("plan_mentions_fail_closed", "fail closed" in text or "fail-closed" in text, True),
        _check_equal("plan_mentions_latency", "latency" in text, True),
        _check_equal("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("plan_blocks_replay", "replay" in text and "unauthorized" in text, True),
        _check_equal("plan_blocks_dp_modification", "dp weights and dp code must remain fixed" in text, True),
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
        _check_equal(
            "boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False
        ),
        _check_equal(
            "boundary_blocks_dp_modification",
            decision["dp_modification_authorized"],
            False,
        ),
        _check_equal(
            "boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False
        ),
        _check_equal(
            "boundary_blocks_benders",
            decision["classic_benders_claim_authorized"],
            False,
        ),
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


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


if __name__ == "__main__":
    main()
