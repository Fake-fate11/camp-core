#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
PAYLOAD_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_non_turn_logit_interaction_payload_smoke.py"
)
SELECTOR_EQUIVALENCE = (
    ROOT / "scripts/integrations/compare_diffusion_planner_selector_logs.py"
)
DATASET_AUDIT = ROOT / "scripts/integrations/audit_diffusion_planner_camp_dataset.py"

READY_STATUS = "non_turn_logit_interaction_payload_nonformal_smoke_plan_ready"
REJECT_STATUS = "non_turn_logit_interaction_payload_nonformal_smoke_plan_rejected"
SOURCE_STATUS = "non_turn_logit_interaction_payload_unit_wired"
AUTHORIZED_NEXT_WORK = (
    "non_turn_logit_interaction_payload_paired_three_step_smoke_only"
)
FORMAL_SEEDS = frozenset({11, 12, 13})
SUMMARY_KEY = "camp_non_turn_logit_interaction_payload_logging"


@dataclass(frozen=True)
class SmokeSpec:
    root: str = "/root/autodl-tmp/camp_dp_non_turn_logit_interaction_payload_smoke"
    diffusion_repo: str = "/root/autodl-tmp/Diffusion-Planner"
    map_path: str = (
        "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
        "sample-map-planning/lanelet2_map_no_ros.osm"
    )
    route: str = "/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl"
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
    seed: int = 1
    steps: int = 3
    max_npcs: int = 4
    spawn_probability: float = 0.3
    traffic_lights: str = "off"
    num_candidates: int = 8
    candidate_noise_scale: float = 1.0
    candidate_reference_blend_steps: int = 5
    reward_horizon_steps: int = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for the first default-off non-turn-logit "
            "interaction payload smoke. It emits paired nonformal replay "
            "commands and does not run Diffusion Planner."
        )
    )
    parser.add_argument("--label", default=None)
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
    report = build_report(
        label=args.label,
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
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    label: str | None = None,
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    smoke: SmokeSpec = SmokeSpec(),
) -> dict[str, Any]:
    source_checks = _source_checks(
        replay_source=replay_source,
        payload_audit_source=payload_audit_source,
        selector_equivalence_source=selector_equivalence_source,
        dataset_audit_source=dataset_audit_source,
    )
    plan_checks = _plan_checks(smoke)
    passed = all(item["passed"] for item in source_checks + plan_checks)
    baseline_dir = f"{smoke.root}/baseline"
    candidate_dir = f"{smoke.root}/logging_enabled"
    audit_dir = f"{smoke.root}/audit"
    commands = {
        "baseline_replay": _runner_command(smoke, baseline_dir, logging=False),
        "candidate_replay": _runner_command(smoke, candidate_dir, logging=True),
        "selector_equivalence": _selector_equivalence_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
        ),
        "payload_audit": _payload_audit_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
            smoke,
        ),
        "dataset_audit": _dataset_audit_command(candidate_dir, audit_dir, smoke),
    }
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "new_replay_authorized": passed,
        "closed_loop_smoke_authorized": passed,
        "closed_loop_replay_authorized": passed,
        "closed_loop_replay_scope": (
            "paired nonformal sample_map_tl_route_59_to_86 seed1 npc4 "
            "traffic_lights_off static, 3 steps only"
            if passed
            else None
        ),
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "CAMP_retraining_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "matched_outcome_audit_authorized": False,
    }
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_payload_nonformal_smoke_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "The smoke only enables default-off logging of current-tick "
                "route-progress/DP-prior-jerk interaction coefficients. It "
                "must not change CAMP scores, feasibility, selected indices, "
                "DP candidates, atom schema, weights, or PerfectTracker "
                "execution. If the interaction is later atomized after "
                "separate evidence, it is a fixed coefficient a_k preserving "
                "affine score_k(w)=a_k^T w and the simplex/CVaR/L2 convex "
                "master. This is not a DP-side classical Benders decomposition."
            ),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "smoke_spec": asdict(smoke),
        "accept_criteria": _accept_criteria(smoke),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "final_decision": decision,
    }


