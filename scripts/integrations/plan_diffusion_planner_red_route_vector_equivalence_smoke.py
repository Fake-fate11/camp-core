#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


READY_STATUS = "red_route_vector_equivalence_smoke_plan_ready"
REJECT_STATUS = "red_route_vector_equivalence_smoke_plan_rejected"
SOURCE_STATUS = "red_route_vector_logging_plan_ready"
SOURCE_NEXT_WORK = "implement_default_off_red_route_vector_logging_unit_tests_only"
AUTHORIZED_NEXT_WORK = "red_route_vector_equivalence_smoke_execution_only"
FORMAL_SEEDS = frozenset({11, 12, 13})


@dataclass(frozen=True)
class RedRouteVectorEquivalenceRunSpec:
    run_id: str = "tl_route59_seed1_npc0_tlon_red_vector"
    route_name: str = "sample_map_tl_route_59_to_86"
    route: str = "/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl"
    seed: int = 1
    max_npcs: int = 0
    spawn_probability: float = 0.0
    traffic_lights: str = "on"
    scenario_buckets: tuple[str, ...] = ("traffic_light", "red_light", "turn_lateral")


@dataclass(frozen=True)
class RedRouteVectorEquivalencePlanSpec:
    root: str = "/root/autodl-tmp/camp_dp_red_route_vector_equivalence_smoke"
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
    steps: int = 3
    num_candidates: int = 8
    candidate_noise_scale: float = 1.0
    candidate_reference_blend_steps: int = 5
    max_p95_red_route_vector_latency_ms: float = 2.0
    min_records_with_red_route_points: int = 1
    run: RedRouteVectorEquivalenceRunSpec = RedRouteVectorEquivalenceRunSpec()


REPLAY_TOKENS = (
    "--camp_red_route_vector_logging",
    "RED_ROUTE_VECTOR_LOGGING_SCHEMA_VERSION",
    "red_route_vector_logging",
    "camp_red_route_vector_logging",
    "latency_ms_red_route_vector_logging",
    '"selection_effect": False',
    '"future_outcome_leakage": False',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only paired smoke plan for default-off red route vector "
            "logging selector equivalence. It does not run Diffusion Planner."
        )
    )
    parser.add_argument("--red_vector_plan_json", type=Path, required=True)
    parser.add_argument(
        "--replay_script",
        type=Path,
        default=Path("scripts/integrations/run_diffusion_planner_camp_replay.py"),
    )
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = RedRouteVectorEquivalencePlanSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        red_vector_plan_report=_read_json(args.red_vector_plan_json),
        replay_script=args.replay_script,
        label=args.label,
        spec=spec,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    red_vector_plan_report: dict[str, Any],
    replay_script: Path,
    label: str | None = None,
    spec: RedRouteVectorEquivalencePlanSpec = RedRouteVectorEquivalencePlanSpec(),
) -> dict[str, Any]:
    source_checks = _source_checks(red_vector_plan_report)
    implementation_checks = _implementation_checks(replay_script)
    plan_checks = _plan_checks(spec)
    passed = all(
        check["passed"]
        for check in [*source_checks, *implementation_checks, *plan_checks]
    )
    commands = _commands(spec)
    return {
        "analysis": {
            "name": "dp_camp_red_route_vector_equivalence_smoke_plan_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This is a design-only paired smoke plan for selector-neutral "
                "current-tick diagnostics. It creates no selector, atom, online "
                "threshold, trajectory-space convexity claim, or Benders cut."
            ),
        },
        "source_checks": source_checks,
        "implementation_checks": implementation_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "commands": commands,
        "equivalence_contract": _equivalence_contract(),
        "payload_contract": _payload_contract(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "blocked_actions": {
            "run_replay_now": True,
            "offline_separability": True,
            "full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "camp_retraining": True,
            "dp_modification": True,
            "classic_benders_claim": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: one nonformal paired replay, baseline versus "
                "--camp_red_route_vector_logging, selector-equivalence audit "
                "required before any separability work"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_Benders_claim_authorized": False,
        },
    }


def _source_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    final = report.get("final_decision") if isinstance(report, dict) else None
    final = final if isinstance(final, dict) else {}
    return [
        {
            "name": "source_plan_ready_and_authorized_implementation_only",
            "passed": final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK,
            "final_decision": final,
        },
        {
            "name": "source_plan_did_not_authorize_replay",
            "passed": final.get("new_replay_authorized") is False
            and final.get("offline_separability_authorized") is False
            and final.get("formal_seeds_authorized") is False,
            "final_decision": final,
        },
    ]


