from __future__ import annotations

import copy
import hashlib
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "camp_core") not in sys.path:
    sys.path.insert(0, str(ROOT / "camp_core"))

from camp_core.integrations import diffusion_planner_v26_integration_boundary as boundary
from camp_core.integrations.diffusion_planner_v21_native import array_sha256
from camp_core.integrations.diffusion_planner_v26_native_runner import (
    V26NativeSameEgoB8Callback,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (
    build_v26_source_signal_config,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _no_signal_config() -> dict[str, object]:
    route_sha = _sha(1)
    map_sha = _sha(2)
    return {
        "signal_authority_mode": boundary.V26_CERTIFIED_NO_SIGNAL_MODE,
        "routes": [{"sha256": route_sha}],
        "map": {"sha256": map_sha},
        "certified_no_signal_authority": {
            "schema_version": boundary.V26_CERTIFIED_NO_SIGNAL_SCHEMA_VERSION,
            "route_sha256": route_sha,
            "map_sha256": map_sha,
            "route_lanelet_ids": [11, 12],
            "route_geometry_sha256": _sha(3),
            "source_chain_sha256": _sha(4),
            "certification_sha256": _sha(5),
            "traffic_light_regulatory_element_ids": [],
        },
    }


def _source_traffic_config(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    source = tmp_path / "source_traffic.osm"
    source.write_text(
        """<osm version=\"0.6\">
  <node id=\"1\" lat=\"0.665608\" lon=\"-0.559376\"/>
  <node id=\"2\" lat=\"0.665609\" lon=\"-0.559375\"/>
  <node id=\"3\" lat=\"0.665610\" lon=\"-0.559374\"/>
  <way id=\"10\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
  <way id=\"11\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
  <way id=\"12\"><nd ref=\"2\"/><nd ref=\"3\"/></way>
  <relation id=\"1\">
    <member type=\"relation\" ref=\"100\" role=\"regulatory_element\"/>
    <tag k=\"type\" v=\"lanelet\"/>
  </relation>
  <relation id=\"100\">
    <member type=\"way\" ref=\"10\" role=\"refers\"/>
    <member type=\"way\" ref=\"11\" role=\"ref_line\"/>
    <member type=\"way\" ref=\"12\" role=\"light_bulbs\"/>
    <tag k=\"type\" v=\"regulatory_element\"/>
    <tag k=\"subtype\" v=\"traffic_light\"/>
  </relation>
</osm>""",
        encoding="utf-8",
    )
    map_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    schedule: dict[str, object] = {
        "family_id": "source_fixture",
        "route_id": "source_fixture/route-0000",
        "corridor_id": _sha(40),
        "parent_ordinal": 485,
        "scenario_seed": 46486,
        "source_artifact_sha256": _sha(41),
        "event_manifest_sha256": _sha(42),
        "route_record": {
            "identity_sha256": _sha(43),
            "source_map_path": str(source),
            "source_map_sha256": map_sha,
            "source_geometry_sha256": _sha(44),
            "lanelet_ids": [1],
            "source_stratum": {
                "traffic_light": True,
                "branch_intersection": False,
                "tight_corridor": True,
                "short_progress_opportunity": False,
            },
        },
    }
    signal = build_v26_source_signal_config(
        schedule=schedule,
        family={"sidecar": None},
        route_sha256=_sha(45),
    )
    return {
        "routes": [{"path": str(tmp_path / "route.pkl"), "sha256": _sha(45)}],
        "map": {"path": str(source), "sha256": map_sha},
        **signal,
    }, schedule


def test_signal_dispatch_requires_an_explicit_mode_and_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="signal_authority_mode is required"):
        boundary.resolve_v26_signal_adapter({})
    with pytest.raises(ValueError, match="no certified adapter"):
        boundary.resolve_v26_signal_adapter({"signal_authority_mode": "legacy"})

    no_signal = boundary.resolve_v26_signal_adapter(_no_signal_config())
    assert no_signal.mode == boundary.V26_CERTIFIED_NO_SIGNAL_MODE
    assert no_signal.adapter_id == boundary.V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID

    fake_binding = {
        "schema_version": "camp_dp_v26_autoware_sidecar_binding_v1",
        "route_sha256": _sha(6),
        "map_sha256": _sha(7),
        "geometry_copy_sha256": _sha(7),
        "sidecar_index_sha256": _sha(8),
        "sidecar_manifest_sha256": _sha(9),
        "sidecar_source_sha256": _sha(10),
    }
    captured: dict[str, object] = {}

    class FakeAdapter:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        boundary,
        "load_autoware_sidecar_binding",
        lambda _config: (fake_binding, {"sidecar": "fixture"}),
    )
    monkeypatch.setattr(boundary, "V26AutowareSidecarSignalAdapter", FakeAdapter)
    sidecar = boundary.resolve_v26_signal_adapter(
        {
            "signal_authority_mode": boundary.V26_AUTOWARE_SIDECAR_SIGNAL_MODE,
        }
    )
    assert sidecar.adapter_id == boundary.V26_AUTOWARE_SIDECAR_ADAPTER_ID
    assert captured["binding"] == fake_binding


def test_boundary_reviewer_rejects_v25_high_level_consumer_ids() -> None:
    signal = boundary.resolve_v26_signal_adapter(_no_signal_config())
    value = boundary.build_v26_integration_boundary(
        signal=signal, reference_weights_root_sha256=_sha(20)
    )
    assert boundary.validate_v26_integration_boundary(value) == value
    assert value["weight_sources"]["reference"]["role"] == (
        boundary.V25_ZERO_SHOT_REFERENCE_READ_ONLY
    )
    assert value["weight_sources"]["adapted"]["role"] == "not_present_for_this_run"
    value["consumer_ids"][0] = "scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout"
    with pytest.raises(ValueError, match="rejects V25 high-level"):
        boundary.validate_v26_integration_boundary(value)


def test_three_exact_signal_pairs_pass_and_cross_pair_unknown_or_hash_drift_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    no_signal = boundary.resolve_v26_signal_adapter(_no_signal_config())
    assert boundary.validate_v26_integration_boundary(
        boundary.build_v26_integration_boundary(
            signal=no_signal, reference_weights_root_sha256=_sha(50)
        )
    )["signal_adapter_id"] == boundary.V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID

    fake_binding = {
        "schema_version": "camp_dp_v26_autoware_sidecar_binding_v1",
        "route_sha256": _sha(51),
        "map_sha256": _sha(52),
        "geometry_copy_sha256": _sha(52),
        "sidecar_index_sha256": _sha(53),
        "sidecar_manifest_sha256": _sha(54),
        "sidecar_source_sha256": _sha(55),
    }

    class FakeAdapter:
        def __init__(self, **_kwargs: object) -> None:
            pass

    monkeypatch.setattr(
        boundary,
        "load_autoware_sidecar_binding",
        lambda _config: (fake_binding, {"sidecar": "fixture"}),
    )
    monkeypatch.setattr(boundary, "V26AutowareSidecarSignalAdapter", FakeAdapter)
    autoware = boundary.resolve_v26_signal_adapter(
        {"signal_authority_mode": boundary.V26_AUTOWARE_SIDECAR_SIGNAL_MODE}
    )
    assert boundary.validate_v26_integration_boundary(
        boundary.build_v26_integration_boundary(
            signal=autoware, reference_weights_root_sha256=_sha(56)
        )
    )["signal_adapter_id"] == boundary.V26_AUTOWARE_SIDECAR_ADAPTER_ID

    config, schedule = _source_traffic_config(tmp_path)
    source_signal = boundary.resolve_v26_signal_adapter(config)
    source_value = boundary.build_v26_integration_boundary(
        signal=source_signal, reference_weights_root_sha256=_sha(57)
    )
    assert boundary.validate_v26_integration_boundary(source_value)["signal_adapter_id"] == (
        boundary.V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID
    )

    cross_pair = copy.deepcopy(source_value)
    cross_pair["signal_adapter_id"] = boundary.V26_AUTOWARE_SIDECAR_ADAPTER_ID
    with pytest.raises(ValueError, match="signal adapter drifted"):
        boundary.validate_v26_integration_boundary(cross_pair)
    unknown = copy.deepcopy(source_value)
    unknown["signal_authority_mode"] = "unknown_source_mode"
    with pytest.raises(ValueError, match="signal adapter drifted"):
        boundary.validate_v26_integration_boundary(unknown)
    hash_drift = copy.deepcopy(source_signal.receipt)
    hash_drift["source_authority"]["source_projection_sha256"] = _sha(58)
    with pytest.raises(ValueError, match="authority hash drifted"):
        boundary.validate_v26_source_map_signal_binding(hash_drift)
    with pytest.raises(ValueError, match="prepared authority"):
        boundary.validate_v26_source_map_signal_binding(
            source_signal.receipt,
            route_sha256=_sha(45),
            map_sha256=schedule["route_record"]["source_map_sha256"],
            route_geometry_sha256=schedule["route_record"]["source_geometry_sha256"],
            source_projection_sha256=_sha(59),
            source_inventory_sha256=source_signal.receipt["source_authority"][
                "source_inventory_sha256"
            ],
        )


def test_source_traffic_qualification_calls_native_boundary_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qualification = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_successor_pre_model"
    )
    config, schedule = _source_traffic_config(tmp_path)
    signal = boundary.resolve_v26_signal_adapter(config)
    calls: list[dict[str, object]] = []

    def build(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"signal_adapter_binding": signal.receipt}

    monkeypatch.setattr(qualification, "build_v26_integration_boundary", build)
    record = schedule["route_record"]
    result = qualification._qualified_integration_boundary(
        schedule=schedule,
        route_sha256=_sha(45),
        projection={"projection_sha256": signal.receipt["source_authority"]["source_projection_sha256"]},
        signal=config,
        signal_binding=signal,
        reference_weights_root_sha256=_sha(60),
    )
    assert result == {"signal_adapter_binding": signal.receipt}
    assert calls == [
        {
            "signal": signal,
            "reference_weights_root_sha256": _sha(60),
        }
    ]
    assert record["source_stratum"]["traffic_light"] is True


