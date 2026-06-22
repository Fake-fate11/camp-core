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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    DEFAULT_DEVELOPMENT_ROOT,
    READY_STATUS as DESIGN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "remediation_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "remediation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "default_off_remediation_unit_tests_plan_only"
)
DEFAULT_DESIGN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_remediation_design_plan_cc3abd9"
)
DESIGN_JSON = "candidate_set_consensus_lane_projected_jerk_progress_remediation_design_plan.json"
DEFAULT_SOURCE_PATH = (
    ROOT / "scripts" / "integrations" / "analyze_diffusion_planner_route_topology_candidate_screen.py"
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
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static contract review for the remediation design plan. "
            "This checks existing source contracts and authorizes only a later "
            "unit-test plan."
        )
    )
    parser.add_argument("--design_root", type=Path, default=Path(DEFAULT_DESIGN_ROOT))
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE_PATH)
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
        design_root=args.design_root,
        source_path=args.source_path,
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
    design_root: Path,
    source_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(
        design_root,
        required_files=(DESIGN_JSON, SHA256SUMS, EXIT_CODE, HEADS),
    )
    design_payload = _load_json_if_present(design_root / DESIGN_JSON)
    source_text = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
    source = _source_summary(design_payload)
    review = _static_contract_review(source_text)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_design_authorization_checks(source),
        *_source_file_checks(source_path, source_text),
        *_contract_checks(review),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_"
                "jerk_progress_remediation_static_contract_review_v1"
            ),
            "label": label,
            "role": (
                "read-only source and artifact review before any default-off "
                "remediation implementation"
            ),
            "read_only": True,
            "source_inspection_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This review reads only the remediation design artifact and "
                "existing CAMP source. It does not edit source code, implement "
                "a new candidate generator, create candidates, rerun the "
                "screen, run DP, run replay, recompute outcomes, define runtime "
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
        "design_artifact": artifact,
        "source_summary": source,
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    review = report["static_contract_review"]
    lines = [
        "# Lane-Projected Jerk/Progress Remediation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Design",
        "",
        f"- Design status: `{source['status']}`",
        f"- Design next work: `{source['authorized_next_work']}`",
        f"- Threads: `{source['thread_names']}`",
        "",
        "## Static Contracts",
        "",
    ]
    for item in review["contracts"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - status: `{item['status']}`")
        lines.append(f"  - evidence: `{item['evidence']}`")
        lines.append(f"  - allowed next step: {item['allowed_next_step']}")
    lines.extend(["", "## Rejection Rules", ""])
    for item in review["rejection_rules"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- source edits are not authorized",
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
                "default_off_remediation_unit_tests_plan_only` is authorized "
                "if all checks pass."
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
    design = _dict(payload.get("remediation_design"))
    thread_names = [
        _dict(item).get("name") for item in _list(design.get("remediation_threads"))
    ]
    return {
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
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
        "thread_names": thread_names,
        "selected_next_work": design.get("selected_next_work"),
        "next_gate_checks": _list(design.get("next_gate_checks")),
    }


def _static_contract_review(source_text: str) -> dict[str, Any]:
    contracts = [
        {
            "name": "relative_comfort_contract",
            "status": _all_present(
                source_text,
                (
                    "_comfort_admissible",
                    "_comfort_failure_classes",
                    "command_jerk_worse_budget_mps3",
                    "command_lateral_worse_budget_mps2",
                    "rollout_jerk_worse_budget_mps3",
                    "rollout_lateral_worse_budget_mps2",
                    "progress_loss_budgets_m",
                    "smoothness_loss_budgets",
                ),
            ),
            "evidence": "comfort budgets and failure classes are explicit in source",
            "allowed_next_step": (
                "plan default-off unit tests for synthetic threshold and "
                "failure-class behavior only"
            ),
        },
        {
            "name": "hard_feasibility_contract",
            "status": _all_present(
                source_text,
                (
                    "reward_hard_feasibility",
                    "dp_kinematic",
                    "dp_lane_crossing",
                    "dp_red_light",
                    "route_topology_hard_feasible_but_underprogress",
                    "_validate_config",
                ),
            ),
            "evidence": "hard blockers remain reward/evaluator labels, not DP edits",
            "allowed_next_step": (
                "plan static tests that classify immutable hard blockers "
                "without changing DP invocation"
            ),
        },
        {
            "name": "latency_contract",
            "status": _all_present(
                source_text,
                (
                    "\"candidate_build\"",
                    "\"total\"",
                    "_summarize_latency",
                    "candidate_build",
                    "time.perf_counter",
                ),
            ),
            "evidence": "candidate-build and total timing are explicit report fields",
            "allowed_next_step": (
                "plan default-off unit tests for deterministic pruning or "
                "caching contracts before any timing claim"
            ),
        },
        {
            "name": "policy_default_off_contract",
            "status": _all_present(
                source_text,
                (
                    "generator_policy",
                    "lane_projected_jerk_progress_red_stop",
                    "choices=(",
                    "default=\"lane_centerline_red_stop\"",
                ),
            ),
            "evidence": "the lane-projected jerk/progress policy is selectable, not default",
            "allowed_next_step": (
                "plan unit tests that preserve default-off behavior for any "
                "later remediation option"
            ),
        },
    ]
    return {
        "selection_type": "remediation_static_contract_review_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "contracts": contracts,
        "rejection_rules": [
            "reject if source edits are needed in this gate",
            "reject if candidate generation or fixed-screen rerun is requested",
            "reject if replay, Full36, or formal seeds are requested",
            "reject if DP code, weights, config, or invocation changes are needed",
            "reject if score_k(w)=a_k^T w or convex master preservation is not explicit",
            "reject if any safety-benefit or classical Benders claim is made",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("design_artifact_exists", artifact["exists"], True),
        _check_equal("design_required_files_present", artifact["required_files_present"], True),
        _check_equal("design_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("design_exit_code_zero", artifact["exit_code"], "0"),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _design_authorization_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("design_status_ready", source["status"], DESIGN_READY_STATUS),
        _check_equal(
            "design_authorizes_static_contract_review",
            source["authorized_next_work"],
            DESIGN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "design_selected_static_contract_review",
            source["selected_next_work"],
            DESIGN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "design_candidate_generation_not_authorized",
            source["candidate_generation_execution_authorized"],
            False,
        ),
        _check_equal(
            "design_screen_rerun_not_authorized",
            source["fixed_snapshot_screen_rerun_authorized"],
            False,
        ),
        _check_equal("design_replay_not_authorized", source["new_replay_authorized"], False),
        _check_equal("design_formal_seeds_not_authorized", source["formal_seeds_authorized"], False),
        _check_equal("design_full36_not_authorized", source["full36_authorized"], False),
        _check_equal("design_online_selector_not_authorized", source["online_selector_authorized"], False),
        _check_equal("design_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("design_retraining_not_authorized", source["camp_retraining_authorized"], False),
        _check_equal("design_dp_modification_not_authorized", source["dp_modification_authorized"], False),
        _check_equal(
            "design_benders_claim_not_authorized",
            source["classic_benders_claim_authorized"],
            False,
        ),
        _check_equal(
            "design_threads_present",
            sorted(source["thread_names"]),
            [
                "hard_feasibility_contract",
                "latency_contract",
                "relative_comfort_contract",
            ],
        ),
    ]


def _source_file_checks(source_path: Path, source_text: str) -> list[dict[str, Any]]:
    return [
        _check_equal("source_file_exists", source_path.is_file(), True),
        _check_equal("source_file_nonempty", bool(source_text), True),
        _check_equal(
            "source_route_topology_candidate_screen",
            source_path.name,
            "analyze_diffusion_planner_route_topology_candidate_screen.py",
        ),
    ]


def _contract_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    names = [item["name"] for item in review["contracts"]]
    checks = [
        _check_equal("review_selected_next_work", review["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal(
            "review_selection_type",
            review["selection_type"],
            "remediation_static_contract_review_only",
        ),
        _check_equal(
            "review_contract_names",
            names,
            [
                "relative_comfort_contract",
                "hard_feasibility_contract",
                "latency_contract",
                "policy_default_off_contract",
            ],
        ),
    ]
    checks.extend(
        _check_equal(f"contract_{item['name']}_present", item["status"], True)
        for item in review["contracts"]
    )
    text = json.dumps(review, sort_keys=True).lower()
    checks.extend(
        [
            _check_equal("review_mentions_default_off", "default-off" in text, True),
            _check_equal("review_mentions_score_linear", "score_k(w)=a_k^t w" in text, True),
            _check_equal("review_mentions_convex_master", "convex master" in text, True),
            _check_equal("review_blocks_source_edits", "source edits" in text, True),
            _check_equal("review_blocks_dp_changes", "dp code" in text, True),
        ]
    )
    return checks


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
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
        "static_contract_review_complete": passed,
        "default_off_remediation_unit_tests_plan_authorized": passed,
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


def _all_present(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


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
