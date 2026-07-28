"""Forward-only V26 continuation identity for the interrupted Stage 8b plan.

The parent acquisition root is immutable.  This module reads only the parent
route/unit identities and terminal fields, derives the exact unattempted tail
of the 1783-route revised plan, and writes a separate successor plan.  It
never consumes parent candidates, labels, training rows, or outcomes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (
    FROZEN_FIXED_DP_HEAD,
    canonical_json_sha256,
)
from camp_core.integrations.diffusion_planner_v26_diversified_plan_revision import (
    PLAN_REVISION_EVIDENCE_ROLE,
    PLAN_REVISION_SCHEMA_VERSION,
)


SUCCESSOR_PLAN_SCHEMA_VERSION = "camp_dp_v26_diversified_training_successor_plan_v1"
SUCCESSOR_PLAN_EVIDENCE_ROLE = "development_nonholdout_diversified_training_successor_plan"
SUCCESSOR_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_diversified_training_successor_manifest_v1"
SUCCESSOR_UNIT_HASH_MANIFEST_SCHEMA_VERSION = (
    "camp_dp_v26_diversified_training_parent_unit_hash_manifest_v1"
)
SUCCESSOR_COVERAGE_SCHEMA_VERSION = "camp_dp_v26_diversified_training_parent_coverage_v1"
UNION_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_diversified_training_union_manifest_v1"
UNION_EVIDENCE_ROLE = "development_nonholdout_diversified_training_union"

PARENT_REVISED_ROUTE_COUNT = 1783
RETAINED_START = 0
RETAINED_END = 484
SUCCESSOR_START = 485
SUCCESSOR_END = 1782
RETAINED_COUNT = RETAINED_END - RETAINED_START + 1
SUCCESSOR_COUNT = SUCCESSOR_END - SUCCESSOR_START + 1
SCENARIO_SEED_BASE = 46001


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _serialized_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_bytes(_json_bytes(value))
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be a SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA256") from exc
    return value


def _copy_parent_plan(parent_plan: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(parent_plan))
    if (
        value.get("schema_version") != PLAN_REVISION_SCHEMA_VERSION
        or value.get("evidence_role") != PLAN_REVISION_EVIDENCE_ROLE
        or value.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or value.get("split") != "development_nonholdout"
        or value.get("holdout_accessed") is not False
        or value.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V26 successor parent revised-plan contract drifted")
    if value.get("denominator") != {
        "planned": PARENT_REVISED_ROUTE_COUNT,
        "complete": 0,
        "failed": 0,
        "unattempted": PARENT_REVISED_ROUTE_COUNT,
    }:
        raise ValueError("V26 successor parent revised-plan denominator drifted")
    routes = value.get("routes")
    if type(routes) is not list or len(routes) != PARENT_REVISED_ROUTE_COUNT:
        raise ValueError("V26 successor parent revised-plan route count drifted")
    route_ids: set[str] = set()
    for ordinal, item in enumerate(routes):
        if type(item) is not dict:
            raise ValueError("V26 successor parent route must be a mapping")
        schedule = dict(item)
        if type(schedule.get("parent_ordinal")) is not int:
            raise ValueError("V26 successor parent route parent ordinal drifted")
        route_id = schedule.get("route_id")
        record = schedule.get("route_record")
        if (
            type(route_id) is not str
            or not route_id
            or route_id in route_ids
            or type(record) is not dict
            or type(record.get("identity_sha256")) is not str
            or type(record.get("source_map_sha256")) is not str
            or type(record.get("source_stratum")) is not dict
        ):
            raise ValueError("V26 successor parent route identity drifted")
        route_ids.add(route_id)
    _require_sha256(value.get("route_plan_sha256"), "V26 successor parent route-plan SHA")
    return value


def _terminal_projection(unit: Mapping[str, Any]) -> dict[str, Any]:
    terminal = unit.get("terminal")
    if type(terminal) is not dict:
        raise ValueError("V26 successor parent unit terminal is missing")
    status = terminal.get("status")
    if status not in {"complete", "typed_failure", "unattempted"}:
        raise ValueError("V26 successor parent unit terminal status drifted")
    failure_class = terminal.get("failure_class")
    failure_reason = terminal.get("failure_reason")
    if status == "complete" and (failure_class is not None or failure_reason is not None):
        raise ValueError("V26 successor parent complete unit failure fields drifted")
    if status == "typed_failure" and (
        type(failure_class) is not str or not failure_class or type(failure_reason) is not str
    ):
        raise ValueError("V26 successor parent typed failure fields drifted")
    if status == "unattempted" and (failure_class is not None or failure_reason is not None):
        raise ValueError("V26 successor parent unattempted fields drifted")
    return {
        "status": status,
        "failure_class": failure_class,
        "failure_reason": failure_reason,
    }


def _route_projection(
    *, ordinal: int, unit: Mapping[str, Any], schedule: Mapping[str, Any]
) -> dict[str, Any]:
    route = unit.get("route")
    record = schedule.get("route_record")
    if type(route) is not dict or type(record) is not dict:
        raise ValueError("V26 successor parent route receipt is missing")
    parent_ordinal = int(schedule["parent_ordinal"])
    expected_seed = SCENARIO_SEED_BASE + parent_ordinal
    expected = {
        "family_id": schedule["family_id"],
        "route_id": schedule["route_id"],
        "corridor_id": schedule["corridor_id"],
        "parent_ordinal": parent_ordinal,
        "route_identity_sha256": record["identity_sha256"],
        "map_sha256": record["source_map_sha256"],
        "source_artifact_sha256": schedule["source_artifact_sha256"],
        "event_manifest_sha256": schedule["event_manifest_sha256"],
        "scenario_seed": expected_seed,
    }
    actual = {key: route.get(key) for key in expected}
    if actual != expected:
        raise ValueError(f"V26 successor parent unit {ordinal} route/seed identity drifted")
    return expected


def _coverage_table(
    *, retained: list[Mapping[str, Any]], parent_plan_sha256: str
) -> dict[str, Any]:
    fields = {
        "family": "family_id",
        "corridor": "corridor_id",
        "source": "source_artifact_sha256",
        "event": "event_manifest_sha256",
    }
    coverage: dict[str, dict[str, Counter[str]]] = {
        name: defaultdict(Counter) for name in fields
    }
    for item in retained:
        status = str(item["terminal"]["status"])
        route = dict(item["route"])
        for output_name, route_name in fields.items():
            coverage[output_name][str(route[route_name])][status] += 1
    return {
        "schema_version": SUCCESSOR_COVERAGE_SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_diversified_training_parent_coverage_read_only",
        "parent_revised_plan_sha256": parent_plan_sha256,
        "retained_revised_plan_ordinal_interval": [RETAINED_START, RETAINED_END],
        "denominator": {
            "planned": RETAINED_COUNT,
            "complete": sum(item["terminal"]["status"] == "complete" for item in retained),
            "failed": sum(item["terminal"]["status"] == "typed_failure" for item in retained),
            "unattempted": sum(item["terminal"]["status"] == "unattempted" for item in retained),
        },
        "coverage": {
            name: {key: dict(value) for key, value in sorted(group.items())}
            for name, group in coverage.items()
        },
    }


def read_parent_recovery_evidence(
    *, parent_recovered_root: Path, parent_plan: Mapping[str, Any]
) -> dict[str, Any]:
    """Read only atomic unit route/terminal identities from the recovered root."""

    root = parent_recovered_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    required = {
        "manifest": root / "manifest.json",
        "raw_receipt": root / "raw_receipt.json",
        "report": root / "report.json",
        "recovery_receipt": root / "recovery_receipt.json",
        "recovery_status": root / "recovery.status.json",
    }
    if not all(path.is_file() for path in required.values()):
        raise FileNotFoundError("V26 successor recovered-root binding is incomplete")
    manifest = json.loads(required["manifest"].read_text(encoding="utf-8"))
    report = json.loads(required["report"].read_text(encoding="utf-8"))
    if (
        manifest.get("route_plan_sha256") != parent_plan["route_plan_sha256"]
        or report.get("route_plan_sha256") != parent_plan["route_plan_sha256"]
        or report.get("denominator")
        != {"planned": 1783, "complete": 479, "failed": 6, "unattempted": 1298}
    ):
        raise ValueError("V26 successor recovered-root parent binding drifted")

    retained: list[dict[str, Any]] = []
    unattempted: list[dict[str, Any]] = []
    unit_sha256_by_ordinal: dict[str, str] = {}
    all_statuses: Counter[str] = Counter()
    routes = list(parent_plan["routes"])
    for ordinal, schedule in enumerate(routes):
        path = root / "units" / f"{ordinal:04d}.json"
        if not path.is_file():
            raise FileNotFoundError(f"V26 successor parent atomic unit is missing: {path}")
        unit = json.loads(path.read_text(encoding="utf-8"))
        if unit.get("unit_index") != ordinal:
            raise ValueError("V26 successor parent unit ordinal drifted")
        route = _route_projection(ordinal=ordinal, unit=unit, schedule=schedule)
        terminal = _terminal_projection(unit)
        unit_sha = _file_sha256(path)
        unit_sha256_by_ordinal[str(ordinal)] = unit_sha
        item = {
            "revised_plan_ordinal": ordinal,
            "unit_file_sha256": unit_sha,
            "planned_unit_id_sha256": unit.get("planned_unit_id_sha256"),
            "route": route,
            "terminal": terminal,
        }
        all_statuses[str(terminal["status"])] += 1
        if ordinal <= RETAINED_END:
            if terminal["status"] not in {"complete", "typed_failure"}:
                raise ValueError("V26 successor retained interval must already be terminal")
            retained.append(item)
        else:
            if terminal["status"] != "unattempted":
                raise ValueError("V26 successor tail must be the untouched unattempted interval")
            unattempted.append(item)
    if all_statuses != Counter({"complete": 479, "typed_failure": 6, "unattempted": 1298}):
        raise ValueError("V26 successor parent recovered denominator drifted")
    if len(retained) != RETAINED_COUNT or len(unattempted) != SUCCESSOR_COUNT:
        raise ValueError("V26 successor parent retained/tail boundary drifted")
    coverage = _coverage_table(
        retained=retained, parent_plan_sha256=str(parent_plan["route_plan_sha256"])
    )
    if coverage["denominator"] != {
        "planned": RETAINED_COUNT,
        "complete": 479,
        "failed": 6,
        "unattempted": 0,
    }:
        raise ValueError("V26 successor retained coverage denominator drifted")
    unit_hash_manifest = {
        "schema_version": SUCCESSOR_UNIT_HASH_MANIFEST_SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_diversified_training_parent_unit_hash_read_only",
        "parent_recovered_root": str(root),
        "parent_revised_plan_sha256": parent_plan["route_plan_sha256"],
        "unit_sha256_by_revised_plan_ordinal": unit_sha256_by_ordinal,
    }
    provenance = {
        "root": str(root),
        "manifest_sha256": _file_sha256(required["manifest"]),
        "raw_receipt_sha256": _file_sha256(required["raw_receipt"]),
        "report_sha256": _file_sha256(required["report"]),
        "recovery_receipt_sha256": _file_sha256(required["recovery_receipt"]),
        "recovery_status_sha256": _file_sha256(required["recovery_status"]),
        "parent_unit_hash_manifest_sha256": _serialized_sha256(unit_hash_manifest),
    }
    return {
        "provenance": provenance,
        "retained": retained,
        "unattempted": unattempted,
        "coverage": coverage,
        "unit_hash_manifest": unit_hash_manifest,
    }


def _plan_hash_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result.pop("route_plan_sha256", None)
    return result


def build_successor_plan(
    *, parent_revised_plan_path: Path, parent_recovered_root: Path
) -> dict[str, Any]:
    """Derive the exact 485..1782 continuation from immutable parent evidence."""

    parent_path = parent_revised_plan_path.resolve()
    if not parent_path.is_file():
        raise FileNotFoundError(parent_path)
    parent = _copy_parent_plan(json.loads(parent_path.read_text(encoding="utf-8")))
    parent_family_count = len({str(item["family_id"]) for item in parent["routes"]})
    parent_corridor_count = len({str(item["corridor_id"]) for item in parent["routes"]})
    if parent_family_count != 6 or parent_corridor_count != 155:
        raise ValueError("V26 successor must retain the fixed six-family/155-corridor design")
    evidence = read_parent_recovery_evidence(
        parent_recovered_root=parent_recovered_root, parent_plan=parent
    )
    routes: list[dict[str, Any]] = []
    for ordinal in range(SUCCESSOR_START, SUCCESSOR_END + 1):
        schedule = copy.deepcopy(dict(parent["routes"][ordinal]))
        schedule["revised_plan_ordinal"] = ordinal
        schedule["scenario_seed"] = SCENARIO_SEED_BASE + int(schedule["parent_ordinal"])
        routes.append(schedule)
    retained_failures = [
        item for item in evidence["retained"] if item["terminal"]["status"] == "typed_failure"
    ]
    plan: dict[str, Any] = {
        "schema_version": SUCCESSOR_PLAN_SCHEMA_VERSION,
        "evidence_role": SUCCESSOR_PLAN_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "parent_revised_plan": {
            "path": str(parent_path),
            "file_sha256": _file_sha256(parent_path),
            "schema_version": parent["schema_version"],
            "evidence_role": parent["evidence_role"],
            "route_plan_sha256": parent["route_plan_sha256"],
        },
        "parent_recovered_root": evidence["provenance"],
        "retained_parent_interval": {
            "revised_plan_ordinals": [RETAINED_START, RETAINED_END],
            "terminal_identities": evidence["retained"],
            "typed_failure_identities": retained_failures,
        },
        "successor_interval": {
            "revised_plan_ordinals": [SUCCESSOR_START, SUCCESSOR_END],
            "route_count": SUCCESSOR_COUNT,
            "pre_model": True,
            "not_result_driven": True,
            "parent_candidates_labels_training_rows_consumed": False,
        },
        "union_contract": {
            "parent_revised_plan_route_count": PARENT_REVISED_ROUTE_COUNT,
            "retained_interval": [RETAINED_START, RETAINED_END],
            "successor_interval": [SUCCESSOR_START, SUCCESSOR_END],
            "no_overlap": True,
            "no_rerun_retained_ordinals": True,
            "required_exact_revised_plan_ordinal_range": [0, PARENT_REVISED_ROUTE_COUNT - 1],
            "retained_denominator": {"complete": 479, "failed": 6, "unattempted": 0},
            "successor_initial_denominator": {
                "planned": SUCCESSOR_COUNT,
                "complete": 0,
                "failed": 0,
                "unattempted": SUCCESSOR_COUNT,
            },
            "full_denominator_contract": {"planned": PARENT_REVISED_ROUTE_COUNT},
            "preserve_parent_typed_failures_verbatim": True,
        },
        "family_projections": copy.deepcopy(parent["family_projections"]),
        "routes": routes,
        "identity": {
            "family_count": parent_family_count,
            "corridor_count": parent_corridor_count,
            "parent_revised_route_count": PARENT_REVISED_ROUTE_COUNT,
            "successor_route_count": SUCCESSOR_COUNT,
            "b8_same_ego_topology_frozen": True,
        },
        "denominator": {
            "planned": SUCCESSOR_COUNT,
            "complete": 0,
            "failed": 0,
            "unattempted": SUCCESSOR_COUNT,
        },
    }
    plan["route_plan_sha256"] = canonical_json_sha256(_plan_hash_payload(plan))
    return {
        "route_plan": plan,
        "parent_coverage": evidence["coverage"],
        "parent_unit_hash_manifest": evidence["unit_hash_manifest"],
        "parent_evidence": evidence,
    }


def validate_successor_plan(
    *,
    value: Mapping[str, Any],
    parent_revised_plan_path: Path,
    parent_recovered_root: Path,
) -> dict[str, Any]:
    expected = build_successor_plan(
        parent_revised_plan_path=parent_revised_plan_path,
        parent_recovered_root=parent_recovered_root,
    )
    actual = copy.deepcopy(dict(value))
    if actual != expected["route_plan"]:
        raise ValueError("V26 successor plan is not the exact parent-evidence continuation")
    return expected


def materialize_successor_plan(
    *,
    parent_revised_plan_path: Path,
    parent_recovered_root: Path,
    output_dir: Path,
    camp_head: str,
) -> dict[str, Path]:
    """Write a new successor plan root without changing any parent root."""

    root = output_dir.resolve()
    if root.exists():
        raise FileExistsError(f"V26 successor plan output already exists: {root}")
    material = build_successor_plan(
        parent_revised_plan_path=parent_revised_plan_path,
        parent_recovered_root=parent_recovered_root,
    )
    root.mkdir(parents=True, exist_ok=False)
    plan_path = root / "successor_plan.json"
    coverage_path = root / "parent_coverage.json"
    unit_hash_path = root / "parent_unit_hash_manifest.json"
    _atomic_write_json(unit_hash_path, material["parent_unit_hash_manifest"])
    if _file_sha256(unit_hash_path) != material["route_plan"]["parent_recovered_root"][
        "parent_unit_hash_manifest_sha256"
    ]:
        raise ValueError("V26 successor parent unit-hash manifest serialization drifted")
    _atomic_write_json(coverage_path, material["parent_coverage"])
    _atomic_write_json(plan_path, material["route_plan"])
    manifest = {
        "schema_version": SUCCESSOR_MANIFEST_SCHEMA_VERSION,
        "evidence_role": SUCCESSOR_PLAN_EVIDENCE_ROLE,
        "camp_head": str(camp_head),
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "successor_plan_path": str(plan_path),
        "successor_plan_file_sha256": _file_sha256(plan_path),
        "successor_plan_sha256": material["route_plan"]["route_plan_sha256"],
        "parent_coverage_path": str(coverage_path),
        "parent_coverage_sha256": _file_sha256(coverage_path),
        "parent_unit_hash_manifest_path": str(unit_hash_path),
        "parent_unit_hash_manifest_sha256": _file_sha256(unit_hash_path),
        "parent_recovered_root": material["route_plan"]["parent_recovered_root"],
        "pre_model": True,
        "outcome_fields_consumed": [],
        "not_result_driven": True,
    }
    manifest_path = root / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    _atomic_write_json(
        root / "run.status.json",
        {
            "evidence_role": SUCCESSOR_PLAN_EVIDENCE_ROLE,
            "status": "terminal",
            "successor_plan_sha256": material["route_plan"]["route_plan_sha256"],
            "denominator": material["route_plan"]["denominator"],
        },
    )
    (root / "run.exit").write_text("0\n", encoding="utf-8")
    return {
        "root": root,
        "plan": plan_path,
        "coverage": coverage_path,
        "parent_unit_hash_manifest": unit_hash_path,
        "manifest": manifest_path,
    }


def load_verified_successor_plan(
    *,
    successor_plan_path: Path,
    parent_revised_plan_path: Path,
    parent_recovered_root: Path,
) -> dict[str, Any]:
    plan_path = successor_plan_path.resolve()
    if not plan_path.is_file():
        raise FileNotFoundError(plan_path)
    expected = validate_successor_plan(
        value=json.loads(plan_path.read_text(encoding="utf-8")),
        parent_revised_plan_path=parent_revised_plan_path,
        parent_recovered_root=parent_recovered_root,
    )
    unit_hash_path = plan_path.parent / "parent_unit_hash_manifest.json"
    if not unit_hash_path.is_file() or (
        _file_sha256(unit_hash_path)
        != expected["route_plan"]["parent_recovered_root"]["parent_unit_hash_manifest_sha256"]
    ):
        raise ValueError("V26 successor parent unit-hash manifest binding drifted")
    if json.loads(unit_hash_path.read_text(encoding="utf-8")) != expected["parent_unit_hash_manifest"]:
        raise ValueError("V26 successor parent unit-hash manifest content drifted")
    return expected


def read_prior_successor_attempt(
    *, prior_attempt_root: Path, route_plan: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind the failed first tail attempt as immutable history, never training data.

    A recovery owns a fresh 485..1782 attempt.  The original ordinal-485
    ParentExecutionException remains visible only as attempt provenance, so the
    full scientific route identity remains represented exactly once in the new
    union rather than being silently reclassified or replayed.
    """

    root = prior_attempt_root.resolve()
    required = {
        "manifest": root / "manifest.json",
        "raw_receipt": root / "raw_receipt.json",
        "report": root / "report.json",
        "run_status": root / "run.status.json",
        "run_exit": root / "run.exit",
        "boundary_unit": root / "units" / f"{SUCCESSOR_START:04d}.json",
    }
    if not root.is_dir() or not all(path.is_file() for path in required.values()):
        raise FileNotFoundError("V26 predecessor tail-attempt evidence is incomplete")
    manifest = json.loads(required["manifest"].read_text(encoding="utf-8"))
    raw = json.loads(required["raw_receipt"].read_text(encoding="utf-8"))
    report = json.loads(required["report"].read_text(encoding="utf-8"))
    status = json.loads(required["run_status"].read_text(encoding="utf-8"))
    boundary = json.loads(required["boundary_unit"].read_text(encoding="utf-8"))
    expected_denominator = {
        "planned": SUCCESSOR_COUNT,
        "complete": 0,
        "failed": 1,
        "unattempted": SUCCESSOR_COUNT - 1,
    }
    if (
        manifest.get("successor_plan_sha256") != route_plan["route_plan_sha256"]
        or raw.get("successor_plan_sha256") != route_plan["route_plan_sha256"]
        or report.get("route_plan_sha256") != route_plan["route_plan_sha256"]
        or report.get("denominator") != expected_denominator
        or raw.get("denominator") != expected_denominator
        or status.get("denominator") != expected_denominator
        or report.get("status") != "terminal_no_trainable_pools"
        or status.get("status") != "terminal"
        or required["run_exit"].read_bytes() != b"0\n"
        or boundary.get("unit_index") != SUCCESSOR_START
        or boundary.get("terminal", {}).get("status") != "typed_failure"
        or boundary.get("terminal", {}).get("failure_class") != "ParentExecutionException"
        or boundary.get("parent_exception_boundary", {}).get("revised_plan_ordinal")
        != SUCCESSOR_START
    ):
        raise ValueError("V26 predecessor tail-attempt provenance drifted")
    return {
        "role": "immutable_prior_attempt_history_only",
        "root": str(root),
        "manifest_sha256": _file_sha256(required["manifest"]),
        "raw_receipt_sha256": _file_sha256(required["raw_receipt"]),
        "report_sha256": _file_sha256(required["report"]),
        "run_status_sha256": _file_sha256(required["run_status"]),
        "boundary_unit_sha256": _file_sha256(required["boundary_unit"]),
        "parent_exception_boundary": dict(boundary["parent_exception_boundary"]),
        "prior_denominator": expected_denominator,
        "scientific_route_identity_replayed": False,
        "outcome_fields_consumed": [],
    }


