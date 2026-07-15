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


@pytest.mark.parametrize(
    ("target", "match"), (("split", "opened holdout"), ("census", "outcome_accessed"))
)
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


def _remaining_review(manifest: dict) -> dict:
    route_order = [
        route["record_key"]
        for route in sorted(manifest["routes"], key=lambda item: item["record_key"])
    ]
    return {
        "schema": "camp_dp_v24_native_corpus_pilot_independent_review_v1",
        "status": "passed_with_warning",
        "failed_count": 0,
        "review_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "decision": {
            "authorized": True,
            "action": "execute_frozen_remaining_train_seeds",
            "route_count": len(route_order),
            "route_order": route_order,
            "seeds": [24002, 24003, 24004, 24005],
            "preserve_all_failures_and_denominator": True,
            "route_removal_replacement_reordering_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
    }


def test_remaining_rows_freeze_route_major_seed_minor_denominator(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        remaining_rows,
    )

    manifest = _pilot_manifest(tmp_path)
    rows = remaining_rows(manifest, _remaining_review(manifest), expected_route_count=2)

    assert [(route["identity_sha256"], seed) for route, seed in rows] == [
        (_sha("route:0"), 24002),
        (_sha("route:0"), 24003),
        (_sha("route:0"), 24004),
        (_sha("route:0"), 24005),
        (_sha("route:1"), 24002),
        (_sha("route:1"), 24003),
        (_sha("route:1"), 24004),
        (_sha("route:1"), 24005),
    ]


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ("authorization", "authorization"),
        ("route_order", "route order"),
        ("seeds", "seed"),
        ("denominator", "denominator"),
        ("tuning", "tuning"),
        ("outcome", "outcome"),
        ("holdout", "holdout"),
        ("training", "training"),
    ),
)
def test_remaining_rows_reject_review_boundary_drift(
    tmp_path: Path, mutation: str, match: str
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        remaining_rows,
    )

    manifest = _pilot_manifest(tmp_path)
    review = _remaining_review(manifest)
    decision = review["decision"]
    if mutation == "authorization":
        decision["authorized"] = False
    elif mutation == "route_order":
        decision["route_order"] = list(reversed(decision["route_order"]))
    elif mutation == "seeds":
        decision["seeds"][-1] = 24205
    elif mutation == "denominator":
        decision["preserve_all_failures_and_denominator"] = False
    elif mutation == "tuning":
        decision["tuning_authorized"] = True
    elif mutation == "outcome":
        decision["outcome_access_authorized"] = True
    elif mutation == "training":
        review["training_executed"] = True
    else:
        decision["holdout_access_authorized"] = True

    with pytest.raises(ValueError, match=match):
        remaining_rows(manifest, review, expected_route_count=2)


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
    assert all(
        json.loads(path.read_text())["retained_in_denominator"] for path in receipts
    )


def test_remaining_executor_retains_failures_across_all_frozen_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.integrations import (
        execute_diffusion_planner_v24_native_corpus as executor,
    )

    manifest = _pilot_manifest(tmp_path)
    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    calls = []
    aggregate_calls = 0
    original_aggregate = executor._aggregate_execution

    def aggregate_spy(output_dir, planned):
        nonlocal aggregate_calls
        aggregate_calls += 1
        return original_aggregate(output_dir, planned)

    monkeypatch.setattr(executor, "_aggregate_execution", aggregate_spy)

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, output_dir, max_steps
        identity = config["routes"][0]["name"]
        seed = config["seeds"]["scenario"]
        calls.append((identity, seed))
        if identity == _sha("route:0"):
            raise RuntimeError("retained source-invalid route")
        decision_sink(_snapshot(seed))
        return {"status": "ok", "steps": []}

    output_dir = tmp_path / "remaining"
    summary = executor.execute_remaining_manifest(
        manifest,
        _remaining_review(manifest),
        template,
        output_dir=output_dir,
        run_arm=run_arm,
        expected_route_count=2,
        free_bytes=lambda: 20 * 1024**3,
    )

    assert calls == [
        *[(_sha("route:0"), seed) for seed in range(24002, 24006)],
        *[(_sha("route:1"), seed) for seed in range(24002, 24006)],
    ]
    assert summary["status"] == "complete_with_retained_failures"
    assert summary["phase"] == "main_completion_remaining_frozen_seeds"
    assert summary["seeds"] == [24002, 24003, 24004, 24005]
    assert summary["planned_route_seed_runs"] == 8
    assert summary["complete_route_seed_runs"] == 4
    assert summary["failed_route_seed_runs"] == 4
    assert summary["retained_route_seed_runs"] == 8
    assert summary["theoretical_max_snapshots"] == 512
    receipt_paths = list((output_dir / "receipts" / "train").rglob("*.json"))
    assert len(receipt_paths) == 8
    for path in receipt_paths:
        receipt = json.loads(path.read_text())
        assert receipt["schema"] == "camp_dp_v24_native_corpus_remaining_run_receipt_v1"
        assert receipt["phase"] == "main_completion_remaining_frozen_seeds"
    progress = json.loads((output_dir / "progress.json").read_text())
    assert progress["schema"] == "camp_dp_v24_native_corpus_remaining_progress_v1"
    assert progress["status"] == summary["status"]
    assert progress["last_completed_row"] == 8
    assert aggregate_calls == 2


