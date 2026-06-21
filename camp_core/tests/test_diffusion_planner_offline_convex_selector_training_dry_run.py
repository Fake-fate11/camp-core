from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from scripts.integrations.run_diffusion_planner_offline_convex_selector_training_dry_run import (
    BLOCKED_STATUS,
    COMPLETE_STATUS,
    run_dry_run,
)


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _log(tmp_path: Path) -> Path:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([{"atoms": [[1.0]], "feasible_mask": [True]}]), encoding="utf-8")
    return path


def _manifest(log_path: Path) -> dict:
    return {
        "final_decision": {
            "status": "offline_convex_selector_training_input_manifest_ready",
            "passed": True,
            "authorized_next_work": "offline_convex_selector_training_execution_dry_run_only",
        },
        "summary": {
            "records": 1,
            "formal_seed_logs": 0,
            "required_buckets": ["normal"],
            "bucket_record_counts": {"normal": 1, "overall": 1},
        },
        "manifest": {
            "logs": [
                {
                    "path": str(log_path),
                    "sha256": _sha(log_path),
                    "records": 1,
                    "scenario_buckets": ["overall", "normal"],
                }
            ]
        },
    }


def _fake_runner(command, **_kwargs):
    command_text = " ".join(str(part) for part in command)
    if "train_diffusion_planner_robust_camp.py" in command_text:
        output_dir = Path(command[command.index("--output_dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        scales = output_dir / "atom_scales_dp_static.json"
        weights = output_dir / "offline_weights_dp_static.npy"
        scales.write_text(
            json.dumps({"atom_schema_version": "unit", "atom_names": ["a"], "scales": [1.0]}),
            encoding="utf-8",
        )
        np.save(weights, np.asarray([1.0], dtype=np.float64))
        (output_dir / "training_summary.json").write_text(
            json.dumps(
                {
                    "artifacts": {
                        "atom_scales_path": str(scales),
                        "weights_path": str(weights),
                    },
                    "converged": True,
                }
            ),
            encoding="utf-8",
        )
    elif "evaluate_diffusion_planner_camp_safety_cost.py" in command_text:
        output_json = Path(command[command.index("--output_json") + 1])
        output_md = Path(command[command.index("--output_md") + 1])
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps({"analysis": {"name": "eval"}}), encoding="utf-8")
        output_md.write_text("# eval\n", encoding="utf-8")
    elif "summarize_diffusion_planner_camp_safety_cost_proof.py" in command_text:
        output_json = Path(command[command.index("--output_json") + 1])
        output_md = Path(command[command.index("--output_md") + 1])
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                {
                    "final_decision": {
                        "status": "candidate_branch_proof_passes_for_safety_cost_trained_selector",
                        "safety_cost_trained_selector_candidate_branch_proof": True,
                    }
                }
            ),
            encoding="utf-8",
        )
        output_md.write_text("# proof\n", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")


def test_offline_convex_training_dry_run_executes_three_steps(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    oracle = tmp_path / "oracle.json"
    oracle.write_text("{}", encoding="utf-8")
    buckets = tmp_path / "buckets.json"
    buckets.write_text("{}", encoding="utf-8")

    report = run_dry_run(
        manifest=_manifest(log_path),
        oracle_report=oracle,
        scenario_bucket_manifest=buckets,
        output_dir=tmp_path / "out",
        selector_name="unit_selector",
        runner=_fake_runner,
    )

    decision = report["final_decision"]
    assert decision["status"] == COMPLETE_STATUS
    assert decision["candidate_branch_proof_passed"] is True
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert set(report["commands"]) == {"training", "selector_eval", "proof_summary"}
    assert "training_summary" in report["artifacts"]
    assert "selector_eval" in report["artifacts"]
    assert "camp_vs_top1_safety_cost_proof" in report["artifacts"]


def test_offline_convex_training_dry_run_blocks_bad_manifest(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    manifest = _manifest(log_path)
    manifest["final_decision"]["status"] = "offline_convex_selector_training_input_manifest_blocked"

    report = run_dry_run(
        manifest=manifest,
        oracle_report=tmp_path / "oracle.json",
        scenario_bucket_manifest=tmp_path / "buckets.json",
        output_dir=tmp_path / "out",
        runner=_fake_runner,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["commands"] == {}
    assert "manifest_status_not_ready" in report["input_check"]["errors"]


def test_offline_convex_training_dry_run_blocks_hash_mismatch(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    manifest = _manifest(log_path)
    manifest["manifest"]["logs"][0]["sha256"] = "bad"

    report = run_dry_run(
        manifest=manifest,
        oracle_report=tmp_path / "oracle.json",
        scenario_bucket_manifest=tmp_path / "buckets.json",
        output_dir=tmp_path / "out",
        runner=_fake_runner,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert any("sha_mismatch" in error for error in report["input_check"]["errors"])
