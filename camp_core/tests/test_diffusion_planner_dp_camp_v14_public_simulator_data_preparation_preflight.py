import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_data_preparation.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_data_prep_preflight", SCRIPT_PATH)
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


def _record(step: int, tensor_hash: str, *, candidate_count: int = 8) -> dict:
    atom_version, atom_names = atom_schema_for_dimension(14)
    atoms = [[float(i + 1) for i in range(14)] for _ in range(candidate_count)]
    return {
        "selection_step": step,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 0,
        "num_candidates": candidate_count,
        "atoms": atoms,
        "normalized_atoms": atoms,
        "atom_schema_version": atom_version,
        "atom_names": list(atom_names),
        "feasible_mask": [True] + [False] * (candidate_count - 1),
        "candidate_closed_loop_outcomes": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": candidate_count,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "camp_candidate_tensor_provenance": {
            "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "candidate_count": candidate_count,
            "post_selector_candidate_count": candidate_count,
            "selected_index": 0,
            "pre_camp_scoring_tensor": {
                "sha256": tensor_hash,
                "shape": [candidate_count, 16, 3],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
            "post_camp_selector_tensor": {
                "sha256": tensor_hash,
                "shape": [candidate_count, 16, 3],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_gate: bool = False, zero_passed: bool = True):
    execution_root = tmp_path / "execution"
    logs = []
    for log_index, seed in enumerate((1, 2), start=1):
        out_dir = execution_root / f"route_{log_index}" / f"seed_{seed}"
        records = [
            _record(step, f"{log_index:02x}{step:02x}" * 16) for step in range(3)
        ]
        _write_json(out_dir / "camp_selection_log.json", records)
        logs.append(out_dir / "camp_selection_log.json")

    zero_dir = tmp_path / "zero_overlap"
    zero_dir.mkdir()
    zero_decision = {
        "passed": zero_passed,
        "status": (
            "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed"
            if zero_passed
            else "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_rejected"
        ),
        "failed_checks": [] if zero_passed else ["candidate_tensor_hash_intersection_count"],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK if zero_passed else None,
    }
    intersections = {
        "candidate_tensor_hash_intersection_count": 0 if zero_passed else 1,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }
    summary = {
        "selection_log_count": 2,
        "record_count": 6,
        "wrong_step_logs": [],
        "candidate_tensor_hash_count": 6,
        "path_signature_count": 2,
        "record_identity_hash_count": 6,
        "formal_seed_intersection": [],
        "tensor_hash_mismatches": 0,
        "executed_non_top1": 0,
        "default_off_missing": 0,
        "provenance_missing": 0,
        "closed_loop_collect_count": 0,
        "forbidden_runtime_flags": 0,
    }
    _write_json(zero_dir / "zero_overlap_validation_report.json", {
        "final_decision": zero_decision,
        "registry_summary": summary,
        "zero_intersection_counts": intersections,
    })
    _write_json(zero_dir / "selection_logs.json", [str(path) for path in logs])
    for name in (
        "candidate_tensor_hash_registry",
        "path_signature_registry",
        "record_identity_hash_registry",
        "split_manifest_root_registry",
    ):
        _write_json(zero_dir / f"{name}.json", {"values": ["old"]})

    v14_audit = tmp_path / "docs" / "diffusion_planner_v14_iteration_audit.md"
    target = "old_gate" if wrong_gate else module.AUTHORIZED_CURRENT_WORK
    v14_audit.parent.mkdir(parents=True)
    v14_audit.write_text(
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={target}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_status = tmp_path / "docs" / "diffusion_planner_current_status.md"
    current_status.write_text(
        "\n".join(
            [
                module.EXPECTED_CURRENT_STATUS,
                module.AUTHORIZED_CURRENT_WORK,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "execution_output_root": execution_root,
        "zero_overlap_artifact_dir": zero_dir,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": "abc",
        "current_camp_origin_main": "abc",
        "current_dp_head": module.FIXED_DP_HEAD,
    }


def test_v14_data_preparation_preflight_passes_and_plans_training_inputs(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)

    decision = report["final_decision"]
    manifest = report["training_input_manifest"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_preflight_authorized_next"] is True
    assert decision["training_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["score_expression"] == "score_k(w)=a_k^T w"
    assert decision["approved_atoms_nonnegative_simplex_only"] is True
    assert decision["simplex_cvar_l2_master_convexity_preserved"] is True
    assert report["training_data_contract"]["passed"] is True
    assert report["training_data_contract"]["records"] == 6
    assert manifest["fixed_dp_candidate_tensor_only"] is True
    assert manifest["expected_records"] == 6
    assert len(manifest["selection_logs"]) == 2


def test_v14_data_preparation_preflight_rejects_wrong_eof_gate(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, wrong_gate=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_v14_data_preparation_preflight_rejects_failed_zero_overlap(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, zero_passed=False)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "zero_overlap_passed" in report["final_decision"]["failed_checks"]
    assert "candidate_tensor_hash_intersection_count" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_v14_data_preparation_preflight_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    exit_code = module.main(
        [
            "--execution_output_root",
            str(kwargs["execution_output_root"]),
            "--zero_overlap_artifact_dir",
            str(kwargs["zero_overlap_artifact_dir"]),
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
        ]
    )

    assert exit_code == 0
    assert (kwargs["output_dir"] / "training_input_manifest.json").is_file()
    assert (kwargs["output_dir"] / "data_preparation_preflight_report.json").is_file()
    assert (kwargs["output_dir"] / "data_preparation_preflight_report.md").is_file()
    assert (kwargs["output_dir"] / "run_data_preparation_preflight.sh").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()
