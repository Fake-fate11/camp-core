import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "validate_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_zero_overlap", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _patch_small(module, monkeypatch) -> None:
    monkeypatch.setattr(module, "EXPECTED_LOG_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_STEPS_PER_LOG", 3)
    monkeypatch.setattr(module, "EXPECTED_RECORDS", 6)


def _record(step: int, tensor_hash: str) -> dict:
    return {
        "selection_step": step,
        "selected_index": 0,
        "executed_index": 0,
        "num_candidates": 8,
        "candidate_reference_blend": None,
        "candidate_closed_loop_outcomes": None,
        "candidate_generation_contract": {"guidance_enabled": False},
        "default_off_shadow_selector": {
            "candidate_tensor_hash": {"sha256": tensor_hash},
        },
        "camp_candidate_tensor_provenance": {
            "pre_camp_scoring_tensor": {"sha256": tensor_hash},
            "post_camp_selector_tensor": {"sha256": tensor_hash},
        },
    }


def _fixture(tmp_path: Path, module):
    root = tmp_path / "execution_outputs"
    for log_index, seed in enumerate((1, 2), start=1):
        out_dir = root / "route_a" / f"seed_{seed}" / "tl_on" / "fixed_dp_top1_execution"
        records = [
            _record(step, f"hash_{log_index}_{step}") for step in range(3)
        ]
        _write_json(out_dir / "camp_selection_log.json", records)
        _write_json(
            out_dir / "camp_validation_summary.json",
            {
                "benchmark": {
                    "route": f"/route/{log_index}.pkl",
                    "map_path": "/map.osm",
                    "seed": seed,
                    "traffic_lights": True,
                    "steps": 3,
                }
            },
        )
    execution_report = tmp_path / "execution_report.json"
    _write_json(
        execution_report,
        {
            "final_decision": {
                "passed": True,
                "status": "public_simulator_fixed_dp_candidate_generation_execution_passed",
            },
            "execution": {"commands_succeeded": 2},
        },
    )
    audit = tmp_path / "docs" / "diffusion_planner_v14_iteration_audit.md"
    _write_json(tmp_path / "dummy.json", {})
    audit.parent.mkdir(parents=True)
    audit.write_text(
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    status = tmp_path / "docs" / "diffusion_planner_current_status.md"
    status.write_text(
        "\n".join([module.EXPECTED_CURRENT_STATUS, module.AUTHORIZED_CURRENT_WORK, ""]),
        encoding="utf-8",
    )
    refs = tmp_path / "refs"
    ref_files = {
        "reference_candidate_tensor_hash_registry_json": refs / "training_candidate_tensor_hash_registry.json",
        "reference_path_signature_registry_json": refs / "training_path_signature_registry.json",
        "reference_record_identity_registry_json": refs / "training_record_identity_registry.json",
        "reference_split_manifest_root_registry_json": refs / "training_split_manifest_root_registry.json",
    }
    for path in ref_files.values():
        _write_json(path, {"values": [f"old_{path.stem}"]})
    kwargs = {
        "execution_output_root": root,
        "execution_report_json": execution_report,
        "v14_audit_md": audit,
        "current_status_md": status,
        "output_dir": tmp_path / "out",
        "current_camp_head": "abc",
        "current_camp_origin_main": "abc",
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        **ref_files,
    }
    return kwargs


def test_v14_zero_overlap_validation_passes_and_writes_registries(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert report["registry_summary"]["selection_log_count"] == 2
    assert report["registry_summary"]["record_count"] == 6
    assert report["registry_summary"]["candidate_tensor_hash_count"] == 6
    assert report["registry_summary"]["path_signature_count"] == 2
    assert report["registry_summary"]["record_identity_hash_count"] == 6
    assert report["zero_intersection_counts"] == {
        "candidate_tensor_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }
    assert (kwargs["output_dir"] / "candidate_tensor_hash_registry.json").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_zero_overlap_validation_rejects_candidate_hash_intersection(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)
    _write_json(
        kwargs["reference_candidate_tensor_hash_registry_json"],
        {"values": ["hash_1_0"]},
    )

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert (
        "candidate_tensor_hash_intersection_count"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "zero_overlap_intersection_nonzero"


def test_v14_zero_overlap_validation_rejects_empty_reference_registry(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)
    _write_json(kwargs["reference_record_identity_registry_json"], {"values": []})

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "reference_record_identity_hashes_nonempty" in report["final_decision"]["failed_checks"]


def test_v14_zero_overlap_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    exit_code = module.main(
        [
            "--execution_output_root",
            str(kwargs["execution_output_root"]),
            "--execution_report_json",
            str(kwargs["execution_report_json"]),
            "--v14_audit_md",
            str(kwargs["v14_audit_md"]),
            "--current_status_md",
            str(kwargs["current_status_md"]),
            "--output_dir",
            str(kwargs["output_dir"]),
            "--current_camp_head",
            kwargs["current_camp_head"],
            "--current_camp_origin_main",
            kwargs["current_camp_origin_main"],
            "--current_dp_head",
            kwargs["current_dp_head"],
            "--reference_candidate_tensor_hash_registry_json",
            str(kwargs["reference_candidate_tensor_hash_registry_json"]),
            "--reference_path_signature_registry_json",
            str(kwargs["reference_path_signature_registry_json"]),
            "--reference_record_identity_registry_json",
            str(kwargs["reference_record_identity_registry_json"]),
            "--reference_split_manifest_root_registry_json",
            str(kwargs["reference_split_manifest_root_registry_json"]),
        ]
    )

    assert exit_code == 0
    assert (kwargs["output_dir"] / "zero_overlap_validation_report.json").is_file()
    assert module.READY_STATUS in (
        kwargs["output_dir"] / "zero_overlap_validation_report.json"
    ).read_text(encoding="utf-8")
