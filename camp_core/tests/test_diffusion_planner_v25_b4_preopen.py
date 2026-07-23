from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_b4_preopen import (
    build_b4_holdout_identity,
    build_b4_protocol_amendment,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)


def test_b4_identity_and_protocol_amendment_are_outcome_blind_and_stable() -> None:
    suite = build_signal_complete_suite("fresh_b4")
    plan = build_signal_complete_execution_plan("fresh_b4")
    identity = build_b4_holdout_identity(suite=suite, plan=plan)
    amendment = build_b4_protocol_amendment(suite=suite, plan=plan)
    assert identity == build_b4_holdout_identity(suite=suite, plan=plan)
    assert identity["split"] == "fresh_b4"
    assert identity["paired_unit_count"] == 500
    assert identity["arm_run_count"] == 1500
    assert identity["tick_capacity"] == 96_000
    assert amendment["scientific_model_atom_margin_claim_rules_changed"] is False
    assert amendment["b2_or_b3_raw_values_used"] is False
    assert amendment["outcome_fields_consumed"] == []


def test_b4_identity_rejects_prior_split_materialization() -> None:
    suite = build_signal_complete_suite("fresh_b4")
    plan = build_signal_complete_execution_plan("fresh_b4")
    changed = copy.deepcopy(plan)
    changed["split"] = "fresh_b3"
    with pytest.raises(ValueError):
        build_b4_holdout_identity(suite=suite, plan=changed)
