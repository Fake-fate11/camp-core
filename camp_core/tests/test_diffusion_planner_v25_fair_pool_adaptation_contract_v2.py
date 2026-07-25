from __future__ import annotations

from copy import deepcopy
import hashlib
import math

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v2 as review_module,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest as manifest_module,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    action_equivalent,
    adaptation_contract_v2,
    bootstrap_upper_threshold,
    clopper_pearson_upper,
    decide_endpoint_statuses,
    empirical_quantile_higher,
    numeric_endpoint_result,
    sha256_json,
    spearman_rank_error,
    validate_contract_v2,
    validate_endpoint_result_keyset,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_review_v2 import (
    literal_action_equivalent,
    literal_b4_case_clone_payload,
    literal_bootstrap_upper,
    literal_cp_upper,
    literal_numeric_endpoint_result,
    literal_rank_error,
    review_contract_literal_v2,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_input_manifest import (
    canonical_bytes,
    materialize_b4_forbidden_clone_manifest,
    materialize_input_only_manifest,
    resample_route_polyline_0_5m,
    validate_preflight_receipt,
)


def _rehash(value: dict[str, object]) -> dict[str, object]:
    value = deepcopy(value)
    value.pop("contract_payload_sha256", None)
    value["contract_payload_sha256"] = sha256_json(value)
    return value


def _mutated(path: tuple[object, ...], replacement: object) -> dict[str, object]:
    value: object = deepcopy(adaptation_contract_v2())
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = replacement  # type: ignore[index]
    return _rehash(value)  # type: ignore[arg-type]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_record(
    ordinal: int, *, map_sha: str, route_sha: str
) -> dict[str, object]:
    return {
        "source_state_ordinal": ordinal,
        "map_geometry_sha256": map_sha,
        "route_asset_sha256": route_sha,
        "scenario_source_content_sha256": _sha(f"scenario:{ordinal}"),
        "spawn_pose": {
            "x_m": ordinal * 0.01,
            "y_m": -1.0,
            "z_m": 0.0,
            "heading_rad": math.pi + 0.00005,
        },
        "goal_pose": {
            "x_m": 3.0 + ordinal * 0.01,
            "y_m": 2.0,
            "z_m": 0.0,
            "heading_rad": 0.0,
        },
        "ordered_route_polyline_xy_m": [
            [ordinal * 0.01, 0.0],
            [1.0 + ordinal * 0.01, 0.0],
            [1.0 + ordinal * 0.01, 1.25],
        ],
        "dynamic_actors_initial": [],
        "actual_input_sha256": _sha(f"input:{ordinal}"),
        "actual_state_sha256": _sha(f"state:{ordinal}"),
        "actual_latent_tensor_sha256": _sha(f"latent:{ordinal}"),
    }


