from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation.py"
)
HEAD = "fc6b8a99c87bf7fed51f6bbb2b35107f6d442b34"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "24247d7924a7ac388adf7893cc70510b9fa6496aee9b394f34747ead8b12f4e2"
STATIC_REVIEW_ROOT_SHA = "82182c771919e5dffcff57a546b04931553507a80ec6565bd398d9f6d6747512"
PREFLIGHT_ROOT_SHA = "620c55ade0d5dba9e6a1c816ebb16178f27729189971308697fda3c9c2e42514"
TRAINING_ROOT_SHA = "70875a2691fcd45f6337c48db563b9623e9606adbc35c5fd1df9f7e68029f28e"
TRAINING_REVIEW_ROOT_SHA = "1063073e0b1f7088b142241f71a238711635865409ed5166e389b46299521429"
SPLIT_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
SPLIT_REVIEW_ROOT_SHA = "1322556d790e25527818d38e77cf5240bb6fd68678563190a6ad0f88cbc70d0e"
SCALEUP_CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_paired_eval_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_paired_eval_execution_computes_primary_metrics(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.run_execution(**fixture)

    decision = report["final_decision"]
    paired = report["scaleup_paired_evaluation_execution"]
    metrics = report["split_metrics"]["primary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["paired_evaluation_executed"] is True
    assert decision["training_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert paired["paired_rows_by_split"] == {
        "calibration": 2156,
        "holdout": 1581,
        "primary_eval_total": 3737,
        "train_reporting_only": 6263,
    }
    assert paired["primary_eval_splits"] == ["calibration", "holdout"]
    assert paired["reporting_only_splits"] == ["train"]
    assert paired["score_expression"] == module.SCORE_EXPRESSION
    assert paired["weights_nonnegative"] is True
    assert paired["weights_sum_to_one"] is True
    assert paired["approved_atoms_only"] is True
    assert paired["candidate_tensor_mutated_count"] == 0
    assert paired["selected_index_out_of_range_count"] == 0
    assert metrics["row_count"] == 3737
    assert metrics["better_tie_worse"] == {"better": 2, "tie": 3735, "worse": 0}
    assert metrics["mean_delta"] == pytest.approx(-2.0 / 3737.0)
    assert metrics["ci95"]["low"] < metrics["mean_delta"] < metrics["ci95"]["high"]
    assert metrics["dp_top1_metric"]["mean"] == pytest.approx(3739.0 / 3737.0)
    assert metrics["camp_selected_metric"]["mean"] == pytest.approx(1.0)
    assert metrics["non_top1_selection_rate"] == pytest.approx(2.0 / 3737.0)
    assert metrics["oracle_gap_closed"] == pytest.approx(1.0)
    assert report["selector_latency_ms"]["count"] == 3737
    assert len(report["paired_rows"]) == 3737
    assert {row["split"] for row in report["paired_rows"]} == {"calibration", "holdout"}
    assert all(row["selected_index_in_range"] for row in report["paired_rows"])
    assert all(row["candidate_tensor_sha256_present"] for row in report["paired_rows"])
    assert all(row["candidate_tensor_unchanged_by_camp"] for row in report["paired_rows"])
    assert all(row["camp_atom_table_sha256"] for row in report["paired_rows"])
    assert not any(row["split"] == "train" for row in report["paired_rows"])
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PAIRED_ROWS_JSONL_NAME).is_file()
    assert (fixture["output_dir"] / module.SPLIT_METRICS_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.LATENCY_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_paired_eval_execution_rejects_train_in_primary_eval(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    preflight = json.loads(fixture["source_preflight_json"].read_text(encoding="utf-8"))
    preflight["scaleup_paired_evaluation_preflight"]["primary_eval_splits"] = [
        "train",
        "calibration",
        "holdout",
    ]
    fixture["source_preflight_json"].write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = module.build_report(**{key: value for key, value in fixture.items() if key not in {"command"}})

    assert report["final_decision"]["passed"] is False
    assert "train_excluded_from_primary_eval" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module) -> dict:
    artifacts = {
        "plan": tmp_path / "plan",
        "static_review": tmp_path / "static_review",
        "preflight": tmp_path / "preflight",
        "training": tmp_path / "training",
        "training_review": tmp_path / "training_review",
        "split": tmp_path / "split",
        "split_review": tmp_path / "split_review",
        "scaleup_corpus": tmp_path / "scaleup_corpus",
    }
    for path in artifacts.values():
        path.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    records_by_split = {
        "train": [_record("train", index, better=False) for index in range(6263)],
        "calibration": [_record("calibration", index, better=index == 0) for index in range(2156)],
        "holdout": [_record("holdout", index, better=index == 0) for index in range(1581)],
    }
    for split, records in records_by_split.items():
        _write(
            artifacts["split"] / f"{split}_records.jsonl",
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        )

    _write_json(artifacts["plan"] / module.SOURCE_PLAN_JSON_NAME, _plan_payload(module))
    _write_json(artifacts["static_review"] / module.SOURCE_STATIC_REVIEW_JSON_NAME, _static_review_payload(module))
    _write_json(artifacts["preflight"] / module.SOURCE_PREFLIGHT_JSON_NAME, _preflight_payload(module, artifacts))
    _write_json(artifacts["training"] / module.SOURCE_TRAINING_JSON_NAME, _training_payload(module, artifacts))
    _write_json(artifacts["training"] / "static_camp_weights_model.json", _model_payload(module))
    _write_json(artifacts["training_review"] / module.SOURCE_TRAINING_REVIEW_JSON_NAME, _training_review_payload(module))
    _write_json(artifacts["split"] / module.SOURCE_SPLIT_JSON_NAME, _split_payload(module, artifacts))
    _write_json(artifacts["split_review"] / module.SOURCE_SPLIT_REVIEW_JSON_NAME, _split_review_payload(module))
    for name, root in {
        "plan": PLAN_ROOT_SHA,
        "static_review": STATIC_REVIEW_ROOT_SHA,
        "preflight": PREFLIGHT_ROOT_SHA,
        "training": TRAINING_ROOT_SHA,
        "training_review": TRAINING_REVIEW_ROOT_SHA,
        "split": SPLIT_ROOT_SHA,
        "split_review": SPLIT_REVIEW_ROOT_SHA,
        "scaleup_corpus": SCALEUP_CORPUS_ROOT_SHA,
    }.items():
        _write_common_files(artifacts[name], module)
        _write_manifest(artifacts[name], root)

    return {
        "source_plan_artifact_dir": artifacts["plan"],
        "source_plan_json": artifacts["plan"] / module.SOURCE_PLAN_JSON_NAME,
        "source_static_review_artifact_dir": artifacts["static_review"],
        "source_static_review_json": artifacts["static_review"] / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        "source_preflight_artifact_dir": artifacts["preflight"],
        "source_preflight_json": artifacts["preflight"] / module.SOURCE_PREFLIGHT_JSON_NAME,
        "source_training_artifact_dir": artifacts["training"],
        "source_training_json": artifacts["training"] / module.SOURCE_TRAINING_JSON_NAME,
        "source_training_model_json": artifacts["training"] / "static_camp_weights_model.json",
        "source_training_result_review_artifact_dir": artifacts["training_review"],
        "source_training_result_review_json": artifacts["training_review"] / module.SOURCE_TRAINING_REVIEW_JSON_NAME,
        "source_split_execution_artifact_dir": artifacts["split"],
        "source_split_execution_json": artifacts["split"] / module.SOURCE_SPLIT_JSON_NAME,
        "source_calibration_records_jsonl": artifacts["split"] / "calibration_records.jsonl",
        "source_holdout_records_jsonl": artifacts["split"] / "holdout_records.jsonl",
        "source_train_records_jsonl": artifacts["split"] / "train_records.jsonl",
        "source_split_result_review_artifact_dir": artifacts["split_review"],
        "source_split_result_review_json": artifacts["split_review"] / module.SOURCE_SPLIT_REVIEW_JSON_NAME,
        "source_scaleup_corpus_artifact_dir": artifacts["scaleup_corpus"],
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "expected_preflight_root_sha256": PREFLIGHT_ROOT_SHA,
        "expected_training_root_sha256": TRAINING_ROOT_SHA,
        "expected_training_result_review_root_sha256": TRAINING_REVIEW_ROOT_SHA,
        "expected_split_execution_root_sha256": SPLIT_ROOT_SHA,
        "expected_split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
        "expected_scaleup_corpus_root_sha256": SCALEUP_CORPUS_ROOT_SHA,
        "enabled": True,
        "command": ["execute"],
    }


def _plan_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.SOURCE_PLAN_STATUS,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.SOURCE_STATIC_REVIEW_CURRENT_WORK,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _static_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "plan_static_review": {"source_plan_root_sha256": PLAN_ROOT_SHA},
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.SOURCE_PREFLIGHT_CURRENT_WORK,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _preflight_payload(module, artifacts: dict[str, Path]) -> dict:
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA_VERSION,
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "source_artifacts": {
            "plan": {"path": str(artifacts["plan"]), "root_sha256": PLAN_ROOT_SHA},
            "static_review": {"path": str(artifacts["static_review"]), "root_sha256": STATIC_REVIEW_ROOT_SHA},
            "training": {"path": str(artifacts["training"]), "root_sha256": TRAINING_ROOT_SHA},
        },
        "scaleup_paired_evaluation_preflight": {
            "primary_eval_splits": ["calibration", "holdout"],
            "reporting_only_splits": ["train"],
            "paired_rows_by_split": {
                "calibration": 2156,
                "holdout": 1581,
                "primary_eval_total": 3737,
                "train_reporting_only": 6263,
            },
            "score_expression": module.SCORE_EXPRESSION,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "approved_atoms_only": True,
            "scaleup_evidence_only": True,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _training_payload(module, artifacts: dict[str, Path]) -> dict:
    return {
        "schema_version": module.SOURCE_TRAINING_SCHEMA_VERSION,
        "status": module.SOURCE_TRAINING_STATUS,
        "source_artifacts": {
            "scaleup_corpus": {"path": str(artifacts["scaleup_corpus"]), "root_sha256": SCALEUP_CORPUS_ROOT_SHA},
            "split_execution": {"path": str(artifacts["split"]), "root_sha256": SPLIT_ROOT_SHA},
            "split_result_review": {"path": str(artifacts["split_review"]), "root_sha256": SPLIT_REVIEW_ROOT_SHA},
        },
        "scaleup_training_execution": {
            "train_records": 6263,
            "calibration_records": 2156,
            "holdout_records": 1581,
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "static_camp_model": _model_payload(module),
        "final_decision": {
            "passed": True,
            "training_executed": True,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _training_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_TRAINING_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_TRAINING_REVIEW_STATUS,
        "source_artifact": {"root_sha256": TRAINING_ROOT_SHA},
        "final_decision": {
            "passed": True,
            "authorized_next_work": "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_only",
            "training_executed_by_review": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _split_payload(module, artifacts: dict[str, Path]) -> dict:
    return {
        "schema_version": module.SOURCE_SPLIT_SCHEMA_VERSION,
        "status": module.SOURCE_SPLIT_STATUS,
        "source_artifacts": {
            "scaleup_corpus": {"path": str(artifacts["scaleup_corpus"]), "root_sha256": SCALEUP_CORPUS_ROOT_SHA}
        },
        "split_execution": {"counts": {"train": 6263, "calibration": 2156, "holdout": 1581}},
        "final_decision": {"passed": True, "split_execution_executed": True, "paired_evaluation_executed": False},
    }


def _split_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_SPLIT_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_SPLIT_REVIEW_STATUS,
        "source_artifact": {"root_sha256": SPLIT_ROOT_SHA},
        "final_decision": {
            "passed": True,
            "authorized_next_work": "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_only",
            "split_execution_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _model_payload(module) -> dict:
    return {
        "artifact_type": "static_camp_weights_model",
        "atom_schema_version": "test_v1",
        "atom_names": ["cost", "unused", "unused2"],
        "approved_atoms": ["cost", "unused", "unused2"],
        "approved_atoms_only": True,
        "score_expression": module.SCORE_EXPRESSION,
        "weights": [1.0, 0.0, 0.0],
        "weights_sum": 1.0,
        "weights_nonnegative": True,
        "weights_sum_to_one": True,
    }


def _record(split: str, index: int, *, better: bool) -> dict:
    atoms = [[1.0, 0.0, 0.0] for _ in range(8)]
    if better:
        atoms[0][0] = 2.0
        atoms[1][0] = 1.0
    return {
        "split": split,
        "scene_id": f"{split}_scene_{index}",
        "sample_id": f"{split}_sample_{index}",
        "K": 8,
        "candidate_count": 8,
        "DP_HEAD": DP_HEAD,
        "CAMP_HEAD": "b9a43b733712d38252a43415050ced20ade5edae",
        "camp_atom_table_sha256": f"{split}_{index:04x}_atoms",
        "candidate_tensor_sha256": f"{split}_{index:04x}",
        "candidate_tensor_unchanged_by_camp": True,
        "candidate_tensor_shape": [8, 80, 4],
        "adapter_input_shape": {"version": []},
        "dp_top1_index": 0,
        "atom_names": ["cost", "unused", "unused2"],
        "atom_schema_version": "test_v1",
        "atoms": atoms,
        "feasible_mask": [True] * 8,
    }


def _write_common_files(artifact: Path, module) -> None:
    _write(artifact / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(artifact / "COMMAND", "command\n")
    _write(artifact / "COMMAND.shell", "command shell\n")
    _write(artifact / "stdout.txt", "{}\n")
    _write(artifact / "stderr.txt", "")
    _write(artifact / "run.exit", "0\n")


def _write_manifest(artifact: Path, root_sha: str) -> None:
    rows = []
    for path in sorted(artifact.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.name}\n")
    _write(artifact / "SHA256SUMS", "".join(rows))
    _write(artifact / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
