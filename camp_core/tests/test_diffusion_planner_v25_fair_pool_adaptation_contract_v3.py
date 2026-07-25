from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import math

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v3 as review_module,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest as legacy_manifest,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest_v2 as manifest_module,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v3 import (
    CROSS_ONLY_NUMERIC_IDS,
    MODE_BY_PHASE,
    QUALIFICATION_RECEIPT_SCHEMA_VERSION,
    adaptation_contract_v3,
    decide_qualification_v3,
    expected_result_keys,
    sha256_json,
    validate_contract_v3,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_review_v3 import (
    literal_decide_qualification_v3,
    literal_validate_preflight_receipt_v3,
    review_contract_literal_v3,
)


def _sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def _rehash_contract(value: dict[str, object]) -> dict[str, object]:
    result = deepcopy(value)
    result.pop("contract_payload_sha256", None)
    result["contract_payload_sha256"] = sha256_json(result)
    return result


def _synthetic_specs(split: str) -> list[dict[str, object]]:
    base = 0 if split == "development_calibration" else 64
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    module_sha = hashlib.sha256(
        manifest_module.__file__ and open(manifest_module.__file__, "rb").read()
    ).hexdigest()
    result = []
    for index in range(64):
        payload = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": module_sha,
            "route_asset_sha256": manifest_module.ROUTE_ASSET_SHA256,
            "map_geometry_sha256": manifest_module.MAP_SHA256,
            "family": "four_track_highway",
            "tier": tiers[index % 4],
            "scenario_seed": scenario_base + index,
            "latent_seed": latent_base + index,
            "latent_policy": (
                "row0_zero_rows1_7_numpy_default_rng_pcg64_"
                "standard_normal_float32_v1"
            ),
            "candidate_k": 8,
            "independent_statistical_unit": "state",
        }
        payload["state_spec_sha256"] = manifest_module.sha256_json(payload)
        result.append(payload)
    return result


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
        "semantic_clone_sha256": legacy_manifest.sha256_json(semantic),
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
        "source_map_sha256": _sha("synthetic-b4-map"),
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


@pytest.fixture
def synthetic_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    route_bytes = b"synthetic-route-authority"
    map_bytes = b"synthetic-map-authority"
    route_sha = _sha(route_bytes)
    map_sha = _sha(map_bytes)
    b4_raw = legacy_manifest.canonical_bytes(
        [_b4_case(index) for index in range(100)]
    )
    b4_sha = _sha(b4_raw)
    for module in (manifest_module, review_module):
        monkeypatch.setattr(module, "ROUTE_ASSET_SHA256", route_sha)
        monkeypatch.setattr(module, "MAP_SHA256", map_sha)
        monkeypatch.setattr(module, "LATENT_SHAPE", (8, 2, 2, 1))
    monkeypatch.setattr(
        legacy_manifest,
        "B4_PREPARED_RUNTIME_CASES_SHA256",
        b4_sha,
    )
    monkeypatch.setattr(
        manifest_module,
        "B4_PREPARED_RUNTIME_CASES_SHA256",
        b4_sha,
    )
    monkeypatch.setattr(review_module, "B4_PREPARED_SHA", b4_sha)
    calibration_specs = _synthetic_specs("development_calibration")
    validation_specs = _synthetic_specs("independent_validation")
    all_specs = calibration_specs + validation_specs
    tensors = {
        spec["state_spec_id"]: {
            "ego": np.asarray(
                [spec["source_state_ordinal"], spec["scenario_seed"]],
                dtype=np.float32,
            )
        }
        for spec in all_specs
    }
    manifests = [
        manifest_module.materialize_input_only_manifest(
            state_spec=spec,
            route_asset_bytes=route_bytes,
            map_asset_bytes=map_bytes,
            actual_input_tensors=tensors[spec["state_spec_id"]],
        )
        for spec in all_specs
    ]
    forbidden = legacy_manifest.materialize_b4_forbidden_clone_manifest(
        b4_raw
    )
    authority_root = "a" * 64
    contract_root = "b" * 64
    review_root = "c" * 64
    authority = {
        "schema_version": manifest_module.AUTHORITY_SCHEMA_VERSION,
        "status": "authorized_by_future_versioned_high_control",
        "authority_artifact_path": (
            "/root/autodl-tmp/synthetic_test_authority"
        ),
        "authority_artifact_root_sha256": authority_root,
        "decision_sha256": "d" * 64,
        "authorized_contract_root_sha256": contract_root,
        "authorized_contract_review_root_sha256": review_root,
        "acquisition_authorized": True,
        "fresh_or_holdout_authorized": False,
    }
    receipt = {
        "schema_version": manifest_module.RECEIPT_SCHEMA_VERSION,
        "acquisition_authority": authority,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": review_root,
        "b4_forbidden_manifest_authority": {
            "preopen_path": manifest_module.B4_PREOPEN_PATH,
            "preopen_root_sha256": manifest_module.B4_PREOPEN_ROOT_SHA256,
            "prepared_runtime_cases_sha256": b4_sha,
            "derived_forbidden_manifest_sha256": forbidden[
                "manifest_sha256"
            ],
            "derived_forbidden_clone_key_count": 100,
            "derived_inside_validator_from_exact_bytes": True,
        },
        "calibration_manifests": manifests[:64],
        "validation_manifests": manifests[64:],
        "model_pool_selector_call_count_before_receipt": 0,
        "within_calibration_overlap_count": 0,
        "within_validation_overlap_count": 0,
        "cross_split_overlap_count": 0,
        "b4_overlap_count": 0,
        "no_drop_no_replacement": True,
        "status": "passed_before_first_model_pool_selector_call",
    }
    return {
        "receipt": receipt,
        "authority_root": authority_root,
        "contract_root": contract_root,
        "review_root": review_root,
        "calibration_specs": calibration_specs,
        "validation_specs": validation_specs,
        "route_bytes": route_bytes,
        "map_bytes": map_bytes,
        "b4_raw": b4_raw,
        "tensors": tensors,
    }


