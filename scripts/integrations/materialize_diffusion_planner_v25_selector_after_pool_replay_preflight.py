"""Freeze sealed inputs and selector assets for zero-model selector replay."""

from __future__ import annotations

import argparse
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
PACKAGE = ROOT / "camp_core"
for _path in (ROOT, PACKAGE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay import (  # noqa: E402
    CORRECTED_PREFLIGHT_REVIEW_ROOT,
    CORRECTED_PREFLIGHT_ROOT,
    CORRECTED_RAW_REVIEW_ROOT,
    CORRECTED_RAW_ROOT,
    EXACT_DIRS,
    FIXED_DP_HEAD,
    OBSERVATION_NORMALIZER_SHA256,
    TENSOR_CONVERTER_SHA256,
    TRAINING_MODEL_PARAMETERS_FILE_SHA256,
    TRAINING_REVIEW_ROOT,
    TRAINING_ROOT,
    TRAINING_SCALE_FILE_SHA256,
    TRAINING_STATIC_WEIGHTS_FILE_SHA256,
    array_sha256,
    assert_python_runtime,
    canonical_bytes,
    causal_input_from_model_input,
    pool_id_from_preimages,
    sha256_bytes,
    sha256_file,
    validate_contract,
)
from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    causal_input_receipt,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (  # noqa: E402
    _build_no_signal_chain,
)


AUTODL = Path("/root/autodl-tmp")
DP = AUTODL / "Diffusion-Planner"
CORRECTED_PREFLIGHT = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_preflight_v1_dc76fbc8"
)
CORRECTED_PREFLIGHT_REVIEW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_preflight_review_v1_dc76fbc8"
)
CORRECTED_RAW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_v1_dc76fbc8"
)
CORRECTED_RAW_REVIEW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_review_v1_dc76fbc8"
)
TRAINING = AUTODL / "camp_dp_v25_camp_training_863e28da_20260722T103219CST"
TRAINING_REVIEW = AUTODL / (
    "camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST"
)
PROBE_CONFIG = AUTODL / (
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.ascontiguousarray(np.array(archive[name], copy=True))
            for name in archive.files
        }


