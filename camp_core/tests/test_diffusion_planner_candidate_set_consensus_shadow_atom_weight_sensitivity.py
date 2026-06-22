from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)
from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (
    COEFFICIENT_FIELD,
    PAYLOAD_KEY,
)


def _plan(
    *,
    expected_logs: int = 2,
    expected_records: int = 4,
    expected_candidates: int = 2,
    lambda_grid: list[float] | None = None,
    **decision_overrides: object,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_shadow_atom_weight_sensitivity_plan_ready",
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_weight_sensitivity_implementation_unit_tests_only"
        ),
        "weight_sensitivity_plan_ready": True,
        "sensitivity_implementation_authorized": True,
        "sensitivity_execution_authorized": False,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "sensitivity_plan": {
            "expected_logs": expected_logs,
            "expected_records": expected_records,
            "expected_candidates": expected_candidates,
            "formal_seeds_forbidden": [11, 12, 13],
            "atom_name": "candidate_set_consensus_center_rms_cost_v1",
            "payload_key": PAYLOAD_KEY,
            "coefficient_field": COEFFICIENT_FIELD,
            "lambda_grid": [0.0, 0.05, 0.1]
            if lambda_grid is None
            else lambda_grid,
            "score_formula": (
                "score_prime_k(lambda) = selection_score_k + lambda * "
                "candidate_set_consensus_center_rms_m[k]"
            ),
        },
    }


def _payload(*, coeff: list[float] | None = None) -> dict:
    return {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
        "candidate_count": 2,
        "available": True,
        "availability_reason": None,
        COEFFICIENT_FIELD: [1.0, 0.0] if coeff is None else coeff,
        "atom_candidate_names": list(CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES),
    }


def _record(
    *,
    coeff: list[float] | None = None,
    bad_selected_score: bool = False,
    fallback: bool = False,
) -> dict:
    if fallback:
        feasible = [False, False]
        scores = [0.0, 0.05]
    else:
        feasible = [True, True]
        scores = [0.0, 0.05]
        if bad_selected_score:
            scores = [0.1, 0.0]
    return {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        PAYLOAD_KEY: _payload(coeff=coeff),
        "selection_scores": scores,
        "feasible_mask": feasible,
        "used_fallback": fallback,
        "camp_fallback_mode": "uniform",
        "infeasibility_reasons": [[], []],
    }


def _write_logs(
    root: Path,
    *,
    coeff: list[float] | None = None,
    bad_selected_score: bool = False,
    formal_seed: bool = False,
    fallback: bool = False,
) -> None:
    for run_idx in range(2):
        run_name = (
            f"sample_tl59_seed11_npc0_tlon_{run_idx}"
            if formal_seed and run_idx == 0
            else f"sample_tl59_seed20{run_idx}_npc0_tlon"
        )
        run = root / run_name
        run.mkdir(parents=True)
        rows = [
            _record(
                coeff=coeff,
                bad_selected_score=bad_selected_score and run_idx == 0 and idx == 0,
                fallback=fallback and idx == 1,
            )
            for idx in range(2)
        ]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_candidate_set_consensus_weight_sensitivity_accepts_grid(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        weight_sensitivity_plan=_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        label="unit",
    )
    decision = report["final_decision"]
    by_lambda = {
        row["lambda"]: row for row in report["sensitivity_summary"]["by_lambda"]
    }

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert by_lambda[0.0]["changed_records"] == 0
    assert by_lambda[0.05]["changed_records"] == 0
    assert by_lambda[0.1]["changed_records"] == 4
    assert report["sensitivity_summary"]["min_critical_positive_lambda"] == 0.05
    assert report["sensitivity_summary"]["selected_index_transition_counts"] == {
        "0->1": 4
    }
    assert "score'_k(lambda)" in report["analysis"]["math_boundary"]


def test_candidate_set_consensus_weight_sensitivity_retains_fallback_records(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, fallback=True)

    report = analyze(
        weight_sensitivity_plan=_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["sensitivity_summary"]["fallback_retained_records"] == 2
    by_lambda = {
        row["lambda"]: row for row in report["sensitivity_summary"]["by_lambda"]
    }
    assert by_lambda[0.1]["changed_records"] == 2


def test_candidate_set_consensus_weight_sensitivity_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        weight_sensitivity_plan=_plan(
            status="candidate_set_consensus_shadow_atom_weight_sensitivity_plan_rejected",
            passed=False,
            authorized_next_work=None,
            weight_sensitivity_plan_ready=False,
            sensitivity_implementation_authorized=False,
        ),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]
    assert "source_passed" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_weight_sensitivity_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, formal_seed=True)

    report = analyze(
        weight_sensitivity_plan=_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "no_formal_seed_logs" in report["final_decision"]["failed_checks"]
    assert report["sensitivity_summary"]["record_error_counts"]["formal_seed_detected"] == 2


def test_candidate_set_consensus_weight_sensitivity_rejects_negative_coefficient(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, coeff=[1.0, -0.1])

    report = analyze(
        weight_sensitivity_plan=_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_records_valid" in report["final_decision"]["failed_checks"]
    assert (
        report["sensitivity_summary"]["record_error_counts"][
            "coefficient_nonfinite_or_negative"
        ]
        == 4
    )


def test_candidate_set_consensus_weight_sensitivity_rejects_bad_zero_lambda(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, bad_selected_score=True)

    report = analyze(
        weight_sensitivity_plan=_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "lambda_zero_preserves_selection" in report["final_decision"][
        "failed_checks"
    ]


def test_candidate_set_consensus_weight_sensitivity_rejects_bad_source_grid(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        weight_sensitivity_plan=_plan(lambda_grid=[0.1]),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_lambda_grid_contains_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_candidate_set_consensus_weight_sensitivity_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logging_enabled"
    source_json = tmp_path / "plan.json"
    output_json = tmp_path / "sensitivity.json"
    output_md = tmp_path / "sensitivity.md"
    _write_logs(root)
    source_json.write_text(json.dumps(_plan()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-weight-sensitivity",
            "--weight_sensitivity_plan_json",
            str(source_json),
            "--candidate_root",
            str(root),
            "--expected_logs",
            "2",
            "--expected_records",
            "4",
            "--expected_candidates",
            "2",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Shadow Atom Weight Sensitivity" in (
        output_md.read_text(encoding="utf-8")
    )
