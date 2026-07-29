from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import build_v25_atom_source_masks
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    validate_causal_signal_atom_input,
)
from camp_core.integrations.diffusion_planner_v26_nuplan import (
    build_v26_nuplan_unavailable_signal_authority,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "integrations" / "run_diffusion_planner_v26_nuplan_b8_corpus_materialization.py"
SPEC = importlib.util.spec_from_file_location("v26_nuplan_b8_corpus", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source() -> dict[str, object]:
    return {
        "record_id": "anchor-0",
        "official_split": "train",
        "log_token": "log-0",
        "scenario_token": "scenario-0",
        "scene_token": "scene-0",
        "state_token": "state-0",
        "mission_route_roadblock_chain_sha256": _sha("route"),
        "corridor_id": "corridor-0",
        "geometry_clone_group_sha256": _sha("geometry"),
        "city": "boston",
        "map_family": "us-ma-boston",
        "source_db_sha256": _sha("db"),
        "map_sha256": _sha("map"),
        "event_strata": ["scenario_tag:test"],
    }


def _anchor(anchor_id: str, city: str, partition: str) -> dict[str, str]:
    return {"anchor_id": anchor_id, "city": city, "partition": partition}


def _reporting_plan() -> dict[str, object]:
    return {
        "plan_sha256": _sha("plan"),
        "analysis_freeze": {"cluster_aware_ci": {"method": "frozen"}},
        "city_partition_denominator": [
            {"city": "boston", "partition": "val_iid", "log_cluster_count": 188},
            {"city": "pittsburgh", "partition": "val_iid", "log_cluster_count": 25},
        ],
    }


def test_unavailable_official_signal_is_opt_in_mask_not_false_no_signal() -> None:
    authority = build_v26_nuplan_unavailable_signal_authority(
        source_identity=_source(),
        route_lanes=np.zeros((25, 20, 33), dtype=np.float64),
        decision_timestamp_us=100_000,
        traffic_light_state_available=True,
    )
    causal = authority["causal_signal_atom_input"]
    with pytest.raises(ValueError, match="unavailable-signal"):
        validate_causal_signal_atom_input(causal)
    validated = validate_causal_signal_atom_input(causal, allow_unavailable=True)
    assert validated["source_state"] == "unavailable"
    with pytest.raises(ValueError, match="unavailable"):
        build_v25_atom_source_masks(
            route_speed_source_valid=np.ones(8, dtype=np.bool_),
            signal_source_state="unavailable",
            current_phase="none",
        )
    source, applicable = build_v25_atom_source_masks(
        route_speed_source_valid=np.ones(8, dtype=np.bool_),
        signal_source_state="unavailable",
        current_phase="none",
        allow_unavailable_signal_atoms=True,
    )
    assert not source[:, [10, 12]].any()
    assert not applicable[:, [10, 12]].any()
    assert applicable[:, :10].all()


def test_reporting_contract_freezes_coverage_balanced_log_cluster_rule() -> None:
    contract = MODULE.build_frozen_reporting_contract(_reporting_plan())
    assert contract["within_city_estimand"] == "frozen_coverage_balanced_corpus_performance"
    assert contract["post_hoc_prevalence_weights_permitted"] is False
    assert contract["between_city_iid_aggregation"]["weights"] == {
        "boston": 0.5,
        "pittsburgh": 0.5,
    }
    assert contract["independent_n"]["validation_log_cluster_counts"] == {
        "boston": 188,
        "pittsburgh": 25,
    }
    assert contract["independent_n"]["anchors_are_independent_n"] is False
    assert contract["independent_n"]["b8_rows_are_independent_n"] is False


def test_streaming_selection_excludes_held_out_city_and_keeps_partition_identity() -> None:
    plan = {
        "planned_anchors": [
            _anchor("b-train", "boston", "train_iid"),
            _anchor("p-train", "pittsburgh", "train_iid"),
            _anchor("b-val", "boston", "val_iid"),
            _anchor("p-val", "pittsburgh", "val_iid"),
            _anchor("s-test", "singapore", "test_ood"),
        ]
    }
    selected = MODULE.select_materialization_anchors(
        plan,
        expected_counts={
            ("boston", "train_iid"): 1,
            ("pittsburgh", "train_iid"): 1,
            ("boston", "val_iid"): 1,
            ("pittsburgh", "val_iid"): 1,
        },
    )
    assert [row["anchor_id"] for row in selected] == [
        "b-train",
        "b-val",
        "p-train",
        "p-val",
    ]
    assert all(row["city"] != "singapore" for row in selected)
