"""Identity-only V26 partial-source training-corpus manifest.

This module reads only the immutable Stage 8b union manifest's route identities
and terminal fields.  It deliberately never opens candidate, label, trajectory,
or outcome payloads.  The resulting manifest is the exclusive membership
contract for a six-family *partial-source* training corpus: completed units are
eligible, and every typed failure remains explicitly excluded.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (
    FROZEN_FIXED_DP_HEAD,
)
from camp_core.integrations.diffusion_planner_v26_diversified_successor import (
    UNION_EVIDENCE_ROLE,
    UNION_MANIFEST_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    v26_generator_topology,
)


PARTIAL_SOURCE_MANIFEST_SCHEMA_VERSION = (
    "camp_dp_v26_six_family_partial_source_training_manifest_v1"
)
PARTIAL_SOURCE_COVERAGE_SCHEMA_VERSION = (
    "camp_dp_v26_six_family_partial_source_coverage_v1"
)
PARTIAL_SOURCE_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v26_six_family_partial_source_manifest_receipt_v1"
)
PARTIAL_SOURCE_EVIDENCE_ROLE = (
    "development_nonholdout_six_family_partial_source_training_manifest"
)
PARTIAL_SOURCE_COVERAGE_EVIDENCE_ROLE = (
    "development_nonholdout_six_family_partial_source_coverage"
)
PARTIAL_SOURCE_RECEIPT_EVIDENCE_ROLE = (
    "development_nonholdout_six_family_partial_source_manifest_materialization"
)
PARTIAL_SOURCE_ARTIFACT_ROLE = "partial-source"

EXPECTED_PLANNED = 1783
EXPECTED_TRAINABLE = 1623
EXPECTED_TYPED_FAILURES = 160
EXPECTED_FAMILY_COUNT = 6
EXPECTED_CORRIDOR_COUNT = 155
KASHI_SPEED_METADATA_ORDINALS = frozenset(
    tuple(range(547, 619)) + tuple(range(777, 858))
)

_TERMINAL_STATUSES = frozenset({"complete", "typed_failure"})
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


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _require_git_head(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError(f"{label} must be a Git SHA1")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a Git SHA1") from exc
    return value


def _json_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _terminal_projection(value: Any, *, ordinal: int) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"V26 partial-source unit {ordinal} terminal is missing")
    terminal = dict(value)
    status = terminal.get("status")
    failure_class = terminal.get("failure_class")
    failure_reason = terminal.get("failure_reason")
    if status not in _TERMINAL_STATUSES:
        raise ValueError(f"V26 partial-source unit {ordinal} terminal must be final")
    if status == "complete":
        if failure_class is not None or failure_reason is not None:
            raise ValueError(f"V26 partial-source unit {ordinal} complete failure fields drifted")
    elif type(failure_class) is not str or not failure_class or type(failure_reason) is not str or not failure_reason:
        raise ValueError(f"V26 partial-source unit {ordinal} typed failure fields drifted")
    return {
        "status": status,
        "failure_class": failure_class,
        "failure_reason": failure_reason,
    }


def _route_projection(value: Any, *, ordinal: int) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"V26 partial-source unit {ordinal} route is missing")
    route = dict(value)
    if type(route.get("family_id")) is not str or not route["family_id"]:
        raise ValueError(f"V26 partial-source unit {ordinal} family identity drifted")
    if type(route.get("route_id")) is not str or not route["route_id"]:
        raise ValueError(f"V26 partial-source unit {ordinal} route identity drifted")
    if type(route.get("parent_ordinal")) is not int:
        raise ValueError(f"V26 partial-source unit {ordinal} parent ordinal drifted")
    if type(route.get("scenario_seed")) is not int:
        raise ValueError(f"V26 partial-source unit {ordinal} seed identity drifted")
    for field in (
        "corridor_id",
        "route_identity_sha256",
        "map_sha256",
        "source_artifact_sha256",
        "event_manifest_sha256",
    ):
        _require_sha256(route.get(field), f"V26 partial-source unit {ordinal} {field}")
    return {field: route[field] for field in _ROUTE_FIELDS}


def _unit_projection(value: Any, *, ordinal: int) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"V26 partial-source union unit {ordinal} must be a mapping")
    unit = dict(value)
    if unit.get("revised_plan_ordinal") != ordinal:
        raise ValueError("V26 partial-source union ordinal membership drifted")
    return {
        "revised_plan_ordinal": ordinal,
        "unit_file_sha256": _require_sha256(
            unit.get("unit_file_sha256"), "V26 partial-source unit file"
        ),
        "planned_unit_id_sha256": _require_sha256(
            unit.get("planned_unit_id_sha256"), "V26 partial-source planned unit"
        ),
        "route": _route_projection(unit.get("route"), ordinal=ordinal),
        "terminal": _terminal_projection(unit.get("terminal"), ordinal=ordinal),
    }


def _read_verified_union(immutable_union_manifest_path: Path) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    path = Path(immutable_union_manifest_path).resolve()
    union = _json_object(path, "V26 immutable union manifest")
    if (
        union.get("schema_version") != UNION_MANIFEST_SCHEMA_VERSION
        or union.get("evidence_role") != UNION_EVIDENCE_ROLE
        or union.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or union.get("split") != "development_nonholdout"
        or union.get("holdout_accessed") is not False
        or union.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V26 partial-source immutable union contract drifted")
    membership = union.get("membership")
    if (
        type(membership) is not dict
        or membership.get("required_revised_plan_ordinal_range") != [0, EXPECTED_PLANNED - 1]
        or membership.get("exactly_once") is not True
        or membership.get("route_ids_unique") is not True
    ):
        raise ValueError("V26 partial-source immutable union membership contract drifted")
    units = union.get("units")
    if type(units) is not list or len(units) != EXPECTED_PLANNED:
        raise ValueError("V26 partial-source immutable union unit count drifted")
    projected = [_unit_projection(item, ordinal=index) for index, item in enumerate(units)]
    route_ids = {str(item["route"]["route_id"]) for item in projected}
    if len(route_ids) != EXPECTED_PLANNED:
        raise ValueError("V26 partial-source immutable union route identity is not unique")
    denominator = Counter(item["terminal"]["status"] for item in projected)
    actual_denominator = {
        "planned": EXPECTED_PLANNED,
        "complete": int(denominator["complete"]),
        "failed": int(denominator["typed_failure"]),
        "unattempted": 0,
    }
    if union.get("denominator") != actual_denominator or actual_denominator != {
        "planned": EXPECTED_PLANNED,
        "complete": EXPECTED_TRAINABLE,
        "failed": EXPECTED_TYPED_FAILURES,
        "unattempted": 0,
    }:
        raise ValueError("V26 partial-source immutable union denominator drifted")
    if len({item["route"]["family_id"] for item in projected}) != EXPECTED_FAMILY_COUNT:
        raise ValueError("V26 partial-source family inventory drifted")
    if len({item["route"]["corridor_id"] for item in projected}) != EXPECTED_CORRIDOR_COUNT:
        raise ValueError("V26 partial-source corridor inventory drifted")
    return path, union, projected


def _exclusion_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    ordinal = int(item["revised_plan_ordinal"])
    terminal = dict(item["terminal"])
    if ordinal in KASHI_SPEED_METADATA_ORDINALS:
        exclusion_class = "missing_authoritative_speed_metadata"
        exclusion_reason = (
            "authoritative positive speed metadata is unavailable; imputation is forbidden"
        )
    else:
        exclusion_class = "retained_terminal_typed_failure"
        exclusion_reason = "immutable union terminal typed failure remains excluded from training"
    return {
        "revised_plan_ordinal": ordinal,
        "planned_unit_id_sha256": item["planned_unit_id_sha256"],
        "unit_file_sha256": item["unit_file_sha256"],
        "route": dict(item["route"]),
        "terminal_failure_class_observed": terminal["failure_class"],
        "terminal_failure_reason_observed": terminal["failure_reason"],
        "partial_source_exclusion_class": exclusion_class,
        "partial_source_exclusion_reason": exclusion_reason,
    }


def _group_coverage(items: Iterable[Mapping[str, Any]], *, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for item in items:
        route = dict(item["route"])
        key = tuple(str(route[field]) for field in fields)
        counts[key][str(item["terminal"]["status"])] += 1
    result: list[dict[str, Any]] = []
    for key in sorted(counts):
        count = counts[key]
        row = {field: value for field, value in zip(fields, key)}
        row.update(
            {
                "planned_count": int(count["complete"] + count["typed_failure"]),
                "retained_complete_count": int(count["complete"]),
                "typed_failure_count": int(count["typed_failure"]),
            }
        )
        result.append(row)
    return result


def _coverage_manifest(
    items: list[dict[str, Any]], *, immutable_union_path: Path, immutable_union_sha256: str
) -> dict[str, Any]:
    families = _group_coverage(items, fields=("family_id",))
    corridors = _group_coverage(items, fields=("corridor_id",))
    sources = _group_coverage(items, fields=("source_artifact_sha256",))
    event_strata = _group_coverage(
        items, fields=("source_artifact_sha256", "event_manifest_sha256")
    )
    empty_key_strata = [
        row
        for row in event_strata
        if int(row["retained_complete_count"]) == 0
    ]
    if empty_key_strata:
        raise ValueError("V26 partial-source key event stratum has zero retained complete units")
    return {
        "schema_version": PARTIAL_SOURCE_COVERAGE_SCHEMA_VERSION,
        "evidence_role": PARTIAL_SOURCE_COVERAGE_EVIDENCE_ROLE,
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "immutable_union": {
            "path": str(immutable_union_path),
            "immutable_union_manifest_sha256": immutable_union_sha256,
        },
        "denominator": {
            "planned": EXPECTED_PLANNED,
            "retained_complete": EXPECTED_TRAINABLE,
            "typed_failure": EXPECTED_TYPED_FAILURES,
            "unattempted": 0,
        },
        "coverage": {
            "family": families,
            "corridor": corridors,
            "source": sources,
            "source_event_stratum": event_strata,
        },
        "source_coverage_accounting": {
            "planned_family_count": len(families),
            "planned_corridor_count": len(corridors),
            "planned_source_count": len(sources),
            "preplanned_key_event_stratum_count": len(event_strata),
            "all_key_event_strata_have_retained_complete": True,
            "empty_key_event_strata": [],
        },
        "read_scope": {
            "identity_and_terminal_fields_only": True,
            "candidate_payloads_read": False,
            "label_payloads_read": False,
            "trajectory_payloads_read": False,
            "outcome_payloads_read": False,
        },
    }


def build_partial_source_training_manifest(
    *, immutable_union_manifest_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read identity-only union data and derive the exact partial-source subset."""

    path, _union, items = _read_verified_union(immutable_union_manifest_path)
    failures = [item for item in items if item["terminal"]["status"] == "typed_failure"]
    completed = [item for item in items if item["terminal"]["status"] == "complete"]
    failure_ordinals = {int(item["revised_plan_ordinal"]) for item in failures}
    if not KASHI_SPEED_METADATA_ORDINALS.issubset(failure_ordinals):
        raise ValueError("V26 partial-source Kashi speed-metadata failures drifted")
    if len(KASHI_SPEED_METADATA_ORDINALS) != 153:
        raise AssertionError("V26 partial-source Kashi exclusion cardinality drifted")
    non_kashi_failures = failure_ordinals - KASHI_SPEED_METADATA_ORDINALS
    if len(non_kashi_failures) != 7 or 1276 not in non_kashi_failures:
        raise ValueError("V26 partial-source retained typed-failure identity drifted")
    kashi_families = {
        str(item["route"]["family_id"])
        for item in failures
        if int(item["revised_plan_ordinal"]) in KASHI_SPEED_METADATA_ORDINALS
    }
    if len(kashi_families) != 1:
        raise ValueError("V26 partial-source Kashi within-family identity drifted")
    immutable_union_sha256 = _file_sha256(path)
    coverage = _coverage_manifest(
        items,
        immutable_union_path=path,
        immutable_union_sha256=immutable_union_sha256,
    )
    manifest = {
        "schema_version": PARTIAL_SOURCE_MANIFEST_SCHEMA_VERSION,
        "evidence_role": PARTIAL_SOURCE_EVIDENCE_ROLE,
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "corpus_label": "six-family partial-source training corpus",
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "immutable_union": {
            "path": str(path),
            "immutable_union_manifest_sha256": immutable_union_sha256,
            "schema_version": UNION_MANIFEST_SCHEMA_VERSION,
            "evidence_role": UNION_EVIDENCE_ROLE,
        },
        "denominator": {
            "planned": EXPECTED_PLANNED,
            "trainable_complete": EXPECTED_TRAINABLE,
            "typed_failure_excluded": EXPECTED_TYPED_FAILURES,
            "unattempted": 0,
        },
        "membership": {
            "union_membership_exactly_once": True,
            "complete_unit_identities_unique": True,
            "excluded_typed_failure_identities_unique": True,
            "full_union_family_count": EXPECTED_FAMILY_COUNT,
            "full_union_corridor_count": EXPECTED_CORRIDOR_COUNT,
        },
        "training_input_contract": {
            "training_source_schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "generator_topology": v26_generator_topology(),
            "allowed_unit_identity_source": "complete_units",
            "only_manifest_complete_identities": True,
            "typed_failure_identities_permitted": False,
            "v25_training_rows_permitted": False,
            "future_training_receipt_artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
            "future_rows_scales_weights_identity_source": "complete_units",
            "candidate_label_trajectory_outcome_payloads_read_during_manifest_build": False,
        },
        "complete_units": [
            {
                "revised_plan_ordinal": item["revised_plan_ordinal"],
                "planned_unit_id_sha256": item["planned_unit_id_sha256"],
                "unit_file_sha256": item["unit_file_sha256"],
                "route": dict(item["route"]),
            }
            for item in completed
        ],
        "excluded_typed_failures": [_exclusion_projection(item) for item in failures],
        "partial_source_disclosure": {
            "kashi_within_family_id": next(iter(kashi_families)),
            "kashi_missing_authoritative_speed_metadata_excluded": len(
                KASHI_SPEED_METADATA_ORDINALS
            ),
            "other_terminal_typed_failures_excluded": len(non_kashi_failures),
            "full_denominator_complete": False,
            "imputation_or_route_substitution_permitted": False,
            "unseen_family_generalization_claim_permitted": False,
        },
    }
    validate_partial_source_training_manifest(manifest)
    return manifest, coverage


