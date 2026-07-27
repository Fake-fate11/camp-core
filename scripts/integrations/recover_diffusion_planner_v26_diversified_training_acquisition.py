"""Ledger-only recovery for a Stage 8b acquisition finalization failure.

This command never imports a model, Diffusion Planner replay, torch, or CUDA.
It only reads immutable atomic unit receipts, verifies their byte hashes, and
atomically materializes the missing terminal artifacts in the existing root.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (  # noqa: E402
    canonical_json_sha256,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    v26_generator_topology,
)
from scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition import (  # noqa: E402
    EVIDENCE_ROLE,
    LABEL_SIDECAR_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION,
    _AcquisitionLedger,
    _atomic_write_json,
    _file_sha256,
)


RECOVERY_SCHEMA_VERSION = "camp_dp_v26_stage8b_atomic_ledger_recovery_v1"
RECOVERY_EVIDENCE_ROLE = "development_training_same_ego_b8_acquisition_recovery"
_TERMINAL_STATUSES = frozenset({"complete", "typed_failure", "unattempted"})
_MISSING_OUTPUTS = (
    "raw_receipt.json",
    "report.json",
    "training_rows.npz",
    "training_scales.json",
    "label_sidecar.json",
    "run.exit",
)


def _atomic_write_text(path: Path, value: str) -> None:
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(value, encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _tracked_changes(path: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=path,
            text=True,
            encoding="utf-8",
        ).strip()
    )


def _contiguous_ranges(indices: Sequence[int]) -> list[list[int]]:
    ranges: list[list[int]] = []
    for index in sorted(indices):
        if not ranges or index != ranges[-1][1] + 1:
            ranges.append([index, index])
        else:
            ranges[-1][1] = index
    return ranges


def _load_atomic_units(root: Path, *, planned: int) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    unit_dir = root / "units"
    expected = {f"{index:04d}.json" for index in range(planned)}
    if not unit_dir.is_dir() or {path.name for path in unit_dir.glob("*.json")} != expected:
        raise ValueError("V26 Stage8b recovery unit inventory is not exact")
    units: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    typed: list[dict[str, Any]] = []
    unattempted_indices: list[int] = []
    for index in range(planned):
        path = unit_dir / f"{index:04d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        terminal = dict(payload.get("terminal", {}))
        status = terminal.get("status")
        if payload.get("unit_index") != index or status not in _TERMINAL_STATUSES:
            raise ValueError("V26 Stage8b recovery unit terminal schema drifted")
        hashes[str(index)] = _file_sha256(path)
        units.append(payload)
        if status == "typed_failure":
            route = dict(payload.get("route", {}))
            typed.append(
                {
                    "unit_index": index,
                    "parent_ordinal": route.get("parent_ordinal"),
                    "family_id": route.get("family_id"),
                    "route_id": route.get("route_id"),
                    "failure_class": terminal.get("failure_class"),
                    "failure_reason": terminal.get("failure_reason"),
                }
            )
        elif status == "unattempted":
            unattempted_indices.append(index)
    groups = Counter((item["failure_class"], item["failure_reason"]) for item in typed)
    inspection = {
        "typed_failure_units": typed,
        "typed_failure_groups": [
            {"failure_class": key[0], "failure_reason": key[1], "count": count}
            for key, count in sorted(groups.items())
        ],
        "unattempted": {
            "count": len(unattempted_indices),
            "ranges": _contiguous_ranges(unattempted_indices),
            "first_unit_index": unattempted_indices[0] if unattempted_indices else None,
            "last_unit_index": unattempted_indices[-1] if unattempted_indices else None,
            "ledger_semantics": "run_terminated_before_this_planned_unit",
            "all_terminal_failure_fields_null": all(
                dict(units[index]["terminal"]).get("failure_class") is None
                and dict(units[index]["terminal"]).get("failure_reason") is None
                for index in unattempted_indices
            ),
            "cause_evidence_limit": "immutable unit ledgers establish non-execution after termination; they do not retain a parent exception string",
        },
    }
    return units, hashes, inspection


def _denominator(units: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter(str(dict(unit["terminal"])["status"]) for unit in units)
    result = {
        "planned": len(units),
        "complete": counts["complete"],
        "failed": counts["typed_failure"],
        "unattempted": counts["unattempted"],
    }
    if sum(result[name] for name in ("complete", "failed", "unattempted")) != result["planned"]:
        raise ValueError("V26 Stage8b recovery denominator is incomplete")
    return result


def _recovery_provenance(
    *,
    root: Path,
    manifest: Mapping[str, Any],
    stale_status: Mapping[str, Any],
    stale_status_sha256: str,
    unit_hashes: Mapping[str, str],
    inspection: Mapping[str, Any],
    repaired_head: str,
    stderr_log: Path,
) -> dict[str, Any]:
    return {
        "schema_version": RECOVERY_SCHEMA_VERSION,
        "evidence_role": RECOVERY_EVIDENCE_ROLE,
        "recovery_mode": "atomic_unit_ledger_only_no_model_dp_gpu_latent_generation",
        "root": str(root),
        "manifest_sha256": _file_sha256(root / "manifest.json"),
        "route_plan_sha256": manifest["route_plan_sha256"],
        "original_stale_run_status": dict(stale_status),
        "original_stale_run_status_sha256": stale_status_sha256,
        "original_stderr_log_path": str(stderr_log),
        "original_stderr_log_sha256": _file_sha256(stderr_log),
        "repaired_code_head": repaired_head,
        "recovery_script_sha256": _file_sha256(Path(__file__).resolve()),
        "unit_file_sha256_by_index": dict(unit_hashes),
        "unit_hash_manifest_sha256": canonical_json_sha256(dict(unit_hashes)),
        "failure_inspection": dict(inspection),
        "recovery_invocation_counts": {
            "model_forward_count": 0,
            "dp_forward_count": 0,
            "gpu_invocation_count": 0,
            "latent_generation_count": 0,
            "candidate_generation_count": 0,
            "sequential_forward_count": 0,
        },
    }


def run(args: argparse.Namespace) -> Path:
    root = args.output_dir.resolve()
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 Stage8b recovery requires an exact clean repaired CAMP checkout")
    manifest_path = root / "manifest.json"
    status_path = root / "run.status.json"
    stderr_path = args.original_stderr_log.resolve()
    if not root.is_dir() or not manifest_path.is_file() or not status_path.is_file() or not stderr_path.is_file():
        raise FileNotFoundError("V26 Stage8b recovery root provenance input is missing")
    if any((root / name).exists() for name in _MISSING_OUTPUTS):
        raise FileExistsError("V26 Stage8b recovery refuses to overwrite terminal artifacts")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stale_status = json.loads(status_path.read_text(encoding="utf-8"))
    stale_status_sha256 = _file_sha256(status_path)
    if (
        manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("evidence_role") != EVIDENCE_ROLE
        or manifest.get("route_plan_sha256") != args.expected_route_plan_sha256
        or manifest.get("planned_unit_count") != args.expected_planned
        or stale_status_sha256 != args.expected_stale_status_sha256
        or stale_status != {"evidence_role": EVIDENCE_ROLE, "status": "running", "planned": args.expected_planned}
    ):
        raise ValueError("V26 Stage8b recovery root identity or stale-status binding drifted")
    units, unit_hashes, inspection = _load_atomic_units(root, planned=args.expected_planned)
    denominator = _denominator(units)
    expected_denominator = {
        "planned": args.expected_planned,
        "complete": args.expected_complete,
        "failed": args.expected_failed,
        "unattempted": args.expected_unattempted,
    }
    if denominator != expected_denominator:
        raise ValueError("V26 Stage8b recovery denominator drifted from the immutable unit ledger")
    complete = [unit for unit in units if unit["terminal"]["status"] == "complete"]
    rows_sha, scales_sha, label_sha = _AcquisitionLedger.write_training_artifacts_from_atomic_units(
        output_dir=root, manifest=manifest, complete=complete
    )
    report = {
        "schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "status": "terminal_training_evidence" if complete else "terminal_no_trainable_pools",
        "fixed_dp_head": manifest["fixed_dp_head"],
        "camp_head": manifest["camp_head"],
        "route_plan_sha256": manifest["route_plan_sha256"],
        "generator_id": V26_GENERATOR_ID,
        "generator_topology": v26_generator_topology(),
        "runner_id": "camp_dp_v26_native_same_ego_b8_acquisition_runner_v1",
        "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
        "training_rows_schema_version": V26_TRAINING_ROWS_SCHEMA_VERSION,
        "evaluation_schema": "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1",
        "outcome_fields_consumed": [],
        "holdout_accessed": False,
        "source_manifest_sha256": manifest["route_plan_sha256"],
        "training_rows_sha256": rows_sha,
        "training_scales_sha256": scales_sha,
        "label_sidecar_sha256": label_sha,
        "snapshot_count": len(complete),
        "candidate_count": len(complete) * 8,
        "denominator": denominator,
        "failure_denominator_complete": True,
        "terminal_error": "original_finalization_exception_not_persisted_recovered_from_atomic_units",
        "recovery_provenance_pending": True,
    }
    _atomic_write_json(root / "report.json", report)
    raw_receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "manifest_sha256": _file_sha256(manifest_path),
        "route_plan_sha256": manifest["route_plan_sha256"],
        "denominator": denominator,
        "terminal_error": report["terminal_error"],
        "recovered_from_atomic_units": True,
    }
    _atomic_write_json(root / "raw_receipt.json", raw_receipt)
    _atomic_write_text(root / "run.exit", "0\n")
    provenance = _recovery_provenance(
        root=root,
        manifest=manifest,
        stale_status=stale_status,
        stale_status_sha256=stale_status_sha256,
        unit_hashes=unit_hashes,
        inspection=inspection,
        repaired_head=args.expected_camp_head,
        stderr_log=stderr_path,
    )
    output_hashes = {
        name: _file_sha256(root / name)
        for name in (*_MISSING_OUTPUTS,)
    }
    provenance["output_file_sha256"] = output_hashes
    _atomic_write_json(root / "recovery_receipt.json", provenance)
    _atomic_write_json(
        root / "recovery.status.json",
        {
            "schema_version": RECOVERY_SCHEMA_VERSION,
            "evidence_role": RECOVERY_EVIDENCE_ROLE,
            "status": "terminal_recovered_from_atomic_units",
            "denominator": denominator,
            "route_plan_sha256": manifest["route_plan_sha256"],
            "recovery_receipt_sha256": _file_sha256(root / "recovery_receipt.json"),
            "output_file_sha256": output_hashes,
        },
    )
    if {
        str(index): _file_sha256(root / "units" / f"{index:04d}.json")
        for index in range(args.expected_planned)
    } != unit_hashes:
        raise RuntimeError("V26 Stage8b recovery detected immutable unit-byte drift")
    return root / "recovery_receipt.json"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--original-stderr-log", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument("--expected-route-plan-sha256", required=True)
    parser.add_argument("--expected-stale-status-sha256", required=True)
    parser.add_argument("--expected-planned", type=int, required=True)
    parser.add_argument("--expected-complete", type=int, required=True)
    parser.add_argument("--expected-failed", type=int, required=True)
    parser.add_argument("--expected-unattempted", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(parse_args(argv)))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
