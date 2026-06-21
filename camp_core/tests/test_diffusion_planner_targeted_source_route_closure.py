from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_targeted_source_route_closure import (
    BLOCKED_STATUS,
    CLOSED_STATUS,
    build_report,
    main,
    render_markdown,
)


def _support_reject(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "new_no_leak_targeted_support_source_not_available",
        "passed": True,
        "support_source_ready": False,
        "current_camp_dp_selector_route_rejected": True,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(overrides)
    return {"final_decision": decision}


def _score_inventory() -> dict[str, object]:
    families = [
        "non_turn_interaction_family",
        "observable_interaction_family",
        "progress_lane_hard_context",
        "relaxed_strict_atom_family",
        "revised_context_atom_family",
        "turn_logit_atom_family",
    ]
    return {
        "score_families": [
            {"name": family, "status": "rejected_or_limited"}
            for family in families
        ],
        "final_decision": {
            "status": "no_leak_score_family_inventory_requires_new_design",
            "unclosed_support_families": [],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _tensor_visibility(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "current_tick_tensor_visibility_no_new_candidate_source",
        "primary_gap": "visible_candidate_tensor_sources_already_closed",
        "candidate_source_names": [],
        "closed_visible_candidate_source_names": ["turn_indicator_logits"],
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "source_gate": {"stale": False},
        "tensor_sources": [
            {
                "name": "turn_indicator_logits",
                "visibility_status": "visible_but_score_family_closed",
                "closed_by_score_inventory": True,
            },
            {
                "name": "dp_native_log_probability_or_score",
                "visibility_status": "not_visible",
                "closed_by_score_inventory": False,
            },
        ],
        "final_decision": decision,
    }


def _proof_redesign() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "proof_protocol_redesign_required",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _report(**kwargs: object) -> dict[str, object]:
    inputs = {
        "support_reject": _support_reject(),
        "score_family_inventory": _score_inventory(),
        "tensor_visibility": _tensor_visibility(),
        "proof_protocol_redesign": _proof_redesign(),
        "label": "unit",
    }
    inputs.update(kwargs)
    return build_report(**inputs)


def test_targeted_source_route_closure_passes_when_sources_are_closed() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == CLOSED_STATUS
    assert decision["passed"] is True
    assert decision["source_discovery_closed"] is True
    assert decision["authorized_next_work"] == (
        "proof_protocol_v2_or_scenario_objective_redesign_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert "turn_logit_atom_family" in report["closed_score_families"]
    assert report["tensor_visibility_summary"]["closed_visible_candidate_source_names"] == [
        "turn_indicator_logits"
    ]


def test_targeted_source_route_closure_blocks_visible_new_candidate_source() -> None:
    tensor = _tensor_visibility(
        status="current_tick_tensor_visibility_has_candidate_source",
        primary_gap="visible_runtime_admissible_candidate_tensor_source_found",
        candidate_source_names=["dp_native_log_probability_or_score"],
        closed_visible_candidate_source_names=[],
    )
    report = _report(tensor_visibility=tensor)

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["passed"] is False
    assert "tensor_visibility_status" in decision["failed_checks"]
    assert "tensor_visibility_no_candidate_sources" in decision["failed_checks"]


def test_targeted_source_route_closure_blocks_stale_tensor_gate() -> None:
    tensor = _tensor_visibility()
    tensor["source_gate"]["stale"] = True
    report = _report(tensor_visibility=tensor)

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "tensor_visibility_source_not_stale" in decision["failed_checks"]
    assert decision["formal_seeds_authorized"] is False


def test_targeted_source_route_closure_markdown_states_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Targeted Source Route Closure" in markdown
    assert "turn_indicator_logits" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "No DP-side classical Benders" in markdown


def test_targeted_source_route_closure_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    support = tmp_path / "support.json"
    score = tmp_path / "score.json"
    tensor = tmp_path / "tensor.json"
    proof = tmp_path / "proof.json"
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"
    support.write_text(json.dumps(_support_reject()), encoding="utf-8")
    score.write_text(json.dumps(_score_inventory()), encoding="utf-8")
    tensor.write_text(json.dumps(_tensor_visibility()), encoding="utf-8")
    proof.write_text(json.dumps(_proof_redesign()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--support_reject_json",
            str(support),
            "--score_family_inventory_json",
            str(score),
            "--tensor_visibility_json",
            str(tensor),
            "--proof_protocol_redesign_json",
            str(proof),
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
    assert payload["final_decision"]["status"] == CLOSED_STATUS
    assert "Targeted Source Route Closure" in output_md.read_text(encoding="utf-8")
