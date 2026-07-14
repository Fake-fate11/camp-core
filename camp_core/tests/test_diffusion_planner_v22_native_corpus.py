import hashlib
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "integrations" / "diffusion_planner_v22_native_corpus.json"
BASE_NATIVE_CONFIG = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"
SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "materialize_diffusion_planner_v22_native_corpus.py"
)


def _module():
    from scripts.integrations import materialize_diffusion_planner_v22_native_corpus

    return materialize_diffusion_planner_v22_native_corpus


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _route(tmp_path: Path, split: str) -> dict:
    path = tmp_path / f"{split}.pkl"
    path.write_text(split, encoding="utf-8")
    return {
        "identity_sha256": _sha(f"identity:{split}"),
        "group_sha256": _sha(f"group:{split}"),
        "logical_map_sha256": (
            "a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036"
        ),
        "route_asset": {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        "route_spec": {
            "map_path": (
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            )
        },
    }


def _manifest(tmp_path: Path) -> dict:
    routes = {split: _route(tmp_path, split) for split in ("train", "calibration", "holdout")}
    seeds = {"train": [22001, 22002], "calibration": [22101], "holdout": [22201]}
    expected_pairs = []
    splits = {}
    for split, route in routes.items():
        splits[split] = {
            "group_sha256": [route["group_sha256"]],
            "routes": [route],
            "seed_namespace": seeds[split],
        }
        for seed in seeds[split]:
            expected_pairs.append(
                {
                    "split": split,
                    "route_identity_sha256": route["identity_sha256"],
                    "seed": seed,
                    "expected_arms": ["dp", "camp"],
                    "receipt_key": f"{split}/{route['identity_sha256']}/seed_{seed}/pair.json",
                }
            )
    return {
        "schema_version": "v22_route_family_split_manifest_v1",
        "source_only": True,
        "outcome_fields_consumed": [],
        "split_freeze_sha256": _sha("split-freeze"),
        "splits": splits,
        "expected_pairs": expected_pairs,
        "pilot_route_identity_sha256": [routes["calibration"]["identity_sha256"]],
        "main_route_identity_sha256": [routes["holdout"]["identity_sha256"]],
    }


def _config(manifest: dict) -> dict:
    return {
        "schema_version": "camp_dp_v22_native_corpus_v1",
        "source_split": {
            "split_freeze_sha256": manifest["split_freeze_sha256"],
        },
        "collection": {
            "execution_splits": ["train"],
            "sample_every_ticks": 5,
            "native_dt_s": 0.1,
            "snapshot_interval_s": 0.5,
            "max_steps": 64,
            "expected_route_counts": {"train": 1, "calibration": 1, "holdout": 1},
            "expected_seed_counts": {"train": 2, "calibration": 1, "holdout": 1},
            "expected_train_route_seed_runs": 2,
            "theoretical_max_train_snapshots": 26,
            "learning_curve_levels": [5000, 10000, 20000, 50000],
            "behavior_policy": "v18_ablation_corpus_collection_only",
            "candidate_k": 8,
            "selection_policy": "v22_source_valid",
            "score_contract": "score_k(w)=a_k^T w",
            "nonnegative_simplex": True,
        },
        "feature_payload_fields": [
            "atom_matrix",
            "source_valid_mask",
            "candidate_row_sha256",
        ],
        "receipt_only_identity_fields": [
            "logical_map_sha256",
            "route_identity_sha256",
            "group_sha256",
            "split",
            "seed",
        ],
        "holdout_execution_authorized": False,
        "calibration_execution_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "claim_authorized": False,
    }


def test_tracked_preflight_freezes_reachable_train_ceiling() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    collection = config["collection"]

    assert config["source_split"]["split_freeze_sha256"] == (
        "00394a1ad67f6d760f8c12f28532c6f661663fe7709a233adb79dc3b05904bc8"
    )
    assert collection["execution_splits"] == ["train"]
    assert collection["expected_route_counts"] == {
        "train": 4,
        "calibration": 30,
        "holdout": 100,
    }
    assert collection["expected_seed_counts"] == {
        "train": 8,
        "calibration": 3,
        "holdout": 5,
    }
    assert collection["expected_train_route_seed_runs"] == 32
    assert collection["sample_every_ticks"] == 5
    assert collection["snapshot_interval_s"] == 0.5
    assert collection["max_steps"] == 64
    assert collection["theoretical_max_train_snapshots"] == 416
    assert collection["learning_curve_levels"] == [5000, 10000, 20000, 50000]
    assert collection["behavior_policy"] == "v18_ablation_corpus_collection_only"
    assert config["holdout_execution_authorized"] is False
    assert config["calibration_execution_authorized"] is False
    assert config["claim_authorized"] is False


def test_preflight_accepts_train_only_and_reports_no_reachable_tier(tmp_path: Path) -> None:
    module = _module()
    manifest = _manifest(tmp_path)
    summary = module.validate_corpus_preflight(_config(manifest), manifest)

    assert summary["status"] == "passed_with_sub_5k_training_ceiling"
    assert summary["train_route_seed_runs"] == 2
    assert summary["theoretical_max_train_snapshots"] == 26
    assert summary["reachable_learning_curve_levels"] == []
    assert summary["run_all_available_snapshots"] is True
    assert summary["model_loaded"] is False
    assert summary["simulator_executed"] is False
    assert summary["holdout_outcomes_read"] is False
    assert summary["next_work_target"] == "v22_native_train_corpus_execution_only"


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ("holdout", "train-only"),
        ("identity_feature", "feature payload"),
        ("asset", "route asset SHA256"),
    ),
)
def test_preflight_rejects_holdout_identity_features_or_mutated_asset(
    tmp_path: Path, mutation: str, match: str
) -> None:
    module = _module()
    manifest = _manifest(tmp_path)
    config = _config(manifest)
    if mutation == "holdout":
        config["collection"]["execution_splits"] = ["train", "holdout"]
    elif mutation == "identity_feature":
        config["feature_payload_fields"].append("route_id")
    else:
        Path(manifest["splits"]["train"]["routes"][0]["route_asset"]["path"]).write_text(
            "mutated", encoding="utf-8"
        )

    with pytest.raises(ValueError, match=match):
        module.validate_corpus_preflight(config, manifest)


