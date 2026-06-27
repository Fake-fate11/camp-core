from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.preflight_diffusion_planner_dp_camp_v13_promotion_evidence_package import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "c3a57b1a512ce1ba77ae0ebae1996835f46b0c7c"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCALE_SHA = "52c1ffe117c4661c0b4798e242487fc9d2ed1ef6f44f65fbfa7aa37faef2a1b6"
DATASET_SHA = "2f41d07adedd28ded0869ec0f13a5e13beabe2f7e5f07a54e97b220df928113b"


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
        "camp_training_executed": False,
    }


def _result_review() -> dict[str, object]:
    return {
        "artifact_summary": {
            "records_total": 51200,
            "records_without_feasible_candidate": 14058,
            "training_records": 11262,
            "validation_records": 2796,
            "num_candidates": 8,
            "num_atoms": 14,
            "score_expression": "score_k(w)=a_k^T w",
        },
        "final_decision": {
            "status": "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready",
            "passed": True,
            "failed_checks": [],
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
        },
    }


def _promotion_plan(*, selector_promotion: bool = False) -> dict[str, object]:
    return {
        "source_summary": {
            "records_total": 51200,
            "score_expression": "score_k(w)=a_k^T w",
        },
        "promotion_decision_plan": {
            "recommendation": "do_not_promote_from_current_evidence_alone",
        },
        "evidence_package_preflight": {
            "status": "planned_not_executed",
        },
        "final_decision": {
            "status": "dp_camp_v13_promotion_decision_plan_ready",
            "passed": True,
            "authorized_next_work": "dp_camp_v13_promotion_evidence_package_preflight_only",
            "evidence_package_preflight_authorized": True,
            "failed_checks": [],
            "selector_promotion_authorized": selector_promotion,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
        },
    }


def _weights(*, negative: bool = False) -> dict[str, object]:
    values = [0.0] * 14
    values[4] = -0.1 if negative else 0.2
    values[5] = 0.2
    values[6] = 0.2
    values[10] = 0.2
    values[12] = 0.3 if negative else 0.2
    return {
        "atom_names": [f"atom_{idx}" for idx in range(14)],
        "atom_schema_version": "dp_camp_v10_14d",
        "fallback_only": True,
        "score_expression": "score_k(w)=a_k^T w",
        "selector_promotion_executed": False,
        "source_hashes": {
            "dataset": DATASET_SHA,
            "scale_manifest": SCALE_SHA,
        },
        "weights": values,
    }


def _atom_scales() -> dict[str, object]:
    return {
        "atom_names": [f"atom_{idx}" for idx in range(14)],
        "atom_schema_version": "dp_camp_v10_14d",
        "scales": [float(idx + 1) for idx in range(14)],
        "source_scale_manifest_sha256": SCALE_SHA,
    }


def _training(
    *,
    weights_json_sha: str,
    weights_npy_sha: str,
    atom_scales_sha: str,
    seed: int = 23,
    weights_min: float = 0.0,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": "dp_native_fallback_risk_static_camp_training_complete",
            "passed": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training": True,
        },
        "output_artifacts": {
            "weights_json_sha256": weights_json_sha,
            "weights_npy_sha256": weights_npy_sha,
            "atom_scales_json_sha256": atom_scales_sha,
        },
        "training": {
            "training_seed": seed,
            "num_candidates": 8,
            "num_atoms": 14,
            "atom_schema_version": "dp_camp_v10_14d",
            "objective": "simplex_hinge_cvar_l2",
            "risk_type": "cvar",
            "score_expression": "score_k(w)=a_k^T w",
            "training_records": 11262,
            "validation_records": 2796,
            "weights_sum": 1.0,
            "weights_min": weights_min,
        },
    }


def _pipeline(training_sha: str) -> dict[str, object]:
    return {
        "status": "complete",
        "dataset_record_counts": {
            "records_built": 14058,
            "records_total": 51200,
        },
        "split_record_counts": {"training_records": 11262, "validation_records": 2796},
        "scale_fit_record_counts": {"fit_records_used": 11262},
        "sha256": {
            "dataset_json_sha256": DATASET_SHA,
            "scale_manifest_json_sha256": SCALE_SHA,
            "training_summary_json_sha256": training_sha,
        },
        "preflight_final_decision": {"passed": True},
        "validator_final_decision": {"passed": True},
        "training_final_decision": {
            "passed": True,
            "fixed_dp_candidate_reranking_only": True,
        },
    }


