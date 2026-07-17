#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    FRESH_B_SEEDS,
    PILOT_SEEDS,
    SCENARIO_FAMILIES,
    V25ControlledSceneAdapter,
    build_controlled_scenario_plan,
    build_final_controlled_corpus_plan,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    build_native_arm_runner,
    validate_native_arm_receipt,
    validate_v25_controlled_capability_config,
    verify_config_assets,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_scenario_phase_v1"
OFFICIAL_COMMIT = "e22f01093fa6516c0552549ada302270329c59a4"
OFFICIAL_ANCHORS = (
    "test_runner/scenario_test_runner/scenario/LongitudinalAction.SpeedAction.yaml",
    "test_runner/scenario_test_runner/scenario/LateralAction.LaneChangeAction.yaml",
    "test_runner/scenario_test_runner/scenario/RoutingAction.AssignRouteAction-use_lane_ids_for_routing.yaml",
    "test_runner/scenario_test_runner/scenario/RoutingAction.FollowTrajectoryAction-straight-pedestrian.yaml",
    "test_runner/scenario_test_runner/scenario/TrafficSignalControllerAction.yaml",
)
FORMAL_FORBIDDEN_SEEDS = [11, 12, 13, 24001, 24002, 24003, 24004, 24005]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze and optionally execute the outcome-blind V25 controlled coverage pilot."
    )
    parser.add_argument("--route-census", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--official-repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--pilot-artifact", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute-pilot", action="store_true")
    mode.add_argument("--freeze-formal", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD drifted")
    if shutil.disk_usage(args.output_dir.parent).free < 10 * 1024**3:
        raise RuntimeError("free disk is below the 10 GiB floor")

    census = _load_json(args.route_census)
    split = _load_json(args.split_manifest)
    template = _load_json(args.probe_template)
    if census.get("schema") != "diffusion_planner_v24_outcome_blind_route_census_v1":
        raise ValueError("route census schema mismatch")
    if split.get("schema") != "camp_dp_v24_map_family_split_manifest_v1":
        raise ValueError("split manifest schema mismatch")
    plan = build_controlled_scenario_plan(census["retained_routes"], split["records"])
    official = _official_source_audit(args.official_repo)
    args.output_dir.mkdir(parents=True)
    _write_json(args.output_dir / "controlled_scenario_plan.json", plan.as_dict())
    _write_json(args.output_dir / "official_source_audit.json", official)
    source_receipt = {
        "route_census_path": str(args.route_census),
        "route_census_sha256": _file_sha256(args.route_census),
        "split_manifest_path": str(args.split_manifest),
        "split_manifest_sha256": _file_sha256(args.split_manifest),
        "probe_template_path": str(args.probe_template),
        "probe_template_sha256": _file_sha256(args.probe_template),
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": _git_head(args.dp_repo),
        "free_bytes_at_start": shutil.disk_usage(args.output_dir.parent).free,
    }
    _write_json(args.output_dir / "source_receipt.json", source_receipt)

    if args.freeze_formal:
        if args.pilot_artifact is None:
            raise ValueError("--freeze-formal requires --pilot-artifact")
        report = _freeze_formal(plan, args)
    elif args.preflight:
        report = _preflight(plan, template, args)
    else:
        report = _execute_pilot(plan, template, args)
    _write_json(args.output_dir / "report.json", report)
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={source_receipt['camp_head']}\n"
        f"fixed_dp_head={source_receipt['fixed_dp_head']}\n"
        f"official_scenario_simulator_v2_commit={OFFICIAL_COMMIT}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "mode": report["mode"],
                "output_dir": str(args.output_dir),
                "root_sha256": root_sha,
                "pilot_case_count": len(plan.pilot),
            },
            sort_keys=True,
        )
    )


