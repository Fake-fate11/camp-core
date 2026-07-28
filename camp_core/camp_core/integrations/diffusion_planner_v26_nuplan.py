"""V26-native, outcome-blind nuPlan source and same-ego B8 contracts.

This module deliberately owns only the official-source identity boundary and
the fixed-DP B8 topology.  It neither reads expert futures/outcomes nor imports
the V18/V25 candidate exporters, runners, validators, or evaluators.
"""

from __future__ import annotations

from contextlib import nullcontext
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

import numpy as np

from .diffusion_planner_v21_native import (
    array_sha256,
    candidate_latents,
    candidate_seed,
    verify_default_candidate0_identity,
)
from .diffusion_planner_causal_atoms import CANDIDATE_LOCAL_EXACT_SPEED
from .nuplan_causal_adapter import materialize_nuplan_planner_input


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
NUPLAN_SOURCE_SCHEMA_VERSION = "camp_dp_v26_official_nuplan_v11_source_v1"
NUPLAN_SPLIT_MANIFEST_SCHEMA_VERSION = (
    "camp_dp_v26_official_nuplan_v11_group_split_manifest_v1"
)
NUPLAN_ACADEMIC_CITY_SOURCE_PLAN_SCHEMA_VERSION = (
    "camp_dp_v26_nuplan_v11_academic_city_source_plan_v1"
)
NUPLAN_B8_TOPOLOGY_SCHEMA_VERSION = "camp_dp_v26_nuplan_same_ego_b8_v1"
NUPLAN_V26_ADAPTER_ID = "camp_dp_v26_official_nuplan_input_adapter_v1"
NUPLAN_V26_RUNNER_ID = "camp_dp_v26_official_nuplan_same_ego_b8_runner_v1"

OFFICIAL_SPLITS = ("train", "val", "test")
MINI_SMOKE_SPLIT = "mini"
_SOURCE_SPLITS = frozenset((*OFFICIAL_SPLITS, MINI_SMOKE_SPLIT))
SMOKE_ARMS = ("candidate0", "Static14D", "Scene14D")
_SHA256_LENGTH = 64
_SOURCE_REQUIRED_FIELDS = frozenset(
    {
        "record_id",
        "official_split",
        "log_token",
        "scenario_token",
        "scene_token",
        "state_token",
        "mission_route_roadblock_chain_sha256",
        "corridor_id",
        "geometry_clone_group_sha256",
        "city",
        "map_family",
        "source_db_sha256",
        "map_sha256",
        "event_strata",
    }
)
_OUTCOME_FIELD_TOKENS = frozenset(
    {
        "action",
        "candidate",
        "collision",
        "completion",
        "endpoint_value",
        "expert_future",
        "future_trajectory",
        "label",
        "outcome",
        "reward",
        "safety_cost",
        "score",
        "selected_index",
        "trajectory",
    }
)
_ACADEMIC_CITY_SOURCE_SPEC = {
    "boston": {
        "map_family": "us-ma-boston",
        "academic_role": "iid_grouped_source",
    },
    "pittsburgh": {
        "map_family": "us-pa-pittsburgh-hazelwood",
        "academic_role": "iid_grouped_source",
    },
    "singapore": {
        "map_family": "sg-one-north",
        "academic_role": "city_held_out_ood",
    },
}
_CITY_ARCHIVE_STATUSES = frozenset(
    {"official_identity_verified", "external_authenticated_manifest_pending"}
)
_SENSITIVE_ACCESS_FIELD_TOKENS = frozenset(
    {"cookie", "password", "secret", "signature", "signed_url", "token"}
)


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a non-secret receipt deterministically."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def v26_nuplan_b8_topology() -> dict[str, Any]:
    """Return the frozen current-pool topology, without running a model."""

    return {
        "schema_version": NUPLAN_B8_TOPOLOGY_SCHEMA_VERSION,
        "generator_id": "fixed_dp_same_ego_single_invocation_b8_v1",
        "runner_id": NUPLAN_V26_RUNNER_ID,
        "same_ego_batch_size": 8,
        "primary_forward_count": 1,
        "sequential_forward_count": 0,
        "candidate0_row": 0,
        "selector_arms": list(SMOKE_ARMS),
        "selector_pool_semantics": "same_current_pool_only",
        "post_pool_model_calls": 0,
        "post_pool_dp_calls": 0,
        "post_pool_latent_calls": 0,
        "post_pool_generation_calls": 0,
        "candidate_pool_mutation_count": 0,
        "trajectory_regeneration_count": 0,
    }


