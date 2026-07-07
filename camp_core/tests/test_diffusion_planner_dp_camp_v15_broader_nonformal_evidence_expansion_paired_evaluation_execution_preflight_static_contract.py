from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_static_contract.py"
)
HEAD = "638dc2d7670e5a6fa7ac4edec5c55ffff6d93a77"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v15_paired_evaluation_execution_preflight_static_review", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_paired_evaluation_execution_preflight_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_paired_evaluation_execution_preflight"] is True
    assert decision["paired_evaluation_execution_preflight_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["online_selector_latency_executed"] is False
    assert decision["fallback_latency_executed"] is False
    assert decision["training_executed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_paired_evaluation_execution_preflight_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_preflight_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_preflight_static_review_rejects_execution_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_updates={"paired_evaluation_executed": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_paired_eval_not_executed" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_preflight_static_review_rejects_timing_behavior_change(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        timing_updates={"instrumentation_changes_selector_behavior": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "timing_changes_selector_behavior" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_preflight_static_review_is_latest_status() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v15_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v15_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert f"current_v15_status={module.READY_STATUS}" in status_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_updates: dict | None = None,
    timing_updates: dict | None = None,
) -> dict:
    preflight_module = module.PREFLIGHT_MODULE
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
    timing = _timing_payload()
    if timing_updates:
        timing.update(timing_updates)
    source_json = artifact / preflight_module.PREFLIGHT_JSON_NAME
    source_md = artifact / preflight_module.PREFLIGHT_MD_NAME
    timing_json = artifact / preflight_module.TIMING_JSON_NAME
    timing_md = artifact / preflight_module.TIMING_MD_NAME
    _write_json(source_json, _source_preflight_payload(module, timing, source_updates=source_updates))
    source_md.write_text("# Paired Evaluation Execution Preflight\n", encoding="utf-8")
    _write_json(timing_json, timing)
    timing_md.write_text("# Timing\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run paired evaluation execution preflight\n",
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
                preflight_module.PREFLIGHT_JSON_NAME,
                preflight_module.PREFLIGHT_MD_NAME,
                preflight_module.TIMING_JSON_NAME,
                preflight_module.TIMING_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_preflight_artifact_dir": artifact,
        "source_preflight_json": source_json,
        "source_preflight_md": source_md,
        "source_timing_json": timing_json,
        "source_timing_md": timing_md,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_payload(
    module,
    timing: dict,
    *,
    source_updates: dict | None = None,
) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "paired_evaluation_execution_preflight_executed": True,
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
        "schema_version": module.PREFLIGHT_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
        "paired_evaluation_execution_preflight": _source_preflight_contract(module, timing),
        "timing_contract": timing,
    }


def _source_preflight_contract(module, timing: dict) -> dict:
    return {
        "blocked_inputs": {
            "Full36": False,
            "formal_seeds_11_12_13": False,
            "train_split_for_evaluation": False,
        },
        "mutations": {
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
        "paired_protocol": {
            "baseline": "dp_top1",
            "camp_selection_policy": "select_from_fixed_dp_candidate_tensor",
            "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
        },
        "required_inputs": {
            "evaluation_splits": ("calibration", "holdout"),
        },
        "timing_contract": timing,
    }


def _timing_payload() -> dict:
    return {
        "instrumentation_changes_selector_behavior": False,
        "online_selector_latency_required_fields": ["count", "mean", "median", "p95", "p99", "max"],
        "fallback_latency_required_fields": ["count", "mean", "median", "p95", "p99", "max"],
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
