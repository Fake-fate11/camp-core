from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training.py"
)
HEAD = "c6be3928ca46d4b01da5adb38ddfa95f2a5b3ecd"
SPLIT_EXECUTION_ROOT_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"
SPLIT_REVIEW_ROOT_SHA = "028e40a2bf2c9c4fc9300660371079656a931e1dce8d3e9fc8c0a51a84f3d1e2"
PLAN_ROOT_SHA = "bc0c5b63a26dd035fcfd74a74df6465df173597278aacc95f77dd5ad8d86f2aa"
REVIEW_ROOT_SHA = "0a73622f95790703a8a1512c46ae8be93dbd99c1932fda912069ee870e5dd188"
PREFLIGHT_ROOT_SHA = "12a143284bff4bb8f6b0c423b61db85bd047684b8ecd652072d9964e61a58d9a"
PREFLIGHT_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_"
    "b336752518_20260708T105309CST"
)
TRAINING_HEAD = "e368adf10ade7180573430bbf9edb0e530796633"
TRAINING_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_"
    "e368adf10a_20260708T111406CST"
)
TRAINING_JSON_SHA = "53dccb70eb1d23ffb29d04197ccfa18299e8418b4d79e1a9c0c84513f9ea1267"
TRAINING_MD_SHA = "12ad059357066dd4ad05bcbd808f468552f42f4499ee8b74cf269d3eaa5b461e"
TRAINING_CONFIG_SHA = "a2f517cbb4757b8ada665e78874b6cd73da49df83b75a5b4c64f3cb94b889c60"
TRAINING_TIMING_JSON_SHA = "03245a893b108be8bca2dc38d953402599ee70878874266c3b40cfbd3df573a7"
TRAINING_TIMING_MD_SHA = "6f4cc38ad53f36734fde74ef640e2631262661ad49c2aaccd5ac21d8c08225ee"
TRAINING_SHA256SUMS_SHA = "603271fd88f28c4e7905a6b2e095b5308967a676ea8c11c8b898ebe8c1a16084"
TRAINING_ROOT_SHA256SUMS_SHA = "ad4a4f11c25ef8da64d56f939b400a856f1013190b51eb2fde46206d47357e00"
TRAINING_HEADS_SHA = "ce36eb7302fc3a007885ede1af3b6c0bb15cbb5dd88bee45ea252e1b25a2c77b"
TRAINING_COMMAND_SHA = "a4099e6bd9905195229c6912ee38e3d67566a904441e9f6dc50e1b64a849cd2b"
TRAINING_STDOUT_SHA = "1381c04ac2dc78de818b90fe92c185df15787f5950967ac138b0c09484d57ed9"
TRAINING_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
TRAINING_RUN_EXIT_SHA = "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865"
TRAINING_SUCCESS_HEAD = "2f0448ad80abb5b858595c904d4bd6c2de3930a0"
TRAINING_SUCCESS_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_"
    "2f0448ad80_20260708T114018CST"
)
TRAINING_SUCCESS_JSON_SHA = "548a5c43feecf4a01084fb7a65535ac820ff34c25cd98047c755cdf561eccf6a"
TRAINING_SUCCESS_MD_SHA = "2a28dea6e920d0254d7051eb950e9a006a90ac0d34c2de29851cc8812f6aea30"
TRAINING_SUCCESS_MODEL_SHA = "b12fb355f4f2754931fbf1b412460e6fcc52ea5c5a4f16ac94aa484584d2b8cd"
TRAINING_SUCCESS_CONFIG_SHA = "687e83c172e9d208aba512ea82484c425171f8023d8d023c7fc2266e25102553"
TRAINING_SUCCESS_TIMING_JSON_SHA = "5f878e09fcd5fcba6726ffc01635fbf6f39ba6f0c3339dbe51b1bc8d72453fe1"
TRAINING_SUCCESS_TIMING_MD_SHA = "44bb42a79ba2732f353005e9d4a69cc4c68bf72d00dd532d53427f228cb57ace"
TRAINING_SUCCESS_SHA256SUMS_SHA = "92ebe656b28a61b27a5317cf48e41f38a0c1f5d7f333323e2fdaeeb8c8dcd493"
TRAINING_SUCCESS_ROOT_SHA256SUMS_SHA = "ddc4fd268c3acf6eca420bc5cf767e0fd4d33f2bcde73caec0dfc90eb7a51170"
TRAINING_SUCCESS_HEADS_SHA = "2a25bcddf864f113f2c2cdc37b4b27ac5ced9256b2fbfe78d3d14e457ad92622"
TRAINING_SUCCESS_COMMAND_SHA = "c194fd99bfea5d49cb21749098de783f930d39be187ef14c32f2a9f9d288d522"
TRAINING_SUCCESS_STDOUT_SHA = "81396ec8322f0f164b5bcf173a6fadee29b83aa0cad0f0a0d208f55016997fc8"
TRAINING_SUCCESS_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
TRAINING_SUCCESS_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_training_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_training_execution_trains_train_only(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True)

    report = module.run_execution(**fixture)

    decision = report["final_decision"]
    training = report["pilot_training_execution"]
    model = report["static_camp_model"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is True
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert training["train_records"] == 863
    assert training["calibration_records_used_for_training"] == 0
    assert training["holdout_records_used_for_training"] == 0
    assert "calibration_records.jsonl" not in " ".join(training["training_command"])
    assert "holdout_records.jsonl" not in " ".join(training["training_command"])
    assert model["atom_count"] == 12
    assert model["weights_nonnegative"] is True
    assert model["weights_sum_to_one"] is True
    assert model["approved_atoms_only"] is True
    assert model["score_expression"] == module.SCORE_EXPRESSION
    assert model["weights_sum"] == 1.0
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "static_camp_weights_model.json").is_file()
    assert (fixture["output_dir"] / "pilot_training_config.json").is_file()
    assert (fixture["output_dir"] / "pilot_training_timing.json").is_file()
    assert (fixture["output_dir"] / "pilot_training_timing.md").is_file()
    assert (fixture["output_dir"] / "training_log.jsonl").is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_training_execution_rejects_missing_atoms(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=False)

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["training_executed"] is False
    assert "train_atoms_present" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_execution_derives_atoms_from_existing_npz(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=False, with_atom_sources=True)

    report = module.run_execution(**fixture)

    training = report["pilot_training_execution"]
    model = report["static_camp_model"]
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["training_executed"] is True
    assert training["atom_summary"]["atom_count"] == 9
    assert training["atom_derivation"]["records_enriched"] == 863
    assert training["atom_derivation"]["candidate_tensor_sha_mismatches"] == 0
    assert "--label_source" in training["training_command"]
    assert "proxy" in training["training_command"]
    assert model["atom_count"] == 9
    assert model["weights_nonnegative"] is True
    assert model["weights_sum_to_one"] is True


