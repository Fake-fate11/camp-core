#!/usr/bin/env python3
"""Independently review v24 train-only causal label materialization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.review_diffusion_planner_v24_atom_availability import (  # noqa: E402
    _snapshot_arrays,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PREFLIGHT_SOURCE_HEAD = "bfc0a52307bf7d9184a5f4596b951058c02ba67c"
PREFLIGHT_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_training_static_preflight_bfc0a523_20260716T195856CST"
)
PREFLIGHT_ROOT_SHA256 = (
    "43f26263ff24cad5966cb3a740af6d3307490ab1bd3e07d03284589bee0d28f5"
)
MERGED_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_native_corpus_merged_train_assembly_5b725629_20260716T154602CST"
)
MERGED_ROOT_SHA256 = (
    "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc"
)
MERGED_REVIEW_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_native_corpus_merged_train_assembly_independent_review_"
    "5b725629_20260716T154723CST"
)
MERGED_REVIEW_ROOT_SHA256 = (
    "925db2aa58f136c20b3e9054d87dbd8d73d4162d18d079b10abbcacc63f09490"
)
ATOM_FREEZE_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_train_atom_availability_freeze_dc6f3715_20260716T190035CST"
)
ATOM_FREEZE_ROOT_SHA256 = (
    "ced620a4a5852e9e4196a2d272ef9b0ac1963512ecd62c2bf3612a3ed252438b"
)
ATOM_FREEZE_REVIEW_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_train_atom_availability_freeze_independent_review_"
    "dc6f3715_20260716T190514CST"
)
ATOM_FREEZE_REVIEW_ROOT_SHA256 = (
    "a88e6d43041e4f8005a7df5cccd9dd64510758a9c2a4af1de15e339e250e80b8"
)
EXPECTED_SNAPSHOTS = 67796
EXPECTED_ROUTES = 375
EXPECTED_ROUTE_SEEDS = 1875
EXPECTED_SEEDS = (24001, 24002, 24003, 24004, 24005)
EXPECTED_SEVERITY = np.asarray(
    [0.0, 0.0, 0.25, 0.25, 10.0, 0.0, 0.0, 20.0, 10.0, 1.0, 15.0, 1.0, 15.0, 0.25],
    dtype=np.float64,
)
MINIMUM_FREE_BYTES = 10 * 1024**3
LABEL_FILES = {
    "snapshot_sha256.txt",
    "snapshot_provenance.jsonl",
    "candidate_cost.f64le",
    "oracle_index.u8",
    "source_valid_mask.u8",
    "physical_feasible_mask.u8",
    "all_k_high_risk.u8",
}
_SHA256_HEX = frozenset("0123456789abcdef")
PRODUCER_PROVENANCE_FILES = (
    "scripts/integrations/materialize_diffusion_planner_v24_training_labels.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/freeze_diffusion_planner_v24_atom_availability.py",
)
PREFLIGHT_STABLE_PROVENANCE_FILES = PRODUCER_PROVENANCE_FILES[1:]
REVIEW_PROVENANCE_FILES = (
    "scripts/integrations/review_diffusion_planner_v24_training_labels.py",
    "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_HEX


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_bytes(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _tracked_source_provenance(
    *,
    repo: Path,
    current_head: str,
    relative_paths: Sequence[str],
    stable_at_preflight: Sequence[str] = (),
) -> dict[str, dict[str, Any]]:
    stable_paths = frozenset(stable_at_preflight)
    receipts: dict[str, dict[str, Any]] = {}
    for relative in relative_paths:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        live = (Path(repo) / relative).read_bytes()
        current = _git_blob_bytes(Path(repo), current_head, relative)
        blob = subprocess.run(
            ["git", "rev-parse", f"{current_head}:{relative}"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if live != current or len(blob) != 40 or set(blob) - _SHA256_HEX:
            raise ValueError(f"review source is not tracked by current HEAD: {relative}")
        stable = relative in stable_paths
        if stable and live != _git_blob_bytes(
            Path(repo), PREFLIGHT_SOURCE_HEAD, relative
        ):
            raise ValueError(f"reviewed validator changed after preflight: {relative}")
        receipts[relative] = {
            "git_blob": blob,
            "sha256": hashlib.sha256(live).hexdigest(),
            "matches_current_head": True,
            "matches_preflight_head": stable,
        }
    return receipts


def _manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(None, 1)
        normalized = relative.strip().removeprefix("./")
        item = PurePosixPath(normalized)
        if (
            not _is_sha256(digest)
            or item.is_absolute()
            or ".." in item.parts
            or normalized in entries
            or item.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ):
            raise ValueError("independent seal manifest is unsafe")
        entries[normalized] = digest
    if not entries:
        raise ValueError("independent seal manifest is empty")
    return entries


def verify_complete_seal(root: Path, expected: str) -> dict[str, str]:
    supplied = Path(root)
    if supplied.is_symlink():
        raise ValueError("artifact root symlink is forbidden")
    source = supplied.resolve()
    sums = source / "SHA256SUMS"
    receipt = source / "ROOT_SHA256SUMS"
    if (
        not source.is_dir()
        or not _is_sha256(expected)
        or not sums.is_file()
        or not receipt.is_file()
        or _file_sha256(sums) != expected
        or receipt.read_text(encoding="ascii") != f"{expected}  SHA256SUMS\n"
    ):
        raise ValueError("independent seal root receipt mismatch")
    entries = _manifest(sums)
    actual: set[str] = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("artifact symlink is forbidden")
        if not path.is_file() or path in {sums, receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested reserved manifest is forbidden")
        actual.add(path.relative_to(source).as_posix())
    if actual != set(entries):
        raise ValueError("independent seal inventory mismatch")
    for relative, digest in entries.items():
        if _file_sha256(source / relative) != digest:
            raise ValueError("independent sealed file hash mismatch")
    return entries


def _clean_execution(root: Path) -> bool:
    return (
        (Path(root) / "run.exit").read_text(encoding="ascii") == "0\n"
        and (Path(root) / "stderr.txt").read_text(encoding="utf-8") == ""
    )


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_bytes().splitlines():
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("review JSONL row is not an object")
        rows.append(row)
    return rows


def _check(checks: list[dict[str, Any]], name: str, passed: bool) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def _review_checks_passed(review: Mapping[str, Any]) -> bool:
    checks = review.get("checks")
    count = review.get("check_count")
    return (
        isinstance(checks, list)
        and type(count) is int
        and count > 0
        and count == len(checks)
        and review.get("failed_count") == 0
        and review.get("failed_checks") == []
        and all(
            isinstance(check, Mapping) and check.get("passed") is True
            for check in checks
        )
    )


def _require_clean_repo(repo: Path, expected_head: str) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if head != expected_head or tracked:
        raise ValueError("review CAMP/DP head or tracked state drift")


def review_labels(
    *,
    label_root: Path,
    expected_label_root_sha256: str,
    repo: Path,
    dp_repo: Path,
    expected_camp_head: str,
    output_dir: Path,
    free_bytes: int | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    available = (
        int(free_bytes)
        if free_bytes is not None
        else int(shutil.disk_usage(output.parent).free)
    )
    if available <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")
    _require_clean_repo(Path(repo), expected_camp_head)
    _require_clean_repo(Path(dp_repo), FIXED_DP_HEAD)
    checks: list[dict[str, Any]] = []
    inventories: dict[str, dict[str, str]] = {}
    recomputed: dict[str, Any] = {}
    review_source_provenance: dict[str, dict[str, Any]] = {}
    failure: dict[str, str] | None = None
    started = time.perf_counter()
    try:
        producer_source_provenance = _tracked_source_provenance(
            repo=Path(repo),
            current_head=expected_camp_head,
            relative_paths=PRODUCER_PROVENANCE_FILES,
            stable_at_preflight=PREFLIGHT_STABLE_PROVENANCE_FILES,
        )
        review_source_provenance = _tracked_source_provenance(
            repo=Path(repo),
            current_head=expected_camp_head,
            relative_paths=REVIEW_PROVENANCE_FILES,
        )
        if (
            not str(Path(label_root)).startswith(
                "/root/autodl-tmp/camp_dp_v24_train_causal_labels_"
            )
            or not _is_sha256(expected_label_root_sha256)
        ):
            raise ValueError("label artifact path or root is invalid")
        inventories["labels"] = verify_complete_seal(
            label_root, expected_label_root_sha256
        )
        inventories["preflight"] = verify_complete_seal(
            PREFLIGHT_ARTIFACT, PREFLIGHT_ROOT_SHA256
        )
        inventories["merged"] = verify_complete_seal(
            MERGED_ARTIFACT, MERGED_ROOT_SHA256
        )
        inventories["merged_review"] = verify_complete_seal(
            MERGED_REVIEW_ARTIFACT, MERGED_REVIEW_ROOT_SHA256
        )
        inventories["atom_freeze"] = verify_complete_seal(
            ATOM_FREEZE_ARTIFACT, ATOM_FREEZE_ROOT_SHA256
        )
        inventories["atom_freeze_review"] = verify_complete_seal(
            ATOM_FREEZE_REVIEW_ARTIFACT, ATOM_FREEZE_REVIEW_ROOT_SHA256
        )
        _check(
            checks,
            "clean_execution_receipts",
            all(
                _clean_execution(root)
                for root in (
                    label_root,
                    PREFLIGHT_ARTIFACT,
                    MERGED_ARTIFACT,
                    MERGED_REVIEW_ARTIFACT,
                    ATOM_FREEZE_ARTIFACT,
                    ATOM_FREEZE_REVIEW_ARTIFACT,
                )
            ),
        )
        manifest = _read_json(Path(label_root) / "label_manifest.json")
        plan = _read_json(PREFLIGHT_ARTIFACT / "training_plan_preflight.json")
        freeze = _read_json(ATOM_FREEZE_ARTIFACT / "atom_freeze.json")
        merged = _read_json(MERGED_ARTIFACT / "merged_summary.json")
        merged_review = _read_json(MERGED_REVIEW_ARTIFACT / "review.json")
        freeze_review = _read_json(ATOM_FREEZE_REVIEW_ARTIFACT / "review.json")
        source_specs = merged.get("source_artifacts")
        if not isinstance(source_specs, Mapping):
            raise ValueError("merged source artifact authority is missing")
        direct_source_roots: dict[str, Path] = {}
        for phase in ("pilot", "pilot_review", "remaining", "remaining_review"):
            spec = source_specs.get(phase)
            if not isinstance(spec, Mapping):
                raise ValueError(f"merged source artifact is missing: {phase}")
            raw_path = spec.get("path")
            root_sha = spec.get("root_sha256")
            pure = PurePosixPath(raw_path) if isinstance(raw_path, str) else None
            if (
                pure is None
                or not pure.is_absolute()
                or pure.parts[:3] != ("/", "root", "autodl-tmp")
                or ".." in pure.parts
                or not _is_sha256(root_sha)
            ):
                raise ValueError(f"merged source artifact authority is invalid: {phase}")
            direct_source_roots[phase] = Path(raw_path)
            inventories[f"direct_source_{phase}"] = verify_complete_seal(
                Path(raw_path), root_sha
            )
            if not _clean_execution(Path(raw_path)):
                raise ValueError(f"merged source execution receipt is not clean: {phase}")
        label_contract = plan.get("label_contract")
        severity = np.asarray(label_contract.get("atom_severity_weights"), dtype=np.float64)
        scales = np.asarray(freeze.get("atom_scales"), dtype=np.float64)
        expected_columns = {
            "candidate_cost": {
                "file": "candidate_cost.f64le",
                "dtype": "<f8",
                "shape": [EXPECTED_SNAPSHOTS, 8],
            },
            "oracle_index": {
                "file": "oracle_index.u8",
                "dtype": "u1",
                "shape": [EXPECTED_SNAPSHOTS],
            },
            "source_valid_mask": {
                "file": "source_valid_mask.u8",
                "dtype": "u1_bool",
                "shape": [EXPECTED_SNAPSHOTS, 8],
            },
            "physical_feasible_mask": {
                "file": "physical_feasible_mask.u8",
                "dtype": "u1_bool",
                "shape": [EXPECTED_SNAPSHOTS, 8],
            },
            "all_k_high_risk": {
                "file": "all_k_high_risk.u8",
                "dtype": "u1_bool",
                "shape": [EXPECTED_SNAPSHOTS],
            },
        }
        _check(
            checks,
            "manifest_schema_and_columns",
            manifest.get("schema") == "camp_dp_v24_train_causal_label_manifest_v1"
            and manifest.get("status") == "passed"
            and manifest.get("label_schema")
            == "camp_dp_v24_train_causal_label_columns_v1"
            and manifest.get("split") == "train"
            and manifest.get("columns") == expected_columns,
        )
        _check(
            checks,
            "upstream_review_authority",
            merged_review.get("schema")
            == "camp_dp_v24_native_corpus_merged_independent_review_v1"
            and merged_review.get("status") == "passed"
            and merged_review.get("source_assembly_root_sha256")
            == MERGED_ROOT_SHA256
            and _review_checks_passed(merged_review)
            and merged_review.get("review_only") is True
            and merged_review.get("training_executed") is False
            and merged_review.get("outcome_accessed") is False
            and merged_review.get("holdout_opened") is False
            and merged_review.get("claim_authorized") is False
            and freeze_review.get("schema")
            == "camp_dp_v24_train_atom_availability_freeze_independent_review_v1"
            and freeze_review.get("status") == "passed"
            and freeze_review.get("source_freeze_root_sha256")
            == ATOM_FREEZE_ROOT_SHA256
            and freeze_review.get("source_merged_root_sha256")
            == MERGED_ROOT_SHA256
            and freeze_review.get("source_merged_review_root_sha256")
            == MERGED_REVIEW_ROOT_SHA256
            and _review_checks_passed(freeze_review)
            and freeze_review.get("review_only") is True
            and freeze_review.get("training_executed") is False
            and freeze_review.get("outcome_accessed") is False
            and freeze_review.get("holdout_opened") is False
            and freeze_review.get("claim_authorized") is False,
        )
        _check(
            checks,
            "frozen_authority_chain",
            manifest.get("source_preflight_root_sha256") == PREFLIGHT_ROOT_SHA256
            and manifest.get("source_preflight_artifact") == str(PREFLIGHT_ARTIFACT)
            and manifest.get("source_merged_root_sha256") == MERGED_ROOT_SHA256
            and manifest.get("source_merged_review_root_sha256")
            == MERGED_REVIEW_ROOT_SHA256
            and manifest.get("source_atom_freeze_root_sha256")
            == ATOM_FREEZE_ROOT_SHA256
            and manifest.get("source_atom_freeze_review_root_sha256")
            == ATOM_FREEZE_REVIEW_ROOT_SHA256
            and manifest.get("route_plan_sha256") == plan.get("route_plan_sha256")
            and manifest.get("camp_head") == expected_camp_head
            and manifest.get("fixed_dp_head") == FIXED_DP_HEAD,
        )
        _check(
            checks,
            "tracked_source_provenance",
            manifest.get("source_provenance") == producer_source_provenance
            and set(review_source_provenance) == set(REVIEW_PROVENANCE_FILES),
        )
        _check(
            checks,
            "label_contract",
            isinstance(label_contract, Mapping)
            and label_contract.get("schema_version")
            == "camp_dp_v24_causal_soft_risk_surrogate_v1"
            and label_contract.get("physical_risk_penalty") == 100.0
            and label_contract.get("normalized_atom_clip") == 10.0
            and np.array_equal(severity, EXPECTED_SEVERITY)
            and label_contract.get("oracle_eligibility") == "source_valid_mask_only"
            and label_contract.get("oracle_tie_break") == "lowest_candidate_index"
            and label_contract.get("actual_closed_loop_outcome") is False
            and manifest.get("label_contract") == label_contract
            and manifest.get("label_contract_sha256")
            == hashlib.sha256(_canonical(label_contract)).hexdigest(),
        )
        _check(
            checks,
            "floating_point_contract",
            manifest.get("floating_point_contract")
            == {
                "input_dtype": "float64",
                "normalized_dtype": "float64",
                "cost_dtype": "little_endian_float64",
                "accumulation": (
                    "physical_penalty_then_atoms_0_through_13_left_to_right"
                ),
                "fused_multiply_add": False,
                "review_match": "exact_binary_float64",
            },
        )
        _check(
            checks,
            "frozen_scales_and_mask",
            scales.shape == (14,)
            and np.isfinite(scales).all()
            and np.all(scales > 0.0)
            and manifest.get("atom_scales") == scales.tolist()
            and manifest.get("atom_scales_sha256")
            == hashlib.sha256(_canonical(scales.tolist())).hexdigest()
            and manifest.get("active_atom_mask") == [True] * 14
            and manifest.get("scale_or_mask_recomputed") is False,
        )

        atoms, valid, physical, source_inventories = _snapshot_arrays(
            merged_root=MERGED_ARTIFACT, summary=merged
        )
        inventories.update(
            {f"source_{name}": files for name, files in source_inventories.items()}
        )
        _check(
            checks,
            "source_snapshot_dimensions",
            atoms.shape == (EXPECTED_SNAPSHOTS, 8, 14)
            and valid.shape == (EXPECTED_SNAPSHOTS, 8)
            and physical.shape == (EXPECTED_SNAPSHOTS, 8),
        )
        normalized = np.clip(atoms / scales.reshape(1, 1, 14), 0.0, 10.0)
        independent_costs = 100.0 * (~physical).astype(np.float64)
        for atom_index in range(14):
            independent_costs = independent_costs + (
                normalized[:, :, atom_index] * EXPECTED_SEVERITY[atom_index]
            )
        independent_oracle = np.argmin(
            np.where(valid, independent_costs, np.inf), axis=1
        ).astype(np.uint8)
        independent_all_k = (valid.all(axis=1) & ~physical.any(axis=1)).astype(
            np.uint8
        )

        stored_costs = np.fromfile(
            Path(label_root) / "candidate_cost.f64le", dtype="<f8"
        ).reshape(EXPECTED_SNAPSHOTS, 8)
        stored_oracle = np.fromfile(
            Path(label_root) / "oracle_index.u8", dtype=np.uint8
        )
        stored_valid = np.fromfile(
            Path(label_root) / "source_valid_mask.u8", dtype=np.uint8
        ).reshape(EXPECTED_SNAPSHOTS, 8)
        stored_physical = np.fromfile(
            Path(label_root) / "physical_feasible_mask.u8", dtype=np.uint8
        ).reshape(EXPECTED_SNAPSHOTS, 8)
        stored_all_k = np.fromfile(
            Path(label_root) / "all_k_high_risk.u8", dtype=np.uint8
        )
        _check(
            checks,
            "independent_cost_recompute",
            np.array_equal(stored_costs, independent_costs)
            and (Path(label_root) / "candidate_cost.f64le").read_bytes()
            == independent_costs.astype("<f8", copy=False).tobytes(order="C"),
        )
        _check(
            checks,
            "independent_oracle_and_masks",
            np.array_equal(stored_oracle, independent_oracle)
            and np.array_equal(stored_valid, valid.astype(np.uint8))
            and np.array_equal(stored_physical, physical.astype(np.uint8))
            and np.array_equal(stored_all_k, independent_all_k),
        )

        index_rows = _read_jsonl(MERGED_ARTIFACT / "snapshot_index.jsonl")
        expected_snapshot_text = (
            "\n".join(str(row["sha256"]) for row in index_rows) + "\n"
        ).encode("ascii")
        source_roots = {
            phase: direct_source_roots[phase] for phase in ("pilot", "remaining")
        }
        route_rows = _read_jsonl(PREFLIGHT_ARTIFACT / "learning_curve_routes.jsonl")
        route_set = {row["route_identity_sha256"] for row in route_rows}
        provenance_bytes = bytearray()
        seen_ticks: set[tuple[str, int, int]] = set()
        for row in index_rows:
            phase = row["phase"]
            relative = PurePosixPath(row["relative_path"])
            payload = _read_json(source_roots[phase] / Path(*relative.parts))
            sidecar = payload["sidecar"]
            route = sidecar["route_identity_sha256"]
            seed = sidecar["seed"]
            tick = sidecar["tick_index"]
            key = (route, seed, tick)
            if route not in route_set or key in seen_ticks:
                raise ValueError("independent provenance membership failed")
            seen_ticks.add(key)
            provenance_bytes.extend(
                _canonical(
                    {
                        "snapshot_sha256": row["sha256"],
                        "route_identity_sha256": route,
                        "seed": seed,
                        "phase": phase,
                        "source_relative_path": relative.as_posix(),
                        "tick_index": tick,
                    }
                )
            )
        _check(
            checks,
            "snapshot_and_provenance_alignment",
            (Path(label_root) / "snapshot_sha256.txt").read_bytes()
            == expected_snapshot_text
            and (Path(label_root) / "snapshot_provenance.jsonl").read_bytes()
            == bytes(provenance_bytes),
        )

        receipts = manifest.get("file_receipts")
        _check(
            checks,
            "label_file_receipts",
            isinstance(receipts, Mapping)
            and set(receipts) == LABEL_FILES
            and all(
                receipts[name].get("sha256") == _file_sha256(Path(label_root) / name)
                and receipts[name].get("bytes") == (Path(label_root) / name).stat().st_size
                for name in LABEL_FILES
            ),
        )
        histogram = np.bincount(stored_oracle, minlength=8).astype(int).tolist()
        recomputed = {
            "snapshot_count": int(stored_oracle.size),
            "candidate_count": int(stored_costs.size),
            "source_valid_candidate_count": int(valid.sum()),
            "source_invalid_candidate_count": int(valid.size - valid.sum()),
            "physical_feasible_candidate_count": int(physical.sum()),
            "all_k_high_risk_snapshot_count": int(independent_all_k.sum()),
            "oracle_histogram": histogram,
            "oracle_candidate0_count": histogram[0],
            "oracle_non_candidate0_count": EXPECTED_SNAPSHOTS - histogram[0],
            "candidate_cost_minimum": float(np.min(stored_costs)),
            "candidate_cost_maximum": float(np.max(stored_costs)),
            "candidate_cost_mean": float(np.mean(stored_costs)),
        }
        _check(
            checks,
            "manifest_recomputed_counts_and_metrics",
            all(manifest.get(name) == value for name, value in recomputed.items()),
        )
        _check(
            checks,
            "full_denominator",
            manifest.get("snapshot_count") == EXPECTED_SNAPSHOTS
            and manifest.get("candidate_count") == EXPECTED_SNAPSHOTS * 8
            and manifest.get("route_count") == EXPECTED_ROUTES
            and manifest.get("retained_route_seed_count") == EXPECTED_ROUTE_SEEDS
            and manifest.get("complete_route_seed_count") == 1054
            and manifest.get("failed_route_seed_count") == 821
            and manifest.get("failure_reason_counts")
            == plan["corpus_receipt"]["failure_reason_counts"]
            and manifest.get("learning_curve_levels")
            == plan["learning_curve_levels"]
            and manifest.get("train_seeds") == list(EXPECTED_SEEDS),
        )
        _check(
            checks,
            "closed_boundaries",
            manifest.get("snapshot_payloads_copied") is False
            and manifest.get("snapshot_payloads_modified") is False
            and manifest.get("candidate_tensors_modified") is False
            and manifest.get("identity_fields_stored_only_in_separate_provenance")
            is True
            and manifest.get("identity_fields_used_as_label_or_feature") is False
            and manifest.get("actual_closed_loop_outcomes_read") is False
            and manifest.get("future_outcome_fields_read") is False
            and manifest.get("model_loaded") is False
            and manifest.get("simulator_executed") is False
            and manifest.get("candidate_generation_started") is False
            and manifest.get("training_executed") is False
            and manifest.get("tuning_executed") is False
            and manifest.get("calibration_accessed") is False
            and manifest.get("holdout_opened") is False
            and manifest.get("claim_authorized") is False
            and manifest.get("training_execution_authorized") is False,
        )
        _check(
            checks,
            "next_gate",
            manifest.get("next_work_target")
            == "v24_train_only_causal_label_materialization_independent_review_only",
        )
    except Exception as exc:
        failure = {
            "type": type(exc).__name__,
            "message": str(exc).replace("\r", " ").replace("\n", " ")[:1000],
        }
        _check(checks, "review_input_valid", False)
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema": "camp_dp_v24_train_causal_label_independent_review_v1",
        "status": "passed" if passed else "failed",
        "source_label_artifact": str(label_root),
        "source_label_root_sha256": expected_label_root_sha256,
        "camp_head": expected_camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "review_source_provenance": review_source_provenance,
        "failure": failure,
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "verified_file_count": sum(len(files) for files in inventories.values()),
        "recomputed": recomputed,
        "review_wall_clock_s": time.perf_counter() - started,
        "decision": {
            "action": (
                "implement_and_static_preflight_v24_convex_training_executor"
                if passed
                else "label_failure_analysis_only"
            ),
            "training_executor_tdd_static_preflight_authorized": passed,
            "training_execution_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "review_only": True,
        "label_files_modified": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "free_disk_gib": available / (1024**3),
        "minimum_free_disk_gib": 10,
        "next_work_target": (
            "v24_convex_selector_training_executor_tdd_static_preflight_only"
            if passed
            else "v24_train_causal_label_failure_analysis_only"
        ),
    }


def seal_artifact(root: Path) -> str:
    source = Path(root)
    if source.is_symlink():
        raise ValueError("review artifact root symlink is forbidden")
    sums = source / "SHA256SUMS"
    receipt = source / "ROOT_SHA256SUMS"
    files = []
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("review artifact symlink is forbidden")
        if not path.is_file() or path in {sums, receipt}:
            continue
        if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            raise ValueError("nested review manifest is forbidden")
        files.append(path)
    files.sort()
    sums.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(sums)
    receipt.write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-root", type=Path, required=True)
    parser.add_argument("--expected-label-root-sha256", required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    command = " ".join(sys.argv)
    review = review_labels(
        label_root=args.label_root,
        expected_label_root_sha256=args.expected_label_root_sha256,
        repo=args.repo,
        dp_repo=args.dp_repo,
        expected_camp_head=args.camp_head,
        output_dir=args.output_dir,
    )
    args.output_dir.mkdir()
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(command + "\n", encoding="utf-8")
    (args.output_dir / "review.json").write_bytes(_canonical(review))
    (args.output_dir / "review.md").write_text(
        "# V24 Train-Only Causal Label Independent Review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed: `{review['check_count']} / {review['failed_count']}`\n"
        "- training / calibration / holdout: `not executed`\n"
        f"- next: `{review['next_work_target']}`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(
        {
            "status": review["status"],
            "check_count": review["check_count"],
            "failed_count": review["failed_count"],
            "training_executed": False,
            "next_work_target": review["next_work_target"],
        },
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    stderr = ""
    if review["status"] != "passed":
        stderr = json.dumps(
            review.get("failure"), sort_keys=True, allow_nan=False
        ) + "\n"
    (args.output_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    (args.output_dir / "run.exit").write_text(
        "0\n" if review["status"] == "passed" else "1\n", encoding="ascii"
    )
    root_sha256 = seal_artifact(args.output_dir)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    if os.name != "posix":
        raise SystemExit("v24 label review requires the isolated AutoDL host")
    raise SystemExit(main())
