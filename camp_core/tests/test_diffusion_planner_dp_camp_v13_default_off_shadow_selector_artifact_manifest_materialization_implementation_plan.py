from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation import (
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


CAMP_HEAD = "b8164c645683391374faf4523d3b4e84e27296d0"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_review(*, implementation_plan_authorized: bool = True) -> dict[str, Any]:
    return {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_v1"
        ),
        "contract_summary": {
            "planned_runtime_manifest_exists": False,
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_complete"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only"
            ),
            "artifact_manifest_materialization_static_contract_review_complete": True,
            "artifact_manifest_materialization_implementation_plan_authorized": implementation_plan_authorized,
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


def _source_plan(
    *,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    required_dp_head: str = FIXED_DP_HEAD,
    atom_logical_name: str = "atom_scales",
) -> dict[str, Any]:
    return {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"
        ),
        "materialization_plan": {
            "status": "plan_ready_no_runtime_manifest_written",
            "planned_runtime_manifest_path": "/tmp/future_runtime_manifest.json",
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
                "required_candidate_count": 8,
                "atom_count": 14,
                "atom_schema_version": "dp_camp_v10_14d",
                "score_expression": "score_k(w)=a_k^T w",
                "required_dp_head": required_dp_head,
                "artifacts": {
                    "atom_scales": {
                        "logical_name": atom_logical_name,
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
    }


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
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only"
    )
    if wrong_target:
        target = "next_work_target=old_scope"
    return "\n".join(
        [
            target,
            "artifact_manifest_materialization_implementation_plan_authorized=True",
            "artifact_manifest_materialization_authorized=False",
            "runtime_shadow_selector_execution_authorized=False",
            "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
            "",
        ]
    )


def _write_inputs(
    tmp_path: Path,
    *,
    implementation_plan_authorized: bool = True,
    runtime_schema: str = "dp_camp_v13_default_off_shadow_selector_runtime_v1",
    required_dp_head: str = FIXED_DP_HEAD,
    atom_logical_name: str = "atom_scales",
    wrong_audit_target: bool = False,
) -> dict[str, Path]:
    return {
        "artifact_manifest_materialization_static_review_json": _write_json(
            tmp_path / "static_review.json",
            _source_review(implementation_plan_authorized=implementation_plan_authorized),
        ),
        "artifact_manifest_materialization_plan_json": _write_json(
            tmp_path / "materialization_plan.json",
            _source_plan(
                runtime_schema=runtime_schema,
                required_dp_head=required_dp_head,
                atom_logical_name=atom_logical_name,
            ),
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


def test_materialization_implementation_plan_ready_but_does_not_implement(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["artifact_manifest_materialization_implementation_plan_ready"] is True
    assert (
        decision[
            "artifact_manifest_materialization_implementation_static_contract_review_authorized"
        ]
        is True
    )
    assert decision["artifact_manifest_materialization_implementation_authorized"] is False
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed"] is False
    assert plan["future_materializer_script"] == FUTURE_MATERIALIZER
    assert plan["future_materializer_test"] == FUTURE_UNIT_TEST
    assert plan["materializer_implemented_by_this_gate"] is False
    assert plan["runtime_manifest_written_by_this_gate"] is False


def test_materialization_implementation_plan_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        artifact_manifest_materialization_static_review_json=missing,
        artifact_manifest_materialization_plan_json=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["plan_checks"] == []


def test_materialization_implementation_plan_rejects_source_review_gate_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, implementation_plan_authorized=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_review_implementation_plan_authorized"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_implementation_plan_rejects_runtime_schema_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, runtime_schema="wrong_schema")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_schema" in report["final_decision"]["failed_checks"]


def test_materialization_implementation_plan_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, required_dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_required_dp_head" in report["final_decision"]["failed_checks"]


def test_materialization_implementation_plan_rejects_logical_name_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, atom_logical_name="wrong_atom_scales")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_atom_entry_logical_name" in report["final_decision"]["failed_checks"]


def test_materialization_implementation_plan_rejects_audit_target_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, wrong_audit_target=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_current_scope_authorizes_implementation_plan_only"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_implementation_plan_cli_writes_plan(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--artifact_manifest_materialization_static_review_json",
            str(paths["artifact_manifest_materialization_static_review_json"]),
            "--artifact_manifest_materialization_plan_json",
            str(paths["artifact_manifest_materialization_plan_json"]),
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
            "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_artifact_manifest_materialization_implementation_plan_v1")
    assert payload["implementation_plan"]["materializer_implemented_by_this_gate"] is False
    assert payload["implementation_plan"]["runtime_manifest_written_by_this_gate"] is False
    assert payload["final_decision"]["artifact_manifest_materialization_implementation_authorized"] is False
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is False
    assert "plan-only" in output_md.read_text(encoding="utf-8")