def _nonpromotion() -> dict[str, object]:
    return {
        "final_decision": {
            "passed": True,
            "training_artifacts_nonpromotion": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training_artifact": True,
            "score_expression": "score_k(w)=a_k^T w",
            "training_authorized": False,
            "deployment_authorized": False,
        }
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
        }
    }


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifacts(
    tmp_path: Path,
    *,
    selector_promotion: bool = False,
    training_seed: int = 23,
    negative_weights: bool = False,
) -> dict[str, Path]:
    paths = {
        "promotion_decision_plan_json": tmp_path / "promotion_decision_plan.json",
        "result_review_json": tmp_path / "result_review.json",
        "collection_summary_json": tmp_path / "collection_summary.json",
        "pipeline_summary_json": tmp_path / "pipeline_summary.json",
        "training_summary_json": tmp_path / "training_summary.json",
        "weights_json": tmp_path / "weights.json",
        "weights_npy": tmp_path / "weights.npy",
        "atom_scales_json": tmp_path / "atom_scales.json",
        "nonpromotion_audit_json": tmp_path / "nonpromotion_audit.json",
        "holdout_audit_json": tmp_path / "holdout_audit.json",
    }
    weights_sha = _write_json(paths["weights_json"], _weights(negative=negative_weights))
    atom_scales_sha = _write_json(paths["atom_scales_json"], _atom_scales())
    paths["weights_npy"].write_bytes(b"static-weight-bytes")
    weights_npy_sha = hashlib.sha256(paths["weights_npy"].read_bytes()).hexdigest()
    training_sha = _write_json(
        paths["training_summary_json"],
        _training(
            weights_json_sha=weights_sha,
            weights_npy_sha=weights_npy_sha,
            atom_scales_sha=atom_scales_sha,
            seed=training_seed,
            weights_min=-0.1 if negative_weights else 0.0,
        ),
    )
    _write_json(paths["promotion_decision_plan_json"], _promotion_plan(selector_promotion=selector_promotion))
    _write_json(paths["result_review_json"], _result_review())
    _write_json(paths["collection_summary_json"], _collection())
    _write_json(paths["pipeline_summary_json"], _pipeline(training_sha))
    _write_json(paths["nonpromotion_audit_json"], _nonpromotion())
    _write_json(paths["holdout_audit_json"], _holdout())
    return paths


def _report(tmp_path: Path) -> dict[str, object]:
    return build_report(
        **_write_artifacts(tmp_path),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )


def test_evidence_package_preflight_ready_but_does_not_promote(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["promotion_evidence_package_preflight_ready"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert len(report["artifact_manifest"]) == 10
    assert report["static_integration_contract"]["score_expression"] == "score_k(w)=a_k^T w"


def test_evidence_package_preflight_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        promotion_decision_plan_json=missing,
        result_review_json=missing,
        collection_summary_json=missing,
        pipeline_summary_json=missing,
        training_summary_json=missing,
        weights_json=missing,
        weights_npy=tmp_path / "missing.npy",
        atom_scales_json=missing,
        nonpromotion_audit_json=missing,
        holdout_audit_json=missing,
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["preflight_checks"] == []


def test_evidence_package_preflight_rejects_formal_training_seed(tmp_path: Path) -> None:
    report = build_report(
        **_write_artifacts(tmp_path, training_seed=11),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_seed_not_formal" in report["final_decision"]["failed_checks"]


def test_evidence_package_preflight_rejects_negative_weight(tmp_path: Path) -> None:
    report = build_report(
        **_write_artifacts(tmp_path, negative_weights=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "weights_nonnegative" in report["final_decision"]["failed_checks"]


def test_evidence_package_preflight_rejects_source_promotion_leak(tmp_path: Path) -> None:
    report = build_report(
        **_write_artifacts(tmp_path, selector_promotion=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "promotion_plan_selector_promotion_authorized_false" in report[
        "final_decision"
    ]["failed_checks"]


def test_evidence_package_preflight_markdown_preserves_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Promotion Evidence Package Preflight" in markdown
    assert "Promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "does not promote atoms or selectors" in markdown


def test_evidence_package_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_artifacts(tmp_path)
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    argv = [
        "v13-evidence-package-preflight",
        "--current_camp_head",
        CAMP_HEAD,
        "--current_dp_head",
        DP_HEAD,
        "--enable_v13_promotion_evidence_package_preflight",
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
    assert "Evidence Package Preflight" in output_md.read_text(encoding="utf-8")