def _validate_preflight(
    fixture: dict[str, object],
    receipt: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    receipt = receipt or fixture["receipt"]
    kwargs = {
        "expected_acquisition_authority_root_sha256": fixture[
            "authority_root"
        ],
        "expected_authorized_contract_root_sha256": fixture[
            "contract_root"
        ],
        "expected_authorized_contract_review_root_sha256": fixture[
            "review_root"
        ],
        "calibration_specs": fixture["calibration_specs"],
        "validation_specs": fixture["validation_specs"],
        "route_asset_bytes": fixture["route_bytes"],
        "map_asset_bytes": fixture["map_bytes"],
        "prepared_runtime_cases_bytes": fixture["b4_raw"],
        "actual_input_tensors_by_state_id": fixture["tensors"],
    }
    producer = manifest_module.validate_preflight_receipt(
        receipt,
        acquisition_authority=receipt["acquisition_authority"],
        **kwargs,
    )
    reviewer_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key
        not in {
            "expected_authorized_contract_root_sha256",
            "expected_authorized_contract_review_root_sha256",
        }
    }
    reviewer_kwargs["expected_contract_root_sha256"] = fixture[
        "contract_root"
    ]
    reviewer_kwargs["expected_contract_review_root_sha256"] = fixture[
        "review_root"
    ]
    reviewer = literal_validate_preflight_receipt_v3(
        receipt,
        **reviewer_kwargs,
    )
    return producer, reviewer


def test_contract_v3_and_independent_review_pass() -> None:
    contract = adaptation_contract_v3()
    assert validate_contract_v3(contract) == contract
    review = review_contract_literal_v3(contract)
    assert review["status"] == (
        "passed_independent_executable_semantic_review_v3"
    )
    assert review["state_spec_count"] == 128
    assert review["endpoint_count"] == 37
    assert review["phase_result_key_count"] == 83
    assert contract["run_and_claim_boundary"]["acquisition_authorized"] is False


def test_preflight_reconstructs_exact_manifests_and_b4_bytes(
    synthetic_preflight: dict[str, object],
) -> None:
    producer, reviewer = _validate_preflight(synthetic_preflight)
    assert producer == synthetic_preflight["receipt"]
    assert reviewer == synthetic_preflight["receipt"]
    first = producer["calibration_manifests"][0]
    assert first["actual_state_sha256"] == first["source_scene"][
        "source_scene_sha256"
    ]
    assert first["actual_latent_tensor_manifest"]["shape"] == [8, 2, 2, 1]


