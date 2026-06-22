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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_availability_diversity_synthesis import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)


READY_STATUS = "candidate_set_consensus_candidate_generation_support_redesign_plan_ready"
REJECT_STATUS = "candidate_set_consensus_candidate_generation_support_redesign_plan_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_route_topology_comfort_support_preflight_only"

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SYNTHESIS_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_candidate_availability_"
    "diversity_synthesis_plan_f6b491b"
)

SYNTHESIS_JSON = (
    "candidate_set_consensus_candidate_availability_diversity_synthesis_plan.json"
)
SYNTHESIS_MD = (
    "candidate_set_consensus_candidate_availability_diversity_synthesis_plan.md"
)
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
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only candidate-generation support redesign gate after the "
            "candidate-set consensus availability/diversity synthesis. It "
            "authorizes only a route/topology comfort-support preflight."
        )
    )
    parser.add_argument(
        "--synthesis_root",
        type=Path,
        default=Path(DEFAULT_SYNTHESIS_ROOT),
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
        synthesis_root=args.synthesis_root,
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
    synthesis_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(synthesis_root)
    source = _source_summary(artifact.get("json_payload") or {})
    plan = _support_redesign_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_candidate_generation_support_redesign_plan_v1",
            "label": label,
            "role": (
                "plan-only support-redesign gate that converts the current "
                "availability/diversity synthesis into a no-execution "
                "route/topology comfort-support preflight"
            ),
            "plan_only": True,
            "training": False,
            "online_selector_change": False,
            "candidate_generation_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "atom_promotion": False,
            "math_boundary": (
                "This plan reads only the availability/diversity synthesis "
                "artifact and fixed-head audit. It does not generate DP "
                "candidates, run replay, recompute outcomes, define runtime "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "synthesis_artifact": _strip_payload(artifact),
        "source_summary": source,
        "support_redesign_plan": plan,
        "support_redesign_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["support_redesign_plan"]
    lines = [
        "# Candidate-Set Consensus Candidate-Generation Support Redesign Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selected next work: `{plan['selected_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Redesign Hypothesis",
        "",
        plan["redesign_hypothesis"],
        "",
        "## Rejected Families",
        "",
    ]
    for item in plan["rejected_or_blocked_families"]:
        lines.append(f"- `{item['name']}`: {item['reason']}")
    lines.extend(["", "## Preflight Requirements", ""])
    for item in plan["preflight_required_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Acceptance Criteria", ""])
    for item in plan["accept_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Rejection Criteria", ""])
    for item in plan["reject_criteria"]:
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
    for check in report["support_redesign_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    required = (
        SYNTHESIS_JSON,
        SYNTHESIS_MD,
        COMMAND_LOG,
        COMMAND_ERR,
        EXIT_CODE,
        HEADS,
        SHA256SUMS,
    )
    files = {name: root / name for name in required}
    exists = {name: path.is_file() for name, path in files.items()}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    payload: dict[str, Any] = {}
    if files[SYNTHESIS_JSON].is_file():
        loaded = _load_json(files[SYNTHESIS_JSON])
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
    plan = _dict(payload.get("synthesis_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "synthesis_plan_ready": bool(
            decision.get("candidate_availability_diversity_synthesis_plan_ready")
        ),
        "support_redesign_plan_authorized": bool(
            decision.get("candidate_generation_support_redesign_plan_authorized")
        ),
        "selected_next_work": decision.get("selected_next_work"),
        "source_selected_next_work": plan.get("selected_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _support_redesign_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "selection_type": "fresh_preflight_only_gate",
        "redesign_hypothesis": (
            "A materially different route/topology comfort-support preflight "
            "may be worth planning only if it first proves fixed current-tick "
            "route, lane, red-light, candidate0, tracker, progress, comfort, "
            "latency, fallback, and artifact contracts without executing "
            "candidate generation. The design direction is lane-valid, "
            "curvature-bounded, prefix-preserving route/topology support, not "
            "another selector threshold, bridge-length, stop-margin, or DP "
            "tuning loop."
        ),
        "rejected_or_blocked_families": [
            {
                "name": "selector_threshold_or_camp_retraining",
                "reason": "materiality failure is candidate support, not an online CAMP scoring authorization",
            },
            {
                "name": "simple_k_noise_or_same_mode_generator",
                "reason": "previous design preflight rejected simple candidate count or noise variants",
            },
            {
                "name": "route_lane_guidance_retry",
                "reason": "old guidance and dense candidate0-preserving guidance failed support or latency gates",
            },
            {
                "name": "source_donor_graft_or_world_frame_bridge",
                "reason": "source donor and bridge families lacked comfort-admissible lower-red support",
            },
            {
                "name": "constant_deceleration_red_stop_margin_tuning",
                "reason": "route/topology red-stop margin and stop-margin tuning moved the blocker to comfort and progress transfer",
            },
            {
                "name": "prefix_or_bridge_length_grid_tuning",
                "reason": "prefix and bridge grids are not a replay-worthy tuning knob after prior rejection",
            },
        ],
        "preflight_required_checks": [
            "verify the synthesis source artifact and SHA256SUMS before any new design work",
            "preserve candidate0 exactly and append any future candidates default-off",
            "require fixed DP weights, fixed DP code, and no DP-side tuning knobs",
            "prove every proposed input is available from the current tick with no future outcome leakage",
            "predeclare nonformal-only asset scope and keep formal seeds 11/12/13 frozen",
            "predeclare lane-valid corridor construction and curvature/heading-continuity constraints",
            "predeclare endpoint and mode diversity diagnostics before any candidate generation execution",
            "predeclare DP hard-feasibility, red-light, lane, progress, and comfort gates",
            "predeclare PerfectTracker command and open-loop rollout comfort boundaries",
            "predeclare fallback behavior when no generated candidate passes all gates",
            "predeclare latency measurement and p95 rejection criteria before execution",
            "record HEADS, artifact paths, SHA256SUMS, command logs, and exit code",
        ],
        "accept_criteria": [
            "source synthesis artifact is ready and authorizes only this support-redesign plan",
            "CAMP HEAD equals origin/main and DP HEAD equals the fixed Tier4 commit",
            "all blocked actions remain false",
            "the next work item is preflight-only and cannot execute candidate generation",
            "the plan explicitly rejects repeats of old guidance, bridge, stop-margin, and selector loops",
        ],
        "reject_criteria": [
            "source artifact SHA, HEADS, or exit code cannot be verified",
            "CAMP HEAD diverges from origin/main or DP HEAD is not fixed",
            "the proposed design requires DP code, DP weights, or DP hyperparameter changes",
            "the proposed design would run replay, generate candidates, train CAMP, or promote an atom",
            "the proposed design lacks candidate0, latency, fallback, progress, or comfort boundaries",
            "the proposed design is only another minor variant of a rejected route family",
        ],
        "blocked_boundaries": [
            "this gate is plan-only and authorizes only a preflight-only next gate",
            "no candidate generation execution is authorized",
            "no replay or closed-loop smoke is authorized",
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
            "synthesis_required_files_present",
            artifact["required_files_present"],
            {key: True for key in artifact["required_files_present"]},
        ),
        _check_equal("synthesis_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal("synthesis_exit_code_zero", artifact["exit_code"], "0"),
        _check_equal(
            "synthesis_heads_present",
            bool(str(artifact.get("heads_text") or "").strip()),
            True,
        ),
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
        _check_equal(
            "source_authorizes_support_redesign",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_synthesis_plan_ready", source["synthesis_plan_ready"], True),
        _check_equal(
            "source_support_redesign_plan_authorized",
            source["support_redesign_plan_authorized"],
            True,
        ),
        _check_equal(
            "source_selected_next_work",
            source["selected_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal(
            "source_plan_selected_next_work",
            source["source_selected_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    family_text = " ".join(
        item["name"] + " " + item["reason"]
        for item in plan["rejected_or_blocked_families"]
    ).lower()
    checks_text = " ".join(plan["preflight_required_checks"]).lower()
    return [
        _check_equal("plan_selected_next_work", plan["selected_next_work"], AUTHORIZED_NEXT_WORK),
        _check_equal("plan_selection_type", plan["selection_type"], "fresh_preflight_only_gate"),
        _check_equal("plan_has_redesign_hypothesis", bool(plan["redesign_hypothesis"]), True),
        _check_equal("plan_rejects_selector_loop", "selector" in family_text, True),
        _check_equal("plan_rejects_guidance_retry", "guidance" in family_text, True),
        _check_equal("plan_rejects_bridge_family", "bridge" in family_text, True),
        _check_equal("plan_rejects_stop_margin_tuning", "stop-margin" in family_text, True),
        _check_equal("plan_requires_candidate0", "candidate0" in checks_text, True),
        _check_equal("plan_requires_no_leak_current_tick", "current tick" in checks_text, True),
        _check_equal("plan_requires_endpoint_mode", "endpoint" in checks_text and "mode" in checks_text, True),
        _check_equal("plan_requires_progress_comfort", "progress" in checks_text and "comfort" in checks_text, True),
        _check_equal("plan_requires_tracker", "perfecttracker" in checks_text, True),
        _check_equal("plan_requires_latency", "latency" in checks_text and "p95" in checks_text, True),
        _check_equal("plan_requires_fallback", "fallback" in checks_text, True),
        _check_equal("plan_requires_artifact_sha", "sha256sums" in checks_text and "heads" in checks_text, True),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = " ".join(
        [plan["redesign_hypothesis"]]
        + plan["preflight_required_checks"]
        + plan["accept_criteria"]
        + plan["reject_criteria"]
        + plan["blocked_boundaries"]
    ).lower()
    return [
        _check_equal("boundary_mentions_plan_only", "plan-only" in text, True),
        _check_equal("boundary_authorizes_only_preflight", "preflight-only" in text, True),
        _check_equal("boundary_blocks_candidate_generation_execution", "no candidate generation execution" in text, True),
        _check_equal("boundary_blocks_replay", "no replay" in text, True),
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
        "candidate_generation_support_redesign_plan_ready": passed,
        "route_topology_comfort_support_preflight_authorized": passed,
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
