#!/usr/bin/env python3
"""Decide the v13 holdout consumption policy after result readiness.

This tool is read-only. It consumes the fixed result-readiness artifact and
records whether the clean evaluation records remain a holdout/evidence split or
may be consumed by a later training gate. It does not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "dp_camp_v13_split_policy_holdout_consumption_decision_v1"
GATE_NAME = "dp_camp_v13_split_policy_holdout_consumption_decision_gate"
PASS_STATUS = "dp_camp_v13_split_policy_holdout_consumption_decision_passed"
REJECT_STATUS = "dp_camp_v13_split_policy_holdout_consumption_decision_rejected"
DEFAULT_DECISION = "preserve_current_holdout"
DEFAULT_NEXT_WORK_TARGET = (
    "dp_camp_v13_fresh_nonoverlap_dp_native_development_collection_preflight_only"
)
RESULT_REVIEW_STATUS = (
    "result_readiness_rejected_nonoverlap_remediation_static_dp_reward_training_"
    "artifact_shadow_replay_evaluation_result_review_passed"
)
CURRENT_SOURCE_RESULT_REVIEW_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_result_review_passed"
)
RESULT_REVIEW_STATUSES = {
    RESULT_REVIEW_STATUS,
    CURRENT_SOURCE_RESULT_REVIEW_STATUS,
}
RESULT_READINESS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_"
    "ready_for_training_preflight"
)
APPROVED_DECISIONS = {
    "preserve_current_holdout",
    "split_current_holdout",
    "consume_current_holdout_and_collect_new_holdout",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only v13 split-policy decision after result readiness."
    )
    parser.add_argument("--result_readiness_json", type=Path, required=True)
    parser.add_argument("--registry_manifest_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--decision", choices=sorted(APPROVED_DECISIONS), default=DEFAULT_DECISION)
    parser.add_argument("--next_work_target", default=DEFAULT_NEXT_WORK_TARGET)
    parser.add_argument("--expected_training_log_count", type=int, default=224)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        result_readiness_json=args.result_readiness_json,
        registry_manifest_json=args.registry_manifest_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        decision=args.decision,
        next_work_target=args.next_work_target,
        expected_training_log_count=args.expected_training_log_count,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    result_readiness_json: Path,
    registry_manifest_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    decision: str = DEFAULT_DECISION,
    next_work_target: str = DEFAULT_NEXT_WORK_TARGET,
    expected_training_log_count: int = 224,
) -> dict[str, Any]:
    result_readiness_json = result_readiness_json.resolve()
    registry_manifest_json = registry_manifest_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    readiness = _load_json_dict(result_readiness_json)
    registry_manifest = _load_json_dict(registry_manifest_json)
    audit_text = _read_text(v13_audit_md)
    latest = {
        "current_v13_status": _latest_audit_value(audit_text, "current_v13_status"),
        "next_work_target": _latest_audit_value(audit_text, "next_work_target"),
        "result_review_passed": _latest_audit_value(
            audit_text,
            "static_dp_reward_training_artifact_shadow_replay_evaluation_result_review_passed",
        ),
        "training_preflight_clean_data_available": _latest_audit_value(
            audit_text,
            "static_dp_reward_training_artifact_shadow_replay_evaluation_result_review_training_preflight_clean_data_available",
        ),
        "holdout_consumption_requires_split_policy_decision": _latest_audit_value(
            audit_text,
            "static_dp_reward_training_artifact_shadow_replay_evaluation_holdout_consumption_requires_split_policy_decision",
        ),
        "training_execution_authorized": _latest_audit_value(
            audit_text,
            "training_execution_authorized_by_current_boundary",
        ),
        "replay_execution_authorized": _latest_audit_value(
            audit_text,
            "replay_execution_authorized_by_current_boundary",
        ),
        "fixed_dp_candidate_generation_authorized": _latest_audit_value(
            audit_text,
            "fixed_dp_candidate_generation_authorized_by_current_boundary",
        ),
    }
    evidence = _evidence(readiness, registry_manifest)
    checks = _checks(
        result_readiness_json=result_readiness_json,
        registry_manifest_json=registry_manifest_json,
        v13_audit_md=v13_audit_md,
        readiness=readiness,
        registry_manifest=registry_manifest,
        latest=latest,
        evidence=evidence,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        decision=decision,
        expected_training_log_count=expected_training_log_count,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    policy = _policy_decision(
        decision=decision,
        next_work_target=next_work_target,
        evidence=evidence,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "gate_name": GATE_NAME,
        "analysis": {
            "read_only": True,
            "fixed_artifact_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "candidate_generation_by_camp_executed": False,
            "training_executed": False,
            "dp_modified": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "method_boundary": "CAMP reranking/selection only over fixed DP candidate tensors.",
        },
        "source_paths": {
            "result_readiness_json": str(result_readiness_json),
            "registry_manifest_json": str(registry_manifest_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "result_readiness_json_sha256": _sha256(result_readiness_json),
            "registry_manifest_json_sha256": _sha256(registry_manifest_json),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "audit_eof": latest,
        "source_artifact_registry": _source_artifact_registry(readiness, registry_manifest),
        "input_evidence": evidence,
        "policy_decision": policy,
        "checks": checks,
        "final_decision": {
            "passed": passed,
            "status": PASS_STATUS if passed else REJECT_STATUS,
            "failed_checks": failed,
            "decision": decision,
            "authorized_next_work": policy["next_work_target"] if passed else "read_only_insufficiency_attribution",
            "current_holdout_preserved": policy["current_holdout_preserved"] if passed else False,
            "current_holdout_consumed": policy["current_holdout_consumed"] if passed else False,
            "training_from_current_holdout_authorized": (
                policy["training_from_current_holdout_authorized"] if passed else False
            ),
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "static_dp_reward_training_execution_authorized_next": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _checks(
    *,
    result_readiness_json: Path,
    registry_manifest_json: Path,
    v13_audit_md: Path,
    readiness: dict[str, Any],
    registry_manifest: dict[str, Any],
    latest: dict[str, Any],
    evidence: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    decision: str,
    expected_training_log_count: int,
) -> list[dict[str, Any]]:
    final_decision = _dict(readiness.get("final_decision"))
    heads = _dict(readiness.get("heads"))
    return [
        _check("result_readiness_json_exists", result_readiness_json.is_file(), str(result_readiness_json), "file exists"),
        _check("registry_manifest_json_exists", registry_manifest_json.is_file(), str(registry_manifest_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("result_artifact_dp_head_fixed", heads.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("result_artifact_required_dp_head_fixed", heads.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("result_readiness_passed", final_decision.get("passed"), True),
        _expect("result_readiness_status", final_decision.get("status"), RESULT_READINESS_STATUS),
        _check(
            "audit_latest_status",
            latest["current_v13_status"] in RESULT_REVIEW_STATUSES,
            latest["current_v13_status"],
            sorted(RESULT_REVIEW_STATUSES),
        ),
        _check(
            "audit_latest_next_work_authorizes_split_policy",
            str(latest["next_work_target"]).startswith("none")
            or latest["next_work_target"] == GATE_NAME,
            latest["next_work_target"],
            f"none* or {GATE_NAME}",
        ),
        _expect("audit_result_review_passed", latest["result_review_passed"], "True"),
        _expect("audit_training_preflight_clean_data_available", latest["training_preflight_clean_data_available"], "True"),
        _expect("audit_holdout_consumption_requires_split_policy", latest["holdout_consumption_requires_split_policy_decision"], "True"),
        _expect("audit_training_execution_not_authorized", latest["training_execution_authorized"], "False"),
        _expect("audit_replay_execution_not_authorized", latest["replay_execution_authorized"], "False"),
        _expect("audit_fixed_dp_candidate_generation_not_authorized", latest["fixed_dp_candidate_generation_authorized"], "False"),
        _expect("clean_contract_passed", evidence["clean_contract_passed"], True),
        _expect("future_training_input_contract_satisfied", evidence["future_training_input_contract_satisfied"], True),
        _expect("record_count", evidence["records_total"], 3200),
        _expect("selection_log_count", evidence["selection_log_count"], 32),
        _check("usable_feasible_records_present", evidence["usable_feasible_records"] > 0, evidence["usable_feasible_records"], "> 0"),
        _expect("formal_seed_records_zero", evidence["formal_seed_records"], 0),
        _expect("reference_blend_records_zero", evidence["reference_blend_records"], 0),
        _expect("guidance_records_zero", evidence["guidance_records"], 0),
        _expect("postselection_records_zero", evidence["postselection_records"], 0),
        _expect("closed_loop_outcome_records_zero", evidence["closed_loop_outcome_records"], 0),
        _expect("camp_candidate_generation_effect_records_zero", evidence["camp_candidate_generation_effect_records"], 0),
        _expect("dp_modification_records_zero", evidence["dp_modification_records"], 0),
        _expect("candidate_hash_intersection_zero", evidence["candidate_hash_intersection_count"], 0),
        _expect("path_signature_intersection_zero", evidence["path_signature_intersection_count"], 0),
        _expect("record_identity_intersection_zero", evidence["record_identity_intersection_count"], 0),
        _expect("candidate_tensor_eval_hashes_in_previous_zero", evidence["candidate_tensor_eval_hashes_in_previous_count"], 0),
        _check("decision_is_approved", decision in APPROVED_DECISIONS, decision, sorted(APPROVED_DECISIONS)),
        _expect("default_decision_preserves_holdout", decision, DEFAULT_DECISION),
        _expect(
            "registry_training_log_count",
            evidence["training_log_count"],
            expected_training_log_count,
        ),
        _expect("registry_evaluation_log_count", evidence["evaluation_log_count"], 32),
        _check(
            "registry_training_candidate_hash_count",
            evidence["training_candidate_hash_count"] > 0,
            evidence["training_candidate_hash_count"],
            "> 0",
        ),
        _expect("registry_evaluation_candidate_hash_count", evidence["evaluation_candidate_hash_count"], 3200),
        _expect("registry_evaluation_record_identity_count", evidence["evaluation_record_identity_count"], 3200),
    ]


def _evidence(readiness: dict[str, Any], registry_manifest: dict[str, Any]) -> dict[str, Any]:
    clean = _dict(readiness.get("clean_contract"))
    training = _dict(readiness.get("training_readiness"))
    overlap = _dict(readiness.get("candidate_tensor_overlap"))
    return {
        "clean_contract_passed": bool(clean.get("passed")),
        "future_training_input_contract_satisfied": bool(clean.get("future_training_input_contract_satisfied")),
        "clean_contract_records": int(clean.get("records", 0)),
        "selection_log_count": int(training.get("selection_log_count", 0)),
        "records_total": int(training.get("records_total", 0)),
        "usable_feasible_records": int(training.get("usable_feasible_records", 0)),
        "multi_feasible_records": int(training.get("multi_feasible_records", 0)),
        "all_infeasible_records": int(training.get("all_infeasible_records", 0)),
        "route_records": _dict(training.get("route_records")),
        "route_tl_records": _dict(training.get("route_tl_records")),
        "seed_records": _dict(training.get("seed_records")),
        "formal_seed_records": int(training.get("formal_seed_records", 0)),
        "reference_blend_records": int(training.get("reference_blend_enabled_records", 0)),
        "guidance_records": int(training.get("guidance_enabled_records", 0)),
        "postselection_records": int(training.get("postselection_records", 0)),
        "closed_loop_outcome_records": int(training.get("closed_loop_outcome_records", 0)),
        "camp_candidate_generation_effect_records": int(training.get("camp_candidate_generation_effect_records", 0)),
        "dp_modification_records": int(training.get("dp_modification_records", 0)),
        "shadow_differs_from_dp_top1_records": int(training.get("shadow_differs_from_dp_top1_records", 0)),
        "candidate_tensor_eval_hashes_in_previous_count": int(overlap.get("eval_hashes_in_previous_count", 0)),
        "candidate_tensor_eval_hashes_in_previous_rate": float(overlap.get("eval_hashes_in_previous_rate", 0.0)),
        "candidate_hash_intersection_count": int(registry_manifest.get("candidate_hash_intersection_count", 0)),
        "path_signature_intersection_count": int(registry_manifest.get("path_signature_intersection_count", 0)),
        "record_identity_intersection_count": int(registry_manifest.get("record_identity_intersection_count", 0)),
        "training_log_count": _first_int(registry_manifest, "training_log_count", "previous_training_log_count"),
        "evaluation_log_count": _first_int(registry_manifest, "evaluation_log_count", "rejected_eval_log_count"),
        "training_candidate_hash_count": _first_int(
            registry_manifest,
            "training_candidate_hash_count",
            "candidate_hash_training_value_count",
            "candidate_hash_training_unique_value_count",
        ),
        "evaluation_candidate_hash_count": _first_int(
            registry_manifest,
            "evaluation_candidate_hash_count",
            "candidate_hash_evaluation_value_count",
            "candidate_hash_evaluation_unique_value_count",
        ),
        "evaluation_record_identity_count": _first_int(
            registry_manifest,
            "evaluation_record_identity_count",
            "evaluation_record_count",
        ),
    }


def _policy_decision(
    *,
    decision: str,
    next_work_target: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    preserve = decision == DEFAULT_DECISION
    return {
        "decision": decision,
        "current_holdout_name": "v13_result_readiness_rejected_nonoverlap_shadow_eval_holdout_3200",
        "current_holdout_record_count": evidence["records_total"],
        "current_holdout_selection_log_count": evidence["selection_log_count"],
        "current_holdout_usable_feasible_records": evidence["usable_feasible_records"],
        "current_holdout_preserved": preserve,
        "current_holdout_consumed": not preserve,
        "training_from_current_holdout_authorized": not preserve,
        "requires_new_holdout_before_claims": True,
        "next_work_target": next_work_target,
        "reason": (
            "Preserve the clean non-overlap evaluation records as evidence and "
            "continue with a fresh DP-native development collection preflight."
            if preserve
            else "Non-default holdout consumption policy was requested."
        ),
    }


def _source_artifact_registry(
    readiness: dict[str, Any],
    registry_manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "result_readiness_source_paths": _dict(readiness.get("source_paths")),
        "result_readiness_source_hashes": _dict(readiness.get("source_hashes")),
        "registry_manifest": registry_manifest,
    }


def render_markdown(report: dict[str, Any]) -> str:
    evidence = report["input_evidence"]
    policy = report["policy_decision"]
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V13 Split Policy Holdout Consumption Decision",
            "",
            f"- status: `{decision['status']}`",
            f"- passed: `{decision['passed']}`",
            f"- policy decision: `{policy['decision']}`",
            f"- current holdout preserved: `{policy['current_holdout_preserved']}`",
            f"- current holdout consumed: `{policy['current_holdout_consumed']}`",
            f"- records: `{evidence['records_total']}`",
            f"- usable feasible records: `{evidence['usable_feasible_records']}`",
            f"- candidate hash intersection: `{evidence['candidate_hash_intersection_count']}`",
            f"- path signature intersection: `{evidence['path_signature_intersection_count']}`",
            f"- record identity intersection: `{evidence['record_identity_intersection_count']}`",
            f"- next work target: `{policy['next_work_target']}`",
            "",
            "This gate is read-only. It does not train CAMP, run replay, generate "
            "candidates, modify DP, promote selectors/atoms, deploy, or authorize "
            "safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _latest_audit_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_int(mapping: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return int(value)
    return 0


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
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