def test_v16_pilot_training_execution_accepts_failed_current_status_with_preflight_recorded(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True)
    fixture["current_status_md"].write_text(
        "\n".join(
            [
                f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_status={module.SOURCE_PREFLIGHT_STATUS}",
                f"current_v16_status={module.FAILED_STATUS}",
                f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["training_executed"] is True


def test_v16_pilot_training_execution_keeps_all_false_feasibility_for_proxy_smoke(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        with_atoms=False,
        with_atom_sources=True,
        all_infeasible_atom_source=True,
    )

    report = module.run_execution(**fixture)

    training = report["pilot_training_execution"]
    assert report["final_decision"]["passed"] is True
    assert training["atom_derivation"]["records_enriched"] == 863
    assert training["atom_derivation"]["all_false_feasible_fallback_records"] == 863
    assert report["final_decision"]["training_executed"] is True


def test_v16_pilot_training_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True, next_work="wrong_gate")

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_training_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_training_execution" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_execution_failure_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")

    for text in (audit,):
        assert TRAINING_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_status={module.FAILED_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_authorized_next_work="
            f"{module.AUTHORIZED_CURRENT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_exit=1" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_passed=False" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_failed_checks="
            '["train_atoms_present","approved_atom_count_positive","approved_atom_schema_canonical"]'
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_calibration_records=14" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_holdout_records=147" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_train_missing_atoms=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_closed_loop_outcomes_used_for_training=False" in text
        assert f"current_v16_status={module.FAILED_STATUS}" in text
        assert f"next_work_target={module.AUTHORIZED_CURRENT_WORK}" in text
        assert TRAINING_HEAD in text
        assert TRAINING_JSON_SHA in text
        assert TRAINING_MD_SHA in text
        assert TRAINING_CONFIG_SHA in text
        assert TRAINING_TIMING_JSON_SHA in text
        assert TRAINING_TIMING_MD_SHA in text
        assert TRAINING_SHA256SUMS_SHA in text
        assert TRAINING_ROOT_SHA256SUMS_SHA in text
        assert TRAINING_HEADS_SHA in text
        assert TRAINING_COMMAND_SHA in text
        assert TRAINING_STDOUT_SHA in text
        assert TRAINING_STDERR_SHA in text
        assert TRAINING_RUN_EXIT_SHA in text
        assert SPLIT_EXECUTION_ROOT_SHA in text
        assert SPLIT_REVIEW_ROOT_SHA in text
        assert PLAN_ROOT_SHA in text
        assert REVIEW_ROOT_SHA in text
        assert PREFLIGHT_ROOT_SHA in text


def test_v16_pilot_training_execution_success_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert TRAINING_SUCCESS_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_derivation_records_enriched=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_derivation_failed_records=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_derivation_all_false_feasible_fallback_records=389" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_count=9" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_atom_schema_version=camp_legacy_v1_9d" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_training_executed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_offline_training_wall_clock_seconds=0.535838" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_weights_sum=1.0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_dp_modified=False" in text
        assert TRAINING_SUCCESS_HEAD in text
        assert TRAINING_SUCCESS_JSON_SHA in text
        assert TRAINING_SUCCESS_MD_SHA in text
        assert TRAINING_SUCCESS_MODEL_SHA in text
        assert TRAINING_SUCCESS_CONFIG_SHA in text
        assert TRAINING_SUCCESS_TIMING_JSON_SHA in text
        assert TRAINING_SUCCESS_TIMING_MD_SHA in text
        assert TRAINING_SUCCESS_SHA256SUMS_SHA in text
        assert TRAINING_SUCCESS_ROOT_SHA256SUMS_SHA in text
        assert TRAINING_SUCCESS_HEADS_SHA in text
        assert TRAINING_SUCCESS_COMMAND_SHA in text
        assert TRAINING_SUCCESS_STDOUT_SHA in text
        assert TRAINING_SUCCESS_STDERR_SHA in text
        assert TRAINING_SUCCESS_RUN_EXIT_SHA in text

def _write_fixture(
    tmp_path: Path,
    module,
    *,
    with_atoms: bool,
    with_atom_sources: bool = False,
    all_infeasible_atom_source: bool = False,
    next_work: str | None = None,
) -> dict:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"current_v16_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    split_execution = _artifact(tmp_path / "split_execution", SPLIT_EXECUTION_ROOT_SHA)
    split_review = _artifact(tmp_path / "split_review", SPLIT_REVIEW_ROOT_SHA)
    plan = _artifact(tmp_path / "plan", PLAN_ROOT_SHA)
    review = _artifact(tmp_path / "review", REVIEW_ROOT_SHA)
    preflight = _artifact(tmp_path / "preflight", PREFLIGHT_ROOT_SHA)
    _write_json(preflight / module.SOURCE_PREFLIGHT_JSON_NAME, _preflight_payload(module))

    atom_version, atom_names = module.atom_schema_for_dimension(12)
    atom_source = _write_atom_source_npzs(tmp_path, all_infeasible=all_infeasible_atom_source) if with_atom_sources else None
    records = _records_by_split(
        module,
        with_atoms=with_atoms,
        with_atom_sources=with_atom_sources,
        atom_source=atom_source,
        atom_version=atom_version,
        atom_names=atom_names,
    )
    for name, split in {
        "train_records.jsonl": "train",
        "calibration_records.jsonl": "calibration",
        "holdout_records.jsonl": "holdout",
    }.items():
        (split_execution / name).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records[split]),
            encoding="utf-8",
        )
    for artifact in (split_execution, preflight):
        _rewrite_manifest(artifact)
    _write(split_execution / "ROOT_SHA256SUMS", f"{SPLIT_EXECUTION_ROOT_SHA}  SHA256SUMS\n")
    _write(preflight / "ROOT_SHA256SUMS", f"{PREFLIGHT_ROOT_SHA}  SHA256SUMS\n")

    training_script = tmp_path / "fake_trainer.py"
    _write(training_script, _fake_trainer())
    return {
        "split_execution_artifact_dir": split_execution,
        "split_result_review_artifact_dir": split_review,
        "source_plan_artifact_dir": plan,
        "source_static_review_artifact_dir": review,
        "source_preflight_artifact_dir": preflight,
        "source_preflight_json": preflight / module.SOURCE_PREFLIGHT_JSON_NAME,
        "source_train_records_jsonl": split_execution / "train_records.jsonl",
        "source_calibration_records_jsonl": split_execution / "calibration_records.jsonl",
        "source_holdout_records_jsonl": split_execution / "holdout_records.jsonl",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "training_script": training_script,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_split_execution_root_sha256": SPLIT_EXECUTION_ROOT_SHA,
        "expected_split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": REVIEW_ROOT_SHA,
        "expected_preflight_root_sha256": PREFLIGHT_ROOT_SHA,
        "python_executable": sys.executable,
        "epochs": 1,
        "enabled": True,
        "command": ["test-command"],
    }


