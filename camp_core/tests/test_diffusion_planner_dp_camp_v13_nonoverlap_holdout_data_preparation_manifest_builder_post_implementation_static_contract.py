from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
    EXCLUSION_MANIFEST_SCHEMA_VERSION,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUEST_MANIFEST_SCHEMA_VERSION,
    SOURCE_BUILDER_SCHEMA_VERSION,
    SOURCE_BUILDER_STATUS,
    TARGET_HOLDOUT_RECORDS,
    TARGET_HOLDOUT_SELECTION_LOGS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "46a33312854bd92421d9eb2412f6dd8e8091cf6e"
BUILDER_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation_manifest.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder.py"
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _request_manifest(path: Path, *, mutation: Any | None = None) -> Path:
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
        "schema_version": REQUEST_MANIFEST_SCHEMA_VERSION,
        "target_holdout_selection_logs": TARGET_HOLDOUT_SELECTION_LOGS,
        "target_holdout_records": TARGET_HOLDOUT_RECORDS,
        "expected_steps_per_log": 100,
        "expected_candidate_count": 8,
        "expected_atom_count": 14,
        "formal_seeds_11_12_13_excluded": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
        "route_seed_requests": requests,
        "executions_requested_by_this_manifest": {
            "fixed_dp_candidate_generation": False,
            "data_preparation": False,
            "replay": False,
            "training": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _exclusion_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": EXCLUSION_MANIFEST_SCHEMA_VERSION,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "train_eval_record_identity_intersection_must_be_zero": True,
            "formal_seeds_11_12_13_excluded": True,
        },
    )


def _expected_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
            "expected_selection_log_count": TARGET_HOLDOUT_SELECTION_LOGS,
            "expected_records": TARGET_HOLDOUT_RECORDS,
            "expected_steps_per_log": 100,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "required_outputs": [
                "selection_logs",
                "candidate_tensor_hash_registry.json",
                "path_signature_registry.json",
                "record_identity_hash_registry.json",
                "SHA256SUMS",
            ],
            "must_not_execute_by_manifest_builder": {
                "fixed_dp_candidate_generation": True,
                "data_preparation": True,
                "replay": True,
                "training": True,
                "dp_modification": True,
            },
        },
    )


