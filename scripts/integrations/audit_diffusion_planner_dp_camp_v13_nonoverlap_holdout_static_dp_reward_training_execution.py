#!/usr/bin/env python3
"""Audit completed v13 non-overlap holdout static DP-reward training.

This is a read-only evidence audit for a completed offline training run. It
does not run training, replay, generate candidates, modify Diffusion Planner,
promote artifacts, deploy, or make safety/CAMP-over-DP Top-1 claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_static_dp_reward_training_execution_audit_v1"
)
READY_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_static_dp_reward_training_execution_audit_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_static_dp_reward_training_execution_audit_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_static_dp_reward_training_execution_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_training_artifact_shadow_replay_evaluation_preflight_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for completed v13 non-overlap holdout static "
            "DP-reward training."
        )
    )
    parser.add_argument("--training_execution_artifact", type=Path, required=True)
    parser.add_argument("--training_output_dir", type=Path, required=True)
    parser.add_argument("--preflight_artifact", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_total_records", type=int, default=16000)
    parser.add_argument("--expected_trained_records", type=int, default=13616)
    parser.add_argument("--expected_dropped_records", type=int, default=2384)
    parser.add_argument("--expected_selection_log_count", type=int, default=160)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        training_execution_artifact=args.training_execution_artifact,
        training_output_dir=args.training_output_dir,
        preflight_artifact=args.preflight_artifact,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_total_records=args.expected_total_records,
        expected_trained_records=args.expected_trained_records,
        expected_dropped_records=args.expected_dropped_records,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(args.output_json.parent)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    training_execution_artifact: Path,
    training_output_dir: Path,
    preflight_artifact: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_total_records: int = 16000,
    expected_trained_records: int = 13616,
    expected_dropped_records: int = 2384,
    expected_selection_log_count: int = 160,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    execution_root = training_execution_artifact.resolve()
    training_root = training_output_dir.resolve()
    preflight_root = preflight_artifact.resolve()
    summary_path = training_root / "training_summary.json"
    weights_path = training_root / "offline_weights_dp_static.npy"
    scales_path = training_root / "atom_scales_dp_static.json"
    summary = _load_json_dict(summary_path)
    scales = _load_json_dict(scales_path)
    preflight = _load_json_dict(preflight_root / "preflight.json")
    command_plan = _load_json_dict(preflight_root / "training_command_plan.json")
    audit_text = _read_text(v13_audit_md)
    weights = _load_weights(weights_path)
    heads = _parse_heads(execution_root / "HEADS.txt")
    execution_exit = _read_exit(execution_root / "training.exit")
    execution_stderr = _read_text(execution_root / "training.stderr.txt")
    output_files = _read_lines(execution_root / "training_output_files.txt")
    training_hashes = _file_hashes(training_root)
    artifact_hashes = _artifact_hashes(execution_root)

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
            }
        )

    preflight_decision = _dict(preflight.get("final_decision"))
    preflight_summary = _dict(preflight.get("training_input_summary"))
    preflight_combined = _dict(preflight_summary.get("combined"))

    check("training_execution_artifact_exists", execution_root.is_dir(), str(execution_root))
    check("training_output_dir_exists", training_root.is_dir(), str(training_root))
    check("preflight_artifact_exists", preflight_root.is_dir(), str(preflight_root))
    check("training_exit_zero", execution_exit == 0, execution_exit, 0)
    check("training_stderr_empty", execution_stderr.strip() == "", execution_stderr.strip(), "")
    check(
        "training_output_files",
        output_files == [
            "atom_scales_dp_static.json",
            "offline_weights_dp_static.npy",
            "training_summary.json",
        ],
        output_files,
    )
    check("preflight_passed", preflight_decision.get("passed") is True, preflight_decision.get("passed"))
    check(
        "preflight_authorized_training_execution",
        preflight_decision.get("authorized_next_work") == authorized_current_work,
        preflight_decision.get("authorized_next_work"),
        authorized_current_work,
    )
    check(
        "preflight_training_log_count",
        preflight_combined.get("selection_log_count") == expected_selection_log_count,
        preflight_combined.get("selection_log_count"),
        expected_selection_log_count,
    )
    check(
        "preflight_total_records",
        preflight_combined.get("records_total") == expected_total_records,
        preflight_combined.get("records_total"),
        expected_total_records,
    )
    check(
        "command_plan_training_not_previously_executed",
        command_plan.get("training_execution_performed") is False,
        command_plan.get("training_execution_performed"),
        False,
    )
    check("audit_latest_next_work", _latest_audit_value(audit_text, "next_work_target") == authorized_current_work, _latest_audit_value(audit_text, "next_work_target"), authorized_current_work)
    check("audit_training_execution_authorized", _latest_audit_value(audit_text, "training_execution_authorized_by_current_boundary") == "True", _latest_audit_value(audit_text, "training_execution_authorized_by_current_boundary"), "True")
    check("audit_replay_execution_blocked", _latest_audit_value(audit_text, "replay_execution_authorized_by_current_boundary") == "False", _latest_audit_value(audit_text, "replay_execution_authorized_by_current_boundary"), "False")
    check("audit_dp_modification_blocked", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary") == "False", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary"), "False")
    check("execution_source_camp_head", _is_sha(heads.get("camp_head")), heads.get("camp_head"), "40-hex sha")
    check("execution_source_camp_origin_main", heads.get("camp_origin_main") == heads.get("camp_head"), heads, "source CAMP head equals origin/main")
    check("execution_source_dp_head_fixed", heads.get("dp_head") == required_dp_head, heads.get("dp_head"), required_dp_head)
    check("audit_camp_head_matches_origin", current_camp_head == current_camp_origin_main, {"head": current_camp_head, "origin": current_camp_origin_main}, "current CAMP head equals origin/main")
    check("audit_current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head)
    check("summary_training_type", summary.get("training_type") == "diffusion_planner_static_candidate_preference", summary.get("training_type"), "diffusion_planner_static_candidate_preference")
    check("summary_label_source", summary.get("label_source") == "dp_reward", summary.get("label_source"), "dp_reward")
    check("summary_reward_key", summary.get("reward_key") == "quality_without_progress", summary.get("reward_key"), "quality_without_progress")
    check("summary_reward_progress_weight", float(summary.get("reward_progress_weight", math.nan)) == 2.0, summary.get("reward_progress_weight"), 2.0)
    check("summary_total_contract_records", _dict(summary.get("dp_native_training_data_contract")).get("records") == expected_total_records, _dict(summary.get("dp_native_training_data_contract")).get("records"), expected_total_records)
    check("summary_contract_passed", _dict(summary.get("dp_native_training_data_contract")).get("passed") is True, _dict(summary.get("dp_native_training_data_contract")).get("passed"))
    check("summary_trained_records", summary.get("num_records") == expected_trained_records, summary.get("num_records"), expected_trained_records)
    check("summary_dropped_records", summary.get("dropped_records_without_feasible_candidate") == expected_dropped_records, summary.get("dropped_records_without_feasible_candidate"), expected_dropped_records)
    check("summary_candidate_count", summary.get("num_candidates") == expected_candidate_count, summary.get("num_candidates"), expected_candidate_count)
    check("summary_atom_count", summary.get("num_atoms") == expected_atom_count, summary.get("num_atoms"), expected_atom_count)
    check("summary_atom_schema", summary.get("atom_schema_version") == ATOM_SCHEMA_VERSION, summary.get("atom_schema_version"), ATOM_SCHEMA_VERSION)
    check("summary_atom_schema_verified_records", _dict(summary.get("atom_schema")).get("verified_records") == expected_total_records, _dict(summary.get("atom_schema")).get("verified_records"), expected_total_records)
    check("summary_history_reaches_epoch_1000", _last_history_epoch(summary) == 1000.0, _last_history_epoch(summary), 1000.0)
    check("summary_caveat_present", "not counterfactual closed-loop outcomes" in str(summary.get("caveat")), summary.get("caveat"))
    check("weights_shape", list(weights.shape) == [expected_atom_count], list(weights.shape), [expected_atom_count])
    check("weights_all_finite", bool(np.isfinite(weights).all()), weights.tolist())
    check("weights_nonnegative", bool((weights >= -1e-12).all()), weights.tolist())
    check("weights_simplex_sum", abs(float(weights.sum()) - 1.0) <= 1e-9, float(weights.sum()), 1.0)
    check("weights_match_summary", _weights_match_summary(weights, summary), {"weights": weights.tolist(), "summary": summary.get("trained_weights")})
    check("atom_scales_schema", scales.get("atom_schema_version") == ATOM_SCHEMA_VERSION, scales.get("atom_schema_version"), ATOM_SCHEMA_VERSION)
    check("atom_scales_count", len(scales.get("scales", [])) == expected_atom_count, len(scales.get("scales", [])), expected_atom_count)
    check("atom_scales_positive", all(float(value) > 0.0 for value in scales.get("scales", [])), scales.get("scales"))
    check("output_summary_hash_present", "training_summary.json" in training_hashes, training_hashes)
    check("output_weights_hash_present", "offline_weights_dp_static.npy" in training_hashes, training_hashes)
    check("output_scales_hash_present", "atom_scales_dp_static.json" in training_hashes, training_hashes)
    check("artifact_sha256sums_present", "SHA256SUMS" in artifact_hashes, artifact_hashes)

    failed_checks = [item["name"] for item in checks if not item["passed"]]
    passed = not failed_checks
    final_decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed_checks,
        "authorized_next_work": authorized_next_work if passed else None,
        "training_executed": execution_exit == 0,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "dp_modification_authorized": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_artifact_shadow_replay_evaluation_preflight_authorized_next": passed,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "paths": {
            "training_execution_artifact": str(execution_root),
            "training_output_dir": str(training_root),
            "preflight_artifact": str(preflight_root),
            "training_summary_json": str(summary_path),
            "static_weights_npy": str(weights_path),
            "atom_scales_json": str(scales_path),
        },
        "heads": {
            "source": heads,
            "audit": {
                "current_camp_head": current_camp_head,
                "current_camp_origin_main": current_camp_origin_main,
                "current_dp_head": current_dp_head,
                "required_dp_head": required_dp_head,
            },
        },
        "training_summary": {
            "num_records": summary.get("num_records"),
            "dropped_records_without_feasible_candidate": summary.get("dropped_records_without_feasible_candidate"),
            "dp_native_training_data_contract": summary.get("dp_native_training_data_contract"),
            "oracle_match_rate": summary.get("oracle_match_rate"),
            "feasible_candidate_rate": summary.get("feasible_candidate_rate"),
            "records_with_any_infeasible": summary.get("records_with_any_infeasible"),
            "history_last": summary.get("history", [{}])[-1] if summary.get("history") else {},
        },
        "weights": {
            "shape": list(weights.shape),
            "min": float(weights.min()) if weights.size else None,
            "max": float(weights.max()) if weights.size else None,
            "sum": float(weights.sum()) if weights.size else None,
            "all_finite": bool(np.isfinite(weights).all()) if weights.size else False,
            "nonnegative": bool((weights >= -1e-12).all()) if weights.size else False,
            "simplex_close": abs(float(weights.sum()) - 1.0) <= 1e-9 if weights.size else False,
        },
        "atom_scales": {
            "schema_version": scales.get("atom_schema_version"),
            "count": len(scales.get("scales", [])),
            "strictly_positive": all(float(value) > 0.0 for value in scales.get("scales", [])),
        },
        "hashes": {
            "training_output_files": training_hashes,
            "execution_artifact_files": artifact_hashes,
        },
        "review_checks": checks,
        "final_decision": final_decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    weights = report["weights"]
    summary = report["training_summary"]
    lines = [
        "# V13 Non-Overlap Holdout Static DP-Reward Training Execution Audit",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Training executed: `{decision['training_executed']}`",
        f"- Trained records: `{summary['num_records']}`",
        f"- Dropped records without feasible candidate: `{summary['dropped_records_without_feasible_candidate']}`",
        f"- Weights sum: `{weights['sum']}`",
        f"- Weights nonnegative simplex: `{weights['nonnegative'] and weights['simplex_close']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "This audit is read-only and does not run replay, generate candidates, "
        "modify DP, promote artifacts, deploy, or make safety/CAMP-over-DP claims.",
        "",
    ]
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _load_weights(path: Path) -> np.ndarray:
    if not path.is_file():
        return np.asarray([], dtype=np.float64)
    return np.asarray(np.load(path), dtype=np.float64).reshape(-1)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_lines(path: Path) -> list[str]:
    return [line.strip() for line in _read_text(path).splitlines() if line.strip()]


def _read_exit(path: Path) -> int | None:
    text = _read_text(path).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_heads(path: Path) -> dict[str, str]:
    heads = {}
    for line in _read_text(path).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            heads[key.strip()] = value.strip()
    return heads


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _latest_audit_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _last_history_epoch(summary: dict[str, Any]) -> float | None:
    history = summary.get("history")
    if not isinstance(history, list) or not history:
        return None
    try:
        return float(_dict(history[-1]).get("epoch"))
    except (TypeError, ValueError):
        return None


def _weights_match_summary(weights: np.ndarray, summary: dict[str, Any]) -> bool:
    summary_weights = summary.get("trained_weights")
    if not isinstance(summary_weights, list):
        return False
    other = np.asarray(summary_weights, dtype=np.float64).reshape(-1)
    return weights.shape == other.shape and bool(np.allclose(weights, other, atol=1e-12, rtol=0.0))


def _file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if not root.is_dir():
        return hashes
    for path in sorted(item for item in root.iterdir() if item.is_file()):
        hashes[path.name] = _sha256(path)
    return hashes


def _artifact_hashes(root: Path) -> dict[str, str]:
    names = (
        "HEADS.txt",
        "training_command.txt",
        "training.stdout.txt",
        "training.stderr.txt",
        "training.exit",
        "preflight_training_command_plan.json",
        "preflight_selection_manifest.json",
        "training_output_files.txt",
        "training_output_SHA256SUMS",
        "SHA256SUMS",
    )
    return {name: _sha256(root / name) for name in names if (root / name).is_file()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256sums(root: Path) -> None:
    rows = []
    for path in sorted(item for item in root.iterdir() if item.is_file()):
        if path.name == "SHA256SUMS":
            continue
        rows.append(f"{_sha256(path)}  {path.name}")
    (root / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
