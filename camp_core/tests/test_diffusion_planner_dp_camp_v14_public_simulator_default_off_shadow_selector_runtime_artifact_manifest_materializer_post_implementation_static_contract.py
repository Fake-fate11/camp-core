from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "98de7455afa80cd8533d7f220e75fb422a8c83fe"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _implementation_plan(
    planned_manifest: Path,
    *,
    runtime_schema: str = "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
    candidate_count: int = 8,
    runtime_authorized: bool = False,
    promotion_claim: bool = False,
) -> dict[str, Any]:
    atom_path = planned_manifest.parent / "atom_scales_dp_static.json"
    weights_path = planned_manifest.parent / "offline_weights_dp_static.npy"
    atom_sha = "1" * 64
    weights_sha = "2" * 64
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_default_off_shadow_selector_"
            "runtime_artifact_manifest_materialization_implementation_plan_v1"
        ),
        "implementation_plan": {
            "runtime_manifest_written_by_this_gate": False,
            "runtime_manifest_materialized_by_this_gate": False,
            "runtime_execution_enabled_by_this_gate": False,
            "future_materializer_contract": {
                "write_strategy": "same-directory temp file plus atomic replace",
                "writes_exactly_one_runtime_manifest": True,
                "planned_output_path": str(planned_manifest),
                "required_dp_head": FIXED_DP_HEAD,
                "manifest_required_content": {
                    "schema_version": runtime_schema,
                    "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
                    "source_scope": "public_simulator_fixed_dp_candidate_tensor",
                    "default_off": True,
                    "fail_closed": True,
                    "selection_effect": False,
                    "online_selector_change": False,
                    "selector_mode": "static",
                    "candidate_operation": "fixed DP candidate reranking only",
                    "executed_output_policy": "dp_top1",
                    "required_candidate_count": candidate_count,
                    "atom_count": 9,
                    "atom_schema_version": "camp_legacy_v1_9d",
                    "score_expression": "score_k(w)=a_k^T w",
                    "forbidden_runtime_claims": {
                        "selector_promotion_authorized": promotion_claim,
                        "atom_promotion_authorized": False,
                        "deployment_authorized": False,
                        "safety_benefit_claim_authorized": False,
                        "camp_over_dp_top1_claim_authorized": False,
                    },
                    "artifacts": {
                        "atom_scales": {
                            "logical_name": "atom_scales",
                            "path": str(atom_path),
                            "sha256": atom_sha,
                            "required": True,
                        },
                        "static_weights": {
                            "logical_name": "static_weights",
                            "path": str(weights_path),
                            "sha256": weights_sha,
                            "required": True,
                        },
                    },
                    "sha256": {
                        "atom_scales": atom_sha,
                        atom_path.name: atom_sha,
                        str(atom_path): atom_sha,
                        "static_weights": weights_sha,
                        weights_path.name: weights_sha,
                        str(weights_path): weights_sha,
                    },
                },
            },
        },
        "final_decision": {
            "status": (
                "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
                "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
                "manifest_materialization_implementation_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "default_off_shadow_selector_runtime_execution_authorized": runtime_authorized,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
        },
    }


def _materializer_source(*, dangerous: bool = False, missing_enable: bool = False) -> str:
    text = '''
SCHEMA_VERSION = "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_v1"
SOURCE_PLAN_SCHEMA_VERSION = "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_v1"
runtime_artifact_manifest_materializer_default_off_disabled
--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer
if not enabled:
implementation_plan_sha256_matches_expected
output_path_matches_source_plan
output_runtime_manifest_absent_before_write
current_dp_head_fixed
_expect(f"{logical_name}_sha256_matches"
("atom_scales", "static_weights")
_atomic_write_json
os.replace
os.fsync
dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1
public_simulator_fixed_dp_candidate_tensor
"fail_closed": True
fixed DP candidate reranking only
score_k(w)=a_k^T w
dp_top1
"authorizations"
"default_off_shadow_selector_runtime_execution_authorized": False
"runtime_artifact_manifest_materialization_authorized": False
"training_executed": False
'''
    if missing_enable:
        text = text.replace(
            "--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer",
            "missing_enable",
        )
    if dangerous:
        text += "\nsubprocess\nrun_diffusion_planner\nDiffusion-Planner\n"
    return text


def _materializer_test_source(*, missing_hash_test: bool = False) -> str:
    tests = [
        "test_materializer_is_default_off_and_does_not_read_missing_inputs",
        "test_materializer_writes_exact_runtime_manifest_shape_when_enabled",
        "test_materializer_rejects_plan_hash_mismatch_without_output",
        "test_materializer_rejects_hash_mismatch_without_output",
        "test_materializer_rejects_dp_head_drift_without_output",
        "test_materializer_rejects_output_path_drift_without_output",
        "test_materializer_rejects_existing_output_without_overwrite",
        "test_materializer_rejects_schema_or_candidate_count_drift_without_output",
        "test_materializer_rejects_runtime_or_promotion_authorization_leaks",
        "test_materializer_uses_same_directory_temp_and_atomic_replace",
        "test_materializer_does_not_run_replay_train_or_touch_dp_sources",
        "test_materializer_cli_writes_manifest",
    ]
    if missing_hash_test:
        tests.remove("test_materializer_rejects_hash_mismatch_without_output")
    return "\n".join(f"def {name}(): pass" for name in tests)


