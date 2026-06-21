#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_broader_nonformal_smoke import (
    BroaderSmokeSpec,
    EvidenceRunSpec,
    FORMAL_SEEDS,
    MAX_BROADER_LOGGING_MS,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_logging_smoke import (
    DATASET_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    _check_order,
    _check_tokens,
)


ROOT = Path(__file__).resolve().parents[2]
MATCHED_CONTEXT_CONTRACT_AUDIT = (
    ROOT
    / "scripts/integrations/"
    "analyze_diffusion_planner_matched_progress_lane_hard_context_outcomes.py"
)

READY_STATUS = "progress_lane_hard_context_matched_outcome_label_pass_plan_ready"
REJECT_STATUS = "progress_lane_hard_context_matched_outcome_label_pass_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "progress_lane_hard_context_matched_outcome_label_nonformal_smoke_only"
)
BROADER_SMOKE_STATUS = "progress_lane_hard_context_logging_smoke_passed"
BROADER_COVERAGE_STATUS = (
    "progress_lane_hard_context_payload_coverage_ready_for_offline_separability_design"
)
MIN_SOURCE_RECORDS = 48
MIN_SOURCE_CANDIDATE_ROWS = 384


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a nonformal matched progress+lane/hard "
            "context plus candidate-outcome-label replay pass. It emits "
            "commands and accept/reject gates, but does not run Diffusion "
            "Planner."
        )
    )
    parser.add_argument("--broader_smoke_audit_json", type=Path, required=True)
    parser.add_argument("--broader_selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--broader_dataset_audit_json", type=Path, required=True)
    parser.add_argument("--broader_coverage_audit_json", type=Path, required=True)
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
        "--matched_context_contract_audit_source",
        type=Path,
        default=MATCHED_CONTEXT_CONTRACT_AUDIT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = replace(
        BroaderSmokeSpec(),
        root=(
            "/root/autodl-tmp/"
            "camp_dp_progress_lane_hard_context_matched_outcome_labels_nonformal_v1"
        ),
    )
    if args.output_root is not None:
        spec = replace(spec, root=args.output_root)
    report = build_report(
        broader_smoke_audit=_read_json(args.broader_smoke_audit_json),
        broader_selector_equivalence=_read_json(args.broader_selector_equivalence_json),
        broader_dataset_audit=_read_json(args.broader_dataset_audit_json),
        broader_coverage_audit=_read_json(args.broader_coverage_audit_json),
        label=args.label,
        spec=spec,
        replay_source=args.replay_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
        matched_context_contract_audit_source=(
            args.matched_context_contract_audit_source
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
    broader_smoke_audit: dict[str, Any],
    broader_selector_equivalence: dict[str, Any],
    broader_dataset_audit: dict[str, Any],
    broader_coverage_audit: dict[str, Any],
    label: str | None = None,
    spec: BroaderSmokeSpec | None = None,
    replay_source: Path = RUNNER,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    matched_context_contract_audit_source: Path = MATCHED_CONTEXT_CONTRACT_AUDIT,
) -> dict[str, Any]:
    if spec is None:
        spec = replace(
            BroaderSmokeSpec(),
            root=(
                "/root/autodl-tmp/"
                "camp_dp_progress_lane_hard_context_matched_outcome_labels_nonformal_v1"
            ),
        )
    source_checks = [
        *_source_artifact_checks(
            smoke=broader_smoke_audit,
            selector=broader_selector_equivalence,
            dataset=broader_dataset_audit,
            coverage=broader_coverage_audit,
        ),
        *_source_text_checks(
            replay_source=replay_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
            matched_context_contract_audit_source=matched_context_contract_audit_source,
        ),
    ]
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_progress_lane_hard_context_matched_outcome_label_pass_plan_v1"
            ),
            "label": label,
            "source_status": BROADER_COVERAGE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "formal_seed_records": 0,
            "future_outcome_leakage": False,
            "math_boundary": (
                "The planned matched branch records current-tick "
                "progress+lane/hard context atoms and posterior candidate "
                "closed-loop outcomes in the same replay record. Outcomes are "
                "offline labels only and are forbidden as runtime selector "
                "features. Context atoms are fixed nonnegative candidate "
                "coefficients, so CAMP score_k(w)=a_k^T w remains affine and "
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
                "next gate only: 4 paired nonformal runs x 12 steps; matched "
                "branch collects progress_lane_hard_context_logging and "
                "candidate_closed_loop_outcomes"
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
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    smoke_final = smoke.get("final_decision", {})
    smoke_counts = smoke.get("counts", {})
    smoke_latency = smoke.get("latency_ms", {})
    coverage_final = coverage.get("final_decision", {})
    coverage_counts = coverage.get("counts", {})
    context = coverage.get("context") or {}
    logging_ms = _float(
        smoke_latency.get("latency_ms_progress_lane_hard_context_logging")
    )
    return [
        {
            "name": "broader_context_smoke_passed",
            "passed": smoke_final.get("status") == BROADER_SMOKE_STATUS
            and smoke_final.get("passed") is True,
            "status": smoke_final.get("status"),
            "passed_value": smoke_final.get("passed"),
        },
        {
            "name": "broader_context_records_material",
            "passed": int(smoke_counts.get("records", 0)) >= MIN_SOURCE_RECORDS
            and int(smoke_counts.get("candidate_payload_records", 0))
            >= MIN_SOURCE_RECORDS,
            "counts": smoke_counts,
            "min_records": MIN_SOURCE_RECORDS,
        },
        {
            "name": "broader_context_logging_latency_within_budget",
            "passed": logging_ms <= MAX_BROADER_LOGGING_MS,
            "value_ms": logging_ms,
            "threshold_ms": MAX_BROADER_LOGGING_MS,
        },
        {
            "name": "broader_context_coverage_ready",
            "passed": coverage_final.get("status") == BROADER_COVERAGE_STATUS
            and coverage_final.get("validation_passed") is not False
            and coverage_final.get("materiality_gate_passed") is True,
            "final_decision": coverage_final,
        },
        {
            "name": "broader_context_coverage_material",
            "passed": int(coverage_counts.get("records", 0)) >= MIN_SOURCE_RECORDS
            and int(coverage_counts.get("payload_records", 0)) >= MIN_SOURCE_RECORDS
            and int(coverage_counts.get("candidate_rows", 0))
            >= MIN_SOURCE_CANDIDATE_ROWS
            and int(context.get("context_records", 0)) > 0
            and len(coverage.get("material_atom_fields") or []) >= 2
            and coverage.get("validation", {}).get("errors") == []
            and coverage.get("validation", {}).get("warnings") == [],
            "counts": coverage_counts,
            "context": context,
            "material_atom_fields": coverage.get("material_atom_fields"),
            "validation": coverage.get("validation"),
        },
        {
            "name": "broader_selector_exact_equivalence",
            "passed": selector.get("equivalent") is True
            and _sum_nested_numbers(selector.get("exact_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_field_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_shape_mismatches")) == 0.0
            and _sum_nested_numbers(selector.get("numeric_nonexact_entries")) == 0.0,
            "equivalent": selector.get("equivalent"),
        },
        {
            "name": "broader_dataset_audit_passed_without_outcomes",
            "passed": dataset.get("passed") is True
            and dataset.get("checks", {}).get("forbidden_seed_check") is not False
            and dataset.get("checks", {}).get("closed_loop_outcomes_forbidden") is not False,
            "passed_value": dataset.get("passed"),
            "checks": dataset.get("checks"),
        },
    ]


def _source_text_checks(
    *,
    replay_source: Path,
    selector_equivalence_source: Path,
    dataset_audit_source: Path,
    matched_context_contract_audit_source: Path,
) -> list[dict[str, Any]]:
    replay_text = _read_text(replay_source)
    selector_text = _read_text(selector_equivalence_source)
    dataset_text = _read_text(dataset_audit_source)
    contract_text = _read_text(matched_context_contract_audit_source)
    return [
        _check_tokens(
            "replay_supports_context_logging_and_outcome_labels",
            replay_text,
            (
                "--camp_progress_lane_hard_context_logging",
                "--camp_collect_closed_loop_outcomes",
                "build_progress_lane_hard_context_logging_payload(",
                "compute_candidate_closed_loop_outcomes(",
            ),
        ),
        _check_order(
            "replay_computes_context_payload_before_outcomes",
            replay_text,
            "build_progress_lane_hard_context_logging_payload(",
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
            "matched_context_contract_audit_available",
            contract_text,
            (
                "dp_camp_matched_progress_lane_hard_context_outcome_contract_v1",
                "progress_lane_hard_context_logging",
                "candidate_closed_loop_outcomes",
                "future_outcome_leakage",
            ),
        ),
    ]


def _plan_checks(spec: BroaderSmokeSpec) -> list[dict[str, Any]]:
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
            "name": "context_horizon_and_corridor_budget_fixed",
            "passed": int(spec.context_steps) == 10
            and abs(float(spec.context_dt_s) - 0.1) <= 1e-12
            and float(spec.corridor_half_width_m) > 0.0
            and 0.0 <= float(spec.corridor_safety_margin_m)
            < float(spec.corridor_half_width_m),
            "details": {
                "context_steps": int(spec.context_steps),
                "context_dt_s": float(spec.context_dt_s),
                "corridor_half_width_m": float(spec.corridor_half_width_m),
                "corridor_safety_margin_m": float(spec.corridor_safety_margin_m),
            },
        },
    ]


