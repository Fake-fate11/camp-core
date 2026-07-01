from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.materialize_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_inputs import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION,
    NONOVERLAP_REPORT_SCHEMA_VERSION,
    PREFLIGHT_INPUTS_SCHEMA_VERSION,
    POST_REVIEW_PASS_STATUS,
    POST_REVIEW_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_BEHAVIOR,
    SCHEMA_VERSION,
    SHA256SUMS_NAME,
    ZERO_INTERSECTION_KEYS,
    build_materialization_report,
    main,
)


CAMP_HEAD = "d70f02fd2f53689ba0cc5752b81671d2da271a3b"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_post_implementation_static_contract_review_passed"
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _review(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": POST_REVIEW_SCHEMA_VERSION,
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "review_checks": [
            {
                "name": f"materializer_contains_{behavior}",
                "observed": "present",
                "expected": behavior,
                "passed": True,
            }
            for behavior in REQUIRED_BEHAVIOR
        ],
        "final_decision": {
            "status": POST_REVIEW_PASS_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "materialization_only_authorized_next": True,
            "materializer_execution_authorized_next": True,
            "materialization_execution_authorized_next": True,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _registry(path: Path, values: list[str], key: str = "values") -> Path:
    return _write_json(path, {key: values})


def _source_registry_manifest(path: Path, prefix: str) -> Path:
    root = path.parent
    candidate = _registry(root / f"{prefix}_candidate.json", [f"{prefix}_cand"])
    path_sig = _registry(root / f"{prefix}_path.json", [f"{prefix}_path"])
    record = _registry(root / f"{prefix}_record.json", [f"{prefix}_record"])
    split = _registry(root / f"{prefix}_split.json", [f"{prefix}_split"])
    return _write_json(
        path,
        {
            "schema_version": f"{prefix}_source_registry_v1",
            "candidate_tensor_hash_registry_json": str(candidate),
            "path_signature_registry_json": str(path_sig),
            "record_identity_hash_registry_json": str(record),
            "split_manifest_root_registry_json": str(split),
        },
    )


def _candidates(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": "dp_camp_v13_fresh_member_source_candidates_v1",
        "members": [
            {
                "member_id": "fresh-a",
                "source_path": "/candidate/fresh-a/camp_selection_log.json",
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["fresh_cand_a"],
                "path_signatures": ["fresh_path_a"],
                "record_identity_hashes": ["fresh_record_a"],
                "split_manifest_roots": ["fresh_split_a"],
            },
            {
                "member_id": "overlap-candidate",
                "source_path": "/candidate/overlap/camp_selection_log.json",
                "route": "sample_tl",
                "seed": 2101,
                "candidate_tensor_hashes": ["train_cand"],
                "path_signatures": ["fresh_path_b"],
                "record_identity_hashes": ["fresh_record_b"],
                "split_manifest_roots": ["fresh_split_b"],
            },
        ],
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                "materialization_only_authorized_next=True",
                "materializer_execution_authorized_next=True",
                "materialization_execution_authorized_next=True",
                f"next_work_target={target}",
                "implementation_execution_authorized_next=False",
                "member_source_builder_execution_authorized_next=False",
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
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _build(
    tmp_path: Path,
    *,
    enabled: bool = True,
    target: str = AUTHORIZED_CURRENT_WORK,
    review_mutation: Any | None = None,
    candidate_mutation: Any | None = None,
    current_dp_head: str = FIXED_DP_HEAD,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    review = _review(tmp_path / "review.json", mutation=review_mutation)
    out = output_dir or (tmp_path / "out")
    return build_materialization_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        candidate_member_source_manifest_json=_candidates(
            tmp_path / "candidate_members.json",
            mutation=candidate_mutation,
        ),
        training_candidate_tensor_hash_registry_json=_registry(
            tmp_path / "training_candidate.json",
            ["train_cand"],
            "candidate_tensor_hashes",
        ),
        training_path_signature_registry_json=_registry(
            tmp_path / "training_path.json",
            ["train_path"],
            "path_signatures",
        ),
        training_record_identity_registry_json=_registry(
            tmp_path / "training_record.json",
            ["train_record"],
            "record_identity_hashes",
        ),
        training_split_manifest_root_registry_json=_registry(
            tmp_path / "training_split.json",
            ["train_split"],
            "split_manifest_roots",
        ),
        recovered_prior_registry_manifest_json=_source_registry_manifest(
            tmp_path / "recovered" / "registry_manifest.json",
            "recovered",
        ),
        rejected_overlap_source_registry_manifest_json=_source_registry_manifest(
            tmp_path / "rejected" / "registry_manifest.json",
            "rejected",
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        output_dir=out,
        output_json=out / "member_source_materializer_report.json",
        output_md=out / "member_source_materializer_report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=current_dp_head,
        enabled=enabled,
    )


def test_member_source_materializer_is_default_off_and_has_no_side_effects(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    report = build_materialization_report(
        implementation_static_contract_review_json=tmp_path / "missing_review.json",
        expected_static_contract_review_sha256="0" * 64,
        candidate_member_source_manifest_json=tmp_path / "missing_candidates.json",
        training_candidate_tensor_hash_registry_json=tmp_path / "missing_train_candidate.json",
        training_path_signature_registry_json=tmp_path / "missing_train_path.json",
        training_record_identity_registry_json=tmp_path / "missing_train_record.json",
        training_split_manifest_root_registry_json=tmp_path / "missing_train_split.json",
        recovered_prior_registry_manifest_json=tmp_path / "missing_recovered.json",
        rejected_overlap_source_registry_manifest_json=tmp_path / "missing_rejected.json",
        v13_audit_md=tmp_path / "missing_audit.md",
        output_dir=out,
        output_json=out / "report.json",
        output_md=out / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["checks"] == []
    assert not out.exists()


def test_member_source_materializer_writes_only_fresh_nonoverlap_outputs(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    report = _build(tmp_path, output_dir=out)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["member_source_manifest_written"] is True
    assert report["final_decision"]["fresh_member_selection_execution_authorized_next"] is False
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["final_decision"]["training_execution_authorized_next"] is False
    assert report["final_decision"]["replay_execution_authorized_next"] is False
    assert report["final_decision"]["candidate_generation_by_camp_authorized"] is False
    assert report["final_decision"]["trajectory_modification_by_camp_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False

    manifest = json.loads(
        (out / "fresh_evaluation_split_member_source_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    nonoverlap = json.loads(
        (out / "fresh_evaluation_split_member_source_nonoverlap_report.json").read_text(
            encoding="utf-8"
        )
    )
    preflight = json.loads(
        (out / "fresh_evaluation_split_member_source_preflight_inputs.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["schema_version"] == MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION
    assert manifest["selected_member_count"] == 1
    assert manifest["selected_members"][0]["member_id"] == "fresh-a"
    assert manifest["zero_intersection_counts"] == {
        "candidate_tensor_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }
    assert manifest["math_and_runtime_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert manifest["math_and_runtime_boundary"]["fixed_dp_candidate_generation"] is False
    assert nonoverlap["schema_version"] == NONOVERLAP_REPORT_SCHEMA_VERSION
    assert nonoverlap["zero_intersection_proof_executed_by_this_builder"] is True
    assert nonoverlap["split_root_only_acceptance"] is False
    assert preflight["schema_version"] == PREFLIGHT_INPUTS_SCHEMA_VERSION
    assert preflight["authorized_next_work"] == AUTHORIZED_NEXT_WORK


def test_member_source_materializer_main_writes_report_and_sha256sums(
    tmp_path: Path,
) -> None:
    review = _review(tmp_path / "review.json")
    out = tmp_path / "out"
    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(review),
            "--expected_static_contract_review_sha256",
            _sha256(review),
            "--candidate_member_source_manifest_json",
            str(_candidates(tmp_path / "candidate_members.json")),
            "--training_candidate_tensor_hash_registry_json",
            str(_registry(tmp_path / "training_candidate.json", ["train_cand"], "candidate_tensor_hashes")),
            "--training_path_signature_registry_json",
            str(_registry(tmp_path / "training_path.json", ["train_path"], "path_signatures")),
            "--training_record_identity_registry_json",
            str(_registry(tmp_path / "training_record.json", ["train_record"], "record_identity_hashes")),
            "--training_split_manifest_root_registry_json",
            str(_registry(tmp_path / "training_split.json", ["train_split"], "split_manifest_roots")),
            "--recovered_prior_registry_manifest_json",
            str(_source_registry_manifest(tmp_path / "recovered" / "registry_manifest.json", "recovered")),
            "--rejected_overlap_source_registry_manifest_json",
            str(_source_registry_manifest(tmp_path / "rejected" / "registry_manifest.json", "rejected")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--output_dir",
            str(out),
            "--output_json",
            str(out / "member_source_materializer_report.json"),
            "--output_md",
            str(out / "member_source_materializer_report.md"),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_fresh_evaluation_split_member_source_materializer",
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (out / "member_source_materializer_report.json").read_text(encoding="utf-8")
    )
    assert payload["final_decision"]["status"] == READY_STATUS
    sha_text = (out / SHA256SUMS_NAME).read_text(encoding="utf-8")
    assert "fresh_evaluation_split_member_source_manifest.json" in sha_text
    assert "member_source_materializer_report.json" not in sha_text
    assert "default-off" in (out / "member_source_materializer_report.md").read_text(
        encoding="utf-8"
    )


def test_member_source_materializer_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_materializer" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_materializer_rejects_source_action_leak(tmp_path: Path) -> None:
    def authorize_replay(payload: dict[str, Any]) -> None:
        payload["final_decision"]["replay_execution_authorized_next"] = True

    report = _build(tmp_path, review_mutation=authorize_replay)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_blocks_action_leaks" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_materializer_rejects_missing_registry(tmp_path: Path) -> None:
    out = tmp_path / "out"
    review = _review(tmp_path / "review.json")
    report = build_materialization_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        candidate_member_source_manifest_json=_candidates(tmp_path / "candidate_members.json"),
        training_candidate_tensor_hash_registry_json=tmp_path / "missing_training_candidate.json",
        training_path_signature_registry_json=_registry(tmp_path / "training_path.json", ["train_path"], "path_signatures"),
        training_record_identity_registry_json=_registry(tmp_path / "training_record.json", ["train_record"], "record_identity_hashes"),
        training_split_manifest_root_registry_json=_registry(tmp_path / "training_split.json", ["train_split"], "split_manifest_roots"),
        recovered_prior_registry_manifest_json=_source_registry_manifest(tmp_path / "recovered" / "registry_manifest.json", "recovered"),
        rejected_overlap_source_registry_manifest_json=_source_registry_manifest(tmp_path / "rejected" / "registry_manifest.json", "rejected"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=out,
        output_json=out / "report.json",
        output_md=out / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_candidate_tensor_hashes_json_exists" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_materializer_rejects_missing_candidate_manifest_without_crash(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    review = _review(tmp_path / "review.json")

    report = build_materialization_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        candidate_member_source_manifest_json=tmp_path / "missing_candidates.json",
        training_candidate_tensor_hash_registry_json=_registry(
            tmp_path / "training_candidate.json",
            ["train_cand"],
            "candidate_tensor_hashes",
        ),
        training_path_signature_registry_json=_registry(
            tmp_path / "training_path.json",
            ["train_path"],
            "path_signatures",
        ),
        training_record_identity_registry_json=_registry(
            tmp_path / "training_record.json",
            ["train_record"],
            "record_identity_hashes",
        ),
        training_split_manifest_root_registry_json=_registry(
            tmp_path / "training_split.json",
            ["train_split"],
            "split_manifest_roots",
        ),
        recovered_prior_registry_manifest_json=_source_registry_manifest(
            tmp_path / "recovered" / "registry_manifest.json",
            "recovered",
        ),
        rejected_overlap_source_registry_manifest_json=_source_registry_manifest(
            tmp_path / "rejected" / "registry_manifest.json",
            "rejected",
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=out,
        output_json=out / "report.json",
        output_md=out / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_member_source_manifest_json_exists" in report["final_decision"][
        "failed_checks"
    ]
    assert report["planned_outputs"]["member_source_manifest"] == str(
        out / "fresh_evaluation_split_member_source_manifest.json"
    )


def test_member_source_materializer_reads_nested_result_review_registries(
    tmp_path: Path,
) -> None:
    out = tmp_path / "out"
    review = _review(tmp_path / "review.json")

    report = build_materialization_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        candidate_member_source_manifest_json=_candidates(tmp_path / "candidate_members.json"),
        training_candidate_tensor_hash_registry_json=_write_json(
            tmp_path / "training_candidate.json",
            {
                "schema_version": "nested_candidate_registry_v1",
                "training": {"values": ["train_cand"]},
                "evaluation": {"values": ["eval_cand"]},
            },
        ),
        training_path_signature_registry_json=_write_json(
            tmp_path / "training_path.json",
            {
                "schema_version": "nested_path_registry_v1",
                "training": {"signatures": ["train_path"]},
                "evaluation": {"signatures": ["eval_path"]},
            },
        ),
        training_record_identity_registry_json=_write_json(
            tmp_path / "training_record.json",
            {
                "schema_version": "nested_record_registry_v1",
                "training": {"record_identities": ["train_record"]},
                "evaluation": {"record_identities": ["eval_record"]},
            },
        ),
        training_split_manifest_root_registry_json=_write_json(
            tmp_path / "training_split.json",
            {
                "schema_version": "nested_split_registry_v1",
                "training": {"split_manifest_roots": ["train_split"]},
                "evaluation": {"split_manifest_roots": ["eval_split"]},
            },
        ),
        recovered_prior_registry_manifest_json=_source_registry_manifest(
            tmp_path / "recovered" / "registry_manifest.json",
            "recovered",
        ),
        rejected_overlap_source_registry_manifest_json=_source_registry_manifest(
            tmp_path / "rejected" / "registry_manifest.json",
            "rejected",
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=out,
        output_json=out / "report.json",
        output_md=out / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["source_summaries"]["training_registries"] == {
        "label": "training",
        "candidate_tensor_hash_count": 2,
        "path_signature_count": 2,
        "record_identity_hash_count": 2,
        "split_manifest_root_count": 2,
    }


def test_member_source_materializer_rejects_split_root_only_acceptance(
    tmp_path: Path,
) -> None:
    def root_clean_but_candidate_overlaps(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "root-only-would-look-clean",
                "source_path": "/candidate/root-clean/camp_selection_log.json",
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["train_cand"],
                "path_signatures": ["fresh_path_c"],
                "record_identity_hashes": ["fresh_record_c"],
                "split_manifest_roots": ["fresh_split_c"],
            }
        ]

    report = _build(tmp_path, candidate_mutation=root_clean_but_candidate_overlaps)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "fresh_member_source_candidates_after_filters_nonempty" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 1


def test_member_source_materializer_excludes_formal_seeds_and_full36(
    tmp_path: Path,
) -> None:
    def forbidden_members(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "formal-seed",
                "source_path": "/candidate/formal/camp_selection_log.json",
                "route": "sample_normal",
                "seed": 11,
                "candidate_tensor_hashes": ["fresh_cand_formal"],
                "path_signatures": ["fresh_path_formal"],
                "record_identity_hashes": ["fresh_record_formal"],
                "split_manifest_roots": ["fresh_split_formal"],
            },
            {
                "member_id": "full36",
                "source_path": "/candidate/full36/camp_selection_log.json",
                "route": "Full36",
                "seed": 2102,
                "candidate_tensor_hashes": ["fresh_cand_full36"],
                "path_signatures": ["fresh_path_full36"],
                "record_identity_hashes": ["fresh_record_full36"],
                "split_manifest_roots": ["fresh_split_full36"],
            },
        ]

    report = _build(tmp_path, candidate_mutation=forbidden_members)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "fresh_member_source_candidates_after_filters_nonempty" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 2
