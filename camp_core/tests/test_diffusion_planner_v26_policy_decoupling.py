from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_camp_context_math import (
    CAMPContextSourceCapabilities,
    build_camp_raw_context,
)
from camp_core.integrations.diffusion_planner_camp_training_math import (
    ATOM_COUNT,
    build_train_only_causal_labels as neutral_labels,
    fit_train_only_atom_scales as neutral_scales,
    hierarchical_snapshot_weights as neutral_weights,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    V25ContextScaler,
    build_v25_raw_context,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    build_train_only_causal_labels as v25_labels,
    fit_train_only_atom_scales as v25_scales,
    hierarchical_snapshot_weights as v25_weights,
)
from camp_core.integrations.diffusion_planner_v26_nuplan import (
    build_v26_nuplan_unavailable_signal_authority,
)
from camp_core.integrations.diffusion_planner_v26_source_capabilities import (
    build_v26_camp_raw_context,
    v26_source_capabilities,
)


ROOT = Path(__file__).resolve().parents[2]
V26_PRODUCTION_SOURCES = (
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_nuplan.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_nuplan_signal.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_source_capabilities.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_native_runner.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_scene14d_adapter.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_selector_adaptation.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_development_comparison.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_integration_boundary.py",
    ROOT / "scripts/integrations/run_diffusion_planner_v26_nuplan_mini_b8_smoke.py",
    ROOT / "scripts/integrations/run_diffusion_planner_v26_nuplan_b8_corpus_materialization.py",
)
NEUTRAL_CAMP_CORE_SOURCES = (
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_camp_context_math.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_camp_training_math.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_camp_signal_contract.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_fixed_dp_reference.py",
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_source_capabilities.py",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _causal_input(*, speed_available: bool) -> dict[str, np.ndarray]:
    result = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    result["ego_current_state"] = np.asarray(
        [0.0, 0.0, 1.0, 0.0, 8.0, 0.0, -1.0, 0.0, 0.0, 0.1], dtype=np.float32
    )
    result["ego_shape"] = np.asarray([2.9, 4.5, 1.9], dtype=np.float32)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(0.0, 19.0, 20)
    route[1, :, 0] = np.linspace(20.0, 39.0, 20)
    route[:2, :, 2] = 1.0
    route[:2, :, 5] = 2.0
    route[:2, :, 7] = -2.0
    result["route_lanes"] = route
    if speed_available:
        result["route_lanes_speed_limit"][:2, 0] = 12.0
        result["route_lanes_has_speed_limit"][:2, 0] = True
    return result


def _candidates() -> np.ndarray:
    result = np.zeros((8, 80, 4), dtype=np.float64)
    for index in range(8):
        result[index, :, 0] = np.linspace(0.1, 30.0 + index, 80)
        result[index, :, 2] = 1.0
    return result


def _unavailable_authority() -> dict[str, object]:
    return build_v26_nuplan_unavailable_signal_authority(
        source_identity={
            "record_id": "anchor-0",
            "official_split": "train",
            "log_token": "log-0",
            "scenario_token": "scenario-0",
            "scene_token": "scene-0",
            "state_token": "state-0",
            "mission_route_roadblock_chain_sha256": _sha("route"),
            "corridor_id": "corridor-0",
            "geometry_clone_group_sha256": _sha("geometry"),
            "city": "boston",
            "map_family": "us-ma-boston",
            "source_db_sha256": _sha("db"),
            "map_sha256": _sha("map"),
            "event_strata": ["scenario_tag:test"],
        },
        route_lanes=np.zeros((25, 20, 33), dtype=np.float64),
        decision_timestamp_us=100_000,
        traffic_light_state_available=False,
    )


def _assert_no_direct_v25_policy_imports(paths: tuple[Path, ...]) -> None:
    forbidden = ("diffusion_planner_v25_", "validate_diffusion_planner_v25_")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(token in module for token in forbidden), (path, module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(token in alias.name for token in forbidden), (path, alias.name)


def test_active_v26_production_sources_do_not_directly_import_v25_policy_modules() -> None:
    _assert_no_direct_v25_policy_imports(V26_PRODUCTION_SOURCES)


def test_neutral_camp_core_does_not_reimport_v25_policy_modules() -> None:
    _assert_no_direct_v25_policy_imports(NEUTRAL_CAMP_CORE_SOURCES)


def test_v25_context_entry_uses_the_same_neutral_context_arithmetic() -> None:
    causal = _causal_input(speed_available=True)
    candidates = _candidates()
    source = np.ones(8, dtype=np.bool_)
    legacy = build_v25_raw_context(
        causal_input=causal, candidates=candidates, source_valid_mask=source
    )
    neutral = build_camp_raw_context(
        causal_input=causal,
        candidates=candidates,
        source_valid_mask=source,
        source_capabilities=CAMPContextSourceCapabilities(
            speed_limit_status="available", signal_source_state="route_only"
        ),
    )
    assert legacy.raw.tobytes() == neutral.raw.tobytes()
    assert legacy.source_complete == neutral.source_complete
    assert dict(legacy.source_receipt) == dict(neutral.source_receipt)


def test_v25_training_public_math_is_neutral_and_bit_exact() -> None:
    weights = v25_weights(["a", "a", "b"], ["x", "x", "y"], [1, 1, 1], [0, 1, 0])
    np.testing.assert_array_equal(weights, neutral_weights(["a", "a", "b"], ["x", "x", "y"], [1, 1, 1], [0, 1, 0]))
    raw = np.ones((2, 8, ATOM_COUNT), dtype=np.float64)
    source = np.ones((2, 8), dtype=np.bool_)
    atom_source = np.ones_like(raw, dtype=np.bool_)
    applicable = np.ones_like(raw, dtype=np.bool_)
    physical = np.ones((2, 8), dtype=np.bool_)
    scales_v25 = v25_scales(raw, source, atom_source, applicable, np.asarray([0.5, 0.5]), ["a", "b"], minimum_positive_rows=1, minimum_positive_blocks=1)
    scales_neutral = neutral_scales(raw, source, atom_source, applicable, np.asarray([0.5, 0.5]), ["a", "b"], minimum_positive_rows=1, minimum_positive_blocks=1)
    np.testing.assert_array_equal(scales_v25["scales"], scales_neutral["scales"])
    labels_v25 = v25_labels(raw, source, atom_source, applicable, physical, scales_v25["scales"])
    labels_neutral = neutral_labels(raw, source, atom_source, applicable, physical, scales_neutral["scales"])
    for key in labels_v25:
        np.testing.assert_array_equal(labels_v25[key], labels_neutral[key])


def test_v26_typed_missing_capability_masks_optional_context_without_defaults() -> None:
    authority = _unavailable_authority()
    capabilities = v26_source_capabilities(
        speed_limit_status="typed_missing", signal_authority=authority
    )
    record = build_v26_camp_raw_context(
        causal_input=_causal_input(speed_available=False),
        candidates=_candidates(),
        source_valid_mask=np.ones(8, dtype=np.bool_),
        signal_authority=authority,
        capabilities=capabilities,
    )
    assert record.source_complete[8:10] == (False, False)
    assert record.source_complete[10:15] == (False,) * 5
    assert record.raw[8:10].tolist() == [0.0, 0.0]


def test_v26_source_capability_hard_fails_on_authority_state_drift() -> None:
    authority = _unavailable_authority()
    capabilities = v26_source_capabilities(
        speed_limit_status="typed_missing", signal_authority=authority
    )
    drifted = dict(authority)
    drifted["source_state"] = "not_applicable"
    with pytest.raises(ValueError, match="does not match source authority"):
        build_v26_camp_raw_context(
            causal_input=_causal_input(speed_available=False),
            candidates=_candidates(),
            source_valid_mask=np.ones(8, dtype=np.bool_),
            signal_authority=drifted,
            capabilities=capabilities,
        )
