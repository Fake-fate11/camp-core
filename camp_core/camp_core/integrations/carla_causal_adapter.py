from __future__ import annotations

from typing import Any, Mapping, Optional

import numpy as np

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CausalDPMaterialization,
    materialize_causal_dp_input,
)


_FORBIDDEN_SOURCE_PARTS = (
    "future",
    "outcome",
    "label",
    "holdout",
    "metric",
    "safety",
    "collision",
    "ade",
    "fde",
)


def _reject_forbidden_source_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _FORBIDDEN_SOURCE_PARTS):
                raise ValueError("forbidden source field: %s" % key)
            _reject_forbidden_source_fields(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_forbidden_source_fields(child)


def materialize_carla_snapshot(
    *,
    timestamps_us: Any,
    decision_timestamp_us: int,
    traffic_timestamp_us: Optional[int],
    batch: Any,
    decision_context: Mapping[str, Any],
    source_metadata: Mapping[str, Any],
) -> CausalDPMaterialization:
    """Validate one source-only CARLA tick and reuse the fixed causal boundary."""
    _reject_forbidden_source_fields(source_metadata)
    timestamps = np.asarray(timestamps_us)
    if timestamps.shape != (31,) or timestamps.dtype.kind not in "iu":
        raise ValueError("CARLA history must contain 31 timestamps")
    if not np.all(np.diff(timestamps) == 100_000):
        raise ValueError("CARLA history timestamps must be uniform 0.1s ticks")
    decision = int(decision_timestamp_us)
    if int(timestamps[-1]) != decision:
        raise ValueError("CARLA history must end at the decision tick")
    traffic_available = decision_context.get("traffic_light_state_available")
    if traffic_available is True and (
        traffic_timestamp_us is None or int(traffic_timestamp_us) != decision
    ):
        raise ValueError("CARLA traffic timestamp must equal the decision tick")
    if decision_context.get("route_source") != "current_map_topology_successors":
        raise ValueError("CARLA route must use current_map_topology_successors")

    materialized = materialize_causal_dp_input(batch, decision_context)
    return CausalDPMaterialization(
        dp_input=materialized.dp_input,
        metadata={
            **materialized.metadata,
            "source": "official_carla_snapshot",
            "observable_dynamic_limit": 32,
            "observable_static_limit": 5,
            "source_metadata": dict(source_metadata),
        },
    )
