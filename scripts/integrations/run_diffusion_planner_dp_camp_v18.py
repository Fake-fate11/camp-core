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
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    materialize_canonical_14d,
)
from camp_core.integrations.nuplan_causal_adapter import (  # noqa: E402
    load_nuplan_expert_ego_future,
    materialize_nuplan_decision,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_K = 8
EXPECTED_MINI_RECORD_COUNT = 367
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


def _verify_fixed_dp_repo(dp_repo: Path) -> str:
    head = subprocess.run(
        ["git", "-C", str(dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != FIXED_DP_HEAD:
        raise ValueError(f"fixed DP HEAD mismatch: {head}")
    status = subprocess.run(
        [
            "git",
            "-C",
            str(dp_repo),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise ValueError("fixed DP tracked files are not clean")
    return head


def _fixed_dp_red_cost(
    candidates: np.ndarray,
    causal_input: Mapping[str, Any],
    dp_repo: Path,
    dt: float,
) -> np.ndarray:
    if str(dp_repo) not in sys.path:
        sys.path.insert(0, str(dp_repo))
    import torch
    from rlvr.reward import RewardConfig, compute_red_light_score_batch

    config = RewardConfig(dt=float(dt))
    with torch.no_grad():
        scores = compute_red_light_score_batch(
            torch.from_numpy(np.asarray(candidates)).float(),
            {
                "route_lanes": torch.from_numpy(
                    np.asarray(causal_input["route_lanes"])
                ).float()
            },
            config,
        )
    costs = np.maximum(
        -scores.detach().cpu().numpy().astype(np.float64).reshape(-1),
        0.0,
    )
    if costs.shape != (EXPECTED_K,) or not np.isfinite(costs).all():
        raise ValueError("fixed-DP planned red cost must be finite [8]")
    return costs


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"{path.name} is empty")
    return rows


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return tuple(
        str(row[key])
        for key in ("split", "log_token", "scene_token", "decision_token")
    )


def _read_sha256sums(path: Path) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split(None, 1)
        except ValueError as exc:
            raise ValueError(f"invalid SHA256SUMS line: {line!r}") from exc
        relative = relative.strip()
        if relative.startswith("./"):
            relative = relative[2:]
        item = Path(relative)
        if item.is_absolute() or ".." in item.parts:
            raise ValueError(f"unsafe SHA256SUMS path: {relative!r}")
        normalized = item.as_posix()
        if len(digest) != 64 or normalized in entries:
            raise ValueError(f"invalid SHA256SUMS entry: {line!r}")
        entries[normalized] = digest
    if not entries:
        raise ValueError("SHA256SUMS is empty")
    return entries


def _verify_hash_entries(root: Path, entries: Mapping[str, str]) -> None:
    for relative, expected in entries.items():
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"candidate source SHA256 mismatch: {relative}")


def _candidate_source_snapshot(
    candidate_root: Path,
    expected_root_sha256: str,
    manifest: Path | None = None,
) -> dict[str, Any]:
    sums = candidate_root / "SHA256SUMS"
    actual_root = _sha256(sums)
    if actual_root != expected_root_sha256:
        raise ValueError("candidate root SHA256 mismatch")
    entries = _read_sha256sums(sums)
    _verify_hash_entries(candidate_root, entries)
    snapshot: dict[str, Any] = {
        "candidate_root_sha256": actual_root,
        "candidate_records_sha256": _sha256(candidate_root / "records.jsonl"),
        "candidate_summary_sha256": _sha256(candidate_root / "summary.json"),
        "candidate_npz_hashes": dict(entries),
    }
    if manifest is not None:
        snapshot["manifest_sha256"] = _sha256(manifest)
    return snapshot


def _verified_candidate_source(
    candidate_root: Path,
    expected_root_sha256: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    Path,
    dict[str, Any],
]:
    snapshot = _candidate_source_snapshot(
        candidate_root, expected_root_sha256
    )
    entries = snapshot["candidate_npz_hashes"]
    records = _read_jsonl(candidate_root / "records.jsonl")
    summary = json.loads(
        (candidate_root / "summary.json").read_text(encoding="utf-8")
    )
    if (
        len(records) != EXPECTED_MINI_RECORD_COUNT
        or int(summary.get("record_count", -1)) != EXPECTED_MINI_RECORD_COUNT
        or len(entries) != EXPECTED_MINI_RECORD_COUNT
    ):
        raise ValueError(
            f"candidate source must contain {EXPECTED_MINI_RECORD_COUNT} records"
        )
    if (
        summary.get("candidate_generation_executed") is not True
        or summary.get("dp_head") != FIXED_DP_HEAD
        or int(summary.get("k", -1)) != EXPECTED_K
    ):
        raise ValueError("candidate summary contract mismatch")
    manifest = Path(str(summary["manifest"]))
    if not manifest.is_absolute():
        manifest = candidate_root / manifest
    source_rows = _read_manifest(manifest, str(summary["manifest_sha256"]))
    if len(source_rows) != EXPECTED_MINI_RECORD_COUNT:
        raise ValueError("candidate manifest record count mismatch")
    identities = [_identity(row) for row in records]
    if len(set(identities)) != len(identities):
        raise ValueError("candidate identities are not unique")
    if identities != [_identity(row) for row in source_rows]:
        raise ValueError("candidate records do not match manifest identity/order")
    allowed_splits = {"train", "calibration", "holdout"}
    for row, source in zip(records, source_rows):
        if row["split"] not in allowed_splits:
            raise ValueError(f"unsupported split: {row['split']}")
        relative = Path(str(row["output_npz"])).as_posix()
        if entries.get(relative) != row.get("output_npz_sha256"):
            raise ValueError(f"candidate NPZ hash manifest mismatch: {relative}")
        if row.get("DP_HEAD") != FIXED_DP_HEAD:
            raise ValueError("candidate record DP HEAD mismatch")
        if row.get("K") != EXPECTED_K or row.get("candidate_count") != EXPECTED_K:
            raise ValueError("candidate record K/count mismatch")
        if row.get("dp_top1_index") != BASELINE_INDEX:
            raise ValueError("candidate baseline position must be index 0")
        if row.get("causal_input_sha256") != source.get("causal_input_sha256"):
            raise ValueError("candidate/manifest causal input SHA256 mismatch")
    snapshot["manifest_sha256"] = _sha256(manifest)
    if snapshot["manifest_sha256"] != summary["manifest_sha256"]:
        raise ValueError("manifest SHA256 changed during source verification")
    return records, source_rows, manifest, snapshot


def _load_candidate_npz(
    candidate_root: Path,
    row: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    path = candidate_root / str(row["output_npz"])
    required = {
        "candidate_tensor",
        "neighbor_prediction_tensor",
        "neighbor_valid_mask",
        "candidate_signal_source_available_mask",
        "eligible_for_canonical_14d",
        "dp_top1_index",
        "candidate_count",
        "causal_input_sha256",
        "causal_source_schema_version",
    }
    with np.load(path, allow_pickle=False) as archive:
        missing = required - set(archive.files)
        if missing or any("future" in key for key in archive.files):
            raise ValueError(
                f"candidate NPZ fields invalid: missing={sorted(missing)}"
            )
        arrays = {key: np.array(archive[key], copy=True) for key in required}
    candidates = arrays["candidate_tensor"]
    neighbors = arrays["neighbor_prediction_tensor"]
    valid = arrays["neighbor_valid_mask"]
    signal = arrays["candidate_signal_source_available_mask"]
    if candidates.shape != (8, 80, 4) or not np.isfinite(candidates).all():
        raise ValueError("candidate tensor must be finite [8,80,4]")
    if neighbors.shape != (8, 32, 80, 4) or not np.isfinite(neighbors).all():
        raise ValueError("neighbor prediction tensor must be finite [8,32,80,4]")
    if valid.shape != (32,) or valid.dtype != np.bool_:
        raise ValueError("neighbor valid mask must be bool [32]")
    if signal.shape != (8,) or signal.dtype != np.bool_:
        raise ValueError("candidate signal mask must be bool [8]")
    checks = {
        "candidate_tensor_sha256": _array_sha256(candidates),
        "neighbor_prediction_tensor_sha256": _array_sha256(neighbors),
        "neighbor_valid_mask_sha256": _array_sha256(valid),
        "candidate_signal_source_available_mask_sha256": _array_sha256(signal),
    }
    for key, actual in checks.items():
        if row.get(key) != actual:
            raise ValueError(f"candidate array SHA256 mismatch: {key}")
    if (
        int(arrays["candidate_count"].item()) != EXPECTED_K
        or int(arrays["dp_top1_index"].item()) != BASELINE_INDEX
        or str(arrays["causal_input_sha256"].item())
        != row["causal_input_sha256"]
        or str(arrays["causal_source_schema_version"].item())
        != CAUSAL_SOURCE_SCHEMA_VERSION
    ):
        raise ValueError("candidate NPZ scalar provenance mismatch")
    return arrays


def _atomic_savez(path: Path, values: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(temporary)
    with temporary.open("wb") as stream:
        np.savez(stream, **values)
    os.replace(temporary, path)


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


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


def _materialization_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "total",
        "source_complete",
        "signal_source_incomplete",
        "lane_component_failure",
        "obb_component_failure",
        "all_k_infeasible",
        "materialized",
        "labelled",
        "holdout_sealed",
    )

    def empty() -> dict[str, int]:
        return {metric: 0 for metric in metrics}

    overall = empty()
    by_split: dict[str, dict[str, int]] = {}
    by_log: dict[str, dict[str, int]] = {}
    for row in rows:
        values = {
            "total": 1,
            "source_complete": int(all(row["signal_mask"])),
            "signal_source_incomplete": int(not all(row["signal_mask"])),
            "lane_component_failure": int(not all(row["lane_feasible_mask"])),
            "obb_component_failure": int(
                not all(row["obb_collision_free_mask"])
            ),
            "all_k_infeasible": int(
                row["exclusion_reason"]
                == "all_candidates_physically_infeasible"
            ),
            "materialized": int(row["canonical_output_npz"] is not None),
            "labelled": int(row["label_read"]),
            "holdout_sealed": int(
                row["split"] == "holdout" and not row["label_read"]
            ),
        }
        buckets = (
            overall,
            by_split.setdefault(row["split"], empty()),
            by_log.setdefault(row["log_token"], empty()),
        )
        for bucket in buckets:
            for metric, value in values.items():
                bucket[metric] += value
    return {"overall": overall, "by_split": by_split, "by_log": by_log}


def run_materialization(args: argparse.Namespace) -> dict[str, Any]:
    pointer = read_v18_status_pointer(args.current_status, args.v18_audit)
    output_root = args.materialize_output_dir
    staging_root = output_root.with_name(output_root.name + ".tmp")
    if output_root.exists():
        raise FileExistsError(output_root)
    if staging_root.exists():
        raise FileExistsError(staging_root)
    records, source_rows, manifest, source_before = _verified_candidate_source(
        args.candidate_root,
        args.expected_candidate_root_sha256,
    )
    dp_head = _verify_fixed_dp_repo(args.dp_repo)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir()
    output_records: list[dict[str, Any]] = []
    started = time.time()
    records_path = staging_root / "records.jsonl"
    source_verified_after_run = False
    try:
        with records_path.open("w", encoding="utf-8") as records_stream:
            for index, (row, source) in enumerate(zip(records, source_rows)):
                arrays = _load_candidate_npz(args.candidate_root, row)
                materialized = materialize_nuplan_decision(
                    source["db_path"],
                    source["map_path"],
                    source["decision_token"],
                )
                input_hash = causal_input_sha256(materialized.dp_input)
                if input_hash != row["causal_input_sha256"]:
                    raise ValueError(
                        f"causal input SHA256 mismatch at record {index}"
                    )
                candidates = arrays["candidate_tensor"]
                planned_red = _fixed_dp_red_cost(
                    candidates,
                    materialized.dp_input,
                    args.dp_repo,
                    _TARGET_DT_S,
                )
                canonical = materialize_canonical_14d(
                    candidates=candidates,
                    causal_input=materialized.dp_input,
                    neighbor_predictions=arrays["neighbor_prediction_tensor"],
                    neighbor_valid_mask=arrays["neighbor_valid_mask"],
                    signal_mask=arrays[
                        "candidate_signal_source_available_mask"
                    ],
                    planned_red_light_cost=planned_red,
                    dt=_TARGET_DT_S,
                )
                split = str(row["split"])
                label = None
                if canonical["canonical_eligible"] and split in {
                    "train",
                    "calibration",
                }:
                    label = load_nuplan_expert_ego_future(
                        source["db_path"],
                        source["decision_token"],
                        target_dt_s=_TARGET_DT_S,
                        horizon_steps=80,
                    )
                    label = np.asarray(label, dtype=np.float64)
                    if label.shape != (80, 3) or not np.isfinite(label).all():
                        raise ValueError("expert label must be finite [80,3]")

                relative = None
                canonical_hash = None
                if canonical["canonical_eligible"]:
                    relative_path = (
                        Path(split)
                        / str(row["log_token"])
                        / f"{row['scene_token']}.npz"
                    )
                    target = staging_root / relative_path
                    npz_values: dict[str, Any] = {
                        "atom_matrix": canonical["atom_matrix"],
                        "atom_names": np.asarray(canonical["atom_names"]),
                        "signal_mask": canonical["signal_mask"],
                        "lane_feasible_mask": canonical["lane_feasible_mask"],
                        "obb_collision_free_mask": canonical[
                            "obb_collision_free_mask"
                        ],
                        "physical_feasible_mask": canonical[
                            "physical_feasible_mask"
                        ],
                        "candidate_reasons_json": np.array(
                            json.dumps(canonical["candidate_reasons"])
                        ),
                        "route_progress": canonical["route_progress"],
                        "minimum_obb_clearance": canonical[
                            "minimum_obb_clearance"
                        ],
                        "minimum_obb_clearance_clip_m": np.array(
                            canonical["minimum_obb_clearance_clip_m"]
                        ),
                        "progress_reference": np.array(
                            canonical["progress_reference"]
                        ),
                        "planned_red_light_cost": planned_red,
                        "schema_version": np.array("dp_camp_v10_14d"),
                        "source_candidate_npz": np.array(row["output_npz"]),
                        "source_candidate_npz_sha256": np.array(
                            row["output_npz_sha256"]
                        ),
                        "candidate_root_sha256": np.array(
                            args.expected_candidate_root_sha256
                        ),
                        "candidate_tensor_sha256": np.array(
                            row["candidate_tensor_sha256"]
                        ),
                        "neighbor_prediction_tensor_sha256": np.array(
                            row["neighbor_prediction_tensor_sha256"]
                        ),
                        "neighbor_valid_mask_sha256": np.array(
                            row["neighbor_valid_mask_sha256"]
                        ),
                        "candidate_signal_source_available_mask_sha256": (
                            np.array(
                                row[
                                    "candidate_signal_source_available_mask_sha256"
                                ]
                            )
                        ),
                        "causal_input_sha256": np.array(input_hash),
                        "baseline_index": np.array(
                            BASELINE_INDEX, dtype=np.int64
                        ),
                        "baseline_semantics": np.array(BASELINE_SEMANTICS),
                        "equivalence_verified": np.array(False),
                        "native_ranked_top1": np.array(False),
                        "feasibility_scope": np.array(FEASIBILITY_SCOPE),
                        "closed_loop_safety_claim": np.array(False),
                    }
                    if label is not None:
                        npz_values["expert_ego_future_xyh"] = label
                    _atomic_savez(target, npz_values)
                    relative = relative_path.as_posix()
                    canonical_hash = _sha256(target)

                output_record = {
                    "record_index": index,
                    "split": split,
                    "log_token": row["log_token"],
                    "scene_token": row["scene_token"],
                    "decision_token": row["decision_token"],
                    "source_candidate_npz": row["output_npz"],
                    "source_candidate_npz_sha256": row["output_npz_sha256"],
                    "candidate_root_sha256": args.expected_candidate_root_sha256,
                    "DP_HEAD": dp_head,
                    "candidate_tensor_sha256": row["candidate_tensor_sha256"],
                    "neighbor_prediction_tensor_sha256": row[
                        "neighbor_prediction_tensor_sha256"
                    ],
                    "neighbor_valid_mask_sha256": row[
                        "neighbor_valid_mask_sha256"
                    ],
                    "candidate_signal_source_available_mask_sha256": row[
                        "candidate_signal_source_available_mask_sha256"
                    ],
                    "causal_input_sha256": input_hash,
                    "baseline_index": BASELINE_INDEX,
                    "baseline_semantics": BASELINE_SEMANTICS,
                    "equivalence_verified": False,
                    "legacy_dp_top1_index_position_only": True,
                    "native_ranked_top1": False,
                    "feasibility_scope": FEASIBILITY_SCOPE,
                    "closed_loop_safety_claim": False,
                    "signal_mask": np.asarray(
                        canonical["signal_mask"], dtype=bool
                    ).tolist(),
                    "lane_feasible_mask": np.asarray(
                        canonical["lane_feasible_mask"], dtype=bool
                    ).tolist(),
                    "obb_collision_free_mask": np.asarray(
                        canonical["obb_collision_free_mask"], dtype=bool
                    ).tolist(),
                    "physical_feasible_mask": np.asarray(
                        canonical["physical_feasible_mask"], dtype=bool
                    ).tolist(),
                    "candidate_reasons": [
                        list(reasons)
                        for reasons in canonical["candidate_reasons"]
                    ],
                    "canonical_eligible": bool(
                        canonical["canonical_eligible"]
                    ),
                    "canonical_schema_version": "dp_camp_v10_14d",
                    "atom_names": list(canonical["atom_names"]),
                    "progress_reference": (
                        None
                        if canonical["progress_reference"] is None
                        else float(canonical["progress_reference"])
                    ),
                    "exclusion_reason": canonical["exclusion_reason"],
                    "label_read": label is not None,
                    "canonical_output_npz": relative,
                    "canonical_output_npz_sha256": canonical_hash,
                }
                output_records.append(output_record)
                records_stream.write(
                    json.dumps(output_record, sort_keys=True) + "\n"
                )
                records_stream.flush()

        counts = _materialization_counts(output_records)
        holdout_labels_read = sum(
            row["label_read"] and row["split"] == "holdout"
            for row in output_records
        )
        if holdout_labels_read:
            raise RuntimeError("holdout labels were read during materialization")
        source_after = _candidate_source_snapshot(
            args.candidate_root,
            args.expected_candidate_root_sha256,
            manifest,
        )
        if source_after != source_before:
            raise RuntimeError("candidate source changed during materialization")
        if _verify_fixed_dp_repo(args.dp_repo) != dp_head:
            raise RuntimeError("fixed DP changed during materialization")
        source_verified_after_run = True
        summary = {
            "schema_version": "dp_camp_v18_nuplan_canonical_materialization_v1",
            "candidate_root": str(args.candidate_root),
            "candidate_root_sha256": args.expected_candidate_root_sha256,
            "candidate_records_sha256": source_before[
                "candidate_records_sha256"
            ],
            "candidate_summary_sha256": source_before[
                "candidate_summary_sha256"
            ],
            "manifest": str(manifest),
            "manifest_sha256": source_before["manifest_sha256"],
            "record_count": len(output_records),
            "materialize_output_dir": str(output_root),
            "records_jsonl": str(output_root / "records.jsonl"),
            "counts": counts,
            "model_calls": 0,
            "candidate_generation_executed": False,
            "candidate_tensor_mutation": False,
            "baseline_semantics": BASELINE_SEMANTICS,
            "equivalence_verified": False,
            "native_ranked_top1": False,
            "feasibility_scope": FEASIBILITY_SCOPE,
            "closed_loop_safety_claim": False,
            "holdout_labels_read": holdout_labels_read,
            "candidate_source_unchanged": True,
            "controller_pointer": pointer,
            "dp_head": dp_head,
            "wall_clock_seconds": round(time.time() - started, 6),
        }
        _atomic_write_text(
            staging_root / "summary.json",
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
        )
        os.replace(staging_root, output_root)
    finally:
        if not source_verified_after_run:
            source_after = _candidate_source_snapshot(
                args.candidate_root,
                args.expected_candidate_root_sha256,
                manifest,
            )
            if source_after != source_before:
                raise RuntimeError(
                    "candidate source changed during materialization"
                )
            if _verify_fixed_dp_repo(args.dp_repo) != dp_head:
                raise RuntimeError("fixed DP changed during materialization")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected_manifest_sha256")
    parser.add_argument("--refresh_manifest_output", type=Path)
    parser.add_argument("--output_dir", type=Path)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--args_json", type=Path)
    parser.add_argument("--candidate_root", type=Path)
    parser.add_argument("--expected_candidate_root_sha256")
    parser.add_argument("--materialize_output_dir", type=Path)
    parser.add_argument("--current_status", type=Path)
    parser.add_argument("--v18_audit", type=Path)
    parser.add_argument("--k", type=int, default=EXPECTED_K)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max_records", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.candidate_root is not None:
        required = (
            "expected_candidate_root_sha256",
            "materialize_output_dir",
            "current_status",
            "v18_audit",
        )
        missing = [name for name in required if getattr(args, name) is None]
        manifest_fields = (
            "manifest",
            "expected_manifest_sha256",
            "refresh_manifest_output",
            "output_dir",
            "checkpoint",
            "args_json",
        )
        conflicting = [
            name for name in manifest_fields if getattr(args, name) is not None
        ]
        if missing or conflicting or args.execute:
            parser.error(
                "materialization mode requires its five inputs and is mutually "
                "exclusive with manifest generation inputs"
            )
    else:
        required = (
            "manifest",
            "expected_manifest_sha256",
            "output_dir",
            "checkpoint",
            "args_json",
        )
        if any(getattr(args, name) is None for name in required):
            parser.error("manifest mode requires manifest/output/model inputs")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = (
            run_materialization(args)
            if args.candidate_root is not None
            else run_manifest(args)
        )
    except Exception as exc:
        print(json.dumps({"failure_class": type(exc).__name__, "message": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
