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
    SHA256SUMS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_post_implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_fixed_snapshot_screen_rerun_plan_only"
)
DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_IMPLEMENTATION_ARTIFACT_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_implementation_aaffbbe"
)
DEFAULT_SOURCE = (
    ROOT
    / "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
)
DEFAULT_TEST = (
    ROOT / "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
)

BLOCKED_ACTIONS = (
    "implementation_code_edit_authorized",
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
            "Static post-implementation contract review for the default-off "
            "lane-projected jerk/progress remediation implementation."
        )
    )
    parser.add_argument(
        "--implementation_artifact_root",
        type=Path,
        default=Path(DEFAULT_IMPLEMENTATION_ARTIFACT_ROOT),
    )
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--test_path", type=Path, default=DEFAULT_TEST)
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
        implementation_artifact_root=args.implementation_artifact_root,
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
    implementation_artifact_root: Path,
    source_path: Path,
    test_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(implementation_artifact_root)
    source = _source_summary(source_path)
    tests = _test_summary(test_path)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_contract_checks(source),
        *_test_contract_checks(tests),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_post_implementation_static_contract_review_v1"
            ),
            "label": label,
            "role": "static post-implementation contract review",
            "static_review_only": True,
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
                "This review reads only source text, focused tests, and the "
                "implementation artifact. It does not execute candidate "
                "generation, rerun the fixed-snapshot screen, run DP, run "
                "replay, define runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, modify DP "
                "weights or code, or claim a DP-side classical Benders "
                "decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "implementation_artifact": artifact,
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
        "# Lane-Projected Jerk/Progress Default-Off Remediation Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Contract",
        "",
        f"- Source path: `{source['path']}`",
        f"- Contracts: `{source['contracts']}`",
        "",
        "## Test Contract",
        "",
        f"- Test path: `{tests['path']}`",
        f"- Contracts: `{tests['contracts']}`",
        "",
        "## Boundaries",
        "",
        "- static review only; implementation edits are not authorized",
        "- candidate generation execution is not authorized",
        "- fixed-snapshot screen rerun execution is not authorized",
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
            "default_off_remediation_fixed_snapshot_screen_rerun_plan_only` "
            "is authorized if all checks pass. It is a plan-only gate and "
            "does not authorize rerun execution."
        ),
        "",
    ]
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = _artifact_required_files(root)
    files = {name: (root / name).is_file() for name in required}
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "py_compile_exit_ok": _exit_ok(root, "PY_COMPILE_EXIT"),
        "pytest_route_exit_ok": (
            _exit_ok(root, "PYTEST_ROUTE_EXIT")
            or _exit_ok(root, "PYTEST_UNIT_EXIT")
        ),
        "pytest_related_exit_ok": _exit_ok(root, "PYTEST_RELATED_EXIT"),
        "py_compile_err_bytes": _file_size(root / "PY_COMPILE.err"),
        "pytest_route_err_bytes": _first_file_size(
            root,
            ("PYTEST_ROUTE.err", "PYTEST_UNIT.err"),
        ),
        "pytest_related_err_bytes": _file_size(root / "PYTEST_RELATED.err"),
        "sha256sums_ok": _sha256sum_check(root / SHA256SUMS),
    }


