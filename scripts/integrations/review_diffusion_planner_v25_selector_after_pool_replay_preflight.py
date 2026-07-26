"""Separate-role raw-byte review of selector-after-pool replay preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    causal_input_receipt,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    validate_no_signal_chain,
)


AUTODL = Path("/root/autodl-tmp")
PREFLIGHT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_preflight_v2_59874f4a"
)
OUTPUT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_preflight_review_v2_59874f4a"
)
CORRECTED_PREFLIGHT = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_preflight_v1_dc76fbc8"
)
CORRECTED_RAW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_v1_dc76fbc8"
)
TRAINING = AUTODL / "camp_dp_v25_camp_training_863e28da_20260722T103219CST"
ROOTS = {
    "corrected_preflight": (
        "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac"
    ),
    "corrected_raw": (
        "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
    ),
    "training": (
        "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
    ),
}
TRAINING_FILES = {
    "runtime_atom_scales.json": (
        "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
    ),
    "static14d_runtime_weights.npy": (
        "1d512bc80442e82f6bc5e9dd479670cd17b2954a285ce9f5ab2d2afa828ce49e"
    ),
    "model_parameters.npz": (
        "62ae9ceb9ebf563025887d8d60734c2c7865e52fb2b01c1b9d7656ff6f78daa8"
    ),
}


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must be object")
    return value


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.ascontiguousarray(np.array(archive[name], copy=True))
            for name in archive.files
        }


def _literal_inverse(
    arrays: Mapping[str, np.ndarray],
    normalization: Mapping[str, Mapping[str, Any]],
) -> dict[str, np.ndarray]:
    work = {
        name: np.ascontiguousarray(np.asarray(value))
        for name, value in arrays.items()
        if name not in {"delay", "sampled_trajectories"}
    }
    for name, row in normalization.items():
        if name not in work or name in {"ego", "neighbor"}:
            continue
        if type(row) is not dict or set(row) != {"mean", "std"}:
            raise ValueError("review normalization schema drifted")
        value = work[name]
        mean = np.asarray(row["mean"], dtype=np.float32)
        std = np.asarray(row["std"], dtype=np.float32)
        if not np.isfinite(mean).all() or not np.isfinite(std).all() or np.any(std <= 0):
            raise ValueError("review normalization value drifted")
        mask = np.sum(np.not_equal(value, 0), axis=-1) == 0
        restored = value.astype(np.float32, copy=False) * std + mean
        restored[mask] = 0
        work[name] = np.ascontiguousarray(restored)
    result = {}
    for name, value in work.items():
        array = value[0] if value.ndim >= 1 and value.shape[0] == 1 else value
        result[name] = np.ascontiguousarray(array)
    for name in ("lanes_has_speed_limit", "route_lanes_has_speed_limit"):
        result[name] = result[name].astype(np.bool_, copy=False)
    result["turn_indicators"] = result["turn_indicators"].astype(
        np.int32, copy=False
    )
    past = result["ego_agent_past"]
    result["ego_agent_past"] = np.stack(
        (
            past[..., 0],
            past[..., 1],
            np.arctan2(past[..., 3], past[..., 2]),
        ),
        axis=-1,
    ).astype(np.float32)
    goal = result["goal_pose"]
    result["goal_pose"] = np.asarray(
        (
            goal[0],
            goal[1],
            float(np.arctan2(goal[3], goal[2])),
        ),
        dtype=np.float32,
    )
    result["neighbor_agents_past"] = np.ascontiguousarray(
        result["neighbor_agents_past"][:32]
    )
    result["version"] = np.asarray(1, dtype=np.int64)
    return result


def review(*, preflight_root: str, output: Path = OUTPUT) -> str:
    if (
        sys.executable != "/root/autodl-tmp/dp312_venv/bin/python"
        or sys.version_info[:3] != (3, 12, 3)
        or sys.prefix != "/root/autodl-tmp/dp312_venv"
    ):
        raise RuntimeError("preflight reviewer Python authority drifted")
    for path, root, label in (
        (PREFLIGHT, preflight_root, "selector replay preflight"),
        (
            CORRECTED_PREFLIGHT,
            ROOTS["corrected_preflight"],
            "corrected preflight",
        ),
        (CORRECTED_RAW, ROOTS["corrected_raw"], "corrected raw"),
        (TRAINING, ROOTS["training"], "accepted training"),
    ):
        verify_complete_seal(path, root, label=label)
    if output != OUTPUT or output.exists():
        raise RuntimeError("preflight review exact output drifted")
    report = _json(PREFLIGHT / "report.json")
    normalization = _json(PREFLIGHT / "normalization.json")
    corrected = _json(CORRECTED_PREFLIGHT / "receipt.json")
    manifests = corrected["run_manifests"]
    if (
        report.get("status") != "PASS_sealed_input_and_weight_preflight"
        or report.get("state_count") != 64
        or report.get("slot_count") != 320
        or len(report.get("state_receipts", [])) != 64
        or len(report.get("slot_receipts", [])) != 320
        or report.get("model_dp_latent_candidate_generation_call_count") != 0
        or report.get("selector_call_count") != 0
    ):
        raise ValueError("review preflight denominator/call topology drifted")
    for relative, expected in TRAINING_FILES.items():
        if _file(TRAINING / relative) != expected:
            raise ValueError(f"review training file drifted: {relative}")
    if _file(PREFLIGHT / "selector_assets.npz") != report[
        "selector_assets_sha256"
    ]:
        raise ValueError("review selector assets file drifted")
    with np.load(PREFLIGHT / "selector_assets.npz", allow_pickle=False) as assets:
        if (
            set(assets.files)
            != {
                "atom_scales",
                "static14d_weights",
                "scene14d_theta",
                "context_q05",
                "context_q95",
            }
            or assets["atom_scales"].shape != (14,)
            or assets["static14d_weights"].shape != (14,)
            or assets["scene14d_theta"].shape != (14, 53)
            or assets["context_q05"].shape != (26,)
            or assets["context_q95"].shape != (26,)
        ):
            raise ValueError("review selector asset schema drifted")
    by_state = {row["state_index"]: row for row in report["state_receipts"]}
    for state_index in range(64):
        rows = [row for row in manifests if row["state_index"] == state_index]
        if len(rows) != 5:
            raise ValueError("review state denominator drifted")
        input_path = CORRECTED_PREFLIGHT / rows[0]["input_npz_relpath"]
        if _file(input_path) != rows[0]["input_npz_sha256"]:
            raise ValueError("review input preimage drifted")
        literal = _literal_inverse(_arrays(input_path), normalization)
        boundary = causal_input_receipt(literal, source_observed_frames=31)
        produced_path = PREFLIGHT / by_state[state_index]["causal_input_relpath"]
        produced = _arrays(produced_path)
        if (
            _file(produced_path)
            != by_state[state_index]["causal_input_file_sha256"]
            or boundary.receipt["input_sha256"]
            != by_state[state_index]["causal_input_sha256"]
            or set(produced) != set(boundary.causal_input)
            or any(
                not np.array_equal(produced[name], boundary.causal_input[name])
                for name in produced
            )
        ):
            raise ValueError("review causal input reconstruction drifted")
    for slot, binding in enumerate(report["slot_receipts"]):
        manifest = manifests[slot]
        receipt = _json(CORRECTED_RAW / "runs" / f"{slot:03d}" / "receipt.json")
        candidate = np.fromfile(
            CORRECTED_RAW / receipt["candidate_relpath"], dtype="<f4"
        ).reshape(8, 80, 4)
        neighbor = np.fromfile(
            CORRECTED_RAW / receipt["neighbor_relpath"], dtype="<f4"
        ).reshape(8, 32, 80, 4)
        candidate_sha256 = _digest(candidate.tobytes(order="C"))
        neighbor_sha256 = _digest(neighbor.tobytes(order="C"))
        expected_pool_id = _digest(
            _canonical(
                {
                    "forward_id": receipt["forward_id"],
                    "candidate_tensor_sha256": candidate_sha256,
                    "neighbor_tensor_sha256": neighbor_sha256,
                }
            )
        )
        if (
            binding["slot"] != slot
            or binding["run_id"] != manifest["run_id"]
            or binding["forward_id"] != receipt["forward_id"]
            or binding["pool_id"] != expected_pool_id
            or receipt["pool_id"] != expected_pool_id
            or binding["candidate_tensor_sha256"]
            != candidate_sha256
            or binding["neighbor_tensor_sha256"]
            != neighbor_sha256
            or binding["candidate_row_sha256"]
            != [
                _digest(np.ascontiguousarray(candidate[index]).tobytes(order="C"))
                for index in range(8)
            ]
        ):
            raise ValueError("review corrected raw slot binding drifted")
    chain = validate_no_signal_chain(_json(PREFLIGHT / "no_signal_chain.json"))
    if (
        chain["traffic_light_regulatory_element_ids"] != []
        or _digest(_canonical(chain)) != report["no_signal_chain_sha256"]
    ):
        raise ValueError("review no-signal authority drifted")
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        reviewed = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_preflight_review_v2"
            ),
            "status": "PASS_independent_raw_byte_preflight_review",
            "preflight_root_sha256": preflight_root,
            "reviewed_state_count": 64,
            "reviewed_slot_count": 320,
            "reviewed_training_file_count": 3,
            "normalizer_inverse_rebuilt_locally": True,
            "corrected_raw_bytes_rebuilt": True,
            "model_dp_latent_candidate_generation_call_count": 0,
            "selector_call_count": 0,
            "outcome_read": False,
        }
        (staging / "report.json").write_bytes(_canonical(reviewed))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector-after-pool replay preflight review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 selector-after-pool replay preflight review",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(review(preflight_root=args.preflight_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
