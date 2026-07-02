import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_generation.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_public_sim_execution", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(tmp_path: Path, *, next_work: str | None = None):
    module = _load_module()
    camp_repo = tmp_path / "camp"
    dp_repo = tmp_path / "dp"
    replay_script = camp_repo / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
    _write(
        replay_script,
        "\n".join(
            [
                "import json",
                "import sys",
                "from pathlib import Path",
                "out = Path(sys.argv[sys.argv.index('--output_dir') + 1])",
                "out.mkdir(parents=True, exist_ok=True)",
                "(out / 'camp_validation_summary.json').write_text(json.dumps({",
                "  'camp_default_off_shadow_selector': {'enabled': True},",
                "  'camp_candidate_tensor_provenance': {'enabled': True},",
                "}))",
                "(out / 'camp_replay_summary.json').write_text(json.dumps({'ok': True}))",
            ]
        ),
    )
    candidate_root = tmp_path / "candidate_outputs"
    commands = []
    for index in range(32):
        output_dir = candidate_root / f"case_{index:02d}" / "fixed_dp_top1_execution"
        commands.append(
            [
                sys.executable,
                str(replay_script),
                "--output_dir",
                str(output_dir),
                "--steps",
                "100",
                "--seed",
                str((index % 4) + 1),
                "--num_candidates",
                "8",
                "--camp_selector_mode",
                "static",
                "--camp_candidate_tensor_provenance_logging",
                "--camp_default_off_shadow_selector",
            ]
        )
    preflight = {
        "final_decision": {
            "passed": True,
            "status": module.PREFLIGHT_READY_STATUS,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "fixed_dp_candidate_generation_executed": False,
        },
        "public_simulator_preflight": {
            "candidate_output_root": str(candidate_root),
            "planned_command_count": 32,
            "steps_per_command": 100,
            "expected_records": 3200,
            "num_candidates": 8,
            "executed_output_policy": "dp_top1",
            "default_off_shadow_selector": True,
            "candidate_tensor_provenance_logging": True,
            "camp_repo": str(camp_repo),
            "dp_repo": str(dp_repo),
            "planned_commands": commands,
        },
    }
    preflight_json = tmp_path / "preflight.json"
    preflight_json.write_text(json.dumps(preflight), encoding="utf-8")
    v14_audit = tmp_path / "docs" / "diffusion_planner_v14_iteration_audit.md"
    next_work = next_work or module.AUTHORIZED_CURRENT_WORK
    _write(
        v14_audit,
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = tmp_path / "docs" / "diffusion_planner_current_status.md"
    _write(
        current_status,
        "\n".join(
            [
                "docs/diffusion_planner_v14_iteration_audit.md",
                module.EXPECTED_CURRENT_STATUS,
                module.AUTHORIZED_CURRENT_WORK,
                "",
            ]
        ),
    )
    kwargs = {
        "preflight_json": preflight_json,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "execution_artifact_dir": tmp_path / "execution_artifact",
        "current_camp_head": "abc123",
        "current_camp_origin_main": "abc123",
        "current_dp_head": module.FIXED_DP_HEAD,
    }
    kwargs["execution_artifact_dir"].mkdir(parents=True)
    return module, kwargs, candidate_root


def test_v14_fixed_dp_candidate_generation_execution_runs_guarded_commands(
    tmp_path: Path, monkeypatch
) -> None:
    module, kwargs, candidate_root = _fixture(tmp_path)
    monkeypatch.setenv(module.GUARD_ENV_VAR, "1")

    report = module.build_report(**kwargs)
    assert report["pre_execution_decision"]["passed"] is True
    execution = module.execute_commands(report, kwargs["execution_artifact_dir"])
    final = module._final_decision(
        pre_execution_passed=True,
        execution=execution,
        authorized_next_work=module.AUTHORIZED_NEXT_WORK,
    )

    assert final["passed"] is True
    assert final["status"] == module.EXECUTION_PASSED_STATUS
    assert final["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert final["fixed_dp_candidate_generation_executed"] is True
    assert final["candidate_generation_by_camp_authorized"] is False
    assert final["trajectory_modification_by_camp_authorized"] is False
    assert final["training_execution_authorized_next"] is False
    assert final["dp_modification_authorized"] is False
    assert execution["commands_started"] == 32
    assert execution["commands_succeeded"] == 32
    assert execution["candidate_output_root_exists_after"] is True
    assert candidate_root.exists()
    assert execution["output_summary"]["validation_summary_count"] == 32
    assert execution["output_summary"]["replay_summary_count"] == 32
    assert execution["output_summary"]["default_off_shadow_selector_summary_count"] == 32
    assert execution["output_summary"]["candidate_tensor_provenance_summary_count"] == 32


def test_v14_execution_rejects_missing_guard(tmp_path: Path, monkeypatch) -> None:
    module, kwargs, _candidate_root = _fixture(tmp_path)
    monkeypatch.delenv(module.GUARD_ENV_VAR, raising=False)

    report = module.build_report(**kwargs)

    assert report["pre_execution_decision"]["passed"] is False
    assert "guard_env_set" in report["pre_execution_decision"]["failed_checks"]


def test_v14_execution_rejects_wrong_eof_target(tmp_path: Path, monkeypatch) -> None:
    module, kwargs, _candidate_root = _fixture(
        tmp_path,
        next_work="public_simulator_fixed_dp_candidate_generation_preflight",
    )
    monkeypatch.setenv(module.GUARD_ENV_VAR, "1")

    report = module.build_report(**kwargs)

    assert report["pre_execution_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["pre_execution_decision"]["failed_checks"]


def test_v14_execution_rejects_preexisting_candidate_root(tmp_path: Path, monkeypatch) -> None:
    module, kwargs, candidate_root = _fixture(tmp_path)
    candidate_root.mkdir(parents=True)
    monkeypatch.setenv(module.GUARD_ENV_VAR, "1")

    report = module.build_report(**kwargs)

    assert report["pre_execution_decision"]["passed"] is False
    assert "candidate_output_root_absent_before" in report["pre_execution_decision"]["failed_checks"]


def test_v14_execution_cli_writes_report_and_sha(tmp_path: Path, monkeypatch) -> None:
    module, kwargs, _candidate_root = _fixture(tmp_path)
    monkeypatch.setenv(module.GUARD_ENV_VAR, "1")

    exit_code = module.main(
        [
            "--preflight_json",
            str(kwargs["preflight_json"]),
            "--v14_audit_md",
            str(kwargs["v14_audit_md"]),
            "--current_status_md",
            str(kwargs["current_status_md"]),
            "--execution_artifact_dir",
            str(kwargs["execution_artifact_dir"]),
            "--current_camp_head",
            kwargs["current_camp_head"],
            "--current_camp_origin_main",
            kwargs["current_camp_origin_main"],
            "--current_dp_head",
            kwargs["current_dp_head"],
        ]
    )

    assert exit_code == 0
    report = json.loads((kwargs["execution_artifact_dir"] / "execution_report.json").read_text())
    assert report["final_decision"]["status"] == module.EXECUTION_PASSED_STATUS
    assert "SHA256SUMS" in {path.name for path in kwargs["execution_artifact_dir"].iterdir()}
