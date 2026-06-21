#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


READY_STATUS = "observable_interaction_coverage_broader_nonformal_plan_ready"
REJECT_STATUS = "observable_interaction_coverage_broader_nonformal_plan_rejected"
SOURCE_STATUS = "observable_interaction_descriptor_bottleneck_diagnosed"
SOURCE_NEXT_WORK = "predeclare_broader_nonformal_observable_interaction_coverage_plan_only"
AUTHORIZED_NEXT_WORK = "observable_interaction_coverage_broader_nonformal_paired_smoke_only"
FORMAL_SEEDS = frozenset({11, 12, 13})


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
    target_context_families: tuple[str, ...]
    expected_descriptor_targets: tuple[str, ...]


@dataclass(frozen=True)
class CoveragePlanSpec:
    root: str = "/root/autodl-tmp/camp_dp_observable_interaction_coverage_broader_nonformal_smoke"
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
    red_distance_budget_m: float = 5.0
    clearance_budget_m: float = 2.0
    lateral_error_budget_m: float = 0.5
    min_records_for_materiality: int = 48
    min_candidate_rows_for_materiality: int = 384
    min_red_context_records: int = 1
    min_clearance_context_records: int = 1
    min_turn_lateral_context_records: int = 1
    runs: tuple[EvidenceRunSpec, ...] = (
        EvidenceRunSpec(
            run_id="tl_route59_seed1_npc0_tlon",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.0,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light", "turn_lateral"),
            target_context_families=("red_context", "turn_lateral_context"),
            expected_descriptor_targets=(
                "red_aligned_stopline_proximity_hinge_v1",
                "turn_lateral_clearance_context_hinge_v1",
            ),
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
                "red_light",
                "npc_interaction",
                "clearance",
                "turn_lateral",
            ),
            target_context_families=(
                "red_context",
                "clearance_context",
                "turn_lateral_context",
            ),
            expected_descriptor_targets=(
                "red_aligned_stopline_proximity_hinge_v1",
                "clearance_progress_tradeoff_hinge_v1",
                "turn_lateral_clearance_context_hinge_v1",
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
            scenario_buckets=("npc_interaction", "clearance", "turn_lateral"),
            target_context_families=("clearance_context", "turn_lateral_context"),
            expected_descriptor_targets=(
                "clearance_progress_tradeoff_hinge_v1",
                "turn_lateral_clearance_context_hinge_v1",
            ),
        ),
        EvidenceRunSpec(
            run_id="normal_route2_seed1_npc0_tloff",
            route_name="sample_map_route_2_to_104",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.0,
            traffic_lights="off",
            scenario_buckets=("normal_control",),
            target_context_families=("normal_control",),
            expected_descriptor_targets=("top1_deviation_without_current_safety_gain_v1",),
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a broader nonformal observable interaction "
            "coverage pass. It reads the bottleneck artifact and emits the "
            "next paired-smoke scope, but does not run Diffusion Planner."
        )
    )
    parser.add_argument("--bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = CoveragePlanSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        bottleneck_report=_read_json(args.bottleneck_json),
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
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    spec: CoveragePlanSpec = CoveragePlanSpec(),
) -> dict[str, Any]:
    source_checks = _source_checks(bottleneck_report)
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    commands = _commands(spec)
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_coverage_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This is a design-only gate. It predeclares current-tick "
                "observable-state coverage targets for a later nonformal paired "
                "smoke. It creates no selector threshold and no CAMP atom. Any "
                "later atomization must use finite candidate coefficients so "
                "score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. No DP-side classical Benders "
                "master/subproblem, dual, or valid cut is constructed."
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
            "classic_Benders_claim": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: paired nonformal observable interaction "
                "coverage matrix, 4 runs x 12 steps, baseline plus "
                "observable-logging-enabled, no formal seeds, selector-neutral"
                if passed
                else None
            ),
            "new_replay_authorized": False,
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
    materiality = report.get("payload_materiality") if isinstance(report, dict) else None
    diagnostics = report.get("descriptor_diagnostics") if isinstance(report, dict) else None
    diagnosis = report.get("diagnosis") if isinstance(report, dict) else None
    records = report.get("records") if isinstance(report, dict) else None
    final = final if isinstance(final, dict) else {}
    materiality = materiality if isinstance(materiality, dict) else {}
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    diagnosis = diagnosis if isinstance(diagnosis, dict) else {}
    records = records if isinstance(records, dict) else {}

    collapsed = set(diagnostics.get("collapsed_descriptors") or [])
    missing_context = set(diagnosis.get("missing_context_families") or [])
    return [
        {
            "name": "source_bottleneck_gate_authorizes_plan_only",
            "passed": final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK,
            "final_decision": final,
        },
        {
            "name": "source_records_are_nonformal_and_finite_candidate",
            "passed": int(records.get("formal_seed_records", -1)) == 0
            and int(records.get("candidate_rows", 0)) > 0
            and int(records.get("alternative_rows", 0)) > 0,
            "records": records,
        },
        {
            "name": "source_gap_is_missing_red_and_clearance_context",
            "passed": "red_context" in missing_context
            and "clearance_context" in missing_context
            and int(materiality.get("records_with_red_risk_candidate_variation", -1))
            == 0
            and int(
                materiality.get(
                    "records_with_clearance_deficit_candidate_variation", -1
                )
            )
            == 0,
            "missing_context_families": sorted(missing_context),
            "payload_materiality": materiality,
        },
        {
            "name": "source_collapsed_interaction_descriptors_present",
            "passed": {
                "red_aligned_stopline_proximity_hinge_v1",
                "clearance_progress_tradeoff_hinge_v1",
                "turn_lateral_clearance_context_hinge_v1",
            }.issubset(collapsed),
            "collapsed_descriptors": sorted(collapsed),
        },
    ]