@pytest.mark.parametrize(
    "mutation",
    (
        "unknown_manifest_field",
        "clone_payload",
        "spawn",
        "actor",
        "arbitrary_contract_root",
        "arbitrary_authority_root",
        "b4_bytes",
    ),
)
def test_forged_preflight_fails_closed(
    synthetic_preflight: dict[str, object],
    mutation: str,
) -> None:
    fixture = deepcopy(synthetic_preflight)
    receipt = fixture["receipt"]
    if mutation == "unknown_manifest_field":
        item = receipt["calibration_manifests"][0]
        item["forged_payload_not_recomputed"] = True
        payload = dict(item)
        payload.pop("manifest_sha256")
        item["manifest_sha256"] = manifest_module.sha256_json(payload)
    elif mutation == "clone_payload":
        item = receipt["calibration_manifests"][0]
        item["clone_payload"]["scenario_source_content_sha256"] = "e" * 64
        item["clone_key_sha256"] = manifest_module.sha256_json(
            item["clone_payload"]
        )
        payload = dict(item)
        payload.pop("manifest_sha256")
        item["manifest_sha256"] = manifest_module.sha256_json(payload)
    elif mutation == "spawn":
        item = receipt["calibration_manifests"][0]
        item["source_scene"]["spawn_pose"]["x_m"] += 1.0
        scene = dict(item["source_scene"])
        scene.pop("source_scene_sha256")
        item["source_scene"]["source_scene_sha256"] = (
            manifest_module.sha256_json(scene)
        )
        payload = dict(item)
        payload.pop("manifest_sha256")
        item["manifest_sha256"] = manifest_module.sha256_json(payload)
    elif mutation == "actor":
        item = receipt["calibration_manifests"][1]
        item["source_scene"]["dynamic_actors_initial"][0]["speed_mps"] += 1.0
        scene = dict(item["source_scene"])
        scene.pop("source_scene_sha256")
        item["source_scene"]["source_scene_sha256"] = (
            manifest_module.sha256_json(scene)
        )
        payload = dict(item)
        payload.pop("manifest_sha256")
        item["manifest_sha256"] = manifest_module.sha256_json(payload)
    elif mutation == "arbitrary_contract_root":
        receipt["contract_root_sha256"] = "f" * 64
    elif mutation == "arbitrary_authority_root":
        receipt["acquisition_authority"][
            "authority_artifact_root_sha256"
        ] = "f" * 64
    elif mutation == "b4_bytes":
        fixture["b4_raw"] += b" "
    with pytest.raises(ValueError):
        _validate_preflight(fixture, receipt)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("scenario_seed", 999),
        ("tier", "high_density"),
        ("source_state_ordinal", 63),
        ("source_sampler_module_sha256", "f" * 64),
    ),
)
def test_state_spec_seed_tier_or_ordinal_swap_fails(
    synthetic_preflight: dict[str, object],
    field: str,
    replacement: object,
) -> None:
    fixture = deepcopy(synthetic_preflight)
    spec = fixture["calibration_specs"][0]
    spec[field] = replacement
    payload = dict(spec)
    payload.pop("state_spec_sha256")
    spec["state_spec_sha256"] = manifest_module.sha256_json(payload)
    with pytest.raises(ValueError, match="deterministic authority"):
        _validate_preflight(fixture)


def _threshold_authority(
    phase: str,
    mode: str,
    endpoint_id: str,
    threshold: float,
) -> dict[str, object]:
    result = {
        "schema_version": "camp_dp_v25_fair_pool_threshold_authority_v1",
        "phase": phase,
        "mode": mode,
        "endpoint_id": endpoint_id,
        "calibration_state_count": 64,
        "threshold": threshold,
        "algorithm": (
            "q99_higher_then_10000_state_bootstrap_pcg64dxsm_"
            "seed825071_one_sided95_index9500_max_resolution_floor"
        ),
    }
    result["authority_sha256"] = sha256_json(result)
    return result