def materialize_v26_nuplan_planner_input(
    current_input: Any,
    initialization: Any,
    *,
    source_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize one official nuPlan state without a future/outcome channel.

    ``materialize_nuplan_planner_input`` is a narrow raw-state adapter.  V26
    wraps it here so source identity and the no-outcome boundary are retained in
    the receipt rather than being inherited from any historical candidate pool.
    """

    identity = validate_v26_nuplan_source_record(source_identity)
    # Missing speed authority is an endpoint-applicability fact, not a reason
    # to discard an otherwise source-valid scenario before the fixed-DP pool.
    materialized = materialize_nuplan_planner_input(
        current_input,
        initialization,
        speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
    )
    has_speed = bool(
        np.any(
            np.asarray(
                materialized.dp_input.get("lanes_has_speed_limit", ()), dtype=bool
            )
        )
    )
    has_signal = bool(getattr(current_input, "traffic_light_data", None))
    return {
        "adapter_id": NUPLAN_V26_ADAPTER_ID,
        "source_schema_version": NUPLAN_SOURCE_SCHEMA_VERSION,
        "source_identity": identity,
        "dp_input": materialized.dp_input,
        "materialization_metadata": dict(materialized.metadata),
        "endpoint_applicability": {
            "red_light": "observed" if has_signal else "missing_or_inapplicable",
            "speed_limit": "observed" if has_speed else "missing_or_inapplicable",
        },
        "outcome_fields_consumed": [],
    }


def validate_v26_nuplan_source_record(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one identity-only official nuPlan source record."""

    if not isinstance(value, Mapping):
        raise ValueError("nuPlan source record must be a mapping")
    missing = _SOURCE_REQUIRED_FIELDS - set(value)
    if missing:
        raise ValueError(f"nuPlan source record missing fields: {sorted(missing)}")
    _reject_outcome_fields(value)

    record: dict[str, Any] = {}
    for field in _SOURCE_REQUIRED_FIELDS - {"event_strata"}:
        record[field] = _nonempty_string(value[field], field)
    if record["official_split"] not in _SOURCE_SPLITS:
        raise ValueError("official_split must be train, val, test, or mini")
    for field in (
        "mission_route_roadblock_chain_sha256",
        "geometry_clone_group_sha256",
        "source_db_sha256",
        "map_sha256",
    ):
        _require_sha256(record[field], field)

    strata = value["event_strata"]
    if not isinstance(strata, Sequence) or isinstance(strata, (str, bytes)):
        raise ValueError("event_strata must be a sequence of source labels")
    normalized_strata = sorted({_nonempty_string(item, "event_strata") for item in strata})
    record["event_strata"] = normalized_strata
    record["source_identity_sha256"] = canonical_json_sha256(
        {
            key: record[key]
            for key in (
                "log_token",
                "scenario_token",
                "scene_token",
                "state_token",
                "mission_route_roadblock_chain_sha256",
                "corridor_id",
                "geometry_clone_group_sha256",
                "city",
                "map_family",
                "source_db_sha256",
                "map_sha256",
                "event_strata",
            )
        }
    )
    return record


def build_v26_nuplan_split_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    raw_source: Mapping[str, Any],
    fixed_dp: Mapping[str, Any],
    camp_source_head: str,
    ood_city_map_families: Iterable[tuple[str, str]] = (),
) -> dict[str, Any]:
    """Freeze outcome-independent official/IID/OOD source membership.

    Official train/val/test remains the top-level source split.  The optional
    OOD set may only be a disjoint city/map-family subset of official test;
    anything else is rejected instead of silently redistributing records.
    """

    normalized = [validate_v26_nuplan_source_record(record) for record in records]
    if not normalized:
        raise ValueError("official nuPlan source inventory is empty")
    if any(record["official_split"] not in OFFICIAL_SPLITS for record in normalized):
        raise ValueError("formal nuPlan source manifest cannot include mini smoke records")
    normalized.sort(key=lambda record: record["record_id"])
    record_ids = [record["record_id"] for record in normalized]
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("official nuPlan source record_id values must be unique")
    identities = [record["source_identity_sha256"] for record in normalized]
    if len(set(identities)) != len(identities):
        raise ValueError("official nuPlan source identities must be unique")

    raw = _validate_raw_source(raw_source)
    dp = _validate_fixed_dp_binding(fixed_dp)
    _require_commit(camp_source_head, "camp_source_head")
    ood_pairs = {
        (_nonempty_string(city, "ood city"), _nonempty_string(family, "ood map_family"))
        for city, family in ood_city_map_families
    }

    _validate_group_disjointness(normalized)
    partitions: dict[str, list[dict[str, Any]]] = {
        "train_iid": [],
        "val_iid": [],
        "test_iid": [],
        "test_ood": [],
    }
    for record in normalized:
        city_map = (record["city"], record["map_family"])
        if city_map in ood_pairs:
            if record["official_split"] != "test":
                raise ValueError("OOD city/map-family must be confined to official test")
            partition = "test_ood"
        else:
            partition = f'{record["official_split"]}_iid'
        enriched = dict(record)
        enriched["leakage_group_sha256"] = canonical_json_sha256(
            {
                "log_token": record["log_token"],
                "scenario_token": record["scenario_token"],
                "mission_route_roadblock_chain_sha256": record[
                    "mission_route_roadblock_chain_sha256"
                ],
                "corridor_id": record["corridor_id"],
                "geometry_clone_group_sha256": record["geometry_clone_group_sha256"],
            }
        )
        enriched["cluster_id"] = canonical_json_sha256(
            {"log_token": record["log_token"], "corridor_id": record["corridor_id"]}
        )
        partitions[partition].append(enriched)

    _validate_partition_disjointness(partitions)
    payload = {
        "schema_version": NUPLAN_SPLIT_MANIFEST_SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_official_nuplan_source_manifest",
        "outcome_fields_consumed": [],
        "raw_source": raw,
        "fixed_dp": dp,
        "camp_source_head": camp_source_head,
        "generator_topology": v26_nuplan_b8_topology(),
        "cluster_unit": "log_token_plus_corridor_id",
        "official_split_upper_layer": list(OFFICIAL_SPLITS),
        "ood_city_map_families": [
            {"city": city, "map_family": family} for city, family in sorted(ood_pairs)
        ],
        "partitions": {
            name: _partition_summary(rows) for name, rows in partitions.items()
        },
        "records": [
            record
            for name in ("train_iid", "val_iid", "test_iid", "test_ood")
            for record in partitions[name]
        ],
    }
    payload["identity_manifest_sha256"] = canonical_json_sha256(payload)
    return payload