def test_corpus_script_has_no_parallel_native_replay_loop() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "run_route_replay" not in text
    assert "advance_scene_mpc" not in text
    assert "build_native_arm_runner" in text


def _snapshot() -> dict:
    candidate_sha = [_sha(f"row:{index}") for index in range(8)]
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": np.ones((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": candidate_sha,
        },
        "sidecar": {
            "tick_index": 5,
            "candidate_tensor_sha256_before": _sha("tensor"),
            "candidate_tensor_sha256_after": _sha("tensor"),
            "causal_input_sha256": _sha("causal"),
            "default_output_sha256": candidate_sha[0],
            "candidate0_sha256": candidate_sha[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": candidate_sha[0],
                "candidate0_sha256": candidate_sha[0],
                "native_ranked_k8": False,
            },
            "physical_feasible_mask": [False] * 8,
            "all_k_high_risk": True,
            "offline_label_provenance": (
                "pending_train_only_offline_supervision_sidecar"
            ),
        },
    }


def test_content_addressed_writer_keeps_identity_in_sidecar_and_deduplicates(
    tmp_path: Path,
) -> None:
    module = _module()
    writer = module.CorpusSnapshotWriter(
        output_dir=tmp_path,
        split="train",
        logical_map_sha256=_sha("map"),
        route_identity_sha256=_sha("route"),
        group_sha256=_sha("group"),
        seed=22001,
    )

    first = writer(_snapshot())
    second = writer(_snapshot())

    assert first == second
    assert len(list((tmp_path / "snapshots").glob("*.json"))) == 1
    payload = json.loads((tmp_path / "snapshots" / f"{first}.json").read_text())
    assert set(payload["feature_payload"]) == {
        "atom_matrix",
        "source_valid_mask",
        "candidate_row_sha256",
    }
    assert not set(payload["feature_payload"]).intersection(
        {"logical_map_sha256", "route_identity_sha256", "group_sha256", "split", "seed"}
    )
    assert payload["sidecar"]["split"] == "train"
    assert payload["sidecar"]["seed"] == 22001
    assert writer.snapshot_sha256 == [first]


def test_writer_rejects_holdout_or_candidate_tensor_mismatch(tmp_path: Path) -> None:
    module = _module()
    kwargs = {
        "output_dir": tmp_path,
        "logical_map_sha256": _sha("map"),
        "route_identity_sha256": _sha("route"),
        "group_sha256": _sha("group"),
        "seed": 22001,
    }
    with pytest.raises(ValueError, match="holdout"):
        module.CorpusSnapshotWriter(split="holdout", **kwargs)

    writer = module.CorpusSnapshotWriter(split="train", **kwargs)
    snapshot = _snapshot()
    snapshot["sidecar"]["candidate_tensor_sha256_after"] = _sha("mutated")
    with pytest.raises(ValueError, match="candidate tensor SHA256"):
        writer(snapshot)


@pytest.mark.parametrize(
    "mutation",
    ("default_output", "candidate0", "identity", "candidate_row0"),
)
def test_writer_rejects_missing_or_mismatched_default_candidate0_identity(
    tmp_path: Path, mutation: str
) -> None:
    module = _module()
    writer = module.CorpusSnapshotWriter(
        output_dir=tmp_path,
        split="train",
        logical_map_sha256=_sha("map"),
        route_identity_sha256=_sha("route"),
        group_sha256=_sha("group"),
        seed=22001,
    )
    snapshot = _snapshot()
    if mutation == "default_output":
        del snapshot["sidecar"]["default_output_sha256"]
    elif mutation == "candidate0":
        snapshot["sidecar"]["candidate0_sha256"] = _sha("drifted")
    elif mutation == "identity":
        snapshot["sidecar"]["default_candidate0_identity"]["elementwise_equal"] = False
    else:
        snapshot["feature_payload"]["candidate_row_sha256"][0] = _sha("drifted")

    with pytest.raises(ValueError, match="operational default/candidate 0 identity"):
        writer(snapshot)


