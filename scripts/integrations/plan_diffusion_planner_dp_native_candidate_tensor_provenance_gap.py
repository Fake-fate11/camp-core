#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


READY_STATUS = "dp_native_candidate_tensor_provenance_gap_design_plan_ready"
REJECT_STATUS = "dp_native_candidate_tensor_provenance_gap_design_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "dp_native_candidate_tensor_provenance_payload_implementation_authorization_only"
)
DEFAULT_EVIDENCE_AUDIT_JSON = (
    ROOT
    / "analysis_bundles"
    / "dp_native_candidate_reranking_fixed_artifact_evidence_audit_5467a3f"
    / "dp_native_candidate_reranking_fixed_artifact_evidence_audit.json"
)
REQUIRED_SOURCE_GAPS = (
    "candidate_tensor_hash_missing",
    "full_candidate_coordinate_tensor_artifact_missing",
    "raw_dp_pre_camp_candidate_set_immutability_not_proven",
    "reference_blend_selection_effect_requires_provenance_separation",
    "full_candidate_tensor_mutation_absence_not_proven",
)
BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "trajectory_rewrite_authorized",
    "candidate_tensor_mutation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "offline_selector_screen_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "atom_promotion_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for closing DP-native candidate tensor provenance "
            "gaps before any reranking/replay/training claim."
        )
    )
    parser.add_argument(
        "--evidence_audit_json",
        type=Path,
        default=DEFAULT_EVIDENCE_AUDIT_JSON,
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        evidence_audit=_load_json(args.evidence_audit_json),
        evidence_audit_json=str(args.evidence_audit_json),
        label=args.label,
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
    evidence_audit: dict[str, Any],
    evidence_audit_json: str = str(DEFAULT_EVIDENCE_AUDIT_JSON),
    label: str | None = None,
) -> dict[str, Any]:
    source = _source_summary(evidence_audit)
    plan = _design_plan(evidence_audit_json=evidence_audit_json, source=source)
    checks = [
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_native_candidate_tensor_provenance_gap_design_plan_v1",
            "label": label,
            "role": (
                "plan-only response to fixed-artifact evidence gaps; defines "
                "the minimum provenance contract needed before DP-native "
                "reranking can advance"
            ),
            "plan_only": True,
            "read_only": True,
            "candidate_generation_execution": False,
            "trajectory_rewrite": False,
            "candidate_tensor_mutation": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This plan reads only the completed evidence audit and writes a "
                "provenance remediation design. It does not implement logging, "
                "run replay, generate candidates, rewrite trajectories, train "
                "CAMP, promote atoms, change online selection, modify DP, claim "
                "safety benefit, or claim CAMP over DP Top-1."
            ),
        },
        "source_summary": source,
        "provenance_gap_design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["provenance_gap_design_plan"]
    lines = [
        "# DP-Native Candidate Tensor Provenance Gap Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized now: `{decision['implementation_authorized_now']}`",
        f"- Replay authorized: `{decision['new_replay_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Evidence Audit",
        "",
        f"- Source status: `{source['status']}`",
        f"- Evidence audit complete: `{source['evidence_audit_complete']}`",
        f"- DP-native reranking evidence ready: `{source['dp_native_reranking_evidence_ready']}`",
        f"- Source authorized next work: `{source['authorized_next_work']}`",
        "",
        "## Required Provenance Stages",
        "",
    ]
    for stage in plan["required_provenance_stages"]:
        lines.append(f"- `{stage}`")
    lines.extend(["", "## Required Fields", ""])
    for field in plan["required_payload_fields"]:
        lines.append(f"- `{field}`")
    lines.extend(["", "## Acceptance Criteria", ""])
    for item in plan["acceptance_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    gaps = list(decision.get("evidence_gaps") or [])
    blocked = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "evidence_audit_complete": bool(decision.get("evidence_audit_complete")),
        "dp_native_reranking_evidence_ready": bool(
            decision.get("dp_native_reranking_evidence_ready")
        ),
        "candidate_tensor_provenance_gap": bool(
            decision.get("candidate_tensor_provenance_gap")
        ),
        "authorized_next_work": decision.get("authorized_next_work"),
        "evidence_gaps": gaps,
        "blocked_action_conflicts": blocked,
    }


