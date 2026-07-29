"""Neutral read-only facade for frozen zero-shot CAMP reference weights.

This compatibility bridge exposes selector arithmetic only.  V26 callers do
not receive V25 runner, evaluator, release, or receipt-policy interfaces.
"""

from __future__ import annotations

from .diffusion_planner_v25_scene_runtime import (
    V25Scene14DWeightProvider as CAMPScene14DReferenceProvider,
    load_v25_runtime_selector_assets as load_camp_zero_shot_reference_assets,
)

__all__ = ("CAMPScene14DReferenceProvider", "load_camp_zero_shot_reference_assets")
