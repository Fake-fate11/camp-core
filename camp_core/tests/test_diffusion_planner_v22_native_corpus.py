import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "integrations" / "diffusion_planner_v22_native_corpus.json"
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
        "logical_map_sha256": _sha("map"),
        "route_asset": {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
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
