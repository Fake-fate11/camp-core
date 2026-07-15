import copy
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASE_CONFIG = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _config() -> dict:
    config = copy.deepcopy(json.loads(BASE_CONFIG.read_text(encoding="utf-8")))
    route_identity = _sha("v24-train-route")
    config["schema_version"] = "camp_dp_v24_native_corpus_run_v1"
    config["selector"]["role"] = "v24_train_corpus_collection_only"
    config["map"] = {"path": "/tmp/v24.osm", "sha256": _sha("v24-map")}
    config["routes"] = [
        {
            "name": route_identity,
            "path": "/tmp/v24-route.pkl",
            "sha256": _sha("v24-route-asset"),
        }
    ]
    config["seeds"] = {
        "scenario": 24001,
        "candidate": 24001,
        "bootstrap": 24001,
        "formal_forbidden": [11, 12, 13],
    }
    config["spawn_config"]["seed"] = 24001
    config["spawn_config"]["max_steps"] = 64
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [route_identity],
        "corpus_steps": 64,
        "sample_every_ticks": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v24_train_corpus_collection",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": True,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
    }
    return config


def test_v24_corpus_run_config_is_train_only_per_tick_k8() -> None:
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    config = _config()
    validate_v24_corpus_run_config(config)

    assert config["protocol"]["sample_every_ticks"] == 1
    assert config["protocol"]["candidate_k"] == 8
    assert config["protocol"]["training_authorized"] is True
    assert config["protocol"]["calibration_authorized"] is False
    assert config["protocol"]["holdout_access_authorized"] is False
    assert config["protocol"]["claim_authorized"] is False


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ("cadence", "protocol mismatch"),
        ("holdout", "protocol mismatch"),
        ("calibration", "protocol mismatch"),
        ("seed", "seed namespace"),
    ),
)
def test_v24_corpus_run_config_rejects_protocol_drift(
    mutation: str, match: str
) -> None:
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    config = _config()
    if mutation == "cadence":
        config["protocol"]["sample_every_ticks"] = 5
    elif mutation == "holdout":
        config["protocol"]["holdout_access_authorized"] = True
    elif mutation == "calibration":
        config["protocol"]["calibration_authorized"] = True
    else:
        config["seeds"]["scenario"] = 24101

    with pytest.raises(ValueError, match=match):
        validate_v24_corpus_run_config(config)


def _route(index: int, family: str) -> dict:
    identity = _sha(f"route:{index}")
    record_key = f"{family}/map/{index}/{identity[:16]}"
    return {
        "record_key": record_key,
        "identity_sha256": identity,
        "map_family_id": family,
        "logical_map_sha256": _sha(f"logical-map:{family}"),
        "source_map_path": f"/tmp/{family}.osm",
        "source_map_sha256": _sha(f"source-map:{family}"),
        "source_stratum": {"traffic_light": False},
        "route_spec": {
            "map_path": f"/tmp/{family}.osm",
            "lanelet_ids": [index + 1],
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [80.0, 0.0, 0.0],
        },
    }


def _split_and_census() -> tuple[dict, dict]:
    from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
        SPLIT_MANIFEST_SHA256,
        SPLIT_PLAN_SHA256,
    )

    assignments = (
        [("train", "map_family_train", list(range(375)))]
        + [("calibration", "map_family_calibration", list(range(375, 377)))]
        + [("holdout", "map_family_holdout", list(range(377, 401)))]
    )
    seed_namespaces = {
        "train": [24001, 24002, 24003, 24004, 24005],
        "calibration": [24101, 24102, 24103, 24104, 24105],
        "holdout": [24201, 24202, 24203, 24204, 24205],
    }
    routes = []
    records = []
    for split, family, indices in assignments:
        for index in indices:
            route = _route(index, family)
            routes.append(route)
            records.append(
                {
                    "record_key": route["record_key"],
                    "identity_sha256": route["identity_sha256"],
                    "map_family_id": family,
                    "corridor_group_sha256": _sha(f"corridor:{family}"),
                    "split": split,
                    "seeds": seed_namespaces[split],
                }
            )
    split = {
        "schema": "camp_dp_v24_map_family_split_manifest_v1",
        "plan_sha256": SPLIT_PLAN_SHA256,
        "manifest_sha256": SPLIT_MANIFEST_SHA256,
        "seed_namespaces": seed_namespaces,
        "records": records,
        "outcome_fields_consumed": [],
        "holdout_opened": False,
    }
    census = {
        "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "retained_routes": routes,
    }
    return split, census


