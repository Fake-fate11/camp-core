from __future__ import annotations

import inspect

from scripts.integrations import evaluate_diffusion_planner_v25_fresh_b2 as producer
from scripts.integrations import review_diffusion_planner_v25_fresh_b2_evaluation as reviewer


def test_evaluation_root_gates_are_derived_from_reviewed_denominators() -> None:
    qualification = {
        "zero_overlap_receipt": {
            "status": "passed",
            "fresh_outcome_consumed": False,
        }
    }
    assert producer._derive_root_gates(
        execution_report={
            "planned_arm_run_count": 1500,
            "terminal_arm_run_count": 1500,
            "candidate_tensor_modified": False,
        },
        execution_review={
            "reviewed_arm_run_count": 1500,
            "candidate_tensor_modified": False,
        },
        qualification=qualification,
    ) == {
        "failure_denominator_complete": True,
        "immutability_passed": True,
        "zero_overlap_passed": True,
    }

    assert producer._derive_root_gates(
        execution_report={
            "planned_arm_run_count": 1500,
            "terminal_arm_run_count": 1499,
            "candidate_tensor_modified": False,
        },
        execution_review={
            "reviewed_arm_run_count": 1499,
            "candidate_tensor_modified": False,
        },
        qualification=qualification,
    )["failure_denominator_complete"] is False


def test_evaluation_artifact_does_not_reopen_or_modify_fresh_protocol() -> None:
    producer_source = inspect.getsource(producer.evaluate)
    reviewer_source = inspect.getsource(reviewer.review)
    for source in (producer_source, reviewer_source):
        assert "freeze_fresh_b2_opening_release" not in source
        assert "_consume_opening_nonce" not in source
        assert "build_native_arm_runner" not in source
        assert "run_diffusion_planner" not in source
    assert "evaluate_fresh_b2_three_arm(" in producer_source
    assert "evaluate_fresh_b2_three_arm(" in reviewer_source


def test_evaluation_reviewer_rebuilds_claims_instead_of_trusting_summary() -> None:
    source = inspect.getsource(reviewer.review)
    rebuild = source.index("rebuilt = evaluate_fresh_b2_three_arm(")
    compare = source.index("if not _strict_equal(recorded, rebuilt)")
    claim_compare = source.index("evaluation report claim summary drifted")
    assert rebuild < compare < claim_compare
