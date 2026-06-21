from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.integrations.diagnose_diffusion_planner_offline_convex_objective_label_sensitivity_results import (
    READY_STATUS,
    REDESIGN_NEXT_WORK,
    build_report,
)


def _write_variant_artifacts(
    tmp_path: Path,
    *,
    name: str,
    logged_ci_high: float,
    collision: float,
    near_miss: float,
    top1_failures: dict[str, float],
    gap_failures: dict[str, float],
) -> dict:
    root = tmp_path / name
    training_dir = root / "training"
    eval_dir = root / "selector_eval"
    proof_dir = root / "proof"
    training_dir.mkdir(parents=True)
    eval_dir.mkdir()
    proof_dir.mkdir()
    weights_path = training_dir / "offline_weights_dp_static.npy"
    np.save(weights_path, np.asarray([0.7, 0.2, 0.1], dtype=np.float64))
    training_summary = training_dir / "training_summary.json"
    training_summary.write_text(
        json.dumps(
            {
                "atom_names": [
                    "planned_red_light_cost",
                    "red_stopping_margin_cost",
                    "jerk_early",
                ],
                "converged": True,
                "final_master_gap": 0.0,
                "train": {"oracle_match_rate": 0.6},
                "val": {"oracle_match_rate": 0.5},
            }
        ),
        encoding="utf-8",
    )
    selector_eval = eval_dir / "selector_eval.json"
    selector_eval.write_text(
        json.dumps(
            {
                "logs": {"formal_seed_logs": 0},
                "selector_comparison": {
                    "changed_record_rate": 0.2,
                    "evaluated_minus_logged_cost_mean": 0.1,
                    "run_level_evaluated_minus_logged_cost_ci": {
                        "ci95_high": logged_ci_high
                    },
                    "weighted_component_delta_mean": {
                        "collision": collision,
                        "near_miss": near_miss,
                        "lane_violation": 0.0,
                        "realized_red_light": 0.0,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    proof = proof_dir / "camp_vs_top1_safety_cost_proof.json"
    proof.write_text(
        json.dumps(
            {
                "gates": {
                    "safety_cost_trained_selector_vs_top1": {
                        "passed": False,
                        "overall_ci_high": -0.2,
                        "bucket_failures": top1_failures,
                    },
                    "safety_cost_trained_selector_gap_closed": {
                        "passed": False,
                        "overall_ci_high": 1.0,
                        "bucket_failures": gap_failures,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return {
        "training_summary_json": {"path": str(training_summary), "sha256": "unused"},
        "selector_eval_json": {"path": str(selector_eval), "sha256": "unused"},
        "camp_vs_top1_safety_cost_proof_json": {
            "path": str(proof),
            "sha256": "unused",
        },
        "offline_weights_dp_static": {"path": str(weights_path), "sha256": "unused"},
    }


def _wrapper(tmp_path: Path, *, accepted_variants: list[str] | None = None) -> dict:
    accepted_variants = accepted_variants or []
    variants = [
        {
            "name": "control_reproduce_failed_35fedb8",
            "role": "control",
            "accepted_for_next_review": False,
            "status": "variant_complete",
            "parameters": {"alpha": 0.9},
            "artifacts": _write_variant_artifacts(
                tmp_path,
                name="control_reproduce_failed_35fedb8",
                logged_ci_high=0.17,
                collision=0.08,
                near_miss=0.005,
                top1_failures={"traffic_light": 0.2, "red_light_turn": 0.3},
                gap_failures={"normal": 0.1, "traffic_light": 1.0},
            ),
            "acceptance_gate": {
                "checks": [
                    {"name": "variant_is_not_control", "passed": False},
                    {"name": "top1_bucket_gate_passed", "passed": False},
                    {"name": "logged_selector_nonworse_ci_high", "passed": False},
                ]
            },
        },
        {
            "name": "tail_alpha_0p95",
            "role": "candidate",
            "accepted_for_next_review": False,
            "status": "variant_complete",
            "parameters": {"alpha": 0.95},
            "artifacts": _write_variant_artifacts(
                tmp_path,
                name="tail_alpha_0p95",
                logged_ci_high=0.18,
                collision=0.08,
                near_miss=0.006,
                top1_failures={"traffic_light": 0.2, "red_light_turn": 0.3},
                gap_failures={"normal": 0.1, "traffic_light": 1.0},
            ),
            "acceptance_gate": {
                "checks": [
                    {"name": "top1_bucket_gate_passed", "passed": False},
                    {"name": "logged_selector_nonworse_ci_high", "passed": False},
                    {"name": "component_nonpositive_collision", "passed": False},
                ]
            },
        },
    ]
    return {
        "final_decision": {
            "status": "offline_convex_objective_label_sensitivity_dry_run_complete",
            "passed": True,
            "authorized_next_work": "diagnose_objective_label_sensitivity_results",
            "accepted_variants": accepted_variants,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "summary": {
            "variants_total": len(variants),
            "variants_complete": len(variants),
            "accepted_for_next_review": accepted_variants,
        },
        "variants": variants,
    }


def test_sensitivity_results_diagnosis_rejects_no_direction_route(tmp_path: Path) -> None:
    report = build_report(sensitivity=_wrapper(tmp_path))

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["sensitivity_route_rejected"] is True
    assert decision["authorized_next_work"] == REDESIGN_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["route_diagnosis"]["diagnosis"] == "reject_objective_label_sensitivity_route"
    assert report["comparison_summary"]["credible_direction_candidates"] == []
    candidate = {
        row["name"]: row for row in report["variant_diagnostics"]
    }["tail_alpha_0p95"]
    assert candidate["direction_vs_control"]["credible_direction"] is False
    assert candidate["selector_regression"]["positive_hard_component_deltas"][
        "collision"
    ] == 0.08


def test_sensitivity_results_diagnosis_blocks_when_variant_was_accepted(tmp_path: Path) -> None:
    report = build_report(
        sensitivity=_wrapper(tmp_path, accepted_variants=["tail_alpha_0p95"])
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert any(not check["passed"] for check in report["source_checks"])
