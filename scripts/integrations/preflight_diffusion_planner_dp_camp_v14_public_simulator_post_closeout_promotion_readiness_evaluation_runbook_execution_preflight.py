#!/usr/bin/env python3
"""Read-only v14 promotion-readiness evaluation runbook execution preflight.

This gate consumes the audited runbook plan static review and its
source plan artifact. It checks artifact immutability, fixed-DP provenance,
EOF authorization, and no-go conditions for a future promotion-readiness
evaluation runbook execution discussion. It does not run evaluation, replay, training,
candidate generation, promotion, deployment, online selector activation,
Diffusion Planner modification, or safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_plan_static_review_v1"
)
SOURCE_PLAN_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_runbook_execution_preflight_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_ready"
)
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_only"
)

STATIC_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.json"
)
STATIC_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review.md"
)
PLAN_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_plan.json"
PLAN_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_plan.md"
PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight.md"

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "replay_execution_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)
EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
    "evaluation_runbook_executed_by_this_gate",
)
ANALYSIS_FALSE_FLAGS = (
    "training_execution",
    "replay_execution",
    "candidate_generation",
    "dp_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
    "evaluation_runbook_execution",
)
EXPECTED_RUNBOOK_PREFLIGHT_STEPS = (
    "lock_source_artifacts_and_heads",
    "load_fixed_dp_candidate_tensor_outputs_read_only",
    "apply_default_off_shadow_selector_without_output_effect",
    "compute_predeclared_metrics_and_uncertainty",
    "evaluate_fail_closed_and_no_go_conditions",
    "construct_nonclaim_evidence_matrix",
    "emit_static_review_ready_runbook_plan_artifact",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook_plan_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--runbook_plan_static_review_json", type=Path, required=True)
    parser.add_argument("--runbook_plan_static_review_md", type=Path, required=True)
    parser.add_argument("--runbook_plan_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_runbook_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_runbook_plan_json", type=Path, required=True)
    parser.add_argument("--source_runbook_plan_md", type=Path, required=True)
    parser.add_argument("--source_runbook_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight",
        action="store_true",
        help="Explicit opt-in for read-only promotion-readiness evaluation runbook execution preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runbook_plan_static_review_artifact_dir=args.runbook_plan_static_review_artifact_dir,
        runbook_plan_static_review_json=args.runbook_plan_static_review_json,
        runbook_plan_static_review_md=args.runbook_plan_static_review_md,
        runbook_plan_static_review_sha256s=args.runbook_plan_static_review_sha256s,
        source_runbook_plan_artifact_dir=args.source_runbook_plan_artifact_dir,
        source_runbook_plan_json=args.source_runbook_plan_json,
        source_runbook_plan_md=args.source_runbook_plan_md,
        source_runbook_plan_sha256s=args.source_runbook_plan_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runbook_plan_static_review_artifact_dir: Path,
    runbook_plan_static_review_json: Path,
    runbook_plan_static_review_md: Path,
    runbook_plan_static_review_sha256s: Path,
    source_runbook_plan_artifact_dir: Path,
    source_runbook_plan_json: Path,
    source_runbook_plan_md: Path,
    source_runbook_plan_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    static_artifact = runbook_plan_static_review_artifact_dir.resolve()
    plan_artifact = source_runbook_plan_artifact_dir.resolve()
    paths = {
        "runbook_plan_static_review_json": runbook_plan_static_review_json.resolve(),
        "runbook_plan_static_review_md": runbook_plan_static_review_md.resolve(),
        "runbook_plan_static_review_sha256s": runbook_plan_static_review_sha256s.resolve(),
        "source_runbook_plan_json": source_runbook_plan_json.resolve(),
        "source_runbook_plan_md": source_runbook_plan_md.resolve(),
        "source_runbook_plan_sha256s": source_runbook_plan_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_artifact_files = {
        "command": static_artifact / "COMMAND",
        "heads": static_artifact / "HEADS",
        "stdout": static_artifact / "stdout.txt",
        "stderr": static_artifact / "stderr.txt",
        "run_exit": static_artifact / "run.exit",
        "root_sha256s": static_artifact / "SHA256SUMS",
        "review_json": static_artifact / "review" / STATIC_REVIEW_JSON_NAME,
        "review_md": static_artifact / "review" / STATIC_REVIEW_MD_NAME,
        "review_sha256s": static_artifact / "review" / "SHA256SUMS",
    }
    plan_artifact_files = {
        "command": plan_artifact / "COMMAND",
        "heads": plan_artifact / "HEADS",
        "stdout": plan_artifact / "stdout.txt",
        "stderr": plan_artifact / "stderr.txt",
        "run_exit": plan_artifact / "run.exit",
        "root_sha256s": plan_artifact / "SHA256SUMS",
        "plan_json": plan_artifact / "plan" / PLAN_JSON_NAME,
        "plan_md": plan_artifact / "plan" / PLAN_MD_NAME,
        "plan_sha256s": plan_artifact / "plan" / "SHA256SUMS",
    }
    static_review = _read_json_dict(paths["runbook_plan_static_review_json"])
    source_plan = _read_json_dict(paths["source_runbook_plan_json"])
    static_root_sha256s = _read_sha256sums(static_artifact_files["root_sha256s"])
    static_review_sha256s = _read_sha256sums(paths["runbook_plan_static_review_sha256s"])
    plan_root_sha256s = _read_sha256sums(plan_artifact_files["root_sha256s"])
    source_plan_sha256s = _read_sha256sums(paths["source_runbook_plan_sha256s"])
    static_heads = _parse_key_values(_read_text(static_artifact_files["heads"]))
    plan_heads = _parse_key_values(_read_text(plan_artifact_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("runbook_execution_preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_plan_artifact_dir_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_artifact_files.items():
        checks.extend(_path_checks(f"static_review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in plan_artifact_files.items():
        checks.extend(_path_checks(f"source_plan_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["runbook_plan_static_review_json"], static_artifact_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["runbook_plan_static_review_md"], static_artifact_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["runbook_plan_static_review_sha256s"], static_artifact_files["review_sha256s"]),
            _expect("source_plan_json_matches_artifact_layout", paths["source_runbook_plan_json"], plan_artifact_files["plan_json"]),
            _expect("source_plan_md_matches_artifact_layout", paths["source_runbook_plan_md"], plan_artifact_files["plan_md"]),
            _expect("source_plan_sha256s_matches_artifact_layout", paths["source_runbook_plan_sha256s"], plan_artifact_files["plan_sha256s"]),
        ]
    )
    checks.extend(_static_review_artifact_hash_checks(static_artifact_files, static_root_sha256s, static_review_sha256s))
    checks.extend(_source_plan_artifact_hash_checks(plan_artifact_files, plan_root_sha256s, source_plan_sha256s))
    checks.extend(_static_heads_checks(static_heads, static_review, plan_artifact))
    checks.extend(_source_plan_heads_checks(plan_heads, source_plan))
    checks.extend(_static_review_contract_checks(static_review))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "preflight_only": True,
            "read_only": True,
            "runbook_plan_static_review_artifact_dir": str(static_artifact),
            "source_runbook_plan_artifact_dir": str(plan_artifact),
            "runbook_plan_static_review_json": str(paths["runbook_plan_static_review_json"]),
            "source_runbook_plan_json": str(paths["source_runbook_plan_json"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "math_boundary": (
                "This read-only runbook execution preflight keeps CAMP as a default-off "
                f"shadow reranker with affine {SCORE_EXPRESSION} over approved "
                "atoms and nonnegative simplex weights. It authorizes only "
                "static review of the runbook execution preflight artifact."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **static_artifact_files, **plan_artifact_files}.items()
        },
        "source_static_review_summary": _static_review_summary(static_review),
        "source_runbook_plan_summary": _source_plan_summary(source_plan),
        "runbook_execution_preflight": _runbook_execution_preflight(),
        "artifact_manifest_requirements": _artifact_manifest_requirements(),
        "no_go_status": _no_go_status(),
        "future_review_requirements": _future_review_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / PREFLIGHT_JSON_NAME, report)
    (output_dir / PREFLIGHT_MD_NAME).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Runbook preflight checks: `{len(report['runbook_execution_preflight'])}`",
        f"- Artifact manifest requirements: `{len(report['artifact_manifest_requirements'])}`",
        f"- No-go conditions false: `{all(not item['triggered'] for item in report['no_go_status'])}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Runbook Execution Preflight",
        "",
    ]
    for item in report["runbook_execution_preflight"]:
        lines.append(f"- `{item['name']}`: `{item['status']}`")
    lines.extend(["", "## Artifact Manifest Requirements", ""])
    for item in report["artifact_manifest_requirements"]:
        lines.append(f"- `{item['name']}`: `{item['status']}`")
    lines.extend(["", "## No-Go Status", ""])
    for item in report["no_go_status"]:
        lines.append(f"- `{item['name']}`: triggered=`{item['triggered']}`")
    lines.extend(
        [
            "",
            "This preflight did not run evaluation, replay, training, candidate "
            "generation, promotion, deployment, online selector activation, DP "
            "modification, or safety/CAMP-over-DP claim construction.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["preflight_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _static_review_artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    root_expected = {
        "command": ("COMMAND", "./COMMAND"),
        "heads": ("HEADS", "./HEADS"),
        "stdout": ("stdout.txt", "./stdout.txt"),
        "stderr": ("stderr.txt", "./stderr.txt"),
        "run_exit": ("run.exit", "./run.exit"),
        "review_json": (STATIC_REVIEW_JSON_NAME, f"review/{STATIC_REVIEW_JSON_NAME}", f"./review/{STATIC_REVIEW_JSON_NAME}"),
        "review_md": (STATIC_REVIEW_MD_NAME, f"review/{STATIC_REVIEW_MD_NAME}", f"./review/{STATIC_REVIEW_MD_NAME}"),
    }
    checks = [
        _check("static_review_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"),
        _check("static_review_review_sha256s_parseable", bool(review_sha256s), sorted(review_sha256s), "nonempty"),
    ]
    for name, keys in root_expected.items():
        checks.append(_sha256sums_expect(f"static_review_artifact_{name}_root_sha", files[name], root_sha256s, keys))
    checks.extend(
        [
            _sha256sums_expect_optional(
                "static_review_artifact_review_sha256s_root_sha",
                files["review_sha256s"],
                root_sha256s,
                ("review/SHA256SUMS", "./review/SHA256SUMS"),
            ),
            _sha256sums_expect("static_review_report_json_review_sha", files["review_json"], review_sha256s, (STATIC_REVIEW_JSON_NAME, f"./{STATIC_REVIEW_JSON_NAME}")),
            _sha256sums_expect("static_review_report_md_review_sha", files["review_md"], review_sha256s, (STATIC_REVIEW_MD_NAME, f"./{STATIC_REVIEW_MD_NAME}")),
            _expect("static_review_artifact_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
        ]
    )
    return checks


def _source_plan_artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    root_expected = {
        "command": ("COMMAND", "./COMMAND"),
        "heads": ("HEADS", "./HEADS"),
        "stdout": ("stdout.txt", "./stdout.txt"),
        "stderr": ("stderr.txt", "./stderr.txt"),
        "run_exit": ("run.exit", "./run.exit"),
        "plan_json": (PLAN_JSON_NAME, f"plan/{PLAN_JSON_NAME}", f"./plan/{PLAN_JSON_NAME}"),
        "plan_md": (PLAN_MD_NAME, f"plan/{PLAN_MD_NAME}", f"./plan/{PLAN_MD_NAME}"),
        "plan_sha256s": ("SHA256SUMS", "plan/SHA256SUMS", "./plan/SHA256SUMS"),
    }
    checks = [
        _check("source_plan_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"),
        _check("source_plan_sha256s_parseable", bool(plan_sha256s), sorted(plan_sha256s), "nonempty"),
    ]
    for name, keys in root_expected.items():
        checks.append(_sha256sums_expect(f"source_plan_artifact_{name}_root_sha", files[name], root_sha256s, keys))
    checks.extend(
        [
            _sha256sums_expect("source_plan_json_plan_sha", files["plan_json"], plan_sha256s, (PLAN_JSON_NAME, f"./{PLAN_JSON_NAME}")),
            _sha256sums_expect("source_plan_md_plan_sha", files["plan_md"], plan_sha256s, (PLAN_MD_NAME, f"./{PLAN_MD_NAME}")),
            _expect("source_plan_artifact_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
        ]
    )
    return checks


def _static_heads_checks(
    heads: dict[str, str],
    static_review: dict[str, Any],
    source_plan_artifact: Path,
) -> list[dict[str, Any]]:
    analysis = _dict(static_review.get("analysis"))
    return [
        _expect("static_review_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("static_review_heads_camp_head_is_sha", _is_git_sha(str(heads.get("camp_head", ""))), heads.get("camp_head"), "40-char git sha"),
        _check("static_review_heads_camp_origin_is_sha", _is_git_sha(str(heads.get("camp_origin_main", ""))), heads.get("camp_origin_main"), "40-char git sha"),
        _expect("static_review_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect("static_review_heads_source_plan_artifact", heads.get("source_runbook_plan_artifact"), str(source_plan_artifact)),
        _expect("static_review_analysis_source_plan_artifact", analysis.get("runbook_plan_artifact_dir"), str(source_plan_artifact)),
    ]


def _source_plan_heads_checks(heads: dict[str, str], source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(source_plan.get("analysis"))
    return [
        _expect("source_plan_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("source_plan_heads_camp_head_is_sha", _is_git_sha(str(heads.get("camp_head", ""))), heads.get("camp_head"), "40-char git sha"),
        _check("source_plan_heads_camp_origin_is_sha", _is_git_sha(str(heads.get("camp_origin_main", ""))), heads.get("camp_origin_main"), "40-char git sha"),
        _expect("source_plan_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect(
            "source_plan_heads_source_preflight_static_review",
            heads.get("source_runbook_preflight_static_review_artifact"),
            analysis.get("runbook_preflight_static_review_artifact_dir"),
        ),
        _expect(
            "source_plan_heads_source_preflight",
            heads.get("source_runbook_preflight_artifact"),
            analysis.get("source_runbook_preflight_artifact_dir"),
        ),
        _expect("source_plan_analysis_current_dp_fixed", analysis.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("source_plan_analysis_required_dp_fixed", analysis.get("required_dp_head"), FIXED_DP_HEAD),
    ]


def _static_review_contract_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    analysis = _dict(static_review.get("analysis"))
    checks = [
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_runbook_execution_preflight_authorized", decision.get("evaluation_runbook_execution_preflight_authorized"), True),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_static_review_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_read_only", analysis.get("read_only"), True),
        _expect("source_static_review_check_failures", _failed_source_checks(static_review, "review_checks"), []),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        observed = analysis.get(flag)
        if flag == "evaluation_runbook_execution" and flag not in analysis:
            observed = False
        checks.append(_expect(f"source_static_review_analysis_{flag}", observed, False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_static_review_blocked_{action}", _dict(static_review.get("blocked_actions")).get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    analysis = _dict(source_plan.get("analysis"))
    checks = [
        _expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        _expect("source_plan_failure_class", decision.get("failure_class"), None),
        _expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_static_review_authorized", decision.get("evaluation_runbook_plan_static_review_authorized"), True),
        _expect("source_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_plan_only", analysis.get("plan_only"), True),
        _expect("source_plan_read_only", analysis.get("read_only"), True),
        _expect("source_plan_runbook_steps", _names(source_plan.get("runbook_plan")), list(EXPECTED_RUNBOOK_PREFLIGHT_STEPS)),
        _expect("source_plan_artifact_count", len(_list(source_plan.get("planned_artifacts"))), 9),
        _expect("source_plan_metrics_count", len(_list(source_plan.get("metrics_plan"))), 6),
        _expect("source_plan_decision_criteria_count", len(_list(source_plan.get("decision_criteria_plan"))), 6),
        _expect("source_plan_no_go_count", len(_list(source_plan.get("no_go_conditions"))), 8),
        _expect("source_plan_forbidden_action_count", len(_list(source_plan.get("forbidden_actions"))), 10),
        _expect("source_plan_future_review_count", len(_list(source_plan.get("future_review_requirements"))), 4),
        _expect("source_plan_check_failures", _failed_source_checks(source_plan, "plan_checks"), []),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_plan_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_plan_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_plan_blocked_{action}", _dict(source_plan.get("blocked_actions")).get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_STATIC_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_runbook_execution_preflight", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_runbook_execution_preflight", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_runbook_plan_static_review_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed"), "True"),
        _expect("audit_runbook_execution_preflight_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_authorized"), "True"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _runbook_execution_preflight() -> list[dict[str, str]]:
    return [
        {"name": "source_artifact_inventory", "status": "ready_for_static_review_only"},
        {"name": "fixed_dp_candidate_tensor_boundary", "status": "ready_for_static_review_only"},
        {"name": "split_seed_zero_overlap_boundary", "status": "ready_for_static_review_only"},
        {"name": "default_off_shadow_selector_no_output_effect_boundary", "status": "ready_for_static_review_only"},
        {"name": "metric_uncertainty_and_no_claim_boundary", "status": "ready_for_static_review_only"},
        {"name": "execution_command_dry_run_boundary", "status": "ready_for_static_review_only"},
        {"name": "claim_promotion_deployment_stop_boundary", "status": "ready_for_static_review_only"},
    ]


def _artifact_manifest_requirements() -> list[dict[str, str]]:
    return [
        {"name": "HEADS", "status": "required"},
        {"name": "COMMAND", "status": "required"},
        {"name": "stdout_stderr", "status": "required"},
        {"name": "run_exit", "status": "required"},
        {"name": "SHA256SUMS", "status": "required"},
        {"name": "source_static_review_json_md_sha256s", "status": "required"},
        {"name": "source_plan_json_md_sha256s", "status": "required"},
    ]


def _no_go_status() -> list[dict[str, Any]]:
    return [
        {"name": "dp_head_drift", "triggered": False},
        {"name": "camp_trajectory_generation_or_modification", "triggered": False},
        {"name": "closed_loop_outcome_input", "triggered": False},
        {"name": "full36_or_formal_seed_11_12_13", "triggered": False},
        {"name": "non_affine_score", "triggered": False},
        {"name": "non_simplex_or_nonconvex_master", "triggered": False},
        {"name": "promotion_deployment_online_selector_or_claim_bundled", "triggered": False},
        {"name": "safety_or_camp_over_dp_claim_bundled", "triggered": False},
    ]


def _future_review_requirements() -> list[dict[str, str]]:
    return [
        {"name": "runbook_execution_preflight_static_review", "status": "required_before_any_evaluation_runbook_execution"},
        {"name": "source_artifact_hash_review", "status": "must_confirm_static_review_and_plan_artifacts"},
        {"name": "authorization_boundary_review", "status": "must_keep_promotion_deployment_online_and_claims_false"},
        {"name": "fixed_dp_math_boundary_review", "status": "must_confirm_fixed_dp_affine_simplex_convex_boundary"},
    ]


def _static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    return {
        "schema_version": static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(static_review.get("review_checks"))),
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(_list(source_plan.get("plan_checks"))),
        "runbook_step_count": len(_list(source_plan.get("runbook_plan"))),
        "artifact_count": len(_list(source_plan.get("planned_artifacts"))),
        "metrics_count": len(_list(source_plan.get("metrics_plan"))),
        "decision_criteria_count": len(_list(source_plan.get("decision_criteria_plan"))),
        "no_go_condition_count": len(_list(source_plan.get("no_go_conditions"))),
        "forbidden_action_count": len(_list(source_plan.get("forbidden_actions"))),
        "future_review_count": len(_list(source_plan.get("future_review_requirements"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready": bool(passed),
        "evaluation_runbook_execution_preflight_static_review_authorized": bool(passed),
        "evaluation_runbook_execution_authorized": False,
        "recommendation": "static_review_this_runbook_execution_preflight_only",
        "immediate_action": "static_review_promotion_readiness_evaluation_runbook_execution_preflight_only",
        "score_expression": SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
        "evaluation_runbook_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "runbook_execution_preflight_enabled" in failed_set:
        return "explicit_runbook_execution_preflight_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "static_review_heads_dp_fixed", "source_plan_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_static_review_") for name in failed):
        return "source_static_review_contract_failure"
    if any(name.startswith("source_plan_") for name in failed):
        return "source_runbook_plan_contract_failure"
    if any(name.startswith("static_review_heads_") or name.startswith("source_plan_heads_") for name in failed):
        return "source_artifact_heads_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_evaluation_runbook_execution_preflight_failure"


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.is_dir()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "directory")]
    if require_file and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.is_file() and path.stat().st_size > 0, path.stat().st_size if path.is_file() else None, ">0 bytes"))
    return checks


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    listed = [sha256sums.get(key) for key in keys if key in sha256sums]
    return _check(
        name,
        observed is not None and observed in listed,
        {"observed": observed, "listed": listed, "keys": keys},
        "matching sha256 listed in SHA256SUMS",
    )


def _sha256sums_expect_optional(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    present_keys = [key for key in keys if key in sha256sums]
    listed = [sha256sums.get(key) for key in present_keys]
    return _check(
        name,
        observed is not None and (not present_keys or observed in listed),
        {"observed": observed, "listed": listed, "keys": keys},
        "omitted from SHA256SUMS or matching sha256 listed",
    )


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            key = parts[1].strip()
            value = parts[0]
            values[key] = value
            values[key.removeprefix("./")] = value
            values[Path(key).name] = value
    return values


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        values[key] = value
        values[key.lower()] = value
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _names(value: Any) -> list[str]:
    return [
        str(item.get("name"))
        for item in _list(value)
        if isinstance(item, dict) and item.get("name")
    ]


def _failed_source_checks(payload: dict[str, Any], field: str) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(payload.get(field))
        if isinstance(check, dict) and not check.get("passed")
    ]


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())

