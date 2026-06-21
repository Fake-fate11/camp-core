#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_CLOSED_SCORE_FAMILIES = (
    "progress_lane_hard_context",
    "revised_context_atom_family",
    "relaxed_strict_atom_family",
    "observable_interaction_family",
    "turn_logit_atom_family",
    "non_turn_interaction_family",
)

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
            "Read-only proof-protocol redesign gate for CAMP-on-fixed-DP. It "
            "consolidates current score-family closures, tensor-source closure, "
            "SafetyCost proof, proof-to-deployable gap, and support-bottleneck "
            "evidence before another design loop."
        )
    )
    parser.add_argument("--score_family_inventory_json", type=Path, required=True)
    parser.add_argument("--tensor_visibility_json", type=Path, required=True)
    parser.add_argument("--safety_cost_proof_json", type=Path, required=True)
    parser.add_argument("--proof_to_deployable_gap_json", type=Path, required=True)
    parser.add_argument("--support_bottleneck_json", type=Path, required=True)
    parser.add_argument("--next_design_preflight_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        score_family_inventory=_load_json(args.score_family_inventory_json),
        tensor_visibility=_load_json(args.tensor_visibility_json),
        safety_cost_proof=_load_json(args.safety_cost_proof_json),
        proof_to_deployable_gap=_load_json(args.proof_to_deployable_gap_json),
        support_bottleneck=_load_json(args.support_bottleneck_json),
        next_design_preflight=(
            None
            if args.next_design_preflight_json is None
            else _load_json(args.next_design_preflight_json)
        ),
        label=args.label,
        paths={
            "score_family_inventory_json": str(args.score_family_inventory_json),
            "tensor_visibility_json": str(args.tensor_visibility_json),
            "safety_cost_proof_json": str(args.safety_cost_proof_json),
            "proof_to_deployable_gap_json": str(args.proof_to_deployable_gap_json),
            "support_bottleneck_json": str(args.support_bottleneck_json),
            "next_design_preflight_json": _path_or_none(args.next_design_preflight_json),
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
    score_family_inventory: dict[str, Any],
    tensor_visibility: dict[str, Any],
    safety_cost_proof: dict[str, Any],
    proof_to_deployable_gap: dict[str, Any],
    support_bottleneck: dict[str, Any],
    next_design_preflight: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    sources = {
        "score_family_inventory": _score_family_source(score_family_inventory),
        "tensor_visibility": _tensor_visibility_source(tensor_visibility),
        "safety_cost_proof": _safety_cost_proof_source(safety_cost_proof),
        "proof_to_deployable_gap": _proof_to_deployable_source(
            proof_to_deployable_gap
        ),
        "support_bottleneck": _support_bottleneck_source(support_bottleneck),
        "next_design_preflight": _next_design_source(next_design_preflight),
    }
    conflicts = _authorization_conflicts(
        score_family_inventory,
        tensor_visibility,
        safety_cost_proof,
        proof_to_deployable_gap,
        support_bottleneck,
        *([] if next_design_preflight is None else [next_design_preflight]),
    )
    decision = _decision(sources, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_proof_protocol_redesign_gate_v1",
            "label": label,
            "role": (
                "read-only proof-protocol ledger after current atom/source "
                "routes and fixed-DP selector calibration routes have closed"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This gate "
                "only reads prior JSON artifacts and source decisions. Runtime "
                "CAMP features must remain fixed current-tick finite-candidate "
                "coefficients, so score_k(w)=a_k^T w stays affine and the "
                "simplex/CVaR/L2 robust master remains convex. Offline outcomes "
                "may be used only as evaluation labels. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed here."
            ),
        },
        "required_scenario_buckets": list(REQUIRED_SCENARIO_BUCKETS),
        "expected_closed_score_families": list(EXPECTED_CLOSED_SCORE_FAMILIES),
        "sources": sources,
        "source_authorization_conflicts": conflicts,
        "proof_protocol_v2_contract": _proof_protocol_contract(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _score_family_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    families = {
        str(row.get("name")): str(row.get("status"))
        for row in report.get("score_families") or []
        if isinstance(row, dict)
    }
    missing_or_unclosed = [
        family
        for family in EXPECTED_CLOSED_SCORE_FAMILIES
        if families.get(family) != "rejected_or_limited"
    ]
    status = str(final.get("status") or "")
    return {
        "status": status,
        "passed": (
            status == "no_leak_score_family_inventory_requires_new_design"
            and not missing_or_unclosed
        ),
        "missing_or_unclosed_families": missing_or_unclosed,
        "closed_families": [
            family
            for family in EXPECTED_CLOSED_SCORE_FAMILIES
            if families.get(family) == "rejected_or_limited"
        ],
    }


def _tensor_visibility_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    status = str(final.get("status") or "")
    candidate_sources = list(final.get("candidate_source_names") or [])
    closed_visible = list(final.get("closed_visible_candidate_source_names") or [])
    return {
        "status": status,
        "passed": (
            status == "current_tick_tensor_visibility_no_new_candidate_source"
            and not candidate_sources
        ),
        "primary_gap": final.get("primary_gap"),
        "candidate_sources": candidate_sources,
        "closed_visible_candidate_sources": closed_visible,
    }


def _safety_cost_proof_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    gates = report.get("gates") or {}
    candidate_pool = gates.get("candidate_pool_opportunity") or {}
    selector = gates.get("safety_cost_trained_selector_vs_top1") or {}
    current = gates.get("current_camp_vs_top1") or {}
    return {
        "status": final.get("status"),
        "passed": bool(candidate_pool.get("passed"))
        and bool(final.get("safety_cost_trained_selector_candidate_branch_proof")),
        "candidate_pool_opportunity_passed": bool(candidate_pool.get("passed")),
        "safety_cost_trained_selector_candidate_branch_proof": bool(
            final.get("safety_cost_trained_selector_candidate_branch_proof")
        ),
        "current_camp_complete_proof": bool(
            final.get("current_camp_complete_proof")
        ),
        "current_bucket_failures": current.get("bucket_failures") or {},
        "selector_bucket_failures": selector.get("bucket_failures") or {},
        "selector_overall_ci_high": selector.get("overall_ci_high"),
    }


def _proof_to_deployable_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    mechanism = report.get("mechanism") or {}
    return {
        "status": final.get("status"),
        "passed": final.get("status") == "deployable_gap_diagnosed",
        "candidate_support_exists": bool(mechanism.get("candidate_support_exists")),
        "candidate_branch_selector_passes": bool(
            mechanism.get("candidate_branch_selector_passes")
        ),
        "deployable_gate_passes": bool(mechanism.get("deployable_gate_passes")),
        "root_cause_class": mechanism.get("root_cause_class"),
        "primary_blockers": list(mechanism.get("primary_blockers") or []),
    }


def _support_bottleneck_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == "current_fixed_dp_selector_calibration_exhausted"
        ),
        "reasons": list(final.get("reasons") or []),
    }


def _next_design_source(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {
            "status": "not_supplied",
            "passed": True,
            "conditional_paths": [],
            "rejected_paths": [],
        }
    final = report.get("final_decision") or {}
    return {
        "status": final.get("status"),
        "passed": final.get("status")
        in {
            "next_design_preflight_has_conditional_paths",
            "next_design_boundary_requires_new_offline_design",
        },
        "conditional_paths": list(final.get("conditional_paths") or []),
        "rejected_paths": list(final.get("rejected_paths") or []),
    }


def _decision(
    sources: dict[str, dict[str, Any]],
    conflicts: list[str],
) -> dict[str, Any]:
    not_passed = [name for name, source in sources.items() if not source["passed"]]
    if conflicts:
        status = "proof_protocol_redesign_source_conflict"
        next_step = "Resolve source authorization conflicts before any proof redesign."
    elif not_passed:
        status = "proof_protocol_redesign_sources_incomplete"
        next_step = (
            "Refresh or inspect the incomplete source gates before declaring the "
            "current route family exhausted."
        )
    else:
        status = "proof_protocol_redesign_required"
        next_step = (
            "Write a design-only ProofProtocol v2 or scenario-objective gate. It "
            "must preserve the SafetyCost v1 claim rule, explicitly cover the "
            "required scenario buckets, compare against DP Top-1 and current CAMP, "
            "and reject any design that reopens closed score/tensor families."
        )
    return {
        "status": status,
        "passed": status == "proof_protocol_redesign_required",
        "incomplete_sources": not_passed,
        "source_authorization_conflicts": conflicts,
        "authorized_next_work": (
            "predeclare_proof_protocol_v2_or_scenario_objective_design_only"
        ),
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "reasons": _decision_reasons(sources, status),
        "next_step": next_step,
    }


def _decision_reasons(
    sources: dict[str, dict[str, Any]],
    status: str,
) -> list[str]:
    if status != "proof_protocol_redesign_required":
        return ["source_gates_do_not_yet_support_protocol_redesign"]
    reasons = [
        "closed_score_families_exhaust_current_atom_routes",
        "tensor_visibility_has_no_unclosed_runtime_candidate_source",
        "safetycost_candidate_branch_proof_exists",
        "deployable_closed_loop_gap_remains_open",
        "fixed_dp_selector_calibration_route_exhausted",
    ]
    conditional = sources["next_design_preflight"].get("conditional_paths") or []
    if conditional:
        reasons.append("legacy_conditional_paths_require_new_design_gate")
    return reasons


def _proof_protocol_contract() -> dict[str, Any]:
    return {
        "score": {
            "name": "SafetyCost_v1",
            "direction": "lower_is_better",
            "claim_rule": (
                "hard gate passes and ci95_high(CAMP_minus_DP_Top1) < 0"
            ),
            "tail_rule": "report and gate CVaR90 delta before larger nonformal runs",
        },
        "required_buckets": list(REQUIRED_SCENARIO_BUCKETS),
        "comparators": [
            "DP Top-1",
            "current logged CAMP",
            "hard-guarded candidate-branch oracle",
        ],
        "nondegradation_gates": [
            "collision nonpositive CI high",
            "near-miss nonpositive CI high",
            "lane nonpositive CI high",
            "realized red-light nonpositive CI high",
            "completion CI low >= -0.001",
            "progress, jerk, lateral, fallback, and latency explicitly reported",
            "per-run p95 planning path leaves positive margin under 100 ms",
        ],
        "no_leak_boundary": [
            "runtime inputs are current-tick finite-candidate quantities only",
            "posterior outcomes are offline labels only",
            "formal seeds 11/12/13 remain frozen until separately authorized",
            "closed score/tensor families must not be reopened",
        ],
        "math_boundary": [
            "new atoms must be fixed candidate coefficients",
            "signed quantities require a nonnegative split before CAMP scoring",
            "score_k(w)=a_k^T w remains affine",
            "simplex/CVaR/L2 robust master remains convex",
            "finite candidate selectors are not classical Benders",
        ],
    }


def _authorization_conflicts(*reports: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    for index, report in enumerate(reports):
        final = report.get("final_decision") or {}
        name = str(_get(report, "analysis", "name") or f"source_{index}")
        for key in BLOCKED_ACTIONS:
            if bool(final.get(key)):
                conflicts.append(f"{name}:{key}")
    return conflicts


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP Proof Protocol Redesign Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gates",
        "",
        "| Source | Status | Passed | Key detail |",
        "| --- | --- | ---: | --- |",
    ]
    for name, source in report["sources"].items():
        lines.append(
            f"| `{name}` | `{source.get('status')}` | `{source.get('passed')}` | "
            f"{_source_detail(name, source)} |"
        )
    lines.extend(
        [
            "",
            "## Closed Score Families",
            "",
        ]
    )
    for family in report["expected_closed_score_families"]:
        lines.append(f"- `{family}`")
    lines.extend(
        [
            "",
            "## ProofProtocol v2 Contract",
            "",
            f"- Score: `{report['proof_protocol_v2_contract']['score']['name']}` "
            f"({report['proof_protocol_v2_contract']['score']['direction']})",
            f"- Claim rule: {report['proof_protocol_v2_contract']['score']['claim_rule']}",
            f"- Required buckets: `{', '.join(report['required_scenario_buckets'])}`",
            "- Comparators: "
            + ", ".join(
                f"`{item}`"
                for item in report["proof_protocol_v2_contract"]["comparators"]
            ),
            "",
            "Nondegradation gates:",
        ]
    )
    for item in report["proof_protocol_v2_contract"]["nondegradation_gates"]:
        lines.append(f"- {item}")
    lines.extend(["", "No-leak boundary:"])
    for item in report["proof_protocol_v2_contract"]["no_leak_boundary"]:
        lines.append(f"- {item}")
    lines.extend(["", "Mathematical boundary:"])
    for item in report["proof_protocol_v2_contract"]["math_boundary"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Decision Reasons",
            "",
        ]
    )
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Blocked Actions",
            "",
        ]
    )
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
        lines.append(f"| `{name}` | `{path or 'none'}` |")
    lines.append("")
    return "\n".join(lines)


def _source_detail(name: str, source: dict[str, Any]) -> str:
    if name == "score_family_inventory":
        return (
            "`missing_or_unclosed=`"
            + ", ".join(source.get("missing_or_unclosed_families") or ["none"])
        )
    if name == "tensor_visibility":
        return (
            "`candidate_sources=`"
            + ", ".join(source.get("candidate_sources") or ["none"])
        )
    if name == "safety_cost_proof":
        return f"`selector_ci_high={source.get('selector_overall_ci_high')}`"
    if name == "proof_to_deployable_gap":
        return "`blockers=`" + ", ".join(source.get("primary_blockers") or ["none"])
    if name == "support_bottleneck":
        return "`reasons=`" + ", ".join(source.get("reasons") or ["none"])
    if name == "next_design_preflight":
        return "`conditional=`" + ", ".join(source.get("conditional_paths") or ["none"])
    return ""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
