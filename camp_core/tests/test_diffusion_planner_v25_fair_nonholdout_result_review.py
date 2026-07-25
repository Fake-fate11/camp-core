from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.integrations import (
    review_diffusion_planner_v25_fair_nonholdout as reviewer,
)
from scripts.integrations import (
    validate_diffusion_planner_v25_fair_nonholdout as producer,
)


def _valid_preimage():
    atoms = np.arange(112, dtype=np.float64).reshape(8, 14) / 100.0
    scales = np.ones(14, dtype=np.float64)
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    mask = np.ones(8, dtype=np.bool_)
    return atoms, scales, weights, mask


def test_reviewer_local_score_selects_lowest_score():
    atoms, scales, weights, mask = _valid_preimage()
    scores, selected = reviewer._selected(atoms, scales, weights, mask)
    assert selected == 0
    assert scores.shape == (8,)


def test_reviewer_local_score_uses_source_mask_and_lowest_index_tie():
    atoms, scales, weights, mask = _valid_preimage()
    atoms[:] = 0.0
    mask[:3] = False
    _scores, selected = reviewer._selected(atoms, scales, weights, mask)
    assert selected == 3


def test_reviewer_local_score_clips_normalized_atoms_at_ten():
    atoms, scales, weights, mask = _valid_preimage()
    atoms[0] = 100.0
    scores, _selected = reviewer._selected(atoms, scales, weights, mask)
    assert scores[0] == pytest.approx(10.0)


@pytest.mark.parametrize(
    "mutation",
    ("no_eligible", "bad_mask_dtype", "bad_scale", "bad_weight_sum"),
)
def test_reviewer_local_score_fails_closed(mutation):
    atoms, scales, weights, mask = _valid_preimage()
    if mutation == "no_eligible":
        mask[:] = False
    elif mutation == "bad_mask_dtype":
        mask = mask.astype(np.int64)
    elif mutation == "bad_scale":
        scales[0] = 0.0
    else:
        weights[0] += 0.1
    with pytest.raises(ValueError):
        reviewer._selected(atoms, scales, weights, mask)


def test_reviewer_does_not_import_producer_or_fairness_oracle():
    source = Path(reviewer.__file__).read_text("utf-8")
    forbidden = (
        "validate_diffusion_planner_v25_fair_nonholdout import",
        "diffusion_planner_v25_fair_nonholdout import",
        "select_camp_candidate",
        "materialize_canonical_14d",
        "candidate_latents",
    )
    assert not any(token in source for token in forbidden)
    assert "def _selected(" in source


def test_producer_baseline_has_explicit_uncalled_stage_na_gate():
    source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "validate_diffusion_planner_v25_fair_nonholdout.py"
    ).read_text("utf-8")
    assert '"atoms": None' in source
    assert '"context": None' in source
    assert '"weights": None' in source
    assert '"selector_incremental": None' in source
    assert "real selector made a forbidden model call" in source


def test_producer_builds_explicit_root_bound_no_signal_input():
    class Lanelet:
        def trafficLights(self):
            return []

    class Cached:
        raw_centerline = np.asarray([[0.0, 0.0], [10.0, 0.0]])

    class Builder:
        _ll_by_id = {7: Lanelet()}
        _cache = {7: Cached()}

    chain = producer._build_no_signal_chain(
        builder=Builder(),
        route_ids=[7],
        map_sha256="1" * 64,
        route_sha256="2" * 64,
    )
    assert chain["traffic_light_regulatory_element_ids"] == []
    assert chain["source_map_sha256"] == "1" * 64
    assert chain["route_identity_sha256"] == "2" * 64


def test_producer_rejects_signalized_route_for_no_signal_contract():
    class Light:
        id = 3

    class Lanelet:
        def trafficLights(self):
            return [Light()]

    class Cached:
        raw_centerline = np.asarray([[0.0, 0.0], [10.0, 0.0]])

    class Builder:
        _ll_by_id = {7: Lanelet()}
        _cache = {7: Cached()}

    with pytest.raises(ValueError, match="signal authority"):
        producer._build_no_signal_chain(
            builder=Builder(),
            route_ids=[7],
            map_sha256="1" * 64,
            route_sha256="2" * 64,
        )
