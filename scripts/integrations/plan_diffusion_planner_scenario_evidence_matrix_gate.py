#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_PROTOCOL_STATUS = "proof_protocol_v2_predeclared"
REQUIRED_PROTOCOL_NEXT_WORK = "scenario_manifest_and_evidence_matrix_design_only"
REQUIRED_MATRIX_DECISION = "approved_nonformal_plan_only"
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
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for the ProofProtocol v2 scenario manifest and "
            "evidence matrix. It validates an existing diverse matrix plan "
            "without running DP."
        )
    )
    parser.add_argument("--proof_protocol_v2_json", type=Path, required=True)
    parser.add_argument("--matrix_plan_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        proof_protocol_v2=_load_json(args.proof_protocol_v2_json),
        matrix_plan=_load_json(args.matrix_plan_json),
        label=args.label,
        paths={
            "proof_protocol_v2_json": str(args.proof_protocol_v2_json),
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
    proof_protocol_v2: dict[str, Any],
    matrix_plan: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    protocol_source = _protocol_source(proof_protocol_v2)
    matrix_source = _matrix_source(matrix_plan, protocol_source["required_buckets"])
    conflicts = _source_conflicts(proof_protocol_v2, matrix_plan)
    decision = _decision(protocol_source, matrix_source, conflicts)
    return {
        "analysis": {
            "name": "dp_camp_scenario_evidence_matrix_gate_v1",
            "label": label,
            "role": (
                "design-only ProofProtocol v2 gate for explicit scenario "
                "manifest coverage and predeclared non-formal evidence matrix"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "Scenario bucket labels and matrix rows are evaluation metadata. "
                "They do not change DP candidate generation, postprocessing, "
                "PerfectTracker, CAMP atoms, candidate features, affine "
                "score_k(w)=a_k^T w, or the simplex/CVaR/L2 robust master. "
                "This gate does not construct a DP-side classical Benders "
                "master/subproblem, dual, or cut."
            ),
        },
        "protocol_source": protocol_source,
        "matrix_source": matrix_source,
        "source_authorization_conflicts": conflicts,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _protocol_source(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    protocol = report.get("protocol") or {}
    required_buckets = list(protocol.get("required_scenario_buckets") or [])
    blocked_true = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == REQUIRED_PROTOCOL_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == REQUIRED_PROTOCOL_NEXT_WORK
            and not blocked_true
            and bool(required_buckets)
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "required_buckets": required_buckets,
        "blocked_true": blocked_true,
        "claim_rule": (protocol.get("primary_score") or {}).get("claim_rule"),
    }


def _matrix_source(
    report: dict[str, Any],
    required_buckets: list[str],
) -> dict[str, Any]:
    summary = report.get("summary") or {}
    manifest = report.get("scenario_bucket_manifest") or {}
    command = report.get("command") or {}
    argv = list(command.get("argv") or [])
    filters = list(manifest.get("filters") or [])
    filter_errors = _filter_errors(filters)
    bucket_counts = dict(summary.get("bucket_counts") or {})
    missing = [
        bucket
        for bucket in required_buckets
        if int(bucket_counts.get(bucket, 0) or 0) <= 0
    ]
    seeds = [int(seed) for seed in summary.get("seeds") or []]
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    command_gaps = [flag for flag in REQUIRED_COMMAND_FLAGS if flag not in argv]
    variants = _argument_value(argv, "--variants")
    variant_static = variants == "static"
    blockers = list(report.get("blockers") or [])
    return {
        "decision": report.get("decision"),
        "passed": (
            report.get("decision") == REQUIRED_MATRIX_DECISION
            and not blockers
            and not missing
            and not formal
            and not filter_errors
            and not command_gaps
            and variant_static
            and bool((report.get("analysis") or {}).get("explicit_labeling_only"))
            and bool(
                (report.get("analysis") or {}).get(
                    "labels_are_not_inferred_from_metrics"
                )
            )
        ),
        "planned_run_count": summary.get("planned_run_count"),
        "route_count": summary.get("route_count"),
        "bucket_counts": bucket_counts,
        "missing_required_buckets": missing,
        "formal_seeds": formal,
        "filter_errors": filter_errors,
        "command_gaps": command_gaps,
        "variant_static": variant_static,
        "blockers": blockers,
        "manifest_filter_count": len(filters),
        "manifest_route_labels": manifest.get("routes") or {},
        "explicit_labeling_only": bool(
            (report.get("analysis") or {}).get("explicit_labeling_only")
        ),
        "labels_are_not_inferred_from_metrics": bool(
            (report.get("analysis") or {}).get("labels_are_not_inferred_from_metrics")
        ),
    }


def _decision(
    protocol_source: dict[str, Any],
    matrix_source: dict[str, Any],
    conflicts: list[str],
) -> dict[str, Any]:
    if conflicts:
        status = "scenario_evidence_matrix_source_conflict"
        reasons = ["source_authorizes_blocked_action"]
        next_step = "Resolve source authorization conflicts before scenario evidence planning."
    elif not protocol_source["passed"]:
        status = "scenario_evidence_matrix_blocked_by_protocol"
        reasons = ["proof_protocol_v2_not_ready"]
        next_step = "Refresh or repair ProofProtocol v2 before validating a matrix plan."
    elif not matrix_source["passed"]:
        status = "scenario_evidence_matrix_incomplete"
        reasons = _matrix_failure_reasons(matrix_source)
        next_step = (
            "Fix the design-only matrix plan or manifest coverage before any "
            "candidate-branch oracle label collection."
        )
    else:
        status = "scenario_evidence_matrix_predeclared"
        reasons = [
            "all_required_buckets_have_predeclared_coverage",
            "scenario_labels_use_route_or_config_metadata_only",
            "static_outcome_label_matrix_command_is_predeclared",
            "formal_seeds_are_excluded",
        ]
        next_step = (
            "Run or refresh the candidate-branch oracle input-readiness gate "
            "against the planned non-formal matrix outputs before any selector "
            "training, tiny smoke, or larger non-formal run."
        )
    return {
        "status": status,
        "passed": status == "scenario_evidence_matrix_predeclared",
        "authorized_next_work": "candidate_branch_oracle_input_readiness_gate",
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "reasons": reasons,
        "next_step": next_step,
    }


def _matrix_failure_reasons(source: dict[str, Any]) -> list[str]:
    reasons = []
    if source["decision"] != REQUIRED_MATRIX_DECISION:
        reasons.append("matrix_plan_not_approved")
    if source["blockers"]:
        reasons.append("matrix_plan_has_blockers")
    if source["missing_required_buckets"]:
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
        final = report.get("final_decision") or {}
        name = str(_get(report, "analysis", "name") or f"source_{index}")
        for key in BLOCKED_ACTIONS:
            if bool(final.get(key)):
                conflicts.append(f"{name}:{key}")
    return conflicts


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    matrix = report["matrix_source"]
    lines = [
        "# DP-CAMP Scenario Evidence Matrix Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Protocol Source",
        "",
        f"- Status: `{report['protocol_source']['status']}`",
        f"- Passed: `{report['protocol_source']['passed']}`",
        f"- Claim rule: `{report['protocol_source']['claim_rule']}`",
        "",
        "## Matrix Source",
        "",
        f"- Decision: `{matrix['decision']}`",
        f"- Passed: `{matrix['passed']}`",
        f"- Planned runs: `{matrix['planned_run_count']}`",
        f"- Routes: `{matrix['route_count']}`",
        f"- Missing buckets: `{', '.join(matrix['missing_required_buckets']) or 'none'}`",
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
    lines.extend(["", "## Blocked Actions", ""])
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision.get(action, False)}`")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Source Artifacts",
            "",
            "| Artifact | Path |",
            "| --- | --- |",
        ]
    )
    for name, path in (report["analysis"].get("paths") or {}).items():
        lines.append(f"| `{name}` | `{path}` |")
    lines.append("")
    return "\n".join(lines)


def _argument_value(argv: list[str], flag: str) -> str | None:
    try:
        index = argv.index(flag)
    except ValueError:
        return None
    next_index = index + 1
    if next_index >= len(argv):
        return None
    return str(argv[next_index])


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
