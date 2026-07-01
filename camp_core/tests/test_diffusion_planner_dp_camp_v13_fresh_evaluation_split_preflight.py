from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.preflight_diffusion_planner_dp_camp_v13_fresh_evaluation_split import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_REMEDIATION_NEXT_WORK,
    FIXED_DP_HEAD,
    PASS_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "2192fbdadd5901b5b68f25ccc328fa7c27a7a8ef"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_manifest_builder_post_implementation_static_contract_review_complete",
        "fresh_evaluation_split_preflight_authorized_next=True",
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
        f"next_work_target={target}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _registry_file(path: Path, field: str, evaluation: list[str], training: list[str]) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "registry_v1",
            "evaluation": {"source_log_count": 32, field: evaluation},
            "training": {"source_log_count": 416, field: training},
        },
    )


def _split_manifest(path: Path, *, root_overlap: bool = False) -> Path:
    holdout = [f"/tmp/fresh/route_{idx}/static_shadow" for idx in range(32)]
    training = [f"/tmp/train/route_{idx}/static_shadow" for idx in range(416)]
    if root_overlap:
        training[0] = holdout[0]
    return _write_json(
        path,
        {
            "schema_version": "split_v1",
            "holdout": {"selection_log_roots": holdout, "seeds": [2000, 2001]},
            "training": {"selection_log_roots": training, "seeds": [1000, 1001]},
        },
    )


def _fixtures(tmp_path: Path, *, overlap: bool) -> dict[str, Path]:
    artifact = tmp_path / "artifact"
    source = tmp_path / "source"
    candidate_eval = [f"eval_candidate_{idx}" for idx in range(3200)]
    candidate_train = [f"train_candidate_{idx}" for idx in range(35200)]
    path_eval = [f"eval_path_{idx % 32}" for idx in range(3200)]
    path_train = [f"train_path_{idx % 416}" for idx in range(35200)]
    record_eval = [f"eval_record_{idx}" for idx in range(3200)]
    record_train = [f"train_record_{idx}" for idx in range(35200)]
    if overlap:
        candidate_train[:3] = candidate_eval[:3]
        path_train[:2] = path_eval[:2]
        record_train[:4] = record_eval[:4]
    candidate = _registry_file(
        source / "candidate_tensor_hash_registry.json",
        "values",
        candidate_eval,
        candidate_train,
    )
    paths = _registry_file(
        source / "path_signature_registry.json",
        "signatures",
        path_eval,
        path_train,
    )
    records = _registry_file(
        source / "record_identity_hash_registry.json",
        "record_identities",
        record_eval,
        record_train,
    )
    split = _split_manifest(source / "split_manifest.json")
    registry_manifest = _write_json(
        source / "registry_manifest.json",
        {
            "schema_version": "dp_camp_v13_current_source_result_review_source_registry_manifest_v1",
            "candidate_tensor_hash_registry_json": str(candidate),
            "path_signature_registry_json": str(paths),
            "record_identity_hash_registry_json": str(records),
            "split_manifest_json": str(split),
            "training_manifest_json": str(source / "training_manifest.json"),
            "training_formal_seed_count": 0,
            "evaluation_formal_seed_count": 0,
            "evaluation_candidate_hash_count": 3200,
        },
    )
    builder = _write_json(
        artifact / "fresh_evaluation_split_manifest_builder_report.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_manifest_builder_v1",
            "final_decision": {
                "status": "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete",
                "passed": True,
                "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            },
        },
    )
    scope = _write_json(
        artifact / "fresh_evaluation_split_scope_manifest.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_scope_manifest_v1",
            "target_selection_log_count": 32,
            "target_record_count": 3200,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "nonnegative_simplex_weights_only": True,
            "rejected_evaluation_source_registry_manifest_json": str(registry_manifest),
            "recovered_prior_registry_manifest_json": str(registry_manifest),
            "training_selection_manifest_json": str(source / "training_manifest.json"),
            "fresh_split_members_selected_by_this_builder": False,
            "future_preflight_must_prove": {
                "candidate_tensor_hash_intersection_count": 0,
                "path_signature_intersection_count": 0,
                "record_identity_intersection_count": 0,
                "split_manifest_root_intersection_count": 0,
            },
            "required_runtime_contract": {
                "default_off_shadow_selector": True,
                "executed_dp_top1": True,
                "reference_blend": False,
                "guidance": False,
                "postprocess_or_postselection": False,
                "closed_loop_outcomes_as_training_or_online_input": False,
            },
            "executions_requested_by_this_manifest": {
                "fixed_dp_candidate_generation": False,
                "data_preparation": False,
                "replay": False,
                "training": False,
                "dp_modification": False,
                "selector_or_atom_promotion": False,
                "deployment": False,
            },
        },
    )
    registry_report = _write_json(
        artifact / "fresh_evaluation_split_nonoverlap_registry_report.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_nonoverlap_registry_report_v1",
            "future_zero_intersection_preflight_required": True,
            "nonoverlap_requirements_for_future_fresh_split": {
                "candidate_tensor_hash_intersection_count": 0,
                "path_signature_intersection_count": 0,
                "record_identity_intersection_count": 0,
                "split_manifest_root_intersection_count": 0,
            },
        },
    )
    runbook = artifact / "run_fresh_evaluation_split_preflight.sh"
    runbook.write_text("#!/usr/bin/env bash\necho validation-only\n", encoding="utf-8")
    sha256sums = artifact / "SHA256SUMS.txt"
    sha256sums.write_text(
        "\n".join(
            [
                f"{_sha256(scope)}  fresh_evaluation_split_scope_manifest.json",
                f"{_sha256(registry_report)}  fresh_evaluation_split_nonoverlap_registry_report.json",
                f"{_sha256(runbook)}  run_fresh_evaluation_split_preflight.sh",
                "",
            ]
        ),
        encoding="utf-8",
    )
    audit = _audit(tmp_path / "audit.md")
    return {
        "builder": builder,
        "scope": scope,
        "registry_report": registry_report,
        "sha256sums": sha256sums,
        "audit": audit,
    }


