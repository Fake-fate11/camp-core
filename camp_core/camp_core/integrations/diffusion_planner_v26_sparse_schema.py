"""Frozen sparse training schema for the V26 same-tick atom bank."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


V26_GLOBAL_ATOM_NAMES = (
    "predicted_obb_collision_exposure_fraction",
    "ttc_deficit_0_95s",
    "dynamic_clearance_buffer_deficit",
    "overspeed_integral_m2_per_s",
    "full_footprint_road_exit_severity_s",
    "reverse_progress_severity_m",
    "red_light_crossing_exposure_fraction",
    "red_stopping_margin_m2_s",
    "route_progress_shortfall_m",
    "longitudinal_acceleration_energy_s",
    "lateral_acceleration_energy_s",
    "yaw_rate_energy_s",
    "yaw_acceleration_energy_s",
    "longitudinal_jerk_energy_s",
    "jerk_magnitude_energy_s",
)
V26_ATOM_STATUS_VOCABULARY = (
    "observed",
    "not_applicable",
    "typed_missing",
)
V26_TRAINABLE_ATOM_NAMES = V26_GLOBAL_ATOM_NAMES
V26_UNRESOLVED_ATOM_NAMES: tuple[str, ...] = ()
V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES = (
    V26_GLOBAL_ATOM_NAMES[0],
    *V26_GLOBAL_ATOM_NAMES[9:15],
)
V26_GLOBAL_ATOM_INDEX = {
    name: index for index, name in enumerate(V26_GLOBAL_ATOM_NAMES)
}

_T = 80
_DT_SECONDS = 0.1


def validate_v26_sparse_pool_artifact(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one current sparse artifact without expanding missing columns."""

    if tuple(artifact.get("bank_atom_names", ())) != V26_GLOBAL_ATOM_NAMES:
        raise ValueError("bank_atom_names must equal the frozen global 15-bank order")
    observed_names = _strict_names(
        artifact.get("observed_atom_names", ()), "observed_atom_names"
    )
    if len(set(observed_names)) != len(observed_names):
        raise ValueError("observed_atom_names must be unique")
    if any(name not in V26_GLOBAL_ATOM_INDEX for name in observed_names):
        raise ValueError("observed_atom_names contains an unknown global atom")
    expected_indices = tuple(V26_GLOBAL_ATOM_INDEX[name] for name in observed_names)
    global_indices = _strict_indices(
        artifact.get("observed_global_atom_indices", ()),
        "observed_global_atom_indices",
    )
    if global_indices != expected_indices:
        raise ValueError(
            "observed columns must map one-to-one to their frozen global indices"
        )
    if tuple(sorted(global_indices)) != global_indices:
        raise ValueError("sparse observed columns must retain global bank order")

    states = artifact.get("atom_states")
    if not isinstance(states, Sequence) or isinstance(states, (str, bytes)):
        raise ValueError("atom_states must be a 15-row sequence")
    if len(states) != len(V26_GLOBAL_ATOM_NAMES):
        raise ValueError("atom_states must retain all 15 global rows")
    state_names: list[str] = []
    state_status: dict[str, str] = {}
    for state in states:
        if not isinstance(state, Mapping):
            raise ValueError("each atom state must be a mapping")
        name = state.get("name")
        status = state.get("status")
        if type(name) is not str or not name:
            raise ValueError("atom state names must be nonempty native strings")
        if status not in V26_ATOM_STATUS_VOCABULARY:
            raise ValueError("atom state uses an unknown status")
        state_names.append(name)
        state_status[name] = status
    if tuple(state_names) != V26_GLOBAL_ATOM_NAMES:
        raise ValueError("atom_states must retain frozen global order")
    state_observed = tuple(
        name for name in V26_GLOBAL_ATOM_NAMES if state_status[name] == "observed"
    )
    if state_observed != observed_names:
        raise ValueError(
            "observed_atom_names must exactly match the jointly observed state rows"
        )

    candidate_count = artifact.get("K")
    if type(candidate_count) is not int or candidate_count < 1:
        raise ValueError("artifact K must be a positive native integer")
    candidates = _raw_matrix(artifact.get("candidate_atoms_raw"), "candidate_atoms_raw")
    experts = _raw_matrix(artifact.get("expert_atoms_raw"), "expert_atoms_raw")
    expected_shape = (candidate_count, len(observed_names))
    if candidates.shape != expected_shape or experts.shape != expected_shape:
        raise ValueError("raw sparse matrices must both have shape [K,Q_pool]")
    if artifact.get("T") != _T:
        raise ValueError("artifact must retain fixed T=80")
    if not np.isclose(float(artifact.get("dt_seconds", -1.0)), _DT_SECONDS):
        raise ValueError("artifact must retain fixed dt=0.1 seconds")
    if artifact.get("candidate0_row") != 0:
        raise ValueError("artifact must retain candidate0=row0")
    identity = artifact.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("artifact identity must be a mapping")

    return {
        "identity": dict(identity),
        "observed_atom_names": observed_names,
        "observed_global_atom_indices": global_indices,
        "candidate_atoms_raw": candidates,
        "expert_atoms_raw": experts,
        "atom_status_by_name": state_status,
    }


def evaluate_v26_complete_pool_eligibility(
    artifact: Mapping[str, Any],
    *,
    expert_future_brackets_8s: bool,
) -> dict[str, Any]:
    """Evaluate scientific-source completeness without gating optional endpoints."""

    validated = validate_v26_sparse_pool_artifact(artifact)
    identity = validated["identity"]
    reasons: list[str] = []
    if expert_future_brackets_8s is not True:
        reasons.append("expert_future_does_not_bracket_8_seconds")
    if identity.get("city") not in {"boston", "pittsburgh"}:
        reasons.append("city_is_not_Boston_or_Pittsburgh")
    if identity.get("partition") != "train_iid":
        reasons.append("partition_is_not_train_iid")
    if not identity.get("anchor_id"):
        reasons.append("anchor_id_is_missing")
    observed = set(validated["observed_atom_names"])
    missing_required = [
        name for name in V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES if name not in observed
    ]
    if missing_required:
        reasons.append("required_joint_atoms_missing:" + ",".join(missing_required))
    endpoint_local = {
        name: validated["atom_status_by_name"][name]
        for name in V26_TRAINABLE_ATOM_NAMES
        if name not in V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES
    }
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "required_joint_atom_names": list(V26_COMPLETE_POOL_REQUIRED_ATOM_NAMES),
        "endpoint_local_authoritative_atom_states": endpoint_local,
        "unresolved_atoms_are_eligibility_gates": False,
    }


def _strict_names(values: Any, field: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a sequence")
    if any(type(value) is not str or not value for value in values):
        raise ValueError(f"{field} must contain nonempty native strings")
    return tuple(values)


def _strict_indices(values: Any, field: str) -> tuple[int, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a sequence")
    if any(type(value) is not int for value in values):
        raise ValueError(f"{field} must contain native integers")
    return tuple(values)


def _raw_matrix(value: Any, field: str) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 2 or array.dtype.kind not in "fiu" or array.dtype.kind == "b":
        raise ValueError(f"{field} must be a native numeric matrix")
    array = array.astype(np.float64, copy=False)
    if not np.isfinite(array).all() or np.any(array < 0.0):
        raise ValueError(f"{field} must be finite nonnegative")
    return array
