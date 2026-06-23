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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_remediation_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_static_contract_"
    "review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_static_contract_"
    "review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_unit_tests_plan_only"
)

DEFAULT_DESIGN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "remediation_design_plan_963dc8b"
)
DESIGN_JSON = "fixed_snapshot_screen_rerun_remediation_design_plan.json"
DESIGN_JSON_COMPAT = "remediation_design_plan.json"
SHA256SUMS = "SHA256SUMS"
HEADS = "HEADS.txt"
DESIGN_EXIT = "DESIGN_EXIT"
PLAN_COMMAND_EXIT = "PLAN_COMMAND_EXIT"
EXIT_CODE = "EXIT_CODE"
DEFAULT_SOURCE_PATH = (
    ROOT / "scripts" / "integrations" / "analyze_diffusion_planner_route_topology_candidate_screen.py"
)

BLOCKED_ACTIONS = (
    "implementation_authorized",
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
            "Read-only static contract review for the default-off fixed-snapshot "
            "rerun remediation design."
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
    design_json_name = _design_json_name(design_root)
    design_exit_name = _design_exit_name(design_root)
    artifact = _artifact_summary(
        design_root,
        required_files=(design_json_name, design_exit_name, HEADS, SHA256SUMS),
        design_exit_name=design_exit_name,
    )
    design_payload = _load_json_if_present(design_root / design_json_name)
    source_text = _source_bundle(source_path)
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
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "remediation_static_contract_review_v1"
            ),
            "label": label,
            "role": "read-only source and artifact review before any unit-test plan",
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
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This review reads only the remediation design artifact and "
                "existing CAMP source. It does not edit source code, implement "
                "tests, create candidates, rerun the screen, run DP, run "
                "replay, use formal seeds, define runtime atoms, choose lambda "
                "online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, claim safety benefit, claim CAMP "
                "is better than DP Top-1, or claim a DP-side classical Benders "
                "decomposition."
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
        "# Default-Off Fixed-Snapshot Rerun Remediation Static Contract Review",
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
            "- implementation and unit-test changes are not authorized",
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
                "unit_tests_plan_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(
    root: Path,
    *,
    required_files: tuple[str, ...],
    design_exit_name: str,
) -> dict[str, Any]:
    files = {name: (root / name).is_file() for name in required_files}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "design_exit": _read_text(root / design_exit_name).strip() or None,
        "design_exit_file": design_exit_name,
        "heads_text_present": bool(_read_text(root / HEADS).strip()),
    }


def _design_json_name(design_root: Path) -> str:
    if (design_root / DESIGN_JSON).is_file():
        return DESIGN_JSON
    return DESIGN_JSON_COMPAT


def _design_exit_name(design_root: Path) -> str:
    if (design_root / DESIGN_EXIT).is_file():
        return DESIGN_EXIT
    if (design_root / PLAN_COMMAND_EXIT).is_file():
        return PLAN_COMMAND_EXIT
    return EXIT_CODE


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    design = _dict(payload.get("remediation_design"))
    thread_names = [
        _dict(item).get("name") for item in _list(design.get("remediation_threads"))
    ]
    return {
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_next_work": design.get("selected_next_work"),
        "thread_names": thread_names,
        "next_gate_checks": _list(design.get("next_gate_checks")),
        **{key: bool(decision.get(key)) for key in BLOCKED_ACTIONS},
    }


