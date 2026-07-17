from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_ATOM_CONTRACTS,
)


EXPECTED_ATOMS = tuple(DP_CAMP_ATOM_NAMES_V10)
EXPECTED_PAPER_9D = tuple(CAMP_ATOM_NAMES)
FORBIDDEN_CONTEXT_TOKENS = (
    "identity",
    "map_family",
    "route_family",
    "scenario_family",
    "scenario_id",
    "split_id",
    "seed",
    "holdout",
    "outcome",
    "collision",
    "future",
    "ground_truth",
    "private_latent",
)


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not (set(value) - frozenset("0123456789abcdef"))
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _read_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        item = Path(relative.strip().removeprefix("./"))
        if (
            separator != "  "
            or not _is_sha256(digest)
            or item.is_absolute()
            or ".." in item.parts
            or item.as_posix() in entries
        ):
            raise ValueError("unsafe or duplicate SHA256SUMS entry")
        entries[item.as_posix()] = digest
    if not entries:
        raise ValueError("SHA256SUMS is empty")
    return entries


def verify_seal(root: Path, expected_root_sha256: str) -> int:
    source = Path(root).resolve()
    manifest = source / "SHA256SUMS"
    receipt = source / "ROOT_SHA256SUMS"
    if (
        not source.is_dir()
        or not _is_sha256(expected_root_sha256)
        or not manifest.is_file()
        or not receipt.is_file()
        or _file_sha256(manifest) != expected_root_sha256
        or receipt.read_text(encoding="ascii")
        != f"{expected_root_sha256}  SHA256SUMS\n"
    ):
        raise ValueError(f"sealed artifact root mismatch: {source}")
    entries = _read_manifest(manifest)
    actual = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    }
    if actual != set(entries):
        raise ValueError(f"sealed artifact inventory mismatch: {source}")
    for relative, digest in entries.items():
        if _file_sha256(source / relative) != digest:
            raise ValueError(f"sealed artifact payload mismatch: {source / relative}")
    return len(entries)


def seal_artifact(root: Path) -> str:
    source = Path(root)
    files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    (source / "SHA256SUMS").write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(source / "SHA256SUMS")
    (source / "ROOT_SHA256SUMS").write_text(
        f"{digest}  SHA256SUMS\n", encoding="ascii"
    )
    return digest


def validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    atoms = config.get("atom_contract")
    corpus = config.get("corpus_contract")
    labels = config.get("train_only_label_contract")
    audit = config.get("audit_contract")
    context = config.get("causal_context_contract")
    boundary = config.get("boundary_contract")
    sources = config.get("source_authority")
    if (
        config.get("schema_version") != "camp_dp_v25_atom_context_freeze_v1"
        or not isinstance(atoms, Mapping)
        or tuple(atoms.get("atom_names", ())) != EXPECTED_ATOMS
        or tuple(atoms.get("paper_consistent_9d_subset_indices", ()))
        != tuple(range(9))
        or tuple(atoms.get("dp_extension_indices", ())) != tuple(range(9, 14))
        or tuple(atoms.get("active_mask_14d", ())) != (True,) * 14
        or tuple(atoms.get("active_mask_9d", ())) != (True,) * 9 + (False,) * 5
        or atoms.get("new_atom_admission_authorized") is not False
        or atoms.get("score_contract") != "score_k=a_k^T*w(x)"
        or not isinstance(corpus, Mapping)
        or corpus.get("split") != "train"
        or corpus.get("candidate_k") != 8
        or corpus.get("snapshot_count") != 67796
        or not isinstance(labels, Mapping)
        or labels.get("actual_closed_loop_outcome") is not False
        or labels.get("future_outcome_fields_read") is not False
        or labels.get("holdout_fields_read") is not False
        or not isinstance(audit, Mapping)
        or not isinstance(context, Mapping)
        or context.get("schema_version") != "camp_dp_v25_causal_context_raw_v1"
        or context.get("every_feature_causal") is not True
        or context.get("future_fields_allowed") is not False
        or context.get("closed_loop_outcome_fields_allowed") is not False
        or context.get("ground_truth_holdout_fields_allowed") is not False
        or context.get("map_route_scenario_split_identity_or_proxy_allowed")
        is not False
        or context.get("private_dp_latent_allowed") is not False
        or context.get("softmax_allowed") is not False
        or context.get("neural_context_head_allowed") is not False
        or not isinstance(boundary, Mapping)
        or any(value is not False for value in boundary.values())
        or not isinstance(sources, Mapping)
        or set(sources)
        != {
            "merged_train_corpus",
            "merged_train_corpus_review",
            "atom_freeze",
            "atom_freeze_review",
            "causal_labels",
            "causal_labels_review",
        }
    ):
        raise ValueError("v25 atom/context freeze contract drift")
    features = context.get("raw_features")
    if not isinstance(features, list) or len(features) != 26:
        raise ValueError("v25 context feature count drift")
    names: list[str] = []
    for feature in features:
        if (
            not isinstance(feature, Mapping)
            or not isinstance(feature.get("name"), str)
            or not isinstance(feature.get("source"), str)
            or not isinstance(feature.get("unit"), str)
            or type(feature.get("signed")) is not bool
        ):
            raise ValueError("v25 context feature declaration is invalid")
        name = str(feature["name"])
        haystack = f"{name} {feature['source']}".lower()
        if name in names or any(token in haystack for token in FORBIDDEN_CONTEXT_TOKENS):
            raise ValueError(f"forbidden or duplicate causal context: {name}")
        names.append(name)
    if context.get("phi_dimension") != 1 + 2 * len(features):
        raise ValueError("v25 complement-lift dimension drift")
    for value in sources.values():
        if (
            not isinstance(value, Mapping)
            or not isinstance(value.get("artifact"), str)
            or not _is_sha256(value.get("artifact_root_sha256"))
        ):
            raise ValueError("v25 source authority is invalid")
    return dict(config)


