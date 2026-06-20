#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
SELECTOR_EQUIVALENCE = (
    ROOT / "scripts/integrations/compare_diffusion_planner_selector_logs.py"
)
DATASET_AUDIT = ROOT / "scripts/integrations/audit_diffusion_planner_camp_dataset.py"
MATCHED_CONTRACT_AUDIT = (
    ROOT / "scripts/integrations/analyze_diffusion_planner_matched_observable_outcomes.py"
)

READY_STATUS = "matched_observable_outcome_label_pass_plan_ready"
REJECT_STATUS = "matched_observable_outcome_label_pass_plan_rejected"
FORMAL_SEEDS = frozenset({11, 12, 13})


@dataclass(frozen=True)
class MatchedRunSpec:
    run_id: str
    route_name: str
    route: str
    seed: int
    max_npcs: int
    spawn_probability: float
    traffic_lights: str
    scenario_buckets: tuple[str, ...]


@dataclass(frozen=True)
class MatchedPlanSpec:
    root: str = (
        "/root/autodl-tmp/"
        "camp_dp_matched_observable_outcome_labels_nonformal_v1"
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
    camp_outcome_horizon_steps: int = 30
    runs: tuple[MatchedRunSpec, ...] = (
        MatchedRunSpec(
            run_id="sample_tl_seed1_npc0_tlon",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        MatchedRunSpec(
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
        MatchedRunSpec(
            run_id="sample_tl_seed1_npc4_tloff",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=1,
            max_npcs=4,
            spawn_probability=0.3,
            traffic_lights="off",
            scenario_buckets=("sharp_turn", "npc_interaction"),
        ),
        MatchedRunSpec(
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
            "Design-only gate for a nonformal matched observable-state plus "
            "candidate-outcome-label replay pass. It emits commands and "
            "accept/reject gates, but does not run Diffusion Planner."
        )
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=REPLAY)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    parser.add_argument(
        "--matched_contract_audit_source",
        type=Path,
        default=MATCHED_CONTRACT_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = MatchedPlanSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        matched_contract_audit_source=args.matched_contract_audit_source,
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
    label: str | None = None,
    spec: MatchedPlanSpec = MatchedPlanSpec(),
    replay_source: Path = REPLAY,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    matched_contract_audit_source: Path = MATCHED_CONTRACT_AUDIT,
) -> dict[str, Any]:
    source_checks = _source_checks(
        replay_source=replay_source,
        selector_equivalence_source=selector_equivalence_source,
        dataset_audit_source=dataset_audit_source,
        matched_contract_audit_source=matched_contract_audit_source,
    )
    plan_checks = _plan_checks(spec)
    passed = all(item["passed"] for item in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_matched_observable_outcome_label_pass_plan_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "formal_seed_records": 0,
            "future_outcome_leakage": False,
            "math_boundary": (
                "The planned matched run records current-tick observable "
                "finite-candidate descriptors and offline candidate outcomes in "
                "the same replay record. Outcome labels are posterior labels "
                "only and are forbidden as runtime selector features. CAMP "
                "score_k(w)=a_k^T w remains affine over fixed atoms and the "
                "simplex/CVaR/L2 robust master remains convex. No DP-side "
                "classical Benders decomposition, dual, or cut is claimed."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "plan_spec": asdict(spec),
        "coverage_targets": _coverage_targets(spec),
        "commands": _commands(spec),
        "accept_criteria": _accept_criteria(spec),
        "reject_criteria": _reject_criteria(),
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": (
                "matched_observable_outcome_label_pass_nonformal_smoke_only"
                if passed
                else None
            ),
            "replay_authorized_scope": (
                "4 paired nonformal runs x 12 steps; matched branch only "
                "collects observable_state_logging and candidate_closed_loop_outcomes"
                if passed
                else None
            ),
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def _source_checks(
    *,
    replay_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
    matched_contract_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    matched_text = _read_text(matched_contract_audit_source)
    return [
        _check_tokens(
            "replay_supports_matched_logging_and_labels",
            replay_text,
            (
                "--camp_observable_state_logging",
                "--camp_collect_closed_loop_outcomes",
                "observable_state_logging_payload = _observable_state_logging_payload(",
                "compute_candidate_closed_loop_outcomes(",
            ),
        ),
        _check_order(
            "replay_computes_observable_payload_before_outcomes",
            replay_text,
            "observable_state_logging_payload = _observable_state_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "selector_equivalence_audit_available",
            selector_text,
            ("selected_index", "selection_scores", "require_equivalent"),
        ),
        _check_tokens(
            "dataset_required_outcome_audit_available",
            dataset_text,
            (
                "--closed_loop_outcome_policy",
                "required",
                "--require_finite_candidate_contract",
                "--forbid_seed",
            ),
        ),
        _check_tokens(
            "matched_contract_audit_available",
            matched_text,
            (
                "dp_camp_matched_observable_outcome_contract_v1",
                "observable_state_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
    ]


def _plan_checks(spec: MatchedPlanSpec) -> list[dict[str, Any]]:
    seeds = {run.seed for run in spec.runs}
    traffic_modes = {run.traffic_lights for run in spec.runs}
    npc_counts = {run.max_npcs for run in spec.runs}
    route_names = {run.route_name for run in spec.runs}
    bucket_counts = _bucket_counts(spec)
    return [
        {
            "name": "formal_seeds_excluded",
            "passed": not (seeds & FORMAL_SEEDS),
            "details": {"seeds": sorted(seeds), "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "small_nonformal_smoke_scope",
            "passed": len(spec.runs) == 4 and int(spec.steps) == 12,
            "details": {"runs": len(spec.runs), "steps": int(spec.steps)},
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
    ]


def _coverage_targets(spec: MatchedPlanSpec) -> dict[str, Any]:
    return {
        "paired_runs": len(spec.runs),
        "baseline_logs": len(spec.runs),
        "matched_logs": len(spec.runs),
        "matched_records": len(spec.runs) * int(spec.steps),
        "matched_candidate_rows": (
            len(spec.runs) * int(spec.steps) * int(spec.num_candidates)
        ),
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _commands(spec: MatchedPlanSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    matched_root = f"{spec.root}/matched_observable_outcomes"
    audit_root = f"{spec.root}/audit"
    replays: list[dict[str, Any]] = []
    for run in spec.runs:
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "baseline",
                "command": _replay_command(spec, run, f"{baseline_root}/{run.run_id}", matched=False),
                "shell": shlex.join(
                    _replay_command(spec, run, f"{baseline_root}/{run.run_id}", matched=False)
                ),
            }
        )
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "matched_observable_outcomes",
                "command": _replay_command(spec, run, f"{matched_root}/{run.run_id}", matched=True),
                "shell": shlex.join(
                    _replay_command(spec, run, f"{matched_root}/{run.run_id}", matched=True)
                ),
            }
        )
    return {
        "paired_replays": replays,
        "selector_equivalence": _selector_equivalence_command(
            baseline_root,
            matched_root,
            audit_root,
        ),
        "dataset_required_outcome_audit": _dataset_audit_command(
            matched_root,
            audit_root,
            spec,
        ),
        "matched_contract_audit": _matched_contract_command(
            matched_root,
            audit_root,
            spec,
        ),
    }


def _replay_command(
    spec: MatchedPlanSpec,
    run: MatchedRunSpec,
    output_dir: str,
    *,
    matched: bool,
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
        str(spec.camp_outcome_horizon_steps),
        "--near_miss_threshold_m",
        "2.0",
    ]
    if matched:
        command.extend(
            [
                "--camp_observable_state_logging",
                "--camp_collect_closed_loop_outcomes",
            ]
        )
    return command


def _selector_equivalence_command(
    baseline_root: str,
    matched_root: str,
    audit_root: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/compare_diffusion_planner_selector_logs.py",
        "--baseline_root",
        baseline_root,
        "--candidate_root",
        matched_root,
        "--output_json",
        f"{audit_root}/selector_equivalence.json",
        "--require_equivalent",
    ]


def _dataset_audit_command(
    matched_root: str,
    audit_root: str,
    spec: MatchedPlanSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--root",
        matched_root,
        "--atom_scales",
        spec.atom_scales,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_candidates",
        str(spec.num_candidates),
        "--expected_advance_mode",
        "perfect",
        "--expected_candidate_reference_blend_steps",
        str(spec.candidate_reference_blend_steps),
        "--closed_loop_outcome_policy",
        "required",
        "--require_finite_candidate_contract",
        "--forbid_seed",
        "11",
        "--forbid_seed",
        "12",
        "--forbid_seed",
        "13",
        "--output_json",
        f"{audit_root}/dataset_required_outcome_audit.json",
    ]


def _matched_contract_command(
    matched_root: str,
    audit_root: str,
    spec: MatchedPlanSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_matched_observable_outcomes.py",
        "--root",
        matched_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--label",
        "matched_observable_outcome_labels_nonformal_v1",
        "--output_json",
        f"{audit_root}/matched_observable_outcome_contract.json",
        "--output_md",
        f"{audit_root}/matched_observable_outcome_contract.md",
        "--require_pass",
    ]


def _accept_criteria(spec: MatchedPlanSpec) -> list[str]:
    return [
        "all source and plan checks pass before replay",
        "all paired baseline and matched replay commands exit 0",
        "matched records contain observable_state_logging payloads and candidate_closed_loop_outcomes in the same record",
        "observable payloads report selection_effect=false and future_outcome_leakage=false",
        "observable payloads do not embed candidate_closed_loop_outcomes",
        "selector equivalence passes between baseline and matched branches",
        "dataset audit passes with closed_loop_outcome_policy=required",
        "matched contract audit passes for all records and candidates",
        f"exactly {len(spec.runs)} matched logs and {len(spec.runs) * int(spec.steps)} matched records are present",
        "no formal seed 11/12/13 appears in any path, summary, or record",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any source or plan check fails",
        "any replay or audit command fails",
        "any matched record lacks observable_state_logging or candidate_closed_loop_outcomes",
        "any selected index, feasibility mask, atom, score, or weight changes under logging/outcome collection",
        "any runtime descriptor uses closed-loop outcome labels or reports future_outcome_leakage=true",
        "any formal seed appears",
        "the run expands beyond the predeclared 4-run x 12-step nonformal scope",
    ]


def _bucket_counts(spec: MatchedPlanSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _check_tokens(name: str, text: str | None, tokens: tuple[str, ...]) -> dict[str, Any]:
    missing = [] if text is None else [token for token in tokens if token not in text]
    return {
        "name": name,
        "passed": text is not None and not missing,
        "missing": missing if text is not None else list(tokens),
    }


def _check_order(name: str, text: str | None, first: str, second: str) -> dict[str, Any]:
    first_idx = -1 if text is None else text.find(first)
    second_idx = -1 if text is None else text.find(second)
    return {
        "name": name,
        "passed": first_idx >= 0 and second_idx >= 0 and first_idx < second_idx,
        "first_index": first_idx,
        "second_index": second_idx,
    }


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Matched Observable Outcome Label Pass Plan",
        "",
        "This is a design-only plan. It does not run Diffusion Planner, does not "
        "train CAMP, and does not authorize online selector promotion.",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(report["coverage_targets"], indent=2, sort_keys=True),
        "```",
        "",
        "## Source Checks",
        "",
    ]
    lines.extend(
        f"- {item['name']}: {item['passed']}" for item in report["source_checks"]
    )
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(f"- {item['name']}: {item['passed']}" for item in report["plan_checks"])
    lines.extend(["", "## Replay Commands", ""])
    for item in report["commands"]["paired_replays"]:
        lines.extend(
            [
                f"### {item['variant']} / {item['run_id']}",
                "",
                "```bash",
                item["shell"],
                "```",
                "",
            ]
        )
    lines.extend(["## Audit Commands", ""])
    for name, command in report["commands"].items():
        if name == "paired_replays":
            continue
        lines.extend(["```bash", shlex.join(command), "```", ""])
    lines.extend(
        [
            "## Decision",
            "",
            f"status=`{report['final_decision']['status']}`",
            f"passed=`{report['final_decision']['passed']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
