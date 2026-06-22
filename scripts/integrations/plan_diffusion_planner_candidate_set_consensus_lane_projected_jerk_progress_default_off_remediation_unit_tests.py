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
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as REVIEW_AUTHORIZED_NEXT_WORK,
    DEFAULT_DEVELOPMENT_ROOT,
    READY_STATUS as REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_unit_tests_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_unit_tests_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_unit_tests_only"
)
DEFAULT_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_remediation_static_contract_review_3da7f3b"
)
REVIEW_JSON = "candidate_set_consensus_lane_projected_jerk_progress_remediation_static_contract_review.json"

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
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only default-off unit tests for the lane-projected "
            "jerk/progress remediation contracts."
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
    artifact = _artifact_summary(
        review_root,
        required_files=(REVIEW_JSON, SHA256SUMS, EXIT_CODE, HEADS),
    )
    review_payload = _load_json_if_present(review_root / REVIEW_JSON)
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
                "dp_camp_candidate_set_consensus_lane_projected_"
                "jerk_progress_default_off_remediation_unit_tests_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only unit-test contract for a later default-off "
                "remediation implementation"
            ),
            "plan_only": True,
            "unit_tests_only_next": True,
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
                "This plan reads only the static contract review artifact. It "
                "does not edit implementation code, implement a remediation, "
                "create candidates, rerun the screen, run DP, run replay, "
                "recompute outcomes, define runtime atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition."
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
        "# Lane-Projected Jerk/Progress Default-Off Remediation Unit Tests Plan",
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
            "- implementation code edits are not authorized",
            "- candidate generation execution is not authorized",
            "- fixed-snapshot screen rerun is not authorized",
            "- replay is not authorized",
            "- formal seeds 11/12/13 remain frozen and unused",
            "- Full36 is not authorized",
            "- atom promotion, CAMP retraining, and online selector changes are not authorized",
            "- DP weights and DP code must remain fixed",
            "- no safety-benefit claim or classical Benders claim is authorized",
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_remediation_unit_tests_only` is authorized if all "
                "checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path, *, required_files: tuple[str, ...]) -> dict[str, Any]:
    files = {name: (root / name).is_file() for name in required_files}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    exit_code = None
    exit_path = root / EXIT_CODE
    if exit_path.is_file():
        exit_code = exit_path.read_text(encoding="utf-8").strip()
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "exit_code": exit_code,
    }


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
        "implementation_code_edit_authorized": bool(
            decision.get("implementation_code_edit_authorized")
        ),
        "candidate_generation_execution_authorized": bool(
            decision.get("candidate_generation_execution_authorized")
        ),
        "fixed_snapshot_screen_rerun_authorized": bool(
            decision.get("fixed_snapshot_screen_rerun_authorized")
        ),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "full36_authorized": bool(decision.get("full36_authorized")),
        "online_selector_authorized": bool(decision.get("online_selector_authorized")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
        "classic_benders_claim_authorized": bool(
            decision.get("classic_benders_claim_authorized")
        ),
        "contract_status": contract_status,
        "selected_next_work": review.get("selected_next_work"),
    }


def _unit_test_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "default_off_remediation_unit_tests_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "test_groups": [
            {
                "name": "relative_comfort_threshold_unit_tests",
                "purpose": (
                    "pin _comfort_admissible and _comfort_failure_classes "
                    "behavior for jerk, lateral, rollout, progress, and "
                    "smoothness blockers"
                ),
                "required_assertions": [
                    "lower_union_red, hard_feasible, and progress_feasible remain required",
                    "zero or configured comfort budgets are enforced deterministically",
                    "failure-class labels match the violated budget family",
                    "all synthetic inputs use current-tick fields only",
                ],
                "forbidden_coverage": (
                    "no DP runtime, no snapshot replay, no outcome labels, no "
                    "candidate generation"
                ),
            },
            {
                "name": "hard_feasibility_label_unit_tests",
                "purpose": (
                    "pin hard-reason pass-through and reporting without "
                    "duplicating or modifying DP internals"
                ),
                "required_assertions": [
                    "hard_reasons are preserved as evaluator labels",
                    "hard_reason_counts aggregate deterministic synthetic rows",
                    "underprogress is separate from DP hard infeasibility",
                ],
                "forbidden_coverage": (
                    "no DP code, weights, configs, invocation changes, or "
                    "classic Benders framing"
                ),
            },
            {
                "name": "latency_reporting_unit_tests",
                "purpose": (
                    "pin candidate_build and total latency fields before any "
                    "future pruning or caching remediation"
                ),
                "required_assertions": [
                    "candidate_build and total summaries are present",
                    "latency tests use deterministic synthetic timing inputs",
                    "no hardware performance or safety-benefit claim is made",
                ],
                "forbidden_coverage": (
                    "no GPU timing claim, no DP reward/tracker mutation, no "
                    "screen rerun"
                ),
            },
            {
                "name": "policy_default_off_unit_tests",
                "purpose": (
                    "pin that lane_projected_jerk_progress_red_stop and any "
                    "future remediation option remain opt-in"
                ),
                "required_assertions": [
                    "default generator_policy remains lane_centerline_red_stop",
                    "remediation options are disabled unless explicitly selected",
                    "CLI choices expose opt-in behavior without online selector changes",
                ],
                "forbidden_coverage": (
                    "no online selector promotion, no atom promotion, no CAMP "
                    "training"
                ),
            },
            {
                "name": "math_boundary_unit_tests",
                "purpose": (
                    "pin that any later test scaffold preserves linear scoring "
                    "and convex master assumptions"
                ),
                "required_assertions": [
                    "no test introduces future labels or outcome features",
                    "score_k(w)=a_k^T w remains the allowed atom contract",
                    "simplex/CVaR/L2 master convexity assumptions are preserved",
                ],
                "forbidden_coverage": (
                    "no classical Benders claim, no DP-side decomposition, no "
                    "online lambda selection"
                ),
            },
        ],
        "accept_criteria": [
            "unit-test-only implementation plan is complete",
            "all planned tests are synthetic or static and do not call DP",
            "no production implementation files are authorized in the next gate",
            "no candidate generation, screen rerun, replay, Full36, or formal seeds",
            "no CAMP retraining, atom promotion, online selector change, or DP modification",
            "next gate records HEADS, SHA256SUMS, and test output before any later implementation gate",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("review_artifact_exists", artifact["exists"], True),
        _check_equal("review_required_files_present", artifact["required_files_present"], True),
        _check_equal("review_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("review_exit_code_zero", artifact["exit_code"], "0"),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _review_authorization_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
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
        _check_equal(
            "review_implementation_edit_not_authorized",
            source["implementation_code_edit_authorized"],
            False,
        ),
        _check_equal(
            "review_candidate_generation_not_authorized",
            source["candidate_generation_execution_authorized"],
            False,
        ),
        _check_equal(
            "review_screen_rerun_not_authorized",
            source["fixed_snapshot_screen_rerun_authorized"],
            False,
        ),
        _check_equal("review_replay_not_authorized", source["new_replay_authorized"], False),
        _check_equal("review_formal_seeds_not_authorized", source["formal_seeds_authorized"], False),
        _check_equal("review_full36_not_authorized", source["full36_authorized"], False),
        _check_equal("review_online_selector_not_authorized", source["online_selector_authorized"], False),
        _check_equal("review_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("review_retraining_not_authorized", source["camp_retraining_authorized"], False),
        _check_equal("review_dp_modification_not_authorized", source["dp_modification_authorized"], False),
        _check_equal(
            "review_benders_claim_not_authorized",
            source["classic_benders_claim_authorized"],
            False,
        ),
    ]


def _review_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "relative_comfort_contract",
        "hard_feasibility_contract",
        "latency_contract",
        "policy_default_off_contract",
    }
    observed = set(source["contract_status"])
    checks = [
        _check_equal("review_contract_names_present", sorted(observed), sorted(expected)),
    ]
    checks.extend(
        _check_equal(f"review_contract_{name}_true", source["contract_status"].get(name), True)
        for name in sorted(expected)
    )
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "plan_selection_type",
            plan["selection_type"],
            "default_off_remediation_unit_tests_plan_only",
        ),
        _check_equal("plan_has_five_test_groups", len(plan["test_groups"]), 5),
        _check_equal("plan_mentions_relative_comfort", "relative_comfort" in text, True),
        _check_equal("plan_mentions_hard_feasibility", "hard_feasibility" in text, True),
        _check_equal("plan_mentions_latency", "latency" in text, True),
        _check_equal("plan_mentions_default_off", "default" in text and "opt-in" in text, True),
        _check_equal("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
        _check_equal("plan_blocks_dp", "no dp" in text, True),
        _check_equal("plan_blocks_replay", "no candidate generation" in text and "replay" in text, True),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_implementation_edits", decision["implementation_code_edit_authorized"], False),
        _check_equal("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"], False),
        _check_equal("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"], False),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
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
        "implementation_code_edit_authorized": False,
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
        item = root / name.strip()
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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    main()
