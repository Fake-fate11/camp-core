#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.integrations.design_diffusion_planner_observable_state_logging import (
    FIELD_SPECS,
    ROOT,
)
from scripts.integrations.plan_diffusion_planner_missing_candidate_state_logging_preflight import (
    AUTHORIZED_NEXT_WORK as PREFLIGHT_NEXT_WORK,
    BLOCKED_ACTIONS,
    READY_STATUS as PREFLIGHT_READY_STATUS,
)


READY_STATUS = "missing_candidate_state_logging_implementation_unit_tested"
BLOCKED_STATUS = "missing_candidate_state_logging_implementation_blocked"
AUTHORIZED_NEXT_WORK = "predeclare_default_off_missing_candidate_state_tiny_smoke_plan_only"

RUNNER = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
DEFAULT_TEST_SOURCES = {
    "integration_payload_unit": (
        ROOT / "camp_core/tests/test_diffusion_planner_integration.py"
    ),
    "payload_coverage_contract": (
        ROOT / "camp_core/tests/test_diffusion_planner_observable_state_payload_coverage.py"
    ),
    "smoke_audit_and_plan_contract": (
        ROOT / "camp_core/tests/test_diffusion_planner_observable_state_logging_smoke.py"
    ),
    "current_preflight_contract": (
        ROOT / "camp_core/tests/test_diffusion_planner_missing_candidate_state_logging_preflight.py"
    ),
}


@dataclass(frozen=True)
class TestContract:
    name: str
    path_key: str
    required_tokens: tuple[str, ...]
    rationale: str


