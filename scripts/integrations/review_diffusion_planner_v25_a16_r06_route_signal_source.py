#!/usr/bin/env python3
"""Independently review the A1.6/R0.6 route-level signal-source census."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    install_lanelet2_projection_fallback,
    require_source_preserving_lanelet2_regulatory_adapter,
)
from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    build_critical_implementation_manifest,
    canonical_sha256 as full_r_canonical_sha256,
    verify_dual_head_contract,
)


SCHEMA_VERSION = "camp_dp_v25_a161_route_signal_source_review_v2"
PRODUCER_SCHEMA_VERSION = "camp_dp_v25_a161_route_signal_source_census_v2"
RECEIPTS_SCHEMA_VERSION = "camp_dp_v25_a161_route_signal_source_receipts_v2"
SUPPLEMENT_SCHEMA_VERSION = "camp_dp_v25_formal_route_source_contract_supplement_v2"
MAPPED_CHAIN_SCHEMA_VERSION = (
    "camp_dp_v25_family_independent_mapped_signal_source_chain_v1"
)
RUNTIME_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_family_independent_current_signal_receipt_v1"
)
NO_SIGNAL_CHAIN_SCHEMA_VERSION = "camp_dp_v25_no_signal_source_chain_v1"
SEMANTIC_PAYLOAD_SCHEMA_VERSION = "camp_dp_v25_semantic_clone_payload_v3"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
CONSUMED_RELEASE_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2"
)
CONSUMED_RELEASE_ROOT_SHA256 = (
    "cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1"
)
FAILED_PREFLIGHT_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_full_config_preflight_1e1c32c7_5f919a54290957e2"
)
FAILED_PREFLIGHT_ROOT_SHA256 = (
    "b2022b6eb363023ce4ad842aefebb95c7d575a5101d822c0bdf874890758b62d"
)
CONSUMED_NONCE = (
    "5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e"
)
CONSUMED_MARKER_SHA256 = (
    "0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d"
)
CANONICAL_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
CANONICAL_CONSUMED_MARKER = Path(
    "/root/autodl-tmp/.camp_dp_v25_controlled_train_release_nonces/"
    "v25_preflight_5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e."
    "consumed.json"
)
CANONICAL_CONSUMED_MARKER_PAYLOAD = {
    "gate": "preflight",
    "nonce": CONSUMED_NONCE,
    "authorized_output_dir": str(FAILED_PREFLIGHT_ARTIFACT),
}
SOURCE_PAYLOAD_PATHS = frozenset(
    {
        "COMMAND",
        "HEADS",
        "formal_route_source_contract_supplement.json",
        "report.json",
        "route_signal_source_receipts.json",
        "run.exit",
    }
)
REVIEW_PAYLOAD_PATHS = frozenset({"COMMAND", "HEADS", "report.json", "run.exit"})
DP_IMPORT_PATHS = {
    "scenario_generation.traffic_light": "scenario_generation/traffic_light.py",
    "scenario_generation.gui.lanelet_scene_builder": (
        "scenario_generation/gui/lanelet_scene_builder.py"
    ),
}
CURRENT_REQUEST_SOURCE_ID = "fixed_dp_current_request_route_map_signal_one_hot"
EXPECTED_EXECUTABLE = 1500
EXPECTED_RETAINED = 153
EXPECTED_EXECUTABLE_MAPPED = 146
EXPECTED_EXECUTABLE_NO_SIGNAL = 1354
EXPECTED_CONTROLLED = 21
EXPECTED_OBSERVED = 125
EXPECTED_SEED = 25001
MINIMUM_FREE_BYTES = 10 * 1024**3
BOUNDED_COVERAGE_SCHEMA_VERSION = "camp_dp_v25_bounded_coverage_design_v1"
BOUNDED_COVERAGE_MAX_IDENTITIES = 320
EXPECTED_SOURCE_CHECK_FIELDS = frozenset(
    {
        "all_1653_formal_train_identities_accounted",
        "all_1500_executable_source_qualified",
        "all_153_retained_preserved",
        "executable_146_mapped_signal",
        "executable_1354_no_signal",
        "mapped_21_controlled_same_tick_override",
        "mapped_125_observe_same_tick_request",
        "source_failures_empty",
        "future_schedule_not_consumed",
        "phase_remaining_unavailable",
        "no_model_simulator_candidate_dp_forward",
        "training_calibration_scene_v2i_fresh_outcome_closed",
        "bounded_coverage_design_within_320_identity_cap",
        "bounded_coverage_design_k8_not_executed",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--expected-camp-source-head", required=True)
    parser.add_argument("--expected-camp-pointer-head", required=True)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _oracle_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _oracle_sha256(payload: Any) -> str:
    return hashlib.sha256(_oracle_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if raw != _oracle_bytes(value):
        raise ValueError(f"noncanonical JSON bytes: {path.name}")
    return value


def _load_plain(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    path.write_bytes(_oracle_bytes(payload))


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _verify_exact_payload_inventory(
    root: Path, root_sha256: str, *, expected_paths: frozenset[str], label: str
) -> dict[str, Any]:
    receipt = verify_complete_seal(root, root_sha256, label=label)
    paths = receipt.get("manifest_paths")
    if (
        type(paths) is not list
        or frozenset(paths) != expected_paths
        or len(paths) != len(expected_paths)
        or receipt.get("file_count") != len(expected_paths)
    ):
        raise ValueError(f"{label} exact payload inventory drifted")
    return receipt


def _validate_consumed_marker(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("consumed nonce marker must not be a symlink")
    if (
        not path.is_absolute()
        or str(path) != str(CANONICAL_CONSUMED_MARKER)
        or path.resolve() != CANONICAL_CONSUMED_MARKER.resolve()
        or not path.is_file()
        or _file_sha256(path) != CONSUMED_MARKER_SHA256
    ):
        raise ValueError("consumed nonce marker canonical path/bytes drifted")
    payload = _load(path)
    if not _strict_equal(payload, CANONICAL_CONSUMED_MARKER_PAYLOAD):
        raise ValueError("consumed nonce marker schema/value/type drifted")
    return payload


def _verify_imported_dp_module(
    *, repo: Path, fixed_head: str, module: Any, relative_path: str
) -> dict[str, str]:
    expected = repo.resolve() / Path(relative_path)
    module_file = getattr(module, "__file__", None)
    if type(module_file) is not str or Path(module_file).resolve() != expected.resolve():
        raise ValueError("imported fixed-DP module is outside canonical fixed-DP repo")
    if expected.is_symlink() or not expected.is_file():
        raise ValueError("imported fixed-DP module path is unavailable or symlinked")
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_path],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    committed = subprocess.run(
        ["git", "show", f"{fixed_head}:{relative_path}"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    actual = expected.read_bytes()
    if actual != committed:
        raise ValueError("imported fixed-DP module bytes differ from fixed git object")
    return {
        "relative_path": relative_path,
        "resolved_path": str(expected.resolve()),
        "sha256": hashlib.sha256(actual).hexdigest(),
    }


def _verify_dp_import_authority(dp_repo: Path) -> dict[str, dict[str, str]]:
    if (
        not dp_repo.is_absolute()
        or str(dp_repo) != str(CANONICAL_DP_REPO)
        or dp_repo.is_symlink()
        or dp_repo.resolve() != CANONICAL_DP_REPO.resolve()
    ):
        raise ValueError("fixed-DP repo must be the canonical real path")
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    receipts = {}
    for module_name, relative_path in DP_IMPORT_PATHS.items():
        receipts[module_name] = _verify_imported_dp_module(
            repo=dp_repo,
            fixed_head=FIXED_DP_HEAD,
            module=importlib.import_module(module_name),
            relative_path=relative_path,
        )
    return receipts


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _tracked_clean(repo: Path) -> bool:
    return not subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _round_clean(values: np.ndarray, decimals: int = 6) -> np.ndarray:
    rounded = np.round(np.asarray(values, dtype=np.float64), decimals)
    rounded[np.abs(rounded) < 0.5 * 10.0 ** (-decimals)] = 0.0
    return rounded


def _resample_polyline(points: np.ndarray, count: int = 64) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if (
        values.ndim != 2
        or values.shape[1] != 2
        or len(values) < 2
        or not np.isfinite(values).all()
    ):
        raise ValueError("independent route polyline is invalid")
    lengths = np.linalg.norm(np.diff(values, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    if cumulative[-1] <= 1e-9:
        raise ValueError("independent route polyline has no length")
    result = np.empty((count, 2), dtype=np.float64)
    for index, target in enumerate(
        np.linspace(0.0, float(cumulative[-1]), count)
    ):
        left = min(
            max(int(np.searchsorted(cumulative, target, side="right") - 1), 0),
            len(values) - 2,
        )
        span = float(cumulative[left + 1] - cumulative[left])
        fraction = 0.0 if span <= 1e-12 else (target - cumulative[left]) / span
        result[index] = values[left] + fraction * (values[left + 1] - values[left])
    return result


def _semantic_payload(
    case: Mapping[str, Any], route_world: np.ndarray, stop_world: np.ndarray | None
) -> dict[str, Any]:
    sampled = _resample_polyline(route_world)
    origin = sampled[0]
    direction = sampled[1] - sampled[0]
    tangent = direction / np.linalg.norm(direction)
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    rotation = np.stack((tangent, normal), axis=1)
    parameter_fields = {
        "headway_m",
        "ego_speed_mps",
        "other_speed_mps",
        "deceleration_mps2",
        "trigger_time_s",
        "lateral_offset_m",
        "lateral_speed_mps",
        "crossing_speed_mps",
        "variant",
    }
    parameters_raw = case.get("parameters")
    if not isinstance(parameters_raw, Mapping) or set(parameters_raw) - parameter_fields:
        raise ValueError("independent semantic parameter fields drifted")
    parameters: dict[str, float] = {}
    for key, value in parameters_raw.items():
        if key == "variant":
            if type(value) is not int:
                raise ValueError("semantic variant parameter must be native int")
            continue
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise ValueError("semantic physical parameter is invalid")
        parameters[key] = float(value)
    actor_fields = {
        "id",
        "agent_type",
        "initial_xy",
        "initial_heading_rad",
        "route_tangent",
        "route_normal",
        "trigger_time_s",
        "longitudinal_speed_mps",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "longitudinal_acceleration_mps2",
        "length_m",
        "width_m",
        "wheelbase_m",
    }
    actors: list[dict[str, Any]] = []
    for raw in case.get("actors", []):
        if (
            not isinstance(raw, Mapping)
            or set(raw) - actor_fields
            or not (actor_fields - {"id"}).issubset(raw)
        ):
            raise ValueError("independent semantic actor fields drifted")
        heading = float(raw["initial_heading_rad"])
        item: dict[str, Any] = {
            "agent_type": str(raw["agent_type"]),
            "initial_xy_local_m": _round_clean(
                (np.asarray(raw["initial_xy"], dtype=np.float64) - origin) @ rotation
            ).tolist(),
            "initial_heading_local_unit": _round_clean(
                np.asarray([math.cos(heading), math.sin(heading)]) @ rotation
            ).tolist(),
            "route_tangent_local": _round_clean(
                np.asarray(raw["route_tangent"], dtype=np.float64) @ rotation
            ).tolist(),
            "route_normal_local": _round_clean(
                np.asarray(raw["route_normal"], dtype=np.float64) @ rotation
            ).tolist(),
        }
        for key in sorted(
            (actor_fields - {"id"})
            - {
                "agent_type",
                "initial_xy",
                "initial_heading_rad",
                "route_tangent",
                "route_normal",
            }
        ):
            value = raw[key]
            if key == "lateral_target_m" and value is None:
                item[key] = None
            elif type(value) in (int, float) and math.isfinite(float(value)):
                item[key] = float(value)
            else:
                raise ValueError("semantic actor physical field is invalid")
        actors.append(item)
    actors.sort(key=_oracle_sha256)
    signal = case.get("signal")
    if not isinstance(signal, Mapping) or set(signal) not in (
        {"phase", "mapped_source_required"},
        {"phase", "phase_remaining_s", "mapped_source_required"},
    ):
        raise ValueError("independent semantic signal fields drifted")
    payload: dict[str, Any] = {
        "schema_version": SEMANTIC_PAYLOAD_SCHEMA_VERSION,
        "family": str(case["family"]),
        "tier": str(case["tier"]),
        "semantic_variant": str(case["semantic_variant"]),
        "parameters": parameters,
        "actors": actors,
        "signal": {
            "current_phase": str(signal["phase"]),
            "mapped_source_required": signal["mapped_source_required"] is True,
            "source_mode": "no_v2i",
        },
        "route_polyline_local_m": _round_clean(
            (sampled - origin) @ rotation
        ).tolist(),
    }
    if stop_world is not None:
        payload["stop_line_local_m"] = _round_clean(
            (np.asarray(stop_world, dtype=np.float64) - origin) @ rotation
        ).tolist()
    return payload


def _route_polyline(builder: Any, route_ids: list[int]) -> np.ndarray:
    pieces = []
    for lanelet_id in route_ids:
        if lanelet_id not in builder._cache:
            raise ValueError("formal route lanelet is absent from actual map")
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        pieces.append(line if not pieces else line[1:])
    return np.concatenate(pieces, axis=0)


def _stop_projection(
    builder: Any,
    route_ids: list[int],
    controlled: list[int],
    stop: np.ndarray,
) -> tuple[float, float, float, np.ndarray]:
    midpoint = stop.mean(axis=0)
    route_offset = 0.0
    best: tuple[float, float, np.ndarray] | None = None
    for lanelet_id in route_ids:
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        local_offset = 0.0
        for start, end in zip(line[:-1], line[1:]):
            vector = end - start
            length = float(np.linalg.norm(vector))
            fraction = (
                0.0
                if length <= 1e-12
                else float(
                    np.clip(((midpoint - start) @ vector) / length**2, 0.0, 1.0)
                )
            )
            if lanelet_id in controlled and length > 1e-12:
                projected = start + fraction * vector
                candidate = (
                    float(np.linalg.norm(midpoint - projected)),
                    route_offset + local_offset + fraction * length,
                    vector / length,
                )
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            local_offset += length
        route_offset += local_offset
    if best is None:
        raise ValueError("independent stop-line projection failed")
    return best[0], best[1], route_offset, best[2]


def _actual_regs(case: Mapping[str, Any], builder: Any) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for lanelet_id in case["route_spec"]["lanelet_ids"]:
        lanelet = builder._ll_by_id.get(int(lanelet_id))
        if lanelet is None:
            raise ValueError("formal route lanelet is missing")
        for reg in lanelet.trafficLights():
            row = result.setdefault(int(reg.id), {"reg": reg, "lanelet_ids": []})
            row["lanelet_ids"].append(int(lanelet_id))
    return result


def _reconstruct_chain(
    case: Mapping[str, Any], builder: Any, regs: Mapping[int, Mapping[str, Any]]
) -> dict[str, Any]:
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    route = _route_polyline(builder, route_ids)
    if not regs:
        semantic = _semantic_payload(case, route, None)
        chain: dict[str, Any] = {
            "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
            "scenario_id": str(case["scenario_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "source_map_sha256": str(case["source_map_sha256"]),
            "route_lanelet_ids": route_ids,
            "route_geometry_sha256": _oracle_sha256(
                {"route_polyline_local_m": semantic["route_polyline_local_m"]}
            ),
            "traffic_light_regulatory_element_ids": [],
            "semantic_clone_payload": semantic,
            "semantic_clone_sha256": _oracle_sha256(semantic),
            "source_chain_sha256": "",
        }
    else:
        if len(regs) != 1:
            raise ValueError("mapped route has ambiguous regulatory elements")
        reg_id, row = next(iter(regs.items()))
        reg = row["reg"]
        stop_line = reg.stopLine
        if stop_line is None:
            raise ValueError("mapped regulatory element has no stop line")
        stop = np.asarray([(point.x, point.y) for point in stop_line], dtype=np.float64)
        controlled = sorted(set(int(value) for value in row["lanelet_ids"]))
        distance, arc, length, tangent = _stop_projection(
            builder, route_ids, controlled, stop
        )
        semantic = _semantic_payload(case, route, stop)
        formal_phase = str(case["signal"]["phase"])
        controlled_override = formal_phase in {"green", "yellow", "red"}
        params = reg.parameters
        chain = {
            "schema_version": MAPPED_CHAIN_SCHEMA_VERSION,
            "scenario_id": str(case["scenario_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "source_map_sha256": str(case["source_map_sha256"]),
            "phase_authority_mode": (
                "controlled_same_tick_override"
                if controlled_override
                else "observe_same_tick_request"
            ),
            "expected_current_phase": formal_phase if controlled_override else None,
            "formal_phase": formal_phase,
            "formal_mapped_source_required": case["signal"][
                "mapped_source_required"
            ],
            "formal_route_mapped_traffic_light": case["source_availability"][
                "mapped_traffic_light"
            ],
            "phase_remaining_available": False,
            "regulatory_element_ids": [int(reg_id)],
            "physical_light_ids": (
                sorted(int(value.id) for value in params["refers"])
                if "refers" in params
                else []
            ),
            "bulb_ids": (
                sorted(int(value.id) for value in params["light_bulbs"])
                if "light_bulbs" in params
                else []
            ),
            "controlled_lanelet_ids": controlled,
            "route_lanelet_ids": route_ids,
            "route_geometry_sha256": _oracle_sha256(
                {
                    "route_polyline_local_m": semantic["route_polyline_local_m"],
                    "stop_line_local_m": semantic["stop_line_local_m"],
                }
            ),
            "stop_line_id": int(stop_line.id),
            "stop_line_geometry_m": stop.tolist(),
            "stop_line_geometry_sha256": _oracle_sha256(stop.tolist()),
            "stop_line_route_distance_m": distance,
            "route_arc_m": arc,
            "route_length_m": length,
            "route_tangent_world": tangent.tolist(),
            "semantic_clone_payload": semantic,
            "semantic_clone_sha256": _oracle_sha256(semantic),
            "source_chain_sha256": "",
        }
    chain["source_chain_sha256"] = _oracle_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return chain


def _decode_rows(
    tensor: np.ndarray, lanelet_ids: list[int], controlled: set[int]
) -> tuple[list[str], list[dict[str, Any]]]:
    phases: list[str] = []
    rows: list[dict[str, Any]] = []
    for index, lanelet_id in enumerate(lanelet_ids):
        if lanelet_id not in controlled:
            continue
        state = np.asarray(tensor[index, :, 8:13], dtype=np.float64)
        point_phases: list[str] = []
        for point in state:
            matches = []
            for phase, local in (("green", 0), ("yellow", 1), ("red", 2)):
                expected = np.zeros(5, dtype=np.float64)
                expected[local] = 1.0
                if np.allclose(point, expected, rtol=0.0, atol=1e-8):
                    matches.append(phase)
            if len(matches) != 1:
                raise ValueError("independent current phase is missing/multihot/unknown")
            point_phases.append(matches[0])
        if len(set(point_phases)) != 1:
            raise ValueError("independent controlled row has mixed phases")
        phases.append(point_phases[0])
        rows.append(
            {
                "lanelet_id": lanelet_id,
                "signal_channels_8_12": state.tolist(),
            }
        )
    return phases, rows


def _materialize_expected(
    case: Mapping[str, Any], builder: Any, chain: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    from scenario_generation.traffic_light import TrafficLightController

    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    route_lanes, _speed, _has_speed = builder._route_to_33dim(route_ids)
    route_row_ids = [value for value in route_ids[:25] if value in builder._cache]
    route_lanes = np.asarray(route_lanes[: len(route_row_ids)], dtype=np.float64)
    map_data = builder._build_map_data(route_ids)
    map_ids = [int(value) for value in builder._last_map_data_ids]
    controller = TrafficLightController(
        builder, route_ids, seed=int(case["seeds"][0])
    )
    controller.tick(SimpleNamespace(map_data=map_data), 0.0, map_ids, ego_xy=None)
    controller.write_to_route_lanes(route_lanes, route_row_ids, 0.0)
    map_lanes = np.asarray(map_data.lanes, dtype=np.float64)
    controlled = set(int(value) for value in chain["controlled_lanelet_ids"])
    if chain["phase_authority_mode"] == "controlled_same_tick_override":
        channel = {"green": 8, "yellow": 9, "red": 10}[
            chain["expected_current_phase"]
        ]
        for values, ids in ((route_lanes, route_row_ids), (map_lanes, map_ids)):
            for index, lanelet_id in enumerate(ids):
                if lanelet_id in controlled:
                    values[index, :, 8:13] = 0.0
                    values[index, :, channel] = 1.0
    route_phases, route_rows = _decode_rows(route_lanes, route_row_ids, controlled)
    map_phases, map_rows = _decode_rows(map_lanes, map_ids, controlled)
    phases = route_phases + map_phases
    if not phases or len(set(phases)) != 1:
        raise ValueError("independent route/map current phase differs")
    phase = phases[0]
    if (
        chain["phase_authority_mode"] == "controlled_same_tick_override"
        and phase != chain["expected_current_phase"]
    ):
        raise ValueError("independent controlled phase readback differs")
    route_hash = _oracle_sha256(route_rows)
    map_hash = _oracle_sha256(map_rows)
    receipt = {
        "schema_version": RUNTIME_RECEIPT_SCHEMA_VERSION,
        "scenario_id": str(case["scenario_id"]),
        "tick_index": 0,
        "phase_authority_mode": chain["phase_authority_mode"],
        "current_phase": phase,
        "decision_timestamp_s": 0.0,
        "source_timestamp_s": 0.0,
        "source_age_s": 0.0,
        "freshness": "same_tick",
        "source_id": CURRENT_REQUEST_SOURCE_ID,
        "regulatory_element_id": chain["regulatory_element_ids"][0],
        "physical_light_ids": list(chain["physical_light_ids"]),
        "bulb_ids": list(chain["bulb_ids"]),
        "controlled_lanelet_ids": list(chain["controlled_lanelet_ids"]),
        "stop_line_id": chain["stop_line_id"],
        "stop_line_geometry_sha256": chain["stop_line_geometry_sha256"],
        "route_geometry_sha256": chain["route_geometry_sha256"],
        "route_arc_m": chain["route_arc_m"],
        "source_chain_sha256": chain["source_chain_sha256"],
        "observed_route_lanelet_ids": [row["lanelet_id"] for row in route_rows],
        "observed_map_lanelet_ids": [row["lanelet_id"] for row in map_rows],
        "route_signal_tensor_sha256": route_hash,
        "map_signal_tensor_sha256": map_hash,
        "phase_remaining_available": False,
        "source_valid": True,
        "applicable": phase == "red",
    }
    evidence = {
        "schema_version": "camp_dp_v25_same_tick_signal_tensor_evidence_v1",
        "scenario_id": str(case["scenario_id"]),
        "traffic_controller_seed": int(case["seeds"][0]),
        "decision_timestamp_s": 0.0,
        "source_timestamp_s": 0.0,
        "route_lanelet_ids": route_row_ids,
        "map_lanelet_ids": map_ids,
        "route_signal_rows": route_rows,
        "map_signal_rows": map_rows,
        "route_signal_tensor_sha256": route_hash,
        "map_signal_tensor_sha256": map_hash,
        "current_phase": phase,
        "phase_remaining_available": False,
        "future_schedule_consumed": False,
    }
    return receipt, evidence


def _oracle_id_free_tensor_layout(
    case: Mapping[str, Any], builder: Any
) -> dict[str, Any]:
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    route_lanes, _speed, _has_speed = builder._route_to_33dim(route_ids)
    route_row_count = len(
        [value for value in route_ids[:25] if value in builder._cache]
    )
    route = np.asarray(route_lanes[:route_row_count])
    map_data = builder._build_map_data(route_ids)
    mapped = np.asarray(map_data.lanes)
    if (
        route.ndim != 3
        or mapped.ndim != 3
        or route.shape[-1] != 33
        or mapped.shape[-1] != 33
    ):
        raise ValueError("independent fixed-DP request tensor layout is invalid")
    payload = {
        "schema_version": "camp_dp_v25_id_free_tensor_layout_v1",
        "route_tensor_shape": [int(value) for value in route.shape],
        "map_tensor_shape": [int(value) for value in mapped.shape],
        "signal_channel_slice": [8, 13],
        "lanelet_ids_included": False,
        "map_route_scenario_split_ids_included": False,
    }
    return {**payload, "layout_sha256": _oracle_sha256(payload)}


def _oracle_bounded_coverage_design(
    train: list[Mapping[str, Any]], receipts: list[Mapping[str, Any]]
) -> dict[str, Any]:
    rows = {str(row["scenario_id"]): row for row in receipts}
    executable = [case for case in train if case.get("runner_eligible") is True]
    if len(rows) != len(train) or len(executable) != EXPECTED_EXECUTABLE:
        raise ValueError("independent bounded coverage denominator drifted")

    def tie(case: Mapping[str, Any]) -> tuple[str, str, str]:
        row = rows[str(case["scenario_id"])]
        return (
            str(row["source_chain"]["semantic_clone_sha256"]),
            str(case["route_identity_sha256"]),
            str(case["scenario_id"]),
        )

    mapped = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "mapped_signal"
    ]
    no_signal = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "no_signal"
    ]
    if len(mapped) != EXPECTED_EXECUTABLE_MAPPED:
        raise ValueError("independent bounded mapped denominator drifted")
    selected = {str(case["scenario_id"]): case for case in mapped}
    primary_groups: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    for case in no_signal:
        key = (
            str(case["family"]),
            str(case["semantic_variant"]),
            str(case["tier"]),
            str(case["source_map_sha256"]),
        )
        primary_groups.setdefault(key, []).append(case)
    for group in primary_groups.values():
        chosen = min(group, key=tie)
        selected[str(chosen["scenario_id"])] = chosen

    def augment(value_for) -> int:
        universe = {value_for(case) for case in no_signal}
        selected_ids = set(selected)
        covered = {
            value_for(case)
            for case in no_signal
            if str(case["scenario_id"]) in selected_ids
        }
        for value in sorted(universe - covered):
            chosen = min(
                [case for case in no_signal if value_for(case) == value], key=tie
            )
            selected[str(chosen["scenario_id"])] = chosen
        return len(universe)

    corridor_count = augment(lambda case: str(case["corridor_group_sha256"]))
    layout_count = augment(
        lambda case: str(rows[str(case["scenario_id"])]["id_free_tensor_layout"]["layout_sha256"])
    )
    identity0 = executable[0]
    selected[str(identity0["scenario_id"])] = identity0
    selected_cases = sorted(selected.values(), key=tie)
    if len(selected_cases) > BOUNDED_COVERAGE_MAX_IDENTITIES:
        raise ValueError("independent bounded coverage exceeds the hard cap")
    selected_ids = {str(case["scenario_id"]) for case in selected_cases}
    if (
        any(str(case["scenario_id"]) not in selected_ids for case in mapped)
        or any(
            not any(str(case["scenario_id"]) in selected_ids for case in group)
            for group in primary_groups.values()
        )
    ):
        raise ValueError("independent bounded coverage leaves a cell uncovered")
    return {
        "schema_version": BOUNDED_COVERAGE_SCHEMA_VERSION,
        "status": "design_only_k8_not_authorized",
        "selection_rule": (
            "all_mapped_then_nosignal_family_semantic_variant_tier_source_map_"
            "cells_then_corridor_and_id_free_tensor_layout_augmentation"
        ),
        "tie_break_fields": [
            "semantic_clone_sha256",
            "route_identity_sha256",
            "scenario_id",
        ],
        "forbidden_selection_inputs": [
            "outcome",
            "score",
            "atom",
            "margin",
            "selected_index",
            "dp_private_latent",
        ],
        "selected_scenario_ids": [str(case["scenario_id"]) for case in selected_cases],
        "selected_identity_count": len(selected_cases),
        "mapped_selected_count": len(mapped),
        "no_signal_selected_count": len(selected_cases) - len(mapped),
        "no_signal_primary_cell_count": len(primary_groups),
        "no_signal_corridor_count": corridor_count,
        "no_signal_id_free_tensor_layout_count": layout_count,
        "formal_identity0_scenario_id": str(identity0["scenario_id"]),
        "formal_identity0_separate_64_tick_repeat_planned": True,
        "unique_identity_hard_cap": BOUNDED_COVERAGE_MAX_IDENTITIES,
        "k8_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
    }


def _builder_for(case: Mapping[str, Any], builders: dict[str, Any], dp_repo: Path) -> Any:
    map_path = str(case["source_map_path"])
    if map_path in builders:
        return builders[map_path]
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    path = Path(map_path)
    require_source_preserving_lanelet2_regulatory_adapter(path)
    sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
    sys.modules.pop("autoware_lanelet2_extension_python", None)
    install_lanelet2_projection_fallback(path)
    builder = LaneletSceneBuilder(map_path)
    builders[map_path] = builder
    return builder


def review(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")
    pointer_head = _git_head(ROOT)
    critical_manifest = build_critical_implementation_manifest(ROOT)
    dual_head = verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=args.expected_camp_source_head,
        current_pointer_head=pointer_head,
        implementation_manifest=critical_manifest,
    )
    if (
        pointer_head != args.expected_camp_pointer_head
        or not _tracked_clean(ROOT)
        or _git_head(args.dp_repo) != FIXED_DP_HEAD
        or not _tracked_clean(args.dp_repo)
    ):
        raise ValueError("CAMP/fixed-DP live authority drifted")
    fixed_dp_import_authority = _verify_dp_import_authority(args.dp_repo)
    source_seal = _verify_exact_payload_inventory(
        args.source_artifact,
        args.source_root_sha256,
        expected_paths=SOURCE_PAYLOAD_PATHS,
        label="A1.6/R0.6 source census",
    )
    verify_complete_seal(FORMAL_ARTIFACT, FORMAL_ROOT_SHA256, label="formal plan")
    report = _load(args.source_artifact / "report.json")
    receipts_payload = _load(
        args.source_artifact / "route_signal_source_receipts.json"
    )
    supplement = _load(
        args.source_artifact / "formal_route_source_contract_supplement.json"
    )
    expected_report_fields = {
        "schema_version",
        "status",
        "authority",
        "checks",
        "counts",
        "receipts_sha256",
        "supplement_sha256",
        "bounded_coverage_design",
        "bounded_coverage_design_sha256",
        "model_loaded",
        "simulator_started",
        "candidate_generation_started",
        "dp_forward_executed",
        "gpu_used",
        "training_executed",
        "calibration_executed",
        "scene_runtime_connected",
        "v2i_enabled",
        "full_config_preflight_started",
        "full_r_started",
        "fresh_b2_opened",
        "outcome_fields_consumed",
        "claim_authorized",
    }
    expected_authority_fields = {
        "camp_source_head",
        "camp_pointer_head",
        "pointer_only_changed_paths",
        "critical_implementation_manifest",
        "critical_implementation_manifest_sha256",
        "fixed_dp_head",
        "fixed_dp_repo",
        "fixed_dp_import_authority",
        "formal_root_sha256",
        "consumed_release_artifact",
        "consumed_release_root_sha256",
        "failed_preflight_artifact",
        "failed_preflight_root_sha256",
        "consumed_nonce",
        "consumed_marker_path",
        "consumed_marker_sha256",
        "gpu_compute_process_count",
        "free_bytes_before",
    }
    expected_check_fields = EXPECTED_SOURCE_CHECK_FIELDS
    expected_count_fields = {
        "formal_train_identity_count",
        "executable_identity_count",
        "retained_identity_count",
        "executable_mapped_signal_count",
        "executable_no_signal_count",
        "controlled_same_tick_override_count",
        "observe_same_tick_request_count",
        "source_failure_count",
    }
    authority = report.get("authority")
    checks = report.get("checks")
    counts = report.get("counts")
    if (
        not isinstance(authority, dict)
        or not isinstance(checks, dict)
        or not isinstance(counts, dict)
        or set(report) != expected_report_fields
        or set(authority) != expected_authority_fields
        or set(checks) != expected_check_fields
        or set(counts) != expected_count_fields
        or any(type(value) is not bool for value in checks.values())
        or any(type(value) is not int for value in counts.values())
        or type(authority.get("gpu_compute_process_count")) is not int
        or authority.get("gpu_compute_process_count") != 0
        or type(authority.get("free_bytes_before")) is not int
        or authority["free_bytes_before"] < MINIMUM_FREE_BYTES
    ):
        raise ValueError("source census report schema/type contract drifted")
    if (
        set(receipts_payload)
        != {
            "schema_version",
            "formal_artifact",
            "formal_root_sha256",
            "camp_source_head",
            "fixed_dp_head",
            "cases",
            "source_failures",
        }
        or set(supplement)
        != {
            "schema_version",
            "formal_artifact",
            "formal_root_sha256",
            "formal_train_case_count",
            "formal_composition_unchanged",
            "formal_composition_sha256",
            "source_semantics_only",
            "cases",
        }
        or receipts_payload.get("formal_artifact") != str(FORMAL_ARTIFACT)
        or receipts_payload.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or receipts_payload.get("camp_source_head") != args.expected_camp_source_head
        or receipts_payload.get("fixed_dp_head") != FIXED_DP_HEAD
        or supplement.get("formal_artifact") != str(FORMAL_ARTIFACT)
        or supplement.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or type(supplement.get("formal_train_case_count")) is not int
        or supplement.get("formal_train_case_count")
        != EXPECTED_EXECUTABLE + EXPECTED_RETAINED
    ):
        raise ValueError("source receipt/supplement top-level authority drifted")
    if (args.source_artifact / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("source census did not exit successfully")
    if (args.source_artifact / "HEADS").read_text(encoding="ascii").splitlines() != [
        f"camp_source_head={args.expected_camp_source_head}",
        f"camp_pointer_head={args.expected_camp_pointer_head}",
        f"fixed_dp_head={FIXED_DP_HEAD}",
    ]:
        raise ValueError("source census HEADS drifted")
    if not (args.source_artifact / "COMMAND").read_text(encoding="utf-8").strip():
        raise ValueError("source census COMMAND is empty")
    if (
        authority.get("consumed_release_artifact") != str(CONSUMED_RELEASE_ARTIFACT)
        or authority.get("failed_preflight_artifact")
        != str(FAILED_PREFLIGHT_ARTIFACT)
        or authority.get("consumed_marker_path") != str(CANONICAL_CONSUMED_MARKER)
    ):
        raise ValueError("source census diagnostic path authority drifted")
    verify_complete_seal(
        CONSUMED_RELEASE_ARTIFACT,
        CONSUMED_RELEASE_ROOT_SHA256,
        label="consumed full-config release",
    )
    verify_complete_seal(
        FAILED_PREFLIGHT_ARTIFACT,
        FAILED_PREFLIGHT_ROOT_SHA256,
        label="failed full-config preflight",
    )
    _validate_consumed_marker(Path(str(authority["consumed_marker_path"])))
    if (
        report.get("schema_version") != PRODUCER_SCHEMA_VERSION
        or report.get("status") != "passed_source_only_route_signal_authority_census"
        or receipts_payload.get("schema_version") != RECEIPTS_SCHEMA_VERSION
        or supplement.get("schema_version") != SUPPLEMENT_SCHEMA_VERSION
        or report.get("receipts_sha256") != _oracle_sha256(receipts_payload)
        or report.get("supplement_sha256") != _oracle_sha256(supplement)
        or report.get("authority", {}).get("camp_source_head")
        != args.expected_camp_source_head
        or report.get("authority", {}).get("camp_pointer_head")
        != args.expected_camp_pointer_head
        or not _strict_equal(
            report.get("authority", {}).get("pointer_only_changed_paths"),
            dual_head["pointer_only_changed_paths"],
        )
        or not _strict_equal(
            report.get("authority", {}).get("critical_implementation_manifest"),
            critical_manifest,
        )
        or report.get("authority", {}).get(
            "critical_implementation_manifest_sha256"
        )
        != full_r_canonical_sha256(critical_manifest)
        or report.get("authority", {}).get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("authority", {}).get("fixed_dp_repo")
        != str(CANONICAL_DP_REPO)
        or not _strict_equal(
            report.get("authority", {}).get("fixed_dp_import_authority"),
            fixed_dp_import_authority,
        )
        or report.get("authority", {}).get("formal_root_sha256")
        != FORMAL_ROOT_SHA256
        or report.get("authority", {}).get("consumed_release_root_sha256")
        != CONSUMED_RELEASE_ROOT_SHA256
        or report.get("authority", {}).get("failed_preflight_root_sha256")
        != FAILED_PREFLIGHT_ROOT_SHA256
        or report.get("authority", {}).get("consumed_nonce") != CONSUMED_NONCE
        or report.get("authority", {}).get("consumed_marker_sha256")
        != CONSUMED_MARKER_SHA256
        or any(
            report.get(name) is not False
            for name in (
                "model_loaded",
                "simulator_started",
                "candidate_generation_started",
                "dp_forward_executed",
                "gpu_used",
                "training_executed",
                "calibration_executed",
                "scene_runtime_connected",
                "v2i_enabled",
                "full_config_preflight_started",
                "full_r_started",
                "fresh_b2_opened",
                "claim_authorized",
            )
        )
        or report.get("outcome_fields_consumed") != []
        or not all(report.get("checks", {}).values())
    ):
        raise ValueError("source census report authority/status drifted")

    plan = _load_plain(FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    train = plan["train"]
    if (
        len(train) != EXPECTED_EXECUTABLE + EXPECTED_RETAINED
        or supplement.get("formal_composition_sha256") != _oracle_sha256(train)
        or supplement.get("formal_composition_unchanged") is not True
        or supplement.get("source_semantics_only") is not True
    ):
        raise ValueError("formal supplement composition binding drifted")
    actual_receipts = receipts_payload.get("cases")
    supplement_cases = supplement.get("cases")
    if (
        not isinstance(actual_receipts, list)
        or len(actual_receipts) != len(train)
        or receipts_payload.get("source_failures") != []
        or not isinstance(supplement_cases, list)
        or len(supplement_cases) != len(train)
    ):
        raise ValueError("source census denominator drifted")
    actual_by_id = {row.get("scenario_id"): row for row in actual_receipts}
    supplement_by_id = {row.get("scenario_id"): row for row in supplement_cases}
    if len(actual_by_id) != len(train) or len(supplement_by_id) != len(train):
        raise ValueError("source census scenario identities are not unique")

    builders: dict[str, Any] = {}
    independent_rows: list[dict[str, Any]] = []
    for case in sorted(train, key=lambda item: str(item["scenario_id"])):
        scenario_id = str(case["scenario_id"])
        actual = actual_by_id.get(scenario_id)
        if not isinstance(actual, dict):
            raise ValueError("source census identity is missing")
        builder = _builder_for(case, builders, args.dp_repo)
        if _file_sha256(Path(str(case["source_map_path"]))) != case["source_map_sha256"]:
            raise ValueError("independent source map SHA drifted")
        regs = _actual_regs(case, builder)
        mapped = bool(regs)
        if case["source_availability"]["mapped_traffic_light"] is not mapped:
            raise ValueError("independent formal/actual mapped classification differs")
        chain = _reconstruct_chain(case, builder, regs)
        expected: dict[str, Any] = {
            "scenario_id": scenario_id,
            "formal_case_sha256": _oracle_sha256(case),
            "runner_eligible": case["runner_eligible"],
            "retention_role": str(case["retention_role"]),
            "family": str(case["family"]),
            "tier": str(case["tier"]),
            "seed": int(case["seeds"][0]),
            "source_map_sha256": str(case["source_map_sha256"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "actual_mapped_signal": mapped,
            "id_free_tensor_layout": (
                _oracle_id_free_tensor_layout(case, builder)
                if case["runner_eligible"] is True
                else None
            ),
            "source_class": "mapped_signal" if mapped else "no_signal",
            "phase_authority_mode": (
                chain["phase_authority_mode"] if mapped else None
            ),
            "source_chain": chain,
        }
        if mapped:
            runtime, tensor = _materialize_expected(case, builder, chain)
            expected["runtime_receipt"] = runtime
            expected["tensor_evidence"] = tensor
        else:
            expected["runtime_receipt"] = None
            expected["tensor_evidence"] = None
        if not _strict_equal(actual, expected):
            raise ValueError(f"source receipt differs from independent oracle: {scenario_id}")
        expected_supplement = {
            "scenario_id": scenario_id,
            "formal_case_sha256": expected["formal_case_sha256"],
            "runner_eligible": expected["runner_eligible"],
            "retention_role": expected["retention_role"],
            "source_class": expected["source_class"],
            "phase_authority_mode": expected["phase_authority_mode"],
            "source_chain_sha256": chain["source_chain_sha256"],
            "runtime_receipt_sha256": (
                _oracle_sha256(expected["runtime_receipt"])
                if expected["runtime_receipt"] is not None
                else None
            ),
        }
        if not _strict_equal(supplement_by_id.get(scenario_id), expected_supplement):
            raise ValueError("source supplement row differs from independent oracle")
        independent_rows.append(expected)

    expected_bounded_design = _oracle_bounded_coverage_design(
        train, independent_rows
    )
    if (
        not _strict_equal(
            report.get("bounded_coverage_design"), expected_bounded_design
        )
        or report.get("bounded_coverage_design_sha256")
        != _oracle_sha256(expected_bounded_design)
    ):
        raise ValueError("bounded coverage design differs from independent oracle")

    executable = [row for row in independent_rows if row["runner_eligible"] is True]
    retained = [row for row in independent_rows if row["runner_eligible"] is False]
    mapped = sum(row["source_class"] == "mapped_signal" for row in executable)
    no_signal = sum(row["source_class"] == "no_signal" for row in executable)
    controlled = sum(
        row["phase_authority_mode"] == "controlled_same_tick_override"
        for row in executable
    )
    observed = sum(
        row["phase_authority_mode"] == "observe_same_tick_request"
        for row in executable
    )
    expected_counts = {
        "formal_train_identity_count": len(train),
        "executable_identity_count": len(executable),
        "retained_identity_count": len(retained),
        "executable_mapped_signal_count": mapped,
        "executable_no_signal_count": no_signal,
        "controlled_same_tick_override_count": controlled,
        "observe_same_tick_request_count": observed,
        "source_failure_count": 0,
    }
    expected_checks = {
        "all_1653_formal_train_identities_accounted": True,
        "all_1500_executable_source_qualified": True,
        "all_153_retained_preserved": True,
        "executable_146_mapped_signal": True,
        "executable_1354_no_signal": True,
        "mapped_21_controlled_same_tick_override": True,
        "mapped_125_observe_same_tick_request": True,
        "source_failures_empty": True,
        "future_schedule_not_consumed": True,
        "phase_remaining_unavailable": True,
        "no_model_simulator_candidate_dp_forward": True,
        "training_calibration_scene_v2i_fresh_outcome_closed": True,
        "bounded_coverage_design_within_320_identity_cap": True,
        "bounded_coverage_design_k8_not_executed": True,
    }
    if (
        len(executable) != EXPECTED_EXECUTABLE
        or len(retained) != EXPECTED_RETAINED
        or mapped != EXPECTED_EXECUTABLE_MAPPED
        or no_signal != EXPECTED_EXECUTABLE_NO_SIGNAL
        or controlled != EXPECTED_CONTROLLED
        or observed != EXPECTED_OBSERVED
        or not _strict_equal(report.get("counts"), expected_counts)
        or not _strict_equal(report.get("checks"), expected_checks)
    ):
        raise ValueError("independent source census counts drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_route_signal_source_review",
        "reviewed_artifact": str(args.source_artifact),
        "reviewed_root_sha256": source_seal["root_sha256"],
        "camp_source_head": args.expected_camp_source_head,
        "camp_pointer_head": args.expected_camp_pointer_head,
        "pointer_only_changed_paths": dual_head["pointer_only_changed_paths"],
        "critical_implementation_manifest_sha256": full_r_canonical_sha256(
            critical_manifest
        ),
        "fixed_dp_import_authority": fixed_dp_import_authority,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_root_sha256": FORMAL_ROOT_SHA256,
        "counts": expected_counts,
        "bounded_coverage_design": expected_bounded_design,
        "independent_checks": {
            "formal_actual_route_classification_recomputed": True,
            "regulatory_physical_bulb_stopline_route_arc_chain_recomputed": True,
            "same_tick_route_map_tensors_rebuilt": True,
            "controlled_override_readback_recomputed": True,
            "observed_request_phase_recomputed": True,
            "receipt_and_supplement_roots_recomputed": True,
            "future_schedule_unused": True,
            "phase_remaining_unavailable": True,
            "denominator_unchanged": True,
            "bounded_coverage_design_recomputed_without_outcome_or_k8": True,
        },
        "model_loaded": False,
        "simulator_started": False,
        "candidate_generation_started": False,
        "dp_forward_executed": False,
        "gpu_used": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }


def main() -> None:
    args = parse_args()
    report = review(args)
    args.output_dir.mkdir(parents=False)
    _write(args.output_dir / "report.json", report)
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={report['camp_source_head']}\n"
        f"camp_pointer_head={report['camp_pointer_head']}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = seal_artifact(args.output_dir, label="A1.6/R0.6 source review")
    _verify_exact_payload_inventory(
        args.output_dir,
        root_sha256,
        expected_paths=REVIEW_PAYLOAD_PATHS,
        label="A1.6.1 source review",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "root_sha256": root_sha256,
                "output_dir": str(args.output_dir),
                "counts": report["counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