def test_remaining_resume_accepts_only_matching_unsealed_partial_artifact(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _validate_remaining_resume,
    )

    output_dir = tmp_path / "partial"
    output_dir.mkdir()
    heads = "CAMP_HEAD=" + "a" * 40 + "\n"
    (output_dir / "HEADS").write_text(heads, encoding="ascii")
    (output_dir / "COMMAND").write_text(
        "v24 native corpus execute-remaining\n", encoding="utf-8"
    )

    _validate_remaining_resume(output_dir, heads)

    (output_dir / "run.exit").write_text("0\n", encoding="ascii")
    with pytest.raises(ValueError, match="cannot resume"):
        _validate_remaining_resume(output_dir, heads)


def test_remaining_resume_rejects_source_head_drift(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _validate_remaining_resume,
    )

    output_dir = tmp_path / "partial"
    output_dir.mkdir()
    (output_dir / "HEADS").write_text("CAMP_HEAD=" + "b" * 40 + "\n")
    (output_dir / "COMMAND").write_text(
        "v24 native corpus execute-remaining\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="HEADS mismatch"):
        _validate_remaining_resume(output_dir, "CAMP_HEAD=" + "a" * 40 + "\n")


def test_remaining_executor_rejects_tampered_resume_receipt(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        execute_remaining_manifest,
    )

    manifest = _pilot_manifest(tmp_path)
    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, config, output_dir, max_steps
        decision_sink(_snapshot())
        return {"status": "ok", "steps": []}

    output_dir = tmp_path / "remaining"
    execute_remaining_manifest(
        manifest,
        _remaining_review(manifest),
        template,
        output_dir=output_dir,
        run_arm=run_arm,
        expected_route_count=2,
        free_bytes=lambda: 20 * 1024**3,
    )
    receipt_path = next((output_dir / "receipts" / "train").rglob("*.json"))
    receipt = json.loads(receipt_path.read_text())
    receipt["phase"] = "tampered"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="receipt boundary"):
        execute_remaining_manifest(
            manifest,
            _remaining_review(manifest),
            template,
            output_dir=output_dir,
            run_arm=run_arm,
            expected_route_count=2,
            free_bytes=lambda: 20 * 1024**3,
            resume=True,
        )


def test_remaining_executor_rejects_unplanned_resume_receipt(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        execute_remaining_manifest,
    )

    manifest = _pilot_manifest(tmp_path)
    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    output_dir = tmp_path / "remaining"
    rogue = output_dir / "receipts" / "train" / _sha("rogue-route") / "seed_24002.json"
    rogue.parent.mkdir(parents=True)
    rogue.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="unplanned files"):
        execute_remaining_manifest(
            manifest,
            _remaining_review(manifest),
            template,
            output_dir=output_dir,
            run_arm=lambda **kwargs: kwargs,
            expected_route_count=2,
            free_bytes=lambda: 20 * 1024**3,
            resume=True,
        )


def test_terminal_snapshot_inventory_rejects_orphan(tmp_path: Path) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _validate_terminal_snapshot_inventory,
    )

    snapshot = tmp_path / "snapshots" / f"{_sha('orphan')}.json"
    snapshot.parent.mkdir()
    snapshot.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="differs from receipts"):
        _validate_terminal_snapshot_inventory(tmp_path)


