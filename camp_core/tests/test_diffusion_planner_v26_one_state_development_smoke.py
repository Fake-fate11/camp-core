from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    materialization_phase_receipt_not_available,
)
from camp_core.integrations.diffusion_planner_v26_one_state_development_smoke import (
    EVIDENCE_ROLE,
    SMOKE_ARM,
    build_development_smoke_manifest,
    build_development_smoke_receipt,
    validate_development_smoke_manifest,
    validate_development_smoke_receipt,
)
from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (
    PRODUCTION_SURFACE_ID,
    build_target_bounded_tick_receipt,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _manifest() -> dict[str, object]:
    return build_development_smoke_manifest(
        camp_head="a" * 40,
        probe_config_sha256=_sha(1),
        route_sha256=_sha(2),
        scenario_seed=17,
        spawn_config={"scenario_seed": 17},
        fixed_dp_head="b" * 40,
        checkpoint_path="/fixed/model.ckpt",
        checkpoint_sha256=_sha(3),
        args_path="/fixed/args.json",
        args_sha256=_sha(4),
        training_root_sha256=_sha(5),
        training_review_root_sha256=_sha(6),
        atom_scales_sha256=_sha(7),
        static14d_weights_sha256=_sha(8),
        signal_authority={
            "schema_version": "camp_dp_v26_autoware_sidecar_binding_v1",
            "route_sha256": _sha(2),
            "map_sha256": _sha(70),
            "geometry_copy_sha256": _sha(70),
            "sidecar_index_sha256": _sha(71),
            "sidecar_manifest_sha256": _sha(72),
            "sidecar_source_sha256": _sha(73),
        },
    )


def _completed_unit() -> dict[str, object]:
    rows = [_sha(20 + index) for index in range(8)]
    latent_rows = [_sha(40 + index) for index in range(8)]
    return {
        "unit_index": 0,
        "operational_arm": SMOKE_ARM,
        "state_sha256": _sha(9),
        "input": {
            "source_input_sha256": _sha(10),
            "expanded_input_sha256": _sha(11),
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": {
                "history": {"shape": [8, 31, 11], "dtype": "torch.float32", "finite": True},
                "sampled_trajectories": {"shape": [8, 321, 81, 4], "dtype": "torch.float32", "finite": True},
            },
        },
        "latent": {
            "seed": 19,
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "finite": True,
            "tensor_sha256": _sha(12),
            "row_sha256": latent_rows,
            "row0_zero": True,
        },
        "candidate_pool": {
            "shape": [8, 80, 4],
            "dtype": "float32",
            "finite": True,
            "pool_sha256": _sha(13),
            "row_sha256": rows,
            "candidate0": {"index": 0, "row_sha256": rows[0], "default_output_sha256": rows[0]},
        },
        "forward_calls": {
            "model_call_count_before": 0,
            "model_call_count_after": 1,
            "model_call_delta": 1,
            "primary_forward_count": 1,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "selection": {"selected_index": 2, "selected_row_sha256": rows[2]},
        "simulator": {"selected_row_sha256": rows[2]},
        "signal_authority": {
            "schema_version": "camp_dp_v26_autoware_sidecar_signal_receipt_v1",
            "binding": _manifest()["signal_authority"],
            "route_lanelet_ids": [100, 443, 81],
            "controlled_lanelet_ids": [443],
            "regulatory_element_id": 1346,
            "physical_light_ids": [1412, 1414, 1416],
            "bulb_ids": [70101, 69969, 70219],
            "stop_line_id": 1439,
            "stop_line_geometry_sha256": _sha(74),
            "route_graph_sha256": _sha(75),
            "signal_chain_sha256": _sha(76),
            "runtime_receipt_sha256": _sha(77),
            "phase_authority_mode": "observe_same_tick_request",
            "current_phase": "green",
            "source_valid": True,
            "future_schedule_consumed": False,
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
        },
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def test_manifest_is_one_nonholdout_static14d_unit_and_rejects_extra_paths() -> None:
    manifest = _manifest()
    assert validate_development_smoke_manifest(manifest) == manifest
    assert manifest["evidence_role"] == EVIDENCE_ROLE
    assert manifest["state_count"] == 1
    assert manifest["operational_arm"] == SMOKE_ARM

    holdout = copy.deepcopy(manifest)
    holdout["state"]["split"] = "holdout"
    holdout["state"]["holdout"] = True
    with pytest.raises(ValueError, match="rejects holdout"):
        validate_development_smoke_manifest(holdout)

    extra_forward = copy.deepcopy(manifest)
    extra_forward["production_surface_manifest"]["execution_options"]["evaluate_all_arms"] = True
    with pytest.raises(ValueError, match="one operational arm"):
        validate_development_smoke_manifest(extra_forward)

    wrong_arm = copy.deepcopy(manifest)
    wrong_arm["operational_arm"] = "Scene14D"
    with pytest.raises(ValueError, match="Static14D"):
        validate_development_smoke_manifest(wrong_arm)


def test_completed_receipt_binds_one_b8_pool_candidate0_and_simulator_row() -> None:
    receipt = build_development_smoke_receipt(
        manifest=_manifest(), unit=_completed_unit()
    )
    assert validate_development_smoke_receipt(receipt) == receipt
    assert receipt["denominator"] == {"planned": 1, "complete": 1, "failed": 0, "unattempted": 0}
    unit = receipt["unit"]
    assert unit["candidate_pool"]["candidate0"]["index"] == 0
    assert unit["forward_calls"]["primary_forward_count"] == 1
    assert unit["forward_calls"]["post_pool_dp_forward_count"] == 0
    assert unit["signal_authority"]["binding"] == receipt["manifest"]["signal_authority"]
    assert unit["selection"]["selected_row_sha256"] == unit["simulator"]["selected_row_sha256"]
    assert not {"support", "ood", "stability", "safety", "claim"} & set(receipt)

    bad = copy.deepcopy(receipt)
    bad["unit"]["candidate_pool"]["candidate0"]["default_output_sha256"] = _sha(99)
    with pytest.raises(ValueError, match="default output"):
        validate_development_smoke_receipt(bad)
    bad = copy.deepcopy(receipt)
    bad["unit"]["forward_calls"]["sequential_forward_count"] = 1
    with pytest.raises(ValueError, match="extra or post-pool"):
        validate_development_smoke_receipt(bad)


def test_typed_failure_keeps_one_unit_denominator_without_action_claim() -> None:
    failed = _completed_unit()
    failed.pop("signal_authority")
    failed["selection"] = None
    failed["simulator"] = None
    failed["terminal"] = {
        "status": "typed_failure",
        "failure_class": "RuntimeError",
        "failure_reason": "selector unavailable",
    }
    failed["forward_calls"]["model_call_count_after"] = 1
    failed["forward_calls"]["model_call_delta"] = 1
    receipt = build_development_smoke_receipt(manifest=_manifest(), unit=failed)
    assert receipt["denominator"] == {"planned": 1, "complete": 0, "failed": 1, "unattempted": 0}
    assert receipt["unit"]["selection"] is None
    assert receipt["unit"]["simulator"] is None


def test_runner_projects_actual_v26_tick_binding_into_one_unit_ledger() -> None:
    rows = [_sha(20 + index) for index in range(8)]
    v26_tick = build_target_bounded_tick_receipt(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options={
            "adaptation_diagnostics": False,
            "sequential_forward_enabled": False,
            "replay_extra_forward_enabled": False,
            "guidance_policy": "disabled",
            "evaluate_all_arms": False,
        },
        operational_arm=SMOKE_ARM,
        tick_index=0,
        state_sha256=_sha(9),
        candidate_pool_sha256_before=_sha(13),
        candidate_pool_sha256_after=_sha(13),
        primary_forward_count=1,
        sequential_forward_count=0,
        zero_call_receipt={
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        selector_receipt={
            "status": "ok",
            "selected_index": 2,
            "selected_row_sha256": rows[2],
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "margin_best_vs_runner_up": 0.1,
            "exact_tie_set": [2],
        },
        simulator_selected_row_sha256=rows[2],
        materialization_phase_receipt=materialization_phase_receipt_not_available(),
    )
    raw = {
        "v26_production_surface_receipt": v26_tick,
        "candidate_row_sha256": rows,
        "state_sha256": _sha(9),
        "source_input_sha256": _sha(10),
        "input_sha256": _sha(11),
        "latent_seed": 19,
        "latent_shape": [8, 321, 81, 4],
        "latent_dtype": "float32",
        "latent_tensor_sha256": _sha(12),
        "latent_row_sha256": [_sha(40 + index) for index in range(8)],
        "candidate_tensor_sha256_after": _sha(13),
        "default_output_sha256": rows[0],
    }
    raw["same_ego_batch_metadata"] = {
        "same_ego_batch_size": 8,
        "nonlatent_rows_identical": True,
        "tensor_metadata": _completed_unit()["input"]["tensor_metadata"],
    }
    raw["controlled_scene"] = {
        "signal_authority": _completed_unit()["signal_authority"],
    }
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    unit = runner._completed_unit(
        raw,
        SimpleNamespace(
            primary_candidates=[np.zeros((8, 80, 4), dtype=np.float32)],
            model_call_count=1,
        ),
    )
    receipt = build_development_smoke_receipt(manifest=_manifest(), unit=unit)
    assert receipt["unit"]["selection"]["selected_row_sha256"] == rows[2]
    assert receipt["unit"]["simulator"]["selected_row_sha256"] == rows[2]


def test_cli_has_one_explicit_static_arm_and_rejects_legacy_flags() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    args = runner.parse_args(
        [
            "--output-dir", "out",
            "--worker-lock", "worker.lock",
            "--probe-config", "probe.json",
            "--training", "training",
            "--training-root", _sha(1),
            "--training-review", "review",
            "--training-review-root", _sha(2),
            "--fixed-dp-repo", "fixed-dp",
            "--arm", "Static14D",
        ]
    )
    assert args.arm == SMOKE_ARM
    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--output-dir", "out",
                "--worker-lock", "worker.lock",
                "--probe-config", "probe.json",
                "--training", "training",
                "--training-root", _sha(1),
                "--training-review", "review",
                "--training-review-root", _sha(2),
                "--fixed-dp-repo", "fixed-dp",
                "--arm", "Static14D",
                "--legacy-preflight",
            ]
        )
    source = Path(runner.__file__).read_text(encoding="utf-8")
    for literal in (
        "max_ticks=1",
        "operational_arm=SMOKE_ARM",
        "evaluate_all_arms=False",
        "adaptation_diagnostics=False",
        "production_surface_id=PRODUCTION_SURFACE_ID",
    ):
        assert literal in source
    assert "preflight(" not in source
    assert "evaluate(" not in source


def test_runner_accepts_only_the_explicit_development_nonholdout_role() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    assert callable(runner.array_sha256)
    config = {
        "protocol": {
            "holdout_access_authorized": False,
            "route_role": "development_nonholdout",
        },
        "routes": [{"path": "/route", "sha256": _sha(1)}],
        "seeds": {"scenario": 17},
        "fixed_dp": {
            "checkpoint": {"path": "/checkpoint", "sha256": _sha(2)},
            "args_json": {"path": "/args", "sha256": _sha(3)},
        },
    }
    assert runner._require_single_nonholdout_config(config) == config
    holdout = copy.deepcopy(config)
    holdout["protocol"]["route_role"] = "holdout"
    with pytest.raises(ValueError, match="development_nonholdout"):
        runner._require_single_nonholdout_config(holdout)


def test_prepare_manifest_loads_scene_runtime_selector_assets_without_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    scene_runtime = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v25_scene_runtime"
    )

    def write_bound_file(name: str, payload: bytes) -> dict[str, str]:
        path = tmp_path / name
        path.write_bytes(payload)
        return {
            "path": str(path),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    route = write_bound_file("route.pkl", b"route")
    map_binding = write_bound_file("map.osm", b"map")
    checkpoint = write_bound_file("model.pth", b"checkpoint")
    args_json = write_bound_file("args.json", b"{}")
    config_path = tmp_path / "probe.json"
    config_path.write_text(
        json.dumps(
            {
                "protocol": {
                    "holdout_access_authorized": False,
                    "route_role": "development_nonholdout",
                },
                "routes": [{"name": "development", **route}],
                "map": map_binding,
                "seeds": {"scenario": 17},
                "spawn_config": {"seed": 17},
                "fixed_dp": {"checkpoint": checkpoint, "args_json": args_json},
            }
        ),
        encoding="utf-8",
    )
    training = tmp_path / "training"
    training_review = tmp_path / "training_review"
    training.mkdir()
    training_review.mkdir()
    loaded: dict[str, object] = {}
    fake_assets = SimpleNamespace(
        atom_scales=np.arange(1, 15, dtype=np.float64),
        static14d_weights=np.full(14, 1.0 / 14.0, dtype=np.float64),
    )
    signal_binding = {
        "schema_version": "camp_dp_v26_autoware_sidecar_binding_v1",
        "route_sha256": route["sha256"],
        "map_sha256": map_binding["sha256"],
        "geometry_copy_sha256": map_binding["sha256"],
        "sidecar_index_sha256": _sha(62),
        "sidecar_manifest_sha256": _sha(63),
        "sidecar_source_sha256": _sha(64),
    }

    def fake_loader(**kwargs: object) -> SimpleNamespace:
        loaded.update(kwargs)
        return fake_assets

    monkeypatch.setattr(runner, "_tracked_changes", lambda _path: False)
    monkeypatch.setattr(
        runner,
        "_git_head",
        lambda _path: "7a1d33da277a1992ec474b5383a0c963c72e04e4",
    )
    monkeypatch.setattr(
        scene_runtime, "load_v25_runtime_selector_assets", fake_loader
    )
    monkeypatch.setattr(
        runner, "load_autoware_sidecar_binding", lambda _config: (signal_binding, {})
    )
    manifest, prepared_config, assets = runner._prepare_manifest(
        argparse.Namespace(
            probe_config=config_path,
            training=training,
            training_root=_sha(60),
            training_review=training_review,
            training_review_root=_sha(61),
            fixed_dp_repo=tmp_path / "fixed_dp",
        )
    )
    assert assets is fake_assets
    assert prepared_config["protocol"]["route_role"] == "development_nonholdout"
    assert manifest["signal_authority"] == signal_binding
    assert manifest["selector"]["training_root_sha256"] == _sha(60)
    assert loaded == {
        "training_artifact": training.resolve(),
        "training_root_sha256": _sha(60),
        "training_review_artifact": training_review.resolve(),
        "training_review_root_sha256": _sha(61),
    }


def test_same_ego_batch_metadata_requires_identical_nonlatent_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResult:
        def __init__(self, value: bool) -> None:
            self.value = value

        def all(self) -> "FakeResult":
            return self

        def item(self) -> bool:
            return self.value

    class FakeTensor:
        def __init__(self, shape: tuple[int, ...], *, rows_equal: bool = True) -> None:
            self.shape = shape
            self.ndim = len(shape)
            self.dtype = "torch.float32"
            self.rows_equal = rows_equal

        def is_floating_point(self) -> bool:
            return True

        def is_complex(self) -> bool:
            return False

        def __getitem__(self, _index: object) -> "FakeTensor":
            return self

        def expand_as(self, _other: "FakeTensor") -> "FakeTensor":
            return self

    class FakeTorch:
        @staticmethod
        def isfinite(_value: FakeTensor) -> FakeResult:
            return FakeResult(True)

        @staticmethod
        def equal(value: FakeTensor, _other: FakeTensor) -> bool:
            return value.rows_equal

    monkeypatch.setitem(sys.modules, "torch", FakeTorch())
    fair = importlib.import_module(
        "scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout"
    )
    metadata = fair._same_ego_batch_metadata(
        {
            "history": FakeTensor((8, 31, 11)),
            "sampled_trajectories": FakeTensor((8, 2)),
        }
    )
    assert metadata["same_ego_batch_size"] == 8
    assert metadata["nonlatent_rows_identical"] is True
    assert metadata["tensor_metadata"]["history"]["finite"] is True

    with pytest.raises(ValueError, match="nonlatent input rows drifted"):
        fair._same_ego_batch_metadata(
            {
                "history": FakeTensor((8, 31, 11), rows_equal=False),
                "sampled_trajectories": FakeTensor((8, 2)),
            }
        )
