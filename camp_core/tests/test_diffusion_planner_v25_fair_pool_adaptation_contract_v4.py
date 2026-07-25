from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v3 as v3_review,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v4 as v4_review,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v3 as v3,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v4 as v4,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest as legacy_manifest,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest_v2 as manifest,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    bootstrap_upper_threshold,
    sha256_json,
)


def _sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def _specs(
    split: str,
    sampler_sha: str,
    route_sha: str,
    map_sha: str,
) -> list[dict[str, object]]:
    base = 0 if split == "development_calibration" else 64
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    result = []
    for index in range(64):
        row = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": sampler_sha,
            "route_asset_sha256": route_sha,
            "map_geometry_sha256": map_sha,
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
        row["state_spec_sha256"] = sha256_json(row)
        result.append(row)
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


def _candidate(state_index: int, repeat: int = 0) -> np.ndarray:
    value = np.zeros((8, 80, 4), dtype=np.float64)
    for row in range(8):
        value[row, :, 0] = row + state_index * 1e-3 + repeat * 1e-6
        value[row, :, 3] = 1.0
    return value


def _tensor_hashes(value: np.ndarray) -> tuple[str, list[str]]:
    array = np.ascontiguousarray(value.astype("<f8", copy=False))
    return (
        hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        [
            hashlib.sha256(
                np.ascontiguousarray(array[index]).tobytes(order="C")
            ).hexdigest()
            for index in range(8)
        ],
    )


def _run_receipts(
    *,
    split: str,
    specs: list[dict[str, object]],
    manifest_by_id: dict[str, dict[str, object]],
) -> tuple[list[dict[str, object]], dict[tuple[str, str, int], dict[str, object]]]:
    rows = []
    mapping = {}
    for mode in v4.MODES:
        for state_index, spec in enumerate(specs):
            state_id = spec["state_spec_id"]
            preflight = manifest_by_id[state_id]
            for repeat in range(5):
                tensor_sha, row_sha = _tensor_hashes(
                    _candidate(state_index, repeat)
                )
                row = {
                    "state_spec_id": state_id,
                    "mode": mode,
                    "repeat_index": repeat,
                    "input_manifest_sha256": preflight["manifest_sha256"],
                    "actual_state_sha256": preflight["actual_state_sha256"],
                    "actual_latent_manifest_sha256": preflight[
                        "actual_latent_tensor_manifest"
                    ]["manifest_sha256"],
                    "fixed_dp_head": v4.FIXED_DP_HEAD,
                    "checkpoint_sha256": (
                        "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
                    ),
                    "model_source_sha256": (
                        "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
                    ),
                    "forward_invocation_id": (
                        f"{split}:{state_id}:{mode}:forward:{repeat}"
                    ),
                    "model_call_count": 8 if mode == v4.MODES[0] else 1,
                    "pool_id": f"{split}:{state_id}:{mode}:pool:{repeat}",
                    "candidate_tensor_sha256": tensor_sha,
                    "candidate_row_sha256": row_sha,
                    "all_finite": True,
                }
                row["receipt_sha256"] = sha256_json(row)
                rows.append(row)
                mapping[(mode, state_id, repeat)] = row
    return rows, mapping


