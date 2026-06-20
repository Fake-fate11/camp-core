#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_progress_support_broader_nonformal_smoke import (
    BroaderSmokeSpec as ProgressBroaderSmokeSpec,
    EvidenceRunSpec,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_progress_support_logging_smoke import (
    DATASET_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _check_order,
    _check_tokens,
)


ROOT = Path(__file__).resolve().parents[2]
JOINT_PREFLIGHT_READY_STATUS = "progress_lane_hard_joint_screen_preflight_ready"
JOINT_PREFLIGHT_NEXT_WORK = "progress_lane_hard_joint_cologged_outcome_plan_only"
READY_STATUS = "progress_lane_hard_joint_cologged_outcome_label_pass_plan_ready"
REJECT_STATUS = "progress_lane_hard_joint_cologged_outcome_label_pass_plan_rejected"
AUTHORIZED_NEXT_WORK = "progress_lane_hard_joint_cologged_outcome_nonformal_smoke_only"

MATCHED_PROGRESS_CONTRACT_AUDIT = (
    ROOT / "scripts/integrations/analyze_diffusion_planner_matched_progress_support_outcomes.py"
)
MATCHED_LANE_HARD_CONTRACT_AUDIT = (
    ROOT
    / "scripts/integrations/analyze_diffusion_planner_matched_lane_hard_violation_support_outcomes.py"
)


