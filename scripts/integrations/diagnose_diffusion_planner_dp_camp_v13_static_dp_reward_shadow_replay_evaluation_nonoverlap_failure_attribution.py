#!/usr/bin/env python3
"""Attribute v13 static DP-reward shadow replay non-overlap failures.

This tool is read-only. It consumes an existing result-review artifact whose
registry evidence rejected a fixed-DP shadow replay evaluation because the
evaluation set overlaps the training manifest. It does not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_attribution_v1"
)
ATTRIBUTED_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_attributed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "attribution_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_plan_only"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_"
    "rejected"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
REQUIRED_FAILED_CHECKS = (
    "candidate_tensor_hash_registry_intersection_zero",
    "path_signature_registry_intersection_zero",
    "record_identity_hash_registry_intersection_zero",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only attribution for a v13 static DP-reward shadow replay "
            "evaluation result-review non-overlap rejection."
        )
    )
    parser.add_argument("--result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        result_review_artifact_dir=args.result_review_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        expected_records=args.expected_records,
        expected_selection_log_count=args.expected_selection_log_count,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    result_review_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_records: int = 3200,
    expected_selection_log_count: int = 32,
) -> dict[str, Any]:
    result_review_artifact_dir = result_review_artifact_dir.resolve()
    v13_audit_md = v13_audit_md.resolve()
    summary = _load_json(result_review_artifact_dir / "result_review_summary.json")
    registry = _load_json(result_review_artifact_dir / "registry_manifest.json")
    overlap = _load_json(result_review_artifact_dir / "overlap_summary.json")
    result_review = _load_json(result_review_artifact_dir / "result_review.json")
    final_review = _dict(result_review.get("final_decision"))
    audit_text = v13_audit_md.read_text(encoding="utf-8")

    checks = _checks(
        result_review_artifact_dir=result_review_artifact_dir,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        summary=summary,
        registry=registry,
        overlap=overlap,
        final_review=final_review,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        expected_records=expected_records,
        expected_selection_log_count=expected_selection_log_count,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    attribution = {
        "failure_class": (
            "evaluation_set_overlaps_training_manifest_recovered_prior_source"
        ),
        "primary_cause": (
            "the current fixed-DP shadow replay evaluation reuses candidate "
            "tensor hashes, path signatures, and record identities from a prior "
            "source represented in the 76c2 training manifest"
        ),
        "raw_prior_logs_missing_but_recovered_registry_authoritative": True,
        "training_summary_only_overlap_is_insufficient_for_this_case": True,
        "current_evaluation_is_not_independent_holdout": True,
        "static_dp_reward_training_preflight_blocked": True,
        "required_remediation": (
            "plan a fresh fixed-DP evaluation split with zero candidate, path, "
            "and record-identity intersection against the full 76c2 training "
            "manifest, including recovered missing-prior registry evidence"
        ),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "inputs": {
            "result_review_artifact_dir": str(result_review_artifact_dir),
            "v13_audit_md": str(v13_audit_md),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "source_result_review": {
            "status": summary.get("status"),
            "passed": summary.get("passed"),
            "failed_checks": summary.get("failed_checks"),
            "final_decision_status": final_review.get("status"),
            "final_decision_passed": final_review.get("passed"),
            "final_decision_failed_checks": final_review.get("failed_checks"),
        },
        "overlap_evidence": {
            "selection_log_count": summary.get("selection_log_count"),
            "records_total": summary.get("records_total"),
            "clean_contract_passed": summary.get("clean_contract_passed"),
            "formal_seed_records": summary.get("formal_seed_records"),
            "training_manifest_log_count": registry.get("training_manifest_log_count"),
            "training_existing_log_count": registry.get("training_existing_log_count"),
            "training_missing_log_count": registry.get("training_missing_log_count"),
            "training_candidate_hash_count": registry.get("training_candidate_hash_count"),
            "evaluation_candidate_hash_count": registry.get("evaluation_candidate_hash_count"),
            "recovered_candidate_hash_count": registry.get("recovered_candidate_hash_count"),
            "recovered_path_signature_count": registry.get("recovered_path_signature_count"),
            "recovered_record_identity_count": registry.get("recovered_record_identity_count"),
            "candidate_hash_intersection_count": registry.get("candidate_hash_intersection_count"),
            "path_signature_intersection_count": registry.get("path_signature_intersection_count"),
            "record_identity_intersection_count": registry.get("record_identity_intersection_count"),
            "candidate_tensor_eval_hashes_in_previous_count": registry.get(
                "candidate_tensor_eval_hashes_in_previous_count"
            ),
            "candidate_tensor_eval_hashes_in_previous_rate": registry.get(
                "candidate_tensor_eval_hashes_in_previous_rate"
            ),
            "training_summary_only_candidate_tensor_overlap_count": _dict(
                result_review.get("candidate_tensor_overlap")
            ).get("eval_hashes_in_previous_count"),
            "overlap_summary": overlap,
        },
        "attribution": attribution,
        "review_checks": checks,
        "final_decision": {
            "status": ATTRIBUTED_STATUS if passed else "nonoverlap_failure_attribution_rejected",
            "passed": passed,
            "failed_checks": failed,
            "authorized_next_work": authorized_next_work if passed else None,
            "static_dp_reward_training_preflight_authorized_next": False,
            "static_dp_reward_training_execution_authorized_next": False,
            "training_executed": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
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
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    final_decision = report["final_decision"]
    attribution = report["attribution"]
    evidence = report["overlap_evidence"]
    lines = [
        "# V13 Non-Overlap Failure Attribution",
        "",
        f"status={final_decision['status']}",
        f"passed={final_decision['passed']}",
        f"failed_checks={final_decision['failed_checks']}",
        f"failure_class={attribution['failure_class']}",
        f"primary_cause={attribution['primary_cause']}",
        f"records_total={evidence['records_total']}",
        (
            "candidate_tensor_eval_hashes_in_previous_rate="
            f"{evidence['candidate_tensor_eval_hashes_in_previous_rate']}"
        ),
        f"record_identity_intersection_count={evidence['record_identity_intersection_count']}",
        f"authorized_next_work={final_decision['authorized_next_work']}",
        "",
    ]
    return "\n".join(lines)


def _checks(
    *,
    result_review_artifact_dir: Path,
    v13_audit_md: Path,
    audit_text: str,
    summary: dict[str, Any],
    registry: dict[str, Any],
    overlap: dict[str, Any],
    final_review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    expected_records: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    latest_target = _latest_value(audit_text, "next_work_target")
    latest_status = _latest_value(audit_text, "current_v13_status")
    required_files = [
        "result_review_summary.json",
        "registry_manifest.json",
        "overlap_summary.json",
        "result_review.json",
        "result_review.exit",
        "registry_builder.exit",
    ]
    checks = [
        _check("result_review_artifact_dir_exists", result_review_artifact_dir.is_dir()),
        _check("v13_audit_md_exists", v13_audit_md.is_file()),
        _check(
            "required_artifact_files_exist",
            all((result_review_artifact_dir / name).is_file() for name in required_files),
        ),
        _check("authorized_current_work_is_latest_target", latest_target == authorized_current_work),
        _check(
            "latest_status_is_result_review_rejection",
            latest_status
            == (
                "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
                "shadow_replay_evaluation_result_review_rejected_overlap"
            ),
        ),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
        _check("registry_builder_exit_zero", _read_exit(result_review_artifact_dir / "registry_builder.exit") == 0),
        _check("result_review_exit_one", _read_exit(result_review_artifact_dir / "result_review.exit") == 1),
        _check("result_review_status_rejected", summary.get("status") == REJECT_STATUS),
        _check("result_review_passed_false", summary.get("passed") is False),
        _check(
            "final_review_status_rejected",
            final_review.get("status") == REJECT_STATUS,
        ),
        _check("final_review_passed_false", final_review.get("passed") is False),
        _check(
            "failed_checks_match_required_overlap_checks",
            sorted(summary.get("failed_checks") or []) == sorted(REQUIRED_FAILED_CHECKS),
        ),
        _check(
            "selection_log_count_expected",
            summary.get("selection_log_count") == expected_selection_log_count,
        ),
        _check("records_total_expected", summary.get("records_total") == expected_records),
        _check("clean_contract_passed", summary.get("clean_contract_passed") is True),
        _check("formal_seed_records_zero", summary.get("formal_seed_records") == 0),
        _check(
            "training_manifest_has_missing_logs_for_recovered_registry_case",
            int(registry.get("training_missing_log_count") or 0) > 0,
        ),
        _check(
            "recovered_candidate_hashes_present",
            int(registry.get("recovered_candidate_hash_count") or 0) > 0,
        ),
        _check(
            "candidate_hash_intersection_nonzero",
            int(registry.get("candidate_hash_intersection_count") or 0) > 0,
        ),
        _check(
            "path_signature_intersection_nonzero",
            int(registry.get("path_signature_intersection_count") or 0) > 0,
        ),
        _check(
            "record_identity_intersection_full",
            registry.get("record_identity_intersection_count") == expected_records,
        ),
        _check(
            "candidate_tensor_eval_hashes_in_previous_full",
            registry.get("candidate_tensor_eval_hashes_in_previous_count") == expected_records,
        ),
        _check(
            "candidate_tensor_eval_hashes_in_previous_rate_one",
            registry.get("candidate_tensor_eval_hashes_in_previous_rate") == 1.0,
        ),
        _check(
            "overlap_summary_record_identity_matches_registry",
            overlap.get("record_identity_intersection_count")
            == registry.get("record_identity_intersection_count"),
        ),
        _check("review_did_not_authorize_training_preflight", final_review.get("static_dp_reward_training_preflight_authorized_next") is False),
        _check("review_did_not_execute_training", final_review.get("training_executed") is False),
        _check("review_did_not_execute_replay", final_review.get("replay_executed") is False),
        _check("review_did_not_execute_candidate_generation", final_review.get("candidate_generation_executed") is False),
        _check("review_did_not_authorize_dp_modification", final_review.get("dp_modification_authorized") is False),
        _check("review_did_not_authorize_selector_promotion", final_review.get("selector_promotion_authorized") is False),
        _check("review_did_not_authorize_atom_promotion", final_review.get("atom_promotion_authorized") is False),
        _check("review_did_not_authorize_deployment", final_review.get("deployment_authorized") is False),
        _check("review_did_not_authorize_safety_claim", final_review.get("safety_benefit_claim_authorized") is False),
        _check("review_did_not_authorize_camp_over_dp_claim", final_review.get("camp_over_dp_top1_claim_authorized") is False),
    ]
    return checks


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return data


def _latest_value(text: str, key: str) -> str | None:
    values = re.findall(rf"^{re.escape(key)}=(.+)$", text, re.M)
    return values[-1] if values else None


def _read_exit(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
