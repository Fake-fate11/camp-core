from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.materialize_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_missing_inputs import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    MEMBER_MANIFEST_SCHEMA_VERSION,
    OUTPUT_FILES,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    SOURCE_REVIEW_PASS_STATUS,
    SOURCE_REVIEW_SCHEMA_VERSION,
    TRAINING_SPLIT_ROOTS_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "d7e9255fc3620d47f57afe0184c5f13ee596bc9e"


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
            "status": SOURCE_REVIEW_PASS_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "materialization_failure_remediation_implementation_authorized_next": True,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _member(**overrides: Any) -> dict[str, Any]:
    payload = {
        "member_id": "fresh-a",
        "source_path": "/fixed-dp/current-source/fresh-a.json",
        "route": "sample_normal",
        "seed": 2100,
        "candidate_tensor_hashes": ["fresh-cand-a"],
        "path_signatures": ["fresh-path-a"],
        "record_identity_hashes": ["fresh-record-a"],
        "split_manifest_roots": ["fresh-split-a"],
    }
    payload.update(overrides)
    return payload


def _inputs(tmp_path: Path, *, member: dict[str, Any] | None = None) -> dict[str, Any]:
    review = _static_review(tmp_path / "review.json")
    source_members = _write_json(
        tmp_path / "source_members.json",
        {"schema_version": "test_source_v1", "members": [member or _member()]},
    )
    candidate_source = _write_json(
        tmp_path / "candidate_source_manifest.json",
        {
            "schema_version": "candidate_source_collection_v1",
            "source_json_paths": [str(source_members)],
        },
    )
    training_split_roots = _write_json(
        tmp_path / "training_split_sources.json",
        {
            "schema_version": "training_split_sources_v1",
            "split_manifest_roots": ["train-split-a"],
        },
    )
    rejected = _write_json(
        tmp_path / "rejected_registry.json",
        {
            "schema_version": "rejected_registry_v1",
            "candidate_tensor_hashes": ["rejected-cand"],
            "path_signatures": ["rejected-path"],
            "record_identity_hashes": ["rejected-record"],
            "split_manifest_roots": ["rejected-split"],
        },
    )
    return {
        "implementation_static_contract_review_json": review,
        "expected_static_contract_review_sha256": _sha256(review),
        "candidate_source_manifest_json": candidate_source,
        "training_split_root_sources_json": training_split_roots,
        "rejected_overlap_source_registry_manifest_json": rejected,
        "output_dir": tmp_path / "out",
    }


def _report(tmp_path: Path, *, enabled: bool = True, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=enabled,
    )


def test_missing_input_materializer_default_off_has_no_outputs(tmp_path: Path) -> None:
    report = _report(tmp_path, enabled=False)

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["candidate_member_source_manifest_written"] is False
    assert not (tmp_path / "out" / "candidate_member_source_manifest.json").exists()


def test_missing_input_materializer_writes_candidate_manifest_and_training_split_roots(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    out = tmp_path / "out"

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["candidate_member_count"] == 1
    assert report["final_decision"]["training_split_manifest_root_count"] == 1
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["final_decision"]["candidate_generation_by_camp_authorized"] is False
    assert report["final_decision"]["training_execution_authorized_next"] is False
    candidate_manifest = json.loads(
        (out / "candidate_member_source_manifest.json").read_text(encoding="utf-8")
    )
    split_roots = json.loads(
        (out / "training_split_manifest_roots.json").read_text(encoding="utf-8")
    )
    assert candidate_manifest["schema_version"] == MEMBER_MANIFEST_SCHEMA_VERSION
    assert candidate_manifest["members"][0]["member_id"] == "fresh-a"
    assert split_roots["schema_version"] == TRAINING_SPLIT_ROOTS_SCHEMA_VERSION
    assert split_roots["split_manifest_roots"] == ["train-split-a"]
    for name in OUTPUT_FILES:
        assert (out / name).is_file()


def test_missing_input_materializer_rejects_formal_seed(tmp_path: Path) -> None:
    report = _report(tmp_path, member=_member(seed=11))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_member_errors_empty" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["training_execution_authorized_next"] is False


def test_missing_input_materializer_rejects_full36(tmp_path: Path) -> None:
    report = _report(tmp_path, member=_member(route="Full36"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_member_errors_empty" in report["final_decision"]["failed_checks"]


def test_missing_input_materializer_rejects_rejected_overlap_identity(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        member=_member(candidate_tensor_hashes=["rejected-cand"]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_member_errors_empty" in report["final_decision"]["failed_checks"]


def test_missing_input_materializer_rejects_empty_training_split_roots(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    _write_json(
        inputs["training_split_root_sources_json"],
        {"schema_version": "training_split_sources_v1", "split_manifest_roots": []},
    )

    report = build_report(
        **inputs,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_split_roots_nonempty" in report["final_decision"]["failed_checks"]


def test_missing_input_materializer_rejects_static_review_sha_mismatch(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    inputs["expected_static_contract_review_sha256"] = "0" * 64

    report = build_report(
        **inputs,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_sha256" in report["final_decision"]["failed_checks"]


def test_missing_input_materializer_main_writes_report(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    report_json = tmp_path / "report" / "materializer_report.json"
    report_md = tmp_path / "report" / "materializer_report.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(inputs["implementation_static_contract_review_json"]),
            "--expected_static_contract_review_sha256",
            inputs["expected_static_contract_review_sha256"],
            "--candidate_source_manifest_json",
            str(inputs["candidate_source_manifest_json"]),
            "--training_split_root_sources_json",
            str(inputs["training_split_root_sources_json"]),
            "--rejected_overlap_source_registry_manifest_json",
            str(inputs["rejected_overlap_source_registry_manifest_json"]),
            "--output_dir",
            str(inputs["output_dir"]),
            "--output_json",
            str(report_json),
            "--output_md",
            str(report_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_fresh_evaluation_split_member_source_missing_input_materializer",
        ]
    )

    assert exit_code == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Missing Member-Source Input Materializer" in report_md.read_text(
        encoding="utf-8"
    )
