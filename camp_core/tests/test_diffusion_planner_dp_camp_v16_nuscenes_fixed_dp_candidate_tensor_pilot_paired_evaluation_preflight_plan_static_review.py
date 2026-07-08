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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_plan_static_contract.py"
)
HEAD = "7506316c38212839593152e891c11cf8b5ba9100"
PLAN_HEAD = "09e49fbffd4f6cb1144b6ad1bc26ce01af261f55"
PLAN_ROOT_SHA = "c95c3c99cf0362fac33d6dea85541b55c5903a0c7317cde808b300cfc8dd4d97"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_paired_eval_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_paired_eval_preflight_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["plan_static_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["evaluation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["primary_eval_splits"] == ["calibration", "holdout"]
    assert review["reporting_only_splits"] == ["train"]
    assert review["paired_rows_by_split"] == {
        "calibration": 14,
        "holdout": 147,
        "primary_eval_total": 161,
        "train_reporting_only": 863,
    }
    assert review["comparison"] == {
        "baseline": "dp_top1",
        "camp_selection": "camp_selected_fixed_dp_candidate",
        "candidate_source": "fixed_dp_candidate_tensor",
    }
    assert review["pass_fail_conditions"]["k"] == 8
    assert review["pass_fail_conditions"]["candidate_count"] == 8
    assert review["pass_fail_conditions"]["dp_head_fixed"] == module.FIXED_DP_HEAD
    assert review["pass_fail_conditions"]["candidate_tensor_hashes_present"] is True
    assert review["pass_fail_conditions"]["no_candidate_mutation"] is True
    assert review["pass_fail_conditions"]["affine_simplex_checks_pass"] is True
    assert set(review["metrics_planned"]) >= set(module.REQUIRED_METRICS)
    assert review["pilot_eval_smoke_only"] is True
    assert review["claims"]["performance_claim_allowed"] is False
    assert review["claims"]["safety_claim_allowed"] is False
    assert review["claims"]["camp_over_dp_claim_allowed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_paired_eval_preflight_plan_static_review_rejects_train_leakage(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, primary_eval_splits=["train", "holdout"])

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "primary_eval_splits_calibration_holdout_only" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    primary_eval_splits: list[str] | None = None,
) -> dict:
    plan = module.PLAN_MODULE
    artifact = tmp_path / "paired_eval_preflight_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={plan.READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source = _source_payload(module, primary_eval_splits=primary_eval_splits or ["calibration", "holdout"])
    _write_json(artifact / plan.PLAN_JSON_NAME, source)
    _write(artifact / plan.PLAN_MD_NAME, "# Paired-evaluation preflight plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={PLAN_HEAD}\nCAMP_ORIGIN_MAIN={PLAN_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "paired eval preflight plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        plan.PLAN_JSON_NAME,
        plan.PLAN_MD_NAME,
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
    )
    _write(
        artifact / "SHA256SUMS",
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
    )
    _write(artifact / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": artifact / plan.PLAN_JSON_NAME,
        "source_plan_md": artifact / plan.PLAN_MD_NAME,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "source_plan_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, primary_eval_splits: list[str]) -> dict:
    plan = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": plan.READY_STATUS,
        "authorized_current_work": plan.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "heads": {
            "camp_head": PLAN_HEAD,
            "camp_origin_main": PLAN_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "0ffbf63faa26f2b04d3ffe6ed3c976595cf73c09",
        },
        "paired_evaluation_preflight_plan": {
            "primary_eval_splits": primary_eval_splits,
            "reporting_only_splits": ["train"],
            "paired_rows_by_split": {
                "calibration": 14,
                "holdout": 147,
                "primary_eval_total": 161,
                "train_reporting_only": 863,
            },
            "comparison": {
                "camp_selection": "camp_selected_fixed_dp_candidate",
                "baseline": "dp_top1",
                "candidate_source": "fixed_dp_candidate_tensor",
            },
            "metrics_planned": list(module.REQUIRED_METRICS),
            "pilot_eval_smoke_only": True,
            "claims": {
                "performance_claim_allowed": False,
                "safety_claim_allowed": False,
                "camp_over_dp_claim_allowed": False,
            },
            "pass_fail_conditions": {
                "no_train_leakage_into_primary_eval": True,
                "k": 8,
                "candidate_count": 8,
                "dp_head_fixed": module.FIXED_DP_HEAD,
                "candidate_tensor_hashes_present": True,
                "no_candidate_mutation": True,
                "affine_simplex_checks_pass": True,
            },
            "planned_outputs": {
                "plan_json": plan.PLAN_JSON_NAME,
                "plan_md": plan.PLAN_MD_NAME,
                "heads": "HEADS",
                "command": "COMMAND",
                "stdout": "stdout.txt",
                "stderr": "stderr.txt",
                "sha256s": "SHA256SUMS",
            },
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "paired_evaluation_preflight_plan_only": True,
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


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
