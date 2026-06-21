#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "new_no_leak_targeted_support_source_predeclared"
SOURCE_READY_NEXT_WORK = "default_off_new_no_leak_support_payload_design_only"
SOURCE_NAME = "previous_plan_temporal_consistency_source_v1"
SOURCE_FAMILY = "closed_loop_plan_memory_temporal_consistency"
SCORE_FAMILY = "temporal_consistency_atom_family"

READY_STATUS = "temporal_consistency_payload_design_predeclared"
BLOCKED_STATUS = "temporal_consistency_payload_design_blocked"
AUTHORIZED_NEXT_WORK = "default_off_temporal_consistency_payload_runtime_preflight_only"

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
            "Design-only gate for the accepted previous-plan temporal "
            "consistency source. It predeclares the default-off payload and "
            "atomization contract without running DP, replay, or training."
        )
    )
    parser.add_argument("--source_proposal_gate_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_proposal_gate=_load_json(args.source_proposal_gate_json),
        label=args.label,
        paths={"source_proposal_gate_json": str(args.source_proposal_gate_json)},
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
    source_proposal_gate: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(source_proposal_gate)
    payload = _payload_contract()
    atom = _atom_contract()
    latency = _latency_contract()
    checks = [
        *_source_checks(source),
        *_payload_checks(payload),
        *_atom_checks(atom),
        *_latency_checks(latency),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_payload_design_v1",
            "label": label,
            "role": (
                "design-only default-off payload contract for previous-plan "
                "temporal consistency as a CAMP-on-DP candidate source"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "The payload would compute fixed current-tick finite-candidate "
                "coefficients a_k before selection. CAMP may score them as "
                "score_k(w)=a_k^T w. Since the robust master optimizes only "
                "over weights w, not trajectory coordinates, the simplex/CVaR/L2 "
                "master remains convex. This gate creates no DP-side classical "
                "Benders master/subproblem, dual, or valid cut."
            ),
        },
        "source_summary": source,
        "payload_contract": payload,
        "atom_contract": atom,
        "latency_contract": latency,
        "design_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    proposal_rows = [
        row for row in report.get("proposals") or [] if isinstance(row, dict)
    ]
    matching = [row for row in proposal_rows if row.get("name") == SOURCE_NAME]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "support_source_ready": bool(decision.get("support_source_ready")),
        "admissible_support_sources": list(
            decision.get("admissible_support_sources") or []
        ),
        "matching_proposal": matching[0] if matching else None,
        "blocked_action_conflicts": conflicts,
    }


def _payload_contract() -> dict[str, Any]:
    return {
        "status": "temporal_consistency_payload_contract_predeclared",
        "default_off": True,
        "runtime_inputs": [
            "current_tick_dp_candidate_trajectories_before_selection",
            "previous_tick_selected_planned_trajectory_memory",
            "planner_dt_seconds",
        ],
        "state_memory": {
            "source": "previous selected planned trajectory emitted before the current tick",
            "future_outcome_leakage": False,
            "first_tick_policy": "fail_closed_to_baseline_selector_or_emit_documented_neutral_only_under_explicit_runtime_flag",
            "missing_memory_policy": "fail_closed_before selector promotion",
        },
        "candidate_alignment": {
            "method": "drop elapsed dt from the previous plan and compare overlapping future pose samples on the same horizon/grid",
            "minimum_overlap_steps": 2,
            "coordinate_frame": "same ego/world frame already used for candidate scoring logs",
        },
        "non_equivalence_claim": [
            "stateful continuity against the previous selected plan, not current DP Top-1 ranking",
            "not candidate-set consensus or mode seeking because no current candidate ensemble centroid is used",
            "not route progress/lane-hard because route geometry is not used in the coefficient definition",
            "not comfort jerk/lateral because the coefficient compares two planned trajectories, not candidate derivatives",
            "not postprocess/tracker distortion because raw-vs-postprocess differences are not used",
        ],
    }


def _atom_contract() -> dict[str, Any]:
    return {
        "status": "temporal_consistency_atom_contract_predeclared",
        "coefficient_name": "previous_plan_temporal_consistency_rms_m",
        "definition": (
            "a_k = sqrt(mean_i ||p_candidate[k, i] - p_previous_shifted[i]||_2^2) "
            "over matched overlapping pose samples"
        ),
        "domain": "nonnegative_finite_scalar_per_candidate",
        "missing_or_nonfinite_policy": "fail_closed_before online selector promotion",
        "affine_score": "score_k(w)=a_k^T w after adding this fixed coefficient to the CAMP atom vector",
        "convex_master_argument": (
            "a_k is fixed before the master optimizes weights; simplex, CVaR, "
            "and L2 regularization remain convex in w"
        ),
    }


