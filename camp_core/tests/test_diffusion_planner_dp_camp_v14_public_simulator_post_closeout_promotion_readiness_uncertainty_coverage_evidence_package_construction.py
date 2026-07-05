from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "construct_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package.py"
)
ARTIFACT_HEAD = "7" * 40
CURRENT_HEAD = "8" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_package_construction_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["uncertainty_coverage_evidence_package_constructed"] is True
    assert decision["evidence_package_constructed_by_this_gate"] is True
    assert decision["evidence_package_construction_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_manifest_summary"]["manifest_count"] == module.EXPECTED_MANIFEST_COUNT
    assert report["source_manifest_summary"]["all_no_execution"] is True
    assert report["source_manifest_summary"]["all_no_claim"] is True
    assert len(report["evidence_package_files"]) == len(module.PACKAGE_FILES) + 1

    package_dir = fixture["output_dir"] / module.PACKAGE_DIR_NAME
    assert (fixture["output_dir"] / module.CONSTRUCTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.CONSTRUCTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    for file_name in module.PACKAGE_FILES:
        assert (package_dir / file_name).is_file()
    assert (package_dir / "SHA256SUMS").is_file()

    package_manifest = json.loads((package_dir / "evidence_package_manifest.json").read_text(encoding="utf-8"))
    assert package_manifest["evidence_package_constructed_by_this_gate"] is True
    assert package_manifest["authorizes_execution"] is False
    assert package_manifest["authorizes_claim"] is False
    assert package_manifest["authorizes_promotion"] is False


def test_uncertainty_coverage_evidence_package_construction_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "construction_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_package_construction_authorization_missing"
    )


def test_uncertainty_coverage_evidence_package_construction_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_boundary_authorizes_construction_or_command_harness_rerun" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_package_construction_accepts_command_harness_rerun_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, command_harness_rerun_boundary=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert "audit_boundary_authorizes_construction_or_command_harness_rerun" not in report["final_decision"]["failed_checks"]


def test_uncertainty_coverage_evidence_package_construction_rejects_source_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_static_review_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_package_construction_rejects_manifest_claim(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        manifest_updates={module.EXPECTED_MANIFESTS[0]: {"authorizes_claim": True}},
    )

    report = module.build_report(**fixture)

    assert f"manifest_{module.EXPECTED_MANIFESTS[0]}_no_claim" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_evidence_package_construction_contract_failure"
    )


