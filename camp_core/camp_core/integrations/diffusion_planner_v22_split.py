from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from copy import deepcopy
from itertools import combinations, product
from typing import Any, Iterable, Mapping

import numpy as np


SPLITS = ("train", "calibration", "holdout")
FORMAL_SEEDS = frozenset({11, 12, 13})
FORBIDDEN_FEATURE_FIELDS = frozenset(
    {
        "map_id",
        "logical_map_id",
        "logical_map_sha256",
        "route_id",
        "route_identity_sha256",
        "route_family",
        "route_family_group_sha256",
        "group_sha256",
        "split",
        "split_id",
        "split_identity",
    }
)
_SOURCE_STRATA = (
    "traffic_light",
    "branch_intersection",
    "tight_corridor",
    "short_progress_opportunity",
)
_OUTCOME_FIELDS = frozenset(
    {
        "safety_cost",
        "collision",
        "near_miss",
        "completion",
        "selected_index",
        "candidate_score",
        "failure_reason",
    }
)


def canonical_json_bytes(value: Any) -> bytes:
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


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def build_leakage_groups(
    routes: Iterable[Mapping[str, Any]],
    *,
    overlap_distance_m: float = 3.0,
    min_overlap_samples: int = 20,
    max_heading_delta_deg: float = 15.0,
) -> dict[str, Any]:
    if (
        not math.isfinite(overlap_distance_m)
        or overlap_distance_m <= 0.0
        or isinstance(min_overlap_samples, bool)
        or min_overlap_samples < 2
        or not math.isfinite(max_heading_delta_deg)
        or not 0.0 < max_heading_delta_deg <= 90.0
    ):
        raise ValueError("invalid frozen corridor-overlap thresholds")
    records = [_normalize_route(route) for route in routes]
    if not records:
        raise ValueError("route census is empty")
    records.sort(key=lambda route: route["record_key"])
    keys = [route["record_key"] for route in records]
    if len(keys) != len(set(keys)):
        raise ValueError("route record_key values must be unique")

    reasons: dict[tuple[int, int], set[str]] = defaultdict(set)

    def index_equal(field: str, reason: str, *, map_local: bool = False) -> None:
        index: dict[Any, list[int]] = defaultdict(list)
        for route_index, route in enumerate(records):
            raw_values = route[field]
            values = raw_values if isinstance(raw_values, list) else [raw_values]
            for value in set(values):
                if value is None:
                    continue
                key = (
                    (route["logical_map_sha256"], value)
                    if map_local
                    else value
                )
                index[key].append(route_index)
        for members in index.values():
            for left, right in combinations(sorted(set(members)), 2):
                reasons[(left, right)].add(reason)

    index_equal("identity_sha256", "equal_route_identity")
    index_equal("lanelet_ids", "shared_lanelet", map_local=True)
    index_equal("boundary_ids", "shared_boundary", map_local=True)

    topology: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for route_index, route in enumerate(records):
        if route["topology_complex"] is None:
            continue
        key = (
            route["logical_map_sha256"],
            route["topology_complex"],
            route["entry_arm"],
            route["exit_arm"],
        )
        topology[key].append(route_index)
    for members in topology.values():
        for left, right in combinations(sorted(members), 2):
            reasons[(left, right)].add("same_topology_family")

    cells: dict[tuple[str, int, int], set[int]] = defaultdict(set)
    route_cells: list[set[tuple[str, int, int]]] = []
    cell_width = float(overlap_distance_m)
    for route_index, route in enumerate(records):
        occupied = {
            (
                route["logical_map_sha256"],
                math.floor(point[0] / cell_width),
                math.floor(point[1] / cell_width),
            )
            for point in route["centerline_samples_m"]
        }
        route_cells.append(occupied)
        for cell in occupied:
            cells[cell].add(route_index)
    geometry_pairs: set[tuple[int, int]] = set()
    for route_index, occupied in enumerate(route_cells):
        for map_sha, x_cell, y_cell in occupied:
            for x_offset in (-1, 0, 1):
                for y_offset in (-1, 0, 1):
                    for other in cells.get(
                        (map_sha, x_cell + x_offset, y_cell + y_offset), ()
                    ):
                        if other != route_index:
                            geometry_pairs.add(tuple(sorted((route_index, other))))
    max_heading_delta = math.radians(max_heading_delta_deg)
    for left, right in sorted(geometry_pairs):
        if reasons.get((left, right)):
            continue
        if _corridors_overlap(
            records[left],
            records[right],
            distance_m=overlap_distance_m,
            min_samples=min_overlap_samples,
            max_heading_delta=max_heading_delta,
        ):
            reasons[(left, right)].add("overlapping_corridor")

    union_find = _UnionFind(len(records))
    for left, right in reasons:
        union_find.union(left, right)
    components: dict[int, list[int]] = defaultdict(list)
    for route_index in range(len(records)):
        components[union_find.find(route_index)].append(route_index)

    groups = []
    for members in components.values():
        ordered = sorted(members, key=lambda index: records[index]["record_key"])
        identities = sorted(records[index]["identity_sha256"] for index in ordered)
        group_sha = hashlib.sha256("".join(identities).encode("ascii")).hexdigest()
        stratum_counts = {
            name: sum(bool(records[index]["source_stratum"][name]) for index in ordered)
            for name in _SOURCE_STRATA
        }
        groups.append(
            {
                "group_sha256": group_sha,
                "route_record_keys": [records[index]["record_key"] for index in ordered],
                "route_identity_sha256": identities,
                "route_record_count": len(ordered),
                "unique_route_count": len(set(identities)),
                "logical_map_sha256": sorted(
                    {records[index]["logical_map_sha256"] for index in ordered}
                ),
                "source_stratum_counts": stratum_counts,
                "holdout_forbidden": any(
                    records[index]["holdout_forbidden"] for index in ordered
                ),
            }
        )
    groups.sort(key=lambda group: group["group_sha256"])
    edges = [
        {
            "route_a": records[left]["record_key"],
            "route_b": records[right]["record_key"],
            "reasons": sorted(edge_reasons),
        }
        for (left, right), edge_reasons in sorted(
            reasons.items(),
            key=lambda item: (
                records[item[0][0]]["record_key"],
                records[item[0][1]]["record_key"],
            ),
        )
    ]
    return {
        "schema_version": "v22_route_leakage_groups_v1",
        "source_only": True,
        "outcome_fields_consumed": [],
        "thresholds": {
            "sample_spacing_m": 1.0,
            "overlap_distance_m": float(overlap_distance_m),
            "min_overlap_samples": int(min_overlap_samples),
            "max_heading_delta_deg": float(max_heading_delta_deg),
        },
        "route_records": records,
        "edges": edges,
        "groups": groups,
    }