def materialize_immutable_union_manifest(
    *,
    successor_plan_path: Path,
    parent_revised_plan_path: Path,
    parent_recovered_root: Path,
    successor_acquisition_root: Path,
    output_dir: Path,
    prior_attempt_root: Path | None = None,
) -> Path:
    """Build a new immutable identity/denominator union after successor terminal."""

    root = output_dir.resolve()
    if root.exists():
        raise FileExistsError(f"V26 successor union output already exists: {root}")
    expected = load_verified_successor_plan(
        successor_plan_path=successor_plan_path,
        parent_revised_plan_path=parent_revised_plan_path,
        parent_recovered_root=parent_recovered_root,
    )
    plan = expected["route_plan"]
    prior_attempt = (
        read_prior_successor_attempt(prior_attempt_root=prior_attempt_root, route_plan=plan)
        if prior_attempt_root is not None
        else None
    )
    successor_root = successor_acquisition_root.resolve()
    required = ("manifest.json", "raw_receipt.json", "report.json", "run.status.json", "run.exit")
    if not successor_root.is_dir() or not all((successor_root / name).is_file() for name in required):
        raise FileNotFoundError("V26 successor acquisition terminal evidence is incomplete")
    parent_items = list(expected["parent_evidence"]["retained"])
    union_items = list(parent_items)
    statuses: Counter[str] = Counter(item["terminal"]["status"] for item in parent_items)
    seen_ordinals = {int(item["revised_plan_ordinal"]) for item in parent_items}
    seen_routes = {str(item["route"]["route_id"]) for item in parent_items}
    successor_units: list[dict[str, Any]] = []
    for schedule in plan["routes"]:
        ordinal = int(schedule["revised_plan_ordinal"])
        path = successor_root / "units" / f"{ordinal:04d}.json"
        if not path.is_file():
            raise FileNotFoundError(f"V26 successor atomic unit is missing: {path}")
        unit = json.loads(path.read_text(encoding="utf-8"))
        if unit.get("unit_index") != ordinal:
            raise ValueError("V26 successor unit ordinal drifted")
        route = _route_projection(ordinal=ordinal, unit=unit, schedule=schedule)
        terminal = _terminal_projection(unit)
        if ordinal in seen_ordinals or route["route_id"] in seen_routes:
            raise ValueError("V26 successor union contains a duplicate parent identity")
        item = {
            "revised_plan_ordinal": ordinal,
            "unit_file_sha256": _file_sha256(path),
            "planned_unit_id_sha256": unit.get("planned_unit_id_sha256"),
            "route": route,
            "terminal": terminal,
            "origin": "successor_acquisition",
        }
        seen_ordinals.add(ordinal)
        seen_routes.add(route["route_id"])
        statuses[str(terminal["status"])] += 1
        successor_units.append(item)
        union_items.append(item)
    if sorted(seen_ordinals) != list(range(PARENT_REVISED_ROUTE_COUNT)):
        raise ValueError("V26 successor union does not contain every revised-plan ordinal exactly once")
    if len(seen_routes) != PARENT_REVISED_ROUTE_COUNT:
        raise ValueError("V26 successor union route identities are not unique")
    denominator = {
        "planned": PARENT_REVISED_ROUTE_COUNT,
        "complete": int(statuses["complete"]),
        "failed": int(statuses["typed_failure"]),
        "unattempted": int(statuses["unattempted"]),
    }
    if sum(denominator.values()) - denominator["planned"] != denominator["planned"]:
        raise AssertionError("V26 successor union denominator arithmetic drifted")
    if denominator["failed"] < 6:
        raise ValueError("V26 successor union lost a retained typed failure")
    retained_failures = [
        item for item in parent_items if item["terminal"]["status"] == "typed_failure"
    ]
    union = {
        "schema_version": UNION_MANIFEST_SCHEMA_VERSION,
        "evidence_role": UNION_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "successor_plan": {
            "path": str(successor_plan_path.resolve()),
            "file_sha256": _file_sha256(successor_plan_path.resolve()),
            "route_plan_sha256": plan["route_plan_sha256"],
            "parent_revised_plan_sha256": plan["parent_revised_plan"]["route_plan_sha256"],
        },
        "parent_recovered_root": plan["parent_recovered_root"],
        "prior_attempt_history": prior_attempt,
        "successor_acquisition_root": {
            "path": str(successor_root),
            "manifest_sha256": _file_sha256(successor_root / "manifest.json"),
            "raw_receipt_sha256": _file_sha256(successor_root / "raw_receipt.json"),
            "report_sha256": _file_sha256(successor_root / "report.json"),
        },
        "denominator": denominator,
        "membership": {
            "required_revised_plan_ordinal_range": [0, PARENT_REVISED_ROUTE_COUNT - 1],
            "retained_interval": [RETAINED_START, RETAINED_END],
            "successor_interval": [SUCCESSOR_START, SUCCESSOR_END],
            "exactly_once": True,
            "route_ids_unique": True,
        },
        "retained_typed_failures_verbatim": retained_failures,
        "units": union_items,
    }
    root.mkdir(parents=True, exist_ok=False)
    manifest_path = root / "immutable_union_manifest.json"
    _atomic_write_json(manifest_path, union)
    _atomic_write_json(
        root / "run.status.json",
        {
            "evidence_role": UNION_EVIDENCE_ROLE,
            "status": "terminal",
            "denominator": denominator,
            "immutable_union_manifest_sha256": _file_sha256(manifest_path),
        },
    )
    (root / "run.exit").write_text("0\n", encoding="utf-8")
    return manifest_path
