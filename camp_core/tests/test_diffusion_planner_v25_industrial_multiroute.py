from __future__ import annotations

from copy import deepcopy
import hashlib

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    evaluation_contract_v3,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute import (
    AUTHORITY_SHA256,
    FAMILIES,
    RISK_TIERS,
    ROUTE_BINS,
    SOURCE_AVAILABILITY,
    canonical_sha256,
    capacity_decision,
    contract,
    find_feasible_counts,
    latent_seed,
    latent_tensor,
    overlap_report,
    select_lexicographically_smallest_feasible,
    validate_candidate,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_review import (
    review_contract_literal,
    review_overlap_literal,
    review_selected_manifest_literal,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _candidate(
    family: int,
    risk: int,
    route: int,
    source: int,
    ordinal: int,
) -> dict:
    semantic_family = FAMILIES[family]
    risk_tier = RISK_TIERS[risk]
    source_class = SOURCE_AVAILABILITY[source]
    signal = _sha(f"signal:{family}:{risk}:{route}:{source}:{ordinal}")
    actors = _sha(f"actors:{family}:{risk}:{route}:{source}:{ordinal}")
    route_sha = _sha(f"route:{family}:{risk}:{route}:{source}:{ordinal}")
    geometry_sha = _sha(f"geometry:{family}:{risk}:{route}:{source}:{ordinal}")
    source_sha = _sha(f"source:{family}:{risk}:{route}:{source}:{ordinal}")
    seed_sha = _sha(f"seed:{family}:{risk}:{route}:{source}:{ordinal}")
    latent_sha = _sha(f"latent:{family}:{risk}:{route}:{source}:{ordinal}")
    payload = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
        ),
        "canonical_route_lanelet_arc_sha256": route_sha,
        "route_geometry_sha256": geometry_sha,
        "semantic_family": semantic_family,
        "risk_tier": risk_tier,
        "source_availability": source_class,
        "certified_signal_stopline_inventory_sha256": signal,
        "canonical_state_actor_geometry_sha256": actors,
        "scenario_source_bytes_sha256": source_sha,
        "scenario_seed_sha256": seed_sha,
        "latent_instance_sha256": latent_sha,
    }
    key = canonical_sha256(payload)
    return {
        "clone_payload": payload,
        "clone_key_sha256": key,
        "route_bin": ROUTE_BINS[route],
        "overlap_keys": {
            "route": route_sha,
            "state": _sha(f"state:{ordinal}:{key}"),
            "geometry": geometry_sha,
            "semantic": canonical_sha256(
                {
                    "family": semantic_family,
                    "tier": risk_tier,
                    "signal_stopline": signal,
                    "actor_geometry": actors,
                }
            ),
            "source": source_sha,
            "seed": seed_sha,
            "latent_instance": latent_sha,
            "composite": key,
        },
        "source_binding": {
            "artifact_path": "/sealed/source",
            "artifact_root_sha256": _sha("source-root"),
            "inventory_entry_path": f"/entries/{ordinal:04d}.json",
            "inventory_entry_sha256": _sha(f"entry:{ordinal}"),
        },
    }


def _feasible_candidates() -> list[dict]:
    upper = {
        (family, risk, route, source): 100
        for family in range(7)
        for risk in range(3)
        for route in range(3)
        for source in range(2)
    }
    table = find_feasible_counts({}, upper)
    assert table is not None
    rows = []
    ordinal = 0
    first_cell = None
    for cell, count in sorted(table.items()):
        for _ in range(count):
            rows.append(_candidate(*cell, ordinal))
            ordinal += 1
            first_cell = cell if first_cell is None else first_cell
    assert len(rows) == 100
    rows.append(_candidate(*first_cell, ordinal))
    return rows


def test_contract_and_independent_literal_review() -> None:
    value = contract()
    assert value["authority_sha256"] == AUTHORITY_SHA256
    assert value["denominator"]["planned_tick_slots"] == 19_200
    reviewed = review_contract_literal(
        value, accepted_industrial_contract=evaluation_contract_v3()
    )
    assert reviewed["capture_matrix"]["leaf_count"] == 161


