#!/usr/bin/env python3
"""Read-only evaluator for v13 fresh evaluation split shadow logs.

The evaluator consumes already-materialized fixed-DP candidate selection logs.
It does not run Diffusion Planner, generate candidates, replay, train CAMP,
modify DP, change the online selector, promote, deploy, or make safety/CAMP
over-DP claims. It records only shadow selected indices while executed output
remains DP Top-1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
MEMBER_SOURCE_SCHEMA = "dp_camp_v13_fresh_evaluation_split_member_source_manifest_v1"
NONOVERLAP_REPORT_SCHEMA = "dp_camp_v13_fresh_evaluation_split_member_source_nonoverlap_report_v1"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_evaluation_v1"
DISABLED_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_default_off_disabled"
READY_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_passed"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_evaluation_rejected"
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_execution_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_result_review_only"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
AUDIT_FALSE_FLAGS = (
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only v13 fresh evaluation split shadow evaluator."
    )
    parser.add_argument("--evaluation_output_dir", type=Path, required=True)
    parser.add_argument("--member_source_manifest_json", type=Path, required=True)
    parser.add_argument("--member_source_nonoverlap_report_json", type=Path, required=True)
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_fresh_evaluation_split_evaluation",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evaluation_output_dir=args.evaluation_output_dir,
        member_source_manifest_json=args.member_source_manifest_json,
        member_source_nonoverlap_report_json=args.member_source_nonoverlap_report_json,
        runtime_manifest_json=args.runtime_manifest_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_records=args.expected_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_v13_fresh_evaluation_split_evaluation,
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
    member_source_manifest_json: Path,
    member_source_nonoverlap_report_json: Path,
    runtime_manifest_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_selection_log_count: int = 32,
    expected_records: int = 3200,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        evaluation_output_dir=evaluation_output_dir,
        member_source_manifest_json=member_source_manifest_json,
        member_source_nonoverlap_report_json=member_source_nonoverlap_report_json,
        runtime_manifest_json=runtime_manifest_json,
        v13_audit_md=v13_audit_md,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
    )
    if not enabled:
        return report

    paths = {
        "evaluation_output_dir": evaluation_output_dir.resolve(),
        "member_source_manifest_json": member_source_manifest_json.resolve(),
        "member_source_nonoverlap_report_json": member_source_nonoverlap_report_json.resolve(),
        "runtime_manifest_json": runtime_manifest_json.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    member_source = _load_json_dict(paths["member_source_manifest_json"])
    nonoverlap = _load_json_dict(paths["member_source_nonoverlap_report_json"])
    runtime_manifest = _load_json_dict(paths["runtime_manifest_json"])
    audit_text = _read_text(paths["v13_audit_md"])
    selection_logs = sorted(paths["evaluation_output_dir"].rglob("camp_selection_log.json"))
    clean_contract = validate_logs(selection_logs) if selection_logs else {
        "passed": False,
        "records": 0,
        "failed_records": [{"errors": ["selection_logs_missing"]}],
        "selection_logs": [],
    }
    evaluation = _summarize_logs(
        selection_logs=selection_logs,
        expected_candidate_count=expected_candidate_count,
        expected_atom_count=expected_atom_count,
    )
    checks = _checks(
        paths=paths,
        member_source=member_source,
        nonoverlap=nonoverlap,
        runtime_manifest=runtime_manifest,
        audit_text=audit_text,
        selection_logs=selection_logs,
        clean_contract=clean_contract,
        evaluation=evaluation,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_selection_log_count=expected_selection_log_count,
        expected_records=expected_records,
        expected_candidate_count=expected_candidate_count,
        expected_atom_count=expected_atom_count,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    report["source_hashes"] = {
        name: _sha256(path)
        for name, path in paths.items()
        if path.is_file()
    }
    report["source_hashes"]["evaluation_output_dir"] = _hash_paths(selection_logs)
    report["member_source_summary"] = _member_source_summary(member_source)
    report["nonoverlap_summary"] = _nonoverlap_summary(nonoverlap)
    report["runtime_manifest_summary"] = _runtime_manifest_summary(runtime_manifest)
    report["clean_contract"] = clean_contract
    report["evaluation"] = evaluation
    report["evaluation_checks"] = checks
    report["final_decision"] = _decision(
        passed=passed,
        failed=failed,
        status=READY_STATUS if passed else REJECT_STATUS,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
        enabled=True,
    )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    evaluation = report.get("evaluation", {})
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Evaluation",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Enabled: `{decision['enabled']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selection logs: `{evaluation.get('selection_log_count', 0)}`",
            f"- Records: `{evaluation.get('record_count', 0)}`",
            f"- Shadow differs from DP Top-1 records: `{evaluation.get('shadow_differs_from_dp_top1_records', 0)}`",
            f"- Max affine score error: `{evaluation.get('max_affine_score_error', 0.0)}`",
            "",
            "This evaluator is read-only over existing fixed-DP candidate logs. "
            "Executed output remains DP Top-1; CAMP only records shadow selected "
            "indices and affine fixed-candidate scores.",
            "",
        ]
    )


def _empty_report(
    *,
    enabled: bool,
    evaluation_output_dir: Path,
    member_source_manifest_json: Path,
    member_source_nonoverlap_report_json: Path,
    runtime_manifest_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "read_only_existing_logs": True,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "training_execution": False,
            "online_selector_change": False,
            "executed_trajectory_change": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "evaluation_output_dir": str(evaluation_output_dir),
            "member_source_manifest_json": str(member_source_manifest_json),
            "member_source_nonoverlap_report_json": str(member_source_nonoverlap_report_json),
            "runtime_manifest_json": str(runtime_manifest_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {},
        "member_source_summary": {},
        "nonoverlap_summary": {},
        "runtime_manifest_summary": {},
        "clean_contract": {},
        "evaluation": {},
        "evaluation_checks": [],
        "final_decision": _decision(
            passed=False,
            failed=[],
            status=DISABLED_STATUS,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
            enabled=False,
        ),
    }


def _checks(
    *,
    paths: dict[str, Path],
    member_source: dict[str, Any],
    nonoverlap: dict[str, Any],
    runtime_manifest: dict[str, Any],
    audit_text: str,
    selection_logs: list[Path],
    clean_contract: dict[str, Any],
    evaluation: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_selection_log_count: int,
    expected_records: int,
    expected_candidate_count: int,
    expected_atom_count: int,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    nonoverlap_summary = _nonoverlap_summary(nonoverlap)
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("evaluation_output_dir_exists", paths["evaluation_output_dir"].is_dir(), str(paths["evaluation_output_dir"]), "directory exists"),
        _check("member_source_manifest_exists", paths["member_source_manifest_json"].is_file(), str(paths["member_source_manifest_json"]), "file exists"),
        _check("member_source_nonoverlap_report_exists", paths["member_source_nonoverlap_report_json"].is_file(), str(paths["member_source_nonoverlap_report_json"]), "file exists"),
        _check("runtime_manifest_exists", paths["runtime_manifest_json"].is_file(), str(paths["runtime_manifest_json"]), "file exists"),
        _check("v13_audit_md_exists", paths["v13_audit_md"].is_file(), str(paths["v13_audit_md"]), "file exists"),
        _expect("member_source_schema", member_source.get("schema_version"), MEMBER_SOURCE_SCHEMA),
        _expect("member_source_selected_member_count", _int(member_source.get("selected_member_count")), expected_selection_log_count),
        _expect("nonoverlap_all_zero", nonoverlap_summary.get("all_required_intersections_zero"), True),
        _expect("runtime_schema", runtime_manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA),
        _expect("runtime_default_off", runtime_manifest.get("default_off"), True),
        _expect("runtime_selection_effect_false", runtime_manifest.get("selection_effect"), False),
        _expect("runtime_executed_output_dp_top1", runtime_manifest.get("executed_output_policy"), "dp_top1"),
        _expect("runtime_candidate_operation", runtime_manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("runtime_score_affine", runtime_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("runtime_dp_head_fixed", runtime_manifest.get("current_dp_head", runtime_manifest.get("required_dp_head")), FIXED_DP_HEAD),
        _expect("selection_log_count", len(selection_logs), expected_selection_log_count),
        _expect("clean_contract_passed", clean_contract.get("passed"), True),
        _expect("record_count", clean_contract.get("records"), expected_records),
        _expect("evaluation_record_count", evaluation.get("record_count"), expected_records),
        _expect("evaluation_candidate_count", evaluation.get("candidate_count"), expected_candidate_count),
        _expect("evaluation_atom_count", evaluation.get("atom_count"), expected_atom_count),
        _expect("evaluation_executed_index_violations_zero", evaluation.get("executed_index_violations"), 0),
        _expect("evaluation_online_selector_change_violations_zero", evaluation.get("online_selector_change_violations"), 0),
        _expect("evaluation_closed_loop_outcome_records_zero", evaluation.get("closed_loop_outcome_records"), 0),
        _check("evaluation_affine_error_tiny", float(evaluation.get("max_affine_score_error", math.inf)) <= 1.0e-6, evaluation.get("max_affine_score_error"), "<=1e-6"),
    ]
    for key in ZERO_INTERSECTION_KEYS:
        checks.append(_expect(f"nonoverlap_zero_{key}", nonoverlap_summary.get(key), 0))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_keeps_training_blocked",
            _latest_value(text, "training_execution_authorized_by_current_boundary"),
            "False",
        ),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(text, flag), "False"))
    return checks


def _summarize_logs(
    *,
    selection_logs: list[Path],
    expected_candidate_count: int,
    expected_atom_count: int,
) -> dict[str, Any]:
    record_count = 0
    shadow_differs = 0
    executed_index_violations = 0
    online_selector_change_violations = 0
    closed_loop_records = 0
    max_affine_error = 0.0
    candidate_count = 0
    atom_count = 0
    shadow_index_counts: dict[str, int] = {}
    for log_path in selection_logs:
        payload = _load_json_list(log_path)
        for record in payload:
            if not isinstance(record, dict):
                continue
            record_count += 1
            executed_index = _int(record.get("executed_index"))
            selected_index = _int(record.get("selected_index"))
            shadow_index = _int(record.get("shadow_selected_index"))
            if executed_index != 0 or selected_index != 0:
                executed_index_violations += 1
            selector = _dict(record.get("default_off_shadow_selector"))
            if selector.get("online_selector_change") not in (False, None):
                online_selector_change_violations += 1
            if shadow_index is not None and shadow_index != 0:
                shadow_differs += 1
            if shadow_index is not None:
                key = str(shadow_index)
                shadow_index_counts[key] = shadow_index_counts.get(key, 0) + 1
            atoms = record.get("selection_normalized_atoms", record.get("normalized_atoms", record.get("atoms")))
            weights = record.get("selection_weights", record.get("weights"))
            scores = record.get("scores")
            candidate_count = max(candidate_count, len(atoms) if isinstance(atoms, list) else 0)
            if isinstance(atoms, list) and atoms and isinstance(atoms[0], list):
                atom_count = max(atom_count, len(atoms[0]))
            max_affine_error = max(max_affine_error, _max_affine_error(atoms, weights, scores))
            if record.get("candidate_closed_loop_outcomes") is not None:
                closed_loop_records += 1
    return {
        "selection_log_count": len(selection_logs),
        "record_count": record_count,
        "candidate_count": candidate_count or expected_candidate_count,
        "atom_count": atom_count or expected_atom_count,
        "shadow_differs_from_dp_top1_records": shadow_differs,
        "shadow_selected_index_counts": dict(sorted(shadow_index_counts.items())),
        "executed_index_violations": executed_index_violations,
        "online_selector_change_violations": online_selector_change_violations,
        "closed_loop_outcome_records": closed_loop_records,
        "max_affine_score_error": max_affine_error,
        "read_only_existing_logs": True,
        "executed_output_policy": "dp_top1",
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _max_affine_error(atoms: Any, weights: Any, scores: Any) -> float:
    if not isinstance(atoms, list) or not isinstance(weights, list) or not isinstance(scores, list):
        return math.inf
    errors = []
    for row, score in zip(atoms, scores):
        if not isinstance(row, list):
            return math.inf
        try:
            expected = sum(float(atom) * float(weight) for atom, weight in zip(row, weights))
            errors.append(abs(expected - float(score)))
        except (TypeError, ValueError):
            return math.inf
    return max(errors) if errors else math.inf


def _member_source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    members = payload.get("members")
    return {
        "schema_version": payload.get("schema_version"),
        "selected_member_count": _int(payload.get("selected_member_count")),
        "member_entries": len(members) if isinstance(members, list) else 0,
    }


def _nonoverlap_summary(payload: dict[str, Any]) -> dict[str, Any]:
    result = _dict(payload.get("preflight_result")) or payload
    counts = _dict(result.get("zero_intersection_counts")) or result
    summary = {
        key: _int(counts.get(key))
        for key in ZERO_INTERSECTION_KEYS
    }
    summary["schema_version"] = payload.get("schema_version")
    summary["all_required_intersections_zero"] = (
        result.get("all_required_intersections_zero") is True
        or all(summary.get(key) == 0 for key in ZERO_INTERSECTION_KEYS)
    )
    return summary


def _runtime_manifest_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "default_off": payload.get("default_off"),
        "selection_effect": payload.get("selection_effect"),
        "executed_output_policy": payload.get("executed_output_policy"),
        "candidate_operation": payload.get("candidate_operation"),
        "score_expression": payload.get("score_expression"),
        "current_dp_head": payload.get("current_dp_head", payload.get("required_dp_head")),
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    status: str,
    authorized_current_work: str,
    authorized_next_work: str,
    enabled: bool,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "status": status,
        "passed": bool(passed),
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "fresh_evaluation_split_evaluation_executed": bool(enabled and passed),
        "fresh_evaluation_split_evaluation_result_review_authorized_next": bool(passed),
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json_list(path: Path) -> list[Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        try:
            digest.update(path.read_bytes())
        except OSError:
            pass
    return digest.hexdigest()


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
