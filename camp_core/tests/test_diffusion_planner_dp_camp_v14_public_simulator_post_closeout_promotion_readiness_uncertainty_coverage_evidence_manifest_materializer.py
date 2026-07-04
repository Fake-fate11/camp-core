from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "materialize_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifests.py"
)
ARTIFACT_HEAD = "1" * 40
CURRENT_HEAD = "2" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materializer",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uncertainty_coverage_evidence_manifest_materializer_writes_five_manifests(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], fixture["manifest_output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_manifest_materialized_by_this_gate"] is True
    assert decision["materialized_manifest_count"] == 5
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(report["materialized_manifest_files"]) == 5
    for item in report["materialized_manifest_files"]:
        path = Path(item["path"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == module.MANIFEST_SCHEMA_VERSION
        assert payload["materialized_by_this_gate"] is True
        assert payload["authorizes_execution"] is False
        assert payload["authorizes_claim"] is False
    assert (fixture["manifest_output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()


def test_uncertainty_coverage_evidence_manifest_materializer_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "materialization_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_uncertainty_coverage_evidence_manifest_materialization_authorization_missing"
    )


def test_uncertainty_coverage_evidence_manifest_materializer_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_materialization" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_materialization" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_uncertainty_coverage_evidence_manifest_materializer_rejects_unapproved_source_review(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_review_decision_updates={"evidence_manifest_materialization_authorized": False},
    )

    report = module.build_report(**fixture)

    assert "source_review_authorizes_materialization" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_evidence_manifest_materialization_contract_failure"


def test_uncertainty_coverage_evidence_manifest_materializer_rejects_existing_manifest_dir(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["manifest_output_dir"].mkdir(parents=True)

    report = module.build_report(**fixture)

    assert "manifest_output_dir_absent_before_write" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "artifact_contract_failure"


def test_uncertainty_coverage_evidence_manifest_materializer_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    exit_code = module.main(
        [
            "--materialization_static_review_artifact_dir",
            str(fixture["materialization_static_review_artifact_dir"]),
            "--materialization_static_review_json",
            str(fixture["materialization_static_review_json"]),
            "--materialization_static_review_md",
            str(fixture["materialization_static_review_md"]),
            "--materialization_static_review_sha256s",
            str(fixture["materialization_static_review_sha256s"]),
            "--source_plan_artifact_dir",
            str(fixture["source_plan_artifact_dir"]),
            "--source_plan_json",
            str(fixture["source_plan_json"]),
            "--source_plan_sha256s",
            str(fixture["source_plan_sha256s"]),
            "--manifest_output_dir",
            str(fixture["manifest_output_dir"]),
            "--v14_audit_md",
            str(fixture["v14_audit_md"]),
            "--current_status_md",
            str(fixture["current_status_md"]),
            "--output_dir",
            str(fixture["output_dir"]),
            "--current_camp_head",
            CURRENT_HEAD,
            "--current_camp_origin_main",
            CURRENT_HEAD,
            "--current_dp_head",
            module.FIXED_DP_HEAD,
            "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization",
        ]
    )

    assert exit_code == 0
    assert len(list(fixture["manifest_output_dir"].glob("*.json"))) == 5
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_review_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_artifact = tmp_path / "static_review_artifact"
    review_dir = review_artifact / "review"
    plan_artifact = tmp_path / "plan_artifact"
    plan_dir = plan_artifact / "plan"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "evidence_manifest_materialization_authorized=True",
            "evidence_manifest_materialized_by_this_gate=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    plan_json = _write_json(plan_dir / module.SOURCE_PLAN_JSON_NAME, _source_plan_payload(module))
    plan_sha256s = _write_sha256sums(plan_dir / "SHA256SUMS", [plan_json])
    _write_sha256sums(plan_artifact / "SHA256SUMS", [plan_json], relative_to=plan_artifact)

    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_review_payload(module, decision_updates=source_review_decision_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# Static Review\n")
    review_sha256s = _write_sha256sums(review_dir / "SHA256SUMS", [review_json, review_md])
    command = _write(review_artifact / "COMMAND", "static review command\n")
    heads = _write(
        review_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={ARTIFACT_HEAD}",
                f"CAMP_ORIGIN_MAIN={ARTIFACT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(review_artifact / "stdout.txt", "ok\n")
    stderr = _write(review_artifact / "stderr.txt", "")
    run_exit = _write(review_artifact / "run.exit", "0\n")
    _write_sha256sums(
        review_artifact / "SHA256SUMS",
        [command, heads, stdout, stderr, run_exit, review_json, review_md],
        relative_to=review_artifact,
    )
    return {
        "materialization_static_review_artifact_dir": review_artifact,
        "materialization_static_review_json": review_json,
        "materialization_static_review_md": review_md,
        "materialization_static_review_sha256s": review_sha256s,
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_json,
        "source_plan_sha256s": plan_sha256s,
        "manifest_output_dir": tmp_path / "manifests",
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_plan_payload(module) -> dict[str, Any]:
    manifests = [
        {
            "manifest_name": name,
            "source_gap": f"gap_for_{name}",
            "planned_path": f"/future/{name}.json",
            "required_inputs": ["source_review"],
            "acceptance_checks": ["read_only"],
            "materialized_by_this_gate": False,
            "authorizes_execution": False,
            "authorizes_claim": False,
        }
        for name in module.EXPECTED_MANIFESTS
    ]
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "evidence_manifest_materialization_plan": manifests,
        "plan_checks": [{"name": f"check_{index}", "passed": True} for index in range(139)],
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failure_class": None,
            "failed_checks": [],
            "authorized_next_work": module.REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
        },
    }


def _source_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "evidence_manifest_materialization_authorized": True,
        "evidence_manifest_materialized_by_this_gate": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "current_camp_head": ARTIFACT_HEAD,
            "current_camp_origin_main": ARTIFACT_HEAD,
            "current_dp_head": module.FIXED_DP_HEAD,
        },
        "source_plan_summary": {
            "plan_check_count": 139,
            "manifest_plan_item_count": 5,
        },
        "review_checks": [{"name": f"check_{index}", "passed": True} for index in range(153)],
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
