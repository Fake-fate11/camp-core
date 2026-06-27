from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "7e597fe60730b72962a96da2a4cb651a5ef967fb"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_plan(
    *,
    materialized: bool = False,
    materialization_authorized: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1",
        "artifact_manifest_plan": {
            "status": "plan_ready_no_runtime_manifest_materialized",
            "runtime_manifest_schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "materialized_by_this_gate": materialized,
            "selector_mode": "static",
            "candidate_count": 8,
            "atom_count": 14,
            "atom_schema_version": "dp_camp_v10_14d",
            "score_expression": "score_k(w)=a_k^T w",
            "required_runtime_entries": {
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
            "required_evidence_entries": {
                "training_summary": {
                    "path": "/tmp/training_summary.json",
                    "sha256": "3" * 64,
                },
                "fallback_master_config": {
                    "path": "/tmp/fallback_master_config.json",
                    "sha256": "4" * 64,
                },
            },
            "planned_runner_args": [
                "--camp_selector_mode static",
                "--num_candidates 8",
                "--camp_default_off_shadow_selector",
                "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
                "--camp_shadow_expected_atom_scales_sha256 " + "1" * 64,
                "--camp_shadow_expected_static_weights_sha256 " + "2" * 64,
            ],
        },
        "final_decision": {
            "status": "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready",
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only"
            ),
            "artifact_manifest_plan_ready": True,
            "artifact_manifest_static_contract_review_authorized": True,
            "artifact_manifest_materialization_authorized": materialization_authorized,
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
            "user_camp_training_authorized": True,
        },
    }


def _plan_script_source() -> str:
    return '''
SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
"materialized_by_this_gate": False
"required_runtime_entries"
"logical_name": "atom_scales"
"logical_name": "static_weights"
--camp_shadow_artifact_manifest <future_runtime_manifest_json>
default_off_shadow_selector_runtime_execution_authorized
--user_camp_training_authorized
'''


def _plan_test_source() -> str:
    return """
def test_artifact_manifest_plan_ready_without_materializing_runtime_manifest(): pass
def test_artifact_manifest_plan_is_default_off_and_does_not_read_missing_inputs(): pass
def test_artifact_manifest_plan_rejects_weight_simplex_drift(): pass
def test_artifact_manifest_plan_rejects_training_summary_hash_mismatch(): pass
def test_artifact_manifest_plan_rejects_audit_boundary_drift(): pass
"""


def _runner_source() -> str:
    return '''
def _manifest_expected_sha256(): pass
def _shadow_artifact_entry(): pass
logical_name="atom_scales"
logical_name="static_weights"
manifest_missing
hash_mismatch
'''


def _audit_source(*, wrong_target: bool = False) -> str:
    target = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only"
    )
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            target,
            "artifact_manifest_materialization_authorized=False",
            "runtime_shadow_selector_execution_authorized=False",
            "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
            "",
        ]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    materialized: bool = False,
    materialization_authorized: bool = False,
    wrong_audit_target: bool = False,
) -> dict[str, Path]:
    return {
        "artifact_manifest_plan_json": _write_json(
            tmp_path / "artifact_manifest_plan.json",
            _source_plan(
                materialized=materialized,
                materialization_authorized=materialization_authorized,
            ),
        ),
        "artifact_manifest_plan_script_py": _write(
            tmp_path / "plan_script.py",
            _plan_script_source(),
        ),
        "artifact_manifest_plan_test_py": _write(
            tmp_path / "test_plan.py",
            _plan_test_source(),
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


def test_artifact_manifest_static_contract_review_authorizes_only_next_plan(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["artifact_manifest_static_contract_review_complete"] is True
    assert decision["artifact_manifest_materialization_plan_authorized"] is True
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed"] is False
    assert report["contract_summary"]["required_runtime_entries"] == [
        "atom_scales",
        "static_weights",
    ]


def test_artifact_manifest_static_contract_review_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        artifact_manifest_plan_json=missing,
        artifact_manifest_plan_script_py=missing,
        artifact_manifest_plan_test_py=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []


def test_artifact_manifest_static_contract_review_rejects_materialized_source_plan(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, materialized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_materialized_by_this_gate_false" in report["final_decision"]["failed_checks"]


def test_artifact_manifest_static_contract_review_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, materialization_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_materialization_forbidden" in report["final_decision"]["failed_checks"]
    assert (
        "source_plan_artifact_manifest_materialization_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_artifact_manifest_static_contract_review_rejects_audit_target_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, wrong_audit_target=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_current_scope_authorizes_static_review_only"
        in report["final_decision"]["failed_checks"]
    )


def test_artifact_manifest_static_contract_review_cli_writes_review(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--artifact_manifest_plan_json",
            str(paths["artifact_manifest_plan_json"]),
            "--artifact_manifest_plan_script_py",
            str(paths["artifact_manifest_plan_script_py"]),
            "--artifact_manifest_plan_test_py",
            str(paths["artifact_manifest_plan_test_py"]),
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
            "--enable_v13_default_off_shadow_selector_artifact_manifest_static_contract_review",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_artifact_manifest_static_contract_review_v1")
    assert payload["final_decision"]["artifact_manifest_materialization_plan_authorized"] is True
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is False
    assert "static only" in output_md.read_text(encoding="utf-8")
