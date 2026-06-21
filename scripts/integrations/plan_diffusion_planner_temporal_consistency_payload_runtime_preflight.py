#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_temporal_consistency_payload import (
    TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS,
    TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
    build_temporal_consistency_payload,
)


DESIGN_READY_STATUS = "temporal_consistency_payload_design_predeclared"
DESIGN_READY_NEXT_WORK = "default_off_temporal_consistency_payload_runtime_preflight_only"

READY_STATUS = "temporal_consistency_payload_runtime_preflight_ready"
BLOCKED_STATUS = "temporal_consistency_payload_runtime_preflight_blocked"
AUTHORIZED_NEXT_WORK = "default_off_temporal_consistency_tiny_paired_smoke_plan_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Runtime preflight gate for the default-off previous-plan temporal "
            "consistency payload. It verifies wiring and pure payload behavior "
            "without running DP replay, training, or online selector promotion."
        )
    )
    parser.add_argument("--payload_design_gate_json", type=Path, required=True)
    parser.add_argument(
        "--runner_path",
        type=Path,
        default=Path("scripts/integrations/run_diffusion_planner_camp_replay.py"),
    )
    parser.add_argument(
        "--summary_script_path",
        type=Path,
        default=Path("scripts/integrations/summarize_diffusion_planner_camp_replay.py"),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        payload_design_gate=_load_json(args.payload_design_gate_json),
        runner_source=args.runner_path.read_text(encoding="utf-8"),
        summary_source=args.summary_script_path.read_text(encoding="utf-8"),
        label=args.label,
        paths={
            "payload_design_gate_json": str(args.payload_design_gate_json),
            "runner_path": str(args.runner_path),
            "summary_script_path": str(args.summary_script_path),
        },
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
    payload_design_gate: dict[str, Any],
    runner_source: str,
    summary_source: str,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    design = _design_summary(payload_design_gate)
    pure_payload = _pure_payload_checks()
    wiring = _wiring_summary(runner_source, summary_source)
    checks = [
        *_design_checks(design),
        *pure_payload["checks"],
        *wiring["checks"],
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_payload_runtime_preflight_v1",
            "label": label,
            "role": (
                "default-off runtime preflight for previous-plan temporal "
                "consistency payload logging"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "The runtime payload produces a fixed current-tick finite "
                "candidate coefficient a_k before selection. The coefficient is "
                "nonnegative when available and missing previous-plan memory "
                "fails closed. If later atomized, CAMP score remains affine in "
                "weights, score_k(w)=a_k^T w, and the simplex/CVaR/L2 master "
                "remains convex. This preflight constructs no DP-side classical "
                "Benders master/subproblem, dual, or valid cuts."
            ),
        },
        "design_summary": design,
        "pure_payload_runtime": pure_payload["summary"],
        "runner_wiring": wiring["summary"],
        "runtime_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def _design_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "payload_design_ready": bool(decision.get("payload_design_ready")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": conflicts,
    }


