#!/usr/bin/env python3
"""Audit a v13 static DP-reward default-off shadow replay execution artifact.

This is a read-only result audit. It inspects a fixed execution artifact and
its `camp_selection_log.json` outputs. It does not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_v1"
READY_STATUS = "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_passed"
REJECT_STATUS = "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_rejected"
DISABLED_STATUS = "dp_camp_v13_static_dp_reward_shadow_replay_execution_audit_disabled"
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_static_dp_reward_training_artifact_"
    "shadow_replay_evaluation_result_review_and_training_readiness_only"
)
RUNTIME_MANIFEST_SCHEMA = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
FORBIDDEN_STDERR_MARKERS = (
    "Traceback (most recent call last)",
    "ModuleNotFoundError",
    "TypeError:",
    "RuntimeError:",
    "ValueError:",
)
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit fixed v13 static DP-reward shadow replay execution outputs."
    )
    parser.add_argument("--execution_dir", type=Path, required=True)
    parser.add_argument("--base_output_dir", type=Path, required=True)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_log_count", type=int, default=32)
    parser.add_argument("--expected_steps_per_log", type=int, default=100)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--expected_num_candidates", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_static_dp_reward_shadow_replay_execution_audit",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_dir=args.execution_dir,
        base_output_dir=args.base_output_dir,
        preflight_json=args.preflight_json,
        runtime_manifest_json=args.runtime_manifest_json,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_log_count=args.expected_log_count,
        expected_steps_per_log=args.expected_steps_per_log,
        expected_records=args.expected_records,
        expected_num_candidates=args.expected_num_candidates,
        expected_atom_count=args.expected_atom_count,
        authorized_next_work=args.authorized_next_work,
        enabled=bool(args.enable_v13_static_dp_reward_shadow_replay_execution_audit),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_dir: Path,
    base_output_dir: Path,
    preflight_json: Path,
    runtime_manifest_json: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_log_count: int = 32,
    expected_steps_per_log: int = 100,
    expected_records: int = 3200,
    expected_num_candidates: int = 8,
    expected_atom_count: int = 14,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "read_only_result_audit": True,
            "replay_execution_performed_by_this_audit": False,
            "candidate_generation_performed_by_this_audit": False,
            "training_performed_by_this_audit": False,
            "dp_modified_by_this_audit": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "source_hashes": {},
        "execution": {},
        "records": {},
        "review_checks": [],
        "final_decision": _decision(
            False,
            [],
            DISABLED_STATUS,
            authorized_next_work=authorized_next_work,
            enabled=False,
        ),
    }
    if not enabled:
        return report

    failed: list[str] = []
    stdout_path = _first_existing(
        execution_dir / "runbook.stdout.log",
        execution_dir / "stdout.log",
    )
    stderr_path = _first_existing(
        execution_dir / "runbook.stderr.log",
        execution_dir / "stderr.log",
    )
    sha256sums_path = _first_existing(
        execution_dir / "SHA256SUMS.txt",
        execution_dir / "SHA256SUMS",
    )
    source_paths = {
        "execution_HEADS": execution_dir / "HEADS.txt",
        "execution_runbook_exit": execution_dir / "runbook.exit",
        "execution_stdout": stdout_path,
        "execution_stderr": stderr_path,
        "execution_sha256sums": sha256sums_path,
        "preflight_json": preflight_json,
        "runtime_manifest_json": runtime_manifest_json,
    }
    for name, path in source_paths.items():
        if path.exists():
            report["source_hashes"][name] = _sha256(path)
        else:
            failed.append(f"{name}_exists")

    if not execution_dir.exists():
        failed.append("execution_dir_exists")
    if not base_output_dir.exists():
        failed.append("base_output_dir_exists")
    if current_dp_head != required_dp_head:
        failed.append("current_dp_head_fixed")
    if current_camp_head != current_camp_origin_main:
        failed.append("camp_head_matches_origin_main")

    manifest = _read_json(runtime_manifest_json, failed, "runtime_manifest_json")
    preflight = _read_json(preflight_json, failed, "preflight_json")
    runbook_exit = _read_text(execution_dir / "runbook.exit").strip()
    stderr_text = _read_text(stderr_path)
    heads_text = _read_text(execution_dir / "HEADS.txt")
    stdout_lines = _count_lines(stdout_path)
    stderr_lines = _count_lines(stderr_path)

    if runbook_exit != "0":
        failed.append("runbook_exit_zero")
    if any(marker in stderr_text for marker in FORBIDDEN_STDERR_MARKERS):
        failed.append("stderr_without_python_exception_markers")
    if f"dp_head={required_dp_head}" not in heads_text:
        failed.append("heads_dp_head_fixed")
    if f"camp_head={current_camp_head}" not in heads_text:
        failed.append("heads_camp_head_matches_current")

    if manifest:
        if manifest.get("schema_version") != RUNTIME_MANIFEST_SCHEMA:
            failed.append("runtime_manifest_schema")
        if manifest.get("selection_effect") is not False:
            failed.append("runtime_manifest_selection_effect_false")
        if manifest.get("executed_output_policy") != "dp_top1":
            failed.append("runtime_manifest_executed_output_policy_dp_top1")
        if manifest.get("default_off") is not True:
            failed.append("runtime_manifest_default_off_true")
        if manifest.get("score_expression") != SCORE_EXPRESSION:
            failed.append("runtime_manifest_score_expression")
        if manifest.get("current_dp_head") != required_dp_head:
            failed.append("runtime_manifest_dp_head_fixed")
    if preflight:
        decision = preflight.get("final_decision", {})
        if decision.get("passed") is not True:
            failed.append("preflight_passed")
        if decision.get("runtime_manifest_written") is not True:
            failed.append("preflight_runtime_manifest_written")
        if decision.get("shadow_replay_evaluation_execution_authorized_next") is not True:
            failed.append("preflight_authorized_execution_next")

    logs = sorted(base_output_dir.rglob("camp_selection_log.json")) if base_output_dir.exists() else []
    if len(logs) != expected_log_count:
        failed.append("selection_log_count")

    record_summary, record_failures = _audit_selection_logs(
        logs=logs,
        expected_steps_per_log=expected_steps_per_log,
        expected_num_candidates=expected_num_candidates,
        expected_atom_count=expected_atom_count,
    )
    failed.extend(record_failures)
    if record_summary["record_count"] != expected_records:
        failed.append("record_count")

    report["execution"] = {
        "execution_dir": str(execution_dir),
        "base_output_dir": str(base_output_dir),
        "runbook_exit": runbook_exit,
        "stdout_lines": stdout_lines,
        "stderr_lines": stderr_lines,
        "stderr_only_known_warnings": "stderr_without_python_exception_markers" not in failed,
        "selection_log_count": len(logs),
        "expected_log_count": expected_log_count,
        "expected_records": expected_records,
    }
    report["records"] = record_summary
    report["review_checks"] = _checks_from_failures(failed)
    passed = not failed
    report["final_decision"] = _decision(
        passed,
        failed,
        READY_STATUS if passed else REJECT_STATUS,
        authorized_next_work=authorized_next_work,
        enabled=True,
    )
    return report


def _audit_selection_logs(
    *,
    logs: list[Path],
    expected_steps_per_log: int,
    expected_num_candidates: int,
    expected_atom_count: int,
) -> tuple[dict[str, Any], list[str]]:
    failed: list[str] = []
    route_counts: dict[str, int] = {}
    record_count = 0
    shadow_differs = 0
    feasible_records = 0
    used_fallback_records = 0
    max_affine_error = 0.0
    log_record_counts: dict[str, int] = {}
    violation_counts: dict[str, int] = {
        "default_off_contract": 0,
        "executed_index": 0,
        "postselection": 0,
        "reference_blend": 0,
        "guidance": 0,
        "closed_loop_outcomes": 0,
        "atom_schema": 0,
        "shape": 0,
        "affine_score": 0,
        "selection_score_mask": 0,
    }
    masked_selection_score_inf_count = 0

    for log_path in logs:
        route = _route_name_from_path(log_path)
        route_counts[route] = route_counts.get(route, 0) + 1
        payload = _read_json(log_path, failed, f"log_json:{log_path}")
        if not isinstance(payload, list):
            failed.append(f"log_is_list:{log_path}")
            continue
        log_record_counts[str(log_path)] = len(payload)
        if len(payload) != expected_steps_per_log:
            failed.append(f"log_steps:{log_path}")
        for record in payload:
            if not isinstance(record, dict):
                violation_counts["shape"] += 1
                continue
            record_count += 1
            selector = record.get("default_off_shadow_selector")
            if not _valid_default_off_selector(selector):
                violation_counts["default_off_contract"] += 1
            if record.get("selected_index") != 0 or record.get("executed_index") != 0:
                violation_counts["executed_index"] += 1
            if isinstance(selector, dict) and selector.get("shadow_selected_index") != 0:
                shadow_differs += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                violation_counts["postselection"] += 1
            if record.get("candidate_reference_blend_steps") is not None:
                violation_counts["reference_blend"] += 1
            generation_contract = record.get("candidate_generation_contract")
            if isinstance(generation_contract, dict):
                if generation_contract.get("reference_blend_steps") is not None:
                    violation_counts["reference_blend"] += 1
                if generation_contract.get("guidance_enabled") not in (False, None):
                    violation_counts["guidance"] += 1
                guidance = generation_contract.get("guidance")
                if isinstance(guidance, dict) and any(
                    guidance.get(key) not in (None, [], {}, False)
                    for key in ("config_path", "config_sha256", "functions", "guidance_scale")
                ):
                    violation_counts["guidance"] += 1
                if generation_contract.get("changes_diffusion_planner_weights") not in (
                    False,
                    None,
                ):
                    violation_counts["guidance"] += 1
            if (
                record.get("candidate_closed_loop_outcomes") is not None
                or record.get("candidate_closed_loop_outcome_weights") is not None
            ):
                violation_counts["closed_loop_outcomes"] += 1
            if record.get("atom_schema_version") != ATOM_SCHEMA_VERSION:
                violation_counts["atom_schema"] += 1

            normalized_atoms = record.get("selection_normalized_atoms", record.get("normalized_atoms"))
            weights = record.get("selection_weights", record.get("weights"))
            scores = record.get("scores")
            selection_scores = record.get("selection_scores")
            feasible = record.get("feasible_mask")
            if not _valid_shapes(
                normalized_atoms,
                weights,
                scores,
                expected_num_candidates,
                expected_atom_count,
            ):
                violation_counts["shape"] += 1
            else:
                for atom_row, score in zip(normalized_atoms, scores):
                    expected = sum(float(a) * float(w) for a, w in zip(atom_row, weights))
                    error = abs(expected - float(score))
                    max_affine_error = max(max_affine_error, error)
                    if error > 1.0e-6:
                        violation_counts["affine_score"] += 1
                        break

            mask_errors, masked_inf = _selection_score_mask_errors(
                selection_scores,
                feasible,
                expected_num_candidates,
            )
            violation_counts["selection_score_mask"] += mask_errors
            masked_selection_score_inf_count += masked_inf

            if isinstance(feasible, list) and any(bool(item) for item in feasible):
                feasible_records += 1
            if record.get("used_fallback") is True:
                used_fallback_records += 1

    for name, count in violation_counts.items():
        if count:
            failed.append(f"{name}_violations")

    return (
        {
            "record_count": record_count,
            "route_log_counts": dict(sorted(route_counts.items())),
            "log_record_counts_min": min(log_record_counts.values()) if log_record_counts else 0,
            "log_record_counts_max": max(log_record_counts.values()) if log_record_counts else 0,
            "shadow_differs_from_dp_top1_records": shadow_differs,
            "feasible_records": feasible_records,
            "used_fallback_records": used_fallback_records,
            "masked_selection_score_inf_count": masked_selection_score_inf_count,
            "max_affine_score_error": max_affine_error,
            "violation_counts": violation_counts,
        },
        failed,
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    execution = report.get("execution", {})
    records = report.get("records", {})
    lines = [
        "# V13 Static DP-Reward Shadow Replay Execution Audit",
        "",
        f"Status: `{decision['status']}`",
        f"Passed: `{decision['passed']}`",
        f"Execution dir: `{execution.get('execution_dir')}`",
        f"Base output dir: `{execution.get('base_output_dir')}`",
        f"Runbook exit: `{execution.get('runbook_exit')}`",
        f"Selection logs: `{execution.get('selection_log_count')}`",
        f"Records: `{records.get('record_count')}`",
        f"Route log counts: `{records.get('route_log_counts')}`",
        f"Shadow differs from DP Top-1 records: `{records.get('shadow_differs_from_dp_top1_records')}`",
        f"Max affine score error: `{records.get('max_affine_score_error')}`",
        "",
        "This is a read-only non-promotion audit. It does not authorize selector",
        "promotion, atom promotion, deployment, safety benefit claims, or CAMP-over-DP",
        "claims.",
        "",
        "## Failed Checks",
    ]
    failed = decision.get("failed_checks", [])
    lines.extend(f"- `{item}`" for item in failed) if failed else lines.append("- none")
    lines.append("")
    lines.append(f"Authorized next work: `{decision.get('authorized_next_work')}`")
    return "\n".join(lines) + "\n"


def _decision(
    passed: bool,
    failed_checks: list[str],
    status: str,
    *,
    authorized_next_work: str,
    enabled: bool,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "passed": bool(passed),
        "status": status,
        "failed_checks": list(failed_checks),
        "authorized_next_work": authorized_next_work if passed else None,
        "result_review_and_training_readiness_authorized_next": bool(passed),
        "replay_execution_performed_by_this_audit": False,
        "candidate_generation_performed_by_this_audit": False,
        "training_performed_by_this_audit": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _valid_default_off_selector(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("schema_version") == RUNTIME_MANIFEST_SCHEMA
        and value.get("enabled") is True
        and value.get("default_off") is True
        and value.get("selection_effect") is False
        and value.get("online_selector_change") is False
        and value.get("executed_index") == 0
        and value.get("executed_output_policy") == "dp_top1"
        and value.get("failed_closed_reason") is None
        and value.get("artifact_contract_ready") is True
        and value.get("candidate_operation") == "fixed DP candidate reranking only"
        and value.get("score_expression") == SCORE_EXPRESSION
        and isinstance(value.get("shadow_selected_index"), int)
    )


def _valid_shapes(
    normalized_atoms: Any,
    weights: Any,
    scores: Any,
    expected_num_candidates: int,
    expected_atom_count: int,
) -> bool:
    if not isinstance(normalized_atoms, list) or len(normalized_atoms) != expected_num_candidates:
        return False
    if not isinstance(weights, list) or len(weights) != expected_atom_count:
        return False
    if not isinstance(scores, list) or len(scores) != expected_num_candidates:
        return False
    if not all(_finite_number(item) for item in weights):
        return False
    if abs(sum(float(item) for item in weights) - 1.0) > 1.0e-6:
        return False
    for row in normalized_atoms:
        if not isinstance(row, list) or len(row) != expected_atom_count:
            return False
        if not all(_finite_number(item) for item in row):
            return False
    return all(_finite_number(item) for item in scores)


def _selection_score_mask_errors(
    selection_scores: Any,
    feasible_mask: Any,
    expected_num_candidates: int,
) -> tuple[int, int]:
    if not isinstance(selection_scores, list) or len(selection_scores) != expected_num_candidates:
        return 1, 0
    if not isinstance(feasible_mask, list) or len(feasible_mask) != expected_num_candidates:
        return 1, 0
    errors = 0
    masked_inf = 0
    for score, feasible in zip(selection_scores, feasible_mask):
        if _finite_number(score):
            continue
        if isinstance(score, (int, float)) and math.isinf(float(score)) and not bool(feasible):
            masked_inf += 1
            continue
        errors += 1
    return errors, masked_inf


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _route_name_from_path(path: Path) -> str:
    for part in path.parts:
        if part.startswith("sample_") or part.startswith("nishi_"):
            return part
    return "unknown"


def _read_json(path: Path, failed: list[str], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        failed.append(f"{label}_json_readable")
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _count_lines(path: Path) -> int:
    text = _read_text(path)
    return len(text.splitlines()) if text else 0


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _checks_from_failures(failed: list[str]) -> list[dict[str, Any]]:
    failed_set = set(failed)
    names = [
        "execution_dir_exists",
        "base_output_dir_exists",
        "runbook_exit_zero",
        "selection_log_count",
        "record_count",
        "runtime_manifest_selection_effect_false",
        "runtime_manifest_executed_output_policy_dp_top1",
        "default_off_contract_violations",
        "executed_index_violations",
        "affine_score_violations",
        "postselection_violations",
        "reference_blend_violations",
        "guidance_violations",
        "closed_loop_outcomes_violations",
        "current_dp_head_fixed",
    ]
    return [
        {
            "name": name,
            "passed": name not in failed_set,
        }
        for name in names
    ]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _stable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    if isinstance(value, tuple):
        return [_stable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
