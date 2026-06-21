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

PLAN_STATUS = "offline_convex_objective_label_sensitivity_plan_ready"
PLAN_NEXT_WORK = "implement_objective_label_sensitivity_dry_run_wrapper_only"
MANIFEST_STATUS = "offline_convex_selector_training_input_manifest_ready"
MANIFEST_NEXT_WORK = "offline_convex_selector_training_execution_dry_run_only"

COMPLETE_STATUS = "offline_convex_objective_label_sensitivity_dry_run_complete"
BLOCKED_STATUS = "offline_convex_objective_label_sensitivity_dry_run_blocked"

HARD_COMPONENTS = (
    "collision",
    "near_miss",
    "lane_violation",
    "realized_red_light",
    "red_light_violation",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the predeclared offline convex objective/label sensitivity "
            "wrapper over fixed DP candidate logs. This runs only the planned "
            "offline training/evaluation/proof commands; it never runs DP, "
            "closed-loop replay, online selection, Full36, or formal seeds."
        )
    )
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--manifest_json", type=Path, required=True)
    parser.add_argument("--oracle_report", type=Path, required=True)
    parser.add_argument("--scenario_bucket_manifest", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--selector_prefix", default="objective_label_sensitivity")
    parser.add_argument("--timeout_seconds", type=int, default=3600)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_sensitivity_dry_run(
        plan=_load_json(args.plan_json),
        manifest=_load_json(args.manifest_json),
        plan_path=args.plan_json,
        manifest_path=args.manifest_json,
        oracle_report=args.oracle_report,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        output_dir=args.output_dir,
        selector_prefix=args.selector_prefix,
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


def run_sensitivity_dry_run(
    *,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    plan_path: Path | None = None,
    manifest_path: Path | None = None,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    output_dir: Path,
    selector_prefix: str = "objective_label_sensitivity",
    timeout_seconds: int = 3600,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    plan_check = _plan_check(plan)
    input_check = _manifest_check(manifest)
    if not plan_check["passed"] or not input_check["passed"]:
        return _result_report(
            status=BLOCKED_STATUS,
            plan_check=plan_check,
            input_check=input_check,
            variants=[],
            plan_path=plan_path,
            manifest_path=manifest_path,
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            output_dir=output_dir,
            selector_prefix=selector_prefix,
            reason="source_gate_not_ready",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    log_paths = [Path(item["path"]) for item in input_check["logs"]]
    variants = _planned_variants(plan)
    variant_reports = [
        _run_variant(
            variant=variant,
            log_paths=log_paths,
            output_dir=output_dir / variant["name"],
            selector_name=f"{selector_prefix}_{variant['name']}",
            oracle_report=oracle_report,
            scenario_bucket_manifest=scenario_bucket_manifest,
            timeout_seconds=timeout_seconds,
            runner=runner,
        )
        for variant in variants
    ]
    complete = all(row["status"] == "variant_complete" for row in variant_reports)
    return _result_report(
        status=COMPLETE_STATUS if complete else BLOCKED_STATUS,
        plan_check=plan_check,
        input_check=input_check,
        variants=variant_reports,
        plan_path=plan_path,
        manifest_path=manifest_path,
        oracle_report=oracle_report,
        scenario_bucket_manifest=scenario_bucket_manifest,
        output_dir=output_dir,
        selector_prefix=selector_prefix,
        reason=None if complete else "variant_command_failed",
    )


def _run_variant(
    *,
    variant: dict[str, Any],
    log_paths: Sequence[Path],
    output_dir: Path,
    selector_name: str,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    timeout_seconds: int,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    training_dir = output_dir / "training"
    eval_dir = output_dir / "selector_eval"
    proof_dir = output_dir / "proof"
    training_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    proof_dir.mkdir(parents=True, exist_ok=True)

    commands: dict[str, dict[str, Any]] = {}
    train_command = _training_command(log_paths, training_dir, variant["parameters"])
    train_result = _run_command(train_command, runner, timeout_seconds)
    commands["training"] = train_result
    if train_result["returncode"] != 0:
        return _variant_report(
            variant=variant,
            selector_name=selector_name,
            status="variant_blocked",
            reason="training_command_failed",
            commands=commands,
            artifacts={},
            selector_eval=None,
            proof_report=None,
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
    commands["selector_eval"] = eval_result
    artifacts = _artifact_map(training_summary_path, atom_scales, static_weights)
    if eval_result["returncode"] != 0:
        return _variant_report(
            variant=variant,
            selector_name=selector_name,
            status="variant_blocked",
            reason="selector_eval_command_failed",
            commands=commands,
            artifacts=artifacts,
            selector_eval=None,
            proof_report=None,
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
    commands["proof_summary"] = proof_result
    artifacts = _artifact_map(
        training_summary_path,
        atom_scales,
        static_weights,
        eval_json,
        eval_md,
        proof_json,
        proof_md,
    )
    selector_eval = _load_json(eval_json) if eval_json.is_file() else None
    proof_report = _load_json(proof_json) if proof_json.is_file() else None
    if proof_result["returncode"] != 0:
        return _variant_report(
            variant=variant,
            selector_name=selector_name,
            status="variant_blocked",
            reason="proof_summary_command_failed",
            commands=commands,
            artifacts=artifacts,
            selector_eval=selector_eval,
            proof_report=proof_report,
        )

    return _variant_report(
        variant=variant,
        selector_name=selector_name,
        status="variant_complete",
        reason=None,
        commands=commands,
        artifacts=artifacts,
        selector_eval=selector_eval,
        proof_report=proof_report,
    )


def _variant_report(
    *,
    variant: dict[str, Any],
    selector_name: str,
    status: str,
    reason: str | None,
    commands: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, str]],
    selector_eval: dict[str, Any] | None,
    proof_report: dict[str, Any] | None,
) -> dict[str, Any]:
    gate = _variant_gate(
        variant=variant,
        selector_eval=selector_eval,
        proof_report=proof_report,
        command_complete=status == "variant_complete",
    )
    return {
        "name": variant["name"],
        "role": variant["role"],
        "selector_name": selector_name,
        "parameters": variant["parameters"],
        "status": status,
        "reason": reason,
        "commands": commands,
        "artifacts": artifacts,
        "acceptance_gate": gate,
        "accepted_for_next_review": gate["passed"],
    }


def _variant_gate(
    *,
    variant: dict[str, Any],
    selector_eval: dict[str, Any] | None,
    proof_report: dict[str, Any] | None,
    command_complete: bool,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        _check_equal("commands_complete", command_complete, True),
        _check_equal("variant_is_not_control", variant["role"], "candidate"),
    ]
    if selector_eval is None or proof_report is None:
        checks.append(
            {
                "name": "selector_eval_and_proof_available",
                "passed": False,
                "reason": "missing selector_eval or proof artifact",
            }
        )
        return _gate_result(checks)
    logs = selector_eval.get("logs") or {}
    checks.append(
        _check_equal("formal_seed_logs_zero", logs.get("formal_seed_logs"), 0)
    )
    proof_gates = proof_report.get("gates") or {}
    top1_gate = proof_gates.get("safety_cost_trained_selector_vs_top1") or {}
    gap_gate = proof_gates.get("safety_cost_trained_selector_gap_closed") or {}
    checks.extend(
        [
            _check_equal("top1_bucket_gate_passed", top1_gate.get("passed"), True),
            _check_equal("oracle_gap_gate_passed", gap_gate.get("passed"), True),
        ]
    )
    comparison = selector_eval.get("selector_comparison") or {}
    ci_high = _get(
        comparison,
        "run_level_evaluated_minus_logged_cost_ci",
        "ci95_high",
    )
    checks.append(
        {
            "name": "logged_selector_nonworse_ci_high",
            "passed": ci_high is not None and float(ci_high) <= 0.0,
            "ci95_high": ci_high,
        }
    )
    weighted = comparison.get("weighted_component_delta_mean") or {}
    for name in HARD_COMPONENTS:
        if name in weighted:
            value = float(weighted.get(name, 0.0))
            checks.append(
                {
                    "name": f"component_nonpositive_{name}",
                    "passed": value <= 0.0,
                    "value": value,
                }
            )
    if not any(check["name"].startswith("component_nonpositive_") for check in checks):
        checks.append(
            {
                "name": "hard_component_deltas_available",
                "passed": False,
                "reason": "no hard component deltas were reported",
            }
        )
    return _gate_result(checks)


def _gate_result(checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _plan_check(plan: dict[str, Any]) -> dict[str, Any]:
    decision = plan.get("final_decision") or {}
    variants = _planned_variants(plan)
    errors: list[str] = []
    if decision.get("status") != PLAN_STATUS:
        errors.append("plan_status_not_ready")
    if decision.get("passed") is not True:
        errors.append("plan_not_passed")
    if decision.get("authorized_next_work") != PLAN_NEXT_WORK:
        errors.append("plan_does_not_authorize_wrapper_implementation")
    if not variants:
        errors.append("plan_has_no_variants")
    if not any(variant["role"] == "control" for variant in variants):
        errors.append("plan_missing_control_variant")
    if not any(variant["role"] == "candidate" for variant in variants):
        errors.append("plan_missing_candidate_variants")
    return {
        "passed": not errors,
        "errors": errors,
        "variants": [{"name": row["name"], "role": row["role"]} for row in variants],
    }


def _planned_variants(plan: dict[str, Any]) -> list[dict[str, Any]]:
    raw_plan = plan.get("predeclared_sensitivity_plan") or {}
    variants: list[dict[str, Any]] = []
    control = raw_plan.get("control_variant")
    if isinstance(control, dict) and control.get("name"):
        variants.append(
            {
                "name": str(control["name"]),
                "role": "control",
                "parameters": dict(control.get("parameters") or {}),
            }
        )
    for item in raw_plan.get("candidate_variants") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        variants.append(
            {
                "name": str(item["name"]),
                "role": "candidate",
                "parameters": dict(item.get("parameters") or {}),
            }
        )
    return variants


def _manifest_check(manifest: dict[str, Any]) -> dict[str, Any]:
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


def _training_command(
    log_paths: Sequence[Path],
    output_dir: Path,
    parameters: dict[str, Any],
) -> list[str]:
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
        str(parameters.get("label_source") or "safety_cost_v1_hard_guarded"),
        "--objective",
        "robust_margin_cvar",
        "--risk_type",
        str(parameters.get("risk_type") or "cvar"),
        "--alpha",
        str(parameters.get("alpha", 0.9)),
        "--margin_scale",
        "0.1",
        "--margin_clip",
        "2.0",
        "--l2_reg",
        str(parameters.get("l2_reg", 1e-4)),
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
    for item in parameters.get("min_atom_weight") or []:
        command.extend(["--min_atom_weight", str(item)])
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


def _result_report(
    *,
    status: str,
    plan_check: dict[str, Any],
    input_check: dict[str, Any],
    variants: list[dict[str, Any]],
    plan_path: Path | None,
    manifest_path: Path | None,
    oracle_report: Path,
    scenario_bucket_manifest: Path,
    output_dir: Path,
    selector_prefix: str,
    reason: str | None,
) -> dict[str, Any]:
    accepted = [
        row["name"] for row in variants if row.get("accepted_for_next_review") is True
    ]
    complete = status == COMPLETE_STATUS
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_objective_label_sensitivity_dry_run_v1",
            "selector_prefix": selector_prefix,
            "training": complete,
            "training_scope": (
                "offline finite sensitivity wrapper over frozen nonformal manifest"
            ),
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "plan_json": None if plan_path is None else str(plan_path),
            "manifest_json": None if manifest_path is None else str(manifest_path),
            "oracle_report": str(oracle_report),
            "scenario_bucket_manifest": str(scenario_bucket_manifest),
            "output_dir": str(output_dir),
            "math_boundary": (
                "This wrapper only runs predeclared offline CAMP weight "
                "sensitivity variants over fixed logged DP candidate atoms and "
                "offline SafetyCost labels. Candidate scores remain affine "
                "a_k^T w with simplex/L2/CVaR training. The wrapper does not run "
                "or modify DP, does not use future outcomes online, and is not "
                "a classical Benders claim."
            ),
        },
        "plan_check": plan_check,
        "input_check": input_check,
        "variants": variants,
        "summary": {
            "variants_total": len(variants),
            "variants_complete": sum(
                int(row.get("status") == "variant_complete") for row in variants
            ),
            "accepted_for_next_review": accepted,
            "rejected_or_blocked": [
                row["name"] for row in variants if row["name"] not in accepted
            ],
        },
        "final_decision": {
            "status": status,
            "passed": complete,
            "reason": reason,
            "authorized_next_work": (
                "review_objective_label_sensitivity_candidate_before_any_replay"
                if complete and accepted
                else (
                    "diagnose_objective_label_sensitivity_results"
                    if complete
                    else None
                )
            ),
            "accepted_variants": accepted,
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
        "# Offline Convex Objective/Label Sensitivity Dry Run",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- accepted variants: `{', '.join(decision['accepted_variants']) or 'none'}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Inputs",
        "",
        f"- plan errors: `{', '.join(report['plan_check'].get('errors', [])) or 'none'}`",
        f"- manifest errors: `{', '.join(report['input_check'].get('errors', [])) or 'none'}`",
        f"- logs: `{len(report['input_check'].get('logs', []))}`",
        "",
        "## Variants",
        "",
        "| Variant | Role | Status | Accepted | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["variants"]:
        lines.append(
            f"| `{row['name']}` | `{row['role']}` | `{row['status']}` | "
            f"`{row['accepted_for_next_review']}` | `{row['reason']}` |"
        )
    lines.extend(["", "## Artifacts", "", "| Variant | Artifact | SHA-256 |", "| --- | --- | --- |"])
    for row in report["variants"]:
        for name, artifact in row.get("artifacts", {}).items():
            lines.append(f"| `{row['name']}` | `{name}` | `{artifact['sha256']}` |")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_map(*paths: Path) -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {}
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


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