def _audit_text(*, wrong_target: bool = False) -> str:
    target = f"next_work_target={AUTHORIZED_CURRENT_WORK}"
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            target,
            "runtime_artifact_manifest_materializer_implementation_complete=True",
            "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True",
            "runtime_artifact_manifest_materialization_authorized=False",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "candidate_generation_by_camp_authorized_by_current_boundary=False",
            "dp_modification_authorized_by_current_boundary=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
        ]
    )


def _current_status_text(*, wrong_target: bool = False) -> str:
    target = f"next_work_target={AUTHORIZED_CURRENT_WORK}"
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete",
            target,
            "does not materialize the real planned runtime manifest",
            "post-implementation static contract review only",
        ]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    manifest_exists: bool = False,
    runtime_schema: str = "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
    candidate_count: int = 8,
    runtime_authorized: bool = False,
    promotion_claim: bool = False,
    dangerous_materializer: bool = False,
    missing_enable: bool = False,
    missing_hash_test: bool = False,
    wrong_audit_target: bool = False,
    wrong_status_target: bool = False,
) -> dict[str, Path]:
    planned_manifest = tmp_path / "planned_runtime" / "runtime_manifest.json"
    if manifest_exists:
        _write(planned_manifest, "{}\n")
    return {
        "runtime_artifact_manifest_materialization_implementation_plan_json": _write_json(
            tmp_path / "implementation_plan.json",
            _implementation_plan(
                planned_manifest,
                runtime_schema=runtime_schema,
                candidate_count=candidate_count,
                runtime_authorized=runtime_authorized,
                promotion_claim=promotion_claim,
            ),
        ),
        "materializer_script_py": _write(
            tmp_path / "materializer.py",
            _materializer_source(dangerous=dangerous_materializer, missing_enable=missing_enable),
        ),
        "materializer_test_py": _write(
            tmp_path / "test_materializer.py",
            _materializer_test_source(missing_hash_test=missing_hash_test),
        ),
        "v14_audit_md": _write(tmp_path / "audit.md", _audit_text(wrong_target=wrong_audit_target)),
        "current_status_md": _write(
            tmp_path / "current_status.md",
            _current_status_text(wrong_target=wrong_status_target),
        ),
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_write_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )


def test_post_implementation_static_review_authorizes_only_manifest_materialization(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed"] is True
    assert decision["runtime_artifact_manifest_materialization_authorized"] is True
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["training_executed"] is False


def test_post_implementation_static_review_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        runtime_artifact_manifest_materialization_implementation_plan_json=missing,
        materializer_script_py=missing,
        materializer_test_py=missing,
        v14_audit_md=missing,
        current_status_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []


def test_post_implementation_static_review_rejects_existing_runtime_manifest(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, manifest_exists=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_runtime_manifest_absent_now" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_materializer_contract_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_enable=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "materializer_enable_flag" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_dangerous_materializer_source(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, dangerous_materializer=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "materializer_no_subprocess" in report["final_decision"]["failed_checks"]
    assert "materializer_no_replay_runner" in report["final_decision"]["failed_checks"]
    assert "materializer_no_dp_repo_token" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_missing_focused_test(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_hash_test=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_artifact_hash_mismatch" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_source_plan_drift(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        runtime_schema="wrong_schema",
        candidate_count=9,
        promotion_claim=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_schema" in report["final_decision"]["failed_checks"]
    assert "future_manifest_candidate_count" in report["final_decision"]["failed_checks"]
    assert "future_manifest_selector_promotion_authorized_false" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_runtime_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, runtime_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_plan_default_off_shadow_selector_runtime_execution_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_post_implementation_static_review_rejects_audit_or_status_target_drift(
    tmp_path: Path,
) -> None:
    audit_report = _report(tmp_path / "audit", wrong_audit_target=True)
    status_report = _report(tmp_path / "status", wrong_status_target=True)

    assert audit_report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_current_scope_authorizes_this_review" in audit_report["final_decision"]["failed_checks"]
    assert status_report["final_decision"]["status"] == REJECT_STATUS
    assert "current_status_next_target" in status_report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_cli_writes_review(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--runtime_artifact_manifest_materialization_implementation_plan_json",
            str(paths["runtime_artifact_manifest_materialization_implementation_plan_json"]),
            "--materializer_script_py",
            str(paths["materializer_script_py"]),
            "--materializer_test_py",
            str(paths["materializer_test_py"]),
            "--v14_audit_md",
            str(paths["v14_audit_md"]),
            "--current_status_md",
            str(paths["current_status_md"]),
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
            "--enable_v14_public_simulator_runtime_artifact_manifest_materializer_post_implementation_static_contract_review",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_post_implementation_static_contract_review_v1")
    assert payload["final_decision"]["runtime_artifact_manifest_materialization_authorized"] is True
    assert payload["final_decision"]["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert "static only" in output_md.read_text(encoding="utf-8")
