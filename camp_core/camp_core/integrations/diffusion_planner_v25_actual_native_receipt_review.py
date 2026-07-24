from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract,
)


POOL_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_supplementary_candidate_pool_evidence_v3"
)
SUPPLEMENTARY_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_supplementary_native_receipt_v1"
)


def independent_validate_actual_native_receipt(
    value: Mapping[str, Any],
    *,
    branch: str,
    expected_ticks: int = 64,
) -> dict[str, Any]:
    """Validate the declared ABI without importing any production validator."""

    declaration = actual_native_receipt_contract()
    if branch not in declaration["branches"]:
        raise ValueError("independent actual-native branch drifted")
    branch_contract = declaration["branches"][branch]
    required = set(branch_contract["header"]["required"])
    if type(value) is not dict or set(value) != required:
        raise ValueError(f"independent {branch} header field set drifted")
    for name, kind in branch_contract["header_native_types"].items():
        _independent_kind(
            value[name],
            kind,
            declaration=declaration,
            label=f"{branch}.header.{name}",
        )
    if (
        value["schema_version"] != declaration["native_receipt_schema_version"]
        or value["status"] != "ok"
        or value["arm"]
        != ("dp" if branch.startswith("candidate0_") else "camp")
        or value["claim_authorized"] is not False
        or value["actual_native_receipt_contract_sha256"]
        != independent_contract_sha256()
        or value["runtime_annotation_compatibility"]
        != "not_required_python310_or_newer"
        or len(value["ticks"]) != expected_ticks
    ):
        raise ValueError(f"independent {branch} header value drifted")
    ticks = []
    tick_fields = set(branch_contract["tick"]["required"])
    for index, tick in enumerate(value["ticks"]):
        if type(tick) is not dict or set(tick) != tick_fields:
            raise ValueError(f"independent {branch} tick field set drifted")
        for name, kind in branch_contract["tick_native_types"].items():
            _independent_kind(
                tick[name],
                kind,
                declaration=declaration,
                label=f"{branch}.tick.{name}",
            )
        if tick["tick_index"] != index or tick["status"] != "ok":
            raise ValueError(f"independent {branch} tick sequence drifted")
        if set(tick["latency_ms"]) != set(branch_contract["latency_fields"]):
            raise ValueError(f"independent {branch} latency namespace drifted")
        _independent_tick_semantics(tick, branch=branch, index=index)
        ticks.append(dict(tick))
    if ticks[0]["input_sha256"] != value["initial_input_sha256"]:
        raise ValueError(f"independent {branch} initial input binding drifted")
    result = dict(value)
    result["ticks"] = ticks
    return result


