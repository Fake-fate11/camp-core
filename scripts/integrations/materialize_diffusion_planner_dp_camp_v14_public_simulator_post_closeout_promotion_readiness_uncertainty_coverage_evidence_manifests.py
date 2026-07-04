#!/usr/bin/env python3
"""Materialize v14 uncertainty/coverage evidence manifests from an audited plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REVIEW_MODULE = _load_review_module()
PLAN_MODULE = REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = REVIEW_MODULE.READY_STATUS
SOURCE_PLAN_SCHEMA = REVIEW_MODULE.SOURCE_PLAN_SCHEMA
SOURCE_PLAN_STATUS = REVIEW_MODULE.SOURCE_PLAN_STATUS
AUTHORIZED_CURRENT_WORK = REVIEW_MODULE.AUTHORIZED_NEXT_WORK
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_manifest_materialization_v1"
)
MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_manifest_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialized"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_only"
)
SOURCE_REVIEW_JSON_NAME = REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_PLAN_JSON_NAME = REVIEW_MODULE.SOURCE_PLAN_JSON_NAME
REPORT_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization.json"
)
REPORT_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization.md"
)
EXPECTED_MANIFESTS = REVIEW_MODULE.EXPECTED_MANIFESTS
EXPECTED_REVIEW_CHECK_COUNT = 153
EXPECTED_SOURCE_PLAN_CHECK_COUNT = 139
EXPECTED_SOURCE_MANIFEST_COUNT = 5
BLOCKED_ACTIONS = REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = REVIEW_MODULE.FALSE_EXECUTION_FLAGS
FALSE_EXECUTION_FLAGS = tuple(
    flag for flag in FALSE_EXECUTION_FLAGS if flag != "evidence_manifest_materialized_by_this_gate"
)
ANALYSIS_FALSE_FLAGS = REVIEW_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialization_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--materialization_static_review_json", type=Path, required=True)
    parser.add_argument("--materialization_static_review_md", type=Path, required=True)
    parser.add_argument("--materialization_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--manifest_output_dir", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization",
        action="store_true",
        help="Explicit opt-in to materialize uncertainty/coverage evidence manifests.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        materialization_static_review_artifact_dir=args.materialization_static_review_artifact_dir,
        materialization_static_review_json=args.materialization_static_review_json,
        materialization_static_review_md=args.materialization_static_review_md,
        materialization_static_review_sha256s=args.materialization_static_review_sha256s,
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        manifest_output_dir=args.manifest_output_dir,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization
        ),
    )
    write_outputs(args.output_dir, args.manifest_output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    materialization_static_review_artifact_dir: Path,
    materialization_static_review_json: Path,
    materialization_static_review_md: Path,
    materialization_static_review_sha256s: Path,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_sha256s: Path,
    manifest_output_dir: Path,
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
    review_artifact_dir = materialization_static_review_artifact_dir.resolve()
    plan_artifact_dir = source_plan_artifact_dir.resolve()
    manifest_dir = manifest_output_dir.resolve()
    paths = {
        "materialization_static_review_json": materialization_static_review_json.resolve(),
        "materialization_static_review_md": materialization_static_review_md.resolve(),
        "materialization_static_review_sha256s": materialization_static_review_sha256s.resolve(),
        "source_plan_json": source_plan_json.resolve(),
        "source_plan_sha256s": source_plan_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    review_artifact_files = {
        "command": review_artifact_dir / "COMMAND",
        "heads": review_artifact_dir / "HEADS",
        "stdout": review_artifact_dir / "stdout.txt",
        "stderr": review_artifact_dir / "stderr.txt",
        "run_exit": review_artifact_dir / "run.exit",
        "root_sha256s": review_artifact_dir / "SHA256SUMS",
        "review_json": review_artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": review_artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": review_artifact_dir / "review" / "SHA256SUMS",
    }
    plan_artifact_files = {
        "plan_json": plan_artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_sha256s": plan_artifact_dir / "plan" / "SHA256SUMS",
        "root_sha256s": plan_artifact_dir / "SHA256SUMS",
    }

    source_review = PLAN_MODULE._read_json_dict(paths["materialization_static_review_json"])
    source_plan = PLAN_MODULE._read_json_dict(paths["source_plan_json"])
    review_root_sha256s = PLAN_MODULE._read_sha256sums(review_artifact_files["root_sha256s"])
    review_sha256s = PLAN_MODULE._read_sha256sums(paths["materialization_static_review_sha256s"])
    plan_sha256s = PLAN_MODULE._read_sha256sums(paths["source_plan_sha256s"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(review_artifact_files["heads"]))
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        PLAN_MODULE._expect("materialization_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._check("static_review_artifact_dir_exists", review_artifact_dir.is_dir(), str(review_artifact_dir), "directory"),
        PLAN_MODULE._check("source_plan_artifact_dir_exists", plan_artifact_dir.is_dir(), str(plan_artifact_dir), "directory"),
        PLAN_MODULE._check("manifest_output_dir_absent_before_write", not manifest_dir.exists(), str(manifest_dir), "absent"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, require_file=True))
    for name, path in review_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in plan_artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"plan_artifact_{name}", path, require_file=True))
    checks.extend(
        [
            PLAN_MODULE._expect("static_review_json_matches_artifact_layout", paths["materialization_static_review_json"], review_artifact_files["review_json"]),
            PLAN_MODULE._expect("static_review_md_matches_artifact_layout", paths["materialization_static_review_md"], review_artifact_files["review_md"]),
            PLAN_MODULE._expect("static_review_sha256s_matches_artifact_layout", paths["materialization_static_review_sha256s"], review_artifact_files["review_sha256s"]),
            PLAN_MODULE._expect("source_plan_json_matches_artifact_layout", paths["source_plan_json"], plan_artifact_files["plan_json"]),
            PLAN_MODULE._expect("source_plan_sha256s_matches_artifact_layout", paths["source_plan_sha256s"], plan_artifact_files["plan_sha256s"]),
        ]
    )
    checks.extend(_review_artifact_hash_checks(review_artifact_files, review_root_sha256s, review_sha256s))
    checks.extend(_plan_artifact_hash_checks(plan_artifact_files, plan_sha256s))
    checks.extend(_heads_checks(heads, source_review))
    checks.extend(_source_review_contract_checks(source_review))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_audit_checks(v14_text, status_text))

    manifest_payloads = _manifest_payloads(
        source_plan=source_plan,
        source_review=source_review,
        manifest_output_dir=manifest_dir,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        label=label,
    )
    checks.extend(_manifest_contract_checks(manifest_payloads))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "materialization_only": True,
            "read_only_source_review": True,
            "static_review_artifact_dir": str(review_artifact_dir),
            "source_plan_artifact_dir": str(plan_artifact_dir),
            "manifest_output_dir": str(manifest_dir),
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
            "score_expression": SCORE_EXPRESSION,
        },
        "source_hashes": {
            name: PLAN_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **review_artifact_files, **plan_artifact_files}.items()
        },
        "source_review_summary": _source_review_summary(source_review),
        "source_plan_summary": _source_plan_summary(source_plan),
        "evidence_manifests": manifest_payloads,
        "materialized_manifest_files": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "materialization_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, manifest_output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    materialized_files: list[dict[str, Any]] = []
    if report["final_decision"]["passed"]:
        manifest_output_dir.mkdir(parents=True, exist_ok=False)
        for manifest in report["evidence_manifests"]:
            path = manifest_output_dir / f"{manifest['manifest_name']}.json"
            PLAN_MODULE._write_json(path, manifest)
            materialized_files.append(
                {
                    "manifest_name": manifest["manifest_name"],
                    "path": str(path.resolve()),
                    "sha256": PLAN_MODULE._sha256(path),
                }
            )
        PLAN_MODULE._write_sha256sums(manifest_output_dir)
    report["materialized_manifest_files"] = materialized_files
    PLAN_MODULE._write_json(output_dir / REPORT_JSON_NAME, report)
    (output_dir / REPORT_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    PLAN_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        f"- materialized_manifest_count: `{len(report['materialized_manifest_files'])}`",
        "",
        "## Materialized Files",
    ]
    for item in report["materialized_manifest_files"]:
        lines.append(f"- `{item['manifest_name']}`: `{item['path']}` `{item['sha256']}`")
    lines.extend(["", "## Checks"])
    for check in report["materialization_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{PLAN_MODULE._compact(check['observed'])}` expected=`{PLAN_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _review_artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect("review_artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect("review_artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect("review_artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect("review_artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect("review_artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect("review_artifact_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{SOURCE_REVIEW_JSON_NAME}", f"./review/{SOURCE_REVIEW_JSON_NAME}", SOURCE_REVIEW_JSON_NAME)),
        PLAN_MODULE._sha256sums_expect("review_artifact_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{SOURCE_REVIEW_MD_NAME}", f"./review/{SOURCE_REVIEW_MD_NAME}", SOURCE_REVIEW_MD_NAME)),
        PLAN_MODULE._sha256sums_expect("source_review_json_review_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        PLAN_MODULE._sha256sums_expect("source_review_md_review_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
        PLAN_MODULE._expect("review_artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _plan_artifact_hash_checks(
    artifact_files: dict[str, Path],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._sha256sums_expect("source_plan_json_plan_sha", artifact_files["plan_json"], plan_sha256s, (SOURCE_PLAN_JSON_NAME, f"./{SOURCE_PLAN_JSON_NAME}")),
    ]


def _heads_checks(heads: dict[str, str], source_review: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = PLAN_MODULE._dict(source_review.get("analysis"))
    return [
        PLAN_MODULE._expect("review_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        PLAN_MODULE._expect("review_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        PLAN_MODULE._expect("review_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        PLAN_MODULE._expect("review_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_review_contract_checks(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    summary = PLAN_MODULE._dict(source_review.get("source_plan_summary"))
    checks = [
        PLAN_MODULE._expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        PLAN_MODULE._expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        PLAN_MODULE._expect("source_review_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_review_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_review_authorizes_materialization", decision.get("evidence_manifest_materialization_authorized"), True),
        PLAN_MODULE._expect("source_review_materialized_by_gate_false", decision.get("evidence_manifest_materialized_by_this_gate"), False),
        PLAN_MODULE._expect("source_review_check_count", len(PLAN_MODULE._list(source_review.get("review_checks"))), EXPECTED_REVIEW_CHECK_COUNT),
        PLAN_MODULE._expect("source_review_plan_check_count", summary.get("plan_check_count"), EXPECTED_SOURCE_PLAN_CHECK_COUNT),
        PLAN_MODULE._expect("source_review_manifest_count", summary.get("manifest_plan_item_count"), EXPECTED_SOURCE_MANIFEST_COUNT),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_review_decision_{action}", decision.get(action), False))
    return checks


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    manifests = PLAN_MODULE._list(source_plan.get("evidence_manifest_materialization_plan"))
    names = [PLAN_MODULE._dict(item).get("manifest_name") for item in manifests]
    return [
        PLAN_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        PLAN_MODULE._expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("source_plan_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_plan_authorized_static_review", decision.get("authorized_next_work"), REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_plan_manifest_names", names, list(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("source_plan_manifest_count", len(manifests), EXPECTED_SOURCE_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_plan_no_materialization", [PLAN_MODULE._dict(item).get("materialized_by_this_gate") for item in manifests], [False] * len(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("source_plan_no_execution", [PLAN_MODULE._dict(item).get("authorizes_execution") for item in manifests], [False] * len(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("source_plan_no_claim", [PLAN_MODULE._dict(item).get("authorizes_claim") for item in manifests], [False] * len(EXPECTED_MANIFESTS)),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("audit_latest_status_is_static_review_passed", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        PLAN_MODULE._expect("audit_latest_eof_authorizes_materialization", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("audit_manifest_materialization_authorized", PLAN_MODULE._latest_value(v14_text, "evidence_manifest_materialization_authorized"), "True"),
        PLAN_MODULE._expect("audit_manifest_not_materialized_yet", PLAN_MODULE._latest_value(v14_text, "evidence_manifest_materialized_by_this_gate"), "False"),
        PLAN_MODULE._expect("status_doc_latest_status_is_static_review_passed", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        PLAN_MODULE._expect("status_doc_latest_eof_authorizes_materialization", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("status_doc_mentions_materialization_next", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _manifest_payloads(
    *,
    source_plan: dict[str, Any],
    source_review: dict[str, Any],
    manifest_output_dir: Path,
    current_camp_head: str,
    current_dp_head: str,
    label: str | None,
) -> list[dict[str, Any]]:
    source_decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    source_plan_items = [PLAN_MODULE._dict(item) for item in PLAN_MODULE._list(source_plan.get("evidence_manifest_materialization_plan"))]
    payloads = []
    for item in source_plan_items:
        name = item.get("manifest_name")
        payloads.append(
            {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "manifest_name": name,
                "label": label,
                "source_gap": item.get("source_gap"),
                "source_planned_path": item.get("planned_path"),
                "materialized_path": str((manifest_output_dir / f"{name}.json").resolve()),
                "required_inputs": item.get("required_inputs", []),
                "acceptance_checks": item.get("acceptance_checks", []),
                "source_static_review_status": source_decision.get("status"),
                "source_static_review_authorized_next_work": source_decision.get("authorized_next_work"),
                "current_camp_head": current_camp_head,
                "current_dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "score_expression": SCORE_EXPRESSION,
                "materialized_by_this_gate": True,
                "authorizes_execution": False,
                "authorizes_claim": False,
                "training_execution": False,
                "replay_execution": False,
                "candidate_generation": False,
                "dp_modification": False,
                "online_selector_change": False,
                "promotion_executed": False,
                "deployment_executed": False,
                "safety_or_camp_over_dp_claim": False,
            }
        )
    return payloads


def _manifest_contract_checks(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = [manifest.get("manifest_name") for manifest in manifests]
    checks = [
        PLAN_MODULE._expect("manifest_count", len(manifests), len(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("manifest_names", names, list(EXPECTED_MANIFESTS)),
    ]
    for manifest in manifests:
        name = str(manifest.get("manifest_name"))
        checks.extend(
            [
                PLAN_MODULE._expect(f"manifest_{name}_schema", manifest.get("schema_version"), MANIFEST_SCHEMA_VERSION),
                PLAN_MODULE._expect(f"manifest_{name}_dp_fixed", manifest.get("current_dp_head"), FIXED_DP_HEAD),
                PLAN_MODULE._expect(f"manifest_{name}_required_dp_fixed", manifest.get("required_dp_head"), FIXED_DP_HEAD),
                PLAN_MODULE._expect(f"manifest_{name}_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
                PLAN_MODULE._expect(f"manifest_{name}_materialized", manifest.get("materialized_by_this_gate"), True),
                PLAN_MODULE._expect(f"manifest_{name}_no_execution", manifest.get("authorizes_execution"), False),
                PLAN_MODULE._expect(f"manifest_{name}_no_claim", manifest.get("authorizes_claim"), False),
            ]
        )
        for flag in ANALYSIS_FALSE_FLAGS:
            checks.append(PLAN_MODULE._expect(f"manifest_{name}_{flag}", manifest.get(flag), False))
    return checks


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(PLAN_MODULE._list(source_review.get("review_checks"))),
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    manifests = PLAN_MODULE._list(source_plan.get("evidence_manifest_materialization_plan"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(PLAN_MODULE._list(source_plan.get("plan_checks"))),
        "manifest_plan_item_count": len(manifests),
        "manifest_names": [PLAN_MODULE._dict(item).get("manifest_name") for item in manifests],
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "materialization_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_manifest_materialization_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif "manifest_output_dir_absent_before_write" in failed:
        failure_class = "artifact_contract_failure"
    elif any(name.startswith(("source_", "manifest_")) for name in failed):
        failure_class = "source_evidence_manifest_materialization_contract_failure"
    elif any("dp_head" in name or "dp_fixed" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    else:
        failure_class = "artifact_contract_failure"
    decision: dict[str, Any] = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "uncertainty_coverage_evidence_manifest_materialized": passed,
        "evidence_manifest_materialized_by_this_gate": passed,
        "materialized_manifest_count": len(EXPECTED_MANIFESTS) if passed else 0,
        "evidence_manifest_materialization_static_review_authorized": passed,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "static_review_materialized_uncertainty_coverage_evidence_manifests_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_manifest_materialization_static_review_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
