from __future__ import annotations

from pathlib import Path

from scripts.integrations.build_diffusion_planner_v24_map_family_split import (
    PRIMARY_SEEDS,
    build_split_manifest,
    build_split_plan,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-map-family-split.md"
)


def _census() -> dict:
    routes = []
    groups = []
    for family, count in (("family-large", 7), ("family-medium", 2), ("family-small", 1)):
        keys = []
        identities = []
        for index in range(count):
            key = f"{family}/{index}"
            identity = f"{index + count:064x}"
            keys.append(key)
            identities.append(identity)
            routes.append(
                {
                    "record_key": key,
                    "identity_sha256": identity,
                    "map_family_id": family,
                    "logical_map_name": family,
                    "holdout_forbidden": False,
                }
            )
        groups.append(
            {
                "group_sha256": f"{count:064x}",
                "route_record_keys": keys,
                "route_identity_sha256": identities,
                "route_record_count": count,
            }
        )
    return {
        "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "retained_routes": routes,
        "corridor_groups": {
            "source_only": True,
            "outcome_fields_consumed": [],
            "route_records": routes,
            "groups": groups,
        },
    }


def test_split_plan_assigns_whole_families_outcome_blind() -> None:
    plan = build_split_plan(_census())

    assert plan["family_assignments"] == {
        "family-large": "train",
        "family-medium": "holdout",
        "family-small": "calibration",
    }
    assert plan["route_counts"] == {"train": 7, "calibration": 1, "holdout": 2}
    assert plan["route_seed_counts"] == {
        "train": 35,
        "calibration": 5,
        "holdout": 10,
    }
    assert plan["primary_seeds"] == list(PRIMARY_SEEDS)
    assert plan["pilot_seed"] == PRIMARY_SEEDS[0]
    assert plan["holdout_opened"] is False
    assert plan["outcome_fields_consumed"] == []


def test_split_plan_preregisters_indivisible_and_seed_boundaries() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "entire map family is indivisible",
        "train/calibration/holdout = 70/10/20",
        "24001, 24002, 24003, 24004, 24005",
        "same route and all of its seeds remain in one split",
        "Outcomes, K=8 scores, and holdout metrics are forbidden",
        "375 / 2 / 24",
    ):
        assert phrase in text


def test_split_manifest_covers_routes_without_family_or_seed_leakage() -> None:
    census = _census()
    plan = build_split_plan(census)

    manifest = build_split_manifest(census, plan)

    assert manifest["route_count"] == 10
    assert manifest["route_seed_count"] == 50
    assert len(manifest["records"]) == 10
    assert len({record["record_key"] for record in manifest["records"]}) == 10
    for record in manifest["records"]:
        assert record["split"] == plan["family_assignments"][record["map_family_id"]]
        assert record["seeds"] == list(PRIMARY_SEEDS)
        assert len(record["corridor_group_sha256"]) == 64
    assert manifest["outcome_fields_consumed"] == []
    assert manifest["holdout_opened"] is False
