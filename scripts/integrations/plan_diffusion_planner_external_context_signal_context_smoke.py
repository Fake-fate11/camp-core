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


SOURCE_SCHEMA = "dp_camp_signal_context_wiring_impl_unit_smoke_v1"
READY_STATUS = "external_context_signal_context_smoke_plan_ready"
REJECT_STATUS = "external_context_signal_context_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = "external_context_signal_context_paired_smoke_only"
TARGET_ROOT = "/root/autodl-tmp/camp_dp_external_context_signal_context_smoke"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only traffic-lights-on paired smoke after default-off "
            "signal-context wiring implementation tests."
        )
    )
    parser.add_argument("--implementation_smoke_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    parser.add_argument("--root", default=TARGET_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        implementation_smoke=_load_json(args.implementation_smoke_json),
        label=args.label,
        root=args.root,
        paths={"implementation_smoke_json": str(args.implementation_smoke_json)},
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
    implementation_smoke: dict[str, Any],
    label: str | None = None,
    root: str = TARGET_ROOT,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(implementation_smoke)
    smoke = replace(SmokeSpec(), root=root, traffic_lights="on")
    payload_plan = build_payload_smoke_plan(label=label, smoke=smoke)
    source_checks = _source_checks(source)
    plan_checks = [
        _check_equal(
            "base_payload_smoke_plan_ready",
            payload_plan["final_decision"]["passed"],
            True,
        ),
        _check_equal("traffic_lights_enabled_for_signal_smoke", smoke.traffic_lights, "on"),
        _check_equal("scope_seed_is_nonformal", smoke.seed not in {11, 12, 13}, True),
        _check_equal("scope_steps_tiny", int(smoke.steps), 3),
        _check_equal("scope_candidates_tiny", int(smoke.num_candidates), 8),
    ]
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_signal_context_smoke_plan_v1",
            "label": label,
            "role": (
                "plan-only paired nonformal traffic-lights-on smoke after "
                "signal-context wiring unit tests"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This is a smoke plan only. It authorizes at most a paired "
                "tiny nonformal replay to verify default-off logging with "
                "traffic lights enabled. It creates no atom, trains no CAMP "
                "weights, changes no selector, and does not modify DP. Any "
                "future traffic-signal atom still requires materiality and "
                "atomization gates preserving score_k(w)=a_k^T w and the "
                "convex simplex/CVaR/L2 master."
            ),
        },
        "source_implementation_smoke": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "payload_smoke_plan": payload_plan,
        "final_decision": _decision(passed, root),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": report.get("schema_version"),
        "selection_effect": bool(report.get("selection_effect")),
        "closed_loop_replay": bool(report.get("closed_loop_replay")),
        "diffusion_planner_execution": bool(report.get("diffusion_planner_execution")),
        "training": bool(report.get("training")),
        "payload_traffic_signal_context_available": bool(
            report.get("payload_traffic_signal_context_available")
        ),
        "finite_checks_all": bool(report.get("finite_checks_all")),
        "signal_context": report.get("signal_context"),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_schema_ready", source["schema_version"], SOURCE_SCHEMA),
        _check_equal("source_selection_effect_free", source["selection_effect"], False),
        _check_equal("source_closed_loop_replay_false", source["closed_loop_replay"], False),
        _check_equal(
            "source_dp_execution_false",
            source["diffusion_planner_execution"],
            False,
        ),
        _check_equal("source_training_false", source["training"], False),
        _check_equal(
            "source_signal_payload_available",
            source["payload_traffic_signal_context_available"],
            True,
        ),
        _check_equal("source_finite_checks_passed", source["finite_checks_all"], True),
    ]


def _decision(passed: bool, root: str) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "new_replay_authorized": passed,
        "closed_loop_smoke_authorized": passed,
        "closed_loop_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "paired nonformal signal-context smoke, seed1 npc4 "
            "traffic_lights_on static, 3 steps, 8 candidates"
            if passed
            else None
        ),
        "target_root": root,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Run only this paired tiny traffic-lights-on smoke, then repeat "
            "selector-equivalence, payload, dataset, result, and materiality "
            "gates before any atomization."
            if passed
            else "Reject signal-context smoke execution and repair failed checks."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Signal-Context Smoke Plan",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Scope: `{decision['closed_loop_replay_scope']}`",
        f"- Target root: `{decision['target_root']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Checks",
        "",
        "| Check | Passed | Actual | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in [*report["source_checks"], *report["plan_checks"]]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check['actual']}` | `{check['expected']}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