def independent_candidate0_pool_evidence(
    primary: Mapping[str, Any],
    supplementary: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild candidate0 pool evidence without producer validators/helpers."""

    declaration = actual_native_receipt_contract()
    contract_sha = declaration["contract_sha256"]
    primary_required = set(
        declaration["branches"]["candidate0_primary"]["header"]["required"]
    )
    if (
        type(primary) is not dict
        or set(primary) != primary_required
        or primary.get("actual_native_receipt_contract_sha256") != contract_sha
        or primary.get("schema_version") != "v21_native_arm_receipt_v1"
        or primary.get("status") != "ok"
        or primary.get("arm") != "dp"
        or primary.get("claim_authorized") is not False
    ):
        raise ValueError("independent candidate0 primary ABI drifted")
    supplementary_fields = {
        "schema_version",
        "status",
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "arm",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
        "ticks",
        "claim_authorized",
        "outcome_fields_consumed",
        "actual_native_receipt_contract_sha256",
    }
    if (
        type(supplementary) is not dict
        or set(supplementary) != supplementary_fields
        or supplementary.get("schema_version") != SUPPLEMENTARY_SCHEMA_VERSION
        or supplementary.get("status") != "ok"
        or supplementary.get("arm") != "dp"
        or supplementary.get("claim_authorized") is not False
        or supplementary.get("outcome_fields_consumed") != []
        or supplementary.get("actual_native_receipt_contract_sha256")
        != contract_sha
    ):
        raise ValueError("independent candidate0 supplementary ABI drifted")
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if type(primary.get(name)) is not type(supplementary.get(name)) or (
            primary.get(name) != supplementary.get(name)
        ):
            raise ValueError(
                f"independent candidate0 header binding drifted: {name}"
            )
    primary_ticks = primary.get("ticks")
    diagnostic_ticks = supplementary.get("ticks")
    if (
        type(primary_ticks) is not list
        or type(diagnostic_ticks) is not list
        or len(primary_ticks) != 64
        or len(diagnostic_ticks) != 64
    ):
        raise ValueError("independent candidate0 tick denominator drifted")
    rows = []
    for index, (action, diagnostic) in enumerate(
        zip(primary_ticks, diagnostic_ticks, strict=True)
    ):
        _independent_primary_tick(action, index, declaration)
        _independent_supplementary_tick(diagnostic, index)
        for name in (
            "input_sha256",
            "default_output_sha256",
            "selected_trajectory_sha256",
        ):
            if action[name] != diagnostic[name]:
                raise ValueError(
                    f"independent candidate0 tick binding drifted: {name}"
                )
        if diagnostic["planning_started_ns"] < action["action_available_ns"]:
            raise ValueError(
                "independent supplementary evidence preceded action availability"
            )
        if diagnostic["receipt_projected_ns"] < diagnostic["planning_started_ns"]:
            raise ValueError("independent supplementary timestamp order drifted")
        rows.append(
            {
                "tick_index": index,
                "input_sha256": diagnostic["input_sha256"],
                "candidate_tensor_sha256": diagnostic[
                    "candidate_tensor_sha256_before"
                ],
                "candidate_row_sha256": list(
                    diagnostic["candidate_row_sha256"]
                ),
                "default_output_sha256": diagnostic["default_output_sha256"],
                "source_valid_mask": list(diagnostic["source_valid_mask"]),
                "physical_feasible_mask": list(
                    diagnostic["physical_feasible_mask"]
                ),
                "action_available_ns": action["action_available_ns"],
                "supplementary_started_ns": diagnostic["planning_started_ns"],
                "supplementary_completed_ns": diagnostic[
                    "receipt_projected_ns"
                ],
            }
        )
    return {
        "schema_version": POOL_SCHEMA_VERSION,
        "candidate_tensor_source": (
            "post_action_same_tick_same_base_forward_supplementary"
        ),
        "candidate_tensor_modified": False,
        "same_forward_claimed": False,
        "pool_evidence_affects_action": False,
        "pool_evidence_affects_rng_or_next_tick": False,
        "ticks": rows,
        "outcome_fields_consumed": [],
        "fresh_protocol_changed": False,
    }


def independent_historical_candidate0_pool_evidence(
    primary: Mapping[str, Any],
    supplementary: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the pre-ABI B3 pool without importing producer helpers."""

    if (
        type(primary) is not dict
        or primary.get("schema_version") != "v21_native_arm_receipt_v1"
        or primary.get("status") != "ok"
        or primary.get("arm") != "dp"
        or primary.get("claim_authorized") is not False
        or type(supplementary) is not dict
        or supplementary.get("schema_version") != SUPPLEMENTARY_SCHEMA_VERSION
        or supplementary.get("status") != "ok"
        or supplementary.get("arm") != "dp"
        or supplementary.get("claim_authorized") is not False
        or supplementary.get("outcome_fields_consumed") != []
    ):
        raise ValueError("independent historical candidate0 header drifted")
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if type(primary.get(name)) is not type(supplementary.get(name)) or (
            primary.get(name) != supplementary.get(name)
        ):
            raise ValueError(
                f"independent historical header binding drifted: {name}"
            )
    primary_ticks = primary.get("ticks")
    diagnostic_ticks = supplementary.get("ticks")
    if (
        type(primary_ticks) is not list
        or type(diagnostic_ticks) is not list
        or len(primary_ticks) != 64
        or len(diagnostic_ticks) != 64
    ):
        raise ValueError("independent historical denominator drifted")
    rows = []
    for index, (action, diagnostic) in enumerate(
        zip(primary_ticks, diagnostic_ticks, strict=True)
    ):
        if (
            type(action) is not dict
            or action.get("tick_index") != index
            or action.get("candidate0_action_first") is not True
            or action.get("candidate0_operational_default") is not True
            or action.get("selected_index") != 0
            or action.get("selected_trajectory_sha256")
            != action.get("default_output_sha256")
        ):
            raise ValueError(
                "independent historical candidate0 primary tick drifted"
            )
        _independent_supplementary_tick(diagnostic, index)
        for name in (
            "input_sha256",
            "default_output_sha256",
            "selected_trajectory_sha256",
        ):
            if action.get(name) != diagnostic.get(name):
                raise ValueError(
                    f"independent historical tick binding drifted: {name}"
                )
        if diagnostic["planning_started_ns"] < action["action_available_ns"]:
            raise ValueError(
                "independent historical supplementary ordering drifted"
            )
        rows.append(
            {
                "tick_index": index,
                "input_sha256": diagnostic["input_sha256"],
                "candidate_tensor_sha256": diagnostic[
                    "candidate_tensor_sha256_before"
                ],
                "candidate_row_sha256": list(
                    diagnostic["candidate_row_sha256"]
                ),
                "default_output_sha256": diagnostic["default_output_sha256"],
                "source_valid_mask": list(diagnostic["source_valid_mask"]),
                "physical_feasible_mask": list(
                    diagnostic["physical_feasible_mask"]
                ),
                "action_available_ns": action["action_available_ns"],
                "supplementary_started_ns": diagnostic[
                    "planning_started_ns"
                ],
                "supplementary_completed_ns": diagnostic[
                    "receipt_projected_ns"
                ],
            }
        )
    return {
        "schema_version": POOL_SCHEMA_VERSION,
        "candidate_tensor_source": (
            "post_action_same_tick_same_base_forward_supplementary"
        ),
        "candidate_tensor_modified": False,
        "same_forward_claimed": False,
        "pool_evidence_affects_action": False,
        "pool_evidence_affects_rng_or_next_tick": False,
        "ticks": rows,
        "outcome_fields_consumed": [],
        "fresh_protocol_changed": False,
    }


def independent_project_candidate0_supplementary(
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently project the raw supplementary receipt from sealed ABI."""

    declaration = actual_native_receipt_contract()
    required = set(
        declaration["branches"]["candidate0_supplementary"]["header"][
            "required"
        ]
    )
    contract_sha = declaration["contract_sha256"]
    if (
        type(raw) is not dict
        or set(raw) != required
        or raw.get("schema_version") != "v21_native_arm_receipt_v1"
        or raw.get("status") != "ok"
        or raw.get("arm") != "dp"
        or raw.get("claim_authorized") is not False
        or raw.get("actual_native_receipt_contract_sha256") != contract_sha
    ):
        raise ValueError("independent supplementary raw header ABI drifted")
    ticks = raw.get("ticks")
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("independent supplementary raw denominator drifted")
    projected = [
        _project_raw_supplementary_tick(tick, index, declaration)
        for index, tick in enumerate(ticks)
    ]
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "checkpoint_sha256",
        "args_sha256",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if not _sha(raw.get(name)):
            raise ValueError(
                f"independent supplementary raw SHA drifted: {name}"
            )
    if type(raw.get("scenario_seed")) is not int:
        raise ValueError("independent supplementary raw seed drifted")
    return {
        "schema_version": SUPPLEMENTARY_SCHEMA_VERSION,
        "status": "ok",
        "route_sha256": raw["route_sha256"],
        "logical_map_sha256": raw["logical_map_sha256"],
        "fixed_dp_head": raw["fixed_dp_head"],
        "checkpoint_sha256": raw["checkpoint_sha256"],
        "args_sha256": raw["args_sha256"],
        "arm": "dp",
        "scenario_seed": raw["scenario_seed"],
        "spawn_config_sha256": raw["spawn_config_sha256"],
        "initial_state_sha256": raw["initial_state_sha256"],
        "initial_input_sha256": raw["initial_input_sha256"],
        "ticks": projected,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
        "actual_native_receipt_contract_sha256": contract_sha,
    }


def _project_raw_supplementary_tick(
    value: Any, index: int, declaration: Mapping[str, Any]
) -> dict[str, Any]:
    required = set(
        declaration["branches"]["candidate0_supplementary"]["tick"][
            "required"
        ]
    )
    if type(value) is not dict or set(value) != required:
        raise ValueError("independent supplementary raw tick ABI drifted")
    _independent_supplementary_actual_tick(value, index)
    identity = value["default_candidate0_identity"]
    if (
        type(identity) is not dict
        or set(identity)
        != {
            "elementwise_equal",
            "max_abs_difference",
            "default_output_sha256",
            "candidate0_sha256",
            "native_ranked_k8",
        }
        or identity["elementwise_equal"] is not True
        or identity["max_abs_difference"] != 0.0
        or identity["default_output_sha256"]
        != value["default_output_sha256"]
        or identity["candidate0_sha256"]
        != value["candidate_row_sha256"][0]
        or identity["native_ranked_k8"] is not False
    ):
        raise ValueError("independent supplementary candidate0 identity drifted")
    return {
        "tick_index": index,
        "input_sha256": value["input_sha256"],
        "candidate_tensor_sha256_before": value[
            "candidate_tensor_sha256_before"
        ],
        "candidate_tensor_sha256_after": value[
            "candidate_tensor_sha256_after"
        ],
        "candidate_row_sha256": list(value["candidate_row_sha256"]),
        "default_output_sha256": value["default_output_sha256"],
        "selected_trajectory_sha256": value["selected_trajectory_sha256"],
        "default_candidate0_identity": dict(identity),
        "selected_index": 0,
        "source_valid_mask": list(value["source_valid_mask"]),
        "physical_feasible_mask": list(value["physical_feasible_mask"]),
        "source_complete_mask": list(value["source_complete_mask"]),
        "atom_matrix_sha256": value["atom_matrix_sha256"],
        "latency_ms": {
            name: float(value["latency_ms"][name])
            for name in sorted(value["latency_ms"])
        },
        "planning_started_ns": value["planning_started_ns"],
        "action_available_ns": value["action_available_ns"],
        "receipt_projected_ns": value["receipt_projected_ns"],
        "same_forward_claimed": False,
        "supplementary_only": True,
    }


def _independent_supplementary_actual_tick(value: Any, index: int) -> None:
    if (
        value.get("tick_index") != index
        or value.get("status") != "ok"
        or value.get("candidate_tensor_sha256_before")
        != value.get("candidate_tensor_sha256_after")
        or value.get("selected_index") != 0
        or value.get("selected_trajectory_sha256")
        != value.get("default_output_sha256")
        or value.get("candidate0_operational_default") is not True
    ):
        raise ValueError("independent supplementary raw tick value drifted")
    rows = value.get("candidate_row_sha256")
    if (
        type(rows) is not list
        or len(rows) != 8
        or rows[0] != value.get("default_output_sha256")
        or any(not _sha(item) for item in rows)
    ):
        raise ValueError("independent supplementary raw K8 rows drifted")
    for name in (
        "source_valid_mask",
        "physical_feasible_mask",
        "source_complete_mask",
    ):
        mask = value.get(name)
        if type(mask) is not list or len(mask) != 8 or any(
            type(item) is not bool for item in mask
        ):
            raise ValueError(f"independent supplementary raw mask drifted: {name}")
    if any(
        physical and not source
        for physical, source in zip(
            value["physical_feasible_mask"],
            value["source_valid_mask"],
            strict=True,
        )
    ) or not any(value["source_valid_mask"]):
        raise ValueError("independent supplementary raw eligibility drifted")
    expected_latency = {
        "input_materialization",
        "default_inference",
        "candidate_inference",
        "atom_materialization",
        "hook_total",
        "tracker",
        "total_planning",
    }
    latency = value.get("latency_ms")
    if (
        type(latency) is not dict
        or set(latency) != expected_latency
        or any(
            type(item) not in {int, float}
            or type(item) is bool
            or not math.isfinite(float(item))
            or float(item) < 0.0
            for item in latency.values()
        )
    ):
        raise ValueError("independent supplementary raw latency drifted")
    for name in (
        "input_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "selected_trajectory_sha256",
        "atom_matrix_sha256",
    ):
        if not _sha(value.get(name)):
            raise ValueError(f"independent supplementary raw SHA drifted: {name}")
    _timestamps(value)


def _independent_primary_tick(
    value: Any, index: int, declaration: Mapping[str, Any]
) -> None:
    required = set(
        declaration["branches"]["candidate0_primary"]["tick"]["required"]
    )
    if (
        type(value) is not dict
        or set(value) != required
        or value.get("tick_index") != index
        or value.get("status") != "ok"
        or value.get("candidate0_action_first") is not True
        or value.get("candidate0_operational_default") is not True
        or value.get("candidate0_pool_evidence_collected_online") is not False
        or value.get("candidate0_pool_evidence_required_post_action") is not True
        or value.get("same_forward_claimed") is not False
        or value.get("selected_index") != 0
        or value.get("selected_trajectory_sha256")
        != value.get("default_output_sha256")
    ):
        raise ValueError("independent candidate0 primary tick drifted")
    _timestamps(value)


def _independent_supplementary_tick(value: Any, index: int) -> None:
    fields = {
        "tick_index",
        "input_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate_row_sha256",
        "default_output_sha256",
        "selected_trajectory_sha256",
        "default_candidate0_identity",
        "selected_index",
        "source_valid_mask",
        "physical_feasible_mask",
        "source_complete_mask",
        "atom_matrix_sha256",
        "latency_ms",
        "planning_started_ns",
        "action_available_ns",
        "receipt_projected_ns",
        "same_forward_claimed",
        "supplementary_only",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("tick_index") != index
        or value.get("candidate_tensor_sha256_before")
        != value.get("candidate_tensor_sha256_after")
        or value.get("selected_index") != 0
        or value.get("selected_trajectory_sha256")
        != value.get("default_output_sha256")
        or value.get("same_forward_claimed") is not False
        or value.get("supplementary_only") is not True
    ):
        raise ValueError("independent candidate0 supplementary tick drifted")
    rows = value.get("candidate_row_sha256")
    if (
        type(rows) is not list
        or len(rows) != 8
        or rows[0] != value.get("default_output_sha256")
        or any(not _sha(item) for item in rows)
    ):
        raise ValueError("independent candidate0 K8 row identity drifted")
    for name in (
        "source_valid_mask",
        "physical_feasible_mask",
        "source_complete_mask",
    ):
        mask = value.get(name)
        if type(mask) is not list or len(mask) != 8 or any(
            type(item) is not bool for item in mask
        ):
            raise ValueError(f"independent candidate0 mask drifted: {name}")
    if any(
        physical and not source
        for physical, source in zip(
            value["physical_feasible_mask"],
            value["source_valid_mask"],
            strict=True,
        )
    ) or not any(value["source_valid_mask"]):
        raise ValueError("independent candidate0 eligibility drifted")
    for name in (
        "input_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "selected_trajectory_sha256",
        "atom_matrix_sha256",
    ):
        if not _sha(value.get(name)):
            raise ValueError(f"independent candidate0 SHA drifted: {name}")
    latency = value.get("latency_ms")
    expected_latency = {
        "input_materialization",
        "default_inference",
        "candidate_inference",
        "atom_materialization",
        "hook_total",
        "tracker",
        "total_planning",
    }
    if (
        type(latency) is not dict
        or set(latency) != expected_latency
        or any(
            type(item) not in {int, float}
            or type(item) is bool
            or not math.isfinite(float(item))
            or float(item) < 0.0
            for item in latency.values()
        )
    ):
        raise ValueError("independent candidate0 latency drifted")
    _timestamps(value)


def _timestamps(value: Mapping[str, Any]) -> None:
    for name in (
        "planning_started_ns",
        "action_available_ns",
        "receipt_projected_ns",
    ):
        if type(value.get(name)) is not int or value[name] < 0:
            raise ValueError(f"independent candidate0 timestamp drifted: {name}")


def _independent_tick_semantics(
    value: Mapping[str, Any], *, branch: str, index: int
) -> None:
    _timestamps(value)
    if value["receipt_projected_ns"] < value["action_available_ns"]:
        raise ValueError(f"independent {branch} receipt preceded action")
    if branch == "candidate0_primary":
        _independent_primary_tick(
            value, index, actual_native_receipt_contract()
        )
        return
    if value["candidate_tensor_sha256_before"] != value[
        "candidate_tensor_sha256_after"
    ]:
        raise ValueError(f"independent {branch} candidate tensor mutated")
    rows = value["candidate_row_sha256"]
    selected = value["selected_index"]
    if (
        rows[0] != value["default_output_sha256"]
        or rows[selected] != value["selected_trajectory_sha256"]
        or value["default_candidate0_identity"]["candidate0_sha256"] != rows[0]
        or value["default_candidate0_identity"]["default_output_sha256"]
        != rows[0]
        or value["default_candidate0_identity"]["elementwise_equal"] is not True
        or value["default_candidate0_identity"]["max_abs_difference"] != 0.0
        or value["default_candidate0_identity"]["native_ranked_k8"] is not False
        or any(
            physical and not source
            for physical, source in zip(
                value["physical_feasible_mask"],
                value["source_valid_mask"],
                strict=True,
            )
        )
        or not any(value["source_valid_mask"])
    ):
        raise ValueError(f"independent {branch} selection binding drifted")
    if branch == "candidate0_supplementary":
        if (
            selected != 0
            or value["candidate0_operational_default"] is not True
            or value["selection_policy"] != "candidate0_operational_default"
            or value["score_contract"] != "candidate0_operational_default"
            or value["eligibility_mask_name"]
            != "candidate0_operational_default"
        ):
            raise ValueError(
                "independent candidate0 supplementary semantics drifted"
            )
        return
    if (
        value["selection_policy"] != "v22_source_valid"
        or value["score_contract"]
        != "score_k=clip(a_k/s,0,10)^T w"
        or value["eligibility_mask_name"] != "source_valid_mask"
        or value["tie_break_contract"]
        != "lowest_eligible_candidate_index"
    ):
        raise ValueError(f"independent {branch} CAMP score contract drifted")
    eligible = [
        i
        for i, source in enumerate(value["source_valid_mask"])
        if source
    ]
    minimum = min(value["scores"][i] for i in eligible)
    expected = min(i for i in eligible if value["scores"][i] == minimum)
    if selected != expected:
        raise ValueError(f"independent {branch} eligible argmin drifted")
    if branch == "scene14d":
        context = value["v25_context"]
        selector = value["v25_scene_selector"]
        if (
            context["schema_version"]
            != "camp_dp_v25_causal_context_raw_v2"
            or len(context["raw_context"]) != 26
            or len(context["source_complete"]) != 26
            or selector["schema_version"]
            != "camp_dp_v25_scene_weight_receipt_v3"
            or selector["model_name"] != "CAMP-Scene14D"
            or selector["runtime_projection"] is not False
            or selector["softmax"] is not False
        ):
            raise ValueError("independent scene14d context shape drifted")


def _independent_kind(
    value: Any,
    kind: str,
    *,
    declaration: Mapping[str, Any],
    label: str,
) -> None:
    valid = False
    if kind == "native_nonnegative_int":
        valid = type(value) is int and value >= 0
    elif kind == "native_bool":
        valid = type(value) is bool
    elif kind == "nonempty_string":
        valid = type(value) is str and bool(value)
    elif kind == "sha256":
        valid = _sha(value)
    elif kind == "git_sha":
        valid = (
            type(value) is str
            and len(value) == 40
            and not (set(value) - set("0123456789abcdef"))
        )
    elif kind == "finite_float":
        valid = type(value) is float and math.isfinite(value)
    elif kind == "mapping":
        valid = type(value) is dict
    elif kind == "native_list":
        valid = type(value) is list
    elif kind == "finite_nonnegative_number_mapping":
        valid = type(value) is dict and all(
            type(item) in {int, float}
            and type(item) is not bool
            and math.isfinite(float(item))
            and float(item) >= 0.0
            for item in value.values()
        )
    elif kind == "finite_context_mapping":
        expected = set(
            declaration["nested_schemas"]["v25_context"][
                "context_feature_names"
            ]
        )
        valid = (
            type(value) is dict
            and set(value) == expected
            and all(
                type(item) is float and math.isfinite(item)
                for item in value.values()
            )
        )
    elif kind == "bool_context_mapping":
        expected = set(
            declaration["nested_schemas"]["v25_context"][
                "context_feature_names"
            ]
        )
        valid = (
            type(value) is dict
            and set(value) == expected
            and all(type(item) is bool for item in value.values())
        )
    elif kind == "no_v2i_context_source_receipt":
        valid = (
            type(value) is dict
            and set(value)
            == {
                "mode",
                "phase_remaining_available",
                "regulatory_signal_mapped",
            }
            and value["mode"] == "no_v2i"
            and value["phase_remaining_available"] is False
            and type(value["regulatory_signal_mapped"]) is bool
        )
    elif kind.startswith("sha256_list:"):
        count = int(kind.split(":", 1)[1])
        valid = (
            type(value) is list
            and len(value) == count
            and all(_sha(item) for item in value)
        )
    elif kind.startswith("native_bool_list"):
        parts = kind.split(":", 1)
        valid = type(value) is list and all(
            type(item) is bool for item in value
        )
        if valid and len(parts) == 2:
            valid = len(value) == int(parts[1])
    elif kind.startswith("finite_number_list"):
        parts = kind.split(":", 1)
        valid = type(value) is list and all(
            type(item) in {int, float}
            and type(item) is not bool
            and math.isfinite(float(item))
            for item in value
        )
        if valid and len(parts) == 2:
            valid = len(value) == int(parts[1])
    elif kind == "string_matrix:8":
        valid = (
            type(value) is list
            and len(value) == 8
            and all(
                type(row) is list
                and all(type(item) is str for item in row)
                for row in value
            )
        )
    elif kind.startswith("nested:"):
        schema_name = kind.split(":", 1)[1]
        schema = declaration["nested_schemas"][schema_name]
        if schema["kind"] == "signal_optional_exact_mapping":
            try:
                _independent_safety_record(value, schema=schema)
                valid = True
            except ValueError:
                valid = False
        elif schema["kind"] == "discriminated_exact_mapping":
            try:
                _independent_controlled_scene(value, schema=schema)
                valid = True
            except ValueError:
                valid = False
        else:
            fields = schema["fields"]
            if type(value) is dict and set(value) == set(fields):
                try:
                    for name, child_kind in fields.items():
                        _independent_kind(
                            value[name],
                            child_kind,
                            declaration=declaration,
                            label=f"{label}.{name}",
                        )
                    valid = True
                except ValueError:
                    valid = False
    elif kind == "native_result":
        fields = {
            "final_step",
            "goal_reached",
            "reason",
            "n_npc_spawned",
            "trajectory_log_path",
            "clearance_log_path",
        }
        valid = (
            type(value) is dict
            and set(value) == fields
            and type(value["final_step"]) is int
            and value["final_step"] >= 0
            and type(value["goal_reached"]) is bool
            and type(value["reason"]) is str
            and bool(value["reason"])
            and type(value["n_npc_spawned"]) is int
            and value["n_npc_spawned"] >= 0
            and _exact_native_log_paths(value)
        )
    if not valid:
        raise ValueError(f"independent actual-native type drifted: {label}")


def _independent_safety_record(
    value: Any, *, schema: Mapping[str, Any]
) -> None:
    common = set(schema["common_fields"])
    signal = set(schema["signal_fields"])
    if type(value) is not dict or set(value) not in (
        common,
        common | signal,
    ):
        raise ValueError("independent safety field set drifted")
    if type(value["tick_index"]) is not int or value["tick_index"] < 0:
        raise ValueError("independent safety tick drifted")
    for name in (
        "speed_mps",
        "ego_heading_rad",
        "route_heading_rad",
        "route_progress_m",
        "min_obb_clearance_m",
    ):
        if type(value[name]) is not float or not math.isfinite(value[name]):
            raise ValueError(f"independent safety {name} drifted")
    if value["speed_mps"] < 0.0 or value["min_obb_clearance_m"] < 0.0:
        raise ValueError("independent safety nonnegative value drifted")
    for name in ("position_xy", "front_center_prev_xy", "front_center_xy"):
        _independent_vector(value[name], 2, f"safety.{name}")
    for name in (
        "five_point_drivable_coverage",
        "red_light_at_interval_start",
        "source_complete",
    ):
        if type(value[name]) is not bool:
            raise ValueError(f"independent safety {name} drifted")
    _independent_stop_lines(value["red_stop_lines"], "safety.red_stop_lines")
    if (
        value["speed_limit_mps"] is not None
        and (
            type(value["speed_limit_mps"]) is not float
            or not math.isfinite(value["speed_limit_mps"])
            or value["speed_limit_mps"] <= 0.0
        )
    ):
        raise ValueError("independent safety speed limit drifted")
    if (
        value["constant_velocity_circle_ttc_diagnostic_s"] is not None
        and (
            type(value["constant_velocity_circle_ttc_diagnostic_s"]) is not float
            or not math.isfinite(
                value["constant_velocity_circle_ttc_diagnostic_s"]
            )
            or value["constant_velocity_circle_ttc_diagnostic_s"] < 0.0
        )
    ):
        raise ValueError("independent safety TTC drifted")
    if signal <= set(value):
        if value["signal_phase_at_interval_start"] not in {
            "green",
            "yellow",
            "red",
        }:
            raise ValueError("independent safety signal phase drifted")
        _independent_stop_lines(
            value["certified_signal_stop_lines"],
            "safety.certified_signal_stop_lines",
        )
        if (
            type(value["pre_decision_speed_mps"]) is not float
            or not math.isfinite(value["pre_decision_speed_mps"])
            or value["pre_decision_speed_mps"] < 0.0
        ):
            raise ValueError("independent safety pre-decision speed drifted")


def _independent_controlled_scene(
    value: Any, *, schema: Mapping[str, Any]
) -> None:
    if type(value) is not dict or set(value) != set(schema["fields"]):
        raise ValueError("independent controlled-scene field set drifted")
    if (
        type(value["scenario_id"]) is not str
        or not value["scenario_id"]
        or type(value["tick_index"]) is not int
        or value["tick_index"] < 0
        or type(value["sim_time_s"]) is not float
        or not math.isfinite(value["sim_time_s"])
        or value["sim_time_s"] < 0.0
        or type(value["actor_count"]) is not int
        or value["actor_count"] < 0
        or type(value["actors"]) is not list
        or len(value["actors"]) != value["actor_count"]
        or value["outcome_fields_consumed"] != []
        or value["candidate_tensor_consumed"] is not False
        or value["selected_trajectory_consumed"] is not False
    ):
        raise ValueError("independent controlled-scene scalar drifted")
    for actor in value["actors"]:
        if type(actor) is not dict or set(actor) != set(
            schema["actor_fields"]
        ):
            raise ValueError("independent controlled actor field set drifted")
        if (
            type(actor["id"]) is not str
            or not actor["id"]
            or type(actor["agent_type"]) is not str
            or not actor["agent_type"]
            or type(actor["heading_rad"]) is not float
            or not math.isfinite(actor["heading_rad"])
            or actor["scripted_exogenous"] is not True
            or type(actor["excluded_from_dp_control"]) is not bool
        ):
            raise ValueError("independent controlled actor scalar drifted")
        _independent_vector(actor["position_xy"], 2, "actor.position_xy")
        _independent_vector(
            actor["velocity_xy_mps"], 2, "actor.velocity_xy_mps"
        )
    _independent_controlled_signal(
        value["signal"],
        schema=schema,
        tick=value["tick_index"],
        scenario=value["scenario_id"],
    )
    cache = value["model_input_cache"]
    if type(cache) is not dict or set(cache) != set(
        schema["model_input_cache_fields"]
    ):
        raise ValueError("independent model-input cache field set drifted")
    if (
        cache["schema_version"]
        != "camp_dp_v25_model_input_signal_cache_receipt_v1"
        or cache["scenario_id"] != value["scenario_id"]
        or cache["tick_index"] != value["tick_index"]
        or cache["signal_source_class"] not in {"mapped_signal", "no_signal"}
        or cache["phase_authority_mode"]
        not in {
            None,
            "controlled_same_tick_override",
            "observe_same_tick_request",
        }
        or cache["cache_matches_scene_after"] is not True
        or type(cache["observe_cache_unchanged"]) is not bool
        or cache["sync_applied_before_tensor_conversion"] is not True
        or cache["future_schedule_consumed"] is not False
        or cache["phase_remaining_available"] is not False
        or cache["model_cache_tl_sha256_after"]
        != cache["scene_map_tl_sha256"]
    ):
        raise ValueError("independent model-input cache value drifted")
    if (
        cache["signal_source_class"] == "no_signal"
        and cache["phase_authority_mode"] is not None
    ) or (
        cache["signal_source_class"] == "mapped_signal"
        and cache["phase_authority_mode"] is None
    ):
        raise ValueError("independent model-input cache mode drifted")
    for name in (
        "scene_map_tl_sha256",
        "model_cache_tl_sha256_before",
        "model_cache_tl_sha256_after",
        "model_route_lanes_tl_sha256",
    ):
        if not _sha(cache[name]):
            raise ValueError(f"independent model-input cache {name} drifted")


def _independent_controlled_signal(
    value: Any,
    *,
    schema: Mapping[str, Any],
    tick: int,
    scenario: str,
) -> None:
    if type(value) is not dict or type(value.get("source_receipt")) is not dict:
        raise ValueError("independent controlled signal drifted")
    source = value["source_receipt"]
    if set(value) == set(schema["no_signal_fields"]):
        if (
            set(source) != set(schema["no_signal_source_fields"])
            or value["phase"] != "none"
            or value["source_row_count"] != 0
            or value["applied"] is not False
            or source["schema_version"]
            != "camp_dp_v25_current_signal_runtime_receipt_v2"
            or source["scenario_id"] != scenario
            or source["tick_index"] != tick
            or source["source_mode"] != "same_tick_no_signal_rule_no_v2i"
            or source["current_phase"] != "none"
            or source["traffic_light_regulatory_element_ids"] != []
            or source["phase_remaining_available"] is not False
            or source["source_valid"] is not True
            or source["applicable"] is not False
            or type(source["decision_time_s"]) is not float
            or not math.isfinite(source["decision_time_s"])
            or source["decision_time_s"] < 0.0
            or any(
                not _sha(source[name])
                for name in (
                    "route_geometry_sha256",
                    "source_chain_sha256",
                    "semantic_clone_sha256",
                )
            )
            or type(source["route_lanelet_ids"]) is not list
            or any(
                type(item) is not int for item in source["route_lanelet_ids"]
            )
        ):
            raise ValueError("independent no-signal receipt drifted")
        return
    if (
        set(value) != set(schema["mapped_signal_fields"])
        or set(source) != set(schema["mapped_signal_source_fields"])
        or source["schema_version"]
        != "camp_dp_v25_family_independent_current_signal_receipt_v1"
        or source["scenario_id"] != scenario
        or source["tick_index"] != tick
        or value["phase"] != source["current_phase"]
        or type(value["source_row_count"]) is not int
        or value["source_row_count"] <= 0
        or type(value["applied"]) is not bool
        or source["phase_authority_mode"]
        not in {"controlled_same_tick_override", "observe_same_tick_request"}
        or source["current_phase"] not in {"green", "yellow", "red"}
        or source["freshness"] != "same_tick"
        or source["source_id"]
        != "fixed_dp_current_request_route_map_signal_one_hot"
        or source["phase_remaining_available"] is not False
        or source["source_valid"] is not True
        or type(source["applicable"]) is not bool
        or source["applicable"] is not (source["current_phase"] == "red")
    ):
        raise ValueError("independent mapped signal receipt drifted")
    for name in (
        "decision_timestamp_s",
        "source_timestamp_s",
        "source_age_s",
        "route_arc_m",
    ):
        if (
            type(source[name]) is not float
            or not math.isfinite(source[name])
            or source[name] < 0.0
        ):
            raise ValueError(f"independent mapped signal {name} drifted")
    if (
        abs(
            source["decision_timestamp_s"]
            - source["source_timestamp_s"]
            - source["source_age_s"]
        )
        > 1e-12
        or source["source_age_s"] > 1e-9
    ):
        raise ValueError("independent mapped signal timestamp drifted")
    for name in (
        "stop_line_geometry_sha256",
        "route_geometry_sha256",
        "source_chain_sha256",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
    ):
        if not _sha(source[name]):
            raise ValueError(f"independent mapped signal {name} drifted")
    for name in (
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "observed_route_lanelet_ids",
        "observed_map_lanelet_ids",
    ):
        if type(source[name]) is not list or any(
            type(item) not in {int, str}
            or (type(item) is str and not item)
            for item in source[name]
        ):
            raise ValueError(f"independent mapped signal {name} drifted")
    if any(
        type(source[name]) not in {int, str}
        or (type(source[name]) is str and not source[name])
        for name in ("regulatory_element_id", "stop_line_id")
    ):
        raise ValueError("independent mapped signal authority ID drifted")
    evidence = value["tensor_evidence"]
    if (
        type(evidence) is not dict
        or set(evidence) != set(schema["tensor_evidence_fields"])
        or evidence["schema_version"]
        != "camp_dp_v25_production_signal_tensor_evidence_v2"
        or evidence["tick_index"] != tick
        or evidence["current_phase"] != source["current_phase"]
        or evidence["decision_timestamp_s"]
        != source["decision_timestamp_s"]
        or evidence["source_timestamp_s"] != source["source_timestamp_s"]
        or evidence["route_signal_tensor_sha256"]
        != source["route_signal_tensor_sha256"]
        or evidence["map_signal_tensor_sha256"]
        != source["map_signal_tensor_sha256"]
        or evidence["future_schedule_consumed"] is not False
        or evidence["phase_remaining_available"] is not False
    ):
        raise ValueError("independent tensor evidence drifted")
    route_ids, route_phase = _independent_signal_rows(
        evidence["route_signal_rows"], "route_signal_rows"
    )
    map_ids, map_phase = _independent_signal_rows(
        evidence["map_signal_rows"], "map_signal_rows"
    )
    observed_phases = {
        phase for phase in (route_phase, map_phase) if phase is not None
    }
    if (
        not route_ids
        and not map_ids
        or route_ids != source["observed_route_lanelet_ids"]
        or map_ids != source["observed_map_lanelet_ids"]
        or value["source_row_count"] != len(route_ids) + len(map_ids)
        or observed_phases != {source["current_phase"]}
        or _independent_canonical_sha(evidence["route_signal_rows"])
        != source["route_signal_tensor_sha256"]
        or _independent_canonical_sha(evidence["map_signal_rows"])
        != source["map_signal_tensor_sha256"]
    ):
        raise ValueError("independent signal row authority drifted")


def _independent_vector(value: Any, length: int, label: str) -> None:
    if (
        type(value) is not list
        or len(value) != length
        or any(type(item) is not float or not math.isfinite(item) for item in value)
    ):
        raise ValueError(f"independent {label} drifted")


def _independent_stop_lines(value: Any, label: str) -> None:
    if type(value) is not list:
        raise ValueError(f"independent {label} drifted")
    for line in value:
        if type(line) is not list or len(line) != 2:
            raise ValueError(f"independent {label} drifted")
        for point in line:
            _independent_vector(point, 2, label)


def _independent_signal_rows(
    value: Any, label: str
) -> tuple[list[int], str | None]:
    if type(value) is not list:
        raise ValueError(f"independent {label} drifted")
    ids: list[int] = []
    phases: set[str] = set()
    for row in value:
        if (
            type(row) is not dict
            or set(row) != {"lanelet_id", "signal_channels_8_12"}
            or type(row["lanelet_id"]) is not int
            or type(row["signal_channels_8_12"]) is not list
            or not row["signal_channels_8_12"]
        ):
            raise ValueError(f"independent {label} drifted")
        row_phases: set[str] = set()
        active_count = 0
        for channels in row["signal_channels_8_12"]:
            _independent_vector(channels, 5, label)
            if all(item == 0.0 for item in channels):
                continue
            active_count += 1
            matches = []
            for phase, column in (("green", 0), ("yellow", 1), ("red", 2)):
                expected = [0.0] * 5
                expected[column] = 1.0
                if channels == expected:
                    matches.append(phase)
            if len(matches) != 1:
                raise ValueError(f"independent {label} phase drifted")
            row_phases.add(matches[0])
        if active_count == 0 or len(row_phases) != 1:
            raise ValueError(f"independent {label} phase drifted")
        ids.append(row["lanelet_id"])
        phases.update(row_phases)
    if len(ids) != len(set(ids)) or len(phases) > 1:
        raise ValueError(f"independent {label} authority drifted")
    return ids, next(iter(phases)) if phases else None


def _independent_canonical_sha(value: Any) -> str:
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


def _exact_native_log_paths(value: Mapping[str, Any]) -> bool:
    if (
        type(value.get("trajectory_log_path")) is not str
        or type(value.get("clearance_log_path")) is not str
    ):
        return False
    trajectory = Path(value["trajectory_log_path"])
    clearance = Path(value["clearance_log_path"])
    return (
        trajectory.is_absolute()
        and clearance.is_absolute()
        and str(trajectory) == str(trajectory.resolve())
        and str(clearance) == str(clearance.resolve())
        and trajectory.name == "trajectory_log.json"
        and clearance.name == "clearance_log.json"
        and trajectory.parent == clearance.parent
    )


def _sha(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def independent_contract_sha256() -> str:
    value = actual_native_receipt_contract()
    embedded = value.pop("contract_sha256")
    calculated = hashlib.sha256(
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
    if embedded != calculated:
        raise ValueError("actual-native ABI declaration hash drifted")
    return calculated
