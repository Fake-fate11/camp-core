#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
PAYLOAD_SMOKE_AUDIT = (
    ROOT / "scripts/integrations/analyze_diffusion_planner_observable_state_logging_smoke.py"
)
PAYLOAD_COVERAGE_AUDIT = (
    ROOT
    / "scripts/integrations/analyze_diffusion_planner_observable_state_payload_coverage.py"
)
SELECTOR_EQUIVALENCE = (
    ROOT / "scripts/integrations/compare_diffusion_planner_selector_logs.py"
)
DATASET_AUDIT = ROOT / "scripts/integrations/audit_diffusion_planner_camp_dataset.py"

READY_STATUS = "observable_state_logging_broader_nonformal_plan_ready"
REJECT_STATUS = "observable_state_logging_broader_nonformal_plan_rejected"
SOURCE_STATUS = "observable_state_payload_coverage_insufficient_for_materiality"
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


@dataclass(frozen=True)
class CoveragePlanSpec:
    root: str = (
        "/root/autodl-tmp/"
        "camp_dp_observable_state_logging_coverage_broader_436debb"
    )
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
    min_records_for_materiality: int = 12
    min_red_context_records: int = 1
    min_material_candidate_fields: int = 4
    runs: tuple[EvidenceRunSpec, ...] = (
        EvidenceRunSpec(
            run_id="sample_tl_seed1_npc0_tlon",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        EvidenceRunSpec(
            run_id="sample_tl_seed1_npc4_tlon",
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
            run_id="sample_tl_seed1_npc4_tloff",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("sharp_turn", "npc_interaction"),
        ),
        EvidenceRunSpec(
            run_id="sample_normal_seed1_npc0_tloff",
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
            "Design-only gate for a broader default-off observable-state "
            "logging evidence pass. It emits paired nonformal replay and audit "
            "commands, but does not run Diffusion Planner."
        )
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument(
        "--payload_smoke_audit_source",
        type=Path,
        default=PAYLOAD_SMOKE_AUDIT,
    )
    parser.add_argument(
        "--payload_coverage_audit_source",
        type=Path,
        default=PAYLOAD_COVERAGE_AUDIT,
    )
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = CoveragePlanSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        payload_smoke_audit_source=args.payload_smoke_audit_source,
        payload_coverage_audit_source=args.payload_coverage_audit_source,
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
    label: str | None = None,
    spec: CoveragePlanSpec = CoveragePlanSpec(),
    replay_source: Path = RUNNER,
    payload_smoke_audit_source: Path = PAYLOAD_SMOKE_AUDIT,
    payload_coverage_audit_source: Path = PAYLOAD_COVERAGE_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
) -> dict[str, Any]:
    source_checks = _source_checks(
        replay_source=replay_source,
        payload_smoke_audit_source=payload_smoke_audit_source,
        payload_coverage_audit_source=payload_coverage_audit_source,
        selector_equivalence_source=selector_equivalence_source,
        dataset_audit_source=dataset_audit_source,
    )
    plan_checks = _plan_checks(spec)
    passed = all(item["passed"] for item in source_checks + plan_checks)
    commands = _commands(spec)
    return {
        "analysis": {
            "name": "dp_camp_observable_state_logging_broader_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This plan only authorizes a default-off logging evidence pass. "
                "Runtime payloads must be current-tick fixed finite-candidate "
                "descriptors computed before any closed-loop outcome labels. "
                "The run must preserve DP candidates, CAMP scores, feasibility, "
                "selected indices, and PerfectTracker behavior. If any "
                "descriptor is later atomized, it must enter as a fixed "
                "candidate coefficient a_k, preserving affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 convex master. This is not a DP-side "
                "classical Benders decomposition."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "coverage_targets": _coverage_targets(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": (
                "default_off_observable_state_logging_broader_nonformal_paired_smoke_only"
                if passed
                else None
            ),
            "closed_loop_replay_authorized": passed,
            "closed_loop_replay_scope": (
                "paired nonformal logging-only matrix, 4 runs x 12 steps, "
                "baseline plus logging-enabled, no formal seeds, selector-neutral"
                if passed
                else None
            ),
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _source_checks(
    *,
    replay_source: Path,
    payload_smoke_audit_source: Path,
    payload_coverage_audit_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    payload_smoke_text = _read_text(payload_smoke_audit_source)
    payload_coverage_text = _read_text(payload_coverage_audit_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    return [
        _check_tokens(
            "replay_default_off_logging_cli",
            replay_text,
            (
                "--camp_observable_state_logging",
                "selection_effect",
                "future_outcome_leakage",
                "observable_state_logging_payload = None",
            ),
        ),
        _check_order(
            "replay_payload_before_outcomes",
            replay_text,
            "observable_state_logging_payload = _observable_state_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "payload_smoke_audit_available",
            payload_smoke_text,
            (
                "dp_camp_observable_state_logging_smoke_audit_v1",
                "observable_state_logging",
                "candidate_closed_loop_outcomes",
                "formal_seed_detected",
            ),
        ),
        _check_tokens(
            "payload_coverage_audit_available",
            payload_coverage_text,
            (
                "dp_camp_observable_state_payload_coverage_v1",
                "READY_STATUS",
                "INSUFFICIENT_STATUS",
                "closed_loop_outcome_labels_allowed",
            ),
        ),
        _check_tokens(
            "selector_equivalence_available",
            selector_text,
            (
                "diffusion_planner_selector_log_equivalence_v1",
                "selected_index",
                "selection_scores",
                "require_equivalent",
            ),
        ),
        _check_tokens(
            "dataset_audit_available",
            dataset_text,
            (
                "--closed_loop_outcome_policy",
                "--require_finite_candidate_contract",
                "--forbid_seed",
            ),
        ),
    ]


def _plan_checks(spec: CoveragePlanSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    route_names = {run.route_name for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    npc_counts = {run.max_npcs for run in spec.runs}
    bucket_counts = _bucket_counts(spec)
    total_records = int(spec.steps) * len(spec.runs)
    checks = [
        {
            "name": "formal_seeds_excluded",
            "passed": not (seeds & FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "minimum_logged_records_predeclared",
            "passed": total_records >= int(spec.min_records_for_materiality),
            "details": {
                "planned_records": total_records,
                "required_records": int(spec.min_records_for_materiality),
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
            "name": "uniform_step_count_for_paired_payload_audit",
            "passed": int(spec.steps) == 12,
            "details": {"steps": int(spec.steps)},
        },
    ]
    return checks


def _coverage_targets(spec: CoveragePlanSpec) -> dict[str, Any]:
    return {
        "planned_logs": len(spec.runs),
        "planned_records": len(spec.runs) * int(spec.steps),
        "planned_candidate_rows": (
            len(spec.runs) * int(spec.steps) * int(spec.num_candidates)
        ),
        "min_records_for_materiality": int(spec.min_records_for_materiality),
        "min_red_context_records": int(spec.min_red_context_records),
        "min_material_candidate_fields": int(spec.min_material_candidate_fields),
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _accept_criteria(spec: CoveragePlanSpec) -> list[str]:
    return [
        "all paired baseline and logging-enabled replay commands exit 0",
        "baseline summaries report camp_observable_state_logging.enabled=false",
        "logging-enabled summaries report camp_observable_state_logging.enabled=true",
        "selector equivalence passes across all paired logs",
        "payload smoke audit passes schema, finite checks, latency fields, and no-leak flags",
        "coverage audit passes validation and reaches materiality gate readiness",
        f"coverage audit sees at least {spec.min_records_for_materiality} records",
        f"coverage audit sees at least {spec.min_red_context_records} red-context records",
        f"coverage audit sees at least {spec.min_material_candidate_fields} material candidate fields",
        "dataset audit passes finite-candidate contract with closed_loop_outcome_policy=forbidden",
        "no formal seed 11/12/13 appears in any path or summary",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any source or plan check fails",
        "any replay or audit command fails",
        "any selected index, feasibility mask, atom, score, or weight changes under logging",
        "any payload contains closed-loop outcome labels or reports future_outcome_leakage=true",
        "coverage remains too small, lacks red context, or lacks material candidate-field variation",
        "the run expands beyond the predeclared nonformal 4-run x 12-step scope",
    ]


def _commands(spec: CoveragePlanSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    candidate_root = f"{spec.root}/logging_enabled"
    audit_root = f"{spec.root}/audit"
    replay_commands = []
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
    return {
        "paired_replays": replay_commands,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            candidate_root,
            audit_root,
        ),
        "payload_smoke_audit": _payload_smoke_audit_command(
            baseline_root,
            candidate_root,
            audit_root,
            spec,
        ),
        "payload_coverage_audit": _payload_coverage_audit_command(
            candidate_root,
            audit_root,
            spec,
        ),
        "dataset_audit": _dataset_audit_command(candidate_root, audit_root, spec),
    }


def _runner_command(
    spec: CoveragePlanSpec,
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
        command.append("--camp_observable_state_logging")
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


def _payload_smoke_audit_command(
    baseline_root: str,
    candidate_root: str,
    audit_root: str,
    spec: CoveragePlanSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_observable_state_logging_smoke.py",
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
        f"{audit_root}/observable_state_logging_smoke.json",
        "--output_md",
        f"{audit_root}/observable_state_logging_smoke.md",
        "--require_pass",
    ]


def _payload_coverage_audit_command(
    candidate_root: str,
    audit_root: str,
    spec: CoveragePlanSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_observable_state_payload_coverage.py",
        "--root",
        candidate_root,
        "--label",
        "broader_observable_state_logging_coverage",
        "--min_records_for_materiality",
        str(spec.min_records_for_materiality),
        "--min_red_context_records",
        str(spec.min_red_context_records),
        "--min_material_candidate_fields",
        str(spec.min_material_candidate_fields),
        "--output_json",
        f"{audit_root}/observable_state_payload_coverage.json",
        "--output_md",
        f"{audit_root}/observable_state_payload_coverage.md",
        "--require_valid",
    ]


def _dataset_audit_command(
    candidate_root: str,
    audit_root: str,
    spec: CoveragePlanSpec,
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


def _bucket_counts(spec: CoveragePlanSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _check_tokens(name: str, text: str | None, tokens: tuple[str, ...]) -> dict[str, Any]:
    missing = [token for token in tokens if text is None or token not in text]
    return {
        "name": name,
        "passed": not missing,
        "missing_tokens": missing,
    }


def _check_order(name: str, text: str | None, first: str, second: str) -> dict[str, Any]:
    if text is None:
        return {"name": name, "passed": False, "reason": "missing_source"}
    first_index = text.find(first)
    second_index = text.find(second)
    return {
        "name": name,
        "passed": first_index >= 0 and second_index >= 0 and first_index < second_index,
        "first_index": first_index,
        "second_index": second_index,
    }


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable State Logging Broader Evidence Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- scope: `{decision['closed_loop_replay_scope']}`",
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
    lines.extend(["", "## Source Checks", "", "| Check | Passed | Missing |", "| --- | --- | --- |"])
    for check in report["source_checks"]:
        missing = ", ".join(check.get("missing_tokens", []))
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{missing}` |")
    lines.extend(["", "## Plan Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Audit Commands", ""])
    separator = " \\\n  "
    for name in (
        "selector_equivalence",
        "payload_smoke_audit",
        "payload_coverage_audit",
        "dataset_audit",
    ):
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
    lines.extend(
        [
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan does not itself run DP. It only authorizes the exact "
            "nonformal logging-only evidence pass if all source and plan checks "
            "remain valid.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
