from __future__ import annotations

from copy import deepcopy

import pytest

from camp_core.integrations import (
    diffusion_planner_v25_project_authored_multiroute_source as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_project_authored_multiroute_source_review as reviewer,
)


CONTRACT_ROOT = "1" * 64


def _reseal_record(value: dict) -> dict:
    row = deepcopy(value)
    row.pop("source_record_sha256", None)
    row["source_record_sha256"] = producer.canonical_sha256(row)
    return row


def test_contract_freezes_corrected_authority_and_zero_execution() -> None:
    contract = producer.source_contract()
    assert contract["authority_sha256"] == producer.AUTHORITY_SHA256
    assert (
        contract["audited_generator_base_sha256"]["no_signal_authority"]
        == "82b363c53f8d53ce0e57e0cfcb93f7f9697807601b43f552c034cd0f338b6a5b"
    )
    assert contract["universe"]["candidate_ceiling"] == 252
    assert contract["selection"]["selected_count"] == 100
    assert contract["execution_boundary"]["model_pool_selector_calls"] == 0
    reviewer.review_contract_literal(contract)


def test_ordinal_formula_and_candidate_253_fail_closed() -> None:
    assert producer.decode_ordinal(0)["family"] == producer.FAMILIES[0]
    assert producer.decode_ordinal(0)["replica"] == 0
    assert producer.decode_ordinal(1)["replica"] == 1
    last = producer.decode_ordinal(251)
    assert last["family"] == producer.FAMILIES[-1]
    assert last["risk_tier"] == producer.RISK_TIERS[-1]
    assert last["route_bin"] == producer.ROUTE_BINS[-1]
    assert last["source_availability"] == producer.SOURCE_AVAILABILITY[-1]
    assert last["replica"] == 1
    with pytest.raises(ValueError):
        producer.decode_ordinal(252)


@pytest.mark.parametrize("ordinal", [0, 1, 17, 109, 250, 251])
def test_source_record_exact_geometry_signal_and_independent_review(
    ordinal: int,
) -> None:
    built = producer.build_source_record(ordinal)
    record = built["record"]
    raw = built["map_bytes"]
    assert producer.validate_source_record(record, raw) == record
    assert reviewer.review_source_record_literal(record, raw) == record
    assert record["map"]["license_spdx"] == "MIT"
    assert record["map"]["third_party_payload_derived"] is False
    assert record["route"]["spawn_to_goal_reachable"] is True
    assert record["selection_latent_instance"]["unique_row_sha256_cardinality"] == 8


def test_no_signal_hidden_signal_and_mapped_chain_mutations_fail_closed() -> None:
    no_signal = producer.build_source_record(1)
    hidden = no_signal["map_bytes"].replace(
        b"</osm>\n",
        b'<node id="999999999" lat="35" lon="139"><tag k="type" '
        b'v="traffic_light"/></node></osm>\n',
    )
    with pytest.raises(ValueError):
        reviewer.review_source_record_literal(no_signal["record"], hidden)

    mapped = producer.build_source_record(0)
    missing = mapped["map_bytes"].replace(b'v="light_bulbs"', b'v="other_value"')
    with pytest.raises(ValueError):
        reviewer.review_source_record_literal(mapped["record"], missing)


def test_seed_cell_license_and_source_sha_mutations_fail_even_when_resealed() -> None:
    built = producer.build_source_record(37)
    for mutate in (
        lambda row: row["seeds"].__setitem__("actor", row["seeds"]["actor"] + 1),
        lambda row: row["cell"].__setitem__("risk_tier", "easy"),
        lambda row: row["map"].__setitem__("license_spdx", "UNKNOWN"),
        lambda row: row["route"]["geometry"].__setitem__("lane_width_m", 9.0),
    ):
        changed = deepcopy(built["record"])
        mutate(changed)
        changed = _reseal_record(changed)
        with pytest.raises(ValueError):
            producer.validate_source_record(changed, built["map_bytes"])
        with pytest.raises(ValueError):
            reviewer.review_source_record_literal(changed, built["map_bytes"])


