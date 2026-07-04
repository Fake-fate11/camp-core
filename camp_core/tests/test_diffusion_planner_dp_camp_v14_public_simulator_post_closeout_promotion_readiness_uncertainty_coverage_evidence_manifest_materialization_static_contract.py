from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_contract.py"
)
ARTIFACT_HEAD = "3" * 40
CURRENT_HEAD = "4" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_contract",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_passes(
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
    assert decision["evidence_package_construction_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["manifest_summary"]["manifest_count"] == 5
    assert report["manifest_summary"]["all_no_execution"] is True
    assert report["manifest_summary"]["all_no_claim"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_manifest_materialization_static_review_authorization_missing"
    )


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_rejects_source_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"selector_promotion_authorized": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_materialization_decision_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_rejects_manifest_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, manifest_updates={"no_go_summary": {"authorizes_claim": True}})

    report = module.build_report(**fixture)

    assert "manifest_no_go_summary_no_claim" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_evidence_manifest_materialization_static_review_contract_failure"
    )


def test_uncertainty_coverage_evidence_manifest_materialization_static_contract_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    output_dir = tmp_path / "cli_out"

    exit_code = module.main(
        [
            "--evidence_manifest_materialization_artifact_dir",
            str(fixture["evidence_manifest_materialization_artifact_dir"]),
            "--evidence_manifest_materialization_json",
            str(fixture["evidence_manifest_materialization_json"]),
            "--evidence_manifest_materialization_md",
            str(fixture["evidence_manifest_materialization_md"]),
            "--evidence_manifest_materialization_sha256s",
            str(fixture["evidence_manifest_materialization_sha256s"]),
            "--evidence_manifests_dir",
            str(fixture["evidence_manifests_dir"]),
            "--evidence_manifests_sha256s",
            str(fixture["evidence_manifests_sha256s"]),
            "--materializer_script_py",
            str(fixture["materializer_script_py"]),
            "--materializer_test_py",
            str(fixture["materializer_test_py"]),
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
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review",
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
    manifest_updates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "materialization_artifact"
    materialization_dir = artifact / "materialization"
    manifests_dir = artifact / "manifests"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_MATERIALIZATION_STATUS}",
            f"next_work_target={current_next}",
            "uncertainty_coverage_evidence_manifest_materialized=True",
            "evidence_manifest_materialization_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    materialized_files = []
    manifest_paths = []
    for name in module.EXPECTED_MANIFESTS:
        manifest = _manifest_payload(module, name, manifests_dir / f"{name}.json")
        if manifest_updates and name in manifest_updates:
            manifest.update(manifest_updates[name])
        path = _write_json(manifests_dir / f"{name}.json", manifest)
        manifest_paths.append(path)
        materialized_files.append({"manifest_name": name, "path": str(path), "sha256": _sha256(path)})
    manifests_sha256s = _write_sha256sums(manifests_dir / "SHA256SUMS", manifest_paths)

    materialization_json = _write_json(
        materialization_dir / module.SOURCE_MATERIALIZATION_JSON_NAME,
        _source_materialization_payload(module, materialized_files, decision_updates=source_decision_updates),
    )
    materialization_md = _write(materialization_dir / module.SOURCE_MATERIALIZATION_MD_NAME, "# Materialization\n")
    materialization_sha256s = _write_sha256sums(
        materialization_dir / "SHA256SUMS",
        [materialization_json, materialization_md],
    )
    command = _write(artifact / "COMMAND", "materialize command\n")
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
        [command, heads, stdout, stderr, run_exit, materialization_json, materialization_md, *manifest_paths],
        relative_to=artifact,
    )
    materializer_script = _write(
        tmp_path / "materializer.py",
        "evidence_manifest_materialization_v1\n"
        "evidence_manifest_materialization_static_review_only\n",
    )
    materializer_test = _write(
        tmp_path / "test_materializer.py",
        "writes_five_manifests\nrejects_existing_manifest_dir\n",
    )
    return {
        "evidence_manifest_materialization_artifact_dir": artifact,
        "evidence_manifest_materialization_json": materialization_json,
        "evidence_manifest_materialization_md": materialization_md,
        "evidence_manifest_materialization_sha256s": materialization_sha256s,
        "evidence_manifests_dir": manifests_dir,
        "evidence_manifests_sha256s": manifests_sha256s,
        "materializer_script_py": materializer_script,
        "materializer_test_py": materializer_test,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _manifest_payload(module, name: str, path: Path) -> dict[str, Any]:
    return {
        "schema_version": module.MANIFEST_SCHEMA_VERSION,
        "manifest_name": name,
        "source_gap": f"gap_for_{name}",
        "source_planned_path": f"/future/{name}.json",
        "materialized_path": str(path),
        "required_inputs": ["source_review"],
        "acceptance_checks": ["read_only"],
        "source_static_review_status": module.MATERIALIZER_MODULE.SOURCE_REVIEW_STATUS,
        "source_static_review_authorized_next_work": module.MATERIALIZER_MODULE.AUTHORIZED_CURRENT_WORK,
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


def _source_materialization_payload(
    module,
    materialized_files: list[dict[str, str]],
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_MATERIALIZATION_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "evidence_manifest_materialization_static_review_authorized": True,
        "evidence_manifest_materialized_by_this_gate": True,
        "materialized_manifest_count": 5,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_MATERIALIZATION_SCHEMA,
        "analysis": {
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
        },
        "materialization_checks": [
            {"name": f"check_{index}", "passed": True, "observed": True, "expected": True}
            for index in range(200)
        ],
        "materialized_manifest_files": materialized_files,
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
    for file_path in files:
        digest = _sha256(file_path)
        name = str(file_path.relative_to(relative_to)) if relative_to else file_path.name
        rows.append(f"{digest}  {name.replace(chr(92), '/')}")
    return _write(path, "\n".join(rows) + "\n")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
