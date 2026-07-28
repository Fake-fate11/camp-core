"""Materialize the V26 partial-source training rows from immutable unit ledgers.

The final-population receipt closes membership using identity-only data.  This
module is the separate, reproducible transition that reads the selected V26
atomic unit payloads to build rows and train-only scales.  It never invokes a
model, Diffusion Planner, CUDA, or a V25 high-level consumer.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (
    FROZEN_FIXED_DP_HEAD,
)
from camp_core.integrations.diffusion_planner_v26_diversified_successor import (
    UNION_EVIDENCE_ROLE,
    UNION_MANIFEST_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_partial_source_training import (
    EXPECTED_PLANNED,
    EXPECTED_TRAINABLE,
    EXPECTED_TYPED_FAILURES,
    PARTIAL_SOURCE_ARTIFACT_ROLE,
    load_final_training_population_receipt,
    validate_partial_source_training_manifest,
)
from scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition import (
    EVIDENCE_ROLE as V26_ACQUISITION_EVIDENCE_ROLE,
    _AcquisitionLedger,
    _atomic_write_json,
    _atomic_write_npz,
    _file_sha256,
)


MATERIALIZATION_SCHEMA_VERSION = "camp_dp_v26_partial_source_rows_materialization_v1"
MATERIALIZATION_EVIDENCE_ROLE = (
    "development_nonholdout_six_family_partial_source_rows_materialization"
)
MATERIALIZATION_RUNNER_ID = "camp_dp_v26_partial_source_ledger_materializer_v1"
_ROUTE_FIELDS = (
    "family_id",
    "route_id",
    "corridor_id",
    "parent_ordinal",
    "route_identity_sha256",
    "map_sha256",
    "source_artifact_sha256",
    "event_manifest_sha256",
    "scenario_seed",
)


def _json_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be a SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA256") from exc
    return value


def _require_git_head(value: str) -> str:
    if len(value) != 40:
        raise ValueError("V26 partial-source materialization CAMP head is invalid")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("V26 partial-source materialization CAMP head is invalid") from exc
    return value


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()


def _source_root(value: Any, label: str) -> Path:
    if type(value) is str and value:
        return Path(value).resolve()
    if type(value) is dict:
        mapping = dict(value)
        for key in ("path", "root"):
            if type(mapping.get(key)) is str and mapping[key]:
                return Path(mapping[key]).resolve()
    raise ValueError(f"V26 partial-source {label} root binding is missing")


def _route_projection(value: Any, *, ordinal: int) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("V26 partial-source source unit route is missing")
    route = dict(value)
    if route.get("parent_ordinal") != ordinal:
        raise ValueError("V26 partial-source source unit route ordinal drifted")
    for field in _ROUTE_FIELDS:
        if field not in route:
            raise ValueError("V26 partial-source source unit route field is missing")
    return {field: route[field] for field in _ROUTE_FIELDS}


def _validate_union(value: Mapping[str, Any], *, expected_sha256: str) -> dict[str, Any]:
    union = dict(value)
    if (
        union.get("schema_version") != UNION_MANIFEST_SCHEMA_VERSION
        or union.get("evidence_role") != UNION_EVIDENCE_ROLE
        or union.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or union.get("split") != "development_nonholdout"
        or union.get("holdout_accessed") is not False
        or union.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V26 partial-source immutable union contract drifted")
    _require_sha256(expected_sha256, "V26 partial-source immutable union")
    membership = union.get("membership")
    if (
        type(membership) is not dict
        or membership.get("required_revised_plan_ordinal_range") != [0, EXPECTED_PLANNED - 1]
        or membership.get("retained_interval") != [0, 484]
        or membership.get("successor_interval") != [485, EXPECTED_PLANNED - 1]
        or membership.get("exactly_once") is not True
        or membership.get("route_ids_unique") is not True
    ):
        raise ValueError("V26 partial-source immutable union membership drifted")
    denominator = union.get("denominator")
    if denominator != {
        "planned": EXPECTED_PLANNED,
        "complete": EXPECTED_TRAINABLE,
        "failed": EXPECTED_TYPED_FAILURES,
        "unattempted": 0,
    }:
        raise ValueError("V26 partial-source immutable union denominator drifted")
    units = union.get("units")
    if type(units) is not list or len(units) != EXPECTED_PLANNED:
        raise ValueError("V26 partial-source immutable union units drifted")
    return union


def _selected_by_ordinal(
    *,
    partial_manifest: Mapping[str, Any],
    final_receipt: Mapping[str, Any],
) -> dict[int, dict[str, Any]]:
    complete_by_id = {
        str(item["planned_unit_id_sha256"]): dict(item)
        for item in partial_manifest["complete_units"]
    }
    selected: dict[int, dict[str, Any]] = {}
    for member in final_receipt["selected_members"]:
        row = dict(member)
        ordinal = row.get("revised_plan_ordinal")
        planned_id = _require_sha256(
            row.get("planned_unit_id_sha256"), "V26 partial-source final selected id"
        )
        unit_hash = _require_sha256(
            row.get("unit_file_sha256"), "V26 partial-source final selected unit file"
        )
        if type(ordinal) is not int or ordinal in selected or planned_id not in complete_by_id:
            raise ValueError("V26 partial-source final selected membership drifted")
        expected = complete_by_id[planned_id]
        if (
            expected["revised_plan_ordinal"] != ordinal
            or expected["unit_file_sha256"] != unit_hash
        ):
            raise ValueError("V26 partial-source final selected identity/hash drifted")
        selected[ordinal] = expected
    if len(selected) != EXPECTED_TRAINABLE:
        raise ValueError("V26 partial-source final selected count drifted")
    if set(selected) != {
        int(item["revised_plan_ordinal"]) for item in partial_manifest["complete_units"]
    }:
        raise ValueError("V26 partial-source final selected set is not all complete units")
    return selected


def _collect_complete_units(
    *,
    union: Mapping[str, Any],
    selected_by_ordinal: Mapping[int, Mapping[str, Any]],
    expected_count: int = EXPECTED_TRAINABLE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load only the selected atomic unit records and cross-bind their bytes."""

    parent_root = _source_root(union.get("parent_recovered_root"), "parent recovered")
    successor_root = _source_root(
        union.get("successor_acquisition_root"), "successor acquisition"
    )
    for root, label in ((parent_root, "parent"), (successor_root, "successor")):
        if not (root / "units").is_dir():
            raise FileNotFoundError(f"V26 partial-source {label} unit root is missing")
    union_units = list(union["units"])
    complete: list[dict[str, Any]] = []
    source_units: list[dict[str, Any]] = []
    for ordinal in sorted(selected_by_ordinal):
        expected = dict(selected_by_ordinal[ordinal])
        union_item = dict(union_units[ordinal])
        if (
            union_item.get("revised_plan_ordinal") != ordinal
            or union_item.get("planned_unit_id_sha256") != expected["planned_unit_id_sha256"]
            or union_item.get("unit_file_sha256") != expected["unit_file_sha256"]
            or dict(union_item.get("terminal", {})).get("status") != "complete"
            or _route_projection(union_item.get("route"), ordinal=ordinal) != expected["route"]
        ):
            raise ValueError("V26 partial-source immutable union selected unit drifted")
        root = parent_root if ordinal <= 484 else successor_root
        unit_path = root / "units" / f"{ordinal:04d}.json"
        if not unit_path.is_file():
            raise FileNotFoundError(f"V26 partial-source atomic unit is missing: {unit_path}")
        unit_hash = _file_sha256(unit_path)
        if unit_hash != expected["unit_file_sha256"]:
            raise ValueError("V26 partial-source atomic unit byte hash drifted")
        unit = _json_object(unit_path, "V26 partial-source atomic unit")
        if (
            unit.get("unit_index") != ordinal
            or unit.get("planned_unit_id_sha256") != expected["planned_unit_id_sha256"]
            or dict(unit.get("terminal", {})).get("status") != "complete"
            or _route_projection(unit.get("route"), ordinal=ordinal) != expected["route"]
        ):
            raise ValueError("V26 partial-source atomic unit identity drifted")
        if type(unit.get("training_pool")) is not dict:
            raise ValueError("V26 partial-source completed atomic unit training pool is missing")
        complete.append(unit)
        source_units.append(
            {
                "revised_plan_ordinal": ordinal,
                "planned_unit_id_sha256": expected["planned_unit_id_sha256"],
                "unit_file_sha256": unit_hash,
                "source_root_role": "parent_recovered" if ordinal <= 484 else "successor_acquisition",
            }
        )
    if len(complete) != expected_count:
        raise ValueError("V26 partial-source completed unit count drifted")
    return complete, {
        "parent_recovered_root": str(parent_root),
        "successor_acquisition_root": str(successor_root),
        "selected_unit_hash_manifest_sha256": _canonical_sha256(
            {str(item["revised_plan_ordinal"]): item["unit_file_sha256"] for item in source_units}
        ),
        "source_units": source_units,
    }


