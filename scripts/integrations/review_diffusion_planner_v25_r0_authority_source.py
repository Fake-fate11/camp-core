#!/usr/bin/env python3
"""Independently review the V25 R0 21-red authority/source preflight."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
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
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _file_sha256,
    _load_json,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    FORMAL_ROOT_SHA256,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _canonical_sha256,
    _git_head,
    _load_formal_plan,
    _tracked_dirty,
)
from scripts.integrations.preflight_diffusion_planner_v25_r0_authority_source import (  # noqa: E402
    A0_ROOT,
)


SCHEMA_VERSION = "camp_dp_v25_r01_authority_source_review_v2"
SOURCE_SCHEMA_VERSION = "camp_dp_v25_r01_authority_source_preflight_v2"


def _native_bool_checks(checks: Mapping[str, Any]) -> dict[str, bool]:
    return {str(name): bool(value) for name, value in checks.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _route_geometry(builder: Any, route_ids: list[int]) -> np.ndarray:
    parts = []
    for lanelet_id in route_ids:
        values = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        parts.append(values if not parts else values[1:])
    return np.concatenate(parts, axis=0)


def _project(
    builder: Any,
    route_ids: list[int],
    controlled: set[int],
    stop: np.ndarray,
) -> tuple[float, float, float, np.ndarray]:
    point = stop.mean(axis=0)
    offset = 0.0
    best: tuple[float, float, np.ndarray] | None = None
    for lanelet_id in route_ids:
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        local = 0.0
        for start, end in zip(line[:-1], line[1:]):
            vector = end - start
            length = float(np.linalg.norm(vector))
            fraction = 0.0 if length <= 1e-12 else float(
                np.clip(((point - start) @ vector) / (length * length), 0.0, 1.0)
            )
            if lanelet_id in controlled:
                distance = float(np.linalg.norm(point - (start + fraction * vector)))
                tangent = vector / length if length > 1e-12 else np.zeros(2)
                candidate = (distance, offset + local + fraction * length, tangent)
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            local += length
        offset += local
    if best is None:
        raise ValueError("review found no controlled route projection")
    return best[0], best[1], offset, best[2]


def _independent_chain_checks(
    case: Mapping[str, Any], chain: Mapping[str, Any], builder: Any
) -> dict[str, bool]:
    validated = validate_signal_chain(chain)
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    regs = {}
    for lanelet_id in route_ids:
        for reg in builder._ll_by_id[lanelet_id].trafficLights():
            regs.setdefault(int(reg.id), {"reg": reg, "lanelets": []})[
                "lanelets"
            ].append(lanelet_id)
    if len(regs) != 1:
        raise ValueError("review found non-unique route regulatory element")
    reg_id, item = next(iter(regs.items()))
    reg = item["reg"]
    params = reg.parameters
    physical = sorted(int(value.id) for value in params["refers"]) if "refers" in params else []
    bulbs = sorted(int(value.id) for value in params["light_bulbs"]) if "light_bulbs" in params else []
    stop_line = reg.stopLine
    if stop_line is None:
        raise ValueError("review found no stop line")
    stop = np.asarray([(point.x, point.y) for point in stop_line], dtype=np.float64)
    controlled = sorted(set(int(value) for value in item["lanelets"]))
    distance, arc, length, tangent = _project(
        builder, route_ids, set(controlled), stop
    )
    semantic = build_semantic_clone_payload(
        case,
        route_polyline_world=_route_geometry(builder, route_ids),
        stop_line_world=stop,
    )
    geometry_sha = canonical_json_sha256(
        {
            "route_polyline_local_m": semantic["route_polyline_local_m"],
            "stop_line_local_m": semantic["stop_line_local_m"],
        }
    )
    checks = {
        "formal_identity_exact": validated["scenario_id"] == case["scenario_id"]
        and validated["route_identity_sha256"] == case["route_identity_sha256"],
        "map_sha_exact": validated["source_map_sha256"]
        == case["source_map_sha256"]
        and _file_sha256(Path(str(case["source_map_path"])))
        == case["source_map_sha256"],
        "unique_regulatory_exact": validated["regulatory_element_ids"] == [reg_id],
        "physical_lights_exact": validated["physical_light_ids"] == physical,
        "bulbs_exact": validated["bulb_ids"] == bulbs,
        "controlled_lanelets_exact": validated["controlled_lanelet_ids"] == controlled
        and validated["route_lanelet_ids"] == route_ids,
        "stop_line_exact": validated["stop_line_id"] == int(stop_line.id)
        and validated["stop_line_geometry_sha256"]
        == canonical_json_sha256(stop.tolist()),
        "route_arc_exact": np.isclose(
            validated["stop_line_route_distance_m"], distance, rtol=0.0, atol=1e-9
        )
        and np.isclose(validated["route_arc_m"], arc, rtol=0.0, atol=1e-9)
        and np.isclose(validated["route_length_m"], length, rtol=0.0, atol=1e-9),
        "route_tangent_exact": np.allclose(
            np.asarray(validated["route_tangent_world"], dtype=np.float64),
            tangent,
            rtol=0.0,
            atol=1e-9,
        ),
        "geometry_sha_exact": validated["route_geometry_sha256"] == geometry_sha,
        "semantic_clone_exact": validated["semantic_clone_payload"] == semantic
        and validated["semantic_clone_sha256"] == canonical_json_sha256(semantic),
        "same_tick_phase_exact": validated["expected_current_phase"]
        == case["signal"]["phase"],
    }
    if not all(checks.values()):
        raise ValueError(
            "independent red source-chain mismatch: "
            + ",".join(name for name, value in checks.items() if not value)
        )
    return _native_bool_checks(checks)


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP drifted or is dirty")
    for path in (args.dp_repo, args.dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    seal = verify_complete_seal(
        args.source_artifact, args.source_root_sha256, label="V25 R0 source"
    )
    if (args.source_artifact / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("R0 source run.exit is not zero")
    report = _load_json(args.source_artifact / "report.json")
    chain_payload = _load_json(args.source_artifact / "red_signal_chains.json")
    no_signal_payload = _load_json(args.source_artifact / "no_signal_chains.json")
    bounded = _load_json(args.source_artifact / "bounded_red_cases.json")
    config_payload = _load_json(args.source_artifact / "config_receipts.json")
    chains = chain_payload.get("chains")
    no_signal_chains = no_signal_payload.get("chains")
    receipts = config_payload.get("receipts")
    input_roots: dict[str, str] = {}
    for label in ("ultra_decision", "a0", "a1_ledger", "a1_validation"):
        artifact_key = f"{label}_artifact"
        root_key = f"{label}_root_sha256"
        artifact_value = report.get(artifact_key)
        root_value = report.get(root_key)
        if not isinstance(artifact_value, str) or not isinstance(root_value, str):
            raise ValueError("R0 source input-artifact binding is incomplete")
        artifact = Path(artifact_value)
        input_roots[label] = verify_complete_seal(
            artifact, root_value, label=f"R0 review {label}"
        )["root_sha256"]
        if (artifact / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError("R0 source input artifact has nonzero run.exit")
    decision = _load_json(Path(str(report["ultra_decision_artifact"])) / "decision.json")
    a0_report = _load_json(Path(str(report["a0_artifact"])) / "report.json")
    ledger = _load_json(Path(str(report["a1_ledger_artifact"])) / "atom_ledger.json")
    validation = _load_json(
        Path(str(report["a1_validation_artifact"])) / "report.json"
    )
    if (
        report.get("schema_version") != SOURCE_SCHEMA_VERSION
        or report.get("status") != "passed_source_only_full_r_closed"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or report.get("s01_preflight_root_sha256") != PASSED_PREFLIGHT_ROOT
        or report.get("s01_review_root_sha256") != PASSED_REVIEW_ROOT
        or report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or input_roots.get("a0") != A0_ROOT
        or decision.get("status") != "A1_1_R0_1_only_released"
        or decision.get("full_r_authorized") is not False
        or a0_report.get("status") != "passed"
        or ledger.get("status")
        != "passed_with_warnings_progress_source_valid_frozen"
        or validation.get("status")
        != "passed_with_warnings_progress_source_valid_frozen"
        or validation.get("fail_count") != 0
        or validation.get("reviewed_root_sha256")
        != input_roots.get("a1_ledger")
        or report.get("full_r_authorized") is not False
        or report.get("fresh_b2_opened") is not False
        or not isinstance(chains, list)
        or len(chains) != 21
        or not isinstance(receipts, list)
        or len(receipts) != 22
        or not isinstance(no_signal_chains, list)
        or len(no_signal_chains) != 1
        or report.get("distinct_source_map_count") != 4
        or report.get("physical_signature_count") != 9
        or report.get("stop_line_geometry_sha256_count") != 5
        or report.get("validated_identity_chain_receipt_count") != 21
        or report.get("config_receipts_root_sha256")
        != canonical_json_sha256(receipts)
    ):
        raise ValueError("R0 source report authority drifted")
    plan, formal_root = _load_formal_plan()
    if formal_root != FORMAL_ROOT_SHA256:
        raise ValueError("formal root drifted")
    red_cases = {
        str(case["scenario_id"]): case
        for case in plan["train"]
        if case.get("runner_eligible") is True
        and case.get("family") == "red_light_phase_timing"
    }
    if set(red_cases) != {str(chain.get("scenario_id")) for chain in chains}:
        raise ValueError("R0 chain denominator differs from formal red identities")
    builders: dict[str, Any] = {}
    reviewed = []
    for chain in chains:
        case = red_cases[str(chain["scenario_id"])]
        map_path = str(case["source_map_path"])
        if map_path not in builders:
            from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

            path = Path(map_path)
            require_source_preserving_lanelet2_regulatory_adapter(path)
            sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
            sys.modules.pop("autoware_lanelet2_extension_python", None)
            install_lanelet2_projection_fallback(path)
            builders[map_path] = LaneletSceneBuilder(map_path)
        checks = _independent_chain_checks(case, chain, builders[map_path])
        reviewed.append(
            {
                "scenario_id": case["scenario_id"],
                "chain_sha256": chain["source_chain_sha256"],
                "checks": checks,
            }
        )
    selected = bounded.get("cases")
    selected_ids = [case.get("scenario_id") for case in selected] if isinstance(selected, list) else []
    if (
        not isinstance(selected, list)
        or len(selected) != 22
        or collections.Counter(str(case.get("family")) for case in selected).get(
            "red_light_phase_timing"
        ) != 21
        or [case.get("scenario_id") for case in selected]
        != report.get("selected_bounded_probe_scenario_ids")
        or [receipt.get("scenario_id") for receipt in receipts] != selected_ids
        or any(
            case.get("red_signal_authority", {}).get("source_chain_sha256")
            != next(
                chain["source_chain_sha256"]
                for chain in chains
                if chain["scenario_id"] == case.get("scenario_id")
            )
            for case in selected
            if case.get("family") == "red_light_phase_timing"
        )
        or any(
            receipt.get("config_sha256") != _canonical_sha256(receipt.get("config"))
            for receipt in receipts
        )
        or any(
            receipt.get("tier") != case.get("tier")
            or receipt.get("semantic_clone_sha256")
            != case.get("canonical_semantic_clone_sha256")
            or receipt.get("source_chain_sha256")
            != (
                case.get("red_signal_authority")
                or case.get("no_signal_authority")
                or {}
            ).get("source_chain_sha256")
            or receipt.get("config", {}).get("controlled_scenario") != case
            or receipt.get("config", {}).get("fixed_dp", {}).get("head")
            != FIXED_DP_HEAD
            or receipt.get("config", {}).get("protocol", {}).get("corpus_steps")
            != 64
            or receipt.get("config", {}).get("protocol", {}).get("fresh_b_opened")
            is not False
            for case, receipt in zip(selected, receipts)
        )
    ):
        raise ValueError("R0 bounded case/config authority drifted")
    no_signal = validate_no_signal_chain(no_signal_chains[0])
    no_signal_case = next(
        case for case in selected if case.get("family") != "red_light_phase_timing"
    )
    if (
        no_signal.get("scenario_id") != no_signal_case.get("scenario_id")
        or no_signal_case.get("no_signal_authority") != no_signal
    ):
        raise ValueError("R0 no-signal authority binding drifted")
    map_path = Path(str(no_signal_case["source_map_path"]))
    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
    sys.modules.pop("autoware_lanelet2_extension_python", None)
    install_lanelet2_projection_fallback(map_path)
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    no_signal_builder = LaneletSceneBuilder(str(map_path))
    observed_regulatory_ids = sorted(
        {
            int(reg.id)
            for lanelet_id in no_signal["route_lanelet_ids"]
            for reg in no_signal_builder._ll_by_id[int(lanelet_id)].trafficLights()
        }
    )
    if observed_regulatory_ids:
        raise ValueError("R0 independent no-signal scan found a signal rule")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_source_review_full_r_closed",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(args.source_artifact),
        "reviewed_root_sha256": seal["root_sha256"],
        "reviewed_red_identity_count": len(reviewed),
        "reviewed_by_tier": dict(
            collections.Counter(str(red_cases[row["scenario_id"]]["tier"]) for row in reviewed)
        ),
        "reviewed_distinct_source_map_count": len(
            {case["source_map_sha256"] for case in red_cases.values()}
        ),
        "independent_chain_checks": reviewed,
        "bounded_probe_identity_count": len(selected),
        "reviewed_non_signal_identity_count": 1,
        "independent_no_signal_regulatory_scan": True,
        "full_r_authorized": False,
        "full_r_started": False,
        "monitor_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "producer_boolean_summary_trusted": False,
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 R0 authority/source review")
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
        seal_artifact(args.output_dir, label="V25 failed R0 source review")
        raise


if __name__ == "__main__":
    main()