def _b4_case(index: int) -> dict[str, object]:
    semantic = {
        "actors": [],
        "family": "synthetic_input_only",
        "parameters": {"ordinal": index},
        "route_polyline_local_m": [[0.0, 0.0], [2.0, 0.0]],
        "schema_version": "synthetic_semantic_v1",
        "semantic_variant": f"variant_{index}",
        "signal": {
            "current_phase": "none",
            "mapped_source_required": False,
            "source_mode": "none",
        },
        "stop_line_local_m": [],
        "tier": "synthetic",
    }
    mapped = {
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": sha256_json(semantic),
    }
    case = {
        "actors": [],
        "corridor_group_sha256": _sha(f"corridor:{index}"),
        "family": "synthetic_input_only",
        "holdout_outcome_consumed": False,
        "map_family_id": "map",
        "mapped_signal_authority": mapped,
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "parameter_block_id": f"p{index}",
        "parameters": {},
        "phase_authority_mode": "none",
        "record_key": f"record{index}",
        "route_family_id": "route",
        "route_identity_sha256": _sha(f"route:{index}"),
        "route_spec": {
            "goal_pose": [2.0 + index * 0.01, 0.0, 0.0],
            "lanelet_ids": [1],
            "start_pose": [index * 0.01, 0.0, 0.0],
        },
        "runner_eligible": True,
        "scenario_id": f"scenario{index}",
        "schema_version": "synthetic_case_v1",
        "seeds": [1, 2, 3, 4, 5],
        "semantic_variant": f"variant_{index}",
        "signal": {"mapped_source_required": False, "phase": "none"},
        "signal_source_class": "none",
        "source_availability": {"mapped_traffic_light": False},
        "source_map_path": "map.osm",
        "source_map_sha256": _sha("map"),
        "source_requirements": [],
        "source_stratum": {
            "branch_intersection": False,
            "traffic_light": False,
        },
        "split": "fresh_b4",
        "tier": "synthetic",
    }
    return {
        "calibration_outcomes_consumed": False,
        "candidate_generation_executed": False,
        "case": case,
        "fresh_b2_opened": False,
        "identity_ordinal": index,
        "map_artifact": "map",
        "mapped_signal_authority": mapped,
        "model_loaded": False,
        "outcome_fields_consumed": [],
        "route_polyline_world_m": [
            [index * 0.01, 0.0],
            [2.0 + index * 0.01, 0.0],
        ],
        "scenario_identity_sha256": _sha(f"identity:{index}"),
        "schema_version": "synthetic_prepared_v1",
        "status": "prepared",
        "training_executed": False,
    }


def test_contract_and_independent_semantic_review_pass() -> None:
    contract = adaptation_contract_v2()
    assert validate_contract_v2(contract) == contract
    reviewed = review_contract_literal_v2(contract)
    assert reviewed["status"] == "passed_independent_executable_semantic_review"
    assert reviewed["state_spec_count"] == 128
    assert reviewed["endpoint_count"] == 37


def test_manifest_clone_formula_and_route_endpoint_are_exact() -> None:
    contract = adaptation_contract_v2()
    spec = contract["state_specifications"]["development_calibration"][0]
    source = _source_record(
        0,
        map_sha=spec["map_geometry_sha256"],
        route_sha=spec["route_asset_sha256"],
    )
    source["dynamic_actors_initial"] = [
        {
            "class": "vehicle",
            "length_m": 4.5,
            "width_m": 2.0,
            "x_m": 3.0005,
            "y_m": -0.0005,
            "heading_rad": -math.pi,
            "speed_mps": 1.0005,
        },
        {
            "class": "bicycle",
            "length_m": 1.8,
            "width_m": 0.6,
            "x_m": 2.0,
            "y_m": 1.0,
            "heading_rad": 0.0,
            "speed_mps": 0.0,
        },
    ]
    manifest = materialize_input_only_manifest(
        state_spec=spec, source_record=source
    )
    payload = manifest["clone_payload"]
    assert payload["spawn_pose_quantized"]["heading_1e4rad"] == -31415
    assert payload["dynamic_actor_initial_state_sorted"][0]["class"] == "bicycle"
    assert payload["route_polyline_resampled_0_5m_quantized"][-1] == [1000, 1250]
    assert resample_route_polyline_0_5m([[0.0, 0.0], [1.25, 0.0]]) == [
        [0, 0],
        [500, 0],
        [1000, 0],
        [1250, 0],
    ]


