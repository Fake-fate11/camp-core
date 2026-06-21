#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = ROOT / "scripts/integrations/train_diffusion_planner_robust_camp.py"
EVAL_SCRIPT = ROOT / "scripts/integrations/evaluate_diffusion_planner_camp_safety_cost.py"
PROOF_SCRIPT = ROOT / "scripts/integrations/summarize_diffusion_planner_camp_safety_cost_proof.py"

MANIFEST_STATUS = "offline_convex_selector_training_input_manifest_ready"
MANIFEST_NEXT_WORK = "offline_convex_selector_training_execution_dry_run_only"
COMPLETE_STATUS = "offline_convex_selector_training_dry_run_complete"
BLOCKED_STATUS = "offline_convex_selector_training_dry_run_blocked"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the offline convex DP-CAMP selector training dry run from a "
            "frozen input manifest. This trains/evaluates only over existing "
            "candidate logs; it never runs Diffusion Planner."
        )
    )
    parser.add_argument("--manifest_json", type=Path, required=True)
    parser.add_argument("--oracle_report", type=Path, required=True)
    parser.add_argument("--scenario_bucket_manifest", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--selector_name", default="offline_convex_safety_cost_v1")
    parser.add_argument("--timeout_seconds", type=int, default=3600)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_dry_run(
        manifest=_load_json(args.manifest_json),
        manifest_path=args.manifest_json,
        oracle_report=args.oracle_report,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        output_dir=args.output_dir,
        selector_name=args.selector_name,
        timeout_seconds=args.timeout_seconds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def run_dry_run(
    *,
    manifest: dict[str, Any],
    manifest_path: Path | None = None,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    output_dir: Path,
    selector_name: str = "offline_convex_safety_cost_v1",
    timeout_seconds: int = 3600,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    input_check = _input_check(manifest)
    if not input_check["passed"]:
        return _blocked_report(
            input_check=input_check,
            manifest_path=manifest_path,
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            output_dir=output_dir,
            selector_name=selector_name,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    training_dir = output_dir / "training"
    eval_dir = output_dir / "selector_eval"
    proof_dir = output_dir / "proof"
    training_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    proof_dir.mkdir(parents=True, exist_ok=True)

    log_paths = [Path(item["path"]) for item in input_check["logs"]]
    train_command = _training_command(log_paths, training_dir)
    train_result = _run_command(train_command, runner, timeout_seconds)
    if train_result["returncode"] != 0:
        return _result_report(
            status=BLOCKED_STATUS,
            input_check=input_check,
            manifest_path=manifest_path,
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            output_dir=output_dir,
            selector_name=selector_name,
            commands={"training": train_result},
            artifacts={},
            proof_report=None,
            reason="training_command_failed",
        )

    training_summary_path = training_dir / "training_summary.json"
    training_summary = _load_json(training_summary_path)
    atom_scales = Path(
        _get(training_summary, "artifacts", "atom_scales_path")
        or training_dir / "atom_scales_dp_static.json"
    )
    static_weights = Path(
        _get(training_summary, "artifacts", "weights_path")
        or training_dir / "offline_weights_dp_static.npy"
    )
    eval_json = eval_dir / "selector_eval.json"
    eval_md = eval_dir / "selector_eval.md"
    eval_command = _eval_command(
        log_paths,
        atom_scales=atom_scales,
        static_weights=static_weights,
        selector_name=selector_name,
        scenario_bucket_manifest=scenario_bucket_manifest,
        output_json=eval_json,
        output_md=eval_md,
    )
    eval_result = _run_command(eval_command, runner, timeout_seconds)
    if eval_result["returncode"] != 0:
        return _result_report(
            status=BLOCKED_STATUS,
            input_check=input_check,
            manifest_path=manifest_path,
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            output_dir=output_dir,
            selector_name=selector_name,
            commands={"training": train_result, "selector_eval": eval_result},
            artifacts=_artifact_map(training_summary_path, atom_scales, static_weights),
            proof_report=None,
            reason="selector_eval_command_failed",
        )

    proof_json = proof_dir / "camp_vs_top1_safety_cost_proof.json"
    proof_md = proof_dir / "camp_vs_top1_safety_cost_proof.md"
    proof_command = _proof_command(
        oracle_report=oracle_report,
        selector_eval_report=eval_json,
        output_json=proof_json,
        output_md=proof_md,
    )
    proof_result = _run_command(proof_command, runner, timeout_seconds)
    proof_report = _load_json(proof_json) if proof_json.is_file() else None
    if proof_result["returncode"] != 0:
        return _result_report(
            status=BLOCKED_STATUS,
            input_check=input_check,
            manifest_path=manifest_path,
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            output_dir=output_dir,
            selector_name=selector_name,
            commands={
                "training": train_result,
                "selector_eval": eval_result,
                "proof_summary": proof_result,
            },
            artifacts=_artifact_map(
                training_summary_path,
                atom_scales,
                static_weights,
                eval_json,
                eval_md,
                proof_json,
                proof_md,
            ),
            proof_report=proof_report,
            reason="proof_summary_command_failed",
        )

    return _result_report(
        status=COMPLETE_STATUS,
        input_check=input_check,
        manifest_path=manifest_path,
        oracle_report=oracle_report,
        scenario_bucket_manifest=scenario_bucket_manifest,
        output_dir=output_dir,
        selector_name=selector_name,
        commands={
            "training": train_result,
            "selector_eval": eval_result,
            "proof_summary": proof_result,
        },
        artifacts=_artifact_map(
            training_summary_path,
            atom_scales,
            static_weights,
            eval_json,
            eval_md,
            proof_json,
            proof_md,
        ),
        proof_report=proof_report,
        reason=None,
    )


def _input_check(manifest: dict[str, Any]) -> dict[str, Any]:
    decision = manifest.get("final_decision") or {}
    errors: list[str] = []
    if decision.get("status") != MANIFEST_STATUS:
        errors.append("manifest_status_not_ready")
    if decision.get("passed") is not True:
        errors.append("manifest_not_passed")
    if decision.get("authorized_next_work") != MANIFEST_NEXT_WORK:
        errors.append("manifest_does_not_authorize_training_dry_run")
    if _get(manifest, "summary", "formal_seed_logs") != 0:
        errors.append("manifest_contains_formal_seed_logs")
    logs = manifest.get("manifest", {}).get("logs")
    if not isinstance(logs, list) or not logs:
        errors.append("manifest_has_no_logs")
        logs = []
    checked_logs: list[dict[str, Any]] = []
    for item in logs:
        if not isinstance(item, dict):
            errors.append("manifest_log_entry_not_object")
            continue
        path = Path(str(item.get("path", "")))
        expected_sha = str(item.get("sha256") or "")
        if not path.is_file():
            errors.append(f"missing_log={path}")
            continue
        actual_sha = _sha256(path)
        if expected_sha and actual_sha != expected_sha:
            errors.append(f"sha_mismatch={path}")
        checked_logs.append({**item, "actual_sha256": actual_sha})
    return {
        "passed": not errors,
        "errors": errors,
        "logs": checked_logs,
        "records": _get(manifest, "summary", "records"),
        "required_buckets": _get(manifest, "summary", "required_buckets") or [],
        "bucket_record_counts": _get(manifest, "summary", "bucket_record_counts")
        or {},
    }


def _training_command(log_paths: Sequence[Path], output_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(TRAIN_SCRIPT),
        "--output_dir",
        str(output_dir),
        "--mode",
        "static",
        "--training_scope",
        "feasible_ranking",
        "--label_source",
        "safety_cost_v1_hard_guarded",
        "--objective",
        "robust_margin_cvar",
        "--risk_type",
        "cvar",
        "--alpha",
        "0.9",
        "--margin_scale",
        "0.1",
        "--margin_clip",
        "2.0",
        "--l2_reg",
        "1e-4",
        "--max_iter",
        "20",
        "--tolerance",
        "1e-6",
        "--solver",
        "CLARABEL",
        "--scale_percentile",
        "95.0",
        "--val_fraction",
        "0.2",
        "--seed",
        "7",
        "--require_atom_schema",
    ]
    for path in log_paths:
        command.extend(["--selection_log", str(path)])
    return command


def _eval_command(
    log_paths: Sequence[Path],
    *,
    atom_scales: Path,
    static_weights: Path,
    selector_name: str,
    scenario_bucket_manifest: Path,
    output_json: Path,
    output_md: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(EVAL_SCRIPT),
        "--atom_scales",
        str(atom_scales),
        "--static_weights",
        str(static_weights),
        "--selector_name",
        selector_name,
        "--scenario_bucket_manifest",
        str(scenario_bucket_manifest),
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
        "--fail_on_formal_seeds",
        "--fail_on_missing_required",
    ]
    for path in log_paths:
        command.extend(["--selection_log", str(path)])
    return command


def _proof_command(
    *,
    oracle_report: Path,
    selector_eval_report: Path,
    output_json: Path,
    output_md: Path,
) -> list[str]:
    return [
        sys.executable,
        str(PROOF_SCRIPT),
        "--oracle_report",
        str(oracle_report),
        "--selector_eval_report",
        str(selector_eval_report),
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
    ]


def _run_command(
    command: list[str],
    runner: Callable[..., subprocess.CompletedProcess[str]],
    timeout_seconds: int,
) -> dict[str, Any]:
    completed = runner(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    return {
        "argv": command,
        "returncode": int(completed.returncode),
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }


def _blocked_report(
    *,
    input_check: dict[str, Any],
    manifest_path: Path | None,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    output_dir: Path,
    selector_name: str,
) -> dict[str, Any]:
    return _result_report(
        status=BLOCKED_STATUS,
        input_check=input_check,
        manifest_path=manifest_path,
        oracle_report=oracle_report,
        scenario_bucket_manifest=scenario_bucket_manifest,
        output_dir=output_dir,
        selector_name=selector_name,
        commands={},
        artifacts={},
        proof_report=None,
        reason="input_manifest_not_ready",
    )


def _result_report(
    *,
    status: str,
    input_check: dict[str, Any],
    manifest_path: Path | None,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    output_dir: Path,
    selector_name: str,
    commands: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
    proof_report: dict[str, Any] | None,
    reason: str | None,
) -> dict[str, Any]:
    complete = status == COMPLETE_STATUS
    proof_decision = proof_report.get("final_decision", {}) if proof_report else {}
    proof_passed = bool(
        proof_decision.get("safety_cost_trained_selector_candidate_branch_proof")
    )
    if complete and proof_passed:
        next_work = "candidate_branch_proof_review_before_deployability_gate"
    elif complete:
        next_work = "diagnose_offline_convex_selector_training_failure_modes"
    else:
        next_work = None
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_selector_training_dry_run_v1",
            "selector_name": selector_name,
            "training": complete,
            "training_scope": "offline dry run over frozen nonformal manifest",
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "manifest_json": None if manifest_path is None else str(manifest_path),
            "oracle_report": str(oracle_report),
            "scenario_bucket_manifest": str(scenario_bucket_manifest),
            "output_dir": str(output_dir),
            "math_boundary": (
                "This dry run only optimizes CAMP weights over fixed logged "
                "candidate atoms and offline hard-guarded SafetyCost labels. "
                "Scores remain affine a_k^T w with simplex/L2/CVaR robust "
                "margin training. It does not run or modify DP, does not use "
                "future outcomes online, and is not a classical Benders claim."
            ),
        },
        "input_check": input_check,
        "commands": commands,
        "artifacts": artifacts,
        "proof_status": proof_decision,
        "final_decision": {
            "status": status,
            "passed": complete,
            "reason": reason,
            "authorized_next_work": next_work,
            "candidate_branch_proof_passed": proof_passed,
            "candidate_branch_proof_status": proof_decision.get("status"),
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Offline Convex Selector Training Dry Run",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- candidate-branch proof passed: `{decision['candidate_branch_proof_passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- online selector authorized: `{decision['online_selector_authorized']}`",
        "",
        "## Input Manifest",
        "",
        f"- records: `{report['input_check'].get('records')}`",
        f"- logs: `{len(report['input_check'].get('logs', []))}`",
        f"- errors: `{', '.join(report['input_check'].get('errors', [])) or 'none'}`",
        "",
        "## Commands",
        "",
    ]
    for name, command in report["commands"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- return code: `{command['returncode']}`",
                f"- stdout tail: `{command['stdout_tail']}`",
                f"- stderr tail: `{command['stderr_tail']}`",
                "",
            ]
        )
    lines.extend(["## Artifacts", "", "| Name | Path | SHA-256 |", "| --- | --- | --- |"])
    for name, artifact in report["artifacts"].items():
        lines.append(f"| `{name}` | `{artifact['path']}` | `{artifact['sha256']}` |")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_map(*paths: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path or not Path(path).is_file():
            continue
        artifacts[Path(path).stem] = {
            "path": str(path),
            "sha256": _sha256(Path(path)),
        }
    return artifacts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tail(text: str | None, max_chars: int = 4000) -> str:
    if not text:
        return ""
    return text[-max_chars:]


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
