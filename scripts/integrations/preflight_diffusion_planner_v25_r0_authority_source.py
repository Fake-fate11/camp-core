#!/usr/bin/env python3
"""Build the bounded V25 R0 authority and 21-red source qualification artifact."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import sys
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
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_no_signal_chain,
    validate_signal_chain,
)
from scripts.integrations.review_diffusion_planner_v25_stage_a0_authority import (  # noqa: E402
    PASSED_PREFLIGHT_ROOT,
    PASSED_REVIEW_ROOT,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    verify_config_assets,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _file_sha256,
    _load_json,
    _materialize_routes,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    EXPECTED_TEMPLATE_SHA256,
    FORMAL_ROOT_SHA256,
    MINIMUM_FREE_BYTES,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _canonical_sha256,
    _git_head,
    _load_formal_plan,
    _tracked_dirty,
    build_controlled_train_config,
)


SCHEMA_VERSION = "camp_dp_v25_r01_authority_source_preflight_v4"
A0_ROOT = "b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41"
PHYSICAL_SIGNATURE_SCHEMA_VERSION = "camp_dp_v25_signal_physical_signature_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--ultra-decision-artifact", type=Path, required=True)
    parser.add_argument("--ultra-decision-root-sha256", required=True)
    parser.add_argument("--a0-artifact", type=Path, required=True)
    parser.add_argument("--a0-root-sha256", required=True)
    parser.add_argument("--a1-ledger-artifact", type=Path, required=True)
    parser.add_argument("--a1-ledger-root-sha256", required=True)
    parser.add_argument("--a1-validation-artifact", type=Path, required=True)
    parser.add_argument("--a1-validation-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _route_polyline(builder: Any, route_ids: list[int]) -> np.ndarray:
    pieces = []
    for lanelet_id in route_ids:
        if lanelet_id not in builder._cache:
            raise ValueError("formal route lanelet is absent from map cache")
        values = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        pieces.append(values if not pieces else values[1:])
    result = np.concatenate(pieces, axis=0)
    if result.ndim != 2 or result.shape[1] != 2 or len(result) < 2:
        raise ValueError("formal route geometry is invalid")
    return result


def _project_stop_to_controlled_route(
    builder: Any,
    route_ids: list[int],
    controlled_ids: list[int],
    stop_points: np.ndarray,
) -> tuple[float, float, float, np.ndarray]:
    midpoint = np.asarray(stop_points, dtype=np.float64).mean(axis=0)
    route_offset = 0.0
    best: tuple[float, float, np.ndarray] | None = None
    total = 0.0
    for lanelet_id in route_ids:
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        local_offset = 0.0
        for start, end in zip(line[:-1], line[1:]):
            vector = end - start
            length = float(np.linalg.norm(vector))
            fraction = (
                0.0
                if length <= 1e-12
                else float(np.clip(((midpoint - start) @ vector) / (length * length), 0.0, 1.0))
            )
            if lanelet_id in controlled_ids:
                projected = start + fraction * vector
                distance = float(np.linalg.norm(midpoint - projected))
                tangent = vector / length if length > 1e-12 else np.zeros(2)
                candidate = (
                    distance,
                    route_offset + local_offset + fraction * length,
                    tangent,
                )
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            local_offset += length
        route_offset += local_offset
        total += local_offset
    if best is None:
        raise ValueError("stop line has no controlled route lanelet projection")
    return best[0], best[1], total, best[2]


def _physical_signature_payload(
    controlled_centerlines_world: list[np.ndarray],
    stop_points_world: np.ndarray,
    route_tangent_world: np.ndarray,
) -> dict[str, Any]:
    """Build an SE(2)-invariant physical signature without source or object IDs."""
    stop = np.asarray(stop_points_world, dtype=np.float64)
    tangent = np.asarray(route_tangent_world, dtype=np.float64)
    if stop.ndim != 2 or stop.shape[1] != 2 or len(stop) < 2:
        raise ValueError("physical signature stop line is invalid")
    norm = float(np.linalg.norm(tangent))
    if tangent.shape != (2,) or not np.isfinite(tangent).all() or norm <= 1e-12:
        raise ValueError("physical signature tangent is invalid")
    tangent = tangent / norm
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    basis = np.stack([tangent, normal], axis=1)
    origin = stop.mean(axis=0)
    local_stop = np.round((stop - origin) @ basis, 6).tolist()
    local_stop.sort()
    local_centerlines: list[list[list[float]]] = []
    for raw in controlled_centerlines_world:
        line = np.asarray(raw, dtype=np.float64)
        if (
            line.ndim != 2
            or line.shape[1] != 2
            or len(line) < 2
            or not np.isfinite(line).all()
        ):
            raise ValueError("physical signature controlled centerline is invalid")
        local = np.round((line - origin) @ basis, 6)
        if float(local[-1, 0]) < float(local[0, 0]):
            local = local[::-1]
        local_centerlines.append(local.tolist())
    local_centerlines.sort(key=canonical_json_sha256)
    return {
        "schema_version": PHYSICAL_SIGNATURE_SCHEMA_VERSION,
        "frame": "certified_stop_midpoint_route_tangent_normal",
        "controlled_centerlines_local_m": local_centerlines,
        "stop_line_local_m": local_stop,
    }


def _physical_signature_sha256(builder: Any, chain: Mapping[str, Any]) -> str:
    payload = _physical_signature_payload(
        [
            np.asarray(builder._cache[int(lanelet_id)].raw_centerline, dtype=np.float64)
            for lanelet_id in chain["controlled_lanelet_ids"]
        ],
        np.asarray(chain["stop_line_geometry_m"], dtype=np.float64),
        np.asarray(chain["route_tangent_world"], dtype=np.float64),
    )
    return canonical_json_sha256(payload)


def _extract_chain(case: Mapping[str, Any], builder: Any) -> dict[str, Any]:
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    regs: dict[int, dict[str, Any]] = {}
    for lanelet_id in route_ids:
        lanelet = builder._ll_by_id.get(lanelet_id)
        if lanelet is None:
            raise ValueError("formal route lanelet is missing")
        for reg in lanelet.trafficLights():
            entry = regs.setdefault(int(reg.id), {"reg": reg, "lanelet_ids": []})
            entry["lanelet_ids"].append(lanelet_id)
    if len(regs) != 1:
        raise ValueError("red route must map to exactly one TrafficLightRegulatoryElement")
    reg_id, entry = next(iter(regs.items()))
    reg = entry["reg"]
    params = reg.parameters
    physical = sorted(int(value.id) for value in params["refers"]) if "refers" in params else []
    bulbs = sorted(int(value.id) for value in params["light_bulbs"]) if "light_bulbs" in params else []
    stop = reg.stopLine
    if stop is None:
        raise ValueError("red route TrafficLightRegulatoryElement has no stop line")
    stop_points = np.asarray([(point.x, point.y) for point in stop], dtype=np.float64)
    controlled = sorted(set(int(value) for value in entry["lanelet_ids"]))
    distance, route_arc, route_length, route_tangent = _project_stop_to_controlled_route(
        builder, route_ids, controlled, stop_points
    )
    route_polyline = _route_polyline(builder, route_ids)
    semantic = build_semantic_clone_payload(
        case,
        route_polyline_world=route_polyline,
        stop_line_world=stop_points,
    )
    geometry_payload = {
        "route_polyline_local_m": semantic["route_polyline_local_m"],
        "stop_line_local_m": semantic["stop_line_local_m"],
    }
    chain: dict[str, Any] = {
        "schema_version": SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": str(case["scenario_id"]),
        "route_identity_sha256": str(case["route_identity_sha256"]),
        "source_map_sha256": str(case["source_map_sha256"]),
        "regulatory_element_ids": [reg_id],
        "physical_light_ids": physical,
        "bulb_ids": bulbs,
        "controlled_lanelet_ids": controlled,
        "route_lanelet_ids": route_ids,
        "route_geometry_sha256": canonical_json_sha256(geometry_payload),
        "stop_line_id": int(stop.id),
        "stop_line_geometry_m": stop_points.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop_points.tolist()),
        "stop_line_route_distance_m": distance,
        "route_arc_m": route_arc,
        "route_length_m": route_length,
        "route_tangent_world": route_tangent.tolist(),
        "expected_current_phase": str(case["signal"]["phase"]),
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return validate_signal_chain(chain)


def _extract_no_signal_chain(
    case: Mapping[str, Any], builder: Any
) -> dict[str, Any]:
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    regulatory_ids: set[int] = set()
    for lanelet_id in route_ids:
        lanelet = builder._ll_by_id.get(lanelet_id)
        if lanelet is None:
            raise ValueError("formal no-signal route lanelet is missing")
        regulatory_ids.update(int(reg.id) for reg in lanelet.trafficLights())
    if regulatory_ids:
        raise ValueError("formal no-signal route unexpectedly has signal authority")
    route_polyline = _route_polyline(builder, route_ids)
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route_polyline, stop_line_world=None
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


def _verify_input_artifacts(
    args: argparse.Namespace, *, current_head: str
) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for label, path, root in (
        ("ultra_decision", args.ultra_decision_artifact, args.ultra_decision_root_sha256),
        ("a0", args.a0_artifact, args.a0_root_sha256),
        ("a1_ledger", args.a1_ledger_artifact, args.a1_ledger_root_sha256),
        ("a1_validation", args.a1_validation_artifact, args.a1_validation_root_sha256),
    ):
        bindings[f"{label}_artifact"] = str(path)
        bindings[f"{label}_root_sha256"] = verify_complete_seal(
            path, root, label=label
        )["root_sha256"]
        if (path / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError(f"{label} run.exit is not zero")
    decision = _load_json(args.ultra_decision_artifact / "decision.json")
    a0_report = _load_json(args.a0_artifact / "report.json")
    ledger = _load_json(args.a1_ledger_artifact / "atom_ledger.json")
    validation = _load_json(args.a1_validation_artifact / "report.json")
    if (
        bindings["a0_root_sha256"] != A0_ROOT
        or decision.get("schema_version")
        != "camp_dp_v25_ultra_stage_a15_r05_decision_v6"
        or decision.get("status") != "A1_5_R0_5_only_released"
        or decision.get("corrected_source_head") != current_head
        or decision.get("fixed_dp_head") != FIXED_DP_HEAD
        or decision.get("s01_preflight_root_sha256") != PASSED_PREFLIGHT_ROOT
        or decision.get("s01_review_root_sha256") != PASSED_REVIEW_ROOT
        or decision.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or decision.get("a0_root_sha256") != bindings["a0_root_sha256"]
        or decision.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or decision.get("a1_5_authorized") is not True
        or decision.get("r0_5_source_authority_preflight_authorized") is not True
        or decision.get("full_r_authorized") is not False
        or a0_report.get("stage_a0_code_head") is None
        or a0_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or ledger.get("schema_version") != "camp_dp_v25_static_atom_ledger_v6"
        or ledger.get("authority", {}).get("stage_a_producer_head") != current_head
        or ledger.get("authority", {}).get("fixed_dp_head") != FIXED_DP_HEAD
        or ledger.get("authority", {}).get("a0_root_sha256")
        != bindings["a0_root_sha256"]
        or ledger.get("authority", {}).get("ultra_decision_root_sha256")
        != bindings["ultra_decision_root_sha256"]
        or validation.get("schema_version")
        != "camp_dp_v25_static_atom_ledger_validation_v6"
        or validation.get("status")
        != "passed_with_warnings_progress_source_valid_frozen"
        or validation.get("progress_reference")
        != "source_valid_candidate_set_reference"
        or validation.get("fail_count") != 0
        or validation.get("reviewed_root_sha256")
        != bindings["a1_ledger_root_sha256"]
    ):
        raise ValueError("R0 input authority is invalid")
    expected_heads = {
        "ultra_decision": [
            f"camp_head={current_head}", f"fixed_dp_head={FIXED_DP_HEAD}"
        ],
        "a0": [
            f"camp_head={a0_report['stage_a0_code_head']}",
            f"fixed_dp_head={FIXED_DP_HEAD}",
        ],
        "a1_ledger": [
            f"camp_head={current_head}", f"fixed_dp_head={FIXED_DP_HEAD}"
        ],
        "a1_validation": [
            f"camp_head={current_head}", f"fixed_dp_head={FIXED_DP_HEAD}"
        ],
    }
    for label, path in (
        ("ultra_decision", args.ultra_decision_artifact),
        ("a0", args.a0_artifact),
        ("a1_ledger", args.a1_ledger_artifact),
        ("a1_validation", args.a1_validation_artifact),
    ):
        if (path / "HEADS").read_text(encoding="ascii").splitlines() != expected_heads[
            label
        ]:
            raise ValueError(f"R0 input authority HEADS drifted: {label}")
    return bindings


def run(args: argparse.Namespace) -> dict[str, Any]:
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP drifted or is dirty")
    for path in (args.dp_repo, args.dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    if _file_sha256(args.probe_template) != EXPECTED_TEMPLATE_SHA256:
        raise ValueError("probe template SHA drifted")
    inputs = _verify_input_artifacts(args, current_head=head)
    plan, formal_root = _load_formal_plan()
    red_cases = [
        case
        for case in plan["train"]
        if case.get("runner_eligible") is True
        and case.get("family") == "red_light_phase_timing"
    ]
    if len(red_cases) != 21:
        raise ValueError("formal executable red denominator is not 21")
    builders: dict[str, Any] = {}
    chains = []
    for case in sorted(red_cases, key=lambda item: str(item["scenario_id"])):
        map_path = str(case["source_map_path"])
        if map_path not in builders:
            from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

            path = Path(map_path)
            require_source_preserving_lanelet2_regulatory_adapter(path)
            sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
            sys.modules.pop("autoware_lanelet2_extension_python", None)
            install_lanelet2_projection_fallback(path)
            builders[map_path] = LaneletSceneBuilder(map_path)
        chains.append(_extract_chain(case, builders[map_path]))
    chain_by_id = {chain["scenario_id"]: chain for chain in chains}
    physical_signature_by_id = {
        chain["scenario_id"]: _physical_signature_sha256(
            builders[str(next(
                case["source_map_path"]
                for case in red_cases
                if str(case["scenario_id"]) == chain["scenario_id"]
            ))],
            chain,
        )
        for chain in chains
    }
    selected = []
    for case in sorted(red_cases, key=lambda item: str(item["scenario_id"])):
        enriched = json.loads(json.dumps(case))
        chain = chain_by_id[str(case["scenario_id"])]
        enriched["red_signal_authority"] = chain
        enriched["canonical_semantic_clone_sha256"] = chain[
            "semantic_clone_sha256"
        ]
        selected.append(enriched)
    no_signal_case = None
    no_signal_chain = None
    for candidate in sorted(
        (
            item
            for item in plan["train"]
            if item.get("runner_eligible") is True
            and item.get("signal", {}).get("phase") == "none"
        ),
        key=lambda item: str(item["scenario_id"]),
    ):
        map_path = str(candidate["source_map_path"])
        if map_path not in builders:
            from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

            path = Path(map_path)
            require_source_preserving_lanelet2_regulatory_adapter(path)
            sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
            sys.modules.pop("autoware_lanelet2_extension_python", None)
            install_lanelet2_projection_fallback(path)
            builders[map_path] = LaneletSceneBuilder(map_path)
        try:
            no_signal_chain = _extract_no_signal_chain(candidate, builders[map_path])
        except ValueError:
            continue
        no_signal_case = json.loads(json.dumps(candidate))
        no_signal_case["no_signal_authority"] = no_signal_chain
        no_signal_case["canonical_semantic_clone_sha256"] = no_signal_chain[
            "semantic_clone_sha256"
        ]
        selected.append(no_signal_case)
        break
    if no_signal_case is None or no_signal_chain is None:
        raise ValueError("no executable source-qualified non-signal identity exists")
    route_assets = _materialize_routes(selected, args.output_dir / "routes", args.dp_repo)
    template = _load_json(args.probe_template)
    config_receipts = []
    for case in selected:
        config = build_controlled_train_config(
            template, case, route_assets[str(case["route_identity_sha256"])]
        )
        verify_config_assets(config)
        config_receipts.append(
            {
                "scenario_id": case["scenario_id"],
                "tier": case["tier"],
                "family": case["family"],
                "semantic_clone_sha256": case["canonical_semantic_clone_sha256"],
                "source_chain_sha256": (
                    case.get("red_signal_authority")
                    or case.get("no_signal_authority")
                )["source_chain_sha256"],
                "physical_signature_sha256": physical_signature_by_id.get(
                    str(case["scenario_id"])
                ),
                "config_sha256": _canonical_sha256(config),
                "config": config,
            }
        )
    tier_counts = collections.Counter(str(case["tier"]) for case in red_cases)
    observed_counts = {
        "source_map_files": len({chain["source_map_sha256"] for chain in chains}),
        "physical_signatures": len(
            set(physical_signature_by_id.values())
        ),
        "stop_line_geometry_shas": len(
            {chain["stop_line_geometry_sha256"] for chain in chains}
        ),
    }
    if observed_counts != {
        "source_map_files": 4,
        "physical_signatures": 9,
        "stop_line_geometry_shas": 5,
    }:
        raise ValueError(f"R0.5 physical authority census drifted: {observed_counts}")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_source_only_full_r_closed",
        "camp_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_root_sha256": formal_root,
        "s01_preflight_root_sha256": PASSED_PREFLIGHT_ROOT,
        "s01_review_root_sha256": PASSED_REVIEW_ROOT,
        **inputs,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "formal_executable_red_identity_count": len(red_cases),
        "red_by_tier": dict(tier_counts),
        "distinct_source_map_count": observed_counts["source_map_files"],
        "unique_regulatory_chain_count": len(chains),
        "validated_identity_chain_receipt_count": len(chains),
        "physical_signature_count": observed_counts["physical_signatures"],
        "physical_signature_sha256s": sorted(set(physical_signature_by_id.values())),
        "stop_line_geometry_sha256_count": observed_counts[
            "stop_line_geometry_shas"
        ],
        "non_signal_identity_count": 1,
        "all_source_chains_valid": True,
        "selected_bounded_probe_identity_count": len(selected),
        "selected_bounded_probe_scenario_ids": [case["scenario_id"] for case in selected],
        "config_receipts_root_sha256": canonical_json_sha256(config_receipts),
        "source_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "full_r_authorized": False,
        "full_r_started": False,
        "monitor_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_connected": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(args.output_dir / "red_signal_chains.json", {"chains": chains})
    _write_json(
        args.output_dir / "no_signal_chains.json", {"chains": [no_signal_chain]}
    )
    _write_json(args.output_dir / "bounded_red_cases.json", {"cases": selected})
    _write_json(args.output_dir / "config_receipts.json", {"receipts": config_receipts})
    return report


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = run(args)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 R0 authority/source preflight")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "full_r_started": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed R0 authority/source preflight")
        raise


if __name__ == "__main__":
    main()