def test_synthetic_b4_forbidden_manifest_and_64_plus_64_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = [_b4_case(index) for index in range(100)]
    raw = canonical_bytes(cases)
    raw_sha = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(
        manifest_module, "B4_PREPARED_RUNTIME_CASES_SHA256", raw_sha
    )
    forbidden = materialize_b4_forbidden_clone_manifest(raw)
    assert len(forbidden["clone_keys_sorted"]) == 100
    first_literal = literal_b4_case_clone_payload(cases[0])
    assert forbidden["entries"][0]["clone_key_sha256"] == sha256_json(
        first_literal
    )
    contract = adaptation_contract_v2()
    calibration_specs = contract["state_specifications"][
        "development_calibration"
    ]
    validation_specs = contract["state_specifications"][
        "independent_validation"
    ]
    calibration = [
        materialize_input_only_manifest(
            state_spec=spec,
            source_record=_source_record(
                spec["source_state_ordinal"],
                map_sha=spec["map_geometry_sha256"],
                route_sha=spec["route_asset_sha256"],
            ),
        )
        for spec in calibration_specs
    ]
    validation = [
        materialize_input_only_manifest(
            state_spec=spec,
            source_record=_source_record(
                spec["source_state_ordinal"],
                map_sha=spec["map_geometry_sha256"],
                route_sha=spec["route_asset_sha256"],
            ),
        )
        for spec in validation_specs
    ]
    receipt = {
        "schema_version": (
            "camp_dp_v25_fair_pool_input_only_preflight_receipt_v1"
        ),
        "contract_root_sha256": _sha("contract"),
        "b4_forbidden_manifest_authority": {
            "preopen_path": manifest_module.B4_PREOPEN_PATH,
            "preopen_root_sha256": manifest_module.B4_PREOPEN_ROOT_SHA256,
            "prepared_runtime_cases_sha256": raw_sha,
            "forbidden_manifest_sha256": forbidden["manifest_sha256"],
            "forbidden_clone_key_count": 100,
        },
        "calibration_manifests": calibration,
        "validation_manifests": validation,
        "model_pool_selector_call_count_before_receipt": 0,
        "within_calibration_overlap_count": 0,
        "within_validation_overlap_count": 0,
        "cross_split_overlap_count": 0,
        "b4_overlap_count": 0,
        "status": "passed_before_first_model_pool_selector_call",
    }
    assert (
        validate_preflight_receipt(
            receipt,
            calibration_spec_sha256s=[
                spec["state_spec_sha256"] for spec in calibration_specs
            ],
            validation_spec_sha256s=[
                spec["state_spec_sha256"] for spec in validation_specs
            ],
            b4_forbidden_manifest=forbidden,
        )
        == receipt
    )
    duplicate = deepcopy(receipt)
    duplicate["validation_manifests"][0]["clone_payload"] = deepcopy(
        duplicate["calibration_manifests"][0]["clone_payload"]
    )
    duplicate["validation_manifests"][0]["clone_key_sha256"] = duplicate[
        "calibration_manifests"
    ][0]["clone_key_sha256"]
    item = dict(duplicate["validation_manifests"][0])
    item.pop("manifest_sha256")
    duplicate["validation_manifests"][0]["manifest_sha256"] = sha256_json(item)
    duplicate["cross_split_overlap_count"] = 1
    with pytest.raises(ValueError, match="cross_split_overlap_count"):
        validate_preflight_receipt(
            duplicate,
            calibration_spec_sha256s=[
                spec["state_spec_sha256"] for spec in calibration_specs
            ],
            validation_spec_sha256s=[
                spec["state_spec_sha256"] for spec in validation_specs
            ],
            b4_forbidden_manifest=forbidden,
        )


def test_quantile_bootstrap_and_cp_are_reproducible() -> None:
    values = np.linspace(0.0, 1.0, 64)
    assert empirical_quantile_higher(values, 0.99) == 1.0
    producer = bootstrap_upper_threshold(values, resolution_floor=1e-9)
    reviewer = literal_bootstrap_upper(values, 1e-9)
    assert producer == reviewer
    assert producer == bootstrap_upper_threshold(values, resolution_floor=1e-9)
    for k in (0, 2, 3):
        assert clopper_pearson_upper(k, 64) == literal_cp_upper(k, 64)
    assert clopper_pearson_upper(2, 64) <= 0.10
    assert clopper_pearson_upper(3, 64) > 0.10


