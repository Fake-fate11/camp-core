from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result.py"
)
CURRENT_HEAD = "89191c5593cee343f0b3accbf233858ad2b22e89"
SOURCE_DECISION_HEAD = "a0b4e1a33fe7155956e48f7ae50319e03b036c97"
SOURCE_STATIC_REVIEW_HEAD = "132bfc179b085d838b9825676d493e942d9a5e6c"
SOURCE_PLAN_HEAD = "174c2538a735307a611abb80b9bb6afe9ae39d6b"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_DECISION_ROOT_SHA = "7920ce632f417b56344feef054fdf5a766978603fb1ffd46c8423ab9c68ffbe7"
SOURCE_STATIC_REVIEW_ROOT_SHA = "4fbf099cbe84472c26320db8f3e10c07d0291e4d7cfa4de25aaa544fa1354535"
SOURCE_PLAN_ROOT_SHA = "151b22be196dcd0911857e1e43a9a5919bab5211294fc593941853ada67dbce7"
SOURCE_DECISION_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_"
    "a0b4e1a3_20260710T012719CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_"
    "89191c55_20260710T013445CST"
)
REVIEW_ROOT_SHA = "19e3b8ba1ba9c749920ccd65385c5ad9268ad76dfa6a4786e7f7a1860200905e"
REVIEW_ROOT_SHA256SUMS_SHA = "be54e2c543fb1869efe507a2c51641a4a047e2b3f4b51225b8777c73869e538a"
REVIEW_JSON_SHA = "19441ab15395785423eed968dd1e709478e68fc2a840b2c79df7766e196d7c91"
REVIEW_MD_SHA = "70f564257861b466968b72b10fe87c24a95c3cdc2d7cf2d6718431fa2b580fc8"
REVIEW_HEADS_SHA = "7c3277d3bec48c446875172f117819200bbfb976cb76e3ce67584167618ecba1"
REVIEW_COMMAND_SHA = "4674aa2a58ce20c53515a25ba82acb88416f59e6ace22c9752efabc05716c0bd"
REVIEW_COMMAND_SHELL_SHA = "a32772df195f1d90816c218228907e04067229336433deb78251bbe754a7d8ff"
REVIEW_STDOUT_SHA = "30e464fb3f519efcc115617ac0aa2454e32016689fdf434fda9b2bfae4f384f6"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_only"
CLAIM_TEXT = (
    "在固定 TiER IV Diffusion Planner commit 7a1d33da、固定 K=8 candidate tensors、"
    "v16 nuScenes scale-up paired evaluation 的 3737 calibration+holdout rows 上，"
    "CAMP selector 相比 DP Top-1 降低了当前定义的 paired metric。"
)
FORBIDDEN_CLAIMS = [
    "safety claim",
    "closed-loop safety claim",
    "deployment claim",
    "broad nuScenes benchmark claim",
    "Full36/formal seeds claim",
    "DP model improvement claim",
    "trajectory generation claim",
]
FORBIDDEN_WORDING = ["safe", "deployable", "beats DP generally", "improves TIER IV DP model"]


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_claim_decision_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_claim_decision_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["claim_decision_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["claim_text_modified"] is False
    assert decision["promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert review["source_claim_decision_root_sha256"] == SOURCE_DECISION_ROOT_SHA
    assert review["claim_text"] == CLAIM_TEXT
    assert review["claim_language"] == "zh-CN"
    assert review["claim_text_avoids_forbidden_terms"] is True
    assert review["forbidden_claims"] == FORBIDDEN_CLAIMS
    assert review["forbidden_wording"] == FORBIDDEN_WORDING
    assert review["source_claim_flags"] == {
        "broad_nuscenes_benchmark_claim_authorized": False,
        "closed_loop_safety_claim_authorized": False,
        "deployment_authorized": False,
        "dp_model_improvement_claim_authorized": False,
        "full36_or_formal_seed_claim_authorized": False,
        "limited_descriptive_claim_authorized": True,
        "online_activation_authorized": False,
        "promotion_authorized": False,
        "safety_claim_authorized": False,
        "trajectory_generation_claim_authorized": False,
    }
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_claim_decision_result_review_rejects_forbidden_wording(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, claim_text="This is safe and deployable.")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "claim_text_avoids_forbidden_terms" in report["final_decision"]["failed_checks"]


def test_v16_claim_decision_result_review_rejects_wrong_eof_target(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_current_next_work" in report["final_decision"]["failed_checks"]


def test_v16_claim_decision_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_status={module.READY_STATUS}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_artifact={REVIEW_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_claim_decision_artifact={SOURCE_DECISION_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_claim_decision_root_sha256={SOURCE_DECISION_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_static_review_root_sha256={SOURCE_STATIC_REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_plan_root_sha256={SOURCE_PLAN_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_claim_decision_camp_head={SOURCE_DECISION_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_static_review_camp_head={SOURCE_STATIC_REVIEW_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_source_plan_camp_head={SOURCE_PLAN_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_dp_head={DP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_check_count=47" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_claim_text={CLAIM_TEXT}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_claim_text_avoids_forbidden_terms=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_result_review_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_claim_text_modified=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_promotion_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_deployment_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_online_activation_authorized=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_root_sha256s_sha256={REVIEW_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_report_json_sha256={REVIEW_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_report_md_sha256={REVIEW_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_heads_sha256={REVIEW_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_command_sha256={REVIEW_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_command_shell_sha256={REVIEW_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_stdout_sha256={REVIEW_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_stderr_sha256={REVIEW_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_run_exit_sha256={REVIEW_RUN_EXIT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_authorized_next_work={module.AUTHORIZED_NEXT_WORK}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={REVIEW_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    claim_text: str = CLAIM_TEXT,
    next_work: str | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "claim_decision"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_DECISION_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write_json(artifact / module.SOURCE_DECISION_JSON_NAME, _source_decision_payload(module, claim_text=claim_text))
    _write(artifact / module.SOURCE_DECISION_MD_NAME, "# Claim decision\n")
    for name, content in {
        "HEADS": (
            f"CAMP_HEAD={SOURCE_DECISION_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_DECISION_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
            f"SOURCE_STATIC_REVIEW_CAMP_HEAD={SOURCE_STATIC_REVIEW_HEAD}\n"
            f"SOURCE_PLAN_CAMP_HEAD={SOURCE_PLAN_HEAD}\n"
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={SOURCE_STATIC_REVIEW_ROOT_SHA}\n"
            f"SOURCE_PLAN_ROOT_SHA256={SOURCE_PLAN_ROOT_SHA}\n"
            f"NEXT_WORK_TARGET={module.AUTHORIZED_CURRENT_WORK}\n"
        ),
        "COMMAND": "claim decision\n",
        "COMMAND.shell": "claim decision shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_sha_manifest(artifact)
    _write(artifact / "ROOT_SHA256SUMS", f"{SOURCE_DECISION_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_claim_decision_artifact_dir": artifact,
        "source_claim_decision_json": artifact / module.SOURCE_DECISION_JSON_NAME,
        "source_claim_decision_md": artifact / module.SOURCE_DECISION_MD_NAME,
        "source_claim_decision_sha256s": artifact / "SHA256SUMS",
        "source_claim_decision_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_claim_decision_root_sha256": SOURCE_DECISION_ROOT_SHA,
        "enabled": True,
    }


def _source_decision_payload(module, *, claim_text: str) -> dict[str, Any]:
    return {
        "schema_version": module.SOURCE_DECISION_SCHEMA,
        "status": module.SOURCE_DECISION_STATUS,
        "authorized_current_work": module.SOURCE_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "claim_record": {
            "claim_text": claim_text,
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "forbidden_wording": FORBIDDEN_WORDING,
            "language": "zh-CN",
            "metrics": {},
            "non_claim_boundary": module.SOURCE_MODULE.NON_CLAIM_BOUNDARY,
            "source_plan_root_sha256": SOURCE_PLAN_ROOT_SHA,
            "source_static_review_root_sha256": SOURCE_STATIC_REVIEW_ROOT_SHA,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "broad_nuscenes_benchmark_claim_authorized": False,
            "claim_executed_by_this_gate": True,
            "closed_loop_safety_claim_authorized": False,
            "deployment_authorized": False,
            "dp_model_improvement_claim_authorized": False,
            "full36_or_formal_seed_claim_authorized": False,
            "limited_descriptive_claim_authorized": True,
            "online_activation_authorized": False,
            "passed": True,
            "promotion_authorized": False,
            "safety_claim_authorized": False,
            "status": module.SOURCE_DECISION_STATUS,
            "trajectory_generation_claim_authorized": False,
        },
        "heads": {
            "camp_head": SOURCE_DECISION_HEAD,
            "camp_origin_main": SOURCE_DECISION_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_plan_camp_head": SOURCE_PLAN_HEAD,
            "source_static_review_camp_head": SOURCE_STATIC_REVIEW_HEAD,
        },
    }


def _write_sha_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(file_path)}  {file_path.name}\n")
    _write(path / "SHA256SUMS", "".join(rows))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
