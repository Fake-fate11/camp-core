from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_source_inventory_preflight_static_contract.py"
)
HEAD = "36cc0b9a76f41fd457925af57fc4c9325153c088"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_source_inventory_preflight_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_source_inventory_preflight_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["inventory_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_source_inventory_preflight_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_source_inventory_preflight_static_review_rejects_missing_requirement(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_requirement=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "inventory_requirement_timing_artifact_contract" in report["final_decision"]["failed_checks"]


def test_v15_source_inventory_preflight_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v15_source_inventory_preflight_static_review_is_recorded() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v15_iteration_audit.md").read_text(
        encoding="utf-8"
    )

    assert (
        "v15_broader_nonformal_evidence_expansion_source_inventory_preflight_static_review_status="
        f"{module.READY_STATUS}"
        in audit_text
    )
    assert (
        "v15_broader_nonformal_evidence_expansion_source_inventory_preflight_static_review_authorized_next_work="
        f"{module.AUTHORIZED_NEXT_WORK}"
        in audit_text
    )


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    drop_requirement: bool = False,
) -> dict:
    preflight = module.PREFLIGHT_MODULE
    artifact = tmp_path / "source_preflight"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")

    source_json = artifact / preflight.PREFLIGHT_JSON_NAME
    source_md = artifact / preflight.PREFLIGHT_MD_NAME
    requirements = list(preflight.INVENTORY_REQUIREMENTS)
    if drop_requirement:
        requirements.remove("timing_artifact_contract")
    _write_json(source_json, _source_preflight_payload(module, requirements))
    source_md.write_text("# Source Inventory Preflight\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run source inventory preflight\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    sha_path = artifact / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                preflight.PREFLIGHT_JSON_NAME,
                preflight.PREFLIGHT_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_preflight_artifact_dir": artifact,
        "source_preflight_json": source_json,
        "source_preflight_md": source_md,
        "source_preflight_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_payload(module, requirements: list[str]) -> dict:
    return {
        "schema_version": module.PREFLIGHT_MODULE.SCHEMA_VERSION,
        "inventory_requirements": requirements,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