def _find_key(value: Any, key: str) -> list[Any]:
    found = []
    if isinstance(value, Mapping):
        for name, child in value.items():
            if name == key:
                found.append(child)
            found.extend(_find_key(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_key(child, key))
    return found


def _normalization_authority() -> tuple[Path, dict[str, Any]]:
    config = _json(PROBE_CONFIG)
    args_path = Path(config["fixed_dp"]["args_json"]["path"])
    args = _json(args_path)
    values = _find_key(args, "normalization_file_path")
    if len(values) != 1 or not isinstance(values[0], str):
        raise RuntimeError("normalization path authority is not unique")
    raw = Path(values[0])
    candidates = (
        (raw,) if raw.is_absolute() else (args_path.parent / raw, DP / raw)
    )
    matches = [path.resolve() for path in candidates if path.is_file()]
    if len(set(matches)) != 1:
        raise RuntimeError("normalization path did not resolve uniquely")
    path = matches[0]
    payload = _json(path)
    for name, row in payload.items():
        if name in {"ego", "neighbor"}:
            continue
        if (
            type(row) is not dict
            or set(row) != {"mean", "std"}
            or not np.isfinite(np.asarray(row["mean"], dtype=np.float64)).all()
            or not np.isfinite(np.asarray(row["std"], dtype=np.float64)).all()
            or np.any(np.asarray(row["std"], dtype=np.float64) <= 0.0)
        ):
            raise RuntimeError(f"normalization row drifted: {name}")
    return path, payload


def _roundtrip(
    source: Mapping[str, np.ndarray],
    causal: Mapping[str, np.ndarray],
    normalization: Mapping[str, Mapping[str, Any]],
) -> None:
    reconstructed = {}
    for name, value in causal.items():
        if name == "version":
            continue
        array = np.asarray(value)
        if name == "ego_agent_past":
            array = np.stack(
                (
                    array[..., 0],
                    array[..., 1],
                    np.cos(array[..., 2]),
                    np.sin(array[..., 2]),
                ),
                axis=-1,
            ).astype(np.float32)
        elif name == "goal_pose":
            array = np.asarray(
                (
                    array[0],
                    array[1],
                    np.cos(array[2]),
                    np.sin(array[2]),
                ),
                dtype=np.float32,
            )
        array = np.ascontiguousarray(array[None, ...])
        if name in normalization:
            row = normalization[name]
            mean = np.asarray(row["mean"], dtype=np.float32)
            std = np.asarray(row["std"], dtype=np.float32)
            mask = np.sum(np.not_equal(array, 0), axis=-1) == 0
            array = (array - mean) / std
            array[mask] = 0
        reconstructed[name] = np.ascontiguousarray(array)
    for name, expected in source.items():
        if name in {"delay", "sampled_trajectories"}:
            continue
        observed = reconstructed[name].astype(expected.dtype, copy=False)
        if not np.array_equal(observed, expected):
            raise RuntimeError(f"normalizer inverse roundtrip drifted: {name}")


def materialize(
    *,
    repo: Path,
    implementation_head: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    output: Path,
) -> str:
    assert_python_runtime(
        executable=sys.executable,
        version_info=sys.version_info[:3],
        prefix=sys.prefix,
        expected_executable="/root/autodl-tmp/dp312_venv/bin/python",
        expected_prefix="/root/autodl-tmp/dp312_venv",
        expected_exact_version=(3, 12, 3),
    )
    if (
        output != Path(EXACT_DIRS["preflight"])
        or output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main") != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(DP, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(DP, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("selector replay preflight live authority drifted")
    for path, root_sha, label in (
        (contract_dir, contract_root, "selector replay contract"),
        (contract_review_dir, contract_review_root, "selector replay contract review"),
        (CORRECTED_PREFLIGHT, CORRECTED_PREFLIGHT_ROOT, "corrected preflight"),
        (
            CORRECTED_PREFLIGHT_REVIEW,
            CORRECTED_PREFLIGHT_REVIEW_ROOT,
            "corrected preflight review",
        ),
        (CORRECTED_RAW, CORRECTED_RAW_ROOT, "corrected raw"),
        (CORRECTED_RAW_REVIEW, CORRECTED_RAW_REVIEW_ROOT, "corrected raw review"),
        (TRAINING, TRAINING_ROOT, "accepted training"),
        (TRAINING_REVIEW, TRAINING_REVIEW_ROOT, "accepted training review"),
    ):
        verify_complete_seal(path, root_sha, label=label)
    contract_value = validate_contract(_json(contract_dir / "contract.json"))
    if (
        contract_value["implementation_head"] != implementation_head
        or contract_value["exact_dirs"]["preflight"] != str(output)
    ):
        raise RuntimeError("selector replay contract/preflight binding drifted")
    for relative, expected in (
        ("runtime_atom_scales.json", TRAINING_SCALE_FILE_SHA256),
        ("static14d_runtime_weights.npy", TRAINING_STATIC_WEIGHTS_FILE_SHA256),
        ("model_parameters.npz", TRAINING_MODEL_PARAMETERS_FILE_SHA256),
    ):
        if sha256_file(TRAINING / relative) != expected:
            raise RuntimeError(f"sealed training file drifted: {relative}")
    tensor_converter = DP / "scenario_generation/tensor_converter.py"
    normalizer_source = (
        DP / "diffusion_planner/diffusion_planner/utils/normalizer.py"
    )
    if (
        sha256_file(tensor_converter) != TENSOR_CONVERTER_SHA256
        or sha256_file(normalizer_source) != OBSERVATION_NORMALIZER_SHA256
    ):
        raise RuntimeError("fixed-DP tensor-converter source drifted")
    normalization_path, normalization = _normalization_authority()
    corrected_preflight = _json(CORRECTED_PREFLIGHT / "receipt.json")
    corrected_raw = _json(CORRECTED_RAW / "report.json")
    manifests = corrected_preflight.get("run_manifests")
    if (
        not isinstance(manifests, list)
        or len(manifests) != 320
        or corrected_raw.get("completed_run_count") != 320
        or corrected_raw.get("formal_model_call_count") != 320
        or corrected_raw.get("selector_call_count") != 0
        or corrected_raw.get("post_pool_call_count") != 0
    ):
        raise RuntimeError("corrected sealed denominator drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=TRAINING,
        training_root_sha256=TRAINING_ROOT,
        training_review_artifact=TRAINING_REVIEW,
        training_review_root_sha256=TRAINING_REVIEW_ROOT,
    )

    config = _json(PROBE_CONFIG)
    route_path = Path(config["routes"][0]["path"])
    map_path = Path(config["map"]["path"])
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(str(map_path))
    route = Route.load(route_path)
    no_signal_chain = _build_no_signal_chain(
        builder=builder,
        route_ids=list(route.route_lanelet_ids),
        map_sha256=config["map"]["sha256"],
        route_sha256=config["routes"][0]["sha256"],
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "causal_inputs").mkdir()
        state_receipts = []
        for state_index in range(64):
            rows = [row for row in manifests if row["state_index"] == state_index]
            if (
                len(rows) != 5
                or {row["repeat_index"] for row in rows} != set(range(5))
                or len({row["input_npz_sha256"] for row in rows}) != 1
                or len(
                    {
                        row["latent_manifest"]["tensor_sha256"]
                        for row in rows
                    }
                )
                != 1
            ):
                raise RuntimeError("corrected same-state manifest drifted")
            input_path = CORRECTED_PREFLIGHT / rows[0]["input_npz_relpath"]
            if sha256_file(input_path) != rows[0]["input_npz_sha256"]:
                raise RuntimeError("corrected input preimage drifted")
            source_arrays = _arrays(input_path)
            causal = causal_input_from_model_input(
                source_arrays, normalization=normalization
            )
            _roundtrip(source_arrays, causal, normalization)
            boundary = causal_input_receipt(causal, source_observed_frames=31)
            causal_path = (
                staging / "causal_inputs" / f"state_{state_index:03d}.npz"
            )
            np.savez(causal_path, **boundary.causal_input)
            state_receipts.append(
                {
                    "state_index": state_index,
                    "state_spec_id": rows[0]["state_spec"]["state_spec_id"],
                    "input_npz_sha256": rows[0]["input_npz_sha256"],
                    "latent_tensor_sha256": rows[0]["latent_manifest"][
                        "tensor_sha256"
                    ],
                    "causal_input_relpath": (
                        f"causal_inputs/state_{state_index:03d}.npz"
                    ),
                    "causal_input_file_sha256": sha256_file(causal_path),
                    "causal_input_sha256": boundary.receipt["input_sha256"],
                    "normalizer_roundtrip_exact": True,
                }
            )
        slot_receipts = []
        for slot, manifest in enumerate(manifests):
            run = CORRECTED_RAW / "runs" / f"{slot:03d}"
            receipt = _json(run / "receipt.json")
            candidate = np.fromfile(run / "candidate.f32le", dtype="<f4").reshape(
                8, 80, 4
            )
            neighbor = np.fromfile(run / "neighbor.f32le", dtype="<f4").reshape(
                8, 32, 80, 4
            )
            candidate_sha256 = array_sha256(candidate)
            neighbor_sha256 = array_sha256(neighbor)
            expected_pool_id = pool_id_from_preimages(
                forward_id=receipt.get("forward_id"),
                candidate_tensor_sha256=candidate_sha256,
                neighbor_tensor_sha256=neighbor_sha256,
            )
            if (
                receipt.get("slot") != slot
                or receipt.get("run_id") != manifest["run_id"]
                or receipt.get("state_index") != manifest["state_index"]
                or receipt.get("repeat_index") != manifest["repeat_index"]
                or receipt.get("formal_model_call_count") != 1
                or receipt.get("selector_call_count") != 0
                or receipt.get(
                    "post_pool_model_dp_latent_candidate_generation_call_count"
                )
                != 0
                or receipt.get("pool_id") != expected_pool_id
                or candidate_sha256 != receipt["candidate"]["tensor_sha256"]
                or neighbor_sha256 != receipt["neighbor"]["tensor_sha256"]
            ):
                raise RuntimeError(f"corrected raw slot binding drifted: {slot}")
            slot_receipts.append(
                {
                    "slot": slot,
                    "run_id": receipt["run_id"],
                    "state_index": receipt["state_index"],
                    "repeat_index": receipt["repeat_index"],
                    "forward_id": receipt["forward_id"],
                    "pool_id": receipt["pool_id"],
                    "candidate_relpath": receipt["candidate_relpath"],
                    "neighbor_relpath": receipt["neighbor_relpath"],
                    "candidate_tensor_sha256": candidate_sha256,
                    "neighbor_tensor_sha256": neighbor_sha256,
                    "candidate_row_sha256": [
                        array_sha256(candidate[index]) for index in range(8)
                    ],
                }
            )
        np.savez(
            staging / "selector_assets.npz",
            atom_scales=np.ascontiguousarray(assets.atom_scales),
            static14d_weights=np.ascontiguousarray(assets.static14d_weights),
            scene14d_theta=np.ascontiguousarray(
                assets.scene14d_weight_provider.theta
            ),
            context_q05=np.ascontiguousarray(
                assets.scene14d_weight_provider.context_scaler.q05
            ),
            context_q95=np.ascontiguousarray(
                assets.scene14d_weight_provider.context_scaler.q95
            ),
        )
        (staging / "normalization.json").write_bytes(
            canonical_bytes(normalization)
        )
        (staging / "no_signal_chain.json").write_bytes(
            canonical_bytes(no_signal_chain)
        )
        report = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_preflight_v1"
            ),
            "status": "PASS_sealed_input_and_weight_preflight",
            "implementation_head": implementation_head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "corrected_preflight_root_sha256": CORRECTED_PREFLIGHT_ROOT,
            "corrected_preflight_review_root_sha256": (
                CORRECTED_PREFLIGHT_REVIEW_ROOT
            ),
            "corrected_raw_root_sha256": CORRECTED_RAW_ROOT,
            "corrected_raw_review_root_sha256": CORRECTED_RAW_REVIEW_ROOT,
            "training_root_sha256": TRAINING_ROOT,
            "training_review_root_sha256": TRAINING_REVIEW_ROOT,
            "normalization_file_path": str(normalization_path),
            "normalization_file_sha256": sha256_file(normalization_path),
            "normalization_payload_sha256": sha256_bytes(
                canonical_bytes(normalization)
            ),
            "tensor_converter_sha256": TENSOR_CONVERTER_SHA256,
            "observation_normalizer_source_sha256": (
                OBSERVATION_NORMALIZER_SHA256
            ),
            "map_sha256": config["map"]["sha256"],
            "route_sha256": config["routes"][0]["sha256"],
            "state_count": 64,
            "repeat_count_per_state": 5,
            "slot_count": 320,
            "state_receipts": state_receipts,
            "slot_receipts": slot_receipts,
            "selector_assets_sha256": sha256_file(
                staging / "selector_assets.npz"
            ),
            "no_signal_chain_sha256": sha256_bytes(
                canonical_bytes(no_signal_chain)
            ),
            "model_dp_latent_candidate_generation_call_count": 0,
            "selector_call_count": 0,
            "outcome_read": False,
            "old_artifact_or_cas_write": False,
        }
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector-after-pool replay preflight"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 selector-after-pool replay preflight"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract-dir", type=Path, default=Path(EXACT_DIRS["contract"]))
    parser.add_argument("--contract-root", required=True)
    parser.add_argument(
        "--contract-review-dir",
        type=Path,
        default=Path(EXACT_DIRS["contract_review"]),
    )
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["preflight"]))
    args = parser.parse_args()
    print(
        materialize(
            repo=args.repo,
            implementation_head=args.implementation_head,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
