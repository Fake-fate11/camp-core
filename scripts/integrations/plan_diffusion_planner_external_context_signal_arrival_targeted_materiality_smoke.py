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

from scripts.integrations.plan_diffusion_planner_external_context_payload_smoke import (  # noqa: E402
    SmokeSpec,
    build_report as build_payload_smoke_plan,
    render_bash as render_payload_smoke_bash,
)


SOURCE_STATUS = "external_context_materiality_gap_diagnosed"
SOURCE_NEXT_WORK = "external_context_targeted_materiality_smoke_plan_only"
READY_STATUS = "external_context_signal_arrival_materiality_smoke_plan_ready"
REJECT_STATUS = "external_context_signal_arrival_materiality_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = "external_context_signal_arrival_materiality_probe_smoke_only"
TARGET_ROOT = "/root/autodl-tmp/camp_dp_external_context_signal_arrival_materiality_probe"
REQUIRED_GAP = "traffic_signal_context_available_but_no_candidate_arrival"
BASELINE_PAYLOAD_STEPS = 10
TARGET_PAYLOAD_STEPS = 50
MAX_TARGET_PAYLOAD_STEPS = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only signal-arrival targeted materiality smoke after an "
            "external-context materiality gap diagnosis. It emits a paired "
            "tiny traffic-lights-on probe plan and does not run Diffusion Planner."
        )
    )
    parser.add_argument("--gap_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    parser.add_argument("--payload_steps", type=int, default=TARGET_PAYLOAD_STEPS)
    parser.add_argument("--root", default=TARGET_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        gap=_load_json(args.gap_json),
        label=args.label,
        root=args.root,
        payload_steps=args.payload_steps,
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
    payload_steps: int = TARGET_PAYLOAD_STEPS,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gap(gap)
    source_checks = _source_checks(source)
    smoke = replace(
        SmokeSpec(),
        root=root,
        traffic_lights="on",
        payload_steps=int(payload_steps),
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
            "name": "signal_horizon_gap_is_targeted",
            "passed": REQUIRED_GAP in source["gap_names"],
            "actual": source["gap_names"],
            "expected": REQUIRED_GAP,
        },
        {
            "name": "traffic_lights_enabled_for_signal_probe",
            "passed": smoke.traffic_lights == "on",
            "actual": smoke.traffic_lights,
            "expected": "on",
        },
        {
            "name": "payload_support_extends_failed_horizon",
            "passed": smoke.payload_steps > BASELINE_PAYLOAD_STEPS,
            "actual": smoke.payload_steps,
            "expected": f">{BASELINE_PAYLOAD_STEPS}",
        },
        {
            "name": "payload_support_is_bounded_development_probe",
            "passed": BASELINE_PAYLOAD_STEPS < smoke.payload_steps <= MAX_TARGET_PAYLOAD_STEPS,
            "actual": smoke.payload_steps,
            "expected": f"{BASELINE_PAYLOAD_STEPS + 1}..{MAX_TARGET_PAYLOAD_STEPS}",
        },
        {
            "name": "candidate_noise_unchanged_for_signal_probe",
            "passed": smoke.candidate_noise_scale == 1.0,
            "actual": smoke.candidate_noise_scale,
            "expected": 1.0,
        },
    ]
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_signal_arrival_materiality_smoke_plan_v1",
            "label": label,
            "role": (
                "plan-only targeted traffic-signal materiality probe after a "
                "real signal-context smoke produced no candidate signal arrivals"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "target": {
                "family": "traffic_signal",
                "gap": REQUIRED_GAP,
                "root": root,
                "payload_steps": int(payload_steps),
                "payload_dt_s": smoke.payload_dt_s,
                "payload_support_horizon_s": float(payload_steps) * smoke.payload_dt_s,
                "reason": (
                    "the real traffic-lights-on smoke logged current signal "
                    "context, but no fixed DP candidate reached that signal in "
                    f"the previous {BASELINE_PAYLOAD_STEPS}-step payload support"
                ),
            },
            "math_boundary": (
                "This is a plan-only smoke design. The proposed probe changes "
                "only the default-off external-context payload support horizon "
                "in the logging-enabled run so the existing fixed DP candidate "
                "trajectories can expose current-tick signal-arrival descriptors "
                "when present. It does not modify DP code or weights, train CAMP, "
                "change online selection, create atoms, use future outcomes, or "
                "use formal seeds. If materiality is later observed, traffic "
                "signal atomization must use fixed finite-candidate coefficients: "
                "arrival-time costs and right-of-way indicators are nonnegative, "
                "phase margins require hinge or signed-split coefficients, and "
                "the CAMP score must remain score_k(w)=a_k^T w with the "
                "simplex/CVaR/L2 master convex. This is not a DP-side classical "
                "Benders decomposition."
            ),
        },
        "source_gap": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "payload_smoke_plan": payload_plan,
        "accept_criteria": [
            "source gap diagnosis passed and authorized only plan-only targeted materiality design",
            "target is traffic-signal arrival materiality, not route-speed noise probing",
            "traffic lights are enabled and the route/seed scope remains the same nonformal tiny smoke",
            "payload support horizon is extended but bounded as a development probe",
            "selector-equivalence, payload audit, dataset audit, result gate, and materiality gate must all pass after any future execution",
            "future execution must not train CAMP, promote online selection, modify DP, use Full36, or use formal seeds",
        ],
        "reject_criteria": [
            "source gap diagnosis is missing, failed, or authorizes a different next step",
            "the signal-arrival gap is absent from the diagnosis",
            "traffic lights are not enabled for the probe",
            "payload support does not extend the failed 10-step horizon or exceeds the bounded development limit",
            "the plan requests candidate-noise probing, training, online selector promotion, Full36, formal seeds, or DP modification",
        ],
        "final_decision": _final_decision(passed, root, int(payload_steps), smoke.payload_dt_s),
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


def _final_decision(
    passed: bool,
    root: str,
    payload_steps: int,
    payload_dt_s: float,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closed_loop_smoke_authorized": passed,
        "closed_loop_replay_authorized": passed,
        "new_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "paired nonformal signal-arrival materiality probe, seed1 npc4 "
            f"traffic_lights_on static, 3 steps, payload_steps={payload_steps}"
            if passed
            else None
        ),
        "target_root": root,
        "payload_steps": int(payload_steps),
        "payload_dt_s": float(payload_dt_s),
        "payload_support_horizon_s": float(payload_steps) * float(payload_dt_s),
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
            "Run only this paired tiny signal-arrival materiality probe, then "
            "repeat smoke result and materiality gates before any atomization."
            if passed
            else "Reject signal-arrival materiality smoke execution and inspect failed plan checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Signal-Arrival Materiality Smoke Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Scope: `{decision['closed_loop_replay_scope']}`",
        f"- Target root: `{decision['target_root']}`",
        f"- Payload steps: `{decision['payload_steps']}`",
        f"- Payload support horizon s: `{decision['payload_support_horizon_s']}`",
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
