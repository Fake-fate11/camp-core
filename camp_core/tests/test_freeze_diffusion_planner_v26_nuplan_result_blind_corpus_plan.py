from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _module():
    path = ROOT / "scripts/integrations/freeze_diffusion_planner_v26_nuplan_result_blind_corpus_plan.py"
    spec = importlib.util.spec_from_file_location("v26_result_blind_corpus_plan", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _group(city: str, index: int) -> dict[str, str]:
    population_id = f"{city}:population:{index}"
    return {
        "population_id": population_id,
        "city": city,
        "log_token": f"{city}:log:{index}",
        "scenario_scene_token": f"{city}:scene:{index}",
        "mission_route_roadblock_chain_sha256": f"route-{city}-{index}",
        "corridor_id": f"{city}:corridor:{index}",
        "geometry_clone_group_sha256": f"geometry-{city}-{index}",
        "source_db_sha256": f"db-{city}",
        "map_sha256": f"map-{city}",
        "raw_db_relative_path": f"raw_cities/{city}/one.db",
    }


def _anchor(
    group: dict[str, str],
    partition: str,
    index: int,
    memberships: list[tuple[str, str]],
) -> dict[str, object]:
    return {
        "anchor_id": f"{group['population_id']}:anchor:{index}",
        "population_id": group["population_id"],
        "state_token": f"state-{group['city']}-{index}",
        "timestamp": index,
        "partition": partition,
        "event_memberships": [
            {"stratum": stratum, "phase": phase} for stratum, phase in memberships
        ],
        "membership_requests": 999,
    }


def _write_manifest(path: Path) -> None:
    boston_train = _group("boston", 1)
    pittsburgh_train = _group("pittsburgh", 1)
    boston_val = _group("boston", 2)
    pittsburgh_val = _group("pittsburgh", 2)
    singapore_test = _group("singapore", 1)
    anchors = [
        _anchor(
            boston_train,
            "train_iid",
            1,
            [("baseline:deterministic_time", "time_start"), ("scenario_tag:rare", "core")],
        ),
        _anchor(boston_train, "train_iid", 2, [("baseline:deterministic_time", "time_start")]),
        _anchor(pittsburgh_train, "train_iid", 1, [("baseline:deterministic_time", "time_start")]),
        _anchor(pittsburgh_train, "train_iid", 2, [("baseline:deterministic_time", "time_start")]),
        _anchor(boston_val, "val_iid", 1, [("baseline:deterministic_time", "time_start")]),
        _anchor(pittsburgh_val, "val_iid", 1, [("baseline:deterministic_time", "time_start")]),
        _anchor(singapore_test, "test_ood", 1, [("baseline:deterministic_time", "time_start")]),
    ]
    strata = [
        {"city": "boston", "partition": "train_iid", "tag": "baseline:deterministic_time", "phase": "time_start", "population_count": 2},
        {"city": "boston", "partition": "train_iid", "tag": "scenario_tag:rare", "phase": "core", "population_count": 1},
        {"city": "pittsburgh", "partition": "train_iid", "tag": "baseline:deterministic_time", "phase": "time_start", "population_count": 2},
        {"city": "boston", "partition": "val_iid", "tag": "baseline:deterministic_time", "phase": "time_start", "population_count": 1},
        {"city": "pittsburgh", "partition": "val_iid", "tag": "baseline:deterministic_time", "phase": "time_start", "population_count": 1},
        {"city": "singapore", "partition": "test_ood", "tag": "baseline:deterministic_time", "phase": "time_start", "population_count": 1},
    ]
    manifest = {
        "schema_version": "camp_dp_v26_nuplan_full_population_sampling_manifest_v1",
        "evidence_role": "development_nonholdout_nuplan_full_population_sampling",
        "outcome_fields_consumed": [],
        "sampling_manifest_sha256": "a" * 64,
        "sampling_contract": {"status": "identity_only_pre_pool_not_arbitrary_cap"},
        "fixed_dp": {"head": "7a1d33da277a1992ec474b5383a0c963c72e04e4"},
        "population_groups": [
            boston_train,
            pittsburgh_train,
            boston_val,
            pittsburgh_val,
            singapore_test,
        ],
        "city_partition_tag_phase": strata,
        "selected_anchors": anchors,
    }
    path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def test_result_blind_plan_freezes_balanced_quotas_weights_and_cluster_ci(tmp_path: Path) -> None:
    module = _module()
    input_manifest = tmp_path / "sampling_manifest.json"
    _write_manifest(input_manifest)
    args = module.parse_args(
        [
            "--sampling-manifest",
            str(input_manifest),
            "--output",
            str(tmp_path / "plan.json"),
            "--train-per-city",
            "2",
            "--validation-per-city",
            "1",
            "--ood-test-count",
            "1",
            "--rare-stratum-max-unique-anchors",
            "1",
        ]
    )

    plan = module.build_plan(args)

    assert plan["outcome_fields_consumed"] == []
    assert plan["payload_read"] is False
    assert plan["capacity_estimate"]["planned_unique_pool_count"] == 7
    assert plan["analysis_freeze"]["aggregate_weights"]["iid_city_macro"] == {
        "boston": 0.5,
        "pittsburgh": 0.5,
    }
    assert plan["analysis_freeze"]["cluster_aware_ci"]["replicates"] == 2000
    assert plan["analysis_freeze"]["primary_metrics_and_statistics"]["significance"][
        "multiplicity"
    ].startswith("Holm")
    assert plan["analysis_freeze"]["singapore_ood_status"] == (
        "identity_frozen_city_held_out_not_evaluated"
    )
    assert len({row["anchor_id"] for row in plan["planned_anchors"]}) == 7
    assert any(
        row["anchor_id"] == "boston:population:1:anchor:1"
        and any(reason.startswith("retain_rare_source_event") for reason in row["selection_reasons"])
        for row in plan["planned_anchors"]
    )
    assert "membership_requests" in plan["selection_contract"]["forbidden_denominators"]
    assert all("membership_requests" not in row for row in plan["planned_anchors"])
    assert plan["learning_curve"] == []


def test_mandatory_identity_only_coverage_expands_a_too_small_city_quota(tmp_path: Path) -> None:
    module = _module()
    input_manifest = tmp_path / "sampling_manifest.json"
    _write_manifest(input_manifest)
    manifest = json.loads(input_manifest.read_text(encoding="utf-8"))
    boston_val = next(
        group
        for group in manifest["population_groups"]
        if group["population_id"] == "boston:population:2"
    )
    for anchor in manifest["selected_anchors"]:
        if anchor["anchor_id"] == "boston:population:2:anchor:1":
            anchor["event_memberships"].append(
                {"stratum": "scenario_tag:rare", "phase": "core"}
            )
    manifest["selected_anchors"].extend(
        [
            _anchor(
                boston_val,
                "val_iid",
                index,
                [
                    ("baseline:deterministic_time", "time_start"),
                    ("scenario_tag:rare", "core"),
                ],
            )
            for index in (2, 3)
        ]
    )
    for row in manifest["city_partition_tag_phase"]:
        if (row["city"], row["partition"], row["tag"], row["phase"]) == (
            "boston",
            "val_iid",
            "baseline:deterministic_time",
            "time_start",
        ):
            row["population_count"] = 3
    manifest["city_partition_tag_phase"].append(
        {
            "city": "boston",
            "partition": "val_iid",
            "tag": "scenario_tag:rare",
            "phase": "core",
            "population_count": 3,
        }
    )
    input_manifest.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )

    plan = module.build_plan(
        module.parse_args(
            [
                "--sampling-manifest",
                str(input_manifest),
                "--output",
                str(tmp_path / "plan.json"),
                "--train-per-city",
                "2",
                "--validation-per-city",
                "1",
                "--ood-test-count",
                "1",
                "--rare-stratum-max-unique-anchors",
                "3",
            ]
        )
    )

    boston_val_resolution = next(
        row
        for row in plan["quota_resolution"]["partitions"]
        if (row["city"], row["partition"]) == ("boston", "val_iid")
    )
    assert boston_val_resolution == {
        "city": "boston",
        "partition": "val_iid",
        "predeclared_target_quota": 1,
        "mandatory_coverage_lower_bound": 3,
        "effective_quota": 3,
        "quota_expanded_for_mandatory_coverage": True,
    }
    assert plan["quotas"]["val_iid"]["boston"] == 3
    assert plan["capacity_estimate"]["planned_unique_pool_count"] == 9
    assert plan["payload_read"] is False
    assert plan["outcome_fields_consumed"] == []
