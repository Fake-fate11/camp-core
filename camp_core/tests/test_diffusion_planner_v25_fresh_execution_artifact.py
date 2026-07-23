from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_opening import (
    freeze_fresh_b2_opening_release,
)
from scripts.integrations import review_diffusion_planner_v25_fresh_b2_execution as reviewer
from scripts.integrations import run_diffusion_planner_v25_fresh_b2_execution as runner
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as native


def _release() -> dict:
    return freeze_fresh_b2_opening_release(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        controller_decision_root_sha256="1" * 64,
        calibration_contract_root_sha256="2" * 64,
        preopen_qualification_root_sha256="3" * 64,
        model_registry_sha256="4" * 64,
        training_scale_sha256="5" * 64,
        context_scaler_sha256="6" * 64,
        scenario_manifest_root_sha256="7" * 64,
        run_nonce="8" * 64,
        authorized_output_dir="/root/autodl-tmp/v25-fresh-production-test",
    )


def test_fresh_nonce_consumption_is_atomic_and_strictly_reopenable(
    tmp_path: Path,
) -> None:
    release = _release()
    marker = runner._marker_path(release["run_nonce"], marker_root=tmp_path)
    digest = runner._consume_opening_nonce(
        release=release,
        release_root_sha256="9" * 64,
        marker_path=marker,
    )
    assert digest == hashlib.sha256(marker.read_bytes()).hexdigest()
    reviewer._review_nonce_marker(
        marker,
        release=release,
        release_root_sha256="9" * 64,
    )
    with pytest.raises(FileExistsError):
        runner._consume_opening_nonce(
            release=release,
            release_root_sha256="9" * 64,
            marker_path=marker,
        )


def test_production_entry_validates_assets_before_nonce_and_runtime() -> None:
    source = inspect.getsource(runner.run)
    controller = source.index("_verify_controller_decision(")
    assets = source.index("load_v25_runtime_selector_assets(")
    consume = source.index("_consume_opening_nonce(")
    native = source.index("_native_run_one(")
    execute = source.index("execute_fresh_b2_three_arm_units(")
    assert controller < assets < consume < native < execute


def test_fresh_native_callback_reuses_runtime_and_dispatches_frozen_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[dict] = []
    calls: list[dict] = []

    def fake_builder(config: dict, **kwargs: object):
        built.append({"config": config, **kwargs})

        def run_arm(**values: object) -> dict:
            calls.append(dict(values))
            sink = values.get("decision_sink")
            if sink is not None:
                for tick in range(64):
                    sink({"sidecar": {"tick_index": tick}})
            return {"status": "ok"}

        return run_arm

    monkeypatch.setattr(native, "build_native_arm_runner", fake_builder)
    scene_provider = object()
    callback = runner._native_run_one(
        device="cuda",
        assets=SimpleNamespace(scene14d_weight_provider=scene_provider),
        opening_authority={"opening_release": {}},
    )
    configs = [
        {
            "protocol": {"fresh_b2_plan_arm": plan_arm},
            "routes": [{"name": plan_arm}],
        }
        for plan_arm in (
            "candidate0_operational_default",
            "camp_static14d",
            "camp_scene14d_no_v2i",
        )
    ]
    for index, config in enumerate(configs):
        run_dir = tmp_path / str(index)
        run_dir.mkdir()
        receipt = callback(config, run_dir)
        assert receipt["status"] == "ok"
        assert receipt["fresh_decision_evidence_count"] == (0 if index == 0 else 64)
        assert receipt["fresh_decision_evidence_reference"]["logical_nbytes"] > 0
        assert not (run_dir / "decision_evidence.json").exists()
        assert (run_dir / "decision_evidence.json.gz").is_file()
    assert len(built) == 1
    assert [call["arm"] for call in calls] == ["dp", "camp", "camp"]
    assert [call["fixed_k8_candidate0"] for call in calls] == [True, False, False]
    assert calls[0]["v25_weight_provider"] is None
    assert calls[1]["v25_weight_provider"] is None
    assert calls[2]["v25_weight_provider"] is scene_provider
    assert all(call["max_steps"] == 64 for call in calls)