def _plan_checks(spec: CoveragePlanSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    buckets = _bucket_counts(spec)
    context_families = _context_family_counts(spec)
    descriptor_targets = _descriptor_target_counts(spec)
    total_records = len(spec.runs) * int(spec.steps)
    total_candidates = total_records * int(spec.num_candidates)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": not seeds.intersection(FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "planned_records_and_candidates_material",
            "passed": total_records >= int(spec.min_records_for_materiality)
            and total_candidates >= int(spec.min_candidate_rows_for_materiality),
            "details": {
                "planned_records": total_records,
                "planned_candidate_rows": total_candidates,
            },
        },
        {
            "name": "traffic_light_on_and_off_covered",
            "passed": {"on", "off"}.issubset(traffic_modes),
            "details": {"traffic_light_modes": sorted(traffic_modes)},
        },
        {
            "name": "red_clearance_turn_and_normal_buckets_covered",
            "passed": all(
                buckets.get(bucket, 0) > 0
                for bucket in (
                    "red_light",
                    "clearance",
                    "turn_lateral",
                    "normal_control",
                )
            ),
            "details": {"scenario_bucket_counts": buckets},
        },
        {
            "name": "target_context_families_covered",
            "passed": all(
                context_families.get(family, 0) > 0
                for family in (
                    "red_context",
                    "clearance_context",
                    "turn_lateral_context",
                    "normal_control",
                )
            ),
            "details": {"target_context_family_counts": context_families},
        },
        {
            "name": "collapsed_descriptor_targets_revisited",
            "passed": all(
                descriptor_targets.get(name, 0) > 0
                for name in (
                    "red_aligned_stopline_proximity_hinge_v1",
                    "clearance_progress_tradeoff_hinge_v1",
                    "turn_lateral_clearance_context_hinge_v1",
                )
            ),
            "details": {"expected_descriptor_target_counts": descriptor_targets},
        },
    ]


def _coverage_targets(spec: CoveragePlanSpec) -> dict[str, Any]:
    planned_records = len(spec.runs) * int(spec.steps)
    return {
        "planned_logs": len(spec.runs),
        "planned_records": planned_records,
        "planned_candidate_rows": planned_records * int(spec.num_candidates),
        "min_records_for_materiality": int(spec.min_records_for_materiality),
        "min_candidate_rows_for_materiality": int(
            spec.min_candidate_rows_for_materiality
        ),
        "min_red_context_records": int(spec.min_red_context_records),
        "min_clearance_context_records": int(spec.min_clearance_context_records),
        "min_turn_lateral_context_records": int(
            spec.min_turn_lateral_context_records
        ),
        "scenario_bucket_counts": _bucket_counts(spec),
        "target_context_family_counts": _context_family_counts(spec),
        "expected_descriptor_target_counts": _descriptor_target_counts(spec),
    }


