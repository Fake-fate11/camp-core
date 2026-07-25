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
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    segments_intersect_2d,
)
from camp_core.integrations.diffusion_planner_v22_native import (  # noqa: E402
    summarize_speed_protocol,
)
from camp_core.integrations.diffusion_planner_v25_statistics import (  # noqa: E402
    clustered_paired_summary,
)


SOURCE_SCHEMA = "camp_dp_v25_metric_semantics_amendment_artifact_v1"
REVIEW_SCHEMA = "camp_dp_v25_metric_semantics_amendment_review_artifact_v1"
ARMS = ("candidate0", "static14d", "scene14d")
DT = 0.1
THRESHOLDS = (0.5, 1.0, 2.0, 3.0)
CLEARANCE_THRESHOLDS = (0.0, 0.5, 1.0, 2.0)


def review(
    *,
    source: Path,
    source_root: str,
    execution: Path,
    execution_root: str,
    execution_review: Path,
    execution_review_root: str,
    evaluation: Path,
    evaluation_root: str,
    evaluation_review: Path,
    evaluation_review_root: str,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
    continuation_ledger: Path,
    continuation_ledger_sha256: str,
    output: Path,
) -> str:
    for label, path, root in (
        ("amendment", source, source_root),
        ("execution", execution, execution_root),
        ("execution review", execution_review, execution_review_root),
        ("corrected evaluation", evaluation, evaluation_root),
        ("corrected evaluation review", evaluation_review, evaluation_review_root),
        ("contract", contract, contract_root),
        ("contract review", contract_review, contract_review_root),
    ):
        verify_complete_seal(path, root, label=f"Fresh B4 metric {label}")
    if _file_sha256(continuation_ledger) != continuation_ledger_sha256:
        raise ValueError("continuation ledger SHA drifted")
    wrapper = _object(source / "report.json")
    if (
        wrapper.get("schema_version") != SOURCE_SCHEMA
        or wrapper.get("status") != "sealed_metric_semantics_amendment"
        or wrapper.get("execution_read_only") is not True
        or wrapper.get("execution_files_written") is not False
        or wrapper.get("evaluation_rerun") is not False
        or wrapper.get("fresh_execution_rerun") is not False
        or wrapper.get("dp_or_k8_run") is not False
        or wrapper.get("scientific_or_continuation_cas_written") is not False
        or wrapper.get("claim_changed") is not False
    ):
        raise ValueError("metric amendment wrapper invariant drifted")
    amendment = wrapper.get("amendment")
    if type(amendment) is not dict:
        raise ValueError("metric amendment payload missing")
    _verify_literal_invariants(amendment)
    _verify_bindings(
        amendment,
        execution=execution,
        execution_root=execution_root,
        execution_review=execution_review,
        execution_review_root=execution_review_root,
        evaluation=evaluation,
        evaluation_root=evaluation_root,
        evaluation_review=evaluation_review,
        evaluation_review_root=evaluation_review_root,
        contract=contract,
        contract_root=contract_root,
        contract_review=contract_review,
        contract_review_root=contract_review_root,
        continuation_ledger=continuation_ledger,
        continuation_ledger_sha256=continuation_ledger_sha256,
    )
    rows = _list(execution / "evaluation_rows.json")
    terminals = _list(execution / "run_terminals.json")
    run_dirs = sorted((execution / "runs").iterdir())
    produced_runs = amendment.get("run_summaries")
    if (
        len(rows) != 1500
        or len(terminals) != 1500
        or len(run_dirs) != 1500
        or type(produced_runs) is not list
        or len(produced_runs) != 1500
    ):
        raise ValueError("independent denominator inventory drifted")
    row_by_key = {(row.get("pair_key"), row.get("arm")): row for row in rows}
    produced_by_key = {
        (row.get("pair_key"), row.get("arm")): row for row in produced_runs
    }
    if len(row_by_key) != 1500 or len(produced_by_key) != 1500:
        raise ValueError("independent pair/arm identity drifted")
    rebuilt: list[dict[str, Any]] = []
    for run_dir, terminal in zip(run_dirs, terminals, strict=True):
        if _object(run_dir / "terminal.json") != terminal:
            raise ValueError("independent terminal binding drifted")
        key = (terminal.get("unit_sha256"), terminal.get("evaluation_arm"))
        native = _object(run_dir / "native_receipt.json")
        if _canonical_sha(native) != terminal.get("native_receipt_sha256"):
            raise ValueError("independent native SHA binding drifted")
        expected = _independent_projection(native, row_by_key[key])
        _compare_projection(expected, produced_by_key[key])
        rebuilt.append(produced_by_key[key])
    _independent_aggregate_check(amendment, rebuilt)
    review_report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "passed_independent_metric_semantics_amendment_review",
        "source": {"path": str(source.resolve()), "root_sha256": source_root},
        "review_head": _git_head(),
        "producer_metric_module_imported": False,
        "all_1500_native_receipts_independently_read": True,
        "all_1500_legacy_values_independently_equal": True,
        "body_frame_formula_independently_rebuilt": True,
        "boxcar_and_64_62_52_accounting_independently_rebuilt": True,
        "clearance_red_speed_route_extensions_independently_rebuilt": True,
        "per_run_before_cluster_independently_verified": True,
        "paired_cluster_summaries_independently_rebuilt": True,
        "missing_evidence_fail_closed": True,
        "claim_invariance_verified": True,
        "fresh_execution_rerun": False,
        "evaluation_rerun": False,
        "sealed_artifact_or_cas_written": False,
    }
    return _write_atomic(output, review_report)


def _verify_literal_invariants(amendment: Mapping[str, Any]) -> None:
    if (
        amendment.get("schema_version")
        != "camp_dp_v25_metric_semantics_amendment_v1"
        or amendment.get("status") != "sealed_read_only_metric_semantics_amendment"
        or amendment.get("benchmark") != "fresh_b4"
        or amendment.get("denominator")
        != {
            "pair_count": 500,
            "complete_arm_count": 1500,
            "tick_count": 96000,
            "full_denominator_reused": True,
            "fresh_execution_rerun": False,
        }
        or amendment.get("sample_accounting")
        != {
            "ticks_per_run": 64,
            "interval_velocities_per_run": 63,
            "raw_body_accelerations_per_run": 62,
            "filtered_body_accelerations_per_run": 52,
            "per_run_summarized_before_pairing_and_clustering": True,
            "ticks_pooled_as_independent": False,
        }
        or amendment.get("legacy_values_mutated") is not False
        or amendment.get("sealed_execution_written") is not False
        or amendment.get("scientific_or_continuation_cas_written") is not False
    ):
        raise ValueError("independent amendment literal invariant failed")
    claim = amendment.get("claim_invariance")
    if (
        type(claim) is not dict
        or claim.get("final_claim_decision")
        != "honest_no_claim_under_frozen_preregistered_all_gate"
        or claim.get("new_confirmatory_claim_authorized") is not False
        or claim.get("industrial_comfort_decision_claimed") is not False
        or claim.get("promotion_or_deployment_authorized") is not False
    ):
        raise ValueError("independent claim-invariance oracle failed")
    missing = amendment.get("missing_evidence")
    if (
        type(missing) is not dict
        or missing.get("full_polygon_offroad") != "evidence_missing"
        or missing.get("vertical_acceleration") != "not_modeled"
        or missing.get("iso_2631_conformity") != "not_assessed"
        or missing.get("sae_j2834_conformity") != "not_assessed"
    ):
        raise ValueError("independent missing-evidence oracle failed")


def _verify_bindings(amendment: Mapping[str, Any], **expected: Any) -> None:
    bindings = amendment.get("bindings")
    if type(bindings) is not dict:
        raise ValueError("amendment bindings missing")
    for name in (
        "execution", "execution_review", "evaluation", "evaluation_review",
        "contract", "contract_review",
    ):
        key = (
            "corrected_evaluation"
            if name == "evaluation"
            else "corrected_evaluation_review"
            if name == "evaluation_review"
            else name
        )
        actual = bindings.get(key)
        if actual != {
            "path": str(Path(expected[name]).resolve()),
            "root_sha256": expected[f"{name}_root"],
        }:
            raise ValueError(f"amendment binding drifted: {name}")
    if bindings.get("continuation_ledger") != {
        "path": str(Path(expected["continuation_ledger"]).resolve()),
        "sha256": expected["continuation_ledger_sha256"],
        "state": "independently_reviewed_terminal",
    }:
        raise ValueError("amendment continuation binding drifted")


def _independent_projection(
    native: Mapping[str, Any], row: Mapping[str, Any]
) -> dict[str, Any]:
    ticks = native.get("ticks")
    if type(ticks) is not list or len(ticks) != 64 or row.get("status") != "complete":
        raise ValueError("independent projection requires 64 complete ticks")
    safety_summary = _mapping(native, "safety")
    secondary = _mapping(native, "secondary")
    signal = _mapping(native, "signal_safety")
    legacy = _legacy(row)
    component = _mapping(safety_summary, "components")
    direct = {
        "safety.total": safety_summary["safety_cost"],
        "safety.collision": component["collision_any"],
        "safety.near_miss": component["near_miss_noncollision_rate"],
        "safety.offroad": component["offroad_rate"],
        "safety.wrong_way": component["wrong_way_rate"],
        "safety.red_light": component["red_light_violation_any"],
        "safety.speed": component["speed_limit_violation_rate"],
        "performance.progress": secondary["route_progress_m"],
        "performance.completion": secondary["route_completion_rate"],
        "performance.mean_jerk": secondary["mean_abs_jerk_mps3"],
        "performance.max_jerk": secondary["max_jerk_mps3"],
        "performance.mean_lateral_acceleration": secondary[
            "mean_abs_lateral_acceleration_mps2"
        ],
        "performance.max_lateral_acceleration": secondary[
            "max_abs_lateral_acceleration_mps2"
        ],
        "performance.maximum_deceleration": max(
            max(
                _number(tick["pre_decision_speed_mps"])
                - _number(_mapping(tick, "safety")["speed_mps"]),
                0.0,
            )
            / DT
            for tick in ticks
        ),
    }
    for name, value in direct.items():
        if not math.isclose(_number(value), legacy[name], rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"independent legacy equality failed: {name}")
    body = _body(ticks)
    clearance = _clearance(ticks)
    red = _red(ticks, signal)
    speed = summarize_speed_protocol(
        [_mapping(tick, "safety") for tick in ticks], dt=DT
    )
    if speed != safety_summary.get("speed_protocol"):
        raise ValueError("independent speed protocol equality failed")
    route = _route(ticks, secondary)
    return {
        "pair_key": row["pair_key"],
        "arm": row["arm"],
        "inference_cluster_id": row["inference_cluster_id"],
        "legacy_original_values": legacy,
        "body": body,
        "clearance": clearance,
        "red": red,
        "speed": speed,
        "route": route,
    }


def _compare_projection(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    for name in ("pair_key", "arm", "inference_cluster_id"):
        if actual.get(name) != expected[name]:
            raise ValueError(f"producer projection identity drifted: {name}")
    actual_legacy = actual.get("legacy_namespace")
    if type(actual_legacy) is not dict or set(actual_legacy) != set(
        expected["legacy_original_values"]
    ):
        raise ValueError("producer legacy namespace field set drifted")
    for name, value in expected["legacy_original_values"].items():
        item = actual_legacy[name]
        if (
            type(item) is not dict
            or not math.isclose(
                _number(item.get("original_value")), value, rel_tol=0.0, abs_tol=1e-12
            )
            or item.get("deprecated_industrial_interpretation") is not True
        ):
            raise ValueError(f"producer legacy namespace drifted: {name}")
    body = actual.get("vehicle_body_kinematic_comfort_proxy")
    if type(body) is not dict or body.get("sample_count") != 52:
        raise ValueError("producer body proxy structure drifted")
    for axis in ("longitudinal_mps2", "lateral_mps2"):
        _numeric_mapping_equal(body.get(axis), expected["body"][axis], f"body.{axis}")
    if body.get("duration_s") != expected["body"]["duration_s"]:
        raise ValueError("producer body duration grid drifted")
    if actual.get("clearance_descriptive") != expected["clearance"]:
        raise ValueError("producer clearance extension drifted")
    if actual.get("certified_signal_descriptive") != expected["red"]:
        raise ValueError("producer red extension drifted")
    produced_speed = dict(actual.get("speed_protocol_descriptive", {}))
    produced_rates = produced_speed.pop(
        "descriptive_event_rates_by_tolerance_mps", None
    )
    produced_speed.pop("operational_tolerance_is_project_defined_not_legal", None)
    produced_speed.pop("eu_isa_or_type_approval_conformity_claimed", None)
    if produced_speed != expected["speed"]:
        raise ValueError("producer speed extension drifted")
    expected_rates = {
        _key(tolerance): expected["speed"]["sensitivity"][
            "0.0" if tolerance == 0.0 else str(tolerance)
        ]["event_rate"]
        for tolerance in (0.0, 0.05, 0.1, 0.2)
    }
    if produced_rates != expected_rates:
        raise ValueError("producer speed tolerance projection drifted")
    if actual.get("route_descriptive") != expected["route"]:
        raise ValueError("producer route extension drifted")


def _body(ticks: list[Mapping[str, Any]]) -> dict[str, Any]:
    positions = np.asarray(
        [_xy(_mapping(tick, "safety")["position_xy"]) for tick in ticks],
        dtype=np.float64,
    )
    headings = np.asarray(
        [_number(_mapping(tick, "safety")["ego_heading_rad"]) for tick in ticks]
    )
    interval_velocity = (positions[1:] - positions[:-1]) / DT
    world_acceleration = (interval_velocity[1:] - interval_velocity[:-1]) / DT
    heading = headings[1:63]
    longitudinal = (
        world_acceleration[:, 0] * np.cos(heading)
        + world_acceleration[:, 1] * np.sin(heading)
    )
    lateral = (
        -world_acceleration[:, 0] * np.sin(heading)
        + world_acceleration[:, 1] * np.cos(heading)
    )
    kernel = np.ones(11, dtype=np.float64) / 11.0
    long_filtered = np.asarray(
        [float(np.dot(longitudinal[i : i + 11], kernel)) for i in range(52)]
    )
    lat_filtered = np.asarray(
        [float(np.dot(lateral[i : i + 11], kernel)) for i in range(52)]
    )
    return {
        "longitudinal_mps2": _summary(long_filtered),
        "lateral_mps2": _summary(lat_filtered),
        "duration_s": {
            "longitudinal_abs_gt": _durations(np.abs(long_filtered), False),
            "lateral_abs_gt": _durations(np.abs(lat_filtered), False),
            "signed_deceleration_lt_negative": _durations(
                long_filtered, True
            ),
        },
    }


def _summary(values: np.ndarray) -> dict[str, float]:
    absolute = np.abs(values)
    return {
        "signed_mean": float(np.mean(values)),
        "rms": float(np.sqrt(np.mean(values * values))),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "peak_abs": float(np.max(absolute)),
        "abs_p50": float(np.percentile(absolute, 50)),
        "abs_p90": float(np.percentile(absolute, 90)),
        "abs_p95": float(np.percentile(absolute, 95)),
        "abs_p99": float(np.percentile(absolute, 99)),
    }


def _durations(values: np.ndarray, negative: bool) -> dict[str, float]:
    return {
        _key(threshold): int(
            np.sum(values < -threshold) if negative else np.sum(values > threshold)
        )
        * DT
        for threshold in THRESHOLDS
    }


def _clearance(ticks: list[Mapping[str, Any]]) -> dict[str, Any]:
    values = np.asarray(
        [_number(_mapping(tick, "safety")["min_obb_clearance_m"]) for tick in ticks]
    )
    thresholds: dict[str, Any] = {}
    for threshold in CLEARANCE_THRESHOLDS:
        mask = values <= threshold
        episodes = int(
            sum(
                bool(current) and (index == 0 or not bool(mask[index - 1]))
                for index, current in enumerate(mask)
            )
        )
        thresholds[_key(threshold)] = {
            "sample_count": int(np.sum(mask)),
            "duration_s": int(np.sum(mask)) * DT,
            "episode_count": episodes,
        }
    return {
        "minimum_m": float(np.min(values)),
        "thresholds_le_m": thresholds,
        "threshold_grid_is_descriptive": True,
        "clearance_le_2m_named_near_miss": False,
    }


def _red(ticks: list[Mapping[str, Any]], signal: Mapping[str, Any]) -> dict[str, Any]:
    exposure = 0
    speeds: list[float] = []
    violations = 0
    margins: list[float] = []
    for tick in ticks:
        row = _mapping(tick, "safety")
        if row["signal_phase_at_interval_start"] != "red":
            continue
        exposure += 1
        lines = row["certified_signal_stop_lines"]
        if type(lines) is not list or len(lines) != 1:
            raise ValueError("independent red line binding failed")
        line = np.asarray(lines[0], dtype=np.float64)
        previous = _xy(row["front_center_prev_xy"])
        current = _xy(row["front_center_xy"])
        margins.append(_margin(current, line, _number(row["route_heading_rad"])))
        if segments_intersect_2d(previous, current, line[0], line[1]):
            speed = _number(row["speed_mps"])
            speeds.append(speed)
            violations += int(speed > 0.5)
    counts = _mapping(signal, "counts")
    denominators = _mapping(signal, "denominators")
    if (
        len(speeds) != counts["red_crossing_intervals"]
        or violations != counts["red_violation_intervals"]
        or exposure != denominators["red_phase_intervals"]
    ):
        raise ValueError("independent red accounting failed")
    return {
        "certified_phase_line_binding": True,
        "future_phase_consumed": False,
        "red_phase_interval_count": exposure,
        "unthresholded_crossing_count": len(speeds),
        "crossing_rate_per_red_phase_interval": len(speeds) / max(exposure, 1),
        "crossing_speed_mps": {
            "mean": float(np.mean(speeds)) if speeds else 0.0,
            "min": float(np.min(speeds)) if speeds else 0.0,
            "max": float(np.max(speeds)) if speeds else 0.0,
        },
        "minimum_stop_line_margin_m": min(margins) if margins else 0.0,
        "gt_0_5mps_violation_count": violations,
        "gt_0_5mps_violation_any": bool(violations),
        "legal_or_type_approval_violation_rate_claimed": False,
    }


def _route(
    ticks: list[Mapping[str, Any]], secondary: Mapping[str, Any]
) -> dict[str, Any]:
    progress = np.asarray(
        [_number(_mapping(tick, "safety")["route_progress_m"]) for tick in ticks]
    )
    positions = np.asarray(
        [_xy(_mapping(tick, "safety")["position_xy"]) for tick in ticks]
    )
    differences = np.diff(progress)
    final = float(progress[-1])
    length = _number(secondary["route_length_m"])
    distance = float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum())
    if not math.isclose(final, _number(secondary["route_progress_m"]), abs_tol=1e-12):
        raise ValueError("independent route final equality failed")
    if not math.isclose(
        distance, _number(secondary["distance_traveled_m"]), abs_tol=1e-9
    ):
        raise ValueError("independent distance equality failed")
    return {
        "final_nearest_route_polyline_projection_m": final,
        "clipped_final_route_projection_fraction": min(max(final / length, 0.0), 1.0),
        "net_route_projection_m": final - float(progress[0]),
        "maximum_route_projection_gain_m": float(np.max(progress)) - float(progress[0]),
        "backtracking_duration_s": int(np.sum(differences < 0.0)) * DT,
        "backtracking_distance_m": float(-np.sum(np.minimum(differences, 0.0))),
        "distance_traveled_m": distance,
        "nearest_segment_projection_is_route_order_state": False,
    }


def _independent_aggregate_check(
    amendment: Mapping[str, Any], runs: list[Mapping[str, Any]]
) -> None:
    grouped: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in runs:
        grouped[row["pair_key"]][row["arm"]] = row
    if len(grouped) != 500 or any(set(pair) != set(ARMS) for pair in grouped.values()):
        raise ValueError("independent aggregate denominator failed")
    pairs = [grouped[key] for key in sorted(grouped)]
    paths = amendment.get("descriptive_scalar_paths")
    if type(paths) is not list or any(type(path) is not str for path in paths):
        raise ValueError("descriptive scalar paths drifted")
    means = amendment.get("descriptive_arm_means")
    paired = amendment.get("descriptive_paired_cluster_summaries")
    for arm in ARMS:
        for path in paths:
            expected = float(np.mean([_path(pair[arm], path) for pair in pairs]))
            if not math.isclose(
                expected, _number(means[arm][path]), rel_tol=0.0, abs_tol=1e-12
            ):
                raise ValueError(f"independent arm mean drifted: {arm}/{path}")
    for method in ("static14d", "scene14d"):
        clusters = [pair[method]["inference_cluster_id"] for pair in pairs]
        for path in paths:
            expected = clustered_paired_summary(
                np.asarray(
                    [
                        _path(pair[method], path) - _path(pair["candidate0"], path)
                        for pair in pairs
                    ]
                ),
                clusters,
            )
            if expected != paired[method][path]:
                raise ValueError(
                    f"independent paired cluster summary drifted: {method}/{path}"
                )


