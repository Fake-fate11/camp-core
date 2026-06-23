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
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_remediation_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_only"
)

DEFAULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "remediation_static_contract_review_3a04d21"
)
REVIEW_JSON = "fixed_snapshot_screen_rerun_remediation_static_contract_review.json"
REVIEW_JSON_COMPAT = "remediation_static_contract_review.json"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
REVIEW_EXIT = "REVIEW_EXIT"
REVIEW_COMMAND_EXIT = "REVIEW_COMMAND_EXIT"
EXIT_CODE = "EXIT_CODE"

CONTRACTS = (
    "relative_comfort_static_contract",
    "hard_blocker_separation_contract",
    "latency_static_contract",
    "absolute_guard_subset_contract",
    "policy_default_off_contract",
)

BLOCKED_ACTIONS = (
    "implementation_authorized",
    "implementation_code_edit_authorized",
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
            "Plan-only unit tests for the default-off fixed-snapshot rerun "
            "remediation contracts."
        )
    )
    parser.add_argument("--review_root", type=Path, default=Path(DEFAULT_REVIEW_ROOT))
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
        review_root=args.review_root,
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
    review_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    review_json_name = _review_json_name(review_root)
    review_exit_name = _review_exit_name(review_root)
    artifact = _artifact_summary(
        review_root,
        required_files=(review_json_name, review_exit_name, HEADS, SHA256SUMS),
        review_json_name=review_json_name,
        review_exit_name=review_exit_name,
    )
    review_payload = _load_json_if_present(review_root / review_json_name)
    source = _source_summary(review_payload)
    plan = _unit_test_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_review_authorization_checks(source),
        *_review_contract_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "unit_tests_plan_v1"
            ),
            "label": label,
            "role": "plan-only unit-test contract for a later test implementation gate",
            "plan_only": True,
            "unit_tests_implementation_next": True,
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
                "This plan reads only the static contract review artifact. It "
                "does not implement tests, edit implementation code, implement "
                "a remediation, create candidates, rerun the screen, run DP, "
                "run replay, use formal seeds, recompute outcomes, define "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, claim safety "
                "benefit, claim CAMP is better than DP Top-1, or claim a "
                "DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "review_artifact": artifact,
        "source_summary": source,
        "unit_test_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["unit_test_plan"]
    lines = [
        "# Default-Off Fixed-Snapshot Rerun Unit Tests Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Review",
        "",
        f"- Review status: `{source['status']}`",
        f"- Review next work: `{source['authorized_next_work']}`",
        f"- Contracts: `{source['contract_status']}`",
        "",
        "## Planned Test Groups",
        "",
    ]
    for item in plan["test_groups"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - purpose: {item['purpose']}")
        lines.append(f"  - required assertions: `{item['required_assertions']}`")
        lines.append(f"  - forbidden coverage: {item['forbidden_coverage']}")
    lines.extend(["", "## Acceptance Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- unit-test implementation is not authorized in this gate",
            "- implementation code edits are not authorized",
            "- candidate generation execution is not authorized",
            "- fixed-snapshot screen rerun is not authorized",
            "- replay is not authorized",
            "- formal seeds 11/12/13 remain frozen and unused",
            "- Full36 is not authorized",
            "- atom promotion, CAMP retraining, and online selector changes are not authorized",
            "- DP weights and DP code must remain fixed",
            "- no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "- no DP-side classical Benders claim is authorized",
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "unit_tests_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(
    root: Path,
    *,
    required_files: tuple[str, ...],
    review_json_name: str,
    review_exit_name: str,
) -> dict[str, Any]:
    files = {name: (root / name).is_file() for name in required_files}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "review_json_file": review_json_name,
        "review_exit_file": review_exit_name,
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "review_exit": _read_text(root / review_exit_name).strip() or None,
        "heads_text_present": bool(_read_text(root / HEADS).strip()),
    }


def _review_json_name(review_root: Path) -> str:
    if (review_root / REVIEW_JSON).is_file():
        return REVIEW_JSON
    return REVIEW_JSON_COMPAT


def _review_exit_name(review_root: Path) -> str:
    if (review_root / REVIEW_EXIT).is_file():
        return REVIEW_EXIT
    if (review_root / REVIEW_COMMAND_EXIT).is_file():
        return REVIEW_COMMAND_EXIT
    return EXIT_CODE


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    contracts = _list(review.get("contracts"))
    contract_status = {
        str(_dict(item).get("name")): bool(_dict(item).get("status"))
        for item in contracts
    }
    return {
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_next_work": review.get("selected_next_work"),
        "contract_status": contract_status,
        **{key: bool(decision.get(key)) for key in BLOCKED_ACTIONS},
    }


def _unit_test_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "fixed_snapshot_screen_rerun_unit_tests_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "test_groups": [
            {
                "name": "relative_comfort_static_contract_unit_tests",
                "purpose": (
                    "pin comfort admissibility and failure-class behavior for "
                    "jerk, lateral, rollout-distance, rollout-jerk, "
                    "rollout-lateral, progress-loss, and smoothness blockers"
                ),
                "required_assertions": [
                    "lower-union-red, hard-feasible, and progress-feasible remain prerequisites",
                    "violated comfort budget families produce deterministic failure labels",
                    "admissible rows are counted only when every current-tick comfort budget passes",
                    "all synthetic fixtures use current-tick fields only",
                ],
                "forbidden_coverage": (
                    "no DP runtime, no snapshot replay, no outcome labels, no "
                    "candidate generation"
                ),
            },
            {
                "name": "hard_blocker_separation_unit_tests",
                "purpose": (
                    "pin hard-blocker aggregation and separation from "
                    "underprogress or comfort deficits"
                ),
                "required_assertions": [
                    "hard_reasons are preserved as evaluator labels over fixed candidates",
                    "hard_reason_counts aggregate deterministic synthetic rows",
                    "underprogress remains separate from DP hard infeasibility",
                    "no test calls or mocks DP internals as a source of new labels",
                ],
                "forbidden_coverage": (
                    "no DP code, weights, configs, invocation changes, or "
                    "classic Benders framing"
                ),
            },
            {
                "name": "latency_static_contract_unit_tests",
                "purpose": (
                    "pin candidate_build and total latency report fields before "
                    "any future pruning, caching, or vectorization remediation"
                ),
                "required_assertions": [
                    "candidate_build and total summaries are emitted when synthetic timing data exists",
                    "latency gate failures remain diagnostic only",
                    "tests make no hardware performance, safety, or CAMP-superiority claim",
                ],
                "forbidden_coverage": (
                    "no GPU timing claim, no DP reward/tracker mutation, no "
                    "screen rerun"
                ),
            },
            {
                "name": "absolute_guard_subset_unit_tests",
                "purpose": (
                    "pin absolute lateral guard rows as a diagnostic subset, "
                    "not promotion or safety evidence"
                ),
                "required_assertions": [
                    "absolute guard support remains a separate artifact-level signal",
                    "subset support does not authorize atom promotion or online selector changes",
                    "subset support does not imply CAMP improvement over DP Top-1",
                ],
                "forbidden_coverage": (
                    "no safety-benefit claim, no screen rerun, no selector "
                    "promotion"
                ),
            },
            {
                "name": "policy_default_off_unit_tests",
                "purpose": (
                    "pin that lane_projected_jerk_progress_red_stop and later "
                    "remediation choices remain opt-in"
                ),
                "required_assertions": [
                    "default generator_policy remains lane_centerline_red_stop",
                    "remediation options remain disabled unless explicitly selected",
                    "CLI choices preserve opt-in behavior without online selector changes",
                ],
                "forbidden_coverage": (
                    "no online selector promotion, no atom promotion, no CAMP "
                    "training"
                ),
            },
            {
                "name": "math_boundary_unit_tests",
                "purpose": (
                    "pin that future test scaffolds preserve linear scoring "
                    "and convex master assumptions"
                ),
                "required_assertions": [
                    "no test introduces future labels or outcome features",
                    "score_k(w)=a_k^T w remains the allowed atom contract",
                    "simplex/CVaR/L2 master convexity assumptions are preserved",
                    "DP-side finite-candidate selection is not called classical Benders",
                ],
                "forbidden_coverage": (
                    "no DP-side decomposition, no online lambda selection, no "
                    "valid-cut claim"
                ),
            },
        ],
        "accept_criteria": [
            "unit-tests plan artifact is complete and source review checks pass",
            "planned tests are synthetic or static and do not call DP",
            "next gate may add tests only; production implementation files remain unauthorized",
            "no candidate generation, screen rerun, replay, Full36, or formal seeds",
            "no CAMP retraining, atom promotion, online selector change, or DP modification",
            "next gate must record HEADS, SHA256SUMS, and test output before any later implementation gate",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("review_artifact_exists", artifact["exists"], True),
        _check_equal("review_required_files_present", artifact["required_files_present"], True),
        _check_equal("review_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("review_exit_zero", artifact["review_exit"], "0"),
        _check_equal("review_heads_present", artifact["heads_text_present"], True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _review_authorization_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = [key for key in BLOCKED_ACTIONS if source.get(key)]
    return [
        _check_equal("review_status_complete", source["status"], REVIEW_READY_STATUS),
        _check_equal(
            "review_authorizes_unit_tests_plan",
            source["authorized_next_work"],
            REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "review_selected_unit_tests_plan",
            source["selected_next_work"],
            REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("review_blocked_actions_clear", blocked, []),
    ]


def _review_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    observed = set(source["contract_status"])
    checks = [
        _check_equal("review_contract_names_present", sorted(observed), sorted(CONTRACTS)),
    ]
    checks.extend(
        _check_equal(f"review_contract_{name}_true", source["contract_status"].get(name), True)
        for name in CONTRACTS
    )
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "fixed_snapshot_screen_rerun_unit_tests_plan_only",
        ),
        _check_equal("plan_has_six_test_groups", len(plan["test_groups"]), 6),
        _check_equal("plan_mentions_relative_comfort", "relative_comfort" in text, True),
        _check_equal("plan_mentions_hard_blocker", "hard_blocker" in text, True),
        _check_equal("plan_mentions_latency", "latency" in text, True),
        _check_equal("plan_mentions_absolute_guard", "absolute_guard" in text, True),
        _check_equal("plan_mentions_default_off", "default" in text and "opt-in" in text, True),
        _check_equal("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("plan_mentions_convex_master", "simplex/cvar/l2 master" in text, True),
        _check_equal("plan_blocks_dp", "no dp" in text, True),
        _check_equal("plan_blocks_replay", "no candidate generation" in text and "replay" in text, True),
        _check_equal("plan_blocks_safety_claim", "no safety-benefit claim" in text, True),
        _check_equal("plan_blocks_camp_superiority", "dp top-1" in text, True),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_test_implementation", decision["unit_test_implementation_authorized"], False),
        _check_equal("boundary_blocks_implementation_edits", decision["implementation_code_edit_authorized"], False),
        _check_equal("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"], False),
        _check_equal("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"], False),
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
        "unit_tests_plan_ready": passed,
        "unit_tests_only_authorized": passed,
        "unit_test_implementation_authorized": False,
        "implementation_code_edit_authorized": False,
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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    main()
