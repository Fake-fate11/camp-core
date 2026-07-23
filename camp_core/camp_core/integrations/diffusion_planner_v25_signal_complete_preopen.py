from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_fresh_b2 import (
    qualify_fresh_b2_preopen,
    validate_fresh_b2_manifest_row,
    validate_fresh_b2_preopen_qualification,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)
from .diffusion_planner_v25_split import (
    validate_signal_complete_map_license,
    validate_v25_zero_overlap,
)


PREOPEN_ARTIFACT_SCHEMA_VERSION = (
    "camp_dp_v25_signal_complete_fresh_b2_preopen_artifact_v2"
)


def project_signal_complete_split_rows(
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validated = validate_signal_complete_execution_plan(plan)
    seed_namespace = _canonical_sha(
        {"split": validated["split"], "seeds": validated["seeds"]}
    )
    return [
        {
            "split": validated["split"],
            "source_family": validated["source_family"],
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
            "semantic_parameter_block_sha256": identity[
                "semantic_parameter_block_sha256"
            ],
            "seed_namespace": seed_namespace,
            "route_identity_sha256": identity["route_identity_sha256"],
            "scenario_family": identity["scenario_family"],
        }
        for identity in validated["identities"]
    ]


def project_signal_complete_license_rows(
    suite_receipt: Mapping[str, Any], *, map_artifact: Path, license_sha256: str
) -> list[dict[str, Any]]:
    if suite_receipt.get("split") not in {"fresh_b2", "fresh_b3", "fresh_b4"}:
        raise ValueError("holdout map license projection requires a Fresh suite")
    _require_sha(license_sha256, "license_sha256")
    root = map_artifact.resolve()
    rows = []
    for item in suite_receipt.get("maps", []):
        rows.append(
            {
                "map_path": str((root / item["relative_path"]).resolve()),
                "map_file_sha256": item["map_sha256"],
                "map_geometry_sha256": item["map_geometry_sha256"],
                "source_kind": "project_authored_synthetic",
                "source_reference": "CAMP repository project-authored Lanelet2 source",
                "license_spdx": "MIT",
                "license_evidence_sha256": license_sha256,
                "project_authored": True,
            }
        )
    validate_signal_complete_map_license(rows)
    return rows


def project_fresh_b2_qualification_rows(
    plan: Mapping[str, Any],
    *,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return project_holdout_qualification_rows(
        plan,
        prepared_runtime_cases=prepared_runtime_cases,
        expected_split="fresh_b2",
    )


def project_holdout_qualification_rows(
    plan: Mapping[str, Any],
    *,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
    expected_split: str,
) -> list[dict[str, Any]]:
    validated = validate_signal_complete_execution_plan(plan)
    if expected_split not in {"fresh_b2", "fresh_b3", "fresh_b4"}:
        raise ValueError("holdout qualification split drifted")
    if validated["split"] != expected_split:
        raise ValueError("holdout row projection received the wrong plan")
    runtime = _unique_by_route(
        (
            {
                "route_identity_sha256": row.get("mapped_signal_authority", {}).get(
                    "route_identity_sha256"
                ),
                "prepared": row,
            }
            for row in prepared_runtime_cases
        ),
        "static runtime source",
    )
    expected_routes = {
        identity["route_identity_sha256"] for identity in validated["identities"]
    }
    if set(runtime) != expected_routes:
        raise ValueError("Fresh B2 static source qualification denominator drifted")
    rows = []
    for index, identity in enumerate(validated["identities"]):
        route = identity["route_identity_sha256"]
        prepared = runtime[route]["prepared"]
        source = prepared.get("mapped_signal_authority")
        if (
            prepared.get("status")
            != "signal_complete_runtime_case_source_qualified"
            or prepared.get("scenario_identity_sha256")
            != identity["scenario_identity_sha256"]
            or prepared.get("model_loaded") is not False
            or prepared.get("candidate_generation_executed") is not False
            or prepared.get("fresh_b2_opened") is not False
            or prepared.get("outcome_fields_consumed") != []
            or type(source) is not dict
            or source.get("route_identity_sha256") != route
            or source.get("source_map_sha256") != identity["map_sha256"]
            or source.get("phase_remaining_available") is not False
        ):
            raise ValueError("Fresh B2 static source receipt drifted")
        speed_source = _canonical_sha(
            {
                "schema_version": "camp_dp_v25_lanelet2_speed_source_v1",
                "map_file_sha256": identity["map_sha256"],
                "route_identity_sha256": route,
                "speed_limit_kph": identity["physical_payload"]["speed_limit_kph"],
            }
        )
        row = {
            "source_family": validated["source_family"],
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "map_file_sha256": identity["map_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
            "semantic_parameter_block_sha256": identity[
                "semantic_parameter_block_sha256"
            ],
            "route_identity_sha256": route,
            "benchmark_stratum": identity["benchmark_stratum"],
            "scenario_family": identity["scenario_family"],
            "tier": identity["risk_tier"],
            "signal_source_class": "mapped_signal",
            "phase_authority_mode": identity["phase_authority_mode"],
            "source_chain": source,
            "route_length_m": identity["route_length_m"],
            "speed_source_sha256": speed_source,
            "static_signal_chain_qualified": True,
            "runtime_same_tick_signal_receipt_required": True,
            "runtime_fixed_dp_k8_support_required": True,
            "preopen_dp_forward_executed": False,
            "outcome_fields_consumed": [],
        }
        rows.append(validate_fresh_b2_manifest_row(row, index=index))
    return rows


def build_signal_complete_preopen_input_receipt(
    *,
    train_split_rows: Sequence[Mapping[str, Any]],
    calibration_plan: Mapping[str, Any],
    fresh_plan: Mapping[str, Any],
    suite_receipt: Mapping[str, Any],
    map_artifact: Path,
    license_sha256: str,
    runtime_source_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    calibration_rows = project_signal_complete_split_rows(calibration_plan)
    fresh_split_rows = project_signal_complete_split_rows(fresh_plan)
    split_rows = [dict(row) for row in train_split_rows] + calibration_rows + fresh_split_rows
    overlap = validate_v25_zero_overlap(split_rows)
    license_rows = project_signal_complete_license_rows(
        suite_receipt,
        map_artifact=map_artifact,
        license_sha256=license_sha256,
    )
    fresh_rows = project_fresh_b2_qualification_rows(
        fresh_plan,
        prepared_runtime_cases=runtime_source_receipts,
    )
    return {
        "schema_version": "camp_dp_v25_signal_complete_preopen_inputs_v2",
        "status": "outcome_blind_preopen_inputs_materialized",
        "split_rows": split_rows,
        "zero_overlap_receipt": overlap,
        "map_license_rows": license_rows,
        "fresh_rows": fresh_rows,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def freeze_signal_complete_preopen_artifact(
    *,
    preopen_input_receipt: Mapping[str, Any],
    frozen_root_bindings: Mapping[str, str],
    calibration_contract: Mapping[str, Any],
    calibration_contract_root_sha256: str,
    power_pilot_receipt: Mapping[str, Any],
    target_effect: float | None = None,
) -> dict[str, Any]:
    """Freeze the outcome-blind rows consumed by release and execution."""

    inputs = _validate_preopen_input_receipt(preopen_input_receipt)
    qualification = qualify_fresh_b2_preopen(
        split_rows=inputs["split_rows"],
        map_license_rows=inputs["map_license_rows"],
        fresh_rows=inputs["fresh_rows"],
        frozen_root_bindings=frozen_root_bindings,
        calibration_contract=calibration_contract,
        calibration_contract_root_sha256=calibration_contract_root_sha256,
        power_pilot_receipt=power_pilot_receipt,
        target_effect=target_effect,
    )
    payload = {
        "schema_version": PREOPEN_ARTIFACT_SCHEMA_VERSION,
        "status": "passed_outcome_blind_fresh_b2_preopen_artifact",
        "preopen_inputs_sha256": _canonical_sha(inputs),
        "frozen_root_bindings": dict(qualification["frozen_root_bindings"]),
        "calibration_contract_root_sha256": calibration_contract_root_sha256,
        "qualification": qualification,
        "qualification_rows": [dict(row) for row in inputs["fresh_rows"]],
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    return validate_signal_complete_preopen_artifact(
        payload,
        preopen_input_receipt=inputs,
        calibration_contract=calibration_contract,
        power_pilot_receipt=power_pilot_receipt,
        target_effect=target_effect,
    )


def validate_signal_complete_preopen_artifact(
    value: Mapping[str, Any],
    *,
    preopen_input_receipt: Mapping[str, Any],
    calibration_contract: Mapping[str, Any],
    power_pilot_receipt: Mapping[str, Any],
    target_effect: float | None = None,
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "preopen_inputs_sha256",
        "frozen_root_bindings",
        "calibration_contract_root_sha256",
        "qualification",
        "qualification_rows",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 preopen artifact field set drifted")
    inputs = _validate_preopen_input_receipt(preopen_input_receipt)
    if (
        value.get("schema_version") != PREOPEN_ARTIFACT_SCHEMA_VERSION
        or value.get("status")
        != "passed_outcome_blind_fresh_b2_preopen_artifact"
        or value.get("preopen_inputs_sha256") != _canonical_sha(inputs)
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
        or not _strict_equal(value.get("qualification_rows"), inputs["fresh_rows"])
    ):
        raise ValueError("Fresh B2 preopen artifact authority drifted")
    expected = qualify_fresh_b2_preopen(
        split_rows=inputs["split_rows"],
        map_license_rows=inputs["map_license_rows"],
        fresh_rows=inputs["fresh_rows"],
        frozen_root_bindings=value["frozen_root_bindings"],
        calibration_contract=calibration_contract,
        calibration_contract_root_sha256=value[
            "calibration_contract_root_sha256"
        ],
        power_pilot_receipt=power_pilot_receipt,
        target_effect=target_effect,
    )
    qualification = validate_fresh_b2_preopen_qualification(
        value["qualification"]
    )
    if (
        not _strict_equal(qualification, expected)
        or not _strict_equal(
            value["frozen_root_bindings"], expected["frozen_root_bindings"]
        )
    ):
        raise ValueError("Fresh B2 preopen qualification reconstruction drifted")
    return {
        "schema_version": value["schema_version"],
        "status": value["status"],
        "preopen_inputs_sha256": value["preopen_inputs_sha256"],
        "frozen_root_bindings": dict(value["frozen_root_bindings"]),
        "calibration_contract_root_sha256": value[
            "calibration_contract_root_sha256"
        ],
        "qualification": qualification,
        "qualification_rows": [dict(row) for row in value["qualification_rows"]],
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _validate_preopen_input_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "split_rows",
        "zero_overlap_receipt",
        "map_license_rows",
        "fresh_rows",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 preopen input receipt field set drifted")
    if (
        value.get("schema_version")
        != "camp_dp_v25_signal_complete_preopen_inputs_v2"
        or value.get("status") != "outcome_blind_preopen_inputs_materialized"
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
        or type(value.get("split_rows")) is not list
        or type(value.get("map_license_rows")) is not list
        or type(value.get("fresh_rows")) is not list
    ):
        raise ValueError("Fresh B2 preopen input receipt authority drifted")
    result = {
        "schema_version": value["schema_version"],
        "status": value["status"],
        "split_rows": [dict(row) for row in value["split_rows"]],
        "zero_overlap_receipt": dict(value["zero_overlap_receipt"]),
        "map_license_rows": [dict(row) for row in value["map_license_rows"]],
        "fresh_rows": [
            validate_fresh_b2_manifest_row(row, index=index)
            for index, row in enumerate(value["fresh_rows"])
        ],
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    expected_overlap = validate_v25_zero_overlap(result["split_rows"])
    if not _strict_equal(result["zero_overlap_receipt"], expected_overlap):
        raise ValueError("Fresh B2 preopen zero-overlap receipt drifted")
    validate_signal_complete_map_license(result["map_license_rows"])
    return result


def _unique_by_route(
    values: Sequence[Mapping[str, Any]], label: str
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in values:
        if type(row) is not dict:
            raise ValueError(f"{label} row must be a native mapping")
        route = row.get("route_identity_sha256")
        _require_sha(route, f"{label}.route_identity_sha256")
        if route in result:
            raise ValueError(f"{label} route repeated")
        result[route] = dict(row)
    return result


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


def _require_sha(value: Any, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")


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
