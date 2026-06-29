#!/usr/bin/env python3
"""Audit v13 static DP-reward eval-plus-prior training execution artifacts.

This is a read-only post-training audit. It inspects an already completed
static DP-reward training execution and verifies the produced weights, atom
scales, summary, preflight command plan, and execution logs. It does not run
training, replay, candidate generation, Diffusion Planner, promotion, deploy,
or safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_execution_audit_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_execution_audit_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_execution_audit_rejected"
)
DISABLED_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_execution_audit_disabled"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_shadow_replay_eval_plus_prior_static_dp_reward_training_"
    "execution_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "preflight_only"
)
COMMAND_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_command_plan_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only audit for v13 static DP-reward eval-plus-prior training."
    )
    parser.add_argument("--execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--training_output_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--execution_camp_head", default=None)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_selection_log_count", type=int, default=64)
    parser.add_argument("--expected_contract_records", type=int, default=6400)
    parser.add_argument("--expected_training_records", type=int, default=5299)
    parser.add_argument("--expected_dropped_records", type=int, default=1101)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_static_dp_reward_eval_plus_prior_training_execution_audit",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_artifact_dir=args.execution_artifact_dir,
        preflight_artifact_dir=args.preflight_artifact_dir,
        training_output_dir=args.training_output_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        execution_camp_head=args.execution_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_contract_records=args.expected_contract_records,
        expected_training_records=args.expected_training_records,
        expected_dropped_records=args.expected_dropped_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        enabled=bool(args.enable_v13_static_dp_reward_eval_plus_prior_training_execution_audit),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_artifact_dir: Path,
    preflight_artifact_dir: Path,
    training_output_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    execution_camp_head: str | None = None,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_selection_log_count: int = 64,
    expected_contract_records: int = 6400,
    expected_training_records: int = 5299,
    expected_dropped_records: int = 1101,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    enabled: bool = False,
) -> dict[str, Any]:
    execution_artifact_dir = execution_artifact_dir.resolve()
    preflight_artifact_dir = preflight_artifact_dir.resolve()
    training_output_dir = training_output_dir.resolve()
    v13_audit_md = v13_audit_md.resolve()
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "read_only": True,
            "training_execution_audited": False,
            "training_execution_performed_by_this_audit": False,
            "replay_execution_performed_by_this_audit": False,
            "candidate_generation_performed_by_this_audit": False,
            "dp_modified_by_this_audit": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "math_boundary": (
                "The artifact contains nonnegative simplex weights over the "
                "approved atom schema; online selection remains disabled until "
                "a later explicit promotion gate."
            ),
        },
        "source_paths": {
            "execution_artifact_dir": str(execution_artifact_dir),
            "preflight_artifact_dir": str(preflight_artifact_dir),
            "training_output_dir": str(training_output_dir),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {},
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "execution_camp_head": execution_camp_head or current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "training_artifact": {},
        "review_checks": [],
        "final_decision": _decision(False, [], enabled=False),
    }
    if not enabled:
        return report

    paths = {
        "execution_heads": execution_artifact_dir / "HEADS.txt",
        "execution_exit": execution_artifact_dir / "training.exit",
        "execution_stdout": execution_artifact_dir / "training.stdout.log",
        "execution_stderr": execution_artifact_dir / "training.stderr.log",
        "execution_sha256sums": execution_artifact_dir / "SHA256SUMS.txt",
        "preflight_command_plan": preflight_artifact_dir / "training_command_plan.json",
        "preflight_runbook": preflight_artifact_dir / "run_training.sh",
        "training_summary": training_output_dir / "training_summary.json",
        "atom_scales": training_output_dir / "atom_scales_dp_static.json",
        "weights_npy": training_output_dir / "offline_weights_dp_static.npy",
        "v13_audit_md": v13_audit_md,
    }
    for name, path in paths.items():
        report["source_hashes"][f"{name}_sha256"] = _sha256(path) if path.is_file() else None

    command_plan = _load_json_dict(paths["preflight_command_plan"])
    summary = _load_json_dict(paths["training_summary"])
    scales = _load_json_dict(paths["atom_scales"])
    weights = _load_weights(paths["weights_npy"])
    artifact = _artifact_summary(
        command_plan=command_plan,
        summary=summary,
        scales=scales,
        weights=weights,
    )
    report["training_artifact"] = artifact

    checks = _checks(
        execution_artifact_dir=execution_artifact_dir,
        preflight_artifact_dir=preflight_artifact_dir,
        training_output_dir=training_output_dir,
        paths=paths,
        audit_text=_read_text(v13_audit_md),
        heads_text=_read_text(paths["execution_heads"]),
        exit_text=_read_text(paths["execution_exit"]).strip(),
        stderr_text=_read_text(paths["execution_stderr"]),
        command_plan=command_plan,
        summary=summary,
        scales=scales,
        weights=weights,
        artifact=artifact,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        execution_camp_head=execution_camp_head or current_camp_head,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_selection_log_count=expected_selection_log_count,
        expected_contract_records=expected_contract_records,
        expected_training_records=expected_training_records,
        expected_dropped_records=expected_dropped_records,
        expected_candidate_count=expected_candidate_count,
        expected_atom_count=expected_atom_count,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    report["review_checks"] = checks
    report["analysis"]["training_execution_audited"] = bool(passed)
    report["final_decision"] = _decision(passed, failed, enabled=True)
    return report


def _checks(
    *,
    execution_artifact_dir: Path,
    preflight_artifact_dir: Path,
    training_output_dir: Path,
    paths: dict[str, Path],
    audit_text: str,
    heads_text: str,
    exit_text: str,
    stderr_text: str,
    command_plan: dict[str, Any],
    summary: dict[str, Any],
    scales: dict[str, Any],
    weights: np.ndarray,
    artifact: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    execution_camp_head: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_selection_log_count: int,
    expected_contract_records: int,
    expected_training_records: int,
    expected_dropped_records: int,
    expected_candidate_count: int,
    expected_atom_count: int,
) -> list[dict[str, Any]]:
    dp_contract = _dict(summary.get("dp_native_training_data_contract"))
    atom_schema = _dict(summary.get("atom_schema"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("execution_camp_head_is_sha", _is_git_sha(execution_camp_head), execution_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("execution_artifact_dir_exists", execution_artifact_dir.is_dir(), str(execution_artifact_dir), "directory exists"),
        _check("preflight_artifact_dir_exists", preflight_artifact_dir.is_dir(), str(preflight_artifact_dir), "directory exists"),
        _check("training_output_dir_exists", training_output_dir.is_dir(), str(training_output_dir), "directory exists"),
        _check("execution_heads_exists", paths["execution_heads"].is_file(), str(paths["execution_heads"]), "file exists"),
        _check("preflight_runbook_exists", paths["preflight_runbook"].is_file(), str(paths["preflight_runbook"]), "file exists"),
        _check("training_summary_exists", paths["training_summary"].is_file(), str(paths["training_summary"]), "file exists"),
        _check("atom_scales_exists", paths["atom_scales"].is_file(), str(paths["atom_scales"]), "file exists"),
        _check("weights_npy_exists", paths["weights_npy"].is_file(), str(paths["weights_npy"]), "file exists"),
        _expect("execution_exit_zero", exit_text, "0"),
        _check("stderr_has_no_traceback", "Traceback" not in stderr_text, "Traceback" in stderr_text, False),
        _check("heads_camp_head_matches_execution", f"camp_head={execution_camp_head}" in heads_text, heads_text, f"camp_head={execution_camp_head}"),
        _check("heads_dp_head_fixed", f"dp_head={required_dp_head}" in heads_text, heads_text, f"dp_head={required_dp_head}"),
        _expect("audit_latest_next_work_target", _latest_audit_value(audit_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("audit_training_execution_authorized", _latest_audit_value(audit_text, "training_execution_authorized_by_current_boundary"), "True"),
        _expect("audit_replay_execution_blocked", _latest_audit_value(audit_text, "replay_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_dp_modification_blocked", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("command_plan_schema", command_plan.get("schema_version"), COMMAND_PLAN_SCHEMA_VERSION),
        _expect("command_plan_training_not_executed_by_preflight", command_plan.get("training_execution_performed"), False),
        _expect("command_plan_label_source", command_plan.get("label_source"), "dp_reward"),
        _expect("command_plan_reward_key", command_plan.get("reward_key"), "quality_without_progress"),
        _expect("command_plan_reward_progress_weight", command_plan.get("reward_progress_weight"), 2.0),
        _expect("command_plan_requires_contract", command_plan.get("require_dp_native_training_data_contract"), True),
        _expect("command_plan_requires_atom_schema", command_plan.get("require_atom_schema"), True),
        _expect("command_plan_selection_log_count", command_plan.get("selection_log_count"), expected_selection_log_count),
        _expect("summary_training_type", summary.get("training_type"), "diffusion_planner_static_candidate_preference"),
        _expect("summary_label_source", summary.get("label_source"), "dp_reward"),
        _expect("summary_reward_key", summary.get("reward_key"), "quality_without_progress"),
        _expect("summary_reward_progress_weight", summary.get("reward_progress_weight"), 2.0),
        _expect("summary_selection_log_count", len(summary.get("selection_logs", [])), expected_selection_log_count),
        _expect("summary_num_records", summary.get("num_records"), expected_training_records),
        _expect("summary_dropped_records", summary.get("dropped_records_without_feasible_candidate"), expected_dropped_records),
        _expect("summary_num_candidates", summary.get("num_candidates"), expected_candidate_count),
        _expect("summary_num_atoms", summary.get("num_atoms"), expected_atom_count),
        _expect("summary_atom_schema_version", summary.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("summary_contract_passed", dp_contract.get("passed"), True),
        _expect("summary_contract_records", dp_contract.get("records"), expected_contract_records),
        _expect("summary_contract_failed_records_zero", len(dp_contract.get("failed_records", [])), 0),
        _expect("summary_atom_schema_required", atom_schema.get("required"), True),
        _expect("summary_atom_schema_verified_records", atom_schema.get("verified_records"), expected_contract_records),
        _expect("weights_shape", artifact["weights_shape"], [expected_atom_count]),
        _expect("weights_finite", artifact["weights_finite"], True),
        _expect("weights_nonnegative", artifact["weights_nonnegative"], True),
        _check("weights_sum_one", abs(float(artifact["weights_sum"]) - 1.0) <= 1e-9, artifact["weights_sum"], "1.0 +/- 1e-9"),
        _expect("weights_match_summary", artifact["weights_match_summary"], True),
        _expect("scales_schema", scales.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("scales_count", len(scales.get("scales", [])), expected_atom_count),
        _expect("scales_strictly_positive", artifact["scales_strictly_positive"], True),
        _check("training_output_weights_path", _same_path(summary.get("weights_path"), paths["weights_npy"]), summary.get("weights_path"), str(paths["weights_npy"])),
        _check("training_output_atom_scales_path", _same_path(summary.get("atom_scales_path"), paths["atom_scales"]), summary.get("atom_scales_path"), str(paths["atom_scales"])),
    ]
    return checks


def _artifact_summary(
    *,
    command_plan: dict[str, Any],
    summary: dict[str, Any],
    scales: dict[str, Any],
    weights: np.ndarray,
) -> dict[str, Any]:
    trained_weights = np.asarray(summary.get("trained_weights", []), dtype=np.float64)
    scale_values = scales.get("scales", [])
    try:
        scale_array = np.asarray(scale_values, dtype=np.float64)
    except (TypeError, ValueError):
        scale_array = np.asarray([], dtype=np.float64)
    return {
        "planned_training_output_dir": command_plan.get("planned_training_output_dir"),
        "selection_log_count": len(summary.get("selection_logs", [])),
        "num_records": summary.get("num_records"),
        "dropped_records_without_feasible_candidate": summary.get(
            "dropped_records_without_feasible_candidate"
        ),
        "oracle_match_rate": summary.get("oracle_match_rate"),
        "feasible_candidate_rate": summary.get("feasible_candidate_rate"),
        "records_with_any_infeasible": summary.get("records_with_any_infeasible"),
        "weights_shape": list(weights.shape),
        "weights_sum": float(np.sum(weights)) if weights.size else None,
        "weights_min": float(np.min(weights)) if weights.size else None,
        "weights_max": float(np.max(weights)) if weights.size else None,
        "weights_finite": bool(weights.size and np.all(np.isfinite(weights))),
        "weights_nonnegative": bool(weights.size and np.all(weights >= -1e-12)),
        "weights_match_summary": bool(
            weights.size
            and trained_weights.shape == weights.shape
            and np.allclose(weights, trained_weights, atol=1e-12, rtol=1e-12)
        ),
        "scales_count": int(scale_array.size),
        "scales_strictly_positive": bool(
            scale_array.size and np.all(np.isfinite(scale_array)) and np.all(scale_array > 0.0)
        ),
        "nonpromotion_artifact": True,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    artifact = report.get("training_artifact", {})
    return "\n".join(
        [
            "# V13 Static DP-Reward Eval Plus Prior Training Execution Audit",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{','.join(decision['failed_checks'])}`",
            f"- Training records: `{artifact.get('num_records')}`",
            f"- Dropped records: `{artifact.get('dropped_records_without_feasible_candidate')}`",
            f"- Weights sum: `{artifact.get('weights_sum')}`",
            f"- Weights min: `{artifact.get('weights_min')}`",
            f"- Weights max: `{artifact.get('weights_max')}`",
            "",
            "This audit is read-only. It does not run training, replay, candidate "
            "generation, DP modification, promotion, deployment, or safety/CAMP-over-DP "
            "claims.",
            "",
        ]
    )


def _decision(passed: bool, failed_checks: list[str], *, enabled: bool) -> dict[str, Any]:
    if not enabled:
        status = DISABLED_STATUS
    else:
        status = READY_STATUS if passed else REJECT_STATUS
    return {
        "status": status,
        "passed": bool(passed) if enabled else False,
        "failed_checks": failed_checks,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed and enabled else None,
        "shadow_replay_evaluation_preflight_authorized_next": bool(passed and enabled),
        "training_execution_audited": bool(passed and enabled),
        "training_executed_by_audit": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "formal_seeds_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _load_weights(path: Path) -> np.ndarray:
    if not path.is_file():
        return np.asarray([], dtype=np.float64)
    loaded = np.load(path)
    return np.asarray(loaded, dtype=np.float64).reshape(-1)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _same_path(observed: Any, expected: Path) -> bool:
    if not isinstance(observed, str):
        return False
    try:
        return Path(observed).resolve() == expected.resolve()
    except OSError:
        return observed == str(expected)


def _latest_audit_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