def _average_ranks(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    order = np.argsort(array, kind="mergesort")
    sorted_values = array[order]
    ranks = np.empty(array.size, dtype=np.float64)
    start = 0
    while start < array.size:
        end = start + 1
        while end < array.size and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def _correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    x = np.asarray(left, dtype=np.float64).reshape(-1)
    y = np.asarray(right, dtype=np.float64).reshape(-1)
    if x.size != y.size or x.size < 2 or np.std(x) <= 1e-15 or np.std(y) <= 1e-15:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _quantiles(values: Sequence[float], points: Sequence[float]) -> list[float | None]:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if not finite.size:
        return [None for _ in points]
    return [float(value) for value in np.quantile(finite, points)]


def compute_atom_audit(
    *,
    atoms: np.ndarray,
    costs: np.ndarray,
    oracle: np.ndarray,
    source_valid: np.ndarray,
    scales: np.ndarray,
    route_groups: Sequence[str],
    source_strata: Mapping[str, np.ndarray],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    matrix = np.asarray(atoms, dtype=np.float64)
    label_cost = np.asarray(costs, dtype=np.float64)
    oracle_index = np.asarray(oracle, dtype=np.int64).reshape(-1)
    valid = np.asarray(source_valid)
    scale = np.asarray(scales, dtype=np.float64).reshape(-1)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or label_cost.shape != matrix.shape[:2]
        or valid.dtype.kind != "b"
        or valid.shape != matrix.shape[:2]
        or scale.shape != (14,)
        or len(route_groups) != matrix.shape[0]
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(label_cost).all()
        or np.any(label_cost < 0.0)
        or not np.isfinite(scale).all()
        or np.any(scale <= 0.0)
        or not valid.any(axis=1).all()
        or np.any(oracle_index < 0)
        or np.any(oracle_index >= 8)
        or not valid[np.arange(matrix.shape[0]), oracle_index].all()
    ):
        raise ValueError("v25 atom audit inputs are invalid")

    audit_contract = config["audit_contract"]
    labels = config["train_only_label_contract"]
    epsilon = float(audit_contract["candidate_variation_epsilon"])
    zero_epsilon = float(audit_contract["zero_epsilon"])
    clip = float(labels["normalized_atom_clip"])
    normalized = np.clip(matrix / scale.reshape(1, 1, 14), 0.0, clip)
    flat_valid = valid.reshape(-1)
    flat_cost = label_cost.reshape(-1)[flat_valid]
    flat_normalized = normalized.reshape(-1, 14)[flat_valid]
    max_sample = int(audit_contract["spearman_sample_max_candidate_rows"])
    sample_count = min(max_sample, flat_normalized.shape[0])
    sample_positions = np.linspace(
        0, flat_normalized.shape[0] - 1, sample_count, dtype=np.int64
    )
    cost_ranks = _average_ranks(flat_cost[sample_positions])
    route_array = np.asarray(route_groups, dtype=object)
    unique_routes = sorted(set(route_groups))
    atom_rows: list[dict[str, Any]] = []
    contracts = {contract.name: contract for contract in CANONICAL_ATOM_CONTRACTS}

    for atom_index, atom_name in enumerate(EXPECTED_ATOMS):
        raw = matrix[:, :, atom_index]
        norm = normalized[:, :, atom_index]
        raw_flat = raw.reshape(-1)[flat_valid]
        norm_flat = norm.reshape(-1)[flat_valid]
        candidate_range = np.max(raw, axis=1) - np.min(raw, axis=1)
        single_atom_oracle = np.argmin(np.where(valid, raw, np.inf), axis=1)
        route_correlations: list[float] = []
        for route in unique_routes:
            snapshot_mask = route_array == route
            route_valid = valid[snapshot_mask].reshape(-1)
            correlation = _correlation(
                normalized[snapshot_mask, :, atom_index].reshape(-1)[route_valid],
                label_cost[snapshot_mask].reshape(-1)[route_valid],
            )
            if correlation is not None:
                route_correlations.append(correlation)
        event_stability: dict[str, Any] = {}
        for stratum, snapshot_mask_raw in sorted(source_strata.items()):
            snapshot_mask = np.asarray(snapshot_mask_raw, dtype=bool)
            if snapshot_mask.shape != (matrix.shape[0],) or not snapshot_mask.any():
                continue
            event_valid = valid[snapshot_mask].reshape(-1)
            event_stability[stratum] = {
                "snapshot_count": int(np.sum(snapshot_mask)),
                "pearson_with_causal_cost": _correlation(
                    normalized[snapshot_mask, :, atom_index].reshape(-1)[event_valid],
                    label_cost[snapshot_mask].reshape(-1)[event_valid],
                ),
                "single_atom_oracle_agreement_rate": float(
                    np.mean(single_atom_oracle[snapshot_mask] == oracle_index[snapshot_mask])
                ),
            }
        route_q10, route_q50, route_q90 = _quantiles(
            route_correlations, (0.1, 0.5, 0.9)
        )
        contract = contracts[atom_name]
        atom_rows.append(
            {
                "index": atom_index,
                "name": atom_name,
                "subset": "paper_9d" if atom_index < 9 else "dp_14d_extension",
                "unit": contract.unit,
                "formula": contract.formula,
                "inputs": list(contract.inputs),
                "decision_time_availability": contract.decision_time_availability,
                "future_dependency": contract.future_dependency,
                "finite": bool(np.isfinite(raw_flat).all()),
                "nonnegative": bool(np.all(raw_flat >= 0.0)),
                "minimum": float(np.min(raw_flat)),
                "mean": float(np.mean(raw_flat)),
                "p50": float(np.quantile(raw_flat, 0.5)),
                "p95": float(np.quantile(raw_flat, 0.95)),
                "p99": float(np.quantile(raw_flat, 0.99)),
                "maximum": float(np.max(raw_flat)),
                "scale": float(scale[atom_index]),
                "zero_rate": float(np.mean(raw_flat <= zero_epsilon)),
                "clip_saturation_rate": float(np.mean(norm_flat >= clip - 1e-12)),
                "candidate_variable_snapshot_rate": float(
                    np.mean(candidate_range > epsilon)
                ),
                "candidate_range_p50": float(np.quantile(candidate_range, 0.5)),
                "candidate_range_p95": float(np.quantile(candidate_range, 0.95)),
                "pearson_with_causal_cost": _correlation(norm_flat, flat_cost),
                "spearman_with_causal_cost": _correlation(
                    _average_ranks(norm_flat[sample_positions]), cost_ranks
                ),
                "single_atom_oracle_agreement_rate": float(
                    np.mean(single_atom_oracle == oracle_index)
                ),
                "normalized_candidate0_minus_oracle_mean": float(
                    np.mean(norm[:, 0] - norm[np.arange(matrix.shape[0]), oracle_index])
                ),
                "route_correlation_available_group_count": len(route_correlations),
                "route_correlation_q10_q50_q90": [route_q10, route_q50, route_q90],
                "route_positive_alignment_fraction": (
                    float(np.mean(np.asarray(route_correlations) > 0.0))
                    if route_correlations
                    else None
                ),
                "event_stability": event_stability,
                "normalization_transform_monotone_non_decreasing": True,
                "label_severity_weight": float(labels["atom_severity_weights"][atom_index]),
            }
        )

    pearson = np.empty((14, 14), dtype=np.float64)
    spearman = np.empty((14, 14), dtype=np.float64)
    sample_ranks = np.column_stack(
        [
            _average_ranks(flat_normalized[sample_positions, index])
            for index in range(14)
        ]
    )
    for left in range(14):
        for right in range(14):
            pearson[left, right] = (
                1.0
                if left == right
                else (_correlation(flat_normalized[:, left], flat_normalized[:, right]) or 0.0)
            )
            spearman[left, right] = (
                1.0
                if left == right
                else (_correlation(sample_ranks[:, left], sample_ranks[:, right]) or 0.0)
            )
    threshold = float(audit_contract["redundancy_abs_spearman_threshold"])
    redundant_pairs = [
        {
            "left": EXPECTED_ATOMS[left],
            "right": EXPECTED_ATOMS[right],
            "pearson": float(pearson[left, right]),
            "spearman": float(spearman[left, right]),
        }
        for left in range(14)
        for right in range(left + 1, 14)
        if abs(spearman[left, right]) >= threshold
    ]
    return {
        "snapshot_count": int(matrix.shape[0]),
        "candidate_count": int(matrix.shape[0] * matrix.shape[1]),
        "source_valid_candidate_count": int(np.sum(valid)),
        "route_group_count": len(unique_routes),
        "spearman_sample_candidate_count": sample_count,
        "atom_rows": atom_rows,
        "pearson_correlation_matrix": pearson.tolist(),
        "spearman_correlation_matrix": spearman.tolist(),
        "redundancy_threshold": threshold,
        "redundant_pairs": redundant_pairs,
    }


def _load_inputs(config: Mapping[str, Any]) -> dict[str, Any]:
    source_specs = config["source_authority"]
    roots = {
        name: Path(spec["artifact"]) for name, spec in source_specs.items()
    }
    verified_counts = {
        name: verify_seal(root, source_specs[name]["artifact_root_sha256"])
        for name, root in roots.items()
    }
    merged = _read_json(roots["merged_train_corpus"] / "merged_summary.json")
    freeze = _read_json(roots["atom_freeze"] / "atom_freeze.json")
    manifest = _read_json(roots["causal_labels"] / "label_manifest.json")
    corpus = config["corpus_contract"]
    expected_snapshots = int(corpus["snapshot_count"])
    if (
        merged.get("snapshot_count") != expected_snapshots
        or merged.get("route_count") != corpus["route_count"]
        or merged.get("retained_route_seed_runs") != corpus["retained_route_seed_count"]
        or freeze.get("atom_names") != list(EXPECTED_ATOMS)
        or freeze.get("active_atom_mask") != [True] * 14
        or manifest.get("snapshot_count") != expected_snapshots
        or manifest.get("candidate_count") != expected_snapshots * 8
        or manifest.get("actual_closed_loop_outcomes_read") is not False
        or manifest.get("future_outcome_fields_read") is not False
        or manifest.get("holdout_opened") is not False
    ):
        raise ValueError("v25 source corpus/freeze/label authority drift")
    scales = np.asarray(freeze["atom_scales"], dtype=np.float64)
    if not np.array_equal(scales, np.asarray(manifest["atom_scales"], dtype=np.float64)):
        raise ValueError("v25 source atom scale drift")

    label_root = roots["causal_labels"]
    costs = np.fromfile(label_root / "candidate_cost.f64le", dtype="<f8").reshape(
        expected_snapshots, 8
    )
    oracle = np.fromfile(label_root / "oracle_index.u8", dtype=np.uint8)
    source_valid = np.fromfile(
        label_root / "source_valid_mask.u8", dtype=np.uint8
    ).reshape(expected_snapshots, 8)
    if not np.all((source_valid == 0) | (source_valid == 1)):
        raise ValueError("v25 source-valid mask is not boolean")
    source_valid_bool = source_valid.astype(bool)

    source_artifacts = merged.get("source_artifacts")
    if not isinstance(source_artifacts, Mapping):
        raise ValueError("merged source artifact inventory is absent")
    atom_batches: list[np.ndarray] = []
    route_groups: list[str] = []
    stratum_rows: list[dict[str, bool]] = []
    index_path = roots["merged_train_corpus"] / "snapshot_index.jsonl"
    snapshot_bytes_verified = 0
    for line_number, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        phase = row.get("phase")
        source_spec = source_artifacts.get(phase) if isinstance(phase, str) else None
        if (
            not isinstance(source_spec, Mapping)
            or not isinstance(source_spec.get("path"), str)
            or not _is_sha256(row.get("sha256"))
            or not isinstance(row.get("relative_path"), str)
        ):
            raise ValueError(f"invalid merged snapshot index row {line_number}")
        path = Path(source_spec["path"]) / row["relative_path"]
        payload_bytes = path.read_bytes()
        if hashlib.sha256(payload_bytes).hexdigest() != row["sha256"]:
            raise ValueError(f"snapshot content drift at row {line_number}")
        snapshot_bytes_verified += len(payload_bytes)
        snapshot = json.loads(payload_bytes)
        feature = snapshot.get("feature_payload")
        sidecar = snapshot.get("sidecar")
        if (
            snapshot.get("schema_version") != "camp_dp_v24_native_train_snapshot_v1"
            or not isinstance(feature, Mapping)
            or not isinstance(sidecar, Mapping)
            or sidecar.get("split") != "train"
            or sidecar.get("candidate_tensor_sha256_before")
            != sidecar.get("candidate_tensor_sha256_after")
            or sidecar.get("default_candidate0_identity", {}).get("elementwise_equal")
            is not True
        ):
            raise ValueError(f"snapshot boundary drift at row {line_number}")
        batch = np.asarray(feature.get("atom_matrix"), dtype=np.float64)
        batch_valid = np.asarray(feature.get("source_valid_mask"))
        if batch.shape != (8, 14) or batch_valid.shape != (8,):
            raise ValueError(f"snapshot feature shape drift at row {line_number}")
        if not np.array_equal(batch_valid.astype(bool), source_valid_bool[line_number - 1]):
            raise ValueError(f"snapshot/label source-valid mismatch at row {line_number}")
        route = sidecar.get("route_identity_sha256")
        strata = sidecar.get("source_stratum")
        if not _is_sha256(route) or not isinstance(strata, Mapping):
            raise ValueError(f"snapshot audit grouping drift at row {line_number}")
        atom_batches.append(batch)
        route_groups.append(str(route))
        stratum_rows.append({str(key): bool(value) for key, value in strata.items()})
    if len(atom_batches) != expected_snapshots:
        raise ValueError("snapshot index count drift")
    stratum_names = sorted({key for row in stratum_rows for key in row})
    source_strata = {
        name: np.asarray([row.get(name, False) for row in stratum_rows], dtype=bool)
        for name in stratum_names
    }
    return {
        "atoms": np.stack(atom_batches),
        "costs": costs,
        "oracle": oracle,
        "source_valid": source_valid_bool,
        "scales": scales,
        "route_groups": route_groups,
        "source_strata": source_strata,
        "verified_file_counts": verified_counts,
        "snapshot_payload_bytes_verified": snapshot_bytes_verified,
        "label_manifest": manifest,
    }


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_tracked_clean(repo: Path) -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError(f"tracked repository is dirty: {repo}")


def _audit_markdown(result: Mapping[str, Any]) -> str:
    rows = [
        "# V25 train-only atom and causal-context audit",
        "",
        f"- snapshots / candidates / routes: `{result['atom_audit']['snapshot_count']} / {result['atom_audit']['candidate_count']} / {result['atom_audit']['route_group_count']}`",
        f"- redundant atom pairs at |Spearman| >= {result['atom_audit']['redundancy_threshold']}: `{len(result['atom_audit']['redundant_pairs'])}`",
        "- context utility: `phase3 outcome-blind capability pilot required`",
        "- atoms added / silently removed: `0 / 0`",
        "",
        "| atom | subset | zero rate | variable snapshots | p95 / scale | clip saturation | cost Spearman |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for atom in result["atom_audit"]["atom_rows"]:
        rows.append(
            "| {name} | {subset} | {zero_rate:.6f} | {candidate_variable_snapshot_rate:.6f} | {p95:.6g} / {scale:.6g} | {clip_saturation_rate:.6f} | {spearman_with_causal_cost:.6f} |".format(
                **atom
            )
        )
    return "\n".join(rows) + "\n"


def execute_audit(
    *, repo: Path, dp_repo: Path, config_path: Path, output_dir: Path
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    dp_repo = Path(dp_repo).resolve()
    output = Path(output_dir).resolve()
    stage = output.with_name(output.name + ".tmp")
    if output.exists() or stage.exists():
        raise FileExistsError("v25 atom/context audit target already exists")
    _require_tracked_clean(repo)
    _require_tracked_clean(dp_repo)
    config_bytes = Path(config_path).read_bytes()
    config = validate_config(json.loads(config_bytes))
    camp_head = _git_head(repo)
    dp_head = _git_head(dp_repo)
    if dp_head != config["corpus_contract"]["fixed_dp_head"]:
        raise ValueError("fixed DP HEAD drift")
    started = time.perf_counter()
    loaded = _load_inputs(config)
    atom_audit = compute_atom_audit(
        atoms=loaded["atoms"],
        costs=loaded["costs"],
        oracle=loaded["oracle"],
        source_valid=loaded["source_valid"],
        scales=loaded["scales"],
        route_groups=loaded["route_groups"],
        source_strata=loaded["source_strata"],
        config=config,
    )
    source_valid_fraction = np.mean(loaded["source_valid"], axis=1)
    context = config["causal_context_contract"]
    result = {
        "schema_version": "camp_dp_v25_atom_context_audit_result_v1",
        "status": "passed_with_phase3_context_capability_gate_required",
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "source_authority": config["source_authority"],
        "verified_file_counts": loaded["verified_file_counts"],
        "snapshot_payload_bytes_verified": loaded["snapshot_payload_bytes_verified"],
        "atom_schema_version": "dp_camp_v10_14d",
        "paper_consistent_9d_subset": list(EXPECTED_PAPER_9D),
        "dp_14d_extension": list(EXPECTED_ATOMS[9:]),
        "active_atom_mask_14d": [True] * 14,
        "active_atom_mask_9d": [True] * 9 + [False] * 5,
        "atom_decision": "retain_all_14_and_compare_explicit_9d_14d_ablation",
        "new_atoms_admitted": [],
        "silently_excluded_atoms": [],
        "atom_audit": atom_audit,
        "causal_context_freeze": context,
        "v24_context_availability_audit": {
            "frozen_snapshot_raw_context_present": False,
            "candidate_source_valid_fraction_present": True,
            "candidate_source_valid_fraction_unique_values": sorted(
                float(value) for value in np.unique(source_valid_fraction)
            ),
            "candidate_source_valid_fraction_variable": bool(
                np.ptp(source_valid_fraction) > 0.0
            ),
            "requested_raw_feature_count": len(context["raw_features"]),
            "raw_feature_utility_measurable_on_v24_corpus": False,
            "context_conditioned_utility_decision": (
                "not_estimated_from_ids_or_v24_holdout; require phase3 outcome-blind "
                "live-request capability pilot before scene-conditioned training"
            ),
        },
        "boundaries": {
            "split": "train_only",
            "actual_closed_loop_outcomes_read": False,
            "future_fields_read": False,
            "v24_holdout_read": False,
            "fresh_benchmark_b_opened": False,
            "identity_fields_used_as_model_input": False,
            "dp_modified": False,
            "candidate_or_trajectory_modified": False,
            "training_executed": False,
            "calibration_executed": False,
            "promotion_deployment_online_activation": False,
        },
        "wall_clock_s": time.perf_counter() - started,
        "free_disk_bytes": shutil.disk_usage(output.parent).free,
        "minimum_free_disk_gib": 10,
        "next_work_target": "v25_scene_conditioned_implementation_and_context_capability_pilot",
    }
    if result["free_disk_bytes"] <= 10 * 1024**3:
        raise RuntimeError("10 GiB disk floor is unavailable")
    stage.mkdir(parents=False)
    (stage / "atom_context_audit.json").write_bytes(_canonical_json_bytes(result))
    (stage / "atom_context_audit.md").write_text(
        _audit_markdown(result), encoding="utf-8"
    )
    (stage / "config.json").write_bytes(config_bytes)
    (stage / "COMMAND").write_text(
        "train-only V24 sealed atom audit and V25 causal-context schema freeze\n",
        encoding="utf-8",
    )
    (stage / "HEADS").write_text(
        f"CAMP_HEAD={camp_head}\nDP_HEAD={dp_head}\n", encoding="ascii"
    )
    (stage / "run.exit").write_text("0\n", encoding="ascii")
    (stage / "stderr.txt").write_text("", encoding="utf-8")
    (stage / "stdout.txt").write_text(
        json.dumps(
            {
                "status": result["status"],
                "snapshot_count": atom_audit["snapshot_count"],
                "redundant_pair_count": len(atom_audit["redundant_pairs"]),
                "next_work_target": result["next_work_target"],
            },
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    root_sha256 = seal_artifact(stage)
    os.replace(stage, output)
    result["artifact"] = str(output)
    result["artifact_root_sha256"] = root_sha256
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = execute_audit(
        repo=args.repo,
        dp_repo=args.dp_repo,
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
