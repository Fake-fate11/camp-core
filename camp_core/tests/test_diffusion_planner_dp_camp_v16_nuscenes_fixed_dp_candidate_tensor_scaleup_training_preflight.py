from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training.py"
)
HEAD = "1326bd4ffcd934ce6687ea5ba802cadb06328b3b"
PLAN_ROOT_SHA = "990992937869aca189cb71d9832a435575c01091a924e136df1850bc164f549b"
REVIEW_ROOT_SHA = "da8b55d6e897f9aa6fb852d8b40d578960e6b6d07373673311c8dd82fd4b3706"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_"
    "7dfa1b3d13_20260709T150711CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_"
    "12fba87c20_20260709T152321CST"
)
PREFLIGHT_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_"
    "1326bd4ffc_20260709T154101CST"
)
TRAINING_OUTPUT_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_"
    "1326bd4ffc_20260709T154101CST"
)
PREFLIGHT_JSON_SHA = "68efe957d6610866f536242a2047300af244fa338b612566df829d725111d1fd"
PREFLIGHT_MD_SHA = "9b95b4b4b24bf7ea4255046faf237b5ac61acb9ca337b68b8c107659ded93721"
PREFLIGHT_SHA256SUMS_SHA = "5f06539eddaf1a77ca533a69eb7609bab1e9dc269b00a304e3d0823debcf8f0e"
PREFLIGHT_ROOT_SHA256SUMS_SHA = "44daf512404348f6068aa980fbd09ce130d4120c6870105a5c50a2b48b75cb91"
PREFLIGHT_HEADS_SHA = "78404aa428e6e40481168d7275d9a612032fc63734aa598a937c8c0b49dcc43f"
PREFLIGHT_COMMAND_SHA = "8ccbe0d30601a8f450293903e2af4094cce822a018f396a21c4e2aa42ff1e0e2"
PREFLIGHT_STDOUT_SHA = "bb54a93d2d270b7abd18c81bb8de3a49da2af3cd2e49ed0df116b2f63c685bdb"
PREFLIGHT_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PREFLIGHT_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_training_preflight_passes_without_training(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["scaleup_training_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["preflight_only"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert preflight["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert preflight["source_static_review_root_sha256"] == REVIEW_ROOT_SHA
    assert preflight["train_records"] == 6263
    assert preflight["calibration_records"] == 2156
    assert preflight["holdout_records"] == 1581
    assert preflight["calibration_records_used_for_training"] == 0
    assert preflight["holdout_records_used_for_training"] == 0
    assert preflight["scene_zero_overlap"] is True
    assert preflight["sample_zero_overlap"] is True
    assert preflight["train_k_values"] == [8]
    assert preflight["train_candidate_count_values"] == [8]
    assert preflight["missing_train_candidate_tensor_sha256"] == 0
    assert preflight["dp_head"] == module.FIXED_DP_HEAD
    assert preflight["score_expression"] == module.PLAN_MODULE.SCORE_EXPRESSION
    assert preflight["weights_nonnegative"] is True
    assert preflight["weights_sum_to_one"] is True
    assert preflight["approved_atoms_only"] is True
    assert preflight["nonnegative_simplex"] is True
    assert preflight["no_closed_loop_outcomes_as_training_input"] is True
    assert preflight["no_candidate_tensor_mutation"] is True
    assert preflight["no_dp_modification"] is True
    assert preflight["training_output_root_absent"] is True
    assert preflight["training_command_constructed"] is True
    assert preflight["training_command_executed"] is False
    command = " ".join(preflight["training_command_template"])
    assert "train_diffusion_planner_static_camp.py" in command
    assert "train_records.jsonl" in command
    assert "calibration_records.jsonl" not in command
    assert "holdout_records.jsonl" not in command
    assert preflight["planned_outputs"] == {
        "approved_atoms_check": "approved_atoms_check.json",
        "command": "COMMAND",
        "config": "scaleup_training_config.json",
        "heads": "HEADS",
        "model_weights": "static_camp_weights_model.json",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "root_sha256s": "ROOT_SHA256SUMS",
        "sha256s": "SHA256SUMS",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
        "timing_json": "scaleup_training_timing.json",
        "timing_md": "scaleup_training_timing.md",
        "training_log": "scaleup_training.log",
    }
    for condition in (
        "dp_head_mismatch",
        "split_overlap",
        "missing_candidate_tensor_hashes",
        "k_or_candidate_count_drift",
        "candidate_tensor_mutation",
        "non_affine_score",
        "non_simplex_weights",
        "calibration_or_holdout_training_use",
    ):
        assert condition in preflight["stop_conditions"]
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_training_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_training_preflight" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_training_preflight" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["training_output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "training_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_rejects_missing_train_hash(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, missing_train_hash=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "train_candidate_tensor_hashes_present" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert PREFLIGHT_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_check_count=87" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_train_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_train_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_missing_train_candidate_tensor_sha256=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_nonnegative_simplex=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_no_closed_loop_outcomes_as_training_input=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_no_candidate_tensor_mutation=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_no_dp_modification=True" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_training_output_root={TRAINING_OUTPUT_ROOT}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_training_output_root_absent=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_training_command_constructed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_training_command_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_camp_head={HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_dp_head={module.FIXED_DP_HEAD}" in text
        assert PLAN_ARTIFACT in text
        assert PLAN_ROOT_SHA in text
        assert REVIEW_ARTIFACT in text
        assert REVIEW_ROOT_SHA in text
        assert PREFLIGHT_JSON_SHA in text
        assert PREFLIGHT_MD_SHA in text
        assert PREFLIGHT_SHA256SUMS_SHA in text
        assert PREFLIGHT_ROOT_SHA256SUMS_SHA in text
        assert PREFLIGHT_HEADS_SHA in text
        assert PREFLIGHT_COMMAND_SHA in text
        assert PREFLIGHT_STDOUT_SHA in text
        assert PREFLIGHT_STDERR_SHA in text
        assert PREFLIGHT_RUN_EXIT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in audit
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    missing_train_hash: bool = False,
) -> dict:
    plan_artifact = tmp_path / "training_preflight_plan"
    review_artifact = tmp_path / "training_preflight_plan_static_review"
    split_execution = tmp_path / "split_execution"
    for path in (plan_artifact, review_artifact, split_execution):
        path.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    records_by_split = _records_by_split(module)
    if missing_train_hash:
        del records_by_split["train"][0]["candidate_tensor_sha256"]
    for name, records in {
        "train_records.jsonl": records_by_split["train"],
        "calibration_records.jsonl": records_by_split["calibration"],
        "holdout_records.jsonl": records_by_split["holdout"],
    }.items():
        (split_execution / name).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )

    plan_json = plan_artifact / module.PLAN_MODULE.PLAN_JSON_NAME
    _write_json(plan_json, _plan_payload(module))
    _write(plan_artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Scale-up training preflight plan\n")
    _write_source_files(plan_artifact, module.FIXED_DP_HEAD)
    _write_manifest(plan_artifact, PLAN_ROOT_SHA)

    review_json = review_artifact / module.SOURCE_REVIEW_JSON_NAME
    _write_json(review_json, _review_payload(module))
    _write(review_artifact / module.SOURCE_REVIEW_MD_NAME, "# Static review\n")
    _write_source_files(review_artifact, module.FIXED_DP_HEAD)
    _write_manifest(review_artifact, REVIEW_ROOT_SHA)

    training_script = tmp_path / "train_diffusion_planner_static_camp.py"
    _write(training_script, "print('not executed')\n")
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_json,
        "source_plan_sha256s": plan_artifact / "SHA256SUMS",
        "source_plan_root_sha256s": plan_artifact / "ROOT_SHA256SUMS",
        "source_static_review_artifact_dir": review_artifact,
        "source_static_review_json": review_json,
        "source_static_review_sha256s": review_artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": review_artifact / "ROOT_SHA256SUMS",
        "source_train_records_jsonl": split_execution / "train_records.jsonl",
        "source_calibration_records_jsonl": split_execution / "calibration_records.jsonl",
        "source_holdout_records_jsonl": split_execution / "holdout_records.jsonl",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "training_script": training_script,
        "training_output_root": tmp_path / "scaleup_training_outputs",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": REVIEW_ROOT_SHA,
        "python_executable": "python",
        "enabled": True,
    }


def _plan_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
        "authorized_next_work": module.SOURCE_CURRENT_WORK,
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "scaleup_training_preflight_plan": {
            "fixed_dp_head": module.FIXED_DP_HEAD,
            "training_inputs": {
                "calibration_records_available": 2156,
                "calibration_records_used_for_training": 0,
                "forbidden_training_splits": ["calibration", "holdout"],
                "holdout_records_available": 1581,
                "holdout_records_used_for_training": 0,
                "train_records": 6263,
                "training_splits": ["train"],
            },
            "math_contract": {
                "approved_atoms_only": True,
                "nonnegative_simplex": True,
                "no_candidate_tensor_mutation": True,
                "no_closed_loop_outcomes_as_training_input": True,
                "no_dp_modification": True,
                "score_expression": module.PLAN_MODULE.SCORE_EXPRESSION,
                "weights_nonnegative": True,
                "weights_sum_to_one": True,
            },
            "planned_outputs": _planned_outputs(),
            "stop_conditions": _stop_conditions(),
        },
        "final_decision": _final_decision(module.SOURCE_CURRENT_WORK),
    }


def _review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_plan_artifact": {"path": PLAN_ARTIFACT, "root_sha256": PLAN_ROOT_SHA},
        "plan_static_review": {
            "approved_atoms_only": True,
            "calibration_records": 2156,
            "calibration_records_used_for_training": 0,
            "candidate_tensor_schema": {"candidate_count": 8, "candidate_tensor_shape": [8, 80, 4], "k": 8},
            "dp_head": module.FIXED_DP_HEAD,
            "holdout_records": 1581,
            "holdout_records_used_for_training": 0,
            "no_candidate_tensor_mutation": True,
            "no_closed_loop_outcomes_as_training_input": True,
            "no_dp_modification": True,
            "nonnegative_simplex": True,
            "planned_outputs": _planned_outputs(),
            "score_expression": module.PLAN_MODULE.SCORE_EXPRESSION,
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            "stop_conditions": _stop_conditions(),
            "train_records": 6263,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
        },
        "final_decision": _final_decision(module.AUTHORIZED_CURRENT_WORK) | {"static_review_only": True},
    }


def _planned_outputs() -> dict:
    return {
        "approved_atoms_check": "approved_atoms_check.json",
        "command": "COMMAND",
        "heads": "HEADS",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "root_sha256s": "ROOT_SHA256SUMS",
        "sha256s": "SHA256SUMS",
        "static_camp_weights_model_artifact": "static_camp_weights_model.json",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
        "timing_json": "scaleup_training_timing.json",
        "timing_md": "scaleup_training_timing.md",
        "training_config": "scaleup_training_config.json",
        "training_log": "scaleup_training.log",
    }


def _stop_conditions() -> list[str]:
    return [
        "split_overlap",
        "missing_candidate_hashes",
        "k_or_candidate_count_drift",
        "dp_head_mismatch",
        "calibration_or_holdout_leakage",
        "non_affine_score",
        "non_simplex_weights",
    ]


def _final_decision(next_work: str) -> dict:
    return {
        "authorized_next_work": next_work,
        "candidate_tensor_modified": False,
        "deployment_executed": False,
        "dp_modified": False,
        "fake_candidate_tensor_generated": False,
        "paired_evaluation_executed": False,
        "passed": True,
        "performance_claimed": False,
        "promotion_executed": False,
        "training_executed": False,
    }


def _records_by_split(module) -> dict[str, list[dict]]:
    records = {"train": [], "calibration": [], "holdout": []}
    record_index = 0
    for split, scene_prefix, count in [
        ("train", "scene-train", 6263),
        ("calibration", "scene-calibration", 2156),
        ("holdout", "scene-holdout", 1581),
    ]:
        for index in range(count):
            sample_id = f"{scene_prefix}-{index // 250:04d}_{index:06d}"
            records[split].append(_record(module, split, scene_prefix, index, record_index, sample_id))
            record_index += 1
    return records


def _record(module, split: str, scene_prefix: str, index: int, record_index: int, sample_id: str) -> dict:
    return {
        "candidate_count": 8,
        "candidate_tensor_sha256": f"{record_index:064x}",
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_unchanged_by_camp": True,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "K": 8,
        "sample_id": sample_id,
        "scene_id": f"{scene_prefix}-{index // 250:04d}",
        "source_sample_id": sample_id,
        "source_scene_id": f"{scene_prefix}-{index // 250:04d}",
        "split": split,
    }


def _write_source_files(root: Path, dp_head: str) -> None:
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={dp_head}\n",
        "COMMAND": "source command\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(root / name, text)


def _write_manifest(root: Path, root_sha: str) -> None:
    names = sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "ROOT_SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names if name != "SHA256SUMS"),
        encoding="utf-8",
    )
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="utf-8")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
