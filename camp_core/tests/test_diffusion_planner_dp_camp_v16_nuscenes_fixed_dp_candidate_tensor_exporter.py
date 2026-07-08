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
    / "run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py"
)
HEAD = "90bce2e17d5e96c959053b0f1c44fb03cfd7384a"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_exporter", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_candidate_tensor_exporter_contract_accepts_fixed_dp_k8(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert report["runner"]["k"] == 8
    assert report["runner"]["fixed_dp_neighbor_count"] == 320
    assert report["runner"]["native_sampling_entrypoint"].endswith("guidance_gui/generate_samples.py")


def test_v16_candidate_tensor_exporter_rejects_dp_head_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["current_dp_head"] = "wrong"

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_exporter_contract_accepts_retry_gate(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work=module.AUTHORIZED_RETRY_WORK)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True


def test_v16_candidate_tensor_exporter_contract_accepts_pilot_execution_gate(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        next_work="v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_only",
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True


def test_v16_candidate_tensor_exporter_contract_accepts_scaleup_execution_gate(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        next_work="v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_only",
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True


def test_v16_candidate_tensor_exporter_rejects_k_not_8(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["k"] = 7

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "k_is_8" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_exporter_rejects_missing_real_dp_output(tmp_path: Path) -> None:
    module = _load_module()

    result = module.validate_exported_npz(tmp_path / "missing.npz", expected_k=8)

    assert result["passed"] is False
    assert "candidate_output_exists" in result["failed_checks"]


def test_v16_candidate_tensor_exporter_pads_probe_neighbors_for_fixed_dp() -> None:
    module = _load_module()
    arrays = module._fixed_dp_input_arrays(module.example_dp_input())

    assert arrays["neighbor_agents_past"].shape[0] == module.FIXED_DP_NEIGHBOR_COUNT
    assert arrays["neighbor_agents_future"].shape[0] == module.FIXED_DP_NEIGHBOR_COUNT


def test_v16_candidate_tensor_exporter_provenance_fields_and_mutation_guard(tmp_path: Path) -> None:
    module = _load_module()
    input_npz = tmp_path / "input.npz"
    np.savez(input_npz, **module.example_dp_input())
    tensor = np.arange(8 * 80 * 4, dtype=np.float32).reshape(8, 80, 4)

    record = module.build_candidate_record(
        input_npz=input_npz,
        candidate_tensor=tensor,
        camp_head=HEAD,
        dp_head=module.FIXED_DP_HEAD,
        split="mini_val",
        scene_id="scene-0001",
        sample_id="sample-0001",
        command=["python", "runner.py"],
        wall_clock_seconds=1.25,
    )

    required = {
        "split",
        "scene_id",
        "sample_id",
        "DP_HEAD",
        "CAMP_HEAD",
        "K",
        "candidate_count",
        "adapter_input_shape",
        "adapter_input_sha256",
        "candidate_tensor_shape",
        "candidate_tensor_sha256",
        "dp_top1_index",
        "camp_atom_table_sha256",
        "command",
        "wall_clock_seconds",
    }
    assert required <= set(record)
    assert record["K"] == 8
    assert record["candidate_count"] == 8
    assert record["candidate_tensor_unchanged_by_camp"] is True

    mutated = tensor.copy()
    mutated[0, 0, 0] += 1
    mutation = module.candidate_tensor_integrity(tensor, mutated)
    assert mutation["candidate_tensor_unchanged_by_camp"] is False


def _write_fixture(tmp_path: Path, module, next_work: str | None = None) -> dict:
    next_work = next_work or module.AUTHORIZED_CURRENT_WORK
    dp_repo = tmp_path / "Diffusion-Planner"
    _write(dp_repo / "guidance_gui" / "generate_samples.py", "def generate_samples(): pass\n")
    _write(dp_repo / "diffusion_planner" / "valid_predictor.py", "# top1 exporter\n")
    checkpoint = _write(dp_repo / "checkpoint.pth", "fake")
    args_json = _write_json(dp_repo / "diffusion_planner.param.json", {"future_len": 80})
    input_npz = tmp_path / "probe.npz"
    np.savez(input_npz, **module.example_dp_input())

    audit = _write(
        tmp_path / "docs" / "diffusion_planner_v16_iteration_audit.md",
        "\n".join(
            [
                "current_v16_status=v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_failed",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    status = _write(
        tmp_path / "docs" / "diffusion_planner_current_status.md",
        audit.read_text(encoding="utf-8"),
    )
    return {
        "dp_repo": dp_repo,
        "input_npz": input_npz,
        "checkpoint": checkpoint,
        "args_json": args_json,
        "output_npz": tmp_path / "out" / "candidate000000.npz",
        "v16_audit_md": audit,
        "current_status_md": status,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "k": 8,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path