def freeze_split_manifest(
    grouping: Mapping[str, Any],
    *,
    seed_namespaces: Mapping[str, Iterable[int]],
    targets: Mapping[str, int],
) -> dict[str, Any]:
    if grouping.get("schema_version") != "v22_route_leakage_groups_v1":
        raise ValueError("leakage grouping schema mismatch")
    if set(seed_namespaces) != set(SPLITS) or set(targets) != set(SPLITS):
        raise ValueError("split targets and seed namespaces must be exact")
    frozen_seeds = _validate_seed_namespaces(seed_namespaces)
    frozen_targets = {}
    for split in SPLITS:
        value = targets[split]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("split targets must be positive route counts")
        frozen_targets[split] = value

    records = {
        route["record_key"]: deepcopy(route)
        for route in grouping.get("route_records", [])
    }
    groups = [deepcopy(group) for group in grouping.get("groups", [])]
    if not records or not groups:
        raise ValueError("leakage grouping has no records or groups")
    split_payload = {
        split: {
            "target_route_count": frozen_targets[split],
            "achieved_route_count": 0,
            "group_sha256": [],
            "routes": [],
            "seed_namespace": frozen_seeds[split],
        }
        for split in SPLITS
    }
    assigned_groups: dict[str, str] = {}
    excluded = []
    selected_identities: set[str] = set()
    ordered_groups = sorted(groups, key=lambda item: item["group_sha256"])
    allocation = _assign_group_splits(ordered_groups, frozen_targets)

    for group in ordered_groups:
        split = allocation[group["group_sha256"]]
        if split is None:
            for record_key in group["route_record_keys"]:
                route = records[record_key]
                excluded.append(
                    _excluded_route(
                        route,
                        group["group_sha256"],
                        "frozen_capacity_above_target_or_holdout_forbidden",
                    )
                )
            continue
        assigned_groups[group["group_sha256"]] = split
        split_payload[split]["group_sha256"].append(group["group_sha256"])
        remaining = frozen_targets[split] - split_payload[split]["achieved_route_count"]
        ordered_records = sorted(
            (records[key] for key in group["route_record_keys"]),
            key=lambda route: (route["identity_sha256"], route["record_key"]),
        )
        selected_here = 0
        for route in ordered_records:
            identity = route["identity_sha256"]
            if identity in selected_identities:
                excluded.append(
                    _excluded_route(route, group["group_sha256"], "duplicate_route_identity")
                )
                continue
            if selected_here >= remaining:
                excluded.append(
                    _excluded_route(
                        route, group["group_sha256"], "frozen_capacity_above_target"
                    )
                )
                continue
            selected_identities.add(identity)
            selected_here += 1
            split_payload[split]["routes"].append(
                {
                    "record_key": route["record_key"],
                    "identity_sha256": identity,
                    "logical_map_sha256": route["logical_map_sha256"],
                    "group_sha256": group["group_sha256"],
                    "source_stratum": deepcopy(route["source_stratum"]),
                    "route_spec": deepcopy(route.get("route_spec")),
                }
            )
        split_payload[split]["achieved_route_count"] += selected_here

    expected_pairs = []
    for split in SPLITS:
        payload = split_payload[split]
        payload["group_sha256"].sort()
        payload["routes"].sort(key=lambda route: route["identity_sha256"])
        for route in payload["routes"]:
            for seed in payload["seed_namespace"]:
                expected_pairs.append(
                    {
                        "split": split,
                        "route_identity_sha256": route["identity_sha256"],
                        "group_sha256": route["group_sha256"],
                        "seed": seed,
                        "expected_arms": ["dp", "camp"],
                        "receipt_key": (
                            f"{split}/{route['identity_sha256']}/seed_{seed}/pair.json"
                        ),
                    }
                )
    achieved = {
        split: split_payload[split]["achieved_route_count"] for split in SPLITS
    }
    target_reached = {
        split: achieved[split] >= frozen_targets[split] for split in SPLITS
    }
    manifest = {
        "schema_version": "v22_route_family_split_manifest_v1",
        "status": (
            "frozen"
            if target_reached["calibration"] and target_reached["holdout"]
            else "no_go_true_ceiling"
        ),
        "source_only": True,
        "outcome_fields_consumed": [],
        "claim_scope": (
            "unseen route-family/corridor and seed within two fixed logical maps"
        ),
        "unseen_map_generalization_authorized": False,
        "allocation_policy": (
            "source_only_global_eval_target_first_then_training_ceiling_v1"
        ),
        "targets": frozen_targets,
        "achieved_route_counts": achieved,
        "target_reached": target_reached,
        "true_leakage_safe_ceiling": achieved,
        "splits": split_payload,
        "pilot_route_identity_sha256": [
            route["identity_sha256"]
            for route in split_payload["calibration"]["routes"]
        ],
        "main_route_identity_sha256": [
            route["identity_sha256"] for route in split_payload["holdout"]["routes"]
        ],
        "expected_pairs": expected_pairs,
        "excluded_pre_preregistration": sorted(
            excluded, key=lambda route: (route["identity_sha256"], route["record_key"])
        ),
        "route_coverage": {
            "source_route_records": len(records),
            "source_unique_route_identities": len(
                {route["identity_sha256"] for route in records.values()}
            ),
            "preregistered_unique_routes": len(selected_identities),
            "excluded_pre_preregistration_records": len(excluded),
        },
        "leakage_edges": deepcopy(grouping.get("edges", [])),
        "groups": groups,
        "source_routes": [records[key] for key in sorted(records)],
        "assigned_groups": assigned_groups,
        "feature_identity_denylist": sorted(FORBIDDEN_FEATURE_FIELDS),
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "full36_forbidden": True,
    }
    manifest["split_freeze_sha256"] = canonical_json_sha256(manifest)
    validate_split_manifest(manifest)
    return manifest


