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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_harness_preflight.py"
)
RUNTIME_REPLAY_SCRIPT = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
CURRENT_HEAD = "e" * 40
SOURCE_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_objective_3200_candidate_index_replay_harness_preflight_plan",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_replay_harness_preflight_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    runner = report["runner_surface_inventory"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_candidate_index_replay_harness_preflight_plan_ready"] is True
    assert decision["objective_3200_candidate_index_replay_harness_preflight_plan_static_review_authorized"] is True
    assert decision["harness_implementation_authorized"] is False
    assert decision["direct_candidate_index_replay_execution_authorized"] is False
    assert decision["direct_outcome_acquisition_execution_authorized"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["candidate_closed_loop_outcome_records"] == 0
    assert decision["missing_candidate_closed_loop_outcome_records"] == 3200
    assert runner["has_candidate_index_replay_flag"] is False
    assert runner["has_compute_candidate_closed_loop_outcomes_import"] is True
    assert [item["name"] for item in report["harness_preflight_plan"]] == list(
        module.EXPECTED_HARNESS_PLAN_ITEMS
    )
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_replay_harness_preflight_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "harness_preflight_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_replay_harness_preflight_plan_authorization_missing"
    )


def test_candidate_index_replay_harness_preflight_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_replay_harness_preflight_plan_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["source_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "root_review_md_sha" in report["final_decision"]["failed_checks"]
    assert "nested_review_md_sha" in report["final_decision"]["failed_checks"]


def _fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_failure_remediation_plan_static_review_passed=True",
            "objective_3200_outcome_acquisition_candidate_index_replay_harness_preflight_plan_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = _write_source_static_review_artifact(tmp_path, module)
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": artifact / "review" / module.SOURCE_REVIEW_JSON_NAME,
        "source_static_review_md": artifact / "review" / module.SOURCE_REVIEW_MD_NAME,
        "source_static_review_sha256s": artifact / "review" / "SHA256SUMS",
        "runtime_replay_script_py": RUNTIME_REPLAY_SCRIPT,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_static_review_artifact(tmp_path: Path, module) -> Path:
    artifact = tmp_path / "source_static_review"
    review_dir = artifact / "review"
    review_json = _write_json(review_dir / module.SOURCE_REVIEW_JSON_NAME, _source_review_report(module))
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# static review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
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


def _source_review_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_outcome_acquisition_candidate_index_replay_harness_preflight_plan_authorized": True,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "actual_safetycost_v1_available": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_plan_summary": {
            "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_closed_loop_outcome_records": 0,
            "missing_candidate_closed_loop_outcome_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_index_replay_flag_present": False,
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
