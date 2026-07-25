from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t


# Deliberately no import of diffusion_planner_v25_evaluation_v2 or its tables.
ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_review import (  # noqa: E402
    independent_validate_actual_native_receipt,
)


SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_review_artifact_v2"
EXECUTION_ROOT = "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
EXECUTION_REVIEW_ROOT = (
    "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
)
CORRECTED_EVALUATION_ROOT = (
    "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f"
)
CORRECTED_EVALUATION_REVIEW_ROOT = (
    "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459"
)
CONTINUATION_SHA = "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ARMS = ("candidate0", "static14d", "scene14d")
METHODS = ("static14d", "scene14d")
DT = 0.1
EPS = 1e-9
CLEARANCE = (0.0, 0.5, 1.0, 2.0)
TTC = (0.5, 1.0, 2.0, 3.0, 5.0)
CLOSING = (0.5, 1.0, 2.0, 5.0)
DRAC = (0.5, 1.0, 2.0, 3.0, 5.0)
SPEED = (0.0, 0.05, 0.1, 0.2)
ACCEL = (0.5, 1.0, 2.0, 3.0)
JERK = (0.5, 1.0, 2.0, 5.0)
DEADLINES = (50.0, 100.0, 200.0, 500.0, 1000.0)
TTC_HORIZON = 5.0
ROUTE_EPS = 1e-6
SUPERSEDED = {
    "contract_root_sha256": (
        "2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795"
    ),
    "contract_review_root_sha256": (
        "a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed"
    ),
    "materialization_root_sha256": (
        "0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d"
    ),
    "review_root_sha256": (
        "d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d"
    ),
    "preserved": True,
}


def review(
    *,
    output: Path,
    artifact: Path,
    artifact_root: str,
    execution: Path,
    execution_root: str,
    execution_review: Path,
    execution_review_root: str,
    corrected_evaluation: Path,
    corrected_evaluation_root: str,
    corrected_evaluation_review: Path,
    corrected_evaluation_review_root: str,
    continuation_ledger: Path,
    continuation_ledger_sha256: str,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
) -> str:
    expected_roots = (
        (execution_root, EXECUTION_ROOT, execution, "execution"),
        (
            execution_review_root,
            EXECUTION_REVIEW_ROOT,
            execution_review,
            "execution review",
        ),
        (
            corrected_evaluation_root,
            CORRECTED_EVALUATION_ROOT,
            corrected_evaluation,
            "corrected evaluation",
        ),
        (
            corrected_evaluation_review_root,
            CORRECTED_EVALUATION_REVIEW_ROOT,
            corrected_evaluation_review,
            "corrected evaluation review",
        ),
    )
    for actual, known, path, label in expected_roots:
        if actual != known:
            raise ValueError(f"independent Evaluation v2 {label} root drifted")
        verify_complete_seal(path, actual, label=f"Fresh B4 {label}")
    for path, root, label in (
        (contract, contract_root, "Evaluation v2 contract"),
        (contract_review, contract_review_root, "Evaluation v2 contract review"),
        (artifact, artifact_root, "Evaluation v2 materialization"),
    ):
        verify_complete_seal(path, root, label=label)
    if (
        continuation_ledger_sha256 != CONTINUATION_SHA
        or _file_sha(continuation_ledger) != CONTINUATION_SHA
    ):
        raise ValueError("independent Evaluation v2 continuation drifted")
    producer = _object(artifact / "report.json")
    result = _producer_shape(producer, contract_root, contract_review_root)
    corrected = _object(corrected_evaluation / "report.json")
    if (
        _sha_object(corrected["evaluation"])
        != result["legacy_benchmark_v1"]["evaluation_sha256"]
    ):
        raise ValueError("independent legacy evaluation value binding drifted")
    _assert_equal(
        corrected["evaluation"],
        result["legacy_benchmark_v1"]["evaluation"],
        "legacy evaluation",
    )
    endpoint_lookup = _endpoint_lookup(result)
    rows = _list(execution / "evaluation_rows.json")
    terminals = _list(execution / "run_terminals.json")
    run_dirs = sorted(path for path in (execution / "runs").iterdir() if path.is_dir())
    row_by_key = {(row.get("pair_key"), row.get("arm")): row for row in rows}
    if (
        len(rows) != 1500
        or len(terminals) != 1500
        or len(run_dirs) != 1500
        or len(row_by_key) != 1500
    ):
        raise ValueError("independent Evaluation v2 denominator drifted")
    geometry_cache: dict[tuple[str, str], dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    pairs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    candidate_equivalent = candidate_missing = candidate_not_applicable = 0
    for run_dir, terminal in zip(run_dirs, terminals, strict=True):
        if (
            _object(run_dir / "terminal.json") != terminal
            or terminal.get("status") != "complete"
        ):
            raise ValueError("independent Evaluation v2 terminal drifted")
        key = (terminal.get("unit_sha256"), terminal.get("evaluation_arm"))
        if key not in row_by_key:
            raise ValueError("independent Evaluation v2 row binding drifted")
        row = row_by_key[key]
        arm = row["arm"]
        config = _object(run_dir / "run_config.json")
        primary = _object(run_dir / "actual_native_receipt_raw.json")
        independent_validate_actual_native_receipt(
            primary,
            branch=(
                "candidate0_primary"
                if arm == "candidate0"
                else "static14d" if arm == "static14d" else "scene14d"
            ),
        )
        native = _object(run_dir / "native_receipt.json")
        projected = dict(native)
        projected.pop("fresh_decision_evidence_reference", None)
        projected.pop("fresh_decision_evidence_count", None)
        if (
            projected != primary
            or _sha_object(native) != terminal["native_receipt_sha256"]
        ):
            raise ValueError("independent Evaluation v2 native source drifted")
        supplementary = None
        equivalence = None
        if arm == "candidate0":
            supplementary = _object(
                run_dir / "candidate0_supplementary_actual_native_raw.json"
            )
            independent_validate_actual_native_receipt(
                supplementary, branch="candidate0_supplementary"
            )
            actors = config["signal_complete_runtime"]["case"]["actors"]
            equivalence = _candidate_equivalence_for_actor_inventory(
                primary, supplementary, actors
            )
            if equivalence is None:
                candidate_not_applicable += 1
            elif equivalence["equivalent"]:
                candidate_equivalent += 1
            else:
                candidate_missing += 1
        geometry_key = (config["map"]["sha256"], config["routes"][0]["sha256"])
        geometry = geometry_cache.get(geometry_key)
        if geometry is None:
            geometry = _geometry(config)
            geometry_cache[geometry_key] = geometry
        source_sha256 = _sha_object(primary)
        actual_rows = {name: endpoint_lookup[name][key] for name in endpoint_lookup}
        if any(
            endpoint_row["source_sha256"] != source_sha256
            for endpoint_row in actual_rows.values()
        ):
            raise ValueError("independent Evaluation v2 endpoint source SHA drifted")
        actual_endpoints = {
            name: endpoint_row["per_run_value"]
            for name, endpoint_row in actual_rows.items()
        }
        _validate_endpoints_literal(
            actual_endpoints,
            primary=primary,
            supplementary=supplementary,
            equivalence=equivalence,
            config=config,
            geometry=geometry,
        )
        summary = {
            "pair_key": row["pair_key"],
            "arm": arm,
            "inference_cluster_id": row["inference_cluster_id"],
            "benchmark_stratum": row["benchmark_stratum"],
            "scenario_family": row["scenario_family"],
            "source_class": row["source_class"],
            "source_receipt_sha256": source_sha256,
            "run_config_sha256": _sha_object(config),
            "candidate0_supplementary_equivalence": equivalence,
            "endpoints": actual_endpoints,
            "missing_evidence": {
                "collision_severity": "evidence_missing",
                "PET": "evidence_missing",
                "seat_occupant_vertical_roll_pitch": "evidence_missing",
                "production_latency_certification": "evidence_missing",
            },
        }
        summaries.append(summary)
        pairs[row["pair_key"]][arm] = summary
    if _sha_object(summaries) != result["run_summary_inventory_sha256"]:
        raise ValueError("independent Evaluation v2 run inventory SHA drifted")
    if len(pairs) != 500 or any(set(value) != set(ARMS) for value in pairs.values()):
        raise ValueError("independent Evaluation v2 paired inventory drifted")
    _review_aggregates(result, pairs)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_evaluation_v2_corrected_review",
        "artifact_binding": {
            "path": str(artifact.resolve()),
            "root_sha256": artifact_root,
        },
        "source_bindings": {
            "execution_root_sha256": execution_root,
            "execution_review_root_sha256": execution_review_root,
            "corrected_evaluation_root_sha256": corrected_evaluation_root,
            "corrected_evaluation_review_root_sha256": (
                corrected_evaluation_review_root
            ),
            "continuation_ledger_sha256": continuation_ledger_sha256,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
        },
        "superseded_evaluation_v2_diagnostic": dict(SUPERSEDED),
        "denominator": {
            "pair_count": 500,
            "arm_count": 1500,
            "tick_count": 96000,
            "receipt_count_independently_reconstructed": 1500,
            "cluster_count": 100,
        },
        "candidate0_supplementary_equivalence": {
            "equivalent_count": candidate_equivalent,
            "evidence_missing_count": candidate_missing,
            "not_applicable_no_dynamic_actor_count": candidate_not_applicable,
            "candidate0_run_count": 500,
        },
        "literal_oracle": {
            "producer_metric_module_imported": False,
            "producer_threshold_tables_imported": False,
            "geometry_reconstructed": True,
            "sample_accounting_reconstructed": "64_to_63_to_62_to_52_to_51",
            "legacy_equality_reconstructed": True,
            "cluster_statistics_reconstructed": True,
            "better_tie_worse_reconstructed": True,
            "direction_table_reconstructed_locally": True,
            "claim_invariance_reconstructed": True,
        },
        "legacy_values_mutated": False,
        "v2_claim_authorized": False,
        "execution_written": False,
        "corrected_evaluation_written": False,
        "scientific_or_continuation_cas_written": False,
        "fresh_execution_rerun": False,
        "corrected_evaluation_rerun": False,
        "reviewer_head": _git_head(),
    }
    return _write_atomic(output, report)


