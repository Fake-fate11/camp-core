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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_contract.py"
)
REVIEW_CAMP_HEAD = "16dc79401936187938abb9996c627151c16bfa1d"
PLAN_CAMP_HEAD = "f01925cfdcceb8d7288899c0970b82f16cc61592"
PLAN_ROOT_SHA = "24247d7924a7ac388adf7893cc70510b9fa6496aee9b394f34747ead8b12f4e2"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_"
    "f01925cfdc_20260709T165918CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_"
    "16dc794019_20260709T172221CST"
)
REVIEW_JSON_SHA = "c82a8d7a60bf241a4784d2155c4c71f40450b891da678add84cfac93126de3f1"
REVIEW_MD_SHA = "330c02b6f536df7d407a1ca1617739ffe8957be726850213e6eb851c8af6b26e"
REVIEW_SHA256SUMS_SHA = "82182c771919e5dffcff57a546b04931553507a80ec6565bd398d9f6d6747512"
REVIEW_ROOT_SHA256SUMS_SHA = "71e02269373312771393610c0535aa35bc870f40b2b658ffb74f98c67608a733"
REVIEW_HEADS_SHA = "6f31a058b384bb4019c2ae53146712204e77a8846a06a24728a8461b045e0f1f"
REVIEW_COMMAND_SHA = "7d177427958085a098ce42c9d7211fa99c946369ce9c575c2e74e6c5a88bddd5"
REVIEW_STDOUT_SHA = "ddf6863cb158785c230873591b4da7547097e4fec6169b8b97017e82e160ced0"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_paired_eval_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_paired_eval_preflight_plan_static_review_passes(tmp_path: Path) -> None:
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
        "calibration": 2156,
        "holdout": 1581,
        "primary_eval_total": 3737,
        "train_reporting_only": 6263,
    }
    assert review["comparison"] == {
        "baseline": "dp_top1",
        "camp_selection": "camp_selected_fixed_dp_candidate",
        "candidate_source": "fixed_dp_candidate_tensor",
    }
    assert review["pass_fail_conditions"]["no_train_leakage_into_primary_eval"] is True
    assert review["pass_fail_conditions"]["k"] == 8
    assert review["pass_fail_conditions"]["candidate_count"] == 8
    assert review["pass_fail_conditions"]["dp_head_fixed"] == module.FIXED_DP_HEAD
    assert review["pass_fail_conditions"]["candidate_tensor_hashes_present"] is True
    assert review["pass_fail_conditions"]["no_candidate_mutation"] is True
    assert review["pass_fail_conditions"]["affine_simplex_checks_pass"] is True
    assert set(review["metrics_planned"]) >= set(module.REQUIRED_METRICS)
    assert review["scaleup_evidence_only"] is True
    assert review["claims"]["performance_claim_allowed"] is False
    assert review["claims"]["safety_claim_allowed"] is False
    assert review["claims"]["camp_over_dp_claim_allowed"] is False
    assert "no claim until execution and result review pass" in review["claims"]["reason"]
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_paired_eval_preflight_plan_static_review_rejects_train_leakage(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, primary_eval_splits=["train", "holdout"])

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "primary_eval_splits_calibration_holdout_only" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_paired_eval_preflight_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_train_reporting_only_rows=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_calibration_rows=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_holdout_rows=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_primary_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_primary_eval_splits=[calibration,holdout]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_reporting_only_splits=[train]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_comparison=camp_selected_fixed_dp_candidate_vs_dp_top1" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_k=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_candidate_count=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_candidate_tensor_hashes_present=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_no_candidate_mutation=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_affine_simplex_checks_pass=True" in text
        assert "selector_latency_mean_median_p95_p99_max" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_scaleup_evidence_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_camp_over_dp_claimed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_camp_head={REVIEW_CAMP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_source_camp_head={PLAN_CAMP_HEAD}" in text
        assert PLAN_ROOT_SHA in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert REVIEW_HEADS_SHA in text
        assert REVIEW_COMMAND_SHA in text
        assert REVIEW_STDOUT_SHA in text
        assert REVIEW_STDERR_SHA in text
        assert REVIEW_RUN_EXIT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in status
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status


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
    _write(artifact / plan.PLAN_MD_NAME, "# Scale-up paired-evaluation preflight plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={PLAN_CAMP_HEAD}\nCAMP_ORIGIN_MAIN={PLAN_CAMP_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "scale-up paired eval preflight plan\n",
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
        "current_camp_head": REVIEW_CAMP_HEAD,
        "current_camp_origin_main": REVIEW_CAMP_HEAD,
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
            "camp_head": PLAN_CAMP_HEAD,
            "camp_origin_main": PLAN_CAMP_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "7aec1e3b9ec3cd209a142b48986ed74b0386b31a",
        },
        "paired_evaluation_preflight_plan": {
            "primary_eval_splits": primary_eval_splits,
            "reporting_only_splits": ["train"],
            "paired_rows_by_split": {
                "calibration": 2156,
                "holdout": 1581,
                "primary_eval_total": 3737,
                "train_reporting_only": 6263,
            },
            "comparison": {
                "camp_selection": "camp_selected_fixed_dp_candidate",
                "baseline": "dp_top1",
                "candidate_source": "fixed_dp_candidate_tensor",
            },
            "metrics_planned": list(module.REQUIRED_METRICS),
            "scaleup_evidence_only": True,
            "claims": {
                "performance_claim_allowed": False,
                "safety_claim_allowed": False,
                "camp_over_dp_claim_allowed": False,
                "reason": "scale-up evidence only; no claim until execution and result review pass",
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
