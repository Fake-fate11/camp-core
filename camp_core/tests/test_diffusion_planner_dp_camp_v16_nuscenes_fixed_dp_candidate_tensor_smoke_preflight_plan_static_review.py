from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_contract.py"
)
HEAD = "de5d52222032be1005cf1f74f7770a9ea3fc0353"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_"
    "9cdd2c8e76_20260707T161339CST"
)
JSON_SHA = "dc46f9af836a8e447f76315f08b528fd36669e03622953c8e8da5808730432b9"
MD_SHA = "d1cacaaff8e893c3299b3da84a8a14cc1a2b54d47b933d782841aec36d921df2"
SHA256SUMS_SHA = "eb263f8ea7846a1a31762f76900ac04f05a78137881f4ff7c209421cb5c76960"
ROOT_SHA256SUMS_SHA = "83afbd8cd6028d00a32fe7b31d1269dc66ad17ccfb2c53c00cafc217c0c37f45"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_smoke_preflight_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_smoke_preflight_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert report["smoke_contract"]["k"] == 8
    assert report["smoke_contract"]["candidate_count"] == 8
    assert report["smoke_contract"]["must_record_candidate_tensor_shape_hash"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v16_nuscenes_smoke_preflight_plan_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_plan_static_review_rejects_non_k8(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, k=16)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_plan_k8" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    assert f"current_v16_status={module.READY_STATUS}" in audit
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit
    for text in (audit, status):
        assert ARTIFACT in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_check_count=42" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_failed_checks=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_k=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_candidate_count=8" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA256SUMS_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    k: int = 8,
) -> dict:
    source = module.PLAN_MODULE
    artifact = tmp_path / "smoke_preflight_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v16_status={source.READY_STATUS}",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / source.PLAN_JSON_NAME
    source_md = artifact / source.PLAN_MD_NAME
    _write_json(source_json, _source_payload(module, k=k))
    source_md.write_text("# Smoke Preflight Plan\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run smoke preflight plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    (artifact / "SHA256SUMS").write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                source.PLAN_JSON_NAME,
                source.PLAN_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": source_json,
        "source_plan_md": source_md,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_payload(module, *, k: int) -> dict:
    return {
        "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
        "smoke_preflight_plan": {
            "candidate_generation": {"k": k, "candidate_count": k},
            "must_record": [
                "adapter_input_shape",
                "candidate_tensor_shape",
                "candidate_tensor_sha256",
                "dp_top1_index",
                "camp_atom_table_sha256",
            ],
            "records": {"min_records": 100, "max_records": 1000},
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
