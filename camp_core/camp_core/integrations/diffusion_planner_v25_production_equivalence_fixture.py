from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_controlled_scenarios import (
    validate_controlled_scenario_case,
)
from .diffusion_planner_v25_fresh_b2 import (
    validate_fresh_b2_manifest_row,
)
from .diffusion_planner_v25_holdout_contract import canonical_sha256
from .diffusion_planner_v25_holdout_plan_dispatch import (
    NONFRESH_CANARY_SPLIT,
    NONFRESH_SCENARIO_CLASSES,
    freeze_nonfresh_production_equivalence_plan,
    validate_nonfresh_production_equivalence_plan,
)
from .diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    validate_mapped_signal_chain,
)
from .diffusion_planner_v25_semantic_authority import (
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    validate_no_signal_chain,
)
from .diffusion_planner_v25_signal_complete_runtime import (
    SCHEMA_VERSION as RUNTIME_SCHEMA_VERSION,
    build_signal_complete_scene_adapter,
)


MAP_SUITE_SCHEMA_VERSION = (
    "camp_dp_v25_nonfresh_production_equivalence_map_suite_v1"
)


def select_nonfresh_actual_native_fixtures(
    *,
    formal_plan: Mapping[str, Any],
    semantic_authority_chains: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Select one deterministic accepted nonFresh case for each real branch."""

    if (
        type(formal_plan) is not dict
        or formal_plan.get("schema_version")
        != "camp_dp_v25_controlled_corpus_final_plan_v1"
        or type(formal_plan.get("train")) is not list
        or formal_plan.get("outcome_fields_consumed") != []
    ):
        raise ValueError("nonFresh formal plan authority drifted")
    chain_payload = semantic_authority_chains
    if (
        type(chain_payload) is not dict
        or chain_payload.get("schema_version")
        != "camp_dp_v25_full_r_semantic_authority_chains_v3"
        or type(chain_payload.get("chains")) is not list
        or chain_payload.get("identity_count")
        != len(chain_payload["chains"])
        or chain_payload.get("chains_root_sha256")
        != canonical_sha256(chain_payload["chains"])
    ):
        raise ValueError("nonFresh semantic-chain authority drifted")
    chains: dict[str, dict[str, Any]] = {}
    for raw in chain_payload["chains"]:
        chain, _scenario_class = _validated_chain(raw)
        scenario_id = chain["scenario_id"]
        if scenario_id in chains:
            raise ValueError("nonFresh semantic-chain scenario repeated")
        chains[scenario_id] = chain

    candidates: dict[str, list[dict[str, Any]]] = {
        name: [] for name in NONFRESH_SCENARIO_CLASSES
    }
    for raw_case in formal_plan["train"]:
        if type(raw_case) is not dict or raw_case.get("runner_eligible") is not True:
            continue
        case = copy.deepcopy(raw_case)
        validate_controlled_scenario_case(case)
        chain = chains.get(case["scenario_id"])
        if chain is None:
            continue
        validated, scenario_class = _validated_chain(chain)
        if (
            validated["route_identity_sha256"]
            != case["route_identity_sha256"]
            or validated["source_map_sha256"]
            != case["source_map_sha256"]
        ):
            raise ValueError("nonFresh case/source-chain binding drifted")
        candidates[scenario_class].append(
            {
                "nonfresh_scenario_class": scenario_class,
                "case": case,
                "source_chain": validated,
            }
        )
    ordered: dict[str, list[dict[str, Any]]] = {}
    for scenario_class in NONFRESH_SCENARIO_CLASSES:
        rows = sorted(
            candidates[scenario_class],
            key=lambda row: row["case"]["scenario_id"],
        )
        if not rows:
            raise ValueError(
                f"nonFresh fixture class is unavailable: {scenario_class}"
            )
        ordered[scenario_class] = rows

    selected = _select_route_distinct_fixtures(
        ordered=ordered,
        scenario_classes=NONFRESH_SCENARIO_CLASSES,
    )
    if selected is None:
        raise ValueError("nonFresh fixture classes lack route-distinct cases")
    return selected


def _select_route_distinct_fixtures(
    *,
    ordered: Mapping[str, Sequence[dict[str, Any]]],
    scenario_classes: Sequence[str],
) -> list[dict[str, Any]] | None:
    """Return the lexicographically first route-distinct branch fixture set."""

    def visit(
        index: int,
        *,
        seen_routes: set[str],
        selected: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        if index == len(scenario_classes):
            return list(selected)
        scenario_class = scenario_classes[index]
        for row in ordered[scenario_class]:
            route_identity = row["case"]["route_identity_sha256"]
            if route_identity in seen_routes:
                continue
            found = visit(
                index + 1,
                seen_routes=seen_routes | {route_identity},
                selected=[*selected, row],
            )
            if found is not None:
                return found
        return None

    return visit(0, seen_routes=set(), selected=[])


def build_nonfresh_production_equivalence_plan(
    *,
    selected_fixtures: Sequence[Mapping[str, Any]],
    source_fixture_root_sha256: str,
) -> dict[str, Any]:
    _sha(source_fixture_root_sha256, "source_fixture_root_sha256")
    if (
        type(selected_fixtures) is not list
        or len(selected_fixtures) != 3
    ):
        raise ValueError("nonFresh selected fixture denominator drifted")
    identities: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(selected_fixtures):
        if type(raw) is not dict or set(raw) != {
            "nonfresh_scenario_class",
            "case",
            "source_chain",
        }:
            raise ValueError("nonFresh selected fixture fields drifted")
        scenario_class = raw["nonfresh_scenario_class"]
        case = copy.deepcopy(raw["case"])
        chain, expected_class = _validated_chain(raw["source_chain"])
        validate_controlled_scenario_case(case)
        if scenario_class != expected_class:
            raise ValueError("nonFresh selected fixture class drifted")
        semantic = chain["semantic_clone_payload"]
        route_length_m = _route_length(semantic["route_polyline_local_m"])
        map_sha = case["source_map_sha256"]
        semantic_block = canonical_sha256(
            {
                "family": case["family"],
                "tier": case["tier"],
                "semantic_variant": case["semantic_variant"],
                "parameters": case["parameters"],
                "actors": case["actors"],
                "signal": case["signal"],
            }
        )
        scenario_identity = canonical_sha256(
            {
                "split": NONFRESH_CANARY_SPLIT,
                "source_scenario_id": case["scenario_id"],
                "nonfresh_scenario_class": scenario_class,
                "source_chain_sha256": chain["source_chain_sha256"],
                "semantic_parameter_block_sha256": semantic_block,
            }
        )
        intersection_sha = (
            None
            if scenario_class == "no_signal"
            else canonical_sha256(
                {
                    "regulatory_element_ids": chain[
                        "regulatory_element_ids"
                    ],
                    "controlled_lanelet_ids": chain[
                        "controlled_lanelet_ids"
                    ],
                    "stop_line_id": chain["stop_line_id"],
                    "stop_line_geometry_sha256": chain[
                        "stop_line_geometry_sha256"
                    ],
                }
            )
        )
        mode = (
            None
            if scenario_class == "no_signal"
            else chain["phase_authority_mode"]
        )
        controlled_phase = (
            chain.get("expected_current_phase")
            if mode == "controlled_same_tick_override"
            else None
        )
        identity = {
            "identity_ordinal": ordinal,
            "split": NONFRESH_CANARY_SPLIT,
            "scenario_identity_sha256": scenario_identity,
            "map_sha256": map_sha,
            "map_geometry_sha256": map_sha,
            "map_relative_path": f"maps/{map_sha}.osm",
            "corridor_sha256": case["corridor_group_sha256"],
            "intersection_sha256": intersection_sha,
            "route_identity_sha256": case["route_identity_sha256"],
            "route_family_sha256": case["route_family_id"],
            "source_independent_geometry_sha256": canonical_sha256(
                {
                    "map_sha256": map_sha,
                    "route_geometry_sha256": chain[
                        "route_geometry_sha256"
                    ],
                }
            ),
            "physical_payload": semantic,
            "source_chain_sha256": chain["source_chain_sha256"],
            "source_chain": chain,
            "initial_pose": list(case["route_spec"]["start_pose"]),
            "goal_pose": list(case["route_spec"]["goal_pose"]),
            "route_spec": copy.deepcopy(case["route_spec"]),
            "route_length_m": route_length_m,
            "scenario_family": case["family"],
            "risk_tier": case["tier"],
            "benchmark_stratum": "controlled_stress",
            "semantic_variant": case["semantic_variant"],
            "variant_index": int(case["parameters"]["variant"]),
            "parameters": copy.deepcopy(case["parameters"]),
            "semantic_parameter_block_sha256": semantic_block,
            "signal_source_class": (
                "no_signal" if scenario_class == "no_signal" else "mapped_signal"
            ),
            "phase_authority_mode": mode,
            "controlled_current_phase": controlled_phase,
            "future_phase_program_present": False,
            "same_tick_current_phase_required": True,
            "phase_remaining_available": False,
            "source_timestamp_required": True,
            "decision_timestamp_required": True,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
            "nonfresh_scenario_class": scenario_class,
            "source_fixture_root_sha256": source_fixture_root_sha256,
        }
        identities.append(identity)
        ordered_arms = [
            "candidate0_operational_default",
            "camp_static14d",
            "camp_scene14d_no_v2i",
        ]
        ordered_arms = ordered_arms[ordinal:] + ordered_arms[:ordinal]
        seed = _fixture_seed(case)
        unit_payload = {
            "scenario_identity_sha256": scenario_identity,
            "seed": seed,
            "ordered_arms": ordered_arms,
        }
        units.append(
            {
                "unit_ordinal": ordinal,
                **unit_payload,
                "unit_sha256": canonical_sha256(unit_payload),
            }
        )
    return freeze_nonfresh_production_equivalence_plan(
        identities=identities,
        execution_units=units,
    )


def build_nonfresh_prepared_runtime_rows(
    *,
    plan: Mapping[str, Any],
    selected_fixtures: Sequence[Mapping[str, Any]],
    map_artifact: Path,
) -> list[dict[str, Any]]:
    validated = validate_nonfresh_production_equivalence_plan(plan)
    if type(selected_fixtures) is not list or len(selected_fixtures) != 3:
        raise ValueError("nonFresh prepared fixture denominator drifted")
    root = Path(map_artifact).resolve()
    rows: list[dict[str, Any]] = []
    for identity, selected in zip(
        validated["identities"], selected_fixtures, strict=True
    ):
        case = copy.deepcopy(selected["case"])
        chain, scenario_class = _validated_chain(selected["source_chain"])
        if scenario_class != identity["nonfresh_scenario_class"]:
            raise ValueError("nonFresh prepared class drifted")
        map_path = (root / identity["map_relative_path"]).resolve()
        if root not in map_path.parents or _sha256(map_path) != identity["map_sha256"]:
            raise ValueError("nonFresh prepared map bytes drifted")
        case["source_map_path"] = str(map_path)
        case["signal_source_class"] = identity["signal_source_class"]
        case["phase_authority_mode"] = identity["phase_authority_mode"]
        row = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "status": "signal_complete_runtime_case_source_qualified",
            "identity_ordinal": identity["identity_ordinal"],
            "scenario_identity_sha256": identity[
                "scenario_identity_sha256"
            ],
            "semantic_parameter_block_sha256": identity[
                "semantic_parameter_block_sha256"
            ],
            "map_artifact": str(root),
            "case": case,
            "route_polyline_world_m": _world_polyline(
                chain["semantic_clone_payload"]["route_polyline_local_m"],
                case["route_spec"]["start_pose"],
            ),
            "model_loaded": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "calibration_outcomes_consumed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        row[
            "no_signal_authority"
            if scenario_class == "no_signal"
            else "mapped_signal_authority"
        ] = chain
        build_signal_complete_scene_adapter(row)
        rows.append(row)
    return rows


def build_nonfresh_runtime_qualification_rows(
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validated = validate_nonfresh_production_equivalence_plan(plan)
    rows: list[dict[str, Any]] = []
    for index, identity in enumerate(validated["identities"]):
        row = {
            "source_family": "accepted_corrected_full_corpus_nonfresh_fixture",
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "map_file_sha256": identity["map_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
            "semantic_parameter_block_sha256": identity[
                "semantic_parameter_block_sha256"
            ],
            "route_identity_sha256": identity["route_identity_sha256"],
            "benchmark_stratum": identity["benchmark_stratum"],
            "scenario_family": identity["scenario_family"],
            "tier": identity["risk_tier"],
            "signal_source_class": identity["signal_source_class"],
            "phase_authority_mode": identity["phase_authority_mode"],
            "source_chain": identity["source_chain"],
            "route_length_m": identity["route_length_m"],
            "speed_source_sha256": canonical_sha256(
                {
                    "route_identity_sha256": identity[
                        "route_identity_sha256"
                    ],
                    "source_fixture_root_sha256": identity[
                        "source_fixture_root_sha256"
                    ],
                    "source_mode": "accepted_corrected_full_corpus",
                }
            ),
            "static_signal_chain_qualified": True,
            "runtime_same_tick_signal_receipt_required": True,
            "runtime_fixed_dp_k8_support_required": True,
            "preopen_dp_forward_executed": False,
            "outcome_fields_consumed": [],
        }
        rows.append(validate_fresh_b2_manifest_row(row, index=index))
    return rows


def build_nonfresh_map_suite(
    *,
    plan: Mapping[str, Any],
    map_artifact: Path,
    source_map_paths: Mapping[str, str],
) -> dict[str, Any]:
    validated = validate_nonfresh_production_equivalence_plan(plan)
    root = Path(map_artifact).resolve()
    maps: list[dict[str, Any]] = []
    for map_sha in sorted({row["map_sha256"] for row in validated["identities"]}):
        relative = f"maps/{map_sha}.osm"
        path = (root / relative).resolve()
        if root not in path.parents or _sha256(path) != map_sha:
            raise ValueError("nonFresh map suite bytes drifted")
        source_path = source_map_paths.get(map_sha)
        if type(source_path) is not str or not Path(source_path).is_absolute():
            raise ValueError("nonFresh source map path drifted")
        maps.append(
            {
                "map_sha256": map_sha,
                "map_geometry_sha256": map_sha,
                "relative_path": relative,
                "path": str(path),
                "source_path": source_path,
                "allocated_source_reencoded": False,
            }
        )
    result = {
        "schema_version": MAP_SUITE_SCHEMA_VERSION,
        "status": "materialized_accepted_nonfresh_actual_map_bytes",
        "split": NONFRESH_CANARY_SPLIT,
        "map_count": len(maps),
        "maps": maps,
        "map_payload_sha256": canonical_sha256(maps),
        "project_authored_fresh_rows_used": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "outcome_fields_consumed": [],
    }
    return validate_nonfresh_map_suite(result, map_artifact=root)


def validate_nonfresh_map_suite(
    value: Mapping[str, Any], *, map_artifact: Path
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "split",
        "map_count",
        "maps",
        "map_payload_sha256",
        "project_authored_fresh_rows_used",
        "model_loaded",
        "candidate_generation_executed",
        "fresh_identity_cas_created",
        "fresh_outcome_consumed",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("nonFresh map suite fields drifted")
    rows = value["maps"]
    exact = {
        "schema_version": MAP_SUITE_SCHEMA_VERSION,
        "status": "materialized_accepted_nonfresh_actual_map_bytes",
        "split": NONFRESH_CANARY_SPLIT,
        "map_count": len(rows) if type(rows) is list else -1,
        "project_authored_fresh_rows_used": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "outcome_fields_consumed": [],
    }
    if any(value[name] != expected for name, expected in exact.items()):
        raise ValueError("nonFresh map suite contract drifted")
    if type(rows) is not list or not 1 <= len(rows) <= 3:
        raise ValueError("nonFresh map suite denominator drifted")
    if value["map_payload_sha256"] != canonical_sha256(rows):
        raise ValueError("nonFresh map suite root drifted")
    root = Path(map_artifact).resolve()
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != {
            "map_sha256",
            "map_geometry_sha256",
            "relative_path",
            "path",
            "source_path",
            "allocated_source_reencoded",
        }:
            raise ValueError("nonFresh map row fields drifted")
        _sha(row["map_sha256"], "map_sha256")
        if (
            row["map_geometry_sha256"] != row["map_sha256"]
            or row["allocated_source_reencoded"] is not False
            or row["map_sha256"] in seen
        ):
            raise ValueError("nonFresh map row authority drifted")
        path = (root / row["relative_path"]).resolve()
        if (
            root not in path.parents
            or str(path) != row["path"]
            or _sha256(path) != row["map_sha256"]
        ):
            raise ValueError("nonFresh map row bytes drifted")
        seen.add(row["map_sha256"])
    return json.loads(json.dumps(value))


def _validated_chain(
    raw: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if type(raw) is not dict:
        raise ValueError("nonFresh source chain must be an object")
    if raw.get("schema_version") == NO_SIGNAL_CHAIN_SCHEMA_VERSION:
        return validate_no_signal_chain(raw), "no_signal"
    if raw.get("schema_version") == MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION:
        chain = validate_mapped_signal_chain(raw)
        return (
            chain,
            {
                "observe_same_tick_request": "mapped_observe",
                "controlled_same_tick_override": (
                    "mapped_controlled_override"
                ),
            }[chain["phase_authority_mode"]],
        )
    raise ValueError("nonFresh source chain schema is unsupported")


def _fixture_seed(case: Mapping[str, Any]) -> int:
    seeds = case.get("seeds")
    if (
        type(seeds) is not list
        or not seeds
        or any(type(seed) is not int or seed < 0 for seed in seeds)
    ):
        raise ValueError("nonFresh fixture seed authority drifted")
    return seeds[0]


def _route_length(points: Any) -> float:
    array = np.asarray(points, dtype=np.float64)
    if (
        array.ndim != 2
        or array.shape != (64, 2)
        or not np.isfinite(array).all()
    ):
        raise ValueError("nonFresh semantic route polyline drifted")
    length = float(np.linalg.norm(np.diff(array, axis=0), axis=1).sum())
    if not math.isfinite(length) or length <= 0.0:
        raise ValueError("nonFresh semantic route length drifted")
    return length


def _world_polyline(points: Any, start_pose: Any) -> list[list[float]]:
    local = np.asarray(points, dtype=np.float64)
    pose = np.asarray(start_pose, dtype=np.float64)
    if local.shape != (64, 2) or pose.shape != (3,):
        raise ValueError("nonFresh world-polyline source drifted")
    c = math.cos(float(pose[2]))
    s = math.sin(float(pose[2]))
    rotation = np.asarray([[c, s], [-s, c]], dtype=np.float64)
    return (local @ rotation + pose[:2]).tolist()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")