def test_remaining_preflight_cli_never_builds_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.integrations import (
        execute_diffusion_planner_v24_native_corpus as executor,
    )

    route_rows = []
    for index in range(375):
        route = {"record_key": f"route/{index:03d}"}
        route_rows.extend((route, seed) for seed in range(24002, 24006))
    review = {
        "decision": {
            "route_count": 375,
            "preserve_all_failures_and_denominator": True,
        }
    }

    def fake_preflight(**kwargs):
        del kwargs
        return {}, {}, [{"name": "static_only", "passed": True}], review, route_rows

    def forbidden_runner(*args, **kwargs):
        del args, kwargs
        raise AssertionError("remaining preflight constructed the native runner")

    monkeypatch.setattr(executor, "_execution_preflight", fake_preflight)
    monkeypatch.setattr(executor, "build_native_arm_runner", forbidden_runner)
    output_dir = tmp_path / "remaining-preflight"
    rc = executor.main(
        [
            "--mode",
            "remaining-execution-preflight",
            "--preflight-root",
            str(tmp_path / "source-preflight"),
            "--expected-preflight-root-sha256",
            _sha("source-preflight"),
            "--review-root",
            str(tmp_path / "source-review"),
            "--expected-review-root-sha256",
            _sha("source-review"),
            "--pilot-root",
            str(tmp_path / "pilot"),
            "--expected-pilot-root-sha256",
            _sha("pilot"),
            "--pilot-review-root",
            str(tmp_path / "pilot-review"),
            "--expected-pilot-review-root-sha256",
            _sha("pilot-review"),
            "--template",
            str(BASE_CONFIG),
            "--dp-repo",
            str(tmp_path / "dp"),
            "--camp-head",
            "a" * 40,
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    result = json.loads((output_dir / "preflight.json").read_text())
    assert result["route_count"] == 375
    assert result["seeds"] == [24002, 24003, 24004, 24005]
    assert result["route_seed_run_count"] == 1500
    assert result["theoretical_max_snapshots"] == 96000
    assert result["model_loaded"] is False
    assert result["simulator_executed"] is False
    assert result["candidate_generation_started"] is False
    assert result["training_executed"] is False
    assert result["holdout_opened"] is False
    assert result["next_work_target"].endswith("independent_review_only")


def _remaining_authorization_artifacts(
    tmp_path: Path,
) -> tuple[Path, str, Path, str, list]:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _row_order_sha256,
        remaining_rows,
    )

    manifest = _pilot_manifest(tmp_path)
    rows = remaining_rows(manifest, _remaining_review(manifest), expected_route_count=2)
    source_roots = {
        "corpus": _sha("corpus"),
        "corpus_review": _sha("corpus-review"),
        "pilot": _sha("pilot"),
        "pilot_review": _sha("pilot-review"),
    }
    preflight_root = tmp_path / "remaining-preflight-source"
    preflight_root.mkdir()
    (preflight_root / "preflight.json").write_text(
        json.dumps(
            {
                "schema": "camp_dp_v24_native_corpus_remaining_execution_preflight_v1",
                "status": "passed",
                "check_count": 1,
                "failed_count": 0,
                "checks": [{"name": "frozen_preflight", "passed": True}],
                "route_count": 2,
                "seeds": [24002, 24003, 24004, 24005],
                "route_seed_run_count": 8,
                "row_order_sha256": _row_order_sha256(rows),
                "theoretical_max_snapshots": 512,
                "pilot_route_denominator_retained": 2,
                "pilot_failures_retained": True,
                "model_loaded": False,
                "simulator_executed": False,
                "candidate_generation_started": False,
                "outcome_fields_consumed": [],
                "training_executed": False,
                "tuning_executed": False,
                "calibration_accessed": False,
                "holdout_opened": False,
                "claim_authorized": False,
            }
        )
    )
    preflight_sha = _seal_test_artifact(preflight_root)
    review_root = tmp_path / "remaining-preflight-review-source"
    review_root.mkdir()
    (review_root / "review.json").write_text(
        json.dumps(
            {
                "schema": "camp_dp_v24_native_corpus_remaining_preflight_independent_review_v1",
                "status": "passed",
                "check_count": 1,
                "failed_count": 0,
                "failed_checks": [],
                "checks": [{"name": "independent_review", "passed": True}],
                "source_preflight_root_sha256": preflight_sha,
                "source_corpus_root_sha256": source_roots["corpus"],
                "source_corpus_review_root_sha256": source_roots["corpus_review"],
                "source_pilot_root_sha256": source_roots["pilot"],
                "source_pilot_review_root_sha256": source_roots["pilot_review"],
                "route_count": 2,
                "seeds": [24002, 24003, 24004, 24005],
                "route_seed_run_count": 8,
                "row_order_sha256": _row_order_sha256(rows),
                "source_invalid_route_count": 1,
                "validated_run_config_count": 8,
                "preflight_reexecuted": False,
                "execution_preflight_builder_imported_or_called": False,
                "model_loaded": False,
                "simulator_executed": False,
                "candidate_generation_started": False,
                "outcome_fields_consumed": [],
                "training_executed": False,
                "tuning_executed": False,
                "calibration_accessed": False,
                "holdout_opened": False,
                "claim_authorized": False,
                "decision": {
                    "remaining_execution_authorized": True,
                    "action": "launch_one_unique_remaining_train_seed_execution",
                    "route_count": 2,
                    "seeds": [24002, 24003, 24004, 24005],
                    "preserve_all_failures_and_denominator": True,
                    "route_removal_replacement_reordering_authorized": False,
                    "tuning_authorized": False,
                    "outcome_access_authorized": False,
                    "calibration_access_authorized": False,
                    "holdout_access_authorized": False,
                    "claim_authorized": False,
                },
                "next_work_target": (
                    "v24_native_corpus_remaining_train_seeds_unique_execution_only"
                ),
            }
        )
    )
    review_sha = _seal_test_artifact(review_root)
    return preflight_root, preflight_sha, review_root, review_sha, [rows, source_roots]


def test_remaining_execution_requires_sealed_review_authorization(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _remaining_execution_authorization_checks,
    )

    preflight_root, preflight_sha, review_root, review_sha, context = (
        _remaining_authorization_artifacts(tmp_path)
    )
    rows, source_roots = context
    checks = _remaining_execution_authorization_checks(
        remaining_preflight_root=preflight_root,
        expected_remaining_preflight_root_sha256=preflight_sha,
        remaining_review_root=review_root,
        expected_remaining_review_root_sha256=review_sha,
        rows=rows,
        expected_corpus_preflight_root_sha256=source_roots["corpus"],
        expected_corpus_review_root_sha256=source_roots["corpus_review"],
        expected_pilot_root_sha256=source_roots["pilot"],
        expected_pilot_review_root_sha256=source_roots["pilot_review"],
        expected_route_count=2,
        expected_source_invalid_count=1,
    )

    assert checks
    assert all(check["passed"] for check in checks)


def test_remaining_execution_rejects_resealed_unauthorized_review(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _remaining_execution_authorization_checks,
    )

    preflight_root, preflight_sha, review_root, _review_sha, context = (
        _remaining_authorization_artifacts(tmp_path)
    )
    rows, source_roots = context
    path = review_root / "review.json"
    review = json.loads(path.read_text())
    review["decision"]["remaining_execution_authorized"] = False
    path.write_text(json.dumps(review))
    review_sha = _seal_test_artifact(review_root)

    checks = _remaining_execution_authorization_checks(
        remaining_preflight_root=preflight_root,
        expected_remaining_preflight_root_sha256=preflight_sha,
        remaining_review_root=review_root,
        expected_remaining_review_root_sha256=review_sha,
        rows=rows,
        expected_corpus_preflight_root_sha256=source_roots["corpus"],
        expected_corpus_review_root_sha256=source_roots["corpus_review"],
        expected_pilot_root_sha256=source_roots["pilot"],
        expected_pilot_review_root_sha256=source_roots["pilot_review"],
        expected_route_count=2,
        expected_source_invalid_count=1,
    )

    assert any(
        check["name"] == "remaining_review_authorized" and not check["passed"]
        for check in checks
    )


def test_remaining_execution_rejects_unlisted_authorization_json(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _remaining_execution_authorization_checks,
    )

    preflight_root, _preflight_sha, review_root, review_sha, context = (
        _remaining_authorization_artifacts(tmp_path)
    )
    manifest = preflight_root / "SHA256SUMS"
    manifest.write_text(
        "".join(
            line + "\n"
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if not line.endswith("  preflight.json")
        ),
        encoding="utf-8",
    )
    preflight_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (preflight_root / "ROOT_SHA256SUMS").write_text(
        f"{preflight_sha}  SHA256SUMS\n", encoding="ascii"
    )
    rows, source_roots = context

    checks = _remaining_execution_authorization_checks(
        remaining_preflight_root=preflight_root,
        expected_remaining_preflight_root_sha256=preflight_sha,
        remaining_review_root=review_root,
        expected_remaining_review_root_sha256=review_sha,
        rows=rows,
        expected_corpus_preflight_root_sha256=source_roots["corpus"],
        expected_corpus_review_root_sha256=source_roots["corpus_review"],
        expected_pilot_root_sha256=source_roots["pilot"],
        expected_pilot_review_root_sha256=source_roots["pilot_review"],
        expected_route_count=2,
        expected_source_invalid_count=1,
    )

    assert any(
        check["name"] == "remaining_preflight_exact_inventory" and not check["passed"]
        for check in checks
    )


@pytest.mark.parametrize(
    ("source", "field"),
    (("preflight", "outcome_fields_consumed"), ("review", "outcome_fields_consumed")),
)
def test_remaining_execution_rejects_missing_closed_boundary(
    tmp_path: Path,
    source: str,
    field: str,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _remaining_execution_authorization_checks,
    )

    preflight_root, preflight_sha, review_root, review_sha, context = (
        _remaining_authorization_artifacts(tmp_path)
    )
    root = preflight_root if source == "preflight" else review_root
    filename = "preflight.json" if source == "preflight" else "review.json"
    path = root / filename
    payload = json.loads(path.read_text())
    del payload[field]
    path.write_text(json.dumps(payload))
    resealed_sha = _seal_test_artifact(root)
    if source == "preflight":
        preflight_sha = resealed_sha
    else:
        review_sha = resealed_sha
    rows, source_roots = context

    checks = _remaining_execution_authorization_checks(
        remaining_preflight_root=preflight_root,
        expected_remaining_preflight_root_sha256=preflight_sha,
        remaining_review_root=review_root,
        expected_remaining_review_root_sha256=review_sha,
        rows=rows,
        expected_corpus_preflight_root_sha256=source_roots["corpus"],
        expected_corpus_review_root_sha256=source_roots["corpus_review"],
        expected_pilot_root_sha256=source_roots["pilot"],
        expected_pilot_review_root_sha256=source_roots["pilot_review"],
        expected_route_count=2,
        expected_source_invalid_count=1,
    )

    assert any(
        check["name"] == f"remaining_{source}_outcomes_closed" and not check["passed"]
        for check in checks
    )


def test_remaining_execution_rejects_inconsistent_review_checks(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        _remaining_execution_authorization_checks,
    )

    preflight_root, preflight_sha, review_root, _review_sha, context = (
        _remaining_authorization_artifacts(tmp_path)
    )
    path = review_root / "review.json"
    review = json.loads(path.read_text())
    review["checks"][0]["passed"] = False
    path.write_text(json.dumps(review))
    review_sha = _seal_test_artifact(review_root)
    rows, source_roots = context

    checks = _remaining_execution_authorization_checks(
        remaining_preflight_root=preflight_root,
        expected_remaining_preflight_root_sha256=preflight_sha,
        remaining_review_root=review_root,
        expected_remaining_review_root_sha256=review_sha,
        rows=rows,
        expected_corpus_preflight_root_sha256=source_roots["corpus"],
        expected_corpus_review_root_sha256=source_roots["corpus_review"],
        expected_pilot_root_sha256=source_roots["pilot"],
        expected_pilot_review_root_sha256=source_roots["pilot_review"],
        expected_route_count=2,
        expected_source_invalid_count=1,
    )

    assert any(
        check["name"] == "remaining_review_checks_integrity" and not check["passed"]
        for check in checks
    )


def test_execute_remaining_requires_preflight_review_source_chain(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import main

    with pytest.raises(
        ValueError,
        match="requires remaining preflight and review roots",
    ):
        main(
            [
                "--mode",
                "execute-remaining",
                "--preflight-root",
                str(tmp_path / "source-preflight"),
                "--expected-preflight-root-sha256",
                _sha("source-preflight"),
                "--review-root",
                str(tmp_path / "source-review"),
                "--expected-review-root-sha256",
                _sha("source-review"),
                "--pilot-root",
                str(tmp_path / "pilot"),
                "--expected-pilot-root-sha256",
                _sha("pilot"),
                "--pilot-review-root",
                str(tmp_path / "pilot-review"),
                "--expected-pilot-review-root-sha256",
                _sha("pilot-review"),
                "--template",
                str(BASE_CONFIG),
                "--dp-repo",
                str(tmp_path / "dp"),
                "--camp-head",
                "a" * 40,
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )


def test_pilot_preflight_accepts_complete_verified_asset_receipts() -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        verified_asset_receipts_complete,
    )

    complete = {f"asset-{index}": _sha(str(index)) for index in range(12)}
    complete["fixed_dp_head"] = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

    assert verified_asset_receipts_complete(complete) is True
    assert (
        verified_asset_receipts_complete({"fixed_dp_head": complete["fixed_dp_head"]})
        is False
    )


def _seal_test_artifact(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    manifest = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(root).as_posix()}\n"
        for path in files
    )
    (root / "SHA256SUMS").write_text(manifest, encoding="utf-8")
    root_sha256 = hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest()
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha256}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha256