def _coverage_targets(spec: BroaderSmokeSpec) -> dict[str, Any]:
    matched_records = len(spec.runs) * int(spec.steps)
    return {
        "paired_runs": len(spec.runs),
        "baseline_logs": len(spec.runs),
        "matched_logs": len(spec.runs),
        "matched_records": matched_records,
        "matched_candidate_rows": matched_records * int(spec.num_candidates),
        "scenario_bucket_counts": _bucket_counts(spec),
        "max_logging_latency_ms": MAX_BROADER_LOGGING_MS,
    }


def _commands(spec: BroaderSmokeSpec) -> dict[str, Any]:
    baseline_root = f"{spec.root}/baseline"
    matched_root = f"{spec.root}/matched_progress_lane_hard_context_outcomes"
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
                "variant": "matched_progress_lane_hard_context_outcomes",
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
        "matched_context_contract_audit": _matched_context_contract_command(
            matched_root,
            audit_root,
            spec,
        ),
    }


def _replay_command(
    spec: BroaderSmokeSpec,
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
                "--camp_progress_lane_hard_context_logging",
                "--camp_progress_lane_hard_context_steps",
                str(spec.context_steps),
                "--camp_progress_lane_hard_context_dt_s",
                str(spec.context_dt_s),
                "--camp_progress_lane_hard_context_corridor_half_width_m",
                str(spec.corridor_half_width_m),
                "--camp_progress_lane_hard_context_corridor_safety_margin_m",
                str(spec.corridor_safety_margin_m),
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
    spec: BroaderSmokeSpec,
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


def _matched_context_contract_command(
    matched_root: str,
    audit_root: str,
    spec: BroaderSmokeSpec,
) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_matched_progress_lane_hard_context_outcomes.py",
        "--root",
        matched_root,
        "--expected_logs",
        str(len(spec.runs)),
        "--expected_records",
        str(spec.steps),
        "--expected_candidates",
        str(spec.num_candidates),
        "--label",
        "progress_lane_hard_context_matched_outcome_labels_nonformal_v1",
        "--output_json",
        f"{audit_root}/matched_progress_lane_hard_context_outcome_contract.json",
        "--output_md",
        f"{audit_root}/matched_progress_lane_hard_context_outcome_contract.md",
        "--require_pass",
    ]


