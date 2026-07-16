#!/usr/bin/env python3
"""Freeze the v24 train-only label and route-cluster training plan.

This gate is deliberately static: it verifies sealed train authority, freezes
the causal label policy and nested route membership, and checks that the exact
convex solver is available.  It does not materialize labels or solve a model.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CONFIG_SCHEMA = "camp_dp_v24_convex_training_plan_v1"
LABEL_SCHEMA = "camp_dp_v24_causal_soft_risk_surrogate_v1"
CURVE_SCHEMA = "camp_dp_v24_route_cluster_learning_curve_v1"
EXPECTED_ROUTES = 375
EXPECTED_SEEDS = (24001, 24002, 24003, 24004, 24005)
EXPECTED_ROUTE_SEEDS = 1875
EXPECTED_SNAPSHOTS = 67796
EXPECTED_LEVELS = (25, 50, 75, 100)
EXPECTED_LEVEL_ROUTE_COUNTS = (94, 188, 281, 375)
EXPECTED_SEVERITY = (
    0.0,
    0.0,
    0.25,
    0.25,
    10.0,
    0.0,
    0.0,
    20.0,
    10.0,
    1.0,
    15.0,
    1.0,
    15.0,
    0.25,
)
EXPECTED_ATOM_CONTRACT_SHA256 = (
    "b82b3ffe2579c567ab4460a78d630a9191bd18bea7874e9d85e32d1219bc50de"
)
MINIMUM_FREE_BYTES = 10 * 1024**3
REMAINING_TASK_LOCK = Path(
    "/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock"
)
SOURCE_NAMES = (
    "merged_train_corpus",
    "merged_train_corpus_review",
    "atom_freeze",
    "atom_freeze_review",
)
EXPECTED_SOURCE_AUTHORITY = {
    "merged_train_corpus": {
        "artifact": (
            "/root/autodl-tmp/"
            "camp_dp_v24_native_corpus_merged_train_assembly_"
            "5b725629_20260716T154602CST"
        ),
        "artifact_root_sha256": (
            "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc"
        ),
    },
    "merged_train_corpus_review": {
        "artifact": (
            "/root/autodl-tmp/"
            "camp_dp_v24_native_corpus_merged_train_assembly_independent_review_"
            "5b725629_20260716T154723CST"
        ),
        "artifact_root_sha256": (
            "925db2aa58f136c20b3e9054d87dbd8d73d4162d18d079b10abbcacc63f09490"
        ),
    },
    "atom_freeze": {
        "artifact": (
            "/root/autodl-tmp/"
            "camp_dp_v24_train_atom_availability_freeze_"
            "dc6f3715_20260716T190035CST"
        ),
        "artifact_root_sha256": (
            "ced620a4a5852e9e4196a2d272ef9b0ac1963512ecd62c2bf3612a3ed252438b"
        ),
    },
    "atom_freeze_review": {
        "artifact": (
            "/root/autodl-tmp/"
            "camp_dp_v24_train_atom_availability_freeze_independent_review_"
            "dc6f3715_20260716T190514CST"
        ),
        "artifact_root_sha256": (
            "a88e6d43041e4f8005a7df5cccd9dd64510758a9c2a4af1de15e339e250e80b8"
        ),
    },
}
CONFIG_RELATIVE = Path(
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json"
)
RECEIPT_FIELDS = frozenset(
    {
        "phase",
        "relative_path",
        "sha256",
        "record_key",
        "map_family_id",
        "logical_map_sha256",
        "corridor_group_sha256",
        "route_identity_sha256",
        "seed",
        "status",
        "snapshot_count",
        "failure_stage",
        "failure_reason",
    }
)
_SHA256_HEX = frozenset("0123456789abcdef")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= _SHA256_HEX
    )


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL row {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} is not an object")
        rows.append(row)
    return rows


def _read_sha256_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split(None, 1)
        except ValueError as exc:
            raise ValueError("invalid SHA256SUMS line") from exc
        normalized = relative.strip().removeprefix("./")
        item = PurePosixPath(normalized)
        if (
            not _is_sha256(digest)
            or item.is_absolute()
            or ".." in item.parts
            or normalized in entries
            or item.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ):
            raise ValueError("unsafe, duplicate, or reserved SHA256SUMS entry")
        entries[normalized] = digest
    if not entries:
        raise ValueError("SHA256SUMS is empty")
    return entries


def verify_complete_seal(root: Path, expected_root_sha256: str) -> dict[str, str]:
    """Verify the complete tree; nested reserved names and symlinks are forbidden."""

    supplied = Path(root)
    if supplied.is_symlink():
        raise ValueError("sealed artifact root symlink is forbidden")
    source = supplied.resolve()
    if not source.is_dir() or not _is_sha256(expected_root_sha256):
        raise ValueError("sealed artifact root or expected SHA256 is invalid")
    manifest = source / "SHA256SUMS"
    root_receipt = source / "ROOT_SHA256SUMS"
    if not manifest.is_file() or not root_receipt.is_file():
        raise ValueError("sealed artifact receipts are missing")
    if _file_sha256(manifest) != expected_root_sha256:
        raise ValueError("artifact root SHA256 mismatch")
    if root_receipt.read_text(encoding="ascii") != (
        f"{expected_root_sha256}  SHA256SUMS\n"
    ):
        raise ValueError("ROOT_SHA256SUMS receipt mismatch")
    entries = _read_sha256_manifest(manifest)
    actual: set[str] = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("sealed artifact symlink is forbidden")
        if not path.is_file():
            continue
        if path in {manifest, root_receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested reserved manifest name is forbidden")
        actual.add(path.relative_to(source).as_posix())
    if actual != set(entries):
        raise ValueError("sealed artifact inventory mismatch")
    for relative, digest in entries.items():
        if _file_sha256(source / relative) != digest:
            raise ValueError(f"sealed artifact file hash mismatch: {relative}")
    return entries


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} schema mismatch")


def validate_plan_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate every preregistered training-plan choice before data access."""

    if not isinstance(config, Mapping) or config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("v24 convex training config schema mismatch")
    _require_exact_keys(
        config,
        {
            "schema_version",
            "source_authority",
            "corpus_contract",
            "label_contract",
            "learning_curve_contract",
            "convex_master_contract",
            "boundary_contract",
        },
        "training plan",
    )
    authority = config["source_authority"]
    if not isinstance(authority, Mapping) or set(authority) != set(SOURCE_NAMES):
        raise ValueError("training source authority mismatch")
    normalized_authority: dict[str, dict[str, str]] = {}
    for name in SOURCE_NAMES:
        item = authority[name]
        if not isinstance(item, Mapping):
            raise ValueError(f"{name} authority must be an object")
        _require_exact_keys(item, {"artifact", "artifact_root_sha256"}, name)
        path = item.get("artifact")
        digest = item.get("artifact_root_sha256")
        pure = PurePosixPath(path) if isinstance(path, str) else None
        if (
            pure is None
            or not pure.is_absolute()
            or pure.parts[:3] != ("/", "root", "autodl-tmp")
            or ".." in pure.parts
            or len(pure.parts) <= 3
        ):
            raise ValueError(f"{name} artifact path is outside the authorized root")
        if not _is_sha256(digest):
            raise ValueError(f"{name} root SHA256 is invalid")
        normalized_authority[name] = {
            "artifact": path,
            "artifact_root_sha256": digest,
        }
    if normalized_authority != EXPECTED_SOURCE_AUTHORITY:
        raise ValueError("frozen v24 source authority path or root drift")

    corpus = config["corpus_contract"]
    if not isinstance(corpus, Mapping) or corpus != {
        "split": "train",
        "route_count": EXPECTED_ROUTES,
        "train_seeds": list(EXPECTED_SEEDS),
        "retained_route_seed_count": EXPECTED_ROUTE_SEEDS,
        "snapshot_count": EXPECTED_SNAPSHOTS,
        "candidate_count_per_snapshot": 8,
        "atom_schema_version": "dp_camp_v10_14d",
        "active_atom_count": 14,
        "atom_contract_projection_sha256": EXPECTED_ATOM_CONTRACT_SHA256,
    }:
        raise ValueError("v24 train corpus contract drift")

    label = config["label_contract"]
    if not isinstance(label, Mapping):
        raise ValueError("label contract must be an object")
    expected_label = {
        "schema_version": LABEL_SCHEMA,
        "formula": (
            "cost_ik=100*not_physical_feasible_ik+sum_r(q_r*"
            "clip(raw_atom_ikr/frozen_v24_scale_r,0,10))"
        ),
        "physical_risk_penalty": 100.0,
        "normalized_atom_clip": 10.0,
        "atom_severity_weights": list(EXPECTED_SEVERITY),
        "severity_policy_source": (
            "preexisting_v22_causal_soft_risk_policy_not_learned_selector_weights"
        ),
        "scale_source": "exact_gate34_v24_atom_freeze_no_recomputation",
        "active_mask_source": "exact_gate34_v24_atom_freeze_no_reselection",
        "oracle_eligibility": "source_valid_mask_only",
        "oracle_tie_break": "lowest_candidate_index",
        "physical_risk_semantics": "finite_additive_cost_not_veto",
        "all_k_high_risk_semantics": (
            "retain_snapshot_and_choose_relative_minimum_cost"
        ),
        "actual_closed_loop_outcome": False,
        "future_outcome_fields_read": False,
        "identity_fields_read_as_label_or_feature": False,
    }
    if label != expected_label:
        raise ValueError("v24 causal label contract drift")

    curve = config["learning_curve_contract"]
    expected_curve = {
        "schema_version": CURVE_SCHEMA,
        "ordering_domain_separator": "camp-v24-learning-curve-route-order-v1",
        "unit": "route_identity_with_all_five_seeds_receipts_and_snapshots",
        "levels_percent": list(EXPECTED_LEVELS),
        "levels_route_count": list(EXPECTED_LEVEL_ROUTE_COUNTS),
        "strictly_nested": True,
        "failed_routes_retained_in_denominator": True,
        "snapshot_count_targeted": False,
        "full_level_is_only_primary_model": True,
        "curve_metrics_used_for_model_selection": False,
        "unseen_corridor_or_map_claim_authorized": False,
    }
    if not isinstance(curve, Mapping) or curve != expected_curve:
        raise ValueError("route-cluster learning-curve contract drift")

    master = config["convex_master_contract"]
    expected_master = {
        "score_contract": "score_k(w)=a_k^T w",
        "atom_transform": "a_ikr=clip(raw_atom_ikr/frozen_v24_scale_r,0,10)",
        "weight_domain": "nonnegative_simplex_over_frozen_active_atoms_only",
        "margin_formula": "m_ik=clip(0.1*(cost_ik-cost_i_oracle),0,2)",
        "loss_formula": (
            "loss_i=max(0,max_source_valid_k(m_ik+"
            "(a_i_oracle-a_ik)^T*w))"
        ),
        "risk_type": "cvar",
        "cvar_alpha": 0.9,
        "l2_regularization": 0.0001,
        "l2_center": "uniform_over_frozen_active_atoms",
        "static_weight_lower_bounds": [0.0] * 14,
        "optimizer_initialization": (
            "solver_default_no_v18_v22_weight_initialization"
        ),
        "v18_v22_learned_weights_use": (
            "read_only_offline_ablation_only_not_initialization_constraint_or_"
            "model_selection"
        ),
        "solver": "CLARABEL",
        "solver_status_required": "optimal",
        "solver_fallback_allowed": False,
        "solver_options": {
            "tol_gap_abs": 1e-10,
            "tol_gap_rel": 1e-10,
            "tol_feas": 1e-10,
        },
        "cutting_plane_max_iterations": 20,
        "acceptance_gap_max": 1e-6,
        "final_new_cuts_required": 0,
        "epoch_semantics": False,
        "each_level_solved_independently": True,
        "any_level_failure_fails_learning_curve": True,
    }
    if not isinstance(master, Mapping) or master != expected_master:
        raise ValueError("convex master contract drift")

    boundaries = config["boundary_contract"]
    expected_boundaries = {
        "label_materialization_executed": False,
        "training_execution_authorized": False,
        "tuning_authorized": False,
        "calibration_access_authorized": False,
        "holdout_access_authorized": False,
        "actual_closed_loop_outcome_access_authorized": False,
        "claim_authorized": False,
        "dp_code_config_weights_checkpoint_request_modification_authorized": False,
        "candidate_tensor_modification_authorized": False,
    }
    if not isinstance(boundaries, Mapping) or boundaries != expected_boundaries:
        raise ValueError("closed training boundary drift")
    return {
        "source_authority": normalized_authority,
        "label_contract": dict(label),
        "learning_curve_contract": dict(curve),
        "convex_master_contract": dict(master),
    }