def _build(tmp_path: Path, *, overlap: bool = False, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    paths = _fixtures(tmp_path, overlap=overlap)
    if target != AUTHORIZED_CURRENT_WORK:
        paths["audit"] = _audit(tmp_path / "audit.md", target=target)
    return build_report(
        manifest_builder_json=paths["builder"],
        expected_manifest_builder_json_sha256=_sha256(paths["builder"]),
        scope_manifest_json=paths["scope"],
        nonoverlap_registry_report_json=paths["registry_report"],
        sha256sums_txt=paths["sha256sums"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_preflight_rejects_overlap_fail_closed(tmp_path: Path) -> None:
    report = _build(tmp_path, overlap=True)

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["passed"] is False
    assert (
        report["final_decision"]["failure_class"]
        == "candidate_tensor_hash_overlap_with_training_registry"
    )
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_REMEDIATION_NEXT_WORK
    assert report["final_decision"]["fresh_evaluation_split_member_source_remediation_plan_authorized_next"] is True
    assert report["final_decision"]["replay_execution_authorized_next"] is False
    assert report["final_decision"]["training_execution_authorized_next"] is False
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["preflight_result"]["candidate_tensor_hash_intersection_count"] == 3
    assert report["preflight_result"]["path_signature_intersection_count"] == 2
    assert report["preflight_result"]["record_identity_intersection_count"] == 4
    assert report["preflight_result"]["split_manifest_root_intersection_count"] == 0


def test_fresh_evaluation_split_preflight_passes_zero_intersection(tmp_path: Path) -> None:
    report = _build(tmp_path, overlap=False)

    assert report["final_decision"]["status"] == PASS_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["fresh_evaluation_split_evaluation_authorized_next"] is True
    assert report["preflight_result"]["all_required_intersections_zero"] is True


def test_fresh_evaluation_split_preflight_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, target="wrong_gate", overlap=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False


def test_fresh_evaluation_split_preflight_rejects_dp_drift(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path, overlap=False)
    report = build_report(
        manifest_builder_json=paths["builder"],
        expected_manifest_builder_json_sha256=_sha256(paths["builder"]),
        scope_manifest_json=paths["scope"],
        nonoverlap_registry_report_json=paths["registry_report"],
        sha256sums_txt=paths["sha256sums"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_preflight_rejects_reference_blend_leak(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path, overlap=False)
    scope = json.loads(paths["scope"].read_text(encoding="utf-8"))
    scope["required_runtime_contract"]["reference_blend"] = True
    _write_json(paths["scope"], scope)
    report = build_report(
        manifest_builder_json=paths["builder"],
        expected_manifest_builder_json_sha256=_sha256(paths["builder"]),
        scope_manifest_json=paths["scope"],
        nonoverlap_registry_report_json=paths["registry_report"],
        sha256sums_txt=paths["sha256sums"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runtime_blocks_reference_blend" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_preflight_main_writes_report(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path, overlap=True)
    output_json = tmp_path / "out" / "fresh_evaluation_split_preflight.json"
    output_md = tmp_path / "out" / "fresh_evaluation_split_preflight.md"

    exit_code = main(
        [
            "--manifest_builder_json",
            str(paths["builder"]),
            "--expected_manifest_builder_json_sha256",
            _sha256(paths["builder"]),
            "--scope_manifest_json",
            str(paths["scope"]),
            "--nonoverlap_registry_report_json",
            str(paths["registry_report"]),
            "--sha256sums_txt",
            str(paths["sha256sums"]),
            "--v13_audit_md",
            str(paths["audit"]),
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
    assert "fixed-input only" in output_md.read_text(encoding="utf-8")
