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
from typing import Any, Iterable, Mapping, Sequence

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
FINAL_TRAINING_POPULATION_SCHEMA_VERSION = (
    "camp_dp_v26_six_family_partial_source_final_training_population_v1"
)
FINAL_TRAINING_POPULATION_EVIDENCE_ROLE = (
    "development_nonholdout_six_family_partial_source_final_training_population"
)

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
            "future_rows_scales_weights_identity_source": "final_training_population_receipt",
            "final_population_receipt_required_for_final_rows_scales_weights": True,
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
            "denominator_accounting_complete": True,
            "all_planned_units_trainable": False,
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
    current_population_consumer_contract = type(contract) is dict and (
        contract.get("future_rows_scales_weights_identity_source")
        == "final_training_population_receipt"
        and contract.get("final_population_receipt_required_for_final_rows_scales_weights")
        is True
    )
    legacy_population_consumer_contract = type(contract) is dict and (
        contract.get("future_rows_scales_weights_identity_source") == "complete_units"
        and "final_population_receipt_required_for_final_rows_scales_weights" not in contract
    )
    if (
        type(contract) is not dict
        or contract.get("training_source_schema_version") != V26_TRAINING_SOURCE_SCHEMA_VERSION
        or contract.get("generator_topology") != v26_generator_topology()
        or contract.get("allowed_unit_identity_source") != "complete_units"
        or contract.get("only_manifest_complete_identities") is not True
        or contract.get("typed_failure_identities_permitted") is not False
        or contract.get("v25_training_rows_permitted") is not False
        or contract.get("future_training_receipt_artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
        or not (current_population_consumer_contract or legacy_population_consumer_contract)
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
    current_disclosure_semantics = type(disclosure) is dict and (
        disclosure.get("denominator_accounting_complete") is True
        and disclosure.get("all_planned_units_trainable") is False
        and "full_denominator_complete" not in disclosure
    )
    legacy_disclosure_semantics = type(disclosure) is dict and (
        disclosure.get("full_denominator_complete") is False
        and "denominator_accounting_complete" not in disclosure
        and "all_planned_units_trainable" not in disclosure
    )
    if (
        type(disclosure) is not dict
        or disclosure.get("kashi_missing_authoritative_speed_metadata_excluded") != 153
        or disclosure.get("other_terminal_typed_failures_excluded") != 7
        or not (current_disclosure_semantics or legacy_disclosure_semantics)
        or disclosure.get("imputation_or_route_substitution_permitted") is not False
        or disclosure.get("unseen_family_generalization_claim_permitted") is not False
    ):
        raise ValueError("V26 partial-source disclosure contract drifted")
    return manifest


def validate_training_identity_subset(
    manifest: Mapping[str, Any], candidate_unit_identities: Iterable[str]
) -> int:
    """Validate a shard/stream subset without authorizing a final population."""

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


def _final_population_members(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "revised_plan_ordinal": int(item["revised_plan_ordinal"]),
            "planned_unit_id_sha256": str(item["planned_unit_id_sha256"]),
            "unit_file_sha256": str(item["unit_file_sha256"]),
        }
        for item in manifest["complete_units"]
    ]


def _population_coverage(manifest: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "family": ("family_id",),
        "corridor": ("corridor_id",),
        "source": ("source_artifact_sha256",),
        "source_event_stratum": ("source_artifact_sha256", "event_manifest_sha256"),
    }
    output: dict[str, list[dict[str, Any]]] = {}
    for name, route_fields in fields.items():
        counts: Counter[tuple[str, ...]] = Counter()
        for item in manifest["complete_units"]:
            route = dict(item["route"])
            counts[tuple(str(route[field]) for field in route_fields)] += 1
        rows: list[dict[str, Any]] = []
        for key in sorted(counts):
            row = {field: value for field, value in zip(route_fields, key)}
            row["selected_complete_count"] = int(counts[key])
            rows.append(row)
        output[name] = rows
    if (
        len(output["family"]) != EXPECTED_FAMILY_COUNT
        or len(output["corridor"]) != EXPECTED_CORRIDOR_COUNT
        or any(row["selected_complete_count"] < 1 for row in output["source_event_stratum"])
    ):
        raise ValueError("V26 partial-source final population coverage drifted")
    return {
        "family": output["family"],
        "corridor": output["corridor"],
        "source": output["source"],
        "source_event_stratum": output["source_event_stratum"],
        "counts": {
            "family_count": len(output["family"]),
            "corridor_count": len(output["corridor"]),
            "source_count": len(output["source"]),
            "source_event_stratum_count": len(output["source_event_stratum"]),
        },
    }


def _normalize_population_shards(
    *,
    shards: Sequence[Mapping[str, Any]] | None,
    expected_members: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    expected_by_id = {
        str(item["planned_unit_id_sha256"]): str(item["unit_file_sha256"])
        for item in expected_members
    }
    if shards is None:
        shards = [
            {
                "shard_id": "all_complete_planned_ids",
                "members": [
                    {
                        "planned_unit_id_sha256": item["planned_unit_id_sha256"],
                        "unit_file_sha256": item["unit_file_sha256"],
                    }
                    for item in expected_members
                ],
            }
        ]
    if type(shards) not in {list, tuple} or not shards:
        raise ValueError("V26 partial-source final population shards are missing")
    seen_ids: set[str] = set()
    shard_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for shard in shards:
        if type(shard) is not dict or set(shard) != {"shard_id", "members"}:
            raise ValueError("V26 partial-source final population shard schema drifted")
        shard_id = shard.get("shard_id")
        members = shard.get("members")
        if type(shard_id) is not str or not shard_id or shard_id in shard_ids:
            raise ValueError("V26 partial-source final population shard identity drifted")
        if type(members) is not list or not members:
            raise ValueError("V26 partial-source final population shard is empty")
        shard_ids.add(shard_id)
        normalized_members: list[dict[str, str]] = []
        for member in members:
            if type(member) is not dict or set(member) != {
                "planned_unit_id_sha256",
                "unit_file_sha256",
            }:
                raise ValueError("V26 partial-source final population member schema drifted")
            planned_id = _require_sha256(
                member.get("planned_unit_id_sha256"), "V26 final population planned unit"
            )
            unit_hash = _require_sha256(
                member.get("unit_file_sha256"), "V26 final population unit file"
            )
            if planned_id not in expected_by_id:
                raise ValueError("V26 partial-source final population has an extra identity")
            if expected_by_id[planned_id] != unit_hash:
                raise ValueError("V26 partial-source final population unit-file SHA mismatch")
            if planned_id in seen_ids:
                raise ValueError("V26 partial-source final population has a duplicate identity")
            seen_ids.add(planned_id)
            normalized_members.append(
                {
                    "planned_unit_id_sha256": planned_id,
                    "unit_file_sha256": unit_hash,
                }
            )
        normalized.append({"shard_id": shard_id, "members": normalized_members})
    if seen_ids != set(expected_by_id):
        raise ValueError("V26 partial-source final population shard union has missing identities")
    return normalized


def build_final_training_population_receipt(
    *,
    partial_source_manifest_path: Path,
    shards: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Close the final 1623-ID training population without reading row payloads."""

    manifest_path = Path(partial_source_manifest_path).resolve()
    manifest = validate_partial_source_training_manifest(
        _json_object(manifest_path, "V26 partial-source training manifest")
    )
    members = _final_population_members(manifest)
    if len(members) != EXPECTED_TRAINABLE:
        raise ValueError("V26 partial-source final population count drifted")
    shards_value = _normalize_population_shards(shards=shards, expected_members=members)
    coverage = _population_coverage(manifest)
    receipt = {
        "schema_version": FINAL_TRAINING_POPULATION_SCHEMA_VERSION,
        "evidence_role": FINAL_TRAINING_POPULATION_EVIDENCE_ROLE,
        "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
        "partial_source_manifest": {
            "path": str(manifest_path),
            "sha256": _file_sha256(manifest_path),
            "schema_version": manifest["schema_version"],
            "evidence_role": manifest["evidence_role"],
            "artifact_role": manifest["artifact_role"],
        },
        "fixed_dp_head": manifest["fixed_dp_head"],
        "split": manifest["split"],
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "denominator": {
            "planned": EXPECTED_PLANNED,
            "trainable_population": EXPECTED_TRAINABLE,
            "actual_selected": EXPECTED_TRAINABLE,
            "typed_failure_excluded": EXPECTED_TYPED_FAILURES,
            "unattempted": 0,
        },
        "population_semantics": {
            "denominator_accounting_complete": True,
            "all_planned_units_trainable": False,
            "final_population_is_all_complete_planned_ids": True,
            "temporary_sample_population_permitted": False,
        },
        "selected_members": members,
        "shards": shards_value,
        "coverage": coverage,
        "consumer_contract": {
            "rows_scales_weights_require_final_population_receipt": True,
            "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
            "expected_actual_selected": EXPECTED_TRAINABLE,
            "exact_unit_file_sha256_binding_required": True,
            "v25_training_rows_permitted": False,
        },
        "read_scope": {
            "identity_and_terminal_fields_only": True,
            "candidate_payloads_read": False,
            "label_payloads_read": False,
            "trajectory_payloads_read": False,
            "outcome_payloads_read": False,
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
    }
    return validate_final_training_population_receipt(receipt)


def validate_final_training_population_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one exact, nonsecret final-population receipt."""

    receipt = dict(value)
    if (
        receipt.get("schema_version") != FINAL_TRAINING_POPULATION_SCHEMA_VERSION
        or receipt.get("evidence_role") != FINAL_TRAINING_POPULATION_EVIDENCE_ROLE
        or receipt.get("artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
        or receipt.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or receipt.get("split") != "development_nonholdout"
        or receipt.get("holdout_accessed") is not False
        or receipt.get("outcome_fields_consumed") != []
    ):
        raise ValueError("V26 partial-source final population receipt contract drifted")
    source = receipt.get("partial_source_manifest")
    if (
        type(source) is not dict
        or source.get("evidence_role") != PARTIAL_SOURCE_EVIDENCE_ROLE
        or source.get("artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
    ):
        raise ValueError("V26 partial-source final population manifest binding drifted")
    _require_sha256(source.get("sha256"), "V26 partial-source final population manifest")
    if type(source.get("path")) is not str or not source["path"]:
        raise ValueError("V26 partial-source final population manifest path drifted")
    if receipt.get("denominator") != {
        "planned": EXPECTED_PLANNED,
        "trainable_population": EXPECTED_TRAINABLE,
        "actual_selected": EXPECTED_TRAINABLE,
        "typed_failure_excluded": EXPECTED_TYPED_FAILURES,
        "unattempted": 0,
    }:
        raise ValueError("V26 partial-source final population denominator drifted")
    if receipt.get("population_semantics") != {
        "denominator_accounting_complete": True,
        "all_planned_units_trainable": False,
        "final_population_is_all_complete_planned_ids": True,
        "temporary_sample_population_permitted": False,
    }:
        raise ValueError("V26 partial-source final population semantics drifted")
    contract = receipt.get("consumer_contract")
    if (
        type(contract) is not dict
        or contract.get("rows_scales_weights_require_final_population_receipt") is not True
        or contract.get("artifact_role") != PARTIAL_SOURCE_ARTIFACT_ROLE
        or contract.get("expected_actual_selected") != EXPECTED_TRAINABLE
        or contract.get("exact_unit_file_sha256_binding_required") is not True
        or contract.get("v25_training_rows_permitted") is not False
    ):
        raise ValueError("V26 partial-source final population consumer contract drifted")
    members = receipt.get("selected_members")
    if type(members) is not list or len(members) != EXPECTED_TRAINABLE:
        raise ValueError("V26 partial-source final population members drifted")
    selected_by_id: dict[str, str] = {}
    for member in members:
        if type(member) is not dict or set(member) != {
            "revised_plan_ordinal",
            "planned_unit_id_sha256",
            "unit_file_sha256",
        }:
            raise ValueError("V26 partial-source final population member schema drifted")
        if type(member.get("revised_plan_ordinal")) is not int:
            raise ValueError("V26 partial-source final population member ordinal drifted")
        planned_id = _require_sha256(
            member.get("planned_unit_id_sha256"), "V26 final population selected id"
        )
        if planned_id in selected_by_id:
            raise ValueError("V26 partial-source final population receipt has duplicate identities")
        selected_by_id[planned_id] = _require_sha256(
            member.get("unit_file_sha256"), "V26 final population selected unit file"
        )
    shards = receipt.get("shards")
    if type(shards) is not list or not shards:
        raise ValueError("V26 partial-source final population receipt shards drifted")
    normalized = _normalize_population_shards(shards=shards, expected_members=members)
    if normalized != shards:
        raise ValueError("V26 partial-source final population shard serialization drifted")
    coverage = receipt.get("coverage")
    if (
        type(coverage) is not dict
        or type(coverage.get("counts")) is not dict
        or coverage["counts"].get("family_count") != EXPECTED_FAMILY_COUNT
        or coverage["counts"].get("corridor_count") != EXPECTED_CORRIDOR_COUNT
        or any(
            row.get("selected_complete_count", 0) < 1
            for row in coverage.get("source_event_stratum", [])
            if type(row) is dict
        )
    ):
        raise ValueError("V26 partial-source final population coverage receipt drifted")
    scope = receipt.get("read_scope")
    if scope != {
        "identity_and_terminal_fields_only": True,
        "candidate_payloads_read": False,
        "label_payloads_read": False,
        "trajectory_payloads_read": False,
        "outcome_payloads_read": False,
    }:
        raise ValueError("V26 partial-source final population read scope drifted")
    calls = receipt.get("invocation_counts")
    if type(calls) is not dict or any(value != 0 for value in calls.values()):
        raise ValueError("V26 partial-source final population invocation count drifted")
    return receipt


def load_final_training_population_receipt(path: Path) -> dict[str, Any]:
    """Load and cross-bind a final population receipt to its partial manifest."""

    receipt_path = Path(path).resolve()
    receipt = validate_final_training_population_receipt(
        _json_object(receipt_path, "V26 final training population receipt")
    )
    source = dict(receipt["partial_source_manifest"])
    manifest_path = Path(str(source["path"])).resolve()
    if _file_sha256(manifest_path) != source["sha256"]:
        raise ValueError("V26 partial-source final population manifest file SHA drifted")
    manifest = validate_partial_source_training_manifest(
        _json_object(manifest_path, "V26 final population partial manifest")
    )
    expected_members = _final_population_members(manifest)
    expected_by_id = {
        item["planned_unit_id_sha256"]: item["unit_file_sha256"] for item in expected_members
    }
    actual_by_id = {
        item["planned_unit_id_sha256"]: item["unit_file_sha256"]
        for item in receipt["selected_members"]
    }
    if actual_by_id != expected_by_id:
        raise ValueError("V26 partial-source final population does not exactly bind manifest complete IDs")
    return {
        "path": str(receipt_path),
        "sha256": _file_sha256(receipt_path),
        "receipt": receipt,
    }


def validate_final_training_population_source(
    final_population: Mapping[str, Any],
    *,
    planned_unit_identities: Iterable[str],
    unit_file_hashes: Iterable[str],
) -> int:
    """Require final rows/scales/weights to cover the full receipt exactly once."""

    receipt_value = final_population.get("receipt", final_population)
    if type(receipt_value) is not dict:
        raise ValueError("V26 partial-source final population source receipt is invalid")
    receipt = validate_final_training_population_receipt(receipt_value)
    planned = list(planned_unit_identities)
    hashes = list(unit_file_hashes)
    if len(planned) != EXPECTED_TRAINABLE or len(hashes) != EXPECTED_TRAINABLE:
        raise ValueError("V26 partial-source final consumer has a missing population member")
    expected = {
        str(item["planned_unit_id_sha256"]): str(item["unit_file_sha256"])
        for item in receipt["selected_members"]
    }
    observed: dict[str, str] = {}
    for planned_id, unit_hash in zip(planned, hashes):
        planned_id = _require_sha256(planned_id, "V26 final consumer planned unit")
        unit_hash = _require_sha256(unit_hash, "V26 final consumer unit file")
        if planned_id in observed:
            raise ValueError("V26 partial-source final consumer has duplicate identities")
        if planned_id not in expected:
            raise ValueError("V26 partial-source final consumer has an extra identity")
        if expected[planned_id] != unit_hash:
            raise ValueError("V26 partial-source final consumer unit-file SHA mismatch")
        observed[planned_id] = unit_hash
    if observed != expected:
        raise ValueError("V26 partial-source final consumer does not cover the full population")
    return EXPECTED_TRAINABLE


def materialize_final_training_population_receipt(
    *,
    partial_source_manifest_path: Path,
    output_dir: Path,
    camp_head: str,
    shards: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Path]:
    """Write a nonsecret receipt closing the final all-complete training population."""

    _require_git_head(camp_head, "V26 final population CAMP head")
    root = Path(output_dir).resolve()
    if root.exists():
        raise FileExistsError(f"V26 final population output already exists: {root}")
    receipt = build_final_training_population_receipt(
        partial_source_manifest_path=partial_source_manifest_path, shards=shards
    )
    root.mkdir(parents=True, exist_ok=False)
    receipt_path = root / "final_training_population_receipt.json"
    _atomic_write_json(receipt_path, receipt)
    status_path = root / "run.status.json"
    _atomic_write_json(
        status_path,
        {
            "evidence_role": FINAL_TRAINING_POPULATION_EVIDENCE_ROLE,
            "artifact_role": PARTIAL_SOURCE_ARTIFACT_ROLE,
            "status": "terminal_identity_only_final_population_closed",
            "camp_head": camp_head,
            "final_training_population_receipt_sha256": _file_sha256(receipt_path),
            "denominator": dict(receipt["denominator"]),
            "invocation_counts": dict(receipt["invocation_counts"]),
        },
    )
    exit_path = root / "run.exit"
    exit_path.write_text("0\n", encoding="utf-8")
    return {"receipt": receipt_path, "run_status": status_path, "run_exit": exit_path}


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
