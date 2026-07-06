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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_deployment_decision.py"
)
SOURCE_HEAD = "d" * 40
CURRENT_HEAD = "e" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_deployment_decision_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_deployment_decision_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_candidate_index_actual_safetycost_deployment_decision_plan_ready"] is True
    assert decision["objective_3200_candidate_index_actual_safetycost_deployment_decision_plan_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is True
    assert decision["deployment_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is True
    assert decision["camp_over_dp_top1_claim_authorized"] is True
    assert [item["item_name"] for item in report["deployment_decision_plan"]] == list(
        module.DEPLOYMENT_DECISION_ITEMS
    )
    assert {item["authorizes_deployment_now"] for item in report["deployment_decision_plan"]} == {False}
    assert {item["authorizes_online_selector_now"] for item in report["deployment_decision_plan"]} == {False}
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_actual_safetycost_deployment_decision_plan_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "deployment_decision_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_actual_safetycost_deployment_decision_plan_authorization_missing"
    )


def test_candidate_index_actual_safetycost_deployment_decision_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_deployment_decision_plan_rejects_source_deployment_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"deployment_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_deployment_false" in report["final_decision"]["failed_checks"]


def test_candidate_index_actual_safetycost_deployment_decision_plan_rejects_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_selector_promotion_decision_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "root_decision_md_sha" in report["final_decision"]["failed_checks"]
    assert "nested_decision_md_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_hash_mismatch"


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
            f"current_v14_status={module.SOURCE_DECISION_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_actual_safetycost_deployment_decision_plan_authorized=True",
            "selector_promotion_authorized=True",
            "deployment_authorized=False",
            "online_selector_change_authorized=False",
            "safety_benefit_claim_authorized=True",
            "camp_over_dp_top1_claim_authorized=True",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_artifact = _write_source_selector_promotion_decision_artifact(
        tmp_path / "source_selector_promotion_decision_artifact",
        module,
        source_decision_updates=source_decision_updates,
    )
    return {
        "source_selector_promotion_decision_artifact_dir": source_artifact["artifact"],
        "source_selector_promotion_decision_json": source_artifact["json"],
        "source_selector_promotion_decision_md": source_artifact["md"],
        "source_selector_promotion_decision_sha256s": source_artifact["sha256s"],
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_selector_promotion_decision_artifact(
    artifact: Path,
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Path]:
    decision_dir = artifact / "decision"
    decision_json = _write_json(
        decision_dir / module.SOURCE_DECISION_JSON_NAME,
        _source_selector_promotion_decision_report(module, source_decision_updates=source_decision_updates),
    )
    decision_md = _write(decision_dir / module.SOURCE_DECISION_MD_NAME, "# source selector promotion decision\n")
    decision_sha = _write_sha256s(decision_dir / "SHA256SUMS", [decision_json, decision_md])
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
    command = _write(artifact / "COMMAND", "python selector_promotion_decision.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, decision_json, decision_md, decision_sha],
        relative_to=artifact,
    )
    return {
        "artifact": artifact,
        "json": decision_json,
        "md": decision_md,
        "sha256s": decision_sha,
    }


def _source_selector_promotion_decision_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_DECISION_STATUS,
        "failure_class": None,
        "failed_checks": [],
        "check_count": module.EXPECTED_SOURCE_DECISION_CHECK_COUNT,
        "failed_check_count": 0,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_actual_safetycost_deployment_decision_plan_authorized": True,
        "selector_promotion_authorized": True,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": True,
        "camp_over_dp_top1_claim_authorized": True,
    }
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_DECISION_SCHEMA,
        "final_decision": decision,
    }


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_sha256s(path: Path, files: list[Path], *, relative_to: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.relative_to(relative_to).as_posix() if relative_to else file.name
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
