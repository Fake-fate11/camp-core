from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
)
HEAD = "f93e57845f7ba79910d7daf3bd071efa1fd3159e"
PREFLIGHT_ROOT_SHA = "b6ab0db5f25674c9d69ff9566a4c413e00529e64ff1baf5de00627cee9db878b"
FAILED_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_candidates_"
    "1503f04e11_20260708T174857CST"
)
FAILED_CAMP_HEAD = "f7ae27d0443a7a4600e8280880c30f1764b86fc1"
FAILED_ROOT_SHA = "2aef585abf06f8b6af2aaaef0f3f16adac3541a52ad264c5da793feb36819666"
FAILED_ROOT_SHA256SUMS_SHA = "c09df735726a38fca14ef33203fdb0952aadc40517cfba5e598415b9be8956ce"
FAILED_JSON_SHA = "0ba94647e2cb355ee8496288cb5c14e66c5dc8f851d97582c737bd44eacbafe6"
FAILED_RECORD0_JSON_SHA = "ec8aefba7b1adc4fb31b4c0ca5e00a4a7d04f982acdf612f136a7fd7356e8a25"
FAILED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_runner_authorization_remediation_only"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_execution_accepts_10k_gate(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_root"], report)

    decision = report["final_decision"]
    runner = report["runner"]
    assert decision["passed"] is True
    assert decision["status"] == module.RUNNING_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_CURRENT_WORK
    assert runner["target_records"] == 10000
    assert runner["minimum_distinct_scenes"] == 30
    assert runner["max_records_per_scene"] == 334
    assert runner["k"] == 8
    assert runner["candidate_count"] == 8
    assert runner["prefer_more_scenes_over_more_records_per_scene"] is True
    assert runner["training_executed"] is False
    assert runner["paired_evaluation_executed"] is False
    assert runner["performance_claimed"] is False
    assert runner["promotion_executed"] is False
    assert runner["deployment_executed"] is False
    for name in (
        module.REPORT_JSON_NAME,
        module.RECORDS_JSONL_NAME,
        module.SCENE_DISTRIBUTION_JSON_NAME,
        module.TIMING_JSON_NAME,
        module.TIMING_MD_NAME,
        module.REPORT_MD_NAME,
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "SHA256SUMS",
        "ROOT_SHA256SUMS",
    ):
        assert (fixture["output_root"] / name).exists()
    assert (fixture["output_root"] / "run.exit").read_text(encoding="utf-8") == "running\n"


def test_v16_scaleup_execution_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_execution_enforces_scene_cap() -> None:
    module = _load_module()
    counts = {"scene-a": 334}

    assert module._can_accept_scene("scene-a", counts, 334) is False
    assert module._can_accept_scene("scene-b", counts, 334) is True


def test_v16_scaleup_execution_prepares_runner_arg_aliases(tmp_path: Path) -> None:
    module = _load_module()
    args = module.parse_args(
        [
            "--output_root",
            str(tmp_path / "out"),
            "--nuscenes_root",
            str(tmp_path / "nuScenes"),
            "--trajdata_cache_dir",
            str(tmp_path / "cache"),
            "--dp_repo",
            str(tmp_path / "dp"),
            "--checkpoint",
            str(tmp_path / "dp" / "checkpoint.pth"),
            "--args_json",
            str(tmp_path / "dp" / "args.json"),
            "--preflight_artifact",
            str(tmp_path / "preflight"),
            "--v16_audit_md",
            str(tmp_path / "audit.md"),
            "--current_status_md",
            str(tmp_path / "status.md"),
            "--current_camp_head",
            HEAD,
            "--current_camp_origin_main",
            HEAD,
            "--current_dp_head",
            module.FIXED_DP_HEAD,
            "--expected_preflight_root_sha256",
            PREFLIGHT_ROOT_SHA,
        ]
    )

    module._prepare_runner_args(args)

    assert args.output_dir == args.output_root
    assert args.metadata_root == args.nuscenes_root


def test_v16_scaleup_execution_failure_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert FAILED_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_status={module.FAILED_STATUS}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_failure_class=exporter_authorization_allowlist_missing_scaleup_execution" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_failed_checks=[exporter:0:exit=1:,status_authorizes_exporter]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_records=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_distinct_scenes=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_k_candidate_count=[8,8]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_camp_head={FAILED_CAMP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_dp_head={module.FIXED_DP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_root_sha256={FAILED_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_root_sha256s_sha256={FAILED_ROOT_SHA256SUMS_SHA}" in text
        assert FAILED_JSON_SHA in text
        assert FAILED_RECORD0_JSON_SHA in text
        assert f"next_work_target={FAILED_NEXT_WORK}" in text
    assert f"current_v16_status={module.FAILED_STATUS}" in status


def _write_fixture(tmp_path: Path, module) -> dict:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    preflight = tmp_path / "preflight"
    preflight.mkdir()
    for name, text in {
        "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight.json": "{}\n",
        "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_preflight.md": "# preflight\n",
        "HEADS": f"DP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "preflight\n",
        "stdout.txt": "",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(preflight / name, text)
    rows = []
    for path in sorted(preflight.iterdir()):
        if path.is_file():
            rows.append(f"{module._sha256(path)}  {path.name}\n")
    _write(preflight / "SHA256SUMS", "".join(rows))
    _write(preflight / "ROOT_SHA256SUMS", f"{PREFLIGHT_ROOT_SHA}  SHA256SUMS\n")
    dp_repo = tmp_path / "Diffusion-Planner"
    (dp_repo / "guidance_gui").mkdir(parents=True)
    (dp_repo / "diffusion_planner").mkdir()
    _write(dp_repo / "guidance_gui" / "generate_samples.py", "")
    _write(dp_repo / "diffusion_planner" / "valid_predictor.py", "")
    return {
        "output_root": tmp_path / "scaleup_candidates",
        "nuscenes_root": _write(tmp_path / "nuScenes" / "README", "ok\n").parent,
        "trajdata_cache_dir": _write(tmp_path / "trajdata_cache" / "README", "ok\n").parent,
        "dp_repo": dp_repo,
        "checkpoint": _write(dp_repo / "checkpoint.pth", "fake\n"),
        "args_json": _write(dp_repo / "args.json", "{}\n"),
        "preflight_artifact": preflight,
        "v16_audit_md": audit,
        "current_status_md": status,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_preflight_root_sha256": PREFLIGHT_ROOT_SHA,
        "target_records": 10000,
        "minimum_distinct_scenes": 30,
        "max_records_per_scene": 334,
        "k": 8,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
