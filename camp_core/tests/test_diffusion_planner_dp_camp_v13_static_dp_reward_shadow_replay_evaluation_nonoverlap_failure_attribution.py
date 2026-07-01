from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.diagnose_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_attribution import (
    ATTRIBUTED_STATUS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    build_report,
    main,
)


CAMP_HEAD = "3ef8ea04d5730c61e8ca9cf47e7a166fba7dd66e"


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _artifact(tmp_path: Path) -> tuple[Path, Path]:
    artifact = tmp_path / "result_review_rejected_overlap"
    artifact.mkdir()
    failed_checks = [
        "candidate_tensor_hash_registry_intersection_zero",
        "path_signature_registry_intersection_zero",
        "record_identity_hash_registry_intersection_zero",
    ]
    final_decision = {
        "status": "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_rejected",
        "passed": False,
        "failed_checks": failed_checks,
        "static_dp_reward_training_preflight_authorized_next": False,
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    _write_json(
        artifact / "result_review_summary.json",
        {
            "status": final_decision["status"],
            "passed": False,
            "failed_checks": failed_checks,
            "selection_log_count": 32,
            "records_total": 3200,
            "clean_contract_passed": True,
            "formal_seed_records": 0,
        },
    )
    _write_json(
        artifact / "registry_manifest.json",
        {
            "training_manifest_log_count": 416,
            "training_existing_log_count": 320,
            "training_missing_log_count": 96,
            "training_candidate_hash_count": 35200,
            "evaluation_candidate_hash_count": 3200,
            "recovered_candidate_hash_count": 3200,
            "recovered_path_signature_count": 3200,
            "recovered_record_identity_count": 3200,
            "candidate_hash_intersection_count": 2140,
            "path_signature_intersection_count": 32,
            "record_identity_intersection_count": 3200,
            "candidate_tensor_eval_hashes_in_previous_count": 3200,
            "candidate_tensor_eval_hashes_in_previous_rate": 1.0,
        },
    )
    _write_json(
        artifact / "overlap_summary.json",
        {
            "candidate_hash_intersection_count": 2140,
            "path_signature_intersection_count": 32,
            "record_identity_intersection_count": 3200,
        },
    )
    _write_json(
        artifact / "result_review.json",
        {
            "final_decision": final_decision,
            "candidate_tensor_overlap": {
                "eval_hashes_in_previous_count": 0,
                "eval_hashes_in_previous_rate": 0.0,
            },
        },
    )
    _write_text(artifact / "registry_builder.exit", "0\n")
    _write_text(artifact / "result_review.exit", "1\n")
    audit_md = _write_text(
        tmp_path / "audit.md",
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_result_review_rejected_overlap",
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "",
            ]
        ),
    )
    return artifact, audit_md


def test_nonoverlap_failure_attribution_accepts_recovered_registry_overlap(tmp_path: Path) -> None:
    artifact, audit_md = _artifact(tmp_path)

    report = build_report(
        result_review_artifact_dir=artifact,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == ATTRIBUTED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["training_executed"] is False
    assert report["final_decision"]["candidate_generation_executed"] is False
    assert report["overlap_evidence"]["record_identity_intersection_count"] == 3200
    assert report["overlap_evidence"]["candidate_tensor_eval_hashes_in_previous_rate"] == 1.0
    assert (
        report["attribution"]["failure_class"]
        == "evaluation_set_overlaps_training_manifest_recovered_prior_source"
    )


def test_nonoverlap_failure_attribution_rejects_missing_recovered_overlap(tmp_path: Path) -> None:
    artifact, audit_md = _artifact(tmp_path)
    registry_path = artifact / "registry_manifest.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["training_missing_log_count"] = 0
    registry["record_identity_intersection_count"] = 0
    registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")

    report = build_report(
        result_review_artifact_dir=artifact,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["passed"] is False
    assert "training_manifest_has_missing_logs_for_recovered_registry_case" in report[
        "final_decision"
    ]["failed_checks"]
    assert "record_identity_intersection_full" in report["final_decision"]["failed_checks"]


def test_nonoverlap_failure_attribution_main_writes_outputs(tmp_path: Path) -> None:
    artifact, audit_md = _artifact(tmp_path)
    output_json = tmp_path / "attribution.json"
    output_md = tmp_path / "attribution.md"

    exit_code = main(
        [
            "--result_review_artifact_dir",
            str(artifact),
            "--v13_audit_md",
            str(audit_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == ATTRIBUTED_STATUS
    assert ATTRIBUTED_STATUS in output_md.read_text(encoding="utf-8")
