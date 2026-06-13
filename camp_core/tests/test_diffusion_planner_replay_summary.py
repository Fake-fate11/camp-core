from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_camp_replay import (
    merge_replay_metadata,
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
        "camp_shadow_dp_prior_comfort_excess": {
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
    assert merged["camp_shadow_dp_prior_comfort_excess"][
        "effective_horizon_steps"
    ] == 30
    assert merged["benchmark"]["seed"] == 101
