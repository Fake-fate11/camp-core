#!/usr/bin/env python3
"""Plan remediation for v13 non-overlap failure attribution.

This is a plan-only gate. It consumes the read-only non-overlap failure
attribution artifact and defines the contract required before any future fixed-DP
evaluation collection or static DP-reward training preflight. It does not run
replay, generate candidates, train CAMP, modify Diffusion Planner, promote
artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_plan_rejected"
)
ATTRIBUTED_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_attributed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_SELECTION_LOG_COUNT = 32
EXPECTED_RECORD_COUNT = 3200
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only remediation after a recovered-registry non-overlap "
            "failure attribution."
        )
    )
    parser.add_argument("--nonoverlap_failure_attribution_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        nonoverlap_failure_attribution_json=args.nonoverlap_failure_attribution_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    nonoverlap_failure_attribution_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    nonoverlap_failure_attribution_json = nonoverlap_failure_attribution_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    attribution = _load_json_dict(nonoverlap_failure_attribution_json)
    audit_text = v13_audit_md.read_text(encoding="utf-8")
    plan = _remediation_plan(attribution)
    checks = _checks(
        nonoverlap_failure_attribution_json=nonoverlap_failure_attribution_json,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        attribution=attribution,
        plan=plan,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only_inputs": True,
            "training_execution": False,
            "training_preflight": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "nonoverlap_failure_attribution_json": str(nonoverlap_failure_attribution_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "attribution_summary": _attribution_summary(attribution),
        "remediation_plan": plan,
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _remediation_plan(attribution: dict[str, Any]) -> dict[str, Any]:
    evidence = _dict(attribution.get("overlap_evidence"))
    return {
        "objective": (
            "define a later fixed-DP evaluation split that is independent of "
            "the full 76c2 training manifest and all recovered missing-prior "
            "registry evidence before any static DP-reward training preflight"
        ),
        "source_failure_class": _dict(attribution.get("attribution")).get("failure_class"),
        "minimum_future_evaluation": {
            "selection_log_count": EXPECTED_SELECTION_LOG_COUNT,
            "record_count": EXPECTED_RECORD_COUNT,
            "candidate_count": EXPECTED_CANDIDATE_COUNT,
            "atom_count": EXPECTED_ATOM_COUNT,
            "formal_seeds_11_12_13_excluded": True,
        },
        "required_static_contracts": {
            "split_manifest_required": True,
            "training_manifest_sources_must_be_loaded": True,
            "recovered_missing_prior_registry_must_be_loaded": True,
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "candidate_tensor_eval_hashes_in_previous_must_be_zero": True,
            "candidate_hash_intersection_must_be_zero": True,
            "path_signature_intersection_must_be_zero": True,
            "record_identity_intersection_must_be_zero": True,
            "raw_log_absence_must_not_disable_registry_overlap_checks": True,
            "default_off_shadow_selector_contract_required": True,
            "affine_score_contract_required": True,
            "dp_head_fixed_contract_required": True,
        },
        "forbidden_reuse": {
            "reuse_current_failed_evaluation_output_dir": True,
            "reuse_any_training_manifest_selection_log_as_eval": True,
            "reuse_recovered_prior_c92_registry_records_as_eval": True,
            "reuse_eval_route_seed_npc_spawn_tl_static_shadow_signature_in_training": True,
        },
        "source_overlap_evidence": {
            "training_manifest_log_count": evidence.get("training_manifest_log_count"),
            "training_missing_log_count": evidence.get("training_missing_log_count"),
            "candidate_hash_intersection_count": evidence.get(
                "candidate_hash_intersection_count"
            ),
            "path_signature_intersection_count": evidence.get(
                "path_signature_intersection_count"
            ),
            "record_identity_intersection_count": evidence.get(
                "record_identity_intersection_count"
            ),
            "candidate_tensor_eval_hashes_in_previous_rate": evidence.get(
                "candidate_tensor_eval_hashes_in_previous_rate"
            ),
        },
        "blocked_by_this_plan": {
            "training_preflight": True,
            "training_execution": True,
            "replay_execution": True,
            "fixed_dp_candidate_generation_execution": True,
            "candidate_generation_by_camp": True,
            "trajectory_generation_by_camp": True,
            "trajectory_modification_by_camp": True,
            "dp_modification": True,
            "selector_promotion": True,
            "atom_promotion": True,
            "deployment": True,
            "deployable_checkpoint_claim": True,
            "safety_benefit_claim": True,
            "camp_over_dp_top1_claim": True,
        },
        "next_gate": {
            "kind": "static_contract_review_only",
            "purpose": (
                "review this remediation contract before any implementation, "
                "preflight, replay, fixed-DP candidate generation, or training"
            ),
        },
    }


def _attribution_summary(attribution: dict[str, Any]) -> dict[str, Any]:
    final_decision = _dict(attribution.get("final_decision"))
    attribution_body = _dict(attribution.get("attribution"))
    evidence = _dict(attribution.get("overlap_evidence"))
    return {
        "status": final_decision.get("status"),
        "passed": final_decision.get("passed"),
        "failed_checks": final_decision.get("failed_checks"),
        "authorized_next_work": final_decision.get("authorized_next_work"),
        "failure_class": attribution_body.get("failure_class"),
        "primary_cause": attribution_body.get("primary_cause"),
        "current_evaluation_is_not_independent_holdout": attribution_body.get(
            "current_evaluation_is_not_independent_holdout"
        ),
        "raw_prior_logs_missing_but_recovered_registry_authoritative": attribution_body.get(
            "raw_prior_logs_missing_but_recovered_registry_authoritative"
        ),
        "training_summary_only_overlap_is_insufficient_for_this_case": attribution_body.get(
            "training_summary_only_overlap_is_insufficient_for_this_case"
        ),
        "records_total": evidence.get("records_total"),
        "training_manifest_log_count": evidence.get("training_manifest_log_count"),
        "training_missing_log_count": evidence.get("training_missing_log_count"),
        "candidate_hash_intersection_count": evidence.get("candidate_hash_intersection_count"),
        "path_signature_intersection_count": evidence.get("path_signature_intersection_count"),
        "record_identity_intersection_count": evidence.get("record_identity_intersection_count"),
        "candidate_tensor_eval_hashes_in_previous_rate": evidence.get(
            "candidate_tensor_eval_hashes_in_previous_rate"
        ),
    }


def _checks(
    *,
    nonoverlap_failure_attribution_json: Path,
    v13_audit_md: Path,
    audit_text: str,
    attribution: dict[str, Any],
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    final_decision = _dict(attribution.get("final_decision"))
    attribution_body = _dict(attribution.get("attribution"))
    evidence = _dict(attribution.get("overlap_evidence"))
    latest_target = _latest_value(audit_text, "next_work_target")
    latest_status = _latest_value(audit_text, "current_v13_status")
    return [
        _check("nonoverlap_failure_attribution_json_exists", nonoverlap_failure_attribution_json.is_file(), str(nonoverlap_failure_attribution_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_by_latest_audit_target", latest_target == authorized_current_work, latest_target, authorized_current_work),
        _check("latest_audit_status_is_attributed", latest_status == "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_attributed", latest_status, "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_attributed"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        _check("attribution_passed", final_decision.get("passed") is True, final_decision.get("passed"), True),
        _check("attribution_status_expected", final_decision.get("status") == ATTRIBUTED_STATUS, final_decision.get("status"), ATTRIBUTED_STATUS),
        _check("attribution_authorized_this_plan", final_decision.get("authorized_next_work") == authorized_current_work, final_decision.get("authorized_next_work"), authorized_current_work),
        _check("attribution_not_independent_holdout", attribution_body.get("current_evaluation_is_not_independent_holdout") is True, attribution_body.get("current_evaluation_is_not_independent_holdout"), True),
        _check("attribution_recovered_registry_authoritative", attribution_body.get("raw_prior_logs_missing_but_recovered_registry_authoritative") is True, attribution_body.get("raw_prior_logs_missing_but_recovered_registry_authoritative"), True),
        _check("training_summary_only_overlap_insufficient", attribution_body.get("training_summary_only_overlap_is_insufficient_for_this_case") is True, attribution_body.get("training_summary_only_overlap_is_insufficient_for_this_case"), True),
        _check("record_identity_intersection_full", evidence.get("record_identity_intersection_count") == evidence.get("records_total") == EXPECTED_RECORD_COUNT, evidence.get("record_identity_intersection_count"), EXPECTED_RECORD_COUNT),
        _check("candidate_tensor_eval_hashes_in_previous_rate_one", evidence.get("candidate_tensor_eval_hashes_in_previous_rate") == 1.0, evidence.get("candidate_tensor_eval_hashes_in_previous_rate"), 1.0),
        _check("training_missing_logs_present", int(evidence.get("training_missing_log_count") or 0) > 0, evidence.get("training_missing_log_count"), ">0"),
        _check("plan_requires_recovered_registry", plan["required_static_contracts"]["recovered_missing_prior_registry_must_be_loaded"], True, True),
        _check("plan_requires_candidate_zero_overlap", plan["required_static_contracts"]["candidate_tensor_eval_hashes_in_previous_must_be_zero"], True, True),
        _check("plan_requires_path_zero_overlap", plan["required_static_contracts"]["path_signature_intersection_must_be_zero"], True, True),
        _check("plan_requires_record_identity_zero_overlap", plan["required_static_contracts"]["record_identity_intersection_must_be_zero"], True, True),
        _check("plan_blocks_training_preflight", plan["blocked_by_this_plan"]["training_preflight"], True, True),
        _check("plan_blocks_replay_execution", plan["blocked_by_this_plan"]["replay_execution"], True, True),
        _check("plan_blocks_fixed_dp_candidate_generation", plan["blocked_by_this_plan"]["fixed_dp_candidate_generation_execution"], True, True),
        _check("plan_blocks_dp_modification", plan["blocked_by_this_plan"]["dp_modification"], True, True),
        _check("plan_blocks_safety_claims", plan["blocked_by_this_plan"]["safety_benefit_claim"], True, True),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["attribution_summary"]
    plan = report["remediation_plan"]
    lines = [
        "# V13 Non-Overlap Failure Remediation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source failure class: `{summary['failure_class']}`",
        f"- Record identity intersection: `{summary['record_identity_intersection_count']}`",
        f"- Candidate overlap rate: `{summary['candidate_tensor_eval_hashes_in_previous_rate']}`",
        "",
        "## Objective",
        "",
        plan["objective"],
        "",
        "## Required Static Contracts",
        "",
    ]
    for key, value in plan["required_static_contracts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Boundary", ""])
    lines.append(
        "This is plan-only. It does not run replay, generate candidates, train "
        "CAMP, modify DP, promote selector/atom artifacts, deploy, or make "
        "safety/CAMP-over-DP claims."
    )
    lines.append("")
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _latest_value(text: str, key: str) -> str | None:
    values = re.findall(rf"^{re.escape(key)}=(.+)$", text, re.M)
    return values[-1] if values else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