def test_uncertainty_coverage_evidence_package_construction_cli_writes_outputs(
    tmp_path: Path,
) -> None:
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
            "--source_plan_artifact_dir",
            str(fixture["source_plan_artifact_dir"]),
            "--source_plan_json",
            str(fixture["source_plan_json"]),
            "--source_plan_md",
            str(fixture["source_plan_md"]),
            "--source_plan_sha256s",
            str(fixture["source_plan_sha256s"]),
            "--source_materialization_static_review_artifact_dir",
            str(fixture["source_materialization_static_review_artifact_dir"]),
            "--source_materialization_static_review_json",
            str(fixture["source_materialization_static_review_json"]),
            "--source_materialization_static_review_md",
            str(fixture["source_materialization_static_review_md"]),
            "--source_materialization_static_review_sha256s",
            str(fixture["source_materialization_static_review_sha256s"]),
            "--source_materialization_artifact_dir",
            str(fixture["source_materialization_artifact_dir"]),
            "--source_materialization_json",
            str(fixture["source_materialization_json"]),
            "--source_manifests_dir",
            str(fixture["source_manifests_dir"]),
            "--source_manifests_sha256s",
            str(fixture["source_manifests_sha256s"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction",
        ]
    )

    assert exit_code == 0
    assert (output_dir / module.CONSTRUCTION_JSON_NAME).is_file()
    assert (output_dir / module.CONSTRUCTION_MD_NAME).is_file()
    assert (output_dir / module.PACKAGE_DIR_NAME / "claim_boundary_register.json").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    command_harness_rerun_boundary: bool = False,
    source_static_review_decision_updates: dict[str, Any] | None = None,
    manifest_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    if command_harness_rerun_boundary:
        doc_lines = [
            f"current_v14_status={module.REJECT_STATUS}",
            f"next_work_target={module.AUTHORIZED_RERUN_DECISION_WORK}",
            (
                "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_"
                f"evidence_package_construction_failure_root_cause={module.COMMAND_HARNESS_FAILURE_ROOT_CAUSE}"
            ),
            (
                "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_"
                f"evidence_package_construction_failed_checks={module.COMMAND_HARNESS_FAILED_CHECKS}"
            ),
            "single-quoted heredoc",
            "evidence_package_constructed_by_this_gate=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    else:
        doc_lines = [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_package_construction_plan_static_review_passed=True",
            "uncertainty_coverage_evidence_package_construction_authorized=True",
            "evidence_package_construction_authorized=True",
            "evidence_package_constructed_by_this_gate=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    doc_text = "\n".join(doc_lines)
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    static_review_artifact = tmp_path / "package_plan_static_review_artifact"
    static_review_dir = static_review_artifact / "review"
    static_review_json = _write_json(
        static_review_dir / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        _source_static_review_payload(
            module,
            decision_updates=source_static_review_decision_updates,
        ),
    )
    static_review_md = _write(static_review_dir / module.SOURCE_STATIC_REVIEW_MD_NAME, "# Package Plan Static Review\n")
    static_review_sha256s = _write_sha256sums(static_review_dir / "SHA256SUMS", [static_review_json, static_review_md])
    _write_artifact_execution_files(
        module,
        static_review_artifact,
        [static_review_json, static_review_md],
    )

    plan_artifact = tmp_path / "package_plan_artifact"
    plan_dir = plan_artifact / "plan"
    plan_json = _write_json(plan_dir / module.SOURCE_PLAN_JSON_NAME, _source_plan_payload(module))
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# Package Construction Plan\n")
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    _write_artifact_execution_files(module, plan_artifact, [plan_json, plan_md])

    materialization_static_review_artifact = tmp_path / "materialization_static_review_artifact"
    materialization_static_review_dir = materialization_static_review_artifact / "review"
    materialization_static_review_json = _write_json(
        materialization_static_review_dir / module.SOURCE_MATERIALIZATION_STATIC_REVIEW_JSON_NAME,
        _source_materialization_static_review_payload(module),
    )
    materialization_static_review_md = _write(
        materialization_static_review_dir / module.SOURCE_MATERIALIZATION_STATIC_REVIEW_MD_NAME,
        "# Materialization Static Review\n",
    )
    materialization_static_review_sha256s = _write_sha256sums(
        materialization_static_review_dir / "SHA256SUMS",
        [materialization_static_review_json, materialization_static_review_md],
    )
    _write_artifact_execution_files(
        module,
        materialization_static_review_artifact,
        [materialization_static_review_json, materialization_static_review_md],
    )

    materialization_artifact = tmp_path / "materialization_artifact"
    materialization_json = _write_json(
        materialization_artifact / "materialization" / module.SOURCE_MATERIALIZATION_JSON_NAME,
        _source_materialization_payload(module),
    )
    manifests_dir = materialization_artifact / "manifests"
    manifest_paths = []
    for name in module.EXPECTED_MANIFESTS:
        path = manifests_dir / f"{name}.json"
        manifest_paths.append(
            _write_json(
                path,
                _manifest_payload(
                    module,
                    name,
                    path,
                    updates=(manifest_updates or {}).get(name),
                ),
            )
        )
    manifests_sha256s = _write_sha256sums(manifests_dir / "SHA256SUMS", manifest_paths)

    return {
        "source_static_review_artifact_dir": static_review_artifact,
        "source_static_review_json": static_review_json,
        "source_static_review_md": static_review_md,
        "source_static_review_sha256s": static_review_sha256s,
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_json,
        "source_plan_md": plan_md,
        "source_plan_sha256s": plan_sha256s,
        "source_materialization_static_review_artifact_dir": materialization_static_review_artifact,
        "source_materialization_static_review_json": materialization_static_review_json,
        "source_materialization_static_review_md": materialization_static_review_md,
        "source_materialization_static_review_sha256s": materialization_static_review_sha256s,
        "source_materialization_artifact_dir": materialization_artifact,
        "source_materialization_json": materialization_json,
        "source_manifests_dir": manifests_dir,
        "source_manifests_sha256s": manifests_sha256s,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_artifact_execution_files(module, artifact: Path, payload_files: list[Path]) -> None:
    command = _write(artifact / "COMMAND", "command\n")
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
        [command, heads, stdout, stderr, run_exit, *payload_files],
        relative_to=artifact,
    )


def _source_static_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_package_construction_plan_static_review_passed": True,
        "uncertainty_coverage_evidence_package_construction_authorized": True,
        "evidence_package_construction_authorized": True,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    _add_false_boundaries(module, decision)
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": _analysis(module, static_review_only=True),
        "source_plan_summary": {
            "schema_version": module.SOURCE_PLAN_SCHEMA,
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
            "plan_check_count": module.EXPECTED_PLAN_CHECK_COUNT,
        },
        "package_plan_summary": {
            "package_plan_item_count": len(module.PACKAGE_PLAN_ITEMS),
            "package_plan_items": list(module.PACKAGE_PLAN_ITEMS),
            "all_no_construction": True,
            "all_no_execution": True,
            "all_no_claim": True,
            "all_no_promotion": True,
        },
        "review_checks": _checks(module.EXPECTED_STATIC_REVIEW_CHECK_COUNT),
        "final_decision": decision,
    }


def _source_plan_payload(module) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_PLAN_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_package_construction_plan_ready": True,
        "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized": True,
        "evidence_package_constructed_by_this_gate": False,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    _add_false_boundaries(module, decision)
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": _analysis(module, plan_only=True, read_only=True),
        "manifest_summary": {
            "manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "manifest_names": list(module.EXPECTED_MANIFESTS),
            "all_materialized": True,
            "all_no_execution": True,
            "all_no_claim": True,
        },
        "source_review_summary": {
            "review_check_count": module.EXPECTED_MATERIALIZATION_STATIC_REVIEW_CHECK_COUNT,
            "passed": True,
        },
        "source_materialization_summary": {
            "materialization_check_count": module.EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT,
            "materialized_manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "passed": True,
        },
        "evidence_package_construction_plan": [
            {
                "item_name": name,
                "label": "unit",
                "purpose": f"purpose for {name}",
                "source_static_review_status": module.SOURCE_MATERIALIZATION_STATIC_REVIEW_STATUS,
                "source_materialization_status": module.SOURCE_MATERIALIZATION_STATUS,
                "source_manifests_dir": "/tmp/manifests",
                "required_manifest_names": list(module.EXPECTED_MANIFESTS),
                "package_constructed_by_this_gate": False,
                "authorizes_execution": False,
                "authorizes_claim": False,
                "authorizes_promotion": False,
            }
            for name in module.PACKAGE_PLAN_ITEMS
        ],
        "plan_checks": _checks(module.EXPECTED_PLAN_CHECK_COUNT),
        "final_decision": decision,
    }


