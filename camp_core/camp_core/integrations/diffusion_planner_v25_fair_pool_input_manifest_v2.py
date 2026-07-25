"""Fail-closed input-only authority for V25 fair-pool adaptation contract v3.

This module never runs the model, pool generator, selector, or simulator.  It
deterministically derives the exact source-scene blueprint from an authorized
state specification and sealed map/route bytes, hashes actual tensor
preimages, derives the latent tensor from the frozen seed policy, and rebuilds
the Fresh B4 forbidden clone inventory from its sealed prepared-input bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_input_manifest as legacy_manifest,
)


SCHEMA_VERSION = "camp_dp_v25_fair_pool_input_only_manifest_v2"
SOURCE_SCENE_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_deterministic_source_scene_v1"
)
TENSOR_BUNDLE_SCHEMA_VERSION = "camp_dp_v25_tensor_bundle_preimage_manifest_v1"
LATENT_SCHEMA_VERSION = "camp_dp_v25_batched_k8_latent_manifest_v1"
RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_input_only_preflight_receipt_v2"
)
AUTHORITY_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_acquisition_authority_binding_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TENSOR_CONVERTER_SHA256 = (
    "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
)
ROUTE_ASSET_SHA256 = (
    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
)
MAP_SHA256 = "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
B4_PREOPEN_PATH = legacy_manifest.B4_PREOPEN_PATH
B4_PREOPEN_ROOT_SHA256 = legacy_manifest.B4_PREOPEN_ROOT_SHA256
B4_PREPARED_RUNTIME_CASES_SHA256 = (
    legacy_manifest.B4_PREPARED_RUNTIME_CASES_SHA256
)
STATE_SPEC_FIELDS = {
    "split",
    "state_spec_id",
    "state_index",
    "source_state_ordinal",
    "source_role",
    "source_sampler_module_sha256",
    "route_asset_sha256",
    "map_geometry_sha256",
    "family",
    "tier",
    "scenario_seed",
    "latent_seed",
    "latent_policy",
    "candidate_k",
    "independent_statistical_unit",
    "state_spec_sha256",
}
SOURCE_SCENE_FIELDS = {
    "schema_version",
    "state_spec_id",
    "state_spec_sha256",
    "source_state_ordinal",
    "split",
    "family",
    "tier",
    "scenario_seed",
    "map_geometry_sha256",
    "route_asset_sha256",
    "route_lanelet_ids",
    "spawn_pose",
    "goal_pose",
    "ordered_route_polyline_xy_m",
    "dynamic_actors_initial",
    "actor_generation_policy",
    "scenario_source_content_sha256",
    "source_scene_sha256",
}
MANIFEST_FIELDS = {
    "schema_version",
    "split",
    "state_spec_id",
    "state_spec_sha256",
    "source_state_ordinal",
    "scenario_seed",
    "latent_seed",
    "source_scene",
    "actual_input_tensor_manifest",
    "actual_state_sha256",
    "actual_latent_tensor_manifest",
    "clone_payload",
    "clone_key_sha256",
    "manifest_sha256",
}
TIER_ACTOR_COUNTS = {
    "no_npc": 0,
    "low_density": 2,
    "medium_density": 4,
    "high_density": 6,
}
ROUTE_LANELET_IDS = (3002178, 3002181, 3002185)
ROUTE_WORLD_XY_M = (
    (41.650352478027344, -166.84780883789062),
    (40.94586944580078, -163.01504516601562),
    (40.24015808105469, -159.18252563476562),
    (39.534156799316406, -155.3500518798828),
    (38.815608978271484, -151.5199432373047),
    (38.057830810546875, -147.69766235351562),
    (37.295597076416016, -143.87628173828125),
    (36.53434371948242, -140.05471801757812),
    (35.7720947265625, -136.23333740234375),
    (35.010719299316406, -132.41177368164062),
    (34.2730712890625, -128.58538818359375),
    (33.5578498840332, -124.75465393066406),
    (32.88887023925781, -121.12942504882812),
    (32.21886444091797, -117.50437927246094),
    (31.549686431884766, -113.87918853759766),
    (30.88129997253418, -110.25384521484375),
    (30.215145111083984, -106.64425659179688),
    (29.549076080322266, -103.03466033935547),
    (28.882953643798828, -99.42506408691406),
    (28.21786117553711, -95.81527709960938),
    (27.555999755859375, -92.20490264892578),
    (26.895748138427734, -88.59423828125),
    (26.232933044433594, -84.98403930664062),
    (25.565349578857422, -81.37474060058594),
    (24.89661407470703, -77.76565551757812),
    (24.23495101928711, -74.1552505493164),
)
SPAWN_POSE = {
    "x_m": 41.650352478027344,
    "y_m": -166.84780883789062,
    "z_m": 0.0,
    "heading_rad": 1.7525728940963745,
}
GOAL_POSE = {
    "x_m": 24.23495101928711,
    "y_m": -74.1552505493164,
    "z_m": 0.0,
    "heading_rad": 1.752050518989563,
}
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = "<f4"


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_state_spec(
    value: Mapping[str, Any],
    *,
    expected_split: str | None = None,
    expected_index: int | None = None,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != STATE_SPEC_FIELDS:
        raise ValueError("state spec exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("state_spec_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("state spec SHA drifted")
    split = payload["split"]
    if split not in {"development_calibration", "independent_validation"}:
        raise ValueError("state spec split drifted")
    if expected_split is not None and split != expected_split:
        raise ValueError("state spec split order drifted")
    index = payload["state_index"]
    if type(index) is not int or not 0 <= index < 64:
        raise ValueError("state index drifted")
    if expected_index is not None and index != expected_index:
        raise ValueError("state index order drifted")
    ordinal = index if split == "development_calibration" else 64 + index
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    expected_tier = tuple(TIER_ACTOR_COUNTS)[index % 4]
    expected = {
        "split": split,
        "state_spec_id": f"{split}:{index:03d}",
        "state_index": index,
        "source_state_ordinal": ordinal,
        "source_role": "development_nonholdout",
        "source_sampler_module_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "route_asset_sha256": ROUTE_ASSET_SHA256,
        "map_geometry_sha256": MAP_SHA256,
        "family": "four_track_highway",
        "tier": expected_tier,
        "scenario_seed": scenario_base + index,
        "latent_seed": latent_base + index,
        "latent_policy": (
            "row0_zero_rows1_7_numpy_default_rng_pcg64_"
            "standard_normal_float32_v1"
        ),
        "candidate_k": 8,
        "independent_statistical_unit": "state",
    }
    if payload != expected:
        raise ValueError("state spec deterministic authority drifted")
    return dict(value)


def materialize_exact_source_scene(
    *,
    state_spec: Mapping[str, Any],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
) -> dict[str, Any]:
    spec = validate_state_spec(state_spec)
    _exact_asset(route_asset_bytes, ROUTE_ASSET_SHA256, "route")
    _exact_asset(map_asset_bytes, MAP_SHA256, "map")
    actors = _deterministic_actors(
        int(spec["scenario_seed"]),
        str(spec["tier"]),
    )
    source_content = {
        "schema_version": "camp_dp_v25_fair_pool_source_content_v1",
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "tier": spec["tier"],
        "route_lanelet_ids": list(ROUTE_LANELET_IDS),
        "spawn_pose": dict(SPAWN_POSE),
        "goal_pose": dict(GOAL_POSE),
        "ordered_route_polyline_xy_m": [list(row) for row in ROUTE_WORLD_XY_M],
        "dynamic_actors_initial": actors,
        "actor_generation_policy": (
            "numpy_Generator_PCG64DXSM_scenario_seed;"
            "count_by_tier_0_2_4_6;route_fraction_even_slots_plus_"
            "uniform_minus_0_01_plus_0_01;lateral_offset_choice_"
            "minus_1_5_plus_1_5;speed_uniform_3_12;"
            "vehicle_length_4_5_width_2_0"
        ),
    }
    result = {
        "schema_version": SOURCE_SCENE_SCHEMA_VERSION,
        "state_spec_id": spec["state_spec_id"],
        "state_spec_sha256": spec["state_spec_sha256"],
        "source_state_ordinal": spec["source_state_ordinal"],
        "split": spec["split"],
        "family": spec["family"],
        "tier": spec["tier"],
        "scenario_seed": spec["scenario_seed"],
        "map_geometry_sha256": MAP_SHA256,
        "route_asset_sha256": ROUTE_ASSET_SHA256,
        "route_lanelet_ids": list(ROUTE_LANELET_IDS),
        "spawn_pose": dict(SPAWN_POSE),
        "goal_pose": dict(GOAL_POSE),
        "ordered_route_polyline_xy_m": [list(row) for row in ROUTE_WORLD_XY_M],
        "dynamic_actors_initial": actors,
        "actor_generation_policy": source_content["actor_generation_policy"],
        "scenario_source_content_sha256": sha256_json(source_content),
    }
    result["source_scene_sha256"] = sha256_json(result)
    return validate_source_scene(result, state_spec=spec)


def validate_source_scene(
    value: Mapping[str, Any],
    *,
    state_spec: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != SOURCE_SCENE_FIELDS:
        raise ValueError("source scene exact schema drifted")
    supplied = value["source_scene_sha256"]
    payload = dict(value)
    payload.pop("source_scene_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("source scene SHA drifted")
    if value["schema_version"] != SOURCE_SCENE_SCHEMA_VERSION:
        raise ValueError("source scene schema version drifted")
    spec = validate_state_spec(state_spec)
    for field in (
        "state_spec_id",
        "state_spec_sha256",
        "source_state_ordinal",
        "split",
        "family",
        "tier",
        "scenario_seed",
        "map_geometry_sha256",
        "route_asset_sha256",
    ):
        expected_field = {
            "map_geometry_sha256": "map_geometry_sha256",
            "route_asset_sha256": "route_asset_sha256",
        }.get(field, field)
        if value[field] != spec[expected_field]:
            raise ValueError(f"source scene {field} drifted")
    if value["spawn_pose"] != SPAWN_POSE or value["goal_pose"] != GOAL_POSE:
        raise ValueError("source scene spawn/goal drifted")
    if value["route_lanelet_ids"] != list(ROUTE_LANELET_IDS):
        raise ValueError("source scene lanelet route drifted")
    if value["ordered_route_polyline_xy_m"] != [
        list(row) for row in ROUTE_WORLD_XY_M
    ]:
        raise ValueError("source scene ordered route geometry drifted")
    expected_actors = _deterministic_actors(
        int(spec["scenario_seed"]), str(spec["tier"])
    )
    if value["dynamic_actors_initial"] != expected_actors:
        raise ValueError("source scene actors drifted")
    source_content = {
        "schema_version": "camp_dp_v25_fair_pool_source_content_v1",
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "tier": spec["tier"],
        "route_lanelet_ids": list(ROUTE_LANELET_IDS),
        "spawn_pose": dict(SPAWN_POSE),
        "goal_pose": dict(GOAL_POSE),
        "ordered_route_polyline_xy_m": [list(row) for row in ROUTE_WORLD_XY_M],
        "dynamic_actors_initial": expected_actors,
        "actor_generation_policy": value["actor_generation_policy"],
    }
    if value["scenario_source_content_sha256"] != sha256_json(source_content):
        raise ValueError("source scene content SHA drifted")
    return dict(value)


def materialize_latent_manifest(latent_seed: int) -> dict[str, Any]:
    if type(latent_seed) is not int or latent_seed < 0:
        raise ValueError("latent seed must be nonnegative integer")
    rng = np.random.default_rng(latent_seed)
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)
    raw = latent.astype(LATENT_DTYPE, copy=False).tobytes(order="C")
    result = {
        "schema_version": LATENT_SCHEMA_VERSION,
        "policy": (
            "row0_zero_rows1_7_numpy_default_rng_pcg64_"
            "standard_normal_float32_v1"
        ),
        "seed": latent_seed,
        "bit_generator": "PCG64",
        "dtype": LATENT_DTYPE,
        "shape": list(LATENT_SHAPE),
        "row0_all_zero": bool(np.all(latent[0] == 0.0)),
        "tensor_sha256": hashlib.sha256(raw).hexdigest(),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def materialize_tensor_bundle(
    arrays: Mapping[str, np.ndarray],
    *,
    source_scene_sha256: str,
) -> dict[str, Any]:
    if type(arrays) is not dict or not arrays:
        raise ValueError("actual input tensor bundle must be nonempty dict")
    _sha256(source_scene_sha256, "source scene")
    entries = []
    for name in sorted(arrays):
        if type(name) is not str or not name:
            raise ValueError("tensor name must be nonempty string")
        array = np.asarray(arrays[name])
        if array.dtype.kind not in "biuf" or not np.isfinite(array).all():
            raise ValueError("actual input tensor must be finite numeric")
        contiguous = np.ascontiguousarray(array)
        entries.append(
            {
                "name": name,
                "dtype": contiguous.dtype.str,
                "shape": list(contiguous.shape),
                "tensor_sha256": hashlib.sha256(
                    contiguous.tobytes(order="C")
                ).hexdigest(),
            }
        )
    result = {
        "schema_version": TENSOR_BUNDLE_SCHEMA_VERSION,
        "source_scene_sha256": source_scene_sha256,
        "fixed_dp_head": FIXED_DP_HEAD,
        "tensor_converter_path": "scenario_generation/tensor_converter.py",
        "tensor_converter_sha256": TENSOR_CONVERTER_SHA256,
        "tensor_converter_entrypoint": "to_model_tensors",
        "tensor_order": [entry["name"] for entry in entries],
        "tensors": entries,
    }
    result["bundle_sha256"] = sha256_json(result)
    return result


def materialize_input_only_manifest(
    *,
    state_spec: Mapping[str, Any],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    actual_input_tensors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    spec = validate_state_spec(state_spec)
    source_scene = materialize_exact_source_scene(
        state_spec=spec,
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
    )
    tensor_manifest = materialize_tensor_bundle(
        actual_input_tensors,
        source_scene_sha256=source_scene["source_scene_sha256"],
    )
    latent_manifest = materialize_latent_manifest(int(spec["latent_seed"]))
    clone_payload = legacy_manifest._clone_payload(  # noqa: SLF001
        map_geometry_sha256=MAP_SHA256,
        scenario_source_content_sha256=source_scene[
            "scenario_source_content_sha256"
        ],
        spawn_pose=source_scene["spawn_pose"],
        goal_pose=source_scene["goal_pose"],
        ordered_route_polyline_xy_m=source_scene[
            "ordered_route_polyline_xy_m"
        ],
        dynamic_actors_initial=source_scene["dynamic_actors_initial"],
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "split": spec["split"],
        "state_spec_id": spec["state_spec_id"],
        "state_spec_sha256": spec["state_spec_sha256"],
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "latent_seed": spec["latent_seed"],
        "source_scene": source_scene,
        "actual_input_tensor_manifest": tensor_manifest,
        "actual_state_sha256": source_scene["source_scene_sha256"],
        "actual_latent_tensor_manifest": latent_manifest,
        "clone_payload": clone_payload,
        "clone_key_sha256": sha256_json(clone_payload),
    }
    result["manifest_sha256"] = sha256_json(result)
    return validate_manifest(
        result,
        state_spec=spec,
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
        actual_input_tensors=actual_input_tensors,
    )


def validate_manifest(
    value: Mapping[str, Any],
    *,
    state_spec: Mapping[str, Any],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    actual_input_tensors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != MANIFEST_FIELDS:
        raise ValueError("input-only manifest exact schema drifted")
    payload = dict(value)
    supplied = payload.pop("manifest_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("input-only manifest outer SHA drifted")
    expected = materialize_input_only_manifest_unchecked(
        state_spec=state_spec,
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
        actual_input_tensors=actual_input_tensors,
    )
    if dict(value) != expected:
        raise ValueError("input-only manifest semantic reconstruction drifted")
    return dict(value)


def materialize_input_only_manifest_unchecked(
    *,
    state_spec: Mapping[str, Any],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    actual_input_tensors: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    spec = validate_state_spec(state_spec)
    source_scene = materialize_exact_source_scene(
        state_spec=spec,
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
    )
    tensor_manifest = materialize_tensor_bundle(
        actual_input_tensors,
        source_scene_sha256=source_scene["source_scene_sha256"],
    )
    latent_manifest = materialize_latent_manifest(int(spec["latent_seed"]))
    clone_payload = legacy_manifest._clone_payload(  # noqa: SLF001
        map_geometry_sha256=MAP_SHA256,
        scenario_source_content_sha256=source_scene[
            "scenario_source_content_sha256"
        ],
        spawn_pose=source_scene["spawn_pose"],
        goal_pose=source_scene["goal_pose"],
        ordered_route_polyline_xy_m=source_scene[
            "ordered_route_polyline_xy_m"
        ],
        dynamic_actors_initial=source_scene["dynamic_actors_initial"],
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "split": spec["split"],
        "state_spec_id": spec["state_spec_id"],
        "state_spec_sha256": spec["state_spec_sha256"],
        "source_state_ordinal": spec["source_state_ordinal"],
        "scenario_seed": spec["scenario_seed"],
        "latent_seed": spec["latent_seed"],
        "source_scene": source_scene,
        "actual_input_tensor_manifest": tensor_manifest,
        "actual_state_sha256": source_scene["source_scene_sha256"],
        "actual_latent_tensor_manifest": latent_manifest,
        "clone_payload": clone_payload,
        "clone_key_sha256": sha256_json(clone_payload),
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def validate_preflight_receipt(
    receipt: Mapping[str, Any],
    *,
    acquisition_authority: Mapping[str, Any],
    expected_acquisition_authority_root_sha256: str,
    expected_authorized_contract_root_sha256: str,
    expected_authorized_contract_review_root_sha256: str,
    calibration_specs: Sequence[Mapping[str, Any]],
    validation_specs: Sequence[Mapping[str, Any]],
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    prepared_runtime_cases_bytes: bytes,
    actual_input_tensors_by_state_id: Mapping[
        str, Mapping[str, np.ndarray]
    ],
) -> dict[str, Any]:
    authority = _validate_acquisition_authority(
        acquisition_authority,
        expected_authority_root=expected_acquisition_authority_root_sha256,
        expected_contract_root=expected_authorized_contract_root_sha256,
        expected_review_root=expected_authorized_contract_review_root_sha256,
    )
    if type(receipt) is not dict or set(receipt) != {
        "schema_version",
        "acquisition_authority",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "b4_forbidden_manifest_authority",
        "calibration_manifests",
        "validation_manifests",
        "model_pool_selector_call_count_before_receipt",
        "within_calibration_overlap_count",
        "within_validation_overlap_count",
        "cross_split_overlap_count",
        "b4_overlap_count",
        "no_drop_no_replacement",
        "status",
    }:
        raise ValueError("preflight receipt exact fields drifted")
    if receipt["schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise ValueError("preflight receipt schema drifted")
    if receipt["acquisition_authority"] != authority:
        raise ValueError("preflight acquisition authority drifted")
    if receipt["contract_root_sha256"] != expected_authorized_contract_root_sha256:
        raise ValueError("preflight contract root is not the authorized root")
    if (
        receipt["contract_review_root_sha256"]
        != expected_authorized_contract_review_root_sha256
    ):
        raise ValueError("preflight contract review root is not authorized")
    if receipt["model_pool_selector_call_count_before_receipt"] != 0:
        raise ValueError("preflight occurred after forbidden call")
    if receipt["no_drop_no_replacement"] is not True:
        raise ValueError("preflight drop/replacement policy drifted")
    calibration = _reconstruct_manifest_list(
        receipt["calibration_manifests"],
        specs=calibration_specs,
        split="development_calibration",
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
        actual_input_tensors_by_state_id=actual_input_tensors_by_state_id,
    )
    validation = _reconstruct_manifest_list(
        receipt["validation_manifests"],
        specs=validation_specs,
        split="independent_validation",
        route_asset_bytes=route_asset_bytes,
        map_asset_bytes=map_asset_bytes,
        actual_input_tensors_by_state_id=actual_input_tensors_by_state_id,
    )
    forbidden = legacy_manifest.materialize_b4_forbidden_clone_manifest(
        prepared_runtime_cases_bytes
    )
    expected_b4_authority = {
        "preopen_path": B4_PREOPEN_PATH,
        "preopen_root_sha256": B4_PREOPEN_ROOT_SHA256,
        "prepared_runtime_cases_sha256": B4_PREPARED_RUNTIME_CASES_SHA256,
        "derived_forbidden_manifest_sha256": forbidden["manifest_sha256"],
        "derived_forbidden_clone_key_count": 100,
        "derived_inside_validator_from_exact_bytes": True,
    }
    if receipt["b4_forbidden_manifest_authority"] != expected_b4_authority:
        raise ValueError("B4 forbidden exact-byte authority drifted")
    calibration_keys = [row["clone_key_sha256"] for row in calibration]
    validation_keys = [row["clone_key_sha256"] for row in validation]
    forbidden_keys = forbidden["clone_keys_sorted"]
    expected_counts = {
        "within_calibration_overlap_count": (
            len(calibration_keys) - len(set(calibration_keys))
        ),
        "within_validation_overlap_count": (
            len(validation_keys) - len(set(validation_keys))
        ),
        "cross_split_overlap_count": len(
            set(calibration_keys).intersection(validation_keys)
        ),
        "b4_overlap_count": len(
            set(calibration_keys + validation_keys).intersection(
                forbidden_keys
            )
        ),
    }
    for field, expected in expected_counts.items():
        if receipt[field] != expected or expected != 0:
            raise ValueError(f"{field} must be exactly zero")
    if receipt["status"] != "passed_before_first_model_pool_selector_call":
        raise ValueError("preflight status drifted")
    return dict(receipt)


def _reconstruct_manifest_list(
    supplied: Any,
    *,
    specs: Sequence[Mapping[str, Any]],
    split: str,
    route_asset_bytes: bytes,
    map_asset_bytes: bytes,
    actual_input_tensors_by_state_id: Mapping[
        str, Mapping[str, np.ndarray]
    ],
) -> list[dict[str, Any]]:
    if type(supplied) is not list or len(supplied) != 64:
        raise ValueError(f"{split} manifest denominator drifted")
    if type(specs) not in (list, tuple) or len(specs) != 64:
        raise ValueError(f"{split} state spec denominator drifted")
    expected = []
    for index, spec in enumerate(specs):
        checked = validate_state_spec(
            spec,
            expected_split=split,
            expected_index=index,
        )
        state_id = checked["state_spec_id"]
        if set(actual_input_tensors_by_state_id).issuperset({state_id}) is False:
            raise ValueError(f"{split} actual input preimage missing")
        expected.append(
            materialize_input_only_manifest_unchecked(
                state_spec=checked,
                route_asset_bytes=route_asset_bytes,
                map_asset_bytes=map_asset_bytes,
                actual_input_tensors=actual_input_tensors_by_state_id[state_id],
            )
        )
    if supplied != expected:
        raise ValueError(f"{split} manifest reconstruction drifted")
    return expected


def _validate_acquisition_authority(
    value: Mapping[str, Any],
    *,
    expected_authority_root: str,
    expected_contract_root: str,
    expected_review_root: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "status",
        "authority_artifact_path",
        "authority_artifact_root_sha256",
        "decision_sha256",
        "authorized_contract_root_sha256",
        "authorized_contract_review_root_sha256",
        "acquisition_authorized",
        "fresh_or_holdout_authorized",
    }:
        raise ValueError("acquisition authority exact schema drifted")
    if (
        value["schema_version"] != AUTHORITY_SCHEMA_VERSION
        or value["status"] != "authorized_by_future_versioned_high_control"
        or value["acquisition_authorized"] is not True
        or value["fresh_or_holdout_authorized"] is not False
    ):
        raise ValueError("acquisition is not authorized")
    if type(value["authority_artifact_path"]) is not str or not value[
        "authority_artifact_path"
    ].startswith("/root/autodl-tmp/"):
        raise ValueError("acquisition authority path drifted")
    if value["authority_artifact_root_sha256"] != _sha256(
        expected_authority_root, "authorized acquisition authority root"
    ):
        raise ValueError("acquisition authority artifact root drifted")
    _sha256(value["decision_sha256"], "acquisition authority decision")
    if value["authorized_contract_root_sha256"] != _sha256(
        expected_contract_root, "authorized contract root"
    ):
        raise ValueError("acquisition authority contract root drifted")
    if value["authorized_contract_review_root_sha256"] != _sha256(
        expected_review_root, "authorized contract review root"
    ):
        raise ValueError("acquisition authority review root drifted")
    return dict(value)


def _deterministic_actors(seed: int, tier: str) -> list[dict[str, Any]]:
    if tier not in TIER_ACTOR_COUNTS:
        raise ValueError("density tier drifted")
    count = TIER_ACTOR_COUNTS[tier]
    rng = np.random.Generator(np.random.PCG64DXSM(seed))
    route = np.asarray(ROUTE_WORLD_XY_M, dtype=np.float64)
    segment = np.diff(route, axis=0)
    lengths = np.linalg.norm(segment, axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(cumulative[-1])
    actors = []
    for index in range(count):
        fraction = (index + 1) / (count + 1)
        fraction += float(rng.uniform(-0.01, 0.01))
        arc = min(total, max(0.0, fraction * total))
        segment_index = min(
            len(lengths) - 1,
            int(np.searchsorted(cumulative[1:], arc, side="right")),
        )
        local = (arc - cumulative[segment_index]) / lengths[segment_index]
        point = route[segment_index] + local * segment[segment_index]
        tangent = segment[segment_index] / lengths[segment_index]
        normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
        lateral = -1.5 if int(rng.integers(0, 2)) == 0 else 1.5
        position = point + lateral * normal
        actors.append(
            {
                "class": "vehicle",
                "length_m": 4.5,
                "width_m": 2.0,
                "x_m": float(position[0]),
                "y_m": float(position[1]),
                "heading_rad": float(math.atan2(tangent[1], tangent[0])),
                "speed_mps": float(rng.uniform(3.0, 12.0)),
            }
        )
    return actors


def _exact_asset(value: Any, expected_sha: str, label: str) -> bytes:
    if type(value) is not bytes:
        raise ValueError(f"{label} asset must be exact bytes")
    if hashlib.sha256(value).hexdigest() != expected_sha:
        raise ValueError(f"{label} asset SHA drifted")
    return value


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