def _producer_shape(
    producer: dict[str, Any], contract_root: str, contract_review_root: str
) -> dict[str, Any]:
    if (
        producer.get("schema_version")
        != "camp_dp_v25_evaluation_v2_materialization_artifact_v2"
        or producer.get("status")
        != "sealed_read_only_evaluation_v2_corrected_materialization"
        or any(
            producer.get(name) is not False
            for name in (
                "execution_files_written",
                "corrected_evaluation_files_written",
                "fresh_execution_rerun",
                "arm_or_dp_k8_rerun",
                "corrected_evaluation_rerun",
                "scientific_or_continuation_cas_written",
                "legacy_values_mutated",
                "claim_authorized",
            )
        )
    ):
        raise ValueError("independent Evaluation v2 producer authority drifted")
    result = producer.get("evaluation_v2")
    if (
        type(result) is not dict
        or result.get("schema_version") != "camp_dp_v25_evaluation_v2_artifact_v2"
        or result.get("result_semantics") != "exploratory_posthoc_not_claim_authorizing"
        or result.get("contract_root_sha256") != contract_root
        or result.get("contract_review_root_sha256") != contract_review_root
        or result.get("bindings", {}).get("execution", {}).get("root_sha256")
        != EXECUTION_ROOT
        or result.get("bindings", {}).get("corrected_evaluation", {}).get("root_sha256")
        != CORRECTED_EVALUATION_ROOT
        or result.get("bindings", {}).get("continuation_ledger", {}).get("sha256")
        != CONTINUATION_SHA
        or result.get("claim_invariance", {}).get("v2_claim_authorized") is not False
    ):
        raise ValueError("independent Evaluation v2 result binding drifted")
    legacy = result.get("legacy_benchmark_v1")
    if (
        type(legacy) is not dict
        or legacy.get("source_root_sha256") != CORRECTED_EVALUATION_ROOT
        or legacy.get("values_mutated") is not False
        or legacy.get("values_recomputed") is not False
        or legacy.get("legacy_claim_changed") is not False
    ):
        raise ValueError("independent Evaluation v2 legacy namespace drifted")
    if producer.get("superseded_evaluation_v2_diagnostic") != SUPERSEDED:
        raise ValueError("independent superseded Evaluation v2 binding drifted")
    return result


def _endpoint_lookup(
    result: dict[str, Any]
) -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    vector = result.get("endpoint_vector")
    expected = {
        "collision",
        "dynamic_proximity",
        "road_containment",
        "certified_red_crossing",
        "speed",
        "route",
        "goal",
        "vehicle_body_planar_kinematic_proxy",
        "latency",
    }
    if type(vector) is not dict or set(vector) != expected:
        raise ValueError("independent Evaluation v2 endpoint vector drifted")
    lookup = {}
    for name in sorted(vector):
        endpoint = vector[name]
        if (
            type(endpoint) is not dict
            or endpoint.get("source_root_sha256") != EXECUTION_ROOT
            or type(endpoint.get("per_run_values")) is not list
            or len(endpoint["per_run_values"]) != 1500
        ):
            raise ValueError(f"independent Evaluation v2 endpoint drifted: {name}")
        rows = {}
        for row in endpoint["per_run_values"]:
            key = (row.get("pair_key"), row.get("arm"))
            if key in rows or row.get("source_sha256") is None:
                raise ValueError(
                    f"independent Evaluation v2 endpoint identity drifted: {name}"
                )
            rows[key] = row
        lookup[name] = rows
    return lookup


def _validate_endpoints_literal(
    actual: Mapping[str, dict[str, Any]],
    *,
    primary: dict[str, Any],
    supplementary: dict[str, Any] | None,
    equivalence: dict[str, Any] | None,
    config: dict[str, Any],
    geometry: dict[str, Any],
) -> None:
    ticks = primary["ticks"]
    case = config["signal_complete_runtime"]["case"]
    specs = {str(row["id"]): row for row in case["actors"]}
    spawn = config["spawn_config"]
    actor_ticks: Sequence[Mapping[str, Any]] | None
    if not specs:
        actor_ticks = []
    elif primary["arm"] == "dp":
        actor_ticks = (
            supplementary["ticks"]
            if supplementary is not None and equivalence["equivalent"]
            else None
        )
    else:
        actor_ticks = ticks
    expected_collision, expected_proximity = _collision_proximity(
        ticks, actor_ticks, specs, spawn
    )
    _assert_equal(expected_collision, actual["collision"], "collision")
    _assert_equal(expected_proximity, actual["dynamic_proximity"], "dynamic proximity")
    _assert_equal(
        _road(ticks, geometry["drivable_polygons"], spawn, config["map"]["sha256"]),
        actual["road_containment"],
        "road containment",
    )
    _assert_equal(
        _red(
            ticks,
            actor_ticks,
            float(spawn["ego_width"]),
            geometry["initial_heading_rad"],
        ),
        actual["certified_red_crossing"],
        "certified red crossing",
    )
    _assert_equal(_speed(ticks), actual["speed"], "speed")
    _assert_equal(
        _route(ticks, geometry, spawn, primary["native_result"]),
        actual["route"],
        "route",
    )
    _assert_equal(
        _goal(ticks, geometry, spawn, primary["native_result"]),
        actual["goal"],
        "goal",
    )
    _assert_equal(
        _body(ticks), actual["vehicle_body_planar_kinematic_proxy"], "body proxy"
    )
    _assert_equal(_latency(ticks), actual["latency"], "latency")


