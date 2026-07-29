"""V26 boundary for the frozen zero-shot Scene14D reference head.

The reference weights remain read-only.  This adapter only maps V26's
outcome-blind current-state fields into the exact frozen context schema and
checks the established scaler/simplex contract before selector use.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from .diffusion_planner_camp_context_math import CONTEXT_SCHEMA_VERSION, RAW_FEATURE_NAMES


V26_SCENE14D_ADAPTER_SCHEMA_VERSION = "camp_dp_v26_scene14d_reference_adapter_v1"
V26_SCENE14D_CONTEXT_SCHEMA_VERSION = CONTEXT_SCHEMA_VERSION
FROZEN_SIMPLEX_TOLERANCE = 1e-9


def build_v26_scene14d_context(
    *,
    raw_context: Mapping[str, Any],
    source_complete: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and map only existing current-state context fields.

    No missing field is filled, and no candidate outcome or selected action is
    accepted here.  The returned mapping is exactly the frozen reference input
    schema expected by the read-only zero-shot provider.
    """

    if set(raw_context) != set(RAW_FEATURE_NAMES) or set(source_complete) != set(
        RAW_FEATURE_NAMES
    ):
        raise ValueError("V26 Scene14D context field set drifted")
    validated_raw: dict[str, float] = {}
    validated_complete: dict[str, bool] = {}
    for name in RAW_FEATURE_NAMES:
        value = raw_context[name]
        complete = source_complete[name]
        if type(value) not in {int, float} or not math.isfinite(float(value)):
            raise ValueError(f"V26 Scene14D context {name} is not finite")
        if type(complete) is not bool:
            raise ValueError(f"V26 Scene14D source-complete {name} is invalid")
        validated_raw[name] = float(value)
        validated_complete[name] = complete
    if type(source_receipt) is not dict:
        raise ValueError("V26 Scene14D source receipt is invalid")
    return {
        "schema_version": V26_SCENE14D_CONTEXT_SCHEMA_VERSION,
        "raw_context": validated_raw,
        "source_complete": validated_complete,
        "source_receipt": dict(source_receipt),
    }


class V26FrozenScene14DAdapter:
    """Narrow V26 wrapper around a frozen, read-only Scene14D provider."""

    def __init__(self, provider: Any, *, simplex_tolerance: float = FROZEN_SIMPLEX_TOLERANCE) -> None:
        if simplex_tolerance != FROZEN_SIMPLEX_TOLERANCE:
            raise ValueError("V26 Scene14D adapter requires frozen simplex tolerance 1e-9")
        self.provider = provider
        self.simplex_tolerance = float(simplex_tolerance)
        self._reference_contract = self._validate_reference_contract()

    def _validate_reference_contract(self) -> dict[str, Any]:
        theta = np.asarray(getattr(self.provider, "theta", None), dtype=np.float64)
        scaler = getattr(self.provider, "context_scaler", None)
        q05 = np.asarray(getattr(scaler, "q05", None), dtype=np.float64)
        q95 = np.asarray(getattr(scaler, "q95", None), dtype=np.float64)
        if (
            theta.shape != (14, 53)
            or q05.shape != (len(RAW_FEATURE_NAMES),)
            or q95.shape != (len(RAW_FEATURE_NAMES),)
            or not np.isfinite(theta).all()
            or not np.isfinite(q05).all()
            or not np.isfinite(q95).all()
            or np.any(q95 <= q05)
        ):
            raise ValueError("V26 Scene14D frozen reference schema/scaler drifted")
        return {
            "schema_version": V26_SCENE14D_ADAPTER_SCHEMA_VERSION,
            "reference_context_schema_version": V26_SCENE14D_CONTEXT_SCHEMA_VERSION,
            "raw_feature_count": len(RAW_FEATURE_NAMES),
            "context_scaler_sha256": str(getattr(self.provider, "context_scaler_sha256")),
            "theta_sha256": str(getattr(self.provider, "theta_sha256")),
            "simplex_tolerance": self.simplex_tolerance,
            "outcome_fields_consumed": False,
            "imputation_used": False,
        }

    def reference_contract(self) -> dict[str, Any]:
        return dict(self._reference_contract)

    def __call__(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = build_v26_scene14d_context(
            raw_context=dict(context.get("raw_context", {})),
            source_complete=dict(context.get("source_complete", {})),
            source_receipt=dict(context.get("source_receipt", {})),
        )
        receipt = dict(self.provider(payload))
        weights = np.asarray(receipt.get("weights"), dtype=np.float64)
        if (
            weights.shape != (14,)
            or not np.isfinite(weights).all()
            or np.any(weights < -self.simplex_tolerance)
            or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=self.simplex_tolerance)
            or receipt.get("context_scaler_sha256")
            != self._reference_contract["context_scaler_sha256"]
            or receipt.get("theta_sha256") != self._reference_contract["theta_sha256"]
            or receipt.get("runtime_projection") is not False
            or receipt.get("softmax") is not False
        ):
            raise ValueError("V26 Scene14D frozen reference receipt drifted")
        return receipt