@dataclass(frozen=True)
class JointCologgedSpec:
    root: str = (
        "/root/autodl-tmp/"
        "camp_dp_progress_lane_hard_joint_cologged_outcomes_nonformal_v1"
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
    progress_support_steps: int = 10
    progress_support_dt_s: float = 0.1
    lane_hard_support_steps: int = 10
    lane_hard_dt_s: float = 0.1
    lane_hard_corridor_half_width_m: float = 1.75
    lane_hard_lateral_rate_budget_mps: float = 1.0
    runs: tuple[EvidenceRunSpec, ...] = ProgressBroaderSmokeSpec().runs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a nonformal same-record co-logged "
            "progress-support plus lane/hard-violation support outcome pass. "
            "It emits commands and accept/reject gates, but does not run "
            "Diffusion Planner."
        )
    )
    parser.add_argument("--joint_preflight_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    parser.add_argument(
        "--matched_progress_contract_audit_source",
        type=Path,
        default=MATCHED_PROGRESS_CONTRACT_AUDIT,
    )
    parser.add_argument(
        "--matched_lane_hard_contract_audit_source",
        type=Path,
        default=MATCHED_LANE_HARD_CONTRACT_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = JointCologgedSpec()
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        joint_preflight_report=_read_json(args.joint_preflight_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        matched_progress_contract_audit_source=(
            args.matched_progress_contract_audit_source
        ),
        matched_lane_hard_contract_audit_source=(
            args.matched_lane_hard_contract_audit_source
        ),
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
    joint_preflight_report: dict[str, Any],
    label: str | None = None,
    spec: JointCologgedSpec | None = None,
    replay_source: Path = RUNNER,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    matched_progress_contract_audit_source: Path = MATCHED_PROGRESS_CONTRACT_AUDIT,
    matched_lane_hard_contract_audit_source: Path = MATCHED_LANE_HARD_CONTRACT_AUDIT,
) -> dict[str, Any]:
    if spec is None:
        spec = JointCologgedSpec()
    source_checks = [
        *_source_artifact_checks(joint_preflight_report),
        *_source_text_checks(
            replay_source=replay_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
            matched_progress_contract_audit_source=(
                matched_progress_contract_audit_source
            ),
            matched_lane_hard_contract_audit_source=(
                matched_lane_hard_contract_audit_source
            ),
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_progress_lane_hard_joint_cologged_outcome_label_pass_plan_v1"
            ),
            "label": label,
            "source_status": JOINT_PREFLIGHT_READY_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "formal_seed_records": 0,
            "future_outcome_leakage": False,
            "same_record_cologging_required": True,
            "math_boundary": (
                "The planned matched branch records current-tick "
                "progress-support atoms, lane/hard support atoms, and posterior "
                "candidate outcomes in the same replay record. Outcome labels "
                "are offline labels only and are forbidden as runtime selector "
                "features. Concatenating both nonnegative atom vectors preserves "
                "affine score_k(w)=a_k^T w for fixed candidate coefficients and "
                "keeps the simplex/CVaR/L2 robust master convex. No DP-side "
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
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: 4 paired nonformal runs x 12 steps; matched "
                "branch collects progress_support_logging, "
                "lane_hard_violation_support_logging, and "
                "candidate_closed_loop_outcomes in each record"
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


def _source_artifact_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    final = report.get("final_decision", {}) if isinstance(report, dict) else {}
    evidence = report.get("complementarity_evidence", {}) if isinstance(report, dict) else {}
    criteria = (
        (report.get("analysis") or {}).get("next_gate_accept_criteria") or {}
        if isinstance(report, dict)
        else {}
    )
    return [
        {
            "name": "joint_preflight_ready",
            "passed": final.get("status") == JOINT_PREFLIGHT_READY_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == JOINT_PREFLIGHT_NEXT_WORK,
            "status": final.get("status"),
            "authorized_next_work": final.get("authorized_next_work"),
        },
        {
            "name": "joint_preflight_blocks_training_and_online_selector",
            "passed": _false_flag(
                final,
                "CAMP_retraining_authorized",
                "camp_retraining_authorized",
            )
            and _false_flag(final, "online_selector_authorized")
            and _false_flag(final, "DP_modification_authorized", "dp_modification_authorized")
            and _false_flag(final, "formal_seeds_authorized"),
        },
        {
            "name": "complementary_blind_spots_established",
            "passed": evidence.get("complementary_blind_spots_established") is True,
            "primary_gap": evidence.get("primary_gap"),
        },
        {
            "name": "same_record_cologging_required_by_source",
            "passed": criteria.get("requires_same_record_cologged_progress_and_lane_hard_payloads")
            is True
            and criteria.get("formal_seed_records") == 0
            and criteria.get("selector_effect") is False,
            "criteria": criteria,
        },
    ]


def _source_text_checks(
    *,
    replay_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
    matched_progress_contract_audit_source: Path,
    matched_lane_hard_contract_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    progress_text = _read_text(matched_progress_contract_audit_source)
    lane_text = _read_text(matched_lane_hard_contract_audit_source)
    return [
        _check_tokens(
            "replay_supports_joint_logging_and_outcome_labels",
            replay_text,
            (
                "--camp_progress_support_logging",
                "--camp_lane_hard_violation_support_logging",
                "--camp_collect_closed_loop_outcomes",
                "build_progress_support_logging_payload(",
                "build_lane_hard_violation_support_logging_payload(",
                "compute_candidate_closed_loop_outcomes(",
            ),
        ),
        _check_order(
            "replay_computes_progress_payload_before_outcomes",
            replay_text,
            "build_progress_support_logging_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_order(
            "replay_computes_lane_hard_payload_before_outcomes",
            replay_text,
            "build_lane_hard_violation_support_logging_payload(",
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
            "matched_progress_contract_audit_available",
            progress_text,
            (
                "dp_camp_matched_progress_support_outcome_contract_v1",
                "progress_support_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
        _check_tokens(
            "matched_lane_hard_contract_audit_available",
            lane_text,
            (
                "dp_camp_matched_lane_hard_violation_support_outcome_contract_v1",
                "lane_hard_violation_support_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
    ]


def _plan_checks(spec: JointCologgedSpec) -> list[dict[str, Any]]:
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
            "name": "fixed_candidate_pool_size",
            "passed": int(spec.num_candidates) == 8,
            "details": {"num_candidates": int(spec.num_candidates)},
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
        {
            "name": "lane_hard_support_horizon_fixed",
            "passed": int(spec.lane_hard_support_steps) == 10
            and abs(float(spec.lane_hard_dt_s) - 0.1) <= 1e-12
            and float(spec.lane_hard_corridor_half_width_m) > 0.0
            and float(spec.lane_hard_lateral_rate_budget_mps) >= 0.0,
            "details": {
                "lane_hard_support_steps": int(spec.lane_hard_support_steps),
                "lane_hard_dt_s": float(spec.lane_hard_dt_s),
                "lane_hard_corridor_half_width_m": float(
                    spec.lane_hard_corridor_half_width_m
                ),
                "lane_hard_lateral_rate_budget_mps": float(
                    spec.lane_hard_lateral_rate_budget_mps
                ),
            },
        },
    ]


def _coverage_targets(spec: JointCologgedSpec) -> dict[str, Any]:
    return {
        "paired_runs": len(spec.runs),
        "baseline_logs": len(spec.runs),
        "matched_joint_logs": len(spec.runs),
        "matched_records": len(spec.runs) * int(spec.steps),
        "matched_candidate_rows": (
            len(spec.runs) * int(spec.steps) * int(spec.num_candidates)
        ),
        "scenario_bucket_counts": _bucket_counts(spec),
    }


def _commands(spec: JointCologgedSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    matched_root = f"{spec.root}/matched_joint_outcomes"
    audit_root = f"{spec.root}/audit"
    replays: list[dict[str, Any]] = []
    for run in spec.runs:
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "baseline",
                "command": _replay_command(
                    spec,
                    run,
                    f"{baseline_root}/{run.run_id}",
                    matched=False,
                ),
            }
        )
        replays.append(
            {
                "run_id": run.run_id,
                "variant": "matched_progress_lane_hard_joint_outcomes",
                "command": _replay_command(
                    spec,
                    run,
                    f"{matched_root}/{run.run_id}",
                    matched=True,
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
        "matched_progress_contract_audit": _matched_progress_contract_command(
            matched_root,
            audit_root,
            spec,
        ),
        "matched_lane_hard_contract_audit": _matched_lane_hard_contract_command(
            matched_root,
            audit_root,
            spec,
        ),
    }


def _replay_command(
    spec: JointCologgedSpec,
    run: EvidenceRunSpec,
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
        "30",
        "--near_miss_threshold_m",
        "2.0",
    ]
    if matched:
        command.extend(
            [
                "--camp_progress_support_logging",
                "--camp_progress_support_steps",
                str(spec.progress_support_steps),
                "--camp_progress_support_dt_s",
                str(spec.progress_support_dt_s),
                "--camp_lane_hard_violation_support_logging",
                "--camp_lane_hard_violation_support_steps",
                str(spec.lane_hard_support_steps),
                "--camp_lane_hard_violation_support_dt_s",
                str(spec.lane_hard_dt_s),
                "--camp_lane_hard_violation_corridor_half_width_m",
                str(spec.lane_hard_corridor_half_width_m),
                "--camp_lane_hard_violation_lateral_rate_budget_mps",
                str(spec.lane_hard_lateral_rate_budget_mps),
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
    spec: JointCologgedSpec,
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


def _matched_progress_contract_command(
    matched_root: str,
    audit_root: str,
    spec: JointCologgedSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_matched_progress_support_outcomes.py",
        "--root",
        matched_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--label",
        "progress_lane_hard_joint_cologged_outcomes_nonformal_v1",
        "--output_json",
        f"{audit_root}/matched_progress_support_outcome_contract.json",
        "--output_md",
        f"{audit_root}/matched_progress_support_outcome_contract.md",
        "--require_pass",
    ]


def _matched_lane_hard_contract_command(
    matched_root: str,
    audit_root: str,
    spec: JointCologgedSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_matched_lane_hard_violation_support_outcomes.py",
        "--root",
        matched_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--label",
        "progress_lane_hard_joint_cologged_outcomes_nonformal_v1",
        "--output_json",
        f"{audit_root}/matched_lane_hard_violation_support_outcome_contract.json",
        "--output_md",
        f"{audit_root}/matched_lane_hard_violation_support_outcome_contract.md",
        "--require_pass",
    ]


def _accept_criteria(spec: JointCologgedSpec) -> list[str]:
    return [
        "all source and plan checks pass before replay",
        "all paired baseline and matched replay commands exit 0",
        "matched records contain progress_support_logging, lane_hard_violation_support_logging, and candidate_closed_loop_outcomes in the same record",
        "both payloads report selection_effect=false and future_outcome_leakage=false",
        "neither payload embeds candidate_closed_loop_outcomes",
        "selector equivalence passes between baseline and matched branches",
        "dataset audit passes with closed_loop_outcome_policy=required",
        "matched progress contract audit passes for all records and candidates",
        "matched lane/hard contract audit passes for all records and candidates",
        f"exactly {len(spec.runs)} matched logs and {len(spec.runs) * int(spec.steps)} matched records are present",
        "no formal seed 11/12/13 appears in any path, summary, or record",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any source or plan check fails",
        "any replay or audit command fails",
        "any matched record lacks progress_support_logging, lane_hard_violation_support_logging, or candidate_closed_loop_outcomes",
        "any selected index, feasibility mask, atom, score, or weight changes under logging/outcome collection",
        "any runtime descriptor uses closed-loop outcome labels or reports future_outcome_leakage=true",
        "any formal seed appears",
        "the run expands beyond the predeclared 4-run x 12-step nonformal scope",
    ]


def _bucket_counts(spec: JointCologgedSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _false_flag(row: dict[str, Any], *names: str) -> bool:
    return any(row.get(name) is False for name in names)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress + Lane/Hard Joint Co-Logged Outcome Label Pass Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke execution authorized now: `{decision['paired_smoke_execution_authorized']}`",
        f"- scope: `{decision['paired_smoke_execution_scope']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(
        f"- `{check['name']}`: `{check['passed']}`"
        for check in report["plan_checks"]
    )
    lines.extend(["", "## Coverage Targets", "", "```json"])
    lines.append(json.dumps(report["coverage_targets"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Commands", ""])
    command_separator = " \\\n" "  "
    for item in report["commands"]["paired_replays"]:
        lines.extend(
            [
                f"### {item['run_id']} {item['variant']}",
                "",
                "```bash",
                command_separator.join(item["command"]),
                "```",
                "",
            ]
        )
    for name in (
        "selector_equivalence",
        "dataset_required_outcome_audit",
        "matched_progress_contract_audit",
        "matched_lane_hard_contract_audit",
    ):
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(report["commands"][name]),
                "```",
                "",
            ]
        )
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
