from __future__ import annotations

import json

from scripts.integrations.compare_diffusion_planner_camp_replays import (
    _apply_safety_cost_v1,
)
from scripts.integrations.relabel_diffusion_planner_safety_comparison import (
    main,
    relabel_comparison,
)


def _row(
    *,
    variant: str,
    run_key: str,
    route_name: str,
    traffic_lights: bool,
    max_npcs: int,
    jerk: float,
    lateral: float,
    contract: bool,
) -> dict[str, object]:
    row: dict[str, object] = {
        "variant": variant,
        "run_key": run_key,
        "route_name": route_name,
        "seed": 1,
        "steps": 200,
        "max_npcs": max_npcs,
        "spawn_probability": 0.3,
        "traffic_lights": traffic_lights,
        "advance_mode": "perfect",
        "route_completion_rate": 1.0,
        "obb_collision_rate": 0.0,
        "near_miss_rate": 0.0,
        "lane_violation_rate": 0.0,
        "red_light_violation_rate": 0.0,
        "planned_red_light_violation_rate": 0.0,
        "mean_jerk_magnitude_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "p95_selection_latency_ms": 80.0,
        "finite_candidate_contract_verified": contract,
        "scenario_buckets": ["overall"],
    }
    _apply_safety_cost_v1(row)
    return row


def _comparison() -> dict[str, object]:
    rows = []
    for variant, jerk, lateral, contract in (
        ("top1", 20.0, 2.0, False),
        ("camp", 10.0, 1.0, True),
    ):
        rows.append(
            _row(
                variant=variant,
                run_key="sample59-on",
                route_name="sample_map_tl_route_59_to_86",
                traffic_lights=True,
                max_npcs=4,
                jerk=jerk,
                lateral=lateral,
                contract=contract,
            )
        )
        rows.append(
            _row(
                variant=variant,
                run_key="sample2-normal",
                route_name="sample_map_route_2_to_104",
                traffic_lights=False,
                max_npcs=0,
                jerk=jerk,
                lateral=lateral,
                contract=contract,
            )
        )
    return {"baseline": "top1", "runs": rows}


def _manifest() -> dict[str, object]:
    return {
        "routes": {
            "sample_map_tl_route_59_to_86": ["sharp_turn"],
        },
        "filters": [
            {
                "name": "sample59_tl_on",
                "match": {
                    "route_name": "sample_map_tl_route_59_to_86",
                    "traffic_lights": True,
                },
                "buckets": ["traffic_light", "red_light_turn"],
            },
            {
                "name": "normal",
                "match": {
                    "route_name": "sample_map_route_2_to_104",
                    "traffic_lights": False,
                    "max_npcs": 0,
                },
                "buckets": ["normal"],
            },
        ],
    }


def test_relabel_comparison_reapplies_explicit_manifest() -> None:
    report = relabel_comparison(_comparison(), _manifest())
    rows_by_key = {
        (str(row["variant"]), str(row["run_key"])): row for row in report["runs"]
    }

    assert rows_by_key[("camp", "sample59-on")]["scenario_buckets"] == [
        "overall",
        "sharp_turn",
        "traffic_light",
        "red_light_turn",
    ]
    assert rows_by_key[("camp", "sample2-normal")]["scenario_buckets"] == [
        "overall",
        "normal",
    ]
    assert report["relabel_analysis"]["online_selector_change"] is False
    assert report["relabel_analysis"]["training"] is False
    assert report["pairing_audit"]["strictly_paired"]
    assert report["safety_gate_assessments"][0]["hard_gate_passed"]


def test_relabel_cli_writes_json_and_markdown(tmp_path, monkeypatch) -> None:
    input_path = tmp_path / "comparison.json"
    manifest_path = tmp_path / "manifest.json"
    output_json = tmp_path / "relabeled.json"
    output_md = tmp_path / "relabeled.md"
    input_path.write_text(json.dumps(_comparison()), encoding="utf-8")
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "relabel_diffusion_planner_safety_comparison.py",
            "--input_json",
            str(input_path),
            "--scenario_bucket_manifest",
            str(manifest_path),
            "--output_json",
            str(output_json),
            "--output_markdown",
            str(output_md),
            "--require_strict_pairing",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["relabel_analysis"]["explicit_labeling_only"]
    assert "## SafetyCost v1 Hard Gate" in output_md.read_text(encoding="utf-8")
