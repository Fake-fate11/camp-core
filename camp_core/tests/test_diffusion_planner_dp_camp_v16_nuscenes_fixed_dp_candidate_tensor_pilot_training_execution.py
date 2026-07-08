from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


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


def test_v16_pilot_training_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, with_atoms=True, next_work="wrong_gate")

    report = module.run_execution(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_training_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_training_execution" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    with_atoms: bool,
    next_work: str | None = None,
) -> dict:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
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
    records = _records_by_split(module, with_atoms=with_atoms, atom_version=atom_version, atom_names=atom_names)
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


def _records_by_split(module, *, with_atoms: bool, atom_version: str, atom_names: tuple[str, ...]) -> dict[str, list[dict]]:
    return {
        "train": [
            _record(module, "train", "scene-0553" if index < 495 else "scene-0655", index, with_atoms, atom_version, atom_names)
            for index in range(863)
        ],
        "calibration": [
            _record(module, "calibration", "scene-0061", 863 + index, with_atoms, atom_version, atom_names)
            for index in range(14)
        ],
        "holdout": [
            _record(module, "holdout", "scene-0757", 877 + index, with_atoms, atom_version, atom_names)
            for index in range(147)
        ],
    }


def _record(
    module,
    split: str,
    scene: str,
    index: int,
    with_atoms: bool,
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
    return record


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