def _runbook(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "echo 'validation-only runbook for non-overlap holdout manifests'",
                "echo 'no DP execution, no candidate generation, no replay, no training'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _sha256sums(path: Path, files: list[Path]) -> Path:
    path.write_text(
        "".join(f"{_sha256(item)}  {item.name}\n" for item in files),
        encoding="utf-8",
    )
    return path


def _builder_json(
    path: Path,
    *,
    output_dir: Path,
    current_dp_head: str = FIXED_DP_HEAD,
    mutation: Any | None = None,
) -> Path:
    sha_path = output_dir / "SHA256SUMS"
    payload = {
        "schema_version": SOURCE_BUILDER_SCHEMA_VERSION,
        "analysis": {
            "default_off": True,
            "manifest_builder_only": True,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "heads": {
            "current_camp_head": CAMP_HEAD,
            "current_camp_origin_main": CAMP_HEAD,
            "current_dp_head": current_dp_head,
            "required_dp_head": FIXED_DP_HEAD,
        },
        "output_hashes": {
            "holdout_candidate_request_manifest_sha256": _sha256(
                output_dir / "holdout_candidate_request_manifest.json"
            ),
            "nonoverlap_exclusion_registry_manifest_sha256": _sha256(
                output_dir / "nonoverlap_exclusion_registry_manifest.json"
            ),
            "holdout_preparation_runbook_sha256": _sha256(
                output_dir / "holdout_preparation_runbook.sh"
            ),
            "expected_holdout_artifact_manifest_sha256": _sha256(
                output_dir / "expected_holdout_artifact_manifest.json"
            ),
            "sha256sums_sha256": _sha256(sha_path),
        },
        "final_decision": {
            "status": SOURCE_BUILDER_STATUS,
            "passed": True,
            "enabled": True,
            "failed_checks": [],
            "manifest_files_written": True,
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "post_implementation_static_contract_review_authorized_next": True,
            "data_preparation_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "data_preparation_executed": False,
            "fixed_dp_candidate_generation_executed": False,
            "training_executed": False,
            "replay_executed": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, next_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.write_text(
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_manifest_builder_complete",
                "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_post_implementation_static_contract_review_authorized=True",
                "data_preparation_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                f"next_work_target={next_work}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _inputs(
    tmp_path: Path,
    *,
    request_mutation: Any | None = None,
    builder_mutation: Any | None = None,
    current_dp_head: str = FIXED_DP_HEAD,
    audit_next_work: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Path]:
    output_dir = tmp_path / "manifest_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    request = _request_manifest(
        output_dir / "holdout_candidate_request_manifest.json",
        mutation=request_mutation,
    )
    exclusion = _exclusion_manifest(output_dir / "nonoverlap_exclusion_registry_manifest.json")
    expected = _expected_manifest(output_dir / "expected_holdout_artifact_manifest.json")
    runbook = _runbook(output_dir / "holdout_preparation_runbook.sh")
    sha_path = _sha256sums(output_dir / "SHA256SUMS", [request, exclusion, runbook, expected])
    builder = _builder_json(
        tmp_path / "manifest_builder_report.json",
        output_dir=output_dir,
        current_dp_head=current_dp_head,
        mutation=builder_mutation,
    )
    return {
        "manifest_builder_json": builder,
        "manifest_builder_script_py": BUILDER_SCRIPT,
        "manifest_builder_test_py": BUILDER_TEST,
        "request_manifest_json": request,
        "exclusion_manifest_json": exclusion,
        "expected_artifact_manifest_json": expected,
        "holdout_preparation_runbook_sh": runbook,
        "sha256sums": sha_path,
        "v13_audit_md": _audit(tmp_path / "audit.md", next_work=audit_next_work),
    }


def _build(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    paths = _inputs(tmp_path, **kwargs)
    return build_report(
        **paths,
        expected_manifest_builder_json_sha256=_sha256(paths["manifest_builder_json"]),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_manifest_builder_post_static_review_authorizes_data_preparation_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["data_preparation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is True
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["manifest_summary"]["request_count"] == TARGET_HOLDOUT_SELECTION_LOGS
    assert report["manifest_summary"]["formal_seed_overlap"] == []


def test_manifest_builder_post_static_review_rejects_hash_drift(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    report = build_report(
        **paths,
        expected_manifest_builder_json_sha256="0" * 64,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "manifest_builder_json_sha256_matches_expected" in report["final_decision"][
        "failed_checks"
    ]


def test_manifest_builder_post_static_review_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_next_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work_target" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_rejects_builder_data_prep_auth(
    tmp_path: Path,
) -> None:
    def authorize_data_preparation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["data_preparation_authorized_next"] = True

    report = _build(tmp_path, builder_mutation=authorize_data_preparation)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "builder_blocks_data_preparation" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_rejects_formal_seed_request(
    tmp_path: Path,
) -> None:
    def add_formal_seed(payload: dict[str, Any]) -> None:
        payload["route_seed_requests"][0]["seed"] = 11

    report = _build(tmp_path, request_mutation=add_formal_seed)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "request_manifest_no_formal_seeds" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_rejects_target_scale_drift(
    tmp_path: Path,
) -> None:
    def drop_request(payload: dict[str, Any]) -> None:
        payload["route_seed_requests"] = payload["route_seed_requests"][:-1]

    report = _build(tmp_path, request_mutation=drop_request)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "request_manifest_count" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        **_inputs(tmp_path, current_dp_head="0" * 40),
        expected_manifest_builder_json_sha256=_sha256(
            tmp_path / "manifest_builder_report.json"
        ),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_rejects_missing_source_contract(
    tmp_path: Path,
) -> None:
    script = tmp_path / "builder.py"
    script.write_text(BUILDER_SCRIPT.read_text(encoding="utf-8").replace("if not enabled:\n        return report", ""), encoding="utf-8")
    paths = _inputs(tmp_path)
    paths["manifest_builder_script_py"] = script
    report = build_report(
        **paths,
        expected_manifest_builder_json_sha256=_sha256(paths["manifest_builder_json"]),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "builder_returns_before_reads_when_disabled" in report["final_decision"][
        "failed_checks"
    ]


def test_manifest_builder_post_static_review_rejects_missing_test_contract(
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_builder.py"
    test_file.write_text(
        BUILDER_TEST.read_text(encoding="utf-8").replace(
            "test_manifest_builder_rejects_formal_seed_request",
            "test_removed",
        ),
        encoding="utf-8",
    )
    paths = _inputs(tmp_path)
    paths["manifest_builder_test_py"] = test_file
    report = build_report(
        **paths,
        expected_manifest_builder_json_sha256=_sha256(paths["manifest_builder_json"]),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_rejects_formal_seed" in report["final_decision"]["failed_checks"]


def test_manifest_builder_post_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "Data preparation authorized next: `True`" in markdown
    assert "Training authorized next: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This review is read-only" in markdown
    assert "safety/CAMP-over-DP claims" in markdown


def test_manifest_builder_post_static_review_main_writes_outputs(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"

    exit_code = main(
        [
            "--manifest_builder_json",
            str(paths["manifest_builder_json"]),
            "--expected_manifest_builder_json_sha256",
            _sha256(paths["manifest_builder_json"]),
            "--manifest_builder_script_py",
            str(paths["manifest_builder_script_py"]),
            "--manifest_builder_test_py",
            str(paths["manifest_builder_test_py"]),
            "--request_manifest_json",
            str(paths["request_manifest_json"]),
            "--exclusion_manifest_json",
            str(paths["exclusion_manifest_json"]),
            "--expected_artifact_manifest_json",
            str(paths["expected_artifact_manifest_json"]),
            "--holdout_preparation_runbook_sh",
            str(paths["holdout_preparation_runbook_sh"]),
            "--sha256sums",
            str(paths["sha256sums"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "read-only" in output_md.read_text(encoding="utf-8")
