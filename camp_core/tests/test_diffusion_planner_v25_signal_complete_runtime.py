from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (
    validate_mapped_signal_chain,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    V25SignalCompleteBackgroundAdapter,
    build_signal_complete_runtime_case,
    build_signal_complete_scene_adapter,
)


ROOT = Path(__file__).resolve().parents[2]


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUALIFIER = _module(
    "scripts/integrations/qualify_diffusion_planner_v25_signal_complete_runtime.py",
    "v25_signal_runtime_qualifier",
)


def _materialize_maps(tmp_path: Path, split: str) -> tuple[Path, dict]:
    suite = build_signal_complete_suite(split)
    for relative, payload in suite["map_payloads"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return tmp_path, suite


def test_fixed_dp_float32_signal_chain_tolerance_is_bounded() -> None:
    exact = {
        "scenario_id": "scenario",
        "route_identity_sha256": "1" * 64,
        "source_map_sha256": "2" * 64,
        "phase_authority_mode": "observe_same_tick_request",
        "expected_current_phase": None,
        "formal_phase": "none",
        "formal_mapped_source_required": False,
        "regulatory_element_ids": [1],
        "physical_light_ids": [2],
        "bulb_ids": [3],
        "controlled_lanelet_ids": [4],
        "route_lanelet_ids": [4, 5, 6],
        "stop_line_id": 7,
        "stop_line_geometry_m": [[10.0, 1.0], [10.0, -1.0]],
        "route_tangent_world": [1.0, 0.0],
        "stop_line_route_distance_m": 0.0,
        "route_arc_m": 10.0,
        "route_length_m": 100.0,
    }
    within = copy.deepcopy(exact)
    within["stop_line_geometry_m"][0][0] += 0.9e-6
    within["route_tangent_world"][1] += 0.9e-5
    within["stop_line_route_distance_m"] += 0.9 * 2e-4
    assert QUALIFIER._planned_actual_chain_consistent(exact, within)

    for field, delta in (
        ("stop_line_route_distance_m", 2.1e-4),
        ("route_arc_m", 2.1e-4),
        ("route_length_m", 2.1e-4),
    ):
        outside = copy.deepcopy(exact)
        outside[field] += delta
        assert not QUALIFIER._planned_actual_chain_consistent(exact, outside)
    outside_tangent = copy.deepcopy(exact)
    outside_tangent["route_tangent_world"][1] += 1.1e-5
    assert not QUALIFIER._planned_actual_chain_consistent(exact, outside_tangent)


def test_every_calibration_identity_builds_legal_source_only_runtime_case(
    tmp_path: Path,
) -> None:
    map_root, _suite = _materialize_maps(tmp_path, "calibration")
    plan = build_signal_complete_execution_plan("calibration")
    phases = set()
    for identity in plan["identities"]:
        result = build_signal_complete_runtime_case(
            identity, map_artifact=map_root, seeds=plan["seeds"]
        )
        case = result["case"]
        chain = validate_mapped_signal_chain(result["mapped_signal_authority"])
        assert case["mapped_signal_authority"] == chain
        assert "phase_remaining_s" not in case["signal"]
        assert chain["phase_remaining_available"] is False
        assert result["model_loaded"] is False
        assert result["candidate_generation_executed"] is False
        assert result["fresh_b2_opened"] is False
        if case["family"] == "red_light_phase_timing":
            phases.add(case["signal"]["phase"])
            assert chain["phase_authority_mode"] == "controlled_same_tick_override"
        else:
            assert case["signal"] == {
                "phase": "none",
                "mapped_source_required": False,
            }
            assert chain["phase_authority_mode"] == "observe_same_tick_request"
    assert phases == {"green", "yellow", "red"}


def test_runtime_case_binds_exact_map_bytes(tmp_path: Path) -> None:
    map_root, _suite = _materialize_maps(tmp_path, "calibration")
    identity = build_signal_complete_execution_plan("calibration")["identities"][0]
    path = map_root / identity["map_relative_path"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="map SHA"):
        build_signal_complete_runtime_case(identity, map_artifact=map_root, seeds=[25301])


def test_runtime_case_rejects_bad_seed_types(tmp_path: Path) -> None:
    map_root, _suite = _materialize_maps(tmp_path, "calibration")
    identity = build_signal_complete_execution_plan("calibration")["identities"][0]
    with pytest.raises(ValueError, match="seeds"):
        build_signal_complete_runtime_case(identity, map_artifact=map_root, seeds=[True])


def test_fresh_naturalistic_identity_has_no_scripted_actors_or_future_signal(
    tmp_path: Path,
) -> None:
    map_root, _suite = _materialize_maps(tmp_path, "fresh_b2")
    plan = build_signal_complete_execution_plan("fresh_b2")
    identity = next(
        row for row in plan["identities"] if row["benchmark_stratum"] == "naturalistic"
    )
    result = build_signal_complete_runtime_case(
        identity, map_artifact=map_root, seeds=plan["seeds"]
    )
    assert result["case"]["family"] == "naturalistic_background"
    assert result["case"]["tier"] == "naturalistic"
    assert result["case"]["actors"] == []
    assert result["case"]["signal"] == {
        "phase": "none",
        "mapped_source_required": False,
    }
    assert result["mapped_signal_authority"]["phase_authority_mode"] == (
        "observe_same_tick_request"
    )
    adapter = build_signal_complete_scene_adapter(result)
    assert isinstance(adapter, V25SignalCompleteBackgroundAdapter)
    assert adapter.case["actors"] == []
    assert adapter.mapped_signal_authority["expected_current_phase"] is None


def test_controlled_signal_complete_identity_keeps_controlled_adapter(
    tmp_path: Path,
) -> None:
    map_root, _suite = _materialize_maps(tmp_path, "calibration")
    plan = build_signal_complete_execution_plan("calibration")
    identity = next(
        row
        for row in plan["identities"]
        if row["scenario_family"] == "red_light_phase_timing"
    )
    result = build_signal_complete_runtime_case(
        identity, map_artifact=map_root, seeds=plan["seeds"]
    )
    adapter = build_signal_complete_scene_adapter(result)
    assert not isinstance(adapter, V25SignalCompleteBackgroundAdapter)
    assert adapter.case["family"] == "red_light_phase_timing"
