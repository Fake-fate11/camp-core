from __future__ import annotations

import importlib
import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _orchestrator():
    try:
        return importlib.import_module(
            "scripts.integrations.run_diffusion_planner_dp_camp_v18"
        )
    except ModuleNotFoundError:
        pytest.fail("the thin v18 orchestrator is missing")


def _causal_input() -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["neighbor_agents_past"][0, 0, 0] = 7.0
    return data


def test_prepare_causal_arrays_pads_only_neighbor_history() -> None:
    module = _orchestrator()

    prepared = module.prepare_causal_arrays(_causal_input())

    assert set(prepared) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert prepared["neighbor_agents_past"].shape == (320, 31, 11)
    assert prepared["neighbor_agents_past"][0, 0, 0] == 7.0
    assert not prepared["neighbor_agents_past"][32:].any()
    assert not any("future" in key for key in prepared)


def test_prepare_causal_arrays_rejects_future_fields() -> None:
    module = _orchestrator()
    data = _causal_input()
    data["ego_agent_future"] = np.zeros((80, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="future|extra"):
        module.prepare_causal_arrays(data)


def test_same_calls_return_paired_ego_and_first_32_neighbors() -> None:
    torch = pytest.importorskip("torch")
    module = _orchestrator()

    class Decoder:
        _guidance_fn = "original"
        _guidance_scale = 9.0

    class Model:
        decoder = Decoder()

        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _data):
            prediction = torch.zeros((1, 321, 80, 4), dtype=torch.float32)
            prediction[:, :, :, 0] = self.calls
            prediction[:, :, :, 1] = torch.arange(321).reshape(1, 321, 1)
            self.calls += 1
            return None, {"prediction": prediction}

    model = Model()
    context = {
        "torch": torch,
        "device": torch.device("cpu"),
        "model": model,
        "config": type(
            "Config",
            (),
            {
                "predicted_neighbor_num": 320,
                "future_len": 80,
                "observation_normalizer": staticmethod(lambda value: value),
            },
        )(),
        "heading_to_cos_sin": lambda value: value,
        "make_initial_latent": lambda batch, agents, horizon, device, scale: torch.zeros(
            (batch, agents, horizon, 4), device=device
        ),
    }
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0

    candidates, neighbors, valid = module.sample_fixed_dp_sources(data, context)

    assert model.calls == 8
    assert candidates.shape == (8, 80, 4)
    assert neighbors.shape == (8, 32, 80, 4)
    np.testing.assert_array_equal(candidates[:, 0, 0], np.arange(8))
    np.testing.assert_array_equal(neighbors[0, :, 0, 1], np.arange(1, 33))
    np.testing.assert_array_equal(valid[:3], np.ones(3, dtype=bool))
    assert not valid[3:].any()
    assert model.decoder._guidance_fn == "original"
    assert model.decoder._guidance_scale == 9.0


def test_white_signal_mask_is_fail_closed_only_when_reachable() -> None:
    module = _orchestrator()
    candidates = np.zeros((2, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    candidates[1, :, 0] = np.linspace(0.0, 2.0, 80)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(10.0, 15.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 11] = 1.0

    available = module.candidate_signal_source_available_mask(candidates, route)

    np.testing.assert_array_equal(available, [False, True])


def test_refresh_manifest_preserves_identity_and_replaces_causal_provenance(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    old = tmp_path / "old.jsonl"
    row = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "db_path": "db",
        "map_path": "map",
        "causal_input_sha256": "old",
    }
    old.write_text(json.dumps(row) + "\n", encoding="utf-8")
    output = tmp_path / "new.jsonl"
    data = _causal_input()
    data["static_objects"][0, :6] = [1.0, 0.0, 1.0, 0.0, 1.0, 2.0]
    data["neighbor_agents_past"][:3, 0, 0] = 1.0
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": data})(),
    )
    args = type(
        "Args",
        (),
        {
            "manifest": old,
            "expected_manifest_sha256": module._sha256(old),
            "refresh_manifest_output": output,
        },
    )()

    report = module.refresh_manifest(args)
    refreshed = json.loads(output.read_text(encoding="utf-8"))

    assert report["record_count"] == 1
    assert refreshed["split"] == "train"
    assert refreshed["scene_token"] == "scene"
    assert refreshed["causal_input_sha256"] != "old"
    assert refreshed["causal_source_schema_version"] == module.CAUSAL_SOURCE_SCHEMA_VERSION
    assert refreshed["parent_manifest_sha256"] == args.expected_manifest_sha256
    assert refreshed["static_object_count"] == 1
    assert refreshed["neighbor_valid_count"] == 3
    with pytest.raises(FileExistsError):
        module.refresh_manifest(args)


def test_run_manifest_writes_single_record_v2_source_provenance(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0
    data["route_lanes"][0, :, 0] = np.linspace(10.0, 15.0, 20)
    data["route_lanes"][0, :, 2] = 1.0
    data["route_lanes"][0, :, 11] = 1.0
    manifest = tmp_path / "manifest.jsonl"
    row = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "db_path": "db",
        "map_path": "map",
        "causal_input_sha256": module.causal_input_sha256(data),
        "causal_source_schema_version": module.CAUSAL_SOURCE_SCHEMA_VERSION,
    }
    manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float32)
    valid = np.zeros(32, dtype=bool)
    valid[:3] = True
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Completed", (), {"stdout": module.FIXED_DP_HEAD + "\n"}
        )(),
    )
    monkeypatch.setattr(
        module,
        "_load_context",
        lambda *_args: {
            "torch": type("Torch", (), {"manual_seed": staticmethod(lambda _seed: None)})
        },
    )
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": data})(),
    )
    monkeypatch.setattr(
        module,
        "sample_fixed_dp_sources",
        lambda *_args, **_kwargs: (candidates, neighbors, valid),
    )
    args = type(
        "Args",
        (),
        {
            "manifest": manifest,
            "expected_manifest_sha256": module._sha256(manifest),
            "refresh_manifest_output": None,
            "output_dir": tmp_path / "output",
            "dp_repo": tmp_path,
            "checkpoint": tmp_path / "model.ckpt",
            "args_json": tmp_path / "args.json",
            "k": 8,
            "seed": 3407,
            "noise_scale": 1.0,
            "device": "cpu",
            "max_records": 0,
            "execute": True,
        },
    )()

    report = module.run_manifest(args)
    output_npz = args.output_dir / "train" / "log" / "scene.npz"
    with np.load(output_npz, allow_pickle=False) as payload:
        assert set(payload.files) == {
            "candidate_tensor",
            "neighbor_prediction_tensor",
            "neighbor_valid_mask",
            "candidate_signal_source_available_mask",
            "eligible_for_canonical_14d",
            "causal_input_sha256",
            "causal_source_schema_version",
            "dp_top1_index",
            "candidate_count",
        }
        assert payload["neighbor_prediction_tensor"].shape == (8, 32, 80, 4)
        assert payload["neighbor_valid_mask"].shape == (32,)
        assert payload["candidate_signal_source_available_mask"].shape == (8,)
        assert not bool(payload["eligible_for_canonical_14d"])
    record = json.loads((args.output_dir / "records.jsonl").read_text().strip())
    assert report["schema_version"] == "dp_camp_v18_causal_fixed_dp_export_v2"
    assert record["physical_feasibility_mask_materialized"] is False
    assert record["eligible_for_canonical_14d"] is False
    with pytest.raises(FileExistsError):
        module.run_manifest(args)
