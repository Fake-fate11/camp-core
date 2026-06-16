from __future__ import annotations

import json
import sys
import types

import numpy as np
import pytest

from scripts.integrations.summarize_diffusion_planner_camp_replay import (
    merge_existing_summary,
    merge_replay_metadata,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    _candidate_generation_contract,
    _configure_candidate_guidance,
    _lower_union_red_donor_indices,
    _raw_candidate_prefix_payload,
    _summarize_splice_shadow_rule_records,
)


def test_replay_summary_metadata_survives_metric_resummarization() -> None:
    metric_summary = {
        "selection_steps": 3,
        "advance_mode": None,
        "camp_feasibility_source": None,
    }
    replay_summary = {
        "advance_mode": "perfect",
        "camp_feasibility_source": "dp_reward",
        "camp_outcome_horizon_steps": 30,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "guidance_enabled": False,
        },
        "camp_microbenchmark_snapshots": {
            "enabled": True,
            "selection_effect": False,
            "latency_evidence": False,
            "requested_steps": [0, 1],
            "files": ["camp_microbenchmark_step_0000.npz"],
        },
        "camp_raw_candidate_prefix_logging": {
            "enabled": True,
            "selection_effect": False,
            "steps": 10,
            "field": "candidate_raw_trajectory_prefix",
        },
        "camp_splice_shadow_rule": {
            "enabled": True,
            "selection_effect": False,
            "online_selector_change": False,
            "changed_records": 2,
        },
        "camp_shadow_dp_prior_comfort_excess": {
            "enabled": True,
            "selection_effect": False,
            "effective_horizon_steps": 30,
        },
        "camp_shadow_lateral_comfort": {
            "enabled": True,
            "selection_effect": False,
            "effective_horizon_steps": 30,
        },
        "benchmark": {"seed": 101},
    }

    merged = merge_replay_metadata(metric_summary, replay_summary)

    assert merged["selection_steps"] == 3
    assert merged["advance_mode"] == "perfect"
    assert merged["camp_feasibility_source"] == "dp_reward"
    assert merged["camp_outcome_horizon_steps"] == 30
    assert merged["candidate_generation_contract"]["schema_version"] == (
        "dp_candidate_generation_contract_v1"
    )
    assert not merged["candidate_generation_contract"]["guidance_enabled"]
    assert merged["camp_microbenchmark_snapshots"]["requested_steps"] == [0, 1]
    assert not merged["camp_microbenchmark_snapshots"]["selection_effect"]
    assert merged["camp_raw_candidate_prefix_logging"]["steps"] == 10
    assert not merged["camp_raw_candidate_prefix_logging"]["selection_effect"]
    assert merged["camp_splice_shadow_rule"]["changed_records"] == 2
    assert not merged["camp_splice_shadow_rule"]["selection_effect"]
    assert merged["camp_shadow_dp_prior_comfort_excess"][
        "effective_horizon_steps"
    ] == 30
    assert merged["camp_shadow_lateral_comfort"][
        "effective_horizon_steps"
    ] == 30
    assert merged["benchmark"]["seed"] == 101


def test_existing_summary_metrics_survive_partial_resummarization() -> None:
    existing_summary = {
        "route_completion_rate": 0.42,
        "route_progress_m": 123.0,
        "p95_selection_latency_ms": 95.0,
    }
    recomputed_summary = {
        "selection_steps": 3,
        "p95_selection_latency_ms": 90.0,
        "route_completion_rate": None,
    }

    merged = merge_existing_summary(existing_summary, recomputed_summary)

    assert merged["selection_steps"] == 3
    assert merged["p95_selection_latency_ms"] == 90.0
    assert merged["route_completion_rate"] == 0.42
    assert merged["route_progress_m"] == 123.0


def test_candidate_generation_contract_records_fixed_dp_sampling_boundary() -> None:
    class _Args:
        future_len = 80
        predicted_neighbor_num = 320
        diffusion_model_type = "x_start"

    contract = _candidate_generation_contract(
        _Args(),
        num_candidates=16,
        noise_scale=0.75,
        noise_strategy="iid",
        reference_blend_steps=None,
    )

    assert contract["schema_version"] == "dp_candidate_generation_contract_v1"
    assert contract["model_type"] == "x_start"
    assert contract["latent_shape"] == [16, 321, 81, 4]
    assert contract["latent_distribution"] == "standard_normal_scaled"
    assert contract["noise_strategy"] == "iid"
    assert contract["latent_pairing"] == (
        "independent iid draws after deterministic candidate 0"
    )
    assert contract["noise_scale"] == 0.75
    assert contract["deterministic_first"]
    assert contract["candidate0_latent"] == "zeros"
    assert contract["random_seed_scope"] == "process_global_torch_rng"
    assert contract["recorded_tick_seed"] is None
    assert not contract["guidance_enabled"]
    assert contract["guidance_policy"] == (
        "disabled_for_camp_candidate_generation"
    )
    assert contract["guidance"]["enabled"] is False
    assert contract["guidance"]["functions"] == []
    assert contract["dpm_solver_steps"] == 10
    assert contract["dpm_skip_type"] == "logSNR"
    assert contract["changes_candidate_set"]
    assert not contract["changes_camp_score"]
    assert not contract["changes_diffusion_planner_weights"]


