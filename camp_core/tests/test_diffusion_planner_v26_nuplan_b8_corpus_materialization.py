from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import diffusion_planner_causal_atoms as causal_atoms
from camp_core.integrations import nuplan_causal_adapter
from camp_core.integrations.diffusion_planner_causal_atoms import build_v25_atom_source_masks
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    validate_causal_signal_atom_input,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    RAW_FEATURE_NAMES,
    V25ContextRecord,
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


def _unavailable_signal_materialization_fixture() -> tuple[
    np.ndarray, dict[str, np.ndarray], np.ndarray, np.ndarray
]:
    causal_input = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    candidates[:, :, 2] = 1.0
    for index in range(8):
        candidates[index, :, 0] = np.linspace(0.25, 35.0 + index * 0.1, 80)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(0.0, 19.5, 20)
    route[1, :, 0] = np.linspace(20.0, 39.5, 20)
    route[:2, :, 2] = 1.0
    route[:2, :, 5] = 2.0
    route[:2, :, 7] = -2.0
    causal_input["route_lanes"] = route
    causal_input["route_lanes_speed_limit"][:2, 0] = 12.0
    causal_input["route_lanes_has_speed_limit"][:2, 0] = True
    causal_input["ego_shape"] = np.array([2.925, 4.5, 1.9], dtype=np.float32)
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float64)
    neighbor_valid = np.zeros(32, dtype=bool)
    return candidates, causal_input, neighbors, neighbor_valid


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


def test_v26_unavailable_signal_materializes_with_exact_mask_and_no_pool_mutation() -> None:
    candidates, causal_input, neighbors, neighbor_valid = _unavailable_signal_materialization_fixture()
    authority = build_v26_nuplan_unavailable_signal_authority(
        source_identity=_source(),
        route_lanes=np.asarray(causal_input["route_lanes"], dtype=np.float64),
        decision_timestamp_us=100_000,
        traffic_light_state_available=False,
    )
    before = candidates.tobytes()
    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=neighbor_valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.zeros(8, dtype=np.float64),
        causal_signal_atom_input=authority["causal_signal_atom_input"],
        dt=0.1,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
        eligibility_policy=causal_atoms.V22_SOURCE_VALID_ELIGIBILITY,
        allow_inapplicable_speed_atoms=True,
        allow_unavailable_signal_atoms=True,
    )
    assert candidates.tobytes() == before
    assert result["canonical_eligible"] is True
    assert result["masked_unavailable_atom_names"] == (
        "planned_red_light_cost",
        "red_stopping_margin_cost",
    )
    assert not np.asarray(result["atom_source_valid_mask"])[:, [10, 12]].any()
    assert not np.asarray(result["atom_applicable_mask"])[:, [10, 12]].any()
    assert np.asarray(result["atom_matrix"]).shape == (8, 14)


def test_unavailable_signal_columns_must_be_legal_zero() -> None:
    availability = {name: True for name in causal_atoms.DP_CAMP_ATOM_NAMES_V10}
    availability["planned_red_light_cost"] = False
    availability["red_stopping_margin_cost"] = False
    matrix = np.zeros((8, 14), dtype=np.float64)
    matrix[:, 10] = 1.0
    with pytest.raises(ValueError, match="unavailable atom matrix columns must be legal zero"):
        causal_atoms.validate_canonical_atom_matrix(
            "dp_camp_v10_14d",
            availability,
            matrix,
            allowed_unavailable_atom_names=(
                "planned_red_light_cost",
                "red_stopping_margin_cost",
            ),
        )