def test_clone_preimage_and_source_binding_are_independently_rebuilt() -> None:
    built = producer.build_source_record(11)
    candidate = producer.candidate_from_source_record(
        built["record"], source_contract_root_sha256=CONTRACT_ROOT
    )
    reviewer.review_candidate_literal(
        built["record"], candidate, contract_root_sha256=CONTRACT_ROOT
    )
    changed = deepcopy(candidate)
    changed["clone_payload"]["semantic_family"] = producer.FAMILIES[-1]
    changed["clone_key_sha256"] = producer.canonical_sha256(changed["clone_payload"])
    changed["overlap_keys"]["composite"] = changed["clone_key_sha256"]
    with pytest.raises(ValueError):
        reviewer.review_candidate_literal(
            built["record"], changed, contract_root_sha256=CONTRACT_ROOT
        )


def test_full_252_universe_exact_minimal_100_set_and_zero_overlap_review() -> None:
    universe = producer.build_universe(
        source_contract_root_sha256=CONTRACT_ROOT
    )
    assert len(universe["records"]) == 252
    assert len(universe["maps"]) == 252
    assert len(universe["candidates"]) == 252
    manifest = universe["selected_manifest"]
    assert manifest["candidate_ceiling"] == 252
    assert manifest["selected_count"] == 100
    assert len(set(manifest["selected_clone_key_sha256"])) == 100
    forbidden = {
        authority: {level: [] for level in producer.ZERO_OVERLAP_LEVELS}
        for authority in (
            "training",
            "calibration",
            "legacy_nonholdout",
            "bounded_single_route",
            "corrected_64_state_development",
            "Fresh_B2",
            "Fresh_B3",
            "Fresh_B4",
        )
    }
    reviewed = reviewer.review_materialization_literal(
        records=universe["records"],
        maps=universe["maps"],
        candidates=universe["candidates"],
        selected_manifest=manifest,
        contract_root_sha256=CONTRACT_ROOT,
        forbidden=forbidden,
    )
    assert reviewed["candidate_count"] == 252
    assert reviewed["selected_count"] == 100
    assert reviewed["geometry_unique_count"] == 252


def test_drop_replacement_overlap_and_nonminimal_selection_fail_closed() -> None:
    universe = producer.build_universe(
        source_contract_root_sha256=CONTRACT_ROOT
    )
    selected = universe["selected_manifest"]["selected_clone_key_sha256"]
    nonselected = next(
        row["clone_key_sha256"]
        for row in universe["candidates"]
        if row["clone_key_sha256"] not in set(selected)
    )
    changed = deepcopy(universe["selected_manifest"])
    changed["selected_clone_key_sha256"][-1] = nonselected
    with pytest.raises(ValueError):
        reviewer.review_materialization_literal(
            records=universe["records"],
            maps=universe["maps"],
            candidates=universe["candidates"],
            selected_manifest=changed,
            contract_root_sha256=CONTRACT_ROOT,
            forbidden={
                authority: {level: [] for level in producer.ZERO_OVERLAP_LEVELS}
                for authority in (
                    "training",
                    "calibration",
                    "legacy_nonholdout",
                    "bounded_single_route",
                    "corrected_64_state_development",
                    "Fresh_B2",
                    "Fresh_B3",
                    "Fresh_B4",
                )
            },
        )

    first = universe["selected_manifest"]["entries"][0]
    overlap = {
        authority: {level: [] for level in producer.ZERO_OVERLAP_LEVELS}
        for authority in (
            "training",
            "calibration",
            "legacy_nonholdout",
            "bounded_single_route",
            "corrected_64_state_development",
            "Fresh_B2",
            "Fresh_B3",
            "Fresh_B4",
        )
    }
    overlap["training"]["geometry"] = [first["overlap_keys"]["geometry"]]
    with pytest.raises(ValueError):
        reviewer.review_materialization_literal(
            records=universe["records"],
            maps=universe["maps"],
            candidates=universe["candidates"],
            selected_manifest=universe["selected_manifest"],
            contract_root_sha256=CONTRACT_ROOT,
            forbidden=overlap,
        )