def test_source_traffic_prepared_receipt_must_match_qualification(tmp_path: Path) -> None:
    qualification = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_successor_pre_model"
    )
    successor_runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_successor_acquisition"
    )
    config, schedule = _source_traffic_config(tmp_path)
    signal = boundary.resolve_v26_signal_adapter(config)
    projection = {"projection_sha256": signal.receipt["source_authority"]["source_projection_sha256"]}
    integration = qualification._qualified_integration_boundary(
        schedule=schedule,
        route_sha256=_sha(45),
        projection=projection,
        signal=config,
        signal_binding=signal,
        reference_weights_root_sha256=_sha(61),
    )
    record = schedule["route_record"]
    qualified = {
        "route_asset_sha256": _sha(45),
        "source_projection": projection,
        "route": {
            "source_geometry_sha256": record["source_geometry_sha256"],
            "source_map_sha256": record["source_map_sha256"],
        },
        "signal": {
            "source_provenance": config["source_signal_authority"],
            "adapter_binding": signal.receipt,
        },
        "integration_boundary_validation": {
            "status": "passed",
            "integration_boundary": integration,
        },
    }
    prepared = {"config": config, "signal": signal, "projection": projection}
    assert successor_runner._require_qualified_integration_boundary(
        qualified_unit=qualified,
        prepared_item=prepared,
        assets=SimpleNamespace(reference_weights_root_sha256=_sha(61)),
    ) == integration
    drifted = copy.deepcopy(prepared)
    drifted["projection"]["projection_sha256"] = _sha(62)
    with pytest.raises(ValueError, match="route/qualification identity drifted"):
        successor_runner._require_qualified_integration_boundary(
            qualified_unit=qualified,
            prepared_item=drifted,
            assets=SimpleNamespace(reference_weights_root_sha256=_sha(61)),
        )