def _reviewable_pilot(tmp_path: Path) -> tuple[Path, str, Path, str]:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        FIXED_DP_HEAD,
        execute_pilot_manifest,
    )

    manifest = _pilot_manifest(tmp_path)
    preflight_root = tmp_path / "preflight"
    preflight_root.mkdir()
    (preflight_root / "corpus_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    preflight_root_sha256 = _seal_test_artifact(preflight_root)

    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, output_dir, max_steps
        if config["routes"][0]["name"] == _sha("route:0"):
            raise RuntimeError("objective pilot failure")
        decision_sink(_snapshot())
        return {"status": "ok", "steps": []}

    pilot_root = tmp_path / "pilot"
    summary = execute_pilot_manifest(
        manifest,
        template,
        output_dir=pilot_root,
        run_arm=run_arm,
        expected_route_count=2,
        free_bytes=lambda: 20 * 1024**3,
    )
    # Reproduce already-sealed pilot metadata bug after executor is fixed.
    progress_path = pilot_root / "progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    progress["status"] = "running"
    progress_path.write_text(json.dumps(progress), encoding="utf-8")

    (pilot_root / "STATE.json").write_text(
        json.dumps({"status": summary["status"], "pid": 123, "seed": 24001}),
        encoding="utf-8",
    )
    execution = dict(summary)
    execution.update(
        {
            "source_preflight_root_sha256": preflight_root_sha256,
            "fixed_dp_head": FIXED_DP_HEAD,
            "next_work_target": "v24_native_corpus_capability_pilot_independent_review_only",
        }
    )
    (pilot_root / "execution.json").write_text(json.dumps(execution), encoding="utf-8")
    (pilot_root / "HEADS").write_text(
        "CAMP_HEAD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256={preflight_root_sha256}\n",
        encoding="ascii",
    )
    (pilot_root / "COMMAND").write_text("v24 native corpus execute-pilot\n")
    (pilot_root / "stdout.txt").write_text(json.dumps(execution) + "\n")
    (pilot_root / "stderr.txt").write_text("")
    (pilot_root / "run.exit").write_text("0\n")
    pilot_root_sha256 = _seal_test_artifact(pilot_root)
    return pilot_root, pilot_root_sha256, preflight_root, preflight_root_sha256


def test_pilot_independent_review_accepts_stale_progress_as_warning(
    tmp_path: Path,
) -> None:
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_pilot import (
        review_pilot,
    )

    pilot_root, pilot_sha, preflight_root, preflight_sha = _reviewable_pilot(tmp_path)
    review = review_pilot(
        pilot_root,
        pilot_sha,
        preflight_root,
        preflight_sha,
        expected_route_count=2,
    )

    assert review["status"] == "passed_with_warning"
    assert review["failed_count"] == 0
    assert review["warnings"] == ["progress_terminal_status_stale_running"]
    assert review["recomputed"]["failure_reason_counts"] == {
        "RuntimeError: objective pilot failure": 1
    }
    assert review["decision"]["authorized"] is True
    assert review["decision"]["seeds"] == [24002, 24003, 24004, 24005]
    assert review["decision"]["route_count"] == 2
    assert review["decision"]["tuning_authorized"] is False
    assert review["decision"]["outcome_access_authorized"] is False


def test_pilot_independent_review_fails_closed_on_tampered_snapshot(
    tmp_path: Path,
) -> None:
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_pilot import (
        review_pilot,
    )

    pilot_root, pilot_sha, preflight_root, preflight_sha = _reviewable_pilot(tmp_path)
    snapshot_path = next((pilot_root / "snapshots").glob("*.json"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["feature_payload"]["atom_matrix"][0][0] = 2.0
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    review = review_pilot(
        pilot_root,
        pilot_sha,
        preflight_root,
        preflight_sha,
        expected_route_count=2,
    )

    assert review["status"] == "failed"
    assert review["failed_count"] > 0
    assert review["warnings"] == []
    assert review["decision"]["authorized"] is False
    assert any("snapshot" in name for name in review["failed_checks"])


@pytest.mark.parametrize(
    "relative",
    (
        "receipts/train/unexpected.txt",
        "snapshots/unexpected.txt",
        f"snapshots/nested/{_sha('nested-snapshot')}.json",
    ),
)
def test_pilot_independent_review_rejects_extra_semantic_files(
    tmp_path: Path, relative: str
) -> None:
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_pilot import (
        review_pilot,
    )

    pilot_root, _pilot_sha, preflight_root, preflight_sha = _reviewable_pilot(tmp_path)
    extra = pilot_root / relative
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("unexpected", encoding="utf-8")
    pilot_sha = _seal_test_artifact(pilot_root)

    review = review_pilot(
        pilot_root,
        pilot_sha,
        preflight_root,
        preflight_sha,
        expected_route_count=2,
    )

    assert review["status"] == "failed"
    assert review["warnings"] == []
    assert review["decision"]["authorized"] is False
    assert any("inventory" in name for name in review["failed_checks"])


@pytest.mark.parametrize(
    ("field", "drifted"),
    (
        ("phase", "wrong_phase"),
        ("corpus_steps", 63),
        ("sample_every_ticks", 2),
        ("theoretical_max_snapshots", 127),
    ),
)
def test_pilot_independent_review_rejects_protocol_drift(
    tmp_path: Path, field: str, drifted: object
) -> None:
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_pilot import (
        review_pilot,
    )

    pilot_root, _pilot_sha, preflight_root, preflight_sha = _reviewable_pilot(tmp_path)
    for name in ("pilot_summary.json", "execution.json"):
        path = pilot_root / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload[field] = drifted
        path.write_text(json.dumps(payload), encoding="utf-8")
    pilot_sha = _seal_test_artifact(pilot_root)

    review = review_pilot(
        pilot_root,
        pilot_sha,
        preflight_root,
        preflight_sha,
        expected_route_count=2,
    )

    assert review["status"] == "failed"
    assert review["warnings"] == []
    assert review["decision"]["authorized"] is False
    assert any("protocol" in name for name in review["failed_checks"])


def test_pilot_executor_rewrites_progress_with_terminal_aggregate(
    tmp_path: Path,
) -> None:
    from scripts.integrations.execute_diffusion_planner_v24_native_corpus import (
        execute_pilot_manifest,
    )

    manifest = _pilot_manifest(tmp_path)
    template = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, config, output_dir, max_steps
        decision_sink(_snapshot())
        return {"status": "ok", "steps": []}

    output_dir = tmp_path / "terminal-progress"
    summary = execute_pilot_manifest(
        manifest,
        template,
        output_dir=output_dir,
        run_arm=run_arm,
        expected_route_count=2,
        free_bytes=lambda: 20 * 1024**3,
    )
    progress = json.loads((output_dir / "progress.json").read_text())

    assert progress["schema"] == "camp_dp_v24_native_corpus_pilot_progress_v1"
    assert progress["status"] == summary["status"] == "complete"
    assert progress["last_completed_row"] == 2
    assert progress["free_disk_gib"] == 20.0
    for name in (
        "planned_route_seed_runs",
        "complete_route_seed_runs",
        "failed_route_seed_runs",
        "retained_route_seed_runs",
        "pending_route_seed_runs",
        "snapshot_count",
    ):
        assert progress[name] == summary[name]
