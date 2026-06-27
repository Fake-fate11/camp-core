from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "842b3935d4cc7bd5f2e8b77854d6390828fad333"
PLANNED_MANIFEST = "/tmp/dp_camp_v13_shadow_artifact_manifest_runtime.json"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_review(*, materialization_authorized: bool = False) -> dict[str, Any]:
    return {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_v1"
        ),
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_complete"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only"
            ),
            "artifact_manifest_static_contract_review_complete": True,
            "artifact_manifest_materialization_plan_authorized": True,
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
        },
    }


def _source_plan(*, logical_name_drift: bool = False) -> dict[str, Any]:
    atom_logical = "wrong_atom_scales" if logical_name_drift else "atom_scales"
    return {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1",
        "artifact_manifest_plan": {
            "status": "plan_ready_no_runtime_manifest_materialized",
            "runtime_manifest_schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "materialized_by_this_gate": False,
            "selector_mode": "static",
            "candidate_count": 8,
            "atom_count": 14,
            "atom_schema_version": "dp_camp_v10_14d",
            "score_expression": "score_k(w)=a_k^T w",
            "required_runtime_entries": {
                "atom_scales": {
                    "logical_name": atom_logical,
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
            ],
        },
        "final_decision": {
            "status": "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready",
            "passed": True,
            "failed_checks": [],
            "artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
        },
    }


def _runner_source() -> str:
    return '''
def _load_shadow_artifact_manifest(): pass
def _manifest_expected_sha256(): pass
artifacts = manifest.get("artifacts")
hashes = manifest.get("sha256")
logical_name="atom_scales"
logical_name="static_weights"
hash_mismatch
'''


def _audit_source(*, wrong_target: bool = False) -> str:
    target = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only"
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
    materialization_authorized: bool = False,
    logical_name_drift: bool = False,
    wrong_audit_target: bool = False,
) -> dict[str, Path]:
    return {
        "artifact_manifest_static_contract_review_json": _write_json(
            tmp_path / "static_review.json",
            _source_review(materialization_authorized=materialization_authorized),
        ),
        "artifact_manifest_plan_json": _write_json(
            tmp_path / "artifact_plan.json",
            _source_plan(logical_name_drift=logical_name_drift),
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
        planned_runtime_manifest_path=PLANNED_MANIFEST,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )


def test_materialization_plan_ready_but_does_not_write_runtime_manifest(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["materialization_plan"]
    future = plan["future_manifest_required_content"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["artifact_manifest_materialization_plan_ready"] is True
    assert decision["artifact_manifest_materialization_static_contract_review_authorized"] is True
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed"] is False
    assert plan["runtime_manifest_written_by_this_gate"] is False
    assert plan["this_plan_is_runtime_manifest"] is False
    assert future["schema_version"] == "dp_camp_v13_default_off_shadow_selector_runtime_v1"
    assert future["selection_effect"] is False
    assert future["executed_output_policy"] == "dp_top1"
    assert future["sha256"]["atom_scales"] == "1" * 64
    assert future["sha256"]["static_weights"] == "2" * 64


def test_materialization_plan_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        artifact_manifest_static_contract_review_json=missing,
        artifact_manifest_plan_json=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        planned_runtime_manifest_path=PLANNED_MANIFEST,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["plan_checks"] == []


def test_materialization_plan_rejects_source_review_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, materialization_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_materialization_forbidden" in report["final_decision"]["failed_checks"]
    assert (
        "source_review_artifact_manifest_materialization_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_plan_rejects_source_plan_logical_name_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, logical_name_drift=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_atom_scales_logical_name" in report["final_decision"]["failed_checks"]


def test_materialization_plan_rejects_audit_target_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_audit_target=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_current_scope_authorizes_materialization_plan_only"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_plan_cli_writes_plan_not_runtime_manifest(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "materialization_plan.json"
    output_md = tmp_path / "materialization_plan.md"

    exit_code = main(
        [
            "--artifact_manifest_static_contract_review_json",
            str(paths["artifact_manifest_static_contract_review_json"]),
            "--artifact_manifest_plan_json",
            str(paths["artifact_manifest_plan_json"]),
            "--replay_runner_py",
            str(paths["replay_runner_py"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
            "--planned_runtime_manifest_path",
            PLANNED_MANIFEST,
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
            "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_plan",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_artifact_manifest_materialization_plan_v1")
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is False
    assert payload["materialization_plan"]["this_plan_is_runtime_manifest"] is False
    assert payload["materialization_plan"]["runtime_manifest_written_by_this_gate"] is False
    assert "plan-only" in output_md.read_text(encoding="utf-8")
