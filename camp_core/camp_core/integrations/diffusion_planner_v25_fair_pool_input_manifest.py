"""Pure input-only manifest and clone-key materialization for V25 fair pools."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "camp_dp_v25_fair_pool_input_only_manifest_v1"
RECEIPT_SCHEMA_VERSION = "camp_dp_v25_fair_pool_input_only_preflight_receipt_v1"
B4_FORBIDDEN_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_input_only_forbidden_clone_manifest_v1"
)
B4_PREOPEN_PATH = (
    "/root/autodl-tmp/"
    "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST"
)
B4_PREOPEN_ROOT_SHA256 = (
    "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
)
B4_PREPARED_RUNTIME_CASES_SHA256 = (
    "e67fee3309f822c80605b3e9b00009d2ae3e27139e36396d009b9a2b306535a2"
)
PI = math.pi
TWO_PI = 2.0 * math.pi


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


def wrap_to_pi(value: float) -> float:
    value = _finite(value, "angle")
    wrapped = (value + PI) % TWO_PI - PI
    return -PI if wrapped == PI else wrapped


def quantize_half_away_from_zero(value: float, quantum: str) -> int:
    value = _finite(value, "quantized value")
    scaled = Decimal(str(value)) / Decimal(quantum)
    return int(scaled.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def resample_route_polyline_0_5m(
    points_xy_m: Sequence[Sequence[float]],
) -> list[list[int]]:
    if type(points_xy_m) not in (list, tuple) or len(points_xy_m) < 2:
        raise ValueError("ordered route polyline requires at least two points")
    points = [_xy(point, "route point") for point in points_xy_m]
    lengths: list[float] = []
    cumulative = [0.0]
    for left, right in zip(points, points[1:]):
        length = math.hypot(right[0] - left[0], right[1] - left[1])
        if not math.isfinite(length) or length <= 1e-12:
            raise ValueError("route segment must be finite and longer than 1e-12 m")
        lengths.append(length)
        cumulative.append(cumulative[-1] + length)
    total = cumulative[-1]
    sample_s = [0.5 * i for i in range(int(math.floor(total / 0.5)) + 1)]
    if total - sample_s[-1] > 1e-12:
        sample_s.append(total)
    else:
        sample_s[-1] = total
    result: list[list[int]] = []
    segment = 0
    for distance in sample_s:
        while segment + 1 < len(cumulative) and (
            distance > cumulative[segment + 1] + 1e-12
        ):
            segment += 1
        ratio = (distance - cumulative[segment]) / lengths[segment]
        ratio = min(1.0, max(0.0, ratio))
        x = points[segment][0] + ratio * (
            points[segment + 1][0] - points[segment][0]
        )
        y = points[segment][1] + ratio * (
            points[segment + 1][1] - points[segment][1]
        )
        result.append(
            [
                quantize_half_away_from_zero(x, "0.001"),
                quantize_half_away_from_zero(y, "0.001"),
            ]
        )
    return result


def materialize_input_only_manifest(
    *,
    state_spec: Mapping[str, Any],
    source_record: Mapping[str, Any],
) -> dict[str, Any]:
    if type(state_spec) is not dict or type(source_record) is not dict:
        raise ValueError("state spec and source record must be objects")
    required_record = {
        "source_state_ordinal",
        "map_geometry_sha256",
        "route_asset_sha256",
        "scenario_source_content_sha256",
        "spawn_pose",
        "goal_pose",
        "ordered_route_polyline_xy_m",
        "dynamic_actors_initial",
        "actual_input_sha256",
        "actual_state_sha256",
        "actual_latent_tensor_sha256",
    }
    if set(source_record) != required_record:
        raise ValueError("source record fields drifted")
    for field in (
        "map_geometry_sha256",
        "route_asset_sha256",
        "scenario_source_content_sha256",
        "actual_input_sha256",
        "actual_state_sha256",
        "actual_latent_tensor_sha256",
    ):
        _sha256(source_record[field], field)
    if source_record["source_state_ordinal"] != state_spec.get(
        "source_state_ordinal"
    ):
        raise ValueError("source state ordinal drifted")
    if source_record["map_geometry_sha256"] != state_spec.get(
        "map_geometry_sha256"
    ):
        raise ValueError("map authority drifted")
    if source_record["route_asset_sha256"] != state_spec.get(
        "route_asset_sha256"
    ):
        raise ValueError("route authority drifted")
    clone_payload = _clone_payload(
        map_geometry_sha256=source_record["map_geometry_sha256"],
        scenario_source_content_sha256=source_record[
            "scenario_source_content_sha256"
        ],
        spawn_pose=source_record["spawn_pose"],
        goal_pose=source_record["goal_pose"],
        ordered_route_polyline_xy_m=source_record[
            "ordered_route_polyline_xy_m"
        ],
        dynamic_actors_initial=source_record["dynamic_actors_initial"],
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "split": state_spec.get("split"),
        "state_spec_id": state_spec.get("state_spec_id"),
        "state_spec_sha256": state_spec.get("state_spec_sha256"),
        "source_state_ordinal": source_record["source_state_ordinal"],
        "scenario_seed": state_spec.get("scenario_seed"),
        "latent_seed": state_spec.get("latent_seed"),
        "actual_input_sha256": source_record["actual_input_sha256"],
        "actual_state_sha256": source_record["actual_state_sha256"],
        "actual_latent_tensor_sha256": source_record[
            "actual_latent_tensor_sha256"
        ],
        "clone_payload": clone_payload,
        "clone_key_sha256": sha256_json(clone_payload),
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest


def materialize_b4_forbidden_clone_manifest(
    prepared_runtime_cases_bytes: bytes,
) -> dict[str, Any]:
    """Derive the input-only B4 forbidden set without reading run outcomes."""

    if type(prepared_runtime_cases_bytes) is not bytes:
        raise ValueError("prepared runtime cases must be exact bytes")
    if hashlib.sha256(prepared_runtime_cases_bytes).hexdigest() != (
        B4_PREPARED_RUNTIME_CASES_SHA256
    ):
        raise ValueError("B4 prepared runtime cases file SHA drifted")
    try:
        cases = json.loads(prepared_runtime_cases_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("B4 prepared runtime cases are not UTF-8 JSON") from error
    if type(cases) is not list or len(cases) != 100:
        raise ValueError("B4 prepared runtime case count must be exactly 100")
    entries: list[dict[str, Any]] = []
    for expected_ordinal, prepared in enumerate(cases):
        if type(prepared) is not dict or set(prepared) != {
            "calibration_outcomes_consumed",
            "candidate_generation_executed",
            "case",
            "fresh_b2_opened",
            "identity_ordinal",
            "map_artifact",
            "mapped_signal_authority",
            "model_loaded",
            "outcome_fields_consumed",
            "route_polyline_world_m",
            "scenario_identity_sha256",
            "schema_version",
            "status",
            "training_executed",
        }:
            raise ValueError("B4 prepared runtime top-level schema drifted")
        if (
            prepared["identity_ordinal"] != expected_ordinal
            or prepared["model_loaded"] is not False
            or prepared["candidate_generation_executed"] is not False
            or prepared["training_executed"] is not False
            or prepared["calibration_outcomes_consumed"] is not False
            or prepared["outcome_fields_consumed"] != []
        ):
            raise ValueError("B4 prepared runtime input-only boundary drifted")
        _sha256(prepared["scenario_identity_sha256"], "B4 scenario identity")
        case = prepared["case"]
        if type(case) is not dict or set(case) != {
            "actors",
            "corridor_group_sha256",
            "family",
            "holdout_outcome_consumed",
            "map_family_id",
            "mapped_signal_authority",
            "outcome_blind",
            "outcome_fields_consumed",
            "parameter_block_id",
            "parameters",
            "phase_authority_mode",
            "record_key",
            "route_family_id",
            "route_identity_sha256",
            "route_spec",
            "runner_eligible",
            "scenario_id",
            "schema_version",
            "seeds",
            "semantic_variant",
            "signal",
            "signal_source_class",
            "source_availability",
            "source_map_path",
            "source_map_sha256",
            "source_requirements",
            "source_stratum",
            "split",
            "tier",
        }:
            raise ValueError("B4 prepared runtime case schema drifted")
        if (
            case["split"] != "fresh_b4"
            or case["outcome_blind"] is not True
            or case["holdout_outcome_consumed"] is not False
            or case["outcome_fields_consumed"] != []
        ):
            raise ValueError("B4 case is not outcome-blind Fresh B4 input")
        route_spec = case["route_spec"]
        if type(route_spec) is not dict or set(route_spec) != {
            "goal_pose",
            "lanelet_ids",
            "start_pose",
        }:
            raise ValueError("B4 route spec schema drifted")
        source = case["mapped_signal_authority"]
        if type(source) is not dict:
            raise ValueError("B4 mapped source authority missing")
        semantic = source.get("semantic_clone_payload")
        semantic_sha = _sha256(
            source.get("semantic_clone_sha256"), "B4 semantic clone"
        )
        if type(semantic) is not dict or sha256_json(semantic) != semantic_sha:
            raise ValueError("B4 semantic clone payload SHA drifted")
        actors = [_b4_actor(actor) for actor in case["actors"]]
        start = _b4_pose(route_spec["start_pose"], "B4 start")
        goal = _b4_pose(route_spec["goal_pose"], "B4 goal")
        clone_payload = _clone_payload(
            map_geometry_sha256=_sha256(
                case["source_map_sha256"], "B4 source map"
            ),
            scenario_source_content_sha256=semantic_sha,
            spawn_pose=start,
            goal_pose=goal,
            ordered_route_polyline_xy_m=prepared[
                "route_polyline_world_m"
            ],
            dynamic_actors_initial=actors,
        )
        entries.append(
            {
                "identity_ordinal": expected_ordinal,
                "scenario_identity_sha256": prepared[
                    "scenario_identity_sha256"
                ],
                "clone_key_sha256": sha256_json(clone_payload),
            }
        )
    clone_keys = [entry["clone_key_sha256"] for entry in entries]
    if len(set(clone_keys)) != 100:
        raise ValueError("B4 forbidden clone keys must be unique")
    manifest = {
        "schema_version": B4_FORBIDDEN_SCHEMA_VERSION,
        "source": {
            "preopen_path": B4_PREOPEN_PATH,
            "preopen_root_sha256": B4_PREOPEN_ROOT_SHA256,
            "relative_path": "fresh_b4_prepared_runtime_cases.json",
            "file_sha256": B4_PREPARED_RUNTIME_CASES_SHA256,
            "case_count": 100,
            "outcome_fields_read": [],
        },
        "entries": entries,
        "clone_keys_sorted": sorted(clone_keys),
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest


def validate_preflight_receipt(
    receipt: Mapping[str, Any],
    *,
    calibration_spec_sha256s: Sequence[str],
    validation_spec_sha256s: Sequence[str],
    b4_forbidden_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if type(receipt) is not dict:
        raise ValueError("preflight receipt must be object")
    required = {
        "schema_version",
        "contract_root_sha256",
        "b4_forbidden_manifest_authority",
        "calibration_manifests",
        "validation_manifests",
        "model_pool_selector_call_count_before_receipt",
        "within_calibration_overlap_count",
        "within_validation_overlap_count",
        "cross_split_overlap_count",
        "b4_overlap_count",
        "status",
    }
    if set(receipt) != required:
        raise ValueError("preflight receipt fields drifted")
    if receipt["schema_version"] != RECEIPT_SCHEMA_VERSION:
        raise ValueError("preflight receipt schema drifted")
    _sha256(receipt["contract_root_sha256"], "contract root")
    if receipt["model_pool_selector_call_count_before_receipt"] != 0:
        raise ValueError("preflight occurred after a forbidden call")
    forbidden_manifest = _validated_b4_forbidden_manifest(
        b4_forbidden_manifest
    )
    expected_b4_authority = {
        "preopen_path": B4_PREOPEN_PATH,
        "preopen_root_sha256": B4_PREOPEN_ROOT_SHA256,
        "prepared_runtime_cases_sha256": B4_PREPARED_RUNTIME_CASES_SHA256,
        "forbidden_manifest_sha256": forbidden_manifest["manifest_sha256"],
        "forbidden_clone_key_count": 100,
    }
    if receipt["b4_forbidden_manifest_authority"] != expected_b4_authority:
        raise ValueError("B4 forbidden manifest receipt binding drifted")
    calibration = _manifest_list(
        receipt["calibration_manifests"], calibration_spec_sha256s, "calibration"
    )
    validation = _manifest_list(
        receipt["validation_manifests"], validation_spec_sha256s, "validation"
    )
    forbidden = forbidden_manifest["clone_keys_sorted"]
    calibration_keys = [item["clone_key_sha256"] for item in calibration]
    validation_keys = [item["clone_key_sha256"] for item in validation]
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
            set(calibration_keys + validation_keys).intersection(forbidden)
        ),
    }
    for field, expected in expected_counts.items():
        if receipt[field] != expected or expected != 0:
            raise ValueError(f"{field} must be exactly zero")
    if receipt["status"] != "passed_before_first_model_pool_selector_call":
        raise ValueError("preflight status drifted")
    return dict(receipt)


def _validated_b4_forbidden_manifest(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("B4 forbidden manifest must be object")
    payload = dict(value)
    supplied = payload.pop("manifest_sha256", None)
    if supplied != sha256_json(payload):
        raise ValueError("B4 forbidden manifest SHA drifted")
    if payload.get("schema_version") != B4_FORBIDDEN_SCHEMA_VERSION:
        raise ValueError("B4 forbidden manifest schema drifted")
    expected_source = {
        "preopen_path": B4_PREOPEN_PATH,
        "preopen_root_sha256": B4_PREOPEN_ROOT_SHA256,
        "relative_path": "fresh_b4_prepared_runtime_cases.json",
        "file_sha256": B4_PREPARED_RUNTIME_CASES_SHA256,
        "case_count": 100,
        "outcome_fields_read": [],
    }
    if payload.get("source") != expected_source:
        raise ValueError("B4 forbidden manifest source drifted")
    entries = payload.get("entries")
    clone_keys = payload.get("clone_keys_sorted")
    if (
        type(entries) is not list
        or len(entries) != 100
        or type(clone_keys) is not list
        or len(clone_keys) != 100
    ):
        raise ValueError("B4 forbidden manifest denominator drifted")
    expected_keys = []
    for ordinal, entry in enumerate(entries):
        if type(entry) is not dict or set(entry) != {
            "identity_ordinal",
            "scenario_identity_sha256",
            "clone_key_sha256",
        }:
            raise ValueError("B4 forbidden manifest entry schema drifted")
        if entry["identity_ordinal"] != ordinal:
            raise ValueError("B4 forbidden manifest ordinal drifted")
        _sha256(entry["scenario_identity_sha256"], "B4 scenario identity")
        expected_keys.append(_sha256(entry["clone_key_sha256"], "B4 clone key"))
    if clone_keys != sorted(expected_keys) or len(set(clone_keys)) != 100:
        raise ValueError("B4 forbidden clone key inventory drifted")
    return dict(value)


def _clone_payload(
    *,
    map_geometry_sha256: str,
    scenario_source_content_sha256: str,
    spawn_pose: Mapping[str, Any],
    goal_pose: Mapping[str, Any],
    ordered_route_polyline_xy_m: Sequence[Sequence[float]],
    dynamic_actors_initial: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    map_sha = _sha256(map_geometry_sha256, "map geometry")
    source_sha = _sha256(
        scenario_source_content_sha256, "scenario source content"
    )
    spawn = _pose(spawn_pose, "spawn")
    goal = _pose(goal_pose, "goal")
    route = resample_route_polyline_0_5m(ordered_route_polyline_xy_m)
    actors = _actors(dynamic_actors_initial)
    return {
        "schema_version": "camp_dp_v25_id_free_clone_key_payload_v1",
        "units": {
            "position": "integer_millimetres",
            "heading": "integer_1e-4_radians_wrapped_minus_pi_inclusive",
            "speed": "integer_millimetres_per_second",
            "dimensions": "integer_millimetres",
            "route_resample_spacing": "0.5_m_with_exact_final_endpoint",
        },
        "map_geometry_sha256": map_sha,
        "ordered_route_geometry_sha256": sha256_json(route),
        "spawn_pose_quantized": spawn,
        "goal_pose_quantized": goal,
        "route_polyline_resampled_0_5m_quantized": route,
        "dynamic_actor_initial_state_sorted": actors,
        "scenario_source_content_sha256": source_sha,
    }


def _b4_pose(value: Any, label: str) -> dict[str, float]:
    if type(value) is not list or len(value) != 3:
        raise ValueError(f"{label} must be [x_m,y_m,heading_rad]")
    return {
        "x_m": _finite(value[0], label),
        "y_m": _finite(value[1], label),
        "z_m": 0.0,
        "heading_rad": _finite(value[2], label),
    }


def _b4_actor(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "agent_type",
        "id",
        "initial_heading_rad",
        "initial_xy",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "length_m",
        "longitudinal_acceleration_mps2",
        "longitudinal_speed_mps",
        "route_normal",
        "route_tangent",
        "trigger_time_s",
        "wheelbase_m",
        "width_m",
    }:
        raise ValueError("B4 actor schema drifted")
    xy = _xy(value["initial_xy"], "B4 actor initial_xy")
    longitudinal = _finite(
        value["longitudinal_speed_mps"], "B4 actor longitudinal speed"
    )
    lateral = _finite(
        value["lateral_speed_mps"], "B4 actor lateral speed"
    )
    return {
        "class": value["agent_type"],
        "length_m": value["length_m"],
        "width_m": value["width_m"],
        "x_m": xy[0],
        "y_m": xy[1],
        "heading_rad": value["initial_heading_rad"],
        "speed_mps": math.hypot(longitudinal, lateral),
    }


def _manifest_list(
    value: Any, expected_spec_sha256s: Sequence[str], label: str
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(expected_spec_sha256s):
        raise ValueError(f"{label} manifest count drifted")
    result: list[dict[str, Any]] = []
    for item, expected_spec_sha in zip(value, expected_spec_sha256s):
        if type(item) is not dict:
            raise ValueError(f"{label} manifest must be object")
        payload = dict(item)
        supplied = payload.pop("manifest_sha256", None)
        if supplied != sha256_json(payload):
            raise ValueError(f"{label} manifest SHA drifted")
        if item.get("state_spec_sha256") != expected_spec_sha:
            raise ValueError(f"{label} state spec order drifted")
        _sha256(item.get("clone_key_sha256"), "clone key")
        result.append(item)
    return result


def _pose(value: Any, label: str) -> dict[str, int]:
    if type(value) is not dict or set(value) != {"x_m", "y_m", "z_m", "heading_rad"}:
        raise ValueError(f"{label} pose fields drifted")
    return {
        "x_mm": quantize_half_away_from_zero(value["x_m"], "0.001"),
        "y_mm": quantize_half_away_from_zero(value["y_m"], "0.001"),
        "z_mm": quantize_half_away_from_zero(value["z_m"], "0.001"),
        "heading_1e4rad": quantize_half_away_from_zero(
            wrap_to_pi(value["heading_rad"]), "0.0001"
        ),
    }


def _actors(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise ValueError("dynamic actors must be list; missing actors use []")
    result: list[dict[str, Any]] = []
    required = {
        "class",
        "length_m",
        "width_m",
        "x_m",
        "y_m",
        "heading_rad",
        "speed_mps",
    }
    for actor in value:
        if type(actor) is not dict or set(actor) != required:
            raise ValueError("dynamic actor fields drifted")
        if type(actor["class"]) is not str or not actor["class"]:
            raise ValueError("dynamic actor class invalid")
        item = {
            "class": actor["class"],
            "length_mm": quantize_half_away_from_zero(
                _positive(actor["length_m"], "actor length"), "0.001"
            ),
            "width_mm": quantize_half_away_from_zero(
                _positive(actor["width_m"], "actor width"), "0.001"
            ),
            "x_mm": quantize_half_away_from_zero(actor["x_m"], "0.001"),
            "y_mm": quantize_half_away_from_zero(actor["y_m"], "0.001"),
            "heading_1e4rad": quantize_half_away_from_zero(
                wrap_to_pi(actor["heading_rad"]), "0.0001"
            ),
            "speed_mmps": quantize_half_away_from_zero(
                actor["speed_mps"], "0.001"
            ),
        }
        result.append(item)
    return sorted(
        result,
        key=lambda item: (
            item["class"].encode("utf-8"),
            item["length_mm"],
            item["width_mm"],
            item["x_mm"],
            item["y_mm"],
            item["heading_1e4rad"],
            item["speed_mmps"],
        ),
    )


def _xy(value: Sequence[float], label: str) -> tuple[float, float]:
    if type(value) not in (list, tuple) or len(value) != 2:
        raise ValueError(f"{label} must be length-2")
    return _finite(value[0], label), _finite(value[1], label)


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive(value: Any, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return value