def _preflight_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA_VERSION,
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "source_artifacts": {
            "plan": {"path": "/plan", "root_sha256": PLAN_ROOT_SHA},
            "static_review": {"path": "/review", "root_sha256": REVIEW_ROOT_SHA},
        },
        "pilot_training_preflight": {
            "calibration_records": 14,
            "calibration_records_used_for_training": 0,
            "holdout_records": 147,
            "holdout_records_used_for_training": 0,
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            "source_static_review_root_sha256": REVIEW_ROOT_SHA,
            "train_records": 863,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "passed": True,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
        },
    }


def _records_by_split(
    module,
    *,
    with_atoms: bool,
    with_atom_sources: bool,
    atom_source: dict[str, str] | None,
    atom_version: str,
    atom_names: tuple[str, ...],
) -> dict[str, list[dict]]:
    return {
        "train": [
            _record(
                module,
                "train",
                "scene-0553" if index < 495 else "scene-0655",
                index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(863)
        ],
        "calibration": [
            _record(
                module,
                "calibration",
                "scene-0061",
                863 + index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(14)
        ],
        "holdout": [
            _record(
                module,
                "holdout",
                "scene-0757",
                877 + index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(147)
        ],
    }


def _record(
    module,
    split: str,
    scene: str,
    index: int,
    with_atoms: bool,
    with_atom_sources: bool,
    atom_source: dict[str, str] | None,
    atom_version: str,
    atom_names: tuple[str, ...],
) -> dict:
    record = {
        "candidate_count": 8,
        "candidate_tensor_sha256": f"{index:064x}",
        "candidate_tensor_unchanged_by_camp": True,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "K": 8,
        "sample_id": f"{scene}_{index:06d}",
        "scene_id": scene,
        "split": split,
    }
    if with_atoms:
        record.update(
            {
                "atom_names": list(atom_names),
                "atom_schema_version": atom_version,
                "atoms": [[float(candidate + atom + 1) for atom in range(len(atom_names))] for candidate in range(8)],
                "feasible_mask": [True] * 8,
            }
        )
    if with_atom_sources and atom_source is not None:
        record.update(atom_source)
    return record


def _write_atom_source_npzs(tmp_path: Path, *, all_infeasible: bool = False) -> dict[str, str]:
    input_npz = tmp_path / "atom_source" / "dp_input.npz"
    candidate_npz = tmp_path / "atom_source" / "candidate_tensor.npz"
    input_npz.parent.mkdir(parents=True)
    route_lanes = np.zeros((25, 20, 33), dtype=np.float32)
    xs = np.linspace(0.0, 40.0, 20, dtype=np.float32)
    route_lanes[0, :, 0] = xs
    route_lanes[0, :, 3] = 1.0
    neighbor_future = np.zeros((32, 80, 3), dtype=np.float32)
    candidate_tensor = np.zeros((8, 80, 4), dtype=np.float32)
    for candidate in range(8):
        candidate_tensor[candidate, :, 0] = np.linspace(0.0, 8.0 + candidate, 80, dtype=np.float32)
        candidate_tensor[candidate, :, 1] = 100.0 if all_infeasible else float(candidate) * 0.05
    np.savez(
        input_npz,
        ego_current_state=np.array([0.0, 0.0, 1.0, 0.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
        neighbor_agents_future=neighbor_future,
        route_lanes=route_lanes,
        route_lanes_has_speed_limit=np.zeros((25, 1), dtype=bool),
        route_lanes_speed_limit=np.zeros((25, 1), dtype=np.float32),
        static_objects=np.zeros((5, 10), dtype=np.float32),
    )
    np.savez(
        candidate_npz,
        candidate_tensor=candidate_tensor,
        dp_top1_index=np.array(0, dtype=np.int64),
        candidate_count=np.array(8, dtype=np.int64),
        input_npz=np.array(str(input_npz)),
    )
    return {
        "adapter_input_sha256": _sha256(input_npz),
        "candidate_npz": str(candidate_npz),
        "candidate_npz_sha256": _sha256(candidate_npz),
        "candidate_tensor_sha256": hashlib.sha256(np.ascontiguousarray(candidate_tensor).tobytes()).hexdigest(),
        "input_npz": str(input_npz),
    }


def _artifact(path: Path, root_sha: str) -> Path:
    path.mkdir(parents=True)
    _write(path / "HEADS", f"CAMP_HEAD={HEAD}\n")
    _write(path / "COMMAND", "fixture\n")
    _write(path / "stdout.txt", "")
    _write(path / "stderr.txt", "")
    _write(path / "run.exit", "0\n")
    _rewrite_manifest(path)
    _write(path / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")
    return path


def _rewrite_manifest(path: Path) -> None:
    rows = []
    for item in sorted(path.rglob("*")):
        if item.name in {"SHA256SUMS", "ROOT_SHA256SUMS"} or not item.is_file():
            continue
        rows.append(f"{_sha256(item)}  {item.relative_to(path).as_posix()}\n")
    _write(path / "SHA256SUMS", "".join(rows))


def _fake_trainer() -> str:
    return """\
from __future__ import annotations

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--selection_log", action="append", type=Path, required=True)
parser.add_argument("--output_dir", type=Path, required=True)
parser.add_argument("--epochs", default="1")
parser.add_argument("--label_source", default="proxy")
parser.add_argument("--require_atom_schema", action="store_true")
args = parser.parse_args()
records = []
for path in args.selection_log:
    records.extend(json.loads(path.read_text(encoding="utf-8")))
weights = [1.0 / len(records[0]["atom_names"])] * len(records[0]["atom_names"])
summary = {
    "atom_names": records[0]["atom_names"],
    "atom_schema_version": records[0]["atom_schema_version"],
    "history": [{"epoch": 0, "loss": 0.0}],
    "num_atoms": len(records[0]["atom_names"]),
    "num_candidates": len(records[0]["atoms"]),
    "num_records": len(records),
    "trained_weights": weights,
}
args.output_dir.mkdir(parents=True, exist_ok=True)
(args.output_dir / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