def test_numeric_endpoint_equal_threshold_k2_pass_k3_blocks() -> None:
    contract = adaptation_contract_v2()
    endpoint = "trajectory.ego.position_max_m"
    equal = [1.0] * 64
    equal[-2:] = [1.1, 1.1]
    producer = numeric_endpoint_result(
        contract, endpoint, equal, threshold=1.0
    )
    reviewer = literal_numeric_endpoint_result(endpoint, equal, 1.0)
    assert producer == reviewer
    assert producer["status"] == "pass"
    three = list(equal)
    three[-3] = 1.1
    assert numeric_endpoint_result(
        contract, endpoint, three, threshold=1.0
    )["status"] == "cross_mode_functional_drift"
    missing = equal[:-1]
    assert numeric_endpoint_result(
        contract, endpoint, missing, threshold=1.0
    )["status"] == "evidence_missing"


def test_rank_ties_constants_and_shared_eligibility() -> None:
    mask = [True] * 8
    tied = [1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0]
    assert spearman_rank_error(tied, tied, mask, mask) == literal_rank_error(
        tied, tied, mask, mask
    )
    constant = [1.0] * 8
    assert spearman_rank_error(constant, constant, mask, mask) == {
        "status": "computed",
        "rank_error": 0.0,
    }
    assert spearman_rank_error(constant, tied, mask, mask)["status"] == (
        "ambiguous_evidence_missing"
    )
    one = [True] + [False] * 7
    assert spearman_rank_error(tied, tied, one, one)["status"] == (
        "ambiguous_evidence_missing"
    )


def test_action_equivalence_equal_boundary_wrap_and_failures() -> None:
    left = np.zeros((80, 4), dtype=np.float64)
    right = left.copy()
    right[:, 0] = 0.05
    right[:, 2] = 2 * math.pi - 0.01
    right[:, 3] = 0.05
    producer = action_equivalent(
        left,
        right,
        left_executable="executable",
        right_executable="executable",
        left_terminal="complete",
        right_terminal="complete",
    )
    reviewer = literal_action_equivalent(
        left,
        right,
        "executable",
        "executable",
        "complete",
        "complete",
    )
    assert producer == reviewer
    assert producer["status"] == "pass"
    right[0, 0] = 0.0500001
    assert action_equivalent(
        left,
        right,
        left_executable="executable",
        right_executable="executable",
        left_terminal="complete",
        right_terminal="complete",
    )["status"] == "cross_mode_functional_drift"
    with pytest.raises(ValueError):
        action_equivalent(
            left[:79],
            right[:79],
            left_executable="executable",
            right_executable="executable",
            left_terminal="complete",
            right_terminal="complete",
        )
    right[0, 0] = float("nan")
    with pytest.raises(ValueError):
        action_equivalent(
            left,
            right,
            left_executable="executable",
            right_executable="executable",
            left_terminal="complete",
            right_terminal="complete",
        )


def test_endpoint_registry_is_exhaustive_and_unknown_omission_fails() -> None:
    contract = adaptation_contract_v2()
    registry = contract["endpoint_registry"]
    ids = [item["id"] for item in registry]
    assert len(ids) == len(set(ids)) == 37
    assert sum(item["id"].startswith("atom.") for item in registry) == 14
    assert all(
        item["resolution_floor"] is not None
        for item in registry
        if item["kind"] == "numeric_threshold"
    )
    fields = contract["decision_table"]["endpoint_result_exact_fields"]
    results = [
        {
            "endpoint_id": endpoint_id,
            "applicable": True,
            "state_denominator": 64,
            "missing_state_count": 0,
            "threshold": 1.0,
            "exceedance_count": 0,
            "clopper_pearson_upper_95": literal_cp_upper(0, 64),
            "status": "pass",
        }
        for endpoint_id in ids
    ]
    assert set(validate_endpoint_result_keyset(contract, results)) == set(ids)
    with pytest.raises(ValueError):
        validate_endpoint_result_keyset(contract, results[:-1])
    unknown = deepcopy(results)
    unknown[0]["unknown"] = True
    assert set(unknown[0]) != set(fields)
    with pytest.raises(ValueError):
        validate_endpoint_result_keyset(contract, unknown)


