#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "targeted_safety_intervention_proof_objective_predeclared"
SOURCE_NEXT_WORK = "targeted_safety_intervention_scenario_manifest_design_only"

READY_STATUS = "targeted_safety_intervention_scenario_manifest_predeclared"
INCOMPLETE_STATUS = "targeted_safety_intervention_scenario_manifest_incomplete"
SOURCE_BLOCKED_STATUS = "targeted_safety_intervention_scenario_manifest_source_blocked"
CONFLICT_STATUS = "targeted_safety_intervention_scenario_manifest_source_conflict"
AUTHORIZED_NEXT_WORK = "targeted_candidate_branch_oracle_input_readiness_gate"

FORMAL_SEEDS = {11, 12, 13}
ALLOWED_FILTER_FIELDS = {
    "route",
    "route_name",
    "route_stem",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
}
OUTCOME_FILTER_FIELDS = {
    "safety_cost_v1",
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "route_completion_rate",
    "mean_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "fallback_rate",
    "p95_selection_latency_ms",
}
REQUIRED_COMMAND_FLAGS = (
    "--camp_collect_closed_loop_outcomes",
    "--skip_compare",
    "--scenario_bucket_manifest",
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only targeted scenario manifest gate. It validates that a "
            "predeclared nonformal matrix plan covers all targeted safety "
            "objective buckets without outcome-derived filters."
        )
    )
    parser.add_argument("--targeted_objective_json", type=Path, required=True)
    parser.add_argument("--matrix_plan_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        targeted_objective=_load_json(args.targeted_objective_json),
        matrix_plan=_load_json(args.matrix_plan_json),
        label=args.label,
        paths={
            "targeted_objective_json": str(args.targeted_objective_json),
            "matrix_plan_json": str(args.matrix_plan_json),
        },
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
    targeted_objective: dict[str, Any],
    matrix_plan: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    objective_source = _objective_source(targeted_objective)
    matrix_source = _matrix_source(matrix_plan, objective_source)
    conflicts = _source_conflicts(targeted_objective, matrix_plan)
    decision = _decision(objective_source, matrix_source, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_targeted_safety_scenario_manifest_gate_v1",
            "label": label,
            "role": (
                "design-only gate for targeted safety-intervention scenario "
                "manifest and evidence-matrix coverage"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "Scenario bucket labels and matrix rows are evaluation "
                "metadata. They do not change DP candidate generation, "
                "postprocessing, PerfectTracker, CAMP atoms, candidate "
                "features, affine score_k(w)=a_k^T w, or the simplex/CVaR/L2 "
                "robust master. Outcome labels may be collected later only "
                "after a separate gate and are never online selector inputs. "
                "This gate does not construct a DP-side classical Benders "
                "master/subproblem, dual, or cut."
            ),
        },
        "objective_source": objective_source,
        "matrix_source": matrix_source,
        "source_authorization_conflicts": conflicts,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _objective_source(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    objective = _dict(report.get("objective_contract"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    target_buckets = _string_list(objective.get("target_buckets"))
    guard_buckets = _string_list(objective.get("guard_buckets"))
    required_buckets = _string_list(objective.get("required_buckets"))
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and bool(target_buckets)
            and bool(guard_buckets)
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "target_buckets": target_buckets,
        "guard_buckets": guard_buckets,
        "required_buckets": required_buckets,
        "blocked_action_conflicts": conflicts,
        "primary_claim": _dict(objective.get("primary_claim")),
        "guard_claims": _dict(objective.get("guard_claims")),
    }


def _matrix_source(
    report: dict[str, Any],
    objective_source: dict[str, Any],
) -> dict[str, Any]:
    summary = _dict(report.get("summary"))
    manifest = _dict(report.get("scenario_bucket_manifest"))
    command = _dict(report.get("command"))
    analysis = _dict(report.get("analysis"))
    argv = [str(item) for item in command.get("argv") or []]
    bucket_counts = {
        str(key): int(value)
        for key, value in _dict(summary.get("bucket_counts")).items()
        if _int_or_none(value) is not None
    }
    target_missing = [
        bucket
        for bucket in objective_source["target_buckets"]
        if int(bucket_counts.get(bucket, 0)) <= 0
    ]
    guard_missing = [
        bucket
        for bucket in objective_source["guard_buckets"]
        if int(bucket_counts.get(bucket, 0)) <= 0
    ]
    required_missing = [
        bucket
        for bucket in objective_source["required_buckets"]
        if int(bucket_counts.get(bucket, 0)) <= 0
    ]
    seeds = [int(seed) for seed in summary.get("seeds") or []]
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    filter_errors = _filter_errors(list(manifest.get("filters") or []))
    command_gaps = [flag for flag in REQUIRED_COMMAND_FLAGS if flag not in argv]
    variants = _argument_value(argv, "--variants")
    blockers = [str(item) for item in report.get("blockers") or []]
    return {
        "decision": report.get("decision"),
        "passed": (
            report.get("decision") == "approved_nonformal_plan_only"
            and not blockers
            and not target_missing
            and not guard_missing
            and not required_missing
            and not formal
            and not filter_errors
            and not command_gaps
            and variants == "static"
            and bool(analysis.get("explicit_labeling_only"))
            and bool(analysis.get("labels_are_not_inferred_from_metrics"))
        ),
        "planned_run_count": summary.get("planned_run_count"),
        "route_count": summary.get("route_count"),
        "bucket_counts": bucket_counts,
        "target_missing_buckets": target_missing,
        "guard_missing_buckets": guard_missing,
        "required_missing_buckets": required_missing,
        "formal_seeds": formal,
        "filter_errors": filter_errors,
        "command_gaps": command_gaps,
        "variant_static": variants == "static",
        "blockers": blockers,
        "explicit_labeling_only": bool(analysis.get("explicit_labeling_only")),
        "labels_are_not_inferred_from_metrics": bool(
            analysis.get("labels_are_not_inferred_from_metrics")
        ),
        "manifest_filter_count": len(list(manifest.get("filters") or [])),
        "manifest_route_labels": manifest.get("routes") or {},
    }


def _decision(
    objective_source: dict[str, Any],
    matrix_source: dict[str, Any],
    conflicts: list[str],
) -> dict[str, Any]:
    if conflicts:
        status = CONFLICT_STATUS
        reasons = ["source_authorizes_blocked_action"]
        next_step = "Resolve source authorization conflicts before manifest planning."
    elif not objective_source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        reasons = ["targeted_objective_not_ready"]
        next_step = "Repair or rerun the targeted proof-objective gate."
    elif not matrix_source["passed"]:
        status = INCOMPLETE_STATUS
        reasons = _matrix_failure_reasons(matrix_source)
        next_step = (
            "Repair the targeted scenario manifest/matrix plan before any "
            "candidate-branch oracle or outcome-label replay."
        )
    else:
        status = READY_STATUS
        reasons = [
            "all_target_buckets_have_predeclared_coverage",
            "all_guard_buckets_have_predeclared_coverage",
            "scenario_labels_use_route_or_config_metadata_only",
            "static_outcome_label_matrix_command_is_predeclared",
            "formal_seeds_are_excluded",
        ]
        next_step = (
            "Run or refresh the targeted candidate-branch oracle input-readiness "
            "gate before any selector training, tiny smoke, larger nonformal "
            "matrix, or formal seed work."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if status == READY_STATUS else None,
        "recommended_first_action": (
            "targeted_candidate_branch_oracle_input_readiness_gate"
            if status == READY_STATUS
            else "repair_targeted_scenario_manifest_plan"
        ),
        "reasons": reasons,
        "next_step": next_step,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _matrix_failure_reasons(source: dict[str, Any]) -> list[str]:
    reasons = []
    if source["decision"] != "approved_nonformal_plan_only":
        reasons.append("matrix_plan_not_approved")
    if source["blockers"]:
        reasons.append("matrix_plan_has_blockers")
    if source["target_missing_buckets"]:
        reasons.append("matrix_plan_missing_target_buckets")
    if source["guard_missing_buckets"]:
        reasons.append("matrix_plan_missing_guard_buckets")
    if source["required_missing_buckets"]:
        reasons.append("matrix_plan_missing_required_buckets")
    if source["formal_seeds"]:
        reasons.append("matrix_plan_uses_formal_seeds")
    if source["filter_errors"]:
        reasons.append("manifest_filter_not_config_only")
    if source["command_gaps"]:
        reasons.append("matrix_command_missing_required_flags")
    if not source["variant_static"]:
        reasons.append("matrix_command_not_static_variant")
    if not source["explicit_labeling_only"]:
        reasons.append("matrix_source_not_explicit_labeling_only")
    if not source["labels_are_not_inferred_from_metrics"]:
        reasons.append("matrix_source_does_not_forbid_metric_inference")
    return reasons or ["matrix_source_failed_unknown_condition"]


def _filter_errors(filters: list[Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for index, entry in enumerate(filters):
        if not isinstance(entry, dict):
            errors.append({"index": index, "error": "filter_not_object"})
            continue
        match = entry.get("match")
        if not isinstance(match, dict) or not match:
            errors.append({"index": index, "name": entry.get("name"), "error": "empty_match"})
            continue
        invalid = sorted(set(match) - ALLOWED_FILTER_FIELDS)
        outcome = sorted(set(match) & OUTCOME_FILTER_FIELDS)
        if invalid or outcome:
            errors.append(
                {
                    "index": index,
                    "name": entry.get("name"),
                    "invalid_fields": invalid,
                    "outcome_fields": outcome,
                }
            )
    return errors


def _source_conflicts(*reports: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    for index, report in enumerate(reports):
        final = _dict(report.get("final_decision"))
        name = str(_get(report, "analysis", "name") or f"source_{index}")
        for key in BLOCKED_ACTIONS:
            if bool(final.get(key)):
                conflicts.append(f"{name}:{key}")
    return conflicts


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    objective = report["objective_source"]
    matrix = report["matrix_source"]
    lines = [
        "# Targeted Safety Scenario Manifest Gate",
        "",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Objective Source",
        "",
        f"- Status: `{objective['status']}`",
        f"- Targets: `{', '.join(objective['target_buckets'])}`",
        f"- Guards: `{', '.join(objective['guard_buckets'])}`",
        "",
        "## Matrix Source",
        "",
        f"- Decision: `{matrix['decision']}`",
        f"- Planned runs: `{matrix['planned_run_count']}`",
        f"- Routes: `{matrix['route_count']}`",
        f"- Missing target buckets: `{', '.join(matrix['target_missing_buckets']) or 'none'}`",
        f"- Missing guard buckets: `{', '.join(matrix['guard_missing_buckets']) or 'none'}`",
        f"- Formal seeds: `{', '.join(str(seed) for seed in matrix['formal_seeds']) or 'none'}`",
        "",
        "## Bucket Counts",
        "",
        "| Bucket | Planned rows |",
        "| --- | ---: |",
    ]
    for bucket, count in sorted(matrix["bucket_counts"].items()):
        lines.append(f"| `{bucket}` | {count} |")
    lines.extend(["", "## Decision Reasons", ""])
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run DP, train CAMP, promote an online selector, "
            "authorize Full36, or touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _argument_value(argv: list[str], flag: str) -> str | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(argv):
        return None
    return str(argv[index + 1])


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get(report: dict[str, Any], *path: str) -> Any:
    current: Any = report
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
