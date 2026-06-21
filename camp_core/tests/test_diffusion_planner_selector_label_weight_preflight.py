from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_selector_label_weight_preflight import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    DEFAULT_REQUIRED_BUCKETS,
    READY_STATUS,
    build_report,
    render_markdown,
)


def _selector_gap() -> dict:
    return {
        "final_decision": {
            "status": "current_selector_gap_open",
            "passed": False,
            "authorized_next_work": "selector_label_weight_design_preflight",
            "oracle_passed": True,
            "evaluated_same_as_logged": True,
            "evaluated_passed_proof_protocol_v2": False,
            "evaluated_gap_closed": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _oracle() -> dict:
    return {
        "logs": {"total": 108, "formal_seed_logs": 0},
        "records": {"total": 21600},
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": True},
        "by_bucket": [{"bucket": bucket} for bucket in DEFAULT_REQUIRED_BUCKETS],
    }


def _selector_eval() -> dict:
    return {
        "logs": {"total": 108, "formal_seed_logs": 0},
        "coverage_gaps": {"missing_required_buckets": []},
        "selector_comparison": {
            "changed_record_rate": 0.0,
            "evaluated_minus_logged_cost_mean": 0.0,
        },
    }


def test_selector_label_weight_preflight_ready() -> None:
    report = build_report(
        selector_oracle_gap=_selector_gap(),
        safety_cost_oracle=_oracle(),
        selector_eval=_selector_eval(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["offline_convex_selector_training_plan_authorized"] is True
    assert decision["training_execution_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["label_contract"]["online_runtime_feature_allowed"] is False
    assert report["optimization_contract"]["score_convention"].startswith(
        "CAMP selects lower scores"
    )

    markdown = render_markdown(report)
    assert "Selector Label/Weight Preflight" in markdown
    assert "simplex_linear_softmax_cross_entropy" in markdown
    assert "finite-candidate selector is not a DP-side classical Benders" in markdown


def test_selector_label_weight_preflight_blocks_wrong_gap_status() -> None:
    gap = _selector_gap()
    gap["final_decision"]["status"] = "selector_oracle_gap_closed_candidate_branch"

    report = build_report(
        selector_oracle_gap=gap,
        safety_cost_oracle=_oracle(),
        selector_eval=_selector_eval(),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["training_execution_authorized"] is False
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "selector_gap_status_current" in failed


def test_selector_label_weight_preflight_blocks_incomplete_oracle() -> None:
    oracle = _oracle()
    oracle["opportunity_gate"]["passed"] = False
    oracle["logs"]["formal_seed_logs"] = 1
    oracle["coverage_gaps"]["missing_required_buckets"] = ["traffic_light"]

    report = build_report(
        selector_oracle_gap=_selector_gap(),
        safety_cost_oracle=oracle,
        selector_eval=_selector_eval(),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "safety_cost_oracle_opportunity_gate_passed" in failed
    assert "safety_cost_oracle_no_formal_seed_logs" in failed
    assert "safety_cost_oracle_no_missing_required_buckets" in failed


def test_selector_label_weight_preflight_blocks_selector_eval_drift() -> None:
    selector_eval = _selector_eval()
    selector_eval["selector_comparison"]["changed_record_rate"] = 0.2

    report = build_report(
        selector_oracle_gap=_selector_gap(),
        safety_cost_oracle=_oracle(),
        selector_eval=selector_eval,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "selector_eval_current_matches_logged" in failed


def test_selector_label_weight_preflight_allows_missing_optional_selector_eval() -> None:
    report = build_report(
        selector_oracle_gap=_selector_gap(),
        safety_cost_oracle=_oracle(),
        selector_eval=None,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    optional = [
        check for check in report["source_checks"] if check["name"] == "selector_eval_optional"
    ]
    assert optional and optional[0]["passed"] is True
