"""V26-native optional-source capability and eligibility boundary.

Optional speed and signal context is represented as an explicit source state.
Unavailable data is masked or typed-missing; it is never supplied as a default
value, inferred from a route substitute, or routed through V25 policy flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .diffusion_planner_camp_context_math import (
    CAMPContextRecord,
    CAMPContextSourceCapabilities,
    build_camp_raw_context,
)
from .diffusion_planner_causal_atoms import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    V22_SOURCE_VALID_ELIGIBILITY,
    materialize_canonical_14d,
)


_SPEED_STATES = frozenset({"available", "typed_missing"})
_SIGNAL_STATES = frozenset({"available", "not_applicable", "unavailable"})


@dataclass(frozen=True)
class V26SourceCapabilities:
    speed_limit_status: str
    signal_source_state: str

    def __post_init__(self) -> None:
        if self.speed_limit_status not in _SPEED_STATES:
            raise ValueError("V26 speed-limit source capability is invalid")
        if self.signal_source_state not in _SIGNAL_STATES:
            raise ValueError("V26 signal source capability is invalid")

    def context_capabilities(self) -> CAMPContextSourceCapabilities:
        return CAMPContextSourceCapabilities(
            speed_limit_status=self.speed_limit_status,
            signal_source_state=self.signal_source_state,
        )


def v26_source_capabilities(
    *, speed_limit_status: str, signal_authority: Mapping[str, Any]
) -> V26SourceCapabilities:
    if type(signal_authority) is not dict or type(signal_authority.get("source_state")) is not str:
        raise ValueError("V26 signal authority must declare a source state")
    return V26SourceCapabilities(
        speed_limit_status=speed_limit_status,
        signal_source_state=str(signal_authority["source_state"]),
    )


def build_v26_camp_raw_context(
    *, causal_input: Mapping[str, Any], candidates: np.ndarray,
    source_valid_mask: np.ndarray, signal_authority: Mapping[str, Any],
    capabilities: V26SourceCapabilities,
) -> CAMPContextRecord:
    if capabilities.signal_source_state != signal_authority.get("source_state"):
        raise ValueError("V26 signal capability does not match source authority")
    signal_input = signal_authority.get("causal_signal_atom_input")
    if type(signal_input) is not dict:
        raise ValueError("V26 signal authority has no causal atom input")
    return build_camp_raw_context(
        causal_input=causal_input,
        candidates=candidates,
        source_valid_mask=source_valid_mask,
        causal_signal_atom_input=signal_input,
        source_capabilities=capabilities.context_capabilities(),
    )


def materialize_v26_camp_atoms(
    *, candidates: np.ndarray, causal_input: Mapping[str, Any],
    neighbor_predictions: np.ndarray, neighbor_valid_mask: np.ndarray,
    signal_mask: np.ndarray, planned_red_light_cost: np.ndarray,
    signal_authority: Mapping[str, Any], capabilities: V26SourceCapabilities,
    dt: float, phase_receipt: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Materialize shared atoms with V26 capability semantics at one boundary."""
    if capabilities.signal_source_state != signal_authority.get("source_state"):
        raise ValueError("V26 signal capability does not match source authority")
    signal_input = signal_authority.get("causal_signal_atom_input")
    if type(signal_input) is not dict:
        raise ValueError("V26 signal authority has no causal atom input")
    return materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid_mask,
        signal_mask=signal_mask,
        planned_red_light_cost=planned_red_light_cost,
        causal_signal_atom_input=signal_input,
        dt=dt,
        speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
        eligibility_policy=V22_SOURCE_VALID_ELIGIBILITY,
        allow_inapplicable_speed_atoms=(capabilities.speed_limit_status == "typed_missing"),
        allow_unavailable_signal_atoms=(capabilities.signal_source_state == "unavailable"),
        phase_receipt=phase_receipt,
    )
