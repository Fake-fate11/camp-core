from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    FUTURE_MATERIALIZER,
    FUTURE_UNIT_TEST,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "27b9355a8d03c25d8095814800c3d9b6a45f5db5"


REQUIRED_STEPS = [
    "remain default-off and do not read source plan or artifact files unless enable flag is present",
    "load exactly one materialization plan JSON and verify its expected SHA256",
    "verify current DP head equals the fixed TiERIV Diffusion Planner commit",
    "verify planned output path equals materialization_plan.planned_runtime_manifest_path",
    "verify atom_scales and static_weights files exist and match planned SHA256 before writing",
    "write exactly one JSON runtime manifest with schema dp_camp_v13_default_off_shadow_selector_runtime_v1",
    "include artifacts and sha256 aliases for logical names, absolute paths, and basenames",
    "write no replay logs, no candidate artifacts, no weights, and no DP files",
    "fail closed without output on any missing file, hash mismatch, K drift, schema drift, or DP head drift",
]

FUTURE_TESTS = [
    "test_materializer_is_default_off_and_does_not_read_missing_inputs",
    "test_materializer_writes_exact_runtime_manifest_shape_when_enabled",
    "test_materializer_rejects_hash_mismatch_without_output",
    "test_materializer_rejects_dp_head_drift_without_output",
    "test_materializer_rejects_runtime_or_promotion_authorization_leaks",
    "test_materializer_does_not_run_replay_or_touch_dp_sources",
]


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_plan(
    *,
    static_review_authorized: bool = True,
    implementation_authorized: bool = False,
    materializer_implemented: bool = False,
    runtime_written: bool = False,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    runtime_entries: list[str] | None = None,
    drop_step: str | None = None,
    drop_future_test: str | None = None,
) -> dict[str, Any]:
    steps = [step for step in REQUIRED_STEPS if step != drop_step]
    future_tests = [test for test in FUTURE_TESTS if test != drop_future_test]
    return {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_v1"
        ),
        "source_summary": {
            "runtime_manifest_schema_version": runtime_schema,
            "runtime_entries": runtime_entries or ["atom_scales", "static_weights"],
        },
        "implementation_plan": {
            "status": "plan_ready_no_materializer_implemented",
            "future_materializer_script": FUTURE_MATERIALIZER,
            "future_materializer_test": FUTURE_UNIT_TEST,
            "planned_runtime_manifest_path": "/tmp/future_runtime_manifest.json",
            "materializer_implemented_by_this_gate": materializer_implemented,
            "runtime_manifest_written_by_this_gate": runtime_written,
            "runtime_execution_enabled_by_this_gate": False,
            "future_cli_contract": [
                "--artifact_manifest_materialization_plan_json",
                "--expected_materialization_plan_sha256",
                "--output_runtime_manifest_json",
                "--current_camp_head",
                "--current_dp_head",
                "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer",
            ],
            "required_implementation_steps": steps,
            "future_manifest_entries": {
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
            "future_unit_tests": future_tests,
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only"
            ),
            "artifact_manifest_materialization_implementation_plan_ready": True,
            "artifact_manifest_materialization_implementation_static_contract_review_authorized": static_review_authorized,
            "artifact_manifest_materialization_implementation_authorized": implementation_authorized,
            "artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
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
            "training_executed": False,
        },
    }


def _script_source() -> str:
    return f'''
SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_v1"
{FUTURE_MATERIALIZER}
{FUTURE_UNIT_TEST}
dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only
"materializer_implemented_by_this_gate": False
"runtime_manifest_written_by_this_gate": False
verify atom_scales and static_weights files exist and match planned SHA256 before writing
'''


def _test_source() -> str:
    return """
def test_materialization_implementation_plan_ready_but_does_not_implement(): pass
def test_materialization_implementation_plan_is_default_off(): pass
def test_materialization_implementation_plan_rejects_source_review_gate_drift(): pass
def test_materialization_implementation_plan_rejects_runtime_schema_drift(): pass
def test_materialization_implementation_plan_rejects_dp_head_drift(): pass
"""


def _runner_source() -> str:
    return '''
def _load_shadow_artifact_manifest(): pass
def _manifest_expected_sha256(): pass
artifacts = manifest.get("artifacts")
hashes = manifest.get("sha256")
logical_name="atom_scales"
logical_name="static_weights"
'''


