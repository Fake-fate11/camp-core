from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split.py"
)
HEAD = "462a02959bf60ada4318242419082fdae02f231b"
PLAN_ROOT_SHA = "5a0253063e4165506653f897a983a096b3df457d30b09a3524f8c57c4986c343"
STATIC_REVIEW_ROOT_SHA = "02f34f0b614c956a611fa961c3c7b087a896d24acc6406ad18c386a846f5a71f"
CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"
ARTIFACT_PREFIX = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_split_preflight_constructs_execution_contract(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["preflight_only"] is True
    assert decision["split_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert preflight["records"] == 10000
    assert preflight["scenes"] == 50
    assert preflight["planned_scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert preflight["planned_record_counts"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert preflight["scene_zero_overlap"] is True
    assert preflight["sample_zero_overlap"] is True
    assert preflight["record_level_hard_split_executed"] is False
    assert preflight["k_values"] == [8]
    assert preflight["candidate_count_values"] == [8]
    assert preflight["candidate_tensor_mutated_count"] == 0
    assert preflight["execution_output_root"] == str(fixture["execution_output_root"])
    assert preflight["execution_output_root_absent"] is True
    assert preflight["execution_command"][0].endswith(
        "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
    )
    assert preflight["execution_command_constructed"] is True
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_split_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, output_root_exists=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_split_preflight_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert ARTIFACT_PREFIX in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_train_scenes=30" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_calibration_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_holdout_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_execution_output_root=" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_check_count=" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_failed_checks=[]" in text
        assert STATIC_REVIEW_ROOT_SHA in text
        assert PLAN_ROOT_SHA in text
        assert CORPUS_ROOT_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    output_root_exists: bool = False,
) -> dict:
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    static_review = tmp_path / "static_review"
    split_plan = tmp_path / "split_plan"
    corpus = tmp_path / "corpus"
    static_review.mkdir()
    split_plan.mkdir()
    corpus.mkdir()
    static_json = static_review / module.SOURCE_STATIC_REVIEW_JSON_NAME
    plan_json = split_plan / module.SOURCE_PLAN_JSON_NAME
    _write_json(static_json, _static_review_payload(module))
    _write_json(plan_json, _split_plan_payload(module))
    _write(static_review / module.SOURCE_STATIC_REVIEW_MD_NAME, "# Static Review\n")
    _write(split_plan / module.SOURCE_PLAN_MD_NAME, "# Split Plan\n")
    _write(corpus / "records.jsonl", "{}\n")
    _write(corpus / "scene_distribution.json", "{}\n")
    for artifact in (static_review, split_plan, corpus):
        _write(artifact / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
        _write(artifact / "COMMAND", "command\n")
    _write_sha(static_review, (module.SOURCE_STATIC_REVIEW_JSON_NAME, module.SOURCE_STATIC_REVIEW_MD_NAME, "HEADS", "COMMAND"))
    _write_sha(split_plan, (module.SOURCE_PLAN_JSON_NAME, module.SOURCE_PLAN_MD_NAME, "HEADS", "COMMAND"))
    _write_sha(corpus, ("records.jsonl", "scene_distribution.json", "HEADS", "COMMAND"))
    _write(static_review / "ROOT_SHA256SUMS", f"{STATIC_REVIEW_ROOT_SHA}  SHA256SUMS\n")
    _write(split_plan / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
    _write(corpus / "ROOT_SHA256SUMS", f"{CORPUS_ROOT_SHA}  SHA256SUMS\n")
    execution_output_root = tmp_path / "execution_out"
    if output_root_exists:
        execution_output_root.mkdir()
    return {
        "source_static_review_artifact_dir": static_review,
        "source_static_review_json": static_json,
        "source_static_review_sha256s": static_review / "SHA256SUMS",
        "source_static_review_root_sha256s": static_review / "ROOT_SHA256SUMS",
        "source_plan_artifact_dir": split_plan,
        "source_plan_json": plan_json,
        "source_plan_sha256s": split_plan / "SHA256SUMS",
        "source_plan_root_sha256s": split_plan / "ROOT_SHA256SUMS",
        "source_corpus_artifact_dir": corpus,
        "source_corpus_sha256s": corpus / "SHA256SUMS",
        "source_corpus_root_sha256s": corpus / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "preflight_out",
        "execution_output_root": execution_output_root,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_corpus_root_sha256": CORPUS_ROOT_SHA,
        "enabled": True,
    }


def _static_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_plan_artifact": "/root/autodl-tmp/split_plan",
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "plan_review": _plan_review_payload(module),
        "final_decision": _source_final(module),
    }


def _split_plan_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.SOURCE_PLAN_READY_STATUS,
        "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        "source_corpus_artifact": {
            "path": "/root/autodl-tmp/corpus",
            "root_sha256": CORPUS_ROOT_SHA,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_plan": _plan_review_payload(module),
        "final_decision": {
            **_source_final(module),
            "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
            "split_plan_only": True,
            "split_executed": False,
        },
    }


def _plan_review_payload(module) -> dict:
    return {
        "records": 10000,
        "source_records": 10000,
        "scenes": 50,
        "source_scene_count": 50,
        "unique_samples": 10000,
        "source_unique_sample_count": 10000,
        "planned_scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
        "planned_record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
        "scene_zero_overlap": True,
        "sample_zero_overlap": True,
        "record_level_hard_split_executed": False,
        "k_values": [8],
        "candidate_count_values": [8],
        "dp_head_values": [module.FIXED_DP_HEAD],
        "candidate_tensor_mutated_count": 0,
        "followup_policy": {
            "training": "train split only",
            "paired_eval_primary": "calibration+holdout",
        },
    }


def _source_final(module) -> dict:
    return {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "static_review_only": True,
        "split_executed": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha(root: Path, names: tuple[str, ...]) -> None:
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
