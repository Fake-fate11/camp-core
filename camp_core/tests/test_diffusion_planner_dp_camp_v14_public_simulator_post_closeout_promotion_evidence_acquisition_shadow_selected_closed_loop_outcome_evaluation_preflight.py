from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_shadow_selected_closed_loop_outcome_evaluation.py"
)
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_shadow_selected_closed_loop_outcome_evaluation_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_shadow_selected_closed_loop_outcome_evaluation_preflight_builds_runbook(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    runbook = (fixture["output_dir"] / module.RUNBOOK_NAME).read_text(encoding="utf-8")
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["shadow_selected_closed_loop_outcome_evaluation_execution_authorized"] is True
    assert decision["shadow_selected_closed_loop_outcome_evaluation_executed_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["runbook_plan"]["command_count"] == 2
    assert report["runbook_plan"]["inventory"]["generated_default_off_command_count"] == 0
    assert "--camp_default_off_shadow_selector" not in runbook
    assert "--camp_shadow_artifact_manifest" not in runbook
    assert "--camp_collect_closed_loop_outcomes" not in runbook
    assert "runtime_shadow_selected_closed_loop_evaluation" in runbook
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_shadow_selected_closed_loop_outcome_evaluation_preflight_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, seeds=(1, 11))

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "generated_formal_seed_count" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "shadow_selected_runbook_contract_failure"
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_shadow_selected_closed_loop_outcome_evaluation_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work_user_decision" in report["final_decision"]["failed_checks"]
    assert "status_latest_next_work_user_decision" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    seeds: tuple[int, int] = (1, 2),
    next_work: str | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_FAILURE_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "actual_safetycost_outcome_materialization_execution_failed=True",
            "actual_safetycost_v1_available=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_artifact = tmp_path / "source_runtime_artifact"
    source_artifact.mkdir()
    _write(
        source_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={'c' * 40}",
                f"CAMP_ORIGIN_MAIN={'c' * 40}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(source_artifact / "SHA256SUMS", "empty  HEADS\n")

    source_root = tmp_path / "source_runtime"
    source_root.mkdir()
    source_runbook = _write(
        source_artifact / "run_runtime_shadow_replay.sh",
        "\n".join(
            _command_lines(source_root, seeds=seeds)
        )
        + "\n",
    )

    paired_artifact = tmp_path / "paired_execution"
    paired_dir = paired_artifact / "evaluation"
    paired_dir.mkdir(parents=True)
    paired_json = _write_json(
        paired_dir / "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution.json",
        {"final_decision": {"passed": True, "actual_safetycost_v1_available": False}},
    )
    _write(paired_artifact / "SHA256SUMS", "empty  evaluation.json\n")

    materialization_artifact = tmp_path / "materialization_failure"
    materialization_dir = materialization_artifact / "evaluation"
    materialization_dir.mkdir(parents=True)
    materialization_json = _write_json(
        materialization_dir
        / "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_execution.json",
        {
            "final_decision": {
                "passed": False,
                "failure_class": "actual_safetycost_outcome_source_missing",
            }
        },
    )
    _write(materialization_artifact / "SHA256SUMS", "empty  evaluation.json\n")

    return {
        "source_runtime_execution_artifact_dir": source_artifact,
        "source_runtime_runbook": source_runbook,
        "source_runtime_execution_root": source_root,
        "paired_execution_artifact_dir": paired_artifact,
        "paired_execution_json": paired_json,
        "materialization_failure_artifact_dir": materialization_artifact,
        "materialization_failure_json": materialization_json,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "shadow_selected_output_root": tmp_path / "shadow_selected_out",
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_command_count": 2,
        "enabled": True,
    }


def _command_lines(source_root: Path, *, seeds: tuple[int, int]) -> list[str]:
    lines = []
    for index, seed in enumerate(seeds, start=1):
        output_dir = source_root / f"route_{index}" / f"seed_{seed}" / "tl_on" / "runtime_default_off_shadow_replay"
        output_dir.mkdir(parents=True)
        command = [
            "/root/miniconda3/bin/python3.12",
            "/root/autodl-tmp/camp_core/scripts/integrations/run_diffusion_planner_camp_replay.py",
            "--diffusion_repo",
            "/root/autodl-tmp/Diffusion-Planner",
            "--map_path",
            "/root/autodl-tmp/camp_dp_assets/map.osm",
            "--route",
            f"/root/autodl-tmp/camp_dp_assets/route_{index}.pkl",
            "--model_path",
            "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth",
            "--model_args",
            "/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json",
            "--config",
            "/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json",
            "--reward_config",
            "/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json",
            "--output_dir",
            str(output_dir),
            "--device",
            "cuda",
            "--advance_mode",
            "perfect",
            "--steps",
            "100",
            "--seed",
            str(seed),
            "--max_npcs",
            "4",
            "--spawn_probability",
            "0.3",
            "--traffic_lights",
            "on",
            "--camp_selector_mode",
            "static",
            "--camp_static_weights",
            "/root/autodl-tmp/weights/offline_weights_dp_static.npy",
            "--camp_atom_scales",
            "/root/autodl-tmp/weights/atom_scales_dp_static.json",
            "--camp_fallback_mode",
            "top1",
            "--camp_feasibility_source",
            "dp_reward",
            "--camp_min_progress_ratio",
            "0.8",
            "--num_candidates",
            "8",
            "--camp_candidate_tensor_provenance_logging",
            "--camp_default_off_shadow_selector",
            "--camp_shadow_artifact_manifest",
            "/root/autodl-tmp/manifest.json",
            "--camp_shadow_expected_atom_scales_sha256",
            "a" * 64,
            "--camp_shadow_expected_static_weights_sha256",
            "b" * 64,
        ]
        lines.append(" ".join(_quote(part) for part in command))
    return lines


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")
