from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "8bdd4d348df428944302489cc8a991f518d42c52"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _materialization_plan(
    planned_manifest: Path,
    *,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    candidate_count: int = 8,
    runtime_authorized: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"
        ),
        "materialization_plan": {
            "status": "plan_ready_no_runtime_manifest_written",
            "planned_runtime_manifest_path": str(planned_manifest),
            "this_plan_is_runtime_manifest": False,
            "runtime_manifest_written_by_this_gate": False,
            "runtime_execution_enabled_by_this_gate": False,
            "future_manifest_required_content": {
                "schema_version": runtime_schema,
                "default_off": True,
                "selection_effect": False,
                "selector_mode": "static",
                "candidate_operation": "fixed DP candidate reranking only",
                "executed_output_policy": "dp_top1",
                "required_candidate_count": candidate_count,
                "atom_count": 14,
                "atom_schema_version": "dp_camp_v10_14d",
                "score_expression": "score_k(w)=a_k^T w",
                "required_dp_head": FIXED_DP_HEAD,
                "artifacts": {
                    "atom_scales": {
                        "logical_name": "atom_scales",
                        "path": "/tmp/atom_scales.json",
                        "sha256": "1" * 64,
                    },
                    "static_weights": {
                        "logical_name": "static_weights",
                        "path": "/tmp/weights.npy",
                        "sha256": "2" * 64,
                    },
                },
                "sha256": {
                    "atom_scales": "1" * 64,
                    "static_weights": "2" * 64,
                },
            },
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready"
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
            "production_selector_change_authorized": False,
        },
    }


def _materializer_source(*, dangerous: bool = False, missing_enable: bool = False) -> str:
    text = '''
SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_manifest_materializer_v1"
runtime_artifact_manifest_materializer_default_off_disabled
--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer
if not enabled:
materialization_plan_sha256_matches_expected
output_path_matches_source_plan
output_runtime_manifest_absent_before_write
atom_scales_sha256_matches
static_weights_sha256_matches
output_runtime_manifest_json.write_text
dp_camp_v13_default_off_shadow_selector_runtime_v1
fixed DP candidate reranking only
score_k(w)=a_k^T w
dp_top1
"authorizations"
"default_off_shadow_selector_runtime_execution_authorized": False
"training_executed": False
'''
    if missing_enable:
        text = text.replace(
            "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer",
            "missing_enable_flag",
        )
    if dangerous:
        text += "\nimport subprocess\nrun_diffusion_planner\n"
    return text


def _materializer_test_source(*, missing_hash_test: bool = False) -> str:
    tests = [
        "test_materializer_is_default_off_and_does_not_read_missing_inputs",
        "test_materializer_writes_exact_runtime_manifest_shape_when_enabled",
        "test_materializer_rejects_plan_hash_mismatch_without_output",
        "test_materializer_rejects_artifact_hash_mismatch_without_output",
        "test_materializer_rejects_dp_head_drift_without_output",
        "test_materializer_rejects_output_path_drift_without_output",
        "test_materializer_rejects_existing_output_without_overwrite",
        "test_materializer_rejects_schema_or_candidate_count_drift_without_output",
        "test_materializer_rejects_runtime_or_promotion_authorization_leaks",
        "test_materializer_does_not_run_replay_or_touch_dp_sources",
        "test_materializer_cli_writes_manifest",
    ]
    if missing_hash_test:
        tests.remove("test_materializer_rejects_artifact_hash_mismatch_without_output")
    return "\n".join(f"def {name}(): pass" for name in tests)


def _runner_source() -> str:
    return '''
def _load_shadow_artifact_manifest(): pass
def _manifest_expected_sha256(): pass
artifacts = manifest.get("artifacts")
hashes = manifest.get("sha256")
logical_name="atom_scales"
logical_name="static_weights"
"executed_output_policy": "dp_top1"
"selection_effect": False
'''


def _audit_source(*, wrong_target: bool = False) -> str:
    target = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only"
    )
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            target,
            "artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True",
            "artifact_manifest_materialization_authorized=False",
            "runtime_shadow_selector_execution_authorized=False",
            "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
            "",
        ]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    manifest_exists: bool = False,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    candidate_count: int = 8,
    runtime_authorized: bool = False,
    dangerous_materializer: bool = False,
    missing_enable: bool = False,
    missing_hash_test: bool = False,
    wrong_audit_target: bool = False,
) -> dict[str, Path]:
    planned_manifest = tmp_path / "runtime_manifest.json"
    if manifest_exists:
        planned_manifest.write_text("{}", encoding="utf-8")
    return {
        "artifact_manifest_materialization_plan_json": _write_json(
            tmp_path / "materialization_plan.json",
            _materialization_plan(
                planned_manifest,
                runtime_schema=runtime_schema,
                candidate_count=candidate_count,
                runtime_authorized=runtime_authorized,
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
        "replay_runner_py": _write(tmp_path / "runner.py", _runner_source()),
        "v13_audit_md": _write(tmp_path / "audit.md", _audit_source(wrong_target=wrong_audit_target)),
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
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["artifact_manifest_materialization_authorized"] is True
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["training_executed"] is False


def test_post_implementation_static_review_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        artifact_manifest_materialization_plan_json=missing,
        materializer_script_py=missing,
        materializer_test_py=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
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


def test_post_implementation_static_review_rejects_missing_focused_test(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_hash_test=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_artifact_hash_mismatch" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_materialization_plan_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, runtime_schema="wrong_schema", candidate_count=9)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_schema" in report["final_decision"]["failed_checks"]
    assert "future_manifest_candidate_count" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_runtime_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, runtime_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "materialization_plan_default_off_shadow_selector_runtime_execution_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_post_implementation_static_review_rejects_audit_target_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, wrong_audit_target=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_current_scope_authorizes_this_review" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_cli_writes_review(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--artifact_manifest_materialization_plan_json",
            str(paths["artifact_manifest_materialization_plan_json"]),
            "--materializer_script_py",
            str(paths["materializer_script_py"]),
            "--materializer_test_py",
            str(paths["materializer_test_py"]),
            "--replay_runner_py",
            str(paths["replay_runner_py"]),
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
            "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_post_implementation_static_contract_review_v1")
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is True
    assert payload["final_decision"]["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert "static only" in output_md.read_text(encoding="utf-8")
