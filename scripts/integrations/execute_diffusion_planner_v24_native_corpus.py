#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.materialize_diffusion_planner_v22_native_corpus import (
    CorpusSnapshotWriter,
)
from scripts.integrations.prepare_diffusion_planner_v24_native_corpus import (
    build_corpus_run_config,
)
from scripts.integrations.review_diffusion_planner_v24_native_corpus import (
    CORPUS_MANIFEST_SHA256,
    CORPUS_PLAN_SHA256,
    FIXED_DP_HEAD,
    TRAIN_SEEDS,
    _source_root_checks,
    file_sha256,
    validate_corpus_boundaries,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    build_native_arm_runner,
    validate_v24_corpus_run_config,
    verify_config_assets,
)


PILOT_SEED = 24001
PILOT_SEEDS = (PILOT_SEED,)
REMAINING_SEEDS = tuple(TRAIN_SEEDS[1:])
PILOT_PHASE = "capability_pilot_all_train_routes_first_seed"
REMAINING_PHASE = "main_completion_remaining_frozen_seeds"
MINIMUM_FREE_BYTES = 10 * 1024**3
REMAINING_TASK_LOCK = Path("/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock")


def verified_asset_receipts_complete(receipts: Mapping[str, str]) -> bool:
    return receipts.get("fixed_dp_head") == FIXED_DP_HEAD and len(receipts) >= 11


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            _json_safe(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(name): _json_safe(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_json_bytes(value))
    temporary.replace(path)


def _validated_routes(
    manifest: Mapping[str, Any], *, expected_route_count: int
) -> list[dict[str, Any]]:
    if manifest.get("schema") != "camp_dp_v24_native_corpus_manifest_v1":
        raise ValueError("v24 corpus manifest schema mismatch")
    if (
        manifest.get("split") != "train"
        or manifest.get("seeds") != list(TRAIN_SEEDS)
        or manifest.get("outcome_fields_consumed") != []
        or manifest.get("calibration_accessed") is not False
        or manifest.get("holdout_opened") is not False
    ):
        raise ValueError("v24 corpus execution boundary mismatch")
    routes = [dict(route) for route in manifest.get("routes", [])]
    if len(routes) != expected_route_count:
        raise ValueError("v24 corpus route denominator mismatch")
    identities = [str(route["identity_sha256"]) for route in routes]
    if len(set(identities)) != len(identities):
        raise ValueError("v24 corpus route identities are not unique")
    for route in routes:
        if route.get("seeds") != list(TRAIN_SEEDS):
            raise ValueError("v24 corpus route seed namespace mismatch")
    routes.sort(key=lambda route: str(route["record_key"]))
    return routes


def _phase_rows(
    manifest: Mapping[str, Any],
    seeds: Sequence[int],
    *,
    expected_route_count: int,
) -> list[tuple[dict[str, Any], int]]:
    selected_seeds = tuple(int(seed) for seed in seeds)
    if (
        not selected_seeds
        or len(set(selected_seeds)) != len(selected_seeds)
        or any(seed not in TRAIN_SEEDS for seed in selected_seeds)
    ):
        raise ValueError("v24 corpus selected seed namespace mismatch")
    routes = _validated_routes(manifest, expected_route_count=expected_route_count)
    return [(route, seed) for route in routes for seed in selected_seeds]


def pilot_rows(
    manifest: Mapping[str, Any], *, expected_route_count: int = 375
) -> list[tuple[dict[str, Any], int]]:
    return _phase_rows(manifest, PILOT_SEEDS, expected_route_count=expected_route_count)


def remaining_rows(
    manifest: Mapping[str, Any],
    pilot_review: Mapping[str, Any],
    *,
    expected_route_count: int = 375,
) -> list[tuple[dict[str, Any], int]]:
    routes = _validated_routes(manifest, expected_route_count=expected_route_count)
    if (
        pilot_review.get("schema")
        != "camp_dp_v24_native_corpus_pilot_independent_review_v1"
        or pilot_review.get("status") not in {"passed", "passed_with_warning"}
        or pilot_review.get("failed_count") != 0
    ):
        raise ValueError("v24 remaining review authorization is not passed")
    for field, label in (
        ("review_only", "review-only"),
        ("model_loaded", "model"),
        ("candidate_generation_started", "candidate"),
        ("training_executed", "training"),
        ("tuning_executed", "tuning"),
        ("outcome_accessed", "outcome"),
        ("calibration_accessed", "calibration"),
        ("holdout_opened", "holdout"),
        ("claim_authorized", "claim"),
    ):
        expected = field == "review_only"
        if pilot_review.get(field) is not expected:
            raise ValueError(f"v24 remaining review {label} boundary mismatch")
    decision = pilot_review.get("decision")
    if not isinstance(decision, Mapping) or decision.get("authorized") is not True:
        raise ValueError("v24 remaining review authorization missing")
    if decision.get("action") != "execute_frozen_remaining_train_seeds":
        raise ValueError("v24 remaining review authorization action mismatch")
    if decision.get("route_count") != len(routes):
        raise ValueError("v24 remaining route denominator mismatch")
    expected_route_order = [str(route["record_key"]) for route in routes]
    if decision.get("route_order") != expected_route_order:
        raise ValueError("v24 remaining route order mismatch")
    if decision.get("seeds") != list(REMAINING_SEEDS):
        raise ValueError("v24 remaining seed namespace mismatch")
    if decision.get("preserve_all_failures_and_denominator") is not True:
        raise ValueError("v24 remaining denominator preservation mismatch")
    if decision.get("route_removal_replacement_reordering_authorized") is not False:
        raise ValueError("v24 remaining route order mutation is authorized")
    for field, label in (
        ("tuning_authorized", "tuning"),
        ("outcome_access_authorized", "outcome"),
        ("calibration_access_authorized", "calibration"),
        ("holdout_access_authorized", "holdout"),
        ("claim_authorized", "claim"),
    ):
        if decision.get(field) is not False:
            raise ValueError(f"v24 remaining {label} boundary mismatch")
    return [(route, seed) for route in routes for seed in REMAINING_SEEDS]


class V24CorpusSnapshotWriter(CorpusSnapshotWriter):
    def __init__(
        self,
        *,
        route: Mapping[str, Any],
        output_dir: Path,
        seed: int,
        phase: str = PILOT_PHASE,
    ) -> None:
        self.record_key = str(route["record_key"])
        self.map_family_id = str(route["map_family_id"])
        self.corridor_group_sha256 = str(route["corridor_group_sha256"])
        if phase not in {PILOT_PHASE, REMAINING_PHASE}:
            raise ValueError("v24 corpus receipt phase mismatch")
        self.phase = phase
        super().__init__(
            output_dir=output_dir,
            split="train",
            logical_map_sha256=str(route["logical_map_sha256"]),
            route_identity_sha256=str(route["identity_sha256"]),
            group_sha256=self.corridor_group_sha256,
            seed=seed,
            source_stratum=route.get("source_stratum", {}),
        )

    def __call__(self, snapshot: Mapping[str, Any]) -> str:
        payload = json.loads(json.dumps(snapshot, allow_nan=False))
        sidecar = payload.setdefault("sidecar", {})
        sidecar.update(
            {
                "record_key": self.record_key,
                "map_family_id": self.map_family_id,
                "corridor_group_sha256": self.corridor_group_sha256,
            }
        )
        return super().__call__(payload)

    def write_v24_run_receipt(
        self,
        *,
        status: str,
        wall_clock_s: float,
        failure_stage: str | None = None,
        failure_reason: str | None = None,
    ) -> Path:
        if status not in {"ok", "failed"}:
            raise ValueError("v24 pilot receipt status mismatch")
        if status == "failed" and (not failure_stage or not failure_reason):
            raise ValueError("v24 failed pilot receipt requires cause")
        receipt = {
            "schema": (
                "camp_dp_v24_native_corpus_pilot_run_receipt_v1"
                if self.phase == PILOT_PHASE
                else "camp_dp_v24_native_corpus_remaining_run_receipt_v1"
            ),
            "status": status,
            "split": "train",
            "phase": self.phase,
            "record_key": self.record_key,
            "map_family_id": self.map_family_id,
            "logical_map_sha256": self.logical_map_sha256,
            "corridor_group_sha256": self.corridor_group_sha256,
            "route_identity_sha256": self.route_identity_sha256,
            "seed": self.seed,
            "snapshot_sha256": list(self.snapshot_sha256),
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "retained_in_denominator": True,
            "wall_clock_s": wall_clock_s,
        }
        path = (
            self.output_dir
            / "receipts"
            / "train"
            / self.route_identity_sha256
            / f"seed_{self.seed}.json"
        )
        _write_json_atomic(path, receipt)
        return path


def _aggregate_execution(output_dir: Path, planned: int) -> dict[str, Any]:
    receipts = (
        [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (output_dir / "receipts" / "train").rglob("seed_*.json")
        ]
        if (output_dir / "receipts" / "train").is_dir()
        else []
    )
    complete = sum(item.get("status") == "ok" for item in receipts)
    failed = sum(item.get("status") == "failed" for item in receipts)
    snapshots = list((output_dir / "snapshots").glob("*.json"))
    all_k_high_risk = 0
    strata: dict[str, int] = {}
    for path in snapshots:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sidecar = payload["sidecar"]
        all_k_high_risk += int(bool(sidecar.get("all_k_high_risk")))
        active = [
            str(name)
            for name, enabled in sidecar.get("source_stratum", {}).items()
            if enabled
        ] or ["normal"]
        for name in active:
            strata[name] = strata.get(name, 0) + 1
    return {
        "planned_route_seed_runs": planned,
        "complete_route_seed_runs": complete,
        "failed_route_seed_runs": failed,
        "retained_route_seed_runs": len(receipts),
        "pending_route_seed_runs": planned - len(receipts),
        "route_coverage": len(receipts) / planned if planned else 0.0,
        "snapshot_count": len(snapshots),
        "snapshot_count_by_source_stratum": dict(sorted(strata.items())),
        "all_k_high_risk_snapshot_count": all_k_high_risk,
    }


def _record_completed_row(
    aggregate: dict[str, Any], writer: V24CorpusSnapshotWriter, *, status: str
) -> None:
    aggregate[f"{'complete' if status == 'ok' else 'failed'}_route_seed_runs"] += 1
    aggregate["retained_route_seed_runs"] += 1
    aggregate["pending_route_seed_runs"] -= 1
    aggregate["route_coverage"] = (
        aggregate["retained_route_seed_runs"] / aggregate["planned_route_seed_runs"]
    )
    snapshot_count = len(writer.snapshot_sha256)
    aggregate["snapshot_count"] += snapshot_count
    aggregate["all_k_high_risk_snapshot_count"] += writer.all_k_high_risk_snapshot_count
    active_strata = [
        name for name, enabled in writer.source_stratum.items() if enabled
    ] or ["normal"]
    strata = aggregate["snapshot_count_by_source_stratum"]
    for name in active_strata:
        strata[name] = strata.get(name, 0) + snapshot_count
    aggregate["snapshot_count_by_source_stratum"] = dict(sorted(strata.items()))


def _validate_resume_receipt(
    receipt: Mapping[str, Any],
    *,
    route: Mapping[str, Any],
    seed: int,
    phase: str,
    output_dir: Path,
) -> None:
    expected_schema = (
        "camp_dp_v24_native_corpus_pilot_run_receipt_v1"
        if phase == PILOT_PHASE
        else "camp_dp_v24_native_corpus_remaining_run_receipt_v1"
    )
    expected = {
        "schema": expected_schema,
        "split": "train",
        "phase": phase,
        "record_key": str(route["record_key"]),
        "map_family_id": str(route["map_family_id"]),
        "logical_map_sha256": str(route["logical_map_sha256"]),
        "corridor_group_sha256": str(route["corridor_group_sha256"]),
        "route_identity_sha256": str(route["identity_sha256"]),
        "seed": seed,
        "retained_in_denominator": True,
    }
    if any(receipt.get(name) != value for name, value in expected.items()):
        raise ValueError("resume receipt boundary mismatch")
    status = receipt.get("status")
    if status not in {"ok", "failed"}:
        raise ValueError("resume receipt status mismatch")
    if status == "failed" and (
        not receipt.get("failure_stage") or not receipt.get("failure_reason")
    ):
        raise ValueError("resume failed receipt lacks cause")
    snapshots = receipt.get("snapshot_sha256")
    if not isinstance(snapshots, list) or len(set(snapshots)) != len(snapshots):
        raise ValueError("resume receipt snapshot inventory mismatch")
    for digest in snapshots:
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("resume receipt snapshot SHA256 mismatch")
        path = output_dir / "snapshots" / f"{digest}.json"
        if not path.is_file() or file_sha256(path) != digest:
            raise ValueError("resume receipt snapshot content mismatch")


def _validate_existing_receipt_inventory(
    output_dir: Path, rows: Sequence[tuple[Mapping[str, Any], int]]
) -> None:
    receipt_root = output_dir / "receipts" / "train"
    if not receipt_root.is_dir():
        return
    expected = {
        (receipt_root / str(route["identity_sha256"]) / f"seed_{seed}.json").resolve()
        for route, seed in rows
    }
    actual = {path.resolve() for path in receipt_root.rglob("*") if path.is_file()}
    if not actual.issubset(expected):
        raise ValueError("resume receipt inventory contains unplanned files")


def _validate_terminal_snapshot_inventory(output_dir: Path) -> None:
    referenced: set[str] = set()
    receipt_root = output_dir / "receipts" / "train"
    if receipt_root.is_dir():
        for path in receipt_root.rglob("seed_*.json"):
            receipt = json.loads(path.read_text(encoding="utf-8"))
            referenced.update(str(digest) for digest in receipt["snapshot_sha256"])
    snapshot_root = output_dir / "snapshots"
    actual_files = (
        {path.resolve() for path in snapshot_root.rglob("*") if path.is_file()}
        if snapshot_root.is_dir()
        else set()
    )
    expected_files = {
        (snapshot_root / f"{digest}.json").resolve() for digest in referenced
    }
    if actual_files != expected_files:
        raise ValueError("terminal snapshot inventory differs from receipts")
    if any(file_sha256(path) != path.stem for path in actual_files):
        raise ValueError("terminal snapshot content SHA256 mismatch")


def _execute_manifest_rows(
    rows: Sequence[tuple[Mapping[str, Any], int]],
    template: Mapping[str, Any],
    *,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
    phase: str,
    seeds: Sequence[int],
    summary_schema: str,
    progress_schema: str,
    summary_filename: str,
    free_bytes: Callable[[], int] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    rows = list(rows)
    output_dir = Path(output_dir)
    if output_dir.exists() and not resume:
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    free_bytes = free_bytes or (lambda: shutil.disk_usage(output_dir).free)
    execution_started = time.perf_counter()
    stopped_for_disk = False
    _validate_existing_receipt_inventory(output_dir, rows)
    aggregate = _aggregate_execution(output_dir, len(rows))
    for index, (route, seed) in enumerate(rows, start=1):
        receipt_path = (
            output_dir
            / "receipts"
            / "train"
            / str(route["identity_sha256"])
            / f"seed_{seed}.json"
        )
        if receipt_path.is_file():
            prior = json.loads(receipt_path.read_text(encoding="utf-8"))
            _validate_resume_receipt(
                prior,
                route=route,
                seed=seed,
                phase=phase,
                output_dir=output_dir,
            )
            continue
        if free_bytes() <= MINIMUM_FREE_BYTES:
            stopped_for_disk = True
            break
        writer = V24CorpusSnapshotWriter(
            route=route, output_dir=output_dir, seed=seed, phase=phase
        )
        native_output = (
            output_dir / "native_runs" / str(route["identity_sha256"]) / f"seed_{seed}"
        )
        started = time.perf_counter()
        receipt_status = "ok"
        try:
            run_config = build_corpus_run_config(
                template,
                route,
                route["route_asset"],
                seed,
            )
            validate_v24_corpus_run_config(run_config)
            result = run_arm(
                route=run_config["routes"][0],
                arm="camp",
                config=run_config,
                output_dir=native_output,
                max_steps=64,
                decision_sink=writer,
            )
            if result.get("status") != "ok":
                raise RuntimeError(
                    str(result.get("failure_reason") or "native arm failed")
                )
            native_receipt = (
                output_dir
                / "native_receipts"
                / str(route["identity_sha256"])
                / f"seed_{seed}.json"
            )
            _write_json_atomic(native_receipt, result)
            writer.write_v24_run_receipt(
                status="ok", wall_clock_s=time.perf_counter() - started
            )
        except Exception as exc:
            receipt_status = "failed"
            writer.write_v24_run_receipt(
                status="failed",
                failure_stage="native_arm_execution",
                failure_reason=f"{type(exc).__name__}: {exc}",
                wall_clock_s=time.perf_counter() - started,
            )
        _record_completed_row(aggregate, writer, status=receipt_status)
        aggregate.update(
            {
                "schema": progress_schema,
                "status": "running",
                "last_completed_row": index,
                "free_disk_gib": free_bytes() / (1024**3),
            }
        )
        _write_json_atomic(output_dir / "progress.json", aggregate)
        if free_bytes() <= MINIMUM_FREE_BYTES:
            stopped_for_disk = True
            break

    _validate_terminal_snapshot_inventory(output_dir)
    aggregate = _aggregate_execution(output_dir, len(rows))
    if stopped_for_disk:
        status = "stopped_disk_floor"
    elif aggregate["failed_route_seed_runs"]:
        status = "complete_with_retained_failures"
    else:
        status = "complete"
    aggregate.update(
        {
            "schema": summary_schema,
            "status": status,
            "phase": phase,
            "corpus_steps": 64,
            "sample_every_ticks": 1,
            "theoretical_max_snapshots": len(rows) * 64,
            "wall_clock_s": time.perf_counter() - execution_started,
            "free_disk_gib": free_bytes() / (1024**3),
            "all_routes_retained_in_denominator": (
                aggregate["retained_route_seed_runs"] == len(rows)
            ),
            "tuning_executed": False,
            "calibration_accessed": False,
            "holdout_opened": False,
            "outcome_fields_consumed": [],
            "claim_authorized": False,
        }
    )
    if len(seeds) == 1:
        aggregate["seed"] = int(seeds[0])
    else:
        aggregate["seeds"] = [int(seed) for seed in seeds]
    _write_json_atomic(output_dir / summary_filename, aggregate)
    terminal_progress = dict(aggregate)
    terminal_progress.update(
        {
            "schema": progress_schema,
            "status": status,
            "last_completed_row": aggregate["retained_route_seed_runs"],
            "free_disk_gib": aggregate["free_disk_gib"],
        }
    )
    _write_json_atomic(output_dir / "progress.json", terminal_progress)
    return aggregate


def execute_pilot_manifest(
    manifest: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
    expected_route_count: int = 375,
    free_bytes: Callable[[], int] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    return _execute_manifest_rows(
        pilot_rows(manifest, expected_route_count=expected_route_count),
        template,
        output_dir=output_dir,
        run_arm=run_arm,
        phase=PILOT_PHASE,
        seeds=PILOT_SEEDS,
        summary_schema="camp_dp_v24_native_corpus_pilot_summary_v1",
        progress_schema="camp_dp_v24_native_corpus_pilot_progress_v1",
        summary_filename="pilot_summary.json",
        free_bytes=free_bytes,
        resume=resume,
    )


def execute_remaining_manifest(
    manifest: Mapping[str, Any],
    pilot_review: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
    expected_route_count: int = 375,
    free_bytes: Callable[[], int] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    return _execute_manifest_rows(
        remaining_rows(
            manifest, pilot_review, expected_route_count=expected_route_count
        ),
        template,
        output_dir=output_dir,
        run_arm=run_arm,
        phase=REMAINING_PHASE,
        seeds=REMAINING_SEEDS,
        summary_schema="camp_dp_v24_native_corpus_remaining_summary_v1",
        progress_schema="camp_dp_v24_native_corpus_remaining_progress_v1",
        summary_filename="remaining_summary.json",
        free_bytes=free_bytes,
        resume=resume,
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha = file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="ascii")
    return root_sha


def _row_order_sha256(rows: Sequence[tuple[Mapping[str, Any], int]]) -> str:
    payload = [
        {"record_key": str(route["record_key"]), "seed": int(seed)}
        for route, seed in rows
    ]
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _exact_source_root_checks(
    root: Path, expected_root_sha256: str, prefix: str
) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    manifest = root / "SHA256SUMS"
    root_receipt = root / "ROOT_SHA256SUMS"
    checks = [
        {"name": f"{prefix}_manifest_exists", "passed": manifest.is_file()},
        {
            "name": f"{prefix}_root_sha256",
            "passed": manifest.is_file()
            and file_sha256(manifest) == expected_root_sha256,
        },
        {
            "name": f"{prefix}_root_receipt",
            "passed": root_receipt.is_file()
            and root_receipt.read_text(encoding="ascii")
            == f"{expected_root_sha256}  SHA256SUMS\n",
        },
    ]
    listed: dict[str, str] = {}
    manifest_valid = manifest.is_file()
    if manifest_valid:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            parts = line.split("  ", 1)
            if len(parts) != 2:
                manifest_valid = False
                continue
            digest, relative = parts
            path = (root / relative).resolve()
            valid_entry = (
                len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
                and relative not in listed
                and relative not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
                and root in path.parents
            )
            if not valid_entry:
                manifest_valid = False
                continue
            listed[relative] = digest
            checks.append(
                {
                    "name": f"{prefix}_sha:{relative}",
                    "passed": path.is_file() and file_sha256(path) == digest,
                }
            )
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path not in {manifest, root_receipt}
    }
    checks.extend(
        [
            {"name": f"{prefix}_manifest_valid", "passed": manifest_valid},
            {
                "name": f"{prefix}_exact_inventory",
                "passed": manifest_valid and set(listed) == actual,
            },
        ]
    )
    return checks


def _artifact_checks_integrity(
    payload: Mapping[str, Any], *, require_failed_checks: bool
) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return False
    names = [check.get("name") for check in checks if isinstance(check, Mapping)]
    return (
        len(names) == len(checks)
        and all(isinstance(name, str) and name for name in names)
        and len(set(names)) == len(names)
        and all(check.get("passed") is True for check in checks)
        and payload.get("check_count") == len(checks)
        and payload.get("failed_count") == 0
        and (not require_failed_checks or payload.get("failed_checks") == [])
    )


def _remaining_execution_authorization_checks(
    *,
    remaining_preflight_root: Path,
    expected_remaining_preflight_root_sha256: str,
    remaining_review_root: Path,
    expected_remaining_review_root_sha256: str,
    rows: Sequence[tuple[Mapping[str, Any], int]],
    expected_corpus_preflight_root_sha256: str,
    expected_corpus_review_root_sha256: str,
    expected_pilot_root_sha256: str,
    expected_pilot_review_root_sha256: str,
    expected_route_count: int = 375,
    expected_source_invalid_count: int = 153,
) -> list[dict[str, Any]]:
    checks = _exact_source_root_checks(
        remaining_preflight_root,
        expected_remaining_preflight_root_sha256,
        "remaining_preflight",
    )
    checks.extend(
        _exact_source_root_checks(
            remaining_review_root,
            expected_remaining_review_root_sha256,
            "remaining_preflight_review",
        )
    )
    preflight = json.loads(
        (remaining_preflight_root / "preflight.json").read_text(encoding="utf-8")
    )
    review = json.loads(
        (remaining_review_root / "review.json").read_text(encoding="utf-8")
    )
    expected_run_count = expected_route_count * len(REMAINING_SEEDS)
    row_order_sha256 = _row_order_sha256(rows)

    expected_preflight = {
        "schema": "camp_dp_v24_native_corpus_remaining_execution_preflight_v1",
        "status": "passed",
        "failed_count": 0,
        "route_count": expected_route_count,
        "seeds": list(REMAINING_SEEDS),
        "route_seed_run_count": expected_run_count,
        "row_order_sha256": row_order_sha256,
        "theoretical_max_snapshots": expected_run_count * 64,
        "pilot_route_denominator_retained": expected_route_count,
        "pilot_failures_retained": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    for name, expected in expected_preflight.items():
        checks.append(
            {
                "name": f"remaining_preflight_{name}",
                "passed": preflight.get(name) == expected,
            }
        )
    checks.append(
        {
            "name": "remaining_preflight_outcomes_closed",
            "passed": preflight.get("outcome_fields_consumed") == [],
        }
    )
    checks.append(
        {
            "name": "remaining_preflight_checks_integrity",
            "passed": _artifact_checks_integrity(
                preflight, require_failed_checks=False
            ),
        }
    )

    expected_review = {
        "schema": "camp_dp_v24_native_corpus_remaining_preflight_independent_review_v1",
        "status": "passed",
        "failed_count": 0,
        "source_preflight_root_sha256": expected_remaining_preflight_root_sha256,
        "source_corpus_root_sha256": expected_corpus_preflight_root_sha256,
        "source_corpus_review_root_sha256": expected_corpus_review_root_sha256,
        "source_pilot_root_sha256": expected_pilot_root_sha256,
        "source_pilot_review_root_sha256": expected_pilot_review_root_sha256,
        "route_count": expected_route_count,
        "seeds": list(REMAINING_SEEDS),
        "route_seed_run_count": expected_run_count,
        "row_order_sha256": row_order_sha256,
        "source_invalid_route_count": expected_source_invalid_count,
        "validated_run_config_count": expected_run_count,
        "preflight_reexecuted": False,
        "execution_preflight_builder_imported_or_called": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_native_corpus_remaining_train_seeds_unique_execution_only"
        ),
    }
    for name, expected in expected_review.items():
        checks.append(
            {
                "name": f"remaining_review_{name}",
                "passed": review.get(name) == expected,
            }
        )
    checks.append(
        {
            "name": "remaining_review_outcomes_closed",
            "passed": review.get("outcome_fields_consumed") == [],
        }
    )
    checks.append(
        {
            "name": "remaining_review_checks_integrity",
            "passed": _artifact_checks_integrity(review, require_failed_checks=True),
        }
    )
    decision = review.get("decision")
    checks.append(
        {
            "name": "remaining_review_authorized",
            "passed": isinstance(decision, Mapping)
            and decision.get("remaining_execution_authorized") is True
            and decision.get("action")
            == "launch_one_unique_remaining_train_seed_execution"
            and decision.get("route_count") == expected_route_count
            and decision.get("seeds") == list(REMAINING_SEEDS)
            and decision.get("preserve_all_failures_and_denominator") is True
            and decision.get("route_removal_replacement_reordering_authorized") is False
            and decision.get("tuning_authorized") is False
            and decision.get("outcome_access_authorized") is False
            and decision.get("calibration_access_authorized") is False
            and decision.get("holdout_access_authorized") is False
            and decision.get("claim_authorized") is False,
        }
    )
    return checks


def _remaining_task_lock_available() -> bool:
    import fcntl

    REMAINING_TASK_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with REMAINING_TASK_LOCK.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _validate_remaining_resume(output_dir: Path, expected_heads: str) -> None:
    if any(
        (output_dir / name).exists()
        for name in ("SHA256SUMS", "ROOT_SHA256SUMS", "run.exit")
    ):
        raise ValueError("sealed or terminal remaining artifact cannot resume")
    heads = output_dir / "HEADS"
    command = output_dir / "COMMAND"
    if not heads.is_file() or heads.read_text(encoding="ascii") != expected_heads:
        raise ValueError("remaining resume HEADS mismatch")
    if (
        not command.is_file()
        or command.read_text(encoding="utf-8")
        != "v24 native corpus execute-remaining\n"
    ):
        raise ValueError("remaining resume COMMAND mismatch")


def _execution_preflight(
    *,
    preflight_root: Path,
    expected_preflight_root_sha256: str,
    review_root: Path,
    expected_review_root_sha256: str,
    template: Mapping[str, Any],
    dp_repo: Path,
    pilot_root: Path | None = None,
    expected_pilot_root_sha256: str | None = None,
    pilot_review_root: Path | None = None,
    expected_pilot_review_root_sha256: str | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any] | None,
    list[tuple[dict[str, Any], int]],
]:
    plan = json.loads((preflight_root / "corpus_plan.json").read_text())
    manifest = json.loads((preflight_root / "corpus_manifest.json").read_text())
    validate_corpus_boundaries(plan, manifest)
    if plan.get("plan_sha256") != CORPUS_PLAN_SHA256:
        raise ValueError("v24 corpus plan SHA mismatch")
    if manifest.get("manifest_sha256") != CORPUS_MANIFEST_SHA256:
        raise ValueError("v24 corpus manifest SHA mismatch")
    checks = _source_root_checks(
        preflight_root, expected_preflight_root_sha256, "corpus_preflight"
    )
    checks.extend(
        _source_root_checks(review_root, expected_review_root_sha256, "corpus_review")
    )
    remaining_inputs = (
        pilot_root,
        expected_pilot_root_sha256,
        pilot_review_root,
        expected_pilot_review_root_sha256,
    )
    if any(value is not None for value in remaining_inputs) and not all(
        value is not None for value in remaining_inputs
    ):
        raise ValueError("v24 remaining source roots must be supplied together")
    pilot_review = None
    if pilot_root is None:
        rows = pilot_rows(manifest)
        phase_label = "pilot"
    else:
        checks.extend(
            _source_root_checks(
                pilot_root, str(expected_pilot_root_sha256), "corpus_pilot"
            )
        )
        checks.extend(
            _source_root_checks(
                pilot_review_root,
                str(expected_pilot_review_root_sha256),
                "corpus_pilot_review",
            )
        )
        pilot_review = json.loads(
            (Path(pilot_review_root) / "review.json").read_text(encoding="utf-8")
        )
        if (
            pilot_review.get("source_pilot_root_sha256") != expected_pilot_root_sha256
            or pilot_review.get("source_corpus_preflight_root_sha256")
            != expected_preflight_root_sha256
        ):
            raise ValueError("v24 remaining pilot review source chain mismatch")
        rows = remaining_rows(manifest, pilot_review)
        phase_label = "remaining"
        checks.append(
            {
                "name": "remaining_task_lock_available",
                "passed": _remaining_task_lock_available(),
            }
        )
    dp_head = subprocess.run(
        ["git", "-C", str(dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dp_status = subprocess.run(
        ["git", "-C", str(dp_repo), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    validated = 0
    first_config = None
    for route, seed in rows:
        config = build_corpus_run_config(template, route, route["route_asset"], seed)
        validate_v24_corpus_run_config(config)
        if first_config is None:
            first_config = config
        validated += 1
    if first_config is None:
        raise ValueError("v24 pilot has no run config")
    verified_assets = verify_config_assets(first_config)
    route_assets: dict[str, str] = {}
    for route, _seed in rows:
        asset = route["route_asset"]
        path = str(asset["path"])
        digest = str(asset["sha256"])
        if path in route_assets and route_assets[path] != digest:
            raise ValueError("v24 route asset path has conflicting SHA256")
        route_assets[path] = digest
    route_assets_unchanged = all(
        Path(path).is_file() and file_sha256(Path(path)) == digest
        for path, digest in route_assets.items()
    )
    source_maps = {
        str(route["source_map_path"]): str(route["source_map_sha256"])
        for route, _seed in rows
    }
    source_maps_unchanged = all(
        Path(path).is_file() and file_sha256(Path(path)) == digest
        for path, digest in source_maps.items()
    )
    checks.extend(
        [
            {"name": "fixed_dp_head", "passed": dp_head == FIXED_DP_HEAD},
            {"name": "fixed_dp_tracked_clean", "passed": dp_status == ""},
            {
                "name": "verified_first_run_assets_complete",
                "passed": verified_asset_receipts_complete(verified_assets),
            },
            {
                "name": f"all_unique_route_assets_{len(route_assets)}_unchanged",
                "passed": len(route_assets) == 375 and route_assets_unchanged,
            },
            {"name": "all_live_source_maps_unchanged", "passed": source_maps_unchanged},
            {
                "name": f"{phase_label}_route_seed_runs_{len(rows)}",
                "passed": len(rows) == (375 if phase_label == "pilot" else 1500),
            },
            {
                "name": f"{phase_label}_configs_{validated}",
                "passed": validated == len(rows),
            },
            {
                "name": "disk_floor",
                "passed": shutil.disk_usage(preflight_root).free > MINIMUM_FREE_BYTES,
            },
        ]
    )
    return plan, manifest, checks, pilot_review, rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "execution-preflight",
            "execute-pilot",
            "remaining-execution-preflight",
            "execute-remaining",
        ),
        required=True,
    )
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--expected-review-root-sha256", required=True)
    parser.add_argument("--pilot-root", type=Path)
    parser.add_argument("--expected-pilot-root-sha256")
    parser.add_argument("--pilot-review-root", type=Path)
    parser.add_argument("--expected-pilot-review-root-sha256")
    parser.add_argument("--remaining-preflight-root", type=Path)
    parser.add_argument("--expected-remaining-preflight-root-sha256")
    parser.add_argument("--remaining-preflight-review-root", type=Path)
    parser.add_argument("--expected-remaining-preflight-review-root-sha256")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    remaining_mode = args.mode in {
        "remaining-execution-preflight",
        "execute-remaining",
    }
    preflight_mode = args.mode in {
        "execution-preflight",
        "remaining-execution-preflight",
    }
    if remaining_mode and any(
        value is None
        for value in (
            args.pilot_root,
            args.expected_pilot_root_sha256,
            args.pilot_review_root,
            args.expected_pilot_review_root_sha256,
        )
    ):
        raise ValueError("remaining modes require pilot and pilot-review roots")
    if args.mode == "execute-remaining" and any(
        value is None
        for value in (
            args.remaining_preflight_root,
            args.expected_remaining_preflight_root_sha256,
            args.remaining_preflight_review_root,
            args.expected_remaining_preflight_review_root_sha256,
        )
    ):
        raise ValueError(
            "execute-remaining requires remaining preflight and review roots"
        )
    if args.output_dir.exists() and not args.resume:
        raise FileExistsError(args.output_dir)
    if preflight_mode and args.resume:
        raise ValueError("execution preflight cannot resume")

    template = json.loads(args.template.read_text(encoding="utf-8"))
    plan, manifest, checks, pilot_review, rows = _execution_preflight(
        preflight_root=args.preflight_root,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        review_root=args.review_root,
        expected_review_root_sha256=args.expected_review_root_sha256,
        template=template,
        dp_repo=args.dp_repo,
        pilot_root=args.pilot_root if remaining_mode else None,
        expected_pilot_root_sha256=(
            args.expected_pilot_root_sha256 if remaining_mode else None
        ),
        pilot_review_root=args.pilot_review_root if remaining_mode else None,
        expected_pilot_review_root_sha256=(
            args.expected_pilot_review_root_sha256 if remaining_mode else None
        ),
    )
    if args.mode == "execute-remaining":
        checks.extend(
            _remaining_execution_authorization_checks(
                remaining_preflight_root=args.remaining_preflight_root,
                expected_remaining_preflight_root_sha256=(
                    args.expected_remaining_preflight_root_sha256
                ),
                remaining_review_root=args.remaining_preflight_review_root,
                expected_remaining_review_root_sha256=(
                    args.expected_remaining_preflight_review_root_sha256
                ),
                rows=rows,
                expected_corpus_preflight_root_sha256=(
                    args.expected_preflight_root_sha256
                ),
                expected_corpus_review_root_sha256=args.expected_review_root_sha256,
                expected_pilot_root_sha256=args.expected_pilot_root_sha256,
                expected_pilot_review_root_sha256=(
                    args.expected_pilot_review_root_sha256
                ),
            )
        )
    failed = [check["name"] for check in checks if not check["passed"]]
    if failed:
        raise ValueError(f"v24 corpus execution preflight failed: {failed}")
    heads = (
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_CORPUS_PREFLIGHT_ROOT_SHA256={args.expected_preflight_root_sha256}\n"
        f"SOURCE_CORPUS_REVIEW_ROOT_SHA256={args.expected_review_root_sha256}\n"
    )
    if remaining_mode:
        heads += (
            f"SOURCE_PILOT_ROOT_SHA256={args.expected_pilot_root_sha256}\n"
            "SOURCE_PILOT_INDEPENDENT_REVIEW_ROOT_SHA256="
            f"{args.expected_pilot_review_root_sha256}\n"
        )
    if args.mode == "execute-remaining":
        heads += (
            "SOURCE_REMAINING_PREFLIGHT_ROOT_SHA256="
            f"{args.expected_remaining_preflight_root_sha256}\n"
            "SOURCE_REMAINING_PREFLIGHT_INDEPENDENT_REVIEW_ROOT_SHA256="
            f"{args.expected_remaining_preflight_review_root_sha256}\n"
        )

    task_lock_handle = None
    if args.mode == "execute-remaining":
        import fcntl

        REMAINING_TASK_LOCK.parent.mkdir(parents=True, exist_ok=True)
        task_lock_handle = REMAINING_TASK_LOCK.open("a+")
        try:
            fcntl.flock(task_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another v24 remaining execution is active") from exc
        if args.output_dir.exists():
            _validate_remaining_resume(args.output_dir, heads)
        else:
            args.output_dir.mkdir(parents=True)
            (args.output_dir / "HEADS").write_text(heads, encoding="ascii")
            (args.output_dir / "COMMAND").write_text(
                "v24 native corpus execute-remaining\n", encoding="utf-8"
            )
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "HEADS").write_text(heads, encoding="ascii")
        (args.output_dir / "COMMAND").write_text(
            f"v24 native corpus {args.mode}\n", encoding="utf-8"
        )

    if args.mode == "execution-preflight":
        result = {
            "schema": "camp_dp_v24_native_corpus_pilot_execution_preflight_v1",
            "status": "passed",
            "check_count": len(checks),
            "failed_count": 0,
            "checks": checks,
            "route_count": 375,
            "seed": PILOT_SEED,
            "theoretical_max_snapshots": 24000,
            "model_loaded": False,
            "simulator_executed": False,
            "candidate_generation_started": False,
            "outcome_fields_consumed": [],
            "calibration_accessed": False,
            "holdout_opened": False,
            "tuning_executed": False,
            "claim_authorized": False,
            "next_work_target": "v24_native_corpus_capability_pilot_execution_only",
        }
        _write_json_atomic(args.output_dir / "preflight.json", result)
        (args.output_dir / "preflight.md").write_text(
            "# v24 native corpus pilot execution preflight\n\n"
            f"- checks / failed: `{len(checks)} / 0`\n"
            "- routes / seed / max snapshots: `375 / 24001 / 24000`\n"
            "- model/simulator/candidates/outcomes/holdout: `false/false/false/false/false`\n",
            encoding="utf-8",
        )
    elif args.mode == "remaining-execution-preflight":
        result = {
            "schema": "camp_dp_v24_native_corpus_remaining_execution_preflight_v1",
            "status": "passed",
            "check_count": len(checks),
            "failed_count": 0,
            "checks": checks,
            "route_count": 375,
            "seeds": list(REMAINING_SEEDS),
            "route_seed_run_count": len(rows),
            "row_order_sha256": _row_order_sha256(rows),
            "theoretical_max_snapshots": len(rows) * 64,
            "pilot_route_denominator_retained": (
                pilot_review["decision"]["route_count"]
                if pilot_review is not None
                else 0
            ),
            "pilot_failures_retained": (
                pilot_review["decision"]["preserve_all_failures_and_denominator"]
                if pilot_review is not None
                else False
            ),
            "model_loaded": False,
            "simulator_executed": False,
            "candidate_generation_started": False,
            "outcome_fields_consumed": [],
            "calibration_accessed": False,
            "holdout_opened": False,
            "training_executed": False,
            "tuning_executed": False,
            "claim_authorized": False,
            "next_work_target": (
                "v24_native_corpus_remaining_train_seeds_static_preflight_"
                "independent_review_only"
            ),
        }
        _write_json_atomic(args.output_dir / "preflight.json", result)
        (args.output_dir / "preflight.md").write_text(
            "# v24 remaining native corpus execution preflight\n\n"
            f"- checks / failed: `{len(checks)} / 0`\n"
            "- routes / seeds / runs / max snapshots: "
            "`375 / 4 / 1500 / 96000`\n"
            "- retained pilot denominator: `375 / 375`\n"
            "- model/simulator/candidates/outcomes/training/holdout: "
            "`false/false/false/false/false/false`\n",
            encoding="utf-8",
        )
    else:
        import fcntl

        if args.mode == "execute-pilot":
            lock_handle = (args.output_dir / ".pilot.lock").open("a+")
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another v24 pilot owns this artifact lock") from exc
            phase_seeds = list(PILOT_SEEDS)
        else:
            lock_handle = task_lock_handle
            phase_seeds = list(REMAINING_SEEDS)
        state_seed_fields = (
            {"seed": PILOT_SEED}
            if args.mode == "execute-pilot"
            else {"seeds": phase_seeds}
        )
        _write_json_atomic(
            args.output_dir / "STATE.json",
            {"status": "running", "pid": os.getpid(), **state_seed_fields},
        )
        first_route, first_seed = rows[0]
        first_config = build_corpus_run_config(
            template, first_route, first_route["route_asset"], first_seed
        )
        run_arm = build_native_arm_runner(first_config, device=args.device)
        if args.mode == "execute-pilot":
            result = execute_pilot_manifest(
                manifest,
                template,
                output_dir=args.output_dir,
                run_arm=run_arm,
                resume=True,
            )
        else:
            if pilot_review is None:
                raise ValueError("remaining execution lacks reviewed pilot decision")
            result = execute_remaining_manifest(
                manifest,
                pilot_review,
                template,
                output_dir=args.output_dir,
                run_arm=run_arm,
                resume=True,
            )
        _write_json_atomic(
            args.output_dir / "STATE.json",
            {"status": result["status"], "pid": os.getpid(), **state_seed_fields},
        )
        result["source_preflight_root_sha256"] = args.expected_preflight_root_sha256
        result["source_review_root_sha256"] = args.expected_review_root_sha256
        if args.mode == "execute-remaining":
            result["source_pilot_root_sha256"] = args.expected_pilot_root_sha256
            result["source_pilot_review_root_sha256"] = (
                args.expected_pilot_review_root_sha256
            )
            result["source_remaining_preflight_root_sha256"] = (
                args.expected_remaining_preflight_root_sha256
            )
            result["source_remaining_preflight_review_root_sha256"] = (
                args.expected_remaining_preflight_review_root_sha256
            )
        result["fixed_dp_head"] = FIXED_DP_HEAD
        result["next_work_target"] = (
            (
                "v24_native_corpus_capability_pilot_independent_review_only"
                if args.mode == "execute-pilot"
                else "v24_native_corpus_remaining_train_seeds_independent_review_only"
            )
            if result["status"].startswith("complete")
            else "global_stop_disk_floor"
        )
        _write_json_atomic(args.output_dir / "execution.json", result)
        title = (
            "# v24 native corpus capability pilot\n\n"
            if args.mode == "execute-pilot"
            else "# v24 remaining native corpus execution\n\n"
        )
        (args.output_dir / "execution.md").write_text(
            title + f"- status: `{result['status']}`\n"
            f"- complete / failed / retained: `{result['complete_route_seed_runs']} / {result['failed_route_seed_runs']} / {result['retained_route_seed_runs']}`\n"
            f"- snapshots: `{result['snapshot_count']}`\n"
            "- tuning/calibration/holdout/claim: `false/false/false/false`\n",
            encoding="utf-8",
        )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    success = result["status"] == "passed" or result["status"].startswith("complete")
    (args.output_dir / "run.exit").write_text(
        "0\n" if success else "2\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "status": result["status"],
                "check_count": len(checks),
                "failed_count": len(failed),
            },
            sort_keys=True,
        )
    )
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