def test_exact_feasible_selection_and_independent_margin_review() -> None:
    candidates = _feasible_candidates()
    result = select_lexicographically_smallest_feasible(candidates)
    assert result["selected_count"] == 100
    selected = [
        {
            key: value
            for key, value in row.items()
            if key not in {"cluster_ordinal", "cluster_id", "entry_sha256"}
        }
        for row in result["entries"]
    ]
    reviewed = review_selected_manifest_literal(selected)
    assert reviewed["selected_count"] == 100
    same_cell = [
        row["clone_key_sha256"]
        for row in candidates
        if (
            row["clone_payload"]["semantic_family"],
            row["clone_payload"]["risk_tier"],
            row["route_bin"],
            row["clone_payload"]["source_availability"],
        )
        == (
            selected[0]["clone_payload"]["semantic_family"],
            selected[0]["clone_payload"]["risk_tier"],
            selected[0]["route_bin"],
            selected[0]["clone_payload"]["source_availability"],
        )
    ]
    chosen_same_cell = {
        row["clone_key_sha256"]
        for row in selected
        if (
            row["clone_payload"]["semantic_family"],
            row["clone_payload"]["risk_tier"],
            row["route_bin"],
            row["clone_payload"]["source_availability"],
        )
        == (
            selected[0]["clone_payload"]["semantic_family"],
            selected[0]["clone_payload"]["risk_tier"],
            selected[0]["route_bin"],
            selected[0]["clone_payload"]["source_availability"],
        )
    }
    assert min(same_cell) in chosen_same_cell


def test_clone_key_and_overlap_fail_closed() -> None:
    row = _feasible_candidates()[0]
    validate_candidate(row)
    mutation = deepcopy(row)
    mutation["clone_payload"]["route_geometry_sha256"] = _sha("mutated")
    with pytest.raises(ValueError, match="clone key"):
        validate_candidate(mutation)
    selected_result = select_lexicographically_smallest_feasible(
        _feasible_candidates()
    )
    selected = [
        {
            key: value
            for key, value in item.items()
            if key not in {"cluster_ordinal", "cluster_id", "entry_sha256"}
        }
        for item in selected_result["entries"]
    ]
    authorities = (
        "bounded_single_route",
        "corrected_64_state_development",
        "training",
        "calibration",
        "legacy_nonholdout",
        "Fresh_B2",
        "Fresh_B3",
        "Fresh_B4",
    )
    forbidden = {
        authority: {
            level: [_sha(f"{authority}:{level}")]
            for level in (
                "route",
                "state",
                "geometry",
                "semantic",
                "source",
                "seed",
                "latent_instance",
                "composite",
            )
        }
        for authority in authorities
    }
    assert overlap_report(selected, forbidden)
    assert review_overlap_literal(selected, forbidden, authorities)
    forbidden["training"]["route"] = [selected[0]["overlap_keys"]["route"]]
    with pytest.raises(ValueError, match="training"):
        overlap_report(selected, forbidden)
    with pytest.raises(ValueError, match="training"):
        review_overlap_literal(selected, forbidden, authorities)


def test_latent_preimage_excludes_arm_and_is_unique8() -> None:
    clone = _sha("cluster")
    assert latent_seed(clone, 7) == latent_seed(clone, 7)
    assert latent_seed(clone, 7) != latent_seed(clone, 8)
    value = latent_tensor(clone, 7)
    assert value.shape == (8, 321, 81, 4)
    assert value.dtype == np.float32
    assert np.count_nonzero(value[0]) == 0
    assert len({hashlib.sha256(row.tobytes()).hexdigest() for row in value}) == 8


def test_capacity_formula_and_claim_mutations() -> None:
    decision = capacity_decision(
        free_bytes=100 * 1024**3,
        free_inodes=1_000_000,
        class_bytes_and_files={
            "execution": (1024**2, 100),
            "review": (512 * 1024, 50),
        },
    )
    assert decision["passed"] is True
    value = contract()
    value["claim_boundary"]["weighted_total_allowed"] = True
    with pytest.raises(ValueError, match="claim"):
        review_contract_literal(
            value, accepted_industrial_contract=evaluation_contract_v3()
        )


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("planned_tick_slots", 192),
        ("planned_formal_model_calls", 19_199),
    ],
)
def test_denominator_mutation_rejected(field: str, replacement: int) -> None:
    value = contract()
    value["denominator"][field] = replacement
    with pytest.raises(ValueError, match="denominator"):
        review_contract_literal(
            value, accepted_industrial_contract=evaluation_contract_v3()
        )
