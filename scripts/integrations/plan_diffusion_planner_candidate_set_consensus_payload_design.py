#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "post_reconciliation_source_proposal_screen_ready"
SOURCE_READY_NEXT_WORK = "default_off_current_tick_source_payload_design_only"
SOURCE_NAME = "candidate_set_consensus_density_source_v1"
SOURCE_FAMILY = "candidate_set_geometry_consensus"
SCORE_FAMILY = "candidate_set_consensus_density_atom_family"

READY_STATUS = "candidate_set_consensus_payload_design_ready"
BLOCKED_STATUS = "candidate_set_consensus_payload_design_blocked"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_existing_log_materiality_screen_only"

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
            "Design-only gate for the accepted candidate-set consensus source. "
            "It predeclares the default-off payload, coefficient definition, "
            "latency budget, and existing-log materiality screen without "
            "running DP, replay, training, or online selection."
        )
    )
    parser.add_argument("--source_proposal_screen_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_proposal_screen=_load_json(args.source_proposal_screen_json),
        label=args.label,
        paths={"source_proposal_screen_json": str(args.source_proposal_screen_json)},
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
    source_proposal_screen: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(source_proposal_screen)
    payload = _payload_contract()
    coefficient = _coefficient_contract()
    latency = _latency_contract()
    materiality = _materiality_contract()
    checks = [
        *_source_checks(source),
        *_payload_checks(payload),
        *_coefficient_checks(coefficient),
        *_latency_checks(latency),
        *_materiality_checks(materiality),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_payload_design_v1",
            "label": label,
            "role": (
                "design-only default-off payload contract for candidate-set "
                "consensus as a CAMP-on-DP current-tick candidate source"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The payload "
                "would compute fixed current-tick finite-candidate coefficients "
                "a_k from the already generated DP candidate tensor before "
                "selection. CAMP may score them as score_k(w)=a_k^T w. Since "
                "the robust master optimizes only over weights w, not trajectory "
                "coordinates, simplex/CVaR/L2 optimization remains convex in w. "
                "This gate makes no trajectory-coordinate convexity claim and "
                "constructs no DP-side classical Benders master/subproblem, "
                "dual, or valid cut."
            ),
        },
        "source_summary": source,
        "payload_contract": payload,
        "coefficient_contract": coefficient,
        "latency_contract": latency,
        "materiality_contract": materiality,
        "design_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    payload = report["payload_contract"]
    coefficient = report["coefficient_contract"]
    latency = report["latency_contract"]
    materiality = report["materiality_contract"]
    lines = [
        "# Candidate-Set Consensus Payload Design",
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
        f"- Missing candidate policy: `{payload['candidate_tensor_policy']['missing_candidate_tensor']}`",
        f"- Nonfinite policy: `{payload['candidate_tensor_policy']['nonfinite_candidate_tensor']}`",
        "",
        "Non-equivalence claims:",
        "",
    ]
    for item in payload["non_equivalence_claim"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Coefficient Contract",
            "",
            f"- Primary coefficient: `{coefficient['primary_coefficient_name']}`",
            f"- Definition: {coefficient['primary_definition']}",
            f"- Domain: `{coefficient['domain']}`",
            f"- Normalization: {coefficient['normalization']}",
            f"- Affine score: `{coefficient['affine_score']}`",
            f"- Convex master: {coefficient['convex_master_argument']}",
            "",
            "Diagnostic fields:",
            "",
        ]
    )
    for field in coefficient["diagnostic_fields"]:
        lines.append(f"- `{field}`")
    lines.extend(
        [
            "",
            "## Latency Contract",
            "",
            f"- Complexity: `{latency['complexity']}`",
            f"- Budget rule: {latency['budget_rule']}",
            "",
            "## Existing-Log Materiality Contract",
            "",
            "- Required fields: "
            + ", ".join(f"`{item}`" for item in materiality["required_existing_log_fields"]),
            f"- Minimum records: `{materiality['minimum_valid_records']}`",
            f"- Outcome use: `{materiality['outcome_use']}`",
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


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    proposal_rows = [
        row for row in report.get("proposal_rows") or [] if isinstance(row, dict)
    ]
    matching = [row for row in proposal_rows if row.get("name") == SOURCE_NAME]
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "support_source_ready": bool(decision.get("support_source_ready")),
        "admissible_sources": list(decision.get("admissible_sources") or []),
        "matching_proposal": matching[0] if matching else None,
        "blocked_action_conflicts": conflicts,
    }


def _payload_contract() -> dict[str, Any]:
    return {
        "status": "candidate_set_consensus_payload_contract_predeclared",
        "schema_version": "candidate_set_consensus_payload_v1",
        "default_off": True,
        "selection_effect": False,
        "runtime_inputs": [
            "current_tick_dp_candidate_trajectories_before_selection",
            "candidate_count",
            "candidate_horizon_steps",
            "candidate_xy_positions",
        ],
        "candidate_tensor_policy": {
            "required_shape": "[K,T,D>=2]",
            "minimum_candidates": 2,
            "minimum_horizon_steps": 2,
            "coordinate_frame": "same frame already used by CAMP candidate scoring logs",
            "missing_candidate_tensor": "fail_closed_before selector promotion",
            "nonfinite_candidate_tensor": "fail_closed_before selector promotion",
            "rank_or_top1_fields_used": False,
        },
        "non_equivalence_claim": [
            "uses the symmetric current candidate ensemble, not DP Top-1 rank or candidate index",
            "uses no previous-plan memory, so it is not temporal consistency",
            "uses no traffic-light phase, route speed, stopline, lane boundary, or map-control timing",
            "uses no NPC, obstacle, TTC, clearance, or conflict-zone state",
            "does not compare raw and postprocessed versions of the same candidate",
            "does not alter candidate generation, K, noise, anchors, DP weights, or guidance",
        ],
    }


def _coefficient_contract() -> dict[str, Any]:
    return {
        "status": "candidate_set_consensus_coefficient_contract_predeclared",
        "primary_coefficient_name": "candidate_set_consensus_center_rms_cost_v1",
        "primary_definition": (
            "For candidate k, let c_i be the coordinate-wise median xy position "
            "over all K candidates at horizon step i. Compute "
            "a_k = sqrt(mean_i ||p_{k,i} - c_i||_2^2) over the declared "
            "current-tick horizon."
        ),
        "diagnostic_fields": [
            "candidate_set_consensus_center_xy",
            "candidate_set_consensus_center_rms_m",
            "candidate_set_consensus_center_rms_rank",
            "candidate_set_consensus_center_rms_median_m",
            "candidate_set_consensus_center_rms_mad_m",
        ],
        "normalization": (
            "runtime payload records raw meters plus deterministic median/MAD "
            "diagnostics; any later atom normalization or clipping must be "
            "predeclared in a separate atom-schema gate"
        ),
        "domain": "nonnegative_finite_scalar_per_candidate",
        "missing_or_nonfinite_policy": "fail_closed_before online selector promotion",
        "deterministic_tie_handling": (
            "coefficient computation is symmetric and deterministic; any later "
            "selector tie-break must retain the existing deterministic candidate "
            "index order"
        ),
        "affine_score": "score_k(w)=a_k^T w after adding this fixed coefficient to the CAMP atom vector",
        "convex_master_argument": (
            "a_k is fixed before the master optimizes weights; simplex, CVaR, "
            "and L2 regularization remain convex in w"
        ),
        "trajectory_coordinate_convexity_claim": False,
    }


def _latency_contract() -> dict[str, Any]:
    return {
        "status": "candidate_set_consensus_latency_contract_predeclared",
        "complexity": "O(num_candidates * horizon_steps) for median center and RMS diagnostics",
        "default_off_measurement_required": True,
        "component_latency_field": "latency_ms_candidate_set_consensus_payload",
        "runtime_preflight_required_before_replay": True,
        "budget_rule": (
            "must report p50/p95 component latency and fail closed if the "
            "overall planning path cannot retain positive p95 margin under 100 ms"
        ),
    }


def _materiality_contract() -> dict[str, Any]:
    return {
        "status": "candidate_set_consensus_existing_log_materiality_predeclared",
        "new_replay_required": False,
        "required_existing_log_fields": [
            "candidate_raw_trajectory_prefix",
            "candidate_raw_trajectory_prefix_steps",
            "selected_index",
        ],
        "minimum_valid_records": 12,
        "minimum_candidate_count": 2,
        "minimum_nonzero_spread_rate": 0.25,
        "outcome_use": (
            "existing safety or oracle labels may be joined only for offline "
            "materiality diagnosis; they must not be used to compute runtime "
            "coefficients"
        ),
        "next_gate": "read-only existing-log materiality screen before payload implementation or replay",
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
            "candidate_set_consensus_source_admissible",
            source["admissible_sources"],
            SOURCE_NAME,
        ),
        _check_equal("proposal_source_family", proposal.get("source_family"), SOURCE_FAMILY),
        _check_equal("proposal_score_family", proposal.get("score_family"), SCORE_FAMILY),
        _check_equal("proposal_admissible", proposal.get("admissible"), True),
        _check_empty("source_no_blocked_actions", source["blocked_action_conflicts"]),
    ]


