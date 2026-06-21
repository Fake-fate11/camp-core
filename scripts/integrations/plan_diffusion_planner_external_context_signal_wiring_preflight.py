#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "external_context_next_materiality_gate_ready"
SOURCE_NEXT_WORK = "external_context_signal_context_wiring_preflight_design_only"

READY_STATUS = "external_context_signal_context_wiring_preflight_ready"
BLOCKED_STATUS = "external_context_signal_context_wiring_preflight_source_not_ready"
AUTHORIZED_NEXT_WORK = "default_off_signal_context_wiring_implementation_unit_tests_only"

REQUIRED_PAYLOAD_TOKENS = (
    "signal_context",
    "signal_s_m",
    "signal_distance_m",
    "signal_position_ego",
    "current_phase",
    "phase_remaining_s",
    "blocked_phases",
)

REQUIRED_DP_TOKENS = (
    "TrafficLightController",
    "write_to_route_lanes",
    "_GroupState",
    "last_change_time",
    "duration",
)

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
            "Design-only preflight for wiring fixed DP traffic-light runtime "
            "state into the default-off CAMP external-context payload."
        )
    )
    parser.add_argument("--next_gate_json", type=Path, required=True)
    parser.add_argument("--camp_replay_source", type=Path, required=True)
    parser.add_argument("--payload_source", type=Path, required=True)
    parser.add_argument("--dp_source_root", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        next_gate=_load_json(args.next_gate_json),
        camp_replay_source=args.camp_replay_source,
        payload_source=args.payload_source,
        dp_source_root=args.dp_source_root,
        label=args.label,
        paths={
            "next_gate_json": str(args.next_gate_json),
            "camp_replay_source": str(args.camp_replay_source),
            "payload_source": str(args.payload_source),
            "dp_source_root": str(args.dp_source_root),
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
    next_gate: dict[str, Any],
    camp_replay_source: Path,
    payload_source: Path,
    dp_source_root: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(next_gate)
    camp_wiring = _camp_wiring(camp_replay_source)
    payload_contract = _payload_contract(payload_source)
    dp_contract = _dp_contract(dp_source_root)
    preflight_checks = [
        *_source_checks(source),
        _check_equal(
            "camp_replay_currently_fails_closed_with_signal_context_none",
            camp_wiring["signal_context_none_visible"],
            True,
        ),
        _check_equal(
            "payload_accepts_required_signal_context_schema",
            payload_contract["has_required_tokens"],
            True,
        ),
        _check_equal(
            "dp_traffic_light_runtime_tokens_visible",
            dp_contract["has_required_tokens"],
            True,
        ),
    ]
    passed = all(check["passed"] for check in preflight_checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_signal_wiring_preflight_v1",
            "label": label,
            "role": (
                "design-only preflight for default-off signal-context payload "
                "wiring in the CAMP replay wrapper"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This preflight defines a wrapper-side current-tick signal "
                "context contract only. It does not create atoms, run replay, "
                "train CAMP, change online selection, or modify DP. Future "
                "traffic-signal atoms must be fixed finite-candidate "
                "coefficients derived before selection; phase margins require "
                "hinge or signed-split atomization before entering the affine "
                "score_k(w)=a_k^T w. The simplex/CVaR/L2 master remains convex; "
                "no DP-side classical Benders decomposition is claimed."
            ),
        },
        "source_gate": source,
        "camp_wiring": camp_wiring,
        "payload_contract": payload_contract,
        "dp_contract": dp_contract,
        "preflight_checks": preflight_checks,
        "wiring_contract": _wiring_contract(),
        "implementation_constraints": _implementation_constraints(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "primary_gap": final.get("primary_gap"),
        "new_replay_authorized": bool(final.get("new_replay_authorized")),
        "camp_retraining_authorized": bool(final.get("camp_retraining_authorized")),
        "formal_seeds_authorized": bool(final.get("formal_seeds_authorized")),
        "dp_modification_authorized": bool(final.get("dp_modification_authorized")),
        "classic_benders_claim_authorized": bool(
            final.get("classic_benders_claim_authorized")
        ),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_signal_wiring_preflight",
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
        _check_equal(
            "source_classic_benders_not_authorized",
            source["classic_benders_claim_authorized"],
            False,
        ),
    ]


def _camp_wiring(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    return {
        "path": str(path),
        "payload_call_visible": "build_external_context_payload(" in text,
        "signal_context_none_visible": "signal_context=None" in text,
        "external_context_logging_arg_visible": (
            "--camp_external_context_payload_logging" in text
        ),
    }


def _payload_contract(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    missing = [token for token in REQUIRED_PAYLOAD_TOKENS if token not in text]
    return {
        "path": str(path),
        "required_tokens": list(REQUIRED_PAYLOAD_TOKENS),
        "missing_tokens": missing,
        "has_required_tokens": not missing,
    }


def _dp_contract(root: Path) -> dict[str, Any]:
    texts = []
    matched_files = []
    for path in root.rglob("*.py"):
        if not path.is_file() or not _runtime_source(path):
            continue
        text = _read_text(path)
        texts.append(text)
        if any(token in text for token in REQUIRED_DP_TOKENS):
            matched_files.append(str(path))
    combined = "\n".join(texts)
    missing = [token for token in REQUIRED_DP_TOKENS if token not in combined]
    return {
        "root": str(root),
        "required_tokens": list(REQUIRED_DP_TOKENS),
        "missing_tokens": missing,
        "has_required_tokens": not missing,
        "matched_files": sorted(matched_files),
    }


def _runtime_source(path: Path) -> bool:
    normalized = "/" + str(path).replace("\\", "/")
    return "/scenario_generation/" in normalized and "/tests/" not in normalized


def _wiring_contract() -> dict[str, Any]:
    return {
        "helper_name": "build_current_tick_signal_context",
        "location": "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "default_off": True,
        "selection_effect": False,
        "required_inputs": [
            "tl_controller",
            "sim_time_s",
            "route_centerline_ego",
            "ego_route_ids or current route lanelet ids",
            "traffic_lights_enabled flag",
        ],
        "payload_fields": {
            "signal_s_m": (
                "nonnegative route-progress coordinate of the next relevant "
                "route signal or null"
            ),
            "current_phase": "one of red, yellow, green, white, none",
            "phase_remaining_s": (
                "nonnegative remaining duration for the current phase when "
                "available; null is allowed"
            ),
            "blocked_phases": ["red", "yellow"],
        },
        "fail_closed_reasons": [
            "traffic_lights_disabled",
            "tl_controller_absent",
            "route_centerline_absent",
            "route_signal_lanelet_absent",
            "signal_position_unavailable",
            "signal_phase_invalid_or_absent",
        ],
        "latency_bucket": "latency_ms_external_context_traffic_signal_payload",
    }


def _implementation_constraints() -> list[dict[str, Any]]:
    return [
        {
            "name": "no_dp_modification",
            "requirement": (
                "Implement only in CAMP wrapper code; read fixed DP runtime state "
                "without editing Diffusion-Planner."
            ),
        },
        {
            "name": "fail_closed_default_off",
            "requirement": (
                "When any source field is unavailable, pass signal_context=None "
                "and keep traffic_signal_context_available=false."
            ),
        },
        {
            "name": "current_tick_only",
            "requirement": (
                "Use only tl_controller state and route geometry available before "
                "candidate selection at the current tick."
            ),
        },
        {
            "name": "no_selector_effect",
            "requirement": (
                "The first implementation may only log payload diagnostics; it "
                "must not change candidate ranking or CAMP weights."
            ),
        },
        {
            "name": "atom_boundary",
            "requirement": (
                "Signal arrival and right-of-way indicators are only atom "
                "candidates after a later materiality and atomization gate."
            ),
        },
    ]


def _decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "primary_gap": (
            "signal_context_wiring_contract_predeclared"
            if passed
            else "signal_context_wiring_preflight_inputs_not_ready"
        ),
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
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
            "Implement default-off wrapper-side signal_context construction with "
            "unit tests only; do not run a new replay until implementation tests "
            "and a separate smoke plan pass."
            if passed
            else "Repair the source next-materiality gate or signal source scans."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["wiring_contract"]
    lines = [
        "# External Context Signal Wiring Preflight",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Wiring Contract",
        "",
        f"- Helper: `{contract['helper_name']}`",
        f"- Location: `{contract['location']}`",
        f"- Default off: `{contract['default_off']}`",
        f"- Selection effect: `{contract['selection_effect']}`",
        f"- Payload fields: `{', '.join(contract['payload_fields'].keys())}`",
        f"- Fail-closed reasons: `{', '.join(contract['fail_closed_reasons'])}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Actual | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["preflight_checks"]:
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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


if __name__ == "__main__":
    main()