TEST_CONTRACTS: tuple[TestContract, ...] = (
    TestContract(
        name="payload_unit_no_leak_and_finite_shape",
        path_key="integration_payload_unit",
        required_tokens=(
            "test_observable_state_logging_payload_reports_schema_shapes_and_no_leak",
            "_observable_state_logging_payload(",
            "candidate_closed_loop_outcomes",
            "future_outcome_leakage",
            "selection_effect",
            "candidate_min_obstacle_clearance_lower_bound_m",
            "OBSERVABLE_STATE_LATENCY_KEYS",
        ),
        rationale=(
            "synthetic unit coverage for payload schema, finite shapes, latency "
            "keys, and no future outcome keys"
        ),
    ),
    TestContract(
        name="payload_coverage_rejects_outcome_leakage",
        path_key="payload_coverage_contract",
        required_tokens=(
            "test_payload_coverage_rejects_future_outcome_leakage",
            "finite_checks",
            "candidate_closed_loop_outcomes",
            "future_outcome_leakage",
            "materiality_gate_passed",
        ),
        rationale=(
            "offline payload coverage must reject leaked outcome labels and "
            "check finite current-tick descriptors"
        ),
    ),
    TestContract(
        name="paired_smoke_keeps_baseline_equivalence_and_scope",
        path_key="smoke_audit_and_plan_contract",
        required_tokens=(
            "test_observable_state_logging_smoke_plan_authorizes_paired_three_step_only",
            "test_observable_state_logging_smoke_audit_rejects_future_payload_key",
            "--camp_observable_state_logging",
            "Full36_authorized",
            "candidate_closed_loop_outcomes",
        ),
        rationale=(
            "the later smoke plan must remain paired, tiny, no-leak, and below "
            "Full36/formal scope"
        ),
    ),
    TestContract(
        name="current_chain_preflight_blocks_replay_and_requires_equivalence",
        path_key="current_preflight_contract",
        required_tokens=(
            "baseline equivalence tests that logging does not change selection",
            "closed-loop replay",
            "classic_benders_claim_authorized",
            "score_k(w)=a_k^T w",
        ),
        rationale=(
            "the current-chain preflight must keep replay blocked and preserve "
            "the CAMP affine/convex math boundary"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Unit/source gate for default-off missing candidate-state logging. "
            "It consumes the current missing-candidate-state preflight and "
            "does not run Diffusion Planner."
        )
    )
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        preflight_report=_load_json(args.preflight_json),
        replay_source=args.replay_source,
        label=args.label,
        paths={"preflight_json": str(args.preflight_json)},
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
    preflight_report: dict[str, Any],
    replay_source: Path = RUNNER,
    test_sources: dict[str, Path] | None = None,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(preflight_report)
    replay_text = _read_text(replay_source)
    test_source_map = {**DEFAULT_TEST_SOURCES, **(test_sources or {})}
    runtime_checks = _runtime_checks(replay_text)
    test_contract_checks = _test_contract_checks(test_source_map)
    math_checks = _math_boundary_checks()
    passed = (
        bool(source["passed"])
        and not source["blocked_action_conflicts"]
        and all(check["passed"] for check in runtime_checks)
        and all(check["passed"] for check in test_contract_checks)
        and all(check["passed"] for check in math_checks)
    )
    return {
        "analysis": {
            "name": "dp_camp_missing_candidate_state_logging_implementation_unit_gate_v1",
            "label": label,
            "role": (
                "source and unit-test gate for default-off current-tick "
                "candidate-state logging before any replay smoke"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "default_off_logging_only": True,
            "paths": {
                **(paths or {}),
                "replay_source": str(replay_source),
                **{key: str(path) for key, path in test_source_map.items()},
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This gate "
                "only verifies default-off logging source order and unit-test "
                "contracts for current-tick fixed finite-candidate descriptors. "
                "No replay, outcome label, online selector change, DP change, "
                "CAMP retraining, or formal seed is authorized. If a logged "
                "descriptor is later atomized, it must be a fixed candidate "
                "coefficient a_k, nonnegative or represented by nonnegative "
                "signed parts, preserving score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master. No classical Benders "
                "master/subproblem, dual, or cut is claimed."
            ),
        },
        "source_preflight_gate": source,
        "runtime_checks": runtime_checks,
        "test_contract_checks": test_contract_checks,
        "math_boundary_checks": math_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    top_blocked = report.get("blocked_actions") or {}
    conflicts = [
        key
        for key in BLOCKED_ACTIONS
        if bool(final.get(key)) or bool(top_blocked.get(key))
    ]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == PREFLIGHT_READY_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == PREFLIGHT_NEXT_WORK
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "recommended_first_action": final.get("recommended_first_action"),
        "blocked_action_conflicts": conflicts,
    }


def _runtime_checks(replay_text: str | None) -> list[dict[str, Any]]:
    field_names = tuple(field.name for field in FIELD_SPECS)
    latency_keys = tuple(field.latency_bucket for field in FIELD_SPECS)
    return [
        _check_tokens(
            "runtime_default_off_cli_flag",
            replay_text,
            (
                "--camp_observable_state_logging",
                'action="store_true"',
                "Default-off no-leak logging",
                "does not change feasibility, scores, or selection",
            ),
        ),
        _check_tokens(
            "runtime_payload_contract_tokens",
            replay_text,
            (
                "def _observable_state_logging_payload(",
                "OBSERVABLE_STATE_LOGGING_SCHEMA_VERSION",
                '"enabled": True',
                '"default_off": True',
                '"selection_effect": False',
                '"future_outcome_leakage": False',
                '"candidate_count"',
                '"field_shapes"',
                '"finite_checks"',
                '"latency_ms"',
            ),
        ),
        _check_tokens("runtime_payload_fields_present", replay_text, field_names),
        _check_tokens("runtime_latency_fields_present", replay_text, latency_keys),
        _check_order(
            "runtime_payload_before_closed_loop_outcomes",
            replay_text,
            "observable_state_logging_payload = _observable_state_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_order(
            "runtime_payload_before_selection",
            replay_text,
            "observable_state_logging_payload = _observable_state_logging_payload(",
            "selection = selector.select(",
        ),
        _check_tokens(
            "runtime_records_and_summary_metadata",
            replay_text,
            (
                '"observable_state_logging": observable_state_logging_payload',
                '"camp_observable_state_logging": camp_observable_state_logging',
                '"online_selector_change": False',
                '"classical_benders_claim": False',
                '"records": (',
                "if args.camp_observable_state_logging",
            ),
        ),
    ]


def _test_contract_checks(test_sources: dict[str, Path]) -> list[dict[str, Any]]:
    checks = []
    for contract in TEST_CONTRACTS:
        path = test_sources.get(contract.path_key)
        text = _read_text(path) if path is not None else None
        check = _check_tokens(contract.name, text, contract.required_tokens)
        check["path"] = str(path) if path is not None else None
        check["rationale"] = contract.rationale
        checks.append(check)
    return checks


def _math_boundary_checks() -> list[dict[str, Any]]:
    invalid_fields = [
        field.name
        for field in FIELD_SPECS
        if (
            not field.default_off
            or field.selection_effect
            or field.uses_future_outcomes
            or field.requires_dp_modification
        )
    ]
    noncandidate_required = [
        field.name
        for field in FIELD_SPECS
        if field.family != "route_curvature_turn_context" and not field.candidate_level
    ]
    return [
        {
            "name": "field_specs_preserve_no_leak_default_off_boundary",
            "passed": not invalid_fields,
            "invalid_fields": invalid_fields,
        },
        {
            "name": "required_candidate_atom_families_have_candidate_level_fields",
            "passed": not noncandidate_required,
            "noncandidate_required": noncandidate_required,
        },
        {
            "name": "finite_candidate_selector_not_classical_benders",
            "passed": True,
            "classical_benders_claim": False,
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "predeclare_default_off_missing_candidate_state_tiny_smoke_plan"
            if passed
            else "repair_default_off_missing_candidate_state_logging_unit_gate"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
        "closed_loop_replay_authorized": False,
        "tiny_smoke_authorized": False,
        "next_step": (
            "Write a separate tiny paired nonformal smoke plan for the "
            "default-off missing candidate-state logging. Do not run replay "
            "until that plan gate passes."
            if passed
            else "Repair the source, ordering, metadata, or test-contract gap "
            "before planning any smoke."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Missing Candidate-State Logging Implementation Unit Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gate",
        "",
        f"- Source status: `{report['source_preflight_gate']['status']}`",
        f"- Source authorized next work: `{report['source_preflight_gate']['authorized_next_work']}`",
        f"- Blocked action conflicts: `{report['source_preflight_gate']['blocked_action_conflicts']}`",
        "",
        "## Runtime Checks",
        "",
        "| Check | Passed | Missing |",
        "| --- | --- | --- |",
    ]
    lines.extend(_check_rows(report["runtime_checks"]))
    lines.extend(
        [
            "",
            "## Test Contract Checks",
            "",
            "| Check | Passed | Missing |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(_check_rows(report["test_contract_checks"]))
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run replay, train CAMP, modify DP, promote an "
            "online selector, authorize Full36, or authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _check_rows(checks: list[dict[str, Any]]) -> list[str]:
    rows = []
    for check in checks:
        missing = ", ".join(f"`{token}`" for token in check.get("missing_tokens", []))
        rows.append(
            f"| `{check['name']}` | `{check['passed']}` | {missing or '`none`'} |"
        )
    return rows


def _check_tokens(
    name: str,
    text: str | None,
    tokens: tuple[str, ...],
) -> dict[str, Any]:
    missing = [token for token in tokens if text is None or token not in text]
    return {
        "name": name,
        "passed": not missing,
        "missing_tokens": missing,
    }


def _check_order(
    name: str,
    text: str | None,
    first: str,
    second: str,
) -> dict[str, Any]:
    if text is None:
        return {"name": name, "passed": False, "reason": "missing_source"}
    first_index = text.find(first)
    second_index = text.find(second)
    return {
        "name": name,
        "passed": first_index >= 0 and second_index >= 0 and first_index < second_index,
        "first_index": first_index,
        "second_index": second_index,
    }


def _read_text(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
