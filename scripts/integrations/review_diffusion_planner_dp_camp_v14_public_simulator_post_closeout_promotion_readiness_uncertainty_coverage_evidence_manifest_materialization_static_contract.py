#!/usr/bin/env python3
"""Static review for materialized v14 uncertainty/coverage evidence manifests."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_materializer_module():
    materializer_path = Path(__file__).resolve().with_name(
        "materialize_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
        "uncertainty_coverage_evidence_manifests.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materializer",
        materializer_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MATERIALIZER_MODULE = _load_materializer_module()
PLAN_MODULE = MATERIALIZER_MODULE.PLAN_MODULE

FIXED_DP_HEAD = MATERIALIZER_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = MATERIALIZER_MODULE.SCORE_EXPRESSION
SOURCE_MATERIALIZATION_SCHEMA = MATERIALIZER_MODULE.SCHEMA_VERSION
SOURCE_MATERIALIZATION_STATUS = MATERIALIZER_MODULE.READY_STATUS
MANIFEST_SCHEMA_VERSION = MATERIALIZER_MODULE.MANIFEST_SCHEMA_VERSION
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_evidence_manifest_materialization_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = MATERIALIZER_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_only"
)
SOURCE_MATERIALIZATION_JSON_NAME = MATERIALIZER_MODULE.REPORT_JSON_NAME
SOURCE_MATERIALIZATION_MD_NAME = MATERIALIZER_MODULE.REPORT_MD_NAME
REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review.md"
)
EXPECTED_MANIFESTS = MATERIALIZER_MODULE.EXPECTED_MANIFESTS
EXPECTED_MATERIALIZATION_CHECK_COUNT = 200
EXPECTED_MATERIALIZED_MANIFEST_COUNT = 5
BLOCKED_ACTIONS = MATERIALIZER_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = MATERIALIZER_MODULE.FALSE_EXECUTION_FLAGS
ANALYSIS_FALSE_FLAGS = MATERIALIZER_MODULE.ANALYSIS_FALSE_FLAGS


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence_manifest_materialization_artifact_dir", type=Path, required=True)
    parser.add_argument("--evidence_manifest_materialization_json", type=Path, required=True)
    parser.add_argument("--evidence_manifest_materialization_md", type=Path, required=True)
    parser.add_argument("--evidence_manifest_materialization_sha256s", type=Path, required=True)
    parser.add_argument("--evidence_manifests_dir", type=Path, required=True)
    parser.add_argument("--evidence_manifests_sha256s", type=Path, required=True)
    parser.add_argument("--materializer_script_py", type=Path, required=True)
    parser.add_argument("--materializer_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review",
        action="store_true",
        help="Explicit opt-in for static review of materialized evidence manifests.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evidence_manifest_materialization_artifact_dir=args.evidence_manifest_materialization_artifact_dir,
        evidence_manifest_materialization_json=args.evidence_manifest_materialization_json,
        evidence_manifest_materialization_md=args.evidence_manifest_materialization_md,
        evidence_manifest_materialization_sha256s=args.evidence_manifest_materialization_sha256s,
        evidence_manifests_dir=args.evidence_manifests_dir,
        evidence_manifests_sha256s=args.evidence_manifests_sha256s,
        materializer_script_py=args.materializer_script_py,
        materializer_test_py=args.materializer_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evidence_manifest_materialization_artifact_dir: Path,
    evidence_manifest_materialization_json: Path,
    evidence_manifest_materialization_md: Path,
    evidence_manifest_materialization_sha256s: Path,
    evidence_manifests_dir: Path,
    evidence_manifests_sha256s: Path,
    materializer_script_py: Path,
    materializer_test_py: Path,
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
    artifact_dir = evidence_manifest_materialization_artifact_dir.resolve()
    manifests_dir = evidence_manifests_dir.resolve()
    paths = {
        "evidence_manifest_materialization_json": evidence_manifest_materialization_json.resolve(),
        "evidence_manifest_materialization_md": evidence_manifest_materialization_md.resolve(),
        "evidence_manifest_materialization_sha256s": evidence_manifest_materialization_sha256s.resolve(),
        "evidence_manifests_sha256s": evidence_manifests_sha256s.resolve(),
        "materializer_script_py": materializer_script_py.resolve(),
        "materializer_test_py": materializer_test_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "command": artifact_dir / "COMMAND",
        "heads": artifact_dir / "HEADS",
        "stdout": artifact_dir / "stdout.txt",
        "stderr": artifact_dir / "stderr.txt",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "materialization_json": artifact_dir / "materialization" / SOURCE_MATERIALIZATION_JSON_NAME,
        "materialization_md": artifact_dir / "materialization" / SOURCE_MATERIALIZATION_MD_NAME,
        "materialization_sha256s": artifact_dir / "materialization" / "SHA256SUMS",
        "manifests_sha256s": artifact_dir / "manifests" / "SHA256SUMS",
    }
    manifest_files = {
        name: manifests_dir / f"{name}.json"
        for name in EXPECTED_MANIFESTS
    }

    source_materialization = PLAN_MODULE._read_json_dict(paths["evidence_manifest_materialization_json"])
    manifest_payloads = {
        name: PLAN_MODULE._read_json_dict(path)
        for name, path in manifest_files.items()
        if path.is_file()
    }
    root_sha256s = PLAN_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    materialization_sha256s = PLAN_MODULE._read_sha256sums(paths["evidence_manifest_materialization_sha256s"])
    manifests_sha256s = PLAN_MODULE._read_sha256sums(paths["evidence_manifests_sha256s"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(artifact_files["heads"]))
    script_text = PLAN_MODULE._read_text(paths["materializer_script_py"])
    test_text = PLAN_MODULE._read_text(paths["materializer_test_py"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        PLAN_MODULE._expect("static_review_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._check("materialization_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        PLAN_MODULE._check("evidence_manifests_dir_exists", manifests_dir.is_dir(), str(manifests_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    for name, path in manifest_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"manifest_{name}", path, require_file=True))
    checks.extend(
        [
            PLAN_MODULE._expect("materialization_json_matches_artifact_layout", paths["evidence_manifest_materialization_json"], artifact_files["materialization_json"]),
            PLAN_MODULE._expect("materialization_md_matches_artifact_layout", paths["evidence_manifest_materialization_md"], artifact_files["materialization_md"]),
            PLAN_MODULE._expect("materialization_sha256s_matches_artifact_layout", paths["evidence_manifest_materialization_sha256s"], artifact_files["materialization_sha256s"]),
            PLAN_MODULE._expect("manifests_sha256s_matches_artifact_layout", paths["evidence_manifests_sha256s"], artifact_files["manifests_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, manifest_files, root_sha256s, materialization_sha256s, manifests_sha256s))
    checks.extend(_heads_checks(heads, source_materialization))
    checks.extend(_source_materialization_contract_checks(source_materialization))
    checks.extend(_manifest_contract_checks(manifest_payloads, source_materialization))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "evidence_manifest_materialization_static_review_only": True,
            "materialization_artifact_dir": str(artifact_dir),
            "evidence_manifests_dir": str(manifests_dir),
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
            for name, path in {**paths, **artifact_files, **manifest_files}.items()
        },
        "source_materialization_summary": _source_materialization_summary(source_materialization),
        "manifest_summary": _manifest_summary(manifest_payloads),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    PLAN_MODULE._write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    PLAN_MODULE._write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Static Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Manifest Summary",
    ]
    for key, value in report["manifest_summary"].items():
        lines.append(f"- {key}: `{PLAN_MODULE._compact(value)}`")
    lines.extend(["", "## Review Checks"])
    for check in report["review_checks"]:
        lines.append(
            f"- [{'x' if check['passed'] else ' '}] {check['name']}: "
            f"observed=`{PLAN_MODULE._compact(check['observed'])}` expected=`{PLAN_MODULE._compact(check['expected'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    manifest_files: dict[str, Path],
    root_sha256s: dict[str, str],
    materialization_sha256s: dict[str, str],
    manifests_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    checks = [
        PLAN_MODULE._sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        PLAN_MODULE._sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        PLAN_MODULE._sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        PLAN_MODULE._sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        PLAN_MODULE._sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        PLAN_MODULE._sha256sums_expect("artifact_materialization_json_root_sha", artifact_files["materialization_json"], root_sha256s, (f"materialization/{SOURCE_MATERIALIZATION_JSON_NAME}", f"./materialization/{SOURCE_MATERIALIZATION_JSON_NAME}", SOURCE_MATERIALIZATION_JSON_NAME)),
        PLAN_MODULE._sha256sums_expect("artifact_materialization_md_root_sha", artifact_files["materialization_md"], root_sha256s, (f"materialization/{SOURCE_MATERIALIZATION_MD_NAME}", f"./materialization/{SOURCE_MATERIALIZATION_MD_NAME}", SOURCE_MATERIALIZATION_MD_NAME)),
        PLAN_MODULE._sha256sums_expect("source_materialization_json_sha", artifact_files["materialization_json"], materialization_sha256s, (SOURCE_MATERIALIZATION_JSON_NAME, f"./{SOURCE_MATERIALIZATION_JSON_NAME}")),
        PLAN_MODULE._sha256sums_expect("source_materialization_md_sha", artifact_files["materialization_md"], materialization_sha256s, (SOURCE_MATERIALIZATION_MD_NAME, f"./{SOURCE_MATERIALIZATION_MD_NAME}")),
        PLAN_MODULE._expect("artifact_run_exit_zero", PLAN_MODULE._read_text(artifact_files["run_exit"]).strip(), "0"),
    ]
    for name, path in manifest_files.items():
        filename = f"{name}.json"
        checks.append(
            PLAN_MODULE._sha256sums_expect(
                f"manifest_{name}_root_sha",
                path,
                root_sha256s,
                (f"manifests/{filename}", f"./manifests/{filename}", filename),
            )
        )
        checks.append(
            PLAN_MODULE._sha256sums_expect(
                f"manifest_{name}_manifest_sha",
                path,
                manifests_sha256s,
                (filename, f"./{filename}"),
            )
        )
    return checks


def _heads_checks(heads: dict[str, str], source_materialization: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = {key.lower(): value for key, value in heads.items()}
    analysis = PLAN_MODULE._dict(source_materialization.get("analysis"))
    return [
        PLAN_MODULE._expect("artifact_heads_dp_fixed", normalized.get("dp_head"), FIXED_DP_HEAD),
        PLAN_MODULE._expect("artifact_heads_camp_matches_origin", normalized.get("camp_head"), normalized.get("camp_origin_main")),
        PLAN_MODULE._expect("artifact_heads_camp_matches_analysis", normalized.get("camp_head"), analysis.get("current_camp_head")),
        PLAN_MODULE._expect("artifact_heads_origin_matches_analysis", normalized.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_materialization_contract_checks(source_materialization: dict[str, Any]) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_materialization.get("final_decision"))
    checks = [
        PLAN_MODULE._expect("source_materialization_schema", source_materialization.get("schema_version"), SOURCE_MATERIALIZATION_SCHEMA),
        PLAN_MODULE._expect("source_materialization_status", decision.get("status"), SOURCE_MATERIALIZATION_STATUS),
        PLAN_MODULE._expect("source_materialization_passed", decision.get("passed"), True),
        PLAN_MODULE._expect("source_materialization_failure_class", decision.get("failure_class"), None),
        PLAN_MODULE._expect("source_materialization_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("source_materialization_static_review_authorized", decision.get("evidence_manifest_materialization_static_review_authorized"), True),
        PLAN_MODULE._expect("source_materialized_by_this_gate", decision.get("evidence_manifest_materialized_by_this_gate"), True),
        PLAN_MODULE._expect("source_materialized_manifest_count", decision.get("materialized_manifest_count"), EXPECTED_MATERIALIZED_MANIFEST_COUNT),
        PLAN_MODULE._expect("source_materialization_check_count", len(PLAN_MODULE._list(source_materialization.get("materialization_checks"))), EXPECTED_MATERIALIZATION_CHECK_COUNT),
        PLAN_MODULE._expect("source_materialized_file_count", len(PLAN_MODULE._list(source_materialization.get("materialized_manifest_files"))), EXPECTED_MATERIALIZED_MANIFEST_COUNT),
    ]
    for action in BLOCKED_ACTIONS:
        if action in decision:
            checks.append(PLAN_MODULE._expect(f"source_materialization_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        if flag in decision:
            checks.append(PLAN_MODULE._expect(f"source_materialization_decision_{flag}", decision.get(flag), False))
    return checks


def _manifest_contract_checks(
    manifests: dict[str, dict[str, Any]],
    source_materialization: dict[str, Any],
) -> list[dict[str, Any]]:
    source_files = {
        PLAN_MODULE._dict(item).get("manifest_name"): PLAN_MODULE._dict(item).get("sha256")
        for item in PLAN_MODULE._list(source_materialization.get("materialized_manifest_files"))
    }
    checks = [
        PLAN_MODULE._expect("manifest_names", list(manifests), list(EXPECTED_MANIFESTS)),
        PLAN_MODULE._expect("manifest_count", len(manifests), len(EXPECTED_MANIFESTS)),
    ]
    for name in EXPECTED_MANIFESTS:
        manifest = manifests.get(name, {})
        checks.extend(
            [
                PLAN_MODULE._expect(f"manifest_{name}_schema", manifest.get("schema_version"), MANIFEST_SCHEMA_VERSION),
                PLAN_MODULE._expect(f"manifest_{name}_name", manifest.get("manifest_name"), name),
                PLAN_MODULE._expect(f"manifest_{name}_source_sha_matches_report", PLAN_MODULE._sha256(Path(str(manifest.get("materialized_path")))) if Path(str(manifest.get("materialized_path"))).is_file() else source_files.get(name), source_files.get(name)),
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


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._check("materializer_script_schema_constant", "evidence_manifest_materialization_v1" in script_text, "evidence_manifest_materialization_v1", "present"),
        PLAN_MODULE._check("materializer_script_static_review_next", "evidence_manifest_materialization_static_review_only" in script_text, "evidence_manifest_materialization_static_review_only", "present"),
        PLAN_MODULE._check("materializer_test_writes_five_manifests", "writes_five_manifests" in test_text, "writes_five_manifests", "present"),
        PLAN_MODULE._check("materializer_test_rejects_existing_manifest_dir", "rejects_existing_manifest_dir" in test_text, "rejects_existing_manifest_dir", "present"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("audit_latest_status_is_materialized", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_MATERIALIZATION_STATUS),
        PLAN_MODULE._expect("audit_latest_eof_authorizes_static_review", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("audit_materialized_flag", PLAN_MODULE._latest_value(v14_text, "uncertainty_coverage_evidence_manifest_materialized"), "True"),
        PLAN_MODULE._expect("audit_static_review_authorized_flag", PLAN_MODULE._latest_value(v14_text, "evidence_manifest_materialization_static_review_authorized"), "True"),
        PLAN_MODULE._expect("audit_selector_promotion_false", PLAN_MODULE._latest_value(v14_text, "selector_promotion_authorized"), "False"),
        PLAN_MODULE._expect("audit_deployment_false", PLAN_MODULE._latest_value(v14_text, "deployment_authorized"), "False"),
        PLAN_MODULE._expect("audit_safety_claim_false", PLAN_MODULE._latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        PLAN_MODULE._expect("audit_camp_over_dp_claim_false", PLAN_MODULE._latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
        PLAN_MODULE._expect("status_doc_latest_status_is_materialized", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_MATERIALIZATION_STATUS),
        PLAN_MODULE._expect("status_doc_latest_eof_authorizes_static_review", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("status_doc_mentions_static_review_next", AUTHORIZED_CURRENT_WORK in status_text, AUTHORIZED_CURRENT_WORK, "present"),
    ]


def _source_materialization_summary(source_materialization: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_materialization.get("final_decision"))
    return {
        "schema_version": source_materialization.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "materialization_check_count": len(PLAN_MODULE._list(source_materialization.get("materialization_checks"))),
        "materialized_manifest_count": decision.get("materialized_manifest_count"),
    }


def _manifest_summary(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "manifest_count": len(manifests),
        "manifest_names": list(manifests),
        "all_materialized": all(manifest.get("materialized_by_this_gate") is True for manifest in manifests.values()),
        "all_no_execution": all(manifest.get("authorizes_execution") is False for manifest in manifests.values()),
        "all_no_claim": all(manifest.get("authorizes_claim") is False for manifest in manifests.values()),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_uncertainty_coverage_evidence_manifest_materialization_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any(name.startswith(("source_", "manifest_", "materializer_")) for name in failed):
        failure_class = "source_evidence_manifest_materialization_static_review_contract_failure"
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
        "uncertainty_coverage_evidence_manifest_materialization_static_review_passed": passed,
        "uncertainty_coverage_evidence_package_construction_plan_authorized": passed,
        "evidence_package_construction_plan_authorized": passed,
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "score_expression": SCORE_EXPRESSION,
        "recommendation": "plan_uncertainty_coverage_evidence_package_construction_only" if passed else "repair_contract_before_rerun",
        "immediate_action": "evidence_package_construction_plan_only" if passed else "inspect_failed_checks",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


if __name__ == "__main__":
    raise SystemExit(main())