def _pair_receipts(
    *,
    specs: list[dict[str, object]],
    runs: dict[tuple[str, str, int], dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for phase, topology, endpoints in (
        ("sequential_within", v4.WITHIN_PAIRS, v4.WITHIN_NUMERIC_IDS),
        ("batch8_within", v4.WITHIN_PAIRS, v4.WITHIN_NUMERIC_IDS),
        ("cross_mode", v4.CROSS_PAIRS, v4.CROSS_NUMERIC_IDS),
    ):
        mode = v4.MODE_BY_PHASE[phase]
        left_mode = (
            v4.MODES[0] if phase == "cross_mode" else mode
        )
        right_mode = (
            v4.MODES[1] if phase == "cross_mode" else mode
        )
        for spec in specs:
            state_id = spec["state_spec_id"]
            for pair_index, (left_repeat, right_repeat) in enumerate(
                topology
            ):
                row = {
                    "phase": phase,
                    "mode": mode,
                    "state_spec_id": state_id,
                    "pair_index": pair_index,
                    "left_repeat_index": left_repeat,
                    "right_repeat_index": right_repeat,
                    "left_run_receipt_sha256": runs[
                        (left_mode, state_id, left_repeat)
                    ]["receipt_sha256"],
                    "right_run_receipt_sha256": runs[
                        (right_mode, state_id, right_repeat)
                    ]["receipt_sha256"],
                    "endpoint_values": {
                        endpoint: 0.0 for endpoint in endpoints
                    },
                }
                row["receipt_sha256"] = sha256_json(row)
                rows.append(row)
    return rows


def _hard_receipts(
    specs: list[dict[str, object]],
    runs: dict[tuple[str, str, int], dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for state_index, spec in enumerate(specs):
        state_id = spec["state_spec_id"]
        pools = {}
        selectors = {arm: {} for arm in v4.ARMS}
        for mode in v4.MODES:
            run = runs[(mode, state_id, 0)]
            tensor = _candidate(state_index)
            tensor_sha, row_sha = _tensor_hashes(tensor)
            pools[mode] = {
                "run_receipt_sha256": run["receipt_sha256"],
                "state_spec_id": state_id,
                "mode": mode,
                "forward_invocation_id": run["forward_invocation_id"],
                "pool_id": run["pool_id"],
                "input_manifest_sha256": run["input_manifest_sha256"],
                "latent_manifest_sha256": run[
                    "actual_latent_manifest_sha256"
                ],
                "fixed_dp_head": v4.FIXED_DP_HEAD,
                "checkpoint_sha256": run["checkpoint_sha256"],
                "dtype": "<f8",
                "shape": [8, 80, 4],
                "candidate_tensor": tensor.tolist(),
                "tensor_sha256": tensor_sha,
                "row_sha256": row_sha,
            }
            for arm in v4.ARMS:
                selector = {
                    "state_spec_id": state_id,
                    "arm": arm,
                    "mode": mode,
                    "pool_id": run["pool_id"],
                    "candidate_tensor_sha256": tensor_sha,
                    "pre_tensor_sha256": tensor_sha,
                    "post_tensor_sha256": tensor_sha,
                    "scores": [float(index) for index in range(8)],
                    "mask": [True] * 8,
                    "selected_index": 0,
                    "selected_action_80x4": tensor[0].tolist(),
                    "executable": "executable",
                    "terminal": "complete",
                    "dp_model_call_count_after_pool": 0,
                    "latent_replacement_count_after_pool": 0,
                    "candidate_generation_count_after_pool": 0,
                }
                selector["receipt_sha256"] = sha256_json(selector)
                selectors[arm][mode] = selector
        row = {
            "state_spec_id": state_id,
            "candidate_pools": pools,
            "selectors": selectors,
        }
        row["receipt_sha256"] = sha256_json(row)
        rows.append(row)
    return rows


def _receipt_payload(
    *,
    split: str,
    authority_root: str,
    preflight_root: str,
    threshold_root: str | None,
    threshold_review_root: str | None,
    specs: list[dict[str, object]],
    manifest_by_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    runs, run_map = _run_receipts(
        split=split,
        specs=specs,
        manifest_by_id=manifest_by_id,
    )
    return {
        "schema_version": "camp_dp_v25_fair_pool_mode_repeat_receipts_v1",
        "split": split,
        "authority_root_sha256": authority_root,
        "preflight_root_sha256": preflight_root,
        "threshold_freeze_root_sha256": threshold_root,
        "threshold_freeze_review_root_sha256": threshold_review_root,
        "run_receipts": runs,
        "pair_receipts": _pair_receipts(specs=specs, runs=run_map),
        "hard_state_receipts": (
            _hard_receipts(specs, run_map)
            if split == "independent_validation"
            else []
        ),
    }


def _freeze_payload(
    *,
    contract: dict[str, object],
    contract_root: str,
    authority_root: str,
    calibration_root: str,
    calibration_review_root: str,
    calibration_specs: list[dict[str, object]],
    calibration_pair_rows: list[dict[str, object]],
) -> dict[str, object]:
    state_ids = [row["state_spec_id"] for row in calibration_specs]
    by_key = {
        key: {state_id: [] for state_id in state_ids}
        for key in v4._numeric_keys()
    }
    roots = {
        key: {state_id: [] for state_id in state_ids}
        for key in v4._numeric_keys()
    }
    for row in calibration_pair_rows:
        for endpoint, value in row["endpoint_values"].items():
            key = (row["phase"], row["mode"], endpoint)
            by_key[key][row["state_spec_id"]].append(value)
            roots[key][row["state_spec_id"]].append(row["receipt_sha256"])
    records = []
    for key in v4._numeric_keys():
        statistics = [
            0.0 if not by_key[key][state_id] else max(by_key[key][state_id])
            for state_id in state_ids
        ]
        floor = v4._resolution_floor(key[2])
        root_rows = [roots[key][state_id] for state_id in state_ids]
        preimage = {
            "algorithm": contract["threshold_freeze_schema"]["bootstrap"],
            "phase": key[0],
            "mode": key[1],
            "endpoint_id": key[2],
            "calibration_state_ids": state_ids,
            "state_pair_receipt_sha256": root_rows,
            "state_statistics": statistics,
            "resolution_floor": floor,
        }
        upper = bootstrap_upper_threshold(
            statistics,
            resolution_floor=floor,
        )
        records.append(
            {
                "phase": key[0],
                "mode": key[1],
                "endpoint_id": key[2],
                "calibration_state_ids": state_ids,
                "state_pair_receipt_sha256": root_rows,
                "state_statistics": statistics,
                "bootstrap_preimage_sha256": sha256_json(preimage),
                "resolution_floor": floor,
                "bootstrap_result": upper,
                "threshold": upper,
            }
        )
    return {
        "schema_version": "camp_dp_v25_fair_pool_threshold_freeze_v1",
        "contract_root_sha256": contract_root,
        "acquisition_authority_root_sha256": authority_root,
        "calibration_receipts_root_sha256": calibration_root,
        "calibration_receipts_review_root_sha256": calibration_review_root,
        "validation_model_pool_selector_call_count_before_seal": 0,
        "records": records,
    }


@pytest.fixture
def synthetic_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    route_bytes = b"synthetic-route-authority-v4"
    map_bytes = b"synthetic-map-authority-v4"
    route_sha = _sha(route_bytes)
    map_sha = _sha(map_bytes)
    b4_bytes = legacy_manifest.canonical_bytes(
        [_b4_case(index) for index in range(100)]
    )
    b4_sha = _sha(b4_bytes)
    sampler_sha = hashlib.sha256(
        open(manifest.__file__, "rb").read()
    ).hexdigest()
    calibration_specs = _specs(
        "development_calibration", sampler_sha, route_sha, map_sha
    )
    validation_specs = _specs(
        "independent_validation", sampler_sha, route_sha, map_sha
    )
    monkeypatch.setattr(
        v3,
        "_state_specs",
        lambda split, _sampler: deepcopy(
            calibration_specs
            if split == "development_calibration"
            else validation_specs
        ),
    )
    monkeypatch.setattr(manifest, "ROUTE_ASSET_SHA256", route_sha)
    monkeypatch.setattr(manifest, "MAP_SHA256", map_sha)
    monkeypatch.setattr(manifest, "LATENT_SHAPE", (8, 2, 2, 1))
    monkeypatch.setattr(
        legacy_manifest, "B4_PREPARED_RUNTIME_CASES_SHA256", b4_sha
    )
    monkeypatch.setattr(
        manifest, "B4_PREPARED_RUNTIME_CASES_SHA256", b4_sha
    )
    contract = v4.adaptation_contract_v4()
    monkeypatch.setattr(
        v4_review,
        "EXPECTED_PAYLOAD_SHA256",
        contract["contract_payload_sha256"],
    )
    monkeypatch.setattr(
        v4_review,
        "EXPECTED_INHERITED_V3_PAYLOAD_SHA256",
        contract["inherited_v3_contract"]["contract_payload_sha256"],
    )
    literal_preflight = (
        v3_review.literal_validate_preflight_receipt_v3
    )

    def synthetic_literal_preflight(*args: object, **kwargs: object) -> object:
        original = (
            v3_review.ROUTE_ASSET_SHA256,
            v3_review.MAP_SHA256,
            v3_review.B4_PREPARED_SHA,
            v3_review.LATENT_SHAPE,
        )
        v3_review.ROUTE_ASSET_SHA256 = route_sha
        v3_review.MAP_SHA256 = map_sha
        v3_review.B4_PREPARED_SHA = b4_sha
        v3_review.LATENT_SHAPE = (8, 2, 2, 1)
        try:
            return literal_preflight(*args, **kwargs)
        finally:
            (
                v3_review.ROUTE_ASSET_SHA256,
                v3_review.MAP_SHA256,
                v3_review.B4_PREPARED_SHA,
                v3_review.LATENT_SHAPE,
            ) = original

    monkeypatch.setattr(
        v4_review,
        "literal_validate_preflight_receipt_v3",
        synthetic_literal_preflight,
    )
    contract_root = "b" * 64
    contract_review_root = "c" * 64
    input_authority_root = "a" * 64
    tensors = {
        spec["state_spec_id"]: {
            "ego": np.asarray(
                [spec["source_state_ordinal"], spec["scenario_seed"]],
                dtype=np.float32,
            )
        }
        for spec in calibration_specs + validation_specs
    }
    manifests = [
        manifest.materialize_input_only_manifest(
            state_spec=spec,
            route_asset_bytes=route_bytes,
            map_asset_bytes=map_bytes,
            actual_input_tensors=tensors[spec["state_spec_id"]],
        )
        for spec in calibration_specs + validation_specs
    ]
    manifest_by_id = {row["state_spec_id"]: row for row in manifests}
    forbidden = legacy_manifest.materialize_b4_forbidden_clone_manifest(
        b4_bytes
    )
    input_authority = {
        "schema_version": manifest.AUTHORITY_SCHEMA_VERSION,
        "status": "authorized_by_future_versioned_high_control",
        "authority_artifact_path": (
            "/root/autodl-tmp/synthetic_v4_acquisition_authority"
        ),
        "authority_artifact_root_sha256": input_authority_root,
        "decision_sha256": "d" * 64,
        "authorized_contract_root_sha256": contract_root,
        "authorized_contract_review_root_sha256": contract_review_root,
        "acquisition_authorized": True,
        "fresh_or_holdout_authorized": False,
    }
    authority = v4.make_content_artifact(
        v4.ARTIFACT_KIND["acquisition_authority"],
        {
            "schema_version": (
                "camp_dp_v25_fair_pool_future_acquisition_authority_v1"
            ),
            "contract_payload_sha256": contract[
                "contract_payload_sha256"
            ],
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "input_manifest_acquisition_authority": input_authority,
            "authorized_phases": [
                "input_only_preflight",
                "development_calibration",
                "threshold_freeze",
                "independent_validation",
            ],
            "acquisition_authorized": True,
            "fresh_holdout_closed_loop_training_authorized": False,
        },
    )
    authority_review = v4.make_content_review(
        authority,
        review_kind=v4.ARTIFACT_KIND["acquisition_authority_review"],
    )
    preflight_receipt = {
        "schema_version": manifest.RECEIPT_SCHEMA_VERSION,
        "acquisition_authority": input_authority,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "b4_forbidden_manifest_authority": {
            "preopen_path": manifest.B4_PREOPEN_PATH,
            "preopen_root_sha256": manifest.B4_PREOPEN_ROOT_SHA256,
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
    tensor_preimages = []
    for state_id, named in tensors.items():
        tensor_preimages.append(
            {
                "state_spec_id": state_id,
                "tensors": [
                    {
                        "name": name,
                        "dtype": np.ascontiguousarray(array).dtype.str,
                        "shape": list(array.shape),
                        "data_hex": np.ascontiguousarray(array)
                        .tobytes(order="C")
                        .hex(),
                    }
                    for name, array in sorted(named.items())
                ],
            }
        )
    preflight = v4.make_content_artifact(
        v4.ARTIFACT_KIND["split_preflight"],
        {
            "schema_version": (
                "camp_dp_v25_fair_pool_full_preflight_preimages_v1"
            ),
            "receipt": preflight_receipt,
            "route_asset_bytes_hex": route_bytes.hex(),
            "map_asset_bytes_hex": map_bytes.hex(),
            "prepared_runtime_cases_bytes_hex": b4_bytes.hex(),
            "actual_input_tensors": tensor_preimages,
        },
    )
    preflight_review = v4.make_content_review(
        preflight,
        review_kind=v4.ARTIFACT_KIND["split_preflight_review"],
    )
    calibration_payload = _receipt_payload(
        split="development_calibration",
        authority_root=authority["root_sha256"],
        preflight_root=preflight["root_sha256"],
        threshold_root=None,
        threshold_review_root=None,
        specs=calibration_specs,
        manifest_by_id=manifest_by_id,
    )
    calibration = v4.make_content_artifact(
        v4.ARTIFACT_KIND["calibration_receipts"],
        calibration_payload,
    )
    calibration_review = v4.make_content_review(
        calibration,
        review_kind=v4.ARTIFACT_KIND["calibration_receipts_review"],
    )
    freeze = v4.make_content_artifact(
        v4.ARTIFACT_KIND["threshold_freeze"],
        _freeze_payload(
            contract=contract,
            contract_root=contract_root,
            authority_root=authority["root_sha256"],
            calibration_root=calibration["root_sha256"],
            calibration_review_root=calibration_review["root_sha256"],
            calibration_specs=calibration_specs,
            calibration_pair_rows=calibration_payload["pair_receipts"],
        ),
    )
    freeze_review = v4.make_content_review(
        freeze,
        review_kind=v4.ARTIFACT_KIND["threshold_freeze_review"],
    )
    validation = v4.make_content_artifact(
        v4.ARTIFACT_KIND["validation_receipts"],
        _receipt_payload(
            split="independent_validation",
            authority_root=authority["root_sha256"],
            preflight_root=preflight["root_sha256"],
            threshold_root=freeze["root_sha256"],
            threshold_review_root=freeze_review["root_sha256"],
            specs=validation_specs,
            manifest_by_id=manifest_by_id,
        ),
    )
    validation_review = v4.make_content_review(
        validation,
        review_kind=v4.ARTIFACT_KIND["validation_receipts_review"],
    )
    artifacts = {
        "acquisition_authority": authority,
        "acquisition_authority_review": authority_review,
        "split_preflight": preflight,
        "split_preflight_review": preflight_review,
        "calibration_receipts": calibration,
        "calibration_receipts_review": calibration_review,
        "threshold_freeze": freeze,
        "threshold_freeze_review": freeze_review,
        "validation_receipts": validation,
        "validation_receipts_review": validation_review,
    }
    anchor = v4.make_trust_anchor(
        contract,
        contract_root_sha256=contract_root,
        contract_review_root_sha256=contract_review_root,
        input_manifest_authority_root_sha256=input_authority_root,
        artifact_roots={
            name: artifacts[name]["root_sha256"]
            for name in v4.ARTIFACT_NAMES
        },
        high_decision_sha256="e" * 64,
    )
    package = {
        "schema_version": v4.QUALIFICATION_PACKAGE_SCHEMA,
        "contract_payload_sha256": contract["contract_payload_sha256"],
        "trust_anchor_root_sha256": anchor[
            "trust_anchor_root_sha256"
        ],
        "artifacts": artifacts,
    }
    return {
        "contract": contract,
        "package": package,
        "anchor": anchor,
    }


def _reseal_artifact(value: dict[str, object]) -> None:
    value["payload_sha256"] = sha256_json(value["payload"])
    payload = dict(value)
    payload.pop("root_sha256", None)
    value["root_sha256"] = sha256_json(payload)


def _rechain(
    package: dict[str, object],
    anchor: dict[str, object],
) -> None:
    artifacts = package["artifacts"]

    def review(source_name: str, review_name: str) -> None:
        source = artifacts[source_name]
        target = artifacts[review_name]
        target["payload"]["source_root_sha256"] = source["root_sha256"]
        target["payload"]["source_payload_sha256"] = source[
            "payload_sha256"
        ]
        _reseal_artifact(target)

    _reseal_artifact(artifacts["acquisition_authority"])
    review("acquisition_authority", "acquisition_authority_review")
    _reseal_artifact(artifacts["split_preflight"])
    review("split_preflight", "split_preflight_review")
    calibration = artifacts["calibration_receipts"]
    calibration["payload"]["authority_root_sha256"] = artifacts[
        "acquisition_authority"
    ]["root_sha256"]
    calibration["payload"]["preflight_root_sha256"] = artifacts[
        "split_preflight"
    ]["root_sha256"]
    _reseal_artifact(calibration)
    review("calibration_receipts", "calibration_receipts_review")
    freeze = artifacts["threshold_freeze"]
    freeze["payload"]["acquisition_authority_root_sha256"] = artifacts[
        "acquisition_authority"
    ]["root_sha256"]
    freeze["payload"]["calibration_receipts_root_sha256"] = calibration[
        "root_sha256"
    ]
    freeze["payload"][
        "calibration_receipts_review_root_sha256"
    ] = artifacts["calibration_receipts_review"]["root_sha256"]
    _reseal_artifact(freeze)
    review("threshold_freeze", "threshold_freeze_review")
    validation = artifacts["validation_receipts"]
    validation["payload"]["authority_root_sha256"] = artifacts[
        "acquisition_authority"
    ]["root_sha256"]
    validation["payload"]["preflight_root_sha256"] = artifacts[
        "split_preflight"
    ]["root_sha256"]
    validation["payload"]["threshold_freeze_root_sha256"] = freeze[
        "root_sha256"
    ]
    validation["payload"][
        "threshold_freeze_review_root_sha256"
    ] = artifacts["threshold_freeze_review"]["root_sha256"]
    _reseal_artifact(validation)
    review("validation_receipts", "validation_receipts_review")
    anchor["artifact_roots"] = {
        name: artifacts[name]["root_sha256"] for name in v4.ARTIFACT_NAMES
    }
    anchor_payload = dict(anchor)
    anchor_payload.pop("trust_anchor_root_sha256", None)
    anchor["trust_anchor_root_sha256"] = sha256_json(anchor_payload)
    package["trust_anchor_root_sha256"] = anchor[
        "trust_anchor_root_sha256"
    ]


def test_contract_v4_is_design_only_and_externally_anchored() -> None:
    contract = v4.validate_contract_v4(v4.adaptation_contract_v4())
    assert contract["run_and_claim_boundary"]["acquisition_authorized"] is False
    assert contract["trust_anchor"]["provider_task_id"] == v4.CONTROL_TASK_ID
    assert contract["threshold_freeze_schema"][
        "caller_threshold_or_self_hash_accepted"
    ] is False
    assert contract["validation_receipt_schema"][
        "naked_all_finite_mask_action_or_call_count_accepted"
    ] is False


def test_complete_trusted_synthetic_chain_can_pass(
    synthetic_chain: dict[str, object],
) -> None:
    decision = v4.decide_qualification_v4(
        synthetic_chain["contract"],
        synthetic_chain["package"],
        trust_anchor=synthetic_chain["anchor"],
        expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
            "trust_anchor_root_sha256"
        ],
    )
    assert decision["status"] == "PASS"
    assert decision["complete_artifact_chain_validated"] is True
    assert decision["thresholds_recomputed_from_calibration_receipts"] is True
    assert decision[
        "caller_supplied_threshold_status_or_within_boolean_used"
    ] is False
    reviewed = v4_review.literal_decide_qualification_v4(
        synthetic_chain["contract"],
        synthetic_chain["package"],
        trust_anchor=synthetic_chain["anchor"],
        expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
            "trust_anchor_root_sha256"
        ],
    )
    assert reviewed == decision


@pytest.mark.parametrize(
    "mutation",
    (
        "arbitrary_well_formed_root",
        "forged_preflight_status",
        "self_hashed_huge_threshold",
        "random_unique_k8_sha_without_tensor_preimage",
        "zero_action_without_pool_binding",
    ),
)
def test_untrusted_or_unbound_pass_preimages_fail_closed(
    synthetic_chain: dict[str, object],
    mutation: str,
) -> None:
    package = deepcopy(synthetic_chain["package"])
    if mutation == "arbitrary_well_formed_root":
        package["artifacts"]["acquisition_authority"][
            "root_sha256"
        ] = "1" * 64
    elif mutation == "forged_preflight_status":
        preflight = package["artifacts"]["split_preflight"]
        preflight["payload"]["receipt"]["status"] = (
            "passed_before_first_model_pool_selector_call"
        )
        preflight["payload"]["receipt"]["calibration_manifests"][0][
            "forged_payload_not_recomputed"
        ] = True
        _reseal_artifact(preflight)
    elif mutation == "self_hashed_huge_threshold":
        freeze = package["artifacts"]["threshold_freeze"]
        freeze["payload"]["records"][0]["threshold"] = 1e30
        freeze["payload"]["records"][0]["bootstrap_result"] = 1e30
        _reseal_artifact(freeze)
    elif mutation == "random_unique_k8_sha_without_tensor_preimage":
        validation = package["artifacts"]["validation_receipts"]
        run = validation["payload"]["run_receipts"][0]
        run["candidate_row_sha256"] = [
            hashlib.sha256(f"forged:{index}".encode()).hexdigest()
            for index in range(8)
        ]
        payload = dict(run)
        payload.pop("receipt_sha256")
        run["receipt_sha256"] = sha256_json(payload)
        _reseal_artifact(validation)
    elif mutation == "zero_action_without_pool_binding":
        validation = package["artifacts"]["validation_receipts"]
        selector = validation["payload"]["hard_state_receipts"][0][
            "selectors"
        ]["static14d"][v4.MODES[0]]
        selector["pool_id"] = "forged-unbound-pool"
        payload = dict(selector)
        payload.pop("receipt_sha256")
        selector["receipt_sha256"] = sha256_json(payload)
        hard = validation["payload"]["hard_state_receipts"][0]
        payload = dict(hard)
        payload.pop("receipt_sha256")
        hard["receipt_sha256"] = sha256_json(payload)
        _reseal_artifact(validation)
    with pytest.raises(ValueError):
        v4.decide_qualification_v4(
            synthetic_chain["contract"],
            package,
            trust_anchor=synthetic_chain["anchor"],
            expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )


def test_external_anchor_root_cannot_come_from_package(
    synthetic_chain: dict[str, object],
) -> None:
    forged = deepcopy(synthetic_chain["anchor"])
    forged["contract_root_sha256"] = "1" * 64
    payload = dict(forged)
    payload.pop("trust_anchor_root_sha256")
    forged["trust_anchor_root_sha256"] = sha256_json(payload)
    with pytest.raises(ValueError, match="external High trust anchor root"):
        v4.decide_qualification_v4(
            synthetic_chain["contract"],
            synthetic_chain["package"],
            trust_anchor=forged,
            expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "forged_preflight_with_retrusted_roots",
        "huge_threshold_with_retrusted_roots",
        "random_k8_sha_with_retrusted_roots",
        "unbound_selector_with_retrusted_roots",
    ),
)
def test_retrusted_but_semantically_forged_chain_still_fails(
    synthetic_chain: dict[str, object],
    mutation: str,
) -> None:
    package = deepcopy(synthetic_chain["package"])
    anchor = deepcopy(synthetic_chain["anchor"])
    artifacts = package["artifacts"]
    if mutation == "forged_preflight_with_retrusted_roots":
        artifacts["split_preflight"]["payload"]["receipt"][
            "calibration_manifests"
        ][0]["forged_payload_not_recomputed"] = True
    elif mutation == "huge_threshold_with_retrusted_roots":
        record = artifacts["threshold_freeze"]["payload"]["records"][0]
        record["threshold"] = 1e30
        record["bootstrap_result"] = 1e30
    elif mutation == "random_k8_sha_with_retrusted_roots":
        validation = artifacts["validation_receipts"]["payload"]
        run = validation["run_receipts"][0]
        previous_root = run["receipt_sha256"]
        run["candidate_row_sha256"] = [
            hashlib.sha256(f"forged-row:{index}".encode()).hexdigest()
            for index in range(8)
        ]
        run_payload = dict(run)
        run_payload.pop("receipt_sha256")
        run["receipt_sha256"] = sha256_json(run_payload)
        for pair in validation["pair_receipts"]:
            changed = False
            for field in (
                "left_run_receipt_sha256",
                "right_run_receipt_sha256",
            ):
                if pair[field] == previous_root:
                    pair[field] = run["receipt_sha256"]
                    changed = True
            if changed:
                pair_payload = dict(pair)
                pair_payload.pop("receipt_sha256")
                pair["receipt_sha256"] = sha256_json(pair_payload)
        hard = validation["hard_state_receipts"][0]
        hard["candidate_pools"][v4.MODES[0]][
            "run_receipt_sha256"
        ] = run["receipt_sha256"]
        hard_payload = dict(hard)
        hard_payload.pop("receipt_sha256")
        hard["receipt_sha256"] = sha256_json(hard_payload)
    elif mutation == "unbound_selector_with_retrusted_roots":
        validation = artifacts["validation_receipts"]["payload"]
        hard = validation["hard_state_receipts"][0]
        selector = hard["selectors"]["static14d"][v4.MODES[0]]
        selector["pool_id"] = "forged-unbound-pool"
        selector_payload = dict(selector)
        selector_payload.pop("receipt_sha256")
        selector["receipt_sha256"] = sha256_json(selector_payload)
        hard_payload = dict(hard)
        hard_payload.pop("receipt_sha256")
        hard["receipt_sha256"] = sha256_json(hard_payload)
    _rechain(package, anchor)
    with pytest.raises(ValueError):
        v4.decide_qualification_v4(
            synthetic_chain["contract"],
            package,
            trust_anchor=anchor,
            expected_trust_anchor_root_sha256=anchor[
                "trust_anchor_root_sha256"
            ],
        )
    with pytest.raises(ValueError):
        v4_review.literal_decide_qualification_v4(
            synthetic_chain["contract"],
            package,
            trust_anchor=anchor,
            expected_trust_anchor_root_sha256=anchor[
                "trust_anchor_root_sha256"
            ],
        )


def test_reviewer_is_local_and_does_not_import_v4_producer_or_input_oracles() -> None:
    source = inspect.getsource(v4_review)
    assert "fair_pool_adaptation_contract_v4 import" not in source
    assert "fair_pool_input_manifest_v2 import" not in source
    assert "fair_nonholdout import" not in source
    assert "selector import" not in source
