from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    build_causal_signal_atom_input,
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
    build_runtime_signal_receipt,
    validate_no_signal_chain,
    validate_signal_chain,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_scenario_case_v1"
PLAN_SCHEMA_VERSION = "camp_dp_v25_controlled_scenario_plan_v1"
FINAL_PLAN_SCHEMA_VERSION = "camp_dp_v25_controlled_corpus_final_plan_v1"
SCENARIO_FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)
RISK_TIERS = ("easy", "borderline", "high_risk")
PILOT_CASES_PER_FAMILY = 21
TRAIN_SEEDS = (25001,)
CALIBRATION_SEEDS = (25101,)
FRESH_B_SEEDS = (25201, 25202, 25203, 25204, 25205)
PILOT_SEEDS = (25991,)


class ScenarioCapabilityReason(str, Enum):
    """Pre-registered runtime capability failures that may be retained."""

    MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE = (
        "mapped_current_signal_source_unavailable"
    )


class RetainedScenarioCapabilityFailure(RuntimeError):
    """A typed, outcome-blind scenario capability failure."""

    def __init__(
        self,
        *,
        scenario_id: str,
        family: str,
        reason: ScenarioCapabilityReason,
    ) -> None:
        self.scenario_id = str(scenario_id)
        self.family = str(family)
        self.reason = reason
        super().__init__(
            f"scenario capability unavailable: {self.family}/{self.reason.value}"
        )

    def as_receipt(self) -> dict[str, str]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "reason": self.reason.value,
        }


_TIER_PARAMETERS = {
    "easy": {
        "headway_m": 34.0,
        "ego_speed_mps": 7.0,
        "other_speed_mps": 7.0,
        "deceleration_mps2": -2.0,
        "trigger_time_s": 2.5,
        "lateral_offset_m": 4.0,
        "lateral_speed_mps": 0.6,
        "crossing_speed_mps": 1.2,
    },
    "borderline": {
        "headway_m": 22.0,
        "ego_speed_mps": 8.0,
        "other_speed_mps": 5.0,
        "deceleration_mps2": -4.0,
        "trigger_time_s": 1.5,
        "lateral_offset_m": 3.0,
        "lateral_speed_mps": 1.0,
        "crossing_speed_mps": 1.8,
    },
    "high_risk": {
        "headway_m": 14.0,
        "ego_speed_mps": 9.0,
        "other_speed_mps": 2.0,
        "deceleration_mps2": -6.0,
        "trigger_time_s": 0.8,
        "lateral_offset_m": 2.0,
        "lateral_speed_mps": 1.5,
        "crossing_speed_mps": 2.5,
    },
}


@dataclass(frozen=True)
class ControlledScenarioPlan:
    pilot: tuple[dict[str, Any], ...]
    train: tuple[dict[str, Any], ...]
    calibration: tuple[dict[str, Any], ...]
    fresh_b: tuple[dict[str, Any], ...]
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_SCHEMA_VERSION,
            "pilot": list(self.pilot),
            "train": list(self.train),
            "calibration": list(self.calibration),
            "fresh_b": list(self.fresh_b),
            "summary": self.summary,
        }


def build_controlled_scenario_plan(
    retained_routes: Sequence[Mapping[str, Any]],
    split_records: Sequence[Mapping[str, Any]],
) -> ControlledScenarioPlan:
    """Freeze the outcome-blind V25 grammar, inventories, and split schedules."""
    corridor_by_record = {
        str(record["record_key"]): str(record["corridor_group_sha256"])
        for record in split_records
    }
    split_by_family = {
        "map_family_d7f16a17d3eb": "train",
        "map_family_f62e06cd1303": "calibration",
        "map_family_828a913c2f9a": "fresh_b",
    }
    routes_by_split: dict[str, list[Mapping[str, Any]]] = {
        "train": [],
        "calibration": [],
        "fresh_b": [],
    }
    for route in sorted(retained_routes, key=lambda item: str(item["record_key"])):
        record_key = str(route["record_key"])
        family = str(route["map_family_id"])
        if family not in split_by_family or record_key not in corridor_by_record:
            raise ValueError("route inventory is inconsistent with the frozen split")
        routes_by_split[split_by_family[family]].append(route)
    expected_route_counts = {"train": 375, "calibration": 2, "fresh_b": 24}
    if {key: len(value) for key, value in routes_by_split.items()} != expected_route_counts:
        raise ValueError("V25 requires the sealed 375/2/24 source route inventory")

    pilot: list[dict[str, Any]] = []
    train_routes = routes_by_split["train"]
    for family_index, family in enumerate(SCENARIO_FAMILIES):
        eligible = [route for route in train_routes if _route_supports(route, family)]
        if len(eligible) < PILOT_CASES_PER_FAMILY:
            raise ValueError(f"pilot source ceiling is below 21 for {family}")
        offset = (family_index * PILOT_CASES_PER_FAMILY) % len(eligible)
        ordered = eligible[offset:] + eligible[:offset]
        for index, route in enumerate(ordered[:PILOT_CASES_PER_FAMILY]):
            pilot.append(
                build_controlled_scenario_case(
                    route=route,
                    corridor_group_sha256=corridor_by_record[str(route["record_key"])],
                    split="pilot_development",
                    family=family,
                    tier=RISK_TIERS[index % len(RISK_TIERS)],
                    variant=index,
                    seeds=PILOT_SEEDS,
                )
            )

    train: list[dict[str, Any]] = []
    for route_index, route in enumerate(train_routes):
        for variant in range(4):
            family_index = (route_index * 4 + variant) % len(SCENARIO_FAMILIES)
            family = SCENARIO_FAMILIES[family_index]
            while not _route_supports(route, family):
                family_index = (family_index + 1) % len(SCENARIO_FAMILIES)
                family = SCENARIO_FAMILIES[family_index]
            train.append(
                build_controlled_scenario_case(
                    route=route,
                    corridor_group_sha256=corridor_by_record[str(route["record_key"])],
                    split="train",
                    family=family,
                    tier=RISK_TIERS[(route_index + variant) % len(RISK_TIERS)],
                    variant=variant,
                    seeds=TRAIN_SEEDS,
                )
            )

    calibration: list[dict[str, Any]] = []
    for route in routes_by_split["calibration"]:
        for family in SCENARIO_FAMILIES:
            for tier_index, tier in enumerate(RISK_TIERS):
                calibration.append(
                    build_controlled_scenario_case(
                        route=route,
                        corridor_group_sha256=corridor_by_record[
                            str(route["record_key"])
                        ],
                        split="calibration",
                        family=family,
                        tier=tier,
                        variant=tier_index,
                        seeds=CALIBRATION_SEEDS,
                    )
                )

    fresh_b: list[dict[str, Any]] = []
    fresh_families = tuple(
        family for family in SCENARIO_FAMILIES if family != "red_light_phase_timing"
    )
    for route_index, route in enumerate(routes_by_split["fresh_b"]):
        for variant in range(5):
            family = fresh_families[(route_index * 5 + variant) % len(fresh_families)]
            if not _route_supports(route, family):
                raise ValueError("Fresh B scheduled a source-ineligible family")
            fresh_b.append(
                build_controlled_scenario_case(
                    route=route,
                    corridor_group_sha256=corridor_by_record[str(route["record_key"])],
                    split="fresh_b",
                    family=family,
                    tier=RISK_TIERS[(route_index + variant) % len(RISK_TIERS)],
                    variant=variant,
                    seeds=FRESH_B_SEEDS,
                )
            )

    collections = {
        "pilot_development": pilot,
        "train": train,
        "calibration": calibration,
        "fresh_b": fresh_b,
    }
    summary = _plan_summary(collections, routes_by_split)
    _validate_plan(collections, summary)
    return ControlledScenarioPlan(
        pilot=tuple(pilot),
        train=tuple(train),
        calibration=tuple(calibration),
        fresh_b=tuple(fresh_b),
        summary=summary,
    )


