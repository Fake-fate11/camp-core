from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition.py"
)
CURRENT_HEAD = "e" * 40
SOURCE_REVIEW_HEAD = "f" * 40
SOURCE_PLAN_HEAD = "a" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_preflight",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_replay_outcome_acquisition_preflight_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_candidate_index_replay_outcome_acquisition_preflight_ready"] is True
    assert decision["objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_authorized"] is True
    assert decision["candidate_index_replay_harness_implemented"] is True
    assert decision["candidate_index_replay_harness_execution_authorized"] is False
    assert decision["direct_candidate_index_replay_execution_authorized"] is False
    assert decision["direct_outcome_acquisition_execution_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["objective_required_records"] == module.OBJECTIVE_REQUIRED_RECORDS
    assert decision["candidate_closed_loop_outcome_records"] == 0
    assert decision["missing_candidate_closed_loop_outcome_records"] == module.OBJECTIVE_REQUIRED_RECORDS
    assert [item["item"] for item in report["preflight_items"]] == list(module.EXPECTED_PREFLIGHT_ITEMS)
    assert report["planned_outputs"] == list(module.EXPECTED_PLANNED_OUTPUTS)
    assert report["no_go_register"] == list(module.PREFLIGHT_NO_GO)
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_replay_outcome_acquisition_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_replay_outcome_acquisition_preflight_authorization_missing"
    )


def test_candidate_index_replay_outcome_acquisition_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_replay_outcome_acquisition_preflight_rejects_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(
        tmp_path,
        module,
        source_review_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_static_review_camp_over_dp_top1_claim_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_candidate_index_replay_outcome_acquisition_preflight_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["source_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "source_static_review_root_md_sha" in report["final_decision"]["failed_checks"]
    assert "source_static_review_nested_md_sha" in report["final_decision"]["failed_checks"]


def test_candidate_index_replay_outcome_acquisition_preflight_rejects_missing_runner_harness(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["runtime_replay_script_py"].write_text("def run():\n    return None\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "runner_has_candidate_index_replay_flag" in report["final_decision"]["failed_checks"]
    assert "runner_routes_shadow_selected_index" in report["final_decision"]["failed_checks"]


def _fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_review_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passed=True",
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_plan = _write_plan_artifact(tmp_path, module)
    source_review = _write_review_artifact(
        tmp_path,
        module,
        source_review_decision_updates=source_review_decision_updates,
    )
    runtime = _write_runtime_fixture(tmp_path)
    return {
        "source_static_review_artifact_dir": source_review,
        "source_static_review_json": source_review / "review" / module.SOURCE_REVIEW_JSON_NAME,
        "source_static_review_md": source_review / "review" / module.SOURCE_REVIEW_MD_NAME,
        "source_static_review_sha256s": source_review / "review" / "SHA256SUMS",
        "source_preflight_plan_artifact_dir": source_plan,
        "source_preflight_plan_json": source_plan / "plan" / module.SOURCE_PLAN_JSON_NAME,
        "source_preflight_plan_md": source_plan / "plan" / module.SOURCE_PLAN_MD_NAME,
        "source_preflight_plan_sha256s": source_plan / "plan" / "SHA256SUMS",
        "runtime_replay_script_py": runtime,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "preflight",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
        "enabled": True,
    }


def _write_runtime_fixture(tmp_path: Path) -> Path:
    return _write(
        tmp_path / "run_diffusion_planner_camp_replay.py",
        "\n".join(
            [
                "def run(args):",
                "    '--candidate_index_replay'",
                "    '--camp_candidate_index_replay_harness'",
                "    shadow_selected_index = 3",
                "    selected_index = int(shadow_selected_index)",
                "    return _build_candidate_index_replay_harness_payload()",
                "",
            ]
        ),
    )


def _write_review_artifact(
    tmp_path: Path,
    module,
    *,
    source_review_decision_updates: dict[str, Any] | None = None,
) -> Path:
    artifact = tmp_path / "source_static_review"
    review_dir = artifact / "review"
    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_review_report(module, decision_updates=source_review_decision_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_REVIEW_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_REVIEW_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(artifact / "COMMAND", "python review.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, review_json, review_md, review_sha],
        relative_to=artifact,
    )
    return artifact


def _write_plan_artifact(tmp_path: Path, module) -> Path:
    artifact = tmp_path / "source_plan"
    plan_dir = artifact / "plan"
    plan_json = _write_json(plan_dir / module.SOURCE_PLAN_JSON_NAME, _source_plan_report(module))
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# plan\n")
    plan_sha = _write_sha256s(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_PLAN_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_PLAN_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(artifact / "COMMAND", "python plan.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, plan_json, plan_md, plan_sha],
        relative_to=artifact,
    )
    return artifact


def _source_review_report(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passed": True,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_authorized": True,
        "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_index_replay_harness_implemented": True,
        "candidate_index_replay_harness_execution_authorized": False,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    decision.update(decision_updates or {})
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision.setdefault(flag, False)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "read_only": True,
            "static_review_only": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }


def _source_plan_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PLAN_STATUS,
        "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
        "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_index_replay_harness_implemented": True,
        "candidate_index_replay_harness_execution_authorized": False,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "read_only": True,
            "plan_only": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256s(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    lines = []
    for file in files:
        name = file.name if relative_to is None else file.relative_to(relative_to).as_posix()
        lines.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {name}")
    return _write(path, "\n".join(lines) + "\n")