def test_decision_topology_missing_precedence_and_within_gate() -> None:
    contract = adaptation_contract_v2()
    ids = contract["decision_table"]["required_endpoint_ids"]
    statuses = {endpoint_id: "pass" for endpoint_id in ids}
    assert decide_endpoint_statuses(
        contract, statuses, both_within_modes_pass=True
    )["status"] == "PASS"
    assert decide_endpoint_statuses(
        contract, statuses, both_within_modes_pass=False
    ) == {
        "status": "BLOCK",
        "classification": "within_mode_generator_instability",
    }
    statuses[ids[0]] = "ambiguous_evidence_missing"
    assert decide_endpoint_statuses(
        contract, statuses, both_within_modes_pass=True
    )["classification"] == "evidence_missing"
    del statuses[ids[-1]]
    with pytest.raises(ValueError):
        decide_endpoint_statuses(
            contract, statuses, both_within_modes_pass=True
        )


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("threshold_algorithm", "q"), 0.95),
        (("threshold_algorithm", "bootstrap", "resamples"), 9999),
        (
            (
                "threshold_algorithm",
                "validation",
                "cp_upper",
                "k_eq_0",
            ),
            "0",
        ),
        (("repeat_authority", "repeat_count_per_state_per_mode"), 3),
        (
            (
                "state_specifications",
                "development_calibration",
                0,
                "split",
            ),
            "independent_validation",
        ),
        (
            (
                "training_scale_authority",
                "index",
                0,
                "index",
            ),
            1,
        ),
        (
            ("score_margin_rank", "near_tie_equality"),
            "margin < near_tie_threshold",
        ),
        (
            ("score_margin_rank", "spearman", "tie_rank"),
            "ordinal_rank",
        ),
        (
            ("action_equivalence", "position_max_m_pass"),
            "<=0.5",
        ),
        (
            ("decision_table", "numeric_endpoint_pass"),
            "exceedance_count_le_64",
        ),
        (
            ("run_and_claim_boundary", "acquisition_authorized"),
            True,
        ),
    ],
)
def test_semantic_mutations_fail_even_if_rehashed_and_reviewer_pin_repointed(
    path: tuple[object, ...],
    replacement: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _mutated(path, replacement)
    with pytest.raises(ValueError):
        validate_contract_v2(candidate)
    monkeypatch.setattr(
        review_module,
        "EXPECTED_PAYLOAD_SHA256",
        candidate["contract_payload_sha256"],
    )
    with pytest.raises(ValueError):
        review_contract_literal_v2(candidate)


def test_deleted_endpoint_and_claim_scope_mutation_fail_semantically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = adaptation_contract_v2()
    candidate["endpoint_registry"].pop()
    candidate["endpoint_registry_sha256"] = sha256_json(
        candidate["endpoint_registry"]
    )
    candidate["decision_table"]["required_endpoint_ids"] = [
        item["id"] for item in candidate["endpoint_registry"]
    ]
    candidate["decision_table"]["required_endpoint_count"] -= 1
    candidate = _rehash(candidate)
    monkeypatch.setattr(
        review_module,
        "EXPECTED_PAYLOAD_SHA256",
        candidate["contract_payload_sha256"],
    )
    with pytest.raises(ValueError, match="endpoint registry semantics"):
        review_contract_literal_v2(candidate)
    scope = _mutated(
        ("scope", "general_ood_or_architecture_equivalence_claim"), True
    )
    monkeypatch.setattr(
        review_module,
        "EXPECTED_PAYLOAD_SHA256",
        scope["contract_payload_sha256"],
    )
    with pytest.raises(ValueError, match="scope"):
        review_contract_literal_v2(scope)
