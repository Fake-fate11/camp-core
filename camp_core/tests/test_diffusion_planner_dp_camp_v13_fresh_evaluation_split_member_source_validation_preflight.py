from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.preflight_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_MISSING_INPUT_NEXT_WORK,
    AUTHORIZED_PASS_NEXT_WORK,
    FIXED_DP_HEAD,
    MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION,
    NONOVERLAP_REPORT_SCHEMA_VERSION,
    PASS_STATUS,
    PREFLIGHT_INPUTS_SCHEMA_VERSION,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "1bbb2deb8a8c1dad3d48af1bbf18b20a149645f7"
POST_REVIEW_SCHEMA = (
    "dp_camp_v13_fresh_evaluation_split_member_source_builder_"
    "post_implementation_static_contract_review_v1"
)
POST_REVIEW_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_builder_"
    "post_implementation_static_contract_review_complete"
)
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_builder_post_implementation_static_contract_review_complete"
)
MATERIALIZATION_COMPLETE_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_materialization_complete"
)
MATERIALIZER_SCHEMA = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_v1"
)
MATERIALIZER_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_complete"
)
ZERO_COUNTS = {
    "candidate_tensor_hash_intersection_count": 0,
    "path_signature_intersection_count": 0,
    "record_identity_intersection_count": 0,
    "split_manifest_root_intersection_count": 0,
}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _post_review(path: Path, *, mutation: Any | None = None) -> Path:
    flags = {
        "fresh_member_selection_execution_authorized_next": False,
        "fresh_evaluation_split_evaluation_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "real_fresh_member_selection_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }
    payload = {
        "schema_version": POST_REVIEW_SCHEMA,
        "final_decision": {
            "status": POST_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "validation_preflight_authorized_next": True,
            **flags,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _materializer_report(path: Path, *, mutation: Any | None = None) -> Path:
    flags = {
        "fresh_member_selection_execution_authorized_next": False,
        "fresh_evaluation_split_evaluation_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_executed": False,
        "trajectory_generation_by_camp_executed": False,
        "trajectory_modification_by_camp_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }
    payload = {
        "schema_version": MATERIALIZER_SCHEMA,
        "final_decision": {
            "status": MATERIALIZER_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "validation_preflight_authorized_next": True,
            "materialization_complete": True,
            "member_source_manifest_written": True,
            **flags,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _boundary(*, mutation: Any | None = None) -> dict[str, Any]:
    payload = {
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
        "nonnegative_simplex_weights_only": True,
        "master_problem_remains_convex": True,
        "default_off_shadow_selector": True,
        "executed_trajectory_remains_dp_top1": True,
        "fixed_dp_candidate_generation": False,
        "candidate_generation_by_camp": False,
        "trajectory_generation_by_camp": False,
        "trajectory_modification_by_camp": False,
        "reference_blend": False,
        "guidance": False,
        "postprocess_or_postselection": False,
        "closed_loop_outcome_input": False,
        "replay": False,
        "training": False,
        "dp_modification": False,
        "promotion": False,
        "deployment": False,
        "safety_or_camp_over_dp_claim": False,
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _member_source_artifacts(root: Path, *, mutation: Any | None = None) -> dict[str, Path]:
    boundary = _boundary()
    manifest = {
        "schema_version": MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION,
        "selected_member_count": 1,
        "selected_members": [
            {
                "member_id": "fresh-a",
                "candidate_tensor_hashes": ["fresh-cand"],
                "path_signatures": ["fresh-path"],
                "record_identity_hashes": ["fresh-record"],
                "split_manifest_roots": ["fresh-root"],
            }
        ],
        "zero_intersection_counts": dict(ZERO_COUNTS),
        "math_and_runtime_boundary": boundary,
    }
    nonoverlap = {
        "schema_version": NONOVERLAP_REPORT_SCHEMA_VERSION,
        "zero_intersection_proof_executed_by_this_builder": True,
        "zero_intersection_counts": dict(ZERO_COUNTS),
        "split_root_only_acceptance": False,
        "rejected_overlap_source_reuse": False,
        "formal_seed_11_12_13": False,
        "full36": False,
        "math_and_runtime_boundary": dict(boundary),
    }
    preflight_inputs = {
        "schema_version": PREFLIGHT_INPUTS_SCHEMA_VERSION,
        "expected_zero_intersections": dict(ZERO_COUNTS),
        "forbidden_next_actions": {
            "fixed_dp_candidate_generation": True,
            "replay": True,
            "training": True,
            "dp_modification": True,
            "promotion": True,
            "deployment": True,
            "safety_or_camp_over_dp_claim": True,
        },
    }
    payloads = {
        "fresh_evaluation_split_member_source_manifest.json": manifest,
        "fresh_evaluation_split_member_source_nonoverlap_report.json": nonoverlap,
        "fresh_evaluation_split_member_source_preflight_inputs.json": preflight_inputs,
    }
    if mutation is not None:
        mutation(payloads)
    paths = {
        name: _write_json(root / name, payload)
        for name, payload in payloads.items()
    }
    sha_lines = [f"{_sha256(path)}  {name}" for name, path in paths.items()]
    sha_path = root / "SHA256SUMS.txt"
    sha_path.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    paths["SHA256SUMS.txt"] = sha_path
    return paths


def _audit(
    path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    status: str = MATERIALIZATION_COMPLETE_STATUS,
) -> Path:
    flags = [
        "fresh_member_selection_execution_authorized_next=False",
        "fresh_evaluation_split_evaluation_authorized_next=False",
        "data_preparation_authorized_next=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_or_postselection_authorized=False",
        "closed_loop_outcome_authorized=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]
    path.write_text(
        "\n".join(
            [
                f"current_v13_status={status}",
                f"next_work_target={target}",
                "fresh_evaluation_split_member_source_remediation_validation_preflight_authorized_next=True",
                *flags,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _build(tmp_path: Path, *, artifact_mutation: Any | None = None) -> dict[str, Any]:
    review = _post_review(tmp_path / "post_review.json")
    artifacts = _member_source_artifacts(tmp_path / "member_source", mutation=artifact_mutation)
    return build_report(
        post_review_json=review,
        expected_post_review_json_sha256=_sha256(review),
        member_source_manifest_json=artifacts["fresh_evaluation_split_member_source_manifest.json"],
        nonoverlap_report_json=artifacts["fresh_evaluation_split_member_source_nonoverlap_report.json"],
        preflight_inputs_json=artifacts["fresh_evaluation_split_member_source_preflight_inputs.json"],
        sha256sums_txt=artifacts["SHA256SUMS.txt"],
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_member_source_validation_preflight_passes_zero_overlap_artifacts(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_PASS_NEXT_WORK
    assert decision["fresh_evaluation_split_preflight_authorized_next"] is True
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["member_source_builder_executed"] is False
    assert decision["real_fresh_member_selection_executed"] is False
    assert report["member_source_summary"]["selected_member_count"] == 1


def test_member_source_validation_preflight_accepts_materializer_report_source(
    tmp_path: Path,
) -> None:
    source = _materializer_report(tmp_path / "materialization_report.json")
    artifacts = _member_source_artifacts(tmp_path / "member_source")
    report = build_report(
        post_review_json=source,
        expected_post_review_json_sha256=_sha256(source),
        member_source_manifest_json=artifacts["fresh_evaluation_split_member_source_manifest.json"],
        nonoverlap_report_json=artifacts["fresh_evaluation_split_member_source_nonoverlap_report.json"],
        preflight_inputs_json=artifacts["fresh_evaluation_split_member_source_preflight_inputs.json"],
        sha256sums_txt=artifacts["SHA256SUMS.txt"],
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == PASS_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_PASS_NEXT_WORK


def test_member_source_validation_preflight_fail_closes_missing_artifacts(tmp_path: Path) -> None:
    review = _post_review(tmp_path / "post_review.json")
    report = build_report(
        post_review_json=review,
        expected_post_review_json_sha256=_sha256(review),
        member_source_manifest_json=tmp_path / "missing_manifest.json",
        nonoverlap_report_json=tmp_path / "missing_nonoverlap.json",
        preflight_inputs_json=tmp_path / "missing_inputs.json",
        sha256sums_txt=tmp_path / "missing_SHA256SUMS.txt",
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert decision["passed"] is False
    assert decision["failure_class"] == "fresh_member_source_artifact_missing"
    assert decision["authorized_next_work"] == AUTHORIZED_MISSING_INPUT_NEXT_WORK
    assert decision["member_source_materialization_plan_authorized_next"] is True
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False


def test_member_source_validation_preflight_rejects_wrong_audit_target(tmp_path: Path) -> None:
    review = _post_review(tmp_path / "post_review.json")
    artifacts = _member_source_artifacts(tmp_path / "member_source")
    report = build_report(
        post_review_json=review,
        expected_post_review_json_sha256=_sha256(review),
        member_source_manifest_json=artifacts["fresh_evaluation_split_member_source_manifest.json"],
        nonoverlap_report_json=artifacts["fresh_evaluation_split_member_source_nonoverlap_report.json"],
        preflight_inputs_json=artifacts["fresh_evaluation_split_member_source_preflight_inputs.json"],
        sha256sums_txt=artifacts["SHA256SUMS.txt"],
        v13_audit_md=_audit(tmp_path / "audit.md", target="old_gate"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["failure_class"] == "audit_authorization_mismatch"
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_member_source_validation_preflight_rejects_nonzero_overlap(tmp_path: Path) -> None:
    def overlap(payloads: dict[str, dict[str, Any]]) -> None:
        payloads["fresh_evaluation_split_member_source_manifest.json"][
            "zero_intersection_counts"
        ]["candidate_tensor_hash_intersection_count"] = 1
        payloads["fresh_evaluation_split_member_source_nonoverlap_report.json"][
            "zero_intersection_counts"
        ]["candidate_tensor_hash_intersection_count"] = 1

    report = _build(tmp_path, artifact_mutation=overlap)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["failure_class"] == "nonzero_member_source_registry_overlap"
    assert (
        "candidate_tensor_hash_intersection_count_is_zero"
        in report["final_decision"]["failed_checks"]
    )


def test_member_source_validation_preflight_rejects_action_leak(tmp_path: Path) -> None:
    def leak(payloads: dict[str, dict[str, Any]]) -> None:
        payloads["fresh_evaluation_split_member_source_manifest.json"][
            "math_and_runtime_boundary"
        ]["training"] = True

    report = _build(tmp_path, artifact_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["failure_class"] == "forbidden_action_authorization_leak"
    assert "manifest_boundary_blocks_training" in report["final_decision"]["failed_checks"]


def test_member_source_validation_preflight_main_writes_outputs_for_rejection(tmp_path: Path) -> None:
    review = _post_review(tmp_path / "post_review.json")
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"

    exit_code = main(
        [
            "--post_review_json",
            str(review),
            "--expected_post_review_json_sha256",
            _sha256(review),
            "--member_source_manifest_json",
            str(tmp_path / "missing_manifest.json"),
            "--nonoverlap_report_json",
            str(tmp_path / "missing_nonoverlap.json"),
            "--preflight_inputs_json",
            str(tmp_path / "missing_inputs.json"),
            "--sha256sums_txt",
            str(tmp_path / "missing_SHA256SUMS.txt"),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
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
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == REJECT_STATUS
    assert payload["final_decision"]["failure_class"] == "fresh_member_source_artifact_missing"
    assert "read-only" in output_md.read_text(encoding="utf-8")
