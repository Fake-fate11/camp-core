from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation.py"
)
HEAD = "4b8b02d0baae4996c3b5604c076fe0f2237de1a8"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_"
    "6803a93ce4_20260707T234051CST"
)
CANDIDATE_OUTPUT_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_candidates_"
    "6803a93ce4_20260707T234051CST"
)
PLAN_ROOT_SHA = "0ca5ff5106f79a2faff9651f3c6c59f9fedc74f2c87db984f3d0fe78e806fff5"
REVIEW_ROOT_SHA = "5ff9a9301567bdd1c6d3e222ff6ca3be46d1c7ac199095833851ddf76f96de33"
JSON_SHA = "8c438c2a7379f70a52f7d56c32922d224a20990a55af2ad0ef2ac8c56ae815b2"
MD_SHA = "fec4f2bebc4e5c83de021bd4d63568cdbbf46b898a148363122f0f076f93e9fc"
SHA256SUMS_SHA = "c7231046a1084a1e20b61a3339cb5142eda5044390223d8725250981505a1af1"
ROOT_SHA256SUMS_SHA = "abd611f0b99c45fd0aeed956ccafd5e4f95d5b95f20a2262c79cbde9beec1574"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_candidate_tensor_pilot_generation_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["pilot_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["pilot_execution_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert preflight["target_records"] == 1024
    assert preflight["k"] == 8
    assert preflight["candidate_count"] == 8
    assert preflight["wall_clock_seconds"] == 5447.41376
    assert preflight["wall_clock_hours"] == 1.51317
    assert preflight["runner_command_constructed"] is True
    assert preflight["runner_command_executed"] is False
    assert "run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py" in " ".join(
        preflight["runner_command_template"]
    )
    assert "JSONL records" in preflight["required_output_schema"]
    assert "MD" in preflight["required_output_schema"]
    assert "DP HEAD mismatch" in preflight["stop_conditions"]
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_candidate_tensor_pilot_generation_preflight_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "pilot_preflight_enabled" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_pilot_generation_preflight_rejects_existing_output(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["candidate_output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_pilot_generation_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_pilot_preflight" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_pilot_preflight" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_pilot_generation_preflight_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    assert f"current_v16_status={module.READY_STATUS}" in audit
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit
    for text in (audit, status):
        assert ARTIFACT in text
        assert CANDIDATE_OUTPUT_ROOT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_source_plan_root_sha256={PLAN_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_source_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_check_count=51" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_failed_checks=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_target_records=1024" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_k=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_preflight_candidate_count=8" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA256SUMS_SHA in text


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict:
    source = module.SOURCE_REVIEW_MODULE
    plan = source.PLAN_MODULE
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={source.READY_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    plan_artifact = tmp_path / "pilot_plan"
    review_artifact = tmp_path / "pilot_plan_static_review"
    plan_artifact.mkdir()
    review_artifact.mkdir()
    plan_json = plan_artifact / plan.PLAN_JSON_NAME
    plan_md = _write(plan_artifact / plan.PLAN_MD_NAME, "# Plan\n")
    _write_json(plan_json, _plan_payload(module))
    plan_sha = _write_sha256s(
        plan_artifact,
        ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", plan.PLAN_JSON_NAME, plan.PLAN_MD_NAME),
    )
    review_json = review_artifact / source.REVIEW_JSON_NAME
    review_md = _write(review_artifact / source.REVIEW_MD_NAME, "# Review\n")
    _write_json(review_json, _review_payload(module, source_plan_root_sha256=_sha256(plan_sha)))
    review_sha = _write_sha256s(
        review_artifact,
        ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", source.REVIEW_JSON_NAME, source.REVIEW_MD_NAME),
    )
    for path in (plan_md, review_md):
        assert path.is_file()
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_repo.mkdir()
    nuscenes_root = tmp_path / "nuScenes"
    _write(nuscenes_root / "README", "readable\n")
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_json,
        "source_plan_sha256s": plan_sha,
        "source_review_artifact_dir": review_artifact,
        "source_review_json": review_json,
        "source_review_sha256s": review_sha,
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "nuscenes_root": nuscenes_root,
        "camp_repo_root": ROOT,
        "dp_repo": dp_repo,
        "candidate_output_root": tmp_path / "pilot_candidates",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": _sha256(plan_sha),
        "expected_review_root_sha256": _sha256(review_sha),
        "python_executable": "python",
        "enabled": True,
    }


def _plan_payload(module) -> dict:
    plan = module.SOURCE_REVIEW_MODULE.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "final_decision": {"passed": True, "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK},
        "inputs": {
            "source_smoke_review_artifact": "/root/autodl-tmp/smoke_execution_result_review",
            "exporter_script": plan.EXPORTER_SCRIPT,
            "nuscenes_source_root": plan.NUSCENES_SOURCE_ROOT,
            "dp_fixed_head": module.FIXED_DP_HEAD,
        },
        "pilot_plan": {
            "selected_target_records": 1024,
            "k": 8,
            "candidate_count": 8,
        },
        "timing_estimates": {
            "1024": {
                "per_record_mean_seconds": 5.31974,
                "wall_clock_seconds": 5447.41376,
                "wall_clock_hours": 1.51317,
            }
        },
    }


def _review_payload(module, *, source_plan_root_sha256: str) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_MODULE.SCHEMA_VERSION,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_review_only": True,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "plan_review": {
            "source_plan_root_sha256": source_plan_root_sha256,
            "selected_target_records": 1024,
            "k": 8,
            "candidate_count": 8,
            "per_record_mean_seconds": 5.31974,
            "wall_clock_seconds_1024": 5447.41376,
            "wall_clock_hours_1024": 1.51317,
            "required_output_schema": [
                "JSON summary",
                "JSONL records",
                "MD",
                "HEADS",
                "COMMAND",
                "stdout",
                "stderr",
                "SHA256SUMS",
            ],
            "stop_conditions": [
                "output root exists",
                "DP HEAD mismatch",
                "records shortfall",
                "any fake/synthetic candidate tensor",
                "any DP/candidate/trajectory mutation",
            ],
        },
    }


def _write_sha256s(root: Path, names: tuple[str, ...]) -> Path:
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
        _write(root / name, f"{name}\n")
    path = root / "SHA256SUMS"
    path.write_text("".join(f"{_sha256(root / name)}  {name}\n" for name in names), encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