def _source_checks(
    *,
    replay_source: Path,
    payload_audit_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    payload_text = _read_text(payload_audit_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    return [
        _check_tokens(
            "replay_default_off_non_turn_logit_interaction_payload_cli",
            replay_text,
            (
                "--camp_non_turn_logit_interaction_payload_logging",
                "build_non_turn_logit_interaction_payload(",
                "non_turn_logit_interaction_payload_logging_payload = None",
                "\"non_turn_logit_interaction_payload_logging\": (",
                "\"camp_non_turn_logit_interaction_payload_logging\": (",
                "deployed_atom_vector_change",
                "selection_effect",
                "future_outcome_leakage",
                "closed_loop_outcome_fields_read",
            ),
        ),
        _check_order(
            "replay_payload_before_outcomes",
            replay_text,
            "build_non_turn_logit_interaction_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "payload_audit_available",
            payload_text,
            (
                "dp_camp_non_turn_logit_interaction_payload_smoke_audit_v1",
                "non_turn_logit_interaction_payload_logging",
                "comfort_progress_interaction_cost",
                "formal_seed_detected",
                "finite_checks.payload_valid",
                "latency_ms_reward_route_progress",
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


def _plan_checks(smoke: SmokeSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "nonformal_seed",
            "passed": smoke.seed not in FORMAL_SEEDS,
            "value": smoke.seed,
        },
        {
            "name": "tiny_three_step_scope",
            "passed": smoke.steps == 3,
            "value": smoke.steps,
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": smoke.num_candidates == 8,
            "value": smoke.num_candidates,
        },
        {
            "name": "reward_route_progress_horizon_fixed",
            "passed": smoke.reward_horizon_steps == 30,
            "value": smoke.reward_horizon_steps,
        },
        {
            "name": "candidate_diversity_controls_fixed",
            "passed": smoke.candidate_noise_scale > 0.0
            and smoke.candidate_reference_blend_steps >= 0,
            "value": {
                "candidate_noise_scale": smoke.candidate_noise_scale,
                "candidate_reference_blend_steps": (
                    smoke.candidate_reference_blend_steps
                ),
            },
        },
    ]


def _runner_command(smoke: SmokeSpec, output_dir: str, *, logging: bool) -> list[str]:
    command = [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "REPLAY_NO_PNG=1",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "--diffusion_repo",
        smoke.diffusion_repo,
        "--map_path",
        smoke.map_path,
        "--route",
        smoke.route,
        "--model_path",
        smoke.model_path,
        "--model_args",
        smoke.model_args,
        "--config",
        smoke.config,
        "--output_dir",
        output_dir,
        "--device",
        "cuda",
        "--advance_mode",
        "perfect",
        "--steps",
        str(smoke.steps),
        "--seed",
        str(smoke.seed),
        "--max_npcs",
        str(smoke.max_npcs),
        "--spawn_probability",
        str(smoke.spawn_probability),
        "--traffic_lights",
        smoke.traffic_lights,
        "--reward_config",
        smoke.reward_config,
        "--camp_selector_mode",
        "static",
        "--camp_atom_scales",
        smoke.atom_scales,
        "--camp_static_weights",
        smoke.static_weights,
        "--num_candidates",
        str(smoke.num_candidates),
        "--candidate_noise_scale",
        str(smoke.candidate_noise_scale),
        "--candidate_reference_blend_steps",
        str(smoke.candidate_reference_blend_steps),
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
        str(smoke.reward_horizon_steps),
        "--camp_outcome_horizon_steps",
        str(smoke.reward_horizon_steps),
        "--near_miss_threshold_m",
        "2.0",
    ]
    if logging:
        command.append("--camp_non_turn_logit_interaction_payload_logging")
    return command


def _selector_equivalence_command(
    baseline_dir: str,
    candidate_dir: str,
    audit_dir: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/compare_diffusion_planner_selector_logs.py",
        "--baseline_root",
        baseline_dir,
        "--candidate_root",
        candidate_dir,
        "--output_json",
        f"{audit_dir}/selector_equivalence.json",
        "--require_equivalent",
    ]


def _payload_audit_command(
    baseline_dir: str,
    candidate_dir: str,
    audit_dir: str,
    smoke: SmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_non_turn_logit_interaction_payload_smoke.py",
        "--baseline_root",
        baseline_dir,
        "--candidate_root",
        candidate_dir,
        "--expected_logs",
        "1",
        "--expected_records",
        str(smoke.steps),
        "--expected_candidates",
        str(smoke.num_candidates),
        "--output_json",
        f"{audit_dir}/non_turn_logit_interaction_payload_smoke.json",
        "--output_md",
        f"{audit_dir}/non_turn_logit_interaction_payload_smoke.md",
        "--require_pass",
    ]


def _dataset_audit_command(
    candidate_dir: str,
    audit_dir: str,
    smoke: SmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--selection_log",
        f"{candidate_dir}/camp_selection_log.json",
        "--atom_scales",
        smoke.atom_scales,
        "--expected_logs",
        "1",
        "--expected_candidates",
        str(smoke.num_candidates),
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
        f"{audit_dir}/dataset_audit.json",
    ]


def _accept_criteria(smoke: SmokeSpec) -> list[str]:
    return [
        "both paired replay commands exit 0",
        "no formal seed 11/12/13 appears in any output path or summary",
        f"baseline summary reports {SUMMARY_KEY}.enabled=false",
        f"candidate summary reports {SUMMARY_KEY}.enabled=true",
        "candidate records contain non-null non_turn_logit_interaction_payload_logging payloads",
        "payload fields are available, finite, nonnegative, and match interaction=progress_deficit*jerk",
        "candidate0 route_progress_deficit_vs_top1_m is zero",
        "payload latency and latency_ms_reward_route_progress are finite and nonnegative",
        "selector log equivalence passes with selected_index, feasibility, atoms, scores, and weights unchanged",
        "dataset audit passes finite-candidate contract checks with closed-loop outcomes forbidden",
        f"scope remains one paired nonformal run with seed={smoke.seed}, steps={smoke.steps}, candidates={smoke.num_candidates}",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any replay, selector-equivalence, payload, or dataset audit fails",
        "any formal seed is detected",
        "any selected_index or CAMP score/atom field changes between baseline and logging-enabled runs",
        "any payload uses future outcome labels or reports selection_effect=true",
        "any interaction payload field is missing, unavailable, nonfinite, negative, or shape-mismatched",
        "any route-progress latency field is missing or nonfinite",
        "the smoke is expanded beyond the paired 3-step nonformal scope",
    ]


def _check_tokens(name: str, text: str | None, tokens: tuple[str, ...]) -> dict[str, Any]:
    missing = [token for token in tokens if text is None or token not in text]
    return {"name": name, "passed": not missing, "missing_tokens": missing}


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
        "# Non-Turn-Logit Interaction Payload Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- scope: `{decision['closed_loop_replay_scope']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Missing |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        missing = ", ".join(check.get("missing_tokens", []))
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{missing}` |")
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(
        f"- `{check['name']}`: `{check['passed']}`"
        for check in report["plan_checks"]
    )
    lines.extend(["", "## Commands", ""])
    command_separator = " \\\n" "  "
    for name, command in report["commands"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(command),
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


if __name__ == "__main__":
    main()
