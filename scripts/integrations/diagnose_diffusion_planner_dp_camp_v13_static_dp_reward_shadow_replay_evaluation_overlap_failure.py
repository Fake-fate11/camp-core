#!/usr/bin/env python3
"""Diagnose v13 static DP-reward shadow replay evaluation overlap failures.

This tool is read-only. It explains a rejected result-readiness artifact whose
evaluation candidate tensors overlap prior training-summary selection logs. It
does not run replay, generate candidates, train CAMP, modify Diffusion Planner,
promote artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "overlap_failure_diagnosis_v1"
)
DIAGNOSED_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "overlap_failure_diagnosed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "overlap_failure_diagnosis_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_only"
)
OVERLAP_FAILED_CHECK = "candidate_tensor_overlap_rate_within_limit"
ROUTE_NAMES = frozenset(
    {
        "nishi_lane_change",
        "nishi_release",
        "sample_normal",
        "sample_tl",
    }
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only diagnosis for a rejected v13 static DP-reward shadow "
            "replay evaluation result-readiness artifact."
        )
    )
    parser.add_argument("--evaluation_output_dir", type=Path, required=True)
    parser.add_argument("--result_readiness_json", type=Path, required=True)
    parser.add_argument("--previous_training_summary_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evaluation_output_dir=args.evaluation_output_dir,
        result_readiness_json=args.result_readiness_json,
        previous_training_summary_json=args.previous_training_summary_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_records=args.expected_records,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evaluation_output_dir: Path,
    result_readiness_json: Path,
    previous_training_summary_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_selection_log_count: int = 32,
    expected_records: int = 3200,
) -> dict[str, Any]:
    evaluation_output_dir = evaluation_output_dir.resolve()
    result_readiness_json = result_readiness_json.resolve()
    previous_training_summary_json = previous_training_summary_json.resolve()
    v13_audit_md = v13_audit_md.resolve()

    result_readiness = _load_json_dict(result_readiness_json)
    training_summary = _load_json_dict(previous_training_summary_json)
    audit_text = _read_text(v13_audit_md)
    evaluation_logs = sorted(evaluation_output_dir.rglob("camp_selection_log.json"))
    previous_logs = [Path(path) for path in training_summary.get("selection_logs", [])]

    eval_records = _records_by_hash(evaluation_logs)
    previous_records = _records_by_hash(previous_logs)
    previous_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in previous_records:
        previous_by_hash[record["hash"]].append(record)

    matched_eval_records = 0
    same_signature_step_matches = 0
    match_reference_roots: Counter[str] = Counter()
    match_unique_roots: Counter[str] = Counter()
    match_same_signature_step_roots: Counter[str] = Counter()
    duplicate_entry_distribution: Counter[int] = Counter()
    matched_signatures: set[str] = set()

    for record in eval_records:
        entries = previous_by_hash.get(record["hash"], [])
        if not entries:
            continue
        matched_eval_records += 1
        duplicate_entry_distribution[len(entries)] += 1
        roots_for_record = {entry["source_root"] for entry in entries}
        for root in roots_for_record:
            match_unique_roots[root] += 1
        for entry in entries:
            match_reference_roots[entry["source_root"]] += 1
            same_signature_step = (
                entry["signature"] == record["signature"]
                and entry["record_index"] == record["record_index"]
            )
            if same_signature_step:
                same_signature_step_matches += 1
                matched_signatures.add(record["signature"])
                match_same_signature_step_roots[entry["source_root"]] += 1

    eval_signatures = {path_signature(path) for path in evaluation_logs}
    previous_signatures = {path_signature(path) for path in previous_logs}
    signature_intersection = eval_signatures.intersection(previous_signatures)

    result_overlap = _dict(result_readiness.get("candidate_tensor_overlap"))
    final_review = _dict(result_readiness.get("final_decision"))
    checks = _checks(
        evaluation_output_dir=evaluation_output_dir,
        result_readiness_json=result_readiness_json,
        previous_training_summary_json=previous_training_summary_json,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        result_readiness=result_readiness,
        training_summary=training_summary,
        evaluation_logs=evaluation_logs,
        previous_logs=previous_logs,
        eval_records=eval_records,
        previous_records=previous_records,
        matched_eval_records=matched_eval_records,
        same_signature_step_matches=same_signature_step_matches,
        signature_intersection=signature_intersection,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        expected_selection_log_count=expected_selection_log_count,
        expected_records=expected_records,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    diagnosis = {
        "failure_class": (
            "training_summary_includes_prior_evaluation_replay_logs_reused_by_"
            "current_evaluation"
        ),
        "primary_cause": (
            "current evaluation candidate tensors are a rerun of selection-log "
            "signatures and candidate hashes already referenced by the prior "
            "training summary"
        ),
        "training_summary_selection_logs_are_prior_training_evidence": True,
        "current_evaluation_is_not_independent_holdout": True,
        "nonoverlap_data_required_before_training_preflight": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "inputs": {
            "evaluation_output_dir": str(evaluation_output_dir),
            "result_readiness_json": str(result_readiness_json),
            "previous_training_summary_json": str(previous_training_summary_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "result_readiness": {
            "status": final_review.get("status"),
            "passed": final_review.get("passed"),
            "failed_checks": final_review.get("failed_checks"),
            "overlap": result_overlap,
        },
        "path_provenance": {
            "evaluation_selection_log_count": len(evaluation_logs),
            "previous_training_summary_selection_log_count": len(previous_logs),
            "evaluation_source_roots": _counter(evaluation_logs, source_root),
            "previous_source_roots": _counter(previous_logs, source_root),
            "evaluation_signature_count": len(eval_signatures),
            "previous_signature_count": len(previous_signatures),
            "evaluation_signatures_in_previous_count": len(signature_intersection),
            "evaluation_signatures_missing_in_previous_count": len(
                eval_signatures - previous_signatures
            ),
        },
        "hash_provenance": {
            "evaluation_record_count": len(eval_records),
            "previous_record_count": len(previous_records),
            "evaluation_unique_hash_count": len({record["hash"] for record in eval_records}),
            "previous_unique_hash_count": len({record["hash"] for record in previous_records}),
            "matched_evaluation_record_count": matched_eval_records,
            "matched_evaluation_record_rate": (
                float(matched_eval_records / len(eval_records)) if eval_records else 0.0
            ),
            "same_signature_and_step_hash_match_records": same_signature_step_matches,
            "same_signature_and_step_hash_match_rate": (
                float(same_signature_step_matches / len(eval_records)) if eval_records else 0.0
            ),
            "same_signature_and_step_matched_signature_count": len(matched_signatures),
            "match_reference_count_by_previous_source_root": dict(match_reference_roots),
            "match_unique_eval_records_by_previous_source_root": dict(match_unique_roots),
            "same_signature_and_step_matches_by_previous_source_root": dict(
                match_same_signature_step_roots
            ),
            "duplicate_previous_hash_entry_distribution": {
                str(key): value for key, value in sorted(duplicate_entry_distribution.items())
            },
        },
        "diagnosis": diagnosis,
        "review_checks": checks,
        "final_decision": {
            "status": DIAGNOSED_STATUS if passed else f"{DIAGNOSED_STATUS}_incomplete",
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "training_executed": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "next_gate_is_plan_only": passed,
        },
    }


def _checks(
    *,
    evaluation_output_dir: Path,
    result_readiness_json: Path,
    previous_training_summary_json: Path,
    v13_audit_md: Path,
    audit_text: str,
    result_readiness: dict[str, Any],
    training_summary: dict[str, Any],
    evaluation_logs: list[Path],
    previous_logs: list[Path],
    eval_records: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
    matched_eval_records: int,
    same_signature_step_matches: int,
    signature_intersection: set[str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    expected_selection_log_count: int,
    expected_records: int,
) -> list[dict[str, Any]]:
    final_review = _dict(result_readiness.get("final_decision"))
    overlap = _dict(result_readiness.get("candidate_tensor_overlap"))
    failed_checks = final_review.get("failed_checks") or []
    return [
        _check("evaluation_output_dir_exists", evaluation_output_dir.is_dir(), str(evaluation_output_dir), "directory exists"),
        _check("result_readiness_json_exists", result_readiness_json.is_file(), str(result_readiness_json), "file exists"),
        _check("previous_training_summary_json_exists", previous_training_summary_json.is_file(), str(previous_training_summary_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("result_readiness_rejected", final_review.get("passed") is False, final_review.get("passed"), False),
        _check("result_readiness_overlap_check_failed", OVERLAP_FAILED_CHECK in failed_checks, failed_checks, f"contains {OVERLAP_FAILED_CHECK}"),
        _check("result_overlap_rate_is_full", overlap.get("eval_hashes_in_previous_rate") == 1.0, overlap.get("eval_hashes_in_previous_rate"), 1.0),
        _expect("evaluation_selection_log_count", len(evaluation_logs), expected_selection_log_count),
        _expect("evaluation_record_count", len(eval_records), expected_records),
        _check("previous_training_summary_has_selection_logs", bool(training_summary.get("selection_logs")), len(training_summary.get("selection_logs", [])), "> 0"),
        _check("previous_records_present", len(previous_records) > 0, len(previous_records), "> 0"),
        _check("all_eval_log_signatures_in_previous", len(signature_intersection) == len({path_signature(path) for path in evaluation_logs}), len(signature_intersection), len({path_signature(path) for path in evaluation_logs})),
        _expect("matched_evaluation_record_count", matched_eval_records, expected_records),
        _expect("same_signature_and_step_hash_match_records", same_signature_step_matches, expected_records),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    path = report["path_provenance"]
    hashes = report["hash_provenance"]
    diagnosis = report["diagnosis"]
    return "\n".join(
        [
            "# V13 Static DP-Reward Shadow Replay Overlap Failure Diagnosis",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed diagnosis gate: `{decision['passed']}`",
            f"- Failure class: `{diagnosis['failure_class']}`",
            f"- Evaluation logs: `{path['evaluation_selection_log_count']}`",
            f"- Prior training summary logs: `{path['previous_training_summary_selection_log_count']}`",
            f"- Evaluation signatures in previous logs: `{path['evaluation_signatures_in_previous_count']}`",
            f"- Matched evaluation records: `{hashes['matched_evaluation_record_count']}`",
            f"- Same signature and step hash matches: `{hashes['same_signature_and_step_hash_match_records']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "This diagnosis is read-only evidence. It does not run replay, generate candidates, train CAMP, modify DP, promote selectors or atoms, deploy, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _records_by_hash(log_paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = _load_json_list(log_path)
        root = source_root(log_path)
        signature = path_signature(log_path)
        for record_index, row in enumerate(rows):
            value = candidate_tensor_hash(row)
            if not value:
                continue
            records.append(
                {
                    "hash": value,
                    "log_path": str(log_path),
                    "source_root": root,
                    "signature": signature,
                    "record_index": record_index,
                }
            )
    return records


def source_root(path: Path) -> str:
    parts = path.parts
    index = _route_index(parts)
    if index is None:
        return str(path.parent)
    return str(Path(*parts[:index]))


def path_signature(path: Path) -> str:
    parts = path.parts
    index = _route_index(parts)
    if index is None:
        return str(path)
    return "/".join(parts[index:])


def _route_index(parts: tuple[str, ...]) -> int | None:
    for index, value in enumerate(parts):
        if value in ROUTE_NAMES:
            return index
    return None


def candidate_tensor_hash(record: dict[str, Any]) -> str | None:
    selector = _dict(record.get("default_off_shadow_selector"))
    value = _dict(selector.get("candidate_tensor_hash")).get("sha256")
    return value if isinstance(value, str) and len(value) == 64 else None


def _counter(paths: list[Path], fn: Any) -> dict[str, int]:
    return dict(Counter(fn(path) for path in paths))


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list: {path}")
    return [row for row in data if isinstance(row, dict)]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
