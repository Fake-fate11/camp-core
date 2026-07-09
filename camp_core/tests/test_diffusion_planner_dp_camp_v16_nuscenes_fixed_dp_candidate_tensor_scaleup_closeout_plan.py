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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout.py"
)
CURRENT_HEAD = "ed54b6070de7f2e1f11644abf49cf65e8720c4a2"
SOURCE_REVIEW_HEAD = "89191c5593cee343f0b3accbf233858ad2b22e89"
SOURCE_DECISION_HEAD = "a0b4e1a33fe7155956e48f7ae50319e03b036c97"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_REVIEW_ROOT_SHA = "19e3b8ba1ba9c749920ccd65385c5ad9268ad76dfa6a4786e7f7a1860200905e"
SOURCE_DECISION_ROOT_SHA = "7920ce632f417b56344feef054fdf5a766978603fb1ffd46c8423ab9c68ffbe7"
SOURCE_REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_"
    "89191c55_20260710T013445CST"
)
CLOSEOUT_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_"
    "ed54b607_20260710T014244CST"
)
CLOSEOUT_ROOT_SHA = "0b7e79c3be3d277c6b06b45d02a6e9ed24f152bda5cb0b82371788104d958d72"
CLOSEOUT_ROOT_SHA256SUMS_SHA = "97311aab5dd0316ab332a60fa4159aace2c01b0bbc57b45d85d61a29e33d0180"
CLOSEOUT_JSON_SHA = "10ab25351ad6640b7ededea2251682baf13c1a94168a97372f2554d1aa145879"
CLOSEOUT_MD_SHA = "9a36fb5067b2f0d08b6d4228a8983da0b1fe861e27e197242251016d7fec6d10"
CLOSEOUT_HEADS_SHA = "55eeb092b05702acb18011f8f88d55c12214bd39f9d9ceb089915415cbd26fe8"
CLOSEOUT_COMMAND_SHA = "9032f9501593e7ce8f774ad1df4cd4c93c70dc370e48afd3b5715d24ba60841c"
CLOSEOUT_COMMAND_SHELL_SHA = "e30a1c983e47e0b2822cc3745a5aa74d1510ec36c69ab9de5e703ec5df77c2dc"
CLOSEOUT_STDOUT_SHA = "689fa8a92e401ad988e8dfebba32ccb9cb6450982adebb5094cd889ba1157e02"
CLOSEOUT_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
CLOSEOUT_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "user_decision_required_before_v16_nuscenes_fixed_dp_candidate_tensor_next_stage"
CLAIM_TEXT = (
    "在固定 TiER IV Diffusion Planner commit 7a1d33da、固定 K=8 candidate tensors、"
    "v16 nuScenes scale-up paired evaluation 的 3737 calibration+holdout rows 上，"
    "CAMP selector 相比 DP Top-1 降低了当前定义的 paired metric。"
)
NEXT_OPTIONS = [
    "32k expansion plan for stronger evidence",
    "formal benchmark/claim pathway",
    "integration/runtime packaging pathway",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_closeout_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_closeout_plan_lists_user_choices(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    closeout = report["scaleup_closeout_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["closeout_plan_only"] is True
    assert decision["user_decision_required"] is True
    assert decision["next_stage_executed"] is False
    assert closeout["source_result_review_root_sha256"] == SOURCE_REVIEW_ROOT_SHA
    assert closeout["claim_text"] == CLAIM_TEXT
    assert closeout["current_scope"] == {
        "candidate_count": 8,
        "dataset": "v16 nuScenes scale-up paired evaluation",
        "fixed_dp_head": DP_HEAD,
        "primary_eval_rows": 3737,
        "records": 10000,
        "scenes": 50,
    }
    assert closeout["current_metrics"] == {
        "better_tie_worse": [3365, 359, 13],
        "ci95_high": -0.01326782174277094,
        "mean_delta": -0.01762098077036227,
        "non_top1_selection_rate": 0.903933636606904,
        "oracle_gap_closed": 0.9619006786247026,
    }
    assert closeout["next_options"] == NEXT_OPTIONS
    assert closeout["not_executed"] == {
        "32k_expansion": True,
        "formal_benchmark": True,
        "integration_runtime_packaging": True,
        "promotion": True,
        "deployment": True,
        "online_activation": True,
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_closeout_plan_rejects_wrong_eof_target(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_current_next_work" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_closeout_plan_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert CLOSEOUT_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_status={module.READY_STATUS}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_artifact={CLOSEOUT_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_source_result_review_artifact={SOURCE_REVIEW_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_source_result_review_root_sha256={SOURCE_REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_source_claim_decision_root_sha256={SOURCE_DECISION_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_source_result_review_camp_head={SOURCE_REVIEW_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_source_claim_decision_camp_head={SOURCE_DECISION_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_dp_head={DP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_check_count=38" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_claim_text={CLAIM_TEXT}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_next_options=[32k expansion plan for stronger evidence,formal benchmark/claim pathway,integration/runtime packaging pathway]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_user_decision_required=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_next_stage_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_32k_expansion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_formal_benchmark_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_integration_runtime_packaging_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_root_sha256={CLOSEOUT_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_root_sha256s_sha256={CLOSEOUT_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_report_json_sha256={CLOSEOUT_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_report_md_sha256={CLOSEOUT_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_heads_sha256={CLOSEOUT_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_command_sha256={CLOSEOUT_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_command_shell_sha256={CLOSEOUT_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_stdout_sha256={CLOSEOUT_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_stderr_sha256={CLOSEOUT_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_run_exit_sha256={CLOSEOUT_RUN_EXIT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_closeout_plan_authorized_next_work={module.AUTHORIZED_NEXT_WORK}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={CLOSEOUT_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16
    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict[str, Any]:
    artifact = tmp_path / "claim_decision_result_review"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write_json(artifact / module.SOURCE_REVIEW_JSON_NAME, _source_review_payload(module))
    _write(artifact / module.SOURCE_REVIEW_MD_NAME, "# Claim decision result review\n")
    for name, content in {
        "HEADS": (
            f"CAMP_HEAD={SOURCE_REVIEW_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_REVIEW_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
            f"SOURCE_CLAIM_DECISION_CAMP_HEAD={SOURCE_DECISION_HEAD}\n"
            f"SOURCE_CLAIM_DECISION_ROOT_SHA256={SOURCE_DECISION_ROOT_SHA}\n"
            f"NEXT_WORK_TARGET={module.AUTHORIZED_CURRENT_WORK}\n"
        ),
        "COMMAND": "claim decision result review\n",
        "COMMAND.shell": "claim decision result review shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_sha_manifest(artifact)
    _write(artifact / "ROOT_SHA256SUMS", f"{SOURCE_REVIEW_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_result_review_artifact_dir": artifact,
        "source_result_review_json": artifact / module.SOURCE_REVIEW_JSON_NAME,
        "source_result_review_md": artifact / module.SOURCE_REVIEW_MD_NAME,
        "source_result_review_sha256s": artifact / "SHA256SUMS",
        "source_result_review_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_result_review_root_sha256": SOURCE_REVIEW_ROOT_SHA,
        "enabled": True,
    }


def _source_review_payload(module) -> dict[str, Any]:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_current_work": module.SOURCE_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "claim_decision_result_review": {
            "claim_text": CLAIM_TEXT,
            "claim_text_avoids_forbidden_terms": True,
            "source_claim_decision_root_sha256": SOURCE_DECISION_ROOT_SHA,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "claim_text_modified": False,
            "deployment_authorized": False,
            "online_activation_authorized": False,
            "passed": True,
            "promotion_authorized": False,
            "result_review_only": True,
            "status": module.SOURCE_REVIEW_STATUS,
        },
        "heads": {
            "camp_head": SOURCE_REVIEW_HEAD,
            "camp_origin_main": SOURCE_REVIEW_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_claim_decision_camp_head": SOURCE_DECISION_HEAD,
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