def _assign_group_splits(
    groups: list[Mapping[str, Any]], targets: Mapping[str, int]
) -> dict[str, str | None]:
    if len(groups) <= 9:
        choices: tuple[str | None, ...] = (*SPLITS, None)
        best_assignment = None
        best_key = None
        for assignment in product(choices, repeat=len(groups)):
            if any(
                split == "holdout" and group.get("holdout_forbidden")
                for group, split in zip(groups, assignment)
            ):
                continue
            capacity = {split: 0 for split in SPLITS}
            for group, split in zip(groups, assignment):
                if split is not None:
                    capacity[split] += int(group["unique_route_count"])
            ratios = {
                split: min(capacity[split], targets[split]) / targets[split]
                for split in SPLITS
            }
            eval_reached = sum(
                ratios[split] >= 1.0 for split in ("calibration", "holdout")
            )
            assigned_capacity = sum(
                int(group["unique_route_count"])
                for group, split in zip(groups, assignment)
                if split is not None
            )
            tie_break = tuple(
                -(choices.index(split)) for split in assignment
            )
            key = (
                eval_reached,
                min(ratios["calibration"], ratios["holdout"]),
                ratios["train"],
                sum(ratios.values()),
                -assigned_capacity,
                tie_break,
            )
            if best_key is None or key > best_key:
                best_key = key
                best_assignment = assignment
        if best_assignment is None:
            raise ValueError("no source-only group allocation exists")
        return {
            group["group_sha256"]: split
            for group, split in zip(groups, best_assignment)
        }

    achieved = {split: 0 for split in SPLITS}
    result: dict[str, str | None] = {}
    for group in groups:
        eligible = [
            split
            for split in ("holdout", "calibration", "train")
            if achieved[split] < targets[split]
            and not (split == "holdout" and group.get("holdout_forbidden"))
        ]
        if not eligible:
            result[group["group_sha256"]] = None
            continue
        split = max(
            eligible,
            key=lambda name: (targets[name] - achieved[name]) / targets[name],
        )
        result[group["group_sha256"]] = split
        achieved[split] += int(group["unique_route_count"])
    return result


