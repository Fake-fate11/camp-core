#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py"
PAYLOAD_AUDIT = (
    ROOT
    / "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_payload_smoke.py"
)
SELECTOR_EQUIVALENCE = (
    ROOT / "scripts/integrations/compare_diffusion_planner_selector_logs.py"
)
DATASET_AUDIT = ROOT / "scripts/integrations/audit_diffusion_planner_camp_dataset.py"

READY_STATUS = "candidate_set_consensus_payload_nonformal_smoke_plan_ready"
REJECT_STATUS = "candidate_set_consensus_payload_nonformal_smoke_plan_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_payload_paired_three_step_smoke_only"
IMPLEMENTATION_READY_STATUS = "candidate_set_consensus_payload_implementation_unit_tests_ready"
IMPLEMENTATION_NEXT_WORK = "candidate_set_consensus_default_off_tiny_smoke_plan_only"
SUMMARY_KEY = "camp_candidate_set_consensus_payload_logging"
EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = frozenset({11, 12, 13})

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class SmokeSpec:
    camp_repo: str = "/root/autodl-tmp/camp_core"
    root: str = "/root/autodl-tmp/camp_dp_candidate_set_consensus_payload_smoke"
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
    payload_steps: int = 10
    min_available_records: int = 3
    expected_dp_head: str = EXPECTED_DP_HEAD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for a default-off candidate-set consensus "
            "payload smoke. It emits paired nonformal replay commands and does "
            "not run Diffusion Planner."
        )
    )
    parser.add_argument("--implementation_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
    report = build_report(
        implementation=_load_json(args.implementation_json),
        label=args.label,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        paths={"implementation_json": str(args.implementation_json)},
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
    implementation: dict[str, Any],
    label: str | None = None,
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    smoke: SmokeSpec = SmokeSpec(),
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    implementation_summary = _implementation_summary(implementation)
    source_checks = _source_checks(
        replay_source=replay_source,
        payload_audit_source=payload_audit_source,
        selector_equivalence_source=selector_equivalence_source,
        dataset_audit_source=dataset_audit_source,
    )
    plan_checks = [
        *_implementation_checks(implementation_summary),
        *_plan_checks(smoke),
    ]
    passed = all(check["passed"] for check in source_checks + plan_checks)
    baseline_dir = f"{smoke.root}/baseline"
    candidate_dir = f"{smoke.root}/logging_enabled"
    audit_dir = f"{smoke.root}/audit"
    commands = {
        "camp_sync": _camp_sync_command(smoke),
        "head_audit": _head_audit_command(smoke),
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
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_payload_nonformal_smoke_plan_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "sync_boundary": (
                "Before running replay on AutoDL, sync CAMP with git pull "
                "--ff-only and confirm the fixed DP checkout exactly matches "
                f"{EXPECTED_DP_HEAD}."
            ),
            "math_boundary": (
                "The smoke only enables default-off logging of current-tick "
                "candidate-set consensus descriptors derived from the fixed DP "
                "candidate tensor before selection. It must not change CAMP "
                "scores, feasibility, selected indices, DP candidates, or "
                "PerfectTracker execution. If later atomized, "
                "candidate_set_consensus_center_rms_cost_v1 is a fixed finite "
                "nonnegative coefficient preserving score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master. This is not a DP-side classical "
                "Benders decomposition."
            ),
        },
        "implementation_summary": implementation_summary,
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "smoke_spec": asdict(smoke),
        "accept_criteria": _accept_criteria(smoke),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "final_decision": decision,
    }


def _implementation_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    payload = _dict(report.get("payload"))
    finite_checks = _dict(payload.get("finite_checks"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "has_final_decision": bool(decision),
        "payload_available": bool(payload.get("available")),
        "payload_valid": bool(finite_checks.get("payload_valid")),
        "payload_default_off": payload.get("default_off"),
        "payload_selection_effect": payload.get("selection_effect"),
        "payload_future_outcome_leakage": payload.get("future_outcome_leakage"),
        "payload_classical_benders_claim": payload.get("classical_benders_claim"),
        "payload_candidate_count": payload.get("candidate_count"),
        "payload_blocked_action_conflicts": conflicts,
    }


def _implementation_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        _check_equal("implementation_payload_available", summary["payload_available"], True),
        _check_equal("implementation_payload_valid", summary["payload_valid"], True),
        _check_equal("implementation_payload_default_off", summary["payload_default_off"], True),
        _check_equal(
            "implementation_payload_selection_neutral",
            summary["payload_selection_effect"],
            False,
        ),
        _check_equal(
            "implementation_payload_no_future_leakage",
            summary["payload_future_outcome_leakage"],
            False,
        ),
        _check_equal(
            "implementation_no_classic_benders_claim",
            summary["payload_classical_benders_claim"],
            False,
        ),
        _check_empty(
            "implementation_no_blocked_action_conflicts",
            summary["payload_blocked_action_conflicts"],
        ),
    ]
    if summary["has_final_decision"]:
        checks.extend(
            [
                _check_equal(
                    "implementation_status",
                    summary["status"],
                    IMPLEMENTATION_READY_STATUS,
                ),
                _check_equal(
                    "implementation_authorizes_smoke_plan",
                    summary["authorized_next_work"],
                    IMPLEMENTATION_NEXT_WORK,
                ),
            ]
        )
    return checks


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
            "replay_default_off_candidate_set_consensus_payload_cli",
            replay_text,
            (
                "--camp_candidate_set_consensus_payload_logging",
                "--camp_candidate_set_consensus_payload_steps",
                "build_candidate_set_consensus_payload(",
                "candidate_set_consensus_payload_logging_payload = None",
                '"candidate_set_consensus_payload_logging": (',
                '"camp_candidate_set_consensus_payload_logging": (',
                "selection_effect",
                "future_outcome_leakage",
                "closed_loop_outcome_fields_read",
                "CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS",
            ),
        ),
        _check_order(
            "replay_payload_before_selection",
            replay_text,
            "build_candidate_set_consensus_payload(",
            "selected_trajectory = candidates[selected_index]",
        ),
        _check_tokens(
            "payload_audit_available",
            payload_text,
            (
                "dp_camp_candidate_set_consensus_payload_smoke_audit_v1",
                "candidate_set_consensus_payload_logging",
                "candidate_set_consensus_center_rms_m",
                "formal_seed_detected",
                "CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS",
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
        _check_equal("scope_seed_is_nonformal", smoke.seed not in FORMAL_SEEDS, True),
        _check_equal("scope_is_tiny_three_steps", smoke.steps, 3),
        _check_equal("fixed_candidate_count", smoke.num_candidates, 8),
        _check_equal("payload_horizon_valid", smoke.payload_steps >= 2, True),
        _check_equal("requires_all_three_payload_records", smoke.min_available_records, 3),
        _check_equal("fixed_dp_head_declared", smoke.expected_dp_head, EXPECTED_DP_HEAD),
    ]


def _camp_sync_command(smoke: SmokeSpec) -> list[str]:
    return ["git", "-C", smoke.camp_repo, "pull", "--ff-only", "origin", "main"]


def _head_audit_command(smoke: SmokeSpec) -> list[str]:
    return [
        "/bin/bash",
        "-lc",
        (
            f'test "$(git -C {smoke.camp_repo} rev-parse HEAD)" = '
            f'"$(git -C {smoke.camp_repo} rev-parse origin/main)" && '
            f'test "$(git -C {smoke.diffusion_repo} rev-parse HEAD)" = '
            f'"{smoke.expected_dp_head}" && '
            f'echo "CAMP_HEAD=$(git -C {smoke.camp_repo} rev-parse HEAD)" && '
            f'echo "DP_HEAD=$(git -C {smoke.diffusion_repo} rev-parse HEAD)"'
        ),
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
        "30",
        "--camp_outcome_horizon_steps",
        "30",
        "--near_miss_threshold_m",
        "2.0",
    ]
    if logging:
        command.extend(
            [
                "--camp_candidate_set_consensus_payload_logging",
                "--camp_candidate_set_consensus_payload_steps",
                str(smoke.payload_steps),
            ]
        )
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
        "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_payload_smoke.py",
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
        "--min_available_records",
        str(smoke.min_available_records),
        "--output_json",
        f"{audit_dir}/candidate_set_consensus_payload_smoke.json",
        "--output_md",
        f"{audit_dir}/candidate_set_consensus_payload_smoke.md",
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
        "CAMP sync and head audit commands exit 0 before replay",
        "both paired replay commands exit 0",
        "no formal seed 11/12/13 appears in any output path or summary",
        f"baseline summary reports {SUMMARY_KEY}.enabled=false",
        f"candidate summary reports {SUMMARY_KEY}.enabled=true",
        "candidate records contain non-null candidate_set_consensus_payload_logging payloads",
        "payload schema, field shapes, finite checks, latency fields, and no-leak metadata pass audit",
        f"at least {smoke.min_available_records} payload records are available",
        "all available consensus RMS coefficients are finite and nonnegative",
        "candidate_closed_loop_outcomes remain absent",
        "selector log equivalence passes with selected_index, feasibility, atoms, scores, and weights unchanged",
        "dataset audit passes finite-candidate contract checks with closed-loop outcomes forbidden",
        f"scope remains one paired nonformal run with seed={smoke.seed}, steps={smoke.steps}, candidates={smoke.num_candidates}",
    ]


