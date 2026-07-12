from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    paired_run_key,
)
from scripts.integrations import (
    run_diffusion_planner_dp_camp_v19_closed_loop_smoke as smoke,
)


def _scenario(bucket: str, token: str, log: str) -> dict[str, object]:
    return {
        "bucket": bucket,
        "db_path": f"/data/{log}.db",
        "future_span_s": 8.1,
        "location": "sg-one-north",
        "log_token": token[::-1],
        "logfile": log,
        "map_version": "sg-one-north",
        "past_span_s": 3.1,
        "route_roadblock_count": 2,
        "scenario_token": token,
        "scene_name": f"scene-{bucket}",
        "scene_token": token + "-scene",
        "selection_sha256": "a" * 64,
        "selection_tag": "medium_magnitude_speed",
        "tags": ["medium_magnitude_speed"],
        "timestamp_us": 1_633_505_429_350_455,
    }


def _config() -> dict[str, object]:
    return {
        "schema_version": "dp_camp_v19_closed_loop_smoke_config_v1",
        "simulation_mode": "closed_loop_nonreactive_agents",
        "source_scope": "existing_nuplan_mini",
        "claim_scope": "two-scenario nonreactive existing-data smoke only",
        "selected_scenario_count": 2,
        "selected_distinct_logs": True,
        "zero_log_overlap": True,
        "zero_scene_overlap": True,
        "selected_scenarios": [
            _scenario("normal", "scenario-normal", "log-normal"),
            _scenario("interaction", "scenario-interaction", "log-interaction"),
        ],
        "seeds": {
            "scenario": 3411,
            "dp_tick_root": 3412,
            "bootstrap": 3410,
            "forbidden": [11, 12, 13],
        },
        "simulation_history_buffer_duration_s": 3.0,
        "primary_metric": {
            "name": "SafetyCost v1",
            "lower_is_better": True,
            "protocol_sha256": smoke.SAFETY_COST_PROTOCOL_SHA256,
            "required_components": list(smoke.SAFETY_COST_COMPONENTS),
        },
        "arms": {
            "baseline": {
                "arm": "dp_default",
                "baseline_name": "DP-default deterministic/MAP baseline",
                "native_ranked_top1": False,
                "worker_operation": "plan_tick",
            },
            "camp": {
                "arm": "camp",
                "k": 8,
                "noise_scale": 1.0,
                "worker_operation": "plan_tick",
            },
        },
    }


def test_validate_config_freezes_two_unseen_scenarios_and_nonformal_seeds() -> None:
    config = smoke.validate_smoke_config(_config())

    assert [row["bucket"] for row in config["selected_scenarios"]] == [
        "normal",
        "interaction",
    ]
    assert config["arms"]["baseline"]["native_ranked_top1"] is False

    invalid = _config()
    invalid["seeds"]["scenario"] = 11
    with pytest.raises(ValueError, match="formal seed"):
        smoke.validate_smoke_config(invalid)


def test_construct_scenario_uses_official_map_version(monkeypatch) -> None:
    captured = {}
    vehicle = ModuleType("nuplan.common.actor_state.vehicle_parameters")
    vehicle.get_pacifica_parameters = lambda: object()
    scenario = ModuleType(
        "nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario"
    )
    scenario.NuPlanScenario = lambda **kwargs: captured.update(kwargs) or object()
    utils = ModuleType(
        "nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario_utils"
    )
    utils.ScenarioExtractionInfo = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, vehicle.__name__, vehicle)
    monkeypatch.setitem(sys.modules, scenario.__name__, scenario)
    monkeypatch.setitem(sys.modules, utils.__name__, utils)
    record = _scenario("normal", "scenario-normal", "log-normal")
    record["location"] = "las_vegas"
    record["map_version"] = "us-nv-las-vegas-strip"

    smoke.construct_nuplan_scenario(record, data_root="/data", map_root="/maps")

    assert captured["map_name"] == "us-nv-las-vegas-strip"

    invalid = _config()
    invalid["zero_log_overlap"] = False
    with pytest.raises(ValueError, match="zero overlap"):
        smoke.validate_smoke_config(invalid)


def test_pair_plan_uses_identical_pair_identity_and_separate_arm_roots(
    tmp_path: Path,
) -> None:
    rows = smoke.build_paired_run_plan(_config(), tmp_path)

    assert len(rows) == 4
    for scenario_token in ("scenario-normal", "scenario-interaction"):
        pair = [row for row in rows if row["scenario_token"] == scenario_token]
        assert [row["arm"] for row in pair] == ["dp_default", "camp"]
        assert pair[0]["pair_run_key"] == pair[1]["pair_run_key"]
        assert pair[0]["arm_root"] != pair[1]["arm_root"]
        assert Path(pair[0]["arm_root"]).parent == Path(pair[1]["arm_root"]).parent
        expected = paired_run_key(pair[0]["logfile"], scenario_token, 3411)
        assert pair[0]["pair_run_key"] == expected