def test_signal_and_speed_mask_semantics_are_exact() -> None:
    speeds = np.array([True] * 7 + [False], dtype=np.bool_)
    mapped_source, mapped_applicable = build_v25_atom_source_masks(
        route_speed_source_valid=speeds,
        signal_source_state="available",
        current_phase="red",
        allow_inapplicable_speed_atoms=True,
    )
    no_signal_source, no_signal_applicable = build_v25_atom_source_masks(
        route_speed_source_valid=speeds,
        signal_source_state="not_applicable",
        current_phase="none",
        allow_inapplicable_speed_atoms=True,
    )
    unavailable_source, unavailable_applicable = build_v25_atom_source_masks(
        route_speed_source_valid=speeds,
        signal_source_state="unavailable",
        current_phase="none",
        allow_inapplicable_speed_atoms=True,
        allow_unavailable_signal_atoms=True,
    )
    assert mapped_source[:, [10, 12]].all()
    assert mapped_applicable[:, [10, 12]].all()
    assert no_signal_source[:, [10, 12]].all()
    assert not no_signal_applicable[:, [10, 12]].any()
    assert not unavailable_source[:, [10, 12]].any()
    assert not unavailable_applicable[:, [10, 12]].any()
    assert not mapped_source[7, 4:7].any()
    assert not mapped_applicable[7, 4:7].any()


class _Rows:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._rows)


class _RouteLaneMapDb:
    def execute(self, query: str, params: tuple[object, ...] = ()) -> _Rows:
        if "SELECT 1 FROM lane_groups_polygons" in query:
            return _Rows([(1,)])
        if "FROM lanes_polygons AS l" in query:
            return _Rows(
                [
                    (11, b"center-missing-speed", None, 101, 102, None, None, None),
                    (12, b"center-complete", 11.0, 201, 202, None, None, None),
                ]
            )
        if "FROM boundaries" in query:
            assert params in {(101, 102), (201, 202)}
            return _Rows([(params[0], b"left"), (params[1], b"right")])
        raise AssertionError(query)


def test_route_lane_mapping_preserves_missing_speed_without_defaulting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nuplan_causal_adapter,
        "decode_projected_gpkg_geometry",
        lambda blob, _: ("official", blob),
    )
    candidates = nuplan_causal_adapter._roadblock_lane_candidates(
        _RouteLaneMapDb(), "42", "EPSG:26986"
    )
    assert [candidate["fid"] for candidate in candidates] == [11, 12]
    assert candidates[0]["speed_limit_mps"] is None
    assert candidates[0]["source_mapping"] == {
        "roadblock_id": "42",
        "lane_fid": 11,
        "kind": "lane",
        "speed_limit_source": "missing_or_invalid_authoritative",
        "speed_limit_available": False,
        "boundary_source": "official_boundaries_table",
        "boundary_roles": {"left": 101, "right": 102},
    }
    assert candidates[1]["speed_limit_mps"] == 11.0
    assert candidates[1]["source_mapping"]["speed_limit_available"] is True
    normalized, collapsed = nuplan_causal_adapter._collapse_consecutive_route_roadblocks(
        ("42", "42", "43", "43", "44")
    )
    assert normalized == ("42", "43", "44")
    assert collapsed == ("42", "43")


def test_boundary_projection_uses_authoritative_geometry_at_each_center_sample() -> None:
    center = np.column_stack((np.linspace(0.0, 19.0, 20), np.zeros(20)))
    boundary = np.array([[19.0, 2.0], [0.0, 2.0]], dtype=np.float64)
    projected = nuplan_causal_adapter._aligned_boundary(boundary, center)
    assert projected.shape == (20, 2)
    assert np.allclose(projected[:, 0], center[:, 0])
    assert np.allclose(projected[:, 1], 2.0)


def test_raw_context_receipt_serializes_positional_v25_context_by_frozen_names() -> None:
    raw = V25ContextRecord(
        raw=np.arange(len(RAW_FEATURE_NAMES), dtype=np.float64),
        source_complete=tuple(index % 2 == 0 for index in range(len(RAW_FEATURE_NAMES))),
        source_receipt={},
    )
    values, completeness = MODULE._raw_context_receipt(raw)
    assert tuple(values) == RAW_FEATURE_NAMES
    assert values[RAW_FEATURE_NAMES[3]] == 3.0
    assert completeness[RAW_FEATURE_NAMES[0]] is True
    assert completeness[RAW_FEATURE_NAMES[1]] is False


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