def _valid_qualification() -> tuple[dict[str, object], dict[str, object]]:
    contract = adaptation_contract_v3()
    state_ids = [
        row["state_spec_id"]
        for row in contract["state_specifications"]["independent_validation"]
    ]
    numeric = []
    for phase, mode, endpoint_id in expected_result_keys(contract):
        if endpoint_id.startswith("functional.") or endpoint_id in {
            "k8.finite_and_diverse",
            "authority.fingerprint",
            "pool.tensor_immutability_and_zero_calls",
            "split.input_only_clone_nonoverlap",
        }:
            continue
        threshold = 1.0
        numeric.append(
            {
                "phase": phase,
                "mode": mode,
                "endpoint_id": endpoint_id,
                "state_values": [
                    {"state_spec_id": state_id, "value": 0.0}
                    for state_id in state_ids
                ],
                "threshold": threshold,
                "threshold_authority": _threshold_authority(
                    phase, mode, endpoint_id, threshold
                ),
            }
        )
    fingerprint = {
        "fixed_dp_head": (
            "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        ),
        "generator": "new_single_invocation_batched_k8_candidate_pool",
        "candidate_k": 8,
        "checkpoint_sha256": (
            "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
        ),
        "model_source_sha256": (
            "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
        ),
        "decoder_source_sha256": (
            "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
        ),
        "encoder_source_sha256": (
            "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
        ),
        "route_asset_sha256": (
            "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
        ),
        "map_geometry_sha256": (
            "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
        ),
        "dtype": "float32",
    }
    k8 = {
        mode: [
            {
                "state_spec_id": state_id,
                "all_finite": True,
                "row_sha256": [
                    _sha(f"{mode}:{state_id}:{row}") for row in range(8)
                ],
            }
            for state_id in state_ids
        ]
        for mode in ("sequential_batch1_x8", "single_invocation_batch8")
    }
    pool = [
        {
            "state_spec_id": state_id,
            "pre_tensor_sha256": _sha(f"pool:{state_id}"),
            "post_tensor_sha256": _sha(f"pool:{state_id}"),
            "dp_model_call_count_after_pool": 0,
            "latent_replacement_count_after_pool": 0,
            "candidate_generation_count_after_pool": 0,
        }
        for state_id in state_ids
    ]
    masks = {
        arm: [
            {
                "state_spec_id": state_id,
                "sequential_mask": [True] * 8,
                "batch8_mask": [True] * 8,
            }
            for state_id in state_ids
        ]
        for arm in ("static14d", "scene14d")
    }
    action = np.zeros((80, 4), dtype=np.float64).tolist()
    actions = {
        arm: [
            {
                "state_spec_id": state_id,
                "sequential_selected_index": 0,
                "batch8_selected_index": 0,
                "sequential_action_80x4": action,
                "batch8_action_80x4": action,
                "sequential_executable": "executable",
                "batch8_executable": "executable",
                "sequential_terminal": "complete",
                "batch8_terminal": "complete",
            }
            for state_id in state_ids
        ]
        for arm in ("static14d", "scene14d")
    }
    receipt = {
        "schema_version": QUALIFICATION_RECEIPT_SCHEMA_VERSION,
        "contract_payload_sha256": contract["contract_payload_sha256"],
        "contract_root_sha256": "1" * 64,
        "contract_review_root_sha256": "2" * 64,
        "acquisition_authority_root_sha256": "3" * 64,
        "numeric_evidence": numeric,
        "hard_evidence": {
            "fingerprints": {
                "expected": fingerprint,
                "observed_by_mode": {
                    "sequential_batch1_x8": fingerprint,
                    "single_invocation_batch8": fingerprint,
                },
            },
            "k8": k8,
            "pool": pool,
            "masks": masks,
            "actions": actions,
            "split_preflight": {
                "status": "passed_before_first_model_pool_selector_call",
                "receipt_sha256": "4" * 64,
                "contract_root_sha256": "1" * 64,
                "contract_review_root_sha256": "2" * 64,
                "acquisition_authority_root_sha256": "3" * 64,
            },
        },
    }
    return contract, receipt


def test_phase_registry_has_no_cross_only_within_cycle() -> None:
    contract = adaptation_contract_v3()
    keys = set(expected_result_keys(contract))
    for endpoint_id in CROSS_ONLY_NUMERIC_IDS:
        assert (
            "cross_mode",
            MODE_BY_PHASE["cross_mode"],
            endpoint_id,
        ) in keys
        assert not any(
            phase in {"sequential_within", "batch8_within"}
            and observed == endpoint_id
            for phase, _mode, observed in keys
        )
    assert len(keys) == 83


def test_qualification_derives_pass_without_caller_boolean_or_status() -> None:
    contract, receipt = _valid_qualification()
    assert list(inspect.signature(decide_qualification_v3).parameters) == [
        "contract",
        "receipt",
    ]
    producer = decide_qualification_v3(contract, receipt)
    reviewer = literal_decide_qualification_v3(contract, receipt)
    assert producer == reviewer
    assert producer["status"] == "PASS"
    assert producer["derived_result_count"] == 83
    assert producer["caller_supplied_status_or_within_boolean_used"] is False
    forged = deepcopy(receipt)
    forged["both_within_modes_pass"] = True
    with pytest.raises(ValueError, match="exact schema"):
        decide_qualification_v3(contract, forged)


def test_typed_hard_evidence_cannot_self_assert_pass() -> None:
    contract, receipt = _valid_qualification()
    receipt["hard_evidence"]["k8"]["single_invocation_batch8"][0][
        "all_finite"
    ] = False
    producer = decide_qualification_v3(contract, receipt)
    reviewer = literal_decide_qualification_v3(contract, receipt)
    assert producer == reviewer
    assert producer["classification"] == "within_mode_generator_instability"
    contract, receipt = _valid_qualification()
    receipt["hard_evidence"]["pool"][0]["dp_model_call_count_after_pool"] = 1
    producer = decide_qualification_v3(contract, receipt)
    reviewer = literal_decide_qualification_v3(contract, receipt)
    assert producer == reviewer
    assert producer["classification"] == "authority_failure"


def test_numeric_missing_omission_and_equal_boundary_fail_closed() -> None:
    contract, receipt = _valid_qualification()
    receipt["numeric_evidence"][0]["state_values"][0]["value"] = None
    assert decide_qualification_v3(contract, receipt)["classification"] == (
        "evidence_missing"
    )
    contract, receipt = _valid_qualification()
    del receipt["numeric_evidence"][-1]
    with pytest.raises(ValueError, match="denominator"):
        decide_qualification_v3(contract, receipt)
    contract, receipt = _valid_qualification()
    row = receipt["numeric_evidence"][0]
    row["state_values"][-2]["value"] = 1.0
    row["state_values"][-1]["value"] = 1.0
    assert decide_qualification_v3(contract, receipt)["status"] == "PASS"
    for item in row["state_values"][-3:]:
        item["value"] = 1.000001
    assert decide_qualification_v3(contract, receipt)["classification"] == (
        "within_mode_generator_instability"
    )


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (
            (
                "input_authority",
                "source_scene_algorithm",
                "actor_count_by_tier",
                "high_density",
            ),
            7,
        ),
        (
            (
                "result_topology",
                "cross_only_ids_forbidden_in_within",
            ),
            [],
        ),
        (
            (
                "typed_hard_evidence",
                "caller_status_or_within_boolean_accepted",
            ),
            True,
        ),
        (
            ("decision_table", "cross_entry"),
            "caller_boolean",
        ),
        (
            ("endpoint_registry", 0, "formula"),
            "forged_formula",
        ),
        (
            ("run_and_claim_boundary", "acquisition_authorized"),
            True,
        ),
    ),
)
def test_rehashed_semantic_mutations_fail_independent_review(
    path: tuple[object, ...],
    replacement: object,
) -> None:
    candidate: object = deepcopy(adaptation_contract_v3())
    cursor = candidate
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    mutated = _rehash_contract(candidate)
    with pytest.raises(ValueError):
        validate_contract_v3(mutated)
    with pytest.raises(ValueError):
        review_contract_literal_v3(mutated)