def _candidate_equivalence(
    primary: dict[str, Any], supplementary: dict[str, Any]
) -> dict[str, Any]:
    headers = (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    )
    if any(primary.get(name) != supplementary.get(name) for name in headers):
        return {"equivalent": False, "reason": "header_drift"}
    for index, (left, right) in enumerate(
        zip(primary["ticks"], supplementary["ticks"], strict=True)
    ):
        if any(
            left.get(name) != right.get(name)
            for name in (
                "tick_index",
                "input_sha256",
                "default_output_sha256",
                "selected_trajectory_sha256",
                "selected_index",
            )
        ):
            return {"equivalent": False, "reason": f"action_binding_drift_at_{index}"}
        for name in (
            "position_xy",
            "speed_mps",
            "ego_heading_rad",
            "route_heading_rad",
            "route_progress_m",
            "signal_phase_at_interval_start",
            "certified_signal_stop_lines",
            "speed_limit_mps",
        ):
            if left["safety"].get(name) != right["safety"].get(name):
                return {
                    "equivalent": False,
                    "reason": f"ego_or_source_drift_{name}_at_{index}",
                }
        controlled = right.get("controlled_scene")
        if (
            type(controlled) is not dict
            or controlled.get("tick_index") != index
            or controlled.get("outcome_fields_consumed") != []
            or controlled.get("candidate_tensor_consumed") is not False
            or controlled.get("selected_trajectory_consumed") is not False
        ):
            return {
                "equivalent": False,
                "reason": f"controlled_source_drift_at_{index}",
            }
    return {
        "equivalent": True,
        "reason": None,
        "tick_count": 64,
        "proof_fields": [
            *headers,
            "tick_index",
            "input_sha256",
            "default_output_sha256",
            "selected_trajectory_sha256",
            "selected_index",
            "safety.position_xy",
            "safety.speed_mps",
            "safety.ego_heading_rad",
            "safety.route_heading_rad",
            "safety.route_progress_m",
            "safety.signal_phase_at_interval_start",
            "safety.certified_signal_stop_lines",
            "safety.speed_limit_mps",
            "controlled_scene.source_nonconsumption",
        ],
    }


