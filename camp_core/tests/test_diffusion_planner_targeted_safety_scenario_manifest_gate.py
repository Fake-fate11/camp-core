from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_targeted_safety_scenario_manifest_gate import (
    AUTHORIZED_NEXT_WORK,
    INCOMPLETE_STATUS,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    build_report,
    main,
    render_markdown,
)


TARGETS = [
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
]
GUARDS = ["overall", "normal"]
REQUIRED = [*GUARDS, *TARGETS]


def _objective(*, passed: bool = True) -> dict[str, object]:
    return {
        "analysis": {
            "name": "dp_camp_targeted_safety_intervention_proof_objective_v1"
        },
        "objective_contract": {
            "target_buckets": list(TARGETS),
            "guard_buckets": list(GUARDS),
            "required_buckets": list(REQUIRED),
            "primary_claim": {
                "rule": (
                    "hard_gates_pass_all_required_buckets and "
                    "ci95_high(TargetSafetyCost_CAMP_minus_DP_Top1) < 0"
                )
            },
            "guard_claims": {
                "normal_non_degradation": (
                    "ci95_high(SafetyCost_normal_CAMP_minus_DP_Top1) <= 0"
                ),
                "overall_non_degradation": (
                    "ci95_high(SafetyCost_overall_CAMP_minus_DP_Top1) <= 0"
                ),
            },
        },
        "final_decision": {
            "status": (
                "targeted_safety_intervention_proof_objective_predeclared"
                if passed
                else "targeted_safety_intervention_proof_objective_blocked_by_source_gate"
            ),
            "passed": passed,
            "authorized_next_work": (
                "targeted_safety_intervention_scenario_manifest_design_only"
                if passed
                else None
            ),
            "training_execution_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _matrix(
    *,
    missing: str | None = None,
    outcome_filter: bool = False,
    formal_seed: bool = False,
    variant: str = "static",
) -> dict[str, object]:
    bucket_counts = {bucket: 3 for bucket in REQUIRED}
    if missing is not None:
        bucket_counts.pop(missing)
    filters = [
        {
            "name": "sample_tl_on",
            "match": {
                "route_name": "sample_tl_turn",
                "traffic_lights": True,
            },
            "buckets": ["traffic_light", "red_light_turn"],
        },
        {
            "name": "npc_dense",
            "match": {"max_npcs": 8, "spawn_probability": 0.6},
            "buckets": ["npc_interaction", "dense_scene"],
        },
    ]
    if outcome_filter:
        filters.append(
            {
                "name": "bad_metric_filter",
                "match": {"near_miss_rate": 0.0},
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
            "seeds": [1, 11] if formal_seed else [1, 2, 3],
            "bucket_counts": bucket_counts,
        },
        "scenario_bucket_manifest": {
            "routes": {
                "sample_tl_turn": ["sharp_turn"],
                "lane_change": ["lane_change_or_merge"],
            },
            "filters": filters,
            "default_buckets": [],
        },
        "command": {
            "argv": [
                "python",
                "run_diffusion_planner_camp_benchmark_matrix.py",
                "--camp_collect_closed_loop_outcomes",
                "--variants",
                variant,
                "--skip_compare",
                "--scenario_bucket_manifest",
                "/out/scenario_buckets.json",
            ]
        },
        "blockers": [],
        "decision": "approved_nonformal_plan_only",
    }


def test_targeted_scenario_manifest_accepts_complete_explicit_matrix() -> None:
    report = build_report(
        targeted_objective=_objective(),
        matrix_plan=_matrix(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["recommended_first_action"] == (
        "targeted_candidate_branch_oracle_input_readiness_gate"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "all_target_buckets_have_predeclared_coverage" in decision["reasons"]
    assert report["matrix_source"]["target_missing_buckets"] == []
    assert report["matrix_source"]["guard_missing_buckets"] == []


def test_targeted_scenario_manifest_rejects_missing_target_bucket() -> None:
    report = build_report(
        targeted_objective=_objective(),
        matrix_plan=_matrix(missing="lane_change_or_merge"),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert report["matrix_source"]["target_missing_buckets"] == [
        "lane_change_or_merge"
    ]
    assert "matrix_plan_missing_target_buckets" in report["final_decision"]["reasons"]


def test_targeted_scenario_manifest_rejects_missing_normal_guard() -> None:
    report = build_report(
        targeted_objective=_objective(),
        matrix_plan=_matrix(missing="normal"),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert report["matrix_source"]["guard_missing_buckets"] == ["normal"]
    assert "matrix_plan_missing_guard_buckets" in report["final_decision"]["reasons"]


def test_targeted_scenario_manifest_rejects_outcome_filter() -> None:
    report = build_report(
        targeted_objective=_objective(),
        matrix_plan=_matrix(outcome_filter=True),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert report["matrix_source"]["filter_errors"][0]["outcome_fields"] == [
        "near_miss_rate"
    ]
    assert "manifest_filter_not_config_only" in report["final_decision"]["reasons"]


def test_targeted_scenario_manifest_rejects_formal_seed() -> None:
    report = build_report(
        targeted_objective=_objective(),
        matrix_plan=_matrix(formal_seed=True),
    )

    assert report["final_decision"]["status"] == INCOMPLETE_STATUS
    assert report["matrix_source"]["formal_seeds"] == [11]
    assert "matrix_plan_uses_formal_seeds" in report["final_decision"]["reasons"]


def test_targeted_scenario_manifest_blocks_if_objective_not_ready() -> None:
    report = build_report(
        targeted_objective=_objective(passed=False),
        matrix_plan=_matrix(),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["objective_source"]["passed"] is False


def test_targeted_scenario_manifest_markdown_states_boundary() -> None:
    report = build_report(targeted_objective=_objective(), matrix_plan=_matrix())
    markdown = render_markdown(report)

    assert "Targeted Safety Scenario Manifest Gate" in markdown
    assert "lane_change_or_merge" in markdown
    assert "does not run DP" in markdown
    assert "classical Benders" in markdown


def test_targeted_scenario_manifest_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    objective_path = tmp_path / "targeted_objective.json"
    matrix_path = tmp_path / "matrix_plan.json"
    output_json = tmp_path / "manifest_gate.json"
    output_md = tmp_path / "manifest_gate.md"
    objective_path.write_text(json.dumps(_objective()), encoding="utf-8")
    matrix_path.write_text(json.dumps(_matrix()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted_manifest_gate",
            "--targeted_objective_json",
            str(objective_path),
            "--matrix_plan_json",
            str(matrix_path),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Targeted Safety Scenario" in output_md.read_text(encoding="utf-8")