def test_candidate_generation_contract_records_enabled_guidance() -> None:
    class _Args:
        future_len = 80
        predicted_neighbor_num = 320
        diffusion_model_type = "x_start"

    guidance = {
        "enabled": True,
        "policy": "preserve_official_dp_guidance_for_candidate_generation",
        "config_path": "/tmp/guidance.json",
        "config_sha256": "abc",
        "functions": [{"name": "route_following", "enabled": True}],
        "active_function_names": ["route_following"],
        "guidance_scale": 0.25,
    }
    contract = _candidate_generation_contract(
        _Args(),
        num_candidates=8,
        noise_scale=1.0,
        noise_strategy="antithetic",
        reference_blend_steps=5,
        guidance=guidance,
    )

    assert contract["guidance_enabled"]
    assert contract["guidance_policy"] == (
        "preserve_official_dp_guidance_for_candidate_generation"
    )
    assert contract["guidance"]["config_sha256"] == "abc"
    assert contract["guidance"]["active_function_names"] == ["route_following"]
    assert contract["noise_strategy"] == "antithetic"
    assert "+z/-z antithetic pairs" in contract["latent_pairing"]
    assert contract["reference_blend_steps"] == 5
    assert contract["changes_candidate_set"]
    assert not contract["changes_camp_score"]


def test_raw_candidate_prefix_payload_is_disabled_by_default() -> None:
    candidates = np.zeros((2, 3, 4), dtype=np.float64)

    assert _raw_candidate_prefix_payload(candidates, 0) == {}


def test_raw_candidate_prefix_payload_records_requested_prefix() -> None:
    candidates = np.arange(2 * 3 * 4, dtype=np.float64).reshape(2, 3, 4)

    payload = _raw_candidate_prefix_payload(candidates, 2)

    assert payload["candidate_raw_trajectory_prefix_steps"] == 2
    assert payload["candidate_raw_trajectory_prefix"] == (
        candidates[:, :2, :].tolist()
    )


def test_raw_candidate_prefix_payload_clamps_to_horizon() -> None:
    candidates = np.arange(2 * 3 * 4, dtype=np.float64).reshape(2, 3, 4)

    payload = _raw_candidate_prefix_payload(candidates, 10)

    assert payload["candidate_raw_trajectory_prefix_steps"] == 3
    assert payload["candidate_raw_trajectory_prefix"] == candidates.tolist()


def test_raw_candidate_prefix_payload_rejects_wrong_rank() -> None:
    candidates = np.zeros((3, 4), dtype=np.float64)

    with pytest.raises(ValueError, match="rank-3"):
        _raw_candidate_prefix_payload(candidates, 2)


def test_raw_candidate_prefix_payload_rejects_negative_steps() -> None:
    candidates = np.zeros((2, 3, 4), dtype=np.float64)

    with pytest.raises(ValueError, match="non-negative"):
        _raw_candidate_prefix_payload(candidates, -1)


def test_lower_union_red_donor_indices_excludes_selected_and_higher_risk() -> None:
    donors = _lower_union_red_donor_indices(
        np.array([5.0, 2.0, 5.0, 4.0]),
        selected_index=0,
    )

    np.testing.assert_array_equal(donors, np.array([1, 3], dtype=np.int64))


def test_summarize_splice_shadow_rule_records_reports_default_off_state() -> None:
    summary = _summarize_splice_shadow_rule_records(
        [
            {
                "splice_shadow_rule": {
                    "changed": True,
                    "admissible_count": 3,
                    "reason": "budget_admissible_lower_red_candidate",
                    "chosen_union_red": 0.0,
                    "chosen_progress_loss_m": 0.8,
                    "chosen_smoothness_loss": 0.1,
                },
                "latency_ms_splice_shadow_rule": 2.5,
            },
            {
                "splice_shadow_rule": {
                    "changed": False,
                    "admissible_count": 0,
                    "reason": "no_budget_admissible_lower_red_candidate",
                    "chosen_union_red": None,
                    "chosen_progress_loss_m": None,
                    "chosen_smoothness_loss": None,
                },
                "latency_ms_splice_shadow_rule": 1.5,
            },
        ],
        enabled=True,
        anchor_steps=10,
        blend_steps=40,
        heading_mode="donor_offset",
        progress_loss_budget_m=1.0,
        smoothness_loss_budget=0.5,
    )

    assert summary is not None
    assert summary["enabled"] is True
    assert summary["selection_effect"] is False
    assert summary["online_selector_change"] is False
    assert summary["changed_records"] == 1
    assert summary["admissible_count"] == 3
    assert summary["reason_counts"] == {
        "budget_admissible_lower_red_candidate": 1,
        "no_budget_admissible_lower_red_candidate": 1,
    }
    assert summary["latency_ms"]["max"] == 2.5
    assert summary["chosen_union_red"]["max"] == 0.0