def _accept_criteria(spec: CoveragePlanSpec) -> list[str]:
    return [
        "source bottleneck artifact passes and authorizes only a broader coverage plan",
        "paired replay remains selector-neutral: selected index, feasibility, atoms, scores, and weights unchanged",
        "observable logging payload reports default_off=true, selection_effect=false, and future_outcome_leakage=false",
        "coverage audit finds at least one red-risk candidate-variation record",
        "coverage audit finds at least one clearance-deficit candidate-variation record",
        "coverage audit finds at least one turn/lateral candidate-variation record",
        "normal-control run is present so red/clearance descriptors can be checked for non-spurious activation",
        f"scope remains {len(spec.runs)} paired nonformal runs x {spec.steps} steps x {spec.num_candidates} candidates",
        "no formal seed 11/12/13 appears in any command, path, or summary",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source bottleneck artifact is missing, not passed, or does not authorize coverage-plan-only work",
        "any plan check fails",
        "the next gate tries to run Full36, formal seeds, online selector promotion, CAMP retraining, DP modification, or a classic Benders claim",
        "the next coverage smoke lacks red-risk, clearance-deficit, turn/lateral, or normal-control evidence",
        "logging changes selection, feasibility, atoms, scores, or weights",
        "any runtime payload uses closed-loop outcome labels or future outcome leakage",
    ]


def _commands(spec: CoveragePlanSpec) -> dict[str, Any]:
    paired_replays = []
    for run in spec.runs:
        for variant in ("baseline", "observable_logging_enabled"):
            output_dir = (
                f"{spec.root}/logs/{run.run_id}/"
                f"{'baseline' if variant == 'baseline' else 'observable_logging'}"
            )
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
            if variant == "observable_logging_enabled":
                command.append("--camp_observable_state_logging")
            paired_replays.append(
                {
                    "run_id": run.run_id,
                    "variant": variant,
                    "command": command,
                }
            )

    return {
        "paired_replays": paired_replays,
        "required_followup_checks": {
            "selector_equivalence_contract": [
                "selected_index unchanged between baseline and observable logging",
                "feasibility masks unchanged between baseline and observable logging",
                "CAMP atoms, scores, and weights unchanged between baseline and observable logging",
                "observable logging reports selection_effect=false",
            ],
            "observable_interaction_coverage_contract": [
                "records_with_red_risk_candidate_variation >= 1",
                "records_with_clearance_deficit_candidate_variation >= 1",
                "records_with_turn_signal_candidate_variation >= 1",
                "records_with_lateral_excess_candidate_variation >= 1",
                "normal-control run produces no spurious red or clearance activation",
                "coverage audit reads only current-tick observable payload fields",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable Interaction Coverage Broader Nonformal Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        (
            "- paired smoke execution authorized now: "
            f"`{decision['paired_smoke_execution_authorized']}`"
        ),
        f"- scope: `{decision['paired_smoke_execution_scope']}`",
        "",
        "## Coverage Targets",
        "",
        "| Target | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["coverage_targets"].items():
        if isinstance(value, dict):
            value = json.dumps(value, sort_keys=True)
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Planned Runs",
            "",
            "| Run | Route | Seed | NPCs | TL | Buckets | Target Context |",
            "| --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for run in report["plan_spec"]["runs"]:
        lines.append(
            f"| `{run['run_id']}` | `{run['route_name']}` | `{run['seed']}` | "
            f"`{run['max_npcs']}` | `{run['traffic_lights']}` | "
            f"`{','.join(run['scenario_buckets'])}` | "
            f"`{','.join(run['target_context_families'])}` |"
        )

    lines.extend(["", "## Source Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Plan Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")

    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"]])
    lines.extend(["", "## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            "If this gate is accepted, the next gate may execute only the "
            "predeclared paired nonformal observable-interaction coverage smoke. "
            "This plan itself runs no replay and authorizes no Full36, formal "
            "seeds, online selector promotion, CAMP retraining, DP modification, "
            "or classic Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _bucket_counts(spec: CoveragePlanSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _context_family_counts(spec: CoveragePlanSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for family in run.target_context_families:
            counts[family] = counts.get(family, 0) + 1
    return counts


def _descriptor_target_counts(spec: CoveragePlanSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for descriptor in run.expected_descriptor_targets:
            counts[descriptor] = counts.get(descriptor, 0) + 1
    return counts


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