def _pure_payload_checks() -> dict[str, Any]:
    candidates = np.asarray(
        [
            [[1.0, 0.0, 0.0, 0.0], [2.0, 0.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0]],
            [[1.0, 1.0, 0.0, 0.0], [2.0, 1.0, 0.0, 0.0], [3.0, 1.0, 0.0, 0.0]],
        ],
        dtype=np.float64,
    )
    previous = np.asarray(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0, 0.0],
            [3.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    missing = build_temporal_consistency_payload(
        candidates=candidates,
        previous_selected_plan=None,
        support_steps=3,
        dt_s=0.1,
    )
    available = build_temporal_consistency_payload(
        candidates=candidates,
        previous_selected_plan=previous,
        support_steps=3,
        dt_s=0.1,
        elapsed_steps=1,
        min_overlap_steps=2,
    )
    signature = inspect.signature(build_temporal_consistency_payload)
    checks = [
        _check_equal(
            "payload_schema_version",
            available["schema_version"],
            TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
        ),
        _check_equal("missing_previous_plan_unavailable", missing["available"], False),
        _check_equal(
            "missing_previous_plan_reason",
            missing["availability_reason"],
            "previous_selected_plan_absent",
        ),
        _check_equal(
            "missing_previous_plan_fail_closed",
            missing["finite_checks"]["payload_valid"],
            False,
        ),
        _check_equal("available_payload_ready", available["available"], True),
        _check_equal(
            "shifted_rms_costs",
            available["previous_plan_temporal_consistency_rms_m"],
            [0.0, 1.0],
        ),
        _check_equal(
            "coefficient_field_names",
            list(TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES),
            ["previous_plan_temporal_consistency_rms_m"],
        ),
        _check_equal(
            "latency_field_names",
            list(TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS),
            ["latency_ms_temporal_consistency_payload"],
        ),
        _check_equal("no_outcome_signature", "outcome" in str(signature).lower(), False),
        _check_equal(
            "no_closed_loop_signature",
            "closed_loop" in str(signature).lower(),
            False,
        ),
    ]
    return {
        "summary": {
            "missing_previous_plan_available": bool(missing["available"]),
            "missing_previous_plan_reason": missing["availability_reason"],
            "available_costs": available[
                "previous_plan_temporal_consistency_rms_m"
            ],
            "effective_overlap_steps": available["horizons"][
                "effective_overlap_steps"
            ],
            "signature": str(signature),
        },
        "checks": checks,
    }


def _wiring_summary(runner_source: str, summary_source: str) -> dict[str, Any]:
    expected_runner_tokens = [
        "--camp_temporal_consistency_payload_logging",
        "build_temporal_consistency_payload(",
        "previous_selected_plan_memory",
        "previous_selected_plan=previous_selected_plan_memory",
        "temporal_consistency_payload_logging=bool(",
        "args.camp_temporal_consistency_payload_logging",
        '"temporal_consistency_payload_logging": (',
        '"camp_temporal_consistency_payload_logging": (',
        'validation["camp_temporal_consistency_payload_logging"]',
        "**temporal_consistency_payload_latency_ms",
        "default_off_temporal_consistency_payload_runtime_preflight_only",
    ]
    expected_summary_tokens = [
        '"camp_temporal_consistency_payload_logging"',
    ]
    checks = [
        _check_equal(f"runner_contains::{token}", token in runner_source, True)
        for token in expected_runner_tokens
    ]
    checks.extend(
        _check_equal(f"summary_contains::{token}", token in summary_source, True)
        for token in expected_summary_tokens
    )
    return {
        "summary": {
            "runner_tokens_checked": expected_runner_tokens,
            "summary_tokens_checked": expected_summary_tokens,
            "default_off": True,
            "selection_effect": False,
        },
        "checks": checks,
    }


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("design_status", design["status"], DESIGN_READY_STATUS),
        _check_equal("design_gate_passed", design["passed"], True),
        _check_equal("payload_design_ready", design["payload_design_ready"], True),
        _check_equal(
            "design_authorizes_runtime_preflight",
            design["authorized_next_work"],
            DESIGN_READY_NEXT_WORK,
        ),
        _check_empty("design_no_blocked_actions", design["blocked_action_conflicts"]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "runtime_preflight_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Plan a tiny paired nonformal default-off smoke that turns on only "
            "temporal consistency payload logging and proves trajectory/selection "
            "equivalence plus runtime latency before any replay expansion."
            if passed
            else "Repair runtime payload wiring or fail-closed semantics before smoke planning."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Payload Runtime Preflight",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Runtime preflight ready: `{decision['runtime_preflight_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Pure Runtime Payload",
        "",
        f"- Missing previous plan reason: `{report['pure_payload_runtime']['missing_previous_plan_reason']}`",
        f"- Available shifted RMS costs: `{report['pure_payload_runtime']['available_costs']}`",
        f"- Effective overlap steps: `{report['pure_payload_runtime']['effective_overlap_steps']}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This preflight does not authorize DP replay, CAMP training, online "
        "selector promotion, Full36, formal seeds, DP modification, or a "
        "DP-side classical Benders claim.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["runtime_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": [],
        "passed": len(value) == 0,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