def _source_materialization_static_review_payload(module) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_MATERIALIZATION_STATIC_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.SOURCE_PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "evidence_package_construction_plan_authorized": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    _add_false_boundaries(module, decision)
    return {
        "schema_version": module.SOURCE_MATERIALIZATION_STATIC_REVIEW_SCHEMA,
        "analysis": _analysis(module, static_review_only=True),
        "manifest_summary": {
            "manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "manifest_names": list(module.EXPECTED_MANIFESTS),
            "all_materialized": True,
            "all_no_execution": True,
            "all_no_claim": True,
        },
        "review_checks": _checks(module.EXPECTED_MATERIALIZATION_STATIC_REVIEW_CHECK_COUNT),
        "final_decision": decision,
    }


def _source_materialization_payload(module) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_MATERIALIZATION_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "materialized_manifest_count": module.EXPECTED_MANIFEST_COUNT,
        "authorized_next_work": module.SOURCE_PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "evidence_manifest_materialization_static_review_authorized": True,
        "evidence_manifest_materialized_by_this_gate": True,
    }
    _add_false_boundaries(module, decision)
    return {
        "schema_version": module.SOURCE_MATERIALIZATION_SCHEMA,
        "analysis": _analysis(module, materialization_only=True),
        "materialization_checks": _checks(module.EXPECTED_SOURCE_MATERIALIZATION_CHECK_COUNT),
        "materialized_manifest_files": [
            {"manifest_name": name, "path": f"/tmp/{name}.json", "sha256": "0" * 64}
            for name in module.EXPECTED_MANIFESTS
        ],
        "final_decision": decision,
    }


def _manifest_payload(
    module,
    name: str,
    path: Path,
    *,
    updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": module.MANIFEST_SCHEMA_VERSION,
        "manifest_name": name,
        "source_gap": f"gap_for_{name}",
        "materialized_path": str(path),
        "required_inputs": ["source_review"],
        "acceptance_checks": ["read_only"],
        "current_camp_head": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "score_expression": module.SCORE_EXPRESSION,
        "materialized_by_this_gate": True,
        "authorizes_execution": False,
        "authorizes_claim": False,
        "training_execution": False,
        "replay_execution": False,
        "candidate_generation": False,
        "dp_modification": False,
        "online_selector_change": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "safety_or_camp_over_dp_claim": False,
    }
    if updates:
        payload.update(updates)
    return payload


def _analysis(module, **extra: Any) -> dict[str, Any]:
    analysis = {
        "label": "unit",
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
    }
    analysis.update(extra)
    return analysis


def _add_false_boundaries(module, payload: dict[str, Any]) -> None:
    for action in module.BLOCKED_ACTIONS:
        payload[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        payload[flag] = False


def _checks(count: int) -> list[dict[str, Any]]:
    return [
        {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
        for index in range(count)
    ]


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