def validate_partial_source_training_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate that a future training consumer can only select complete identities."""

    manifest = dict(value)
    if (
        manifest.get("schema_version") != PARTIAL_SOURCE_MANIFEST_SCHEMA_VERSION
        or manifest.get("evidence_role") != PARTIAL_SOURCE_EVIDENCE_ROLE
        or manifest.get("artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
        or manifest.get("corpus_label") != "six-family partial-source training corpus"
        or manifest.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or manifest.get("split") != "development_nonholdout"
        or manifest.get("holdout_accessed") is not False
        or manifest.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V26 partial-source training manifest contract drifted")
    union = manifest.get("immutable_union")
    if (
        type(union) is not dict
        or union.get("schema_version") != UNION_MANIFEST_SCHEMA_VERSION
        or union.get("evidence_role") != UNION_EVIDENCE_ROLE
    ):
        raise ValueError("V26 partial-source immutable-union binding drifted")
    _require_sha256(union.get("immutable_union_manifest_sha256"), "V26 partial-source union")
    denominator = manifest.get("denominator")
    if denominator != {
        "planned": EXPECTED_PLANNED,
        "trainable_complete": EXPECTED_TRAINABLE,
        "typed_failure_excluded": EXPECTED_TYPED_FAILURES,
        "unattempted": 0,
    }:
        raise ValueError("V26 partial-source manifest denominator drifted")
    contract = manifest.get("training_input_contract")
    if (
        type(contract) is not dict
        or contract.get("training_source_schema_version") != V26_TRAINING_SOURCE_SCHEMA_VERSION
        or contract.get("generator_topology") != v26_generator_topology()
        or contract.get("allowed_unit_identity_source") != "complete_units"
        or contract.get("only_manifest_complete_identities") is not True
        or contract.get("typed_failure_identities_permitted") is not False
        or contract.get("v25_training_rows_permitted") is not False
        or contract.get("future_training_receipt_artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
        or contract.get("future_rows_scales_weights_identity_source") != "complete_units"
        or contract.get("candidate_label_trajectory_outcome_payloads_read_during_manifest_build")
        is not False
    ):
        raise ValueError("V26 partial-source training-input contract drifted")
    complete = manifest.get("complete_units")
    excluded = manifest.get("excluded_typed_failures")
    if type(complete) is not list or type(excluded) is not list:
        raise ValueError("V26 partial-source identity lists are missing")
    if len(complete) != EXPECTED_TRAINABLE or len(excluded) != EXPECTED_TYPED_FAILURES:
        raise ValueError("V26 partial-source identity list counts drifted")
    complete_ids: set[str] = set()
    complete_ordinals: set[int] = set()
    for item in complete:
        if type(item) is not dict or type(item.get("revised_plan_ordinal")) is not int:
            raise ValueError("V26 partial-source complete identity schema drifted")
        ordinal = int(item["revised_plan_ordinal"])
        complete_ordinals.add(ordinal)
        complete_ids.add(
            _require_sha256(item.get("planned_unit_id_sha256"), "V26 partial-source complete id")
        )
        _require_sha256(item.get("unit_file_sha256"), "V26 partial-source complete unit hash")
        _route_projection(item.get("route"), ordinal=ordinal)
    excluded_ids: set[str] = set()
    excluded_ordinals: set[int] = set()
    for item in excluded:
        if type(item) is not dict or type(item.get("revised_plan_ordinal")) is not int:
            raise ValueError("V26 partial-source exclusion identity schema drifted")
        ordinal = int(item["revised_plan_ordinal"])
        excluded_ordinals.add(ordinal)
        excluded_ids.add(
            _require_sha256(item.get("planned_unit_id_sha256"), "V26 partial-source exclusion id")
        )
        _require_sha256(item.get("unit_file_sha256"), "V26 partial-source exclusion unit hash")
        _route_projection(item.get("route"), ordinal=ordinal)
        if type(item.get("partial_source_exclusion_class")) is not str:
            raise ValueError("V26 partial-source exclusion class drifted")
    if (
        len(complete_ids) != EXPECTED_TRAINABLE
        or len(excluded_ids) != EXPECTED_TYPED_FAILURES
        or complete_ids & excluded_ids
        or complete_ordinals & excluded_ordinals
        or complete_ordinals | excluded_ordinals != set(range(EXPECTED_PLANNED))
    ):
        raise ValueError("V26 partial-source exact-once identity contract drifted")
    kashi = [
        item
        for item in excluded
        if int(item["revised_plan_ordinal"]) in KASHI_SPEED_METADATA_ORDINALS
    ]
    if (
        len(kashi) != len(KASHI_SPEED_METADATA_ORDINALS)
        or any(item.get("partial_source_exclusion_class") != "missing_authoritative_speed_metadata" for item in kashi)
        or 1276 not in excluded_ordinals
    ):
        raise ValueError("V26 partial-source typed-failure disclosure drifted")
    disclosure = manifest.get("partial_source_disclosure")
    if (
        type(disclosure) is not dict
        or disclosure.get("kashi_missing_authoritative_speed_metadata_excluded") != 153
        or disclosure.get("other_terminal_typed_failures_excluded") != 7
        or disclosure.get("full_denominator_complete") is not False
        or disclosure.get("imputation_or_route_substitution_permitted") is not False
        or disclosure.get("unseen_family_generalization_claim_permitted") is not False
    ):
        raise ValueError("V26 partial-source disclosure contract drifted")
    return manifest


def validate_training_identity_subset(
    manifest: Mapping[str, Any], candidate_unit_identities: Iterable[str]
) -> int:
    """Reject any future row/scale/weight input outside manifest complete identities."""

    checked = validate_partial_source_training_manifest(manifest)
    allowed = {
        str(item["planned_unit_id_sha256"])
        for item in checked["complete_units"]
    }
    supplied = list(candidate_unit_identities)
    if not supplied or any(type(item) is not str for item in supplied):
        raise ValueError("V26 partial-source training identity input is empty or invalid")
    if len(set(supplied)) != len(supplied) or not set(supplied).issubset(allowed):
        raise ValueError("V26 partial-source training input includes a non-complete identity")
    return len(supplied)


def materialize_partial_source_training_manifest(
    *,
    immutable_union_manifest_path: Path,
    output_dir: Path,
    camp_head: str,
) -> dict[str, Path]:
    """Atomically write a new partial-source manifest root from immutable identity data."""

    _require_git_head(camp_head, "V26 partial-source CAMP head")
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError(f"V26 partial-source output already exists: {root}")
    manifest, coverage = build_partial_source_training_manifest(
        immutable_union_manifest_path=immutable_union_manifest_path
    )
    root.mkdir(parents=True, exist_ok=False)
    manifest_path = root / "partial_source_training_manifest.json"
    coverage_path = root / "coverage.json"
    _atomic_write_json(manifest_path, manifest)
    _atomic_write_json(coverage_path, coverage)
    receipt = {
        "schema_version": PARTIAL_SOURCE_RECEIPT_SCHEMA_VERSION,
        "evidence_role": PARTIAL_SOURCE_RECEIPT_EVIDENCE_ROLE,
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "status": "terminal_identity_only_manifest_materialized",
        "camp_head": camp_head,
        "immutable_union": dict(manifest["immutable_union"]),
        "denominator": dict(manifest["denominator"]),
        "output_hashes": {
            "partial_source_training_manifest_sha256": _file_sha256(manifest_path),
            "coverage_sha256": _file_sha256(coverage_path),
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
        "read_scope": dict(coverage["read_scope"]),
    }
    receipt_path = root / "receipt.json"
    _atomic_write_json(receipt_path, receipt)
    status = {
        "evidence_role": PARTIAL_SOURCE_RECEIPT_EVIDENCE_ROLE,
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "status": "terminal",
        "denominator": dict(manifest["denominator"]),
        "receipt_sha256": _file_sha256(receipt_path),
        "partial_source_training_manifest_sha256": _file_sha256(manifest_path),
        "coverage_sha256": _file_sha256(coverage_path),
    }
    status_path = root / "run.status.json"
    _atomic_write_json(status_path, status)
    exit_path = root / "run.exit"
    exit_path.write_text("0\n", encoding="utf-8")
    return {
        "manifest": manifest_path,
        "coverage": coverage_path,
        "receipt": receipt_path,
        "run_status": status_path,
        "run_exit": exit_path,
    }
