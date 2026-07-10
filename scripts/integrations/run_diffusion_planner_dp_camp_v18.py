#!/usr/bin/env python3
"""Thin causal nuPlan -> fixed-DP K=8 candidate exporter for v18."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_causal_materializer import (  # noqa: E402
    validate_causal_dp_input,
)
from camp_core.integrations.nuplan_causal_adapter import (  # noqa: E402
    materialize_nuplan_decision,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_K = 8
FIXED_DP_NEIGHBOR_COUNT = 320
DEFAULT_SEED = 3407
CAUSAL_SOURCE_SCHEMA_VERSION = "dp_camp_v18_nuplan_causal_source_v2"
_WHITE_CHANNEL = 11
_SIGNAL_PROXIMITY_M = 3.0
_SIGNAL_HEADING_THRESHOLD = 0.5
_MOVING_THRESHOLD_MPS = 0.5
_TARGET_DT_S = 0.1
POINTER_KEYS = (
    "current_v18_status",
    "current_v18_artifact_scope",
    "current_v18_artifact",
    "current_v18_artifact_root_sha256",
    "next_work_target",
)
BASELINE_INDEX = 0
BASELINE_SEMANTICS = "fixed_dp_deterministic_map_baseline"
NATIVE_RANKED_TOP1 = False
FEASIBILITY_SCOPE = "frozen_observable_32_dynamic_plus_5_static_only"
CLOSED_LOOP_SAFETY_CLAIM = False


def _latest_pointer(lines: list[str]) -> dict[str, str]:
    result = {}
    for key in POINTER_KEYS:
        matches = [line for line in lines if line.startswith(f"{key}=")]
        if not matches:
            raise ValueError(f"missing {key}")
        result[key] = matches[-1].split("=", 1)[1]
    return result


def read_v18_status_pointer(
    current_status: Path,
    v18_audit: Path,
) -> dict[str, str]:
    text = current_status.read_text(encoding="utf-8")
    try:
        section = text.split("## Current V18 Status", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise ValueError("Current V18 Status section is missing") from exc
    status_pointer = _latest_pointer(section.splitlines())
    audit_pointer = _latest_pointer(
        v18_audit.read_text(encoding="utf-8").splitlines()
    )
    if status_pointer != audit_pointer:
        raise ValueError("latest v18 status pointer does not match v18 audit EOF")
    return audit_pointer


def prepare_causal_arrays(data: Mapping[str, Any]) -> dict[str, np.ndarray]:
    arrays = {key: np.asarray(value) for key, value in data.items()}
    errors = validate_causal_dp_input(arrays)
    if errors:
        raise ValueError("; ".join(errors))
    prepared = {key: np.ascontiguousarray(value) for key, value in arrays.items()}
    neighbors = prepared["neighbor_agents_past"]
    padded = np.zeros(
        (FIXED_DP_NEIGHBOR_COUNT, *neighbors.shape[1:]), dtype=neighbors.dtype
    )
    padded[: neighbors.shape[0]] = neighbors
    prepared["neighbor_agents_past"] = padded
    return prepared


def causal_input_sha256(data: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for key in sorted(data):
        array = np.ascontiguousarray(data[key])
        digest.update(key.encode())
        digest.update(b"\0")
        digest.update(array.dtype.str.encode())
        digest.update(b"\0")
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode())
        digest.update(b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def sample_fixed_dp_sources(
    data: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    noise_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw_neighbors = np.asarray(data["neighbor_agents_past"])
    neighbor_valid_mask = np.any(np.abs(raw_neighbors) > 1e-8, axis=(1, 2))
    arrays = prepare_causal_arrays(data)
    torch = context["torch"]
    device = context["device"]
    tensors = {
        key: torch.as_tensor(value).unsqueeze(0).to(device)
        for key, value in arrays.items()
    }
    tensors["ego_agent_past"] = context["heading_to_cos_sin"](
        tensors["ego_agent_past"]
    )
    tensors["goal_pose"] = context["heading_to_cos_sin"](tensors["goal_pose"])
    normalized = context["config"].observation_normalizer(tensors)
    normalized["delay"] = torch.zeros(
        normalized["ego_current_state"].shape[0],
        dtype=torch.float32,
        device=device,
    )
    model = context["model"]
    original_fn = model.decoder._guidance_fn
    original_scale = model.decoder._guidance_scale
    model.decoder._guidance_fn = None
    model.decoder._guidance_scale = 0.5

    def draw(scale: float, count: int) -> np.ndarray:
        results = []
        for _ in range(count):
            normalized["sampled_trajectories"] = context["make_initial_latent"](
                1,
                1 + context["config"].predicted_neighbor_num,
                context["config"].future_len,
                device,
                scale,
            )
            _, output = model(normalized)
            prediction = output["prediction"]
            if tuple(prediction.shape) != (1, 321, 80, 4):
                raise ValueError("fixed DP full prediction must have shape [1,321,80,4]")
            value = prediction[0, :33].detach().cpu().numpy().astype(np.float32)
            if not np.isfinite(value).all():
                raise ValueError("fixed DP full prediction must be finite")
            results.append(value)
        return np.stack(results)

    try:
        full = np.concatenate([draw(0.0, 1), draw(noise_scale, 7)], axis=0)
    finally:
        model.decoder._guidance_fn = original_fn
        model.decoder._guidance_scale = original_scale
    candidates = np.ascontiguousarray(full[:, 0], dtype=np.float32)
    neighbors = np.ascontiguousarray(full[:, 1:33], dtype=np.float32)
    return candidates, neighbors, neighbor_valid_mask.astype(bool, copy=False)


def candidate_signal_source_available_mask(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
) -> np.ndarray:
    trajectories = np.array(candidates, dtype=np.float64, copy=True)
    route = np.asarray(route_lanes, dtype=np.float64)
    white = route[
        (route[..., _WHITE_CHANNEL] > 0.5)
        & (np.linalg.norm(route[..., :2], axis=-1) > 0.1)
    ]
    if white.size == 0:
        return np.ones(trajectories.shape[0], dtype=bool)
    white_xy = white[:, :2]
    white_direction = white[:, 2:4]
    white_direction /= np.maximum(
        np.linalg.norm(white_direction, axis=1, keepdims=True), 1e-6
    )
    heading = trajectories[:, :, 2:4].copy()
    heading /= np.maximum(np.linalg.norm(heading, axis=2, keepdims=True), 1e-6)
    distance = np.linalg.norm(
        trajectories[:, :, None, :2] - white_xy[None, None, :, :],
        axis=3,
    )
    aligned = (
        np.einsum("kti,ri->ktr", heading, white_direction)
        > _SIGNAL_HEADING_THRESHOLD
    )
    speed = (
        np.linalg.norm(np.diff(trajectories[:, :, :2], axis=1), axis=2)
        / _TARGET_DT_S
    )
    speed = np.concatenate([speed, speed[:, -1:]], axis=1)
    reaches = ((distance < _SIGNAL_PROXIMITY_M) & aligned).any(axis=2)
    reaches &= speed > _MOVING_THRESHOLD_MPS
    return ~reaches.any(axis=1)


def _load_context(
    dp_repo: Path, checkpoint: Path, args_json: Path, device: str
) -> dict[str, Any]:
    from scripts.integrations.run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter import (  # noqa: E501
        load_fixed_dp_export_context,
    )

    context = load_fixed_dp_export_context(
        dp_repo=dp_repo,
        checkpoint=checkpoint,
        args_json=args_json,
        device=device,
    )
    from rlvr.closed_loop.batched_rollout import make_initial_latent

    context["make_initial_latent"] = make_initial_latent
    return context


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _nonzero_row_count(array: np.ndarray) -> int:
    values = np.asarray(array)
    axes = tuple(range(1, values.ndim))
    return int(np.count_nonzero(np.any(np.abs(values) > 1e-8, axis=axes)))


def _read_manifest(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    if _sha256(path) != expected_sha256:
        raise ValueError("manifest SHA256 mismatch")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows:
        raise ValueError("manifest is empty")
    return rows


def refresh_manifest(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_manifest(args.manifest, args.expected_manifest_sha256)
    output = args.refresh_manifest_output
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            for row in rows:
                materialized = materialize_nuplan_decision(
                    row["db_path"], row["map_path"], row["decision_token"]
                )
                refreshed = dict(row)
                refreshed.update(
                    {
                        "causal_input_sha256": causal_input_sha256(
                            materialized.dp_input
                        ),
                        "causal_source_schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
                        "parent_manifest_sha256": args.expected_manifest_sha256,
                        "static_object_count": _nonzero_row_count(
                            materialized.dp_input["static_objects"]
                        ),
                        "neighbor_valid_count": _nonzero_row_count(
                            materialized.dp_input["neighbor_agents_past"]
                        ),
                    }
                )
                stream.write(json.dumps(refreshed, sort_keys=True) + "\n")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
        "parent_manifest": str(args.manifest),
        "parent_manifest_sha256": args.expected_manifest_sha256,
        "refreshed_manifest": str(output),
        "refreshed_manifest_sha256": _sha256(output),
        "record_count": len(rows),
        "candidate_generation_executed": False,
    }


def run_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if args.refresh_manifest_output is not None:
        if args.execute:
            raise ValueError(
                "manifest refresh and candidate execution are mutually exclusive"
            )
        return refresh_manifest(args)
    rows = _read_manifest(args.manifest, args.expected_manifest_sha256)
    dp_head = subprocess.run(
        ["git", "-C", str(args.dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dp_head != FIXED_DP_HEAD:
        raise ValueError(f"fixed DP HEAD mismatch: {dp_head}")
    selected = rows[: args.max_records or None]
    plan = {
        "schema_version": "dp_camp_v18_causal_fixed_dp_export_v2",
        "manifest": str(args.manifest),
        "manifest_sha256": args.expected_manifest_sha256,
        "record_count": len(selected),
        "k": args.k,
        "seed": args.seed,
        "dp_head": dp_head,
        "candidate_generation_executed": bool(args.execute),
    }
    if args.k != EXPECTED_K:
        raise ValueError("K must be 8")
    if not args.execute:
        return plan
    if any(
        row.get("causal_source_schema_version") != CAUSAL_SOURCE_SCHEMA_VERSION
        for row in selected
    ):
        raise ValueError("candidate execution requires the refreshed v2 causal manifest")
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    context = _load_context(args.dp_repo, args.checkpoint, args.args_json, args.device)
    random.seed(args.seed)
    np.random.seed(args.seed)
    context["torch"].manual_seed(args.seed)
    records_path = args.output_dir / "records.jsonl"
    started = time.time()
    with records_path.open("w", encoding="utf-8") as records:
        for index, row in enumerate(selected):
            materialized = materialize_nuplan_decision(
                row["db_path"], row["map_path"], row["decision_token"]
            )
            input_hash = causal_input_sha256(materialized.dp_input)
            if input_hash != row["causal_input_sha256"]:
                raise ValueError(f"causal input SHA256 mismatch at record {index}")
            candidates, neighbor_predictions, neighbor_valid_mask = (
                sample_fixed_dp_sources(
                    materialized.dp_input, context, noise_scale=args.noise_scale
                )
            )
            signal_available = candidate_signal_source_available_mask(
                candidates, materialized.dp_input["route_lanes"]
            )
            relative = Path(row["split"]) / row["log_token"] / f"{row['scene_token']}.npz"
            output = args.output_dir / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(".npz.tmp")
            with temporary.open("wb") as stream:
                np.savez(
                    stream,
                    candidate_tensor=candidates,
                    neighbor_prediction_tensor=neighbor_predictions,
                    neighbor_valid_mask=neighbor_valid_mask,
                    candidate_signal_source_available_mask=signal_available,
                    eligible_for_canonical_14d=np.array(bool(signal_available.all())),
                    dp_top1_index=np.array(0, dtype=np.int64),
                    candidate_count=np.array(EXPECTED_K, dtype=np.int64),
                    causal_input_sha256=np.array(input_hash),
                    causal_source_schema_version=np.array(
                        CAUSAL_SOURCE_SCHEMA_VERSION
                    ),
                )
            os.replace(temporary, output)
            record = {
                "record_index": index,
                "split": row["split"],
                "log_token": row["log_token"],
                "scene_token": row["scene_token"],
                "decision_token": row["decision_token"],
                "DP_HEAD": dp_head,
                "K": EXPECTED_K,
                "candidate_count": EXPECTED_K,
                "dp_top1_index": 0,
                "causal_input_sha256": input_hash,
                "causal_source_schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
                "candidate_tensor_sha256": _array_sha256(candidates),
                "neighbor_prediction_tensor_sha256": _array_sha256(
                    neighbor_predictions
                ),
                "neighbor_valid_mask_sha256": _array_sha256(neighbor_valid_mask),
                "candidate_signal_source_available_mask_sha256": _array_sha256(
                    signal_available
                ),
                "neighbor_valid_count": int(neighbor_valid_mask.sum()),
                "signal_source_available_count": int(signal_available.sum()),
                "eligible_for_canonical_14d": bool(signal_available.all()),
                "physical_feasibility_mask_materialized": False,
                "output_npz": relative.as_posix(),
                "output_npz_sha256": _sha256(output),
            }
            records.write(json.dumps(record, sort_keys=True) + "\n")
            records.flush()
    plan["wall_clock_seconds"] = round(time.time() - started, 6)
    plan["records_jsonl"] = str(records_path)
    plan["candidate_generation_executed"] = True
    (args.output_dir / "summary.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected_manifest_sha256", required=True)
    parser.add_argument("--refresh_manifest_output", type=Path)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--args_json", type=Path, required=True)
    parser.add_argument("--k", type=int, default=EXPECTED_K)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max_records", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_manifest(args)
    except Exception as exc:
        print(json.dumps({"failure_class": type(exc).__name__, "message": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
