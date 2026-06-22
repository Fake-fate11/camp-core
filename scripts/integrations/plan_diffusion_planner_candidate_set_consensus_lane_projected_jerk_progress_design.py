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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_route_topology_comfort_support_preflight import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_lane_projected_jerk_progress_support_design_plan_ready"
REJECT_STATUS = "candidate_set_consensus_lane_projected_jerk_progress_support_design_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_implementation_unit_tests_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SOURCE_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_route_topology_"
    "comfort_support_preflight_6999ef5"
)

SOURCE_JSON = "candidate_set_consensus_route_topology_comfort_support_preflight.json"
SOURCE_MD = "candidate_set_consensus_route_topology_comfort_support_preflight.md"
COMMAND_LOG = "COMMAND.log"
COMMAND_ERR = "COMMAND.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

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
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only lane-projected jerk/progress support design after the "
            "route/topology comfort-support preflight. It authorizes only "
            "implementation unit tests, not candidate generation execution."
        )
    )
    parser.add_argument("--preflight_root", type=Path, default=Path(DEFAULT_SOURCE_ROOT))
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
        preflight_root=args.preflight_root,
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
    preflight_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(preflight_root)
    source = _source_summary(artifact.get("json_payload") or {})
    design = _design_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_design_checks(design),
        *_boundary_checks(design),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_design_plan_v1",
            "label": label,
            "role": (
                "plan-only design contract for a lane-projected, jerk/progress-aware "
                "candidate support policy after route/topology preflight"
            ),
            "plan_only": True,
            "candidate_generation_execution": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This design plan reads only the route/topology comfort-support "
                "preflight artifact and fixed-head audit. It does not generate "
                "candidates, run DP, run replay, recompute outcomes, define "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "preflight_artifact": _strip_payload(artifact),
        "source_summary": source,
        "design_plan": design,
        "design_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    design = report["design_plan"]
    lines = [
        "# Lane-Projected Jerk/Progress Support Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{design['selected_next_work']}`",
        f"- Proposed policy: `{design['proposed_policy_name']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Hypothesis",
        "",
        design["design_hypothesis"],
        "",
        "## Fixed Inputs",
        "",
    ]
    for item in design["fixed_current_tick_inputs"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Algorithm Contract", ""])
    for item in design["algorithm_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Unit-Test Scope", ""])
    for item in design["required_unit_tests"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Future Execution Gates", ""])
    for item in design["future_execution_gate_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in design["blocked_boundaries"]:
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
    for check in report["design_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (SOURCE_JSON, SOURCE_MD, COMMAND_LOG, COMMAND_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[SOURCE_JSON].is_file():
        loaded = _load_json(files[SOURCE_JSON])
        payload = loaded if isinstance(loaded, dict) else {}
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
        "json_payload": payload,
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("preflight_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_ready": bool(
            decision.get("route_topology_comfort_support_preflight_ready")
        ),
        "design_plan_authorized": bool(
            decision.get("lane_projected_jerk_progress_support_design_plan_authorized")
        ),
        "selected_next_work": decision.get("selected_next_work"),
        "source_selected_next_work": plan.get("selected_next_work"),
        "lane_projected_absolute_lateral_guard_support_present": (
            _evidence_status(plan, "lane_projected_absolute_lateral_guard")
            == "route_topology_absolute_lateral_guard_support_present"
        ),
        "prefix_lane_projected_absolute_lateral_guard_support_present": (
            _evidence_status(plan, "prefix_lane_projected_absolute_lateral_guard")
            == "route_topology_absolute_lateral_guard_support_present"
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _evidence_status(plan: dict[str, Any], name: str) -> Any:
    contract = _dict(plan.get("evidence_contract"))
    return contract.get(name)


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "implementation_unit_tests_only",
        "proposed_policy_name": "lane_projected_jerk_progress_red_stop",
        "design_hypothesis": (
            "Lane-projected route/topology candidates already provide enough "
            "absolute lateral support, but the evidence still fails relative "
            "comfort because jerk and progress transfer remain uncontrolled. "
            "A future policy should keep the lane-projected red-stop geometry "
            "family, replace the abrupt longitudinal stop profile with a "
            "predeclared acceleration/jerk-limited progress profile, and prove "
            "the implementation contract with unit tests before any fixed-snapshot "
            "execution."
        ),
        "fixed_current_tick_inputs": [
            "selected DP candidate trajectory at the current tick",
            "lane_centerline from the current snapshot",
            "red_route_points from the current snapshot",
            "reward_input__route_lanes for coordinate compatibility only",
            "current speed and dt metadata",
            "predeclared constants for margins, lateral-offset scales, acceleration, jerk, and progress floors",
        ],
        "algorithm_contract": [
            "preserve candidate0 exactly and append generated candidates default-off",
            "project the selected branch into the route/lane frame without future outcome labels",
            "compute the red-stop cap from current red_route_points and predeclared margins",
            "construct a monotone along-lane progress profile that never advances beyond the red-stop cap",
            "limit acceleration and jerk by predeclared constants in the longitudinal profile",
            "preserve or smoothly decay the selected lateral offset using predeclared lane-projected offset scales",
            "emit finite [K,T,D] candidates with heading features derived from generated xy",
            "return an empty generated set when route/topology inputs or red-stop geometry are unavailable",
        ],
        "required_unit_tests": [
            "deterministic output for identical fixed current-tick inputs",
            "candidate0 is not mutated by the helper or caller contract",
            "generated candidates have stable shape, finite values, and metadata for every variant",
            "no DP repository import, DP reward call, replay call, or outcome-label read occurs in unit tests",
            "red-stop cap is respected for synthetic lane/red geometry",
            "along-lane progress is monotone and nonnegative on synthetic fixtures",
            "acceleration and jerk remain under the predeclared synthetic bounds",
            "fallback returns no generated candidates for missing or invalid red-stop geometry",
            "the new policy is only selectable by explicit default-off configuration",
        ],
        "future_execution_gate_requirements": [
            "separate authorization before running on fixed nonformal snapshots",
            "record HEADS, command logs, exit code, artifact paths, and SHA256SUMS",
            "measure candidate-build p95 and total p95 latency",
            "recompute DP hard-feasibility, red-light, lane, progress, and PerfectTracker comfort diagnostics",
            "reject if hard support, progress support, absolute lateral support, relative comfort, or latency fail",
            "keep formal seeds 11/12/13 frozen unless a later formal gate exists",
        ],
        "blocked_boundaries": [
            "this gate is plan-only and authorizes only implementation unit tests",
            "no candidate generation execution is authorized",
            "no DP execution, reward recompute, replay is not authorized, and closed-loop smoke is not authorized",
            "no CAMP retraining is authorized",
            "no atom promotion or online selector change is authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "DP weights and DP code must remain fixed",
            "no safety benefit or DP Top-1 superiority claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
        "source_contract": {
            "status": source["status"],
            "selected_next_work": source["selected_next_work"],
        },
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "preflight_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("preflight_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("preflight_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal("preflight_heads_present", bool(str(artifact.get("heads_text") or "").strip()), True),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_equals_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal("source_authorizes_design_plan", source["authorized_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_preflight_ready", source["preflight_ready"], True),
        _check_equal("source_design_plan_authorized", source["design_plan_authorized"], True),
        _check_equal("source_selected_next_work", source["selected_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal("source_plan_selected_next_work", source["source_selected_next_work"], SOURCE_AUTHORIZED_NEXT_WORK),
        _check_equal(
            "source_lane_projected_absolute_support_present",
            source["lane_projected_absolute_lateral_guard_support_present"],
            True,
        ),
        _check_equal(
            "source_prefix_lane_projected_absolute_support_present",
            source["prefix_lane_projected_absolute_lateral_guard_support_present"],
            True,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        [design["design_hypothesis"], design["proposed_policy_name"]]
        + design["fixed_current_tick_inputs"]
        + design["algorithm_contract"]
        + design["required_unit_tests"]
        + design["future_execution_gate_requirements"]
    ).lower()
    return [
        _check_equal("design_selected_next_work", design["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("design_selection_type", design["selection_type"], "implementation_unit_tests_only"),
        _check_equal("design_policy_name", design["proposed_policy_name"], "lane_projected_jerk_progress_red_stop"),
        _check_equal("design_mentions_lane_projected", "lane-projected" in text or "lane_projected" in text, True),
        _check_equal("design_mentions_jerk_progress", "jerk" in text and "progress" in text, True),
        _check_equal("design_requires_current_tick", "current-tick" in text or "current tick" in text, True),
        _check_equal("design_requires_candidate0", "candidate0" in text, True),
        _check_equal("design_requires_default_off", "default-off" in text, True),
        _check_equal("design_requires_no_dp_in_unit_tests", "no dp" in text and "unit tests" in text, True),
        _check_equal("design_requires_latency_future_gate", "latency" in text and "p95" in text, True),
        _check_equal("design_requires_artifact_sha_future_gate", "sha256sums" in text and "heads" in text, True),
    ]


def _boundary_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        design["algorithm_contract"]
        + design["required_unit_tests"]
        + design["future_execution_gate_requirements"]
        + design["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal("boundary_authorizes_unit_tests_only", "implementation unit tests" in text, True),
        _check_equal("boundary_blocks_candidate_generation_execution", "no candidate generation execution" in text, True),
        _check_equal("boundary_blocks_dp_execution", "no dp execution" in text, True),
        _check_equal("boundary_blocks_replay", "replay" in text and "not authorized" in text, True),
        _check_equal("boundary_blocks_training", "retraining" in text, True),
        _check_equal("boundary_blocks_promotion", "promotion" in text, True),
        _check_equal("boundary_blocks_online_selector", "online selector" in text, True),
        _check_equal("boundary_blocks_formal_seeds", "formal seeds" in text, True),
        _check_equal("boundary_blocks_dp_modification", "dp weights" in text and "fixed" in text, True),
        _check_equal("boundary_blocks_benders_claim", "classical benders" in text, True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "lane_projected_jerk_progress_support_design_plan_ready": passed,
        "implementation_unit_tests_authorized": passed,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "candidate_generation_execution_authorized": False,
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


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "json_payload"}


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
