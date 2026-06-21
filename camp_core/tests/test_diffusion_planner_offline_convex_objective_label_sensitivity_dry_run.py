from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from scripts.integrations.run_diffusion_planner_offline_convex_objective_label_sensitivity_dry_run import (
    BLOCKED_STATUS,
    COMPLETE_STATUS,
    run_sensitivity_dry_run,
)


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _log(tmp_path: Path) -> Path:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(
        json.dumps([{"atoms": [[1.0]], "feasible_mask": [True]}]),
        encoding="utf-8",
    )
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


def _plan(status: str = "offline_convex_objective_label_sensitivity_plan_ready") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "offline_convex_objective_label_sensitivity_plan_ready",
            "authorized_next_work": "implement_objective_label_sensitivity_dry_run_wrapper_only",
        },
        "predeclared_sensitivity_plan": {
            "control_variant": {
                "name": "control_reproduce_failed_35fedb8",
                "parameters": {
                    "label_source": "safety_cost_v1_hard_guarded",
                    "risk_type": "cvar",
                    "alpha": 0.9,
                    "l2_reg": 0.0001,
                    "min_atom_weight": [],
                },
            },
            "candidate_variants": [
                {
                    "name": "tail_alpha_0p95",
                    "parameters": {
                        "label_source": "safety_cost_v1_hard_guarded",
                        "risk_type": "cvar",
                        "alpha": 0.95,
                        "l2_reg": 0.0001,
                        "min_atom_weight": [],
                    },
                },
                {
                    "name": "safety_guard_floor",
                    "parameters": {
                        "label_source": "safety_cost_v1_hard_guarded",
                        "risk_type": "cvar",
                        "alpha": 0.95,
                        "l2_reg": 0.001,
                        "min_atom_weight": [
                            "clearance=0.02",
                            "planned_lateral_acceleration_cost=0.04",
                        ],
                    },
                },
            ],
        },
    }


def _variant_name_from_output(path: Path) -> str:
    parts = path.parts
    for name in (
        "control_reproduce_failed_35fedb8",
        "tail_alpha_0p95",
        "safety_guard_floor",
    ):
        if name in parts:
            return name
    return "unknown"


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
        variant = _variant_name_from_output(output_json)
        accepted = variant == "safety_guard_floor"
        ci_high = -0.1 if accepted else 0.2
        component_delta = -0.01 if accepted else 0.01
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                {
                    "logs": {"formal_seed_logs": 0},
                    "selector_comparison": {
                        "run_level_evaluated_minus_logged_cost_ci": {
                            "ci95_high": ci_high
                        },
                        "weighted_component_delta_mean": {
                            "collision": component_delta,
                            "near_miss": component_delta,
                            "lane_violation": 0.0,
                            "red_light_violation": 0.0,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        output_md.write_text("# eval\n", encoding="utf-8")
    elif "summarize_diffusion_planner_camp_safety_cost_proof.py" in command_text:
        output_json = Path(command[command.index("--output_json") + 1])
        output_md = Path(command[command.index("--output_md") + 1])
        variant = _variant_name_from_output(output_json)
        accepted = variant == "safety_guard_floor"
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                {
                    "gates": {
                        "safety_cost_trained_selector_vs_top1": {
                            "passed": accepted
                        },
                        "safety_cost_trained_selector_gap_closed": {
                            "passed": accepted
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        output_md.write_text("# proof\n", encoding="utf-8")
    return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")


def test_objective_label_sensitivity_wrapper_runs_predeclared_variants(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    report = run_sensitivity_dry_run(
        plan=_plan(),
        manifest=_manifest(log_path),
        oracle_report=tmp_path / "oracle.json",
        scenario_bucket_manifest=tmp_path / "buckets.json",
        output_dir=tmp_path / "out",
        selector_prefix="unit",
        runner=_fake_runner,
    )

    decision = report["final_decision"]
    assert decision["status"] == COMPLETE_STATUS
    assert decision["accepted_variants"] == ["safety_guard_floor"]
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["summary"]["variants_total"] == 3
    control = {row["name"]: row for row in report["variants"]}[
        "control_reproduce_failed_35fedb8"
    ]
    assert control["accepted_for_next_review"] is False
    safety = {row["name"]: row for row in report["variants"]}["safety_guard_floor"]
    assert safety["accepted_for_next_review"] is True
    assert "training_summary_json" in safety["artifacts"]
    assert "selector_eval_json" in safety["artifacts"]
    assert "selector_eval_md" in safety["artifacts"]
    assert "camp_vs_top1_safety_cost_proof_json" in safety["artifacts"]
    assert "camp_vs_top1_safety_cost_proof_md" in safety["artifacts"]


def test_objective_label_sensitivity_wrapper_threads_variant_parameters(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    seen_commands: list[list[str]] = []

    def runner(command, **kwargs):
        seen_commands.append([str(part) for part in command])
        return _fake_runner(command, **kwargs)

    run_sensitivity_dry_run(
        plan=_plan(),
        manifest=_manifest(log_path),
        oracle_report=tmp_path / "oracle.json",
        scenario_bucket_manifest=tmp_path / "buckets.json",
        output_dir=tmp_path / "out",
        runner=runner,
    )

    training_commands = [
        command
        for command in seen_commands
        if any("train_diffusion_planner_robust_camp.py" in part for part in command)
    ]
    assert any("--alpha" in command and command[command.index("--alpha") + 1] == "0.95" for command in training_commands)
    assert any("--l2_reg" in command and command[command.index("--l2_reg") + 1] == "0.001" for command in training_commands)
    flattened = " ".join(" ".join(command) for command in training_commands)
    assert "--min_atom_weight clearance=0.02" in flattened
    assert "--min_atom_weight planned_lateral_acceleration_cost=0.04" in flattened


def test_objective_label_sensitivity_wrapper_blocks_bad_plan(tmp_path: Path) -> None:
    log_path = _log(tmp_path)
    report = run_sensitivity_dry_run(
        plan=_plan("offline_convex_objective_label_sensitivity_plan_blocked"),
        manifest=_manifest(log_path),
        oracle_report=tmp_path / "oracle.json",
        scenario_bucket_manifest=tmp_path / "buckets.json",
        output_dir=tmp_path / "out",
        runner=_fake_runner,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["variants"] == []
    assert "plan_status_not_ready" in report["plan_check"]["errors"]
