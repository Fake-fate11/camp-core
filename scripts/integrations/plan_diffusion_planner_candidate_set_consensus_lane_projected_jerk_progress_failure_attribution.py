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


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "failure_attribution_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "failure_attribution_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_"
    "failure_attribution_read_only_analysis_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SCREEN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_fixed_snapshot_screen_818c823"
)

SCREEN_JSON = "route_topology_lane_projected_jerk_progress_screen.json"
SCREEN_MD = "route_topology_lane_projected_jerk_progress_screen.md"
ABSOLUTE_JSON = "route_topology_lane_projected_jerk_progress_absolute_lateral_guard.json"
ABSOLUTE_MD = "route_topology_lane_projected_jerk_progress_absolute_lateral_guard.md"
CANDIDATE_LOG = "CANDIDATE_SCREEN.log"
CANDIDATE_ERR = "CANDIDATE_SCREEN.err"
ABSOLUTE_LOG = "ABSOLUTE_GUARD.log"
ABSOLUTE_ERR = "ABSOLUTE_GUARD.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"
ABSOLUTE_READY_STATUS = "route_topology_absolute_lateral_guard_support_present"
POLICY_NAME = "lane_projected_jerk_progress_red_stop"

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only failure attribution after the guarded fixed-snapshot "
            "lane-projected jerk/progress screen rejected. This reads existing "
            "artifacts and authorizes only read-only diagnosis."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
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
        screen_root=args.screen_root,
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
    screen_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(screen_root)
    screen = _screen_summary(artifact.get("screen_payload") or {})
    absolute = _absolute_summary(artifact.get("absolute_payload") or {})
    plan = _attribution_plan(screen, absolute)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_screen_checks(screen),
        *_absolute_checks(absolute),
        *_evidence_checks(screen, absolute),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_"
                "jerk_progress_failure_attribution_plan_v1"
            ),
            "label": label,
            "role": (
                "plan-only read-only attribution for a rejected fixed-snapshot "
                "candidate screen"
            ),
            "plan_only": True,
            "read_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_candidate_generation_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan reads only fixed-screen result artifacts and "
                "fixed-head audit. It does not execute candidate generation, "
                "run DP, run replay, recompute outcomes, define runtime atoms, "
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
        "screen_artifact": _strip_payloads(artifact),
        "screen_summary": screen,
        "absolute_summary": absolute,
        "failure_attribution_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["failure_attribution_plan"]
    lines = [
        "# Lane-Projected Jerk/Progress Failure Attribution Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{plan['selected_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Evidence Summary",
        "",
        f"- Screen status: `{report['screen_summary']['status']}`",
        f"- Hard support rate: `{report['screen_summary']['hard_support_rate']}`",
        f"- Comfort support rate: `{report['screen_summary']['comfort_support_rate']}`",
        f"- Candidate-build p95 ms: `{report['screen_summary']['candidate_build_p95_ms']}`",
        f"- Total p95 ms: `{report['screen_summary']['total_p95_ms']}`",
        f"- Absolute guard status: `{report['absolute_summary']['status']}`",
        f"- Absolute guard support rate: `{report['absolute_summary']['absolute_support_rate']}`",
        "",
        "## Read-Only Diagnostic Axes",
        "",
    ]
    for item in plan["diagnostic_axes"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Required Output", ""])
    for item in plan["required_output_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        SCREEN_JSON,
        SCREEN_MD,
        ABSOLUTE_JSON,
        ABSOLUTE_MD,
        CANDIDATE_LOG,
        CANDIDATE_ERR,
        ABSOLUTE_LOG,
        ABSOLUTE_ERR,
        EXIT_CODE,
        HEADS,
        SHA256SUMS,
    )
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    screen_payload: dict[str, Any] = {}
    absolute_payload: dict[str, Any] = {}
    if files[SCREEN_JSON].is_file():
        loaded = _load_json(files[SCREEN_JSON])
        screen_payload = loaded if isinstance(loaded, dict) else {}
    if files[ABSOLUTE_JSON].is_file():
        loaded = _load_json(files[ABSOLUTE_JSON])
        absolute_payload = loaded if isinstance(loaded, dict) else {}
    heads = (
        (root / HEADS).read_text(encoding="utf-8", errors="replace")
        if (root / HEADS).is_file()
        else ""
    )
    exit_code = (
        (root / EXIT_CODE).read_text(encoding="utf-8").strip()
        if (root / EXIT_CODE).is_file()
        else None
    )
    return {
        "root": str(root),
        "required_files_present": exists,
        "sha256sums_ok": sha_ok,
        "sha256sums": sha_details,
        "heads_text": heads,
        "exit_code": exit_code,
        "screen_payload": screen_payload,
        "absolute_payload": absolute_payload,
    }


def _screen_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    support = _dict(payload.get("support_gate"))
    records = _dict(payload.get("records"))
    latency = _dict(payload.get("latency_ms"))
    candidate_build = _dict(latency.get("candidate_build"))
    total = _dict(latency.get("total"))
    return {
        "status": decision.get("status"),
        "offline_selector_screen_authorized": bool(
            decision.get("offline_selector_screen_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "snapshots": records.get("snapshots"),
        "snapshots_with_generated_candidates": records.get(
            "snapshots_with_generated_candidates"
        ),
        "generated_candidate_rows": records.get("generated_candidate_rows"),
        "hard_support_pass": bool(support.get("hard_feasible_snapshot_support_pass")),
        "hard_support_rate": support.get("hard_feasible_snapshot_support_rate"),
        "comfort_support_pass": bool(
            support.get("comfort_admissible_snapshot_support_pass")
        ),
        "comfort_support_rate": support.get(
            "comfort_admissible_snapshot_support_rate"
        ),
        "comfort_rows": records.get("lower_union_red_comfort_admissible_rows"),
        "hard_rows": records.get("lower_union_red_hard_feasible_rows"),
        "progress_rows": records.get("lower_union_red_progress_feasible_rows"),
        "candidate_build_p95_ms": candidate_build.get("p95"),
        "total_p95_ms": total.get("p95"),
        "failure_class_counts": _dict(payload.get("failure_class_counts")),
        "hard_reason_counts": _dict(payload.get("hard_reason_counts")),
        "progress_comfort_delta": _dict(payload.get("progress_comfort_delta")),
        "red_delta": _dict(payload.get("red_delta")),
    }


def _absolute_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    support = _dict(payload.get("support_gate"))
    records = _dict(payload.get("records"))
    return {
        "status": decision.get("status"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "absolute_support_pass": bool(
            support.get("absolute_lateral_guard_snapshot_support_pass")
        ),
        "absolute_support_rate": support.get(
            "absolute_lateral_guard_snapshot_support_rate"
        ),
        "absolute_rows": records.get("absolute_lateral_guard_rows"),
        "hard_progress_rows": records.get("lower_union_red_hard_progress_rows"),
        "failure_class_counts": _dict(payload.get("failure_class_counts")),
        "absolute_metric_summary": _dict(payload.get("absolute_metric_summary")),
    }


def _attribution_plan(
    screen: dict[str, Any],
    absolute: dict[str, Any],
) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "read_only_failure_attribution_plan_only",
        "source_status": {
            "screen_status": screen["status"],
            "absolute_guard_status": absolute["status"],
        },
        "diagnostic_axes": [
            "comfort blocker attribution by command jerk, command lateral, rollout jerk, rollout lateral, progress loss, rollout distance, and smoothness loss",
            "hard blocker attribution by dp_kinematic, dp_lane_crossing, dp_road_border, dp_red_light, and underprogress",
            "absolute lateral guard survivor characterization across the 28 passing rows and 7 support snapshots",
            "latency source attribution for candidate_build p95 and total p95 failures without rerunning candidate generation",
            "red-light reduction retention summary for generated rows and hard/absolute-support subsets",
            "snapshot-level overlap table separating generated/no-generated, hard/pass, progress/pass, absolute/pass, and comfort/pass subsets",
        ],
        "required_output_contract": [
            "read only the fixed screen JSON, absolute guard JSON, HEADS, EXIT_CODE, and SHA256SUMS",
            "record source artifact SHA256SUMS and CAMP/DP heads",
            "produce blocker count tables and snapshot-level overlap tables",
            "produce latency source summary using existing latency_ms only",
            "produce recommendation categories: reject-family, optimize-implementation-only, or design-new-policy-plan-only",
            "do not create new candidate trajectories or rerun the screen",
        ],
        "accept_criteria_for_diagnosis": [
            "source artifact SHA256SUMS match",
            "source screen remains rejected for comfort support or latency",
            "absolute guard source remains available for subset analysis",
            "diagnosis produces nonempty blocker tables",
            "diagnosis preserves no-promotion and no-replay decisions",
        ],
        "blocked_boundaries": [
            "this gate is plan-only and authorizes only read-only failure attribution",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "replay is not authorized",
            "CAMP retraining is not authorized",
            "atom promotion or online selector change is not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or DP Top-1 superiority claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "screen_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("screen_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("screen_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "screen_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _screen_checks(screen: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("screen_status_rejected", screen["status"], SCREEN_REJECT_STATUS),
        _check_equal(
            "screen_offline_selector_not_authorized",
            screen["offline_selector_screen_authorized"],
            False,
        ),
        _check_equal("screen_no_blocked_actions", screen["blocked_action_conflicts"], []),
        _check_equal("screen_generated_rows_present", _positive(screen["generated_candidate_rows"]), True),
        _check_equal("screen_hard_support_passed", screen["hard_support_pass"], True),
        _check_equal("screen_comfort_support_failed", screen["comfort_support_pass"], False),
    ]


def _absolute_checks(absolute: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("absolute_status_ready", absolute["status"], ABSOLUTE_READY_STATUS),
        _check_equal("absolute_support_passed", absolute["absolute_support_pass"], True),
        _check_equal("absolute_rows_present", _positive(absolute["absolute_rows"]), True),
        _check_equal("absolute_no_blocked_actions", absolute["blocked_action_conflicts"], []),
    ]


def _evidence_checks(
    screen: dict[str, Any],
    absolute: dict[str, Any],
) -> list[dict[str, Any]]:
    failure_classes = screen["failure_class_counts"]
    hard_reasons = screen["hard_reason_counts"]
    latency_fail = (
        _float(screen["candidate_build_p95_ms"]) > 10.0
        and _float(screen["total_p95_ms"]) > 100.0
    )
    return [
        _check_equal("evidence_zero_comfort_rows", screen["comfort_rows"], 0),
        _check_equal("evidence_latency_gates_failed", latency_fail, True),
        _check_equal(
            "evidence_comfort_blockers_present",
            all(
                key in failure_classes
                for key in (
                    "route_topology_comfort_blocked_command_jerk",
                    "route_topology_comfort_blocked_command_lateral",
                    "route_topology_comfort_blocked_progress_loss",
                    "route_topology_comfort_blocked_rollout_jerk",
                    "route_topology_comfort_blocked_rollout_lateral",
                )
            ),
            True,
        ),
        _check_equal(
            "evidence_hard_blockers_present",
            all(key in hard_reasons for key in ("dp_kinematic", "dp_red_light")),
            True,
        ),
        _check_equal(
            "evidence_absolute_subset_available",
            _positive(absolute["absolute_rows"])
            and _positive(absolute["hard_progress_rows"]),
            True,
        ),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        plan["diagnostic_axes"]
        + plan["required_output_contract"]
        + plan["accept_criteria_for_diagnosis"]
        + plan["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("plan_selection_type", plan["selection_type"], "read_only_failure_attribution_plan_only"),
        _check_equal("plan_mentions_comfort", "comfort blocker" in text, True),
        _check_equal("plan_mentions_hard_blockers", "hard blocker" in text, True),
        _check_equal("plan_mentions_latency", "latency" in text and "p95" in text, True),
        _check_equal("plan_mentions_absolute_guard", "absolute lateral guard" in text, True),
        _check_equal("plan_mentions_sha_heads", "sha256sums" in text and "heads" in text, True),
        _check_equal("plan_blocks_rerun", "do not create new candidate" in text, True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(plan["blocked_boundaries"]).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal("boundary_authorizes_read_only", "read-only failure attribution" in text, True),
        _check_equal("boundary_blocks_candidate_generation", "candidate generation execution is not authorized" in text, True),
        _check_equal("boundary_blocks_screen_rerun", "screen rerun is not authorized" in text, True),
        _check_equal("boundary_blocks_replay", "replay is not authorized" in text, True),
        _check_equal("boundary_blocks_training", "retraining is not authorized" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp weights" in text and "fixed" in text, True),
        _check_equal("boundary_blocks_benders", "classical benders" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "failure_attribution_plan_ready": passed,
        "read_only_failure_attribution_authorized": passed,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
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


def _strip_payloads(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"screen_payload", "absolute_payload"}
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _positive(value: Any) -> bool:
    try:
        return float(value) > 0.0
    except (TypeError, ValueError):
        return False


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
