"""Neutral API for the shared CAMP convex selector-training arithmetic.

The existing V25 module remains its historical entry point.  This facade gives
V26 a math-only API and deliberately exports no release, opening, receipt, or
artifact-policy behavior.
"""

from __future__ import annotations

from camp_core.integrations.diffusion_planner_v25_training import (
    V25TrainedSelector as CAMPTrainedSelector,
    train_v25_selector_suite as train_camp_selector_suite,
)
from camp_core.outer_master.parametric_cvxpy_master import (
    V25ParametricMasterConfig as CAMPParametricMasterConfig,
)

__all__ = (
    "CAMPParametricMasterConfig",
    "CAMPTrainedSelector",
    "train_camp_selector_suite",
)
