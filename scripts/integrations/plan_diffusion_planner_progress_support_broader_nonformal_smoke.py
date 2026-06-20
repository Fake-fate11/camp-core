#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_progress_support_logging_smoke import (
    DATASET_AUDIT,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _source_checks as _logging_source_checks,
)


READY_STATUS = "progress_support_broader_nonformal_smoke_plan_ready"
REJECT_STATUS = "progress_support_broader_nonformal_smoke_plan_rejected"
SOURCE_STATUS = "progress_support_route_projection_optimized_paired_smoke_passed"
AUTHORIZED_NEXT_WORK = "progress_support_broader_nonformal_paired_smoke_only"
FORMAL_SEEDS = frozenset({11, 12, 13})
MAX_SOURCE_LOGGING_MS = 5.0
MAX_SOURCE_ROUTE_PROJECTION_MS = 5.0
MAX_BROADER_LOGGING_MS = 25.0


@dataclass(frozen=True)
class EvidenceRunSpec:
    run_id: str
    route_name: str
    route: str
    seed: int
    max_npcs: int
    spawn_probability: float
    traffic_lights: str
    scenario_buckets: tuple[str, ...]


@dataclass(frozen=True)
class BroaderSmokeSpec:
    root: str = "/root/autodl-tmp/camp_dp_progress_support_broader_nonformal_smoke"
    diffusion_repo: str = "/root/autodl-tmp/Diffusion-Planner"
    map_path: str = (
        "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
        "sample-map-planning/lanelet2_map_no_ros.osm"
    )
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
    steps: int = 12
    num_candidates: int = 8
    candidate_noise_scale: float = 1.0
    candidate_reference_blend_steps: int = 5
    progress_support_steps: int = 10
    progress_support_dt_s: float = 0.1
    runs: tuple[EvidenceRunSpec, ...] = (
        EvidenceRunSpec(
            run_id="tl_route59_seed1_npc0_tlon",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        EvidenceRunSpec(
            run_id="tl_route59_seed1_npc4_tlon",
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
            run_id="tl_route59_seed2_npc4_tloff",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=2,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("sharp_turn", "npc_interaction"),
        ),
        EvidenceRunSpec(
            run_id="normal_route2_seed1_npc0_tloff",
            route_name="sample_map_route_2_to_104",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("normal",),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a broader nonformal paired smoke using the "
            "optimized progress-support logging path. It emits commands and "
            "accept/reject criteria but does not run Diffusion Planner."
        )
    )
    parser.add_argument("--optimized_smoke_audit_json", type=Path, required=True)
    parser.add_argument("--optimized_selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--optimized_dataset_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
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
        optimized_smoke_audit=_read_json(args.optimized_smoke_audit_json),
        optimized_selector_equivalence=_read_json(
            args.optimized_selector_equivalence_json
        ),
        optimized_dataset_audit=_read_json(args.optimized_dataset_audit_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    optimized_smoke_audit: dict[str, Any],
    optimized_selector_equivalence: dict[str, Any],
    optimized_dataset_audit: dict[str, Any],
    label: str | None = None,
    spec: BroaderSmokeSpec = BroaderSmokeSpec(),
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
) -> dict[str, Any]:
    source_checks = [
        *_source_artifact_checks(
            smoke=optimized_smoke_audit,
            selector=optimized_selector_equivalence,
            dataset=optimized_dataset_audit,
        ),
        *_logging_source_checks(
            replay_source=replay_source,
            payload_audit_source=payload_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    commands = _commands(spec)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_broader_nonformal_smoke_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This plan only authorizes a future nonformal paired logging "
                "smoke after the optimized progress-support hook passed exact "
                "selector-equivalence and dataset audits. Runtime payloads must "
                "remain fixed current-tick finite-candidate diagnostics computed "
                "before closed-loop outcome evaluation. If later atomized, these "
                "diagnostics enter as fixed candidate coefficients a_k, preserving "
                "affine score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master. "
                "No DP-side classical Benders claim is made."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "coverage_targets": _coverage_targets(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "blocked_actions": {
            "run_replay_now": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "online_optimization_promotion": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: paired nonformal progress-support logging "
                "matrix, 4 runs x 12 steps, baseline plus logging-enabled, "
                "no formal seeds, selector-neutral"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "online_optimization_promotion_authorized": False,
        },
    }


def _source_artifact_checks(
    *,
    smoke: dict[str, Any],
    selector: dict[str, Any],
    dataset: dict[str, Any],
) -> list[dict[str, Any]]:
    final = smoke.get("final_decision", {})
    latency = smoke.get("latency_ms", {})
    logging_ms = _float(latency.get("latency_ms_progress_support_logging"))
    route_ms = _float(latency.get("latency_ms_progress_support_route_projection"))
    return [
        {
            "name": "optimized_smoke_passed",
            "passed": final.get("status") == "progress_support_logging_smoke_passed"
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "optimized_smoke_blocks_promotion_training_and_dp_changes",
            "passed": final.get("Full36_authorized") is False
            and final.get("formal_seeds_authorized") is False
            and final.get("online_selector_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("DP_modification_authorized") is False,
            "final_decision": final,
        },
        {
            "name": "optimized_logging_latency_within_source_budget",
            "passed": logging_ms <= MAX_SOURCE_LOGGING_MS,
            "value_ms": logging_ms,
            "threshold_ms": MAX_SOURCE_LOGGING_MS,
        },
        {
            "name": "optimized_route_projection_latency_within_source_budget",
            "passed": route_ms <= MAX_SOURCE_ROUTE_PROJECTION_MS,
            "value_ms": route_ms,
            "threshold_ms": MAX_SOURCE_ROUTE_PROJECTION_MS,
        },
        {
            "name": "optimized_selector_exact_equivalence",
            "passed": selector.get("equivalent") is True
            and _sum_nested_numbers(selector.get("exact_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_shape_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_nonexact_entries")) == 0.0,
            "equivalent": selector.get("equivalent"),
        },
        {
            "name": "optimized_dataset_audit_passed",
            "passed": dataset.get("passed") is True,
            "passed_value": dataset.get("passed"),
        },
    ]


def _plan_checks(spec: BroaderSmokeSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
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
            "passed": len(spec.runs) == 4 and int(spec.steps) == 12,
            "details": {"runs": len(spec.runs), "steps": int(spec.steps)},
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": int(spec.num_candidates) == 8,
            "details": {"num_candidates": int(spec.num_candidates)},
        },
        {
            "name": "planned_records_and_candidates_material",
            "passed": total_records >= 48
            and total_records * int(spec.num_candidates) >= 384,
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
            "name": "red_turn_and_normal_routes_covered",
            "passed": {
                "sample_map_tl_route_59_to_86",
                "sample_map_route_2_to_104",
            }.issubset(route_names),
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
                )
            ),
            "details": {"bucket_counts": bucket_counts},
        },
        {
            "name": "progress_support_horizon_fixed",
            "passed": int(spec.progress_support_steps) == 10
            and abs(float(spec.progress_support_dt_s) - 0.1) <= 1e-12,
            "details": {
                "progress_support_steps": int(spec.progress_support_steps),
                "progress_support_dt_s": float(spec.progress_support_dt_s),
            },
        },
    ]


def _coverage_targets(spec: BroaderSmokeSpec) -> dict[str, Any]:
    return {
        "planned_logs": len(spec.runs),
        "planned_records": len(spec.runs) * int(spec.steps),
        "planned_candidate_rows": (
            len(spec.runs) * int(spec.steps) * int(spec.num_candidates)
        ),
        "max_broader_progress_support_logging_ms": MAX_BROADER_LOGGING_MS,
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _commands(spec: BroaderSmokeSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    candidate_root = f"{spec.root}/logging_enabled"
    audit_root = f"{spec.root}/audit"
    paired_replays = []
    for run in spec.runs:
        paired_replays.append(
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
        paired_replays.append(
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
    return {
        "paired_replays": paired_replays,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            candidate_root,
            audit_root,
        ),
        "payload_audit": _payload_audit_command(
            baseline_root,
            candidate_root,
            audit_root,
            spec,
        ),
        "dataset_audit": _dataset_audit_command(candidate_root, audit_root, spec),
    }


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
        spec.map_path,
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
                "--camp_progress_support_logging",
                "--camp_progress_support_steps",
                str(spec.progress_support_steps),
                "--camp_progress_support_dt_s",
                str(spec.progress_support_dt_s),
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
    baseline_root: str,
    candidate_root: str,
    audit_root: str,
    spec: BroaderSmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_progress_support_logging_smoke.py",
        "--baseline_root",
        baseline_root,
        "--candidate_root",
        candidate_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--output_json",
        f"{audit_root}/progress_support_logging_smoke.json",
        "--output_md",
        f"{audit_root}/progress_support_logging_smoke.md",
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
    return [
        "all paired baseline and logging-enabled replay commands exit 0",
        "no formal seed 11/12/13 appears in any output path or summary",
        "baseline summaries report camp_progress_support_logging.enabled=false",
        "logging-enabled summaries report camp_progress_support_logging.enabled=true",
        "candidate records contain non-null progress_support_logging payloads",
        "progress_support atoms are finite and nonnegative for all candidates",
        "candidate_closed_loop_outcomes remain absent",
        "selector log equivalence passes with selected_index, feasibility, atoms, scores, and weights unchanged",
        "dataset audit passes finite-candidate contract checks",
        f"payload audit max latency_ms_progress_support_logging <= {MAX_BROADER_LOGGING_MS} ms",
        f"scope remains {len(spec.runs)} paired nonformal runs x {spec.steps} steps x {spec.num_candidates} candidates",
    ]


def _reject_criteria() -> list[str]:
    return [
        "optimized paired smoke source artifacts are missing, failed, or latency-blocked",
        "any source or plan check fails",
        "any replay, selector-equivalence, payload, or dataset audit fails in the next gate",
        "any formal seed is detected",
        "any selected_index or CAMP score/atom field changes between baseline and logging-enabled runs",
        "any payload uses future outcome labels or reports selection_effect=true",
        "any progress-support atom is negative, nonfinite, or has an unexpected shape",
        "the smoke expands beyond the predeclared broader nonformal scope",
        "the broader payload audit reports progress-support logging latency above budget",
    ]


def _bucket_counts(spec: BroaderSmokeSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def _sum_nested_numbers(value: Any) -> float:
    if isinstance(value, dict):
        return sum(_sum_nested_numbers(item) for item in value.values())
    if isinstance(value, (int, float)):
        return float(value)
    return float("inf")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress-Support Broader Nonformal Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke execution authorized now: `{decision['paired_smoke_execution_authorized']}`",
        f"- scope: `{decision['paired_smoke_execution_scope']}`",
        "",
        "## Coverage Targets",
        "",
        "| Target | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["coverage_targets"].items():
        if key == "scenario_bucket_counts":
            continue
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Planned Runs",
            "",
            "| Run | Route | Seed | NPCs | TL | Buckets |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for run in report["plan_spec"]["runs"]:
        lines.append(
            f"| `{run['run_id']}` | `{run['route_name']}` | `{run['seed']}` | "
            f"`{run['max_npcs']}` | `{run['traffic_lights']}` | "
            f"`{', '.join(run['scenario_buckets'])}` |"
        )
    lines.extend(["", "## Source Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Plan Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Audit Commands", ""])
    separator = " \\\n  "
    for name in ("selector_equivalence", "payload_audit", "dataset_audit"):
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                separator.join(report["commands"][name]),
                "```",
                "",
            ]
        )
    lines.extend(["## Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
