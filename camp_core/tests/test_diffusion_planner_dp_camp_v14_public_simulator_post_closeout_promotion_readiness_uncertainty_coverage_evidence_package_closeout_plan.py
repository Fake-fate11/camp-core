from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout.py"
)
ARTIFACT_HEAD = "9" * 40
CURRENT_HEAD = "a" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_package_closeout_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["uncertainty_coverage_evidence_package_closeout_plan_ready"] is True
    assert decision["uncertainty_coverage_evidence_package_closeout_plan_static_review_authorized"] is True
    assert decision["evidence_package_closed_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["item_name"] for item in report["closeout_plan"]] == list(module.EXPECTED_CLOSEOUT_ITEMS)
    assert {item["closeout_recorded_by_this_gate"] for item in report["closeout_plan"]} == {False}
    assert {item["authorizes_execution"] for item in report["closeout_plan"]} == {False}
    assert {item["authorizes_claim"] for item in report["closeout_plan"]} == {False}
    assert {item["authorizes_promotion"] for item in report["closeout_plan"]} == {False}
    assert {item["authorizes_deployment"] for item in report["closeout_plan"]} == {False}
    assert report["package_summary"]["package_file_count"] == module.EXPECTED_PACKAGE_FILE_COUNT
    assert report["package_summary"]["package_payload_file_count"] == module.EXPECTED_PACKAGE_PAYLOAD_FILE_COUNT
    assert report["package_summary"]["all_no_execution"] is True
    assert report["package_summary"]["all_no_claim"] is True
    assert report["package_summary"]["all_no_promotion"] is True
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_package_closeout_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "closeout_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_package_closeout_plan_authorization_missing"
    )


def test_uncertainty_coverage_evidence_package_closeout_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_closeout_plan" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_closeout_plan" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_package_closeout_plan_rejects_source_review_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_review_decision_deployment_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["deployment_authorized"] is False


def test_uncertainty_coverage_evidence_package_closeout_plan_rejects_package_summary_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        package_summary_updates={"all_no_claim": False},
    )

    report = module.build_report(**fixture)

    assert "package_summary_all_no_claim" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_uncertainty_coverage_evidence_package_closeout_plan_rejects_artifact_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "review_artifact_md_root_sha" in report["final_decision"]["failed_checks"]
    assert "source_review_md_review_sha" in report["final_decision"]["failed_checks"]


def test_uncertainty_coverage_evidence_package_closeout_plan_cli_writes_outputs(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--source_static_review_artifact_dir",
            str(fixture["source_static_review_artifact_dir"]),
            "--source_static_review_json",
            str(fixture["source_static_review_json"]),
            "--source_static_review_md",
            str(fixture["source_static_review_md"]),
            "--source_static_review_sha256s",
            str(fixture["source_static_review_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan",
        ]
    )

    assert exit_code == 0
    assert (output_dir / module.PLAN_JSON_NAME).is_file()
    assert (output_dir / module.PLAN_MD_NAME).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    package_summary_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "static_review_artifact"
    review_dir = artifact / "review"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_package_construction_static_review_passed=True",
            "uncertainty_coverage_evidence_package_closeout_plan_authorized=True",
            "evidence_package_constructed_by_this_gate=False",
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
        _source_review_payload(
            module,
            decision_updates=source_decision_updates,
            package_summary_updates=package_summary_updates,
        ),
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
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": review_json,
        "source_static_review_md": review_md,
        "source_static_review_sha256s": review_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
    package_summary_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_package_construction_static_review_passed": True,
        "uncertainty_coverage_evidence_package_closeout_plan_authorized": True,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if decision_updates:
        decision.update(decision_updates)
    analysis = {
        "current_camp_head": ARTIFACT_HEAD,
        "current_camp_origin_main": ARTIFACT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for flag in module.ANALYSIS_FALSE_FLAGS:
        analysis[flag] = False
    package_summary = {
        "package_file_count": module.EXPECTED_PACKAGE_FILE_COUNT,
        "package_payload_file_count": module.EXPECTED_PACKAGE_PAYLOAD_FILE_COUNT,
        "manifest_count": module.EXPECTED_PACKAGE_MANIFEST_COUNT,
        "all_no_execution": True,
        "all_no_claim": True,
        "all_no_promotion": True,
    }
    if package_summary_updates:
        package_summary.update(package_summary_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": analysis,
        "source_construction_summary": {
            "construction_check_count": module.EXPECTED_SOURCE_CONSTRUCTION_CHECK_COUNT,
            "failed_check_count": 0,
        },
        "package_summary": package_summary,
        "blocked_actions": {name: False for name in module.BLOCKED_ACTIONS},
        "review_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(module.EXPECTED_SOURCE_REVIEW_CHECK_COUNT)
        ],
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256sums(path: Path, files: list[Path], *, relative_to: Path | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for file_path in files:
        if relative_to is None:
            name = file_path.name
        else:
            name = file_path.relative_to(relative_to).as_posix()
        lines.append(f"{_sha256(file_path)}  {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
