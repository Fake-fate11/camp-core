#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_payload_smoke import (
    DATASET_AUDIT,
    FORMAL_SEEDS,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    SmokeSpec,
    _check_order,
    _check_tokens,
)


ROOT = Path(__file__).resolve().parents[2]
MATCHED_CONTRACT_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_non_turn_logit_interaction_matched_outcomes.py"
)

READY_STATUS = "non_turn_logit_interaction_matched_outcome_contract_plan_ready"
REJECT_STATUS = "non_turn_logit_interaction_matched_outcome_contract_plan_rejected"
SOURCE_STATUS = "non_turn_logit_interaction_payload_smoke_passed"
AUTHORIZED_NEXT_WORK = (
    "non_turn_logit_interaction_matched_outcome_contract_three_step_smoke_only"
)
MIN_SOURCE_RECORDS = 3
MAX_PAYLOAD_LATENCY_MS = 1.0
MAX_ROUTE_PROGRESS_LATENCY_MS = 25.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a nonformal matched non-turn-logit "
            "interaction payload plus candidate-outcome-label replay pass. "
            "It emits commands and accept/reject gates, but does not run "
            "Diffusion Planner."
        )
    )
    parser.add_argument("--payload_smoke_audit_json", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--dataset_audit_json", type=Path, required=True)
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
    parser.add_argument(
        "--matched_contract_audit_source",
        type=Path,
        default=MATCHED_CONTRACT_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = replace(
        SmokeSpec(),
        root=(
            "/root/autodl-tmp/"
            "camp_dp_non_turn_logit_interaction_matched_outcome_contract_v1"
        ),
    )
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        payload_smoke_audit=_read_json(args.payload_smoke_audit_json),
        selector_equivalence=_read_json(args.selector_equivalence_json),
        dataset_audit=_read_json(args.dataset_audit_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
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
    payload_smoke_audit: dict[str, Any],
    selector_equivalence: dict[str, Any],
    dataset_audit: dict[str, Any],
    label: str | None = None,
    spec: SmokeSpec | None = None,
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    matched_contract_audit_source: Path = MATCHED_CONTRACT_AUDIT,
) -> dict[str, Any]:
    if spec is None:
        spec = replace(
            SmokeSpec(),
            root=(
                "/root/autodl-tmp/"
                "camp_dp_non_turn_logit_interaction_matched_outcome_contract_v1"
            ),
        )
    source_checks = [
        *_source_artifact_checks(
            smoke=payload_smoke_audit,
            selector=selector_equivalence,
            dataset=dataset_audit,
        ),
        *_source_text_checks(
            replay_source=replay_source,
            payload_audit_source=payload_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
            matched_contract_audit_source=matched_contract_audit_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_non_turn_logit_interaction_matched_outcome_contract_plan_v1"
            ),
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "formal_seed_records": 0,
            "future_outcome_leakage": False,
            "math_boundary": (
                "The planned matched branch records current-tick "
                "non-turn-logit interaction payloads and posterior candidate "
                "closed-loop outcomes in the same replay record. Outcomes are "
                "offline labels only and are forbidden as runtime selector "
                "features. The interaction is a fixed nonnegative candidate "
                "coefficient, so CAMP score_k(w)=a_k^T w remains affine and "
                "the simplex/CVaR/L2 robust master remains convex. No DP-side "
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
                "next gate only: one paired nonformal run x 3 steps; matched "
                "branch collects non_turn_logit_interaction_payload_logging "
                "and candidate_closed_loop_outcomes"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "schema_promotion_authorized": False,
            "outcome_separability_authorized": False,
        },
    }


def _source_artifact_checks(
    *,
    smoke: dict[str, Any],
    selector: dict[str, Any],
    dataset: dict[str, Any],
) -> list[dict[str, Any]]:
    final = smoke.get("final_decision", {})
    counts = smoke.get("counts", {})
    latency = smoke.get("latency_ms", {})
    payload_latency = _float(
        latency.get("latency_ms_non_turn_logit_interaction_payload")
    )
    route_progress_latency = _float(latency.get("latency_ms_reward_route_progress"))
    return [
        {
            "name": "payload_smoke_passed",
            "passed": final.get("status") == SOURCE_STATUS
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "payload_smoke_records_available",
            "passed": int(counts.get("records", 0)) >= MIN_SOURCE_RECORDS
            and int(counts.get("candidate_payload_records", 0)) >= MIN_SOURCE_RECORDS
            and int(counts.get("available_payload_records", 0)) >= MIN_SOURCE_RECORDS
            and int(counts.get("invalid_payload_records", -1)) == 0,
            "counts": counts,
            "min_records": MIN_SOURCE_RECORDS,
        },
        {
            "name": "payload_latency_within_smoke_budget",
            "passed": payload_latency <= MAX_PAYLOAD_LATENCY_MS,
            "value_ms": payload_latency,
            "threshold_ms": MAX_PAYLOAD_LATENCY_MS,
        },
        {
            "name": "route_progress_latency_within_smoke_budget",
            "passed": route_progress_latency <= MAX_ROUTE_PROGRESS_LATENCY_MS,
            "value_ms": route_progress_latency,
            "threshold_ms": MAX_ROUTE_PROGRESS_LATENCY_MS,
        },
        {
            "name": "selector_exact_equivalence",
            "passed": selector.get("equivalent") is True
            and _sum_nested_numbers(selector.get("exact_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_shape_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_nonexact_entries")) == 0.0,
            "equivalent": selector.get("equivalent"),
        },
        {
            "name": "dataset_audit_passed_without_outcomes",
            "passed": dataset.get("passed") is True
            and dataset.get("checks", {}).get("forbidden_seed_check") is not False
            and dataset.get("checks", {}).get("closed_loop_outcomes_forbidden")
            is not False
            and dataset.get("checks", {}).get("finite_candidate_contract_verified")
            is True,
            "passed_value": dataset.get("passed"),
            "checks": dataset.get("checks"),
        },
    ]


def _source_text_checks(
    *,
    replay_source: Path,
    payload_audit_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
    matched_contract_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    payload_text = _read_text(payload_audit_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    contract_text = _read_text(matched_contract_audit_source)
    return [
        _check_tokens(
            "replay_supports_payload_logging_and_outcome_labels",
            replay_text,
            (
                "--camp_non_turn_logit_interaction_payload_logging",
                "--camp_collect_closed_loop_outcomes",
                "build_non_turn_logit_interaction_payload(",
                "compute_candidate_closed_loop_outcomes(",
            ),
        ),
        _check_order(
            "replay_computes_payload_before_outcomes",
            replay_text,
            "build_non_turn_logit_interaction_payload(",
            "if collect_closed_loop_outcomes:",
        ),
        _check_tokens(
            "payload_smoke_audit_available",
            payload_text,
            (
                "dp_camp_non_turn_logit_interaction_payload_smoke_audit_v1",
                "non_turn_logit_interaction_payload_logging",
                "comfort_progress_interaction_cost",
                "future_outcome_labels_used",
            ),
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
            contract_text,
            (
                "dp_camp_non_turn_logit_interaction_matched_outcome_contract_v1",
                "non_turn_logit_interaction_payload_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
    ]


def _plan_checks(spec: SmokeSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "formal_seed_excluded",
            "passed": spec.seed not in FORMAL_SEEDS,
            "details": {"seed": spec.seed, "formal_seeds": sorted(FORMAL_SEEDS)},
        },
        {
            "name": "same_tiny_nonformal_scope_as_source_smoke",
            "passed": int(spec.steps) == 3 and int(spec.num_candidates) == 8,
            "details": {
                "steps": int(spec.steps),
                "num_candidates": int(spec.num_candidates),
            },
        },
        {
            "name": "traffic_light_and_npc_scope_fixed",
            "passed": spec.traffic_lights == "off"
            and int(spec.max_npcs) == 4
            and float(spec.spawn_probability) == 0.3,
            "details": {
                "traffic_lights": spec.traffic_lights,
                "max_npcs": int(spec.max_npcs),
                "spawn_probability": float(spec.spawn_probability),
            },
        },
        {
            "name": "reward_horizon_fixed",
            "passed": int(spec.reward_horizon_steps) == 30,
            "details": {"reward_horizon_steps": int(spec.reward_horizon_steps)},
        },
    ]


def _coverage_targets(spec: SmokeSpec) -> dict[str, Any]:
    return {
        "paired_runs": 1,
        "baseline_logs": 1,
        "matched_logs": 1,
        "matched_records": int(spec.steps),
        "matched_candidate_rows": int(spec.steps) * int(spec.num_candidates),
        "scope": "contract validation only, not separability or training",
    }


def _commands(spec: SmokeSpec) -> dict[str, Any]:
    baseline_dir = f"{spec.root}/baseline"
    matched_dir = f"{spec.root}/matched_interaction_outcomes"
    audit_dir = f"{spec.root}/audit"
    return {
        "baseline_replay": _replay_command(spec, baseline_dir, matched=False),
        "matched_replay": _replay_command(spec, matched_dir, matched=True),
        "selector_equivalence": _selector_equivalence_command(
            baseline_dir,
            matched_dir,
            audit_dir,
        ),
        "dataset_required_outcome_audit": _dataset_audit_command(
            matched_dir,
            audit_dir,
            spec,
        ),
        "matched_contract_audit": _matched_contract_command(
            matched_dir,
            audit_dir,
            spec,
        ),
    }


def _replay_command(spec: SmokeSpec, output_dir: str, *, matched: bool) -> list[str]:
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
        spec.route,
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
        str(spec.seed),
        "--max_npcs",
        str(spec.max_npcs),
        "--spawn_probability",
        str(spec.spawn_probability),
        "--traffic_lights",
        spec.traffic_lights,
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
        str(spec.reward_horizon_steps),
        "--camp_outcome_horizon_steps",
        str(spec.reward_horizon_steps),
        "--near_miss_threshold_m",
        "2.0",
    ]
    if matched:
        command.extend(
            [
                "--camp_non_turn_logit_interaction_payload_logging",
                "--camp_collect_closed_loop_outcomes",
            ]
        )
    return command


def _selector_equivalence_command(
    baseline_dir: str,
    matched_dir: str,
    audit_dir: str,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/compare_diffusion_planner_selector_logs.py",
        "--baseline_root",
        baseline_dir,
        "--candidate_root",
        matched_dir,
        "--output_json",
        f"{audit_dir}/selector_equivalence.json",
        "--require_equivalent",
    ]


def _dataset_audit_command(
    matched_dir: str,
    audit_dir: str,
    spec: SmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--selection_log",
        f"{matched_dir}/camp_selection_log.json",
        "--atom_scales",
        spec.atom_scales,
        "--expected_logs",
        "1",
        "--expected_candidates",
        str(spec.num_candidates),
        "--expected_advance_mode",
        "perfect",
        "--closed_loop_outcome_policy",
        "required",
        "--forbid_seed",
        "11",
        "--forbid_seed",
        "12",
        "--forbid_seed",
        "13",
        "--require_finite_candidate_contract",
        "--output_json",
        f"{audit_dir}/dataset_required_outcome_audit.json",
    ]


def _matched_contract_command(
    matched_dir: str,
    audit_dir: str,
    spec: SmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_non_turn_logit_interaction_matched_outcomes.py",
        "--selection_log",
        f"{matched_dir}/camp_selection_log.json",
        "--expected_logs",
        "1",
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--label",
        "non_turn_logit_interaction_matched_outcome_contract_v1",
        "--output_json",
        f"{audit_dir}/matched_interaction_outcome_contract.json",
        "--output_md",
        f"{audit_dir}/matched_interaction_outcome_contract.md",
        "--require_pass",
    ]


def _accept_criteria(spec: SmokeSpec) -> list[str]:
    return [
        "all source and plan checks pass before replay",
        "baseline and matched replay commands exit 0",
        "matched records contain non_turn_logit_interaction_payload_logging and candidate_closed_loop_outcomes in the same record",
        "interaction payload reports selection_effect=false and future_outcome_leakage=false",
        "interaction payload does not embed candidate_closed_loop_outcomes",
        "selector equivalence passes between baseline and matched branches",
        "dataset audit passes with closed_loop_outcome_policy=required",
        "matched contract audit passes for all records and candidates",
        f"exactly 1 matched log and {int(spec.steps)} matched records are present",
        "no formal seed 11/12/13 appears in any path, summary, or record",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any source or plan check fails",
        "any replay or audit command fails",
        "any matched record lacks interaction payload or candidate_closed_loop_outcomes",
        "any selected index, feasibility mask, atom, score, or weight changes under logging/outcome collection",
        "any runtime interaction payload uses closed-loop outcome labels or reports future_outcome_leakage=true",
        "any formal seed appears",
        "the run expands beyond the predeclared 1-run x 3-step nonformal scope",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


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
        "# Non-Turn-Logit Interaction Matched Outcome Contract Plan",
        "",
        "This is a design-only plan. It does not run Diffusion Planner, does "
        "not train CAMP, and does not authorize online selector promotion.",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke execution authorized now: `{decision['paired_smoke_execution_authorized']}`",
        f"- scope: `{decision['paired_smoke_execution_scope']}`",
        "",
        "## Coverage Targets",
        "",
        "```json",
        json.dumps(report["coverage_targets"], indent=2, sort_keys=True),
        "```",
        "",
        "## Source Checks",
        "",
    ]
    lines.extend(f"- {item['name']}: {item['passed']}" for item in report["source_checks"])
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(f"- {item['name']}: {item['passed']}" for item in report["plan_checks"])
    lines.extend(["", "## Commands", ""])
    separator = " \\\n  "
    for name, command in report["commands"].items():
        lines.extend([f"### {name}", "", "```bash", separator.join(command), "```", ""])
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
