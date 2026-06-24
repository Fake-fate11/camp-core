#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


COMPLETE_STATUS = "dp_native_candidate_reranking_fixed_artifact_evidence_audit_complete"
REJECT_STATUS = "dp_native_candidate_reranking_fixed_artifact_evidence_audit_rejected"
READY_NEXT_WORK = "dp_native_candidate_reranking_static_selector_contract_plan_only"
GAP_NEXT_WORK = "dp_native_candidate_tensor_provenance_gap_design_plan_only"
EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

DEFAULT_SOURCE_ROOT = (
    ROOT
    / "analysis_bundles"
    / "dp_native_candidate_reranking_fixed_artifact_sources_e9f474a"
)

REQUIRED_CANDIDATE_FIELDS = (
    "feasible_mask",
    "infeasibility_reasons",
    "scores",
    "selection_scores",
    "atoms",
    "normalized_atoms",
)
PROXY_COORDINATE_FIELDS = (
    "candidate_first_reference_xy",
    "candidate_perfect_tracker_reference_first_xy",
    "candidate_perfect_tracker_first_step_reach_m",
)
EXACT_EQUIVALENCE_FIELDS = (
    "selected_index",
    "feasible_mask",
    "infeasibility_reasons",
)
NUMERIC_EQUIVALENCE_FIELDS = (
    "scores",
    "selection_scores",
    "atoms",
    "normalized_atoms",
)
TENSOR_HASH_KEY_FRAGMENTS = (
    "candidate_tensor_sha",
    "candidate_tensor_hash",
    "raw_candidate_sha",
    "raw_candidate_tensor_sha",
)
BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "trajectory_rewrite_authorized",
    "candidate_tensor_mutation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "offline_selector_screen_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "atom_promotion_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only evidence audit for DP-native CAMP candidate reranking "
            "boundaries over fixed artifacts."
        )
    )
    parser.add_argument("--source_root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--selector_equivalence_json", type=Path, default=None)
    parser.add_argument("--payload_audit_json", type=Path, default=None)
    parser.add_argument("--dataset_audit_json", type=Path, default=None)
    parser.add_argument("--baseline_selection_log_json", type=Path, default=None)
    parser.add_argument("--candidate_selection_log_json", type=Path, default=None)
    parser.add_argument("--baseline_replay_summary_json", type=Path, default=None)
    parser.add_argument("--candidate_replay_summary_json", type=Path, default=None)
    parser.add_argument("--safety_cost_oracle_json", type=Path, default=None)
    parser.add_argument("--design_plan_json", type=Path, default=None)
    parser.add_argument("--dp_repo", type=Path, default=None)
    parser.add_argument("--expected_dp_head", default=EXPECTED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = _resolve_paths(args)
    report = build_report(
        selector_equivalence=_load_json(paths["selector_equivalence_json"]),
        payload_audit=_load_json(paths["payload_audit_json"]),
        dataset_audit=_load_json(paths["dataset_audit_json"]),
        baseline_selection_log=_load_list(paths["baseline_selection_log_json"]),
        candidate_selection_log=_load_list(paths["candidate_selection_log_json"]),
        baseline_replay_summary=_load_json(paths["baseline_replay_summary_json"]),
        candidate_replay_summary=_load_json(paths["candidate_replay_summary_json"]),
        safety_cost_oracle=_load_json(paths["safety_cost_oracle_json"]),
        design_plan=_load_json(paths["design_plan_json"]),
        source_paths={key: str(value) for key, value in paths.items()},
        dp_head=_git_head(args.dp_repo) if args.dp_repo else args.expected_dp_head,
        expected_dp_head=args.expected_dp_head,
        label=args.label,
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
    selector_equivalence: dict[str, Any],
    payload_audit: dict[str, Any],
    dataset_audit: dict[str, Any],
    baseline_selection_log: list[Any],
    candidate_selection_log: list[Any],
    baseline_replay_summary: dict[str, Any],
    candidate_replay_summary: dict[str, Any],
    safety_cost_oracle: dict[str, Any],
    design_plan: dict[str, Any],
    source_paths: dict[str, str] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
    expected_dp_head: str = EXPECTED_DP_HEAD,
    label: str | None = None,
) -> dict[str, Any]:
    source_paths = source_paths or {}
    baseline_records = _selection_log_summary(baseline_selection_log)
    candidate_records = _selection_log_summary(candidate_selection_log)
    selector = _selector_equivalence_summary(selector_equivalence)
    payload = _payload_summary(payload_audit)
    dataset = _dataset_summary(dataset_audit)
    replay = _replay_summary_pair(baseline_replay_summary, candidate_replay_summary)
    oracle = _oracle_summary(safety_cost_oracle)
    design = _design_summary(design_plan)
    mutation = _mutation_summary(
        baseline_selection_log=baseline_selection_log,
        candidate_selection_log=candidate_selection_log,
        selector=selector,
    )
    provenance = _candidate_tensor_provenance_summary(
        baseline_selection_log=baseline_selection_log,
        candidate_selection_log=candidate_selection_log,
        baseline_replay_summary=baseline_replay_summary,
        candidate_replay_summary=candidate_replay_summary,
        replay=replay,
    )
    checks = [
        *_source_shape_checks(baseline_records, candidate_records),
        *_selector_checks(selector),
        *_payload_checks(payload),
        *_dataset_checks(dataset),
        *_replay_checks(replay),
        *_oracle_checks(oracle),
        *_design_checks(design),
        _check("dp_head_fixed", dp_head == expected_dp_head),
    ]
    audit_complete = all(check["passed"] for check in checks)
    gaps = _evidence_gaps(provenance=provenance, mutation=mutation)
    weak = _weak_evidence(provenance=provenance, mutation=mutation)
    evidence_ready = audit_complete and not gaps and not weak
    return {
        "analysis": {
            "name": "dp_native_candidate_reranking_fixed_artifact_evidence_audit_v1",
            "label": label,
            "role": (
                "read-only audit of whether existing fixed artifacts prove the "
                "DP-native candidate reranking input/output boundary"
            ),
            "read_only": True,
            "candidate_generation_execution": False,
            "trajectory_rewrite": False,
            "candidate_tensor_mutation": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This audit reads existing fixed artifacts only. It does not "
                "generate candidates, rewrite trajectories, append candidate "
                "rows, rerun screens, run replay, use formal seeds, train CAMP, "
                "promote atoms, change online selection, modify DP, claim safety "
                "benefit, or claim CAMP over DP Top-1."
            ),
        },
        "source_paths": source_paths,
        "source_hashes": _source_hashes(source_paths),
        "head_audit": {
            "dp_head": dp_head,
            "expected_dp_head": expected_dp_head,
        },
        "candidate_count_evidence": {
            "baseline": baseline_records,
            "candidate": candidate_records,
            "count_invariant": (
                baseline_records["candidate_count_values"]
                == candidate_records["candidate_count_values"]
            ),
        },
        "selected_index_range_evidence": {
            "baseline_all_in_range": baseline_records["selected_index_all_in_range"],
            "candidate_all_in_range": candidate_records["selected_index_all_in_range"],
            "selected_index_values": {
                "baseline": baseline_records["selected_index_values"],
                "candidate": candidate_records["selected_index_values"],
            },
        },
        "available_input_evidence": {
            "baseline_required_fields_present": baseline_records[
                "required_candidate_fields_present"
            ],
            "candidate_required_fields_present": candidate_records[
                "required_candidate_fields_present"
            ],
            "field_length_mismatches": {
                "baseline": baseline_records["field_length_mismatches"],
                "candidate": candidate_records["field_length_mismatches"],
            },
        },
        "selector_equivalence_evidence": selector,
        "payload_evidence": payload,
        "dataset_evidence": dataset,
        "replay_summary_evidence": replay,
        "candidate_tensor_provenance_evidence": provenance,
        "mutation_evidence": mutation,
        "candidate_pool_opportunity_evidence": oracle,
        "prior_design_plan_evidence": design,
        "checks": checks,
        "evidence_gaps": gaps,
        "weak_evidence": weak,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(
            audit_complete=audit_complete,
            evidence_ready=evidence_ready,
            gaps=gaps,
            weak=weak,
            checks=checks,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    provenance = report["candidate_tensor_provenance_evidence"]
    mutation = report["mutation_evidence"]
    lines = [
        "# DP-Native Candidate Reranking Fixed-Artifact Evidence Audit",
        "",
        f"- Status: `{decision['status']}`",
        f"- Audit complete: `{decision['evidence_audit_complete']}`",
        f"- DP-native reranking evidence ready: `{decision['dp_native_reranking_evidence_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Candidate generation authorized: `{decision['candidate_generation_execution_authorized']}`",
        f"- Trajectory rewrite authorized: `{decision['trajectory_rewrite_authorized']}`",
        f"- Candidate tensor mutation authorized: `{decision['candidate_tensor_mutation_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Artifacts",
        "",
    ]
    for name, path in sorted(report["source_paths"].items()):
        digest = report["source_hashes"].get(name)
        lines.append(f"- `{name}`: `{path}` sha256=`{digest}`")
    counts = report["candidate_count_evidence"]
    selected = report["selected_index_range_evidence"]
    lines.extend(
        [
            "",
            "## Candidate Count And Selected Index",
            "",
            f"- Baseline candidate counts: `{counts['baseline']['candidate_count_values']}`",
            f"- Candidate candidate counts: `{counts['candidate']['candidate_count_values']}`",
            f"- Candidate count invariant: `{counts['count_invariant']}`",
            f"- Baseline selected indices: `{selected['selected_index_values']['baseline']}`",
            f"- Candidate selected indices: `{selected['selected_index_values']['candidate']}`",
            f"- Baseline selected indices in range: `{selected['baseline_all_in_range']}`",
            f"- Candidate selected indices in range: `{selected['candidate_all_in_range']}`",
            "",
            "## Selector Equivalence",
            "",
            f"- Equivalent: `{report['selector_equivalence_evidence']['equivalent']}`",
            f"- Records: `{report['selector_equivalence_evidence']['records']}`",
            f"- Required exact mismatch total: `{report['selector_equivalence_evidence']['required_exact_mismatch_total']}`",
            f"- Required numeric mismatch total: `{report['selector_equivalence_evidence']['required_numeric_mismatch_total']}`",
            "",
            "## Candidate Tensor Provenance",
            "",
            f"- Finite candidate contract present: `{provenance['finite_candidate_contract_present']}`",
            f"- Candidate tensor hash present: `{provenance['candidate_tensor_hash_present']}`",
            f"- Full candidate coordinate tensor present: `{provenance['full_candidate_coordinate_tensor_present']}`",
            f"- Replay summaries report changes_candidate_set: `{provenance['changes_candidate_set_values']}`",
            f"- Reference blend selection_effect values: `{provenance['reference_blend_selection_effect_values']}`",
            "",
            "## Mutation Evidence",
            "",
            f"- Selector equivalence proves logged selector fields unchanged: `{mutation['selector_equivalence_logged_fields_unchanged']}`",
            f"- Proxy candidate coordinate fields unchanged: `{mutation['proxy_coordinate_fields_unchanged']}`",
            f"- Full candidate tensor mutation proven absent: `{mutation['full_candidate_tensor_mutation_proven_absent']}`",
            "",
            "## Evidence Gaps",
            "",
        ]
    )
    if report["evidence_gaps"]:
        for gap in report["evidence_gaps"]:
            lines.append(f"- {gap}")
    else:
        lines.append("- none")
    lines.extend(["", "## Weak Evidence", ""])
    if report["weak_evidence"]:
        for item in report["weak_evidence"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "This audit is complete if the fixed artifacts can be parsed and their "
            "selector/candidate-count contracts are internally consistent. It does "
            "not treat proxy fields as a full candidate tensor hash. If the tensor "
            "hash or raw DP provenance is missing, the next work must close that "
            "provenance gap before replay, training, promotion, or claims.",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    root = args.source_root
    defaults = {
        "selector_equivalence_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "audit"
            / "selector_equivalence.json"
        ),
        "payload_audit_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "audit"
            / "candidate_set_consensus_payload_smoke.json"
        ),
        "dataset_audit_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "audit"
            / "dataset_audit.json"
        ),
        "baseline_selection_log_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "baseline"
            / "camp_selection_log.json"
        ),
        "candidate_selection_log_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "logging_enabled"
            / "camp_selection_log.json"
        ),
        "baseline_replay_summary_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "baseline"
            / "camp_replay_summary.json"
        ),
        "candidate_replay_summary_json": (
            root
            / "candidate_set_consensus_payload_smoke"
            / "logging_enabled"
            / "camp_replay_summary.json"
        ),
        "safety_cost_oracle_json": (
            root / "safety_cost_oracle_d2899e6" / "safety_cost_oracle.json"
        ),
        "design_plan_json": (
            root
            / "dp_native_candidate_reranking_design_plan_b330901"
            / "dp_native_candidate_reranking_design_plan.json"
        ),
    }
    return {
        key: Path(getattr(args, key)) if getattr(args, key) else value
        for key, value in defaults.items()
    }


