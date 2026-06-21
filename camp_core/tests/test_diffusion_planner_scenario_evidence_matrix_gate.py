from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_scenario_evidence_matrix_gate import (
    build_report,
    render_markdown,
)


REQUIRED_BUCKETS = [
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
]


def _protocol(*, passed: bool = True) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_proof_protocol_v2_predeclaration"},
        "protocol": {
            "required_scenario_buckets": REQUIRED_BUCKETS,
            "primary_score": {
                "claim_rule": (
                    "hard_gate_passed and "
                    "ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0"
                )
            },
        },
        "final_decision": {
            "status": (
                "proof_protocol_v2_predeclared"
                if passed
                else "proof_protocol_v2_predeclaration_blocked_by_source_gate"
            ),
            "passed": passed,
            "authorized_next_work": "scenario_manifest_and_evidence_matrix_design_only",
            "new_replay_authorized": False,
            "online_selector_authorized": False,
        },
    }


def _matrix_plan(
    *,
    missing_bucket: str | None = None,
    outcome_filter: bool = False,
    formal_seed: bool = False,
) -> dict[str, object]:
    bucket_counts = {bucket: 3 for bucket in REQUIRED_BUCKETS}
    if missing_bucket is not None:
        bucket_counts.pop(missing_bucket)
    seed_values = [1, 2, 3]
    if formal_seed:
        seed_values = [1, 11]
    filters = [
        {
            "name": "sample_tl_on",
            "match": {
                "route_name": "sample_tl",
                "traffic_lights": True,
            },
            "buckets": ["traffic_light", "red_light_turn"],
        }
    ]
    if outcome_filter:
        filters.append(
            {
                "name": "bad_outcome_filter",
                "match": {"red_light_violation_rate": 0.0},
                "buckets": ["normal"],
            }
        )
    return {
        "analysis": {
            "name": "dp_camp_diverse_nonformal_matrix_plan_v1",
            "explicit_labeling_only": True,
            "labels_are_not_inferred_from_metrics": True,
        },
        "summary": {
            "planned_run_count": 108,
            "route_count": 3,
            "seeds": seed_values,
            "bucket_counts": bucket_counts,
        },
        "scenario_bucket_manifest": {
            "routes": {"lane_change": ["lane_change_or_merge"]},
            "filters": filters,
            "default_buckets": [],
        },
        "command": {
            "argv": [
                "python",
                "run_diffusion_planner_camp_benchmark_matrix.py",
                "--camp_collect_closed_loop_outcomes",
                "--variants",
                "static",
                "--skip_compare",
                "--scenario_bucket_manifest",
                "/out/scenario_buckets.json",
            ]
        },
        "blockers": [],
        "decision": "approved_nonformal_plan_only",
    }


def test_scenario_evidence_matrix_gate_accepts_explicit_complete_plan() -> None:
    report = build_report(
        proof_protocol_v2=_protocol(),
        matrix_plan=_matrix_plan(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "scenario_evidence_matrix_predeclared"
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == (
        "candidate_branch_oracle_input_readiness_gate"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "all_required_buckets_have_predeclared_coverage" in decision["reasons"]
    assert report["matrix_source"]["planned_run_count"] == 108

    markdown = render_markdown(report)
    assert "Scenario Evidence Matrix Gate" in markdown
    assert "not construct a DP-side classical Benders" in markdown


def test_scenario_evidence_matrix_gate_rejects_missing_bucket() -> None:
    report = build_report(
        proof_protocol_v2=_protocol(),
        matrix_plan=_matrix_plan(missing_bucket="dense_scene"),
    )

    assert report["final_decision"]["status"] == "scenario_evidence_matrix_incomplete"
    assert report["matrix_source"]["missing_required_buckets"] == ["dense_scene"]
    assert "matrix_plan_missing_required_buckets" in report["final_decision"][
        "reasons"
    ]


def test_scenario_evidence_matrix_gate_rejects_outcome_filter() -> None:
    report = build_report(
        proof_protocol_v2=_protocol(),
        matrix_plan=_matrix_plan(outcome_filter=True),
    )

    assert report["final_decision"]["status"] == "scenario_evidence_matrix_incomplete"
    assert report["matrix_source"]["filter_errors"][0]["outcome_fields"] == [
        "red_light_violation_rate"
    ]
    assert "manifest_filter_not_config_only" in report["final_decision"]["reasons"]


def test_scenario_evidence_matrix_gate_rejects_protocol_not_ready() -> None:
    report = build_report(
        proof_protocol_v2=_protocol(passed=False),
        matrix_plan=_matrix_plan(),
    )

    assert (
        report["final_decision"]["status"]
        == "scenario_evidence_matrix_blocked_by_protocol"
    )
    assert report["protocol_source"]["passed"] is False


def test_scenario_evidence_matrix_gate_rejects_formal_seed() -> None:
    report = build_report(
        proof_protocol_v2=_protocol(),
        matrix_plan=_matrix_plan(formal_seed=True),
    )

    assert report["final_decision"]["status"] == "scenario_evidence_matrix_incomplete"
    assert report["matrix_source"]["formal_seeds"] == [11]
    assert "matrix_plan_uses_formal_seeds" in report["final_decision"]["reasons"]
