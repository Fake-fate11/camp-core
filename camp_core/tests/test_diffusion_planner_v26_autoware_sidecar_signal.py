from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v26_autoware_sidecar_signal import (
    V26AutowareSidecarSignalAdapter,
    load_autoware_sidecar_binding,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sidecar_config(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    map_path = tmp_path / "map.osm"
    route_path = tmp_path / "route.pkl"
    map_path.write_bytes(b"map")
    route_path.write_bytes(b"route")
    regulatory = {
        "id": 1346,
        "runtime_type": "AutowareTrafficLight",
        "roles": [
            {
                "role": "ref_line",
                "primitives": [
                    {
                        "id": 1439,
                        "points": [
                            {"id": 1, "x": 1.0, "y": 0.0},
                            {"id": 2, "x": 1.0, "y": 2.0},
                        ],
                    }
                ],
            },
            {
                "role": "refers",
                "primitives": [{"id": 1412}, {"id": 1414}],
            },
            {
                "role": "light_bulbs",
                "primitives": [
                    {"id": 1, "points": [{"id": 70101}, {"id": 69969}]}
                ],
            },
        ],
    }
    manifest = {
        "geometry_copy_sha256": _sha(b"map"),
        "source_sha256": "a" * 64,
        "lanelets": [
            {"id": 100, "regulatory_element_ids": []},
            {"id": 443, "regulatory_element_ids": [1346]},
            {"id": 81, "regulatory_element_ids": []},
        ],
        "regulatory_elements": [regulatory],
    }
    manifest_path = tmp_path / "nishishinjuku.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    manifest_path.write_bytes(manifest_bytes)
    index = {
        "schema": "camp_autoware_lanelet2_regulatory_sidecar_index_v2",
        "status": "materialized_zero_model",
        "manifests": [
            {
                "manifest_path": str(manifest_path.resolve()),
                "manifest_sha256": _sha(manifest_bytes),
                "geometry_copy_sha256": _sha(b"map"),
                "source_sha256": "a" * 64,
            }
        ],
    }
    index_path = tmp_path / "index.json"
    index_bytes = json.dumps(index, sort_keys=True).encode()
    index_path.write_bytes(index_bytes)
    config = {
        "routes": [{"path": str(route_path), "sha256": _sha(b"route")}],
        "map": {"path": str(map_path), "sha256": _sha(b"map")},
        "regulatory_sidecar": {
            "geometry_copy_sha256": _sha(b"map"),
            "index_path": str(index_path),
            "index_sha256": _sha(index_bytes),
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha(manifest_bytes),
            "source_sha256": "a" * 64,
        },
    }
    return config, manifest


class _Cache:
    def __init__(self, start: float) -> None:
        self.raw_centerline = np.asarray([[start, 0.0], [start + 1.0, 0.0]])


class _Lanelet:
    def __init__(self, identifiers: list[int]) -> None:
        self._identifiers = identifiers

    def trafficLights(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=value) for value in self._identifiers]


class _Builder:
    def __init__(self) -> None:
        self._cache = {100: _Cache(0.0), 443: _Cache(1.0), 81: _Cache(2.0)}
        self._ll_by_id = {100: _Lanelet([]), 443: _Lanelet([1346]), 81: _Lanelet([])}


def _scene() -> SimpleNamespace:
    route = np.zeros((3, 2, 13), dtype=np.float32)
    route[1, 0, 8] = 1.0
    mapped = np.zeros((3, 2, 13), dtype=np.float32)
    mapped[1, 0, 8] = 1.0
    ego = SimpleNamespace(
        route_lanes=route,
        current_position=np.asarray([0.0, 0.0]),
        current_heading=0.0,
    )
    return SimpleNamespace(ego_agent=ego, map_data=SimpleNamespace(lanes=mapped), dt=0.1)


def test_traffic_light_sidecar_route_is_accepted_and_receipt_is_bound(tmp_path: Path) -> None:
    config, manifest = _sidecar_config(tmp_path)
    binding, loaded = load_autoware_sidecar_binding(config)
    assert loaded == manifest
    adapter = V26AutowareSidecarSignalAdapter(binding=binding, sidecar_manifest=loaded)
    adapter.bind_builder(_Builder())
    adapter.bind_runtime_lanelet_ids(route_lanelet_ids=[100, 443, 81], map_lanelet_ids=[100, 443, 81])
    controlled = adapter(_scene(), 0)
    receipt = controlled["signal_authority"]
    assert receipt["binding"] == binding
    assert receipt["controlled_lanelet_ids"] == [443]
    assert receipt["regulatory_element_id"] == 1346
    assert receipt["phase_authority_mode"] == "observe_same_tick_request"
    assert receipt["current_phase"] == "green"
    assert receipt["future_schedule_consumed"] is False
    causal = adapter.causal_signal_atom_input(_scene(), 0)
    assert causal["current_phase"] == "green"
    assert causal["runtime_receipt"]["source_chain_sha256"] == causal["source_chain_sha256"]
    assert causal["runtime_receipt"]["route_geometry_sha256"] == causal["route_geometry_sha256"]
    json.dumps(causal, sort_keys=True)


def test_target_scene_adapter_makes_legacy_no_signal_builder_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    fair = importlib.import_module("scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout")

    class FakeBuilder:
        def __init__(self, _map: str) -> None:
            pass

    class FakeRoute:
        route_lanelet_ids = [100]

        @staticmethod
        def load(_path: Path) -> "FakeRoute":
            return FakeRoute()

    class FakeSpawn:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def validate(self) -> None:
            return None

    class FakeReplay:
        SpawnConfig = FakeSpawn

    class Adapter:
        def __init__(self) -> None:
            self.builder = None

        def bind_builder(self, builder: object) -> None:
            self.builder = builder

    adapter = Adapter()
    monkeypatch.setattr(fair, "_build_no_signal_chain", lambda **_kwargs: pytest.fail("legacy path reached"))

    class StopHere(Exception):
        pass

    captured: dict[str, object] = {}

    def stop_callback(**_kwargs: object) -> object:
        captured.update(_kwargs)
        raise StopHere()

    monkeypatch.setattr(fair, "_FairPredictBatch", stop_callback)
    with pytest.raises(StopHere):
        fair._run_one(
            config={
                "map": {"path": "map", "sha256": "b" * 64},
                "routes": [{"path": "route", "sha256": "a" * 64}],
                "spawn_config": {},
                "fixed_dp": {},
            },
            model=object(), model_args=object(), tensor_converter=object(), replay=FakeReplay(),
            builder_type=FakeBuilder, route_type=FakeRoute, fixed_dp_repo=Path("."),
            assets=object(), device="cuda", max_ticks=1, operational_arm="Static14D",
            evaluate_all_arms=False, adaptation_diagnostics=False, scratch_parent=Path("."),
            scene_adapter=adapter,
        )
    assert captured["causal_signal_chain"] is None
    assert captured["scene_adapter"] is adapter