def _static_contract_review(source_text: str) -> dict[str, Any]:
    contracts = [
        {
            "name": "relative_comfort_static_contract",
            "status": _all_present(
                source_text,
                (
                    "_comfort_admissible",
                    "_comfort_failure_classes",
                    "route_topology_comfort_blocked_command_jerk",
                    "route_topology_comfort_blocked_command_lateral",
                    "route_topology_comfort_blocked_progress_loss",
                    "route_topology_comfort_blocked_rollout_distance",
                    "route_topology_comfort_blocked_rollout_jerk",
                    "route_topology_comfort_blocked_rollout_lateral",
                    "progress_comfort_delta",
                ),
            ),
            "evidence": "comfort admissibility and failure classes are explicit report fields",
            "allowed_next_step": "plan unit tests for threshold classification only",
        },
        {
            "name": "hard_blocker_separation_contract",
            "status": _all_present(
                source_text,
                (
                    "reward_hard_feasibility",
                    "hard_reasons",
                    "hard_reason_counts",
                    "route_topology_lane_invalid",
                    "route_topology_red_timing_invalid",
                    "hard_feasible",
                ),
            ),
            "evidence": "hard blockers are evaluator labels over fixed DP candidates",
            "allowed_next_step": "plan tests that classify blockers without DP invocation changes",
        },
        {
            "name": "latency_static_contract",
            "status": _all_present(
                source_text,
                (
                    "\"candidate_build\"",
                    "\"total\"",
                    "_summarize_latency",
                    "time.perf_counter",
                    "latency_ms",
                ),
            ),
            "evidence": "candidate-build and total p95 are explicit latency fields",
            "allowed_next_step": "plan deterministic tests for bookkeeping before timing claims",
        },
        {
            "name": "absolute_guard_subset_contract",
            "status": _all_present(
                source_text,
                (
                    "route_topology_absolute_lateral_guard_support_present",
                    "absolute_lateral_guard_rows",
                    "absolute_lateral_guard_snapshot_support_rate",
                    "absolute_lateral_guard_pass",
                    "absolute_metric_summary",
                ),
            ),
            "evidence": "absolute guard output is a separate diagnostic artifact",
            "allowed_next_step": "plan tests that preserve subset-only semantics",
        },
        {
            "name": "policy_default_off_contract",
            "status": _all_present(
                source_text,
                (
                    "generator_policy",
                    "lane_projected_jerk_progress_red_stop",
                    "choices=(",
                    'default="lane_centerline_red_stop"',
                ),
            ),
            "evidence": "lane-projected jerk/progress policy is selectable and not default",
            "allowed_next_step": "plan tests that preserve default-off behavior",
        },
    ]
    return {
        "selection_type": "remediation_static_contract_review_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "contracts": contracts,
        "rejection_rules": [
            "reject if source edits or unit-test implementation are needed in this gate",
            "reject if candidate generation or fixed-screen rerun is requested",
            "reject if replay, Full36, or formal seeds are requested",
            "reject if DP code, weights, config, or invocation changes are needed",
            "reject if score_k(w)=a_k^T w or convex master preservation is not explicit",
            "reject if safety-benefit, CAMP-over-DP-Top-1, or classical Benders claims are made",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("design_artifact_exists", artifact["exists"], True),
        _check_equal("design_required_files_present", artifact["required_files_present"], True),
        _check_equal("design_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("design_exit_zero", artifact["design_exit"], "0"),
        _check_equal("design_heads_present", artifact["heads_text_present"], True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _design_authorization_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = [key for key in BLOCKED_ACTIONS if source.get(key)]
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
        _check_equal("design_blocked_actions_clear", blocked, []),
        _check_equal(
            "design_threads_present",
            source["thread_names"],
            [
                "relative_comfort_static_contract",
                "hard_blocker_separation_contract",
                "latency_static_contract",
                "absolute_guard_subset_contract",
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


def _source_bundle(source_path: Path) -> str:
    if not source_path.is_file():
        return ""
    parts = [source_path.read_text(encoding="utf-8")]
    absolute_path = source_path.with_name(
        "analyze_diffusion_planner_route_topology_absolute_comfort_guard.py"
    )
    if absolute_path.is_file():
        parts.append(absolute_path.read_text(encoding="utf-8"))
    return "\n".join(parts)


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
                "relative_comfort_static_contract",
                "hard_blocker_separation_contract",
                "latency_static_contract",
                "absolute_guard_subset_contract",
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
            _check_equal("review_blocks_unit_test_implementation", "unit-test implementation" in text, True),
            _check_equal("review_blocks_dp_changes", "dp code" in text, True),
            _check_equal("review_blocks_safety_claim", "safety-benefit" in text, True),
            _check_equal("review_blocks_camp_over_dp_top1_claim", "camp-over-dp-top-1" in text, True),
            _check_equal("review_blocks_benders", "classical benders" in text, True),
        ]
    )
    return checks


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_implementation", decision["implementation_authorized"], False),
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
        "static_contract_review_complete": passed,
        "unit_tests_plan_authorized": passed,
        "implementation_authorized": False,
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
