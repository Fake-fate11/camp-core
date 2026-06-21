from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_selector_oracle_gap import (
    DEFAULT_REQUIRED_BUCKETS,
    build_report,
    render_markdown,
)


def _ci(high: float, mean: float | None = None) -> dict[str, float]:
    value = high - 0.1 if mean is None else mean
    return {"mean": value, "ci95_low": value - 0.1, "ci95_high": high}


def _entry(
    *,
    top1_high: float = -0.2,
    cvar_high: float = -0.1,
    oracle_high: float = -0.3,
    gap_high: float = 0.4,
) -> dict[str, object]:
    return {
        "records": 10,
        "logs": 2,
        "record_rates": {
            "camp_beats_top1": 0.7,
            "camp_matches_hard_guarded_oracle": 0.5,
            "hard_guarded_oracle_beats_top1": 0.9,
        },
        "run_level_delta_ci": {
            "camp_minus_top1": _ci(top1_high),
            "hard_guarded_oracle_minus_top1": _ci(oracle_high),
            "camp_minus_hard_guarded_oracle": _ci(gap_high),
        },
        "run_level_cvar90_delta": {
            "camp_minus_top1": _ci(cvar_high),
        },
    }


def _oracle() -> dict[str, object]:
    return {
        "logs": {"total": 8, "formal_seed_logs": 0},
        "records": {"total": 80},
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": True},
        "overall": _entry(oracle_high=-0.4),
        "by_bucket": [
            {"bucket": bucket, **_entry(oracle_high=-0.2)}
            for bucket in ("overall", *DEFAULT_REQUIRED_BUCKETS)
        ],
    }


def _selector_eval(
    *,
    traffic_top1_high: float = 0.05,
    sharp_cvar_high: float = 0.1,
    gap_high: float = 0.5,
    changed_rate: float = 0.0,
) -> dict[str, object]:
    evaluated = [{"bucket": "overall", **_entry(top1_high=-0.2, gap_high=gap_high)}]
    logged = [{"bucket": "overall", **_entry(top1_high=-0.2, gap_high=gap_high)}]
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        top1_high = traffic_top1_high if bucket == "traffic_light" else -0.05
        cvar_high = sharp_cvar_high if bucket == "sharp_turn" else -0.02
        evaluated.append(
            {
                "bucket": bucket,
                **_entry(top1_high=top1_high, cvar_high=cvar_high, gap_high=gap_high),
            }
        )
        logged.append(
            {
                "bucket": bucket,
                **_entry(top1_high=top1_high, cvar_high=cvar_high, gap_high=gap_high),
            }
        )
    return {
        "analysis": {
            "selector_name": "unit_selector",
        },
        "logs": {"total": 8, "formal_seed_logs": 0},
        "records": {"total": 80},
        "coverage_gaps": {"missing_required_buckets": []},
        "evaluated_selector": {
            "overall": _entry(top1_high=-0.2, cvar_high=-0.1, gap_high=gap_high),
            "by_bucket": evaluated,
        },
        "logged_selector": {
            "overall": _entry(top1_high=-0.2, cvar_high=-0.1, gap_high=gap_high),
            "by_bucket": logged,
        },
        "selector_comparison": {
            "changed_record_rate": changed_rate,
            "evaluated_minus_logged_cost_mean": 0.0,
            "run_level_evaluated_minus_logged_cost_ci": {"ci95_high": 0.0},
        },
    }


def test_selector_oracle_gap_identifies_current_selector_gap_open() -> None:
    report = build_report(
        oracle_report=_oracle(),
        selector_eval_report=_selector_eval(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_selector_gap_open"
    assert decision["passed"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["evaluated_same_as_logged"] is True
    assert report["evaluated_selector"]["top1_bucket_failures"] == {
        "traffic_light": 0.05
    }
    assert report["evaluated_selector"]["cvar90_bucket_failures"] == {
        "sharp_turn": 0.1
    }
    assert "current_selector_fails_required_bucket_or_tail_gate" in decision[
        "reasons"
    ]

    markdown = render_markdown(report)
    assert "Selector Oracle Gap Summary" in markdown
    assert "not construct a DP-side classical Benders" in markdown


def test_selector_oracle_gap_reports_selector_beats_top1_but_gap_open() -> None:
    report = build_report(
        oracle_report=_oracle(),
        selector_eval_report=_selector_eval(
            traffic_top1_high=-0.05,
            sharp_cvar_high=-0.01,
            gap_high=0.2,
            changed_rate=0.4,
        ),
    )

    assert (
        report["final_decision"]["status"]
        == "selector_beats_top1_but_oracle_gap_open"
    )
    assert report["evaluated_selector"]["passed_proof_protocol_v2"] is True
    assert report["evaluated_selector"]["hard_guarded_oracle_gap_closed"] is False


def test_selector_oracle_gap_can_close_candidate_branch_gap() -> None:
    report = build_report(
        oracle_report=_oracle(),
        selector_eval_report=_selector_eval(
            traffic_top1_high=-0.05,
            sharp_cvar_high=-0.01,
            gap_high=-0.01,
            changed_rate=0.4,
        ),
    )

    decision = report["final_decision"]
    assert decision["status"] == "selector_oracle_gap_closed_candidate_branch"
    assert decision["passed"] is True
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False


def test_selector_oracle_gap_blocks_when_oracle_incomplete() -> None:
    oracle = _oracle()
    oracle["opportunity_gate"] = {"passed": False}
    report = build_report(
        oracle_report=oracle,
        selector_eval_report=_selector_eval(),
    )

    assert report["final_decision"]["status"] == "selector_oracle_gap_blocked_by_oracle"
    assert report["oracle"]["passed"] is False