def _design_plan(*, evidence_audit_json: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_audit_json": evidence_audit_json,
        "gap_class": "candidate_tensor_provenance_and_immutability_not_proven",
        "route": "default_off_candidate_tensor_provenance_payload_design",
        "required_provenance_stages": [
            "dp_sampler_output_before_reference_blend_or_any_camp_side_transform",
            "camp_scoring_input_after_dp_postprocess_before_camp_scoring",
            "post_camp_selector_candidate_tensor_reference",
        ],
        "required_payload_fields": [
            "candidate_tensor_provenance_schema_version",
            "candidate_tensor_source_stage",
            "candidate_tensor_shape",
            "candidate_tensor_dtype",
            "candidate_count",
            "candidate_tensor_sha256",
            "candidate_tensor_hash_method",
            "selected_index",
            "selected_index_in_range",
            "pre_camp_scoring_tensor_sha256",
            "post_camp_selector_tensor_sha256",
            "pre_post_tensor_hash_equal",
            "reference_blend_applied",
            "reference_blend_stage_hash_separated",
            "selection_effect",
            "uses_outcome_labels",
            "online_selector_change",
            "dp_modification",
        ],
        "hash_contract": {
            "canonicalization": (
                "hash the contiguous candidate tensor bytes plus explicit shape "
                "and dtype metadata at each declared stage"
            ),
            "minimum_hashes": [
                "camp_scoring_input_after_dp_postprocess_before_camp_scoring",
                "post_camp_selector_candidate_tensor_reference",
            ],
            "raw_dp_hash_required_when_available": True,
            "nan_policy": "preserve tensor bytes; do not stringify floating point values",
        },
        "acceptance_criteria": [
            "payload is default-off and has selection_effect=False",
            "payload records candidate_count and selected_index range proof",
            "pre/post CAMP selector tensor hashes are present and identical",
            "reference-blend or postprocess stage is explicitly separated from CAMP reranking",
            "no candidate rows are appended and no coordinates/headings/speeds are rewritten by CAMP",
            "no outcome labels, replay outcomes, online selector changes, training, promotion, or DP modification are authorized",
        ],
        "next_gate": AUTHORIZED_NEXT_WORK,
        "implementation_authorized_now": False,
        "replay_authorized": False,
        "training_authorized": False,
        "promotion_authorized": False,
        "claim_authorized": False,
        "source_gap_count": len(source["evidence_gaps"]),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = set(source["evidence_gaps"])
    return [
        _check("source_audit_complete", source["evidence_audit_complete"]),
        _check("source_not_ready", not source["dp_native_reranking_evidence_ready"]),
        _check("source_has_provenance_gap", source["candidate_tensor_provenance_gap"]),
        _check(
            "source_authorizes_this_design",
            source["authorized_next_work"]
            == "dp_native_candidate_tensor_provenance_gap_design_plan_only",
        ),
        *[
            _check(f"source_gap_{gap}", gap in gaps)
            for gap in REQUIRED_SOURCE_GAPS
        ],
        _check("source_no_blocked_authorizations", not source["blocked_action_conflicts"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    required = set(plan["required_payload_fields"])
    return [
        _check("plan_route", plan["route"] == "default_off_candidate_tensor_provenance_payload_design"),
        _check("plan_has_three_stages", len(plan["required_provenance_stages"]) == 3),
        _check("plan_records_tensor_hash", "candidate_tensor_sha256" in required),
        _check("plan_records_selected_index_range", "selected_index_in_range" in required),
        _check("plan_records_pre_post_hash_equal", "pre_post_tensor_hash_equal" in required),
        _check("plan_separates_reference_blend", "reference_blend_stage_hash_separated" in required),
        _check("plan_next_gate", plan["next_gate"] == AUTHORIZED_NEXT_WORK),
        _check("plan_no_implementation_now", not plan["implementation_authorized_now"]),
        _check("plan_no_replay", not plan["replay_authorized"]),
        _check("plan_no_training", not plan["training_authorized"]),
        _check("plan_no_promotion", not plan["promotion_authorized"]),
        _check("plan_no_claim", not plan["claim_authorized"]),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_no_replay", not plan["replay_authorized"]),
        _check("boundary_no_training", not plan["training_authorized"]),
        _check("boundary_no_promotion", not plan["promotion_authorized"]),
        _check("boundary_no_claim", not plan["claim_authorized"]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_authorized_now": False,
        "provenance_payload_implementation_authorization_ready": passed,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
