from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.review_diffusion_planner_dp_camp_v13_offline_nonpromotion_static_reranker_result import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "378adc3518490f9b8ebdecfde0d7ee7b557d986a"


def _collection() -> dict[str, object]:
    return {
        "status": "complete",
        "selection_log_count": 512,
        "expected_replay_commands": 512,
        "failed_replay_commands": 0,
        "records_total": 51200,
        "records_without_feasible_candidate": 14058,
        "records_with_feasible_candidate": 37142,
        "records_bad_feasible_mask": 0,
        "candidate_counts": [8],
        "formal_seed_path_matches": 0,
        "provenance_present_records": 51200,
        "provenance_payload_valid_records": 51200,
        "provenance_prepost_equal_records": 51200,
        "provenance_reference_blend_separated_records": 51200,
        "contract_unique_values": [[8, False, None, False]],
        "fixed_dp_candidate_generation_authorized": True,
        "candidate_generation_by_camp_authorized": False,
        "dp_modification_authorized": False,
    }


def _pipeline(training_sha: str) -> dict[str, object]:
    return {
        "status": "complete",
        "dataset_record_counts": {
            "records_built": 14058,
            "records_total": 51200,
        },
        "split_record_counts": {"training_records": 11262, "validation_records": 2796},
        "scale_fit_record_counts": {
            "fit_records_used": 11262,
            "training_records_seen": 11262,
            "validation_records_seen": 2796,
        },
        "sha256": {"training_summary_json_sha256": training_sha},
        "preflight_final_decision": {"passed": True},
        "validator_final_decision": {"passed": True},
        "training_final_decision": {
            "passed": True,
            "training_executed": True,
            "fixed_dp_candidate_reranking_only": True,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
        },
    }


def _training() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "dp_native_fallback_risk_static_camp_training_complete",
            "passed": True,
            "training_authorized": True,
            "training_executed": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training": True,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "training": {
            "training_seed": 23,
            "num_candidates": 8,
            "num_atoms": 14,
            "atom_schema_version": "dp_camp_v10_14d",
            "objective": "simplex_hinge_cvar_l2",
            "risk_type": "cvar",
            "score_expression": "score_k(w)=a_k^T w",
            "training_records": 11262,
            "validation_records": 2796,
            "weights_sum": 1.0,
            "weights_min": 0.0,
        },
    }


def _nonpromotion() -> dict[str, object]:
    return {
        "artifact_checks": {
            "training_summary_sha256_match": True,
            "weights_json_sha256_match": True,
            "weights_npy_sha256_match": True,
            "atom_scales_json_sha256_match": True,
        },
        "final_decision": {
            "passed": True,
            "training_artifacts_nonpromotion": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training_artifact": True,
            "score_expression": "score_k(w)=a_k^T w",
            "training_authorized": False,
            "deployment_authorized": False,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
        },
    }


def _holdout() -> dict[str, object]:
    return {
        "final_decision": {
            "passed": True,
            "records_scope": "validation_groups_only",
            "fallback_branch_only": True,
            "records_without_feasible_candidate_only": True,
            "fixed_dp_candidate_reranking_only": True,
            "selection_rule": "argmin_k score_k(w)",
            "score_expression": "score_k(w)=a_k^T w",
            "training_authorized": False,
            "deployment_authorized": False,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
        }
    }


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifacts(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "collection_summary_json": tmp_path / "collection_summary.json",
        "pipeline_summary_json": tmp_path / "pipeline_summary.json",
        "training_summary_json": tmp_path / "training_summary.json",
        "nonpromotion_audit_json": tmp_path / "nonpromotion_audit.json",
        "holdout_audit_json": tmp_path / "holdout_audit.json",
    }
    _write_json(paths["collection_summary_json"], _collection())
    training_sha = _write_json(paths["training_summary_json"], _training())
    _write_json(paths["pipeline_summary_json"], _pipeline(training_sha))
    _write_json(paths["nonpromotion_audit_json"], _nonpromotion())
    _write_json(paths["holdout_audit_json"], _holdout())
    return paths