def test_writer_retains_failed_route_seed_receipt(tmp_path: Path) -> None:
    module = _module()
    writer = module.CorpusSnapshotWriter(
        output_dir=tmp_path,
        split="train",
        logical_map_sha256=_sha("map"),
        route_identity_sha256=_sha("route"),
        group_sha256=_sha("group"),
        seed=22001,
    )
    path = writer.write_run_receipt(
        status="failed",
        failure_stage="tracker",
        failure_reason="objective execution failure",
    )

    receipt = json.loads(path.read_text())
    assert receipt["status"] == "failed"
    assert receipt["failure_stage"] == "tracker"
    assert receipt["failure_reason"] == "objective execution failure"
    assert receipt["snapshot_sha256"] == []
    assert receipt["retained_in_denominator"] is True


def test_corpus_run_config_injects_only_frozen_train_seed(tmp_path: Path) -> None:
    module = _module()
    runner = __import__(
        "scripts.integrations.run_diffusion_planner_dp_camp_v21_native",
        fromlist=["validate_v22_corpus_run_config"],
    )
    route = _route(tmp_path, "train")
    base = json.loads(BASE_NATIVE_CONFIG.read_text(encoding="utf-8"))

    run_config = module.build_corpus_run_config(
        base, route, seed=22001, max_steps=64
    )

    runner.validate_v22_corpus_run_config(run_config)
    assert run_config["seeds"]["scenario"] == 22001
    assert run_config["seeds"]["candidate"] == 22001
    assert run_config["spawn_config"]["seed"] == 22001
    assert run_config["routes"] == [
        {
            "name": route["identity_sha256"],
            "path": route["route_asset"]["path"],
            "sha256": route["route_asset"]["sha256"],
        }
    ]
    assert run_config["protocol"]["route_role"] == "train_corpus_collection"
    assert run_config["protocol"]["holdout_access_authorized"] is False


def test_execution_harness_attempts_only_train_rows_and_writes_receipts(
    tmp_path: Path,
) -> None:
    module = _module()
    manifest = _manifest(tmp_path)
    config = _config(manifest)
    base = json.loads(BASE_NATIVE_CONFIG.read_text(encoding="utf-8"))
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        calls.append((route["name"], arm, config["seeds"]["scenario"], max_steps))
        decision_sink(_snapshot())
        return {"status": "ok"}

    output = tmp_path / "corpus"
    summary = module.execute_train_manifest(
        config,
        manifest,
        base,
        output_dir=output,
        run_arm=run_arm,
    )

    train_identity = manifest["splits"]["train"]["routes"][0]["identity_sha256"]
    assert calls == [
        (train_identity, "camp", 22001, 64),
        (train_identity, "camp", 22002, 64),
    ]
    assert summary["planned_route_seed_runs"] == 2
    assert summary["complete_route_seed_runs"] == 2
    assert summary["failed_route_seed_runs"] == 0
    assert summary["snapshot_count"] == 2
    assert summary["snapshot_count_by_source_stratum"] == {"normal": 2}
    assert summary["all_k_high_risk_snapshot_count"] == 2
    assert len(summary["route_seed_timings"]) == 2
    assert summary["wall_clock_s"] >= 0.0
    receipts = list((output / "receipts" / "train").rglob("seed_*.json"))
    assert len(receipts) == 2
    assert all(json.loads(path.read_text())["status"] == "ok" for path in receipts)
    assert all(json.loads(path.read_text())["wall_clock_s"] >= 0.0 for path in receipts)
    assert not (output / "receipts" / "calibration").exists()
    assert not (output / "receipts" / "holdout").exists()


def test_execution_harness_retains_failure_and_continues(tmp_path: Path) -> None:
    module = _module()
    manifest = _manifest(tmp_path)
    config = _config(manifest)
    base = json.loads(BASE_NATIVE_CONFIG.read_text(encoding="utf-8"))
    calls = []

    def run_arm(*, route, arm, config, output_dir, max_steps, decision_sink):
        del route, arm, output_dir, max_steps
        seed = config["seeds"]["scenario"]
        calls.append(seed)
        if seed == 22001:
            raise RuntimeError("objective execution failure")
        decision_sink(_snapshot())
        return {"status": "ok"}

    output = tmp_path / "corpus"
    summary = module.execute_train_manifest(
        config,
        manifest,
        base,
        output_dir=output,
        run_arm=run_arm,
    )

    assert calls == [22001, 22002]
    assert summary["status"] == "complete_with_retained_failures"
    assert summary["complete_route_seed_runs"] == 1
    assert summary["failed_route_seed_runs"] == 1
    receipts = [
        json.loads(path.read_text())
        for path in (output / "receipts" / "train").rglob("seed_*.json")
    ]
    failed = next(item for item in receipts if item["status"] == "failed")
    assert failed["failure_stage"] == "native_arm_execution"
    assert failed["retained_in_denominator"] is True