def _audit_source(*, wrong_target: bool = False) -> str:
    target = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only"
    )
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            target,
            "artifact_manifest_materialization_implementation_static_contract_review_authorized=True",
            "artifact_manifest_materialization_implementation_authorized=False",
            "artifact_manifest_materialization_authorized=False",
            "runtime_shadow_selector_execution_authorized=False",
            "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
            "",
        ]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    static_review_authorized: bool = True,
    implementation_authorized: bool = False,
    materializer_implemented: bool = False,
    runtime_written: bool = False,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    runtime_entries: list[str] | None = None,
    drop_step: str | None = None,
    drop_future_test: str | None = None,
    wrong_audit_target: bool = False,
) -> dict[str, Path]:
    return {
        "artifact_manifest_materialization_implementation_plan_json": _write_json(
            tmp_path / "implementation_plan.json",
            _source_plan(
                static_review_authorized=static_review_authorized,
                implementation_authorized=implementation_authorized,
                materializer_implemented=materializer_implemented,
                runtime_written=runtime_written,
                runtime_schema=runtime_schema,
                runtime_entries=runtime_entries,
                drop_step=drop_step,
                drop_future_test=drop_future_test,
            ),
        ),
        "artifact_manifest_materialization_implementation_plan_script_py": _write(
            tmp_path / "implementation_plan.py",
            _script_source(),
        ),
        "artifact_manifest_materialization_implementation_plan_test_py": _write(
            tmp_path / "test_implementation_plan.py",
            _test_source(),
        ),
        "replay_runner_py": _write(tmp_path / "runner.py", _runner_source()),
        "v13_audit_md": _write(
            tmp_path / "audit.md",
            _audit_source(wrong_target=wrong_audit_target),
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


def test_implementation_static_review_authorizes_only_materializer_implementation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "artifact_manifest_materialization_implementation_static_contract_review_complete"
        ]
        is True
    )
    assert decision["artifact_manifest_materialization_implementation_authorized"] is True
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed"] is False


def test_implementation_static_review_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        artifact_manifest_materialization_implementation_plan_json=missing,
        artifact_manifest_materialization_implementation_plan_script_py=missing,
        artifact_manifest_materialization_implementation_plan_test_py=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []


def test_implementation_static_review_rejects_source_plan_gate_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, static_review_authorized=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_static_review_authorized" in report["final_decision"]["failed_checks"]


def test_implementation_static_review_rejects_prior_implementation_authorization(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, implementation_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_plan_implementation_not_yet_authorized"
        in report["final_decision"]["failed_checks"]
    )


def test_implementation_static_review_rejects_materializer_or_manifest_written_flag(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, materializer_implemented=True, runtime_written=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_materializer_not_implemented" in report["final_decision"]["failed_checks"]
    assert "source_plan_runtime_manifest_not_written" in report["final_decision"]["failed_checks"]


def test_implementation_static_review_rejects_missing_required_step(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        drop_step=(
            "fail closed without output on any missing file, hash mismatch, K drift, schema drift, or DP head drift"
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_step_fail_closed" in report["final_decision"]["failed_checks"]


def test_implementation_static_review_rejects_missing_future_unit_test(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        drop_future_test="test_materializer_rejects_runtime_or_promotion_authorization_leaks",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_test_authorization_leak" in report["final_decision"]["failed_checks"]


def test_implementation_static_review_rejects_runtime_contract_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, runtime_schema="wrong_schema", runtime_entries=["atom_scales"])

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_summary_runtime_schema" in report["final_decision"]["failed_checks"]
    assert "source_summary_runtime_entries" in report["final_decision"]["failed_checks"]


def test_implementation_static_review_rejects_audit_target_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, wrong_audit_target=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_current_scope_authorizes_implementation_static_review_only"
        in report["final_decision"]["failed_checks"]
    )


def test_implementation_static_review_cli_writes_review(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--artifact_manifest_materialization_implementation_plan_json",
            str(paths["artifact_manifest_materialization_implementation_plan_json"]),
            "--artifact_manifest_materialization_implementation_plan_script_py",
            str(paths["artifact_manifest_materialization_implementation_plan_script_py"]),
            "--artifact_manifest_materialization_implementation_plan_test_py",
            str(paths["artifact_manifest_materialization_implementation_plan_test_py"]),
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
            "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_implementation_static_contract_review_v1")
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert payload["final_decision"]["artifact_manifest_materialization_implementation_authorized"] is True
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is False
    assert "static only" in output_md.read_text(encoding="utf-8")