def _reject_criteria() -> list[str]:
    return [
        "CAMP sync fails or DP HEAD differs from the fixed commit",
        "any replay, selector-equivalence, payload, or dataset audit fails",
        "any formal seed is detected",
        "any selected_index or CAMP score/atom field changes between baseline and logging-enabled runs",
        "any payload uses future outcome labels or reports selection_effect=true",
        "any available consensus RMS coefficient is negative, nonfinite, or wrong-shaped",
        "fewer than three available payload records are produced in the 3-step smoke",
        "the smoke is expanded beyond the paired 3-step nonformal scope",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Payload Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- scope: `{decision['closed_loop_replay_scope']}`",
        "",
        "## Sync Boundary",
        "",
        report["analysis"]["sync_boundary"],
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


def render_bash(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    if decision.get("authorized_next_work") != AUTHORIZED_NEXT_WORK:
        raise ValueError("Cannot render bash for a rejected smoke plan.")
    commands = report["commands"]
    command_order = (
        "camp_sync",
        "head_audit",
        "baseline_replay",
        "candidate_replay",
        "selector_equivalence",
        "payload_audit",
        "dataset_audit",
    )
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Auto-generated from dp_camp_candidate_set_consensus_payload_nonformal_smoke_plan_v1.",
        "# Scope: paired nonformal seed1, 3 steps, 8 candidates only.",
        "# Forbidden: formal seeds, Full36, online selector promotion, CAMP retraining, DP modification.",
        f"# Expected DP HEAD: {EXPECTED_DP_HEAD}",
        "",
        "cd /root/autodl-tmp/camp_core",
        "",
    ]
    for name in command_order:
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    lines.append('echo "candidate_set_consensus_payload_paired_three_step_smoke_complete"')
    lines.append("")
    return "\n".join(lines)


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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": [],
        "passed": len(value) == 0,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