def validate_v26_nuplan_split_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild and verify the identity-only manifest byte-for-byte."""

    if value.get("schema_version") != NUPLAN_SPLIT_MANIFEST_SCHEMA_VERSION:
        raise ValueError("nuPlan V26 split manifest schema drifted")
    if value.get("evidence_role") != "development_nonholdout_official_nuplan_source_manifest":
        raise ValueError("nuPlan V26 split manifest role drifted")
    if value.get("outcome_fields_consumed") != []:
        raise ValueError("nuPlan V26 split manifest consumed outcomes")
    ood_pairs = [
        (item.get("city"), item.get("map_family"))
        for item in value.get("ood_city_map_families", [])
        if isinstance(item, Mapping)
    ]
    rebuilt = build_v26_nuplan_split_manifest(
        value.get("records", []),
        raw_source=value.get("raw_source", {}),
        fixed_dp=value.get("fixed_dp", {}),
        camp_source_head=value.get("camp_source_head"),
        ood_city_map_families=ood_pairs,
    )
    if rebuilt != dict(value):
        raise ValueError("nuPlan V26 split manifest is not a deterministic rebuild")
    return rebuilt


def build_v26_nuplan_academic_city_source_plan(
    sources: Iterable[Mapping[str, Any]],
    *,
    fixed_dp: Mapping[str, Any],
    camp_source_head: str,
) -> dict[str, Any]:
    """Freeze the three-city, DB-only V26 source boundary before outcomes.

    This deliberately does not repurpose official val/test as a local holdout:
    Boston and Pittsburgh form the future IID grouped-validation source, while
    Singapore is a whole-city OOD source.  Per-record group allocation happens
    only after DB inventory and is therefore outside this archive-identity plan.
    """

    normalized = [_validate_academic_city_source(source) for source in sources]
    normalized.sort(key=lambda source: source["city"])
    cities = [source["city"] for source in normalized]
    if cities != sorted(_ACADEMIC_CITY_SOURCE_SPEC):
        raise ValueError("academic city source plan must contain Boston, Pittsburgh, Singapore")
    if len(set(cities)) != len(cities):
        raise ValueError("academic city source plan contains a duplicate city")
    if any(
        source["archive_status"] != "official_identity_verified"
        for source in normalized
    ):
        raise ValueError("academic city source plan has an unverified archive identity")

    dp = _validate_fixed_dp_binding(fixed_dp)
    _require_commit(camp_source_head, "camp_source_head")
    payload = {
        "schema_version": NUPLAN_ACADEMIC_CITY_SOURCE_PLAN_SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_nuplan_academic_city_source_plan",
        "outcome_fields_consumed": [],
        "camp_source_head": camp_source_head,
        "fixed_dp": dp,
        "generator_topology": v26_nuplan_b8_topology(),
        "split_design": {
            "kind": "outcome_independent_custom_academic_group_split",
            "iid_source_cities": ["boston", "pittsburgh"],
            "city_held_out_ood": "singapore",
            "group_keys": [
                "log_token",
                "scenario_token",
                "mission_route_roadblock_chain",
                "corridor_id",
                "geometry_clone_group",
            ],
            "cluster_unit": "log_token_plus_corridor_id",
            "official_val_test": "future_expansion_not_downloaded",
            "las_vegas": "future_expansion_not_downloaded",
            "sensor_blobs": "not_requested_unless_adapter_proven_necessary",
        },
        "city_archives": normalized,
    }
    payload["source_plan_sha256"] = canonical_json_sha256(payload)
    return payload


def validate_v26_nuplan_academic_city_source_plan(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild an academic city source plan without reading data payloads."""

    if value.get("schema_version") != NUPLAN_ACADEMIC_CITY_SOURCE_PLAN_SCHEMA_VERSION:
        raise ValueError("academic city source plan schema drifted")
    if value.get("evidence_role") != "development_nonholdout_nuplan_academic_city_source_plan":
        raise ValueError("academic city source plan role drifted")
    if value.get("outcome_fields_consumed") != []:
        raise ValueError("academic city source plan consumed outcomes")
    rebuilt = build_v26_nuplan_academic_city_source_plan(
        value.get("city_archives", []),
        fixed_dp=value.get("fixed_dp", {}),
        camp_source_head=value.get("camp_source_head"),
    )
    if rebuilt != dict(value):
        raise ValueError("academic city source plan is not a deterministic rebuild")
    return rebuilt