def _report(tmp_path: Path) -> dict[str, object]:
    return build_report(
        **_write_artifacts(tmp_path),
        current_camp_head=CAMP_HEAD,
        label="unit",
        enabled=True,
    )


def test_v13_result_review_ready(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["promotion_decision_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["artifact_summary"]["score_expression"] == "score_k(w)=a_k^T w"


def test_v13_result_review_accepts_candidate_expansion_expected_counts(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    collection = _collection()
    collection["records_without_feasible_candidate"] = 14410
    collection["records_with_feasible_candidate"] = 36790
    _write_json(paths["collection_summary_json"], collection)

    training = _training()
    training["training"]["training_seed"] = 29  # type: ignore[index]
    training["training"]["training_records"] = 22836  # type: ignore[index]
    training["training"]["validation_records"] = 5632  # type: ignore[index]
    training_sha = _write_json(paths["training_summary_json"], training)

    pipeline = _pipeline(training_sha)
    pipeline["dataset_record_counts"] = {  # type: ignore[index]
        "records_built": 28468,
        "records_total": 102400,
        "records_with_feasible_candidate": 73932,
        "records_without_feasible_candidate": 28468,
    }
    pipeline["split_record_counts"] = {"training_records": 22836, "validation_records": 5632}  # type: ignore[index]
    pipeline["scale_fit_record_counts"] = {  # type: ignore[index]
        "fit_records_used": 22836,
        "training_records_seen": 22836,
        "validation_records_seen": 5632,
    }
    _write_json(paths["pipeline_summary_json"], pipeline)

    report = build_report(
        **paths,
        current_camp_head=CAMP_HEAD,
        label="candidate_expansion",
        expected_counts={
            "collection_records_without_feasible_candidate": 14410,
            "collection_records_with_feasible_candidate": 36790,
            "pipeline_dataset_records_built": 28468,
            "pipeline_dataset_records_total": 102400,
            "pipeline_training_records": 22836,
            "pipeline_validation_records": 5632,
            "pipeline_scale_fit_records_used": 22836,
            "pipeline_scale_training_records_seen": 22836,
            "pipeline_scale_validation_records_seen": 5632,
            "training_records": 22836,
            "training_validation_records": 5632,
        },
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["artifact_summary"]["records_total"] == 102400
    assert report["artifact_summary"]["records_without_feasible_candidate"] == 28468


def test_v13_result_review_rejects_collection_contract_drift(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    collection = _collection()
    collection["candidate_counts"] = [7]
    _write_json(paths["collection_summary_json"], collection)

    report = build_report(**paths, current_camp_head=CAMP_HEAD, enabled=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "collection_candidate_counts" in report["final_decision"]["failed_checks"]


def test_v13_result_review_rejects_formal_seed_training(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    training = _training()
    training["training"]["training_seed"] = 11  # type: ignore[index]
    training_sha = _write_json(paths["training_summary_json"], training)
    _write_json(paths["pipeline_summary_json"], _pipeline(training_sha))

    report = build_report(**paths, current_camp_head=CAMP_HEAD, enabled=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_seed_not_formal" in report["final_decision"]["failed_checks"]


def test_v13_result_review_rejects_forbidden_claim_flag(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    holdout = _holdout()
    holdout["final_decision"]["safety_benefit_claim_authorized"] = True  # type: ignore[index]
    _write_json(paths["holdout_audit_json"], holdout)

    report = build_report(**paths, current_camp_head=CAMP_HEAD, enabled=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        name.endswith("safety_benefit_claim_authorized_false")
        for name in report["final_decision"]["failed_checks"]
    )


def test_v13_result_review_markdown_preserves_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "V13 Offline Nonpromotion Static Reranker Result Review" in markdown
    assert "Promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "does not train CAMP" in markdown


def test_v13_result_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_artifacts(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    argv = [
        "v13-result-review",
        "--current_camp_head",
        CAMP_HEAD,
        "--enable_default_off_v13_offline_nonpromotion_static_reranker_result_review",
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
    ]
    for name, path in paths.items():
        argv.extend([f"--{name}", str(path)])
    monkeypatch.setattr("sys.argv", argv)

    assert main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Result Review" in output_md.read_text(encoding="utf-8")
