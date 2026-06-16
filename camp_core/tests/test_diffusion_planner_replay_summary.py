from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_camp_replay import (
    merge_existing_summary,
    merge_replay_metadata,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    _candidate_generation_contract,
    _configure_candidate_guidance,
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
        reference_blend_steps=None,
    )

    assert contract["schema_version"] == "dp_candidate_generation_contract_v1"
    assert contract["model_type"] == "x_start"
    assert contract["latent_shape"] == [16, 321, 81, 4]
    assert contract["latent_distribution"] == "standard_normal_scaled"
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
        reference_blend_steps=5,
        guidance=guidance,
    )

    assert contract["guidance_enabled"]
    assert contract["guidance_policy"] == (
        "preserve_official_dp_guidance_for_candidate_generation"
    )
    assert contract["guidance"]["config_sha256"] == "abc"
    assert contract["guidance"]["active_function_names"] == ["route_following"]
    assert contract["reference_blend_steps"] == 5
    assert contract["changes_candidate_set"]
    assert not contract["changes_camp_score"]


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
