from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization.py"
)
SOURCE_HEAD = "5" * 40
CURRENT_HEAD = "6" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actual_safetycost_outcome_materialization_preflight_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_ready"
        ]
        is True
    )
    assert (
        decision[
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_static_review_authorized"
        ]
        is True
    )
    assert decision["actual_safetycost_outcome_materialization_preflight_executed_by_this_gate"] is True
    assert decision["actual_safetycost_outcome_materialization_execution_authorized"] is False
    assert decision["actual_safetycost_outcome_materialization_executed_by_this_gate"] is False
    assert decision["paired_evaluation_executed_by_this_gate"] is False
    assert decision["closed_loop_outcome_training_or_online_input_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["name"] for item in report["materialization_inputs"]] == list(
        module.EXPECTED_MATERIALIZATION_INPUTS
    )
    assert [item["name"] for item in report["preflight_steps"]] == list(
        module.EXPECTED_PREFLIGHT_STEPS
    )
    assert {item["materializes_outcomes"] for item in report["preflight_steps"]} == {
        False
    }
    assert [item["name"] for item in report["future_outputs"]] == list(
        module.EXPECTED_FUTURE_OUTPUTS
    )
    assert [item["name"] for item in report["no_go_register"]] == list(
        module.EXPECTED_NO_GO
    )
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_actual_safetycost_outcome_materialization_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "outcome_materialization_preflight_enabled" in report["final_decision"][
        "failed_checks"
    ]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_actual_safetycost_outcome_materialization_preflight_authorization_missing"
    )


def test_actual_safetycost_outcome_materialization_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_actual_safetycost_outcome_materialization_preflight_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"safety_benefit_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_review_decision_safety_benefit_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_actual_safetycost_outcome_materialization_preflight_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["preflight_plan_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_static_review_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_static_review_md_sha" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_plan_static_review_passed=True",
            "actual_safetycost_outcome_materialization_preflight_authorized=True",
            "actual_safetycost_outcome_materialization_executed_by_current_gate=False",
            "paired_evaluation_executed_by_current_gate=False",
            "closed_loop_outcome_training_or_online_input_authorized=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "source_static_review_artifact"
    review_dir = artifact / "review"
    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_static_review_report(
            module,
            source_decision_updates=source_decision_updates,
        ),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# static review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    _write(
        artifact / "HEADS",
        (
            f"CAMP_HEAD={SOURCE_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
        ),
    )
    _write(artifact / "COMMAND", "python review.py\n")
    _write(artifact / "stdout", "{}\n")
    _write(artifact / "stderr", "")
    _write(artifact / "run.exit", "0\n")
    _write_root_sha256s(artifact, [review_json, review_md, review_sha])

    return {
        "preflight_plan_static_review_artifact_dir": artifact,
        "preflight_plan_static_review_json": review_json,
        "preflight_plan_static_review_md": review_md,
        "preflight_plan_static_review_sha256s": review_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_static_review_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_plan_static_review_passed": True,
        "actual_safetycost_outcome_materialization_preflight_authorized": True,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "paired_evaluation_executed_by_this_gate": False,
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "final_decision": decision,
        "static_review_checks": [
            {"name": f"check_{index}", "passed": True, "actual": True, "expected": True}
            for index in range(82)
        ],
        "source_plan_summary": {
            "schema_version": module.SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA,
            "status": module.SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
            "preflight_plan_check_count": 74,
            "failed_check_count": 0,
            "required_input_count": 8,
            "preflight_plan_count": 8,
            "planned_output_count": 6,
            "no_go_count": 10,
            "source_static_review_check_count": 82,
            "source_paired_record_count": 3200,
            "source_shadow_diff_records": 2832,
        },
        "preflight_scope_summary": {
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "planned_materialization_scope": "shadow-selected run-level closed-loop outcome summaries only",
            "closed_loop_outcomes_training_or_online_input": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(path: Path, files: list[Path]) -> Path:
    return _write(path, "".join(f"{_sha256(file)}  {file.name}\n" for file in files))


def _write_root_sha256s(root: Path, files: list[Path]) -> Path:
    lines = []
    for file in files:
        rel = file.relative_to(root).as_posix()
        lines.append(f"{_sha256(file)}  ./{rel}\n")
    return _write(root / "SHA256SUMS", "".join(lines))
