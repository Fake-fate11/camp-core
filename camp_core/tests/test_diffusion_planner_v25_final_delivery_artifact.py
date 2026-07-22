from __future__ import annotations

from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v25_final_delivery import (
    FINAL_INPUT_MANIFEST_SCHEMA_VERSION,
    FIXED_DP_HEAD,
    REQUIRED_ARTIFACT_ROLES,
)
import scripts.integrations.build_diffusion_planner_v25_final_evidence as producer
import scripts.integrations.review_diffusion_planner_v25_final_evidence as reviewer
from scripts.integrations.build_diffusion_planner_v25_final_evidence import (
    CONTRACT_SHA256,
    EXPECTED_REVIEW_STATUS_BY_ROLE,
    _verify_artifact_registry,
    _write_json,
)


def _sealed_pair(root: Path, role: str) -> dict:
    source = root / role
    source.mkdir()
    _write_json(source / "report.json", {"status": "passed_source"})
    (source / "run.exit").write_bytes(b"0\n")
    source_root = seal_artifact(source, label=f"{role} source")

    review = root / f"{role}_review"
    review.mkdir()
    _write_json(
        review / "report.json",
        {
            "status": EXPECTED_REVIEW_STATUS_BY_ROLE[role],
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_root_sha256": source_root,
        },
    )
    (review / "run.exit").write_bytes(b"0\n")
    review_root = seal_artifact(review, label=f"{role} review")
    return {
        "role": role,
        "path": str(source),
        "root_sha256": source_root,
        "review_path": str(review),
        "review_root_sha256": review_root,
    }


def test_final_artifact_registry_reopens_every_source_and_review_seal(
    tmp_path: Path,
) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    verified = _verify_artifact_registry(rows)
    assert set(verified) == set(REQUIRED_ARTIFACT_ROLES)
    assert {
        role: item["review_report"]["status"] for role, item in verified.items()
    } == EXPECTED_REVIEW_STATUS_BY_ROLE


def test_final_artifact_registry_rejects_review_bound_to_another_root(
    tmp_path: Path,
) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    row = rows[0]
    review = Path(row["review_path"])
    (review / "SHA256SUMS").unlink()
    (review / "ROOT_SHA256SUMS").unlink()
    _write_json(
        review / "report.json",
        {
            "status": EXPECTED_REVIEW_STATUS_BY_ROLE[row["role"]],
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_root_sha256": "0" * 64,
        },
    )
    row["review_root_sha256"] = seal_artifact(review, label="mutated review")
    with pytest.raises(ValueError, match="independent-review binding drifted"):
        _verify_artifact_registry(rows)


def test_final_artifact_registry_rejects_review_status_from_another_role(
    tmp_path: Path,
) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    row = rows[0]
    review = Path(row["review_path"])
    (review / "SHA256SUMS").unlink()
    (review / "ROOT_SHA256SUMS").unlink()
    wrong_role = REQUIRED_ARTIFACT_ROLES[1]
    _write_json(
        review / "report.json",
        {
            "status": EXPECTED_REVIEW_STATUS_BY_ROLE[wrong_role],
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_root_sha256": row["root_sha256"],
        },
    )
    row["review_root_sha256"] = seal_artifact(review, label="wrong-role review")
    with pytest.raises(ValueError, match="independent-review binding drifted"):
        _verify_artifact_registry(rows)


def test_final_artifact_registry_rejects_nonzero_run_exit(tmp_path: Path) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    row = rows[-1]
    source = Path(row["path"])
    (source / "SHA256SUMS").unlink()
    (source / "ROOT_SHA256SUMS").unlink()
    (source / "run.exit").write_bytes(b"1\n")
    row["root_sha256"] = seal_artifact(source, label="failed source")
    with pytest.raises(ValueError, match="did not exit successfully"):
        _verify_artifact_registry(rows)


def _manifest(rows: list[dict]) -> dict:
    head = "2" * 40
    return {
        "schema_version": FINAL_INPUT_MANIFEST_SCHEMA_VERSION,
        "fixed_dp_head": FIXED_DP_HEAD,
        "fresh_open_count": 1,
        "fresh_b2_opened": True,
        "outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
        "contract": {
            "path": "configs/integrations/diffusion_planner_v25_final_delivery_contract_v1.json",
            "sha256": CONTRACT_SHA256,
        },
        "camp_heads": {
            "local": head,
            "origin_main": head,
            "fresh_github_main": head,
            "autodl": head,
        },
        "artifacts": rows,
    }


