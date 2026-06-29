from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.plan_diffusion_planner_dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_training_artifact_shadow_replay_evaluation_preflight import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "c7402f3aaa4408d7d7c3fbada9248031d3343f37"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _runner_source() -> str:
    return """
parser.add_argument(
        "--camp_default_off_shadow_selector"
)
parser.add_argument(
        "--camp_shadow_artifact_manifest"
)
def _load_shadow_artifact_manifest(path): pass
{"executed_output_policy": "dp_top1"}
shadow_selected_index
"""


def _audit_text(*, wrong_scope: bool = False) -> str:
    next_target = (
        "old_scope"
        if wrong_scope
        else (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
            "nonformal_shadow_replay_batch_static_dp_reward_training_artifact_"
            "shadow_replay_evaluation_preflight_only"
        )
    )
    return "\n".join(
        [
            "current_v13_status=current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_static_dp_reward_training_execution_passed",
            f"next_work_target={next_target}",
            "runtime_shadow_selector_execution_authorized=False",
            "replay_execution_authorized_by_current_boundary=False",
            "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        ]
    )


def _paths(tmp_path: Path, *, wrong_scope: bool = False) -> dict[str, Path]:
    version, names = atom_schema_for_dimension(14)
    training_dir = tmp_path / "training"
    training_dir.mkdir()
    weights_path = training_dir / "offline_weights_dp_static.npy"
    np.save(weights_path, np.full(14, 1.0 / 14.0, dtype=np.float64))
    scales_path = training_dir / "atom_scales_dp_static.json"
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": version,
                "atom_names": list(names),
                "scales": [1.0 + index for index in range(14)],
            }
        ),
        encoding="utf-8",
    )
    summary_path = training_dir / "training_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "label_source": "dp_reward",
                "reward_key": "quality_without_progress",
                "reward_progress_weight": 2.0,
                "num_records": 2651,
                "dropped_records_without_feasible_candidate": 549,
                "num_candidates": 8,
                "num_atoms": 14,
                "atom_schema_version": version,
                "dp_native_training_data_contract": {
                    "passed": True,
                    "records": 3200,
                },
            }
        ),
        encoding="utf-8",
    )
    route_normal = _write(tmp_path / "routes" / "sample_normal.pkl", "route")
    route_tl = _write(tmp_path / "routes" / "sample_tl.pkl", "route")
    diffusion_repo = tmp_path / "Diffusion-Planner"
    diffusion_repo.mkdir()
    model_path = tmp_path / "diffusion_planner.pth"
    model_path.write_bytes(b"model")
    model_args = _write(tmp_path / "diffusion_planner.param.json", "{}")
    config = _write(tmp_path / "replay_default.json", "{}")
    reward_config = _write(tmp_path / "dp_camp_reward_eval.json", "{}")
    runner = _write(tmp_path / "run_diffusion_planner_camp_replay.py", _runner_source())
    audit = _write(tmp_path / "audit.md", _audit_text(wrong_scope=wrong_scope))
    return {
        "summary": summary_path,
        "weights": weights_path,
        "scales": scales_path,
        "route_normal": route_normal,
        "route_tl": route_tl,
        "diffusion_repo": diffusion_repo,
        "model_path": model_path,
        "model_args": model_args,
        "config": config,
        "reward_config": reward_config,
        "runner": runner,
        "audit": audit,
        "base_output": tmp_path / "planned_eval",
        "runtime_manifest": tmp_path / "out" / "runtime_manifest.json",
    }


def _report(tmp_path: Path, **overrides):
    paths = _paths(tmp_path, wrong_scope=overrides.pop("wrong_scope", False))
    params = {
        "training_summary_json": paths["summary"],
        "atom_scales_json": paths["scales"],
        "static_weights_npy": paths["weights"],
        "replay_runner_py": paths["runner"],
        "v13_audit_md": paths["audit"],
        "diffusion_repo": paths["diffusion_repo"],
        "route_specs": (
            f"sample_normal={paths['route_normal']}",
            f"sample_tl={paths['route_tl']}",
        ),
        "model_path": paths["model_path"],
        "model_args": paths["model_args"],
        "config": paths["config"],
        "reward_config": paths["reward_config"],
        "base_replay_output_dir": paths["base_output"],
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "output_runtime_manifest_json": paths["runtime_manifest"],
        "enabled": True,
    }
    params.update(overrides)
    return build_report(**params)


def test_preflight_disabled_does_not_write_manifest(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        training_summary_json=missing,
        atom_scales_json=missing,
        static_weights_npy=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        diffusion_repo=missing,
        route_specs=("sample_normal=/missing.pkl",),
        model_path=missing,
        model_args=missing,
        config=missing,
        reward_config=missing,
        base_replay_output_dir=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        output_runtime_manifest_json=tmp_path / "runtime.json",
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["runtime_manifest_written"] is False


def test_preflight_accepts_training_artifact_and_builds_runbook(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runtime_manifest_written"] is True
    assert decision["replay_execution_performed"] is False
    assert report["preflight"]["command_count"] == 16
    assert report["preflight"]["expected_records"] == 1600
    assert report["runtime_manifest"]["selection_effect"] is False
    assert report["runtime_manifest"]["executed_output_policy"] == "dp_top1"
    assert all(
        "--camp_default_off_shadow_selector" in item["command"]
        for item in report["planned_commands"]
    )
    assert all(
        "--camp_collect_closed_loop_outcomes" not in item["command"]
        for item in report["planned_commands"]
    )


def test_preflight_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_scope_allows_preflight" in report["final_decision"][
        "failed_checks"
    ]


def test_preflight_rejects_formal_seed(tmp_path: Path) -> None:
    report = _report(tmp_path, seeds=(11, 301))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "seeds_exclude_formal" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_existing_runtime_manifest(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths["runtime_manifest"].parent.mkdir(parents=True, exist_ok=True)
    paths["runtime_manifest"].write_text("{}", encoding="utf-8")

    report = build_report(
        training_summary_json=paths["summary"],
        atom_scales_json=paths["scales"],
        static_weights_npy=paths["weights"],
        replay_runner_py=paths["runner"],
        v13_audit_md=paths["audit"],
        diffusion_repo=paths["diffusion_repo"],
        route_specs=(
            f"sample_normal={paths['route_normal']}",
            f"sample_tl={paths['route_tl']}",
        ),
        model_path=paths["model_path"],
        model_args=paths["model_args"],
        config=paths["config"],
        reward_config=paths["reward_config"],
        base_replay_output_dir=paths["base_output"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        output_runtime_manifest_json=paths["runtime_manifest"],
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runtime_manifest_output_absent" in report["final_decision"][
        "failed_checks"
    ]


def test_preflight_cli_writes_reports_manifest_and_runbook(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"
    output_runbook = tmp_path / "out" / "runbook.sh"

    exit_code = main(
        [
            "--training_summary_json",
            str(paths["summary"]),
            "--atom_scales_json",
            str(paths["scales"]),
            "--static_weights_npy",
            str(paths["weights"]),
            "--replay_runner_py",
            str(paths["runner"]),
            "--v13_audit_md",
            str(paths["audit"]),
            "--diffusion_repo",
            str(paths["diffusion_repo"]),
            "--route",
            f"sample_normal={paths['route_normal']}",
            "--route",
            f"sample_tl={paths['route_tl']}",
            "--model_path",
            str(paths["model_path"]),
            "--model_args",
            str(paths["model_args"]),
            "--config",
            str(paths["config"]),
            "--reward_config",
            str(paths["reward_config"]),
            "--base_replay_output_dir",
            str(paths["base_output"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_runtime_manifest_json",
            str(paths["runtime_manifest"]),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_runbook",
            str(output_runbook),
            "--enable_v13_static_dp_reward_training_artifact_shadow_replay_evaluation_preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    manifest = json.loads(paths["runtime_manifest"].read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert manifest["schema_version"] == "dp_camp_v13_default_off_shadow_selector_runtime_v1"
    assert "Do not execute unless the audit EOF authorizes" in output_runbook.read_text(
        encoding="utf-8"
    )
    assert "Runtime manifest written: `True`" in output_md.read_text(encoding="utf-8")