def causal_soft_risk_labels(
    atoms: np.ndarray,
    *,
    source_valid: np.ndarray,
    physical_feasible: np.ndarray,
    frozen_scales: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Reference math frozen by this preflight; no scale/mask fitting occurs."""

    matrix = np.asarray(atoms, dtype=np.float64)
    valid_raw = np.asarray(source_valid)
    physical_raw = np.asarray(physical_feasible)
    if valid_raw.dtype.kind != "b" or physical_raw.dtype.kind != "b":
        raise ValueError("source-valid and physical masks must contain booleans")
    valid = valid_raw.astype(bool, copy=False)
    physical = physical_raw.astype(bool, copy=False)
    scales = np.asarray(frozen_scales, dtype=np.float64).reshape(-1)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or valid.shape != matrix.shape[:2]
        or physical.shape != matrix.shape[:2]
        or scales.shape != (14,)
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or not valid.any(axis=1).all()
    ):
        raise ValueError("v24 causal label inputs are invalid")
    normalized = np.clip(matrix / scales.reshape(1, 1, 14), 0.0, 10.0)
    costs = 100.0 * (~physical).astype(np.float64) + np.einsum(
        "nkr,r->nk", normalized, np.asarray(EXPECTED_SEVERITY)
    )
    oracle = np.argmin(np.where(valid, costs, np.inf), axis=1)
    return costs, oracle.astype(np.int64)


def _route_order_key(namespace: str, route_identity_sha256: str) -> str:
    if namespace != "camp-v24-learning-curve-route-order-v1":
        raise ValueError("learning-curve order namespace drift")
    if not _is_sha256(route_identity_sha256):
        raise ValueError("route identity SHA256 is invalid")
    payload = f"{namespace}\n{route_identity_sha256}\n".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def build_route_prefix_plan(
    receipt_rows: Sequence[Mapping[str, Any]], *, namespace: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build outcome-blind nested route prefixes while retaining failures."""

    if len(receipt_rows) != EXPECTED_ROUTE_SEEDS:
        raise ValueError("route-seed receipt denominator mismatch")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for row in receipt_rows:
        route = row.get("route_identity_sha256")
        seed = row.get("seed")
        if (
            set(row) != RECEIPT_FIELDS
            or not _is_sha256(route)
            or type(seed) is not int
            or seed not in EXPECTED_SEEDS
            or row.get("phase") != ("pilot" if seed == 24001 else "remaining")
            or row.get("status") not in {"ok", "failed"}
            or not _is_sha256(row.get("sha256"))
            or not isinstance(row.get("relative_path"), str)
            or not row.get("relative_path")
            or not isinstance(row.get("record_key"), str)
            or not row.get("record_key")
            or not _is_sha256(row.get("logical_map_sha256"))
            or not _is_sha256(row.get("corridor_group_sha256"))
            or not isinstance(row.get("map_family_id"), str)
            or not row.get("map_family_id")
            or isinstance(row.get("snapshot_count"), bool)
            or not isinstance(row.get("snapshot_count"), int)
            or row.get("snapshot_count") < 0
        ):
            raise ValueError("invalid merged route-seed receipt row")
        key = (route, seed)
        if key in seen:
            raise ValueError("duplicate route-seed receipt")
        seen.add(key)
        if row["status"] == "failed":
            if not row.get("failure_stage") or not row.get("failure_reason"):
                raise ValueError("failed route-seed receipt lacks cause")
        elif row.get("failure_stage") is not None or row.get("failure_reason") is not None:
            raise ValueError("successful route-seed receipt carries failure")
        grouped[route].append(row)
    if len(grouped) != EXPECTED_ROUTES:
        raise ValueError("route denominator mismatch")

    summaries: list[dict[str, Any]] = []
    for route, rows in grouped.items():
        seeds = sorted(int(row["seed"]) for row in rows)
        metadata = {
            (
                str(row["map_family_id"]),
                str(row["logical_map_sha256"]),
                str(row["corridor_group_sha256"]),
            )
            for row in rows
        }
        if seeds != list(EXPECTED_SEEDS) or len(metadata) != 1:
            raise ValueError("route seed or metadata closure failed")
        map_family, logical_map, corridor = next(iter(metadata))
        summaries.append(
            {
                "route_identity_sha256": route,
                "route_order_key_sha256": _route_order_key(namespace, route),
                "map_family_id": map_family,
                "logical_map_sha256": logical_map,
                "corridor_group_sha256": corridor,
                "seeds": seeds,
                "retained_route_seed_count": len(rows),
                "complete_route_seed_count": sum(row["status"] == "ok" for row in rows),
                "failed_route_seed_count": sum(row["status"] == "failed" for row in rows),
                "snapshot_count": sum(int(row["snapshot_count"]) for row in rows),
            }
        )
    summaries.sort(
        key=lambda row: (
            row["route_order_key_sha256"], row["route_identity_sha256"]
        )
    )

    level_rows: list[dict[str, Any]] = []
    for index, row in enumerate(summaries, start=1):
        included = [
            percent
            for percent, count in zip(EXPECTED_LEVELS, EXPECTED_LEVEL_ROUTE_COUNTS)
            if index <= count
        ]
        row["route_order_rank"] = index
        row["included_learning_curve_percent"] = included
    for percent, count in zip(EXPECTED_LEVELS, EXPECTED_LEVEL_ROUTE_COUNTS):
        selected = summaries[:count]
        level_rows.append(
            {
                "percent": percent,
                "route_count": count,
                "retained_route_seed_count": sum(
                    row["retained_route_seed_count"] for row in selected
                ),
                "complete_route_seed_count": sum(
                    row["complete_route_seed_count"] for row in selected
                ),
                "failed_route_seed_count": sum(
                    row["failed_route_seed_count"] for row in selected
                ),
                "snapshot_count": sum(row["snapshot_count"] for row in selected),
                "route_membership_sha256": hashlib.sha256(
                    _canonical_json_bytes(
                        [row["route_identity_sha256"] for row in selected]
                    )
                ).hexdigest(),
                "primary_model": percent == 100,
                "diagnostic_only": percent != 100,
            }
        )
    if (
        level_rows[-1]["retained_route_seed_count"] != EXPECTED_ROUTE_SEEDS
        or level_rows[-1]["snapshot_count"] != EXPECTED_SNAPSHOTS
    ):
        raise ValueError("full route prefix does not cover the frozen train corpus")
    return summaries, level_rows


def _require_clean_repo(repo: Path, expected_head: str) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if head != expected_head or tracked:
        raise ValueError("CAMP HEAD or tracked state differs from preflight authority")


def _git_blob_bytes(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _require_fixed_dp(dp_repo: Path) -> None:
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)


def _lock_is_free(path: Path = REMAINING_TASK_LOCK) -> bool:
    if os.name != "posix":
        return True
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _require_clean_execution_receipt(root: Path) -> None:
    if (
        (root / "run.exit").read_text(encoding="ascii") != "0\n"
        or (root / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("source artifact execution receipt is not clean")


def _review_checks_passed(review: Mapping[str, Any]) -> bool:
    checks = review.get("checks")
    count = review.get("check_count")
    return (
        isinstance(checks, list)
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count > 0
        and count == len(checks)
        and review.get("failed_count") == 0
        and review.get("failed_checks") == []
        and all(
            isinstance(check, Mapping) and check.get("passed") is True
            for check in checks
        )
    )


def _validate_authority_payloads(
    roots: Mapping[str, Path], digests: Mapping[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = _read_json(roots["merged_train_corpus"] / "merged_summary.json")
    merged_review = _read_json(
        roots["merged_train_corpus_review"] / "review.json"
    )
    freeze = _read_json(roots["atom_freeze"] / "atom_freeze.json")
    freeze_review = _read_json(roots["atom_freeze_review"] / "review.json")
    if (
        merged.get("schema") != "camp_dp_v24_native_corpus_merged_train_index_v1"
        or merged.get("status") != "passed"
        or merged.get("split") != "train"
        or merged.get("route_count") != EXPECTED_ROUTES
        or merged.get("seeds") != list(EXPECTED_SEEDS)
        or merged.get("retained_route_seed_runs") != EXPECTED_ROUTE_SEEDS
        or merged.get("pending_route_seed_runs") != 0
        or merged.get("all_routes_retained_in_denominator") is not True
        or merged.get("snapshot_count") != EXPECTED_SNAPSHOTS
        or merged.get("snapshot_payloads_copied") is not False
        or merged.get("snapshot_payloads_modified") is not False
        or merged.get("route_or_seed_removed_replaced_or_reordered") is not False
        or merged.get("assembly_only") is not True
        or merged.get("model_loaded") is not False
        or merged.get("simulator_executed") is not False
        or merged.get("candidate_generation_started") is not False
        or merged.get("training_executed") is not False
        or merged.get("tuning_executed") is not False
        or merged.get("outcome_fields_consumed") != []
        or merged.get("calibration_accessed") is not False
        or merged.get("holdout_opened") is not False
        or merged.get("claim_authorized") is not False
    ):
        raise ValueError("merged train corpus authority is invalid")
    if (
        merged_review.get("schema")
        != "camp_dp_v24_native_corpus_merged_independent_review_v1"
        or merged_review.get("status") != "passed"
        or merged_review.get("source_assembly_root_sha256")
        != digests["merged_train_corpus"]
        or not _review_checks_passed(merged_review)
        or merged_review.get("review_only") is not True
        or merged_review.get("model_loaded") is not False
        or merged_review.get("candidate_generation_started") is not False
        or merged_review.get("training_executed") is not False
        or merged_review.get("tuning_executed") is not False
        or merged_review.get("outcome_accessed") is not False
        or merged_review.get("holdout_opened") is not False
        or merged_review.get("claim_authorized") is not False
    ):
        raise ValueError("merged train corpus review is invalid")
    scales = freeze.get("atom_scales")
    active = freeze.get("active_atom_mask")
    corpus_receipt = freeze.get("corpus_receipt")
    if (
        freeze.get("schema") != "camp_dp_v24_train_atom_availability_freeze_v1"
        or freeze.get("status") != "passed"
        or freeze.get("split") != "train"
        or freeze.get("source_merged_root_sha256")
        != digests["merged_train_corpus"]
        or freeze.get("source_merged_review_root_sha256")
        != digests["merged_train_corpus_review"]
        or freeze.get("fixed_dp_head") != FIXED_DP_HEAD
        or freeze.get("atom_names") != list(DP_CAMP_ATOM_NAMES_V10)
        or freeze.get("atom_contract_projection_sha256")
        != EXPECTED_ATOM_CONTRACT_SHA256
        or not isinstance(scales, list)
        or len(scales) != 14
        or not np.isfinite(np.asarray(scales, dtype=np.float64)).all()
        or np.any(np.asarray(scales, dtype=np.float64) <= 0.0)
        or active != [True] * 14
        or freeze.get("excluded_atom_names") != []
        or not isinstance(corpus_receipt, Mapping)
        or corpus_receipt.get("snapshot_count") != EXPECTED_SNAPSHOTS
        or corpus_receipt.get("candidate_count") != EXPECTED_SNAPSHOTS * 8
        or corpus_receipt.get("source_valid_candidate_count")
        != EXPECTED_SNAPSHOTS * 8
        or corpus_receipt.get("source_invalid_candidate_count") != 0
        or corpus_receipt.get("outcome_field_count") != 0
        or freeze.get("score_contract") != "score_k(w)=a_k^T w"
        or freeze.get("weight_domain")
        != "nonnegative_simplex_over_active_atoms_only"
        or freeze.get("snapshot_payloads_modified") is not False
        or freeze.get("model_loaded") is not False
        or freeze.get("simulator_executed") is not False
        or freeze.get("candidate_generation_started") is not False
        or freeze.get("training_executed") is not False
        or freeze.get("tuning_executed") is not False
        or freeze.get("outcome_fields_consumed") != []
        or freeze.get("calibration_accessed") is not False
        or freeze.get("holdout_opened") is not False
        or freeze.get("claim_authorized") is not False
        or freeze.get("training_plan_authorized") is not False
        or freeze.get("training_execution_authorized") is not False
    ):
        raise ValueError("atom freeze authority is invalid")
    decision = freeze_review.get("decision")
    if (
        freeze_review.get("schema")
        != "camp_dp_v24_train_atom_availability_freeze_independent_review_v1"
        or freeze_review.get("status") != "passed"
        or freeze_review.get("source_freeze_root_sha256")
        != digests["atom_freeze"]
        or freeze_review.get("source_merged_root_sha256")
        != digests["merged_train_corpus"]
        or freeze_review.get("source_merged_review_root_sha256")
        != digests["merged_train_corpus_review"]
        or freeze_review.get("fixed_dp_head") != FIXED_DP_HEAD
        or not _review_checks_passed(freeze_review)
        or not isinstance(decision, Mapping)
        or decision.get("training_plan_tdd_static_preflight_authorized") is not True
        or decision.get("training_execution_authorized") is not False
        or decision.get("outcome_access_authorized") is not False
        or decision.get("calibration_access_authorized") is not False
        or decision.get("holdout_access_authorized") is not False
        or decision.get("claim_authorized") is not False
        or freeze_review.get("review_only") is not True
        or freeze_review.get("model_loaded") is not False
        or freeze_review.get("simulator_executed") is not False
        or freeze_review.get("candidate_generation_started") is not False
        or freeze_review.get("training_executed") is not False
        or freeze_review.get("tuning_executed") is not False
        or freeze_review.get("outcome_accessed") is not False
        or freeze_review.get("holdout_opened") is not False
        or freeze_review.get("claim_authorized") is not False
        or freeze_review.get("next_work_target")
        != "v24_convex_selector_training_plan_tdd_static_preflight_only"
    ):
        raise ValueError("atom freeze review does not authorize static preflight")
    return merged, freeze


def run_static_preflight(
    *,
    repo: Path,
    dp_repo: Path,
    config_path: Path,
    expected_camp_head: str,
    output_dir: Path,
    git_checker: Callable[[Path, str], None] = _require_clean_repo,
    dp_checker: Callable[[Path], None] = _require_fixed_dp,
    lock_checker: Callable[[], bool] = _lock_is_free,
    free_bytes: Callable[[], int] | None = None,
    blob_bytes_reader: Callable[[Path, str, str], bytes] = _git_blob_bytes,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    available = (
        int(free_bytes())
        if free_bytes is not None
        else int(shutil.disk_usage(output.parent).free)
    )
    if available <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")
    git_checker(Path(repo), expected_camp_head)
    dp_checker(Path(dp_repo))
    if not lock_checker():
        raise RuntimeError("v24 global corpus lock is held")

    config_bytes = Path(config_path).read_bytes()
    expected_config_path = (Path(repo) / CONFIG_RELATIVE).resolve()
    if Path(config_path).resolve() != expected_config_path:
        raise ValueError("training config is not the tracked v24 config path")
    config_blob = blob_bytes_reader(
        Path(repo), expected_camp_head, CONFIG_RELATIVE.as_posix()
    )
    if config_bytes != config_blob:
        raise ValueError("live v24 training config differs from frozen CAMP HEAD")
    config = json.loads(config_bytes)
    validated = validate_plan_config(config)
    authority = validated["source_authority"]
    roots = {name: Path(authority[name]["artifact"]) for name in SOURCE_NAMES}
    digests = {
        name: authority[name]["artifact_root_sha256"] for name in SOURCE_NAMES
    }
    verified_file_counts: dict[str, int] = {}
    for name in SOURCE_NAMES:
        verified_file_counts[name] = len(
            verify_complete_seal(roots[name], digests[name])
        )
        _require_clean_execution_receipt(roots[name])
    merged, freeze = _validate_authority_payloads(roots, digests)
    receipt_rows = _read_jsonl(roots["merged_train_corpus"] / "receipt_index.jsonl")
    routes, levels = build_route_prefix_plan(
        receipt_rows,
        namespace=validated["learning_curve_contract"][
            "ordering_domain_separator"
        ],
    )

    import cvxpy as cp
    from camp_core.outer_master import robust_margin_master

    installed = sorted(cp.installed_solvers())
    if "CLARABEL" not in installed:
        raise RuntimeError("CLARABEL is not available")
    master_path = Path(robust_margin_master.__file__).resolve()
    if not master_path.is_relative_to(Path(repo).resolve()):
        raise ValueError("convex master was imported outside the CAMP repo")
    master_relative = master_path.relative_to(Path(repo).resolve()).as_posix()
    master_blob = subprocess.run(
        ["git", "rev-parse", f"{expected_camp_head}:{master_relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not master_blob or _file_sha256(master_path) != hashlib.sha256(
        blob_bytes_reader(Path(repo), expected_camp_head, master_relative)
    ).hexdigest():
        raise ValueError("convex master live source differs from frozen CAMP HEAD")
    if len(master_blob) != 40 or set(master_blob) - _SHA256_HEX:
        raise ValueError("convex master git blob identity is invalid")

    route_bytes = b"".join(_canonical_json_bytes(row) for row in routes)
    if (
        levels[-1]["complete_route_seed_count"]
        != merged["complete_route_seed_runs"]
        or levels[-1]["failed_route_seed_count"]
        != merged["failed_route_seed_runs"]
    ):
        raise ValueError("learning-curve receipt status accounting drift")
    map_families = sorted({row["map_family_id"] for row in routes})
    logical_maps = sorted({row["logical_map_sha256"] for row in routes})
    corridors = sorted({row["corridor_group_sha256"] for row in routes})
    result = {
        "schema": "camp_dp_v24_convex_training_static_preflight_v1",
        "status": "passed",
        "camp_head": expected_camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "source_authority": authority,
        "verified_file_counts": verified_file_counts,
        "corpus_receipt": {
            "route_count": EXPECTED_ROUTES,
            "train_seeds": list(EXPECTED_SEEDS),
            "retained_route_seed_count": EXPECTED_ROUTE_SEEDS,
            "complete_route_seed_count": merged["complete_route_seed_runs"],
            "failed_route_seed_count": merged["failed_route_seed_runs"],
            "snapshot_count": EXPECTED_SNAPSHOTS,
            "candidate_count": EXPECTED_SNAPSHOTS * 8,
            "all_k_high_risk_snapshot_count": merged[
                "all_k_high_risk_snapshot_count"
            ],
            "map_family_count": len(map_families),
            "logical_map_count": len(logical_maps),
            "corridor_group_count": len(corridors),
            "failure_reason_counts": merged["failure_reason_counts"],
        },
        "atom_freeze": {
            "atom_names": freeze["atom_names"],
            "atom_scales": freeze["atom_scales"],
            "active_atom_mask": freeze["active_atom_mask"],
            "excluded_atom_names": freeze["excluded_atom_names"],
            "scale_rule": freeze["scale_rule"],
            "variation_rule": freeze["variation_rule"],
            "scale_or_mask_recomputed": False,
        },
        "label_contract": validated["label_contract"],
        "learning_curve_contract": validated["learning_curve_contract"],
        "learning_curve_levels": levels,
        "route_plan_sha256": hashlib.sha256(route_bytes).hexdigest(),
        "route_plan_row_count": len(routes),
        "convex_master_contract": validated["convex_master_contract"],
        "solver_preflight": {
            "cvxpy_version": cp.__version__,
            "installed_solvers": installed,
            "required_solver": "CLARABEL",
            "required_solver_available": True,
            "master_source_relative_path": master_relative,
            "master_source_git_blob": master_blob,
            "master_source_sha256": _file_sha256(master_path),
            "corpus_solver_called": False,
            "synthetic_solver_called": False,
            "ram_or_wall_clock_benchmark_executed": False,
            "performance_does_not_authorize_protocol_changes": True,
        },
        "rounding_rule": "floor(percent*375/100+0.5)",
        "same_route_all_seeds_and_failures_together": True,
        "failed_routes_retained_in_denominator": True,
        "full_100_percent_is_only_primary_model": True,
        "learning_curve_is_train_support_diagnostic_not_generalization": True,
        "snapshot_payloads_modified": False,
        "labels_materialized": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "free_disk_gib": available / (1024**3),
        "minimum_free_disk_gib": 10,
        "decision": {
            "action": "materialize_v24_train_only_causal_labels_and_review",
            "label_materialization_tdd_execution_authorized": True,
            "label_independent_review_authorized": True,
            "training_execution_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": (
            "v24_train_only_causal_label_materialization_tdd_execution_review_only"
        ),
    }
    output.mkdir(parents=True)
    (output / "learning_curve_routes.jsonl").write_bytes(route_bytes)
    (output / "training_plan_preflight.json").write_bytes(
        _canonical_json_bytes(result)
    )
    return result


def seal_artifact(root: Path) -> str:
    source = Path(root)
    if source.is_symlink():
        raise ValueError("artifact root symlink is forbidden")
    manifest = source / "SHA256SUMS"
    root_receipt = source / "ROOT_SHA256SUMS"
    files = []
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("artifact symlink is forbidden")
        if not path.is_file() or path in {manifest, root_receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested reserved manifest name is forbidden")
        files.append(path)
    files.sort()
    manifest.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(manifest)
    root_receipt.write_text(
        f"{digest}  SHA256SUMS\n", encoding="ascii"
    )
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    result = run_static_preflight(
        repo=args.repo,
        dp_repo=args.dp_repo,
        config_path=args.config,
        expected_camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(command + "\n", encoding="utf-8")
    (args.output_dir / "training_plan_preflight.md").write_text(
        "# V24 Convex Training Static Preflight\n\n"
        f"- status: `{result['status']}`\n"
        f"- routes / route-seeds / snapshots: `{EXPECTED_ROUTES} / "
        f"{EXPECTED_ROUTE_SEEDS} / {EXPECTED_SNAPSHOTS}`\n"
        "- learning-curve routes: `94 / 188 / 281 / 375`\n"
        "- labels / training / calibration / holdout: `not executed`\n"
        f"- next: `{result['next_work_target']}`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(
        {
            "status": result["status"],
            "route_plan_sha256": result["route_plan_sha256"],
            "learning_curve_levels": result["learning_curve_levels"],
            "training_executed": False,
            "next_work_target": result["next_work_target"],
        },
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = seal_artifact(args.output_dir)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
