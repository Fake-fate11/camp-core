from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (
    ARMS,
    AUTHORITY_SHA256,
    CLUSTER_COUNT,
    EXACT_DIRS,
    PLANNED_MODEL_CALLS,
    PLANNED_TICKS,
    TICKS_PER_ARM,
    build_scene_adapter,
    build_signal_authority,
    contract,
    latent_receipt,
    latent_tensor,
    reconstruct_controlled_case,
    validate_contract,
)
from camp_core.integrations.diffusion_planner_v25_project_authored_multiroute_source import (
    build_source_record,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_review import (
    review_contract_semantics,
)


ROOT = Path(__file__).resolve().parents[2]


def test_contract_has_exact_full_denominator_and_no_claim() -> None:
    value = validate_contract(contract())
    review_contract_semantics(value)
    assert AUTHORITY_SHA256 == (
        "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
    )
    assert CLUSTER_COUNT == 100
    assert len(ARMS) == 3
    assert TICKS_PER_ARM == 64
    assert PLANNED_TICKS == 19_200
    assert PLANNED_MODEL_CALLS == 19_200
    assert value["capture"]["scalar_leaf_count"] == 161
    assert value["capture"]["weighted_total"] is False
    assert value["statistics"]["claim_authorized"] is False
    assert len(set(EXACT_DIRS.values())) == len(EXACT_DIRS)


def test_latent_is_arm_independent_unique_and_tick_specific() -> None:
    clone = "12" * 32
    first = latent_tensor(clone, 0)
    again = latent_tensor(clone, 0)
    later = latent_tensor(clone, 1)
    assert first.shape == (8, 321, 81, 4)
    assert first.dtype == np.dtype("<f4")
    assert np.array_equal(first, again)
    assert not np.array_equal(first, later)
    assert np.array_equal(first[0], np.zeros_like(first[0]))
    assert len({row.tobytes() for row in first}) == 8
    receipt = latent_receipt(clone, 0)
    assert receipt["unique_row_sha256_cardinality"] == 8
    assert receipt["tensor_sha256"] == latent_receipt(clone, 0)["tensor_sha256"]


def test_runtime_source_rebuilds_mapped_and_absent_signal_authorities() -> None:
    mapped = build_source_record(0)["record"]
    mapped_case = reconstruct_controlled_case(mapped)
    mapped_chain, mapped_absent = build_signal_authority(mapped, mapped_case)
    assert mapped_absent is None
    assert mapped_chain is not None
    assert mapped_chain["phase_authority_mode"] == "controlled_same_tick_override"
    assert mapped_chain["formal_phase"] == "green"
    assert mapped_chain["phase_remaining_available"] is False
    assert build_scene_adapter(mapped).mapped_signal_authority is not None

    no_signal = build_source_record(2)["record"]
    absent_case = reconstruct_controlled_case(no_signal)
    absent_mapped, absent_chain = build_signal_authority(no_signal, absent_case)
    assert absent_mapped is None
    assert absent_chain is not None
    assert absent_chain["traffic_light_regulatory_element_ids"] == []
    assert build_scene_adapter(no_signal).no_signal_authority is not None


def test_contract_rejects_denominator_and_sequential_mutation() -> None:
    value = contract()
    value["denominator"]["planned_tick_slots"] = 19199
    with pytest.raises(ValueError):
        validate_contract(value)
    value = contract()
    value["generator"]["sequential_calls"] = 1
    with pytest.raises(ValueError):
        validate_contract(value)


def test_fair_production_hook_applies_scene_before_tensor_conversion() -> None:
    source = (
        ROOT
        / "scripts"
        / "integrations"
        / "validate_diffusion_planner_v25_fair_nonholdout.py"
    ).read_text(encoding="utf-8")
    adapter = source.index("receipt[\"controlled_scene\"] = dict(self.scene_adapter")
    sync = source.index("self.scene_adapter.sync_model_input_map_cache")
    safety = source.index("_capture_pre_safety(", adapter)
    tensor = source.index("self.tensor_converter.to_model_tensors", adapter)
    assert adapter < sync < safety < tensor
    assert "certified_signal_atom_input=causal_signal_atom_input" in source
    assert "scene_adapter=scene_adapter" in source


def test_bare_interpreter_is_absent_from_new_versioned_sources() -> None:
    paths = [
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_industrial_multiroute_v2.py",
        ROOT
        / "scripts"
        / "integrations"
        / "validate_diffusion_planner_v25_fair_nonholdout.py",
        ROOT
        / "scripts"
        / "integrations"
        / "freeze_diffusion_planner_v25_industrial_multiroute_v2.py",
        ROOT
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_v25_industrial_multiroute_v2.py",
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_industrial_multiroute_v2.py",
        ROOT
        / "scripts"
        / "integrations"
        / "evaluate_diffusion_planner_v25_industrial_multiroute_v2.py",
        ROOT
        / "scripts"
        / "integrations"
        / "finalize_diffusion_planner_v25_industrial_multiroute_v2.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert re.search(
            r"(?:^|[\s;&|])python3?(?:\s|$)", source, flags=re.MULTILINE
        ) is None


def test_evaluation_reviewer_uses_literal_metrics_not_evaluator_oracle() -> None:
    source = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_industrial_multiroute_v2.py"
    ).read_text(encoding="utf-8")
    assert (
        "run_diffusion_planner_v25_industrial_bounded_closed_loop import"
        not in source
    )
    assert (
        "evaluate_diffusion_planner_v25_industrial_multiroute_v2 import"
        not in source
    )
    for token in (
        "_literal_collision_proximity",
        "_literal_road",
        "_literal_red",
        "_literal_speed",
        "_literal_route",
        "_literal_goal",
        "_literal_body",
        "_literal_lookup_leaf",
        "_literal_paired_summary",
    ):
        assert token in source


def test_final_docs_role_is_unique_and_not_a_scientific_gate() -> None:
    assert EXACT_DIRS["final_docs"].endswith("_final_docs")
    source = (
        ROOT
        / "scripts"
        / "integrations"
        / "finalize_diffusion_planner_v25_industrial_multiroute_v2.py"
    ).read_text(encoding="utf-8")
    assert '"claim_authorized": False' in source
    assert '"weighted_total_present": False' in source
    assert "legacy_safetycost_computed" in source


def test_preflight_uses_pinned_route_constructor_field_names() -> None:
    source = (
        ROOT
        / "scripts"
        / "integrations"
        / "freeze_diffusion_planner_v25_industrial_multiroute_v2.py"
    ).read_text(encoding="utf-8")
    assert "waypoint_poses=" in source
    assert "waypoint_lanelet_ids=" in source
    assert "waypoints=" not in source
