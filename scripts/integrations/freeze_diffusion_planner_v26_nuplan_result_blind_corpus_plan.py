#!/usr/bin/env python3
"""Freeze an identity-only V26 three-city corpus and reporting plan.

The input is the full-population V26 sampling manifest.  Its selected-anchor
array can be several gigabytes, so this entrypoint streams it rather than
loading it into memory.  It never reads a nuPlan DB, candidate, trajectory,
label, endpoint value, selector score, or outcome.  It first projects the
mandatory identity-only rare-event and stratum-coverage set for every
partition, then uses ``max(target, mandatory_lower_bound)`` for each effective
quota.  This preserves rare anchors rather than silently dropping them when a
target is too small.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    FIXED_DP_HEAD,
    canonical_json_bytes,
    canonical_json_sha256,
)


SCHEMA_VERSION = "camp_dp_v26_nuplan_result_blind_corpus_plan_v2"
EVIDENCE_ROLE = "development_nonholdout_nuplan_result_blind_corpus_plan"
INPUT_SCHEMA_VERSION = "camp_dp_v26_nuplan_full_population_sampling_manifest_v1"
INPUT_EVIDENCE_ROLE = "development_nonholdout_nuplan_full_population_sampling"
CHUNK_BYTES = 1024 * 1024
DEFAULT_PLAN_SEED = 3407
DEFAULT_RARE_STRATUM_MAX_UNIQUE_ANCHORS = 512
CITY_PARTITION_QUOTAS = {
    ("boston", "train_iid"): 25_000,
    ("pittsburgh", "train_iid"): 25_000,
    ("boston", "val_iid"): 2_500,
    ("pittsburgh", "val_iid"): 2_500,
    ("singapore", "test_ood"): 5_000,
}
LEARNING_CURVE_SIZES = (2_000, 5_000, 10_000, 20_000, 50_000)
B8_CANDIDATE_SHAPE = (8, 80, 4)
GROUP_REPORT_FIELDS = (
    "population_id",
    "log_token",
    "corridor_id",
    "geometry_clone_group_sha256",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(value))
    temporary.replace(path)


def _marker_offset(path: Path, marker: bytes) -> int:
    overlap = b""
    position = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            combined = overlap + chunk
            index = combined.find(marker)
            if index >= 0:
                return position - len(overlap) + index + len(marker)
            position += len(chunk)
            overlap = combined[-max(len(marker) - 1, 0) :]
    raise ValueError(f"input manifest is missing {marker!r}")


def _decode_value_from_offset(path: Path, offset: int) -> Any:
    decoder = json.JSONDecoder()
    with path.open("rb") as raw:
        raw.seek(offset)
        stream = io.TextIOWrapper(raw, encoding="utf-8")
        buffer = ""
        while True:
            try:
                return decoder.raw_decode(buffer.lstrip())[0]
            except json.JSONDecodeError:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    raise ValueError("input manifest ended while decoding a top-level value")
                buffer += chunk


def _top_level_value(path: Path, key: str) -> Any:
    return _decode_value_from_offset(path, _marker_offset(path, f'"{key}":'.encode("ascii")))


def _iter_top_level_array(path: Path, key: str) -> Iterable[Any]:
    """Yield one canonical top-level array without materializing it in memory."""

    offset = _marker_offset(path, f'"{key}":['.encode("ascii"))
    decoder = json.JSONDecoder()
    with path.open("rb") as raw:
        raw.seek(offset)
        stream = io.TextIOWrapper(raw, encoding="utf-8")
        buffer = ""
        eof = False
        while True:
            while not buffer and not eof:
                chunk = stream.read(CHUNK_BYTES)
                eof = not chunk
                buffer += chunk
            buffer = buffer.lstrip()
            if not buffer:
                raise ValueError(f"input manifest ended in {key} array")
            if buffer[0] == "]":
                return
            while True:
                try:
                    value, end = decoder.raw_decode(buffer)
                    break
                except json.JSONDecodeError:
                    chunk = stream.read(CHUNK_BYTES)
                    if not chunk:
                        raise ValueError(f"input manifest ended inside {key} value")
                    buffer += chunk
            yield value
            buffer = buffer[end:].lstrip()
            while not buffer:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    raise ValueError(f"input manifest ended after {key} value")
                buffer += chunk
                buffer = buffer.lstrip()
            if buffer[0] == ",":
                buffer = buffer[1:]
                continue
            if buffer[0] == "]":
                return
            raise ValueError(f"invalid delimiter in {key} array")


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"manifest record is missing nonempty {key}")
    return result


def _required_int(value: Mapping[str, Any], key: str) -> int:
    result = value.get(key)
    if not isinstance(result, int) or isinstance(result, bool) or result < 0:
        raise ValueError(f"manifest record has invalid {key}")
    return result


def _rank(seed: int, anchor_id: str) -> tuple[int, str]:
    digest = hashlib.sha256(f"{seed}\0{anchor_id}".encode("utf-8")).hexdigest()
    return int(digest, 16), digest


def _is_event_stratum(value: str) -> bool:
    return value.startswith(("scenario_tag:", "signal:", "kinematic:"))


def _quota_key(city: str, partition: str) -> tuple[str, str]:
    return (city, partition)


def _target_quotas(args: argparse.Namespace) -> dict[tuple[str, str], int]:
    return {
        ("boston", "train_iid"): int(args.train_per_city),
        ("pittsburgh", "train_iid"): int(args.train_per_city),
        ("boston", "val_iid"): int(args.validation_per_city),
        ("pittsburgh", "val_iid"): int(args.validation_per_city),
        ("singapore", "test_ood"): int(args.ood_test_count),
    }


def _quota_nested(quotas: Mapping[tuple[str, str], int]) -> dict[str, dict[str, int]]:
    return {
        "train_iid": {
            "boston": quotas[("boston", "train_iid")],
            "pittsburgh": quotas[("pittsburgh", "train_iid")],
        },
        "val_iid": {
            "boston": quotas[("boston", "val_iid")],
            "pittsburgh": quotas[("pittsburgh", "val_iid")],
        },
        "test_ood": {"singapore": quotas[("singapore", "test_ood")]},
    }


def _load_groups(path: Path) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    required = (
        "population_id",
        "city",
        "log_token",
        "scenario_scene_token",
        "mission_route_roadblock_chain_sha256",
        "corridor_id",
        "geometry_clone_group_sha256",
        "source_db_sha256",
        "map_sha256",
        "raw_db_relative_path",
    )
    for item in _iter_top_level_array(path, "population_groups"):
        if not isinstance(item, Mapping):
            raise ValueError("population_groups contains a non-mapping")
        group = {key: _required_string(item, key) for key in required}
        population_id = group["population_id"]
        if population_id in groups:
            raise ValueError("population_groups contains duplicate population_id")
        groups[population_id] = group
    if not groups:
        raise ValueError("population_groups is empty")
    return groups


def _load_strata(path: Path) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for item in _iter_top_level_array(path, "city_partition_tag_phase"):
        if not isinstance(item, Mapping):
            raise ValueError("city_partition_tag_phase contains a non-mapping")
        row = {
            "city": _required_string(item, "city"),
            "partition": _required_string(item, "partition"),
            "tag": _required_string(item, "tag"),
            "phase": _required_string(item, "phase"),
            "population_count": _required_int(item, "population_count"),
        }
        key = (row["city"], row["partition"], row["tag"], row["phase"])
        if key in seen:
            raise ValueError("city_partition_tag_phase contains duplicate identity")
        seen.add(key)
        result.append(row)
    if not result:
        raise ValueError("city_partition_tag_phase is empty")
    return result


def _anchor_record(
    item: Any,
    *,
    groups: Mapping[str, Mapping[str, str]],
    quotas: Mapping[tuple[str, str], int],
    seed: int,
) -> tuple[tuple[str, str], dict[str, Any]] | None:
    if not isinstance(item, Mapping):
        raise ValueError("selected_anchors contains a non-mapping")
    population_id = _required_string(item, "population_id")
    group = groups.get(population_id)
    if group is None:
        raise ValueError("selected anchor is missing its frozen population group")
    city = group["city"]
    partition = _required_string(item, "partition")
    quota_key = _quota_key(city, partition)
    if quota_key not in quotas:
        return None
    anchor_id = _required_string(item, "anchor_id")
    state_token = _required_string(item, "state_token")
    timestamp = _required_int(item, "timestamp")
    memberships = item.get("event_memberships")
    if not isinstance(memberships, list):
        raise ValueError("selected anchor event_memberships is invalid")
    membership_rows = []
    for membership in memberships:
        if not isinstance(membership, Mapping):
            raise ValueError("selected anchor membership is invalid")
        membership_rows.append(
            {
                "stratum": _required_string(membership, "stratum"),
                "phase": _required_string(membership, "phase"),
            }
        )
    if not membership_rows:
        raise ValueError("selected anchor lacks source-side membership")
    rank_value, rank_sha = _rank(seed, anchor_id)
    return quota_key, {
        "anchor_id": anchor_id,
        "population_id": population_id,
        "state_token": state_token,
        "timestamp": timestamp,
        "city": city,
        "partition": partition,
        "event_memberships": sorted(membership_rows, key=lambda row: (row["stratum"], row["phase"])),
        "allocation_rank_sha256": rank_sha,
        "_rank_value": rank_value,
        "group": dict(group),
    }


def _selected_anchor_pass(
    path: Path,
    *,
    groups: Mapping[str, Mapping[str, str]],
    quotas: Mapping[tuple[str, str], int],
    seed: int,
    rare_keys: set[tuple[str, str, str, str]],
    coverage_keys: set[tuple[str, str, str, str]],
    enforce_quota: bool = True,
) -> tuple[
    dict[tuple[str, str], dict[str, dict[str, Any]]],
    dict[tuple[tuple[str, str], str], set[str]],
    dict[tuple[str, str, str, str], dict[str, Any]],
]:
    retained = {key: {} for key in quotas}
    reasons: dict[tuple[tuple[str, str], str], set[str]] = defaultdict(set)
    coverage_best: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in _iter_top_level_array(path, "selected_anchors"):
        parsed = _anchor_record(item, groups=groups, quotas=quotas, seed=seed)
        if parsed is None:
            continue
        quota_key, anchor = parsed
        anchor_id = anchor["anchor_id"]
        for membership in anchor["event_memberships"]:
            stratum_key = (
                quota_key[0],
                quota_key[1],
                membership["stratum"],
                membership["phase"],
            )
            if stratum_key in rare_keys:
                retained[quota_key][anchor_id] = anchor
                reasons[(quota_key, anchor_id)].add(
                    f"retain_rare_source_event:{membership['stratum']}:{membership['phase']}"
                )
            if stratum_key in coverage_keys:
                current = coverage_best.get(stratum_key)
                if current is None or (
                    anchor["_rank_value"], anchor_id
                ) < (current["_rank_value"], current["anchor_id"]):
                    coverage_best[stratum_key] = anchor
    for key, anchor in coverage_best.items():
        quota_key = (key[0], key[1])
        anchor_id = anchor["anchor_id"]
        retained[quota_key][anchor_id] = anchor
        reasons[(quota_key, anchor_id)].add(
            f"retain_stratum_phase_coverage:{key[2]}:{key[3]}"
        )
    if enforce_quota:
        for quota_key, anchors in retained.items():
            if len(anchors) > quotas[quota_key]:
                raise ValueError(
                    "predeclared rare-event and coverage retention exceeds the city quota: "
                    f"{quota_key} retained={len(anchors)} quota={quotas[quota_key]}"
                )
    return retained, reasons, coverage_best


def _resolve_effective_quotas(
    path: Path,
    *,
    groups: Mapping[str, Mapping[str, str]],
    target_quotas: Mapping[tuple[str, str], int],
    seed: int,
    rare_keys: set[tuple[str, str, str, str]],
    coverage_keys: set[tuple[str, str, str, str]],
) -> tuple[
    dict[tuple[str, str], int],
    dict[tuple[str, str], int],
    dict[tuple[str, str], dict[str, dict[str, Any]]],
    dict[tuple[tuple[str, str], str], set[str]],
]:
    """Project mandatory identity-only anchors before resolving any quota."""

    projection_quotas = {key: sys.maxsize for key in target_quotas}
    retained, reasons, _coverage_best = _selected_anchor_pass(
        path,
        groups=groups,
        quotas=projection_quotas,
        seed=seed,
        rare_keys=rare_keys,
        coverage_keys=coverage_keys,
        enforce_quota=False,
    )
    lower_bounds = {key: len(retained[key]) for key in target_quotas}
    effective_quotas = {
        key: max(target_quotas[key], lower_bounds[key]) for key in target_quotas
    }
    return lower_bounds, effective_quotas, retained, reasons


def _fill_quotas(
    path: Path,
    *,
    groups: Mapping[str, Mapping[str, str]],
    quotas: Mapping[tuple[str, str], int],
    seed: int,
    retained: Mapping[tuple[str, str], Mapping[str, Mapping[str, Any]]],
    reasons: dict[tuple[tuple[str, str], str], set[str]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    heaps: dict[tuple[str, str], list[tuple[int, str, dict[str, Any]]]] = {
        key: [] for key in quotas
    }
    available = {key: 0 for key in quotas}
    for item in _iter_top_level_array(path, "selected_anchors"):
        parsed = _anchor_record(item, groups=groups, quotas=quotas, seed=seed)
        if parsed is None:
            continue
        quota_key, anchor = parsed
        available[quota_key] += 1
        if anchor["anchor_id"] in retained[quota_key]:
            continue
        needed = quotas[quota_key] - len(retained[quota_key])
        if needed <= 0:
            continue
        entry = (-anchor["_rank_value"], anchor["anchor_id"], anchor)
        heap = heaps[quota_key]
        if len(heap) < needed:
            heapq.heappush(heap, entry)
        elif entry[0] > heap[0][0]:
            heapq.heapreplace(heap, entry)
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for quota_key, quota in quotas.items():
        if available[quota_key] < quota:
            raise ValueError(
                f"city quota exceeds available unique anchors: {quota_key} "
                f"available={available[quota_key]} quota={quota}"
            )
        selected = list(retained[quota_key].values()) + [item[2] for item in heaps[quota_key]]
        if len(selected) != quota:
            raise ValueError(f"city quota did not close exactly for {quota_key}")
        for anchor in selected:
            reasons[(quota_key, anchor["anchor_id"])].add("deterministic_identity_rank_fill")
        result[quota_key] = selected
    return result


def _output_anchor(
    anchor: Mapping[str, Any], reasons: Sequence[str], city_rank: int | None
) -> dict[str, Any]:
    group = anchor["group"]
    result = {
        "anchor_id": anchor["anchor_id"],
        "population_id": anchor["population_id"],
        "state_token": anchor["state_token"],
        "timestamp": anchor["timestamp"],
        "city": anchor["city"],
        "partition": anchor["partition"],
        "log_token": group["log_token"],
        "scenario_scene_token": group["scenario_scene_token"],
        "mission_route_roadblock_chain_sha256": group[
            "mission_route_roadblock_chain_sha256"
        ],
        "corridor_id": group["corridor_id"],
        "geometry_clone_group_sha256": group["geometry_clone_group_sha256"],
        "source_db_sha256": group["source_db_sha256"],
        "map_sha256": group["map_sha256"],
        "raw_db_relative_path": group["raw_db_relative_path"],
        "event_memberships": list(anchor["event_memberships"]),
        "allocation_rank_sha256": anchor["allocation_rank_sha256"],
        "selection_reasons": list(sorted(reasons)),
    }
    if city_rank is not None:
        result["within_city_training_rank"] = city_rank
    return result


def _group_summary(anchors: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "unique_anchor_count": len({str(anchor["anchor_id"]) for anchor in anchors}),
        "population_group_count": len({str(anchor["population_id"]) for anchor in anchors}),
        "log_cluster_count": len({str(anchor["group"]["log_token"]) for anchor in anchors}),
        "corridor_cluster_count": len({str(anchor["group"]["corridor_id"]) for anchor in anchors}),
        "geometry_clone_group_count": len(
            {str(anchor["group"]["geometry_clone_group_sha256"]) for anchor in anchors}
        ),
    }


def _coverage_rows(
    strata: Sequence[Mapping[str, Any]], anchors: Sequence[Mapping[str, Any]], quotas: Mapping[tuple[str, str], int]
) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for anchor in anchors:
        for membership in anchor["event_memberships"]:
            selected[(
                str(anchor["city"]),
                str(anchor["partition"]),
                str(membership["stratum"]),
                str(membership["phase"]),
            )].add(str(anchor["anchor_id"]))
    result = []
    for source in sorted(
        (row for row in strata if (row["city"], row["partition"]) in quotas),
        key=lambda row: (row["city"], row["partition"], row["tag"], row["phase"]),
    ):
        key = (source["city"], source["partition"], source["tag"], source["phase"])
        selected_count = len(selected[key])
        if source["population_count"] and selected_count == 0:
            raise ValueError(f"predeclared source stratum lost coverage: {key}")
        result.append(
            {
                "city": source["city"],
                "partition": source["partition"],
                "tag": source["tag"],
                "phase": source["phase"],
                "population_unique_anchor_count": source["population_count"],
                "selected_unique_anchor_count": selected_count,
                "sampling_probability": selected_count / source["population_count"],
            }
        )
    return result


def _learning_curve(selected: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    per_city: dict[str, list[Mapping[str, Any]]] = {}
    for city in ("boston", "pittsburgh"):
        anchors = list(selected[(city, "train_iid")])
        anchors.sort(
            key=lambda anchor: (
                0 if any(reason.startswith("retain_") for reason in anchor["_reasons"]) else 1,
                anchor["_rank_value"],
                anchor["anchor_id"],
            )
        )
        per_city[city] = anchors
    rows = []
    available_total = 2 * min(len(values) for values in per_city.values())
    for total in (size for size in LEARNING_CURVE_SIZES if size <= available_total):
        per_city_quota = total // 2
        if total % 2 or any(len(per_city[city]) < per_city_quota for city in per_city):
            raise ValueError("learning-curve city quota is invalid")
        ids = {
            city: [str(anchor["anchor_id"]) for anchor in per_city[city][:per_city_quota]]
            for city in sorted(per_city)
        }
        rows.append(
            {
                "train_unique_anchor_count": total,
                "per_city_quota": per_city_quota,
                "nested_with_next": total != LEARNING_CURVE_SIZES[-1],
                "city_anchor_id_sha256": {
                    city: canonical_json_sha256(values) for city, values in ids.items()
                },
            }
        )
    return rows


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.sampling_manifest.resolve(strict=True)
    if int(args.plan_seed) != args.plan_seed:
        raise ValueError("plan seed must be an integer")
    target_quotas = _target_quotas(args)
    if any(value <= 0 for value in target_quotas.values()):
        raise ValueError("all predeclared city quotas must be positive")
    if args.rare_stratum_max_unique_anchors <= 0:
        raise ValueError("rare stratum threshold must be positive")

    if _top_level_value(manifest_path, "schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError("sampling manifest schema drifted")
    if _top_level_value(manifest_path, "evidence_role") != INPUT_EVIDENCE_ROLE:
        raise ValueError("sampling manifest evidence role drifted")
    if _top_level_value(manifest_path, "outcome_fields_consumed") != []:
        raise ValueError("sampling manifest is not outcome blind")
    sampling_contract = _top_level_value(manifest_path, "sampling_contract")
    fixed_dp = _top_level_value(manifest_path, "fixed_dp")
    if (
        not isinstance(sampling_contract, Mapping)
        or sampling_contract.get("status") != "identity_only_pre_pool_not_arbitrary_cap"
        or not isinstance(fixed_dp, Mapping)
        or fixed_dp.get("head") != FIXED_DP_HEAD
    ):
        raise ValueError("sampling manifest scientific contract drifted")

    groups = _load_groups(manifest_path)
    strata = _load_strata(manifest_path)
    coverage_keys = {
        (row["city"], row["partition"], row["tag"], row["phase"])
        for row in strata
        if (row["city"], row["partition"]) in target_quotas
        and row["population_count"] > 0
    }
    rare_keys = {
        (row["city"], row["partition"], row["tag"], row["phase"])
        for row in strata
        if (row["city"], row["partition"]) in target_quotas
        and _is_event_stratum(row["tag"])
        and 0 < row["population_count"] <= args.rare_stratum_max_unique_anchors
    }
    mandatory_lower_bounds, quotas, retained, reasons = _resolve_effective_quotas(
        manifest_path,
        groups=groups,
        target_quotas=target_quotas,
        seed=args.plan_seed,
        rare_keys=rare_keys,
        coverage_keys=coverage_keys,
    )
    selected = _fill_quotas(
        manifest_path,
        groups=groups,
        quotas=quotas,
        seed=args.plan_seed,
        retained=retained,
        reasons=reasons,
    )
    for quota_key, anchors in selected.items():
        for anchor in anchors:
            anchor["_reasons"] = reasons[(quota_key, anchor["anchor_id"])]

    all_anchors = [anchor for anchors in selected.values() for anchor in anchors]
    if len({str(anchor["anchor_id"]) for anchor in all_anchors}) != len(all_anchors):
        raise ValueError("frozen corpus selected an anchor more than once")
    coverage = _coverage_rows(strata, all_anchors, quotas)
    city_partition = []
    for key in sorted(quotas):
        anchors = selected[key]
        city_partition.append(
            {
                "city": key[0],
                "partition": key[1],
                "predeclared_target_quota": target_quotas[key],
                "mandatory_coverage_lower_bound": mandatory_lower_bounds[key],
                "quota": quotas[key],
                "quota_expanded_for_mandatory_coverage": quotas[key]
                > target_quotas[key],
                **_group_summary(anchors),
            }
        )

    city_training_order: dict[str, dict[str, int]] = {}
    for city in ("boston", "pittsburgh"):
        ordered = sorted(
            selected[(city, "train_iid")],
            key=lambda anchor: (
                0 if any(reason.startswith("retain_") for reason in anchor["_reasons"]) else 1,
                anchor["_rank_value"],
                anchor["anchor_id"],
            ),
        )
        city_training_order[city] = {
            str(anchor["anchor_id"]): index + 1 for index, anchor in enumerate(ordered)
        }
    output_anchors = []
    for quota_key, anchors in selected.items():
        for anchor in anchors:
            output_anchors.append(
                _output_anchor(
                    anchor,
                    anchor["_reasons"],
                    city_training_order.get(quota_key[0], {}).get(str(anchor["anchor_id"])),
                )
            )
    output_anchors.sort(key=lambda anchor: (anchor["city"], anchor["partition"], anchor["anchor_id"]))
    candidate_bytes = len(output_anchors) * B8_CANDIDATE_SHAPE[0] * B8_CANDIDATE_SHAPE[1] * B8_CANDIDATE_SHAPE[2] * 4
    plan = {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "outcome_fields_consumed": [],
        "payload_read": False,
        "input_sampling_manifest": {
            "path": str(manifest_path),
            "file_sha256": _sha256_file(manifest_path),
            "declared_sampling_manifest_sha256": _top_level_value(
                manifest_path, "sampling_manifest_sha256"
            ),
            "fixed_dp": fixed_dp,
            "sampling_contract_status": sampling_contract["status"],
        },
        "same_pool_contract": {
            "fixed_dp": True,
            "candidate_pool_shape": list(B8_CANDIDATE_SHAPE),
            "one_primary_forward_per_anchor": True,
            "candidate0_row": 0,
            "arms": ["candidate0", "Static14D", "Scene14D"],
            "selector_consumes_same_pool_only": True,
            "post_pool_model_dp_latent_generation_calls": 0,
        },
        "selection_contract": {
            "plan_seed": args.plan_seed,
            "unique_anchor_key": "anchor_id",
            "higher_level_group_keys": list(GROUP_REPORT_FIELDS),
            "forbidden_denominators": ["membership_requests", "candidate_rows", "ticks", "arms"],
            "rare_event_policy": {
                "eligible_strata": ["scenario_tag:*", "signal:*", "kinematic:*"],
                "max_unique_anchors_per_city_partition_stratum_phase": args.rare_stratum_max_unique_anchors,
                "rule": "retain every unique anchor carrying a rare source-event stratum/phase before deterministic common-anchor filling",
            },
            "coverage_policy": "retain one deterministic identity-only anchor for every observed city/partition/tag/phase before common-anchor filling",
            "common_event_policy": "deterministic SHA256 identity rank after rare-event and coverage retention; no outcome, endpoint, candidate, trajectory, label, SafetyCost, or selector input",
        },
        "quota_resolution": {
            "projected_before_effective_quota_resolution": True,
            "rule": "effective_quota=max(predeclared_target_quota, mandatory_identity_only_coverage_lower_bound)",
            "mandatory_set": "rare source-event anchors plus one deterministic anchor for every observed city/partition/tag/phase",
            "partitions": [
                {
                    "city": key[0],
                    "partition": key[1],
                    "predeclared_target_quota": target_quotas[key],
                    "mandatory_coverage_lower_bound": mandatory_lower_bounds[key],
                    "effective_quota": quotas[key],
                    "quota_expanded_for_mandatory_coverage": quotas[key]
                    > target_quotas[key],
                }
                for key in sorted(quotas)
            ],
        },
        "quotas": _quota_nested(quotas),
        "analysis_freeze": {
            "validation_values_read": False,
            "singapore_ood_status": "identity_frozen_city_held_out_not_evaluated",
            "aggregate_weights": {
                "iid_city_macro": {"boston": 0.5, "pittsburgh": 0.5},
                "per_anchor_weight_rule": "within each reporting partition, city_macro_weight / that_city_unique_anchor_count",
                "forbid_raw_anchor_count_weighted_iid_pool": True,
            },
            "cluster_aware_ci": {
                "method": "stratified_log_cluster_bootstrap_percentile_v1",
                "replicates": 2000,
                "confidence_level": 0.95,
                "seed": 93407,
                "per_city": "resample log_token clusters with every selected anchor in each sampled log retained",
                "pooled_iid": "resample log_token clusters separately within Boston and Pittsburgh, then compute an equal-city macro aggregate",
                "independent_n_reporting": "report log and corridor cluster counts; unique anchors are observations, not independent n",
            },
            "primary_metrics_and_statistics": {
                "prediction": ["ADE_m", "FDE_m", "trajectory_feasibility_rate"],
                "industrial_vector": ["safety", "operation_progress", "filtered_body_frame_smoothness", "realtime"],
                "missing_endpoint_policy": "typed_missing_or_inapplicable, never scene exclusion or imputation",
                "legacy_only": ["SafetyCost", "raw_jerk"],
                "comparison": "within-anchor same-pool selector contrast versus candidate0; no weighted composite score",
                "significance": {
                    "primary_contrasts": [
                        "Static14D_minus_candidate0",
                        "Scene14D_minus_candidate0",
                    ],
                    "two_sided_alpha": 0.05,
                    "multiplicity": "Holm across the predeclared ADE/FDE/trajectory-feasibility primary contrast family within each reporting population",
                    "decision_rule": "label a primary contrast statistically distinguishable only when its multiplicity-adjusted two-sided interval excludes zero; always report estimate and interval",
                    "industrial_vector": "city-specific and pooled descriptive cluster-aware intervals without a weighted composite or post-result threshold",
                },
            },
        },
        "learning_curve": _learning_curve(selected),
        "city_partition_denominator": city_partition,
        "city_partition_tag_phase_coverage": coverage,
        "capacity_estimate": {
            "planned_unique_pool_count": len(output_anchors),
            "same_ego_b8_candidate_rows": len(output_anchors) * B8_CANDIDATE_SHAPE[0],
            "candidate_tensor_bytes_lower_bound": candidate_bytes,
            "full_population_pool_materialization": "not_started",
        },
        "planned_anchors": output_anchors,
    }
    plan["plan_sha256"] = canonical_json_sha256(plan)
    return plan


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-seed", type=int, default=DEFAULT_PLAN_SEED)
    parser.add_argument("--train-per-city", type=int, default=25_000)
    parser.add_argument("--validation-per-city", type=int, default=2_500)
    parser.add_argument("--ood-test-count", type=int, default=5_000)
    parser.add_argument(
        "--rare-stratum-max-unique-anchors",
        type=int,
        default=DEFAULT_RARE_STRATUM_MAX_UNIQUE_ANCHORS,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)
    _write_json_atomic(args.output, plan)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "plan_sha256": plan["plan_sha256"],
                "planned_unique_pool_count": plan["capacity_estimate"]["planned_unique_pool_count"],
                "validation_values_read": plan["analysis_freeze"]["validation_values_read"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