def _assembled_evidence() -> dict:
    return {
        "schema_version": "camp_dp_v25_final_delivery_evidence_v1",
        "status": "final_evidence_assembled_from_reviewed_upstream_artifacts",
        "final_decision": "honest_no_claim",
        "method_claims": {
            "static14d": {
                "safety_improvement_claim_passed": False,
                "red_light_improvement_claim_passed": False,
                "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
            },
            "scene14d": {
                "safety_improvement_claim_passed": False,
                "red_light_improvement_claim_passed": False,
                "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
            },
        },
        "sections": {"executive_claim_decision": {}},
        "required_sections_complete": True,
        "fresh_b2_opened_exactly_once": True,
        "outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }


def test_final_artifact_producer_and_reviewer_seal_one_end_to_end_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    manifest = tmp_path / "final_inputs.json"
    _write_json(manifest, _manifest(rows))
    evidence = _assembled_evidence()
    payloads = {
        "atom_audit": {},
        "training_report": {},
        "training_model_reports": {},
        "auxiliary_report": {},
        "calibration_contract": {},
        "preopen_qualification": {},
        "benchmark_b_evaluation": {},
    }
    monkeypatch.setattr(producer, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(producer, "_git_head", lambda _root: "2" * 40)
    monkeypatch.setattr(producer, "_load_scientific_payloads", lambda _items: payloads)
    monkeypatch.setattr(
        producer, "build_v25_final_delivery_evidence", lambda **_kwargs: evidence
    )
    output = tmp_path / "final_evidence"
    output_root = producer.build_final_evidence_artifact(
        input_manifest=manifest,
        output_dir=output,
    )

    monkeypatch.setattr(reviewer, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(reviewer, "_git_head", lambda _root: "2" * 40)
    monkeypatch.setattr(reviewer, "_load_scientific_payloads", lambda _items: payloads)
    monkeypatch.setattr(
        reviewer, "build_v25_final_delivery_evidence", lambda **_kwargs: evidence
    )
    review_output = tmp_path / "final_evidence_review"
    review_root = reviewer.review_final_evidence_artifact(
        artifact=output,
        artifact_root_sha256=output_root,
        output_dir=review_output,
    )
    assert len(output_root) == 64
    assert len(review_root) == 64
    assert (review_output / "run.exit").read_bytes() == b"0\n"


def test_final_reviewer_rejects_resealed_evidence_value_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [_sealed_pair(tmp_path, role) for role in REQUIRED_ARTIFACT_ROLES]
    manifest = tmp_path / "final_inputs.json"
    _write_json(manifest, _manifest(rows))
    evidence = _assembled_evidence()
    payloads = {
        "atom_audit": {},
        "training_report": {},
        "training_model_reports": {},
        "auxiliary_report": {},
        "calibration_contract": {},
        "preopen_qualification": {},
        "benchmark_b_evaluation": {},
    }
    monkeypatch.setattr(producer, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(producer, "_git_head", lambda _root: "2" * 40)
    monkeypatch.setattr(producer, "_load_scientific_payloads", lambda _items: payloads)
    monkeypatch.setattr(
        producer, "build_v25_final_delivery_evidence", lambda **_kwargs: evidence
    )
    output = tmp_path / "final_evidence"
    producer.build_final_evidence_artifact(input_manifest=manifest, output_dir=output)
    (output / "SHA256SUMS").unlink()
    (output / "ROOT_SHA256SUMS").unlink()
    mutated = dict(evidence)
    mutated["final_decision"] = "method_specific_bounded_safety_claim_only"
    _write_json(output / "final_evidence.json", mutated)
    report = producer._canonical_json(output / "report.json")
    report["final_evidence_sha256"] = producer._sha256(output / "final_evidence.json")
    report["final_decision"] = mutated["final_decision"]
    _write_json(output / "report.json", report)
    mutated_root = seal_artifact(output, label="mutated final evidence")

    monkeypatch.setattr(reviewer, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(reviewer, "_git_head", lambda _root: "2" * 40)
    monkeypatch.setattr(reviewer, "_load_scientific_payloads", lambda _items: payloads)
    monkeypatch.setattr(
        reviewer, "build_v25_final_delivery_evidence", lambda **_kwargs: evidence
    )
    with pytest.raises(ValueError, match="independent reconstruction"):
        reviewer.review_final_evidence_artifact(
            artifact=output,
            artifact_root_sha256=mutated_root,
            output_dir=tmp_path / "review",
        )
