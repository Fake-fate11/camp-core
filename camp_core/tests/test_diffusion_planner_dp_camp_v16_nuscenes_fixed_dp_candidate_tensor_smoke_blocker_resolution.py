from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "resolve_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.py"
)
HEAD = "99cd21d303c9a07170a23c4293889594080d2dd3"
SOURCE_BLOCKER = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_candidates_"
    "01b4306d15_20260707T162331CST"
)
SOURCE_BLOCKER_ROOT_SHA = "08b241752485eeddfde46a9a62c86d01525371bf31914797ecc4967cfa6c84dc"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_smoke_blocker_resolution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_smoke_blocker_resolution_passes_with_probe_npz(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_retry_allowed"] is True
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["dp_modified"] is False
    assert report["source_blocker"]["root_sha256s_sha256"] == _sha256(
        fixture["source_blocker_root_sha256s"]
    )
    assert report["metadata_resolution"]["tables_readable_by_trajdata"] is True
    assert report["metadata_resolution"]["extracted_large_blobs"] is False
    assert report["dp_input_probe"]["valid_set_list_loadable"] is True
    assert report["dp_input_probe"]["fields_materialized"] == sorted(module.DP_INPUT_SCHEMA)
    assert report["remaining_gaps"] == []
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()


def test_v16_nuscenes_smoke_blocker_resolution_rejects_missing_probe_npz(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["probe_npz"] = tmp_path / "missing.npz"

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "probe_npz_exists" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_blocker_resolution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "status_authorizes_blocker_resolution" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict:
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_BLOCKER_STATUS}",
            f"current_v16_artifact={SOURCE_BLOCKER}",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    blocker = tmp_path / "source_blocker"
    blocker.mkdir()
    blocker_json = blocker / "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.json"
    _write_json(
        blocker_json,
        {
            "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_v1",
            "status": module.SOURCE_BLOCKER_STATUS,
            "source_preflight_artifact": "/root/autodl-tmp/preflight",
            "final_decision": {
                "passed": False,
                "status": module.SOURCE_BLOCKER_STATUS,
                "failed_checks": [
                    "nuscenes_tables_readable_by_trajdata",
                    "dp_format_valid_set_list_materialized",
                    "v16_smoke_execution_runner_available",
                ],
                "failure_class": "missing_extracted_nuscenes_tables_and_missing_dp_input_materializer",
                "candidate_generation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
            "heads": {
                "camp_head": "4b1d19395c3b0cf7c4aa379e7c923ea8d3ffeb97",
                "camp_origin_main": "4b1d19395c3b0cf7c4aa379e7c923ea8d3ffeb97",
                "dp_head": module.FIXED_DP_HEAD,
                "required_dp_head": module.FIXED_DP_HEAD,
            },
        },
    )
    for name, content in {
        "HEADS": f"CAMP_HEAD=4b1d19395c3b0cf7c4aa379e7c923ea8d3ffeb97\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "pre-execution blocker probe\n",
        "stdout.txt": "records_written=0\n",
        "stderr.txt": "BLOCKER\n",
        "run.exit": "2\n",
        "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.md": "# Blocker\n",
        "ROOT_SHA256SUMS": f"{SOURCE_BLOCKER_ROOT_SHA}  SHA256SUMS\n",
    }.items():
        _write(blocker / name, content)
    (blocker / "SHA256SUMS").write_text(
        "\n".join(
            f"{_sha256(blocker / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                blocker_json.name,
                "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.md",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    metadata_root = tmp_path / "metadata"
    for table in module.NUSCENES_MINI_TABLES:
        _write(metadata_root / "v1.0-mini" / table, "[]\n")
    for map_name in module.NUSCENES_MAP_EXPANSION_JSONS:
        _write(metadata_root / "maps" / "expansion" / map_name, "{}\n")
    _write(metadata_root / "maps" / "93406b464a165eaba6d9de76ca09f5da.png", "png")

    dp_repo = tmp_path / "Diffusion-Planner"
    _write(dp_repo / "diffusion_planner" / "valid_predictor.py", "--valid_set_list\n")
    _write(dp_repo / "diffusion_planner" / "diffusion_planner" / "utils" / "dataset.py", "")
    fixture_npz = dp_repo / "scenario_generation" / "tests" / "test_data" / "fixture_scene.npz"
    fixture_npz.parent.mkdir(parents=True)
    np.savez(fixture_npz, **module.example_dp_input())

    probe_npz = tmp_path / "probe" / "probe_dp_input_000000.npz"
    probe_npz.parent.mkdir()
    np.savez(probe_npz, **module.example_dp_input())
    valid_set_list = tmp_path / "probe" / "valid_set_list.json"
    _write_json(valid_set_list, {"files": [str(probe_npz)]})

    return {
        "source_blocker_artifact_dir": blocker,
        "source_blocker_json": blocker_json,
        "source_blocker_sha256s": blocker / "SHA256SUMS",
        "source_blocker_root_sha256s": blocker / "ROOT_SHA256SUMS",
        "metadata_root": metadata_root,
        "dp_repo": dp_repo,
        "probe_npz": probe_npz,
        "valid_set_list": valid_set_list,
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
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
