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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_contract.py"
)
CONSTRUCTION_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "construct_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package.py"
)
CONSTRUCTION_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction.py"
)
ARTIFACT_HEAD = "7" * 40
CURRENT_HEAD = "8" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_package_construction_static_review_passes(
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
    assert decision["uncertainty_coverage_evidence_package_construction_static_review_passed"] is True
    assert decision["uncertainty_coverage_evidence_package_closeout_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["package_summary"]["package_file_count"] == module.EXPECTED_PACKAGE_FILE_COUNT
    assert report["package_summary"]["package_payload_file_count"] == module.EXPECTED_PACKAGE_PAYLOAD_FILE_COUNT
    assert report["package_summary"]["all_no_execution"] is True
    assert report["package_summary"]["all_no_claim"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_package_construction_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "construction_static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_package_construction_static_review_authorization_missing"
    )


def test_uncertainty_coverage_evidence_package_construction_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_package_construction_static_review_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_construction_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_package_construction_static_review_rejects_package_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    (fixture["evidence_package_construction_artifact_dir"] / "construction" / module.PACKAGE_DIR_NAME / "README.md").write_text(
        "drift\n",
        encoding="utf-8",
    )

    report = module.build_report(**fixture)

    assert "artifact_package_README.md_root_sha" in report["final_decision"]["failed_checks"]
    assert "package_README.md_package_sha" in report["final_decision"]["failed_checks"]


def test_uncertainty_coverage_evidence_package_construction_static_review_rejects_claim_boundary_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        package_updates={"claim_boundary_register.json": {"selector_promotion_authorized": True}},
    )

    report = module.build_report(**fixture)

    assert "claim_boundary_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_package_construction_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_package_construction_artifact_dir",
            str(fixture["evidence_package_construction_artifact_dir"]),
            "--evidence_package_construction_json",
            str(fixture["evidence_package_construction_json"]),
            "--evidence_package_construction_md",
            str(fixture["evidence_package_construction_md"]),
            "--evidence_package_construction_sha256s",
            str(fixture["evidence_package_construction_sha256s"]),
            "--construction_script_py",
            str(fixture["construction_script_py"]),
            "--construction_test_py",
            str(fixture["construction_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review",
        ]
    )

    assert exit_code == 0
    assert (output_dir / module.REVIEW_JSON_NAME).is_file()
    assert (output_dir / module.REVIEW_MD_NAME).is_file()
    assert (output_dir / "SHA256SUMS").is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    package_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "construction_artifact"
    construction_dir = artifact / "construction"
    package_dir = construction_dir / module.PACKAGE_DIR_NAME
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_CONSTRUCTION_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_package_construction_passed=True",
            "uncertainty_coverage_evidence_package_constructed=True",
            "evidence_package_constructed_by_this_gate=True",
            "uncertainty_coverage_evidence_package_construction_static_review_authorized=True",
            "evidence_package_construction_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    package_payloads = _package_payloads(module, package_updates=package_updates)
    package_paths = []
    for file_name in module.PACKAGE_JSON_FILES:
        package_paths.append(_write_json(package_dir / file_name, package_payloads[file_name]))
    package_paths.append(_write(package_dir / "README.md", "# Evidence Package\n"))
    package_sha256s = _write_sha256sums(package_dir / "SHA256SUMS", package_paths)

    construction_json = _write_json(
        construction_dir / module.SOURCE_CONSTRUCTION_JSON_NAME,
        _source_construction_payload(module, source_decision_updates=source_decision_updates),
    )
    construction_md = _write(construction_dir / module.SOURCE_CONSTRUCTION_MD_NAME, "# Construction\n")
    construction_sha256s = _write_sha256sums(construction_dir / "SHA256SUMS", [construction_json, construction_md])

    command = _write(artifact / "COMMAND", "construction command\n")
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
        [command, heads, stdout, stderr, run_exit, construction_json, construction_md, *package_paths],
        relative_to=artifact,
    )

    return {
        "evidence_package_construction_artifact_dir": artifact,
        "evidence_package_construction_json": construction_json,
        "evidence_package_construction_md": construction_md,
        "evidence_package_construction_sha256s": construction_sha256s,
        "construction_script_py": CONSTRUCTION_SCRIPT_PATH,
        "construction_test_py": CONSTRUCTION_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_construction_payload(
    module,
    *,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_CONSTRUCTION_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_current_work": module.CONSTRUCTION_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "uncertainty_coverage_evidence_package_constructed": True,
        "evidence_package_constructed_by_this_gate": True,
        "uncertainty_coverage_evidence_package_construction_static_review_authorized": True,
        "evidence_package_construction_static_review_authorized": True,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    _add_false_boundaries(module, decision)
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_CONSTRUCTION_SCHEMA,
        "analysis": _analysis(module, construction_only=True),
        "source_static_review_summary": {"review_check_count": module.EXPECTED_STATIC_REVIEW_CHECK_COUNT, "passed": True},
        "source_plan_summary": {"plan_check_count": module.EXPECTED_PLAN_CHECK_COUNT, "passed": True},
        "source_materialization_static_review_summary": {"review_check_count": module.EXPECTED_MATERIALIZATION_STATIC_REVIEW_CHECK_COUNT, "passed": True},
        "source_materialization_summary": {"materialization_check_count": module.EXPECTED_MATERIALIZATION_CHECK_COUNT, "materialized_manifest_count": module.EXPECTED_MANIFEST_COUNT, "passed": True},
        "source_manifest_summary": {
            "manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "manifest_names": [f"manifest_{index}" for index in range(module.EXPECTED_MANIFEST_COUNT)],
            "all_materialized": True,
            "all_no_execution": True,
            "all_no_claim": True,
        },
        "evidence_package_files": [
            {"name": file_name, "sha256": "0" * 64}
            for file_name in [*module.PACKAGE_FILES, "SHA256SUMS"]
        ],
        "evidence_package_payloads": {
            file_name: {"schema_version": module.SOURCE_PACKAGE_SCHEMA}
            for file_name in module.PACKAGE_JSON_FILES
        },
        "construction_checks": _checks(module.EXPECTED_CONSTRUCTION_CHECK_COUNT),
        "final_decision": decision,
    }


def _package_payloads(
    module,
    *,
    package_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    payloads = {
        "source_artifact_index.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "source_artifacts": [
                {"name": f"source_{index}", "sha256": "0" * 64}
                for index in range(module.EXPECTED_PACKAGE_PAYLOAD_FILE_COUNT + 5)
            ],
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
        "manifest_bundle_index.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "manifest_count": module.EXPECTED_MANIFEST_COUNT,
            "manifests": [
                {
                    "manifest_name": f"manifest_{index}",
                    "authorizes_execution": False,
                    "authorizes_claim": False,
                    "authorizes_promotion": False,
                }
                for index in range(module.EXPECTED_MANIFEST_COUNT)
            ],
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
        "review_chain_summary.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "review_chain": [
                {
                    "step": f"step_{index}",
                    "authorizes_execution": False,
                    "authorizes_claim": False,
                    "authorizes_promotion": False,
                }
                for index in range(5)
            ],
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
        "claim_boundary_register.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "current_dp_head": module.FIXED_DP_HEAD,
            "score_expression": module.SCORE_EXPRESSION,
            "evidence_package_constructed_by_this_gate": True,
            "direct_promotion_recommendation": False,
            "promotion_decision_plan_authorized_next": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
        "construction_static_review_plan.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "required_package_files": list(module.PACKAGE_FILES),
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
        "evidence_package_manifest.json": {
            "schema_version": module.SOURCE_PACKAGE_SCHEMA,
            "package_files": list(module.PACKAGE_FILES),
            "current_camp_head": CURRENT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "score_expression": module.SCORE_EXPRESSION,
            "evidence_package_constructed_by_this_gate": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "authorizes_execution": False,
            "authorizes_claim": False,
            "authorizes_promotion": False,
        },
    }
    for action in module.BLOCKED_ACTIONS:
        payloads["claim_boundary_register.json"][action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        payloads["claim_boundary_register.json"][flag] = False
    if package_updates:
        for file_name, updates in package_updates.items():
            payloads[file_name].update(updates)
    return payloads


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