def validate_split_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != "v22_route_family_split_manifest_v1":
        raise ValueError("split manifest schema mismatch")
    splits = manifest.get("splits")
    if not isinstance(splits, Mapping) or set(splits) != set(SPLITS):
        raise ValueError("split manifest needs exact train/calibration/holdout")
    identities_seen: set[str] = set()
    groups_seen: set[str] = set()
    seeds_seen: set[int] = set()
    expected_route_seed: set[tuple[str, str, int]] = set()
    for split in SPLITS:
        payload = splits[split]
        groups = list(payload.get("group_sha256", []))
        overlap = groups_seen.intersection(groups)
        if overlap:
            raise ValueError(f"group overlap across splits: {sorted(overlap)}")
        groups_seen.update(groups)
        seeds = list(payload.get("seed_namespace", []))
        seed_overlap = seeds_seen.intersection(seeds)
        if seed_overlap:
            raise ValueError(f"seed overlap across splits: {sorted(seed_overlap)}")
        if set(seeds).intersection(FORMAL_SEEDS):
            raise ValueError("formal seed is forbidden")
        seeds_seen.update(seeds)
        for route in payload.get("routes", []):
            identity = route.get("identity_sha256")
            if identity in identities_seen:
                raise ValueError(f"identity overlap across splits: {identity}")
            identities_seen.add(identity)
            if route.get("group_sha256") not in groups:
                raise ValueError("route references a group outside its split")
            for seed in seeds:
                expected_route_seed.add((split, identity, seed))
    receipts = set()
    actual_route_seed = set()
    for pair in manifest.get("expected_pairs", []):
        if pair.get("expected_arms") != ["dp", "camp"]:
            raise ValueError("every pair must expect DP and CAMP arms")
        key = pair.get("receipt_key")
        if not isinstance(key, str) or not key.endswith("/pair.json") or key in receipts:
            raise ValueError("pair receipt keys must be complete and unique")
        receipts.add(key)
        actual_route_seed.add(
            (pair.get("split"), pair.get("route_identity_sha256"), pair.get("seed"))
        )
    if actual_route_seed != expected_route_seed:
        raise ValueError("pair receipt coverage does not match preregistration")
    calibration = {
        route["identity_sha256"] for route in splits["calibration"]["routes"]
    }
    holdout = {route["identity_sha256"] for route in splits["holdout"]["routes"]}
    if not set(manifest.get("pilot_route_identity_sha256", [])).issubset(calibration):
        raise ValueError("pilot route is outside calibration")
    if not set(manifest.get("main_route_identity_sha256", [])).issubset(holdout):
        raise ValueError("main route is outside holdout")


def validate_feature_fields(fields: Iterable[str]) -> None:
    for field in fields:
        normalized = str(field).strip().lower()
        if normalized in FORBIDDEN_FEATURE_FIELDS:
            raise ValueError(f"forbidden selector feature: {field}")


def _normalize_route(route: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(route))
    outcome_fields = sorted(set(result).intersection(_OUTCOME_FIELDS))
    if outcome_fields:
        raise ValueError(f"source route contains outcome field: {outcome_fields}")
    record_key = result.get("record_key")
    if not isinstance(record_key, str) or not record_key:
        raise ValueError("route record_key must be nonempty")
    for name in ("identity_sha256", "logical_map_sha256"):
        value = result.get(name)
        if not _is_sha256(value):
            raise ValueError(f"route {name} must be lowercase SHA256")
    for name in ("lanelet_ids", "boundary_ids"):
        values = result.get(name)
        if not isinstance(values, list):
            raise ValueError(f"route {name} must be a list")
        result[name] = sorted(set(values)) if name == "boundary_ids" else list(values)
    if not result["lanelet_ids"]:
        raise ValueError("route lanelet_ids must be nonempty")
    samples = np.asarray(result.get("centerline_samples_m"), dtype=np.float64)
    headings = np.asarray(result.get("centerline_headings_rad"), dtype=np.float64)
    if (
        samples.ndim != 2
        or samples.shape[1:] != (2,)
        or samples.shape[0] < 2
        or headings.shape != (samples.shape[0],)
        or not np.isfinite(samples).all()
        or not np.isfinite(headings).all()
    ):
        raise ValueError("route centerline samples/headings are invalid")
    result["centerline_samples_m"] = samples.tolist()
    result["centerline_headings_rad"] = headings.tolist()
    topology = result.get("topology_complex")
    if topology is not None:
        if not all(
            isinstance(result.get(name), str) and result[name]
            for name in ("topology_complex", "entry_arm", "exit_arm")
        ):
            raise ValueError("topology family requires complex and entry/exit arms")
    else:
        result["entry_arm"] = None
        result["exit_arm"] = None
    strata = result.get("source_stratum")
    if not isinstance(strata, Mapping) or set(strata) != set(_SOURCE_STRATA):
        raise ValueError("route source_stratum schema mismatch")
    result["source_stratum"] = {
        name: bool(strata[name]) for name in _SOURCE_STRATA
    }
    result["holdout_forbidden"] = bool(result.get("holdout_forbidden", False))
    return result


def _corridors_overlap(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    distance_m: float,
    min_samples: int,
    max_heading_delta: float,
) -> bool:
    if left["logical_map_sha256"] != right["logical_map_sha256"]:
        return False
    left_xy = np.asarray(left["centerline_samples_m"], dtype=np.float64)
    right_xy = np.asarray(right["centerline_samples_m"], dtype=np.float64)
    distance = np.linalg.norm(left_xy[:, None, :] - right_xy[None, :, :], axis=2)
    left_heading = np.asarray(left["centerline_headings_rad"], dtype=np.float64)
    right_heading = np.asarray(right["centerline_headings_rad"], dtype=np.float64)
    delta = np.abs(
        np.arctan2(
            np.sin(left_heading[:, None] - right_heading[None, :]),
            np.cos(left_heading[:, None] - right_heading[None, :]),
        )
    )
    aligned = np.minimum(delta, np.abs(np.pi - delta)) <= max_heading_delta
    matched = (distance <= distance_m) & aligned
    return bool(
        np.count_nonzero(matched.any(axis=1)) >= min_samples
        and np.count_nonzero(matched.any(axis=0)) >= min_samples
    )


def _validate_seed_namespaces(
    seed_namespaces: Mapping[str, Iterable[int]],
) -> dict[str, list[int]]:
    frozen = {}
    seen = set()
    for split in SPLITS:
        seeds = list(seed_namespaces[split])
        if not seeds:
            raise ValueError("seed namespace must be nonempty")
        if any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seeds
        ):
            raise ValueError("seed namespace must contain nonnegative integers")
        if len(seeds) != len(set(seeds)) or seen.intersection(seeds):
            raise ValueError("seed namespace overlap")
        if set(seeds).intersection(FORMAL_SEEDS):
            raise ValueError("formal seed is forbidden")
        seen.update(seeds)
        frozen[split] = sorted(seeds)
    return frozen


def _excluded_route(
    route: Mapping[str, Any], group_sha256: str, reason: str
) -> dict[str, Any]:
    return {
        "record_key": route["record_key"],
        "identity_sha256": route["identity_sha256"],
        "group_sha256": group_sha256,
        "source_only_reason": reason,
    }


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )
