#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_temporal_consistency_payload_smoke import (
    DATASET_AUDIT,
    EXPECTED_DP_HEAD,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _source_checks as _temporal_payload_source_checks,
)


SOURCE_READY_STATUS = "temporal_consistency_payload_smoke_result_ready"
SOURCE_READY_NEXT_WORK = (
    "default_off_temporal_consistency_broader_nonformal_coverage_plan_only"
)
READY_STATUS = "temporal_consistency_broader_nonformal_smoke_plan_ready"
REJECT_STATUS = "temporal_consistency_broader_nonformal_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "default_off_temporal_consistency_broader_nonformal_paired_smoke_only"
)
FORMAL_SEEDS = frozenset({11, 12, 13})
SUMMARY_KEY = "camp_temporal_consistency_payload_logging"
MAX_SOURCE_PAYLOAD_LATENCY_MS = 1.0
MAX_BROADER_PAYLOAD_LATENCY_MS = 2.0

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


@dataclass(frozen=True)
class EvidenceRunSpec:
    run_id: str
    map_name: str
    map_path: str
    route_name: str
    route: str
    seed: int
    max_npcs: int
    spawn_probability: float
    traffic_lights: str
    scenario_buckets: tuple[str, ...]


@dataclass(frozen=True)
class BroaderSmokeSpec:
    camp_repo: str = "/root/autodl-tmp/camp_core"
    root: str = "/root/autodl-tmp/camp_dp_temporal_consistency_broader_nonformal_smoke"
    diffusion_repo: str = "/root/autodl-tmp/Diffusion-Planner"
    model_path: str = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth"
    model_args: str = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json"
    config: str = (
        "/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/"
        "replay_default.json"
    )
    reward_config: str = (
        "/root/autodl-tmp/camp_core/configs/integrations/"
        "dp_camp_reward_eval.json"
    )
    atom_scales: str = (
        "/root/autodl-tmp/camp_dp_assets/"
        "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
        "atom_scales_dp_static.json"
    )
    static_weights: str = (
        "/root/autodl-tmp/camp_dp_assets/"
        "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
        "offline_weights_dp_static.npy"
    )
    steps: int = 10
    num_candidates: int = 8
    candidate_noise_scale: float = 1.0
    candidate_reference_blend_steps: int = 5
    payload_steps: int = 10
    payload_dt_s: float = 0.1
    payload_elapsed_steps: int = 1
    payload_min_overlap_steps: int = 2
    expected_first_tick_fail_closed_per_run: int = 1
    expected_dp_head: str = EXPECTED_DP_HEAD
    runs: tuple[EvidenceRunSpec, ...] = (
        EvidenceRunSpec(
            run_id="sample_tl59_seed1_npc0_tlon",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        EvidenceRunSpec(
            run_id="sample_tl59_seed1_npc4_tlon",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=(
                "traffic_light",
                "red_light_turn",
                "sharp_turn",
                "npc_interaction",
            ),
        ),
        EvidenceRunSpec(
            run_id="sample_tl59_seed2_npc4_tloff",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=2,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("sharp_turn", "npc_interaction"),
        ),
        EvidenceRunSpec(
            run_id="sample_normal2_seed1_npc0_tloff",
            map_name="sample_map",
            map_path=(
                "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
                "sample-map-planning/lanelet2_map_no_ros.osm"
            ),
            route_name="sample_map_route_2_to_104",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("normal",),
        ),
        EvidenceRunSpec(
            run_id="nishi_lanechange_seed4_npc4_tloff",
            map_name="nishishinjuku",
            map_path="/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm",
            route_name="nishishinjuku_lane_change_route_7_via_8_to_1",
            route=(
                "/root/autodl-tmp/camp_dp_assets/"
                "nishishinjuku_lane_change_route_7_via_8_to_1.pkl"
            ),
            seed=4,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("lane_change", "npc_interaction", "dense_scene"),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a broader nonformal paired smoke using "
            "default-off temporal-consistency payload logging."
        )
    )
    parser.add_argument("--smoke_result_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, default=None)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument("--payload_audit_source", type=Path, default=PAYLOAD_AUDIT)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = BroaderSmokeSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        smoke_result=_read_json(args.smoke_result_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        paths={"smoke_result_json": str(args.smoke_result_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if args.output_bash is not None:
        args.output_bash.parent.mkdir(parents=True, exist_ok=True)
        args.output_bash.write_text(render_bash(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    smoke_result: dict[str, Any],
    label: str | None = None,
    spec: BroaderSmokeSpec = BroaderSmokeSpec(),
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_result_summary(smoke_result)
    source_checks = [
        *_source_result_checks(source),
        *_temporal_payload_source_checks(
            replay_source=replay_source,
            payload_audit_source=payload_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_broader_nonformal_smoke_plan_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "sync_boundary": (
                "Before running replay on AutoDL, sync CAMP with a verified "
                "bundle or other non-destructive fast-forward mechanism, then "
                "confirm CAMP HEAD equals origin/main and DP HEAD is fixed."
            ),
            "math_boundary": (
                "This plan only authorizes a future nonformal paired logging "
                "smoke. The temporal-consistency descriptor is computed from "
                "current-tick fixed DP candidates and previous selected-plan "
                "memory before CAMP scoring and before closed-loop outcomes. "
                "When available it is finite and nonnegative; if later atomized "
                "it is a fixed candidate coefficient a_k, preserving affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master. "
                "This plan constructs no DP-side classical Benders "
                "master/subproblem, dual, or valid cuts."
            ),
        },
        "source_result_summary": source,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "coverage_targets": _coverage_targets(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "commands": _commands(spec),
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "new_replay_authorized": passed,
            "closed_loop_smoke_authorized": passed,
            "closed_loop_replay_authorized": passed,
            "paired_smoke_execution_scope": (
                "paired nonformal temporal-consistency logging matrix, "
                f"{len(spec.runs)} runs x {spec.steps} steps, baseline plus "
                "logging-enabled, no formal seeds, selector-neutral"
                if passed
                else None
            ),
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "atom_promotion_authorized": False,
        },
    }


def _source_result_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    payload = report.get("payload_summary") or {}
    materiality = report.get("materiality_summary") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "runtime_equivalence_ready": bool(decision.get("runtime_equivalence_ready")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "payload_candidate_records": int(payload.get("candidate_records", -1)),
        "payload_available_records": int(payload.get("available_payload_records", -1)),
        "payload_first_tick_fail_closed_records": int(
            payload.get("first_tick_fail_closed_records", -1)
        ),
        "payload_latency_max_ms": _float(payload.get("latency_max_ms")),
        "sufficient_for_broader_plan": bool(
            materiality.get("sufficient_for_broader_plan")
        ),
        "sufficient_for_atom_promotion": bool(
            materiality.get("sufficient_for_atom_promotion")
        ),
        "sufficient_for_training": bool(materiality.get("sufficient_for_training")),
    }


def _source_result_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_result_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_result_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_broader_plan",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_runtime_equivalence_ready",
            source["runtime_equivalence_ready"],
            True,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_empty("source_no_blocked_action_conflicts", source["blocked_action_conflicts"]),
        _check_equal(
            "source_payload_has_minimum_available_records",
            source["payload_available_records"] >= 2,
            True,
        ),
        _check_equal(
            "source_payload_first_tick_fail_closed",
            source["payload_first_tick_fail_closed_records"],
            1,
        ),
        _check_equal(
            "source_payload_latency_within_plan_budget",
            source["payload_latency_max_ms"] <= MAX_SOURCE_PAYLOAD_LATENCY_MS,
            True,
        ),
        _check_equal(
            "source_materiality_sufficient_for_broader_plan",
            source["sufficient_for_broader_plan"],
            True,
        ),
        _check_equal(
            "source_materiality_not_sufficient_for_atom_promotion",
            source["sufficient_for_atom_promotion"],
            False,
        ),
        _check_equal(
            "source_materiality_not_sufficient_for_training",
            source["sufficient_for_training"],
            False,
        ),
    ]


def _plan_checks(spec: BroaderSmokeSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    map_names = {run.map_name for run in spec.runs}
    route_names = {run.route_name for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    npc_counts = {run.max_npcs for run in spec.runs}
    bucket_counts = _bucket_counts(spec)
    total_records = int(spec.steps) * len(spec.runs)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": not (seeds & FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "paired_matrix_size_predeclared",
            "passed": len(spec.runs) == 5 and int(spec.steps) == 10,
            "details": {"runs": len(spec.runs), "steps": int(spec.steps)},
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": int(spec.num_candidates) == 8,
            "details": {"num_candidates": int(spec.num_candidates)},
        },
        {
            "name": "planned_records_and_candidates_material",
            "passed": total_records >= 50
            and total_records * int(spec.num_candidates) >= 400,
            "details": {
                "planned_records": total_records,
                "planned_candidate_rows": total_records * int(spec.num_candidates),
            },
        },
        {
            "name": "traffic_light_on_and_off_covered",
            "passed": {"on", "off"}.issubset(traffic_modes),
            "details": {"traffic_light_modes": sorted(traffic_modes)},
        },
        {
            "name": "npc_and_no_npc_covered",
            "passed": 0 in npc_counts and any(count > 0 for count in npc_counts),
            "details": {"max_npcs": sorted(npc_counts)},
        },
        {
            "name": "sample_and_nishishinjuku_maps_covered",
            "passed": {"sample_map", "nishishinjuku"}.issubset(map_names),
            "details": {"map_names": sorted(map_names)},
        },
        {
            "name": "traffic_sensitive_normal_and_lane_change_routes_covered",
            "passed": "sample_map_tl_route_59_to_86" in route_names
            and "sample_map_route_2_to_104" in route_names
            and "nishishinjuku_lane_change_route_7_via_8_to_1" in route_names,
            "details": {"route_names": sorted(route_names)},
        },
        {
            "name": "scenario_buckets_cover_required_contexts",
            "passed": all(
                bucket_counts.get(bucket, 0) > 0
                for bucket in (
                    "traffic_light",
                    "red_light_turn",
                    "sharp_turn",
                    "npc_interaction",
                    "normal",
                    "lane_change",
                )
            ),
            "details": {"scenario_bucket_counts": bucket_counts},
        },
        {
            "name": "temporal_payload_parameters_valid",
            "passed": int(spec.payload_steps) >= 2
            and float(spec.payload_dt_s) > 0.0
            and int(spec.payload_elapsed_steps) >= 0
            and int(spec.payload_min_overlap_steps) >= 2,
            "details": {
                "payload_steps": int(spec.payload_steps),
                "payload_dt_s": float(spec.payload_dt_s),
                "payload_elapsed_steps": int(spec.payload_elapsed_steps),
                "payload_min_overlap_steps": int(spec.payload_min_overlap_steps),
            },
        },
        {
            "name": "fixed_dp_head_declared",
            "passed": spec.expected_dp_head == EXPECTED_DP_HEAD,
            "details": {"expected_dp_head": spec.expected_dp_head},
        },
    ]


def _coverage_targets(spec: BroaderSmokeSpec) -> dict[str, Any]:
    planned_records = int(spec.steps) * len(spec.runs)
    available_per_run = max(int(spec.steps) - 1, 0)
    return {
        "planned_logs": len(spec.runs),
        "planned_records": planned_records,
        "planned_candidate_rows": planned_records * int(spec.num_candidates),
        "expected_payload_records_per_run": int(spec.steps),
        "expected_available_payload_records_min_per_run": available_per_run,
        "expected_first_tick_fail_closed_per_run": int(
            spec.expected_first_tick_fail_closed_per_run
        ),
        "max_payload_latency_ms": MAX_BROADER_PAYLOAD_LATENCY_MS,
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _commands(spec: BroaderSmokeSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    candidate_root = f"{spec.root}/logging_enabled"
    audit_root = f"{spec.root}/audit"
    replay_commands = []
    payload_audit_commands = []
    for run in spec.runs:
        replay_commands.append(
            {
                "run_id": run.run_id,
                "variant": "baseline",
                "command": _runner_command(
                    spec,
                    run,
                    f"{baseline_root}/{run.run_id}",
                    logging=False,
                ),
            }
        )
        replay_commands.append(
            {
                "run_id": run.run_id,
                "variant": "logging_enabled",
                "command": _runner_command(
                    spec,
                    run,
                    f"{candidate_root}/{run.run_id}",
                    logging=True,
                ),
            }
        )
        payload_audit_commands.append(
            {
                "run_id": run.run_id,
                "command": _payload_audit_command(
                    f"{baseline_root}/{run.run_id}",
                    f"{candidate_root}/{run.run_id}",
                    f"{audit_root}/payload/{run.run_id}",
                    spec,
                ),
            }
        )
    return {
        "asset_audit": _asset_audit_command(spec),
        "head_audit": _head_audit_command(spec),
        "replays": replay_commands,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            candidate_root,
            audit_root,
        ),
        "payload_audits": payload_audit_commands,
        "dataset_audit": _dataset_audit_command(candidate_root, audit_root, spec),
    }


def _asset_audit_command(spec: BroaderSmokeSpec) -> list[str]:
    assets = sorted(
        {
            spec.model_path,
            spec.model_args,
            spec.config,
            spec.reward_config,
            spec.atom_scales,
            spec.static_weights,
            *(run.map_path for run in spec.runs),
            *(run.route for run in spec.runs),
        }
    )
    tests = " && ".join(f"test -f {shlex.quote(path)}" for path in assets)
    return ["/bin/bash", "-lc", f"{tests} && echo temporal_consistency_assets_ok"]


def _head_audit_command(spec: BroaderSmokeSpec) -> list[str]:
    return [
        "/bin/bash",
        "-lc",
        (
            f'test "$(git -C {spec.camp_repo} rev-parse HEAD)" = '
            f'"$(git -C {spec.camp_repo} rev-parse origin/main)" && '
            f'test "$(git -C {spec.diffusion_repo} rev-parse HEAD)" = '
            f'"{spec.expected_dp_head}" && '
            f'echo "CAMP_HEAD=$(git -C {spec.camp_repo} rev-parse HEAD)" && '
            f'echo "DP_HEAD=$(git -C {spec.diffusion_repo} rev-parse HEAD)"'
        ),
    ]


def _runner_command(
    spec: BroaderSmokeSpec,
    run: EvidenceRunSpec,
    output_dir: str,
    *,
    logging: bool,
) -> list[str]:
    command = [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "REPLAY_NO_PNG=1",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "--diffusion_repo",
        spec.diffusion_repo,
        "--map_path",
        run.map_path,
        "--route",
        run.route,
        "--model_path",
        spec.model_path,
        "--model_args",
        spec.model_args,
        "--config",
        spec.config,
        "--output_dir",
        output_dir,
        "--device",
        "cuda",
        "--advance_mode",
        "perfect",
        "--steps",
        str(spec.steps),
        "--seed",
        str(run.seed),
        "--max_npcs",
        str(run.max_npcs),
        "--spawn_probability",
        str(run.spawn_probability),
        "--traffic_lights",
        run.traffic_lights,
        "--reward_config",
        spec.reward_config,
        "--camp_selector_mode",
        "static",
        "--camp_atom_scales",
        spec.atom_scales,
        "--camp_static_weights",
        spec.static_weights,
        "--num_candidates",
        str(spec.num_candidates),
        "--candidate_noise_scale",
        str(spec.candidate_noise_scale),
        "--candidate_reference_blend_steps",
        str(spec.candidate_reference_blend_steps),
        "--camp_lane_corridor_buffer",
        "1.0",
        "--camp_feasibility_source",
        "dp_reward",
        "--camp_fallback_mode",
        "learned",
        "--camp_min_progress_ratio",
        "0.8",
        "--camp_shadow_route_progress",
        "--camp_shadow_obstacle_clearance",
        "--camp_reward_horizon_steps",
        "30",
        "--camp_outcome_horizon_steps",
        "30",
        "--near_miss_threshold_m",
        "2.0",
    ]
    if logging:
        command.extend(
            [
                "--camp_temporal_consistency_payload_logging",
                "--camp_temporal_consistency_payload_steps",
                str(spec.payload_steps),
                "--camp_temporal_consistency_payload_dt_s",
                str(spec.payload_dt_s),
                "--camp_temporal_consistency_payload_elapsed_steps",
                str(spec.payload_elapsed_steps),
                "--camp_temporal_consistency_payload_min_overlap_steps",
                str(spec.payload_min_overlap_steps),
            ]
        )
    return command


def _selector_equivalence_command(
    baseline_root: str,
    candidate_root: str,
    audit_root: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/compare_diffusion_planner_selector_logs.py",
        "--baseline_root",
        baseline_root,
        "--candidate_root",
        candidate_root,
        "--output_json",
        f"{audit_root}/selector_equivalence.json",
        "--require_equivalent",
    ]


def _payload_audit_command(
    baseline_dir: str,
    candidate_dir: str,
    output_dir: str,
    spec: BroaderSmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_temporal_consistency_payload_smoke.py",
        "--baseline_root",
        baseline_dir,
        "--candidate_root",
        candidate_dir,
        "--expected_logs",
        "1",
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--min_available_records",
        str(max(int(spec.steps) - 1, 0)),
        "--expected_first_tick_fail_closed",
        str(spec.expected_first_tick_fail_closed_per_run),
        "--output_json",
        f"{output_dir}/temporal_consistency_payload_smoke.json",
        "--output_md",
        f"{output_dir}/temporal_consistency_payload_smoke.md",
        "--require_pass",
    ]


def _dataset_audit_command(
    candidate_root: str,
    audit_root: str,
    spec: BroaderSmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--root",
        candidate_root,
        "--atom_scales",
        spec.atom_scales,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_candidates",
        str(spec.num_candidates),
        "--expected_advance_mode",
        "perfect",
        "--closed_loop_outcome_policy",
        "forbidden",
        "--forbid_seed",
        "11",
        "--forbid_seed",
        "12",
        "--forbid_seed",
        "13",
        "--require_finite_candidate_contract",
        "--output_json",
        f"{audit_root}/dataset_audit.json",
    ]


def _accept_criteria(spec: BroaderSmokeSpec) -> list[str]:
    available_per_run = max(int(spec.steps) - 1, 0)
    return [
        "asset and head audits exit 0 before replay",
        "all paired replay commands exit 0",
        "no formal seed 11/12/13 appears in any output path or summary",
        f"baseline summaries report {SUMMARY_KEY}.enabled=false",
        f"candidate summaries report {SUMMARY_KEY}.enabled=true",
        "candidate records contain non-null temporal_consistency_payload_logging payloads",
        "each run has exactly one first-tick previous-plan-missing fail-closed record",
        f"each run has at least {available_per_run} available finite temporal consistency records",
        "all available temporal consistency coefficients are finite and nonnegative",
        "candidate_closed_loop_outcomes remain absent",
        "selector log equivalence passes with selected_index, feasibility, atoms, scores, and weights unchanged",
        "dataset audit passes finite-candidate contract checks with closed-loop outcomes forbidden",
        f"payload max latency stays below {MAX_BROADER_PAYLOAD_LATENCY_MS} ms in every run",
        f"scope remains {len(spec.runs)} paired nonformal runs x {spec.steps} steps x {spec.num_candidates} candidates",
    ]


def _reject_criteria() -> list[str]:
    return [
        "asset or head audit fails",
        "any replay, selector-equivalence, payload, or dataset audit fails",
        "any formal seed is detected",
        "any selected_index or CAMP score/atom field changes between baseline and logging-enabled runs",
        "any payload uses future outcome labels or reports selection_effect=true",
        "missing previous-plan memory does not fail closed on the first tick",
        "any available temporal consistency coefficient is negative, nonfinite, or wrong-shaped",
        "payload latency exceeds the predeclared broader budget",
        "the smoke is expanded beyond the predeclared paired nonformal scope",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Broader Nonformal Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- scope: `{decision['paired_smoke_execution_scope']}`",
        "",
        "## Sync Boundary",
        "",
        report["analysis"]["sync_boundary"],
        "",
        "## Source Result",
        "",
        f"`{report['source_result_summary']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Observed | Expected | Missing |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        missing = ", ".join(check.get("missing_tokens", []))
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` | `{missing}` |"
        )
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(
        f"- `{check['name']}`: `{check['passed']}`"
        for check in report["plan_checks"]
    )
    lines.extend(["", "## Coverage Targets", ""])
    lines.append(f"`{report['coverage_targets']}`")
    lines.extend(["", "## Commands", ""])
    command_separator = " \\\n" "  "
    commands = report["commands"]
    for name in ("asset_audit", "head_audit", "selector_equivalence", "dataset_audit"):
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(commands[name]),
                "```",
                "",
            ]
        )
    lines.extend(["### replays", ""])
    for item in commands["replays"]:
        lines.extend(
            [
                f"#### {item['run_id']} {item['variant']}",
                "",
                "```bash",
                command_separator.join(item["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["### payload_audits", ""])
    for item in commands["payload_audits"]:
        lines.extend(
            [
                f"#### {item['run_id']}",
                "",
                "```bash",
                command_separator.join(item["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def render_bash(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    if decision.get("authorized_next_work") != AUTHORIZED_NEXT_WORK:
        raise ValueError("Cannot render bash for a rejected broader smoke plan.")
    commands = report["commands"]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Auto-generated from dp_camp_temporal_consistency_broader_nonformal_smoke_plan_v1.",
        "# Scope: paired nonformal temporal-consistency logging matrix only.",
        "# Forbidden: formal seeds, Full36, online selector promotion, CAMP retraining, DP modification.",
        f"# Expected DP HEAD: {EXPECTED_DP_HEAD}",
        "",
        "cd /root/autodl-tmp/camp_core",
        "",
    ]
    for name in ("asset_audit", "head_audit"):
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    for item in commands["replays"]:
        lines.extend(
            [
                f'echo "== replay {item["run_id"]} {item["variant"]} =="',
                shlex.join(item["command"]),
                "",
            ]
        )
    lines.extend(
        [
            'echo "== selector_equivalence =="',
            shlex.join(commands["selector_equivalence"]),
            "",
        ]
    )
    for item in commands["payload_audits"]:
        lines.extend(
            [
                f'echo "== payload_audit {item["run_id"]} =="',
                shlex.join(item["command"]),
                "",
            ]
        )
    lines.extend(
        [
            'echo "== dataset_audit =="',
            shlex.join(commands["dataset_audit"]),
            "",
            'echo "temporal_consistency_broader_nonformal_smoke_complete"',
            "",
        ]
    )
    return "\n".join(lines)


def _bucket_counts(spec: BroaderSmokeSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {"name": name, "observed": value, "expected": [], "passed": len(value) == 0}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
