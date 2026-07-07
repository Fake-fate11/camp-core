from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight.py"
)
HEAD = "158c5b67e186574e0ac5a60417e80695845e0154"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_preflight_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_paired_evaluation_preflight_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["paired_evaluation_preflight_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert set(plan["required_inputs"]["evaluation_splits"]) == {"calibration", "holdout"}
    assert "train" not in plan["required_inputs"]["evaluation_splits"]
    assert tuple(plan["timing_contract"]["online_selector_latency_required_fields"]) == module.LATENCY_FIELDS
    assert tuple(plan["timing_contract"]["fallback_latency_required_fields"]) == module.LATENCY_FIELDS
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()


def test_v15_paired_evaluation_preflight_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "paired_evaluation_preflight_plan_enabled" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_preflight_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_plan" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_plan" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_preflight_plan_rejects_missing_training(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_updates={"source_training_executed": False})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_training_executed" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_preflight_plan_rejects_paired_eval_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_updates={"paired_evaluation_executed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_paired_eval_not_executed" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_updates: dict | None = None,
) -> dict:
    review = module.SOURCE_REVIEW_MODULE
    artifact = tmp_path / "source_result_review"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")
    source_json = artifact / review.REVIEW_JSON_NAME
    source_md = artifact / review.REVIEW_MD_NAME
    _write_json(source_json, _source_review_payload(module, source_updates=source_updates))
    source_md.write_text("# Offline Training Execution Result Review\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run offline training execution result review\n",
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
                review.REVIEW_JSON_NAME,
                review.REVIEW_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_result_review_artifact_dir": artifact,
        "source_result_review_json": source_json,
        "source_result_review_md": source_md,
        "source_result_review_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_review_payload(module, *, source_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "reviewed_offline_training_execution": True,
        "source_training_executed": True,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "online_selector_latency_executed": False,
        "fallback_latency_executed": False,
        "performance_claimed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if source_updates:
        decision.update(source_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