def build_final_controlled_corpus_plan(
    retained_routes: Sequence[Mapping[str, Any]],
    split_records: Sequence[Mapping[str, Any]],
    source_availability: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Freeze formal corpora after the outcome-blind coverage/source audit.

    The pilot schedule is not rewritten. Formal executable identities use only
    routes whose current Lanelet2 source supplies the positive speed-limit
    contract required by canonical 14D materialization. Every excluded route
    remains in the manifest as an explicit source-ineligible record.
    """
    corridor_by_record = {
        str(record["record_key"]): str(record["corridor_group_sha256"])
        for record in split_records
    }
    split_by_family = {
        "map_family_d7f16a17d3eb": "train",
        "map_family_f62e06cd1303": "calibration",
        "map_family_828a913c2f9a": "fresh_b",
    }
    routes_by_split: dict[str, list[Mapping[str, Any]]] = {
        "train": [],
        "calibration": [],
        "fresh_b": [],
    }
    for route in sorted(retained_routes, key=lambda item: str(item["record_key"])):
        key = str(route["record_key"])
        if key not in source_availability or key not in corridor_by_record:
            raise ValueError("formal source availability does not cover every route")
        routes_by_split[split_by_family[str(route["map_family_id"])]].append(route)

    executable_train_routes = [
        route
        for route in routes_by_split["train"]
        if bool(source_availability[str(route["record_key"])]["speed_limit_complete"])
    ]
    if not executable_train_routes:
        raise ValueError("no controlled train route has complete speed-limit source")
    train: list[dict[str, Any]] = []
    for index in range(1500):
        route = executable_train_routes[index % len(executable_train_routes)]
        family_index = index % len(SCENARIO_FAMILIES)
        family = SCENARIO_FAMILIES[family_index]
        availability = source_availability[str(route["record_key"])]
        while family == "red_light_phase_timing" and not availability[
            "mapped_traffic_light"
        ]:
            family_index = (family_index + 1) % len(SCENARIO_FAMILIES)
            family = SCENARIO_FAMILIES[family_index]
        case = build_controlled_scenario_case(
            route=route,
            corridor_group_sha256=corridor_by_record[str(route["record_key"])],
            split="train",
            family=family,
            tier=RISK_TIERS[(index // len(executable_train_routes)) % len(RISK_TIERS)],
            variant=index,
            seeds=TRAIN_SEEDS,
        )
        train.append(_attach_source_availability(case, availability))
    train.extend(
        _retained_source_ineligible_cases(
            routes_by_split["train"],
            source_availability,
            corridor_by_record,
            split="train",
            seeds=TRAIN_SEEDS,
        )
    )

    calibration: list[dict[str, Any]] = []
    for route in routes_by_split["calibration"]:
        availability = source_availability[str(route["record_key"])]
        for family in SCENARIO_FAMILIES:
            for tier_index, tier in enumerate(RISK_TIERS):
                case = build_controlled_scenario_case(
                    route=route,
                    corridor_group_sha256=corridor_by_record[
                        str(route["record_key"])
                    ],
                    split="calibration",
                    family=family,
                    tier=tier,
                    variant=tier_index,
                    seeds=CALIBRATION_SEEDS,
                )
                calibration.append(_attach_source_availability(case, availability))

    executable_fresh_routes = [
        route
        for route in routes_by_split["fresh_b"]
        if bool(source_availability[str(route["record_key"])]["speed_limit_complete"])
    ]
    if not executable_fresh_routes:
        raise ValueError("Fresh B has no route with complete speed-limit source")
    fresh_families = tuple(
        family for family in SCENARIO_FAMILIES if family != "red_light_phase_timing"
    )
    fresh_b: list[dict[str, Any]] = []
    for index in range(120):
        route = executable_fresh_routes[index % len(executable_fresh_routes)]
        availability = source_availability[str(route["record_key"])]
        case = build_controlled_scenario_case(
            route=route,
            corridor_group_sha256=corridor_by_record[str(route["record_key"])],
            split="fresh_b",
            family=fresh_families[index % len(fresh_families)],
            tier=RISK_TIERS[(index // len(executable_fresh_routes)) % len(RISK_TIERS)],
            variant=index,
            seeds=FRESH_B_SEEDS,
        )
        fresh_b.append(_attach_source_availability(case, availability))
    fresh_b.extend(
        _retained_source_ineligible_cases(
            routes_by_split["fresh_b"],
            source_availability,
            corridor_by_record,
            split="fresh_b",
            seeds=FRESH_B_SEEDS,
        )
    )

    collections = {"train": train, "calibration": calibration, "fresh_b": fresh_b}
    summary = _final_plan_summary(collections, routes_by_split, source_availability)
    _validate_final_plan(collections, summary)
    return {
        "schema_version": FINAL_PLAN_SCHEMA_VERSION,
        **collections,
        "summary": summary,
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "fresh_b_outcome_opened": False,
    }


def build_controlled_scenario_case(
    *,
    route: Mapping[str, Any],
    corridor_group_sha256: str,
    split: str,
    family: str,
    tier: str,
    variant: int,
    seeds: Sequence[int],
) -> dict[str, Any]:
    if family not in SCENARIO_FAMILIES:
        raise ValueError(f"unknown controlled scenario family: {family}")
    if tier not in RISK_TIERS:
        raise ValueError(f"unknown controlled scenario tier: {tier}")
    if isinstance(variant, bool) or not isinstance(variant, int) or variant < 0:
        raise ValueError("scenario variant must be a nonnegative integer")
    seed_values = tuple(int(seed) for seed in seeds)
    if not seed_values or len(set(seed_values)) != len(seed_values):
        raise ValueError("scenario seed namespace must be nonempty and unique")

    params = dict(_TIER_PARAMETERS[tier])
    params["variant"] = int(variant)
    supported = _route_supports(route, family)
    semantic_variant = _semantic_variant(route, family, variant)
    actors, signal = _materialize_semantics(
        route=route,
        family=family,
        tier=tier,
        semantic_variant=semantic_variant,
        params=params,
    )
    parameter_block_id = (
        f"{split}:{family}:{tier}:v{variant:02d}:"
        f"{str(route['map_family_id'])[:24]}"
    )
    identity_payload = {
        "schema_version": SCHEMA_VERSION,
        "split": split,
        "family": family,
        "tier": tier,
        "semantic_variant": semantic_variant,
        "parameter_block_id": parameter_block_id,
        "route_identity_sha256": str(route["identity_sha256"]),
        "seeds": list(seed_values),
        "parameters": params,
        "actors": actors,
        "signal": signal,
    }
    scenario_id = _canonical_sha256(identity_payload)
    case = {
        **identity_payload,
        "scenario_id": scenario_id,
        "record_key": str(route["record_key"]),
        "map_family_id": str(route["map_family_id"]),
        "corridor_group_sha256": str(corridor_group_sha256),
        "route_family_id": str(route["route_serialization_sha256"]),
        "source_map_path": str(route["source_map_path"]),
        "source_map_sha256": str(route["source_map_sha256"]),
        "route_spec": dict(route["route_spec"]),
        "source_stratum": dict(route["source_stratum"]),
        "runner_eligible": bool(supported),
        "source_requirements": _source_requirements(family),
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "holdout_outcome_consumed": False,
    }
    validate_controlled_scenario_case(case)
    return case


def validate_controlled_scenario_case(case: Mapping[str, Any]) -> None:
    if case.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("controlled scenario schema mismatch")
    if case.get("family") not in SCENARIO_FAMILIES:
        raise ValueError("controlled scenario family mismatch")
    if case.get("tier") not in RISK_TIERS:
        raise ValueError("controlled scenario tier mismatch")
    if case.get("outcome_blind") is not True:
        raise ValueError("controlled scenario must be outcome-blind")
    if case.get("outcome_fields_consumed") != []:
        raise ValueError("controlled scenario consumed outcome fields")
    if case.get("holdout_outcome_consumed") is not False:
        raise ValueError("controlled scenario consumed holdout outcome")
    scenario_id = case.get("scenario_id")
    if not _is_sha256(scenario_id):
        raise ValueError("controlled scenario ID must be SHA256")
    seeds = case.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
    ):
        raise ValueError("controlled scenario seeds are invalid")
    actors = case.get("actors")
    if not isinstance(actors, list):
        raise ValueError("controlled scenario actors must be a list")
    for actor in actors:
        if not isinstance(actor, Mapping):
            raise ValueError("controlled actor must be a mapping")
        xy = np.asarray(actor.get("initial_xy"), dtype=np.float64)
        tangent = np.asarray(actor.get("route_tangent"), dtype=np.float64)
        normal = np.asarray(actor.get("route_normal"), dtype=np.float64)
        if (
            xy.shape != (2,)
            or tangent.shape != (2,)
            or normal.shape != (2,)
            or not np.all(np.isfinite(np.concatenate((xy, tangent, normal))))
            or not np.isclose(np.linalg.norm(tangent), 1.0, atol=1e-6)
            or not np.isclose(np.linalg.norm(normal), 1.0, atol=1e-6)
        ):
            raise ValueError("controlled actor geometry is invalid")
    signal = case.get("signal")
    if not isinstance(signal, Mapping):
        raise ValueError("controlled signal must be a mapping")
    if signal.get("phase") not in {"none", "green", "yellow", "red"}:
        raise ValueError("controlled signal phase is invalid")


class V25ControlledSceneAdapter:
    """Apply a deterministic exogenous schedule to a fixed-DP SceneContext.

    Actor poses are rebuilt analytically from the frozen schedule at each tick.
    The adapter does not read model candidates, selected trajectories, outcomes,
    route/scenario IDs as model features, or any future ground truth.
    """

    def __init__(
        self,
        case: Mapping[str, Any],
        *,
        red_signal_authority: Mapping[str, Any] | None = None,
        no_signal_authority: Mapping[str, Any] | None = None,
    ) -> None:
        validate_controlled_scenario_case(case)
        if case.get("runner_eligible") is not True:
            raise ValueError("cannot execute a source-ineligible controlled scenario")
        self.case = dict(case)
        self.red_signal_authority = (
            None
            if red_signal_authority is None
            else validate_signal_chain(red_signal_authority)
        )
        self.no_signal_authority = (
            None
            if no_signal_authority is None
            else validate_no_signal_chain(no_signal_authority)
        )
        if self.red_signal_authority is not None and self.no_signal_authority is not None:
            raise ValueError("controlled scenario has ambiguous signal authority")
        self._route_lanelet_ids: tuple[int, ...] = ()
        self._map_lanelet_ids: tuple[int, ...] = ()
        self.receipts: list[dict[str, Any]] = []

    def bind_runtime_lanelet_ids(
        self,
        *,
        route_lanelet_ids: Sequence[int],
        map_lanelet_ids: Sequence[int],
    ) -> None:
        route = tuple(int(value) for value in route_lanelet_ids)
        mapped = tuple(int(value) for value in map_lanelet_ids)
        if (
            not route
            or not mapped
            or len(set(route)) != len(route)
            or len(set(mapped)) != len(mapped)
        ):
            raise ValueError("runtime route/map lanelet IDs are empty or ambiguous")
        self._route_lanelet_ids = route
        self._map_lanelet_ids = mapped

    def __call__(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        if isinstance(tick_index, bool) or not isinstance(tick_index, int) or tick_index < 0:
            raise ValueError("controlled scene tick must be a nonnegative integer")
        ego = scene.ego_agent
        if ego is None:
            raise ValueError("controlled scene requires an ego agent")
        sim_time_s = float(tick_index) * float(scene.dt)
        actor_receipts = []
        for spec in self.case["actors"]:
            actor_receipts.append(self._upsert_actor(scene, ego, spec, sim_time_s))
        signal_receipt = self._apply_signal(scene, tick_index, sim_time_s)
        receipt = {
            "scenario_id": self.case["scenario_id"],
            "tick_index": tick_index,
            "sim_time_s": sim_time_s,
            "actor_count": len(actor_receipts),
            "actors": actor_receipts,
            "signal": signal_receipt,
            "outcome_fields_consumed": [],
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
        }
        self.receipts.append(receipt)
        return receipt

    def causal_signal_atom_input(
        self, scene: Any, tick_index: int
    ) -> Mapping[str, Any]:
        """Return the same-tick R0-authorized stop line in the ego frame."""
        if self.red_signal_authority is None and self.no_signal_authority is None:
            raise RetainedScenarioCapabilityFailure(
                scenario_id=str(self.case["scenario_id"]),
                family=str(self.case["family"]),
                reason=ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE,
            )
        if not self.receipts or self.receipts[-1].get("tick_index") != tick_index:
            raise ValueError("controlled signal receipt is not same-tick")
        signal = self.receipts[-1].get("signal")
        if not isinstance(signal, Mapping) or not isinstance(
            signal.get("source_receipt"), Mapping
        ):
            raise ValueError("controlled signal source receipt is unavailable")
        if self.no_signal_authority is not None:
            return build_no_signal_causal_atom_input(
                self.no_signal_authority, signal["source_receipt"]
            )
        ego = scene.ego_agent
        if ego is None:
            raise ValueError("controlled signal atom input requires ego state")
        return build_causal_signal_atom_input(
            self.red_signal_authority,
            signal["source_receipt"],
            ego_position_world_m=np.asarray(ego.current_position, dtype=np.float64),
            ego_heading_rad=float(ego.current_heading),
        )

    def _upsert_actor(
        self, scene: Any, ego: Any, spec: Mapping[str, Any], sim_time_s: float
    ) -> dict[str, Any]:
        history_times = sim_time_s + (np.arange(31, dtype=np.float64) - 30.0) * float(
            scene.dt
        )
        states = [_actor_state(spec, value) for value in history_times]
        trajectory = np.asarray(
            [[state[0][0], state[0][1], state[1]] for state in states],
            dtype=np.float32,
        )
        velocities = np.asarray([state[2] for state in states], dtype=np.float32)
        current_acceleration = np.asarray(states[-1][3], dtype=np.float32)
        actor_id = str(spec["id"])
        existing = next((agent for agent in scene.agents if agent.id == actor_id), None)
        if existing is None:
            enum_class = ego.agent_type.__class__
            agent_type = getattr(enum_class, str(spec["agent_type"]).upper())
            existing = ego.__class__(
                id=actor_id,
                agent_type=agent_type,
                length=float(spec["length_m"]),
                width=float(spec["width_m"]),
                wheelbase=float(spec["wheelbase_m"]),
                past_trajectory=trajectory,
                past_velocities=velocities,
                acceleration=current_acceleration,
                steering_angle=0.0,
                yaw_rate=0.0,
                goal_pose=None,
                route_lanes=None,
                route_speed_limit=None,
                route_has_speed_limit=None,
                turn_indicators=np.zeros(31, dtype=np.int32),
                age_steps=999,
                route_lanelet_ids=None,
            )
            scene.agents.append(existing)
        else:
            existing.past_trajectory = trajectory
            existing.past_velocities = velocities
            existing.acceleration = current_acceleration
            existing.yaw_rate = 0.0
            existing.steering_angle = 0.0
        return {
            "id": actor_id,
            "agent_type": str(spec["agent_type"]),
            "position_xy": trajectory[-1, :2].astype(float).tolist(),
            "heading_rad": float(trajectory[-1, 2]),
            "velocity_xy_mps": velocities[-1].astype(float).tolist(),
            "scripted_exogenous": True,
            "excluded_from_dp_control": actor_id.startswith("static_npc_v25_"),
        }

    def _apply_signal(
        self,
        scene: Any,
        tick_index: int,
        sim_time_s: float,
    ) -> dict[str, Any]:
        signal = self.case["signal"]
        phase = str(signal["phase"])
        if phase == "none":
            if self.no_signal_authority is None:
                return {"phase": phase, "source_row_count": 0, "applied": False}
            receipt = build_runtime_no_signal_receipt(
                self.no_signal_authority,
                scenario_id=str(self.case["scenario_id"]),
                tick_index=tick_index,
                decision_time_s=sim_time_s,
            )
            return {
                "phase": phase,
                "source_row_count": 0,
                "applied": False,
                "source_receipt": receipt,
            }
        if self.red_signal_authority is None:
            raise RetainedScenarioCapabilityFailure(
                scenario_id=str(self.case["scenario_id"]),
                family=str(self.case["family"]),
                reason=(
                    ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE
                ),
            )
        channel = {"green": 0, "yellow": 1, "red": 2}[phase]
        controlled = set(self.red_signal_authority["controlled_lanelet_ids"])
        applied_route_lanelet_ids: list[int] = []
        applied_map_lanelet_ids: list[int] = []
        ego = scene.ego_agent
        if ego is not None and ego.route_lanes is not None:
            route_ids = self._route_lanelet_ids
            if not route_ids or len(route_ids) > len(ego.route_lanes):
                raise ValueError("runtime route lanelet ID/tensor alignment is unavailable")
            padded = np.asarray(ego.route_lanes[len(route_ids) :])
            if padded.size and np.any(np.abs(padded) > 0.0):
                raise ValueError("runtime route tensor has unmapped nonzero rows")
            for row_index, lanelet_id in enumerate(route_ids):
                if lanelet_id not in controlled:
                    continue
                values = ego.route_lanes[row_index]
                if not np.any(values[:, 8:12] > 0.5):
                    raise ValueError("qualified route signal row has no current source")
                values[:, 8:13] = 0.0
                values[:, 8 + channel] = 1.0
                applied_route_lanelet_ids.append(lanelet_id)
        if scene.map_data is not None and scene.map_data.lanes is not None:
            values = np.asarray(scene.map_data.lanes)
            if values.ndim != 3 or values.shape[2] < 13:
                raise ValueError("traffic-light tensor shape changed")
            if len(self._map_lanelet_ids) != len(values):
                raise ValueError("runtime map lanelet ID/tensor alignment is unavailable")
            for row_index, lanelet_id in enumerate(self._map_lanelet_ids):
                if lanelet_id not in controlled:
                    continue
                if not np.any(values[row_index, :, 8:12] > 0.5):
                    raise ValueError("qualified map signal row has no current source")
                values[row_index, :, 8:13] = 0.0
                values[row_index, :, 8 + channel] = 1.0
                applied_map_lanelet_ids.append(lanelet_id)
        if not applied_route_lanelet_ids and not applied_map_lanelet_ids:
            raise RetainedScenarioCapabilityFailure(
                scenario_id=str(self.case["scenario_id"]),
                family=str(self.case["family"]),
                reason=(
                    ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE
                ),
            )
        receipt = build_runtime_signal_receipt(
            self.red_signal_authority,
            scenario_id=str(self.case["scenario_id"]),
            tick_index=tick_index,
            decision_time_s=sim_time_s,
            current_phase=phase,
            applied_route_lanelet_ids=applied_route_lanelet_ids,
            applied_map_lanelet_ids=applied_map_lanelet_ids,
        )
        return {
            "phase": phase,
            "source_row_count": (
                len(applied_route_lanelet_ids) + len(applied_map_lanelet_ids)
            ),
            "applied": True,
            "source_receipt": receipt,
        }


def _materialize_semantics(
    *,
    route: Mapping[str, Any],
    family: str,
    tier: str,
    semantic_variant: str,
    params: Mapping[str, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    headway = min(float(params["headway_m"]), float(route["source_route_length_m"]) - 12.0)
    anchor_xy, heading = _route_pose(route, max(headway, 8.0))
    tangent = np.asarray([math.cos(heading), math.sin(heading)], dtype=np.float64)
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    common = {
        "route_tangent": tangent.tolist(),
        "route_normal": normal.tolist(),
        "trigger_time_s": float(params["trigger_time_s"]),
        "longitudinal_acceleration_mps2": 0.0,
        "lateral_target_m": None,
    }
    actors: list[dict[str, Any]] = []
    signal = {"phase": "none", "phase_remaining_s": 0.0, "mapped_source_required": False}

    def actor(
        index: int,
        *,
        agent_type: str,
        longitudinal_speed: float,
        lateral_offset: float = 0.0,
        lateral_speed: float = 0.0,
        acceleration: float = 0.0,
        heading_offset: float = 0.0,
        length: float = 4.5,
        width: float = 1.8,
        lateral_target: float | None = None,
    ) -> dict[str, Any]:
        position = anchor_xy + normal * lateral_offset
        return {
            **common,
            "id": f"static_npc_v25_{index}",
            "agent_type": agent_type,
            "initial_xy": position.tolist(),
            "initial_heading_rad": float(heading + heading_offset),
            "longitudinal_speed_mps": float(longitudinal_speed),
            "lateral_offset_m": float(lateral_offset),
            "lateral_speed_mps": float(lateral_speed),
            "lateral_target_m": lateral_target,
            "longitudinal_acceleration_mps2": float(acceleration),
            "length_m": float(length),
            "width_m": float(width),
            "wheelbase_m": float(max(length * 0.65, 0.5)),
        }

    if family == "lead_vehicle_hard_brake":
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=float(params["other_speed_mps"]),
                acceleration=float(params["deceleration_mps2"]),
            )
        )
    elif family == "cut_in_merge":
        lateral = float(params["lateral_offset_m"])
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=float(params["other_speed_mps"]),
                lateral_offset=lateral,
                lateral_speed=-float(params["lateral_speed_mps"]),
                lateral_target=0.0,
                heading_offset=-0.18,
            )
        )
    elif family == "pedestrian_cyclist_crossing":
        lateral = float(params["lateral_offset_m"]) + 1.5
        crossing_type = "bicycle" if semantic_variant == "cyclist_crossing" else "pedestrian"
        actors.append(
            actor(
                0,
                agent_type=crossing_type,
                longitudinal_speed=0.0,
                lateral_offset=lateral,
                lateral_speed=-float(params["crossing_speed_mps"]),
                lateral_target=-lateral,
                heading_offset=-math.pi / 2.0,
                length=1.8 if crossing_type == "bicycle" else 0.7,
                width=0.6,
            )
        )
        if tier != "easy":
            actors.append(
                actor(
                    1,
                    agent_type="vehicle",
                    longitudinal_speed=0.0,
                    lateral_offset=lateral * 0.72,
                    length=4.8,
                    width=2.0,
                )
            )
    elif family == "unprotected_turn_oncoming_conflict":
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=-max(float(params["other_speed_mps"]), 5.0),
                lateral_offset=0.4 if semantic_variant == "unprotected_turn" else 0.8,
                heading_offset=math.pi,
            )
        )
    elif family == "red_light_phase_timing":
        phase = {"easy": "green", "borderline": "yellow", "high_risk": "red"}[tier]
        remaining = {"easy": 12.0, "borderline": 2.0, "high_risk": 8.0}[tier]
        signal = {
            "phase": phase,
            "phase_remaining_s": remaining,
            "mapped_source_required": True,
        }
    elif family == "blocked_lane_static_obstacle":
        actors.append(actor(0, agent_type="vehicle", longitudinal_speed=0.0))
    elif family == "narrow_encounter":
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=-max(float(params["other_speed_mps"]), 4.0),
                lateral_offset=0.55,
                heading_offset=math.pi,
                width=2.0,
            )
        )
    else:  # pragma: no cover - guarded by public validation
        raise AssertionError(family)
    return actors, signal


def _actor_state(
    spec: Mapping[str, Any], sim_time_s: float
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    tangent = np.asarray(spec["route_tangent"], dtype=np.float64)
    normal = np.asarray(spec["route_normal"], dtype=np.float64)
    initial = np.asarray(spec["initial_xy"], dtype=np.float64)
    trigger = float(spec["trigger_time_s"])
    speed = float(spec["longitudinal_speed_mps"])
    acceleration = float(spec["longitudinal_acceleration_mps2"])
    elapsed = max(sim_time_s - trigger, 0.0)
    if acceleration < 0.0 and speed > 0.0:
        stop_time = speed / -acceleration
        active = min(elapsed, stop_time)
        if sim_time_s < trigger:
            longitudinal_displacement = speed * sim_time_s
        else:
            longitudinal_displacement = (
                speed * trigger + speed * active + 0.5 * acceleration * active**2
            )
        longitudinal_speed = max(speed + acceleration * elapsed, 0.0)
    else:
        longitudinal_displacement = speed * sim_time_s + 0.5 * acceleration * elapsed**2
        longitudinal_speed = speed + acceleration * elapsed
    lateral_speed = float(spec["lateral_speed_mps"])
    lateral_displacement = lateral_speed * sim_time_s
    target = spec.get("lateral_target_m")
    if target is not None:
        initial_offset = float(spec["lateral_offset_m"])
        desired = initial_offset + lateral_displacement
        if lateral_speed < 0.0:
            desired = max(float(target), desired)
        else:
            desired = min(float(target), desired)
        lateral_displacement = desired - initial_offset
        if desired == float(target):
            lateral_speed = 0.0
    position = initial + tangent * longitudinal_displacement + normal * lateral_displacement
    velocity = tangent * longitudinal_speed + normal * lateral_speed
    accel_vector = tangent * (acceleration if sim_time_s >= trigger and longitudinal_speed != 0.0 else 0.0)
    if np.linalg.norm(velocity) > 1e-8:
        heading = float(math.atan2(velocity[1], velocity[0]))
    else:
        heading = float(spec["initial_heading_rad"])
    return position, heading, velocity, accel_vector


def _route_pose(route: Mapping[str, Any], distance_m: float) -> tuple[np.ndarray, float]:
    points = np.asarray(route["centerline_samples_m"], dtype=np.float64)
    headings = np.asarray(route["centerline_headings_rad"], dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2:
        raise ValueError("route centerline samples are invalid")
    segments = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(segments)))
    target = float(np.clip(distance_m, 0.0, cumulative[-1]))
    index = min(int(np.searchsorted(cumulative, target, side="right") - 1), len(points) - 2)
    span = max(float(cumulative[index + 1] - cumulative[index]), 1e-9)
    ratio = (target - cumulative[index]) / span
    point = points[index] * (1.0 - ratio) + points[index + 1] * ratio
    heading = float(headings[min(index, len(headings) - 1)])
    return point, heading


def _route_supports(route: Mapping[str, Any], family: str) -> bool:
    stratum = route.get("source_stratum")
    if not isinstance(stratum, Mapping):
        return False
    if family == "red_light_phase_timing":
        return bool(stratum.get("traffic_light"))
    return True


def _semantic_variant(route: Mapping[str, Any], family: str, variant: int) -> str:
    stratum = route["source_stratum"]
    if family == "pedestrian_cyclist_crossing":
        return "cyclist_crossing" if variant % 2 else "pedestrian_crossing"
    if family == "unprotected_turn_oncoming_conflict":
        return "unprotected_turn" if stratum.get("branch_intersection") else "oncoming_conflict"
    return family


def _source_requirements(family: str) -> list[str]:
    requirements = ["fixed_dp_current_request", "fixed_k8", "explicit_lanelet2_route"]
    if family == "red_light_phase_timing":
        requirements.append("mapped_traffic_light_regulatory_source")
    return requirements


def _plan_summary(
    collections: Mapping[str, Sequence[Mapping[str, Any]]],
    routes_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    split_counts = {}
    for split, cases in collections.items():
        split_counts[split] = {
            "scenario_identity_count": len(cases),
            "runner_eligible_count": sum(case["runner_eligible"] is True for case in cases),
            "route_count": len({case["record_key"] for case in cases}),
            "corridor_count": len({case["corridor_group_sha256"] for case in cases}),
            "map_family_count": len({case["map_family_id"] for case in cases}),
            "scenario_seed_run_count": sum(len(case["seeds"]) for case in cases),
            "family_counts": {
                family: sum(case["family"] == family for case in cases)
                for family in SCENARIO_FAMILIES
            },
            "tier_counts": {
                tier: sum(case["tier"] == tier for case in cases) for tier in RISK_TIERS
            },
        }
    v24_snapshots = 67_796
    controlled_train_snapshots = split_counts["train"]["runner_eligible_count"] * 64
    return {
        "split_counts": split_counts,
        "route_inventory_ceiling": {
            split: len(routes) for split, routes in routes_by_split.items()
        },
        "fresh_b_corridor_ceiling": split_counts["fresh_b"]["corridor_count"],
        "fresh_b_route_ceiling": split_counts["fresh_b"]["route_count"],
        "fresh_b_paired_run_count": split_counts["fresh_b"][
            "scenario_seed_run_count"
        ],
        "v24_reused_train_snapshot_count": v24_snapshots,
        "v25_controlled_train_snapshot_capacity_at_64_ticks": controlled_train_snapshots,
        "combined_train_snapshot_capacity_at_64_ticks": (
            v24_snapshots + controlled_train_snapshots
        ),
        "inventory_ceiling_disclosure": (
            "Fresh B is frozen at 24 independent routes and 3 source corridor "
            "groups; 120 scenario identities x 5 fresh seeds yield 600 paired "
            "runs without representing those repetitions as independent routes."
        ),
        "calibration_ceiling_disclosure": (
            "Calibration has two independent source routes; red-light cases are "
            "retained as source-ineligible rather than fabricated on a map with "
            "no mapped traffic-light regulatory source."
        ),
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "holdout_outcome_consumed": False,
    }


def _validate_plan(
    collections: Mapping[str, Sequence[Mapping[str, Any]]], summary: Mapping[str, Any]
) -> None:
    if len(collections["pilot_development"]) != len(SCENARIO_FAMILIES) * 21:
        raise ValueError("coverage pilot must freeze 21 configurations per family")
    if len(collections["train"]) != 1500:
        raise ValueError("controlled train plan must contain 1500 identities")
    if len(collections["calibration"]) != 42:
        raise ValueError("controlled calibration plan must contain 42 identities")
    if len(collections["fresh_b"]) != 120:
        raise ValueError("Fresh B must contain 120 scenario identities")
    if summary["fresh_b_paired_run_count"] != 600:
        raise ValueError("Fresh B must freeze exactly 600 scenario-seed pairs")
    if summary["combined_train_snapshot_capacity_at_64_ticks"] < 150_000:
        raise ValueError("combined train capacity is below the preregistered target")

    formal = {key: value for key, value in collections.items() if key != "pilot_development"}
    family_sets = {
        split: {case["map_family_id"] for case in cases} for split, cases in formal.items()
    }
    corridor_sets = {
        split: {case["corridor_group_sha256"] for case in cases}
        for split, cases in formal.items()
    }
    route_sets = {
        split: {case["record_key"] for case in cases} for split, cases in formal.items()
    }
    block_sets = {
        split: {case["parameter_block_id"] for case in cases}
        for split, cases in formal.items()
    }
    seed_sets = {
        split: {seed for case in cases for seed in case["seeds"]}
        for split, cases in formal.items()
    }
    for name, values in (
        ("map_family", family_sets),
        ("corridor", corridor_sets),
        ("route", route_sets),
        ("scenario_parameter_block", block_sets),
        ("seed_namespace", seed_sets),
    ):
        ordered = list(values)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if values[left] & values[right]:
                    raise ValueError(f"{name} overlap between {left} and {right}")


def _attach_source_availability(
    case: Mapping[str, Any], availability: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(case)
    result["source_availability"] = dict(availability)
    result["runner_eligible"] = bool(
        result["runner_eligible"] and availability["speed_limit_complete"]
    )
    result["retention_role"] = (
        "executable" if result["runner_eligible"] else "source_ineligible_retained"
    )
    return result


def _retained_source_ineligible_cases(
    routes: Sequence[Mapping[str, Any]],
    source_availability: Mapping[str, Mapping[str, Any]],
    corridor_by_record: Mapping[str, str],
    *,
    split: str,
    seeds: Sequence[int],
) -> list[dict[str, Any]]:
    retained = []
    for index, route in enumerate(routes):
        key = str(route["record_key"])
        availability = source_availability[key]
        if availability["speed_limit_complete"]:
            continue
        case = build_controlled_scenario_case(
            route=route,
            corridor_group_sha256=corridor_by_record[key],
            split=split,
            family="blocked_lane_static_obstacle",
            tier="borderline",
            variant=100_000 + index,
            seeds=seeds,
        )
        retained.append(_attach_source_availability(case, availability))
    return retained


def _final_plan_summary(
    collections: Mapping[str, Sequence[Mapping[str, Any]]],
    routes_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
    source_availability: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    counts = {}
    for split, cases in collections.items():
        executable = [case for case in cases if case["runner_eligible"]]
        counts[split] = {
            "manifest_identity_count": len(cases),
            "executable_identity_count": len(executable),
            "source_ineligible_identity_count": len(cases) - len(executable),
            "inventory_route_count": len(routes_by_split[split]),
            "executable_route_count": len({case["record_key"] for case in executable}),
            "inventory_corridor_count": len(
                {case["corridor_group_sha256"] for case in cases}
            ),
            "executable_corridor_count": len(
                {case["corridor_group_sha256"] for case in executable}
            ),
            "scenario_seed_run_count": sum(len(case["seeds"]) for case in executable),
            "family_counts": {
                family: sum(case["family"] == family for case in executable)
                for family in SCENARIO_FAMILIES
            },
            "tier_counts": {
                tier: sum(case["tier"] == tier for case in executable)
                for tier in RISK_TIERS
            },
        }
    return {
        "split_counts": counts,
        "route_source_counts": {
            split: {
                "total": len(routes),
                "speed_limit_complete": sum(
                    bool(source_availability[str(route["record_key"])][
                        "speed_limit_complete"
                    ])
                    for route in routes
                ),
                "mapped_traffic_light": sum(
                    bool(source_availability[str(route["record_key"])][
                        "mapped_traffic_light"
                    ])
                    for route in routes
                ),
            }
            for split, routes in routes_by_split.items()
        },
        "v24_reused_train_snapshot_count": 67_796,
        "controlled_train_snapshot_capacity_at_64_ticks": (
            counts["train"]["executable_identity_count"] * 64
        ),
        "combined_train_snapshot_capacity_at_64_ticks": (
            67_796 + counts["train"]["executable_identity_count"] * 64
        ),
        "fresh_b_paired_run_count": counts["fresh_b"]["scenario_seed_run_count"],
        "fresh_b_independent_route_ceiling": counts["fresh_b"][
            "executable_route_count"
        ],
        "fresh_b_independent_corridor_ceiling": counts["fresh_b"][
            "executable_corridor_count"
        ],
        "independence_disclosure": (
            "Scenario identities and five paired seeds increase controlled-run "
            "coverage but are not counted as additional independent routes or corridors."
        ),
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "fresh_b_outcome_opened": False,
    }


def _validate_final_plan(
    collections: Mapping[str, Sequence[Mapping[str, Any]]], summary: Mapping[str, Any]
) -> None:
    counts = summary["split_counts"]
    if counts["train"]["executable_identity_count"] != 1500:
        raise ValueError("formal controlled train must freeze 1500 executable identities")
    if summary["combined_train_snapshot_capacity_at_64_ticks"] < 150_000:
        raise ValueError("formal combined train capacity is below 150k snapshots")
    if counts["fresh_b"]["executable_identity_count"] != 120:
        raise ValueError("Fresh B must freeze 120 executable scenario identities")
    if summary["fresh_b_paired_run_count"] != 600:
        raise ValueError("Fresh B must freeze 600 executable paired runs")
    for split, cases in collections.items():
        for case in cases:
            if case["split"] != split:
                raise ValueError("formal controlled split label mismatch")
            if case["runner_eligible"] and case["retention_role"] != "executable":
                raise ValueError("formal executable retention role mismatch")
            if not case["runner_eligible"] and case["retention_role"] != (
                "source_ineligible_retained"
            ):
                raise ValueError("formal source-ineligible route was not retained")
    route_sets = {
        split: {case["record_key"] for case in cases} for split, cases in collections.items()
    }
    seed_sets = {
        split: {seed for case in cases for seed in case["seeds"]}
        for split, cases in collections.items()
    }
    ordered = list(collections)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if route_sets[left] & route_sets[right]:
                raise ValueError("formal controlled route overlap")
            if seed_sets[left] & seed_sets[right]:
                raise ValueError("formal controlled seed overlap")


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )
