from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION,
    NONOVERLAP_REPORT_SCHEMA_VERSION,
    PREFLIGHT_INPUTS_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_BEHAVIOR,
    REMATERIALIZATION_AUTHORIZED_CURRENT_WORK,
    REMATERIALIZATION_AUTHORIZED_NEXT_WORK,
    REMATERIALIZATION_LATEST_AUDIT_STATUS,
    SCHEMA_VERSION,
    SHA256SUMS_NAME,
    SOURCE_REVIEW_PASS_STATUS,
    SOURCE_REVIEW_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_member_source_report,
    main,
)


CAMP_HEAD = "1b3ca6b6438c715023a241073042a87a8ac9e61c"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_implementation_static_contract_review_passed"
)
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_runtime_v1"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selection_log(
    root: Path,
    member_id: str,
    *,
    selected_index: int = 0,
    executed_index: int = 0,
    shadow_selected_index: int = 2,
    include_selector: bool = True,
) -> str:
    path = root / "candidate" / member_id / "camp_selection_log.json"
    record: dict[str, Any] = {
        "selected_index": selected_index,
        "executed_index": executed_index,
        "shadow_selected_index": shadow_selected_index,
        "num_candidates": 8,
        "selection_scores": [float(index) for index in range(8)],
        "selection_weights": [1.0, 0.0],
        "selection_normalized_atoms": [[float(index), 1.0] for index in range(8)],
    }
    if include_selector:
        record["default_off_shadow_selector"] = {
            "schema_version": DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION,
            "enabled": True,
            "default_off": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
            "selection_effect": False,
            "online_selector_change": False,
            "executed_index": executed_index,
            "shadow_selected_index": shadow_selected_index,
        }
    _write_json(path, {"records": [record]})
    return str(path)


def _review(path: Path, *, mutation: Any | None = None) -> Path:
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
    }
    payload = {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "static_contract_review": {
            "required_future_builder_behavior": list(REQUIRED_BEHAVIOR),
            "required_zero_intersections": {key: 0 for key in ZERO_INTERSECTION_KEYS},
            "required_registry_inputs": {
                "candidate_tensor_hash_registry_required": True,
                "path_signature_registry_required": True,
                "record_identity_hash_registry_required": True,
                "split_manifest_root_registry_required": True,
                "training_registry_must_be_loaded": True,
                "recovered_prior_registry_must_be_loaded": True,
                "rejected_source_registry_must_be_loaded": True,
            },
            "source_failure_to_remediate": {
                "candidate_tensor_hash_intersection_count": 2140,
                "path_signature_intersection_count": 32,
                "record_identity_intersection_count": 3200,
                "split_manifest_root_intersection_count": 0,
                "root_zero_is_not_sufficient": True,
            },
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "master_problem_remains_convex": True,
            },
        },
        "final_decision": {
            "status": SOURCE_REVIEW_PASS_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "member_source_remediation_implementation_authorized_next": True,
            "implementation_authorized_next": True,
            **flags,
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
    root = path.parent
    payload = {
        "schema_version": "dp_camp_v13_fresh_member_source_candidates_v1",
        "members": [
            {
                "member_id": "fresh-a",
                "source_path": _selection_log(root, "fresh-a"),
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["fresh_cand_a"],
                "path_signatures": ["fresh_path_a"],
                "record_identity_hashes": ["fresh_record_a"],
                "split_manifest_roots": ["fresh_split_a"],
            },
            {
                "member_id": "overlap-candidate",
                "source_path": _selection_log(root, "overlap"),
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


def _audit(
    path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    status: str = LATEST_STATUS,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"current_v13_status={status}",
                f"next_work_target={target}",
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
    return build_member_source_report(
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
        output_json=out / "member_source_builder_report.json",
        output_md=out / "member_source_builder_report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=current_dp_head,
        enabled=enabled,
    )


def test_member_source_builder_is_default_off_and_has_no_side_effects(tmp_path: Path) -> None:
    out = tmp_path / "out"
    report = build_member_source_report(
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


def test_member_source_builder_writes_only_fresh_nonoverlap_outputs(tmp_path: Path) -> None:
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


def test_member_source_builder_supports_rematerialization_gate_overrides(
    tmp_path: Path,
) -> None:
    review = _review(tmp_path / "review.json")
    out = tmp_path / "out"
    report = build_member_source_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        candidate_member_source_manifest_json=_candidates(
            tmp_path / "candidate_members.json"
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
        v13_audit_md=_audit(
            tmp_path / "audit.md",
            target=REMATERIALIZATION_AUTHORIZED_CURRENT_WORK,
            status=REMATERIALIZATION_LATEST_AUDIT_STATUS,
        ),
        output_dir=out,
        output_json=out / "member_source_builder_report.json",
        output_md=out / "member_source_builder_report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        authorized_current_work=REMATERIALIZATION_AUTHORIZED_CURRENT_WORK,
        authorized_next_work=REMATERIALIZATION_AUTHORIZED_NEXT_WORK,
        required_latest_audit_status=REMATERIALIZATION_LATEST_AUDIT_STATUS,
        source_review_authorized_work=AUTHORIZED_CURRENT_WORK,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == REMATERIALIZATION_AUTHORIZED_NEXT_WORK
    assert report["inputs"]["source_review_authorized_work"] == AUTHORIZED_CURRENT_WORK
    assert (
        report["inputs"]["required_latest_audit_status"]
        == REMATERIALIZATION_LATEST_AUDIT_STATUS
    )
    preflight = json.loads(
        (out / "fresh_evaluation_split_member_source_preflight_inputs.json").read_text(
            encoding="utf-8"
        )
    )
    assert preflight["authorized_next_work"] == REMATERIALIZATION_AUTHORIZED_NEXT_WORK


def test_member_source_builder_main_writes_report_and_sha256sums(tmp_path: Path) -> None:
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
            str(out / "member_source_builder_report.json"),
            "--output_md",
            str(out / "member_source_builder_report.md"),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_fresh_evaluation_split_member_source_builder",
        ]
    )

    assert exit_code == 0
    payload = json.loads(
        (out / "member_source_builder_report.json").read_text(encoding="utf-8")
    )
    assert payload["final_decision"]["status"] == READY_STATUS
    sha_text = (out / SHA256SUMS_NAME).read_text(encoding="utf-8")
    assert "fresh_evaluation_split_member_source_manifest.json" in sha_text
    assert "member_source_builder_report.json" not in sha_text
    assert "default-off" in (out / "member_source_builder_report.md").read_text(
        encoding="utf-8"
    )


def test_member_source_builder_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_builder" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_builder_rejects_source_action_leak(tmp_path: Path) -> None:
    def authorize_replay(payload: dict[str, Any]) -> None:
        payload["final_decision"]["replay_execution_authorized_next"] = True

    report = _build(tmp_path, review_mutation=authorize_replay)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_blocks_action_leaks" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_builder_rejects_missing_registry(tmp_path: Path) -> None:
    out = tmp_path / "out"
    review = _review(tmp_path / "review.json")
    report = build_member_source_report(
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


def test_member_source_builder_rejects_split_root_only_acceptance(tmp_path: Path) -> None:
    def all_root_clean_but_candidate_overlaps(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "root-only-would-look-clean",
                "source_path": _selection_log(tmp_path, "root-clean"),
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["train_cand"],
                "path_signatures": ["fresh_path_c"],
                "record_identity_hashes": ["fresh_record_c"],
                "split_manifest_roots": ["fresh_split_c"],
            }
        ]

    report = _build(tmp_path, candidate_mutation=all_root_clean_but_candidate_overlaps)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "fresh_member_source_candidates_after_filters_nonempty" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 1


def test_member_source_builder_rejects_legacy_non_default_off_selection_log(
    tmp_path: Path,
) -> None:
    def legacy_source_only(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "legacy-source",
                "source_path": _selection_log(
                    tmp_path,
                    "legacy-source",
                    selected_index=3,
                    executed_index=3,
                    include_selector=False,
                ),
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["fresh_cand_legacy"],
                "path_signatures": ["fresh_path_legacy"],
                "record_identity_hashes": ["fresh_record_legacy"],
                "split_manifest_roots": ["fresh_split_legacy"],
            }
        ]

    report = _build(tmp_path, candidate_mutation=legacy_source_only)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "fresh_member_source_candidates_after_filters_nonempty" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 1
    assert report["selection_summary"]["rejected_default_off_contract_failed_count"] == 1


def test_member_source_builder_rejects_rejected_source_reuse(tmp_path: Path) -> None:
    def rejected_source_only(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "rejected-source",
                "source_role": "rejected_overlap_source",
                "source_path": _selection_log(tmp_path, "rejected"),
                "route": "sample_normal",
                "seed": 2100,
                "candidate_tensor_hashes": ["fresh_cand_c"],
                "path_signatures": ["fresh_path_c"],
                "record_identity_hashes": ["fresh_record_c"],
                "split_manifest_roots": ["fresh_split_c"],
            }
        ]

    report = _build(tmp_path, candidate_mutation=rejected_source_only)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 1


def test_member_source_builder_rejects_formal_seed_and_full36(tmp_path: Path) -> None:
    def formal_full36_only(payload: dict[str, Any]) -> None:
        payload["members"] = [
            {
                "member_id": "formal",
                "source_path": _selection_log(tmp_path, "seed_11_full36"),
                "route": "full36",
                "seed": 11,
                "is_full36": True,
                "candidate_tensor_hashes": ["fresh_cand_d"],
                "path_signatures": ["fresh_path_d"],
                "record_identity_hashes": ["fresh_record_d"],
                "split_manifest_roots": ["fresh_split_d"],
            }
        ]

    report = _build(tmp_path, candidate_mutation=formal_full36_only)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["selection_summary"]["selected_member_count"] == 0
    assert report["selection_summary"]["rejected_member_count"] == 1


def test_member_source_builder_rejects_dp_head_drift(tmp_path: Path) -> None:
    report = _build(tmp_path, current_dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]