def _implementation_checks(replay_script: Path) -> list[dict[str, Any]]:
    path = Path(replay_script)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return [
        {
            "name": "replay_script_exists",
            "passed": path.is_file(),
            "path": str(path),
        },
        {
            "name": "red_route_vector_logging_tokens_present",
            "passed": all(token in text for token in REPLAY_TOKENS),
            "missing_tokens": [token for token in REPLAY_TOKENS if token not in text],
        },
    ]


def _plan_checks(spec: RedRouteVectorEquivalencePlanSpec) -> list[dict[str, Any]]:
    run = spec.run
    planned_records = 2 * int(spec.steps)
    planned_candidate_rows = planned_records * int(spec.num_candidates)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": run.seed not in FORMAL_SEEDS,
            "details": {"seed": run.seed, "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "paired_scope_is_tiny_and_nonformal",
            "passed": int(spec.steps) <= 5
            and int(spec.num_candidates) <= 8
            and run.max_npcs == 0
            and run.traffic_lights == "on",
            "details": {
                "paired_runs": 2,
                "steps": int(spec.steps),
                "num_candidates": int(spec.num_candidates),
                "max_npcs": run.max_npcs,
                "traffic_lights": run.traffic_lights,
            },
        },
        {
            "name": "planned_materiality_is_sufficient_for_logging_smoke",
            "passed": planned_records > 0
            and planned_candidate_rows >= 2 * int(spec.num_candidates),
            "details": {
                "planned_records": planned_records,
                "planned_candidate_rows": planned_candidate_rows,
            },
        },
        {
            "name": "route_targets_red_context",
            "passed": "traffic_light" in run.scenario_buckets
            and "red_light" in run.scenario_buckets,
            "details": {"scenario_buckets": list(run.scenario_buckets)},
        },
    ]


def _commands(spec: RedRouteVectorEquivalencePlanSpec) -> dict[str, Any]:
    run = spec.run
    paired_replays = []
    for variant in ("baseline", "red_route_vector_logging_enabled"):
        output_dir = f"{spec.root}/logs/{run.run_id}/{variant}"
        command = [
            "$PY",
            "scripts/integrations/run_diffusion_planner_camp_replay.py",
            "--diffusion_repo",
            spec.diffusion_repo,
            "--map_path",
            spec.map_path,
            "--model_path",
            spec.model_path,
            "--model_args",
            spec.model_args,
            "--config",
            spec.config,
            "--route",
            run.route,
            "--output_dir",
            output_dir,
            "--reward_config",
            spec.reward_config,
            "--camp_atom_scales",
            spec.atom_scales,
            "--camp_static_weights",
            spec.static_weights,
            "--seed",
            str(run.seed),
            "--max_npcs",
            str(run.max_npcs),
            "--spawn_probability",
            str(run.spawn_probability),
            "--traffic_lights",
            run.traffic_lights,
            "--steps",
            str(spec.steps),
            "--num_candidates",
            str(spec.num_candidates),
            "--candidate_noise_scale",
            str(spec.candidate_noise_scale),
            "--candidate_reference_blend_steps",
            str(spec.candidate_reference_blend_steps),
            "--camp_feasibility_source",
            "dp_reward",
            "--camp_fallback_mode",
            "learned",
            "--camp_min_progress_ratio",
            "0.8",
        ]
        if variant == "red_route_vector_logging_enabled":
            command.append("--camp_red_route_vector_logging")
        paired_replays.append(
            {"run_id": run.run_id, "variant": variant, "command": command}
        )
    return {
        "paired_replays": paired_replays,
        "required_followup_checks": {
            "red_route_vector_selector_equivalence_audit": [
                "exact paired record count equality",
                "selected_index equality",
                "camp_selected_index_before_* equality",
                "feasible_mask and infeasibility_reasons equality",
                "atoms, normalized_atoms, scores, weights, selection_scores, selection_weights equality",
                "PerfectTracker inputs and selected trajectory equality",
                "baseline red_route_vector_logging is null in every record",
                "logging-enabled red_route_vector_logging exists in every record",
            ],
            "red_route_vector_payload_audit": [
                "schema_version dp_camp_red_route_vector_logging_v1",
                "default_off=true, selection_effect=false, future_outcome_leakage=false",
                "all planned fields are present with finite checks true",
                f"records_with_red_route_points >= {spec.min_records_with_red_route_points}",
                f"p95 latency_ms_red_route_vector_logging <= {spec.max_p95_red_route_vector_latency_ms}",
            ],
        },
    }


def _equivalence_contract() -> dict[str, Any]:
    exact_fields = (
        "selected_index",
        "camp_selected_index_before_tracker_postselection",
        "camp_selected_index_before_traffic_light_hybrid_postselection",
        "feasible_mask",
        "infeasibility_reasons",
        "scores",
        "weights",
        "selection_scores",
        "selection_weights",
        "atoms",
        "normalized_atoms",
        "selection_normalized_atoms",
        "candidate_first_reference_xy",
        "candidate_perfect_tracker_reference_first_xy",
        "candidate_perfect_tracker_reference_first_heading_rad",
        "candidate_perfect_tracker_target_speed_mps",
        "candidate_perfect_tracker_open_loop_rollout",
        "perfect_tracker_command_inputs",
        "candidate_perfect_tracker_postprocessed_reference_prefix",
    )
    allowed_differences = (
        "red_route_vector_logging",
        "latency_ms_red_route_vector_logging",
        "latency_ms_including_candidate_generation",
        "latency_ms_camp_selection",
        "latency_ms_reward_npz_dump",
    )
    return {
        "exact_fields": list(exact_fields),
        "allowed_differences": list(allowed_differences),
        "baseline_expected_payload": None,
        "logging_enabled_expected_payload": "present_every_record",
    }


def _payload_contract(spec: RedRouteVectorEquivalencePlanSpec) -> dict[str, Any]:
    return {
        "schema_version": "dp_camp_red_route_vector_logging_v1",
        "required_flags": {
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
        },
        "required_fields": [
            "red_route_points_ego_xy_dir",
            "candidate_red_selected_route_point_index",
            "candidate_red_heading_vector_xy",
            "candidate_red_vector_to_selected_point_xy",
            "candidate_red_alignment_recomputed_current",
            "candidate_red_alignment_recomputed_reverse",
        ],
        "min_records_with_red_route_points": int(spec.min_records_with_red_route_points),
        "max_p95_red_route_vector_latency_ms": float(
            spec.max_p95_red_route_vector_latency_ms
        ),
    }


def _accept_criteria(spec: RedRouteVectorEquivalencePlanSpec) -> list[str]:
    return [
        "source plan and implementation hooks are present",
        "paired replay differs only by --camp_red_route_vector_logging",
        "selector-equivalence audit passes for all exact fields",
        "baseline records contain no red_route_vector_logging payload",
        "logging-enabled records contain finite red_route_vector_logging payloads",
        f"p95 red-vector logging latency is <= {spec.max_p95_red_route_vector_latency_ms} ms",
        "no formal seeds, Full36, online selector promotion, CAMP retraining, DP modification, or classic Benders claim",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source plan is missing or did not authorize implementation-only work",
        "runner does not expose the default-off red vector logging implementation",
        "paired command scope includes formal seeds or extra logging/selector flags",
        "selector-equivalence audit finds any selected-index, atom, score, weight, feasibility, PerfectTracker, or trajectory difference",
        "red-vector payload is missing, nonfinite, leaking future outcomes, or too slow",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Red Route Vector Equivalence Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke execution authorized now: `{decision['paired_smoke_execution_authorized']}`",
        "",
        "## Planned Paired Runs",
        "",
        "| Run | Variant | Command Contains Logging Flag |",
        "| --- | --- | --- |",
    ]
    for item in report["commands"]["paired_replays"]:
        has_flag = "--camp_red_route_vector_logging" in item["command"]
        lines.append(f"| `{item['run_id']}` | `{item['variant']}` | `{has_flag}` |")
    for title, checks in (
        ("Source Checks", report["source_checks"]),
        ("Implementation Checks", report["implementation_checks"]),
        ("Plan Checks", report["plan_checks"]),
    ):
        lines.extend(["", f"## {title}", "", "| Check | Passed |", "| --- | --- |"])
        for check in checks:
            lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Equivalence Contract",
            "",
            "```json",
            json.dumps(report["equivalence_contract"], indent=2, sort_keys=True),
            "```",
            "",
            "## Payload Contract",
            "",
            "```json",
            json.dumps(report["payload_contract"], indent=2, sort_keys=True),
            "```",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Accept Criteria",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


if __name__ == "__main__":
    main()