def test_launcher_config_is_fixed_to_dp312_and_no_human_shim() -> None:
    config_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "integrations"
        / "diffusion_planner_v26_autodl_launcher_v1.json"
    )
    config = boundary.load_v26_autodl_launcher_config(config_path)
    assert config["interpreter"] == "/root/autodl-tmp/dp312_venv/bin/python"
    assert config["dp312_site_packages"] == (
        "/root/autodl-tmp/dp312_venv/lib/python3.12/site-packages"
    )
    assert config["inherit_pythonpath"] is False
    assert config["human_shim_required"] is False
    environment = boundary.v26_autodl_launcher_environment(
        source_checkout="/root/autodl-tmp/v26_checkout",
        fixed_dp_repo="/root/autodl-tmp/Diffusion-Planner",
    )
    assert environment == {
        "PYTHONPATH": (
            "/root/autodl-tmp/dp312_venv/lib/python3.12/site-packages:"
            "/root/autodl-tmp/v26_checkout:/root/autodl-tmp/v26_checkout/camp_core:"
            "/root/autodl-tmp/Diffusion-Planner"
        ),
        "PYTHONNOUSERSITE": "1",
    }


def test_every_real_static_scene_selector_call_receives_frozen_simplex_tolerance() -> None:
    callback = V26NativeSameEgoB8Callback.__new__(V26NativeSameEgoB8Callback)
    callback.simplex_nonnegative_atol = boundary.FROZEN_SIMPLEX_TOLERANCE
    callback.selector_assets = SimpleNamespace(
        atom_scales=np.ones(14, dtype=np.float64),
        static9d_weights_sha256=_sha(30),
        scene9d_theta_sha256=_sha(31),
        static14d_weights_sha256=_sha(32),
        scene14d_theta_sha256=_sha(33),
    )
    observed: list[float] = []

    def select_candidate(**kwargs: object) -> dict[str, object]:
        observed.append(float(kwargs["simplex_nonnegative_atol"]))
        return {
            "status": "ok",
            "failure_reason": None,
            "selected_index": 0,
            "scores": np.arange(8, dtype=np.float64),
            "physical_feasible_mask": np.ones(8, dtype=np.bool_),
            "source_valid_mask": np.ones(8, dtype=np.bool_),
        }

    callback._select_candidate = select_candidate
    candidates = np.arange(8 * 2 * 4, dtype=np.float32).reshape(8, 2, 4)
    materialized = {"source_valid_mask": np.ones(8, dtype=np.bool_)}
    for arm_id in ("Static9D", "Scene9D", "Static14D", "Scene14D"):
        row = callback._profile_selector(
            arm_id=arm_id,
            candidates=candidates,
            materialized=materialized,
            weights=np.full(14, 1.0 / 14.0, dtype=np.float64),
            context={} if arm_id.startswith("Scene") else None,
        )
        assert row["selected_row_sha256"] == array_sha256(candidates[0])
    assert observed == [boundary.FROZEN_SIMPLEX_TOLERANCE] * 4