def test_v24_corpus_plan_freezes_all_train_routes_and_five_seeds() -> None:
    from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
        build_corpus_plan,
    )

    split, census = _split_and_census()
    plan = build_corpus_plan(split, census)

    assert plan["execution_splits"] == ["train"]
    assert plan["route_counts"] == {"train": 375, "calibration": 2, "holdout": 24}
    assert plan["train_route_count"] == 375
    assert plan["train_seeds"] == [24001, 24002, 24003, 24004, 24005]
    assert plan["train_route_seed_run_count"] == 1875
    assert plan["sample_every_ticks"] == 1
    assert plan["thinning_rule"] == "none_capture_every_available_tick"
    assert plan["feature_payload_fields"] == [
        "atom_matrix",
        "source_valid_mask",
        "candidate_row_sha256",
    ]
    assert "record_key" in plan["receipt_only_identity_fields"]
    assert plan["candidate_immutability_required"] is True
    assert plan["candidate0_default_identity_required"] is True
    assert plan["theoretical_max_snapshot_count"] == 120000
    assert [phase["route_seed_run_count"] for phase in plan["phases"]] == [375, 1500]
    assert all(phase["tuning_authorized"] is False for phase in plan["phases"])
    assert plan["holdout_opened"] is False
    assert plan["training_execution_authorized"] is False


@pytest.mark.parametrize(("target", "match"), (("split", "opened holdout"), ("census", "outcome_accessed")))
def test_v24_corpus_plan_rejects_boundary_drift(target: str, match: str) -> None:
    from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
        build_corpus_plan,
    )

    split, census = _split_and_census()
    if target == "split":
        split["holdout_opened"] = True
    else:
        census["outcome_accessed"] = True

    with pytest.raises(ValueError, match=match):
        build_corpus_plan(split, census)


def test_v24_corpus_builder_produces_runner_valid_config() -> None:
    from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
        build_corpus_run_config,
    )
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    route = _route(0, "map_family_train")
    config = build_corpus_run_config(
        template,
        route,
        {"path": "/tmp/route.pkl", "sha256": _sha("route-asset")},
        24005,
    )

    validate_v24_corpus_run_config(config)
    assert config["routes"][0]["name"] == route["identity_sha256"]
    assert config["map"]["sha256"] == route["source_map_sha256"]
    assert config["seeds"]["scenario"] == 24005
    assert config["protocol"]["sample_every_ticks"] == 1


def test_independent_reviewer_reconstructs_corpus_run_config() -> None:
    from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
        build_corpus_run_config,
    )
    from scripts.integrations.review_diffusion_planner_v24_native_corpus import (
        build_expected_run_config,
        canonical_sha256,
    )

    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    route = _route(0, "map_family_train")
    asset = {"path": "/tmp/route.pkl", "sha256": _sha("route-asset")}

    prepared = build_corpus_run_config(template, route, asset, 24003)
    reviewed = build_expected_run_config(template, route, asset, 24003)

    assert reviewed == prepared
    assert canonical_sha256(reviewed) == canonical_sha256(prepared)


