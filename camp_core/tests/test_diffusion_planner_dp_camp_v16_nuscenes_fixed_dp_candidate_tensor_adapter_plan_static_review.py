from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_contract.py"
)
HEAD = "aafbde586f882bafd51a27ec73b690ef43f493e1"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_adapter_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_adapter_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["adapter_execution_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert report["smoke_contract"]["must_record_candidate_tensor_shape_hash"] is True
    assert report["adapter_contract"]["candidate_tensor_immutable_after_dp"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v16_nuscenes_adapter_plan_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_static_review_rejects_missing_hash_record(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_smoke_record="candidate_tensor_sha256")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "adapter_plan_records_candidate_tensor_sha256" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v16_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert f"current_v16_status={module.READY_STATUS}" in status_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    drop_smoke_record: str | None = None,
) -> dict:
    source = module.PLAN_MODULE
    artifact = tmp_path / "adapter_plan"
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
    payload = _source_payload(module)
    if drop_smoke_record is not None:
        payload["adapter_plan"]["smoke"]["must_record"].remove(drop_smoke_record)
    _write_json(source_json, payload)
    source_md.write_text("# Adapter Plan\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run adapter plan\n",
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
        "adapter_plan_artifact_dir": artifact,
        "adapter_plan_json": source_json,
        "adapter_plan_md": source_md,
        "adapter_plan_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_payload(module) -> dict:
    return {
        "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
        "adapter_plan": {
            "candidate_tensor_contract": {
                "dp_commit": module.FIXED_DP_HEAD,
                "immutable_after_dp": True,
            },
            "camp_atom_contract": {
                "score": "score_k(w)=a_k^T w",
                "weights": "nonnegative_simplex",
                "trajectory_generation_repair_rewrite_blend": False,
            },
            "input_mapping": {
                name: {"source": name, "adapter": name}
                for name in module.PLAN_MODULE.SOURCE_REVIEW_MODULE.PREFLIGHT_MODULE.DP_INPUT_REQUIREMENTS
            },
            "smoke": {
                "min_records": 100,
                "max_records": 1000,
                "training_executed": False,
                "must_record": [
                    "adapter_input_shape",
                    "candidate_tensor_shape",
                    "candidate_tensor_sha256",
                    "dp_top1_index",
                    "camp_atom_table_sha256",
                ],
            },
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "adapter_execution_executed": False,
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