def test_safety_cost_v1_matches_frozen_formula_and_fails_closed() -> None:
    components = {
        "obb_collision_rate": 0.1,
        "near_miss_rate": 0.2,
        "lane_violation_rate": 0.3,
        "red_light_violation_rate": 0.4,
        "planned_red_light_violation_rate": 0.5,
        "mean_jerk_magnitude_mps3": 12.0,
        "mean_lateral_acceleration_mps2": 5.0,
        "route_completion_rate": 0.75,
    }

    assert smoke.compute_safety_cost_v1(components) == pytest.approx(
        10 + 2 + 6 + 12 + 7.5 + 1.2 + 5 + 0.5
    )

    missing = dict(components)
    del missing["near_miss_rate"]
    with pytest.raises(ValueError, match="missing SafetyCost"):
        smoke.compute_safety_cost_v1(missing)

    nonfinite = dict(components, mean_jerk_magnitude_mps3=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        smoke.compute_safety_cost_v1(nonfinite)


def test_execute_arm_retains_history_metrics_bridge_and_no_cross_arm_result(
    tmp_path: Path, monkeypatch,
) -> None:
    pair_key = "b" * 64
    history = SimpleNamespace(data=[SimpleNamespace(iteration=SimpleNamespace(index=0))])
    arm_root = tmp_path / pair_key / "dp_default"

    def run():
        tick = arm_root / "000000"
        tick.mkdir()
        (tick / "planning_receipt.json").write_text(
            json.dumps(
                {
                    "iteration_index": 0,
                    "latency_ms": {name: 0.0 for name in smoke.LATENCY_FIELDS},
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(succeeded=True, error_message=None)

    runner = SimpleNamespace(run=run)
    simulation = SimpleNamespace(history=history)
    metric_engine = SimpleNamespace(
        compute_metric_results=lambda actual_history, scenario: {
            "metric": [SimpleNamespace(metric_computator="metric", statistics=[])]
        }
    )
    monkeypatch.setattr(
        smoke,
        "materialize_closed_loop_evidence",
        lambda _history, _scenario, receipts: {
            "obb_collision_rate": 0.0,
            "near_miss_rate": 0.0,
            "lane_violation_rate": 0.0,
            "red_light_violation_rate": 0.0,
            "planned_red_light_violation_rate": 0.0,
            "mean_jerk_magnitude_mps3": 0.0,
            "mean_lateral_acceleration_mps2": 0.0,
            "route_completion_rate": 1.0,
        },
    )

    result = smoke.execute_arm(
        arm="dp_default",
        pair_run_key_value=pair_key,
        arm_root=arm_root,
        scenario=SimpleNamespace(token="scenario"),
        simulation=simulation,
        runner=runner,
        metric_engine=metric_engine,
        planner_name="DP-default deterministic/MAP baseline",
    )

    assert result["arm"] == "dp_default"
    assert result["pair_run_key"] == pair_key
    assert result["safety_cost_v1"] == 0.0
    assert tuple(result["latency_ms"]) == smoke.LATENCY_FIELDS
    assert (arm_root / "history.json").is_file()
    assert (arm_root / "official_metrics.json").is_file()
    assert (arm_root / "result.json").is_file()
    assert json.loads((arm_root / "result.json").read_text("utf-8"))["arm"] == (
        "dp_default"
    )

    with pytest.raises(ValueError, match="arm root"):
        smoke.execute_arm(
            arm="camp",
            pair_run_key_value=pair_key,
            arm_root=arm_root,
            scenario=SimpleNamespace(token="scenario"),
            simulation=simulation,
            runner=runner,
            metric_engine=metric_engine,
            planner_name="CAMP fixed-DP K=8 selector",
        )


def test_execute_arm_preserves_failure_evidence(tmp_path: Path) -> None:
    pair_key = "c" * 64
    arm_root = tmp_path / pair_key / "camp"
    runner = SimpleNamespace(
        run=lambda: SimpleNamespace(succeeded=False, error_message="all K infeasible")
    )

    with pytest.raises(RuntimeError, match="all K infeasible"):
        smoke.execute_arm(
            arm="camp",
            pair_run_key_value=pair_key,
            arm_root=arm_root,
            scenario=SimpleNamespace(token="scenario"),
            simulation=SimpleNamespace(history=[]),
            runner=runner,
            metric_engine=SimpleNamespace(),
            planner_name="CAMP fixed-DP K=8 selector",
        )

    failure = json.loads((arm_root / "failure.json").read_text("utf-8"))
    assert failure["arm"] == "camp"
    assert failure["error_type"] == "RuntimeError"
    assert failure["error"] == "scenario arm failed: all K infeasible"
