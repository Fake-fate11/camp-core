from __future__ import annotations

import json

import pytest

from scripts.integrations.build_diffusion_planner_scenario_bucket_manifest import (
    build_manifest,
    main,
)


def _comparison() -> dict[str, object]:
    rows = []
    for variant in ("top1", "camp"):
        for route_name, route_path, seed, traffic_lights in (
            (
                "sample_map_tl_route_59_to_86",
                "/assets/sample_map_tl_route_59_to_86.pkl",
                1,
                True,
            ),
            (
                "nishishinjuku_release_auto_route",
                "/assets/nishishinjuku_release_auto_route.pkl",
                2,
                False,
            ),
        ):
            rows.append(
                {
                    "variant": variant,
                    "run_key": (
                        f"{route_path}|{seed}|200|4|0.3|{traffic_lights}|perfect"
                    ),
                    "route": route_path,
                    "route_name": route_name,
                    "seed": seed,
                    "steps": 200,
                    "max_npcs": 4,
                    "spawn_probability": 0.3,
                    "traffic_lights": traffic_lights,
                    "advance_mode": "perfect",
                }
            )
    return {"baseline": "top1", "runs": rows}


def test_manifest_builder_creates_unlabeled_explicit_skeleton() -> None:
    manifest = build_manifest(_comparison(), include_run_keys=True)

    assert manifest["metadata"]["schema_version"] == "dp_camp_scenario_buckets_v1"
    assert manifest["metadata"]["explicit_labeling_only"]
    assert manifest["routes"] == {
        "nishishinjuku_release_auto_route": [],
        "sample_map_tl_route_59_to_86": [],
    }
    assert len(manifest["run_keys"]) == 2
    assert len(manifest["unlabeled_routes"]) == 2
    assert len(manifest["unlabeled_run_keys"]) == 2
    run_meta = next(iter(manifest["run_key_metadata"].values()))
    assert {
        "route",
        "route_name",
        "seed",
        "steps",
        "max_npcs",
        "spawn_probability",
        "traffic_lights",
        "advance_mode",
    }.issubset(run_meta)


def test_manifest_builder_accepts_only_explicit_valid_labels() -> None:
    manifest = build_manifest(
        _comparison(),
        route_bucket_assignments={
            "sample_map_tl_route_59_to_86": ["traffic_light", "red_light_turn"],
        },
    )

    assert manifest["routes"]["sample_map_tl_route_59_to_86"] == [
        "traffic_light",
        "red_light_turn",
    ]
    assert manifest["routes"]["nishishinjuku_release_auto_route"] == []


def test_manifest_builder_rejects_unknown_route_label() -> None:
    with pytest.raises(ValueError, match="not present"):
        build_manifest(
            _comparison(),
            route_bucket_assignments={"missing_route": ["traffic_light"]},
        )


def test_manifest_builder_cli_writes_json(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    comparison_path = tmp_path / "comparison.json"
    output_path = tmp_path / "manifest.json"
    comparison_path.write_text(json.dumps(_comparison()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_diffusion_planner_scenario_bucket_manifest.py",
            "--comparison_json",
            str(comparison_path),
            "--output_json",
            str(output_path),
            "--include_run_keys",
            "--route_bucket",
            "sample_map_tl_route_59_to_86=traffic_light,red_light_turn",
        ],
    )

    main()

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["routes"]["sample_map_tl_route_59_to_86"] == [
        "traffic_light",
        "red_light_turn",
    ]
    assert len(manifest["run_keys"]) == 2
