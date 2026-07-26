from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_review as reviewer,
)
from scripts.integrations.freeze_diffusion_planner_v25_industrial_evaluation_contract import (
    freeze_contract,
)
from scripts.integrations.materialize_diffusion_planner_v25_industrial_evaluation_capability_matrix import (
    materialize,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_capability_matrix import (
    review_matrix,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_contract import (
    review_contract,
)


ROOT = Path(__file__).resolve().parents[2]


def _contract() -> dict:
    return producer.evaluation_contract()


def _matrix() -> dict:
    contract = _contract()
    return producer.capability_matrix(contract)


def _row(contract: dict, endpoint_id: str) -> dict:
    return next(
        row for row in contract["endpoints"] if row["endpoint_id"] == endpoint_id
    )


def _both_reject(mutated: dict) -> None:
    with pytest.raises(ValueError):
        producer.validate_evaluation_contract(mutated)
    with pytest.raises(ValueError):
        reviewer.review_contract_literal(mutated)


def test_high_authority_exact_ascii_canonical_sha() -> None:
    assert (
        hashlib.sha256(producer.HIGH_AUTHORITY_JSON.encode("utf-8")).hexdigest()
        == producer.HIGH_AUTHORITY_SHA256
        == reviewer.EXPECTED_AUTHORITY_SHA256
    )
    parsed = json.loads(producer.HIGH_AUTHORITY_JSON)
    assert (
        json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        == producer.HIGH_AUTHORITY_JSON
    )


def test_contract_and_capability_matrix_pass_both_oracles() -> None:
    contract = _contract()
    assert producer.validate_evaluation_contract(contract) == contract
    assert reviewer.review_contract_literal(contract) == contract
    matrix = producer.capability_matrix(contract)
    assert producer.validate_capability_matrix(matrix, contract) == matrix
    assert reviewer.review_capability_matrix_literal(matrix, contract) == matrix
    report = reviewer.independent_review_report(contract, matrix)
    assert report["endpoint_count"] == 56
    assert report["model_pool_selector_call_count"] == 0
    assert report["outcome_values_read"] is False


def test_full_contract_matrix_seal_chain_is_atomic_and_zero_run(tmp_path: Path) -> None:
    contract_dir = tmp_path / "contract"
    contract_root = freeze_contract(contract_dir)
    contract_review_dir = tmp_path / "contract_review"
    contract_review_root = review_contract(
        contract_review_dir, contract_dir, contract_root
    )
    matrix_dir = tmp_path / "matrix"
    matrix_root = materialize(
        matrix_dir,
        contract_dir,
        contract_root,
        contract_review_dir,
        contract_review_root,
    )
    matrix_review_dir = tmp_path / "matrix_review"
    matrix_review_root = review_matrix(
        matrix_review_dir,
        contract_dir,
        contract_root,
        contract_review_dir,
        contract_review_root,
        matrix_dir,
        matrix_root,
    )
    for directory, root in (
        (contract_dir, contract_root),
        (contract_review_dir, contract_review_root),
        (matrix_dir, matrix_root),
        (matrix_review_dir, matrix_review_root),
    ):
        assert len(root) == 64
        assert (directory / "ROOT_SHA256SUMS").is_file()
        report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        assert report["model_pool_selector_call_count"] == 0
        assert report["outcome_values_read"] is False


def test_endpoint_registry_is_exact_complete_and_has_no_weighted_total() -> None:
    contract = _contract()
    ids = [row["endpoint_id"] for row in contract["endpoints"]]
    assert len(ids) == len(set(ids)) == 56
    assert set(ids) == set(reviewer.EXPECTED_CORE)
    assert all(set(row) == set(producer.ENDPOINT_FIELDS) for row in contract["endpoints"])
    assert not any("safetycost" in endpoint_id.lower() for endpoint_id in ids)
    assert contract["statistics"]["weighted_total"] is False
    assert contract["legacy"]["role"] == "immutable_legacy_exploratory_diagnostic_only"
    assert contract["legacy"]["allowed_in_primary"] is False
    assert contract["legacy"]["allowed_in_pass_or_claim"] is False
    assert contract["legacy"]["allowed_in_training_support_or_adaptation"] is False


def test_capability_matrix_binds_every_endpoint_without_outcome_values() -> None:
    contract = _contract()
    matrix = _matrix()
    assert matrix["endpoint_count"] == 56
    assert {row["endpoint_id"] for row in matrix["rows"]} == {
        row["endpoint_id"] for row in contract["endpoints"]
    }
    assert sum(matrix["evidence_class_counts"].values()) == 56
    assert all(row["outcome_values_read"] is False for row in matrix["rows"])
    assert (
        _row(contract, "safety.post_encroachment_time_s")["evidence_class"]
        == "evidence_missing"
    )
    assert (
        _row(contract, "comfort.occupant_seat_iso_sae_conformity")[
            "evidence_class"
        ]
        == "scientifically_inapplicable"
    )


def test_vehicle_body_sample_accounting_constant_velocity_and_acceleration() -> None:
    t = np.arange(64, dtype=np.float64) * 0.1
    constant_velocity = np.column_stack((3.0 * t, np.zeros_like(t)))
    zero = producer.vehicle_body_planar_kinematics(
        constant_velocity, np.zeros(64, dtype=np.float64)
    )
    assert zero["interval_velocity"].shape == (63, 2)
    assert zero["world_acceleration"].shape == (62, 2)
    assert zero["filtered_longitudinal_acceleration"].shape == (52,)
    assert zero["filtered_longitudinal_jerk"].shape == (51,)
    assert np.allclose(zero["filtered_longitudinal_acceleration"], 0.0, atol=1e-12)
    assert np.allclose(zero["filtered_lateral_acceleration"], 0.0, atol=1e-12)
    assert np.allclose(zero["filtered_longitudinal_jerk"], 0.0, atol=1e-12)

    acceleration_world_y = np.column_stack(
        (np.zeros_like(t), 0.5 * 2.0 * t**2)
    )
    forward_y = producer.vehicle_body_planar_kinematics(
        acceleration_world_y, np.full(64, np.pi / 2.0)
    )
    assert np.allclose(
        forward_y["body_longitudinal_acceleration"], 2.0, atol=1e-12
    )
    assert np.allclose(forward_y["body_lateral_acceleration"], 0.0, atol=1e-12)
    assert np.allclose(
        forward_y["filtered_longitudinal_acceleration"], 2.0, atol=1e-12
    )


def test_vehicle_body_impulse_and_high_frequency_chatter_use_frozen_filter() -> None:
    raw_acceleration = np.where(np.arange(62) % 2 == 0, 1.0, -1.0)
    velocity = np.zeros(63, dtype=np.float64)
    velocity[1:] = np.cumsum(raw_acceleration) * 0.1
    position_x = np.zeros(64, dtype=np.float64)
    position_x[1:] = np.cumsum(velocity) * 0.1
    result = producer.vehicle_body_planar_kinematics(
        np.column_stack((position_x, np.zeros(64))), np.zeros(64)
    )
    assert np.max(np.abs(result["body_longitudinal_acceleration"])) == pytest.approx(
        1.0
    )
    assert np.max(
        np.abs(result["filtered_longitudinal_acceleration"])
    ) == pytest.approx(1.0 / 11.0)
    assert result["filtered_longitudinal_acceleration"].shape == (52,)
    assert result["filtered_longitudinal_jerk"].shape == (51,)


def test_planar_vdv_like_is_descriptive_and_uses_dt() -> None:
    values = np.full(52, 2.0)
    expected = (52.0 * (2.0**4) * 0.1) ** 0.25
    assert producer.planar_kinematic_vdv_like(values) == pytest.approx(expected)
    row = _row(_contract(), "comfort.planar_kinematic_vdv_like_longitudinal")
    assert "not ISO VDV" in row["industrial_interpretation"]
    with pytest.raises(ValueError):
        producer.planar_kinematic_vdv_like(values, dt_s=0.2)


@pytest.mark.parametrize(
    ("endpoint_id", "field", "replacement"),
    [
        ("safety.collision_any", "units", "score"),
        ("safety.collision_any", "sample_rate", "20 Hz"),
        (
            "comfort.body_longitudinal_filtered_acceleration_summary",
            "filter",
            "causal_5_point",
        ),
        (
            "comfort.filtered_longitudinal_jerk_control_smoothness_summary",
            "formula",
            "raw 0.1s scalar-speed second difference occupant jerk",
        ),
        (
            "safety.post_encroachment_time_s",
            "missing_policy",
            "missing becomes 0",
        ),
        (
            "safety.collision_any",
            "cluster_unit",
            "ticks and rows are independent n",
        ),
        (
            "safety.certified_red_crossing_any",
            "opportunity_denominator",
            "red-phase intervals only",
        ),
        (
            "safety.drivable_outside_fraction_max",
            "formula",
            "five_point_drivable_coverage_failure",
        ),
        (
            "operations.ordered_route_arc_final_m",
            "formula",
            "stateless nearest route segment",
        ),
        (
            "safety.post_encroachment_time_s",
            "evidence_class",
            "reconstructable_with_frozen_transform",
        ),
        (
            "comfort.occupant_seat_iso_sae_conformity",
            "industrial_interpretation",
            "ISO 2631 and SAE J2834 conformity PASS",
        ),
    ],
)
def test_semantic_mutations_fail_even_when_payload_is_rehashed(
    endpoint_id: str, field: str, replacement: object
) -> None:
    contract = _contract()
    _row(contract, endpoint_id)[field] = replacement
    hashlib.sha256(producer.canonical_bytes(contract)).hexdigest()
    _both_reject(contract)


def test_safetycost_reweight_or_primary_promotion_fails_closed() -> None:
    contract = _contract()
    contract["legacy"]["safetycost_formula"] = "1*collision_any"
    _both_reject(contract)
    contract = _contract()
    contract["legacy"]["allowed_in_primary"] = True
    _both_reject(contract)
    contract = _contract()
    injected = copy.deepcopy(contract["endpoints"][0])
    injected["endpoint_id"] = "safety.primary_safetycost"
    injected["formula"] = producer.LEGACY_SAFETYCOST_FORMULA
    contract["endpoints"].append(injected)
    contract["endpoint_count"] += 1
    _both_reject(contract)


def test_filter_window_edge_and_dt_mutations_fail_closed() -> None:
    for key, value in (
        ("dt_s", 0.2),
        ("filter_coefficients", [0.2] * 5),
        ("filter_width_samples", 5),
        ("filter_window_s", 0.5),
        ("valid_only", False),
        ("padding", True),
        ("filtered_acceleration_count", 60),
        ("filtered_jerk_count", 52),
    ):
        contract = _contract()
        contract["comfort_transform"][key] = value
        _both_reject(contract)


def test_unknown_duplicate_or_deleted_endpoint_fails_closed() -> None:
    contract = _contract()
    contract["endpoints"][0]["unknown"] = True
    _both_reject(contract)
    contract = _contract()
    contract["endpoints"].append(copy.deepcopy(contract["endpoints"][0]))
    contract["endpoint_count"] += 1
    _both_reject(contract)
    contract = _contract()
    contract["endpoints"].pop()
    contract["endpoint_count"] -= 1
    _both_reject(contract)


def test_selector_training_and_evaluation_recoupling_fails_closed() -> None:
    contract = _contract()
    contract["evaluation_and_selector_training_decoupled"] = False
    _both_reject(contract)
    contract = _contract()
    contract["legacy"]["allowed_in_training_support_or_adaptation"] = True
    _both_reject(contract)


def test_red_denominators_are_distinct_and_slow_crossing_is_unthresholded() -> None:
    contract = _contract()
    crossing = _row(contract, "safety.certified_red_crossing_any")
    encounter = _row(contract, "safety.certified_red_encounter_opportunity_count")
    interval = _row(contract, "safety.certified_red_phase_interval_count")
    assert "no speed threshold" in crossing["event_definition"]
    assert "0.4m/s" in crossing["event_definition"]
    assert encounter["units"] == "encounter_count"
    assert interval["units"] == "interval_count"
    assert "reported separately and never mixed" in crossing["opportunity_denominator"]


def test_route_and_containment_proxies_cannot_substitute_primary_endpoints() -> None:
    contract = _contract()
    route = _row(contract, "operations.ordered_route_arc_final_m")
    containment = _row(contract, "safety.drivable_outside_fraction_max")
    assert "nonadjacent nearest-segment jumps forbidden" in route["applicability"]
    assert "full ego polygon" in containment["input_shape"]
    assert containment["legacy_alias"] == (
        "five_point_offroad_is_legacy_only_not_a_substitute"
    )


def test_statistics_are_per_run_clustered_vector_and_fail_closed_missing() -> None:
    stats = _contract()["statistics"]
    assert stats["per_run_first"] is True
    assert stats["ticks_rows_arms_seeds_as_independent_n"] is False
    assert stats["weighted_total"] is False
    assert stats["complete_case_claim_allowed"] is False
    assert stats["full_denominator_missing_retention"] is True
    assert stats["numeric_margin"] == (
        "numeric_margin_not_authorized_until_future_preregistration"
    )
    assert "exact zero delta is tie" in stats["better_tie_worse"]


def test_reviewer_does_not_import_producer_or_shared_oracles() -> None:
    source = inspect.getsource(reviewer)
    assert "diffusion_planner_v25_industrial_evaluation_contract" not in source
    assert "from .diffusion_planner_v25_industrial" not in source
    assert "EXPECTED_CORE" in source
    assert "SOURCE_ROOTS" in source


def test_capability_root_class_and_missing_mutations_fail_closed() -> None:
    contract = _contract()
    matrix = producer.capability_matrix(contract)
    matrix["rows"][0]["source_artifact_root_sha256"] = "1" * 64
    with pytest.raises(ValueError):
        producer.validate_capability_matrix(matrix, contract)
    with pytest.raises(ValueError):
        reviewer.review_capability_matrix_literal(matrix, contract)

    matrix = producer.capability_matrix(contract)
    pet = next(
        row
        for row in matrix["rows"]
        if row["endpoint_id"] == "safety.post_encroachment_time_s"
    )
    pet["evidence_class"] = "directly_reconstructable"
    pet["source_artifact_root_sha256"] = producer.EXECUTION_ROOT
    pet["source_sha256"] = producer.EXECUTION_ROOT
    with pytest.raises(ValueError):
        producer.validate_capability_matrix(matrix, contract)
    with pytest.raises(ValueError):
        reviewer.review_capability_matrix_literal(matrix, contract)


def test_official_reference_links_are_current_and_scope_only() -> None:
    references = {(row["name"], row["url"]): row for row in _contract()["references"]}
    assert (
        "ISO 2631-1:1997",
        "https://www.iso.org/standard/7612.html",
    ) in references
    assert (
        "SAE J2834_202504",
        "https://saemobilus.sae.org/standards/"
        "j2834_202504-ride-index-structure-development-methodology",
    ) in references
    assert (
        "ISO 34502:2022",
        "https://www.iso.org/standard/78951.html",
    ) in references
    assert all(row["accessed"] == "2026-07-26" for row in references.values())
    assert all("conformity" in row["use"] or "not certification" in row["use"] or "scope rationale only" in row["use"] for row in references.values())


def test_no_model_outcome_or_old_artifact_write_path_in_modules() -> None:
    producer_source = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_industrial_evaluation_contract.py"
    ).read_text(encoding="utf-8")
    reviewer_source = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_industrial_evaluation_review.py"
    ).read_text(encoding="utf-8")
    for source in (producer_source, reviewer_source):
        assert "model(" not in source
        assert "torch.load" not in source
        assert "mark_scientific" not in source
        assert "terminate_scientific" not in source
        assert "os.replace" not in source
