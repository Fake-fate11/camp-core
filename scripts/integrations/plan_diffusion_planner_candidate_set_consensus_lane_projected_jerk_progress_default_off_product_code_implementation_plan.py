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


GATE_NAME = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "product_code_implementation_plan_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "product_code_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "product_code_implementation_plan_rejected"
)
SOURCE_COMPLETE_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_complete"
)
RECOMMENDED_NEXT_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "product_code_implementation_only"
)

DEFAULT_UNIT_TEST_ARTIFACT_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "unit_tests_only_ffd5cb1"
)

UNIT_TESTS_DECISION = "UNIT_TESTS_DECISION.txt"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
EXIT_CODE = "EXIT_CODE"
PY_COMPILE_EXIT = "PY_COMPILE_EXIT"
PY_COMPILE_ERR = "PY_COMPILE.err"
PYTEST_UNIT_TESTS_EXIT = "PYTEST_UNIT_TESTS_EXIT"
PYTEST_UNIT_TESTS_ERR = "PYTEST_UNIT_TESTS.err"
PYTEST_RELATED_EXIT = "PYTEST_RELATED_EXIT"
PYTEST_RELATED_ERR = "PYTEST_RELATED.err"
SHA256SUMS_CHECK_EXIT = "SHA256SUMS_CHECK_EXIT"

REQUIRED_SOURCE_FILES = (
    HEADS,
    UNIT_TESTS_DECISION,
    SHA256SUMS,
    EXIT_CODE,
    PY_COMPILE_EXIT,
    PY_COMPILE_ERR,
    PYTEST_UNIT_TESTS_EXIT,
    PYTEST_UNIT_TESTS_ERR,
    PYTEST_RELATED_EXIT,
    PYTEST_RELATED_ERR,
    SHA256SUMS_CHECK_EXIT,
)

FORBIDDEN_SOURCE_FLAGS = (
    "implementation_code_edit_authorized",
    "candidate_generation_execution_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "new_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "safety_benefit_evidence",
    "camp_over_dp_top1_claim_authorized",
)

PRODUCT_IMPLEMENTATION_CANDIDATE_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner.py",
    "camp_core/camp_core/integrations/diffusion_planner_candidate_set_consensus_payload.py",
    "camp_core/camp_core/integrations/diffusion_planner_progress_support.py",
)

SUPPORTING_INTEGRATION_FILES = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
)

