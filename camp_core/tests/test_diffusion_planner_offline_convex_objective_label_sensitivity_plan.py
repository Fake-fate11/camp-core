from __future__ import annotations

from pathlib import Path

from scripts.integrations.plan_diffusion_planner_offline_convex_objective_label_sensitivity import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
)


def _diagnosis(status: str = "offline_convex_selector_training_failure_diagnosed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "offline_convex_selector_training_failure_diagnosed",
            "dry_run_selector_rejected": status
            == "offline_convex_selector_training_failure_diagnosed",
            "authorized_next_work": "offline_convex_objective_and_label_sensitivity_plan_only",
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "selector_regression": {
            "changed_record_rate": 0.2,
            "evaluated_minus_logged_cost_mean": 0.1,
            "run_level_evaluated_minus_logged_cost_ci": {"ci95_high": 0.3},
            "regression_components": [
                {"name": "collision", "value": 0.08},
                {"name": "near_miss", "value": 0.01},
            ],
        },
        "proof_failures": {
            "safety_cost_trained_selector_vs_top1": {
                "bucket_failures": {"traffic_light": 0.2}
            },
            "safety_cost_trained_selector_gap_closed": {
                "bucket_failures": {"normal": 0.1, "traffic_light": 1.0}
            },
        },
        "training_summary": {
            "top_weights": [
                {"atom": "planned_red_light_cost", "weight": 0.67},
                {"atom": "red_stopping_margin_cost", "weight": 0.15},
            ]
        },
        "failure_hypotheses": [
            {"name": "critical_bucket_top1_gate_failure"},
            {"name": "hard_guarded_oracle_gap_remains_open"},
        ],
    }


def _source(tmp_path: Path, name: str, tokens: tuple[str, ...]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(tokens), encoding="utf-8")
    return path


def _sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    training = _source(
        tmp_path,
        "train.py",
        (
            "--label_source",
            "safety_cost_v1_hard_guarded",
            "--alpha",
            "--l2_reg",
            "--min_atom_weight",
            "solve_robust_margin_cutting_plane",
            "project_simplex_rows",
        ),
    )
    eval_source = _source(
        tmp_path,
        "eval.py",
        (
            "selector_comparison",
            "weighted_component_delta_mean",
            "run_level_evaluated_minus_logged_cost_ci",
            "--fail_on_formal_seeds",
        ),
    )
    proof = _source(
        tmp_path,
        "proof.py",
        (
            "safety_cost_trained_selector_vs_top1",
            "safety_cost_trained_selector_gap_closed",
            "formal_seeds_authorized",
        ),
    )
    return training, eval_source, proof


def test_objective_label_sensitivity_plan_is_ready_and_plan_only(tmp_path: Path) -> None:
    training, eval_source, proof = _sources(tmp_path)

    report = build_report(
        diagnosis=_diagnosis(),
        training_source=training,
        eval_source=eval_source,
        proof_source=proof,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["plan_checks"][2]["name"] == "logged_selector_regression_gate_required"
    assert any(
        route["name"] == "overall_mean_only_acceptance"
        for route in report["rejected_routes"]
    )
    variants = report["predeclared_sensitivity_plan"]["candidate_variants"]
    assert {variant["name"] for variant in variants} >= {
        "tail_alpha_0p95",
        "safety_guard_floor",
    }
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_objective_label_sensitivity_plan_blocks_if_diagnosis_not_ready(tmp_path: Path) -> None:
    training, eval_source, proof = _sources(tmp_path)
    diagnosis = _diagnosis("offline_convex_selector_training_failure_diagnosis_blocked")
    diagnosis["final_decision"]["authorized_next_work"] = None

    report = build_report(
        diagnosis=diagnosis,
        training_source=training,
        eval_source=eval_source,
        proof_source=proof,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert any(not check["passed"] for check in report["source_checks"])


def test_objective_label_sensitivity_plan_blocks_if_source_lacks_knobs(tmp_path: Path) -> None:
    training, eval_source, proof = _sources(tmp_path)
    training.write_text("--label_source\nsafety_cost_v1_hard_guarded\n", encoding="utf-8")

    report = build_report(
        diagnosis=_diagnosis(),
        training_source=training,
        eval_source=eval_source,
        proof_source=proof,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    token_check = next(
        check
        for check in report["source_checks"]
        if check["name"] == "training_source_supports_existing_objective_knobs"
    )
    assert "--alpha" in token_check["missing_tokens"]
