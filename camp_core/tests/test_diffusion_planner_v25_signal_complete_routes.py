from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
import pickle

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (
    materialize_signal_complete_route_assets,
    validate_signal_complete_route_assets,
)


@dataclass
class FakeRoute:
    map_path: str
    start_pose: np.ndarray
    goal_pose: np.ndarray
    start_lanelet_id: int | None
    goal_lanelet_id: int | None
    waypoint_poses: list[np.ndarray] = field(default_factory=list)
    waypoint_lanelet_ids: list[int] = field(default_factory=list)
    route_lanelet_ids: list[int] | None = None

    def save(self, path: Path) -> None:
        with path.open("wb") as handle:
            pickle.dump(self, handle)

    @classmethod
    def load(cls, path: Path) -> "FakeRoute":
        with path.open("rb") as handle:
            result = pickle.load(handle)
        if not isinstance(result, cls):
            raise TypeError("route type drifted")
        return result


def _maps(tmp_path: Path, split: str) -> Path:
    suite = build_signal_complete_suite(split)
    for relative, payload in suite["map_payloads"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return tmp_path


def test_signal_complete_route_assets_are_exact_fixed_dp_routes(
    tmp_path: Path,
) -> None:
    plan = build_signal_complete_execution_plan("calibration")
    maps = _maps(tmp_path / "maps", "calibration")
    output = tmp_path / "route_artifact"
    manifest = materialize_signal_complete_route_assets(
        plan=plan,
        map_artifact=maps,
        output_dir=output,
        route_class=FakeRoute,
    )
    assert manifest["route_count"] == 50
    assert manifest["model_loaded"] is False
    assert manifest["candidate_generation_executed"] is False
    assert manifest["fresh_b2_opened"] is False
    assert (
        validate_signal_complete_route_assets(
            copy.deepcopy(manifest),
            plan=plan,
            map_artifact=maps,
            route_class=FakeRoute,
        )
        == manifest
    )
    first_identity = plan["identities"][0]
    first = manifest["route_assets"][0]
    route = FakeRoute.load(Path(first["route_asset"]["path"]))
    assert route.start_pose.dtype == np.float32
    assert route.goal_pose.dtype == np.float32
    assert route.route_lanelet_ids == first_identity["route_spec"]["lanelet_ids"]
    assert route.start_lanelet_id == route.route_lanelet_ids[0]
    assert route.goal_lanelet_id == route.route_lanelet_ids[-1]
    assert route.waypoint_poses == []
    assert route.waypoint_lanelet_ids == []


def test_route_asset_manifest_or_pickle_mutation_fails_closed(tmp_path: Path) -> None:
    plan = build_signal_complete_execution_plan("calibration")
    maps = _maps(tmp_path / "maps", "calibration")
    manifest = materialize_signal_complete_route_assets(
        plan=plan,
        map_artifact=maps,
        output_dir=tmp_path / "route_artifact",
        route_class=FakeRoute,
    )

    mutated = copy.deepcopy(manifest)
    mutated["route_assets"][0]["route_asset"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="row root"):
        validate_signal_complete_route_assets(
            mutated,
            plan=plan,
            map_artifact=maps,
            route_class=FakeRoute,
        )

    path = Path(manifest["route_assets"][0]["route_asset"]["path"])
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="bytes"):
        validate_signal_complete_route_assets(
            manifest,
            plan=plan,
            map_artifact=maps,
            route_class=FakeRoute,
        )
