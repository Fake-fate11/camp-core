#!/usr/bin/env python3
"""Materialize train-only causal soft-risk labels for the v22 selector."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner import DP_CAMP_ATOM_NAMES_V10


FORMAL_SEEDS = frozenset({11, 12, 13})
IDENTITY_FIELDS = frozenset(
    {
        "logical_map_sha256",
        "map_id",
        "route_id",
        "route_identity_sha256",
        "group_sha256",
        "split",
        "seed",
    }
)
FEATURE_FIELDS = frozenset(
    {"atom_matrix", "source_valid_mask", "candidate_row_sha256"}
)


def causal_soft_risk_labels(
    atoms: np.ndarray,
    *,
    source_valid: np.ndarray,
    physical_feasible: np.ndarray,
    scales: np.ndarray,
    atom_severity_weights: np.ndarray,
    physical_risk_penalty: float,
    normalized_atom_clip: float,
) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    valid = np.asarray(source_valid, dtype=bool)
    physical = np.asarray(physical_feasible, dtype=bool)
    scale = np.asarray(scales, dtype=np.float64).reshape(-1)
    weights = np.asarray(atom_severity_weights, dtype=np.float64).reshape(-1)
    if matrix.ndim != 3 or matrix.shape[1:] != (8, 14):
        raise ValueError("atoms must have shape [N,8,14]")
    if valid.shape != matrix.shape[:2] or physical.shape != matrix.shape[:2]:
        raise ValueError("source-valid and physical masks must have shape [N,8]")
    if scale.shape != (14,) or weights.shape != (14,):
        raise ValueError("scales and severity weights must contain 14 values")
    if (
        not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(scale).all()
        or np.any(scale <= 0.0)
        or not np.isfinite(weights).all()
        or np.any(weights < 0.0)
    ):
        raise ValueError("label atoms, scales, and weights must be finite nonnegative")
    if not valid.any(axis=1).all():
        raise ValueError("every snapshot needs a source-valid candidate")
    if (
        not np.isfinite(physical_risk_penalty)
        or physical_risk_penalty < 0.0
        or not np.isfinite(normalized_atom_clip)
        or normalized_atom_clip <= 0.0
    ):
        raise ValueError("label penalty and clip must be finite and nonnegative")

    normalized = np.clip(
        matrix / scale.reshape(1, 1, -1),
        0.0,
        float(normalized_atom_clip),
    )
    costs = (
        float(physical_risk_penalty) * (~physical).astype(np.float64)
        + np.einsum("nkr,r->nk", normalized, weights)
    )
    if not np.isfinite(costs).all():
        raise ValueError("causal soft-risk labels must be finite")
    oracle = np.argmin(np.where(valid, costs, np.inf), axis=1)
    return costs, oracle.astype(np.int64)


def fit_train_atom_scales(
    atoms: np.ndarray, *, percentile: float, floor: float
) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    if matrix.ndim != 3 or matrix.shape[1:] != (8, 14):
        raise ValueError("atoms must have shape [N,8,14]")
    if not np.isfinite(matrix).all() or np.any(matrix < 0.0):
        raise ValueError("train atoms must be finite nonnegative")
    if not 0.0 < percentile <= 100.0 or not np.isfinite(floor) or floor <= 0.0:
        raise ValueError("scale percentile and floor are invalid")
    scales = np.maximum(
        np.percentile(matrix.reshape(-1, 14), float(percentile), axis=0),
        float(floor),
    )
    cross_candidate_range = np.ptp(matrix, axis=1)
    supported = np.any(cross_candidate_range > 1e-12, axis=0)
    return scales, supported


def materialize_train_labels(
    *,
    snapshot_dir: Path,
    output_dir: Path,
    config: Mapping[str, Any],
    source_artifact_root_sha256: str,
) -> dict[str, Any]:
    contract = _validate_config(config)
    if not _is_sha256(source_artifact_root_sha256):
        raise ValueError("source artifact root must be lowercase SHA256")
    paths = sorted(Path(snapshot_dir).glob("*.json"))
    if not paths:
        raise ValueError("train snapshot directory is empty")

    payloads = []
    digests = []
    for path in paths:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if path.stem != digest:
            raise ValueError("snapshot content SHA mismatch")
        payload = json.loads(content)
        _validate_snapshot(payload)
        payloads.append(payload)
        digests.append(digest)

    atoms = np.asarray(
        [payload["feature_payload"]["atom_matrix"] for payload in payloads],
        dtype=np.float64,
    )
    source_valid = np.asarray(
        [payload["feature_payload"]["source_valid_mask"] for payload in payloads],
        dtype=bool,
    )
    physical = np.asarray(
        [payload["sidecar"]["physical_feasible_mask"] for payload in payloads],
        dtype=bool,
    )
    scales, supported = fit_train_atom_scales(
        atoms,
        percentile=float(contract["scale_percentile"]),
        floor=float(contract["scale_floor"]),
    )
    severity_weights = np.asarray(
        contract["atom_severity_weights"], dtype=np.float64
    )
    costs, oracle = causal_soft_risk_labels(
        atoms,
        source_valid=source_valid,
        physical_feasible=physical,
        scales=scales,
        atom_severity_weights=severity_weights,
        physical_risk_penalty=float(contract["physical_risk_penalty"]),
        normalized_atom_clip=float(contract["normalized_atom_clip"]),
    )

    output = Path(output_dir)
    label_dir = output / "labels"
    label_dir.mkdir(parents=True, exist_ok=True)
    scales_sha = hashlib.sha256(_canonical_json_bytes(scales.tolist())).hexdigest()
    label_sha = []
    for index, digest in enumerate(digests):
        label = {
            "schema_version": "v22_causal_soft_risk_label_v1",
            "snapshot_sha256": digest,
            "label_source": contract["schema_version"],
            "candidate_cost": costs[index].tolist(),
            "oracle_index": int(oracle[index]),
            "source_valid_mask": source_valid[index].tolist(),
            "physical_feasible_mask": physical[index].tolist(),
            "all_k_high_risk": bool(
                source_valid[index].all() and not physical[index].any()
            ),
            "physical_risk_penalty": float(contract["physical_risk_penalty"]),
            "physical_risk_semantics": contract["physical_risk_semantics"],
            "atom_scales_sha256": scales_sha,
            "actual_closed_loop_outcome": False,
        }
        content = _canonical_json_bytes(label)
        path = label_dir / f"{digest}.json"
        path.write_bytes(content)
        label_sha.append(hashlib.sha256(content).hexdigest())

    oracle_histogram = np.bincount(oracle, minlength=8).astype(int).tolist()
    summary = {
        "schema_version": "v22_causal_soft_risk_label_manifest_v1",
        "status": "complete",
        "source_artifact_root_sha256": source_artifact_root_sha256,
        "label_contract": dict(contract),
        "snapshot_count": len(payloads),
        "label_file_sha256": label_sha,
        "atom_scales": scales.tolist(),
        "atom_scales_sha256": scales_sha,
        "supported_atom_mask": supported.tolist(),
        "supported_atom_names": [
            name
            for name, is_supported in zip(DP_CAMP_ATOM_NAMES_V10, supported)
            if is_supported
        ],
        "unsupported_atom_names": [
            name
            for name, is_supported in zip(DP_CAMP_ATOM_NAMES_V10, supported)
            if not is_supported
        ],
        "oracle_histogram": oracle_histogram,
        "oracle_candidate0_count": oracle_histogram[0],
        "oracle_non_candidate0_count": len(payloads) - oracle_histogram[0],
        "all_k_high_risk_count": int(
            np.sum(source_valid.all(axis=1) & ~physical.any(axis=1))
        ),
        "candidate_cost_min": float(np.min(costs)),
        "candidate_cost_max": float(np.max(costs)),
        "actual_closed_loop_outcomes_read": False,
        "future_outcome_fields_read": False,
        "identity_fields_used_as_label_or_feature": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "model_trained": False,
        "simulator_executed": False,
        "claim_authorized": False,
        "next_work_target": "v22_convex_selector_training_tdd_only",
    }
    (output / "label_manifest.json").write_bytes(_canonical_json_bytes(summary))
    return summary


def _validate_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    if config.get("schema_version") != "camp_dp_v22_training_v1":
        raise ValueError("v22 training config schema mismatch")
    if config.get("execution_split") != "train":
        raise ValueError("label materialization is train-only")
    for name in (
        "formal_seeds_authorized",
        "calibration_execution_authorized",
        "holdout_execution_authorized",
        "claim_authorized",
    ):
        if config.get(name) is not False:
            raise ValueError(f"{name} must remain false")
    contract = config.get("label_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("label_contract must be a mapping")
    if (
        contract.get("schema_version") != "v22_causal_soft_risk_surrogate_v1"
        or contract.get("oracle_eligibility") != "source_valid_mask_only"
        or contract.get("physical_risk_semantics")
        != "finite_additive_cost_not_veto"
        or contract.get("actual_closed_loop_outcome") is not False
    ):
        raise ValueError("causal soft-risk label contract mismatch")
    weights = np.asarray(contract.get("atom_severity_weights"), dtype=np.float64)
    if weights.shape != (14,) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("atom severity weights must be finite nonnegative 14D")
    return contract


def _validate_snapshot(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("decision snapshot schema mismatch")
    features = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if not isinstance(features, Mapping) or set(features) != FEATURE_FIELDS:
        raise ValueError("feature payload schema mismatch")
    if IDENTITY_FIELDS.intersection(features):
        raise ValueError("identity is forbidden in feature payload")
    if not isinstance(sidecar, Mapping) or sidecar.get("split") != "train":
        raise ValueError("label snapshots must be train split")
    seed = sidecar.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed in FORMAL_SEEDS:
        raise ValueError("formal seed is forbidden")
    physical = sidecar.get("physical_feasible_mask")
    if (
        not isinstance(physical, list)
        or len(physical) != 8
        or any(not isinstance(value, bool) for value in physical)
    ):
        raise ValueError("physical risk mask must contain eight booleans")


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    source = config.get("source_corpus")
    if not isinstance(source, Mapping):
        raise ValueError("source_corpus must be a mapping")
    artifact = Path(str(source["artifact"]))
    expected_root = str(source["artifact_root_sha256"])
    actual_root = hashlib.sha256((artifact / "SHA256SUMS").read_bytes()).hexdigest()
    if actual_root != expected_root:
        raise ValueError("source corpus root SHA mismatch")
    summary = materialize_train_labels(
        snapshot_dir=artifact / "corpus" / "snapshots",
        output_dir=args.output,
        config=config,
        source_artifact_root_sha256=actual_root,
    )
    expected_count = int(source["expected_snapshot_count"])
    if summary["snapshot_count"] != expected_count:
        raise ValueError("source corpus snapshot count mismatch")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