def _selection_log_summary(records: list[Any]) -> dict[str, Any]:
    candidate_counts: list[int] = []
    selected_values: list[int] = []
    selected_in_range: list[bool] = []
    missing_fields: dict[str, int] = {field: 0 for field in REQUIRED_CANDIDATE_FIELDS}
    length_mismatches: list[dict[str, Any]] = []
    proxy_fields_present: dict[str, int] = {field: 0 for field in PROXY_COORDINATE_FIELDS}
    for index, record_any in enumerate(records):
        record = _dict(record_any)
        candidate_count = _optional_int(record.get("num_candidates"))
        selected_index = _optional_int(record.get("selected_index"))
        if candidate_count is not None:
            candidate_counts.append(candidate_count)
        if selected_index is not None:
            selected_values.append(selected_index)
        selected_in_range.append(
            candidate_count is not None
            and selected_index is not None
            and 0 <= selected_index < candidate_count
        )
        for field in REQUIRED_CANDIDATE_FIELDS:
            value = record.get(field)
            if not isinstance(value, list):
                missing_fields[field] += 1
                continue
            if candidate_count is not None and len(value) != candidate_count:
                length_mismatches.append(
                    {
                        "record": index,
                        "field": field,
                        "length": len(value),
                        "candidate_count": candidate_count,
                    }
                )
        for field in PROXY_COORDINATE_FIELDS:
            value = record.get(field)
            if isinstance(value, list) and candidate_count is not None and len(value) == candidate_count:
                proxy_fields_present[field] += 1
    return {
        "records": len(records),
        "candidate_count_values": sorted(set(candidate_counts)),
        "selected_index_values": selected_values,
        "selected_index_all_in_range": bool(selected_in_range)
        and all(selected_in_range),
        "required_candidate_fields_present": all(
            count == 0 for count in missing_fields.values()
        ),
        "missing_required_candidate_fields": missing_fields,
        "field_length_mismatches": length_mismatches,
        "proxy_coordinate_fields_present_counts": proxy_fields_present,
    }