def _candidate_equivalence_for_actor_inventory(
    primary: dict[str, Any],
    supplementary: dict[str, Any],
    actors: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    if not actors:
        return None
    return _candidate_equivalence(primary, supplementary)


def _obb(
    position: Any, heading: float, length: float, width: float, wheelbase: float | None
) -> np.ndarray:
    xy = np.asarray(position, dtype=np.float64)
    rear = (length - wheelbase) / 2.0 if wheelbase is not None else length / 2.0
    lo, hi = -rear, length - rear if wheelbase is not None else length / 2.0
    local = np.asarray(
        [[lo, -width / 2], [hi, -width / 2], [hi, width / 2], [lo, width / 2]],
        dtype=np.float64,
    )
    c, s = math.cos(float(heading)), math.sin(float(heading))
    return local @ np.asarray([[c, s], [-s, c]]) + xy


def _sat_ttc(
    a: np.ndarray, b: np.ndarray, va: np.ndarray, vb: np.ndarray
) -> float | None:
    if _polygons_intersect(a, b):
        return 0.0
    relative = vb - va
    relative_position = b.mean(axis=0) - a.mean(axis=0)
    if float(np.dot(relative_position, relative)) >= 0.0:
        return None
    entry, exit_time = 0.0, math.inf
    for polygon in (a, b):
        for index in range(4):
            edge = polygon[(index + 1) % 4] - polygon[index]
            axis = np.asarray([-edge[1], edge[0]], dtype=np.float64)
            axis /= np.linalg.norm(axis)
            amin, amax = (a @ axis).min(), (a @ axis).max()
            bmin, bmax = (b @ axis).min(), (b @ axis).max()
            speed = float(np.dot(relative, axis))
            if abs(speed) <= EPS:
                if amax < bmin or bmax < amin:
                    return None
                continue
            values = ((amin - bmax) / speed, (amax - bmin) / speed)
            entry, exit_time = max(entry, min(values)), min(exit_time, max(values))
            if entry - exit_time > EPS:
                return None
    if exit_time < -EPS:
        return None
    result = float(max(0.0, entry))
    return result if result <= TTC_HORIZON else None


def _collision_proximity(
    ticks: Sequence[dict[str, Any]],
    actor_ticks: Sequence[Mapping[str, Any]] | None,
    specs: Mapping[str, Mapping[str, Any]],
    spawn: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if actor_ticks is None:
        missing = {
            "status": "evidence_missing",
            "reason": "candidate0_supplementary_primary_equivalence_not_proven",
        }
        return dict(missing), dict(missing)
    collision_mask = []
    clearance_values = []
    ttc_values = []
    closing_values = []
    drac_values = []
    opportunities = 0
    for index, tick in enumerate(ticks):
        safety = tick["safety"]
        position = np.asarray(safety["position_xy"], dtype=np.float64)
        heading = float(safety["ego_heading_rad"])
        ego_v = float(safety["speed_mps"]) * np.asarray(
            [math.cos(heading), math.sin(heading)]
        )
        ego = _obb(
            position,
            heading,
            float(spawn["ego_length"]),
            float(spawn["ego_width"]),
            float(spawn["ego_wheelbase"]),
        )
        actors = (
            []
            if actor_ticks == []
            else actor_ticks[index]["controlled_scene"]["actors"]
        )
        rows = []
        for actor in actors:
            spec = specs[str(actor["id"])]
            other = _obb(
                actor["position_xy"],
                float(actor["heading_rad"]),
                float(spec["length_m"]),
                float(spec["width_m"]),
                float(spec["wheelbase_m"]),
            )
            collision = _polygons_intersect(ego, other)
            clearance = _polygon_distance(ego, other)
            r = np.asarray(actor["position_xy"], dtype=np.float64) - position
            vr = np.asarray(actor["velocity_xy_mps"], dtype=np.float64) - ego_v
            closing = max(
                0.0, -float(np.dot(r, vr)) / max(float(np.linalg.norm(r)), EPS)
            )
            drac = (
                closing * closing / (2 * max(clearance, EPS))
                if closing > 0 and clearance > 0
                else None
            )
            rows.append(
                (
                    collision,
                    clearance,
                    _sat_ttc(ego, other, ego_v, np.asarray(actor["velocity_xy_mps"])),
                    closing,
                    drac,
                )
            )
        opportunities += len(rows)
        collision_mask.append(any(row[0] for row in rows))
        clearance_values.append(min((row[1] for row in rows), default=math.inf))
        finite_ttc = [row[2] for row in rows if row[2] is not None and not row[0]]
        ttc_values.append(min(finite_ttc) if finite_ttc else math.inf)
        closing_values.append(max((row[3] for row in rows), default=0.0))
        finite_drac = [row[4] for row in rows if row[4] is not None]
        drac_values.append(max(finite_drac) if finite_drac else 0.0)
    clearance_array = np.asarray(clearance_values)
    finite_clearance = clearance_array[np.isfinite(clearance_array)]
    ttc_array = np.asarray(ttc_values)
    closing_array = np.asarray(closing_values)
    drac_array = np.asarray(drac_values)
    collision = {
        "status": "benchmark_only",
        "collision_any": any(collision_mask),
        "episode_count": _episodes(collision_mask),
        "duration_s": float(sum(collision_mask) * DT),
        "collision_severity": "evidence_missing",
        "kinematic_relative_speed_proxy_is_severity": False,
    }
    proximity = {
        "status": "benchmark_only",
        "actor_tick_opportunity_count": opportunities,
        "min_clearance_m": (
            float(finite_clearance.min()) if finite_clearance.size else None
        ),
        "min_finite_geometry_ttc_s": (
            float(ttc_array[np.isfinite(ttc_array)].min())
            if np.isfinite(ttc_array).any()
            else None
        ),
        "max_closing_mps": float(closing_array.max()),
        "max_drac_mps2": float(drac_array.max()),
        "clearance_grid": _grid(clearance_array, CLEARANCE, "le"),
        "geometry_ttc_grid": _grid(ttc_array, TTC, "le"),
        "closing_grid": _grid(closing_array, CLOSING, "ge"),
        "drac_grid": _grid(drac_array, DRAC, "ge"),
        "stationary_proximity_is_dynamic_risk": False,
        "point_cv_proxy_used_as_geometry_ttc": False,
        "geometry_ttc_approach_condition": "centroid dot(r,v_rel)<0",
        "geometry_ttc_prediction_horizon_s": TTC_HORIZON,
        "geometry_ttc_horizon_classification": (
            "project_descriptive_not_industrial_gate"
        ),
        "ego_velocity_source": (
            "same_tick_scalar_speed_times_heading_kinematic_reconstruction"
        ),
        "PET": "evidence_missing",
    }
    return collision, proximity


def _road(
    ticks: Sequence[dict[str, Any]],
    drivable: Sequence[np.ndarray],
    spawn: Mapping[str, Any],
    map_sha: str,
) -> dict[str, Any]:
    values = []
    for tick in ticks:
        safety = tick["safety"]
        polygon = _obb(
            safety["position_xy"],
            float(safety["ego_heading_rad"]),
            float(spawn["ego_length"]),
            float(spawn["ego_width"]),
            float(spawn["ego_wheelbase"]),
        )
        values.append(_outside_fraction(polygon, drivable))
    array = np.asarray(values)
    mask = array > EPS
    return {
        "status": "benchmark_only",
        "offroad_any": bool(mask.any()),
        "duration_s": float(mask.sum() * DT),
        "episode_count": _episodes(mask.tolist()),
        "max_outside_fraction": float(array.max()),
        "geom_eps": EPS,
        "five_point_proxy_used": False,
        "signed_boundary_clearance_or_penetration": {
            "status": "evidence_missing",
            "reason": (
                "root_bound_drivable_geometry_is_an_unordered_overlapping_"
                "polygon_inventory_without_union_boundary_topology"
            ),
            "units": "m",
        },
        "geometry_source_sha256": map_sha,
    }


def _red(
    ticks: Sequence[dict[str, Any]],
    actor_ticks: Sequence[Mapping[str, Any]] | None,
    width: float,
    initial_heading: float,
) -> dict[str, Any]:
    opportunities = intervals = crossings = legacy = ambiguous = 0
    speeds = []
    seen: set[str] = set()
    for index, tick in enumerate(ticks):
        safety = tick["safety"]
        lines = safety["certified_signal_stop_lines"]
        if safety["signal_phase_at_interval_start"] != "red" or not lines:
            continue
        intervals += 1
        identities = [_sha_object(line) for line in lines]
        if actor_ticks not in (None, []):
            source = actor_ticks[index]["controlled_scene"]["signal"]["source_receipt"]
            if type(source.get("certified_stop_line_id")) is str:
                identities = [source["certified_stop_line_id"]]
        for identity in identities:
            if identity not in seen:
                opportunities += 1
                seen.add(identity)
        heading0 = (
            initial_heading
            if index == 0
            else float(ticks[index - 1]["safety"]["ego_heading_rad"])
        )
        heading1 = float(safety["ego_heading_rad"])
        start = _front(safety["front_center_prev_xy"], heading0, width)
        end = _front(safety["front_center_xy"], heading1, width)
        results = [
            _cross(start, end, np.asarray(line, dtype=np.float64)) for line in lines
        ]
        if (
            any(row[0] == "ambiguous" for row in results)
            or sum(row[1] for row in results) > 1
        ):
            ambiguous += 1
            continue
        found = [row for row in results if row[1]]
        if found:
            alpha = found[0][2]
            speed = float(safety["pre_decision_speed_mps"]) + alpha * (
                float(safety["speed_mps"]) - float(safety["pre_decision_speed_mps"])
            )
            crossings += 1
            speeds.append(speed)
            legacy += int(speed > 0.5)
    if ambiguous:
        return {
            "status": "ambiguous_evidence_missing",
            "maps_to_status": "evidence_missing",
            "red_opportunity_count": opportunities,
            "red_phase_interval_count": intervals,
            "ambiguous_interval_count": ambiguous,
            "unthresholded_crossing_count": None,
        }
    return {
        "status": "benchmark_only",
        "red_opportunity_count": opportunities,
        "red_phase_interval_count": intervals,
        "unthresholded_crossing_count": crossings,
        "unthresholded_crossing_any": crossings > 0,
        "crossing_speed_mps": speeds,
        "legacy_gt_0_5mps_crossing_count": legacy,
        "future_phase_consumed": False,
    }


def _speed(ticks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if any(tick["safety"]["speed_limit_mps"] is None for tick in ticks):
        missing = sum(tick["safety"]["speed_limit_mps"] is None for tick in ticks)
        return {
            "status": "evidence_missing",
            "missing_interval_count": missing,
            "required_interval_count": 64,
        }
    values = np.asarray(
        [
            max(
                0.0,
                float(tick["safety"]["speed_mps"])
                - float(tick["safety"]["speed_limit_mps"]),
            )
            for tick in ticks
        ]
    )
    positives = values[values > 0]
    return {
        "status": "benchmark_only",
        "max_excess_mps": float(values.max()),
        "mean_positive_excess_mps": float(positives.mean()) if positives.size else 0.0,
        "tolerance_grid": {
            _key(tolerance): {
                "duration_s": float(np.count_nonzero(values > tolerance) * DT),
                "magnitude_duration_m": float(
                    np.maximum(0, values - tolerance).sum() * DT
                ),
            }
            for tolerance in SPEED
        },
    }


def _body(ticks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    positions = np.asarray(
        [tick["safety"]["position_xy"] for tick in ticks], dtype=np.float64
    )
    headings = np.asarray(
        [tick["safety"]["ego_heading_rad"] for tick in ticks], dtype=np.float64
    )
    velocity = np.diff(positions, axis=0) / DT
    acceleration = np.diff(velocity, axis=0) / DT
    c, s = np.cos(headings[1:-1]), np.sin(headings[1:-1])
    longitudinal = acceleration[:, 0] * c + acceleration[:, 1] * s
    lateral = -acceleration[:, 0] * s + acceleration[:, 1] * c
    kernel = np.asarray([1 / 11] * 11)
    long_f = np.convolve(longitudinal, kernel, mode="valid")
    lat_f = np.convolve(lateral, kernel, mode="valid")
    long_j = np.diff(long_f) / DT
    lat_j = np.diff(lat_f) / DT
    return {
        "status": "benchmark_only",
        "name": "vehicle_body_planar_kinematic_proxy",
        "sample_accounting": {
            "position_samples": 64,
            "interval_velocity_samples": 63,
            "raw_acceleration_samples": 62,
            "filtered_acceleration_samples": 52,
            "filtered_jerk_samples": 51,
            "padding_used": False,
        },
        "filtered_acceleration": {
            "longitudinal": _signed(long_f),
            "lateral": _signed(lat_f),
            "longitudinal_deceleration": _unsigned(np.maximum(0, -long_f)),
            "duration_abs_gt_s": {
                _key(threshold): {
                    "longitudinal": float(
                        np.count_nonzero(np.abs(long_f) > threshold) * DT
                    ),
                    "lateral": float(np.count_nonzero(np.abs(lat_f) > threshold) * DT),
                }
                for threshold in ACCEL
            },
            "signed_deceleration_duration_lt_s": {
                _key(-threshold): float(np.count_nonzero(long_f < -threshold) * DT)
                for threshold in ACCEL
            },
        },
        "filtered_jerk": {
            "longitudinal": _jerk(long_j),
            "lateral": _jerk(lat_j),
            "duration_abs_gt_s": {
                _key(threshold): {
                    "longitudinal": float(
                        np.count_nonzero(np.abs(long_j) > threshold) * DT
                    ),
                    "lateral": float(np.count_nonzero(np.abs(lat_j) > threshold) * DT),
                }
                for threshold in JERK
            },
        },
        "not_modeled": [
            "seat_response",
            "occupant_response",
            "vertical_acceleration",
            "roll",
            "pitch",
            "ISO_2631",
            "SAE_J2834",
        ],
    }


def _latency(ticks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stages = sorted({stage for tick in ticks for stage in tick["latency_ms"]})
    stage_values = {}
    for stage in stages:
        values = [
            float(tick["latency_ms"][stage])
            for tick in ticks
            if stage in tick["latency_ms"]
        ]
        stage_values[stage] = (
            _distribution(values)
            if len(values) == 64
            else {
                "status": "evidence_missing",
                "available_count": len(values),
                "required_count": 64,
            }
        )
    total = np.asarray(
        [tick["latency_ms"]["total_planning"] for tick in ticks], dtype=np.float64
    )
    return {
        "status": "benchmark_only",
        "stages": stage_values,
        "total": _distribution(total),
        "deadline_grid": {
            _key(deadline): {
                "exceedance_rate": float(np.count_nonzero(total > deadline) / 64),
                "max_exceedance_ms": float(np.maximum(0, total - deadline).max()),
                "label": (
                    "hypothetical_10Hz_budget"
                    if deadline == 100
                    else "project_sensitivity"
                ),
            }
            for deadline in DEADLINES
        },
        "production_deadline_certification": "evidence_missing",
    }


def _route(
    ticks: Sequence[dict[str, Any]],
    geometry: dict[str, Any],
    spawn: Mapping[str, Any],
    native_result: Mapping[str, Any],
) -> dict[str, Any]:
    positions = np.asarray(
        [tick["safety"]["position_xy"] for tick in ticks], dtype=np.float64
    )
    speeds = np.asarray(
        [tick["safety"]["speed_mps"] for tick in ticks], dtype=np.float64
    )
    segments = geometry["segments"]
    first = _candidates(positions[0], segments)
    minimum = min(row[2] for row in first)
    eligible = [row for row in first if abs(row[2] - minimum) <= EPS]
    if len(eligible) != 1:
        return {
            "status": "ambiguous_evidence_missing",
            "maps_to_status": "evidence_missing",
            "reason": "multiple_equal_initial_route_projections",
        }
    states = {eligible[0][0]: (eligible[0][2], (eligible[0][0],), [eligible[0][1]])}
    for tick in range(1, 64):
        next_states = {}
        bound = max(
            0.5 * (speeds[tick - 1] + speeds[tick]) * DT,
            float(np.linalg.norm(positions[tick] - positions[tick - 1])),
        ) + ROUTE_EPS
        candidates = _candidates(positions[tick], segments)
        minimum_lateral = min(row[2] for row in candidates)
        candidates = [
            row for row in candidates if row[2] - minimum_lateral <= ROUTE_EPS
        ]
        for index, s_value, distance in candidates:
            options = []
            for previous_index, previous in states.items():
                allowed = (
                    index == previous_index
                    or index in segments[previous_index]["next_indices"]
                    or previous_index in segments[index]["next_indices"]
                )
                delta = s_value - previous[2][-1]
                if allowed and -bound <= delta <= bound:
                    options.append(
                        (
                            previous[0] + distance,
                            (*previous[1], index),
                            [*previous[2], s_value],
                        )
                    )
            if options:
                options.sort(key=lambda row: (row[0], row[1]))
                if len(options) > 1 and abs(options[0][0] - options[1][0]) <= EPS:
                    return {
                        "status": "ambiguous_evidence_missing",
                        "maps_to_status": "evidence_missing",
                        "reason": "multiple_equal_cost_route_paths",
                    }
                next_states[index] = options[0]
        if not next_states:
            return {
                "status": "ambiguous_evidence_missing",
                "maps_to_status": "evidence_missing",
                "reason": "no_unique_kinematically_feasible_route_path",
            }
        states = next_states
    final = sorted(states.values(), key=lambda row: (row[0], row[1]))
    if len(final) > 1 and abs(final[0][0] - final[1][0]) <= EPS:
        return {
            "status": "ambiguous_evidence_missing",
            "maps_to_status": "evidence_missing",
            "reason": "multiple_equal_cost_route_paths",
        }
    s_values = np.asarray(final[0][2])
    backwards = np.maximum(0, -np.diff(s_values))
    route_length = segments[-1]["arc_end_m"]
    return {
        "status": "benchmark_only",
        "substatus": "computed",
        "s_t_m": s_values.tolist(),
        "final_nearest_route_polyline_projection_m": float(s_values[-1]),
        "net_m": float(s_values[-1] - s_values[0]),
        "max_forward_m": float(s_values.max() - s_values[0]),
        "backtracking_duration_s": float(np.count_nonzero(backwards > 0) * DT),
        "backtracking_distance_m": float(backwards.sum()),
        "distance_traveled_m": float(
            np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()
        ),
        "route_length_m": float(route_length),
        "completion_fraction": float(
            np.clip((s_values.max() - s_values[0]) / route_length, 0, 1)
        ),
        "travel_bound": (
            "max(trapezoidal_speed_distance,sealed_position_displacement)+1e-6m"
        ),
        "geometry_source_sha256": geometry["route_sha"],
    }


def _goal(
    ticks: Sequence[dict[str, Any]],
    geometry: dict[str, Any],
    spawn: Mapping[str, Any],
    native_result: Mapping[str, Any],
) -> dict[str, Any]:
    positions = np.asarray(
        [tick["safety"]["position_xy"] for tick in ticks], dtype=np.float64
    )
    headings = np.asarray(
        [tick["safety"]["ego_heading_rad"] for tick in ticks], dtype=np.float64
    )
    goal = np.asarray(geometry["goal_pose"], dtype=np.float64)
    distances = np.linalg.norm(positions - goal[:2], axis=1)
    tolerance = float(spawn["goal_tolerance_m"])
    pass_window = float(spawn["goal_pass_window_m"])
    reached = bool(np.any(distances <= tolerance))
    passed = any(
        float(np.dot(goal[:2] - position, [math.cos(heading), math.sin(heading)]))
        < 0.0
        and float(distance) <= pass_window
        for position, heading, distance in zip(
            positions, headings, distances, strict=True
        )
    )
    return {
        "status": "benchmark_only",
        "goal_pose": goal.tolist(),
        "goal_tolerance_m": tolerance,
        "goal_pass_window_m": pass_window,
        "minimum_goal_distance_m": float(distances.min()),
        "goal_reached_by_literal_tolerance": reached,
        "goal_passed_by_literal_heading_and_window": passed,
        "goal_pass_uses_same_tick_distance_and_heading": True,
        "historical_minimum_coupled_to_later_heading_used": False,
        "reconstructed_goal_reached_or_passed": reached or passed,
        "native_goal_reached": native_result["goal_reached"],
        "native_reason": native_result["reason"],
        "native_literal_semantics_bound": True,
    }


def _geometry(config: dict[str, Any]) -> dict[str, Any]:
    if config["fixed_dp"]["head"] != FIXED_DP:
        raise ValueError("independent fixed-DP geometry authority drifted")
    dp = Path(config["fixed_dp"]["repo"]).resolve()
    for path in (dp, dp / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    map_path = _asset(config["map"])
    route_path = _asset(config["routes"][0])
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(str(map_path))
    route = Route.load(route_path)
    polygons = []
    for lanelet_id in sorted(builder._cache):
        lane = builder._cache[lanelet_id]
        left = np.asarray(lane.raw_left, dtype=np.float64)[:, :2]
        right = np.asarray(lane.raw_right, dtype=np.float64)[:, :2]
        polygons.append(_ccw(np.concatenate([left, right[::-1]], axis=0)))
    parts = []
    for lanelet_id in route.route_lanelet_ids:
        points = np.asarray(
            builder._cache[lanelet_id].raw_centerline, dtype=np.float64
        )[:, :2]
        if parts and np.linalg.norm(parts[-1][-1] - points[0]) <= 1e-6:
            points = points[1:]
        if points.size:
            parts.append(points)
    centerline = np.concatenate(parts)
    segments = []
    arc = 0.0
    for start, end in zip(centerline[:-1], centerline[1:]):
        length = float(np.linalg.norm(end - start))
        if length <= EPS:
            continue
        index = len(segments)
        segments.append(
            {
                "index": index,
                "start": start,
                "end": end,
                "arc_start_m": arc,
                "arc_end_m": arc + length,
                "next_indices": [index + 1],
            }
        )
        arc += length
    segments[-1]["next_indices"] = []
    return {
        "drivable_polygons": polygons,
        "segments": segments,
        "initial_heading_rad": float(route.start_pose[2]),
        "goal_pose": np.asarray(route.goal_pose, dtype=np.float64).tolist(),
        "route_sha": config["routes"][0]["sha256"],
    }


def _review_aggregates(
    result: dict[str, Any], pairs: Mapping[str, Mapping[str, dict[str, Any]]]
) -> None:
    ordered = [pairs[key] for key in sorted(pairs)]
    for name, endpoint in result["endpoint_vector"].items():
        all_available = all(
            pair[arm]["endpoints"][name]["status"] in {"computed", "benchmark_only"}
            for pair in ordered
            for arm in ARMS
        )
        aggregate = endpoint["aggregate"]
        if not all_available:
            if aggregate != {
                "status": "evidence_missing",
                "paired_inference": "cancelled_missing_full_paired_denominator",
                "complete_case_shrinkage_used": False,
            }:
                raise ValueError(
                    f"independent missing-denominator aggregate drifted: {name}"
                )
            continue
        paths = sorted(
            set.intersection(
                *[
                    set(_numeric_paths(pair[arm]["endpoints"][name]))
                    for pair in ordered
                    for arm in ARMS
                ]
            )
        )
        if aggregate["descriptive_scalar_paths"] != paths:
            raise ValueError(f"independent scalar path drifted: {name}")
        for arm in ARMS:
            expected_means = {
                path: float(
                    np.mean(
                        [_path(pair[arm]["endpoints"][name], path) for pair in ordered]
                    )
                )
                for path in paths
            }
            _assert_equal(
                expected_means, aggregate["arm_means"][arm], f"{name} arm means"
            )
        for method in METHODS:
            clusters = [pair[method]["inference_cluster_id"] for pair in ordered]
            for path in paths:
                deltas = [
                    _path(pair[method]["endpoints"][name], path)
                    - _path(pair["candidate0"]["endpoints"][name], path)
                    for pair in ordered
                ]
                _assert_equal(
                    _cluster(deltas, clusters, _direction(name, path)),
                    aggregate["paired_cluster_summaries"][method][path],
                    f"{name} {method} {path}",
                )


def _cluster(
    deltas: Sequence[float], clusters: Sequence[str], direction: str
) -> dict[str, Any]:
    groups: dict[str, list[float]] = defaultdict(list)
    for value, cluster in zip(deltas, clusters, strict=True):
        groups[cluster].append(float(value))
    if len(groups) != 100 or any(len(rows) != 5 for rows in groups.values()):
        raise ValueError("independent cluster denominator drifted")
    values = np.asarray(deltas)
    means = np.asarray([np.mean(groups[key]) for key in sorted(groups)])
    mean = float(means.mean())
    se = float(means.std(ddof=1) / math.sqrt(100))
    critical = float(student_t.ppf(0.975, df=99))
    if direction not in {"lower", "higher", "descriptive_unclassified"}:
        raise ValueError("independent scalar direction drifted")
    result: dict[str, Any] = {
        "status": "benchmark_only",
        "estimator": "equal_mass_cluster_mean_student_t",
        "pair_count": 500,
        "cluster_count": 100,
        "mean_delta": mean,
        "ci95": [mean - critical * se, mean + critical * se],
        "between_variance": float(means.var(ddof=1)),
        "total_variance": float(values.var(ddof=1)),
        "within_variance": float(
            np.mean([np.var(groups[key], ddof=1) for key in sorted(groups)])
        ),
        "variance_fields_are_not_better_tie_worse": True,
        "direction": direction,
        "claim_authorized": False,
    }
    if direction == "descriptive_unclassified":
        result["better_tie_worse"] = {
            "status": "descriptive_unclassified",
            "reason": "no_outcome_independent_natural_direction",
        }
    else:
        better = int(
            np.count_nonzero(values < 0.0 if direction == "lower" else values > 0.0)
        )
        tie = int(np.count_nonzero(values == 0.0))
        worse = int(values.size - better - tie)
        result["better_tie_worse"] = {
            "status": "benchmark_only",
            "direction": direction,
            "tie_rule": "exact_zero_delta",
            "better": better,
            "tie": tie,
            "worse": worse,
            "sum": better + tie + worse,
        }
    return result


def _direction(endpoint: str, path: str) -> str:
    unclassified = (
        "opportunity_count",
        "red_phase_interval_count",
        "sample",
        "padding_used",
        "geom_eps",
        "prediction_horizon",
        "route_length_m",
        "goal_tolerance_m",
        "goal_pass_window_m",
        "native_goal_reached",
        "native_literal_semantics_bound",
        "future_phase_consumed",
        "five_point_proxy_used",
        "stationary_proximity_is_dynamic_risk",
        "point_cv_proxy_used_as_geometry_ttc",
        "geometry_ttc_approach_required",
        "historical_minimum_coupled_to_later_heading_used",
        "goal_pass_uses_same_tick_distance_and_heading",
        "is_severity",
    )
    if any(token in path for token in unclassified):
        return "descriptive_unclassified"
    if endpoint == "dynamic_proximity" and (
        "min_clearance_m" in path or "min_finite_geometry_ttc_s" in path
    ):
        return "higher"
    if endpoint == "route":
        return "lower" if "backtracking" in path else "higher"
    if endpoint == "goal":
        if "minimum_goal_distance_m" in path:
            return "lower"
        if any(
            token in path
            for token in (
                "goal_reached_by_literal_tolerance",
                "goal_passed_by_literal_heading_and_window",
                "reconstructed_goal_reached_or_passed",
            )
        ):
            return "higher"
        return "descriptive_unclassified"
    if endpoint == "vehicle_body_planar_kinematic_proxy" and any(
        token in path.rsplit("/", 1)[-1]
        for token in ("signed_mean", "min", "max")
    ):
        return "descriptive_unclassified"
    if endpoint in {
        "collision",
        "dynamic_proximity",
        "road_containment",
        "certified_red_crossing",
        "speed",
        "vehicle_body_planar_kinematic_proxy",
        "latency",
    }:
        return "lower"
    return "descriptive_unclassified"


def _numeric_paths(value: Any, prefix: str = "") -> list[str]:
    excluded = {
        "status",
        "substatus",
        "maps_to_status",
        "reason",
        "name",
        "not_modeled",
        "crossing_speed_mps",
        "s_t_m",
        "goal_pose",
        "geometry_source_sha256",
    }
    result = []
    if type(value) is dict:
        for name in sorted(value):
            if name in excluded:
                continue
            token = str(name).replace("~", "~0").replace("/", "~1")
            path = f"{prefix}/{token}"
            result.extend(_numeric_paths(value[name], path))
    elif type(value) in {int, float, bool} and math.isfinite(float(value)):
        result.append(prefix)
    return result


def _path(value: Mapping[str, Any], path: str) -> float:
    current: Any = value
    if not path.startswith("/"):
        raise ValueError(f"independent scalar path is not JSON Pointer: {path}")
    for token in path.split("/")[1:]:
        name = token.replace("~1", "/").replace("~0", "~")
        current = current[name]
    return float(current)


def _candidates(
    point: np.ndarray, segments: Sequence[Mapping[str, Any]]
) -> list[tuple[int, float, float]]:
    result = []
    for segment in segments:
        delta = segment["end"] - segment["start"]
        ratio = float(
            np.clip(
                np.dot(point - segment["start"], delta) / np.dot(delta, delta), 0, 1
            )
        )
        projected = segment["start"] + ratio * delta
        result.append(
            (
                segment["index"],
                float(
                    segment["arc_start_m"]
                    + ratio * (segment["arc_end_m"] - segment["arc_start_m"])
                ),
                float(np.linalg.norm(point - projected)),
            )
        )
    return result


def _front(center: Any, heading: float, width: float) -> np.ndarray:
    center_value = np.asarray(center, dtype=np.float64)
    normal = np.asarray([-math.sin(heading), math.cos(heading)])
    return np.asarray(
        [center_value - width * normal / 2, center_value + width * normal / 2]
    )


def _cross(
    start: np.ndarray, end: np.ndarray, stop: np.ndarray
) -> tuple[str, bool, float | None]:
    swept = np.asarray([start[0], start[1], end[1], end[0]], dtype=np.float64)
    boundary_intersection = (
        _segments_intersect(start[0], start[1], stop[0], stop[1])
        or _segments_intersect(end[0], end[1], stop[0], stop[1])
        or _segments_intersect(start[0], end[0], stop[0], stop[1])
        or _segments_intersect(start[1], end[1], stop[0], stop[1])
    )
    if _self_intersects(swept) or abs(_signed_area(swept)) <= EPS:
        if not boundary_intersection:
            return ("computed", False, None)
        return ("ambiguous", False, None)
    if not _segment_intersects_polygon(stop[0], stop[1], _ccw(swept)):
        return ("computed", False, None)
    alphas = []
    for index in range(2):
        value = _intersection_alpha(start[index], end[index], stop[0], stop[1])
        if value is not None:
            alphas.append(value)
    unique = []
    for value in sorted(alphas):
        if not unique or abs(value - unique[-1]) > 1e-7:
            unique.append(value)
    if len(unique) != 1:
        return ("ambiguous", False, None)
    return ("computed", True, unique[0])


def _intersection_alpha(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
) -> float | None:
    r, s = b - a, d - c
    denominator = float(r[0] * s[1] - r[1] * s[0])
    if abs(denominator) <= EPS:
        return None
    delta = c - a
    t = float((delta[0] * s[1] - delta[1] * s[0]) / denominator)
    u = float((delta[0] * r[1] - delta[1] * r[0]) / denominator)
    return (
        float(np.clip(t, 0, 1))
        if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS
        else None
    )


def _cross2(first: np.ndarray, second: np.ndarray) -> float:
    return float(first[0] * second[1] - first[1] * second[0])


def _signed_area(vertices: np.ndarray) -> float:
    shifted = np.roll(vertices, -1, axis=0)
    return float(
        0.5 * np.sum(vertices[:, 0] * shifted[:, 1] - vertices[:, 1] * shifted[:, 0])
    )


def _area(vertices: np.ndarray) -> float:
    return abs(_signed_area(vertices))


def _ccw(vertices: np.ndarray) -> np.ndarray:
    result = np.asarray(vertices, dtype=np.float64)
    return result if _signed_area(result) >= 0 else result[::-1].copy()


def _segments_intersect(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
) -> bool:
    def orientation(first: np.ndarray, second: np.ndarray, third: np.ndarray) -> float:
        return _cross2(second - first, third - first)

    def contains(first: np.ndarray, second: np.ndarray, point: np.ndarray) -> bool:
        return (
            min(first[0], second[0]) - EPS <= point[0] <= max(first[0], second[0]) + EPS
            and min(first[1], second[1]) - EPS
            <= point[1]
            <= max(first[1], second[1]) + EPS
            and abs(orientation(first, second, point)) <= EPS
        )

    values = (
        orientation(a, b, c),
        orientation(a, b, d),
        orientation(c, d, a),
        orientation(c, d, b),
    )
    if values[0] * values[1] < -EPS and values[2] * values[3] < -EPS:
        return True
    return (
        contains(a, b, c) or contains(a, b, d) or contains(c, d, a) or contains(c, d, b)
    )


def _self_intersects(vertices: np.ndarray) -> bool:
    count = vertices.shape[0]
    for first in range(count):
        first_next = (first + 1) % count
        for second in range(first + 1, count):
            second_next = (second + 1) % count
            if first in {second, second_next} or first_next in {second, second_next}:
                continue
            if _segments_intersect(
                vertices[first],
                vertices[first_next],
                vertices[second],
                vertices[second_next],
            ):
                return True
    return False


def _polygons_intersect(first: np.ndarray, second: np.ndarray) -> bool:
    for polygon in (first, second):
        for index in range(polygon.shape[0]):
            edge = polygon[(index + 1) % polygon.shape[0]] - polygon[index]
            axis = np.asarray([-edge[1], edge[0]], dtype=np.float64)
            first_values = first @ axis
            second_values = second @ axis
            if (
                float(first_values.max()) < float(second_values.min()) - EPS
                or float(second_values.max()) < float(first_values.min()) - EPS
            ):
                return False
    return True


def _point_segment_distance(
    point: np.ndarray, start: np.ndarray, end: np.ndarray
) -> float:
    delta = end - start
    ratio = float(
        np.clip(
            np.dot(point - start, delta) / max(float(np.dot(delta, delta)), EPS),
            0,
            1,
        )
    )
    return float(np.linalg.norm(point - (start + ratio * delta)))


def _polygon_distance(first: np.ndarray, second: np.ndarray) -> float:
    if _polygons_intersect(first, second):
        return 0.0
    return min(
        [
            _point_segment_distance(
                first[index],
                second[other],
                second[(other + 1) % second.shape[0]],
            )
            for index in range(first.shape[0])
            for other in range(second.shape[0])
        ]
        + [
            _point_segment_distance(
                second[index],
                first[other],
                first[(other + 1) % first.shape[0]],
            )
            for index in range(second.shape[0])
            for other in range(first.shape[0])
        ]
    )


def _point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    return all(
        _cross2(
            polygon[(index + 1) % polygon.shape[0]] - polygon[index],
            point - polygon[index],
        )
        >= -EPS
        for index in range(polygon.shape[0])
    )


def _segment_intersects_polygon(
    start: np.ndarray, end: np.ndarray, polygon: np.ndarray
) -> bool:
    return (
        _point_in_polygon(start, polygon)
        or _point_in_polygon(end, polygon)
        or any(
            _segments_intersect(
                start,
                end,
                polygon[index],
                polygon[(index + 1) % polygon.shape[0]],
            )
            for index in range(polygon.shape[0])
        )
    )


def _line_intersection(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
) -> np.ndarray | None:
    first = b - a
    second = d - c
    denominator = _cross2(first, second)
    if abs(denominator) <= EPS:
        return None
    return a + (_cross2(c - a, second) / denominator) * first


def _clip(subject: np.ndarray, clipper: np.ndarray) -> np.ndarray | None:
    output = _ccw(subject)
    clip = _ccw(clipper)
    for index in range(clip.shape[0]):
        edge_start = clip[index]
        edge_end = clip[(index + 1) % clip.shape[0]]
        source = output
        rows: list[np.ndarray] = []
        previous = source[-1]
        previous_inside = _cross2(edge_end - edge_start, previous - edge_start) >= -EPS
        for current in source:
            current_inside = (
                _cross2(edge_end - edge_start, current - edge_start) >= -EPS
            )
            if current_inside != previous_inside:
                intersection = _line_intersection(
                    previous, current, edge_start, edge_end
                )
                if intersection is not None:
                    rows.append(intersection)
            if current_inside:
                rows.append(current)
            previous = current
            previous_inside = current_inside
        if len(rows) < 3:
            return None
        output = np.asarray(rows, dtype=np.float64)
        if _area(output) <= EPS:
            return None
    return output


def _outside_fraction(footprint: np.ndarray, drivable: Sequence[np.ndarray]) -> float:
    candidates = [
        clipped
        for polygon in drivable
        if (clipped := _clip(footprint, polygon)) is not None
    ]

    def accumulate(start: int, current: np.ndarray | None, depth: int) -> float:
        total = 0.0
        for index in range(start, len(candidates)):
            intersection = (
                candidates[index]
                if current is None
                else _clip(current, candidates[index])
            )
            if intersection is None:
                continue
            total += _area(intersection) if depth % 2 == 0 else -_area(intersection)
            total += accumulate(index + 1, intersection, depth + 1)
        return total

    inside = accumulate(0, None, 0)
    return float(np.clip(1.0 - inside / _area(footprint), 0.0, 1.0))


def _grid(values: np.ndarray, thresholds: Sequence[float], mode: str) -> dict[str, Any]:
    return {
        _key(threshold): {
            "duration_s": float(
                np.count_nonzero(
                    values <= threshold if mode == "le" else values >= threshold
                )
                * DT
            ),
            "episode_count": _episodes(
                (values <= threshold if mode == "le" else values >= threshold).tolist()
            ),
        }
        for threshold in thresholds
    }


def _episodes(values: Sequence[bool]) -> int:
    count = 0
    previous = False
    for value in values:
        if value and not previous:
            count += 1
        previous = bool(value)
    return count


def _signed(values: np.ndarray) -> dict[str, float]:
    absolute = np.abs(values)
    return {
        "signed_mean": float(values.mean()),
        "rms": float(np.sqrt(np.mean(values * values))),
        "min": float(values.min()),
        "max": float(values.max()),
        "peak_abs": float(absolute.max()),
        "abs_p50": float(np.percentile(absolute, 50)),
        "abs_p90": float(np.percentile(absolute, 90)),
        "abs_p95": float(np.percentile(absolute, 95)),
        "abs_p99": float(np.percentile(absolute, 99)),
    }


def _unsigned(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "rms": float(np.sqrt(np.mean(values * values))),
        "max": float(values.max()),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
    }


def _jerk(values: np.ndarray) -> dict[str, float]:
    absolute = np.abs(values)
    return {
        "rms": float(np.sqrt(np.mean(values * values))),
        "peak_abs": float(absolute.max()),
        "abs_p95": float(np.percentile(absolute, 95)),
    }


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "status": "benchmark_only",
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(array.max()),
    }


def _assert_equal(expected: Any, actual: Any, label: str) -> None:
    if type(expected) is not type(actual):
        raise ValueError(f"independent {label} type drifted")
    if type(expected) is dict:
        if set(expected) != set(actual):
            raise ValueError(f"independent {label} fields drifted")
        for name in expected:
            _assert_equal(expected[name], actual[name], f"{label}.{name}")
    elif type(expected) is list:
        if len(expected) != len(actual):
            raise ValueError(f"independent {label} length drifted")
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            _assert_equal(left, right, f"{label}[{index}]")
    elif type(expected) is float:
        if not math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"independent {label} value drifted")
    elif expected != actual:
        raise ValueError(f"independent {label} value drifted")


def _asset(value: Mapping[str, Any]) -> Path:
    path = Path(str(value.get("path", ""))).resolve()
    if not path.is_file() or _file_sha(path) != value.get("sha256"):
        raise ValueError("independent Evaluation v2 asset SHA drifted")
    return path


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("Evaluation v2 review output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _bytes(
                {
                    "role": "independent_evaluation_v2_corrected_review",
                    "reviewer_head": report["reviewer_head"],
                    "artifact_root_sha256": report["artifact_binding"]["root_sha256"],
                    "execution_root_sha256": EXECUTION_ROOT,
                    "fixed_dp_head": FIXED_DP,
                }
            )
        )
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 independent Evaluation v2 corrected review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 independent Evaluation v2 corrected review"
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _sha_object(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _list(path: Path) -> list[Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not list:
        raise ValueError(f"{path} must contain a list")
    return value


def _key(value: float) -> str:
    return format(float(value), ".15g")


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--execution-review", type=Path, required=True)
    parser.add_argument("--execution-review-root", required=True)
    parser.add_argument("--corrected-evaluation", type=Path, required=True)
    parser.add_argument("--corrected-evaluation-root", required=True)
    parser.add_argument("--corrected-evaluation-review", type=Path, required=True)
    parser.add_argument("--corrected-evaluation-review-root", required=True)
    parser.add_argument("--continuation-ledger", type=Path, required=True)
    parser.add_argument("--continuation-ledger-sha256", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = review(
        output=args.output,
        artifact=args.artifact,
        artifact_root=args.artifact_root,
        execution=args.execution,
        execution_root=args.execution_root,
        execution_review=args.execution_review,
        execution_review_root=args.execution_review_root,
        corrected_evaluation=args.corrected_evaluation,
        corrected_evaluation_root=args.corrected_evaluation_root,
        corrected_evaluation_review=args.corrected_evaluation_review,
        corrected_evaluation_review_root=args.corrected_evaluation_review_root,
        continuation_ledger=args.continuation_ledger,
        continuation_ledger_sha256=args.continuation_ledger_sha256,
        contract=args.contract,
        contract_root=args.contract_root,
        contract_review=args.contract_review,
        contract_review_root=args.contract_review_root,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