def _final_population_binding(final_population: Mapping[str, Any]) -> dict[str, Any]:
    receipt = dict(final_population["receipt"])
    return {
        "receipt_sha256": final_population["sha256"],
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "planned": EXPECTED_PLANNED,
        "trainable_population": EXPECTED_TRAINABLE,
        "actual_selected": EXPECTED_TRAINABLE,
        "typed_failure_excluded": EXPECTED_TYPED_FAILURES,
    }


def _append_final_population_arrays(
    *,
    rows_path: Path,
    complete: Sequence[Mapping[str, Any]],
    source_units: Sequence[Mapping[str, Any]],
) -> None:
    with np.load(rows_path, allow_pickle=False) as archive:
        payload = {name: np.asarray(archive[name]) for name in archive.files}
    if {"planned_unit_id_sha256", "unit_file_sha256"} & set(payload):
        raise ValueError("V26 partial-source rows unexpectedly already contain final membership arrays")
    payload["planned_unit_id_sha256"] = np.asarray(
        [unit["planned_unit_id_sha256"] for unit in complete], dtype="U64"
    )
    payload["unit_file_sha256"] = np.asarray(
        [item["unit_file_sha256"] for item in source_units],
        dtype="U64",
    )
    _atomic_write_npz(rows_path, **payload)


def materialize_partial_source_training_rows(
    *,
    final_population_receipt_path: Path,
    output_dir: Path,
    camp_head: str,
) -> dict[str, Path]:
    """Build one exact partial-source V26 rows/scales artifact from ledger bytes."""

    _require_git_head(camp_head)
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError(f"V26 partial-source rows output already exists: {root}")
    final_population = load_final_training_population_receipt(final_population_receipt_path)
    final_receipt = dict(final_population["receipt"])
    partial_manifest_path = Path(str(final_receipt["partial_source_manifest"]["path"])).resolve()
    partial_manifest = validate_partial_source_training_manifest(
        _json_object(partial_manifest_path, "V26 partial-source training manifest")
    )
    immutable_union = dict(partial_manifest["immutable_union"])
    union_path = Path(str(immutable_union["path"])).resolve()
    if _file_sha256(union_path) != immutable_union["immutable_union_manifest_sha256"]:
        raise ValueError("V26 partial-source immutable union file SHA drifted")
    union = _validate_union(
        _json_object(union_path, "V26 partial-source immutable union"),
        expected_sha256=str(immutable_union["immutable_union_manifest_sha256"]),
    )
    selected = _selected_by_ordinal(
        partial_manifest=partial_manifest, final_receipt=final_receipt
    )
    complete, source_provenance = _collect_complete_units(
        union=union, selected_by_ordinal=selected
    )
    root.mkdir(parents=True, exist_ok=False)
    try:
        source_manifest_sha256 = final_population["sha256"]
        rows_sha256, _scales_sha256, _label_sha256 = (
            _AcquisitionLedger.write_training_artifacts_from_atomic_units(
                output_dir=root,
                manifest={"route_plan_sha256": source_manifest_sha256},
                complete=complete,
            )
        )
        del rows_sha256
        _append_final_population_arrays(
            rows_path=root / "training_rows.npz",
            complete=complete,
            source_units=source_provenance["source_units"],
        )
        binding = _final_population_binding(final_population)
        scale_path = root / "training_scales.json"
        scales = _json_object(scale_path, "V26 partial-source training scales")
        scales.update(
            {
                "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
                "final_training_population": binding,
                "denominator_accounting_complete": True,
                "all_planned_units_trainable": False,
            }
        )
        _atomic_write_json(scale_path, scales)
        label_path = root / "label_sidecar.json"
        label = _json_object(label_path, "V26 partial-source label sidecar")
        label.update(
            {
                "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
                "final_training_population": binding,
            }
        )
        _atomic_write_json(label_path, label)
        rows_path = root / "training_rows.npz"
        report = {
            "schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evidence_role": V26_ACQUISITION_EVIDENCE_ROLE,
            "materialization_evidence_role": MATERIALIZATION_EVIDENCE_ROLE,
            "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
            "status": "terminal_training_evidence",
            "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
            "camp_head": camp_head,
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "runner_id": MATERIALIZATION_RUNNER_ID,
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "training_rows_schema_version": V26_TRAINING_ROWS_SCHEMA_VERSION,
            "evaluation_schema": "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1",
            "outcome_fields_consumed": [],
            "holdout_accessed": False,
            "source_manifest_sha256": source_manifest_sha256,
            "training_rows_sha256": _file_sha256(rows_path),
            "training_scales_sha256": _file_sha256(scale_path),
            "label_sidecar_sha256": _file_sha256(label_path),
            "snapshot_count": EXPECTED_TRAINABLE,
            "candidate_count": EXPECTED_TRAINABLE * 8,
            "denominator": {
                "planned": EXPECTED_PLANNED,
                "complete": EXPECTED_TRAINABLE,
                "failed": EXPECTED_TYPED_FAILURES,
                "unattempted": 0,
            },
            "failure_denominator_complete": True,
            "final_training_population": binding,
            "source_provenance": {
                "immutable_union_manifest_sha256": immutable_union[
                    "immutable_union_manifest_sha256"
                ],
                **source_provenance,
            },
        }
        report_path = root / "report.json"
        _atomic_write_json(report_path, report)
        materialization_receipt = {
            "schema_version": MATERIALIZATION_SCHEMA_VERSION,
            "evidence_role": MATERIALIZATION_EVIDENCE_ROLE,
            "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
            "status": "terminal_ledger_only_rows_scales_materialized",
            "camp_head": camp_head,
            "final_training_population": binding,
            "denominator": dict(report["denominator"]),
            "source_provenance": dict(report["source_provenance"]),
            "read_scope": {
                "atomic_training_pool_atoms_read": True,
                "candidate_row_hashes_read": True,
                "trajectory_payloads_read": False,
                "outcome_payloads_read": False,
                "holdout_accessed": False,
            },
            "invocation_counts": {
                "model_forward_count": 0,
                "dp_forward_count": 0,
                "gpu_invocation_count": 0,
                "latent_generation_count": 0,
                "candidate_generation_count": 0,
                "selector_invocation_count": 0,
                "simulator_invocation_count": 0,
            },
            "output_file_sha256": {
                "training_rows.npz": _file_sha256(rows_path),
                "training_scales.json": _file_sha256(scale_path),
                "label_sidecar.json": _file_sha256(label_path),
                "report.json": _file_sha256(report_path),
            },
        }
        receipt_path = root / "materialization_receipt.json"
        _atomic_write_json(receipt_path, materialization_receipt)
        status_path = root / "run.status.json"
        _atomic_write_json(
            status_path,
            {
                "evidence_role": MATERIALIZATION_EVIDENCE_ROLE,
                "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
                "status": materialization_receipt["status"],
                "denominator": dict(report["denominator"]),
                "materialization_receipt_sha256": _file_sha256(receipt_path),
                "invocation_counts": dict(materialization_receipt["invocation_counts"]),
            },
        )
        (root / "run.exit").write_text("0\n", encoding="utf-8")
    except BaseException:
        # Preserve the new root for typed forensic inspection; never overwrite
        # a previous materialization attempt.
        raise
    return {
        "training_rows": rows_path,
        "training_scales": scale_path,
        "label_sidecar": label_path,
        "report": report_path,
        "receipt": receipt_path,
        "run_status": status_path,
        "run_exit": root / "run.exit",
    }