def _latency_contract() -> dict[str, Any]:
    return {
        "status": "temporal_consistency_latency_contract_predeclared",
        "complexity": "O(num_candidates * overlap_horizon)",
        "default_off_measurement_required": True,
        "runtime_preflight_required_before_replay": True,
        "budget_rule": (
            "must report component p50/p95 and fail closed if the planning "
            "path cannot retain positive p95 margin under 100 ms"
        ),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    proposal = source.get("matching_proposal") or {}
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_gate_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_payload_design",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal("support_source_ready", source["support_source_ready"], True),
        _check_contains(
            "temporal_source_admissible",
            source["admissible_support_sources"],
            SOURCE_NAME,
        ),
        _check_equal("proposal_source_family", proposal.get("source_family"), SOURCE_FAMILY),
        _check_equal("proposal_score_family", proposal.get("score_family"), SCORE_FAMILY),
        _check_equal("proposal_admissible", proposal.get("admissible"), True),
        _check_empty("source_no_blocked_actions", source["blocked_action_conflicts"]),
    ]


def _payload_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    memory = payload["state_memory"]
    return [
        _check_equal("payload_default_off", payload["default_off"], True),
        _check_equal("payload_memory_no_future_leakage", memory["future_outcome_leakage"], False),
        _check_equal(
            "payload_missing_memory_fail_closed",
            memory["missing_memory_policy"],
            "fail_closed_before selector promotion",
        ),
        _check_contains(
            "payload_has_previous_plan_memory",
            payload["runtime_inputs"],
            "previous_tick_selected_planned_trajectory_memory",
        ),
    ]


def _atom_checks(atom: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("atom_domain_nonnegative", atom["domain"], "nonnegative_finite_scalar_per_candidate"),
        _check_equal(
            "atom_missing_nonfinite_fail_closed",
            atom["missing_or_nonfinite_policy"],
            "fail_closed_before online selector promotion",
        ),
        _check_equal(
            "atom_affine_score_preserved",
            atom["affine_score"],
            "score_k(w)=a_k^T w after adding this fixed coefficient to the CAMP atom vector",
        ),
    ]


def _latency_checks(latency: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("latency_default_off_measurement_required", latency["default_off_measurement_required"], True),
        _check_equal("latency_runtime_preflight_required", latency["runtime_preflight_required_before_replay"], True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "payload_design_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Implement a default-off runtime preflight for logging the temporal "
            "consistency coefficient and measuring fail-closed latency. Do not "
            "run replay, train CAMP, or promote an online selector yet."
            if passed
            else "Repair the temporal consistency source proposal before payload design."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    payload = report["payload_contract"]
    atom = report["atom_contract"]
    latency = report["latency_contract"]
    lines = [
        "# Temporal Consistency Payload Design",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Payload design ready: `{decision['payload_design_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Payload Contract",
        "",
        f"- Status: `{payload['status']}`",
        f"- Default off: `{payload['default_off']}`",
        "- Runtime inputs: "
        + ", ".join(f"`{item}`" for item in payload["runtime_inputs"]),
        f"- First tick policy: `{payload['state_memory']['first_tick_policy']}`",
        f"- Missing memory policy: `{payload['state_memory']['missing_memory_policy']}`",
        "",
        "Non-equivalence claims:",
        "",
    ]
    for item in payload["non_equivalence_claim"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Atom Contract",
            "",
            f"- Coefficient: `{atom['coefficient_name']}`",
            f"- Definition: {atom['definition']}",
            f"- Domain: `{atom['domain']}`",
            f"- Affine score: `{atom['affine_score']}`",
            f"- Convex master: {atom['convex_master_argument']}",
            "",
            "## Latency Contract",
            "",
            f"- Complexity: `{latency['complexity']}`",
            f"- Budget rule: {latency['budget_rule']}",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This design gate does not authorize DP execution, replay, CAMP "
            "training, online selector promotion, Full36, formal seeds, DP "
            "modification, or a DP-side classical Benders claim.",
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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_contains(name: str, observed: Any, expected_member: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": f"contains {expected_member}",
        "passed": expected_member in value,
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
