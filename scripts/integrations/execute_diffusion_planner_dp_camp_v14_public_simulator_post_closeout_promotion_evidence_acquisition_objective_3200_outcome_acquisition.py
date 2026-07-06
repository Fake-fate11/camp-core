#!/usr/bin/env python3
"""Execute or locate objective-3200 shadow-selected outcome acquisition.

This gate consumes the audited objective-3200 preflight static review and a
candidate outcome source root. It verifies that every fixed-DP runtime record
has a paired per-record shadow-selected closed-loop outcome. It does not modify
Diffusion Planner, generate or edit trajectories, train, promote, deploy, enable
an online selector, or make any safety/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_outcome_acquisition_"
        "preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_source_static_review_module()
PREFLIGHT_MODULE = SOURCE_STATIC_REVIEW_MODULE.PREFLIGHT_MODULE

FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_STATIC_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATIC_REVIEW_SCHEMA = SOURCE_STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_STATIC_REVIEW_MD_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_MD_NAME
BLOCKED_ACTIONS = SOURCE_STATIC_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_STATIC_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_acquisition_execution_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_failed"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_result_review_only"
)
FAILED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_execution_failed_user_decision_required"
)

EXECUTION_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution.json"
)
EXECUTION_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution.md"
)

OBJECTIVE_REQUIRED_RECORDS = PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = 32
FORMAL_SEEDS = {11, 12, 13}
FULL36_MARKERS = ("full36", "formal36", "full_36")
BLOCKED_ANALYSIS_FLAGS = (
    "replay_execution",
    "training_execution",
    "candidate_generation",
    "dp_modification",
    "candidate_tensor_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_execution_dir", type=Path, required=True)
    parser.add_argument("--candidate_outcome_source_root", type=Path, required=True)
    parser.add_argument("--candidate_outcome_source_artifact_dir", type=Path, default=None)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument("--expected_selection_log_count", type=int, default=EXPECTED_SELECTION_LOG_COUNT)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_preflight_static_review_artifact_dir=args.source_preflight_static_review_artifact_dir,
        source_preflight_static_review_json=args.source_preflight_static_review_json,
        source_preflight_static_review_md=args.source_preflight_static_review_md,
        source_preflight_static_review_sha256s=args.source_preflight_static_review_sha256s,
        runtime_execution_dir=args.runtime_execution_dir,
        candidate_outcome_source_root=args.candidate_outcome_source_root,
        candidate_outcome_source_artifact_dir=args.candidate_outcome_source_artifact_dir,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_selection_log_count=args.expected_selection_log_count,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_static_review_json: Path,
    source_preflight_static_review_md: Path,
    source_preflight_static_review_sha256s: Path,
    runtime_execution_dir: Path,
    candidate_outcome_source_root: Path,
    candidate_outcome_source_artifact_dir: Path | None,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    expected_selection_log_count: int = EXPECTED_SELECTION_LOG_COUNT,
    enabled: bool = False,
) -> dict[str, Any]:
    source_artifact_dir = source_preflight_static_review_artifact_dir.resolve()
    runtime_root = runtime_execution_dir.resolve()
    outcome_root = candidate_outcome_source_root.resolve()
    outcome_artifact_dir = candidate_outcome_source_artifact_dir.resolve() if candidate_outcome_source_artifact_dir else None
    paths = {
        "source_preflight_static_review_json": source_preflight_static_review_json.resolve(),
        "source_preflight_static_review_md": source_preflight_static_review_md.resolve(),
        "source_preflight_static_review_sha256s": source_preflight_static_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "heads": source_artifact_dir / "HEADS",
        "command": source_artifact_dir / "COMMAND",
        "stdout": source_artifact_dir / "stdout",
        "stderr": source_artifact_dir / "stderr",
        "run_exit": source_artifact_dir / "run.exit",
        "root_sha256s": source_artifact_dir / "SHA256SUMS",
        "review_json": source_artifact_dir / "review" / SOURCE_STATIC_REVIEW_JSON_NAME,
        "review_md": source_artifact_dir / "review" / SOURCE_STATIC_REVIEW_MD_NAME,
        "review_sha256s": source_artifact_dir / "review" / "SHA256SUMS",
    }
    source_review = _read_json_dict(paths["source_preflight_static_review_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["source_preflight_static_review_sha256s"])
    run_exit = _read_text(artifact_files["run_exit"]).strip()

    runtime = _source_root_summary(runtime_root, expected_record_count=expected_record_count)
    candidate = _source_root_summary(outcome_root, expected_record_count=expected_record_count)
    acquisition = _acquisition_summary(
        runtime=runtime,
        candidate=candidate,
        expected_record_count=expected_record_count,
    )
    source_summary = _source_static_review_summary(source_review)
    checks = _checks(
        enabled=enabled,
        source_artifact_dir=source_artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_review=source_review,
        source_summary=source_summary,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
        runtime=runtime,
        candidate=candidate,
        acquisition=acquisition,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "objective_3200_outcome_acquisition_execution": True,
            "outcome_acquisition_attempted_by_this_gate": True,
            "outcome_acquisition_satisfied": passed,
            "read_only_existing_candidate_outcome_source": True,
            "closed_loop_outcomes_training_or_online_input": False,
            "score_expression": SCORE_EXPRESSION,
            **{flag: False for flag in BLOCKED_ANALYSIS_FLAGS},
        },
        "inputs": {
            "source_preflight_static_review_artifact_dir": str(source_artifact_dir),
            "runtime_execution_dir": str(runtime_root),
            "candidate_outcome_source_root": str(outcome_root),
            "candidate_outcome_source_artifact_dir": str(outcome_artifact_dir) if outcome_artifact_dir else None,
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_preflight_static_review_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_preflight_static_review_camp_origin_main": _kv(
                heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_preflight_static_review_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=source_artifact_dir,
            review_json=paths["source_preflight_static_review_json"],
            review_md=paths["source_preflight_static_review_md"],
            review_sha256s=paths["source_preflight_static_review_sha256s"],
        ),
        "source_preflight_static_review_summary": source_summary,
        "runtime_record_source_summary": runtime,
        "candidate_outcome_source_summary": candidate,
        "objective_3200_outcome_acquisition_summary": acquisition,
        "no_go_report": _no_go_report(runtime=runtime, candidate=candidate, acquisition=acquisition),
        "execution_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, acquisition=acquisition),
    }


def _checks(
    *,
    enabled: bool,
    source_artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
    runtime: dict[str, Any],
    candidate: dict[str, Any],
    acquisition: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    analysis = _dict(source_review.get("analysis"))
    checks: list[dict[str, Any]] = [
        _expect("execution_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_artifact_dir_exists", source_artifact_dir.is_dir(), str(source_artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(
        [
            _expect("source_artifact_run_exit", run_exit, "0"),
            _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
            _expect("source_static_review_passed", decision.get("passed"), True),
            _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
            _expect("source_static_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_static_review_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
            _expect(
                "source_static_review_camp_head_matches_origin",
                _kv(heads, "CAMP_HEAD", "camp_head"),
                _kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
            ),
            _expect("source_static_review_static_review_only", analysis.get("static_review_only"), True),
            _expect("source_static_review_outcome_acquisition_executed", analysis.get("outcome_acquisition_executed"), False),
            _expect("source_static_review_dp_modification", analysis.get("dp_modification"), False),
            _expect("source_static_review_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("source_objective_required_records", source_summary["objective_required_records"], expected_record_count),
            _expect("source_runtime_record_count", source_summary["runtime_record_count"], expected_record_count),
            _expect("source_candidate_closed_loop_outcome_records", source_summary["candidate_closed_loop_outcome_records"], 0),
            _expect(
                "source_missing_candidate_closed_loop_outcome_records",
                source_summary["missing_candidate_closed_loop_outcome_records"],
                expected_record_count,
            ),
        ]
    )
    checks.extend(
        _sha_checks(
            root_sha256s=root_sha256s,
            nested_sha256s=nested_sha256s,
            json_path=paths["source_preflight_static_review_json"],
            md_path=paths["source_preflight_static_review_md"],
            sha256s_path=paths["source_preflight_static_review_sha256s"],
        )
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_{flag}", decision.get(flag), False))
    checks.extend(
        [
            _check("runtime_execution_dir_exists", Path(runtime["root"]).is_dir(), runtime["root"], "directory"),
            _check("candidate_outcome_source_root_exists", Path(candidate["root"]).is_dir(), candidate["root"], "directory"),
            _expect("runtime_selection_log_count", runtime["selection_log_count"], expected_selection_log_count),
            _expect("runtime_record_count", runtime["record_count"], expected_record_count),
            _expect("runtime_candidate_closed_loop_outcome_records", runtime["candidate_closed_loop_outcome_records"], 0),
            _expect("runtime_formal_seed_records", runtime["formal_seed_records"], 0),
            _expect("runtime_full36_path_records", runtime["full36_path_records"], 0),
            _expect("runtime_candidate_tensor_mutation_records", runtime["candidate_tensor_mutation_records"], 0),
            _expect("runtime_closed_loop_outcomes_training_or_online_input_records", runtime["closed_loop_training_or_online_input_records"], 0),
            _expect("candidate_selection_log_count", candidate["selection_log_count"], expected_selection_log_count),
            _expect("candidate_record_count", candidate["record_count"], expected_record_count),
            _expect("candidate_outcome_record_count", candidate["candidate_closed_loop_outcome_records"], expected_record_count),
            _expect("candidate_missing_outcome_record_count", candidate["missing_candidate_closed_loop_outcome_records"], 0),
            _expect("candidate_formal_seed_records", candidate["formal_seed_records"], 0),
            _expect("candidate_full36_path_records", candidate["full36_path_records"], 0),
            _expect("candidate_tensor_mutation_records", candidate["candidate_tensor_mutation_records"], 0),
            _expect("candidate_closed_loop_outcomes_training_or_online_input_records", candidate["closed_loop_training_or_online_input_records"], 0),
            _expect("candidate_reference_blend_records", candidate["reference_blend_records"], 0),
            _expect("candidate_non_affine_score_records", candidate["non_affine_score_records"], 0),
            _expect("candidate_non_simplex_weight_records", candidate["non_simplex_weight_records"], 0),
            _expect("paired_record_key_count", acquisition["paired_record_key_count"], expected_record_count),
            _expect("unpaired_runtime_record_key_count", acquisition["unpaired_runtime_record_key_count"], 0),
            _expect("unpaired_candidate_record_key_count", acquisition["unpaired_candidate_record_key_count"], 0),
            _expect("objective_3200_outcome_acquisition_satisfied", acquisition["objective_3200_outcome_acquisition_satisfied"], True),
        ]
    )
    return checks


def _source_root_summary(root: Path, *, expected_record_count: int) -> dict[str, Any]:
    logs = sorted(root.rglob("camp_selection_log.json")) if root.is_dir() else []
    summaries = sorted(root.rglob("camp_validation_summary.json")) if root.is_dir() else []
    counters: Counter[str] = Counter()
    keys: set[str] = set()
    duplicate_keys = 0
    missing_examples: list[dict[str, Any]] = []
    tensor_hashes: Counter[str] = Counter()
    for log in logs:
        rows = _records_from_payload(_read_json(log))
        seed = _seed_from_path(log)
        formal = seed in FORMAL_SEEDS
        full36 = _path_has_any_marker(log, FULL36_MARKERS)
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            counters["record_count"] += 1
            key = _record_key(root, log, row, index)
            if key in keys:
                duplicate_keys += 1
            keys.add(key)
            if formal:
                counters["formal_seed_records"] += 1
            if full36:
                counters["full36_path_records"] += 1
            closed_loop = row.get("candidate_closed_loop_outcomes")
            if isinstance(closed_loop, list) and closed_loop:
                counters["candidate_closed_loop_outcome_records"] += 1
            else:
                counters["missing_candidate_closed_loop_outcome_records"] += 1
                if len(missing_examples) < 5:
                    missing_examples.append({"log": str(log), "record_index": index, "key": key})
            _record_candidate_boundary(row, counters, tensor_hashes)
    return {
        "root": str(root),
        "selection_log_count": len(logs),
        "validation_summary_count": len(summaries),
        "record_count": counters["record_count"],
        "unique_record_key_count": len(keys),
        "duplicate_record_key_count": duplicate_keys,
        "record_key_sha256": hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest(),
        "candidate_closed_loop_outcome_records": counters["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": counters["missing_candidate_closed_loop_outcome_records"],
        "expected_record_count": expected_record_count,
        "formal_seed_records": counters["formal_seed_records"],
        "full36_path_records": counters["full36_path_records"],
        "candidate_tensor_mutation_records": counters["candidate_tensor_mutation_records"],
        "reference_blend_records": counters["reference_blend_records"],
        "closed_loop_training_or_online_input_records": counters["closed_loop_training_or_online_input_records"],
        "non_affine_score_records": counters["non_affine_score_records"],
        "non_simplex_weight_records": counters["non_simplex_weight_records"],
        "unique_candidate_tensor_hash_count": len(tensor_hashes),
        "candidate_tensor_hash_preview": sorted(tensor_hashes)[:10],
        "missing_candidate_closed_loop_outcome_examples": missing_examples,
        "record_keys": sorted(keys),
    }


def _record_candidate_boundary(row: dict[str, Any], counters: Counter[str], tensor_hashes: Counter[str]) -> None:
    selector = _dict(row.get("default_off_shadow_selector"))
    provenance = _dict(row.get("camp_candidate_tensor_provenance"))
    selector_hash = _dict(selector.get("candidate_tensor_hash"))
    pre_hash = _dict(provenance.get("pre_camp_scoring_tensor"))
    post_hash = _dict(provenance.get("post_camp_selector_tensor"))
    hashes = [value for value in (selector_hash.get("sha256"), pre_hash.get("sha256"), post_hash.get("sha256")) if value]
    if hashes:
        for value in hashes:
            tensor_hashes[str(value)] += 1
        if len(set(hashes)) > 1:
            counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("candidate_tensor_mutation_effect") is True or provenance.get("pre_post_tensor_hash_equal") is False:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("reference_blend_present") is True or row.get("candidate_reference_blend_steps") not in (0, None):
        counters["reference_blend_records"] += 1
    if provenance.get("outcome_label_input") is True or provenance.get("closed_loop_outcome_fields_read") is True:
        counters["closed_loop_training_or_online_input_records"] += 1
    if selector and selector.get("score_expression") != SCORE_EXPRESSION:
        counters["non_affine_score_records"] += 1
    weights = row.get("weights", row.get("selection_weights"))
    if isinstance(weights, list) and weights:
        values = [_number_or_none(value) for value in weights]
        if any(value is None or value < -1e-9 for value in values):
            counters["non_simplex_weight_records"] += 1
        elif not math.isclose(sum(value for value in values if value is not None), 1.0, rel_tol=1e-6, abs_tol=1e-6):
            counters["non_simplex_weight_records"] += 1


def _acquisition_summary(
    *,
    runtime: dict[str, Any],
    candidate: dict[str, Any],
    expected_record_count: int,
) -> dict[str, Any]:
    runtime_keys = set(runtime["record_keys"])
    candidate_keys = set(candidate["record_keys"])
    paired = sorted(runtime_keys & candidate_keys)
    unpaired_runtime = sorted(runtime_keys - candidate_keys)
    unpaired_candidate = sorted(candidate_keys - runtime_keys)
    satisfied = (
        runtime["record_count"] == expected_record_count
        and candidate["record_count"] == expected_record_count
        and candidate["candidate_closed_loop_outcome_records"] == expected_record_count
        and candidate["missing_candidate_closed_loop_outcome_records"] == 0
        and len(paired) == expected_record_count
        and not unpaired_runtime
        and not unpaired_candidate
    )
    return {
        "objective_required_records": expected_record_count,
        "runtime_record_count": runtime["record_count"],
        "candidate_source_record_count": candidate["record_count"],
        "candidate_closed_loop_outcome_records": candidate["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": candidate["missing_candidate_closed_loop_outcome_records"],
        "paired_record_key_count": len(paired),
        "paired_record_key_sha256": hashlib.sha256("\n".join(paired).encode("utf-8")).hexdigest(),
        "unpaired_runtime_record_key_count": len(unpaired_runtime),
        "unpaired_candidate_record_key_count": len(unpaired_candidate),
        "unpaired_runtime_record_key_preview": unpaired_runtime[:10],
        "unpaired_candidate_record_key_preview": unpaired_candidate[:10],
        "objective_3200_outcome_acquisition_satisfied": satisfied,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "safetycost_v1_materialization_required_next": bool(satisfied),
    }


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    source = _dict(source_review.get("source_preflight_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": int(
            decision.get("objective_required_records") or source.get("objective_required_records") or 0
        ),
        "runtime_record_count": int(decision.get("runtime_record_count") or source.get("runtime_record_count") or 0),
        "candidate_closed_loop_outcome_records": int(
            decision.get("candidate_closed_loop_outcome_records")
            or source.get("candidate_closed_loop_outcome_records")
            or 0
        ),
        "missing_candidate_closed_loop_outcome_records": int(
            decision.get("missing_candidate_closed_loop_outcome_records")
            or source.get("missing_candidate_closed_loop_outcome_records")
            or 0
        ),
    }


def _no_go_report(*, runtime: dict[str, Any], candidate: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    failures = []
    if candidate["candidate_closed_loop_outcome_records"] != acquisition["objective_required_records"]:
        failures.append("candidate_closed_loop_outcome_records_missing")
    if acquisition["unpaired_runtime_record_key_count"] or acquisition["unpaired_candidate_record_key_count"]:
        failures.append("strict_pairing_key_mismatch")
    for label, summary in (("runtime", runtime), ("candidate", candidate)):
        for key in (
            "formal_seed_records",
            "full36_path_records",
            "candidate_tensor_mutation_records",
            "reference_blend_records",
            "closed_loop_training_or_online_input_records",
            "non_affine_score_records",
            "non_simplex_weight_records",
        ):
            if summary.get(key):
                failures.append(f"{label}_{key}")
    return {
        "entries": [
            "candidate_closed_loop_outcome_records_missing",
            "strict_pairing_key_mismatch",
            "fixed_dp_head_drift",
            "candidate_tensor_identity_missing_or_mutated",
            "reference_blend_or_trajectory_edit",
            "full36_or_formal_seed_11_12_13_present",
            "closed_loop_outcome_training_or_online_input",
            "non_affine_score_or_non_simplex_weight",
            "promotion_deployment_online_selector_or_claim",
        ],
        "failures": sorted(set(failures)),
        "failed_count": len(set(failures)),
        "promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_or_camp_over_dp_claim_authorized": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], acquisition: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_enabled" in failed:
        failure_class = "explicit_objective_3200_outcome_acquisition_execution_authorization_missing"
    elif "audit_latest_next_work" in failed or "status_doc_latest_next_work" in failed:
        failure_class = "v14_eof_contract_mismatch"
    elif "current_dp_head_fixed" in failed or "source_static_review_dp_head_fixed" in failed:
        failure_class = "fixed_dp_head_drift"
    elif "candidate_outcome_record_count" in failed or "candidate_missing_outcome_record_count" in failed:
        failure_class = "objective_3200_outcome_acquisition_execution_source_missing"
    else:
        failure_class = "objective_3200_outcome_acquisition_execution_contract_failure"
    return {
        "passed": passed,
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_next_work": AUTHORIZED_NEXT_WORK if passed else FAILED_NEXT_WORK,
        "objective_required_records": acquisition["objective_required_records"],
        "runtime_record_count": acquisition["runtime_record_count"],
        "candidate_closed_loop_outcome_records": acquisition["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": acquisition["missing_candidate_closed_loop_outcome_records"],
        "paired_record_key_count": acquisition["paired_record_key_count"],
        "objective_3200_outcome_acquisition_execution_passed": passed,
        "objective_3200_outcome_acquisition_satisfied": acquisition["objective_3200_outcome_acquisition_satisfied"],
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "outcome_acquisition_executed_by_this_gate": True,
        "replay_executed_by_this_gate": False,
        "training_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / EXECUTION_JSON_NAME
    md_path = output_dir / EXECUTION_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            [
                f"{_sha256(json_path)}  {json_path.name}",
                f"{_sha256(md_path)}  {md_path.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    acquisition = report["objective_3200_outcome_acquisition_summary"]
    no_go = report["no_go_report"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Acquisition Execution",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
            f"- Runtime records: `{acquisition['runtime_record_count']}`",
            f"- Candidate outcome records: `{acquisition['candidate_closed_loop_outcome_records']}`",
            f"- Missing candidate outcome records: `{acquisition['missing_candidate_closed_loop_outcome_records']}`",
            f"- Paired record keys: `{acquisition['paired_record_key_count']}`",
            f"- Objective satisfied: `{acquisition['objective_3200_outcome_acquisition_satisfied']}`",
            f"- No-go failed count: `{no_go['failed_count']}`",
            f"- Recommended next work: `{decision['recommended_next_work']}`",
            "",
            "This gate keeps promotion, deployment, online selector activation, and safety/CAMP-over-DP claims disabled.",
            "",
        ]
    )


def _source_hashes(*, artifact_dir: Path, review_json: Path, review_md: Path, review_sha256s: Path) -> dict[str, str]:
    return {
        "artifact_dir": str(artifact_dir),
        "review_json_sha256": _sha256(review_json),
        "review_md_sha256": _sha256(review_md),
        "review_sha256s_sha256": _sha256(review_sha256s),
        "root_sha256s_sha256": _sha256(artifact_dir / "SHA256SUMS"),
    }


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    json_path: Path,
    md_path: Path,
    sha256s_path: Path,
) -> list[dict[str, Any]]:
    json_sha = _sha256(json_path)
    md_sha = _sha256(md_path)
    sha_sha = _sha256(sha256s_path)
    return [
        _expect("source_root_json_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_STATIC_REVIEW_JSON_NAME}"), json_sha),
        _expect("source_root_md_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_STATIC_REVIEW_MD_NAME}"), md_sha),
        _expect("source_root_nested_sha256s_sha", _sha_for_suffix(root_sha256s, "review/SHA256SUMS"), sha_sha),
        _expect("source_nested_json_sha", _sha_for_suffix(nested_sha256s, json_path.name), json_sha),
        _expect("source_nested_md_sha", _sha_for_suffix(nested_sha256s, md_path.name), md_sha),
    ]


def _path_checks(name: str, path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    checks = [_check(f"{name}_exists", path.is_file(), str(path), "file")]
    if path.is_file() and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("records", payload.get("selection_log", payload.get("rows")))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _record_key(root: Path, log: Path, row: dict[str, Any], index: int) -> str:
    try:
        parts = log.relative_to(root).parts
    except ValueError:
        parts = log.parts
    scenario = parts[0] if len(parts) > 0 else "unknown"
    seed = next((part.removeprefix("seed_") for part in parts if part.startswith("seed_")), str(_seed_from_path(log)))
    traffic = next((part for part in parts if part.startswith("tl_")), "tl_unknown")
    sample = row.get("sample_index", row.get("sample", row.get("record_index", index)))
    step = row.get("selection_step", index)
    return "|".join(
        [
            f"scenario={scenario}",
            f"seed={seed}",
            f"traffic_light_mode={traffic}",
            f"sample={sample}",
            f"step={step}",
        ]
    )


def _seed_from_path(path: Path) -> int | None:
    for part in path.parts:
        if part.startswith("seed_"):
            try:
                return int(part.removeprefix("seed_"))
            except ValueError:
                return None
    return None


def _path_has_any_marker(path: Path, markers: tuple[str, ...]) -> bool:
    lowered = str(path).lower()
    return any(marker in lowered for marker in markers)


def _latest_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            result[parts[1].strip()] = parts[0]
    return result


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _kv(mapping: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _sha_for_suffix(mapping: dict[str, str], suffix: str) -> str | None:
    normalized = suffix.replace("\\", "/")
    for path, digest in mapping.items():
        if path.replace("\\", "/").endswith(normalized):
            return digest
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