def _freeze_formal(plan, args: argparse.Namespace) -> dict[str, Any]:
    availability = _audit_formal_route_sources(plan, args.dp_repo)
    census = _load_json(args.route_census)
    split = _load_json(args.split_manifest)
    final_plan = build_final_controlled_corpus_plan(
        census["retained_routes"], split["records"], availability
    )
    _write_json(args.output_dir / "formal_source_availability.json", availability)
    _write_json(args.output_dir / "controlled_corpus_final_plan.json", final_plan)
    pilot_review = _review_pilot_source_failures(args.pilot_artifact, plan, availability)
    _write_json(args.output_dir / "pilot_source_failure_review.json", pilot_review)
    checks = {
        "all_401_routes_source_audited": len(availability) == 401,
        "pilot_speed_failures_reproduced_source_only": pilot_review[
            "speed_failure_mismatch_count"
        ]
        == 0,
        "pilot_passes_have_speed_source": pilot_review[
            "passed_speed_source_mismatch_count"
        ]
        == 0,
        "formal_train_1500_executable": final_plan["summary"]["split_counts"][
            "train"
        ]["executable_identity_count"]
        == 1500,
        "combined_train_capacity_at_least_150k": final_plan["summary"][
            "combined_train_snapshot_capacity_at_64_ticks"
        ]
        >= 150_000,
        "fresh_b_120_identities": final_plan["summary"]["split_counts"][
            "fresh_b"
        ]["executable_identity_count"]
        == 120,
        "fresh_b_600_paired_runs": final_plan["summary"][
            "fresh_b_paired_run_count"
        ]
        == 600,
        "fresh_b_unopened": True,
        "outcome_fields_unused": True,
        "fixed_dp_unmodified": _git_head(args.dp_repo) == FIXED_DP_HEAD,
    }
    if not all(checks.values()):
        raise RuntimeError("formal controlled corpus freeze failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "freeze_formal",
        "status": "passed",
        "checks": checks,
        "source_summary": final_plan["summary"],
        "pilot_review": pilot_review,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }


def _audit_formal_route_sources(plan, dp_repo: Path) -> dict[str, dict[str, Any]]:
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    unique_cases = {}
    for case in (*plan.train, *plan.calibration, *plan.fresh_b):
        unique_cases.setdefault(str(case["record_key"]), case)
    builders = {}
    result = {}
    for record_key, case in sorted(unique_cases.items()):
        map_path = str(case["source_map_path"])
        if map_path not in builders:
            builders[map_path] = LaneletSceneBuilder(map_path)
        builder = builders[map_path]
        lanelet_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
        route_lanes, speed_limits, has_speed_limit = builder._route_to_33dim(
            lanelet_ids
        )
        active = np.any(np.abs(route_lanes[:, :, :2]) > 1e-8, axis=(1, 2))
        limits = np.asarray(speed_limits, dtype=np.float64).reshape(-1)
        has_limits = np.asarray(has_speed_limit, dtype=bool).reshape(-1)
        complete = bool(
            np.any(active)
            and np.all(has_limits[active])
            and np.all(np.isfinite(limits[active]))
            and np.all(limits[active] > 0.0)
        )
        traffic_groups = builder.get_traffic_light_groups()
        result[record_key] = {
            "record_key": record_key,
            "map_family_id": str(case["map_family_id"]),
            "source_map_path": map_path,
            "source_map_sha256": str(case["source_map_sha256"]),
            "route_lanelet_count": len(lanelet_ids),
            "active_route_slot_count": int(np.sum(active)),
            "positive_speed_limit_slot_count": int(
                np.sum(active & has_limits & np.isfinite(limits) & (limits > 0.0))
            ),
            "speed_limit_complete": complete,
            "mapped_traffic_light": any(
                lanelet_id in traffic_groups for lanelet_id in lanelet_ids
            ),
            "source_only": True,
            "model_loaded": False,
            "candidate_generation_started": False,
            "outcome_fields_consumed": [],
        }
    if len(result) != 401:
        raise ValueError("source audit did not cover the sealed 401-route inventory")
    return result