def _legacy(row: Mapping[str, Any]) -> dict[str, float]:
    safety = _mapping(row, "safety")
    performance = _mapping(row, "performance")
    return {
        **{
            f"safety.{name}": _number(safety[name])
            for name in ("total", "collision", "near_miss", "offroad", "wrong_way", "red_light", "speed")
        },
        **{
            f"performance.{name}": _number(performance[name])
            for name in (
                "progress", "completion", "mean_jerk", "max_jerk",
                "mean_lateral_acceleration", "max_lateral_acceleration",
                "maximum_deceleration",
            )
        },
    }


def _margin(point: np.ndarray, line: np.ndarray, heading: float) -> float:
    tangent = line[1] - line[0]
    tangent = tangent / np.linalg.norm(tangent)
    normal = np.asarray([-tangent[1], tangent[0]])
    direction = np.asarray([math.cos(heading), math.sin(heading)])
    if float(normal @ direction) < 0.0:
        normal = -normal
    return float((np.mean(line, axis=0) - point) @ normal)


def _path(value: Mapping[str, Any], path: str) -> float:
    current: Any = value
    for part in path.split("."):
        current = current[part]
    return _number(current)


def _numeric_mapping_equal(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not dict or type(expected) is not dict or set(actual) != set(expected):
        raise ValueError(f"{label} field set drifted")
    for key, value in expected.items():
        if not math.isclose(
            _number(actual[key]), _number(value), rel_tol=0.0, abs_tol=1e-12
        ):
            raise ValueError(f"{label}.{key} drifted")


def _mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = value.get(name)
    if type(item) is not dict:
        raise ValueError(f"{name} must be an object")
    return dict(item)


def _number(value: Any) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError("independent numeric value drifted")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("independent finite value drifted")
    return number


def _xy(value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (2,) or not np.isfinite(array).all():
        raise ValueError("independent xy value drifted")
    return array


def _key(value: float) -> str:
    return f"{value:g}".replace(".", "_")


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("metric-semantics amendment review output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {"role": "metric_semantics_amendment_review", "head": _git_head()}
            )
        )
        root = seal_artifact(staging, label="V25 metric-semantics amendment review")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 metric-semantics amendment review"
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


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


def _canonical_bytes(value: Any) -> bytes:
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


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "source", "execution", "execution_review", "evaluation",
        "evaluation_review", "contract", "contract_review",
        "continuation_ledger", "output",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    for name in (
        "source_root", "execution_root", "execution_review_root",
        "evaluation_root", "evaluation_review_root", "contract_root",
        "contract_review_root", "continuation_ledger_sha256",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
