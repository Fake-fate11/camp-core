#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_REDESIGN_STATUS = "proof_protocol_redesign_required"
REQUIRED_NEXT_WORK = "predeclare_proof_protocol_v2_or_scenario_objective_design_only"

REQUIRED_SCENARIO_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Predeclare DP-CAMP ProofProtocol v2 after the proof-protocol "
            "redesign gate. This is design-only and does not run DP."
        )
    )
    parser.add_argument("--redesign_gate_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        redesign_gate=_load_json(args.redesign_gate_json),
        label=args.label,
        paths={"redesign_gate_json": str(args.redesign_gate_json)},
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
    redesign_gate: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _redesign_source(redesign_gate)
    protocol = _protocol_contract()
    decision = _decision(source)
    return {
        "analysis": {
            "name": "dp_camp_proof_protocol_v2_predeclaration",
            "label": label,
            "role": (
                "design-only predeclaration of the score, buckets, gates, "
                "comparators, and mathematical boundary required before any "
                "new DP-CAMP evidence collection"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box finite-candidate generator. "
                "CAMP may score fixed current-tick candidate coefficients with "
                "score_k(w)=a_k^T w, and the simplex/CVaR/L2 robust master must "
                "remain convex. Offline outcomes are labels for proof only. "
                "No DP-side classical Benders master/subproblem, dual, or cut "
                "is constructed by this protocol."
            ),
        },
        "source_gate": source,
        "protocol": protocol,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _redesign_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    blocked_true = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    required_buckets = list(report.get("required_scenario_buckets") or [])
    missing_buckets = [
        bucket for bucket in REQUIRED_SCENARIO_BUCKETS if bucket not in required_buckets
    ]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == REQUIRED_REDESIGN_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == REQUIRED_NEXT_WORK
            and not blocked_true
            and not missing_buckets
        ),
        "blocked_true": blocked_true,
        "missing_required_buckets": missing_buckets,
        "authorized_next_work": final.get("authorized_next_work"),
        "reasons": list(final.get("reasons") or []),
    }


def _protocol_contract() -> dict[str, Any]:
    return {
        "name": "DP-CAMP ProofProtocol v2",
        "primary_score": {
            "name": "SafetyCost_v1",
            "direction": "lower_is_better",
            "formula": (
                "100*collision + 10*near_miss + 20*lane + 30*realized_red "
                "+ 15*planned_red + clip(jerk/10,0,10) "
                "+ 2*clip(lateral/2,0,10) + 2*clip(1-completion,0,1)"
            ),
            "component_fields": {
                "collision": "obb_collision_rate",
                "near_miss": "near_miss_rate",
                "lane": "lane_violation_rate",
                "realized_red": "red_light_violation_rate",
                "planned_red": "planned_red_light_violation_rate",
                "jerk": "mean_jerk_magnitude_mps3",
                "lateral": "mean_lateral_acceleration_mps2",
                "completion": "route_completion_rate",
            },
            "claim_rule": (
                "hard_gate_passed and ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0"
            ),
            "tail_rule": (
                "report CVaR90 delta at every gate; require nonpositive CVaR90 "
                "CI high before moving beyond tiny nonformal smoke"
            ),
        },
        "required_scenario_buckets": list(REQUIRED_SCENARIO_BUCKETS),
        "bucket_manifest_rules": [
            "bucket labels must be predeclared before collecting new evidence",
            "filters may use route/config fields but not closed-loop outcomes",
            "every run is overall plus zero or more explicit manifest buckets",
            "a proof claim requires nonempty coverage for every required bucket",
        ],
        "comparators": [
            "DP Top-1",
            "current logged CAMP",
            "hard-guarded candidate-branch oracle",
            "candidate-branch SafetyCost-trained CAMP selector",
            "future deployable CAMP selector if separately authorized",
        ],
        "hard_gates": {
            "collision": "paired mean delta <= 0 and CI high <= 0",
            "near_miss": "paired mean delta <= 0 and CI high <= 0",
            "lane": "paired mean delta <= 0 and CI high <= 0",
            "realized_red": "paired mean delta <= 0 and CI high <= 0",
            "completion": "paired route_completion_rate CI low >= -0.001",
            "latency": "total planning-path p95 must leave positive margin under 100 ms",
            "fallback": "fallback rate must be reported and must not explain the win",
            "formal_seeds": "seeds 11/12/13 are forbidden until separately authorized",
        },
        "development_ladder": [
            {
                "gate": "scenario_manifest_design",
                "allowed": "write manifest/route matrix only",
                "promotion_condition": "all required buckets are explicitly covered",
            },
            {
                "gate": "candidate_branch_oracle_audit",
                "allowed": "offline labels from nonformal outcome logs only",
                "promotion_condition": (
                    "hard-guarded oracle shows exploitable opportunity versus Top-1"
                ),
            },
            {
                "gate": "selector_training_or_weight_design",
                "allowed": "only after oracle audit proves support and no leakage",
                "promotion_condition": (
                    "atoms are current-tick finite coefficients and score remains affine"
                ),
            },
            {
                "gate": "tiny_paired_nonformal_smoke",
                "allowed": "only after latency projection and unit gates pass",
                "promotion_condition": (
                    "SafetyCost/hard gates/fallback/latency all pass on paired runs"
                ),
            },
            {
                "gate": "larger_nonformal_matrix",
                "allowed": "12/36-run only after tiny smoke has margin",
                "promotion_condition": "predeclared SafetyCost and CVaR gates pass",
            },
            {
                "gate": "formal_seeds",
                "allowed": "separate authorization only",
                "promotion_condition": "development gates are complete and frozen",
            },
        ],
        "runtime_no_leak_contract": [
            "DP candidate trajectories and current tick context are runtime inputs",
            "closed-loop branch outcomes are offline labels only",
            "posterior SafetyCost, red-light violations, collisions, and completion are never selector inputs",
            "closed score/tensor families are not reopened without a new source gate",
        ],
        "camp_math_contract": [
            "each atom is a fixed finite-candidate coefficient at selection time",
            "nonnegative atoms are used directly",
            "signed candidate quantities require a nonnegative split or explicit affine coefficient accounting",
            "score_k(w)=a_k^T w remains affine in CAMP weights",
            "simplex, CVaR, and L2 robust masters remain convex",
            "finite candidate ranking is not a classical Benders decomposition",
        ],
    }


def _decision(source: dict[str, Any]) -> dict[str, Any]:
    if not source["passed"]:
        status = "proof_protocol_v2_predeclaration_blocked_by_source_gate"
        next_step = "Refresh or repair the proof-protocol redesign gate first."
        reasons = ["redesign_gate_does_not_authorize_protocol_v2"]
    else:
        status = "proof_protocol_v2_predeclared"
        next_step = (
            "Build a design-only scenario manifest and evidence matrix plan. "
            "Do not run replay until the manifest gate proves all required "
            "buckets are covered without outcome-field filters."
        )
        reasons = [
            "safetycost_v1_claim_rule_predeclared",
            "diverse_required_buckets_predeclared",
            "comparators_and_hard_gates_predeclared",
            "no_leak_and_convex_camp_boundary_predeclared",
        ]
    return {
        "status": status,
        "passed": status == "proof_protocol_v2_predeclared",
        "authorized_next_work": "scenario_manifest_and_evidence_matrix_design_only",
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "reasons": reasons,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    protocol = report["protocol"]
    score = protocol["primary_score"]
    lines = [
        "# DP-CAMP ProofProtocol v2 Predeclaration",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gate",
        "",
        f"- Status: `{report['source_gate']['status']}`",
        f"- Passed: `{report['source_gate']['passed']}`",
        f"- Blocked true: `{', '.join(report['source_gate']['blocked_true']) or 'none'}`",
        f"- Missing buckets: `{', '.join(report['source_gate']['missing_required_buckets']) or 'none'}`",
        "",
        "## Primary Score",
        "",
        f"- Name: `{score['name']}`",
        f"- Direction: `{score['direction']}`",
        f"- Formula: `{score['formula']}`",
        f"- Claim rule: {score['claim_rule']}",
        f"- Tail rule: {score['tail_rule']}",
        "",
        "## Required Scenario Buckets",
        "",
    ]
    for bucket in protocol["required_scenario_buckets"]:
        lines.append(f"- `{bucket}`")
    lines.extend(["", "## Comparators", ""])
    for item in protocol["comparators"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Hard Gates", ""])
    for name, rule in protocol["hard_gates"].items():
        lines.append(f"- `{name}`: {rule}")
    lines.extend(["", "## Development Ladder", ""])
    for step in protocol["development_ladder"]:
        lines.append(
            f"- `{step['gate']}`: allowed={step['allowed']}; "
            f"promotion={step['promotion_condition']}"
        )
    lines.extend(["", "## Runtime No-Leak Contract", ""])
    for item in protocol["runtime_no_leak_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## CAMP Math Contract", ""])
    for item in protocol["camp_math_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Blocked Actions", ""])
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision.get(action, False)}`")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Source Artifacts",
            "",
            "| Artifact | Path |",
            "| --- | --- |",
        ]
    )
    for name, path in (report["analysis"].get("paths") or {}).items():
        lines.append(f"| `{name}` | `{path}` |")
    lines.append("")
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
