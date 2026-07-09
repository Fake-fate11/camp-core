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
    / "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training.py"
)
HEAD = "b9a43b733712d38252a43415050ced20ade5edae"
CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"
SPLIT_EXECUTION_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
SPLIT_REVIEW_ROOT_SHA = "1322556d790e25527818d38e77cf5240bb6fd68678563190a6ad0f88cbc70d0e"
PLAN_ROOT_SHA = "990992937869aca189cb71d9832a435575c01091a924e136df1850bc164f549b"
REVIEW_ROOT_SHA = "da8b55d6e897f9aa6fb852d8b40d578960e6b6d07373673311c8dd82fd4b3706"
PREFLIGHT_ROOT_SHA = "5f06539eddaf1a77ca533a69eb7609bab1e9dc269b00a304e3d0823debcf8f0e"
PREFLIGHT_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_"
    "1326bd4ffc_20260709T154101CST"
)
TRAINING_SUCCESS_HEAD = HEAD
TRAINING_SUCCESS_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_"
    "1326bd4ffc_20260709T154101CST"
)
TRAINING_SUCCESS_JSON_SHA = "383a1dfa734f98c46bab26f05c569f748bb77e57ed441aed1713a8df8f9f57f3"
TRAINING_SUCCESS_MD_SHA = "73ffac2e4450b533bef01ca7a19f3b86d9e3bc0b9c8627f32d4afdf9f45d9baa"
TRAINING_SUCCESS_MODEL_SHA = "2482619bb2f64d8c89f4493154310fc639f1f6aec3209798526b9ae9e05bd56b"
TRAINING_SUCCESS_CONFIG_SHA = "687e83c172e9d208aba512ea82484c425171f8023d8d023c7fc2266e25102553"
TRAINING_SUCCESS_TIMING_JSON_SHA = "399a35c311437a76a462235646782daeec95be26e96e6e89e79adf5db390ed59"
TRAINING_SUCCESS_TIMING_MD_SHA = "5f22b10c35e21a67a55abd3f8efec31f888abde9a47ef47796bbc716cf661b00"
TRAINING_SUCCESS_LOG_SHA = "e28510356b091835df855952702499a506f148bc34e84614986498ca67cf20d1"
TRAINING_SUCCESS_SHA256SUMS_SHA = "70875a2691fcd45f6337c48db563b9623e9606adbc35c5fd1df9f7e68029f28e"
TRAINING_SUCCESS_ROOT_SHA256SUMS_SHA = "8bc860788e02d9eadfcd9ab951558bdef908dd2f6d3fba224c59e6159907feff"
TRAINING_SUCCESS_HEADS_SHA = "0548c48fe8afc9929e5b88d1de412a507ccde5835be29440f4bad6c2f43d0764"
TRAINING_SUCCESS_COMMAND_SHA = "40960c7c7395292f42aa9c10365c815cef1f3335e79e8be625a6b12c7a9b02eb"
TRAINING_SUCCESS_STDOUT_SHA = "edc76e1d1022c7e22edba01ba721e48ce694e493743162fe84d50b4b8237c94d"
TRAINING_SUCCESS_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
TRAINING_SUCCESS_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_training_execution_trains_train_only(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True)

    report = module.run_execution(**fixture)

    decision = report["final_decision"]
    training = report["scaleup_training_execution"]
    model = report["static_camp_model"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is True
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert training["train_records"] == 6263
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
    assert (fixture["output_dir"] / "scaleup_training_config.json").is_file()
    assert (fixture["output_dir"] / "scaleup_training_timing.json").is_file()
    assert (fixture["output_dir"] / "scaleup_training_timing.md").is_file()
    assert (fixture["output_dir"] / "scaleup_training.log").is_file()
    assert (fixture["output_dir"] / "training_log.jsonl").is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_scaleup_training_execution_rejects_missing_atoms(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=False)

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["training_executed"] is False
    assert "train_atoms_present" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_execution_derives_atoms_from_existing_npz(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=False, with_atom_sources=True)

    report = module.run_execution(**fixture)

    training = report["scaleup_training_execution"]
    model = report["static_camp_model"]
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["training_executed"] is True
    assert training["atom_summary"]["atom_count"] == 9
    assert training["atom_derivation"]["records_enriched"] == 6263
    assert training["atom_derivation"]["candidate_tensor_sha_mismatches"] == 0
    assert "--label_source" in training["training_command"]
    assert "proxy" in training["training_command"]
    assert model["atom_count"] == 9
    assert model["weights_nonnegative"] is True
    assert model["weights_sum_to_one"] is True


def test_v16_scaleup_training_execution_accepts_failed_current_status_with_preflight_recorded(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True)
    fixture["current_status_md"].write_text(
        "\n".join(
            [
                f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_status={module.SOURCE_PREFLIGHT_STATUS}",
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


def test_v16_scaleup_training_execution_keeps_all_false_feasibility_for_proxy_smoke(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        with_atoms=False,
        with_atom_sources=True,
        all_infeasible_atom_source=True,
    )

    report = module.run_execution(**fixture)

    training = report["scaleup_training_execution"]
    assert report["final_decision"]["passed"] is True
    assert training["atom_derivation"]["records_enriched"] == 6263
    assert training["atom_derivation"]["all_false_feasible_fallback_records"] == 6263
    assert report["final_decision"]["training_executed"] is True


def test_v16_scaleup_training_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True, next_work="wrong_gate")

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_training_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_training_execution" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_execution_success_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert TRAINING_SUCCESS_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_atom_derivation_records_enriched=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_atom_derivation_failed_records=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_atom_derivation_all_false_feasible_fallback_records=3401" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_atom_count=9" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_atom_schema_version=camp_legacy_v1_9d" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_training_executed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_offline_training_wall_clock_seconds=1.335207" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_weights_sum=1.0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_weights_min=0.11106111863252109" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_weights_max=0.1111863821117415" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_dp_modified=False" in text
        assert TRAINING_SUCCESS_HEAD in text
        assert TRAINING_SUCCESS_JSON_SHA in text
        assert TRAINING_SUCCESS_MD_SHA in text
        assert TRAINING_SUCCESS_MODEL_SHA in text
        assert TRAINING_SUCCESS_CONFIG_SHA in text
        assert TRAINING_SUCCESS_TIMING_JSON_SHA in text
        assert TRAINING_SUCCESS_TIMING_MD_SHA in text
        assert TRAINING_SUCCESS_LOG_SHA in text
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
            f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"current_v16_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    corpus = _artifact(tmp_path / "corpus", CORPUS_ROOT_SHA)
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
        "source_corpus_artifact_dir": corpus,
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
        "expected_corpus_root_sha256": CORPUS_ROOT_SHA,
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
        "scaleup_training_preflight": {
            "calibration_records": 2156,
            "calibration_records_used_for_training": 0,
            "holdout_records": 1581,
            "holdout_records_used_for_training": 0,
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            "source_static_review_root_sha256": REVIEW_ROOT_SHA,
            "train_records": 6263,
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
                "scene-train" if index < 495 else "scene-train-b",
                index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(6263)
        ],
        "calibration": [
            _record(
                module,
                "calibration",
                "scene-calibration",
                6263 + index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(2156)
        ],
        "holdout": [
            _record(
                module,
                "holdout",
                "scene-holdout",
                6263 + 2156 + index,
                with_atoms,
                with_atom_sources,
                atom_source,
                atom_version,
                atom_names,
            )
            for index in range(1581)
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