REQUIRED_VERIFICATION_FILES = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_payload.py",
    "camp_core/tests/test_diffusion_planner_progress_support_logging_payload.py",
    "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only product-code implementation contract for candidate-set "
            "consensus lane-projected jerk/progress support. The gate reads "
            "unit-test-only evidence and does not edit product code."
        )
    )
    parser.add_argument(
        "--unit_test_artifact_root",
        type=Path,
        default=Path(DEFAULT_UNIT_TEST_ARTIFACT_ROOT),
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
        unit_test_artifact_root=args.unit_test_artifact_root,
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
    unit_test_artifact_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(unit_test_artifact_root)
    source = _source_decision(artifact)
    plan = _implementation_plan()
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head, artifact),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    decision = _final_decision(passed, checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_product_code_implementation_plan_v1"
            ),
            "gate": GATE_NAME,
            "label": label,
            "role": (
                "plan-only product-code implementation contract after the "
                "fixed-snapshot screen-rerun synthetic unit-tests-only gate"
            ),
            "plan_only": True,
            "product_code_modified": False,
            "implementation_code_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "formal_seeds_used": False,
            "training": False,
            "online_selector_change": False,
            "atom_promotion": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This gate only designs a future product-code edit. It does "
                "not edit product code, run DP, create candidates, rerun the "
                "screen, run replay, use formal seeds, compute outcomes, "
                "promote atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, modify "
                "DP weights or code, claim safety benefit, claim CAMP is "
                "better than DP Top-1, or claim classical Benders."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "unit_test_artifact": artifact,
        "source_decision": source,
        "implementation_plan": plan,
        "checks": checks,
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    artifact = report["unit_test_artifact"]
    source = report["source_decision"]
    lines = [
        "# Candidate-Set Consensus Product-Code Implementation Plan",
        "",
        f"- Gate: `{GATE_NAME}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Source artifact: `{artifact['root']}`",
        f"- Source status: `{source.get('status')}`",
        f"- Recommended next gate: `{decision['recommended_next_gate']}`",
        "- Product-code edit authorized now: "
        f"`{decision['implementation_code_edit_authorized']}`",
        "- Product-code edit requires separate explicit authorization: "
        f"`{decision['recommended_next_gate_requires_explicit_authorization']}`",
        "",
        "## Current-Gate Boundary",
        "",
        "The current gate is plan-only. It does not modify CAMP product code, "
        "run candidate generation, execute a fixed-snapshot screen rerun, run "
        "replay, use formal seeds, retrain CAMP, promote atoms, promote the "
        "online selector, modify DP, claim safety benefit, claim CAMP-over-DP-"
        "Top-1, or claim a DP-side classical Benders decomposition.",
        "",
        "## Product-Code Scope Candidate",
        "",
    ]
    lines.extend(f"- `{path}`" for path in plan["product_code_candidate_files"])
    lines.extend(
        [
            "",
            "## Supporting Integration Scope",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in plan["supporting_integration_files"])
    lines.extend(
        [
            "",
            "## Implementation Components",
            "",
        ]
    )
    for component in plan["components"]:
        lines.extend(
            [
                f"### {component['name']}",
                "",
                component["objective"],
                "",
                "Contracts:",
            ]
        )
        lines.extend(f"- {item}" for item in component["contracts"])
        lines.append("")
    lines.extend(
        [
            "## Static Contracts",
            "",
        ]
    )
    lines.extend(f"- `{name}`: {text}" for name, text in plan["static_contracts"].items())
    lines.extend(
        [
            "",
            "## Verification Requirements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in plan["verification_requirements"])
    lines.extend(
        [
            "",
            "## Audit/Artifact Requirements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in plan["artifact_and_audit_requirements"])
    lines.extend(
        [
            "",
            "## Final Decision",
            "",
            "```json",
            json.dumps(decision, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan() -> dict[str, Any]:
    return {
        "selection_type": "product_code_implementation_plan_only",
        "product_code_candidate_files": list(PRODUCT_IMPLEMENTATION_CANDIDATE_FILES),
        "supporting_integration_files": list(SUPPORTING_INTEGRATION_FILES),
        "required_verification_files": list(REQUIRED_VERIFICATION_FILES),
        "recommended_next_gate": RECOMMENDED_NEXT_GATE,
        "recommended_next_gate_requires_explicit_authorization": True,
        "components": [
            {
                "name": "default_off_opt_in_wiring",
                "objective": (
                    "Introduce only an opt-in CAMP-side switch for the future "
                    "candidate-set consensus/progress-support path. The default "
                    "runtime behavior must remain unchanged."
                ),
                "contracts": [
                    "default-off remains the default for all online paths",
                    "opt-in must be explicit in config or CLI wiring",
                    "disabled mode must be selector-equivalent to current HEAD",
                    "fallback must fail closed to the pre-existing selector result",
                ],
            },
            {
                "name": "current_tick_payload_composition",
                "objective": (
                    "Compose already-audited current-tick payload builders for "
                    "candidate-set consensus and progress support without "
                    "introducing future or outcome inputs."
                ),
                "contracts": [
                    "payload reads only fixed current-tick finite DP candidates",
                    "payload reads only current route geometry and current tick state",
                    "payload must report future_outcome_leakage=false",
                    "payload must report selection_effect=false",
                    "payload no-leak/default-off metadata must be logged",
                ],
            },
            {
                "name": "score_and_atom_boundary",
                "objective": (
                    "Keep any new coefficients diagnostic-only in the future "
                    "implementation until a separate atom-promotion gate exists."
                ),
                "contracts": [
                    "no atom promotion in this implementation plan",
                    "future scoring must preserve score_k(w)=a_k^T w",
                    "simplex/CVaR/L2 master convexity must remain intact",
                    "nonnegative or hinge/signed-split legality must be proven before any future atom gate",
                    "do not call the finite-candidate DP-side selector classical Benders",
                ],
            },
            {
                "name": "comfort_progress_hard_blocker_separation",
                "objective": (
                    "Separate comfort/progress support diagnostics from immutable "
                    "DP hard blockers so remediation does not hide kinematic or "
                    "route-topology failures."
                ),
                "contracts": [
                    "hard blockers remain labeled separately from comfort blockers",
                    "progress support must preserve current-tick finite-candidate boundary",
                    "absolute lateral guard remains diagnostic-only",
                    "fallback/progress/comfort boundaries must be logged distinctly",
                    "candidate support insufficiency must reject promotion, not trigger retraining",
                ],
            },
            {
                "name": "latency_and_verification_envelope",
                "objective": (
                    "Predeclare latency measurement and post-implementation "
                    "verification before any product-code edit is considered."
                ),
                "contracts": [
                    "component latency keys must be logged for payload construction",
                    "candidate-build p95 target remains <=10 ms until re-evidenced",
                    "total p95 target remains <=100 ms until re-evidenced",
                    "latency miss must block rerun/replay/promotion claims",
                    "post-implementation static review must run before any fixed-snapshot rerun",
                ],
            },
        ],
        "static_contracts": {
            "default_off": "default runtime behavior must be unchanged unless explicit opt-in is set",
            "payload_no_leak": "no closed-loop outcome, simulator future state, selected effect, hidden DP score, or formal seed input",
            "finite_candidate_current_tick": "all features must be available from the current tick finite candidate set",
            "linear_score": "any later runtime coefficient must preserve score_k(w)=a_k^T w",
            "convex_master": "simplex/CVaR/L2 master must remain convex",
            "fallback": "invalid payload, missing route geometry, or latency miss must fail closed",
            "hard_blocker_separation": "DP kinematic and topology blockers remain separately auditable",
            "absolute_guard": "absolute lateral guard remains diagnostic-only",
            "dp_fixed": "DP weights, config, source code, and fixed commit remain unchanged",
        },
        "verification_requirements": [
            "unit tests for disabled/default-off selector equivalence",
            "unit tests for opt-in payload availability and fail-closed behavior",
            "unit tests for payload no-leak metadata and current-tick-only signatures",
            "unit tests for finite and nonnegative diagnostic coefficients",
            "unit tests for hard-blocker separation and absolute-guard diagnostic-only behavior",
            "static review after implementation before any rerun gate",
            "AutoDL py_compile and pytest revalidation with HEADS.txt and SHA256SUMS",
        ],
        "artifact_and_audit_requirements": [
            "record local/GitHub/AutoDL CAMP HEAD and fixed DP HEAD",
            "record source unit-tests-only artifact path and SHA256SUMS",
            "write implementation plan JSON and Markdown artifacts",
            "write exit code logs and artifact SHA256SUMS",
            "append audit with status, evidence, SHA, math boundary, decision, and next gate",
            "commit, push, and fast-forward AutoDL CAMP to the same HEAD",
            "re-read audit tail before any further gate",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    root = Path(root)
    files = {name: root / name for name in REQUIRED_SOURCE_FILES}
    exists = root.is_dir()
    present = {name: path.is_file() for name, path in files.items()}
    return {
        "root": str(root),
        "exists": exists,
        "required_files_present": bool(exists and all(present.values())),
        "present_files": present,
        "sha256sums_ok": _sha256sum_check(root / SHA256SUMS)[0],
        "sha256sums_details": _sha256sum_check(root / SHA256SUMS)[1],
        "heads": _parse_key_value_file(root / HEADS),
        "decision": _parse_key_value_file(root / UNIT_TESTS_DECISION),
        "exit_code": _read_text(root / EXIT_CODE).strip() or None,
        "py_compile_exit": _read_text(root / PY_COMPILE_EXIT).strip() or None,
        "pytest_unit_tests_exit": _read_text(root / PYTEST_UNIT_TESTS_EXIT).strip()
        or None,
        "pytest_related_exit": _read_text(root / PYTEST_RELATED_EXIT).strip() or None,
        "sha256sums_check_exit": _read_text(root / SHA256SUMS_CHECK_EXIT).strip()
        or None,
        "py_compile_err_bytes": _file_size(root / PY_COMPILE_ERR),
        "pytest_unit_tests_err_bytes": _file_size(root / PYTEST_UNIT_TESTS_ERR),
        "pytest_related_err_bytes": _file_size(root / PYTEST_RELATED_ERR),
    }


def _source_decision(artifact: dict[str, Any]) -> dict[str, Any]:
    raw = artifact.get("decision", {})
    result = {
        "status": raw.get("status"),
        "unit_tests_only_complete": _parse_bool(raw.get("unit_tests_only_complete")),
        "test_groups": _split_csv(raw.get("test_groups")),
        "forbidden_flags": {
            key: _parse_bool(raw.get(key)) for key in FORBIDDEN_SOURCE_FLAGS
        },
    }
    return result


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_artifact_exists", artifact["exists"], True),
        _check_equal("source_required_files_present", artifact["required_files_present"], True),
        _check_equal("source_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("source_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal("source_py_compile_exit_zero", artifact["py_compile_exit"], "0"),
        _check_equal(
            "source_pytest_unit_tests_exit_zero",
            artifact["pytest_unit_tests_exit"],
            "0",
        ),
        _check_equal(
            "source_pytest_related_exit_zero",
            artifact["pytest_related_exit"],
            "0",
        ),
        _check_equal(
            "source_sha256sums_check_exit_zero",
            artifact["sha256sums_check_exit"],
            "0",
        ),
        _check_equal("source_py_compile_err_empty", artifact["py_compile_err_bytes"], 0),
        _check_equal(
            "source_pytest_unit_tests_err_empty",
            artifact["pytest_unit_tests_err_bytes"],
            0,
        ),
        _check_equal(
            "source_pytest_related_err_empty",
            artifact["pytest_related_err_bytes"],
            0,
        ),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    heads = artifact.get("heads", {})
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
        _check_equal(
            "source_camp_head_matches_source_origin",
            heads.get("CAMP_HEAD"),
            heads.get("CAMP_ORIGIN_MAIN"),
        ),
        _check_equal("source_dp_head_fixed", heads.get("DP_HEAD"), EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    forbidden = {
        key: value for key, value in source["forbidden_flags"].items() if value
    }
    return [
        _check_equal("source_status_complete", source["status"], SOURCE_COMPLETE_STATUS),
        _check_equal(
            "source_unit_tests_only_complete",
            source["unit_tests_only_complete"],
            True,
        ),
        _check_equal("source_forbidden_flags_clear", forbidden, {}),
        _check_equal("source_test_group_count", len(source["test_groups"]) >= 6, True),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "product_code_implementation_plan_only",
        ),
        _check_equal(
            "plan_product_files_declared",
            plan["product_code_candidate_files"],
            list(PRODUCT_IMPLEMENTATION_CANDIDATE_FILES),
        ),
        _check_equal("plan_has_five_components", len(plan["components"]), 5),
        _check_equal("plan_mentions_default_off", "default-off" in text, True),
        _check_equal("plan_mentions_opt_in", "opt-in" in text, True),
        _check_equal("plan_mentions_no_leak", "no-leak" in text or "future_outcome_leakage=false" in text, True),
        _check_equal("plan_mentions_current_tick", "current-tick" in text, True),
        _check_equal("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("plan_mentions_convex_master", "simplex/cvar/l2" in text, True),
        _check_equal("plan_mentions_latency_budget", "p95" in text and "latency" in text, True),
        _check_equal("plan_mentions_fallback", "fail closed" in text or "fail-closed" in text, True),
        _check_equal("plan_mentions_comfort_progress", "comfort" in text and "progress" in text, True),
        _check_equal("plan_mentions_hard_blocker", "hard blocker" in text or "hard-blocker" in text, True),
        _check_equal("plan_mentions_absolute_guard", "absolute lateral guard" in text, True),
        _check_equal("plan_blocks_dp_modification", "dp weights, config, source code" in text, True),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal(
            "boundary_current_gate_blocks_product_code_edits",
            decision["implementation_code_edit_authorized"],
            False,
        ),
        _check_equal(
            "boundary_recommended_next_gate_requires_authorization",
            decision["recommended_next_gate_requires_explicit_authorization"],
            True,
        ),
        _check_equal(
            "boundary_does_not_auto_authorize_next_gate",
            decision["authorized_next_work"],
            None,
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
        _check_equal("boundary_blocks_full36", decision["full36_authorized"], False),
        _check_equal("boundary_blocks_camp_retraining", decision["camp_retraining_authorized"], False),
        _check_equal("boundary_blocks_atom_promotion", decision["atom_promotion_authorized"], False),
        _check_equal(
            "boundary_blocks_online_selector_promotion",
            decision["online_selector_promotion_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal(
            "boundary_blocks_camp_over_dp_top1_claim",
            decision["camp_over_dp_top1_claim_authorized"],
            False,
        ),
        _check_equal("boundary_blocks_classic_benders", decision["classic_benders_claim_authorized"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "implementation_plan_ready": passed,
        "authorized_next_work": None,
        "selected_next_work": None,
        "recommended_next_gate": RECOMMENDED_NEXT_GATE if passed else None,
        "recommended_next_gate_requires_explicit_authorization": True,
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


def _parse_key_value_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


if __name__ == "__main__":
    main()