def _accept_criteria(spec: BroaderSmokeSpec) -> list[str]:
    return [
        "all source and plan checks pass before replay",
        "all paired baseline and matched replay commands exit 0",
        "matched records contain progress_lane_hard_context_logging payloads and candidate_closed_loop_outcomes in the same record",
        "context payloads report selection_effect=false and future_outcome_leakage=false",
        "context payloads do not embed candidate_closed_loop_outcomes",
        "selector equivalence passes between baseline and matched branches",
        "dataset audit passes with closed_loop_outcome_policy=required",
        "matched context contract audit passes for all records and candidates",
        f"exactly {len(spec.runs)} matched logs and {len(spec.runs) * int(spec.steps)} matched records are present",
        "no formal seed 11/12/13 appears in any path, summary, or record",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any source or plan check fails",
        "any replay or audit command fails",
        "any matched record lacks progress_lane_hard_context_logging or candidate_closed_loop_outcomes",
        "any selected index, feasibility mask, atom, score, or weight changes under logging/outcome collection",
        "any runtime context descriptor uses closed-loop outcome labels or reports future_outcome_leakage=true",
        "any formal seed appears",
        "the run expands beyond the predeclared 4-run x 12-step nonformal scope",
    ]


def _bucket_counts(spec: BroaderSmokeSpec) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in spec.runs:
        for bucket in run.scenario_buckets:
            counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


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
        "# Progress+Lane/Hard Context Matched Outcome Label Pass Plan",
        "",
        "This is a design-only plan. It does not run Diffusion Planner, does "
        "not train CAMP, and does not authorize online selector promotion.",
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
    for item in report["source_checks"]:
        lines.append(f"| `{item['name']}` | `{item['passed']}` |")
    lines.extend(["", "## Plan Checks", ""])
    lines.extend(f"- `{item['name']}`: `{item['passed']}`" for item in report["plan_checks"])
    lines.extend(["", "## Coverage Targets", "", "```json"])
    lines.append(json.dumps(report["coverage_targets"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Replay Commands", ""])
    separator = " \\\n  "
    for item in report["commands"]["paired_replays"]:
        lines.extend(
            [
                f"### {item['variant']} / {item['run_id']}",
                "",
                "```bash",
                separator.join(item["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["## Audit Commands", ""])
    for name, command in report["commands"].items():
        if name == "paired_replays":
            continue
        lines.extend([f"### {name}", "", "```bash", separator.join(command), "```", ""])
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
