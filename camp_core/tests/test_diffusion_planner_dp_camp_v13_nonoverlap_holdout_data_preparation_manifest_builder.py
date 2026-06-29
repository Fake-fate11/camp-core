from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation_manifest import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
    EXCLUSION_MANIFEST_SCHEMA_VERSION,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUEST_MANIFEST_SCHEMA_VERSION,
    SOURCE_MANIFEST_SCHEMA_VERSION,
    SOURCE_REVIEW_SCHEMA_VERSION,
    SOURCE_REVIEW_STATUS,
    TARGET_HOLDOUT_RECORDS,
    TARGET_HOLDOUT_SELECTION_LOGS,
    build_manifest_report,
    main,
)


CAMP_HEAD = "92db0f240eeecbc176a0817ceace836c94266098"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _static_review(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "final_decision": {
            "status": SOURCE_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "builder_implementation_authorized_next": True,
            "data_preparation_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _source_manifest(path: Path, *, mutation: Any | None = None) -> Path:
    requests = [
        {
            "request_id": f"holdout-{idx:03d}",
            "route_id": f"route_{idx:03d}",
            "seed": 1000 + idx,
            "scenario_tag": "nonformal_holdout",
        }
        for idx in range(TARGET_HOLDOUT_SELECTION_LOGS)
    ]
    payload = {
        "schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        "target_holdout_selection_logs": TARGET_HOLDOUT_SELECTION_LOGS,
        "target_holdout_records": TARGET_HOLDOUT_RECORDS,
        "expected_steps_per_log": 100,
        "expected_candidate_count": 8,
        "expected_atom_count": 14,
        "score_expression": "score_k(w)=a_k^T w",
        "nonnegative_simplex_weights_only": True,
        "formal_seeds_11_12_13_excluded": True,
        "route_seed_requests": requests,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _small_json(path: Path) -> Path:
    return _write_json(path, {"ok": True})


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_implementation_static_contract_review_complete",
                f"next_work_target={current_work}",
                "data_preparation_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
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
    current_work: str = AUTHORIZED_CURRENT_WORK,
    review_mutation: Any | None = None,
    source_mutation: Any | None = None,
    current_dp_head: str = FIXED_DP_HEAD,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    review = _static_review(tmp_path / "static_review.json", mutation=review_mutation)
    source = _source_manifest(tmp_path / "source_manifest.json", mutation=source_mutation)
    output_root = output_dir or (tmp_path / "out")
    return build_manifest_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        nonformal_holdout_source_manifest_json=source,
        previous_training_summary_json=_small_json(tmp_path / "training_summary.json"),
        rejected_result_readiness_json=_small_json(tmp_path / "result_readiness.json"),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        output_dir=output_root,
        output_json=output_root / "manifest_builder_report.json",
        output_md=output_root / "manifest_builder_report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=current_dp_head,
        enabled=enabled,
    )


def test_manifest_builder_is_default_off_and_has_no_side_effects(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    report = build_manifest_report(
        implementation_static_contract_review_json=tmp_path / "missing_review.json",
        expected_static_contract_review_sha256="0" * 64,
        nonformal_holdout_source_manifest_json=tmp_path / "missing_source.json",
        previous_training_summary_json=tmp_path / "missing_training.json",
        rejected_result_readiness_json=tmp_path / "missing_readiness.json",
        v13_audit_md=tmp_path / "missing_audit.md",
        output_dir=output_root,
        output_json=output_root / "report.json",
        output_md=output_root / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["checks"] == []
    assert not output_root.exists()


def test_manifest_builder_writes_manifest_only_outputs_when_enabled(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    report = _build(tmp_path, output_dir=output_root)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["manifest_files_written"] is True
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["data_preparation_authorized_next"] is False
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["final_decision"]["training_execution_authorized_next"] is False
    assert report["final_decision"]["replay_execution_authorized_next"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False

    request_manifest = json.loads(
        (output_root / "holdout_candidate_request_manifest.json").read_text(encoding="utf-8")
    )
    exclusion_manifest = json.loads(
        (output_root / "nonoverlap_exclusion_registry_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    expected_manifest = json.loads(
        (output_root / "expected_holdout_artifact_manifest.json").read_text(encoding="utf-8")
    )
    runbook = (output_root / "holdout_preparation_runbook.sh").read_text(encoding="utf-8")

    assert request_manifest["schema_version"] == REQUEST_MANIFEST_SCHEMA_VERSION
    assert request_manifest["target_holdout_selection_logs"] == TARGET_HOLDOUT_SELECTION_LOGS
    assert request_manifest["target_holdout_records"] == TARGET_HOLDOUT_RECORDS
    assert len(request_manifest["route_seed_requests"]) == TARGET_HOLDOUT_SELECTION_LOGS
    assert request_manifest["executions_requested_by_this_manifest"] == {
        "data_preparation": False,
        "fixed_dp_candidate_generation": False,
        "replay": False,
        "training": False,
    }
    assert exclusion_manifest["schema_version"] == EXCLUSION_MANIFEST_SCHEMA_VERSION
    assert exclusion_manifest["train_eval_candidate_tensor_intersection_must_be_zero"] is True
    assert expected_manifest["schema_version"] == EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION
    assert expected_manifest["must_not_execute_by_manifest_builder"]["training"] is True
    assert "no DP execution" in runbook


def test_manifest_builder_main_writes_report_and_sha256sums(tmp_path: Path) -> None:
    review = _static_review(tmp_path / "static_review.json")
    source = _source_manifest(tmp_path / "source_manifest.json")
    output_root = tmp_path / "out"
    output_json = output_root / "manifest_builder_report.json"
    output_md = output_root / "manifest_builder_report.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(review),
            "--expected_static_contract_review_sha256",
            _sha256(review),
            "--nonformal_holdout_source_manifest_json",
            str(source),
            "--previous_training_summary_json",
            str(_small_json(tmp_path / "training_summary.json")),
            "--rejected_result_readiness_json",
            str(_small_json(tmp_path / "result_readiness.json")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--output_dir",
            str(output_root),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_nonoverlap_holdout_data_preparation_manifest_builder",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert (output_root / "SHA256SUMS").is_file()
    sha_text = (output_root / "SHA256SUMS").read_text(encoding="utf-8")
    assert "holdout_candidate_request_manifest.json" in sha_text
    assert "manifest_builder_report.json" not in sha_text
    assert "manifest-only" in output_md.read_text(encoding="utf-8")


def test_manifest_builder_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _build(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_source_review_data_preparation_auth(tmp_path: Path) -> None:
    def authorize_data_preparation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["data_preparation_authorized_next"] = True

    report = _build(tmp_path, review_mutation=authorize_data_preparation)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_blocks_data_preparation" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_formal_seed_request(tmp_path: Path) -> None:
    def add_formal_seed(payload: dict[str, Any]) -> None:
        payload["route_seed_requests"][0]["seed"] = 11

    report = _build(tmp_path, source_mutation=add_formal_seed)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_manifest_no_formal_seed_requests" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_target_scale_drift(tmp_path: Path) -> None:
    def drop_request(payload: dict[str, Any]) -> None:
        payload["route_seed_requests"] = payload["route_seed_requests"][:-1]

    report = _build(tmp_path, source_mutation=drop_request)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_manifest_request_count" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_dp_head_drift(tmp_path: Path) -> None:
    report = _build(tmp_path, current_dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_output_path_outside_output_dir(tmp_path: Path) -> None:
    review = _static_review(tmp_path / "static_review.json")
    source = _source_manifest(tmp_path / "source_manifest.json")
    output_root = tmp_path / "out"
    report = build_manifest_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        nonformal_holdout_source_manifest_json=source,
        previous_training_summary_json=_small_json(tmp_path / "training_summary.json"),
        rejected_result_readiness_json=_small_json(tmp_path / "result_readiness.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=output_root,
        output_json=tmp_path / "outside_report.json",
        output_md=output_root / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "output_json_under_output_dir" in report["final_decision"]["failed_checks"]
