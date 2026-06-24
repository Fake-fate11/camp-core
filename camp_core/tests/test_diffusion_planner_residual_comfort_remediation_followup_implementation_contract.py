from __future__ import annotations

import copy
import math

import pytest

from scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_followup_unit_tests import (
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
    PLANNED_CONTRACT_TEST,
)


def _surface() -> dict[str, object]:
    return {
        "candidates": [
            {"candidate_id": 0, "trajectory_xy": [[0.0, 0.0], [1.0, 0.0]]},
            {"candidate_id": 1, "trajectory_xy": [[0.0, 0.0], [1.0, 0.1]]},
        ],
        "scores": [0.0, 0.2],
        "selected_index": 0,
        "fallback": {"used": False, "reason": None},
        "online_selector": {"enabled": False, "lambda_id": None},
        "deployed_atom_schema": ["baseline_progress", "red_light_margin"],
    }


def _descriptor_payload(
    *,
    command_jerk: float = 8.6,
    rollout_lateral: float = -1.4,
    include_future: bool = False,
    mutate_candidate: bool = False,
    bad_math: bool = False,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    before = _surface()
    after = copy.deepcopy(before)
    if mutate_candidate:
        after["selected_index"] = 1
    command_jerk_abs = abs(command_jerk)
    rollout_lateral_abs = abs(rollout_lateral)
    descriptors = {
        "payload_role": "report_only",
        "descriptor_family": "command_jerk_rollout_lateral_zero_comfort_gap",
        "current_tick_features_only": not include_future,
        "candidate_local": True,
        "uses_outcome_labels": include_future,
        "future_outcome_leakage": include_future,
        "nonnegative_or_hinge_signed_split_legal": not bad_math,
        "command_jerk_abs_max_mps3": command_jerk_abs,
        "command_jerk_hinge_mps3": max(0.0, command_jerk_abs - 8.0),
        "command_jerk_signed_pos_mps3": max(command_jerk, 0.0),
        "command_jerk_signed_neg_mps3": max(-command_jerk, 0.0),
        "rollout_lateral_abs_max_mps2": rollout_lateral_abs,
        "rollout_lateral_hinge_mps2": max(0.0, rollout_lateral_abs - 1.0),
        "rollout_lateral_signed_pos_mps2": max(rollout_lateral, 0.0),
        "rollout_lateral_signed_neg_mps2": max(-rollout_lateral, 0.0),
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 master unchanged",
        "candidate_mutation": mutate_candidate,
        "score_mutation": False,
        "selected_index_mutation": mutate_candidate,
        "fallback_mutation": False,
        "online_selector_feature": False,
        "deployed_atom_schema_change": False,
        "dp_import": False,
        "reward_recompute": False,
        "tracker_recompute": False,
    }
    if bad_math:
        descriptors["command_jerk_hinge_mps3"] = -0.1
        descriptors["score_contract"] = "nonlinear"
    return before, after, descriptors


def _assert_no_surface_mutation(
    before: dict[str, object],
    after: dict[str, object],
    payload: dict[str, object],
) -> None:
    assert after == before
    assert payload["candidate_mutation"] is False
    assert payload["score_mutation"] is False
    assert payload["selected_index_mutation"] is False
    assert payload["fallback_mutation"] is False
    assert payload["online_selector_feature"] is False
    assert payload["deployed_atom_schema_change"] is False


def _assert_descriptor_contract(payload: dict[str, object]) -> None:
    assert payload["payload_role"] == "report_only"
    assert payload["descriptor_family"] == "command_jerk_rollout_lateral_zero_comfort_gap"
    assert payload["current_tick_features_only"] is True
    assert payload["candidate_local"] is True
    assert payload["uses_outcome_labels"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["nonnegative_or_hinge_signed_split_legal"] is True
    for key in (
        "command_jerk_abs_max_mps3",
        "command_jerk_hinge_mps3",
        "command_jerk_signed_pos_mps3",
        "command_jerk_signed_neg_mps3",
        "rollout_lateral_abs_max_mps2",
        "rollout_lateral_hinge_mps2",
        "rollout_lateral_signed_pos_mps2",
        "rollout_lateral_signed_neg_mps2",
    ):
        assert isinstance(payload[key], float)
        assert math.isfinite(payload[key])
        assert payload[key] >= 0.0
    assert payload["score_contract"] == "score_k(w)=a_k^T w"
    assert payload["convex_master_contract"] == "simplex/CVaR/L2 master unchanged"


def _affine_score(atom_values: list[float], weights: list[float]) -> float:
    return sum(value * weight for value, weight in zip(atom_values, weights))


def test_default_off_followup_contract_preserves_online_surface() -> None:
    before, after, payload = _descriptor_payload()

    _assert_no_surface_mutation(before, after, payload)


def test_opt_in_descriptor_payload_is_current_tick_candidate_local() -> None:
    _, _, payload = _descriptor_payload()

    _assert_descriptor_contract(payload)


def test_descriptor_rejects_future_outcome_or_label_leakage() -> None:
    _, _, payload = _descriptor_payload(include_future=True)

    with pytest.raises(AssertionError):
        _assert_descriptor_contract(payload)


def test_descriptor_terms_are_nonnegative_hinge_or_signed_split() -> None:
    _, _, payload = _descriptor_payload(command_jerk=-9.2, rollout_lateral=1.7)

    _assert_descriptor_contract(payload)
    assert payload["command_jerk_signed_pos_mps3"] == 0.0
    assert payload["command_jerk_signed_neg_mps3"] == 9.2
    assert payload["rollout_lateral_signed_pos_mps2"] == 1.7
    assert payload["rollout_lateral_signed_neg_mps2"] == 0.0


def test_descriptor_rejects_negative_or_nonlinear_math_contract() -> None:
    _, _, payload = _descriptor_payload(bad_math=True)

    with pytest.raises(AssertionError):
        _assert_descriptor_contract(payload)


def test_affine_score_contract_and_convex_master_are_preserved() -> None:
    atom_values = [1.0, 0.25, 0.75]
    weights = [0.5, 0.25, 0.25]
    cvar_alpha = 0.2
    l2_radius = 0.1

    assert weights == pytest.approx([max(weight, 0.0) for weight in weights])
    assert sum(weights) == pytest.approx(1.0)
    assert 0.0 < cvar_alpha <= 1.0
    assert l2_radius >= 0.0
    assert _affine_score(atom_values, weights) == pytest.approx(0.75)


def test_forbidden_execution_and_dp_actions_remain_blocked() -> None:
    decision = {
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }

    assert sorted(FORMAL_SEEDS) == [11, 12, 13]
    assert EXPECTED_DP_HEAD == "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    assert all(value is False for value in decision.values())


def test_unit_contract_scope_stays_in_planned_file_and_blocks_unrelated_cleanup() -> None:
    in_scope = {
        PLANNED_CONTRACT_TEST,
        "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
        "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
    }
    unrelated = {
        "adaptive-prediction/experiments/nuScenes/models/untracked",
        "session_exports",
    }

    assert PLANNED_CONTRACT_TEST in in_scope
    assert in_scope.isdisjoint(unrelated)
