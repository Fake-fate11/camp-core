"""Materialize the exact training-only 1000-pool manifest before model calls."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_training_support_reference import (  # noqa: E402
    CAPACITY_FLOOR_BYTES,
    FIXED_DP_HEAD,
    POOL_COUNT,
    build_clone_payload,
    canonical_bytes,
    finalize_pool_manifest_entry,
    materialize_latent,
    select_finalized_manifest_entries,
    sha256_bytes,
    validate_contract,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    V25ControlledSceneAdapter,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    build_native_arm_runner,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    _attach_semantic_clone_authority,
    _load_formal_plan,
    build_controlled_train_config,
)


TRAINING_ARTIFACT = Path(
    "/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST"
)
TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_CORPUS = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_a17_corrected_full_corpus_19bcebe6_e591ab98ae575ed6"
)
TRAINING_CORPUS_ROOT = (
    "97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd"
)
SOURCE_CENSUS = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_a17_route_signal_source_census_c7b1cdba_20260720T124603CST"
)
SOURCE_CENSUS_ROOT = (
    "252862ea50a6f1be906403b136c170ef16dbb2246568821bcbba9283290b0dbb"
)
FAIR_PREFLIGHT = Path(
    "/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_preflight_"
    "67308ac0_ed0d298c"
)
FAIR_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
B4_PREOPEN = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST"
)
B4_PREOPEN_ROOT = (
    "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
)
PROBE_TEMPLATE = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)
INPUT_TENSOR_NAMES = (
    "delay",
    "ego_agent_past",
    "ego_current_state",
    "ego_shape",
    "goal_pose",
    "lanes",
    "lanes_has_speed_limit",
    "lanes_speed_limit",
    "line_strings",
    "neighbor_agents_past",
    "polygons",
    "route_lanes",
    "route_lanes_has_speed_limit",
    "route_lanes_speed_limit",
    "sampled_trajectories",
    "static_objects",
    "turn_indicators",
)


class _CapturedBeforeModel(RuntimeError):
    pass


class _SceneProxy:
    def __init__(self, delegate: V25ControlledSceneAdapter) -> None:
        self.delegate = delegate
        self.scene: Any = None

    def __call__(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        self.scene = scene
        return self.delegate(scene, tick_index)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _route_assets(cases: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    result = {}
    for case in cases:
        identity = str(case["route_identity_sha256"])
        path = TRAINING_CORPUS / "routes" / f"{identity}.pkl"
        if not path.is_file():
            raise FileNotFoundError(path)
        result[identity] = {"path": str(path), "sha256": _sha_file(path)}
    return result


def _source_cases(
    *, dp_repo: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan, _formal_root = _load_formal_plan()
    census = _json(SOURCE_CENSUS / "route_signal_source_receipts.json")
    cases = _attach_semantic_clone_authority(
        [deepcopy(row) for row in plan["train"] if row["runner_eligible"]],
        dp_repo=dp_repo,
        r0_source_artifact=SOURCE_CENSUS,
        expected_camp_source_head=str(census["camp_source_head"]),
        r0_source_root_sha256=SOURCE_CENSUS_ROOT,
    )
    source_rows = [row for row in census["cases"] if row["runner_eligible"]]
    by_id = {str(row["scenario_id"]): row for row in source_rows}
    if (
        len(cases) != 1500
        or len(source_rows) != 1500
        or set(by_id) != {str(row["scenario_id"]) for row in cases}
    ):
        raise RuntimeError("training source/case denominator drifted")
    return cases, source_rows


def _capture_one(
    *,
    runner: Any,
    native_module: Any,
    case: dict[str, Any],
    config: dict[str, Any],
    work: Path,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, Any], float]:
    captured: dict[str, Any] = {}
    causal: dict[str, np.ndarray] = {}
    proxy = _SceneProxy(
        V25ControlledSceneAdapter(
            case,
            mapped_signal_authority=case.get("mapped_signal_authority"),
            no_signal_authority=case.get("no_signal_authority"),
        )
    )
    original = native_module._model_outputs  # noqa: SLF001

    def stop_before_model(_model: Any, data: Mapping[str, Any]) -> Any:
        arrays = {}
        for name, value in data.items():
            if hasattr(value, "detach"):
                value = value.detach().cpu().numpy()
            arrays[name] = np.ascontiguousarray(np.asarray(value))
        if tuple(sorted(arrays)) != INPUT_TENSOR_NAMES:
            raise RuntimeError("actual model input tensor keyset drifted")
        if any(value.shape[0] != 1 for value in arrays.values()):
            raise RuntimeError("captured model input is not one ego row")
        arrays["sampled_trajectories"] = np.zeros(
            (1, 321, 81, 4), dtype=np.float32
        )
        captured["inputs"] = arrays
        if proxy.scene is None:
            raise RuntimeError("scene adapter did not bind exact source scene")
        captured["signal"] = proxy.causal_signal_atom_input(proxy.scene, 0)
        captured["dt"] = float(proxy.scene.dt)
        raise _CapturedBeforeModel

    native_module._model_outputs = stop_before_model  # noqa: SLF001
    try:
        try:
            runner(
                route=config["routes"][0],
                arm="camp",
                config=config,
                output_dir=work,
                max_steps=1,
                scene_adapter=proxy,
                causal_input_sink=lambda tick, arrays: causal.update(
                    {
                        key: np.ascontiguousarray(np.asarray(value))
                        for key, value in arrays.items()
                    }
                )
                if tick == 0
                else None,
            )
        except _CapturedBeforeModel:
            pass
    finally:
        native_module._model_outputs = original  # noqa: SLF001
    if "inputs" not in captured or not causal or "signal" not in captured:
        raise RuntimeError("input-only capture did not reach exact pre-model boundary")
    return captured["inputs"], causal, captured["signal"], captured["dt"]


def _inventory_layers_from_fair() -> dict[str, dict[str, set[str]]]:
    receipt = _json(FAIR_PREFLIGHT / "receipt.json")
    output = {}
    for label, key in (
        ("development_calibration", "calibration_manifests"),
        ("independent_validation", "validation_manifests"),
        ("legacy_nonholdout", "validation_manifests"),
    ):
        rows = receipt[key]
        output[label] = {
            "route_geometry": {
                str(row["source_scene"]["route_asset_sha256"]) for row in rows
            },
            "source": {
                str(row["source_scene"]["scenario_source_content_sha256"])
                for row in rows
            },
            "state": {str(row["actual_state_sha256"]) for row in rows},
            "seed": {
                sha256_bytes(
                    canonical_bytes(
                        {
                            "scenario_seed": row["scenario_seed"],
                            "source_record_sha256": row["source_scene"][
                                "scenario_source_content_sha256"
                            ],
                        }
                    )
                )
                for row in rows
            },
            "latent_instance": {
                str(row["actual_latent_tensor_manifest"]["manifest_sha256"])
                for row in rows
            },
        }
    return output


def _inventory_layers_from_b4() -> dict[str, set[str]]:
    cases = json.loads(
        (B4_PREOPEN / "prepared_runtime_cases.json").read_text(encoding="utf-8")
    )
    if type(cases) is not list or len(cases) != 100:
        raise RuntimeError("B4 prepared input denominator drifted")
    route = {str(row["case"]["route_identity_sha256"]) for row in cases}
    source = {str(row["scenario_identity_sha256"]) for row in cases}
    state = {
        sha256_bytes(
            canonical_bytes(
                {
                    "scenario_identity_sha256": row["scenario_identity_sha256"],
                    "route_identity_sha256": row["case"]["route_identity_sha256"],
                    "source_map_sha256": row["case"]["source_map_sha256"],
                }
            )
        )
        for row in cases
    }
    seeds = {
        sha256_bytes(canonical_bytes(row["case"]["seeds"])) for row in cases
    }
    # The B2/B3/B4 input identity is common across its one-time attempts; the
    # exact B4 prepared-input bytes are the terminal, outcome-free inventory.
    return {
        "route_geometry": route,
        "source": source,
        "state": state,
        "seed": seeds,
        "latent_instance": set(),
    }


def _zero_overlap(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    training = {
        layer: {str(row["overlap_keys"][layer]) for row in entries}
        for layer in (
            "route_geometry",
            "source",
            "state",
            "seed",
            "latent_instance",
        )
    }
    forbidden = _inventory_layers_from_fair()
    fresh = _inventory_layers_from_b4()
    forbidden.update(
        {"Fresh_B2": fresh, "Fresh_B3": fresh, "Fresh_B4": fresh}
    )
    report = {}
    for split, layers in forbidden.items():
        intersections = {
            layer: sorted(training[layer].intersection(layers[layer]))
            for layer in training
        }
        if any(intersections.values()):
            raise RuntimeError(f"training manifest overlaps {split}")
        report[split] = {
            "forbidden_counts": {
                layer: len(layers[layer]) for layer in training
            },
            "intersection_counts": {
                layer: len(intersections[layer]) for layer in training
            },
        }
    return report


def materialize(
    *,
    repo: Path,
    fixed_dp_repo: Path,
    implementation_head: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    output: Path,
    device: str,
) -> str:
    import scripts.integrations.run_diffusion_planner_dp_camp_v21_native as native

    if (
        output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(
            fixed_dp_repo, "status", "--porcelain=v1", "--untracked-files=no"
        )
    ):
        raise RuntimeError("preflight tracked authority drifted")
    for path, root, label in (
        (contract_dir, contract_root, "training-support contract"),
        (contract_review_dir, contract_review_root, "training-support contract review"),
        (TRAINING_ARTIFACT, TRAINING_ROOT, "accepted training"),
        (TRAINING_CORPUS, TRAINING_CORPUS_ROOT, "accepted training corpus"),
        (SOURCE_CENSUS, SOURCE_CENSUS_ROOT, "accepted source census"),
        (FAIR_PREFLIGHT, FAIR_PREFLIGHT_ROOT, "fair-pool input preflight"),
        (B4_PREOPEN, B4_PREOPEN_ROOT, "Fresh B4 preopen"),
    ):
        verify_complete_seal(path, root, label=label)
    contract = validate_contract(_json(contract_dir / "contract.json"))
    if (
        contract["implementation_head"] != implementation_head
        or contract["exact_dirs"]["preflight"] != str(output)
        or contract["exact_dirs"]["contract"] != str(contract_dir)
        or contract["exact_dirs"]["contract_review"] != str(contract_review_dir)
    ):
        raise RuntimeError("preflight contract binding drifted")

    cases, source_rows = _source_cases(dp_repo=fixed_dp_repo)
    source_by_id = {str(row["scenario_id"]): row for row in source_rows}
    case_by_id = {str(row["scenario_id"]): row for row in cases}
    routes = _route_assets(cases)
    template = _json(PROBE_TEMPLATE)
    runner = build_native_arm_runner(
        build_controlled_train_config(
            template,
            cases[0],
            routes[str(cases[0]["route_identity_sha256"])],
        ),
        device=device,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    capture_dir = staging / "eligible_capture"
    capture_dir.mkdir()
    finalized = []
    try:
        for ordinal, scenario_id in enumerate(sorted(case_by_id)):
            case = case_by_id[scenario_id]
            config = build_controlled_train_config(
                template, case, routes[str(case["route_identity_sha256"])]
            )
            work = staging / "capture_work" / f"{ordinal:04d}"
            inputs, causal, signal, dt = _capture_one(
                runner=runner,
                native_module=native,
                case=case,
                config=config,
                work=work,
            )
            base = build_clone_payload(source_by_id[scenario_id])
            entry = finalize_pool_manifest_entry(
                base, actual_input_tensors=inputs
            )
            entry["source_case_id"] = scenario_id
            entry["source_case_ordinal"] = ordinal
            entry["manifest_entry_sha256"] = sha256_bytes(
                canonical_bytes(
                    {
                        key: value
                        for key, value in entry.items()
                        if key != "manifest_entry_sha256"
                    }
                )
            )
            finalized.append(entry)
            pool = capture_dir / entry["clone_key_sha256"]
            pool.mkdir()
            np.savez(pool / "model_input.npz", **inputs)
            np.savez(pool / "causal_input.npz", **causal)
            (pool / "causal_signal_atom_input.json").write_bytes(
                canonical_bytes(signal)
            )
            (pool / "source_case.json").write_bytes(canonical_bytes(case))
            (pool / "dt.txt").write_text(f"{dt:.17g}\n", "ascii")
            shutil.rmtree(work, ignore_errors=True)

        manifest = select_finalized_manifest_entries(finalized)
        selected_keys = {
            row["clone_key_sha256"] for row in manifest["entries"]
        }
        selected_entries = [
            row for row in finalized if row["clone_key_sha256"] in selected_keys
        ]
        overlap = _zero_overlap(selected_entries)
        pools = staging / "pools"
        pools.mkdir()
        for row in manifest["entries"]:
            source = capture_dir / row["clone_key_sha256"]
            destination = pools / row["pool_id"].replace(":", "_")
            os.replace(source, destination)
            latent = materialize_latent(int(row["latent_manifest"]["seed"]))
            (destination / "latent_tensor.f32le").write_bytes(
                latent.tobytes(order="C")
            )
        shutil.rmtree(capture_dir)
        shutil.rmtree(staging / "capture_work", ignore_errors=True)
        actual_input_bytes = sum(
            path.stat().st_size for path in pools.rglob("*") if path.is_file()
        )
        projected_raw_bytes = POOL_COUNT * (
            8 * 80 * 4 * 4
            + 8 * 32 * 80 * 4 * 4
            + 8 * 14 * 8
            + 2 * 8 * 8
            + 64 * 1024
        )
        projected_total = actual_input_bytes + projected_raw_bytes
        free_before = shutil.disk_usage(output.parent).free
        if free_before - projected_raw_bytes < CAPACITY_FLOOR_BYTES:
            raise RuntimeError("projected end free bytes falls below 10 GiB floor")
        report = {
            "schema_version": (
                "camp_dp_v25_batch8_training_support_reference_preflight_v1"
            ),
            "status": "passed_before_first_training_support_model_call",
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "manifest_sha256": manifest["manifest_sha256"],
            "eligible_manifest_entries_sha256": sha256_bytes(
                canonical_bytes(finalized)
            ),
            "eligible_unique_pool_count": manifest["eligible_unique_pool_count"],
            "selected_pool_count": manifest["selected_pool_count"],
            "zero_overlap": overlap,
            "capacity": {
                "free_before_bytes": free_before,
                "preflight_bytes": actual_input_bytes,
                "projected_raw_increment_bytes": projected_raw_bytes,
                "projected_total_bytes": projected_total,
                "projected_end_free_bytes": free_before - projected_raw_bytes,
                "floor_bytes": CAPACITY_FLOOR_BYTES,
                "passed": True,
            },
            "model_pool_selector_call_count_before_receipt": 0,
            "no_drop_no_replace": True,
            "outcome_read": False,
            "old_artifact_or_cas_write_count": 0,
        }
        (staging / "eligible_manifest_entries.json").write_bytes(
            canonical_bytes(finalized)
        )
        (staging / "manifest.json").write_bytes(canonical_bytes(manifest))
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging, label="V25 batch8 training-support input preflight"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 training-support input preflight"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    print(
        materialize(
            repo=args.repo,
            fixed_dp_repo=args.fixed_dp_repo,
            implementation_head=args.implementation_head,
            contract_dir=args.contract,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review,
            contract_review_root=args.contract_review_root,
            output=args.output,
            device=args.device,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
