from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.search_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_sources import (
    AUTHORIZED_NEXT_WORK_NO_SOURCE,
    AUTHORIZED_NEXT_WORK_WITH_SOURCE,
    NO_SOURCE_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


RUN_IDS = (
    "sample_tl59_seed1_npc0_tlon",
    "sample_tl59_seed2_npc4_tlon",
    "sample_tl59_seed3_npc4_tloff",
    "sample_normal2_seed1_npc0_tloff",
    "nishi_release_seed2_npc4_tlon",
    "nishi_lanechange_seed4_npc4_tloff",
)


def _availability_plan(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "outcome_label_availability_plan_ready"
        ),
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "outcome_label_existing_source_search_only"
        ),
        "outcome_label_availability_plan_ready": True,
        "outcome_label_existing_source_search_authorized": True,
        "outcome_label_generation_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
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
        "outcome_label_availability_plan": {
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "existing_source_search_authorized": True,
            "outcome_label_generation_authorized": False,
            "route_seed_matrix": [
                {"run_id": run_id, "seed": seed}
                for run_id, seed in zip(RUN_IDS, (1, 2, 3, 1, 2, 4))
            ],
        },
    }


def _outcome(index: int) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": 10.0,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.5,
    }


def _write_logs(
    root: Path,
    *,
    include_outcomes: bool,
    run_ids: tuple[str, ...] = RUN_IDS,
) -> None:
    for run_id in run_ids:
        run_root = root / run_id
        run_root.mkdir(parents=True)
        rows = []
        for _ in range(10):
            row: dict[str, object] = {
                "num_candidates": 8,
                "selected_index": 0,
            }
            if include_outcomes:
                row["candidate_closed_loop_outcomes"] = [
                    _outcome(index) for index in range(8)
                ]
            rows.append(row)
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_existing_source_search_no_compatible_source_is_plan_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=False)

    report = build_report(
        availability_plan=_availability_plan(),
        search_roots=(root,),
        label="unit_no_source",
    )
    decision = report["final_decision"]

    assert decision["status"] == NO_SOURCE_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK_NO_SOURCE
    assert decision["compatible_source_found"] is False
    assert decision["guarded_outcome_label_pass_consideration_plan_authorized"] is True
    assert decision["outcome_label_generation_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert report["search_summary"]["relevant_log_count"] == 6
    assert report["search_summary"]["complete_outcome_log_count"] == 0


def test_existing_source_search_finds_complete_compatible_source(
    tmp_path: Path,
) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=True)

    report = build_report(
        availability_plan=_availability_plan(),
        search_roots=(root,),
        label="unit_source_found",
    )
    decision = report["final_decision"]
    source = report["compatible_source_sets"][0]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK_WITH_SOURCE
    assert decision["compatible_source_found"] is True
    assert decision["compatible_source_review_authorized"] is True
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert source["logs"] == 6
    assert source["records"] == 60
    assert source["run_ids"] == sorted(RUN_IDS)


def test_existing_source_search_rejects_unready_source_plan(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=True)

    report = build_report(
        availability_plan=_availability_plan(passed=False),
        search_roots=(root,),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_passed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_existing_source_search_rejects_formal_seed_log_in_search_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=False)
    _write_logs(root, include_outcomes=True, run_ids=("sample_tl59_seed11_npc0_tlon",))

    report = build_report(
        availability_plan=_availability_plan(),
        search_roots=(root,),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "no_formal_seed_logs_in_search" in report["final_decision"]["failed_checks"]


def test_existing_source_search_rejects_missing_search_root(tmp_path: Path) -> None:
    report = build_report(
        availability_plan=_availability_plan(),
        search_roots=(tmp_path / "missing",),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "search_roots_exist" in report["final_decision"]["failed_checks"]


def test_existing_source_search_markdown_states_boundaries(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=False)

    markdown = render_markdown(
        build_report(availability_plan=_availability_plan(), search_roots=(root,))
    )

    assert "Outcome-Label Existing Source Search" in markdown
    assert "Outcome-label generation authorized: `False`" in markdown
    assert "Replay authorized: `False`" in markdown
    assert "classical Benders" in markdown
    assert "guarded outcome-label pass consideration plan" in markdown


def test_existing_source_search_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "existing"
    _write_logs(root, include_outcomes=True)
    source_json = tmp_path / "availability_plan.json"
    output_json = tmp_path / "source_search.json"
    output_md = tmp_path / "source_search.md"
    source_json.write_text(json.dumps(_availability_plan()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-outcome-label-source-search",
            "--availability_plan_json",
            str(source_json),
            "--search_root",
            str(root),
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
    assert "Outcome-Label Existing Source Search" in output_md.read_text(
        encoding="utf-8"
    )
