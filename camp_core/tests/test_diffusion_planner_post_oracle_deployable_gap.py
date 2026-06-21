from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_oracle_deployable_gap import (
    GAP_CLOSED_STATUS,
    GAP_OPEN_NEXT_WORK,
    GAP_OPEN_STATUS,
    build_report,
    main,
    render_markdown,
)


def _ci(mean: float, high: float) -> dict[str, float]:
    return {"mean": mean, "ci95_low": mean - 0.1, "ci95_high": high}


def _bucket(
    bucket: str,
    *,
    records: int = 10,
    camp_top1_high: float = -0.1,
    cvar_high: float = -0.05,
    oracle_top1_high: float = -0.2,
    camp_oracle_high: float = 0.5,
) -> dict[str, object]:
    return {
        "bucket": bucket,
        "records": records,
        "logs": 1,
        "record_rates": {
            "hard_guarded_oracle_available": 1.0,
            "hard_guarded_oracle_beats_top1": 0.9,
            "camp_matches_hard_guarded_oracle": 0.5,
        },
        "candidate_pool_coverage": {
            "fallback_all_infeasible_rate": 0.2,
            "hard_guarded_oracle_available_rate": 1.0,
        },
        "run_level_delta_ci": {
            "camp_minus_top1": _ci(-0.2, camp_top1_high),
            "hard_guarded_oracle_minus_top1": _ci(-0.5, oracle_top1_high),
            "camp_minus_hard_guarded_oracle": _ci(0.3, camp_oracle_high),
        },
        "run_level_cvar90_delta": {
            "camp_minus_top1": _ci(-0.1, cvar_high),
        },
        "fallback_all_infeasible_records": 2,
    }


def _oracle(*, opportunity: bool = True, gap_high: float = 0.5) -> dict[str, object]:
    buckets = [
        _bucket(name, camp_oracle_high=gap_high)
        for name in (
            "overall",
            "normal",
            "traffic_light",
            "red_light_turn",
            "sharp_turn",
            "npc_interaction",
            "dense_scene",
            "lane_change_or_merge",
        )
    ]
    return {
        "analysis": {"name": "dp_camp_candidate_branch_safety_cost_v1_oracle"},
        "logs": {"total": 8, "formal_seed_logs": 0},
        "records": {
            "total": 80,
            "base_feasible": 64,
            "fallback_all_infeasible": 16,
            "formal_seed_records": 0,
        },
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": opportunity},
        "overall": buckets[0],
        "by_bucket": buckets,
        "opportunity_diagnostics": {
            "failure_mode_counts": {
                "camp_not_hard_guarded_oracle_when_available": 40,
                "fallback_all_infeasible": 16,
            },
            "failure_mode_rates": {
                "camp_not_hard_guarded_oracle_when_available": 0.5,
                "fallback_all_infeasible": 0.2,
            },
        },
    }


def _source_inventory() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "post_source_visibility_runtime_inventory_no_new_source_paused",
            "passed": True,
            "authorized_next_work": (
                "keep_selector_route_paused_or_scenario_objective_redesign_only"
            ),
            "new_runtime_source_candidates": [],
        }
    }


def test_post_oracle_gap_diagnoses_current_selector_gap_open() -> None:
    report = build_report(
        oracle=_oracle(),
        source_inventory=_source_inventory(),
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == GAP_OPEN_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == GAP_OPEN_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["current_selector_gap_closed"] is False
    assert "fallback_all_infeasible_records_present" in decision["reasons"]
    assert "camp_misses_available_hard_guarded_oracle_records" in decision["reasons"]
    assert "no_new_runtime_source_available_from_latest_inventory" in decision[
        "reasons"
    ]
    assert report["gap_summary"]["hard_guarded_oracle_gap_bucket_failures"]


def test_post_oracle_gap_blocks_if_oracle_gate_fails() -> None:
    report = build_report(oracle=_oracle(opportunity=False))

    decision = report["final_decision"]
    assert decision["status"] == "post_oracle_deployable_gap_blocked_by_oracle"
    assert decision["passed"] is False
    assert decision["authorized_next_work"] is None


def test_post_oracle_gap_blocks_if_source_inventory_reopens_source() -> None:
    inventory = _source_inventory()
    inventory["final_decision"]["new_runtime_source_candidates"] = ["new_source"]
    report = build_report(oracle=_oracle(), source_inventory=inventory)

    assert report["final_decision"]["status"] == (
        "post_oracle_deployable_gap_blocked_by_source_inventory"
    )
    assert report["source_inventory_summary"]["passed"] is False


def test_post_oracle_gap_can_report_candidate_branch_gap_closed() -> None:
    report = build_report(
        oracle=_oracle(gap_high=-0.01),
        source_inventory=_source_inventory(),
    )

    decision = report["final_decision"]
    assert decision["status"] == GAP_CLOSED_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == "deployability_latency_preflight_design_only"
    assert decision["closed_loop_smoke_authorized"] is False


def test_post_oracle_gap_markdown_states_math_boundary() -> None:
    report = build_report(oracle=_oracle(), source_inventory=_source_inventory())
    markdown = render_markdown(report)

    assert "Post-Oracle Deployability Gap" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_post_oracle_gap_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle_path = tmp_path / "oracle.json"
    inventory_path = tmp_path / "inventory.json"
    output_json = tmp_path / "gap.json"
    output_md = tmp_path / "gap.md"
    oracle_path.write_text(json.dumps(_oracle()), encoding="utf-8")
    inventory_path.write_text(json.dumps(_source_inventory()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "post_oracle_gap",
            "--oracle_json",
            str(oracle_path),
            "--source_inventory_json",
            str(inventory_path),
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
    assert payload["final_decision"]["status"] == GAP_OPEN_STATUS
    assert "Post-Oracle Deployability Gap" in output_md.read_text(encoding="utf-8")