@pytest.mark.parametrize("mutation", ("seed", "split", "holdout"))
def test_independent_reviewer_rejects_corpus_boundary_drift(mutation: str) -> None:
    from scripts.integrations.review_diffusion_planner_v24_native_corpus import (
        validate_corpus_boundaries,
    )

    plan = {
        "execution_splits": ["train"],
        "train_seeds": [24001, 24002, 24003, 24004, 24005],
        "sample_every_ticks": 1,
        "thinning_rule": "none_capture_every_available_tick",
        "outcome_fields_consumed": [],
        "calibration_access_authorized": False,
        "holdout_access_authorized": False,
        "holdout_opened": False,
        "training_execution_authorized": False,
        "claim_authorized": False,
    }
    manifest = {
        "split": "train",
        "seeds": [24001, 24002, 24003, 24004, 24005],
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
    }
    if mutation == "seed":
        manifest["seeds"][-1] = 24205
    elif mutation == "split":
        manifest["split"] = "holdout"
    else:
        plan["holdout_opened"] = True

    with pytest.raises(ValueError, match="boundary"):
        validate_corpus_boundaries(plan, manifest)


def _snapshot(tick: int = 0) -> dict:
    row_sha = [_sha(f"row:{tick}:{index}") for index in range(8)]
    tensor_sha = _sha(f"tensor:{tick}")
    causal_sha = _sha(f"causal:{tick}")
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": [[1.0] * 14 for _ in range(8)],
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": row_sha,
        },
        "sidecar": {
            "tick_index": tick,
            "candidate_tensor_sha256_before": tensor_sha,
            "candidate_tensor_sha256_after": tensor_sha,
            "causal_input_sha256": causal_sha,
            "default_output_sha256": row_sha[0],
            "candidate0_sha256": row_sha[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": row_sha[0],
                "candidate0_sha256": row_sha[0],
                "native_ranked_k8": False,
            },
            "physical_feasible_mask": [True] * 8,
            "all_k_high_risk": False,
        },
    }


def _pilot_manifest(tmp_path: Path) -> dict:
    routes = []
    for index in range(2):
        route = _route(index, "map_family_train")
        asset_path = tmp_path / f"route-{index}.pkl"
        asset_path.write_text(str(index), encoding="utf-8")
        route.update(
            {
                "corridor_group_sha256": _sha("corridor:train"),
                "route_asset": {
                    "path": str(asset_path),
                    "sha256": hashlib.sha256(asset_path.read_bytes()).hexdigest(),
                },
                "seeds": [24001, 24002, 24003, 24004, 24005],
            }
        )
        routes.append(route)
    return {
        "schema": "camp_dp_v24_native_corpus_manifest_v1",
        "split": "train",
        "routes": routes,
        "route_count": 2,
        "seeds": [24001, 24002, 24003, 24004, 24005],
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
    }


def test_pilot_rows_select_every_train_route_at_first_seed_only(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        pilot_rows,
    )

    rows = pilot_rows(_pilot_manifest(tmp_path), expected_route_count=2)

    assert [(route["identity_sha256"], seed) for route, seed in rows] == [
        (_sha("route:0"), 24001),
        (_sha("route:1"), 24001),
    ]


def test_pilot_executor_retains_failure_and_continues(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        execute_pilot_manifest,
    )

    manifest = _pilot_manifest(tmp_path)
    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, output_dir, max_steps
        identity = config["routes"][0]["name"]
        calls.append((identity, config["seeds"]["scenario"]))
        if identity == _sha("route:0"):
            raise RuntimeError("objective pilot failure")
        decision_sink(_snapshot())
        return {"status": "ok", "steps": []}

    summary = execute_pilot_manifest(
        manifest,
        template,
        output_dir=tmp_path / "pilot",
        run_arm=run_arm,
        expected_route_count=2,
        free_bytes=lambda: 20 * 1024**3,
    )

    assert calls == [(_sha("route:0"), 24001), (_sha("route:1"), 24001)]
    assert summary["status"] == "complete_with_retained_failures"
    assert summary["planned_route_seed_runs"] == 2
    assert summary["complete_route_seed_runs"] == 1
    assert summary["failed_route_seed_runs"] == 1
    assert summary["retained_route_seed_runs"] == 2
    assert summary["snapshot_count"] == 1
    receipts = list((tmp_path / "pilot" / "receipts" / "train").rglob("*.json"))
    assert len(receipts) == 2
    assert all(json.loads(path.read_text())["retained_in_denominator"] for path in receipts)