def _source_summary(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    contracts = {
        "diagnostic_function_present": (
            "def route_topology_candidate_construction_diagnostics" in text
        ),
        "snapshot_payload_present": (
            '"candidate_construction_diagnostics": construction_diagnostics or {}'
            in text
        ),
        "default_policy_preserved": (
            'generator_policy: str = "lane_centerline_red_stop"' in text
        ),
        "fail_closed_reasons_present": all(
            token in text
            for token in (
                "candidate_tensor_invalid",
                "selected_index_out_of_range",
                "lane_geometry_invalid",
                "red_route_ahead_missing",
                "red_stop_distance_window",
            )
        ),
        "json_number_helper_present": "def _json_number" in text,
        "candidate_rows_not_diagnostic_payload": (
            '"candidate_rows": rows' in text
            and '"candidate_construction_diagnostics": construction_diagnostics or {}'
            in text
        ),
        "current_tick_scalar_guard_present": all(
            token in text
            for token in (
                "def _requires_current_tick_scalar_evidence",
                "def _current_tick_scalar_failure_reason",
                "current_tick_scalar_invalid",
                "_current_tick_scalar_failure_reason(current_speed_mps, dt)",
            )
        ),
        "opt_in_scalar_guard_only": (
            'return config.generator_policy == "lane_projected_jerk_progress_red_stop"'
            in text
        ),
        "config_budget_failure_labels_present": all(
            token in text
            for token in (
                "progress_budget = _max_finite_budget(config.progress_loss_budgets_m)",
                "smoothness_budget = _max_finite_budget(config.smoothness_loss_budgets)",
                "> config.command_jerk_worse_budget_mps3 + TOL",
                "> config.rollout_distance_loss_budget_m + TOL",
            )
        ),
        "route_failure_classes_passes_config": (
            "route_failure_classes(row, config=config)" in text
            and "_comfort_failure_classes(row, config=config)" in text
        ),
    }
    return {
        "path": str(path),
        "exists": path.is_file(),
        "contracts": contracts,
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _test_summary(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    contracts = {
        "fail_closed_test_present": (
            "test_route_topology_construction_diagnostics_fail_closed_without_red_ahead"
            in text
        ),
        "zero_candidate_payload_test_present": (
            "test_route_topology_zero_candidate_row_carries_construction_diagnostics"
            in text
        ),
        "json_scalar_clean_asserted": (
            "isinstance(value, (str, bool, int, float))" in text
        ),
        "generated_scores_absence_asserted": '"generated_scores" not in row' in text,
        "existing_jerk_progress_tests_preserved": (
            "test_route_topology_generator_jerk_progress_synthetic_bounds" in text
        ),
        "current_tick_scalar_guard_test_present": (
            "test_route_topology_jerk_progress_requires_current_tick_scalars"
            in text
        ),
        "default_policy_unchanged_test_present": (
            'default_meta[0]["variant"] == "lane_centerline_red_stop"' in text
        ),
        "config_budget_failure_label_test_present": (
            "test_route_topology_comfort_failure_labels_follow_config_budgets"
            in text
        ),
        "config_budget_report_counts_asserted": (
            'report["failure_class_counts"][failure_class]' in text
            and 'report["by_snapshot"][0]["failure_class_counts"][failure_class]'
            in text
        ),
    }
    return {
        "path": str(path),
        "exists": path.is_file(),
        "contracts": contracts,
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("implementation_artifact_exists", artifact["exists"], True),
        _check_equal(
            "implementation_artifact_required_files_present",
            artifact["required_files_present"],
            True,
        ),
        _check_equal("implementation_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("implementation_py_compile_exit_ok", artifact["py_compile_exit_ok"], True),
        _check_equal("implementation_pytest_route_exit_ok", artifact["pytest_route_exit_ok"], True),
        _check_equal("implementation_pytest_related_exit_ok", artifact["pytest_related_exit_ok"], True),
        _check_equal("implementation_py_compile_err_empty", artifact["py_compile_err_bytes"], 0),
        _check_equal("implementation_pytest_route_err_empty", artifact["pytest_route_err_bytes"], 0),
        _check_equal("implementation_pytest_related_err_empty", artifact["pytest_related_err_bytes"], 0),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [_check_equal("source_file_exists", source["exists"], True)]
    checks.extend(
        _check_equal(f"source_{name}", value, True)
        for name, value in source["contracts"].items()
    )
    return checks


def _test_contract_checks(tests: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [_check_equal("test_file_exists", tests["exists"], True)]
    checks.extend(
        _check_equal(f"test_{name}", value, True)
        for name, value in tests["contracts"].items()
    )
    return checks


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_implementation_edits", decision["implementation_code_edit_authorized"], False),
        _check_equal("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"], False),
        _check_equal("boundary_blocks_screen_rerun_execution", decision["fixed_snapshot_screen_rerun_authorized"], False),
        _check_equal("boundary_next_gate_plan_only", decision["fixed_snapshot_screen_rerun_plan_authorized"], True),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal("boundary_blocks_benders", decision["classic_benders_claim_authorized"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "post_implementation_static_contract_review_complete": passed,
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
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _sha256sum_check(path: Path) -> bool:
    if not path.is_file():
        return False
    root = path.parent
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            return False
        expected, name = parts
        item = Path(name.strip())
        if not item.is_absolute():
            item = root / item
        if not item.is_file():
            return False
        ok = ok and _sha256(item) == expected
    return ok


def _artifact_required_files(root: Path) -> tuple[str, ...]:
    if (root / "PYTEST_UNIT.log").is_file() or (root / "PYTEST_UNIT_EXIT").is_file():
        return (
            HEADS,
            "PY_COMPILE.log",
            "PY_COMPILE.err",
            "PY_COMPILE_EXIT",
            "PYTEST_UNIT.log",
            "PYTEST_UNIT.err",
            "PYTEST_UNIT_EXIT",
            "PYTEST_RELATED.log",
            "PYTEST_RELATED.err",
            "PYTEST_RELATED_EXIT",
            SHA256SUMS,
        )
    return (
        HEADS,
        "PY_COMPILE.log",
        "PY_COMPILE.err",
        "PYTEST_ROUTE.log",
        "PYTEST_ROUTE.err",
        "PYTEST_RELATED.log",
        "PYTEST_RELATED.err",
        EXIT_CODE,
        SHA256SUMS,
    )


def _exit_ok(root: Path, name: str) -> bool:
    direct = root / name
    if direct.is_file():
        return _read_text(direct).strip() == "0"
    legacy = _read_text(root / EXIT_CODE)
    return f"{name}=0" in legacy


def _first_file_size(root: Path, names: tuple[str, ...]) -> int | None:
    for name in names:
        size = _file_size(root / name)
        if size is not None:
            return size
    return None


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
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


if __name__ == "__main__":
    main()
