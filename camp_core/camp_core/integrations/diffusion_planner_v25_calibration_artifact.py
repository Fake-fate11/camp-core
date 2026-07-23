from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_calibration import (
    estimate_v25_noninferiority_margin_resolvability,
    freeze_v25_calibration_contract,
    validate_v25_calibration_contract,
)
from .diffusion_planner_v25_calibration_corpus import (
    validate_candidate0_calibration_corpus,
)


SCHEMA_VERSION = "camp_dp_v25_calibration_freeze_artifact_payload_v2"


def build_calibration_freeze_payload_from_corpus(
    *,
    root_bindings: Mapping[str, str],
    calibration_corpus: Mapping[str, Any],
    frozen_model_registry_sha256: str,
    training_scale_sha256: str,
    context_scaler_sha256: str,
) -> dict[str, Any]:
    """Derive the entire freeze denominator from one reviewed corpus payload."""

    corpus = validate_candidate0_calibration_corpus(calibration_corpus)
    inventory = {
        "map_count": corpus["map_count"],
        "intersection_count": corpus["intersection_count"],
        "corridor_count": corpus["corridor_count"],
        "route_count": corpus["route_count"],
        "planned_paired_run_count": corpus["planned_run_count"],
        "paired_eligible_run_count": corpus["complete_run_count"],
        "retained_failure_run_count": corpus[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_rate": corpus["paired_eligible_rate"],
    }
    return build_calibration_freeze_payload(
        root_bindings=root_bindings,
        inventory=inventory,
        candidate0_rows=corpus["candidate0_rows"],
        frozen_model_registry_sha256=frozen_model_registry_sha256,
        training_scale_sha256=training_scale_sha256,
        context_scaler_sha256=context_scaler_sha256,
    )


def build_calibration_freeze_payload(
    *,
    root_bindings: Mapping[str, str],
    inventory: Mapping[str, Any],
    candidate0_rows: Sequence[Mapping[str, Any]],
    frozen_model_registry_sha256: str,
    training_scale_sha256: str,
    context_scaler_sha256: str,
) -> dict[str, Any]:
    """Build the complete pre-Fresh calibration freeze payload."""

    rows = [dict(row) for row in candidate0_rows]
    resolvability = estimate_v25_noninferiority_margin_resolvability(rows)
    contract = freeze_v25_calibration_contract(
        root_bindings=root_bindings,
        inventory=inventory,
        noninferiority_resolvability=resolvability,
        frozen_model_registry_sha256=frozen_model_registry_sha256,
        training_scale_sha256=training_scale_sha256,
        context_scaler_sha256=context_scaler_sha256,
    )
    validated_contract = validate_v25_calibration_contract(contract)
    rows_sha = _canonical_sha(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": validated_contract["status"],
        "root_bindings": dict(root_bindings),
        "inventory": dict(inventory),
        "candidate0_row_count": len(rows),
        "candidate0_rows_sha256": rows_sha,
        "candidate0_rows": rows,
        "noninferiority_resolvability": resolvability,
        "calibration_contract": validated_contract,
        "calibration_arm": "candidate0_operational_default",
        "camp_method_outcomes_consumed": False,
        "atom_scale_changed_by_calibration": False,
        "model_parameters_changed_by_calibration": False,
        "margin_enlargement_authorized": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def validate_calibration_freeze_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("calibration freeze payload must be a native mapping")
    required = {
        "schema_version",
        "status",
        "root_bindings",
        "inventory",
        "candidate0_row_count",
        "candidate0_rows_sha256",
        "candidate0_rows",
        "noninferiority_resolvability",
        "calibration_contract",
        "calibration_arm",
        "camp_method_outcomes_consumed",
        "atom_scale_changed_by_calibration",
        "model_parameters_changed_by_calibration",
        "margin_enlargement_authorized",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if set(value) != required:
        raise ValueError("calibration freeze payload field set drifted")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("calibration freeze payload schema drifted")
    rows = value.get("candidate0_rows")
    if type(rows) is not list or value.get("candidate0_row_count") != len(rows):
        raise ValueError("calibration freeze candidate0 denominator drifted")
    if value.get("candidate0_rows_sha256") != _canonical_sha(rows):
        raise ValueError("calibration freeze candidate0 rows SHA drifted")
    expected = build_calibration_freeze_payload(
        root_bindings=value["root_bindings"],
        inventory=value["inventory"],
        candidate0_rows=rows,
        frozen_model_registry_sha256=value["calibration_contract"][
            "frozen_model_registry_sha256"
        ],
        training_scale_sha256=value["calibration_contract"][
            "training_scale_sha256"
        ],
        context_scaler_sha256=value["calibration_contract"][
            "context_scaler_sha256"
        ],
    )
    if not _strict_equal(value, expected):
        raise ValueError("calibration freeze payload differs from reconstruction")
    return expected


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
