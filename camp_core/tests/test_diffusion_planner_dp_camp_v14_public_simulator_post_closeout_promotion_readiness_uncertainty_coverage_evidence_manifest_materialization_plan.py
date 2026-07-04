from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization.py"
)
ARTIFACT_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_manifest_materialization_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized"] is True
    assert decision["evidence_manifest_materialization_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["manifest_name"] for item in report["evidence_manifest_materialization_plan"]] == list(
        module.EXPECTED_MANIFESTS
    )
    assert {item["materialized_by_this_gate"] for item in report["evidence_manifest_materialization_plan"]} == {False}
    assert {item["authorizes_execution"] for item in report["evidence_manifest_materialization_plan"]} == {False}
    assert {item["authorizes_claim"] for item in report["evidence_manifest_materialization_plan"]} == {False}
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.json"
    ).is_file()
    assert (
        fixture["output_dir"]
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.md"
    ).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_manifest_materialization_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "evidence_manifest_materialization_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_manifest_materialization_plan_authorization_missing"
    )


def test_uncertainty_coverage_evidence_manifest_materialization_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_manifest_plan" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_manifest_plan" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_manifest_materialization_plan_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"evidence_manifest_materialization_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_decision_evidence_manifest_materialization_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["evidence_manifest_materialization_authorized"] is False


def test_uncertainty_coverage_evidence_manifest_materialization_plan_rejects_existing_manifest_root(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["planned_manifest_root"].mkdir(parents=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "planned_manifest_root_not_preexisting" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "artifact_contract_failure"


def test_uncertainty_coverage_evidence_manifest_materialization_plan_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--static_review_artifact_dir",
            str(fixture["static_review_artifact_dir"]),
            "--static_review_json",
            str(fixture["static_review_json"]),
            "--static_review_md",
            str(fixture["static_review_md"]),
            "--static_review_sha256s",
            str(fixture["static_review_sha256s"]),
            "--planned_manifest_root",
            str(fixture["planned_manifest_root"]),
            "--v14_audit_md",
            str(fixture["v14_audit_md"]),
            "--current_status_md",
            str(fixture["current_status_md"]),
            "--output_dir",
            str(output_dir),
            "--current_camp_head",
            CURRENT_HEAD,
            "--current_camp_origin_main",
            CURRENT_HEAD,
            "--current_dp_head",
            module.FIXED_DP_HEAD,
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan",
        ]
    )

    assert exit_code == 0
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.json"
    ).is_file()
    assert (
        output_dir
        / "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan.md"
    ).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "static_review_artifact"
    review_dir = artifact / "review"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_gap_closure_plan_static_review_passed=True",
            "uncertainty_coverage_evidence_manifest_materialization_plan_authorized=True",
            "direct_promotion_recommendation=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_static_review_payload(module, decision_updates=source_decision_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# Static Review\n")
    review_sha256s = _write_sha256sums(review_dir / "SHA256SUMS", [review_json, review_md])
    command = _write(artifact / "COMMAND", "static review command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={ARTIFACT_HEAD}",
                f"CAMP_ORIGIN_MAIN={ARTIFACT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, stdout, stderr, run_exit, review_json, review_md],
        relative_to=artifact,
    )
    return {
        "static_review_artifact_dir": artifact,
        "static_review_json": review_json,
        "static_review_md": review_md,
        "static_review_sha256s": review_sha256s,
        "planned_manifest_root": tmp_path / "future_manifests",
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_static_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "authorized_current_work": module.SOURCE_STATIC_REVIEW_STATUS.replace("_passed", "_only"),
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_passed": True,
        "uncertainty_coverage_evidence_manifest_materialization_plan_authorized": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
        "recommendation": "plan_evidence_manifest_materialization_only",
        "immediate_action": "evidence_manifest_materialization_plan_only",
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "score_expression": module.SCORE_EXPRESSION,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_plan_summary": {
            "plan_check_count": module.EXPECTED_SOURCE["source_plan_check_count"],
            "plan_item_count": module.EXPECTED_SOURCE["source_plan_item_count"],
            "source_static_review_check_count": module.EXPECTED_SOURCE["source_static_review_check_count"],
            "source_review_gap_count": module.EXPECTED_SOURCE["source_review_gap_count"],
        },
        "blocked_actions": {action: False for action in module.BLOCKED_ACTIONS},
        "review_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_SOURCE["static_review_check_count"])
        ],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256sums(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    rows = []
    for file in files:
        key = file.relative_to(relative_to).as_posix() if relative_to else file.name
        rows.append(f"{_sha256(file)}  {key}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
