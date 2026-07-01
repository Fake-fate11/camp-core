from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_manifest_builder_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REGISTRY_REPORT_SCHEMA_VERSION,
    REJECT_STATUS,
    SCOPE_MANIFEST_SCHEMA_VERSION,
    SOURCE_BUILDER_SCHEMA_VERSION,
    SOURCE_BUILDER_STATUS,
    TARGET_RECORDS,
    TARGET_SELECTION_LOGS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "b4a55141b6bc956974d04f0a00c995ef3213da64"
BUILDER_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_manifest.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v13_fresh_evaluation_split_manifest_builder.py"
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scope_manifest(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": SCOPE_MANIFEST_SCHEMA_VERSION,
        "target_selection_log_count": TARGET_SELECTION_LOGS,
        "target_record_count": TARGET_RECORDS,
        "expected_steps_per_log": 100,
        "expected_candidate_count": 8,
        "expected_atom_count": 14,
        "routes_minimum": 4,
        "seeds_minimum": 2,
        "route_traffic_light_buckets_minimum": 8,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": "score_k(w)=a_k^T w",
        "nonnegative_simplex_weights_only": True,
        "fresh_split_members_selected_by_this_builder": False,
        "fresh_split_member_count_selected_by_this_builder": 0,
        "future_preflight_must_prove": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "must_exclude": {
            "formal_seeds_11_12_13": True,
            "full36": True,
            "training_manifest_entries": True,
            "recovered_prior_registry_entries": True,
            "rejected_evaluation_source_registry_entries": True,
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
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _registry_report(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": REGISTRY_REPORT_SCHEMA_VERSION,
        "zero_intersection_proof_executed_by_this_builder": False,
        "future_zero_intersection_preflight_required": True,
        "nonoverlap_requirements_for_future_fresh_split": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "rejected_source_overlap_is_exclusion_evidence": {
            "candidate_hash_intersection_count": 2140,
            "path_signature_intersection_count": 32,
            "record_identity_intersection_count": 3200,
        },
        "forbidden_operations": {
            "fixed_dp_candidate_generation": True,
            "candidate_generation_by_camp": True,
            "trajectory_generation_by_camp": True,
            "trajectory_modification_by_camp": True,
            "reference_blend": True,
            "guidance": True,
            "postprocess_or_postselection": True,
            "closed_loop_outcome_input": True,
            "replay": True,
            "training": True,
            "dp_modification": True,
            "promotion": True,
            "claims": True,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _runbook(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "echo 'validation-only runbook for v13 fresh evaluation split manifests'",
                "sha256sum -c SHA256SUMS.txt",
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
            "fresh_evaluation_split_scope_manifest_sha256": _sha256(
                output_dir / "fresh_evaluation_split_scope_manifest.json"
            ),
            "fresh_evaluation_split_nonoverlap_registry_report_sha256": _sha256(
                output_dir / "fresh_evaluation_split_nonoverlap_registry_report.json"
            ),
            "run_fresh_evaluation_split_preflight_sha256": _sha256(
                output_dir / "run_fresh_evaluation_split_preflight.sh"
            ),
            "sha256sums_txt_sha256": _sha256(output_dir / "SHA256SUMS.txt"),
        },
        "final_decision": {
            "status": SOURCE_BUILDER_STATUS,
            "passed": True,
            "enabled": True,
            "failed_checks": [],
            "manifest_files_written": True,
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "post_implementation_static_contract_review_authorized_next": True,
            "fresh_evaluation_split_manifest_builder_implemented": True,
            "fresh_evaluation_split_members_selected": False,
            "zero_intersection_proof_executed_by_this_gate": False,
            "future_zero_intersection_preflight_required": True,
            "data_preparation_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
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
            "data_preparation_executed": False,
            "fixed_dp_candidate_generation_executed": False,
            "replay_executed": False,
            "training_executed": False,
            "dp_modification_executed": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, next_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.write_text(
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_manifest_builder_complete",
                "post_implementation_static_contract_review_authorized_next=True",
                "data_preparation_authorized_next=False",
                "training_preflight_authorized_next=False",
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
    builder_mutation: Any | None = None,
    scope_mutation: Any | None = None,
    registry_mutation: Any | None = None,
    current_dp_head: str = FIXED_DP_HEAD,
    audit_next_work: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Path]:
    output_dir = tmp_path / "manifest_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    scope = _scope_manifest(
        output_dir / "fresh_evaluation_split_scope_manifest.json",
        mutation=scope_mutation,
    )
    registry = _registry_report(
        output_dir / "fresh_evaluation_split_nonoverlap_registry_report.json",
        mutation=registry_mutation,
    )
    runbook = _runbook(output_dir / "run_fresh_evaluation_split_preflight.sh")
    sha_path = _sha256sums(output_dir / "SHA256SUMS.txt", [scope, registry, runbook])
    builder = _builder_json(
        tmp_path / "fresh_evaluation_split_manifest_builder_report.json",
        output_dir=output_dir,
        current_dp_head=current_dp_head,
        mutation=builder_mutation,
    )
    return {
        "manifest_builder_json": builder,
        "manifest_builder_script_py": BUILDER_SCRIPT,
        "manifest_builder_test_py": BUILDER_TEST,
        "scope_manifest_json": scope,
        "nonoverlap_registry_report_json": registry,
        "preflight_runbook_sh": runbook,
        "sha256sums_txt": sha_path,
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


def test_post_static_review_authorizes_fresh_split_preflight_only(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["fresh_evaluation_split_preflight_authorized_next"] is True
    assert decision["fresh_evaluation_split_member_selection_authorized_next"] is False
    assert decision["data_preparation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["manifest_summary"]["target_selection_log_count"] == TARGET_SELECTION_LOGS
    assert report["manifest_summary"]["future_zero_intersection_preflight_required"] is True


def test_post_static_review_rejects_hash_drift(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    report = build_report(
        **paths,
        expected_manifest_builder_json_sha256="0" * 64,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "manifest_builder_json_sha256_matches_expected" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_next_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work_target" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_builder_data_prep_auth(tmp_path: Path) -> None:
    def authorize_data_prep(payload: dict[str, Any]) -> None:
        payload["final_decision"]["data_preparation_authorized_next"] = True

    report = _build(tmp_path, builder_mutation=authorize_data_prep)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "builder_blocks_data_preparation_authorized_next" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_scope_execution_request(tmp_path: Path) -> None:
    def request_replay(payload: dict[str, Any]) -> None:
        payload["executions_requested_by_this_manifest"]["replay"] = True

    report = _build(tmp_path, scope_mutation=request_replay)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "scope_requests_no_replay" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_missing_future_zero_proof_requirement(
    tmp_path: Path,
) -> None:
    def remove_requirement(payload: dict[str, Any]) -> None:
        payload["nonoverlap_requirements_for_future_fresh_split"][
            "record_identity_intersection_count"
        ] = 1

    report = _build(tmp_path, registry_mutation=remove_requirement)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "registry_future_requires_zero_record_identity_intersection_count"
        in report["final_decision"]["failed_checks"]
    )


def test_post_static_review_rejects_dp_head_drift(tmp_path: Path) -> None:
    paths = _inputs(tmp_path, current_dp_head="0" * 40)
    report = build_report(
        **paths,
        expected_manifest_builder_json_sha256=_sha256(paths["manifest_builder_json"]),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_missing_source_contract(tmp_path: Path) -> None:
    script = tmp_path / "builder.py"
    script.write_text(
        BUILDER_SCRIPT.read_text(encoding="utf-8").replace(
            "if not enabled:\n        return report",
            "",
        ),
        encoding="utf-8",
    )
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
    assert "builder_returns_before_reads_when_disabled" in report["final_decision"]["failed_checks"]


def test_post_static_review_rejects_missing_test_contract(tmp_path: Path) -> None:
    test_file = tmp_path / "test_builder.py"
    test_file.write_text(
        BUILDER_TEST.read_text(encoding="utf-8").replace(
            "test_manifest_builder_rejects_formal_seed_in_training_manifest",
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


def test_post_static_review_markdown_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "Fresh split preflight authorized next: `True`" in markdown
    assert "Training authorized next: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This review is read-only" in markdown
    assert "safety/CAMP-over-DP claims" in markdown


def test_post_static_review_main_writes_outputs(tmp_path: Path) -> None:
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
            "--scope_manifest_json",
            str(paths["scope_manifest_json"]),
            "--nonoverlap_registry_report_json",
            str(paths["nonoverlap_registry_report_json"]),
            "--preflight_runbook_sh",
            str(paths["preflight_runbook_sh"]),
            "--sha256sums_txt",
            str(paths["sha256sums_txt"]),
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


def test_post_static_review_script_has_cli_entrypoint() -> None:
    source = (
        REPO_ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_manifest_builder_post_implementation_static_contract.py"
    ).read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source