def build_same_ego_b8_model_input(
    normalized_single_input: Mapping[str, Any],
    latent_rows: np.ndarray,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Expand a batch-one fixed-DP input into one same-ego B8 invocation."""

    latents = np.ascontiguousarray(np.asarray(latent_rows, dtype=np.float32))
    _validate_latent_rows(latents)
    if not normalized_single_input:
        raise ValueError("fixed-DP normalized input is empty")
    expanded: dict[str, Any] = {}
    for key, value in normalized_single_input.items():
        if not hasattr(value, "shape") or len(value.shape) < 1 or int(value.shape[0]) != 1:
            raise ValueError("fixed-DP normalized input must be batch-one")
        if key == "sampled_trajectories":
            expanded[key] = _as_like_tensor(latents, value)
        elif isinstance(value, np.ndarray):
            expanded[key] = np.repeat(value, 8, axis=0)
        else:
            expanded[key] = value.expand(8, *value.shape[1:]).contiguous()
    metadata = _same_ego_batch_metadata(expanded)
    if tuple(expanded["sampled_trajectories"].shape) != tuple(latents.shape):
        raise ValueError("same-ego B8 latent shape drifted")
    return expanded, metadata


def run_v26_nuplan_single_invocation_b8(
    *,
    model: Any,
    normalized_single_input: Mapping[str, Any],
    route_identity_sha256: str,
    tick_index: int,
    root_seed: int,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    """Run exactly one fixed-DP forward and return an immutable B8 pool.

    The caller owns fixed-DP model construction and source materialization.  By
    accepting a normalized batch-one input, this narrow V26 entry cannot reuse a
    historical K8 artifact or issue the legacy sequential 1+7 forwards.
    """

    _require_sha256(route_identity_sha256, "route_identity_sha256")
    if isinstance(tick_index, bool) or not isinstance(tick_index, int) or tick_index < 0:
        raise ValueError("tick_index must be a nonnegative integer")
    if isinstance(root_seed, bool) or not isinstance(root_seed, int) or root_seed < 0:
        raise ValueError("root_seed must be a nonnegative integer")
    latent_seed = candidate_seed(root_seed, route_identity_sha256, tick_index)
    latents = candidate_latents(latent_seed, noise_scale=1.0)
    expanded, same_ego_metadata = build_same_ego_b8_model_input(
        normalized_single_input, latents
    )
    context = nullcontext()
    if torch_module is not None and hasattr(torch_module, "no_grad"):
        context = torch_module.no_grad()
    with context:
        result = model({key: _clone_tensor(value) for key, value in expanded.items()})
    outputs = result[1] if isinstance(result, tuple) and len(result) == 2 else result
    if not isinstance(outputs, Mapping) or "prediction" not in outputs:
        raise ValueError("fixed-DP single invocation returned no prediction")
    prediction = _as_numpy(outputs["prediction"])
    if prediction.shape != (8, 321, 80, 4) or not np.isfinite(prediction).all():
        raise ValueError("fixed-DP B8 prediction must be finite [8,321,80,4]")
    candidates = np.ascontiguousarray(prediction[:, 0], dtype=np.float32)
    row_sha = [array_sha256(row) for row in candidates]
    if len(set(row_sha)) != 8:
        raise ValueError("fixed-DP B8 candidate rows are not unique")
    candidate0 = verify_default_candidate0_identity(candidates[0], candidates[0])
    return {
        "generator_topology": v26_nuplan_b8_topology(),
        "same_ego_batch_metadata": same_ego_metadata,
        "latent_seed": latent_seed,
        "latent_shape": list(latents.shape),
        "latent_dtype": str(latents.dtype),
        "latent_tensor_sha256": array_sha256(latents),
        "latent_row_sha256": [array_sha256(row) for row in latents],
        "candidate_tensor": candidates,
        "candidate_tensor_sha256_before": array_sha256(candidates),
        "candidate_row_sha256": row_sha,
        "candidate_shape": list(candidates.shape),
        "candidate_dtype": str(candidates.dtype),
        "candidate_finite": True,
        "candidate0": candidate0,
        "primary_forward_count": 1,
        "sequential_forward_count": 0,
    }


def bind_v26_nuplan_same_pool_selectors(
    pool: Mapping[str, Any],
    selector_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind candidate0/Static14D/Scene14D to one immutable B8 pool."""

    candidates = np.ascontiguousarray(np.asarray(pool["candidate_tensor"], dtype=np.float32))
    before = _nonempty_string(pool.get("candidate_tensor_sha256_before"), "pool hash")
    if array_sha256(candidates) != before:
        raise ValueError("same-pool selector received a mutated candidate tensor")
    if tuple(selector_receipts) != SMOKE_ARMS:
        raise ValueError("nuPlan B8 smoke selectors must be candidate0, Static14D, Scene14D")
    rows = list(pool.get("candidate_row_sha256", []))
    if len(rows) != 8 or len(set(rows)) != 8:
        raise ValueError("same-pool candidate rows are not an eight-row identity set")
    bound: dict[str, dict[str, Any]] = {}
    for arm in SMOKE_ARMS:
        receipt = dict(selector_receipts[arm])
        index = receipt.get("selected_index")
        if not isinstance(index, int) or not 0 <= index < 8:
            raise ValueError(f"{arm} selected_index must bind a B8 row")
        if arm == "candidate0" and index != 0:
            raise ValueError("candidate0 must remain frozen row 0")
        if receipt.get("selected_row_sha256") != rows[index]:
            raise ValueError(f"{arm} selected row does not bind the same B8 pool")
        if receipt.get("candidate_pool_sha256", before) != before:
            raise ValueError(f"{arm} selector pool hash drifted")
        bound[arm] = {
            **receipt,
            "candidate_pool_sha256": before,
            "selected_index": index,
            "selected_row_sha256": rows[index],
        }
    if array_sha256(candidates) != before:
        raise ValueError("selector mutated the frozen B8 candidate pool")
    return {
        "selector_receipts": bound,
        "candidate_pool_sha256_before": before,
        "candidate_pool_sha256_after": before,
        "post_pool_call_counts": {
            "model": 0,
            "dp": 0,
            "latent": 0,
            "generation": 0,
            "candidate_pool_mutation": 0,
            "trajectory_regeneration": 0,
        },
    }


def _validate_raw_source(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("raw_source must be a mapping")
    required = {
        "nuplan_dataset_version",
        "official_split_entrypoint",
        "official_split_metadata_sha256",
        "data_root_identity_sha256",
        "maps_root_identity_sha256",
    }
    missing = required - set(value)
    if missing:
        raise ValueError(f"raw_source missing fields: {sorted(missing)}")
    result = {key: _nonempty_string(value[key], f"raw_source.{key}") for key in required}
    if result["nuplan_dataset_version"] != "v1.1":
        raise ValueError("V26 nuPlan source must be official v1.1 raw data")
    for field in (
        "official_split_metadata_sha256",
        "data_root_identity_sha256",
        "maps_root_identity_sha256",
    ):
        _require_sha256(result[field], f"raw_source.{field}")
    return result


def _validate_fixed_dp_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("fixed_dp must be a mapping")
    required = {"head", "checkpoint_sha256", "args_sha256"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"fixed_dp missing fields: {sorted(missing)}")
    result = {key: _nonempty_string(value[key], f"fixed_dp.{key}") for key in required}
    if result["head"] != FIXED_DP_HEAD:
        raise ValueError("V26 nuPlan fixed DP head drifted")
    _require_sha256(result["checkpoint_sha256"], "fixed_dp.checkpoint_sha256")
    _require_sha256(result["args_sha256"], "fixed_dp.args_sha256")
    return result


def _validate_academic_city_source(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("academic city archive must be a mapping")
    _reject_sensitive_access_fields(value)
    required = {
        "city",
        "map_family",
        "academic_role",
        "archive_status",
        "archive_url",
        "archive_filename",
        "content_length",
        "etag",
        "last_modified",
        "accept_ranges",
        "content_type",
    }
    if set(value) != required:
        raise ValueError("academic city archive fields drifted")
    result = {
        key: _nonempty_string(value[key], f"academic city archive.{key}")
        for key in required
        if key != "content_length"
    }
    content_length = value["content_length"]
    if isinstance(content_length, bool) or not isinstance(content_length, int) or content_length <= 0:
        raise ValueError("academic city archive.content_length must be a positive integer")
    result["content_length"] = content_length
    if result["city"] not in _ACADEMIC_CITY_SOURCE_SPEC:
        raise ValueError("academic city archive city is not in the frozen three-city design")
    expected = _ACADEMIC_CITY_SOURCE_SPEC[result["city"]]
    if result["map_family"] != expected["map_family"]:
        raise ValueError("academic city archive map_family drifted")
    if result["academic_role"] != expected["academic_role"]:
        raise ValueError("academic city archive role drifted")
    if result["archive_status"] not in _CITY_ARCHIVE_STATUSES:
        raise ValueError("academic city archive status is invalid")
    if result["archive_status"] != "official_identity_verified":
        raise ValueError("academic city archive must have verified official identity")
    parts = urlsplit(result["archive_url"])
    if (
        parts.scheme != "https"
        or parts.netloc != "motional-nuplan.s3.amazonaws.com"
        or bool(parts.query)
        or bool(parts.fragment)
        or parts.username is not None
        or parts.password is not None
        or not parts.path.startswith("/public/nuplan-v1.1/")
    ):
        raise ValueError("academic city archive URL must be a non-secret official object URL")
    filename = parts.path.rsplit("/", 1)[-1]
    if filename != result["archive_filename"]:
        raise ValueError("academic city archive filename does not bind its URL")
    if result["content_type"] != "application/zip":
        raise ValueError("academic city archive content_type must be application/zip")
    if result["accept_ranges"] != "bytes":
        raise ValueError("academic city archive must support byte-range resume")
    return {
        "city": result["city"],
        "map_family": result["map_family"],
        "academic_role": result["academic_role"],
        "archive_status": result["archive_status"],
        "archive_url": result["archive_url"],
        "archive_filename": result["archive_filename"],
        "content_length": result["content_length"],
        "etag": result["etag"],
        "last_modified": result["last_modified"],
        "accept_ranges": result["accept_ranges"],
        "content_type": result["content_type"],
    }


def _validate_group_disjointness(records: Sequence[Mapping[str, Any]]) -> None:
    for field in (
        "log_token",
        "mission_route_roadblock_chain_sha256",
        "corridor_id",
        "geometry_clone_group_sha256",
    ):
        membership: dict[str, set[str]] = {}
        for record in records:
            membership.setdefault(str(record[field]), set()).add(str(record["official_split"]))
        conflicts = sorted(key for key, splits in membership.items() if len(splits) > 1)
        if conflicts:
            raise ValueError(f"official split group overlap for {field}: {conflicts[:3]}")


def _validate_partition_disjointness(partitions: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    seen: dict[str, str] = {}
    for partition, rows in partitions.items():
        for row in rows:
            identity = str(row["source_identity_sha256"])
            if identity in seen:
                raise ValueError(
                    f"source identity appears in both {seen[identity]} and {partition}"
                )
            seen[identity] = partition
    ood_rows = partitions["test_ood"]
    iid_rows = [
        row for name, rows in partitions.items() if name != "test_ood" for row in rows
    ]
    ood_city_maps = {(row["city"], row["map_family"]) for row in ood_rows}
    if ood_city_maps & {(row["city"], row["map_family"]) for row in iid_rows}:
        raise ValueError("OOD city/map-family overlaps IID source membership")


def _partition_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row["record_id"])
    return {
        "record_count": len(ordered),
        "cluster_count": len({row["cluster_id"] for row in ordered}),
        "record_ids": [row["record_id"] for row in ordered],
        "source_identity_sha256": [row["source_identity_sha256"] for row in ordered],
        "city_map_family_counts": _count_rows(ordered, ("city", "map_family")),
        "event_strata_counts": _event_counts(ordered),
    }


def _count_rows(rows: Sequence[Mapping[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, ...], int] = {}
    for row in rows:
        key = tuple(str(row[field]) for field in fields)
        counts[key] = counts.get(key, 0) + 1
    return [
        {**dict(zip(fields, key)), "count": count}
        for key, count in sorted(counts.items())
    ]


def _event_counts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in rows:
        for stratum in row["event_strata"]:
            counts[str(stratum)] = counts.get(str(stratum), 0) + 1
    return [{"event_stratum": key, "count": value} for key, value in sorted(counts.items())]


def _same_ego_batch_metadata(tensors: Mapping[str, Any]) -> dict[str, Any]:
    metadata: dict[str, dict[str, Any]] = {}
    for key, value in sorted(tensors.items()):
        array = _as_numpy(value)
        if array.ndim < 1 or array.shape[0] != 8:
            raise ValueError("V26 nuPlan B8 input has the wrong batch axis")
        if np.issubdtype(array.dtype, np.inexact) and not np.isfinite(array).all():
            raise ValueError("V26 nuPlan B8 input is nonfinite")
        if key != "sampled_trajectories" and not np.array_equal(array, array[0:1].repeat(8, axis=0)):
            raise ValueError("V26 nuPlan nonlatent B8 rows differ")
        metadata[key] = {
            "shape": [int(item) for item in array.shape],
            "dtype": str(array.dtype),
            "finite": True,
        }
    return {
        "same_ego_batch_size": 8,
        "nonlatent_rows_identical": True,
        "tensor_metadata": metadata,
    }


def _validate_latent_rows(value: np.ndarray) -> None:
    if value.shape != (8, 321, 81, 4) or value.dtype != np.float32:
        raise ValueError("V26 nuPlan latent policy requires float32 [8,321,81,4]")
    if not np.isfinite(value).all() or not np.array_equal(value[0], np.zeros_like(value[0])):
        raise ValueError("V26 nuPlan latent row 0 must be finite zeros")
    if len({array_sha256(row) for row in value}) != 8:
        raise ValueError("V26 nuPlan latent rows must be unique")


def _as_like_tensor(value: np.ndarray, reference: Any) -> Any:
    if isinstance(reference, np.ndarray):
        return np.asarray(value, dtype=reference.dtype)
    torch = __import__("torch")
    return torch.from_numpy(np.array(value, copy=True)).to(
        device=reference.device,
        dtype=reference.dtype,
    ).contiguous()


def _clone_tensor(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    return value.detach().clone()


def _as_numpy(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return np.asarray(value)
    return value.detach().cpu().contiguous().numpy()


def _reject_outcome_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in _OUTCOME_FIELD_TOKENS:
                raise ValueError(f"outcome field is forbidden in V26 nuPlan source: {key}")
            _reject_outcome_fields(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_outcome_fields(item)


def _reject_sensitive_access_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_ACCESS_FIELD_TOKENS:
                raise ValueError("academic city source plan must not contain access credentials")
            _reject_sensitive_access_fields(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_sensitive_access_fields(item)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _require_sha256(value: Any, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")


def _require_commit(value: Any, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase Git commit SHA")
