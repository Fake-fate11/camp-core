from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations import diffusion_planner_v26_integration_boundary as boundary
from camp_core.integrations.diffusion_planner_v21_native import array_sha256
from camp_core.integrations.diffusion_planner_v26_native_runner import (
    V26NativeSameEgoB8Callback,
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
