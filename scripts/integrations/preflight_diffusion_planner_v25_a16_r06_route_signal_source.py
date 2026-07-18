#!/usr/bin/env python3
"""Build the source-only A1.6/R0.6 route-level signal-authority census.

This gate opens no model, simulator, candidate generator, outcome, training, or
Fresh artifact.  It materializes only the fixed-DP route/map request tensors
needed to certify the current traffic-signal one-hot at decision tick zero.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
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
from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (  # noqa: E402
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    ROUTE_SOURCE_SUPPLEMENT_SCHEMA_VERSION,
    apply_controlled_same_tick_override,
    build_mapped_signal_runtime_receipt,
    observe_same_tick_request_phase,
    validate_mapped_signal_chain,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_no_signal_chain,
)


SCHEMA_VERSION = "camp_dp_v25_a161_route_signal_source_census_v2"
RECEIPTS_SCHEMA_VERSION = "camp_dp_v25_a161_route_signal_source_receipts_v2"
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
DP_IMPORT_PATHS = {
    "scenario_generation.traffic_light": "scenario_generation/traffic_light.py",
    "scenario_generation.gui.lanelet_scene_builder": (
        "scenario_generation/gui/lanelet_scene_builder.py"
    ),
}
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
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--expected-camp-source-head", required=True)
    parser.add_argument("--expected-camp-pointer-head", required=True)
    parser.add_argument("--consumed-release-artifact", type=Path, required=True)
    parser.add_argument("--failed-preflight-artifact", type=Path, required=True)
    parser.add_argument("--consumed-marker", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _canonical_bytes(payload: Any) -> bytes:
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(_canonical_bytes(payload))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _validate_consumed_marker(
    path: Path,
    *,
    expected_path: Path,
    expected_sha256: str,
    expected_payload: Mapping[str, Any],
) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("consumed nonce marker must not be a symlink")
    if (
        not path.is_absolute()
        or str(path) != str(expected_path)
        or path.resolve() != expected_path.resolve()
    ):
        raise ValueError("consumed nonce marker canonical path drifted")
    if not path.is_file() or _sha256_file(path) != expected_sha256:
        raise ValueError("consumed nonce marker bytes drifted")
    payload = _load_json(path)
    if not isinstance(payload, dict) or not _strict_equal(payload, dict(expected_payload)):
        raise ValueError("consumed nonce marker schema/value/type drifted")
    return payload


def _verify_imported_dp_module(
    *,
    repo: Path,
    fixed_head: str,
    module: Any,
    relative_path: str,
) -> dict[str, str]:
    repo_real = repo.resolve()
    expected = repo_real / Path(relative_path)
    module_file = getattr(module, "__file__", None)
    if type(module_file) is not str or Path(module_file).resolve() != expected.resolve():
        raise ValueError("imported fixed-DP module is outside canonical fixed-DP repo")
    if expected.is_symlink() or not expected.is_file():
        raise ValueError("imported fixed-DP module path is unavailable or symlinked")
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_path],
        cwd=repo_real,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    committed = subprocess.run(
        ["git", "show", f"{fixed_head}:{relative_path}"],
        cwd=repo_real,
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
    receipts: dict[str, dict[str, str]] = {}
    for module_name, relative_path in DP_IMPORT_PATHS.items():
        module = importlib.import_module(module_name)
        receipts[module_name] = _verify_imported_dp_module(
            repo=dp_repo,
            fixed_head=FIXED_DP_HEAD,
            module=module,
            relative_path=relative_path,
        )
    return receipts


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


def _assert_lock_free() -> None:
    import fcntl

    existed = TRAIN_LOCK.exists()
    TRAIN_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with TRAIN_LOCK.open("a+", encoding="ascii") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("controlled-corpus lock is held") from exc
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    if not existed:
        TRAIN_LOCK.unlink(missing_ok=True)


def _gpu_compute_process_count() -> int:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError("GPU process inventory is unavailable")
    return len([line for line in completed.stdout.splitlines() if line.strip()])


def _route_polyline(builder: Any, route_ids: list[int]) -> np.ndarray:
    pieces: list[np.ndarray] = []
    for lanelet_id in route_ids:
        if lanelet_id not in builder._cache:
            raise ValueError("formal route lanelet is missing from actual map")
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        if line.ndim != 2 or line.shape[1] != 2 or len(line) < 2:
            raise ValueError("formal route centerline is invalid")
        pieces.append(line if not pieces else line[1:])
    route = np.concatenate(pieces, axis=0)
    if not np.isfinite(route).all() or len(route) < 2:
        raise ValueError("formal route geometry is invalid")
    return route


def _project_stop_to_controlled_route(
    builder: Any,
    route_ids: list[int],
    controlled_ids: list[int],
    stop_points: np.ndarray,
) -> tuple[float, float, float, np.ndarray]:
    midpoint = np.asarray(stop_points, dtype=np.float64).mean(axis=0)
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
                    np.clip(
                        ((midpoint - start) @ vector) / (length * length),
                        0.0,
                        1.0,
                    )
                )
            )
            if lanelet_id in controlled_ids and length > 1e-12:
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
        raise ValueError("certified stop line has no controlled route projection")
    return best[0], best[1], route_offset, best[2]


def _actual_route_regulatory_elements(
    case: Mapping[str, Any], builder: Any
) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for lanelet_id in case["route_spec"]["lanelet_ids"]:
        lanelet = builder._ll_by_id.get(int(lanelet_id))
        if lanelet is None:
            raise ValueError("formal route lanelet is absent from actual map")
        for reg in lanelet.trafficLights():
            row = result.setdefault(int(reg.id), {"reg": reg, "lanelet_ids": []})
            row["lanelet_ids"].append(int(lanelet_id))
    return result


def _extract_mapped_chain(
    case: Mapping[str, Any], builder: Any, regs: Mapping[int, Mapping[str, Any]]
) -> dict[str, Any]:
    if len(regs) != 1:
        raise ValueError("mapped route must have exactly one regulatory element")
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    reg_id, row = next(iter(regs.items()))
    reg = row["reg"]
    params = reg.parameters
    physical = (
        sorted(int(value.id) for value in params["refers"])
        if "refers" in params
        else []
    )
    bulbs = (
        sorted(int(value.id) for value in params["light_bulbs"])
        if "light_bulbs" in params
        else []
    )
    stop_line = reg.stopLine
    if stop_line is None:
        raise ValueError("mapped regulatory element has no certified stop line")
    stop = np.asarray([(point.x, point.y) for point in stop_line], dtype=np.float64)
    controlled = sorted(set(int(value) for value in row["lanelet_ids"]))
    distance, arc, length, tangent = _project_stop_to_controlled_route(
        builder, route_ids, controlled, stop
    )
    route_world = _route_polyline(builder, route_ids)
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route_world, stop_line_world=stop
    )
    formal_phase = str(case["signal"]["phase"])
    controlled_override = formal_phase in {"green", "yellow", "red"}
    mode = (
        "controlled_same_tick_override"
        if controlled_override
        else "observe_same_tick_request"
    )
    chain: dict[str, Any] = {
        "schema_version": MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": str(case["scenario_id"]),
        "route_identity_sha256": str(case["route_identity_sha256"]),
        "source_map_sha256": str(case["source_map_sha256"]),
        "phase_authority_mode": mode,
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
        "physical_light_ids": physical,
        "bulb_ids": bulbs,
        "controlled_lanelet_ids": controlled,
        "route_lanelet_ids": route_ids,
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": int(stop_line.id),
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
        "stop_line_route_distance_m": distance,
        "route_arc_m": arc,
        "route_length_m": length,
        "route_tangent_world": tangent.tolist(),
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return validate_mapped_signal_chain(chain)


def _extract_no_signal_chain(
    case: Mapping[str, Any], builder: Any, regs: Mapping[int, Mapping[str, Any]]
) -> dict[str, Any]:
    if regs:
        raise ValueError("no-signal route has actual signal authority")
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    semantic = build_semantic_clone_payload(
        case,
        route_polyline_world=_route_polyline(builder, route_ids),
        stop_line_world=None,
    )
    chain: dict[str, Any] = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": str(case["scenario_id"]),
        "route_identity_sha256": str(case["route_identity_sha256"]),
        "source_map_sha256": str(case["source_map_sha256"]),
        "route_lanelet_ids": route_ids,
        "route_geometry_sha256": canonical_json_sha256(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return validate_no_signal_chain(chain)


def _materialize_current_request(
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
    scene = SimpleNamespace(map_data=map_data)
    controller.tick(scene, 0.0, map_ids, ego_xy=None)
    controller.write_to_route_lanes(route_lanes, route_row_ids, 0.0)
    map_lanes = np.asarray(map_data.lanes, dtype=np.float64)
    if chain["phase_authority_mode"] == "controlled_same_tick_override":
        route_lanes, map_lanes = apply_controlled_same_tick_override(
            chain,
            route_tensor=route_lanes,
            route_lanelet_ids=route_row_ids,
            map_tensor=map_lanes,
            map_lanelet_ids=map_ids,
        )
    receipt = build_mapped_signal_runtime_receipt(
        chain,
        tick_index=0,
        decision_timestamp_s=0.0,
        source_timestamp_s=0.0,
        route_tensor=route_lanes,
        route_lanelet_ids=route_row_ids,
        map_tensor=map_lanes,
        map_lanelet_ids=map_ids,
    )
    observed = observe_same_tick_request_phase(
        chain,
        route_tensor=route_lanes,
        route_lanelet_ids=route_row_ids,
        map_tensor=map_lanes,
        map_lanelet_ids=map_ids,
    )
    evidence = {
        "schema_version": "camp_dp_v25_same_tick_signal_tensor_evidence_v1",
        "scenario_id": str(case["scenario_id"]),
        "traffic_controller_seed": int(case["seeds"][0]),
        "decision_timestamp_s": 0.0,
        "source_timestamp_s": 0.0,
        "route_lanelet_ids": route_row_ids,
        "map_lanelet_ids": map_ids,
        "route_signal_rows": observed["route_signal_rows"],
        "map_signal_rows": observed["map_signal_rows"],
        "route_signal_tensor_sha256": observed["route_signal_tensor_sha256"],
        "map_signal_tensor_sha256": observed["map_signal_tensor_sha256"],
        "current_phase": observed["current_phase"],
        "phase_remaining_available": False,
        "future_schedule_consumed": False,
    }
    return receipt, evidence


def _id_free_tensor_layout(case: Mapping[str, Any], builder: Any) -> dict[str, Any]:
    """Describe request tensor layout without map/lanelet/scenario identifiers."""

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
        raise ValueError("fixed-DP request tensor layout is invalid")
    payload = {
        "schema_version": "camp_dp_v25_id_free_tensor_layout_v1",
        "route_tensor_shape": [int(value) for value in route.shape],
        "map_tensor_shape": [int(value) for value in mapped.shape],
        "signal_channel_slice": [8, 13],
        "lanelet_ids_included": False,
        "map_route_scenario_split_ids_included": False,
    }
    return {
        **payload,
        "layout_sha256": canonical_json_sha256(payload),
    }


def _bounded_coverage_design(
    train: list[Mapping[str, Any]], receipts: list[Mapping[str, Any]]
) -> dict[str, Any]:
    """Build an outcome-blind draft only; this function never runs fixed DP."""

    rows = {str(row["scenario_id"]): row for row in receipts}
    executable = [case for case in train if case.get("runner_eligible") is True]
    if len(rows) != len(train) or len(executable) != EXPECTED_EXECUTABLE:
        raise ValueError("bounded coverage design denominator drifted")

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
        raise ValueError("bounded coverage design mapped denominator drifted")
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

    def augment(field_value) -> int:
        universe = {field_value(case) for case in no_signal}
        selected_ids = set(selected)
        covered = {
            field_value(case)
            for case in no_signal
            if str(case["scenario_id"]) in selected_ids
        }
        for value in sorted(universe - covered):
            candidates = [case for case in no_signal if field_value(case) == value]
            chosen = min(candidates, key=tie)
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
        raise ValueError("bounded coverage design exceeds the 320-identity hard cap")
    selected_ids = {str(case["scenario_id"]) for case in selected_cases}
    if (
        any(str(case["scenario_id"]) not in selected_ids for case in mapped)
        or any(
            not any(str(case["scenario_id"]) in selected_ids for case in group)
            for group in primary_groups.values()
        )
    ):
        raise ValueError("bounded coverage design leaves a required cell uncovered")
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


def _builder_for(
    case: Mapping[str, Any], builders: dict[str, Any], dp_repo: Path
) -> Any:
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


def _preconditions(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")
    camp_head = _git_head(ROOT)
    if camp_head != args.expected_camp_pointer_head or not _tracked_clean(ROOT):
        raise ValueError("CAMP pointer HEAD drifted or tracked worktree is dirty")
    critical_manifest = build_critical_implementation_manifest(ROOT)
    dual_head = verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=args.expected_camp_source_head,
        current_pointer_head=camp_head,
        implementation_manifest=critical_manifest,
    )
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or not _tracked_clean(args.dp_repo):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    fixed_dp_import_authority = _verify_dp_import_authority(args.dp_repo)
    _assert_lock_free()
    gpu_processes = _gpu_compute_process_count()
    if gpu_processes != 0:
        raise RuntimeError("GPU compute process is active")
    formal = verify_complete_seal(
        FORMAL_ARTIFACT, FORMAL_ROOT_SHA256, label="sealed formal plan"
    )
    if (
        args.consumed_release_artifact.resolve()
        != CONSUMED_RELEASE_ARTIFACT.resolve()
        or args.failed_preflight_artifact.resolve()
        != FAILED_PREFLIGHT_ARTIFACT.resolve()
    ):
        raise ValueError("consumed diagnostic artifact path authority drifted")
    release = verify_complete_seal(
        args.consumed_release_artifact,
        CONSUMED_RELEASE_ROOT_SHA256,
        label="consumed full-config release",
    )
    failed = verify_complete_seal(
        args.failed_preflight_artifact,
        FAILED_PREFLIGHT_ROOT_SHA256,
        label="failed full-config preflight",
    )
    if (args.consumed_release_artifact / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("consumed release run.exit drifted")
    if (args.failed_preflight_artifact / "run.exit").read_text(encoding="ascii") != "1\n":
        raise ValueError("failed preflight run.exit drifted")
    _validate_consumed_marker(
        args.consumed_marker,
        expected_path=CANONICAL_CONSUMED_MARKER,
        expected_sha256=CONSUMED_MARKER_SHA256,
        expected_payload=CANONICAL_CONSUMED_MARKER_PAYLOAD,
    )
    return {
        "camp_source_head": args.expected_camp_source_head,
        "camp_pointer_head": camp_head,
        "pointer_only_changed_paths": dual_head["pointer_only_changed_paths"],
        "critical_implementation_manifest": critical_manifest,
        "critical_implementation_manifest_sha256": full_r_canonical_sha256(
            critical_manifest
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "fixed_dp_repo": str(CANONICAL_DP_REPO),
        "fixed_dp_import_authority": fixed_dp_import_authority,
        "formal_root_sha256": formal["root_sha256"],
        "consumed_release_artifact": str(args.consumed_release_artifact),
        "consumed_release_root_sha256": release["root_sha256"],
        "failed_preflight_artifact": str(args.failed_preflight_artifact),
        "failed_preflight_root_sha256": failed["root_sha256"],
        "consumed_nonce": CONSUMED_NONCE,
        "consumed_marker_path": str(args.consumed_marker),
        "consumed_marker_sha256": CONSUMED_MARKER_SHA256,
        "gpu_compute_process_count": gpu_processes,
        "free_bytes_before": shutil.disk_usage(args.output_dir.parent).free,
    }


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    authority = _preconditions(args)
    formal_report = _load_json(FORMAL_ARTIFACT / "report.json")
    plan = _load_json(FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    train = plan.get("train")
    if (
        formal_report.get("fresh_b_opened") is not False
        or formal_report.get("outcome_fields_consumed") != []
        or plan.get("fresh_b_outcome_opened") is not False
        or plan.get("outcome_fields_consumed") != []
        or not isinstance(train, list)
        or len(train) != EXPECTED_EXECUTABLE + EXPECTED_RETAINED
    ):
        raise ValueError("formal train/Fresh/outcome authority drifted")
    executable = [case for case in train if case.get("runner_eligible") is True]
    retained = [case for case in train if case.get("runner_eligible") is False]
    if len(executable) != EXPECTED_EXECUTABLE or len(retained) != EXPECTED_RETAINED:
        raise ValueError("formal train denominator drifted")
    if any(case.get("seeds") != [EXPECTED_SEED] for case in train):
        raise ValueError("formal train seed drifted")

    builders: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for case in sorted(train, key=lambda item: str(item["scenario_id"])):
        try:
            builder = _builder_for(case, builders, args.dp_repo)
            if _sha256_file(Path(str(case["source_map_path"]))) != case["source_map_sha256"]:
                raise ValueError("source map SHA drifted")
            regs = _actual_route_regulatory_elements(case, builder)
            actual_mapped = bool(regs)
            declared_mapped = case["source_availability"]["mapped_traffic_light"]
            if type(declared_mapped) is not bool or declared_mapped is not actual_mapped:
                raise ValueError("formal/actual route mapped-signal classification differs")
            item: dict[str, Any] = {
                "scenario_id": str(case["scenario_id"]),
                "formal_case_sha256": canonical_json_sha256(case),
                "runner_eligible": case["runner_eligible"],
                "retention_role": str(case["retention_role"]),
                "family": str(case["family"]),
                "tier": str(case["tier"]),
                "seed": int(case["seeds"][0]),
                "source_map_sha256": str(case["source_map_sha256"]),
                "route_identity_sha256": str(case["route_identity_sha256"]),
                "actual_mapped_signal": actual_mapped,
                "id_free_tensor_layout": (
                    _id_free_tensor_layout(case, builder)
                    if case["runner_eligible"] is True
                    else None
                ),
            }
            if actual_mapped:
                chain = _extract_mapped_chain(case, builder, regs)
                runtime, tensor = _materialize_current_request(case, builder, chain)
                item.update(
                    {
                        "source_class": "mapped_signal",
                        "phase_authority_mode": chain["phase_authority_mode"],
                        "source_chain": chain,
                        "runtime_receipt": runtime,
                        "tensor_evidence": tensor,
                    }
                )
            else:
                chain = _extract_no_signal_chain(case, builder, regs)
                item.update(
                    {
                        "source_class": "no_signal",
                        "phase_authority_mode": None,
                        "source_chain": chain,
                        "runtime_receipt": None,
                        "tensor_evidence": None,
                    }
                )
            receipts.append(item)
        except Exception as exc:
            failures.append(
                {
                    "scenario_id": str(case.get("scenario_id")),
                    "runner_eligible": str(case.get("runner_eligible")),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    executable_rows = [row for row in receipts if row["runner_eligible"] is True]
    retained_rows = [row for row in receipts if row["runner_eligible"] is False]
    executable_mapped = sum(
        row["source_class"] == "mapped_signal" for row in executable_rows
    )
    executable_no_signal = sum(
        row["source_class"] == "no_signal" for row in executable_rows
    )
    controlled = sum(
        row["phase_authority_mode"] == "controlled_same_tick_override"
        for row in executable_rows
    )
    observed = sum(
        row["phase_authority_mode"] == "observe_same_tick_request"
        for row in executable_rows
    )
    checks = {
        "all_1653_formal_train_identities_accounted": (
            len(receipts) + len(failures) == EXPECTED_EXECUTABLE + EXPECTED_RETAINED
        ),
        "all_1500_executable_source_qualified": len(executable_rows) == EXPECTED_EXECUTABLE,
        "all_153_retained_preserved": len(retained_rows) == EXPECTED_RETAINED,
        "executable_146_mapped_signal": executable_mapped == EXPECTED_EXECUTABLE_MAPPED,
        "executable_1354_no_signal": executable_no_signal == EXPECTED_EXECUTABLE_NO_SIGNAL,
        "mapped_21_controlled_same_tick_override": controlled == EXPECTED_CONTROLLED,
        "mapped_125_observe_same_tick_request": observed == EXPECTED_OBSERVED,
        "source_failures_empty": failures == [],
        "future_schedule_not_consumed": all(
            row["tensor_evidence"] is None
            or row["tensor_evidence"]["future_schedule_consumed"] is False
            for row in receipts
        ),
        "phase_remaining_unavailable": all(
            row["runtime_receipt"] is None
            or row["runtime_receipt"]["phase_remaining_available"] is False
            for row in receipts
        ),
        "no_model_simulator_candidate_dp_forward": True,
        "training_calibration_scene_v2i_fresh_outcome_closed": True,
    }
    bounded_coverage_design = _bounded_coverage_design(train, receipts)
    checks["bounded_coverage_design_within_320_identity_cap"] = (
        bounded_coverage_design["selected_identity_count"]
        <= BOUNDED_COVERAGE_MAX_IDENTITIES
    )
    checks["bounded_coverage_design_k8_not_executed"] = (
        bounded_coverage_design["k8_executed"] is False
        and bounded_coverage_design["candidate_generation_started"] is False
    )
    receipt_payload = {
        "schema_version": RECEIPTS_SCHEMA_VERSION,
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": FORMAL_ROOT_SHA256,
        "camp_source_head": authority["camp_source_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "cases": receipts,
        "source_failures": failures,
    }
    supplement_cases = [
        {
            "scenario_id": row["scenario_id"],
            "formal_case_sha256": row["formal_case_sha256"],
            "runner_eligible": row["runner_eligible"],
            "retention_role": row["retention_role"],
            "source_class": row["source_class"],
            "phase_authority_mode": row["phase_authority_mode"],
            "source_chain_sha256": row["source_chain"]["source_chain_sha256"],
            "runtime_receipt_sha256": (
                canonical_json_sha256(row["runtime_receipt"])
                if row["runtime_receipt"] is not None
                else None
            ),
        }
        for row in receipts
    ]
    supplement = {
        "schema_version": ROUTE_SOURCE_SUPPLEMENT_SCHEMA_VERSION,
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": FORMAL_ROOT_SHA256,
        "formal_train_case_count": len(train),
        "formal_composition_unchanged": True,
        "formal_composition_sha256": canonical_json_sha256(train),
        "source_semantics_only": True,
        "cases": supplement_cases,
    }
    args.output_dir.mkdir(parents=False)
    _write_json(args.output_dir / "route_signal_source_receipts.json", receipt_payload)
    _write_json(
        args.output_dir / "formal_route_source_contract_supplement.json", supplement
    )
    status = (
        "passed_source_only_route_signal_authority_census"
        if all(checks.values())
        else "failed_source_only_route_signal_authority_census"
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "authority": authority,
        "checks": checks,
        "counts": {
            "formal_train_identity_count": len(train),
            "executable_identity_count": len(executable_rows),
            "retained_identity_count": len(retained_rows),
            "executable_mapped_signal_count": executable_mapped,
            "executable_no_signal_count": executable_no_signal,
            "controlled_same_tick_override_count": controlled,
            "observe_same_tick_request_count": observed,
            "source_failure_count": len(failures),
        },
        "receipts_sha256": canonical_json_sha256(receipt_payload),
        "supplement_sha256": canonical_json_sha256(supplement),
        "bounded_coverage_design": bounded_coverage_design,
        "bounded_coverage_design_sha256": canonical_json_sha256(
            bounded_coverage_design
        ),
        "model_loaded": False,
        "simulator_started": False,
        "candidate_generation_started": False,
        "dp_forward_executed": False,
        "gpu_used": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_connected": False,
        "v2i_enabled": False,
        "full_config_preflight_started": False,
        "full_r_started": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    _write_json(args.output_dir / "report.json", report)
    return report, 0 if status.startswith("passed_") else 1


def main() -> None:
    args = parse_args()
    report, exit_code = run(args)
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={report['authority']['camp_source_head']}\n"
        f"camp_pointer_head={report['authority']['camp_pointer_head']}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (args.output_dir / "run.exit").write_text(f"{exit_code}\n", encoding="ascii")
    root_sha256 = seal_artifact(args.output_dir, label="A1.6/R0.6 source census")
    _verify_exact_payload_inventory(
        args.output_dir,
        root_sha256,
        expected_paths=SOURCE_PAYLOAD_PATHS,
        label="A1.6.1 source census",
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
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
