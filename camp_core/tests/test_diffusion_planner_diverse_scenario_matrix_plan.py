from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_diverse_scenario_matrix import (
    build_plan,
    main,
)


def _oracle_payload() -> dict[str, object]:
    return {
        "coverage_gaps": {
            "required_buckets": [
                "normal",
                "traffic_light",
                "red_light_turn",
                "sharp_turn",
                "npc_interaction",
                "dense_scene",
                "lane_change_or_merge",
            ],
            "missing_required_buckets": [
                "npc_interaction",
                "dense_scene",
                "lane_change_or_merge",
            ],
        },
        "opportunity_gate": {"passed": False},
        "overall": {
            "run_level_delta_ci": {
                "hard_guarded_oracle_minus_top1": {"ci95_high": -0.4}
            }
        },
    }


def _plan(
    *,
    seeds: list[int] | None = None,
    route_buckets: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    return build_plan(
        oracle_json=_oracle_payload(),
        routes={
            "sample_normal": Path("/routes/sample_normal.pkl"),
            "sample_tl_turn": Path("/routes/sample_tl_turn.pkl"),
            "lane_change": Path("/routes/lane_change.pkl"),
        },
        route_buckets=route_buckets
        or {
            "sample_normal": ["normal", "npc_interaction", "dense_scene"],
            "sample_tl_turn": ["traffic_light", "red_light_turn", "sharp_turn"],
            "lane_change": ["lane_change_or_merge"],
        },
        output_root=Path("/out/diverse"),
        output_manifest=Path("/out/diverse/scenario_buckets.json"),
        diffusion_repo=Path("/dp"),
        map_path="/maps/lanelet2_map.osm",
        model_path=Path("/assets/diffusion_planner.pth"),
        model_args=Path("/assets/diffusion_planner.param.json"),
        config=Path("/dp/scenario_generation/configs/replay_default.json"),
        reward_config=Path("configs/integrations/dp_camp_reward_eval.json"),
        camp_atom_scales=Path("/assets/redstop/atom_scales_dp_static.json"),
        camp_static_weights=Path("/assets/redstop/offline_weights_dp_static.npy"),
        device="cuda",
        steps=200,
        seeds=seeds or [1, 2],
        max_npcs=[0, 8],
        spawn_probabilities=[0.3, 0.6],
        traffic_light_modes=["off", "on"],
    )


def test_diverse_matrix_plan_builds_manifest_and_static_label_command() -> None:
    report = _plan()
    manifest = report["scenario_bucket_manifest"]
    argv = report["command"]["argv"]

    assert report["summary"]["missing_required_buckets"] == []
    assert report["decision"] == "approved_nonformal_plan_only"
    assert manifest["routes"]["sample_tl_turn"] == ["sharp_turn"]
    assert manifest["routes"]["lane_change"] == ["lane_change_or_merge"]
    filters = {entry["name"]: entry for entry in manifest["filters"]}
    assert filters["sample_tl_turn_traffic_light_on"]["buckets"] == [
        "traffic_light",
        "red_light_turn",
    ]
    assert filters["sample_normal_normal_no_tl_no_npc"]["buckets"] == ["normal"]
    assert filters["sample_normal_npc_stress"]["buckets"] == [
        "npc_interaction",
        "dense_scene",
    ]
    assert report["summary"]["bucket_counts"]["lane_change_or_merge"] > 0
    assert "--camp_collect_closed_loop_outcomes" in argv
    assert argv[argv.index("--variants") + 1] == "static"
    assert "--skip_compare" in argv
    assert "--scenario_bucket_manifest" in argv


def test_diverse_matrix_plan_reports_missing_lane_change_bucket() -> None:
    report = _plan(
        route_buckets={
            "sample_normal": ["normal", "npc_interaction", "dense_scene"],
            "sample_tl_turn": ["traffic_light", "red_light_turn", "sharp_turn"],
        }
    )

    assert report["decision"] == "blocked_plan_only"
    assert report["summary"]["missing_required_buckets"] == [
        "lane_change_or_merge"
    ]
    assert report["blockers"] == [
        "missing required planned scenario buckets: lane_change_or_merge"
    ]


def test_diverse_matrix_plan_rejects_formal_seed() -> None:
    with pytest.raises(ValueError, match="formal seeds"):
        _plan(seeds=[11])


def test_diverse_matrix_plan_cli_writes_plan_and_manifest(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle_path = tmp_path / "oracle.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_manifest = tmp_path / "scenario_buckets.json"
    oracle_path.write_text(json.dumps(_oracle_payload()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_diverse_scenario_matrix.py",
            "--oracle_json",
            str(oracle_path),
            "--route",
            "sample_normal=/routes/sample_normal.pkl",
            "--route",
            "sample_tl_turn=/routes/sample_tl_turn.pkl",
            "--route",
            "lane_change=/routes/lane_change.pkl",
            "--route_bucket",
            "sample_normal=normal,npc_interaction,dense_scene",
            "--route_bucket",
            "sample_tl_turn=traffic_light,red_light_turn,sharp_turn",
            "--route_bucket",
            "lane_change=lane_change_or_merge",
            "--output_root",
            "/out/diverse",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_manifest",
            str(output_manifest),
            "--diffusion_repo",
            "/dp",
            "--map_path",
            "/maps/lanelet2_map.osm",
            "--model_path",
            "/assets/diffusion_planner.pth",
            "--model_args",
            "/assets/diffusion_planner.param.json",
            "--config",
            "/dp/scenario_generation/configs/replay_default.json",
            "--reward_config",
            "configs/integrations/dp_camp_reward_eval.json",
            "--camp_atom_scales",
            "/assets/redstop/atom_scales_dp_static.json",
            "--camp_static_weights",
            "/assets/redstop/offline_weights_dp_static.npy",
            "--seeds",
            "1,2",
            "--max_npcs",
            "0,8",
            "--spawn_probabilities",
            "0.3,0.6",
            "--traffic_light_modes",
            "off,on",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
    assert payload["decision"] == "approved_nonformal_plan_only"
    assert manifest["routes"]["lane_change"] == ["lane_change_or_merge"]
    assert "Diverse Non-Formal Matrix Plan" in output_md.read_text(
        encoding="utf-8"
    )