def test_runtime_selector_authority_is_bound_to_release_and_sealed_assets(
    tmp_path: Path,
) -> None:
    training = tmp_path / "training"
    training.mkdir()
    (training / "model_registry.json").write_bytes(b"registry")
    artifacts = {
        "training": training.resolve(),
        "training_review": (tmp_path / "training-review").resolve(),
    }
    roots = {
        "training": "a" * 64,
        "training_review": "b" * 64,
        "preopen": "3" * 64,
        "scenario_manifest": "7" * 64,
    }
    assets = SimpleNamespace(
        atom_scales_sha256="5" * 64,
        static14d_weights_sha256="c" * 64,
        scene14d_weight_provider=SimpleNamespace(
            context_scaler_sha256="6" * 64
        ),
    )
    release = _release()
    release["model_registry_sha256"] = hashlib.sha256(b"registry").hexdigest()
    authority = runner._runtime_selector_authority(
        assets=assets,
        artifacts=artifacts,
        roots=roots,
        release=release,
    )
    assert authority["training_artifact"]["root_sha256"] == "a" * 64
    assert authority["training_review_artifact"]["root_sha256"] == "b" * 64
    assert authority["preopen_qualification_root_sha256"] == "3" * 64
    assert authority["scenario_manifest_root_sha256"] == "7" * 64
    assert authority["training_scale_sha256"] == "5" * 64
    assert authority["context_scaler_sha256"] == "6" * 64

    mutated = dict(release)
    mutated["training_scale_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="sealed runtime selector assets"):
        runner._runtime_selector_authority(
            assets=assets,
            artifacts=artifacts,
            roots=roots,
            release=mutated,
        )


def test_review_nonce_marker_rejects_post_consumption_mutation(
    tmp_path: Path,
) -> None:
    release = _release()
    marker = runner._marker_path(release["run_nonce"], marker_root=tmp_path)
    runner._consume_opening_nonce(
        release=release,
        release_root_sha256="9" * 64,
        marker_path=marker,
    )
    payload = runner._canonical_json(marker)
    payload["second_consumption_allowed"] = True
    marker.write_bytes(runner._canonical_bytes(payload))
    with pytest.raises(ValueError, match="marker exact contract"):
        reviewer._review_nonce_marker(
            marker,
            release=release,
            release_root_sha256="9" * 64,
        )


def test_route_asset_projection_consumes_the_frozen_full_row_schema(
    tmp_path: Path,
) -> None:
    identity = "a" * 64
    row = {
        "route_identity_sha256": identity,
        "scenario_identity_sha256": "b" * 64,
        "map_sha256": "c" * 64,
        "map_geometry_sha256": "d" * 64,
        "corridor_sha256": "e" * 64,
        "source_chain_sha256": "f" * 64,
        "route_asset": {
            "name": identity,
            "path": str(tmp_path / "route.pkl"),
            "sha256": "1" * 64,
        },
        "route_lanelet_ids": [1],
        "start_pose_float32": [0.0, 0.0, 0.0],
        "goal_pose_float32": [1.0, 0.0, 0.0],
        "waypoint_count": 0,
        "fixed_dp_route_source": "scenario_generation/route.py",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    artifact = tmp_path / "route-artifact"
    artifact.mkdir()
    (artifact / "route_assets.json").write_bytes(
        runner._canonical_bytes({"route_assets": [row]})
    )
    assert runner._route_assets(artifact) == {identity: row["route_asset"]}

    row["future_outcome"] = True
    (artifact / "route_assets.json").write_bytes(
        runner._canonical_bytes({"route_assets": [row]})
    )
    with pytest.raises(ValueError, match="route asset row drifted"):
        runner._route_assets(artifact)