def _review_pilot_source_failures(
    pilot_artifact: Path,
    plan,
    availability: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    pilot_root_sha256 = _verify_seal(pilot_artifact)
    payload = _load_json(pilot_artifact / "pilot_results.json")
    cases = {str(case["scenario_id"]): case for case in plan.pilot}
    speed_failure_count = 0
    speed_failure_mismatches = []
    passed_count = 0
    passed_mismatches = []
    tracker_failure_count = 0
    for result in payload["results"]:
        scenario_id = str(result["scenario_id"])
        case = cases[scenario_id]
        source = availability[str(case["record_key"])]
        reason = result.get("failure_reason")
        if reason == "route slot 0 requires a positive speed limit":
            speed_failure_count += 1
            if source["speed_limit_complete"]:
                speed_failure_mismatches.append(scenario_id)
        elif result.get("status") == "passed":
            passed_count += 1
            if not source["speed_limit_complete"]:
                passed_mismatches.append(scenario_id)
        elif reason == "native replay produced no executed tracker tick":
            tracker_failure_count += 1
    return {
        "schema_version": "camp_dp_v25_pilot_source_failure_review_v1",
        "pilot_artifact": str(pilot_artifact),
        "pilot_root_sha256": pilot_root_sha256,
        "passed_count": passed_count,
        "speed_failure_count": speed_failure_count,
        "tracker_failure_count": tracker_failure_count,
        "speed_failure_mismatch_count": len(speed_failure_mismatches),
        "passed_speed_source_mismatch_count": len(passed_mismatches),
        "speed_failure_mismatch_scenario_ids": speed_failure_mismatches,
        "passed_speed_source_mismatch_scenario_ids": passed_mismatches,
        "outcome_fields_consumed": [],
        "fresh_b_opened": False,
    }


def _preflight(plan, template: Mapping[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    route_assets = _materialize_routes(plan.pilot, args.output_dir / "routes", args.dp_repo)
    configs = []
    shared_assets = None
    for case in plan.pilot:
        config = _build_config(template, case, route_assets[case["route_identity_sha256"]])
        validate_v25_controlled_capability_config(config)
        if shared_assets is None:
            verify_config_assets(config)
            shared_assets = _shared_asset_contract(config)
        elif _shared_asset_contract(config) != shared_assets:
            raise ValueError("shared fixed-DP or selector assets changed across pilot cases")
        _verify_case_assets(config)
        configs.append(
            {
                "scenario_id": case["scenario_id"],
                "route_identity_sha256": case["route_identity_sha256"],
                "config_sha256": _canonical_sha256(config),
                "verified_case_asset_count": 2,
            }
        )
    _write_json(args.output_dir / "pilot_config_receipts.json", {"receipts": configs})
    checks = {
        "official_commit_exact": True,
        "fixed_dp_head_exact": _git_head(args.dp_repo) == FIXED_DP_HEAD,
        "pilot_21_per_family": all(
            sum(case["family"] == family for case in plan.pilot) == 21
            for family in SCENARIO_FAMILIES
        ),
        "pilot_all_source_eligible": all(case["runner_eligible"] for case in plan.pilot),
        "train_identity_count_1500": len(plan.train) == 1500,
        "combined_train_capacity_at_least_150k": (
            plan.summary["combined_train_snapshot_capacity_at_64_ticks"] >= 150_000
        ),
        "fresh_b_route_ceiling_24": plan.summary["fresh_b_route_ceiling"] == 24,
        "fresh_b_corridor_ceiling_3": plan.summary["fresh_b_corridor_ceiling"] == 3,
        "fresh_b_paired_runs_600": plan.summary["fresh_b_paired_run_count"] == 600,
        "fresh_b_seed_namespace_exact": {
            seed for case in plan.fresh_b for seed in case["seeds"]
        }
        == set(FRESH_B_SEEDS),
        "fresh_b_outcomes_unopened": all(
            case["holdout_outcome_consumed"] is False for case in plan.fresh_b
        ),
        "all_configs_validate": len(configs) == len(plan.pilot),
        "disk_floor_passed": shutil.disk_usage(args.output_dir.parent).free >= 10 * 1024**3,
    }
    if not all(checks.values()):
        raise RuntimeError("controlled scenario preflight failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "preflight",
        "status": "passed",
        "checks": checks,
        "check_count": len(checks),
        "pilot_execution_started": False,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "fresh_b_opened": False,
        "claim_authorized": False,
    }


def _execute_pilot(plan, template: Mapping[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    route_assets = _materialize_routes(plan.pilot, args.output_dir / "routes", args.dp_repo)
    configs = [
        _build_config(template, case, route_assets[case["route_identity_sha256"]])
        for case in plan.pilot
    ]
    shared_assets = None
    for config in configs:
        validate_v25_controlled_capability_config(config)
        if shared_assets is None:
            verify_config_assets(config)
            shared_assets = _shared_asset_contract(config)
        elif _shared_asset_contract(config) != shared_assets:
            raise ValueError("shared fixed-DP or selector assets changed across pilot cases")
        _verify_case_assets(config)
    runner = build_native_arm_runner(configs[0], device=args.device)
    results = []
    progress_path = args.output_dir / "progress.json"
    started = time.perf_counter()
    for index, (case, config) in enumerate(zip(plan.pilot, configs, strict=True)):
        case_started = time.perf_counter()
        snapshots: list[Mapping[str, Any]] = []
        contexts: list[Mapping[str, Any]] = []
        adapter = V25ControlledSceneAdapter(case)
        try:
            receipt = runner(
                route=config["routes"][0],
                arm="camp",
                config=config,
                output_dir=args.output_dir / "native_runs" / case["scenario_id"],
                max_steps=1,
                decision_sink=snapshots.append,
                scene_adapter=adapter,
                v25_context_sink=contexts.append,
            )
            validate_native_arm_receipt(
                receipt,
                "camp",
                expected_ticks=1,
                require_summary=False,
                expected_selection_policy="v22_source_valid",
                expected_safety_schema="safety_cost_native_v22",
            )
            if len(snapshots) != 1 or len(contexts) != 1 or len(adapter.receipts) != 1:
                raise ValueError("controlled pilot emitted an unexpected receipt count")
            tick = receipt["ticks"][0]
            snapshot = snapshots[0]
            context = contexts[0]
            results.append(
                {
                    "scenario_id": case["scenario_id"],
                    "family": case["family"],
                    "tier": case["tier"],
                    "semantic_variant": case["semantic_variant"],
                    "status": "passed",
                    "atom_matrix": snapshot["feature_payload"]["atom_matrix"],
                    "source_valid_mask": snapshot["feature_payload"]["source_valid_mask"],
                    "raw_context": context["raw_context"],
                    "context_source_complete": context["source_complete"],
                    "candidate_tensor_sha256_before": tick[
                        "candidate_tensor_sha256_before"
                    ],
                    "candidate_tensor_sha256_after": tick[
                        "candidate_tensor_sha256_after"
                    ],
                    "selected_index": tick["selected_index"],
                    "controlled_scene": adapter.receipts[0],
                    "latency_ms": tick["latency_ms"],
                    "wall_seconds": time.perf_counter() - case_started,
                    "outcome_fields_consumed": [],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "scenario_id": case["scenario_id"],
                    "family": case["family"],
                    "tier": case["tier"],
                    "semantic_variant": case["semantic_variant"],
                    "status": "failed",
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "wall_seconds": time.perf_counter() - case_started,
                    "outcome_fields_consumed": [],
                }
            )
        _write_json(
            progress_path,
            {
                "schema_version": "camp_dp_v25_controlled_pilot_progress_v1",
                "completed": index + 1,
                "total": len(configs),
                "passed": sum(item["status"] == "passed" for item in results),
                "failed": sum(item["status"] == "failed" for item in results),
                "last_scenario_id": case["scenario_id"],
                "elapsed_seconds": time.perf_counter() - started,
            },
        )

    _write_json(args.output_dir / "pilot_results.json", {"results": results})
    analysis = _pilot_analysis(results)
    _write_json(args.output_dir / "pilot_analysis.json", analysis)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "execute_pilot",
        "status": analysis["status"],
        "pilot_case_count": len(results),
        "passed_case_count": sum(item["status"] == "passed" for item in results),
        "failed_case_count": sum(item["status"] == "failed" for item in results),
        "analysis": analysis,
        "wall_seconds": time.perf_counter() - started,
        "outcome_fields_consumed": [],
        "outcomes_used_for_scenario_selection": False,
        "fresh_b_opened": False,
        "training_executed": False,
        "calibration_executed": False,
        "claim_authorized": False,
    }


def _pilot_analysis(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    passed = [item for item in results if item["status"] == "passed"]
    family_reports = {}
    for family in SCENARIO_FAMILIES:
        rows = [item for item in passed if item["family"] == family]
        atom_report = {}
        context_report = {}
        if rows:
            atoms = np.asarray([item["atom_matrix"] for item in rows], dtype=np.float64)
            for atom_index, atom_name in enumerate(DP_CAMP_ATOM_NAMES_V10):
                values = atoms[:, :, atom_index]
                atom_report[atom_name] = {
                    "nonzero_fraction": float(np.mean(values > 1e-12)),
                    "candidate_discrimination_mean_range": float(
                        np.mean(np.ptp(values, axis=1))
                    ),
                    "minimum": float(np.min(values)),
                    "maximum": float(np.max(values)),
                }
            for feature in RAW_FEATURE_NAMES:
                values = np.asarray([row["raw_context"][feature] for row in rows])
                context_report[feature] = {
                    "minimum": float(np.min(values)),
                    "maximum": float(np.max(values)),
                    "unique_count": int(np.unique(values).size),
                }
        family_reports[family] = {
            "planned_count": sum(item["family"] == family for item in results),
            "passed_count": len(rows),
            "failed_count": sum(
                item["family"] == family and item["status"] == "failed"
                for item in results
            ),
            "atom_activation": atom_report,
            "context_variation": context_report,
            "any_atom_candidate_discrimination": any(
                value["candidate_discrimination_mean_range"] > 1e-10
                for value in atom_report.values()
            ),
            "varied_context_feature_count": sum(
                value["unique_count"] > 1 for value in context_report.values()
            ),
        }
    checks = {
        "all_147_cases_retained": len(results) == 147,
        "at_least_20_executed_per_family": all(
            report["passed_count"] >= 20 for report in family_reports.values()
        ),
        "all_required_context_sources_complete": all(
            _required_context_complete(item) for item in passed
        ),
        "all_candidate_tensors_immutable": all(
            item["candidate_tensor_sha256_before"]
            == item["candidate_tensor_sha256_after"]
            for item in passed
        ),
        "all_fixed_k8_source_valid": all(
            len(item["source_valid_mask"]) == 8
            and all(item["source_valid_mask"])
            for item in passed
        ),
        "each_family_activates_candidate_discrimination": all(
            report["any_atom_candidate_discrimination"]
            for report in family_reports.values()
        ),
        "each_family_varies_context": all(
            report["varied_context_feature_count"] > 0
            for report in family_reports.values()
        ),
    }
    science_findings = _monotonicity_findings(passed)
    capability_passed = all(checks.values())
    return {
        "status": "passed" if capability_passed else "completed_with_limitations",
        "checks": checks,
        "family_reports": family_reports,
        "monotonicity_findings": science_findings,
        "monotonicity_is_reported_not_result_selection": True,
        "outcome_fields_consumed": [],
        "outcomes_used_for_scenario_selection": False,
        "fresh_b_opened": False,
    }


def _required_context_complete(item: Mapping[str, Any]) -> bool:
    completeness = item["context_source_complete"]
    if item["family"] == "red_light_phase_timing":
        return all(completeness.values())
    optional_when_route_has_no_signal = {
        "traffic_phase_red",
        "traffic_phase_yellow",
        "traffic_phase_green",
        "traffic_phase_unknown",
        "traffic_signal_distance_m",
    }
    return all(
        bool(value) or name in optional_when_route_has_no_signal
        for name, value in completeness.items()
    )


def _monotonicity_findings(passed: list[Mapping[str, Any]]) -> dict[str, Any]:
    tier_order = ("easy", "borderline", "high_risk")
    findings = {}
    for family in SCENARIO_FAMILIES:
        rows = [item for item in passed if item["family"] == family]
        feature = (
            "traffic_phase_red"
            if family == "red_light_phase_timing"
            else "neighbor_min_distance_m"
        )
        medians = {}
        for tier in tier_order:
            values = [item["raw_context"][feature] for item in rows if item["tier"] == tier]
            medians[tier] = float(np.median(values)) if values else None
        if family == "red_light_phase_timing":
            expected = (
                medians["easy"] <= medians["borderline"] <= medians["high_risk"]
                if all(value is not None for value in medians.values())
                else False
            )
        else:
            expected = (
                medians["easy"] >= medians["borderline"] >= medians["high_risk"]
                if all(value is not None for value in medians.values())
                else False
            )
        findings[family] = {
            "feature": feature,
            "tier_medians": medians,
            "expected_order_observed": bool(expected),
        }
    return findings


def _materialize_routes(
    cases: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    output_dir: Path,
    dp_repo: Path,
) -> dict[str, dict[str, str]]:
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route

    output_dir.mkdir(parents=True, exist_ok=True)
    assets = {}
    for case in cases:
        identity = str(case["route_identity_sha256"])
        if identity in assets:
            continue
        spec = case["route_spec"]
        lanelet_ids = [int(value) for value in spec["lanelet_ids"]]
        path = output_dir / f"{identity}.pkl"
        route = Route(
            map_path=str(case["source_map_path"]),
            start_pose=np.asarray(spec["start_pose"], dtype=np.float32),
            goal_pose=np.asarray(spec["goal_pose"], dtype=np.float32),
            start_lanelet_id=lanelet_ids[0],
            goal_lanelet_id=lanelet_ids[-1],
            route_lanelet_ids=lanelet_ids,
        )
        route.save(path)
        assets[identity] = {"path": path.as_posix(), "sha256": _file_sha256(path)}
    return assets


def _build_config(
    template: Mapping[str, Any],
    case: Mapping[str, Any],
    route_asset: Mapping[str, str],
) -> dict[str, Any]:
    config = copy.deepcopy(template)
    identity = str(case["route_identity_sha256"])
    config["schema_version"] = "camp_dp_v25_controlled_capability_v1"
    config["map"] = {
        "path": str(case["source_map_path"]),
        "sha256": str(case["source_map_sha256"]),
    }
    config["routes"] = [
        {"name": identity, "path": route_asset["path"], "sha256": route_asset["sha256"]}
    ]
    config["seeds"] = {
        "scenario": PILOT_SEEDS[0],
        "candidate": PILOT_SEEDS[0],
        "bootstrap": PILOT_SEEDS[0],
        "formal_forbidden": FORMAL_FORBIDDEN_SEEDS,
    }
    config["selector"]["role"] = "v25_controlled_capability_probe_only"
    config["spawn_config"].update(
        {
            "seed": PILOT_SEEDS[0],
            "max_steps": 1,
            "max_active_npcs": 0,
            "spawn_probability": 0.0,
            "static_npc_count": 0,
            "parked_vehicles_yaml": None,
            "ego_init_speed": float(case["parameters"]["ego_speed_mps"]),
        }
    )
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [identity],
        "capability_route": identity,
        "capability_steps": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v25_controlled_outcome_blind_coverage_pilot",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
        "outcomes_used_for_selection": False,
    }
    config["controlled_scenario"] = copy.deepcopy(case)
    return config


def _shared_asset_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fixed_dp": copy.deepcopy(config["fixed_dp"]),
        "selector": copy.deepcopy(config["selector"]),
    }


def _verify_case_assets(config: Mapping[str, Any]) -> None:
    for name, asset in (
        ("map", config["map"]),
        ("route", config["routes"][0]),
    ):
        path = Path(str(asset["path"]))
        if not path.is_file() or _file_sha256(path) != asset["sha256"]:
            raise ValueError(f"v25 controlled {name} asset SHA256 mismatch")


def _official_source_audit(repo: Path) -> dict[str, Any]:
    if _git(repo, "cat-file", "-t", OFFICIAL_COMMIT).strip() != "commit":
        raise ValueError("official scenario_simulator_v2 commit is unavailable")
    anchors = {}
    for relative in OFFICIAL_ANCHORS:
        data = subprocess.run(
            ["git", "-C", str(repo), "show", f"{OFFICIAL_COMMIT}:{relative}"],
            check=True,
            capture_output=True,
        ).stdout
        anchors[relative] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_count": len(data),
        }
    return {
        "schema_version": "camp_dp_v25_official_scenario_source_audit_v1",
        "repository": "tier4/scenario_simulator_v2",
        "commit": OFFICIAL_COMMIT,
        "anchors": anchors,
        "route_policy": "explicit_lanelet2_route_only_no_random_route_action",
        "full_tree_grep_performed": False,
        "support_table_reviewed_separately": True,
        "official_runtime_available": shutil.which("ros2") is not None,
        "native_semantic_equivalent_runner": (
            "fixed_dp_scenario_generation_with_camp_side_deterministic_exogenous_adapter"
        ),
        "dp_modified": False,
        "map_semantics_modified": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _git_head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").strip()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seal(root: Path) -> str:
    excluded = {"SHA256SUMS", "ROOT_SHA256SUMS"}
    files = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name not in excluded
    )
    sums = root / "SHA256SUMS"
    with sums.open("w", encoding="utf-8", newline="\n") as handle:
        for path in files:
            handle.write(f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}\n")
    root_sha = _file_sha256(sums)
    with (root / "ROOT_SHA256SUMS").open(
        "w", encoding="ascii", newline="\n"
    ) as handle:
        handle.write(f"{root_sha}  SHA256SUMS\n")
    return root_sha


def _verify_seal(root: Path) -> str:
    sums = root / "SHA256SUMS"
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if _file_sha256(root / relative) != digest:
            raise ValueError(f"artifact SHA256 mismatch: {relative}")
    root_digest, relative = (root / "ROOT_SHA256SUMS").read_text(
        encoding="ascii"
    ).strip().split("  ", 1)
    if relative != "SHA256SUMS" or _file_sha256(sums) != root_digest:
        raise ValueError("artifact root SHA256 mismatch")
    return root_digest


if __name__ == "__main__":
    main()
