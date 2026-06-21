#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
    parse_selection_log_metadata,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    FORMAL_SEEDS,
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
    _run_key,
    _scenario_buckets,
)


READY_STATUS = "offline_convex_selector_training_input_manifest_ready"
BLOCKED_STATUS = "offline_convex_selector_training_input_manifest_blocked"
SOURCE_STATUS = "offline_convex_selector_training_plan_ready"
SOURCE_NEXT_WORK = "offline_convex_selector_training_input_manifest_gate"
AUTHORIZED_NEXT_WORK = "offline_convex_selector_training_execution_dry_run_only"

DEFAULT_REQUIRED_BUCKETS = tuple(
    bucket for bucket in sorted(SUPPORTED_SCENARIO_BUCKETS) if bucket != "overall"
)
REQUIRED_OUTCOME_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "progress_m",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and materialize the immutable nonformal input manifest for "
            "offline convex DP-CAMP selector training. This does not train."
        )
    )
    parser.add_argument("--training_plan_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, required=True)
    parser.add_argument(
        "--required_bucket",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        action="append",
        default=None,
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        training_plan=_load_json(args.training_plan_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        required_buckets=tuple(args.required_bucket or DEFAULT_REQUIRED_BUCKETS),
        label=args.label,
        paths={"training_plan_json": str(args.training_plan_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: Sequence[Path],
    *,
    training_plan: dict[str, Any],
    scenario_bucket_manifest: Path,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
    label: str | None = None,
    paths_note: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not paths:
        raise ValueError("At least one --root or --selection_log is required.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    log_paths = iter_selection_log_paths(list(paths))
    plan_checks = _training_plan_checks(training_plan)
    log_entries: list[dict[str, Any]] = []
    errors: list[str] = []
    bucket_counts = {bucket: 0 for bucket in ("overall", *required_buckets)}
    total_records = 0
    formal_seed_logs = 0
    atom_dimensions: set[int] = set()
    candidate_counts: set[int] = set()

    for log_path in log_paths:
        try:
            entry = _audit_log(log_path, manifest)
        except Exception as exc:  # pragma: no cover - defensive CLI diagnostics
            errors.append(f"{log_path}: {exc}")
            continue
        log_entries.append(entry)
        total_records += int(entry["records"])
        if entry["formal_seed"]:
            formal_seed_logs += 1
            errors.append(f"{log_path}: formal_seed_detected")
        if entry["errors"]:
            errors.extend(f"{log_path}: {error}" for error in entry["errors"])
        for bucket in entry["scenario_buckets"]:
            if bucket in bucket_counts:
                bucket_counts[bucket] += int(entry["records"])
        atom_dimensions.add(int(entry["atom_dim"]))
        candidate_counts.add(int(entry["candidate_count"]))

    missing_required = [
        bucket for bucket in required_buckets if int(bucket_counts.get(bucket, 0)) <= 0
    ]
    if missing_required:
        errors.append(f"missing_required_buckets={','.join(missing_required)}")
    passed = (
        all(check["passed"] for check in plan_checks)
        and bool(log_entries)
        and formal_seed_logs == 0
        and not missing_required
        and not errors
    )
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_selector_training_input_manifest_v1",
            "label": label,
            "training": False,
            "training_execution": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "scenario_bucket_manifest": str(scenario_bucket_manifest),
            "paths": paths_note or {},
            "math_boundary": (
                "This manifest freezes existing nonformal candidate logs for "
                "offline convex CAMP training. It checks labels and atoms but "
                "does not optimize weights, change DP candidates, change online "
                "features, or construct a DP-side classical Benders proof."
            ),
        },
        "plan_checks": plan_checks,
        "summary": {
            "logs": len(log_entries),
            "records": total_records,
            "formal_seed_logs": formal_seed_logs,
            "atom_dimensions": sorted(atom_dimensions),
            "candidate_counts": sorted(candidate_counts),
            "required_buckets": list(required_buckets),
            "missing_required_buckets": missing_required,
            "bucket_record_counts": bucket_counts,
            "errors": errors,
        },
        "manifest": {
            "immutable": True,
            "logs": log_entries,
        },
        "final_decision": _final_decision(passed),
    }


def _audit_log(log_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    records = _read_json(log_path)
    if not isinstance(records, list) or not records:
        raise ValueError("camp_selection_log.json must contain a nonempty list")
    summary = _read_json_if_exists(log_path.with_name("camp_validation_summary.json"))
    benchmark = summary.get("benchmark") if isinstance(summary, dict) else None
    if not isinstance(benchmark, dict):
        benchmark = {}
    metadata = parse_selection_log_metadata(log_path)
    seed = _first_int(benchmark.get("seed"), metadata.seed)
    route = benchmark.get("route") or metadata.route
    row = {
        "run_key": _run_key(summary if isinstance(summary, dict) else {}, log_path.parent),
        "route": route,
        "route_name": Path(str(route)).stem if route is not None else metadata.route,
        "seed": seed,
        "steps": _first_int(benchmark.get("steps"), len(records)),
        "max_npcs": _first_int(benchmark.get("max_npcs"), metadata.npc_count),
        "spawn_probability": _first_float(
            benchmark.get("spawn_probability"),
            _parse_spawn_probability(metadata.spawn),
        ),
        "traffic_lights": _first_bool(
            benchmark.get("traffic_lights"),
            metadata.traffic_light == "on",
        ),
        "advance_mode": benchmark.get("advance_mode") or metadata.mode,
    }
    buckets = _scenario_buckets(row, manifest)
    errors: list[str] = []
    atom_dim: int | None = None
    candidate_count: int | None = None
    for index, record in enumerate(records):
        record_errors, record_atom_dim, record_candidate_count = _audit_record(record)
        errors.extend(f"record_{index}:{error}" for error in record_errors)
        if atom_dim is None:
            atom_dim = record_atom_dim
        elif atom_dim != record_atom_dim:
            errors.append(f"record_{index}:atom_dim_changed")
        if candidate_count is None:
            candidate_count = record_candidate_count
        elif candidate_count != record_candidate_count:
            errors.append(f"record_{index}:candidate_count_changed")
    return {
        "path": str(log_path),
        "sha256": _sha256(log_path),
        "records": len(records),
        "candidate_count": int(candidate_count or 0),
        "atom_dim": int(atom_dim or 0),
        "seed": seed,
        "formal_seed": seed in FORMAL_SEEDS,
        "scenario_row": row,
        "scenario_buckets": buckets,
        "errors": errors,
    }


def _audit_record(record: Any) -> tuple[list[str], int, int]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record_not_object"], 0, 0
    atoms = np.asarray(record.get("atoms"), dtype=np.float64)
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool)
    outcomes = record.get("candidate_closed_loop_outcomes")
    if atoms.ndim != 2 or atoms.shape[0] == 0 or atoms.shape[1] == 0:
        errors.append("atoms_not_nonempty_matrix")
        candidate_count = 0
        atom_dim = 0
    else:
        candidate_count = int(atoms.shape[0])
        atom_dim = int(atoms.shape[1])
        if not np.isfinite(atoms).all():
            errors.append("atoms_nonfinite")
    if feasible.shape != (candidate_count,):
        errors.append("feasible_mask_shape_mismatch")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        errors.append("candidate_closed_loop_outcomes_shape_mismatch")
    else:
        for idx, outcome in enumerate(outcomes):
            if not isinstance(outcome, dict):
                errors.append(f"outcome_{idx}_not_object")
                continue
            missing = [field for field in REQUIRED_OUTCOME_FIELDS if field not in outcome]
            if missing:
                errors.append(f"outcome_{idx}_missing={','.join(missing)}")
            if not bool(outcome.get("feasible", True)) and "feasible" not in outcome:
                errors.append(f"outcome_{idx}_missing=feasible")
    return errors, atom_dim, candidate_count


def _training_plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = plan.get("final_decision") or {}
    return [
        _check_equal("training_plan_status_ready", decision.get("status"), SOURCE_STATUS),
        _check_equal("training_plan_passed", decision.get("passed"), True),
        _check_equal(
            "training_plan_authorizes_manifest_gate",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "training_plan_execution_not_authorized",
            decision.get("training_execution_authorized"),
            False,
        ),
        _check_equal(
            "training_plan_camp_retraining_not_authorized",
            decision.get("camp_retraining_authorized"),
            False,
        ),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["summary"]
    lines = [
        "# Offline Convex Selector Training Input Manifest",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- training execution authorized: `{decision['training_execution_authorized']}`",
        f"- logs: `{summary['logs']}`",
        f"- records: `{summary['records']}`",
        f"- formal seed logs: `{summary['formal_seed_logs']}`",
        "",
        "## Required Bucket Counts",
        "",
        "| Bucket | Records |",
        "| --- | ---: |",
    ]
    for bucket, count in summary["bucket_record_counts"].items():
        lines.append(f"| `{bucket}` | `{count}` |")
    lines.extend(["", "## Plan Checks", "", "| Check | Passed | Detail |", "| --- | --- | --- |"])
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"actual=`{check.get('actual')}`, expected=`{check.get('expected')}` |"
        )
    lines.extend(["", "## Errors", ""])
    if summary["errors"]:
        lines.extend(f"- {error}" for error in summary["errors"])
    else:
        lines.append("none")
    lines.extend(["", "## Manifest Logs", ""])
    lines.extend(
        [
            "| Path | SHA-256 | Records | Buckets |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for entry in report["manifest"]["logs"]:
        lines.append(
            f"| `{entry['path']}` | `{entry['sha256']}` | "
            f"{entry['records']} | {','.join(entry['scenario_buckets'])} |"
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Run a training execution dry run only after reviewing this manifest."
            if passed
            else "Repair manifest inputs before any training execution."
        ),
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_float(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_bool(*values: Any) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
    return None


def _parse_spawn_probability(value: str | None) -> float | None:
    if not value:
        return None
    text = value
    if text.startswith("spawn_"):
        text = text[len("spawn_") :]
    text = text.replace("p", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