def test_configure_candidate_guidance_default_is_disabled() -> None:
    class _Decoder:
        _guidance_fn = object()
        _guidance_scale = 0.5

    class _Model:
        decoder = _Decoder()

    original_guidance = _Model.decoder._guidance_fn
    contract = _configure_candidate_guidance(
        _Model(),
        guidance_config_path=None,
        guidance_scale=None,
    )

    assert contract["enabled"] is False
    assert contract["policy"] == "disabled_for_camp_candidate_generation"
    assert contract["functions"] == []
    assert _Model.decoder._guidance_fn is original_guidance


def test_configure_candidate_guidance_uses_config_global_scale(
    tmp_path,
    monkeypatch,
) -> None:
    _install_fake_guidance_modules(monkeypatch)
    config_path = tmp_path / "guidance.json"
    config_path.write_text(
        json.dumps(
            {
                "global_scale": 0.2,
                "functions": [
                    {
                        "name": "route_centerline_following",
                        "enabled": True,
                        "scale": 0.5,
                        "params": {"note": "test"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    class _Decoder:
        _guidance_fn = None
        _guidance_scale = 0.9

    class _Model:
        decoder = _Decoder()

    contract = _configure_candidate_guidance(
        _Model(),
        guidance_config_path=config_path,
        guidance_scale=None,
    )

    assert contract["enabled"] is True
    assert contract["active_function_names"] == ["route_centerline_following"]
    assert contract["global_scale"] == 0.2
    assert contract["guidance_scale"] == 0.2
    assert contract["guidance_scale_source"] == "config_global_scale"
    assert _Model.decoder._guidance_scale == 0.2
    assert _Model.decoder._guidance_fn.set_config.global_scale == 0.2


def test_configure_candidate_guidance_cli_scale_overrides_config(
    tmp_path,
    monkeypatch,
) -> None:
    _install_fake_guidance_modules(monkeypatch)
    config_path = tmp_path / "guidance.json"
    config_path.write_text(
        json.dumps(
            {
                "global_scale": 0.2,
                "functions": [
                    {
                        "name": "route_centerline_following",
                        "enabled": True,
                        "scale": 0.5,
                        "params": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    class _Decoder:
        _guidance_fn = None
        _guidance_scale = 0.9

    class _Model:
        decoder = _Decoder()

    contract = _configure_candidate_guidance(
        _Model(),
        guidance_config_path=config_path,
        guidance_scale=0.35,
    )

    assert contract["global_scale"] == 0.2
    assert contract["guidance_scale"] == 0.35
    assert contract["guidance_scale_source"] == "cli_override"
    assert _Model.decoder._guidance_scale == 0.35


def _install_fake_guidance_modules(monkeypatch) -> None:
    class _GuidanceConfig:
        def __init__(
            self,
            *,
            name: str,
            enabled: bool = True,
            scale: float = 1.0,
            params: dict | None = None,
        ) -> None:
            self.name = name
            self.enabled = enabled
            self.scale = scale
            self.params = params or {}

    class _GuidanceSetConfig:
        def __init__(self, *, functions: list[dict], global_scale: float = 0.5):
            self.functions = [
                _GuidanceConfig(**item) if isinstance(item, dict) else item
                for item in functions
            ]
            self.global_scale = global_scale

        @classmethod
        def from_file(cls, path: str):
            with open(path, encoding="utf-8") as handle:
                return cls(**json.load(handle))

    class _GuidanceComposer:
        def __init__(self, set_config):
            self.set_config = set_config

    composer_module = types.ModuleType("diffusion_planner.model.guidance.composer")
    composer_module.GuidanceComposer = _GuidanceComposer
    config_module = types.ModuleType("diffusion_planner.model.guidance.config")
    config_module.GuidanceSetConfig = _GuidanceSetConfig

    monkeypatch.setitem(
        sys.modules,
        "diffusion_planner",
        types.ModuleType("diffusion_planner"),
    )
    monkeypatch.setitem(
        sys.modules,
        "diffusion_planner.model",
        types.ModuleType("diffusion_planner.model"),
    )
    monkeypatch.setitem(
        sys.modules,
        "diffusion_planner.model.guidance",
        types.ModuleType("diffusion_planner.model.guidance"),
    )
    monkeypatch.setitem(
        sys.modules,
        "diffusion_planner.model.guidance.composer",
        composer_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "diffusion_planner.model.guidance.config",
        config_module,
    )