def _selector_equivalence_summary(report: dict[str, Any]) -> dict[str, Any]:
    exact = _dict(report.get("exact_field_mismatches"))
    numeric = _dict(report.get("numeric_field_mismatches"))
    numeric_shape = _dict(report.get("numeric_shape_mismatches"))
    numeric_nonexact = _dict(report.get("numeric_nonexact_entries"))
    return {
        "equivalent": bool(report.get("equivalent")),
        "records": _optional_int(report.get("records")),
        "required_exact_mismatch_total": _sum_selected(exact, EXACT_EQUIVALENCE_FIELDS),
        "required_numeric_mismatch_total": _sum_selected(
            numeric, NUMERIC_EQUIVALENCE_FIELDS
        ),
        "required_numeric_shape_mismatch_total": _sum_selected(
            numeric_shape, NUMERIC_EQUIVALENCE_FIELDS
        ),
        "required_numeric_nonexact_total": _sum_selected(
            numeric_nonexact, NUMERIC_EQUIVALENCE_FIELDS
        ),
        "exact_field_mismatches": exact,
        "numeric_field_mismatches": numeric,
        "numeric_shape_mismatches": numeric_shape,
        "numeric_nonexact_entries": numeric_nonexact,
    }


def _payload_summary(report: dict[str, Any]) -> dict[str, Any]:
    counts = _dict(report.get("counts"))
    decision = _dict(report.get("final_decision"))
    analysis = _dict(report.get("analysis"))
    return {
        "passed": bool(decision.get("passed")),
        "status": decision.get("status"),
        "records": _optional_int(counts.get("records")),
        "available_payload_records": _optional_int(
            counts.get("available_payload_records")
        ),
        "invalid_payload_records": _optional_int(counts.get("invalid_payload_records")),
        "selection_effect_allowed": bool(analysis.get("selection_effect_allowed")),
        "future_outcome_labels_used": bool(analysis.get("future_outcome_labels_used")),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    checks = _dict(report.get("checks"))
    counts = _dict(report.get("counts"))
    return {
        "passed": bool(report.get("passed")),
        "records": _optional_int(counts.get("records")),
        "candidates": _optional_int(counts.get("candidates")),
        "finite_candidate_contract_verified": bool(
            checks.get("finite_candidate_contract_verified")
        ),
        "closed_loop_outcomes_forbidden": bool(
            checks.get("closed_loop_outcomes_forbidden")
        ),
        "closed_loop_outcome_records": _optional_int(
            checks.get("closed_loop_outcome_records")
        ),
        "forbidden_seed_check": bool(checks.get("forbidden_seed_check")),
    }


def _replay_summary_pair(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    baseline_contract = _dict(baseline.get("dp_camp_finite_candidate_contract"))
    candidate_contract = _dict(candidate.get("dp_camp_finite_candidate_contract"))
    baseline_generation = _dict(baseline.get("candidate_generation_contract"))
    candidate_generation = _dict(candidate.get("candidate_generation_contract"))
    baseline_blend = _dict(baseline.get("candidate_reference_blend"))
    candidate_blend = _dict(candidate.get("candidate_reference_blend"))
    return {
        "baseline_num_candidates": _optional_int(baseline.get("num_candidates")),
        "candidate_num_candidates": _optional_int(candidate.get("num_candidates")),
        "num_candidates_match": _optional_int(baseline.get("num_candidates"))
        == _optional_int(candidate.get("num_candidates")),
        "finite_candidate_contract_present": bool(baseline_contract)
        and bool(candidate_contract),
        "finite_candidate_contract_text": candidate_contract.get("candidate_set"),
        "score_contract": candidate_contract.get("score"),
        "selection_rule": candidate_contract.get("selection_rule"),
        "candidate_generation_num_candidates": [
            _optional_int(baseline_generation.get("num_candidates")),
            _optional_int(candidate_generation.get("num_candidates")),
        ],
        "changes_candidate_set_values": [
            bool(baseline_generation.get("changes_candidate_set")),
            bool(candidate_generation.get("changes_candidate_set")),
        ],
        "changes_camp_score_values": [
            bool(baseline_generation.get("changes_camp_score")),
            bool(candidate_generation.get("changes_camp_score")),
        ],
        "changes_dp_weights_values": [
            bool(baseline_generation.get("changes_diffusion_planner_weights")),
            bool(candidate_generation.get("changes_diffusion_planner_weights")),
        ],
        "reference_blend_selection_effect_values": [
            bool(baseline_blend.get("selection_effect")),
            bool(candidate_blend.get("selection_effect")),
        ],
    }


def _oracle_summary(report: dict[str, Any]) -> dict[str, Any]:
    gate = _dict(report.get("opportunity_gate"))
    overall = _dict(report.get("overall"))
    analysis = _dict(report.get("analysis"))
    return {
        "opportunity_gate_passed": bool(gate.get("passed")),
        "records": _optional_int(_dict(report.get("records")).get("total")),
        "mean_eligible_candidates": _optional_float(
            overall.get("mean_eligible_candidates")
        ),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "training": bool(analysis.get("training")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "interpretation": gate.get("interpretation"),
    }


def _design_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("design_plan"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "route": plan.get("route"),
        "candidate_generation_authorized": bool(
            decision.get("candidate_generation_execution_authorized")
        ),
        "trajectory_rewrite_authorized": bool(
            decision.get("trajectory_rewrite_authorized")
        ),
        "candidate_tensor_mutation_authorized": bool(
            decision.get("candidate_tensor_mutation_authorized")
        ),
    }


def _candidate_tensor_provenance_summary(
    *,
    baseline_selection_log: list[Any],
    candidate_selection_log: list[Any],
    baseline_replay_summary: dict[str, Any],
    candidate_replay_summary: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    hash_hits = [
        *_find_key_fragments(baseline_selection_log, TENSOR_HASH_KEY_FRAGMENTS),
        *_find_key_fragments(candidate_selection_log, TENSOR_HASH_KEY_FRAGMENTS),
        *_find_key_fragments(baseline_replay_summary, TENSOR_HASH_KEY_FRAGMENTS),
        *_find_key_fragments(candidate_replay_summary, TENSOR_HASH_KEY_FRAGMENTS),
    ]
    coordinate_tensor_hits = [
        *_find_key_fragments(baseline_selection_log, ("candidate_tensor", "raw_candidates")),
        *_find_key_fragments(candidate_selection_log, ("candidate_tensor", "raw_candidates")),
    ]
    full_coordinate_hits = [
        hit
        for hit in coordinate_tensor_hits
        if "sha" not in hit.lower() and "hash" not in hit.lower()
    ]
    return {
        "finite_candidate_contract_present": replay[
            "finite_candidate_contract_present"
        ],
        "finite_candidate_contract_text": replay["finite_candidate_contract_text"],
        "candidate_tensor_hash_present": bool(hash_hits),
        "candidate_tensor_hash_key_paths": sorted(set(hash_hits)),
        "full_candidate_coordinate_tensor_present": bool(full_coordinate_hits),
        "full_candidate_coordinate_tensor_key_paths": sorted(set(full_coordinate_hits)),
        "candidate_generation_num_candidates": replay[
            "candidate_generation_num_candidates"
        ],
        "changes_candidate_set_values": replay["changes_candidate_set_values"],
        "changes_camp_score_values": replay["changes_camp_score_values"],
        "changes_dp_weights_values": replay["changes_dp_weights_values"],
        "reference_blend_selection_effect_values": replay[
            "reference_blend_selection_effect_values"
        ],
    }


def _mutation_summary(
    *,
    baseline_selection_log: list[Any],
    candidate_selection_log: list[Any],
    selector: dict[str, Any],
) -> dict[str, Any]:
    baseline_hash_values = _find_key_fragment_values(
        baseline_selection_log,
        TENSOR_HASH_KEY_FRAGMENTS,
    )
    candidate_hash_values = _find_key_fragment_values(
        candidate_selection_log,
        TENSOR_HASH_KEY_FRAGMENTS,
    )
    tensor_hash_values_equal = (
        bool(baseline_hash_values)
        and baseline_hash_values == candidate_hash_values
    )
    proxy_equal = {
        field: _field_values(baseline_selection_log, field)
        == _field_values(candidate_selection_log, field)
        for field in PROXY_COORDINATE_FIELDS
    }
    selector_unchanged = (
        selector["equivalent"]
        and selector["required_exact_mismatch_total"] == 0
        and selector["required_numeric_mismatch_total"] == 0
        and selector["required_numeric_shape_mismatch_total"] == 0
        and selector["required_numeric_nonexact_total"] == 0
    )
    return {
        "selector_equivalence_logged_fields_unchanged": selector_unchanged,
        "candidate_tensor_hash_values_equal": tensor_hash_values_equal,
        "proxy_coordinate_field_equality": proxy_equal,
        "proxy_coordinate_fields_unchanged": all(proxy_equal.values()),
        "full_candidate_tensor_mutation_proven_absent": tensor_hash_values_equal,
        "interpretation": (
            "Selector equivalence and proxy coordinate equality prove the logged "
            "selector inputs stayed unchanged in the paired diagnostic smoke, but "
            "they do not prove full raw candidate tensor immutability without a "
            "candidate tensor hash or full tensor artifact."
        ),
    }


def _source_shape_checks(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check("baseline_records_present", baseline["records"] > 0),
        _check("candidate_records_present", candidate["records"] > 0),
        _check("record_counts_match", baseline["records"] == candidate["records"]),
        _check("baseline_selected_index_range", baseline["selected_index_all_in_range"]),
        _check("candidate_selected_index_range", candidate["selected_index_all_in_range"]),
        _check(
            "baseline_required_candidate_fields_present",
            baseline["required_candidate_fields_present"],
        ),
        _check(
            "candidate_required_candidate_fields_present",
            candidate["required_candidate_fields_present"],
        ),
        _check("baseline_field_lengths_match", not baseline["field_length_mismatches"]),
        _check("candidate_field_lengths_match", not candidate["field_length_mismatches"]),
        _check(
            "candidate_count_values_match",
            baseline["candidate_count_values"] == candidate["candidate_count_values"],
        ),
    ]


def _selector_checks(selector: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("selector_equivalent", selector["equivalent"]),
        _check("selector_records_present", (selector["records"] or 0) > 0),
        _check("selector_required_exact_zero", selector["required_exact_mismatch_total"] == 0),
        _check("selector_required_numeric_zero", selector["required_numeric_mismatch_total"] == 0),
        _check(
            "selector_required_numeric_shape_zero",
            selector["required_numeric_shape_mismatch_total"] == 0,
        ),
        _check(
            "selector_required_numeric_nonexact_zero",
            selector["required_numeric_nonexact_total"] == 0,
        ),
    ]


def _payload_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("payload_passed", payload["passed"]),
        _check("payload_records_present", (payload["records"] or 0) > 0),
        _check("payload_available_records_present", (payload["available_payload_records"] or 0) > 0),
        _check("payload_invalid_records_zero", payload["invalid_payload_records"] == 0),
        _check("payload_no_future_outcome_labels", not payload["future_outcome_labels_used"]),
        _check("payload_no_blocked_authorizations", not payload["blocked_action_conflicts"]),
    ]


def _dataset_checks(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("dataset_passed", dataset["passed"]),
        _check("dataset_finite_candidate_contract", dataset["finite_candidate_contract_verified"]),
        _check("dataset_closed_loop_outcomes_forbidden", dataset["closed_loop_outcomes_forbidden"]),
        _check("dataset_closed_loop_outcome_records_zero", dataset["closed_loop_outcome_records"] == 0),
        _check("dataset_forbidden_seed_check", dataset["forbidden_seed_check"]),
    ]


def _replay_checks(replay: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("replay_num_candidates_match", replay["num_candidates_match"]),
        _check("replay_finite_candidate_contract_present", replay["finite_candidate_contract_present"]),
        _check("replay_score_affine_contract", replay["score_contract"] == "a_ik^T w"),
        _check("replay_no_camp_score_change", not any(replay["changes_camp_score_values"])),
        _check("replay_no_dp_weight_change", not any(replay["changes_dp_weights_values"])),
    ]


def _oracle_checks(oracle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("oracle_opportunity_gate_passed", oracle["opportunity_gate_passed"]),
        _check("oracle_no_future_outcome_leakage_flag", not oracle["future_outcome_leakage"]),
        _check("oracle_no_training", not oracle["training"]),
        _check("oracle_no_online_selector_change", not oracle["online_selector_change"]),
    ]


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_plan_passed", design["passed"]),
        _check(
            "design_plan_authorizes_this_audit",
            design["authorized_next_work"]
            == "dp_native_candidate_reranking_fixed_artifact_evidence_audit_only",
        ),
        _check("design_route_dp_native", design["route"] == "dp_native_candidate_reranking_only"),
        _check("design_no_candidate_generation", not design["candidate_generation_authorized"]),
        _check("design_no_trajectory_rewrite", not design["trajectory_rewrite_authorized"]),
        _check("design_no_candidate_tensor_mutation", not design["candidate_tensor_mutation_authorized"]),
    ]


def _evidence_gaps(
    *,
    provenance: dict[str, Any],
    mutation: dict[str, Any],
) -> list[str]:
    gaps: list[str] = []
    if not provenance["candidate_tensor_hash_present"]:
        gaps.append("candidate_tensor_hash_missing")
    if not provenance["full_candidate_coordinate_tensor_present"]:
        gaps.append("full_candidate_coordinate_tensor_artifact_missing")
    if any(provenance["changes_candidate_set_values"]):
        gaps.append("raw_dp_pre_camp_candidate_set_immutability_not_proven")
    if any(provenance["reference_blend_selection_effect_values"]):
        gaps.append("reference_blend_selection_effect_requires_provenance_separation")
    if not mutation["full_candidate_tensor_mutation_proven_absent"]:
        gaps.append("full_candidate_tensor_mutation_absence_not_proven")
    return gaps


def _weak_evidence(
    *,
    provenance: dict[str, Any],
    mutation: dict[str, Any],
) -> list[str]:
    weak: list[str] = []
    if (
        provenance["finite_candidate_contract_present"]
        and not provenance["candidate_tensor_hash_present"]
    ):
        weak.append(
            "finite_candidate_contract_names_the_boundary_but_is_not_a_tensor_hash"
        )
    if (
        mutation["proxy_coordinate_fields_unchanged"]
        and not mutation["full_candidate_tensor_mutation_proven_absent"]
    ):
        weak.append(
            "proxy_coordinate_fields_match_but_do_not_cover_full_candidate_tensor"
        )
    return weak


def _final_decision(
    *,
    audit_complete: bool,
    evidence_ready: bool,
    gaps: list[str],
    weak: list[str],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    status = COMPLETE_STATUS if audit_complete else REJECT_STATUS
    next_work = READY_NEXT_WORK if evidence_ready else GAP_NEXT_WORK
    return {
        "status": status,
        "passed": audit_complete,
        "evidence_audit_complete": audit_complete,
        "dp_native_reranking_evidence_ready": evidence_ready,
        "candidate_tensor_provenance_gap": bool(gaps),
        "failed_checks": failed,
        "evidence_gaps": gaps,
        "weak_evidence": weak,
        "authorized_next_work": next_work if audit_complete else None,
        "provenance_gap_design_plan_authorized": audit_complete and bool(gaps),
        "static_selector_contract_plan_authorized": evidence_ready,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _find_key_fragments(value: Any, fragments: tuple[str, ...], prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            key_lower = str(key).lower()
            if any(fragment in key_lower for fragment in fragments):
                hits.append(path)
            hits.extend(_find_key_fragments(nested, fragments, path))
    elif isinstance(value, list):
        for index, item in enumerate(value[:5]):
            hits.extend(_find_key_fragments(item, fragments, f"{prefix}[{index}]"))
    return hits


def _find_key_fragment_values(value: Any, fragments: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_lower = str(key).lower()
            if any(fragment in key_lower for fragment in fragments):
                values.append(nested)
            values.extend(_find_key_fragment_values(nested, fragments))
    elif isinstance(value, list):
        for item in value:
            values.extend(_find_key_fragment_values(item, fragments))
    return values


def _field_values(records: list[Any], field: str) -> list[Any]:
    return [_dict(record).get(field) for record in records]


def _sum_selected(values: dict[str, Any], keys: tuple[str, ...]) -> int:
    total = 0
    for key in keys:
        value = values.get(key, 0)
        if isinstance(value, dict):
            total += _sum_nested_ints(value)
        else:
            total += int(value or 0)
    return total


def _sum_nested_ints(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_sum_nested_ints(item) for item in value.values())
    if isinstance(value, list):
        return sum(_sum_nested_ints(item) for item in value)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _source_hashes(paths: dict[str, str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, path_str in paths.items():
        path = Path(path_str)
        if path.exists() and path.is_file():
            hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            hashes[key] = "missing"
    return hashes


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_list(path: Path) -> list[Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return payload


def _git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