def _payload_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    policy = payload["candidate_tensor_policy"]
    return [
        _check_equal("payload_default_off", payload["default_off"], True),
        _check_equal("payload_selection_effect_false", payload["selection_effect"], False),
        _check_equal("payload_minimum_candidates", policy["minimum_candidates"], 2),
        _check_equal(
            "payload_missing_candidate_tensor_fail_closed",
            policy["missing_candidate_tensor"],
            "fail_closed_before selector promotion",
        ),
        _check_equal(
            "payload_nonfinite_candidate_tensor_fail_closed",
            policy["nonfinite_candidate_tensor"],
            "fail_closed_before selector promotion",
        ),
        _check_equal("payload_uses_no_rank_or_top1", policy["rank_or_top1_fields_used"], False),
        _check_contains(
            "payload_has_candidate_trajectories",
            payload["runtime_inputs"],
            "current_tick_dp_candidate_trajectories_before_selection",
        ),
    ]


def _coefficient_checks(coefficient: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "coefficient_domain_nonnegative",
            coefficient["domain"],
            "nonnegative_finite_scalar_per_candidate",
        ),
        _check_equal(
            "coefficient_missing_nonfinite_fail_closed",
            coefficient["missing_or_nonfinite_policy"],
            "fail_closed_before online selector promotion",
        ),
        _check_equal(
            "coefficient_affine_score_preserved",
            coefficient["affine_score"],
            "score_k(w)=a_k^T w after adding this fixed coefficient to the CAMP atom vector",
        ),
        _check_equal(
            "coefficient_no_trajectory_convexity_claim",
            coefficient["trajectory_coordinate_convexity_claim"],
            False,
        ),
    ]


def _latency_checks(latency: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("latency_default_off_measurement_required", latency["default_off_measurement_required"], True),
        _check_equal("latency_runtime_preflight_required", latency["runtime_preflight_required_before_replay"], True),
    ]


def _materiality_checks(materiality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("materiality_no_new_replay_required", materiality["new_replay_required"], False),
        _check_equal("materiality_minimum_valid_records", materiality["minimum_valid_records"], 12),
        _check_contains(
            "materiality_requires_candidate_prefix",
            materiality["required_existing_log_fields"],
            "candidate_raw_trajectory_prefix",
        ),
        _check_equal(
            "materiality_runtime_coefficients_no_outcome_use",
            "must not be used to compute runtime coefficients" in materiality["outcome_use"],
            True,
        ),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "payload_design_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Run a read-only existing-log materiality screen for the candidate-set "
            "consensus coefficient before payload implementation, replay, training, "
            "or online selector work."
            if passed
            else "Repair the candidate-set consensus source proposal before payload design."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
