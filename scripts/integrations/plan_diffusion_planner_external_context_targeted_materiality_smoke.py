#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.plan_diffusion_planner_external_context_payload_smoke import (
    SmokeSpec,
    build_report as build_payload_smoke_plan,
    render_bash as render_payload_smoke_bash,
)


SOURCE_STATUS = "external_context_materiality_gap_diagnosed"
SOURCE_NEXT_WORK = "external_context_targeted_materiality_smoke_plan_only"
READY_STATUS = "external_context_targeted_materiality_smoke_plan_ready"
REJECT_STATUS = "external_context_targeted_materiality_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = "external_context_route_speed_materiality_probe_smoke_only"
TARGET_ROOT = "/root/autodl-tmp/camp_dp_external_context_route_speed_materiality_probe"
TARGET_NOISE_SCALE = 2.0
REQUIRED_GAP = "route_speed_context_available_but_no_candidate_excess"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only targeted materiality smoke after an external-context "
            "materiality gap diagnosis. It emits a paired tiny route-speed "
            "probe plan and does not run Diffusion Planner."
        )
    )
    parser.add_argument("--gap_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    parser.add_argument("--candidate_noise_scale", type=float, default=TARGET_NOISE_SCALE)
    parser.add_argument("--root", default=TARGET_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        gap=_load_json(args.gap_json),
        label=args.label,
        root=args.root,
        candidate_noise_scale=args.candidate_noise_scale,
        paths={"gap_json": str(args.gap_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if args.output_bash is not None:
        args.output_bash.parent.mkdir(parents=True, exist_ok=True)
        args.output_bash.write_text(
            render_payload_smoke_bash(report["payload_smoke_plan"]),
            encoding="utf-8",
        )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    gap: dict[str, Any],
    label: str | None = None,
    root: str = TARGET_ROOT,
    candidate_noise_scale: float = TARGET_NOISE_SCALE,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gap(gap)
    source_checks = _source_checks(source)
    smoke = replace(
        SmokeSpec(),
        root=root,
        candidate_noise_scale=float(candidate_noise_scale),
    )
    payload_plan = build_payload_smoke_plan(label=label, smoke=smoke)
    plan_checks = [
        {
            "name": "base_payload_smoke_plan_ready",
            "passed": bool(payload_plan["final_decision"]["passed"]),
            "actual": payload_plan["final_decision"]["status"],
            "expected": "external_context_payload_nonformal_smoke_plan_ready",
        },
        {
            "name": "candidate_noise_scale_is_targeted_probe",
            "passed": 1.0 < float(candidate_noise_scale) <= 3.0,
            "actual": float(candidate_noise_scale),
            "expected": "1.0 < noise <= 3.0",
        },
        {
            "name": "route_speed_gap_is_targeted",
            "passed": REQUIRED_GAP in source["gap_names"],
            "actual": source["gap_names"],
            "expected": REQUIRED_GAP,
        },
        {
            "name": "traffic_signal_not_targeted_until_signal_context_wired",
            "passed": True,
            "actual": "route_speed_only",
            "expected": "route_speed_only",
        },
    ]
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_targeted_materiality_smoke_plan_v1",
            "label": label,
            "role": (
                "plan-only targeted route-speed materiality probe after a real "
                "materiality rejection"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "target": {
                "family": "route_speed",
                "candidate_noise_scale": float(candidate_noise_scale),
                "root": root,
                "reason": (
                    "the real smoke logged route speed context but every "
                    "candidate had zero speed-limit excess"
                ),
            },
            "math_boundary": (
                "This is a plan-only smoke design. The proposed probe changes "
                "only candidate noise scale in both paired baseline and logging "
                "runs to look for current-tick finite-candidate route-speed "
                "variation. It does not modify DP code or weights, train CAMP, "
                "change online selection, create atoms, or use formal seeds. "
                "If materiality is later observed, any atomization must still "
                "use fixed coefficients preserving score_k(w)=a_k^T w and the "
                "convex simplex/CVaR/L2 master."
            ),
        },
        "source_gap": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "payload_smoke_plan": payload_plan,
        "accept_criteria": [
            "source gap diagnosis passed and authorized only plan-only targeted materiality design",
            "target is route-speed materiality, not traffic-signal materiality",
            "candidate noise scale is paired in baseline and logging-enabled runs",
            "scope remains nonformal seed 1, 3 steps, 8 candidates, no formal seeds",
            "future execution must pass smoke result and materiality before any atomization",
        ],
        "reject_criteria": [
            "source gap diagnosis is missing, failed, or authorizes a different next step",
            "traffic-signal materiality is targeted before signal_context is wired",
            "candidate noise scale is not bounded as a tiny diagnostic probe",
            "the plan requests training, online selector promotion, Full36, formal seeds, or DP modification",
        ],
        "final_decision": _final_decision(passed, candidate_noise_scale, root),
    }


def _source_gap(gap: dict[str, Any]) -> dict[str, Any]:
    decision = gap.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "gap_names": list(decision.get("gap_names") or []),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_gap_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_gap_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_plan_only_targeted_design",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_equal("source_new_replay_not_authorized", source["new_replay_authorized"], False),
        _check_equal(
            "source_training_not_authorized",
            source["camp_retraining_authorized"],
            False,
        ),
        _check_equal(
            "source_formal_not_authorized",
            source["formal_seeds_authorized"],
            False,
        ),
        _check_equal(
            "source_dp_modification_not_authorized",
            source["dp_modification_authorized"],
            False,
        ),
    ]


def _final_decision(passed: bool, candidate_noise_scale: float, root: str) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closed_loop_smoke_authorized": passed,
        "closed_loop_replay_authorized": passed,
        "new_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "paired nonformal route-speed materiality probe, seed1 npc4 "
            f"traffic_lights_off static, 3 steps, noise={candidate_noise_scale}"
            if passed
            else None
        ),
        "target_root": root,
        "candidate_noise_scale": float(candidate_noise_scale),
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Run only this paired tiny route-speed materiality probe, then "
            "repeat smoke result and materiality gates before atomization."
            if passed
            else "Reject targeted materiality smoke execution and inspect failed plan checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Targeted Materiality Smoke Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Scope: `{decision['closed_loop_replay_scope']}`",
        f"- Target root: `{decision['target_root']}`",
        f"- Candidate noise scale: `{decision['candidate_noise_scale']}`",
        "",
        "## Source Gap",
        "",
        f"- Gap names: `{report['source_gap']['gap_names']}`",
        "",
        "## Plan Checks",
        "",
    ]
    for check in report["source_checks"] + report["plan_checks"]:
        lines.append(
            f"- `{check['name']}`: passed=`{check['passed']}`, "
            f"actual=`{check['actual']}`, expected=`{check['expected']}`"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
